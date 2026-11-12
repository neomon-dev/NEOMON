import re
from dataclasses import dataclass

from app.research.providers import SearchResult

_STOPWORDS = {
    "about",
    "after",
    "against",
    "among",
    "and",
    "are",
    "does",
    "effect",
    "effects",
    "for",
    "from",
    "how",
    "into",
    "that",
    "the",
    "their",
    "these",
    "this",
    "what",
    "with",
}
_OUTCOME_TERMS = {
    "effect",
    "effects",
    "impact",
    "impacts",
    "influence",
    "productivity",
    "quality",
    "rate",
    "rates",
    "time",
    "outcome",
    "outcomes",
    "relationship",
}
_PUBLICATION_TERMS = {
    "study",
    "experiment",
    "evaluation",
    "review",
    "analysis",
    "evidence",
    "trial",
    "research",
}
_GENERIC_DOMAIN_TERMS = {"artificial", "intelligence", "ai"}


@dataclass(frozen=True)
class RelevanceAssessment:
    score: float
    status: str
    reasons: tuple[str, ...]


def _terms(text: str) -> set[str]:
    return {
        term[:-1] if term.endswith("s") and len(term) > 4 else term
        for term in re.findall(r"[a-z0-9]{3,}", text.casefold())
        if term not in _STOPWORDS
    }


def question_focus(question: str) -> tuple[set[str], set[str], set[str]]:
    terms = _terms(question)
    subject = terms - _OUTCOME_TERMS
    if subject - _GENERIC_DOMAIN_TERMS:
        subject -= _GENERIC_DOMAIN_TERMS
    outcomes = terms & _OUTCOME_TERMS
    return terms, subject, outcomes


def assess_result(question: str, result: SearchResult, timeframe: str | None = None) -> RelevanceAssessment:
    question_terms, subject_terms, outcome_terms = question_focus(question)
    result_terms = _terms(f"{result.title} {result.snippet}")
    direct = len(question_terms & result_terms) / max(1, len(question_terms))
    subject = len(subject_terms & result_terms) / max(1, len(subject_terms))
    outcomes = len(outcome_terms & result_terms) / max(1, len(outcome_terms))
    score = 0.45 * direct + 0.35 * subject + 0.15 * outcomes
    reasons: list[str] = []

    if subject >= 0.5:
        reasons.append("result addresses the question's subject")
    elif subject:
        reasons.append("result partially matches the question's subject")
    else:
        reasons.append("result does not identify the question's subject")
    if outcomes >= 0.5:
        reasons.append("result discusses the requested outcome or relationship")
    elif outcomes:
        reasons.append("result has limited outcome coverage")
    else:
        reasons.append("result does not expose the requested outcome in searchable text")
    if result.source_type in {"academic", "institutional"}:
        score += 0.05
        reasons.append(f"source is classified as {result.source_type}")
    if result.snippet.strip():
        score += 0.05
        reasons.append("abstract or result summary is available")
    if timeframe and any(part in (result.publication_date or "") for part in re.findall(r"\d{4}", timeframe)):
        score += 0.05
        reasons.append("publication date matches the requested timeframe")
    score = round(min(1.0, score), 3)
    status = "relevant" if score >= 0.42 and subject >= 0.25 and outcomes >= 0.25 else "low_relevance"
    if score < 0.28 or subject == 0:
        status = "rejected"
    reasons.append(f"transparent relevance score {score:.3f}; not a truth or credibility probability")
    return RelevanceAssessment(score, status, tuple(reasons))


def assess_text(question: str, text: str) -> RelevanceAssessment:
    return assess_result(question, SearchResult(title="", url="", snippet=text))


def classify_evidence(text: str) -> tuple[str, str]:
    lowered = text.casefold()
    if any(term in lowered for term in ("limitation", "limitations", "small sample", "future research", "cannot generalize")):
        return "methodological_limitation", "Passage explicitly describes a study limitation or generalizability constraint."
    if any(term in lowered for term in ("no significant", "did not improve", "did not increase", "worsened", "lower than")):
        return "contradicting", "Passage contains a negative or null finding relevant to the claim."
    if any(term in lowered for term in ("improved", "increased", "reduced", "faster", "higher", "associated with")):
        return "supporting", "Passage reports an outcome direction relevant to the claim."
    return "contextual", "Passage provides relevant context without an explicit directional finding."
