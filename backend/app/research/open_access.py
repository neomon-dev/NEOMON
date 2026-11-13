import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.research.providers import OpenAccessLocation, SearchResult


@dataclass(frozen=True)
class LocationAssessment:
    status: str
    score: float
    reason: str


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    return value.casefold().strip().removeprefix("https://doi.org/").removeprefix("doi:")


def _title_terms(value: str) -> set[str]:
    return {
        term
        for term in re.findall(r"[a-z0-9]{2,}", value.casefold())
        if term not in {"the", "and", "for", "with", "from", "study", "what", "how", "does", "are"}
    }


def _title_similarity(left: str, right: str) -> float:
    left_terms = _title_terms(left)
    right_terms = _title_terms(right)
    return len(left_terms & right_terms) / max(1, len(left_terms | right_terms))


def _author_key(value: str) -> str:
    terms = re.findall(r"[a-z0-9]+", value.casefold())
    return terms[-1] if terms else ""


def assess_location(result: SearchResult, location: OpenAccessLocation) -> LocationAssessment:
    checks: list[str] = []
    score = 0.0
    result_doi = normalize_doi(result.doi)
    location_doi = normalize_doi(location.doi)
    if result_doi and location_doi:
        if result_doi != location_doi:
            return LocationAssessment("rejected", 0.0, "candidate DOI does not match the source DOI")
        score += 0.55
        checks.append("DOI matches")
    elif location.title:
        similarity = _title_similarity(result.title, location.title)
        if similarity < 0.25:
            return LocationAssessment("rejected", similarity, "candidate title does not match the source title")
        score += min(0.45, similarity)
        checks.append(f"title similarity {similarity:.2f}")
    else:
        checks.append("candidate has no independent metadata; identity relies on the source record")

    if result.publication_date and location.publication_date:
        result_year = (re.search(r"\d{4}", result.publication_date) or [None])[0]
        location_year = (re.search(r"\d{4}", location.publication_date) or [None])[0]
        if result_year and location_year:
            if abs(int(result_year) - int(location_year)) > 2:
                return LocationAssessment("rejected", score, "candidate publication year conflicts with the source")
            score += 0.2
            checks.append("publication year matches")
    if result.authors and location.authors:
        source_authors = {_author_key(author) for author in result.authors}
        candidate_authors = {_author_key(author) for author in location.authors}
        source_authors.discard("")
        candidate_authors.discard("")
        if not source_authors & candidate_authors:
            return LocationAssessment("rejected", score, "candidate authors do not overlap the source authors")
        score += 0.15
        checks.append("author metadata overlaps")
    host = urlsplit(location.url).hostname or ""
    if any(marker in host.casefold() for marker in ("arxiv.org", "repository", "edu", "ac.uk")):
        score += 0.1
        checks.append("candidate is hosted by a repository or academic domain")
    status = "matched" if score >= 0.45 else "uncertain"
    return LocationAssessment(status, round(min(score, 1.0), 3), "; ".join(checks))
