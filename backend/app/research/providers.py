import asyncio
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from app.config import get_settings


@dataclass(frozen=True)
class SearchQuery:
    text: str
    category: str


@dataclass(frozen=True)
class OpenAccessLocation:
    url: str
    repository: str | None = None
    version_type: str = "unknown"
    license: str | None = None
    doi: str | None = None
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    publication_date: str | None = None


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    publisher: str | None = None
    authors: list[str] = field(default_factory=list)
    publication_date: str | None = None
    doi: str | None = None
    source_type: str = "web"
    provider: str = ""
    rank: int | None = None
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    relevance_score: float = 0.0
    relevance_status: str = "unassessed"
    relevance_reasons: list[str] = field(default_factory=list)
    open_access_locations: list[OpenAccessLocation] = field(default_factory=list)


class ResearchProviderError(RuntimeError):
    pass


class ResearchProvider(ABC):
    name: str

    def __init__(self) -> None:
        settings = get_settings()
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.request_timeout_seconds),
            headers={"User-Agent": settings.research_user_agent},
            follow_redirects=False,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def request_json(self, url: str, **kwargs: Any) -> dict[str, Any]:
        for attempt in range(get_settings().provider_retry_count + 1):
            try:
                response = await self.client.get(url, **kwargs)
                if response.status_code >= 500 and attempt < get_settings().provider_retry_count:
                    await asyncio.sleep(0.25 * (attempt + 1))
                    continue
                response.raise_for_status()
                return response.json()
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt >= get_settings().provider_retry_count:
                    raise ResearchProviderError(f"{self.name} request failed.") from exc
                await asyncio.sleep(0.25 * (attempt + 1))
            except (httpx.HTTPStatusError, ValueError) as exc:
                raise ResearchProviderError(f"{self.name} returned an invalid response.") from exc
        raise ResearchProviderError(f"{self.name} request failed.")

    @abstractmethod
    async def search(self, query: SearchQuery, limit: int) -> list[SearchResult]:
        raise NotImplementedError


class TavilyProvider(ResearchProvider):
    name = "tavily"

    async def search(self, query: SearchQuery, limit: int) -> list[SearchResult]:
        api_key = get_settings().tavily_api_key
        if not api_key:
            raise ResearchProviderError("Tavily is not configured; set NEOMON_TAVILY_API_KEY.")
        response = await self.client.post(
            "https://api.tavily.com/search",
            json={"api_key": api_key, "query": query.text, "max_results": limit, "search_depth": "advanced"},
        )
        response.raise_for_status()
        data = response.json()
        return [
            SearchResult(
                title=item.get("title", "Untitled source"),
                url=item["url"],
                snippet=item.get("content", ""),
                provider=self.name,
                rank=index + 1,
            )
            for index, item in enumerate(data.get("results", []))
            if item.get("url")
        ]


class CrossrefProvider(ResearchProvider):
    name = "crossref"

    async def search(self, query: SearchQuery, limit: int) -> list[SearchResult]:
        data = await self.request_json(
            "https://api.crossref.org/works",
            params={
                "query": query.text,
                "rows": limit,
                "select": "title,URL,DOI,author,published,container-title,publisher",
            },
        )
        results: list[SearchResult] = []
        for index, item in enumerate(data.get("message", {}).get("items", [])):
            url = item.get("URL") or (f"https://doi.org/{item['DOI']}" if item.get("DOI") else None)
            title = (item.get("title") or ["Untitled source"])[0]
            if not url:
                continue
            abstract = re.sub("<[^>]+>", " ", item.get("abstract") or "")
            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=" ".join(abstract.split()),
                    publisher=item.get("publisher"),
                    authors=[f"{a.get('given', '')} {a.get('family', '')}".strip() for a in item.get("author", [])],
                    publication_date=str((item.get("published", {}).get("date-parts") or [[""]])[0][0]),
                    doi=item.get("DOI"),
                    source_type="academic",
                    provider=self.name,
                    rank=index + 1,
                )
            )
        return results


class OpenAlexProvider(ResearchProvider):
    name = "openalex"

    async def search(self, query: SearchQuery, limit: int) -> list[SearchResult]:
        data = await self.request_json(
            "https://api.openalex.org/works",
            params={"search": query.text, "per-page": limit},
        )
        results: list[SearchResult] = []
        for index, item in enumerate(data.get("results", [])):
            url = item.get("doi") or item.get("primary_location", {}).get("landing_page_url")
            if not url:
                continue
            doi = item.get("doi") or ""
            abstract_index = item.get("abstract_inverted_index") or {}
            positioned_words: list[tuple[int, str]] = [
                (pos, word)
                for word, positions in abstract_index.items()
                if isinstance(positions, list)
                for pos in positions
                if isinstance(pos, int)
            ]
            positioned_words.sort(key=lambda pair: pair[0])
            abstract_words = [word for _, word in positioned_words]
            authors = [
                author.get("author", {}).get("display_name", "")
                for author in item.get("authorships", [])
                if author.get("author", {}).get("display_name")
            ]
            locations = []
            for location in item.get("locations", []):
                landing_url = location.get("landing_page_url")
                pdf_url = location.get("pdf_url")
                candidate_url = pdf_url or landing_url
                if not candidate_url:
                    continue
                location_source = location.get("source") or {}
                locations.append(
                    OpenAccessLocation(
                        url=candidate_url,
                        repository=location_source.get("display_name"),
                        version_type=location.get("version") or "unknown",
                        license=location.get("license"),
                        doi=item.get("doi"),
                        title=item.get("title"),
                        authors=authors,
                        publication_date=item.get("publication_date"),
                    )
                )
            results.append(
                SearchResult(
                    title=item.get("title", "Untitled source"),
                    url=url,
                    snippet=" ".join(abstract_words),
                    authors=authors,
                    publication_date=item.get("publication_date"),
                    doi=doi.removeprefix("https://doi.org/") or None,
                    source_type="academic",
                    provider=self.name,
                    rank=index + 1,
                    open_access_locations=locations,
                )
            )
        return results


class ArxivProvider(ResearchProvider):
    name = "arxiv"

    async def search(self, query: SearchQuery, limit: int) -> list[SearchResult]:
        url = "https://export.arxiv.org/api/query"
        response = await self.client.get(url, params={"search_query": f"all:{query.text}", "max_results": limit})
        response.raise_for_status()
        import xml.etree.ElementTree as element_tree

        root = element_tree.fromstring(response.text)
        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        results = []
        for index, entry in enumerate(root.findall("atom:entry", namespace)):
            link = entry.findtext("atom:id", namespaces=namespace)
            if not link:
                continue
            pdf_link = link.replace("http://arxiv.org/abs/", "https://arxiv.org/pdf/").replace(
                "https://arxiv.org/abs/", "https://arxiv.org/pdf/"
            ) + ".pdf"
            results.append(
                SearchResult(
                    title=" ".join((entry.findtext("atom:title", namespaces=namespace) or "").split()),
                    url=link,
                    snippet=" ".join((entry.findtext("atom:summary", namespaces=namespace) or "").split()),
                    authors=[author.text or "" for author in entry.findall("atom:author/atom:name", namespace)],
                    publication_date=entry.findtext("atom:published", namespaces=namespace),
                    source_type="academic",
                    provider=self.name,
                    rank=index + 1,
                    open_access_locations=[
                        OpenAccessLocation(
                            url=pdf_link,
                            repository="arXiv",
                            version_type="preprint",
                            title=" ".join((entry.findtext("atom:title", namespaces=namespace) or "").split()),
                            authors=[author.text or "" for author in entry.findall("atom:author/atom:name", namespace)],
                            publication_date=entry.findtext("atom:published", namespaces=namespace),
                        )
                    ],
                )
            )
        return results


class UnpaywallProvider:
    name = "unpaywall"

    def __init__(self) -> None:
        settings = get_settings()
        self.email = settings.unpaywall_email
        self.api_key = settings.unpaywall_api_key
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.request_timeout_seconds),
            headers={"User-Agent": settings.research_user_agent},
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def lookup(self, doi: str) -> list[OpenAccessLocation]:
        if not self.email:
            return []
        params = {"email": self.email}
        if self.api_key:
            params["api_key"] = self.api_key
        try:
            response = await self.client.get(f"https://api.unpaywall.org/v2/{doi}", params=params)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ResearchProviderError("Unpaywall lookup failed.") from exc
        locations: list[OpenAccessLocation] = []
        for item in data.get("oa_locations", []):
            url = item.get("url_for_pdf") or item.get("url")
            if not url:
                continue
            locations.append(
                OpenAccessLocation(
                    url=url,
                    repository=item.get("host_type") or item.get("repository_institution"),
                    version_type=item.get("version") or "unknown",
                    license=item.get("license"),
                    doi=data.get("doi"),
                    title=data.get("title"),
                    authors=[author.get("family", "") for author in data.get("z_authors", []) if author.get("family")],
                    publication_date=str(data.get("year")) if data.get("year") else None,
                )
            )
        return locations


def build_research_providers() -> list[ResearchProvider]:
    return [TavilyProvider(), CrossrefProvider(), OpenAlexProvider(), ArxivProvider()]
