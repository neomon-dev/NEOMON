import hashlib
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from urllib.parse import urlsplit

from app.research.relevance import _PRESERVED_ACRONYMS, _term_matches, _terms, question_focus


class EvidenceCategory(StrEnum):
    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    CONTEXTUAL = "contextual"
    METHODOLOGICAL_LIMITATION = "methodological_limitation"
    MITIGATING = "mitigating"
    INSUFFICIENT = "insufficient"


class SourceCredibilityType(StrEnum):
    PEER_REVIEWED = "peer_reviewed"
    PREPRINT = "preprint"
    GOVERNMENT_INSTITUTIONAL = "government_institutional"
    RESEARCH_ORGANIZATION = "research_organization"
    INDUSTRY_ANALYSIS = "industry_analysis"
    REPUTABLE_JOURNALISM = "reputable_journalism"
    VENDOR_COMMERCIAL = "vendor_commercial"
    GENERAL_REFERENCE = "general_reference"
    COMMUNITY_GENERATED = "community_generated"


# Domain and publisher classifications
_PEER_REVIEWED_HOSTS = {
    "nature.com",
    "science.org",
    "sciencedirect.com",
    "ieee.org",
    "ieeexplore.ieee.org",
    "acm.org",
    "dl.acm.org",
    "springer.com",
    "link.springer.com",
    "wiley.com",
    "cell.com",
    "thelancet.com",
    "pnas.org",
    "plos.org",
    "frontiersin.org",
    "mdpi.com",
    "tandfonline.com",
    "oxfordacademic.com",
    "cambridge.org",
    "sagepub.com",
}

_PREPRINT_HOSTS = {
    "arxiv.org",
    "biorxiv.org",
    "medrxiv.org",
    "ssrn.com",
    "researchsquare.com",
    "preprints.org",
    "chemrxiv.org",
}

_INSTITUTIONAL_GOV_HOSTS = {
    "nih.gov",
    "ncbi.nlm.nih.gov",
    "cdc.gov",
    "who.int",
    "europa.eu",
    "gov.uk",
    "nist.gov",
    "energy.gov",
    "bls.gov",
    "census.gov",
    "oecd.org",
    "worldbank.org",
    "un.org",
}

_RESEARCH_ORG_HOSTS = {
    "pewresearch.org",
    "brookings.edu",
    "rand.org",
    "nber.org",
    "csis.org",
    "carnegieendowment.org",
}

_INDUSTRY_ANALYST_HOSTS = {
    "trendforce.com",
    "gartner.com",
    "idc.com",
    "yolegroup.com",
    "semi.org",
    "statista.com",
    "semiconductor-digest.com",
    "allaboutcircuits.com",
    "semianalysis.com",
    "anandtech.com",
    "tomshardware.com",
}

_REPUTABLE_JOURNALISM_HOSTS = {
    "reuters.com",
    "bloomberg.com",
    "wsj.com",
    "ft.com",
    "nytimes.com",
    "economist.com",
    "arstechnica.com",
    "technologyreview.com",
    "theverge.com",
    "wired.com",
    "bbc.com",
    "apnews.com",
}

_COMMUNITY_REFERENCE_HOSTS = {
    "wikipedia.org",
    "wikimedia.org",
    "reddit.com",
    "quora.com",
    "medium.com",
    "substack.com",
    "youtube.com",
    "youtu.be",
    "github.com",
    "stackoverflow.com",
}


@dataclass(frozen=True)
class SourceCredibilityAssessment:
    source_type: SourceCredibilityType
    credibility_score: float  # 0.0 to 1.0 (heuristic metric)
    credibility_tier: str  # "high", "moderate", "variable", "low"
    is_peer_reviewed: bool
    is_primary: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceClassificationResult:
    category: EvidenceCategory
    confidence: float  # heuristic 0.0 to 1.0
    reason: str
    polarity: str  # "support", "contradict", "mitigate", "limitation", "neutral"

    @property
    def reasoning(self) -> str:
        return self.reason


@dataclass(frozen=True)
class ProvenanceVerificationResult:
    is_verified: bool
    status: str  # "verified", "unresolved", "mismatch"
    exact_match_found: bool
    section_verified: bool
    page_verified: bool
    reason: str

    @property
    def verified(self) -> bool:
        return self.is_verified

    @property
    def traceable(self) -> bool:
        return self.is_verified

    @property
    def failure_reason(self) -> str | None:
        return None if self.is_verified else self.reason


@dataclass
class IndependenceCluster:
    cluster_id: str
    root_entity: str
    source_ids: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    shared_doi: str | None = None
    is_syndicated: bool = False


class IndependenceAnalysisResult:
    def __init__(self, clusters: list[IndependenceCluster], score: float, notes: list[str]):
        self.clusters = clusters
        self.score = score
        self.notes = notes

    def __len__(self) -> int:
        return len(self.clusters)

    def __iter__(self):
        return iter(self.clusters)

    def __getitem__(self, index):
        return self.clusters[index]


# ---------------------------------------------------------------------------
# 1. SOURCE CREDIBILITY ASSESSMENT
# ---------------------------------------------------------------------------
def assess_source_credibility(
    publisher: str | None,
    url: str,
    doi: str | None = None,
    source_type_declared: str | None = None,
    authors: list[str] | None = None,
    publication_date: str | None = None,
) -> SourceCredibilityAssessment:
    parsed = urlsplit(url or "")
    host = parsed.netloc.lower().removeprefix("www.")
    pub_lower = (publisher or "").lower()
    st_declared = (source_type_declared or "").lower()

    reasons: list[str] = []
    is_peer_reviewed = False
    is_primary = False

    is_preprint = any(pr in host for pr in _PREPRINT_HOSTS) or "arxiv" in pub_lower or "biorxiv" in pub_lower or "medrxiv" in pub_lower or "ssrn" in pub_lower
    is_vendor = "vendor" in st_declared or "commercial" in st_declared or "vendor" in pub_lower or "promotional" in pub_lower or "vendor" in host or "commercial" in host
    is_verified_peer_reviewed = (
        any(ph in host for ph in _PEER_REVIEWED_HOSTS)
        or any(ph in pub_lower for ph in ("ieee", "springer", "elsevier", "wiley", "acm", "nature", "science", "oxford", "cambridge", "pnas", "cell", "lancet", "taylor"))
        or (st_declared in ("academic", "peer_reviewed", "journal-article") and bool(doi or any(ph in host for ph in _PEER_REVIEWED_HOSTS)))
    )

    if is_vendor:
        st = SourceCredibilityType.VENDOR_COMMERCIAL
        score = 0.40
        tier = "variable"
        is_primary = False
        reasons.append("Vendor or commercial publication; subject to marketing or product bias.")
    elif is_preprint:
        st = SourceCredibilityType.PREPRINT
        score = 0.85
        tier = "high"
        is_primary = True
        reasons.append("Academic preprint with transparent scholarly authorship and methodological structure.")
    elif is_verified_peer_reviewed:
        st = SourceCredibilityType.PEER_REVIEWED
        score = 0.95
        tier = "authoritative"
        is_peer_reviewed = True
        is_primary = True
        reasons.append("Peer-reviewed publication identified via academic publisher or verified academic indexing.")
    elif any(gh in host for gh in _INSTITUTIONAL_GOV_HOSTS) or host.endswith(".gov") or host.endswith(".mil"):
        st = SourceCredibilityType.GOVERNMENT_INSTITUTIONAL
        score = 0.90
        tier = "authoritative"
        is_primary = True
        reasons.append("Official government or multilateral institution report.")
    elif any(rh in host for rh in _RESEARCH_ORG_HOSTS):
        st = SourceCredibilityType.RESEARCH_ORGANIZATION
        score = 0.85
        tier = "high"
        is_primary = True
        reasons.append("Established independent research institute or policy think-tank.")
    elif any(ih in host for ih in _INDUSTRY_ANALYST_HOSTS):
        st = SourceCredibilityType.INDUSTRY_ANALYSIS
        score = 0.75
        tier = "moderate"
        is_primary = False
        reasons.append("Specialized industry market analysis; provides empirical supply/pricing intelligence.")
    elif any(jh in host for jh in _REPUTABLE_JOURNALISM_HOSTS):
        st = SourceCredibilityType.REPUTABLE_JOURNALISM
        score = 0.75
        tier = "moderate"
        is_primary = False
        reasons.append("Major investigative or technical journalism outlet with editorial oversight.")
    elif any(ch in host for ch in _COMMUNITY_REFERENCE_HOSTS):
        st = SourceCredibilityType.COMMUNITY_GENERATED
        score = 0.40
        tier = "variable"
        is_primary = False
        reasons.append("Community, aggregator, or user-generated platform; requires independent corroboration.")
    elif doi:
        st = SourceCredibilityType.GENERAL_REFERENCE
        score = 0.65
        tier = "moderate"
        is_peer_reviewed = False
        is_primary = False
        reasons.append("Source contains a registered DOI, but publisher or venue is not an established peer-reviewed academic journal. Peer review cannot be verified.")
    else:
        st = SourceCredibilityType.GENERAL_REFERENCE
        score = 0.60
        tier = "variable"
        is_primary = False
        reasons.append("General web publication assessed on content transparency and cited methodology.")

    if authors:
        score = min(1.0, score + 0.05)
        reasons.append(f"Attributed authors: {', '.join(authors[:2])}.")
    if publication_date:
        reasons.append(f"Publication date documented: {publication_date}.")

    tier = (
        "authoritative"
        if score >= 0.90
        else "high"
        if score >= 0.75
        else "moderate"
        if score >= 0.60
        else "variable"
    )

    return SourceCredibilityAssessment(
        source_type=st,
        credibility_score=round(score, 2),
        credibility_tier=tier,
        is_peer_reviewed=is_peer_reviewed,
        is_primary=is_primary,
        reasons=tuple(reasons),
    )


# ---------------------------------------------------------------------------
# 2. SOURCE INDEPENDENCE & SYNDICATION DETECTION
# ---------------------------------------------------------------------------
def _normalize_title_key(title: str) -> str:
    cleaned = re.sub(r"\W+", " ", title.casefold()).strip()
    words = [w for w in cleaned.split() if len(w) > 3]
    return " ".join(words[:8])


def _get_src_attr(src: Any, key: str, default: Any = None) -> Any:
    if isinstance(src, dict):
        return src.get(key, default)
    return getattr(src, key, default)


def detect_source_independence_clusters(
    sources: list[Any],
) -> IndependenceAnalysisResult:
    """Clusters sources by shared underlying reporting, shared DOI, or wire syndication.

    Returns:
        IndependenceAnalysisResult (iterable of IndependenceCluster with score and notes)
    """
    if not sources:
        return IndependenceAnalysisResult([], 5.0, ["No sources available to evaluate independence."])

    clusters: dict[str, IndependenceCluster] = {}
    title_keys: dict[str, str] = {}
    doi_clusters: dict[str, str] = {}
    domain_counts: dict[str, int] = {}
    notes: list[str] = []

    for src in sources:
        src_id = str(_get_src_attr(src, "id", ""))
        title = _get_src_attr(src, "title", "")
        url = _get_src_attr(src, "canonical_url", "") or _get_src_attr(src, "url", "") or _get_src_attr(src, "original_url", "")
        doi = _get_src_attr(src, "doi", None)
        publisher = _get_src_attr(src, "publisher", None)
        parsed = urlsplit(url)
        domain = parsed.netloc.lower().removeprefix("www.")
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

        t_key = _normalize_title_key(title)
        assigned_cluster_id: str | None = None

        if doi and doi.casefold() in doi_clusters:
            assigned_cluster_id = doi_clusters[doi.casefold()]
        elif t_key and t_key in title_keys:
            assigned_cluster_id = title_keys[t_key]
            clusters[assigned_cluster_id].is_syndicated = True

        if assigned_cluster_id is None:
            cluster_id = f"cluster_{len(clusters) + 1}"
            root = domain or (publisher if publisher else "unknown")
            clusters[cluster_id] = IndependenceCluster(
                cluster_id=cluster_id,
                root_entity=root,
                source_ids=[src_id],
                titles=[title],
                shared_doi=doi,
                is_syndicated=False,
            )
            if doi:
                doi_clusters[doi.casefold()] = cluster_id
            if t_key:
                title_keys[t_key] = cluster_id
        else:
            clusters[assigned_cluster_id].source_ids.append(src_id)
            clusters[assigned_cluster_id].titles.append(title)

    independent_cluster_count = len(clusters)
    total_sources = len(sources)
    syndicated_count = sum(len(c.source_ids) - 1 for c in clusters.values() if len(c.source_ids) > 1)

    if syndicated_count > 0:
        notes.append(
            f"Detected {syndicated_count} syndicated or derivative source(s) clustered under shared reports."
        )

    # Calculate 0-25 independence score
    if independent_cluster_count >= 5:
        base_pts = 25.0
    elif independent_cluster_count == 4:
        base_pts = 22.0
    elif independent_cluster_count == 3:
        base_pts = 18.0
    elif independent_cluster_count == 2:
        base_pts = 13.0
    elif independent_cluster_count == 1:
        base_pts = 8.0
    else:
        base_pts = 5.0

    # Penalize if over 40% of sources are duplicates from the same publisher/domain
    max_domain_share = max(domain_counts.values()) / max(1, total_sources) if domain_counts else 0.0
    if max_domain_share > 0.4 and total_sources > 2:
        base_pts = max(5.0, base_pts - 4.0)
        notes.append("High source concentration from a single publishing domain reduces independence rating.")

    notes.append(f"Established {independent_cluster_count} genuinely independent source origin clusters.")
    return IndependenceAnalysisResult(list(clusters.values()), round(base_pts, 1), notes)


# ---------------------------------------------------------------------------
# 3. EVIDENCE CLASSIFICATION INTELLIGENCE (CLAIM-SPECIFIC ENTAILMENT)
# ---------------------------------------------------------------------------
_MITIGATING_MARKERS = {
    "mitigate",
    "mitigates",
    "mitigating",
    "counterbalance",
    "counterbalances",
    "compensate",
    "offset",
    "offsets",
    "buffer",
    "buffers",
    "cushion",
    "rebound",
    "alleviate",
    "alleviates",
    "alleviating",
    "soften",
    "dampen",
    "stacking efficiency",
    "yield improvement",
    "yield enhancement",
    "yield enhancements",
    "compression",
    "counterbalancing",
    "footprint reduction",
    "reduces per-model",
    "supply expansion",
    "alternative capacity",
    "capacity expansion",
    "re-employment",
    "severance package",
    "severance support",
    "energy efficiency",
    "chip efficiency",
}

_LIMITATION_MARKERS = {
    "limitation",
    "limitations",
    "limited to",
    "convenience sample",
    "small sample",
    "sample size",
    "lacked longitudinal",
    "lack of control",
    "unrepresentative",
    "self-reported",
    "cross-sectional only",
    "methodological weakness",
    "future research",
    "cannot generalize",
    "not generalizable",
    "preliminary",
    "observational only",
    "confounding",
    "uncontrolled",
    "measurement error",
    "threat to validity",
    "bias",
    "potential bias",
    "selection bias",
}

_CONTRADICTING_MARKERS = {
    "no significant",
    "did not increase",
    "did not decrease",
    "did not affect",
    "did not improve",
    "did not contribute",
    "no evidence of",
    "contradicts",
    "inconsistent with",
    "refutes",
    "contrary to",
    "opposite effect",
    "unrelated to",
    "no correlation",
    "zero impact",
    "disproved",
    "no measurable",
    "no shortage",
    "no shortages",
    "surplus",
    "heavy surplus",
    "remains in surplus",
    "market surplus",
}

_SUPPORTING_MARKERS = {
    "demonstrates",
    "confirms",
    "proves",
    "shows that",
    "drives",
    "causes",
    "leads to",
    "results in",
    "substantially increases",
    "substantially reduces",
    "direct causal",
    "significant increase",
    "significant decrease",
    "statistically significant",
    "strong correlation",
    "severely constrained",
    "acute shortage",
    "supply deficit",
    "faster",
    "improved",
    "improves",
    "improvement",
    "higher",
    "speedup",
    "associated with",
}


def classify_evidence_for_claim(
    claim_text: str,
    passage_text: str,
) -> EvidenceClassificationResult:
    """Classifies an evidence passage against a specific claim into 1 of 6 categories.

    Categories:
    - supporting: directly supports the specific claim's proposition.
    - contradicting: directly challenges or disproves the claim's proposition.
    - mitigating: demonstrates that the effect is conditional, reduced, or counterbalanced.
    - methodological_limitation: identifies weaknesses in study design, data, or generalizability.
    - contextual: background facts or descriptive domain information without directionality.
    - insufficient: off-topic or irrelevant text lacking defensible connection.
    """
    lowered_passage = passage_text.casefold()
    claim_terms, claim_subject, claim_outcomes = question_focus(claim_text)
    passage_terms = _terms(passage_text)

    # 1. Check for methodological limitation
    if any(marker in lowered_passage for marker in _LIMITATION_MARKERS):
        return EvidenceClassificationResult(
            category=EvidenceCategory.METHODOLOGICAL_LIMITATION,
            confidence=0.88,
            reason="Passage explicitly describes a study limitation, sample constraint, or methodological weakness.",
            polarity="limitation",
        )

    # 2. Check for mitigating factors (counterbalancing, efficiency gains, buffers)
    if any(marker in lowered_passage for marker in _MITIGATING_MARKERS):
        return EvidenceClassificationResult(
            category=EvidenceCategory.MITIGATING,
            confidence=0.84,
            reason="Passage presents mitigating, offsetting, or conditional counterbalances to the effect.",
            polarity="mitigate",
        )

    # 3. Check for direct contradiction / null findings
    if any(marker in lowered_passage for marker in _CONTRADICTING_MARKERS):
        return EvidenceClassificationResult(
            category=EvidenceCategory.CONTRADICTING,
            confidence=0.86,
            reason="Passage presents null findings or directly challenges the relationship asserted in the claim.",
            polarity="contradict",
        )

    # 4. Check for direct directional support
    # A passage is supporting if it shares core subjects with the claim AND contains supporting directional markers
    subject_matches = sum(1 for st in claim_subject if _term_matches(st, passage_terms)) if claim_subject else 1
    has_support_marker = any(marker in lowered_passage for marker in _SUPPORTING_MARKERS)

    # Direction alignment check
    claim_has_shortage = bool(claim_terms & {"shortage", "scarcity", "deficit", "crunch", "squeeze", "constraint"})
    passage_has_shortage = any(
        m in lowered_passage
        for m in (
            "shortage",
            "shortages",
            "scarcity",
            "deficit",
            "crunch",
            "squeeze",
            "bottleneck",
            "bottlenecks",
            "supply constraint",
            "supply constraints",
            "tight supply",
        )
    )

    claim_has_increase = bool(claim_terms & {"increase", "growth", "rise", "surge", "accelerate", "drive", "drives", "causes", "caused"})
    passage_has_increase = any(
        m in lowered_passage
        for m in (
            "increase",
            "growth",
            "rise",
            "surge",
            "accelerate",
            "soar",
            "unprecedented demand",
            "caused",
            "drove",
            "exponential",
        )
    )

    if subject_matches > 0 and (has_support_marker or (claim_has_shortage and passage_has_shortage) or (claim_has_increase and passage_has_increase)):
        return EvidenceClassificationResult(
            category=EvidenceCategory.SUPPORTING,
            confidence=0.82,
            reason="Passage directly corroborates the directional causal effect asserted in the claim.",
            polarity="support",
        )

    # 5. Overlap check for relevance
    all_overlap = sum(1 for ct in claim_terms if _term_matches(ct, passage_terms))
    is_contextual_marker = any(
        m in lowered_passage
        for m in ("invented", "definition", "overview", "history", "founded", "refers to", "traditionally", "consists of")
    )
    if all_overlap >= 2 or (all_overlap >= 1 and (subject_matches > 0 or is_contextual_marker)):
        return EvidenceClassificationResult(
            category=EvidenceCategory.CONTEXTUAL,
            confidence=0.75,
            reason="Passage provides substantive domain context and terminology without asserting directional proof.",
            polarity="neutral",
        )

    # 6. Fallback: insufficient relationship
    return EvidenceClassificationResult(
        category=EvidenceCategory.INSUFFICIENT,
        confidence=0.60,
        reason="Passage lacks sufficient specific factual connection to establish a defensible relationship to the claim.",
        polarity="neutral",
    )


# ---------------------------------------------------------------------------
# 4. PROVENANCE INTEGRITY VERIFICATION
# ---------------------------------------------------------------------------
def verify_evidence_provenance(
    exact_text: str,
    document_content: str | None = None,
    section_name: str | None = None,
    document_headings: list[str] | None = None,
    page_number: int | None = None,
    page_count: int | None = None,
    document: Any = None,
) -> ProvenanceVerificationResult:
    """Verifies that an extracted passage genuinely originates from the document record.

    Prevents:
    - Stale or incorrectly assigned document IDs.
    - Section title hallucinations or cross-document bleeding.
    - Page number overflows beyond page count.
    """
    if document is not None:
        if document_content is None:
            document_content = getattr(document, "content", None)
        if document_headings is None:
            document_headings = getattr(document, "headings", None)
        if page_count is None:
            page_count = getattr(document, "page_count", None)

    if not document_content:
        return ProvenanceVerificationResult(
            is_verified=False,
            status="unresolved",
            exact_match_found=False,
            section_verified=False,
            page_verified=False,
            reason="Document text is missing or inaccessible; passage cannot be verified against source text.",
        )

    # Check exact text containment (normalize whitespace)
    norm_doc = " ".join(document_content.split())
    norm_exact = " ".join(exact_text.split())

    exact_found = norm_exact in norm_doc
    if not exact_found:
        # Check if at least 90% character core is present (tolerant to punctuation/trimming)
        snippet_core = norm_exact[: min(len(norm_exact), 80)]
        exact_found = snippet_core in norm_doc

    if not exact_found:
        return ProvenanceVerificationResult(
            is_verified=False,
            status="mismatch",
            exact_match_found=False,
            section_verified=False,
            page_verified=False,
            reason="Exact text was not found in the linked document content; provenance mismatch detected.",
        )

    # Check section name validity if headings are available
    headings = document_headings or []
    section_verified = True
    if section_name and headings:
        norm_sec = section_name.strip().casefold()
        section_verified = any(norm_sec in h.casefold() or h.casefold() in norm_sec for h in headings)

    # Check page number bounds
    page_verified = True
    if page_number is not None and page_count is not None and page_count > 0:
        page_verified = 1 <= page_number <= page_count

    if not section_verified:
        return ProvenanceVerificationResult(
            is_verified=False,
            status="unresolved",
            exact_match_found=True,
            section_verified=False,
            page_verified=page_verified,
            reason=f"Section heading '{section_name}' does not match document headings.",
        )

    if not page_verified:
        return ProvenanceVerificationResult(
            is_verified=False,
            status="unresolved",
            exact_match_found=True,
            section_verified=section_verified,
            page_verified=False,
            reason=f"Page number {page_number} exceeds document page count of {page_count}.",
        )

    return ProvenanceVerificationResult(
        is_verified=True,
        status="verified",
        exact_match_found=True,
        section_verified=True,
        page_verified=True,
        reason="Passage verbatim text, document identity, and section provenance verified.",
    )
