"""Canonical Source Credibility and Verification Architecture (Milestone 8G.1).

Separates:
1. Source Type (peer_reviewed_journal, academic_preprint, institutional_report, etc.)
2. Verification Status (verified, high_confidence, unverified, disputed, self_declared)
3. Evidence Quality Attributes (is_peer_reviewed, is_primary, confidence, credibility_score)

Rules:
- Never equate DOI presence or declared type with verified peer review.
- Preprints (arXiv, bioRxiv, etc.) have DOIs but are strictly NOT peer-reviewed.
- Repository-hosted DOIs (Zenodo, Figshare, OSF) are unverified unless corroborated by journal indexing.
- Government/Institutional reports are authoritative primary sources but not peer-reviewed.
- Always provide explicit, explainable reasons and preserve uncertainty.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import urlsplit


class CanonicalSourceType(StrEnum):
    PEER_REVIEWED_JOURNAL = "peer_reviewed_journal"
    ACADEMIC_CONFERENCE_PROCEEDING = "academic_conference_proceeding"
    INSTITUTIONAL_REPORT = "institutional_report"
    ACADEMIC_PREPRINT = "academic_preprint"
    TECHNICAL_WHITEPAPER = "technical_whitepaper"
    NEWS_SYNDICATION = "news_syndication"
    REPUTABLE_JOURNALISM = "reputable_journalism"
    BLOG_EDITORIAL = "blog_editorial"
    UNVERIFIED_WEB = "unverified_web"


class SourceVerificationStatus(StrEnum):
    VERIFIED = "verified"
    HIGH_CONFIDENCE = "high_confidence"
    UNVERIFIED = "unverified"
    DISPUTED = "disputed"
    SELF_DECLARED = "self_declared"


# Recognized academic publishers and verified journal/conference venues
_VERIFIED_JOURNAL_PUBLISHERS = {
    "ieee", "acm", "springer", "elsevier", "nature", "science", "wiley",
    "oxford university press", "cambridge university press", "plos",
    "cell press", "frontiers", "pnas", "taylor & francis", "sage",
    "iop publishing", "royal society of chemistry", "american chemical society",
    "american physical society", "biorxiv", "medrxiv"
}

_VERIFIED_JOURNAL_HOSTS = {
    "nature.com",
    "science.org",
    "sciencemag.org",
    "ieeexplore.ieee.org",
    "dl.acm.org",
    "springer.com",
    "link.springer.com",
    "sciencedirect.com",
    "elsevier.com",
    "wiley.com",
    "onlinelibrary.wiley.com",
    "pnas.org",
    "cell.com",
    "plos.org",
    "frontiersin.org",
    "tandfonline.com",
    "oup.com",
    "cambridge.org",
    "iop.org",
    "aps.org",
    "acspubs.org",
    "nejm.org",
    "thelancet.com",
    "bmj.com",
    "jamanetwork.com",
}

_ACADEMIC_CONFERENCE_KEYWORDS = {
    "neurips", "icml", "iclr", "cvpr", "iccv", "eccv", "acl", "emnlp",
    "naacl", "aaai", "ijcai", "sigkdd", "kdd", "sigir", "sigcomm", "mobicom",
    "osdi", "sosp", "asplos", "micro", "isca", "usenix", "vldb", "sigmod"
}

_PREPRINT_HOSTS = {
    "arxiv.org",
    "biorxiv.org",
    "medrxiv.org",
    "chemrxiv.org",
    "techrxiv.org",
    "ssrn.com",
    "preprints.org",
    "researchsquare.com",
    "philsci-archive.pitt.edu",
    "hal.science",
}

_REPOSITORY_DOI_HOSTS = {
    "zenodo.org",
    "figshare.com",
    "osf.io",
    "datadryad.org",
    "dataverse.harvard.edu",
    "github.com",
    "gitlab.com",
}

_INSTITUTIONAL_HOSTS = {
    "who.int",
    "cdc.gov",
    "nih.gov",
    "ncbi.nlm.nih.gov",
    "nsf.gov",
    "nist.gov",
    "nasa.gov",
    "noaa.gov",
    "un.org",
    "oecd.org",
    "worldbank.org",
    "imf.org",
    "bis.org",
    "ecb.europa.eu",
    "europa.eu",
    "bls.gov",
    "cbo.gov",
    "sec.gov",
    "ftc.gov",
    "energy.gov",
}

_REPUTABLE_JOURNALISM_HOSTS = {
    "reuters.com",
    "bloomberg.com",
    "wsj.com",
    "ft.com",
    "nytimes.com",
    "economist.com",
    "bbc.com",
    "bbc.co.uk",
    "apnews.com",
    "theguardian.com",
    "washingtonpost.com",
}

_TECH_INDUSTRY_JOURNALISM_HOSTS = {
    "arstechnica.com",
    "technologyreview.com",
    "theverge.com",
    "wired.com",
    "tomshardware.com",
    "anandtech.com",
    "semianalysis.com",
    "techcrunch.com",
    "zdnet.com",
    "venturebeat.com",
    "theregister.com",
    "ee-times.com",
    "eetimes.com",
}

_COMMUNITY_BLOG_HOSTS = {
    "medium.com",
    "substack.com",
    "reddit.com",
    "quora.com",
    "wikipedia.org",
    "youtube.com",
    "youtu.be",
    "linkedin.com",
    "dev.to",
    "hashnode.com",
}


@dataclass(frozen=True)
class CanonicalCredibilityEvaluation:
    source_type: CanonicalSourceType
    verification_status: SourceVerificationStatus
    is_peer_reviewed: bool
    is_primary: bool
    credibility_score: float
    confidence: float
    venue: str | None
    reasons: list[str] = field(default_factory=list)


def evaluate_canonical_credibility(
    url: str | None,
    publisher: str | None = None,
    doi: str | None = None,
    source_type_declared: str | None = None,
    authors: list[str] | None = None,
    publication_date: str | None = None,
    title: str | None = None,
) -> CanonicalCredibilityEvaluation:
    """Evaluate source credibility with strict verification separation.
    
    Guarantees:
    - Having a DOI does NOT make a source peer-reviewed.
    - Preprints are classified as academic_preprint and is_peer_reviewed=False.
    - Government/institutional reports are classified as institutional_report.
    - Syndicated tech journalism is recognized as secondary reporting.
    """
    clean_url = (url or "").strip()
    parsed = urlsplit(clean_url)
    host = parsed.netloc.lower().removeprefix("www.")
    pub_lower = (publisher or "").strip().lower()
    title_lower = (title or "").strip().lower()
    decl_lower = (source_type_declared or "").strip().lower()
    doi_clean = (doi or "").strip().lower()

    reasons: list[str] = []
    venue: str | None = publisher or None

    # 1. Academic Preprint Check (Preprints have DOIs, but are NOT peer-reviewed)
    is_preprint_host = any(ph in host for ph in _PREPRINT_HOSTS)
    is_preprint_pub = any(kw in pub_lower for kw in ("arxiv", "biorxiv", "medrxiv", "ssrn", "preprint"))
    is_preprint_doi = "10.48550/arxiv" in doi_clean or "biorxiv" in doi_clean or "medrxiv" in doi_clean
    if is_preprint_host or is_preprint_pub or is_preprint_doi or decl_lower == "preprint":
        reasons.append("Academic preprint identified: contains scholarly methodology but has not undergone formal peer review.")
        return CanonicalCredibilityEvaluation(
            source_type=CanonicalSourceType.ACADEMIC_PREPRINT,
            verification_status=SourceVerificationStatus.HIGH_CONFIDENCE,
            is_peer_reviewed=False,
            is_primary=True,
            credibility_score=0.75,
            confidence=0.90,
            venue=venue or "Preprint Repository",
            reasons=reasons,
        )

    # 2. General Data/Code Repositories with DOIs (Zenodo, Figshare, OSF)
    is_repo_host = any(rh in host for rh in _REPOSITORY_DOI_HOSTS)
    if is_repo_host:
        reasons.append("Hosted on open data/code repository; DOI represents persistent identifier, not peer-reviewed publication.")
        return CanonicalCredibilityEvaluation(
            source_type=CanonicalSourceType.TECHNICAL_WHITEPAPER,
            verification_status=SourceVerificationStatus.UNVERIFIED,
            is_peer_reviewed=False,
            is_primary=False,
            credibility_score=0.55,
            confidence=0.80,
            venue=venue or host,
            reasons=reasons,
        )

    # 3. Peer-Reviewed Academic Journals and Top Conferences
    is_verified_journal_host = any(jh in host for jh in _VERIFIED_JOURNAL_HOSTS)
    is_verified_journal_pub = any(jp in pub_lower for jp in _VERIFIED_JOURNAL_PUBLISHERS)
    is_conf = any(ck in title_lower or ck in pub_lower for ck in _ACADEMIC_CONFERENCE_KEYWORDS)

    if is_verified_journal_host or is_verified_journal_pub:
        st = CanonicalSourceType.ACADEMIC_CONFERENCE_PROCEEDING if is_conf else CanonicalSourceType.PEER_REVIEWED_JOURNAL
        v_status = SourceVerificationStatus.VERIFIED if doi_clean else SourceVerificationStatus.HIGH_CONFIDENCE
        reasons.append(f"Published by recognized scholarly venue ({publisher or host}) with editorial and peer-review process.")
        return CanonicalCredibilityEvaluation(
            source_type=st,
            verification_status=v_status,
            is_peer_reviewed=True,
            is_primary=True,
            credibility_score=0.95,
            confidence=0.95 if doi_clean else 0.85,
            venue=venue or host,
            reasons=reasons,
        )

    # 4. Institutional and Government Authorities
    is_gov_or_mil = host.endswith(".gov") or host.endswith(".mil") or host.endswith(".int")
    is_inst_host = any(ih in host for ih in _INSTITUTIONAL_HOSTS)
    if is_gov_or_mil or is_inst_host:
        reasons.append(f"Official governmental or multilateral research institution ({host}). Primary institutional authority.")
        return CanonicalCredibilityEvaluation(
            source_type=CanonicalSourceType.INSTITUTIONAL_REPORT,
            verification_status=SourceVerificationStatus.VERIFIED,
            is_peer_reviewed=False,  # High authority primary, but not academic peer review
            is_primary=True,
            credibility_score=0.90,
            confidence=0.92,
            venue=venue or host,
            reasons=reasons,
        )

    # 5. Reputable Global Journalism (Secondary Reporting)
    is_rep_journalism = any(rh in host for rh in _REPUTABLE_JOURNALISM_HOSTS)
    if is_rep_journalism:
        reasons.append(f"Established investigative journalism outlet ({host}); authoritative secondary reporting.")
        return CanonicalCredibilityEvaluation(
            source_type=CanonicalSourceType.REPUTABLE_JOURNALISM,
            verification_status=SourceVerificationStatus.HIGH_CONFIDENCE,
            is_peer_reviewed=False,
            is_primary=False,
            credibility_score=0.75,
            confidence=0.88,
            venue=venue or host,
            reasons=reasons,
        )

    # 6. Tech Industry & Trade Press (Syndicated / Investigative)
    is_tech_press = any(th in host for th in _TECH_INDUSTRY_JOURNALISM_HOSTS)
    if is_tech_press:
        reasons.append(f"Specialized technology trade publication ({host}); technical coverage and reporting.")
        return CanonicalCredibilityEvaluation(
            source_type=CanonicalSourceType.NEWS_SYNDICATION,
            verification_status=SourceVerificationStatus.HIGH_CONFIDENCE,
            is_peer_reviewed=False,
            is_primary=False,
            credibility_score=0.65,
            confidence=0.80,
            venue=venue or host,
            reasons=reasons,
        )

    # 7. Unverified DOI check (e.g. corporate whitepapers or unlisted publishers registering a DOI)
    if doi_clean:
        reasons.append("Source possesses a registered DOI, but publisher/venue is not an established peer-reviewed journal or academic proceeding. Peer review remains unverified.")
        return CanonicalCredibilityEvaluation(
            source_type=CanonicalSourceType.TECHNICAL_WHITEPAPER,
            verification_status=SourceVerificationStatus.UNVERIFIED,
            is_peer_reviewed=False,
            is_primary=False,
            credibility_score=0.60,
            confidence=0.65,
            venue=venue or host,
            reasons=reasons,
        )

    # 8. Community / User-Generated / Blog
    is_community = any(ch in host for ch in _COMMUNITY_BLOG_HOSTS)
    if is_community or decl_lower in ("blog", "forum", "community"):
        reasons.append(f"Community-generated content or opinion editorial ({host}); variable reliability without editorial verification.")
        return CanonicalCredibilityEvaluation(
            source_type=CanonicalSourceType.BLOG_EDITORIAL,
            verification_status=SourceVerificationStatus.UNVERIFIED,
            is_peer_reviewed=False,
            is_primary=False,
            credibility_score=0.40,
            confidence=0.75,
            venue=venue or host,
            reasons=reasons,
        )

    # 9. Generic Web Fallback
    reasons.append("General web document without verified institutional affiliation or peer-review indexing.")
    return CanonicalCredibilityEvaluation(
        source_type=CanonicalSourceType.UNVERIFIED_WEB,
        verification_status=SourceVerificationStatus.UNVERIFIED,
        is_peer_reviewed=False,
        is_primary=False,
        credibility_score=0.35,
        confidence=0.50,
        venue=venue or host,
        reasons=reasons,
    )
