"""Adaptive Research and Query Refinement Service (Milestone 9C).

Manages query history, detects near-duplicates, evaluates query effectiveness,
and adapts search formulations to maximize information gain while avoiding repetitive loops:
- Provider-tailored formatting (academic literature vs web)
- Deliberate counter-evidence and limitation queries
- Terminology specialization and scope expansion/narrowing
"""

from dataclasses import dataclass, field
import re
from typing import Any


@dataclass
class QueryEffectivenessRecord:
    query_text: str
    provider: str
    results_count: int
    relevant_count: int
    effectiveness_score: float  # 0.0 to 1.0
    is_counter_evidence: bool = False


def _clean_query_tokens(text: str) -> set[str]:
    clean = re.sub(r"[^\w\s]", " ", (text or "").lower())
    stop = {"a", "an", "the", "and", "or", "of", "to", "in", "for", "on", "with", "at", "by", "from", "what", "how", "why"}
    return {t for t in clean.split() if len(t) > 2 and t not in stop}


def is_near_duplicate_query(candidate: str, existing_queries: list[str], threshold: float = 0.75) -> bool:
    """Check if candidate query is substantially similar to an already executed query."""
    cand_tokens = _clean_query_tokens(candidate)
    if not cand_tokens:
        return True

    for eq in existing_queries:
        eq_tokens = _clean_query_tokens(eq)
        if not eq_tokens:
            continue
        overlap = cand_tokens & eq_tokens
        sim = len(overlap) / len(cand_tokens | eq_tokens)
        if sim >= threshold:
            return True
    return False


def refine_query_for_counter_evidence(base_query: str) -> str:
    """Transform a query into a deliberate counter-evidence search."""
    clean = base_query.strip().removesuffix("?").removesuffix(".")
    counter_prefixes = [
        "limitations of",
        "counter-evidence for",
        "confounding factors in",
        "refutation of",
        "empirical failure cases in",
    ]
    # Pick prefix deterministically based on hash of query length
    chosen_prefix = counter_prefixes[len(clean) % len(counter_prefixes)]
    return f"{chosen_prefix} {clean}"


def adapt_query_for_provider(query: str, provider: str) -> str:
    """Adapt query syntax and focus to specific research providers."""
    p_lower = provider.lower()
    clean = query.strip().removesuffix("?")

    if "arxiv" in p_lower:
        # arXiv works best with concise technical keywords
        tokens = [t for t in clean.split() if len(t) > 2][:6]
        return " ".join(tokens)
    elif "crossref" in p_lower or "openalex" in p_lower:
        # Crossref/OpenAlex benefit from scholarly and methodological framing
        if not any(kw in clean.lower() for kw in ("empirical", "study", "analysis", "review", "evaluation")):
            return f"{clean} empirical study"
        return clean
    elif "tavily" in p_lower:
        # Tavily benefits from natural language semantic research questions
        return clean

    return clean


def generate_adaptive_query_variants(
    base_query: str,
    target_providers: list[str],
    executed_queries: list[str],
    last_cycle_results_count: int = 0,
    force_counter_evidence: bool = False,
) -> list[tuple[str, str, str]]:
    """Generate novel, non-duplicate query variants tailored for providers.
    
    Returns list of (query_text, target_provider, rationale).
    """
    variants: list[tuple[str, str, str]] = []
    past = executed_queries or []

    for provider in target_providers:
        # 1. Primary adapted query
        adapted = adapt_query_for_provider(base_query, provider)
        if not is_near_duplicate_query(adapted, past):
            variants.append((
                adapted,
                provider,
                f"Adapted for {provider} using technical vocabulary and scholarly indexing."
            ))
            past.append(adapted)

        # 2. Scope adaptation if previous cycle had 0 results (widen)
        if last_cycle_results_count == 0:
            tokens = [t for t in _clean_query_tokens(base_query)][:4]
            if tokens:
                broadened = f"{' '.join(tokens)} overview"
                if not is_near_duplicate_query(broadened, past):
                    variants.append((
                        broadened,
                        provider,
                        f"Broadened query for {provider} after previous cycle returned 0 results."
                    ))
                    past.append(broadened)

        # 3. Counter-evidence query
        if force_counter_evidence:
            counter_q = refine_query_for_counter_evidence(base_query)
            if not is_near_duplicate_query(counter_q, past):
                variants.append((
                    counter_q,
                    provider,
                    f"Targeted skeptic and counter-evidence search on {provider} to test claim robustness."
                ))
                past.append(counter_q)

    return variants
