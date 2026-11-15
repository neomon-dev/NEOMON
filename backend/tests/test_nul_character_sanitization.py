"""Tests for NUL character sanitization in the document extraction and persistence pipeline.

PostgreSQL does not allow NUL (\x00 / 0x00) characters in text/varchar columns.
These tests verify that:
1. Document extraction (HTML, PDF, plain text) strips NUL bytes.
2. Evidence sentence extraction sanitizes passages.
3. ORM models (Document, Evidence, Source, Claim) automatically strip NUL characters via @validates.
4. Database persistence succeeds with zero NUL leakage.
"""

import pytest
import uuid
from app.db import SessionFactory
from app.models import Claim, Document, Evidence, Investigation, Source
from app.research.evidence import _sentences, extract_evidence
from app.research.retrieval import _HTMLTextParser


def test_html_parser_strips_nul_characters():
    parser = _HTMLTextParser()
    raw_html = "<html><head><title>Test\x00 Title</title></head><body><h1>Heading\x00 1</h1><p>This is a paragraph with\x00 embedded NUL bytes.</p></body></html>"
    parser.feed(raw_html)

    assert "\x00" not in (parser.title or "")
    assert parser.title == "Test Title"
    assert len(parser.headings) == 1
    assert "\x00" not in parser.headings[0]
    assert parser.headings[0] == "Heading 1"
    for section, text in parser.parts:
        assert "\x00" not in text
        if section:
            assert "\x00" not in section


def test_evidence_sentence_splitting_strips_nul_characters():
    text_with_nul = "Empirical evaluation of GLP-1\x00 receptor agonists shows significant weight reduction. Patient cohorts demonstrated sustained glycemic control over forty-eight\x00 weeks."
    sentences = _sentences(text_with_nul)
    assert len(sentences) >= 1
    for s in sentences:
        assert "\x00" not in s


def test_extract_evidence_strips_nul_from_passages():
    claim = "Deep neural networks significantly accelerate protein structure prediction."
    passage = "Empirical data shows that deep neural\x00 networks found that protein structure prediction runtime was reduced by 90%, demonstrating that deep learning accelerates structural\x00 modeling."
    passages = [(1, passage, "Results\x00 Section")]

    results = extract_evidence(passage, claim, passages=passages)
    assert len(results) >= 1
    for item in results:
        assert "\x00" not in item.exact_text
        assert "\x00" not in item.surrounding_context
        if item.section_name:
            assert "\x00" not in item.section_name
        assert "\x00" not in item.relevance_reason


def test_document_model_validates_and_strips_nul():
    doc = Document(
        source_id=uuid.uuid4(),
        content_type="text/html",
        title="Sample\x00 Document Title",
        content="First paragraph\x00 with NUL.\nSecond paragraph\x00 clean.",
        document_url="https://example.com/paper\x00/pdf",
    )
    assert "\x00" not in (doc.title or "")
    assert doc.title == "Sample Document Title"
    assert "\x00" not in doc.content
    assert doc.content == "First paragraph with NUL.\nSecond paragraph clean."
    assert "\x00" not in (doc.document_url or "")
    assert doc.document_url == "https://example.com/paper/pdf"


def test_evidence_model_validates_and_strips_nul():
    ev = Evidence(
        source_id=uuid.uuid4(),
        exact_text="Clinical trial data\x00 shows 40% reduction.",
        surrounding_context="Background context\x00 surrounding trial.",
        section_name="Discussion\x00 Section",
        relevance_reason="High semantic\x00 relevance to claim.",
        extraction_method="relevance_filtered\x00_sentence_match",
        evidence_type="supporting\x00",
    )
    assert "\x00" not in ev.exact_text
    assert ev.exact_text == "Clinical trial data shows 40% reduction."
    assert "\x00" not in (ev.surrounding_context or "")
    assert ev.surrounding_context == "Background context surrounding trial."
    assert "\x00" not in (ev.section_name or "")
    assert ev.section_name == "Discussion Section"
    assert "\x00" not in ev.relevance_reason
    assert "\x00" not in ev.extraction_method
    assert "\x00" not in ev.evidence_type


def test_source_model_validates_and_strips_nul():
    src = Source(
        investigation_id=uuid.uuid4(),
        title="Journal\x00 of Medical Research",
        canonical_url="https://example.com/study",
        original_url="https://example.com/study",
        source_type="academic",
        publisher="Nature\x00 Publishing Group",
        rejection_reason="Relevance\x00 too low",
        study_identity_key="10.1038/s41586\x00",
    )
    assert "\x00" not in src.title
    assert src.title == "Journal of Medical Research"
    assert "\x00" not in (src.publisher or "")
    assert src.publisher == "Nature Publishing Group"
    assert "\x00" not in (src.rejection_reason or "")
    assert src.rejection_reason == "Relevance too low"
    assert "\x00" not in (src.study_identity_key or "")
    assert src.study_identity_key == "10.1038/s41586"


def test_claim_model_validates_and_strips_nul():
    clm = Claim(
        investigation_id=uuid.uuid4(),
        text="Hypothesis\x00 with NUL character.",
        explanation="Detailed\x00 explanation.",
    )
    assert "\x00" not in clm.text
    assert clm.text == "Hypothesis with NUL character."
    assert "\x00" not in clm.explanation
    assert clm.explanation == "Detailed explanation."


@pytest.mark.asyncio
async def test_database_persistence_with_nul_characters():
    """Verify that adding records containing NUL bytes persists cleanly to DB without errors."""
    async with SessionFactory() as session:
        inv = Investigation(question="Test question for NUL sanitization?")
        session.add(inv)
        await session.flush()

        src = Source(
            investigation_id=inv.id,
            title="Paper with\x00 NUL Title",
            canonical_url="https://example.com/paper-nul",
            original_url="https://example.com/paper-nul",
            source_type="academic",
        )
        session.add(src)
        await session.flush()

        doc = Document(
            source_id=src.id,
            content_type="text/plain",
            title="Document\x00 Title",
            content="Deep text containing\x00 multiple\x00 NUL bytes throughout the\x00 corpus.",
        )
        session.add(doc)
        await session.flush()

        ev = Evidence(
            source_id=src.id,
            document_id=doc.id,
            exact_text="Extracted sentence with\x00 NUL.",
            evidence_type="supporting",
            relevance_score=0.92,
            extraction_method="pdf_sentence\x00_match",
        )
        session.add(ev)
        await session.commit()

        # Re-fetch and verify database state
        await session.refresh(doc)
        await session.refresh(ev)
        assert "\x00" not in doc.content
        assert "\x00" not in ev.exact_text
        assert doc.content == "Deep text containing multiple NUL bytes throughout the corpus."
        assert ev.exact_text == "Extracted sentence with NUL."
