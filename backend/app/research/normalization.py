import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.research.providers import SearchResult


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(key, value) for key, value in parse_qsl(parts.query) if not key.lower().startswith(("utm_", "fbclid"))]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def normalize_title(title: str) -> str:
    return re.sub(r"\W+", " ", title.casefold()).strip()


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def deduplicate_results(results: list[SearchResult]) -> list[SearchResult]:
    seen_urls: set[str] = set()
    seen_dois: set[str] = set()
    seen_titles: set[str] = set()
    unique: list[SearchResult] = []
    for result in results:
        result.url = normalize_url(result.url)
        title = normalize_title(result.title)
        doi = result.doi.casefold() if result.doi else None
        if result.url in seen_urls or (doi and doi in seen_dois) or title in seen_titles:
            # If the duplicate has richer metadata (e.g. DOI or academic classification), enrich the existing item
            for existing in unique:
                if (
                    existing.url == result.url
                    or (doi and existing.doi and existing.doi.casefold() == doi)
                    or normalize_title(existing.title) == title
                ):
                    if not existing.doi and result.doi:
                        existing.doi = result.doi
                    if not existing.open_access_locations and result.open_access_locations:
                        existing.open_access_locations = result.open_access_locations
                    if existing.source_type == "web" and result.source_type == "academic":
                        existing.source_type = "academic"
                        existing.publisher = existing.publisher or result.publisher
                        existing.authors = existing.authors or result.authors
                    break
            continue
        seen_urls.add(result.url)
        seen_titles.add(title)
        if doi:
            seen_dois.add(doi)
        unique.append(result)
    return unique
