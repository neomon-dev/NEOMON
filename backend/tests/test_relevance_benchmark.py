import pytest

from app.research.providers import SearchResult
from app.research.relevance import assess_result, question_focus


def test_benchmark_what_is_ai():
    question = "What is AI?"
    terms, subject, outcomes = question_focus(question)
    assert "ai" in terms
    assert "ai" in subject
    assert len(outcomes) == 0

    # Exact title match
    exact = SearchResult(
        title="What Is AI?",
        url="https://example.org/what-is-ai",
        snippet="An introduction to artificial intelligence foundations, definitions, and capabilities.",
        source_type="academic",
    )
    exact_res = assess_result(question, exact)
    assert exact_res.score >= 0.85
    assert exact_res.status == "relevant"
    assert any("title directly matches" in r for r in exact_res.reasons)

    # Relevant variant
    variant = SearchResult(
        title="Understanding AI: Historical Perspectives and Definitions",
        url="https://example.org/ai-history",
        snippet="This paper reviews the historical definitions of artificial intelligence and its core subfields.",
        source_type="academic",
    )
    var_res = assess_result(question, variant)
    assert var_res.score >= 0.40
    assert var_res.status == "relevant"
    assert any("addresses the question's subject" in r for r in var_res.reasons)

    # Irrelevant source
    irrelevant = SearchResult(
        title="Clinical Methods in Adult Cardiology and Echocardiography",
        url="https://example.org/cardio",
        snippet="Standard diagnostic procedures for emergency coronary assessment.",
        source_type="academic",
    )
    irr_res = assess_result(question, irrelevant)
    assert irr_res.score < 0.28
    assert irr_res.status == "rejected"
    assert any("does not identify the question's subject" in r for r in irr_res.reasons)


def test_benchmark_layoffs_it_employees():
    question = "How does layoffs by IT companies affect employees?"
    terms, subject, outcomes = question_focus(question)
    assert {"layoff", "it", "company", "employee"}.issubset(subject)
    assert "affect" in outcomes

    # Relevant source from Investigation A
    relevant = SearchResult(
        title="The Impact of Layoffs on Organizational Culture and Employee Morale in IT Companies",
        url="https://doi.org/10.52783/jier.v5i1.2067",
        snippet="We examine how corporate tech layoffs impact employee satisfaction, mental health, and retention in software firms.",
        source_type="academic",
    )
    rel_res = assess_result(question, relevant)
    assert rel_res.score >= 0.80
    assert rel_res.status == "relevant"
    assert any("addresses the question's subject" in r for r in rel_res.reasons)
    assert any("discusses the requested outcome" in r for r in rel_res.reasons)

    # Partially relevant source (general startup layoffs, limited tech focus)
    partial = SearchResult(
        title="Mass Layoffs and Customer Relations in Retail",
        url="https://example.org/retail-layoffs",
        snippet="A study of store employee reductions and customer shopping frequency.",
        source_type="academic",
    )
    part_res = assess_result(question, partial)
    assert part_res.score < rel_res.score

    # Irrelevant source
    irrelevant = SearchResult(
        title="Pest Management in Organic Rice Agriculture",
        url="https://example.org/rice-pests",
        snippet="Evaluating non-chemical bio-pesticide formulations against seasonal crop damage.",
        source_type="academic",
    )
    irr_res = assess_result(question, irrelevant)
    assert irr_res.score < 0.28
    assert irr_res.status == "rejected"


def test_benchmark_climate_change_agriculture():
    question = "Effects of climate change on agriculture"
    terms, subject, outcomes = question_focus(question)
    assert "climate" in subject
    assert "agriculture" in subject
    assert "effect" in outcomes or "change" in outcomes

    # Relevant source
    relevant = SearchResult(
        title="Climate Change Effects on Agricultural Production and Crop Yields",
        url="https://example.org/ag-climate",
        snippet="Analysis of rising mean temperatures and drought severity on global cereal cultivation.",
        source_type="academic",
    )
    rel_res = assess_result(question, relevant)
    assert rel_res.score >= 0.80
    assert rel_res.status == "relevant"

    # Irrelevant source
    irrelevant = SearchResult(
        title="Quantum Key Distribution Protocols Over Optical Fibers",
        url="https://example.org/quantum-crypto",
        snippet="Security proofs for photon polarization encoding in quantum key exchange.",
        source_type="academic",
    )
    irr_res = assess_result(question, irrelevant)
    assert irr_res.score < 0.28
    assert irr_res.status == "rejected"


def test_benchmark_renewable_energy_benefits_risks():
    question = "Benefits and risks of renewable energy"
    terms, subject, outcomes = question_focus(question)
    assert "renewable" in subject
    assert "energy" in subject
    assert {"benefit", "risk"}.issubset(outcomes)

    # Relevant source
    relevant = SearchResult(
        title="Renewable Energy Transition: Evaluating Economic Benefits and Grid Reliability Risks",
        url="https://example.org/renewable-risks",
        snippet="We evaluate greenhouse gas abatement benefits against intermittency and supply chain risks in wind and solar.",
        source_type="academic",
    )
    rel_res = assess_result(question, relevant)
    assert rel_res.score >= 0.80
    assert rel_res.status == "relevant"

    # Irrelevant source
    irrelevant = SearchResult(
        title="Pediatric Sedation Protocols in Dental Surgery",
        url="https://example.org/dental",
        snippet="Guidelines for safe nitrous oxide administration in young pediatric dental patients.",
        source_type="academic",
    )
    irr_res = assess_result(question, irrelevant)
    assert irr_res.score < 0.28
    assert irr_res.status == "rejected"


def test_benchmark_remote_work_productivity():
    question = "Does remote work affect employee productivity?"
    terms, subject, outcomes = question_focus(question)
    assert "remote" in subject
    assert "work" in subject
    assert "employee" in subject
    assert "productivity" in outcomes or "affect" in outcomes

    # Relevant source
    relevant = SearchResult(
        title="Remote Work and Employee Productivity: Evidence from a Randomized Trial",
        url="https://example.org/remote-productivity",
        snippet="A 9-month randomized trial measuring call center worker output, hours logged, and performance during telecommuting.",
        source_type="academic",
    )
    rel_res = assess_result(question, relevant)
    assert rel_res.score >= 0.80
    assert rel_res.status == "relevant"

    # Irrelevant source
    irrelevant = SearchResult(
        title="Microbial Ecosystems in Submarine Hydrothermal Vents",
        url="https://example.org/microbes",
        snippet="DNA sequencing of thermophilic archaea located near Pacific deep ocean ridges.",
        source_type="academic",
    )
    irr_res = assess_result(question, irrelevant)
    assert irr_res.score < 0.28
    assert irr_res.status == "rejected"


def test_missing_abstract_handling_is_transparent():
    question = "What is AI?"
    no_abstract = SearchResult(
        title="Foundations of AI and Intelligent Systems",
        url="https://example.org/ai-book",
        snippet="",
        source_type="academic",
    )
    assessment = assess_result(question, no_abstract)
    assert assessment.status == "relevant"
    assert any("abstract is unavailable; assessed on title metadata only" in r for r in assessment.reasons)
