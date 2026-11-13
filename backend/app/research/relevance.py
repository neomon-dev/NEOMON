import re
from dataclasses import dataclass

from app.research.providers import SearchResult

_STOPWORDS = {
    "a",
    "about",
    "above",
    "after",
    "again",
    "against",
    "all",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "doing",
    "down",
    "during",
    "each",
    "few",
    "for",
    "from",
    "further",
    "had",
    "has",
    "have",
    "having",
    "he",
    "her",
    "here",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "itself",
    "just",
    "me",
    "more",
    "most",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "same",
    "she",
    "should",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "until",
    "up",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "will",
    "with",
    "would",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
}

_PRESERVED_ACRONYMS = {
    "ai",
    "it",
    "ml",
    "vr",
    "ar",
    "ui",
    "ux",
    "os",
    "ip",
    "db",
    "qa",
    "ci",
    "cd",
    "hr",
    "pr",
    "llm",
    "nlp",
    "iot",
    "bi",
    "5g",
    "6g",
}

_OUTCOME_TERMS = {
    "affect",
    "effect",
    "impact",
    "influence",
    "consequence",
    "outcome",
    "result",
    "productivity",
    "performance",
    "quality",
    "rate",
    "time",
    "relationship",
    "association",
    "correlation",
    "difference",
    "benefit",
    "risk",
    "cost",
    "role",
    "change",
    "trend",
    "contribute",
    "contribution",
    "increase",
    "decrease",
    "growth",
    "rise",
    "fall",
    "drop",
    "shortage",
    "crisis",
    "scarcity",
    "demand",
    "supply",
    "price",
    "pricing",
    "cause",
    "lead",
    "drive",
    "trigger",
}

_OUTCOME_EQUIVALENCE: dict[str, set[str]] = {
    "affect": {"affect", "effect", "impact", "influence", "consequence", "outcome", "result", "role"},
    "effect": {"affect", "effect", "impact", "influence", "consequence", "outcome", "result", "role"},
    "impact": {"affect", "effect", "impact", "influence", "consequence", "outcome", "result", "role"},
    "influence": {"affect", "effect", "impact", "influence", "consequence", "outcome", "result", "role"},
    "consequence": {"affect", "effect", "impact", "influence", "consequence", "outcome", "result"},
    "outcome": {"affect", "effect", "impact", "influence", "consequence", "outcome", "result"},
    "result": {"affect", "effect", "impact", "influence", "consequence", "outcome", "result"},
    "benefit": {"benefit", "advantage", "gain", "value", "positive"},
    "risk": {"risk", "threat", "danger", "hazard", "negative", "drawback", "limitation"},
    "productivity": {"productivity", "performance", "efficiency", "output"},
    "performance": {"productivity", "performance", "efficiency", "quality"},
    "change": {"change", "shift", "transition", "alteration", "variation", "trend"},
    "contribute": {"contribute", "contribution", "cause", "lead", "drive", "trigger", "impact", "affect", "result", "role", "factor"},
    "shortage": {"shortage", "scarcity", "deficit", "crunch", "squeeze", "constraint", "bottleneck", "supply", "allocation"},
    "demand": {"demand", "consumption", "need", "requirement", "utilization", "usage", "appetite"},
    "supply": {"supply", "production", "capacity", "allocation", "inventory", "output"},
    "price": {"price", "pricing", "cost", "expense", "inflation", "rate"},
    "increase": {"increase", "growth", "rise", "surge", "accelerate", "expand", "soar", "gain"},
    "decrease": {"decrease", "decline", "drop", "reduction", "fall", "slowdown"},
}

_TERM_FAMILIES: dict[str, set[str]] = {
    "ram": {"ram", "dram", "hbm", "sram", "vram", "ddr", "ddr4", "ddr5", "memory", "semiconductor"},
    "dram": {"ram", "dram", "hbm", "sram", "vram", "ddr", "ddr4", "ddr5", "memory", "semiconductor"},
    "hbm": {"ram", "dram", "hbm", "sram", "vram", "ddr", "ddr4", "ddr5", "memory", "semiconductor"},
    "ddr5": {"ddr5", "ddr", "ram", "dram", "memory"},
    "electricity": {"electricity", "electric", "power", "grid", "energy", "watt", "kilowatt", "megawatt", "gigawatt", "terawatt", "consumption"},
    "energy": {"electricity", "electric", "power", "grid", "energy"},
    "it": {"it", "tech", "technology", "software", "computing", "computer", "enterprise"},
    "layoff": {"layoff", "layoffs", "downsizing", "severance", "job", "redundancy", "termination", "reduction"},
    "employee": {"employee", "employees", "worker", "workers", "workforce", "staff", "personnel", "talent", "labor"},
    "ai": {"ai", "artificial", "intelligence", "llm", "ml"},
    "ml": {"ml", "machine", "learning", "ai"},
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


def _normalize_term(term: str) -> str:
    if term.endswith("ies") and len(term) > 4:
        return term[:-3] + "y"
    if term.endswith("s") and len(term) > 3 and not term.endswith("ss"):
        return term[:-1]
    return term


def _terms(text: str) -> set[str]:
    raw_tokens = re.findall(r"\b[A-Za-z0-9]+\b", text)
    terms: set[str] = set()
    for token in raw_tokens:
        folded = token.casefold()
        if len(folded) < 2:
            continue
        if folded in _PRESERVED_ACRONYMS:
            terms.add(folded)
            continue
        if folded in _STOPWORDS:
            continue
        normalized = _normalize_term(folded)
        if normalized not in _STOPWORDS:
            terms.add(normalized)
    return terms


def _term_matches(term: str, target_terms: set[str]) -> bool:
    if term in target_terms:
        return True
    equiv = _OUTCOME_EQUIVALENCE.get(term)
    if equiv and bool(equiv & target_terms):
        return True
    family = _TERM_FAMILIES.get(term)
    if family and bool(family & target_terms):
        return True
    return False


def question_focus(question: str) -> tuple[set[str], set[str], set[str]]:
    terms = _terms(question)
    subject = terms - _OUTCOME_TERMS
    specific_subject = subject - _GENERIC_DOMAIN_TERMS
    if len(specific_subject) >= 2:
        subject = specific_subject
    outcomes = terms & _OUTCOME_TERMS
    return terms, subject, outcomes


def assess_result(question: str, result: SearchResult, timeframe: str | None = None) -> RelevanceAssessment:
    question_terms, subject_terms, outcome_terms = question_focus(question)
    title_terms = _terms(result.title)
    snippet_terms = _terms(result.snippet)
    result_terms = title_terms | snippet_terms

    # Direct match: question terms found in result
    matched_direct = sum(1 for qt in question_terms if _term_matches(qt, result_terms))
    direct = matched_direct / max(1, len(question_terms))

    matched_title = sum(1 for qt in question_terms if _term_matches(qt, title_terms))
    title_match = matched_title / max(1, len(question_terms))

    # Subject match
    matched_subjects = sum(1 for st in subject_terms if _term_matches(st, result_terms))
    subject = matched_subjects / max(1, len(subject_terms)) if subject_terms else 1.0

    # Strict domain isolation check:
    # If the question has specific non-generic subject terms (e.g. 'ram' in 'AI contribute to RAM shortages'),
    # at least one specific subject must match; otherwise this source is about another domain entirely.
    specific_subject_terms = subject_terms - _GENERIC_DOMAIN_TERMS
    if specific_subject_terms:
        specific_matches = sum(1 for st in specific_subject_terms if _term_matches(st, result_terms))
        if specific_matches == 0:
            subject = 0.0

    if outcome_terms:
        matched_outcomes = sum(1 for ot in outcome_terms if _term_matches(ot, result_terms))
        outcomes = matched_outcomes / len(outcome_terms)
    else:
        outcomes = 1.0

    q_norm = " ".join(re.findall(r"[a-z0-9]+", question.casefold()))
    t_norm = " ".join(re.findall(r"[a-z0-9]+", result.title.casefold()))
    is_exact_title = bool(q_norm and t_norm and (q_norm == t_norm or q_norm in t_norm or (t_norm in q_norm and len(t_norm) > 5)))

    if not outcome_terms:
        score = 0.50 * direct + 0.40 * subject + 0.10 * title_match
    else:
        score = 0.40 * direct + 0.35 * subject + 0.15 * outcomes + 0.10 * title_match

    if is_exact_title:
        score = max(score, 0.85)

    reasons: list[str] = []
    if is_exact_title:
        reasons.append("result title directly matches the research question")
    if subject >= 0.5:
        reasons.append("result addresses the question's subject")
    elif subject > 0:
        reasons.append("result partially matches the question's subject")
    else:
        reasons.append("result does not identify the question's subject")

    if outcome_terms:
        if outcomes >= 0.5:
            reasons.append("result discusses the requested outcome or relationship")
        elif outcomes > 0:
            reasons.append("result has limited outcome coverage")
        else:
            reasons.append("result does not expose the requested outcome in searchable text")
    else:
        reasons.append("conceptual or definitional inquiry; evaluated on subject coverage")

    if subject == 0:
        score = min(score, 0.15)

    if result.source_type in {"academic", "institutional"}:
        score += 0.05
        reasons.append(f"source is classified as {result.source_type}")
    if result.snippet.strip():
        score += 0.05
        reasons.append("abstract or result summary is available")
    else:
        reasons.append("abstract is unavailable; assessed on title metadata only")
    if timeframe and any(part in (result.publication_date or "") for part in re.findall(r"\d{4}", timeframe)):
        score += 0.05
        reasons.append("publication date matches the requested timeframe")

    if subject == 0:
        score = min(score, 0.20)

    score = round(min(1.0, score), 3)

    if not outcome_terms:
        status = "relevant" if score >= 0.40 and subject >= 0.30 else "low_relevance"
    else:
        status = "relevant" if score >= 0.40 and subject >= 0.25 and (outcomes >= 0.25 or direct >= 0.60 or is_exact_title) else "low_relevance"

    if score < 0.28 or subject == 0:
        status = "rejected"

    reasons.append(f"transparent relevance score {score:.3f}; not a truth or credibility probability")
    return RelevanceAssessment(score, status, tuple(reasons))


def assess_text(question: str, text: str) -> RelevanceAssessment:
    return assess_result(question, SearchResult(title="", url="", snippet=text))


def classify_evidence(text: str, claim: str | None = None) -> tuple[str, str]:
    if claim:
        from app.research.scientific_integrity import classify_evidence_for_claim
        result = classify_evidence_for_claim(claim, text)
        return result.category.value, result.reason

    lowered = text.casefold()
    if any(term in lowered for term in ("limitation", "limitations", "small sample", "future research", "cannot generalize", "potential bias")):
        return "methodological_limitation", "Passage explicitly describes a study limitation or generalizability constraint."
    if any(term in lowered for term in ("mitigate", "mitigating", "counterbalance", "offset", "buffer", "efficiency gain")):
        return "mitigating", "Passage presents mitigating, offsetting, or conditional counterbalances to the effect."
    if any(term in lowered for term in ("no significant", "did not improve", "did not increase", "worsened", "lower than", "inconsistent with")):
        return "contradicting", "Passage contains a negative, null, or contrary finding."
    if any(term in lowered for term in ("improved", "increased", "reduced", "faster", "higher", "associated with", "drives", "causes")):
        return "supporting", "Passage reports an outcome direction relevant to the claim."
    if len(text.strip()) < 30:
        return "insufficient", "Passage lacks sufficient specific factual text."
    return "contextual", "Passage provides relevant context without an explicit directional finding."

