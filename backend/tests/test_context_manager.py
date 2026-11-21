import uuid
import pytest
from app.analysis.context_manager import (
    AGENT_BUDGETS,
    DEFAULT_BUDGET,
    compact_evidence_text,
    deduplicate_evidence,
    estimate_tokens,
    select_evidence_for_role,
)
from app.models import Evidence


def _make_evidence(text: str, ev_type: str = "supporting", relevance: float = 0.8) -> Evidence:
    item = Evidence()
    item.id = uuid.uuid4()
    item.source_id = uuid.uuid4()
    item.exact_text = text
    item.evidence_type = ev_type
    item.relevance_score = relevance
    return item


def test_token_estimation():
    assert estimate_tokens("") == 0
    assert estimate_tokens("hello world") == 2
    long_text = "This is a detailed scientific passage describing green hydrogen production efficiency."
    tokens = estimate_tokens(long_text)
    assert 10 <= tokens <= 30


def test_compact_evidence_text():
    short = "Short text."
    assert compact_evidence_text(short, max_length=100) == "Short text."

    long = "First sentence. Second sentence with important data. Third sentence that goes beyond the threshold."
    compacted = compact_evidence_text(long, max_length=40)
    assert len(compacted) <= 45
    assert compacted.endswith(".") or compacted.endswith("...")


def test_deduplicate_evidence():
    ev1 = _make_evidence("Identical passage text with details about hydrogen fuel cells.")
    ev2 = _make_evidence("Identical passage text with details about hydrogen fuel cells.")
    ev3 = _make_evidence("Completely different passage text with distinct content.")

    deduped = deduplicate_evidence([ev1, ev2, ev3])
    assert len(deduped) == 2
    assert deduped[0].id == ev1.id
    assert deduped[1].id == ev3.id


def test_advocate_evidence_selection_prioritizes_supporting():
    budget = AGENT_BUDGETS["advocate"]
    ev_sup1 = _make_evidence("High efficiency observed in polymer electrolyte membrane.", "supporting", 0.95)
    ev_sup2 = _make_evidence("Electrolyzer capital costs declined by 18 percent.", "supporting", 0.85)
    ev_con = _make_evidence("Levelized cost remains high without renewable subsidies.", "contradicting", 0.90)

    selected = select_evidence_for_role("advocate", [ev_con, ev_sup2, ev_sup1], budget)
    assert len(selected) <= budget.max_evidence_per_claim
    # Advocate should place supporting passages first
    assert selected[0].evidence_type == "supporting"
    assert selected[0].relevance_score == 0.95


def test_skeptic_evidence_selection_never_drops_contradicting():
    budget = AGENT_BUDGETS["skeptic"]
    ev_sup = _make_evidence("Support passage text.", "supporting", 0.9)
    ev_con = _make_evidence("Severe cost penalty under peak grid load.", "contradicting", 0.88)
    ev_lim = _make_evidence("Study cohort limited to pilot scale facilities.", "methodological_limitation", 0.75)

    selected = select_evidence_for_role("skeptic", [ev_sup, ev_con, ev_lim], budget)
    # Skeptic MUST select contradicting and limitation passages first
    types = [e.evidence_type for e in selected]
    assert "contradicting" in types
    assert "methodological_limitation" in types
    assert selected[0].evidence_type in {"contradicting", "methodological_limitation"}


def test_methodology_auditor_prioritizes_methods_and_sample_sizes():
    budget = AGENT_BUDGETS["methodology_auditor"]
    ev_generic = _make_evidence("Hydrogen is an energy carrier.", "contextual", 0.5)
    ev_method = _make_evidence("Randomized trial with n=450 cohort and double-blind protocol with p<0.01.", "supporting", 0.8)

    selected = select_evidence_for_role("methodology_auditor", [ev_generic, ev_method], budget)
    assert selected[0].id == ev_method.id
