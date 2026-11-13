import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from io import BytesIO
from urllib.parse import urljoin, urlsplit

import httpx
from pypdf import PdfReader

from app.config import get_settings


class RetrievalError(RuntimeError):
    pass


@dataclass
class RetrievedDocument:
    url: str
    final_url: str
    content_type: str
    title: str | None
    content: str
    headings: list[str]
    passages: list[tuple[int | None, str, str | None]]
    access_level: str
    extraction_quality: str
    page_count: int | None = None


_VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


class _HTMLTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title: str | None = None
        self.headings: list[str] = []
        self.parts: list[tuple[str | None, str]] = []
        self._stack: list[tuple[str, bool, bool, bool]] = []  # (tag, excluded, is_content, is_abstract)
        self._section: str | None = None

    @staticmethod
    def _is_boilerplate(tag: str, attrs: list[tuple[str, str | None]]) -> bool:
        if tag in {"nav", "header", "footer", "aside", "form", "button", "dialog", "script", "style", "noscript", "svg", "iframe"}:
            return True
        values = " ".join(value or "" for key, value in attrs if key in {"id", "class", "role", "aria-label"}).casefold()
        return any(
            marker in values
            for marker in ("nav", "menu", "sidebar", "cookie", "advert", "social", "related", "share", "promo", "search-form", "breadcrumb")
        )

    @property
    def is_excluded(self) -> bool:
        return any(excluded for _, excluded, _, _ in self._stack)

    @property
    def content_depth(self) -> int:
        return sum(1 for _, _, is_content, _ in self._stack if is_content)

    @property
    def abstract_depth(self) -> int:
        return sum(1 for _, _, _, is_abstract in self._stack if is_abstract)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _VOID_ELEMENTS:
            return
        excluded = self._is_boilerplate(tag, attrs)
        values = " ".join(value or "" for key, value in attrs if key in {"id", "class", "role"}).casefold()
        is_content = tag in {"article", "main"}
        is_abstract = "abstract" in values
        self._stack.append((tag, excluded, is_content, is_abstract))

    def handle_endtag(self, tag: str) -> None:
        while self._stack:
            stacked_tag, _, _, _ = self._stack.pop()
            if stacked_tag in {"article", "section", "main", "footer", "aside", "nav"}:
                self._section = None
            if stacked_tag == tag:
                break

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text or self.is_excluded:
            return
        tag = self._stack[-1][0] if self._stack else None
        if tag == "title":
            self.title = text[:500]
        if tag in {"h1", "h2", "h3"}:
            self.headings.append(text[:300])
            self._section = text[:300]
        if self.content_depth or tag in {"body", "p", "h1", "h2", "h3", "h4", "li", "blockquote", "div", "section"}:
            self.parts.append((self._section, text))

    @property
    def abstract_only(self) -> bool:
        return bool(self.parts) and self.abstract_depth > 0



async def _validate_public_host(hostname: str) -> None:
    if not hostname:
        raise RetrievalError("URL must include a hostname.")
    try:
        addresses = await asyncio.to_thread(socket.getaddrinfo, hostname, None)
    except socket.gaierror as exc:
        raise RetrievalError("URL hostname could not be resolved.") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise RetrievalError("Private and non-public addresses are not allowed.")


async def retrieve_document(url: str) -> RetrievedDocument:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        raise RetrievalError("Only HTTP(S) URLs are supported.")
    await _validate_public_host(parts.hostname or "")
    settings = get_settings()
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(settings.request_timeout_seconds),
        follow_redirects=False,
        headers={"User-Agent": settings.research_user_agent},
    ) as client:
        current_url = url
        try:
            for _ in range(5):
                current_parts = urlsplit(current_url)
                await _validate_public_host(current_parts.hostname or "")
                response = await client.get(current_url)
                if not response.is_redirect:
                    break
                location = response.headers.get("location")
                if not location:
                    raise RetrievalError("Redirect did not include a destination.")
                current_url = urljoin(current_url, location)
                redirected_parts = urlsplit(current_url)
                if redirected_parts.scheme not in {"http", "https"}:
                    raise RetrievalError("Redirect destination must use HTTP(S).")
            else:
                raise RetrievalError("Too many redirects.")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RetrievalError(f"Document request failed: {exc}") from exc
        content_type = response.headers.get("content-type", "").split(";")[0].lower()
        if content_type not in {"text/html", "text/plain", "application/pdf", "application/json"}:
            raise RetrievalError(f"Unsupported content type: {content_type or 'unknown'}.")
        if len(response.content) > settings.research_max_document_bytes:
            raise RetrievalError("Document exceeds the configured size limit.")
        if content_type == "text/html":
            parser = _HTMLTextParser()
            parser.feed(response.text)
            passages = [(None, text, section) for section, text in parser.parts]
            content = "\n".join(text for _, text, _ in passages)[: settings.research_max_document_bytes]
            if not content:
                raise RetrievalError("HTML document did not contain extractable research text.")
            access_level = "full_text" if len(content) >= 1800 and len(parser.headings) >= 2 else "abstract_only"
            quality = "high" if parser.content_depth or len(content) >= 1200 else "medium"
            return RetrievedDocument(
                url,
                str(response.url),
                content_type,
                parser.title,
                content,
                parser.headings,
                passages,
                access_level,
                quality,
            )
        if content_type == "application/pdf":
            try:
                reader = PdfReader(BytesIO(response.content))
                page_passages = [(index + 1, page.extract_text() or "", None) for index, page in enumerate(reader.pages)]
                content = "\n".join(text for _, text, _ in page_passages)
            except Exception as exc:
                raise RetrievalError("PDF text extraction failed.") from exc
            if not content.strip():
                raise RetrievalError("PDF did not contain extractable text.")
            return RetrievedDocument(
                url,
                str(response.url),
                content_type,
                None,
                content[: settings.research_max_document_bytes],
                [],
                page_passages,
                "full_text",
                "high" if len(content) >= 1200 else "medium",
                len(reader.pages),
            )
        content = response.text[: settings.research_max_document_bytes]
        if not content.strip():
            raise RetrievalError("Document did not contain extractable text.")
        return RetrievedDocument(
            url,
            str(response.url),
            content_type,
            None,
            content,
            [],
            [(None, content, None)],
            "metadata_only" if len(content) < 500 else "abstract_only",
            "low" if len(content) < 500 else "medium",
        )
