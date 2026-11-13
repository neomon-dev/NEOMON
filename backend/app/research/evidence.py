import re
from dataclasses import dataclass

from app.research.relevance import _terms, assess_text, classify_evidence, question_focus


@dataclass
class ExtractedEvidence:
    exact_text: str
    surrounding_context: str
    evidence_type: str
    relevance_score: float
    relevance_reason: str
    page_number: int | None = None
    section_name: str | None = None
    extraction_method: str = "relevance_filtered_sentence_match"


def _sentences(content: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", content) if len(sentence.strip()) >= 40]


def _looks_like_boilerplate(sentence: str) -> bool:
    lowered = sentence.casefold()
    markers = (
        "submit your manuscript",
        "privacy policy",
        "cookie settings",
        "all rights reserved",
        "sign in",
        "subscribe",
        "follow us",
        "browse journals",
        "advertisement",
        "copyright notice",
    )
    return any(marker in lowered for marker in markers)


def _has_outcome_signal(sentence: str) -> bool:
    terms = _terms(sentence)
    return bool(
        terms
        & {
            "improved",
            "improvement",
            "increased",
            "reduced",
            "faster",
            "slower",
            "higher",
            "lower",
            "quality",
            "defect",
            "time",
            "productivity",
            "significant",
            "positive",
            "negative",
            "benefit",
            "risk",
            "effect",
            "impact",
        }
    )


def extract_evidence(
    content: str,
    claim: str,
    limit: int = 5,
    passages: list[tuple[int | None, str, str | None]] | None = None,
) -> list[ExtractedEvidence]:
    _, subject_terms, outcome_terms = question_focus(claim)
    source_passages = passages or [(None, content, None)]
    evidence: list[ExtractedEvidence] = []
    for page_number, passage, section_name in source_passages:
        sentences = _sentences(passage)
        for index, sentence in enumerate(sentences):
            if _looks_like_boilerplate(sentence):
                continue
            assessment = assess_text(claim, sentence)
            sentence_terms = _terms(sentence)
            subject_overlap = len(subject_terms & sentence_terms)
            outcome_overlap = len(outcome_terms & sentence_terms)
            evidence_type, classification_reason = classify_evidence(sentence, claim=claim)
            if (
                (assessment.score < 0.2 and evidence_type not in {"methodological_limitation", "contradicting", "mitigating"})
                or (subject_terms and subject_overlap == 0 and evidence_type not in {"methodological_limitation", "contradicting", "mitigating"})
                or (outcome_terms and outcome_overlap == 0 and not _has_outcome_signal(sentence) and evidence_type not in {"methodological_limitation", "contradicting", "mitigating"})
            ):
                continue
            context = " ".join(sentences[max(0, index - 1): min(len(sentences), index + 2)])
            evidence.append(
                ExtractedEvidence(
                    exact_text=sentence,
                    surrounding_context=context,
                    evidence_type=evidence_type,
                    relevance_score=assessment.score,
                    relevance_reason=f"{classification_reason} {'; '.join(assessment.reasons)}",
                    page_number=page_number,
                    section_name=section_name,
                )
            )
    unique: dict[str, ExtractedEvidence] = {}
    for item in evidence:
        # Deduplicate identical sentences to avoid artificial inflation, preserving earliest genuine section
        if item.exact_text not in unique:
            unique[item.exact_text] = item
    return sorted(unique.values(), key=lambda item: item.relevance_score, reverse=True)[:limit]

