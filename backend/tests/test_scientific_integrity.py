import uuid
import pytest

from app.analysis.protocol import DecisionPayload
from app.analysis.report_service import compute_evidence_strength, build_18_report_sections
from app.analysis.service import _candidate_evidence, _role_argument
from app.models import AdjudicationDecision, Claim, Document, Evidence, Source
from app.research.providers import SearchResult
from app.research.relevance import assess_result, classify_evidence
from app.research.retrieval import RetrievedDocument
from app.research.scientific_integrity import (
    EvidenceCategory,
    SourceCredibilityType,
    assess_source_credibility,
    classify_evidence_for_claim,
    detect_source_independence_clusters,
    verify_evidence_provenance,
)


def test_provenance_verification_exact_containment():
    """Verify that exact text containment in the document succeeds, while tampered text fails."""
    doc = RetrievedDocument(
        url="https://ieee.org/papers/123",
        final_url="https://ieee.org/papers/123",
        content_type="text/plain",
        title="High-Bandwidth Memory Architecture for Neural Accelerators",
        content="Modern generative AI models require exponential memory bandwidth. High-bandwidth memory (HBM) stacking has become the primary bottleneck in hyperscale hardware deployments.",
        headings=["Introduction", "Memory Bottlenecks"],
        passages=[
            (None, "Modern generative AI models require exponential memory bandwidth.", "Introduction"),
            (None, "High-bandwidth memory (HBM) stacking has become the primary bottleneck in hyperscale hardware deployments.", "Memory Bottlenecks"),
        ],
        access_level="full_text",
        extraction_quality="high",
        page_count=12,
    )

    # Valid exact text and section
    valid_ver = verify_evidence_provenance(
        document=doc,
        exact_text="High-bandwidth memory (HBM) stacking has become the primary bottleneck in hyperscale hardware deployments.",
        section_name="Memory Bottlenecks",
        page_number=2,
    )
    assert valid_ver.verified is True
    assert valid_ver.traceable is True
    assert valid_ver.failure_reason is None

    # Tampered / fabricated text not present in document
    tampered_ver = verify_evidence_provenance(
        document=doc,
        exact_text="AI will cause global computer memory chips to cease production entirely by 2027.",
        section_name="Memory Bottlenecks",
        page_number=2,
    )
    assert tampered_ver.verified is False
    assert tampered_ver.traceable is False
    assert "Exact text was not found" in (tampered_ver.failure_reason or "")

    # Mismatched section heading
    mismatched_section_ver = verify_evidence_provenance(
        document=doc,
        exact_text="High-bandwidth memory (HBM) stacking has become the primary bottleneck in hyperscale hardware deployments.",
        section_name="Cardiology Clinical Results",
        page_number=2,
    )
    assert mismatched_section_ver.verified is False
    assert mismatched_section_ver.traceable is False
    assert "Section heading" in (mismatched_section_ver.failure_reason or "")

    # Page number out of bounds
    out_of_bounds_ver = verify_evidence_provenance(
        document=doc,
        exact_text="High-bandwidth memory (HBM) stacking has become the primary bottleneck in hyperscale hardware deployments.",
        section_name="Memory Bottlenecks",
        page_number=999,
    )
    assert out_of_bounds_ver.verified is False
    assert out_of_bounds_ver.traceable is False
    assert "exceeds document page count" in (out_of_bounds_ver.failure_reason or "")


def test_claim_specific_evidence_classification_6_categories():
    """Verify claim-specific semantic entailment across all 6 evidence categories."""
    claim = "AI model scaling drives severe global RAM and HBM shortages."

    # 1. Supporting
    res_sup = classify_evidence_for_claim(
        claim,
        "Rapid adoption of LLMs has caused unprecedented demand for HBM3e memory, leading to severe supply constraints across memory foundries.",
    )
    assert res_sup.category == EvidenceCategory.SUPPORTING
    assert res_sup.confidence >= 0.70

    # 2. Contradicting
    res_contra = classify_evidence_for_claim(
        claim,
        "Empirical market audits indicate global DRAM supply remains in heavy surplus, with no measurable shortages in consumer or enterprise memory.",
    )
    assert res_contra.category == EvidenceCategory.CONTRADICTING
    assert res_contra.confidence >= 0.70

    # 3. Mitigating (Counterbalancing forces)
    res_mit = classify_evidence_for_claim(
        claim,
        "While memory demands increase, 3D packaging yield enhancements and architectural DRAM compression significantly reduce per-model memory footprint.",
    )
    assert res_mit.category == EvidenceCategory.MITIGATING
    assert res_mit.confidence >= 0.65

    # 4. Methodological Limitation
    res_lim = classify_evidence_for_claim(
        claim,
        "The survey was limited to a convenience sample of 5 startup founders and lacked longitudinal supply-chain verification.",
    )
    assert res_lim.category == EvidenceCategory.METHODOLOGICAL_LIMITATION

    # 5. Contextual
    res_ctx = classify_evidence_for_claim(
        claim,
        "Dynamic random-access memory (DRAM) was invented in 1968 by Robert Dennard at IBM Research.",
    )
    assert res_ctx.category == EvidenceCategory.CONTEXTUAL

    # 6. Insufficient
    res_ins = classify_evidence_for_claim(
        claim,
        "Weather patterns in the Pacific Northwest have brought unseasonably heavy precipitation this winter.",
    )
    assert res_ins.category == EvidenceCategory.INSUFFICIENT


def test_source_credibility_assessment_rubric():
    """Verify granular credibility classification across authoritative, preprints, journalism, and vendors."""
    # Peer-reviewed academic
    cred_pr = assess_source_credibility(
        publisher="IEEE Computer Society",
        url="https://ieeexplore.ieee.org/document/9876543",
        doi="10.1109/TC.2024.123456",
        source_type_declared="academic",
    )
    assert cred_pr.source_type == SourceCredibilityType.PEER_REVIEWED
    assert cred_pr.credibility_tier == "authoritative"
    assert cred_pr.credibility_score >= 0.90

    # Preprint
    cred_prep = assess_source_credibility(
        publisher="arXiv",
        url="https://arxiv.org/abs/2401.99999",
        doi="10.48550/arXiv.2401.99999",
    )
    assert cred_prep.source_type == SourceCredibilityType.PREPRINT
    assert cred_prep.credibility_score >= 0.70

    # Government / Institutional
    cred_gov = assess_source_credibility(
        publisher="National Institute of Standards and Technology",
        url="https://www.nist.gov/publications/ai-risk-management",
    )
    assert cred_gov.source_type == SourceCredibilityType.GOVERNMENT_INSTITUTIONAL
    assert cred_gov.credibility_score >= 0.90

    # Reputable journalism
    cred_news = assess_source_credibility(
        publisher="Reuters",
        url="https://www.reuters.com/technology/ai-chip-memory-shortage-2024/",
    )
    assert cred_news.source_type == SourceCredibilityType.REPUTABLE_JOURNALISM
    assert cred_news.credibility_score >= 0.70

    # Vendor / Commercial
    cred_vendor = assess_source_credibility(
        publisher="Vendor Promotional Whitepaper",
        url="https://solutions.promotional-vendor.com/product-overview",
    )
    assert cred_vendor.source_type == SourceCredibilityType.VENDOR_COMMERCIAL
    assert cred_vendor.credibility_score <= 0.40


def test_syndication_and_independence_clusters():
    """Verify that syndicated or reposted reports are grouped into single independence clusters."""
    sources = [
        # Syndicate group A: Reuters report republished by Yahoo and MSN
        {"id": "1", "title": "Memory chip supply tightens as AI servers boom", "url": "https://www.reuters.com/tech/memory-chip-2024", "publisher": "Reuters"},
        {"id": "2", "title": "Memory chip supply tightens as AI servers boom", "url": "https://finance.yahoo.com/news/memory-chip-2024", "publisher": "Yahoo Finance"},
        {"id": "3", "title": "Memory chip supply tightens as AI servers boom", "url": "https://www.msn.com/en-us/news/memory-chip-2024", "publisher": "MSN"},
        # Independent study B: IEEE paper with DOI
        {"id": "4", "title": "Thermal and Bandwidth Characterization of HBM3", "url": "https://ieeexplore.ieee.org/doc/1", "doi": "10.1109/HBM.2024.1", "publisher": "IEEE"},
        # Independent study C: Nature Electronics paper with distinct DOI
        {"id": "5", "title": "Next-generation memory architectures for deep learning", "url": "https://nature.com/articles/s41928-024", "doi": "10.1038/s41928-024-1", "publisher": "Nature Publishing Group"},
    ]

    clusters = detect_source_independence_clusters(sources)
    # The 3 syndicated articles should merge into 1 cluster, giving 3 distinct clusters total
    assert len(clusters) == 3
    syndicated_cluster = next(c for c in clusters if len(c.source_ids) == 3)
    assert set(syndicated_cluster.source_ids) == {"1", "2", "3"}


def test_benchmark_5_research_questions():
    """Regression test across the 5 benchmark questions."""
    benchmark_cases = [
        {
            "question": "How does AI contribute to RAM shortages?",
            "relevant_title": "Impact of Large Language Model Infrastructure on Global HBM and DRAM Supply",
            "snippet": "Analysis of high-bandwidth memory allocation in hyperscale AI clusters and packaging constraints.",
            "irrelevant_title": "Historical Weather Patterns in Southern Spain",
            "irrelevant_snippet": "Precipitation analysis for agricultural planning.",
        },
        {
            "question": "How does AI increase electricity demand?",
            "relevant_title": "Electricity Consumption Trends of Machine Learning Data Centers",
            "snippet": "Empirical power draw measurements of GPU clusters and projected grid load additions.",
            "irrelevant_title": "Early Renaissance Fresco Preservation Techniques",
            "irrelevant_snippet": "Methods for restoring Italian fresco pigments.",
        },
        {
            "question": "How do IT company layoffs affect employees?",
            "relevant_title": "Psychological and Career Impacts of Mass Layoffs in the Technology Sector",
            "snippet": "Longitudinal survey on mental health, wage recovery, and job security post-downsizing.",
            "irrelevant_title": "Quantum Hall Effect in Graphene Nanoribbons",
            "irrelevant_snippet": "Electronic transport properties at cryogenic temperatures.",
        },
        {
            "question": "What is AI?",
            "relevant_title": "What is AI? Foundations, Computational Paradigms, and Modern Perspectives",
            "snippet": "A comprehensive survey defining artificial intelligence from Turing to transformers.",
            "irrelevant_title": "Clinical Echocardiography in Canine Veterinary Medicine",
            "irrelevant_snippet": "Diagnostic protocols for canine cardiac assessment.",
        },
        {
            "question": "Does AI improve or worsen educational outcomes?",
            "relevant_title": "Evaluating the Educational Impact of Generative AI in Secondary Schools",
            "snippet": "Randomized controlled trial evaluating student problem-solving and critical thinking with AI tutors.",
            "irrelevant_title": "Synthesis of Novel Zeolites for Catalytic Cracking",
            "irrelevant_snippet": "Hydrothermal synthesis of microporous aluminosilicates.",
        },
    ]

    for case in benchmark_cases:
        q = case["question"]
        rel = SearchResult(
            title=case["relevant_title"],
            url="https://scholar.example.org/study",
            snippet=case["snippet"],
            source_type="academic",
        )
        rel_eval = assess_result(q, rel)
        assert rel_eval.score >= 0.45, f"Expected relevant score for '{q}', got {rel_eval.score}"
        assert rel_eval.status == "relevant"

        irr = SearchResult(
            title=case["irrelevant_title"],
            url="https://scholar.example.org/unrelated",
            snippet=case["irrelevant_snippet"],
            source_type="academic",
        )
        irr_eval = assess_result(q, irr)
        assert irr_eval.score < 0.28, f"Expected rejected score for '{q}', got {irr_eval.score}"
        assert irr_eval.status == "rejected"


def test_agent_integrity_advocate_and_skeptic_evidence_rules():
    """Verify Advocate uses only supporting evidence, while Skeptic uses contradicting/mitigating/limitations."""
    c_id = uuid.uuid4()
    claim = Claim(id=c_id, text="AI drives RAM shortages", search_objectives_json="[]", priority=1)
    s_id = uuid.uuid4()
    source = Source(id=s_id, title="Semiconductor Journal", original_url="https://example.com")
    sources = {s_id: source}

    ev_supp = Evidence(id=uuid.uuid4(), claim_id=c_id, source_id=s_id, exact_text="HBM demand surged 300%.", evidence_type="supporting", relevance_score=0.9, traceable=True)
    ev_contra = Evidence(id=uuid.uuid4(), claim_id=c_id, source_id=s_id, exact_text="DRAM stockpiles rose 15%.", evidence_type="contradicting", relevance_score=0.85, traceable=True)
    ev_mit = Evidence(id=uuid.uuid4(), claim_id=c_id, source_id=s_id, exact_text="DRAM efficiency stacking lowers footprint.", evidence_type="mitigating", relevance_score=0.8, traceable=True)
    ev_ctx = Evidence(id=uuid.uuid4(), claim_id=c_id, source_id=s_id, exact_text="Memory exists in PCs.", evidence_type="contextual", relevance_score=0.4, traceable=True)

    evidence_pool = [ev_supp, ev_contra, ev_mit, ev_ctx]

    # Advocate test: only supporting evidence
    adv_arg = _role_argument("advocate", claim, evidence_pool, sources)
    assert adv_arg.argument_type.value == "supporting"
    assert adv_arg.evidence_ids == [ev_supp.id]
    assert ev_contra.id not in adv_arg.evidence_ids
    assert ev_ctx.id not in adv_arg.evidence_ids

    # Skeptic test: includes contradicting and mitigating evidence
    skep_arg = _role_argument("skeptic", claim, evidence_pool, sources)
    assert skep_arg.argument_type.value == "contradicting"
    assert ev_contra.id in skep_arg.evidence_ids
    assert ev_mit.id in skep_arg.evidence_ids
    assert ev_supp.id not in skep_arg.evidence_ids

    # Empty supporting fallback test
    adv_empty = _role_argument("advocate", claim, [ev_contra, ev_mit], sources)
    assert "No supporting evidence found" in adv_empty.text


def test_compute_evidence_strength_5_dimensions_calibration():
    """Verify deterministic 5-dimension scoring and quality tier explanation."""
    c_id = uuid.uuid4()
    claim = Claim(id=c_id, text="Hypothesis", search_objectives_json="[]", priority=1)
    
    # Sources from 3 distinct clusters
    s1 = Source(id=uuid.uuid4(), title="Nature Study", publisher="Nature", doi="10.1038/s1", canonical_url="https://nature.com/1", source_type="peer_reviewed", relevance_score=0.95)
    s2 = Source(id=uuid.uuid4(), title="IEEE Study", publisher="IEEE", doi="10.1109/s2", canonical_url="https://ieee.org/2", source_type="peer_reviewed", relevance_score=0.92)
    s3 = Source(id=uuid.uuid4(), title="NIST Technical Report", publisher="NIST", canonical_url="https://nist.gov/3", source_type="government_institutional", relevance_score=0.88)
    sources = [s1, s2, s3]

    doc1 = Document(id=uuid.uuid4(), source_id=s1.id, content="Full text 1", access_level="full_text", extraction_quality="high")
    doc2 = Document(id=uuid.uuid4(), source_id=s2.id, content="Full text 2", access_level="full_text", extraction_quality="high")
    docs = [doc1, doc2]

    # Multi-angle evidence: supporting, mitigating, and contradicting
    e1 = Evidence(id=uuid.uuid4(), claim_id=c_id, source_id=s1.id, exact_text="Empirical proof A.", evidence_type="supporting", relevance_score=0.95, traceable=True)
    e2 = Evidence(id=uuid.uuid4(), claim_id=c_id, source_id=s2.id, exact_text="Counter-evidence B.", evidence_type="contradicting", relevance_score=0.85, traceable=True)
    e3 = Evidence(id=uuid.uuid4(), claim_id=c_id, source_id=s3.id, exact_text="Mitigating efficiency factor C.", evidence_type="mitigating", relevance_score=0.80, traceable=True)
    evidence = [e1, e2, e3]

    decision = DecisionPayload(
        claim_id=c_id,
        decision="weakly_supported",
        explanation="Evidence shows mixed effects with counterbalancing factors.",
        evidence_ids=[e1.id, e2.id, e3.id],
    )

    strength = compute_evidence_strength([claim], sources, docs, evidence, [decision])
    assert strength.score >= 70.0
    assert strength.tier in {"strong", "very_strong"}
    assert len(strength.reasons) >= 5
    assert "Source Independence" in strength.reasons[0]
    assert "Full-Text Coverage" in strength.reasons[2]
