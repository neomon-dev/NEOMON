import asyncio
import io
import json
import uuid

import pypdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.analysis.export_service import (
    generate_evidence_csv,
    generate_json_ld_export,
    generate_markdown_export,
    generate_pdf_export,
    generate_sources_csv,
    generate_standalone_html_graph,
    generate_structured_json_export,
    generate_svg_graph_export,
)
from app.analysis.report_service import (
    build_18_report_sections,
    compute_evidence_strength,
)
from app.db import SessionFactory
from app.main import app
from app.models import (
    AdjudicationDecision,
    AnalysisJob,
    Claim,
    Document,
    Evidence,
    Investigation,
    ReportSection,
    ResearchReport,
    Source,
)


def test_markdown_export_format():
    inv = Investigation(id=uuid.uuid4(), question="Does test coverage predict lower defects?", mode="deep")
    c = Claim(id=uuid.uuid4(), text="High test coverage reduces defect escapes.", priority=1)
    src = Source(
        id=uuid.uuid4(),
        title="Defect Study 2024",
        canonical_url="https://doi.org/10.1000/182",
        source_type="academic",
    )
    ev = Evidence(id=uuid.uuid4(), source_id=src.id, exact_text="Teams with >80% coverage had 40% fewer escapes.", evidence_type="direct", relevance_score=0.9)
    strength = compute_evidence_strength([c], [src], [], [ev], [])
    sections = build_18_report_sections(
        inv.question, [c], [], [ev], {src.id: src}, {}, [], [], lambda ids: []
    )

    md = generate_markdown_export(
        inv, None, None, sections, [c], [src], [ev], [], strength
    )

    assert "---" in md
    assert "title: \"NEOMON Research Report:" in md
    assert "evidence_strength_score:" in md
    assert "## Table of Contents" in md
    assert "## 1. Executive Summary" in md
    assert "## 18. References & Evidence Provenance Directory" in md
    assert "Every claim is questioned. Every source is traced." in md


def test_pdf_export_pure_python():
    inv = Investigation(id=uuid.uuid4(), question="Are quantum computers breaking RSA today?", mode="quick")
    c = Claim(id=uuid.uuid4(), text="RSA-2048 is unbroken by current physical hardware.", priority=1)
    sections = build_18_report_sections(
        inv.question, [c], [], [], {}, {}, [], [], lambda ids: []
    )
    strength = compute_evidence_strength([c], [], [], [], [])

    pdf_bytes = generate_pdf_export(inv, None, sections, strength)

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf_bytes

    # Parse with standard pypdf reader to confirm standard compliance
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1
    extracted = "".join(p.extract_text() for p in reader.pages)
    assert "NEOMON Research Intelligence Report" in extracted
    assert "EXECUTIVE SUMMARY" in extracted


def test_structured_json_export():
    inv = Investigation(id=uuid.uuid4(), question="Impact of microservices on latency?", mode="deep")
    c = Claim(id=uuid.uuid4(), text="Microservices introduce network hops.", priority=1)
    src = Source(id=uuid.uuid4(), title="Latency Analysis", canonical_url="https://example.org/lat", source_type="academic")
    ev = Evidence(id=uuid.uuid4(), source_id=src.id, exact_text="P99 latency increased by 14ms.", evidence_type="direct", relevance_score=0.88)
    strength = compute_evidence_strength([c], [src], [], [ev], [])
    sections = build_18_report_sections(inv.question, [c], [], [ev], {src.id: src}, {}, [], [], lambda ids: [])

    snapshot = generate_structured_json_export(
        inv, None, None, sections, [c], [src], [], [ev], [], [], [], None, strength
    )

    assert snapshot["schema_version"] == "1.0.0"
    assert snapshot["investigation"]["id"] == str(inv.id)
    assert len(snapshot["claims"]) == 1
    assert len(snapshot["sources"]) == 1
    assert len(snapshot["evidence"]) == 1
    assert len(snapshot["report"]["sections"]) == 18
    assert snapshot["evidence_strength"]["score"] == strength.score


def test_standalone_html_graph_export():
    inv = Investigation(id=uuid.uuid4(), question="Asynchronous code review effects?", mode="quick")
    c = Claim(id=uuid.uuid4(), text="Review reduces defect escapes.", priority=1)
    src = Source(id=uuid.uuid4(), title="ACM Study", canonical_url="https://acm.org/1", source_type="academic")
    ev = Evidence(id=uuid.uuid4(), source_id=src.id, claim_id=c.id, exact_text="Review reduced defect escapes by 34%.", evidence_type="supporting")

    html_str = generate_standalone_html_graph(inv, [c], [src], [ev], [])

    # Self-contained assertions:
    assert "<!DOCTYPE html>" in html_str
    assert "NEOMON Interactive Knowledge Graph" in html_str
    assert "<svg" in html_str
    assert "<script id=\"graph-data\"" in html_str
    # Must NOT have any remote CDN scripts or fonts
    assert "http://" not in html_str.split("<script id=\"graph-data\"")[0]
    assert "https://" not in html_str.split("<script id=\"graph-data\"")[0]
    assert "cdn." not in html_str.lower()
    assert "unpkg.com" not in html_str.lower()
    assert "cdnjs" not in html_str.lower()


def test_svg_vector_graph_export():
    inv = Investigation(id=uuid.uuid4(), question="Vector graph verification?", mode="quick")
    c = Claim(id=uuid.uuid4(), text="Vector node claim", priority=1)
    src = Source(id=uuid.uuid4(), title="Vector Source", canonical_url="https://example.org", source_type="academic")
    ev = Evidence(id=uuid.uuid4(), source_id=src.id, claim_id=c.id, exact_text="Vector passage", evidence_type="supporting")

    svg_str = generate_svg_graph_export(inv, [c], [src], [ev])

    assert svg_str.startswith("<svg")
    assert svg_str.endswith("</svg>")
    assert "NEOMON Knowledge Graph" in svg_str
    assert "Investigation Hub" in svg_str
    assert "P1: Vector node claim" in svg_str


def test_json_ld_export():
    inv = Investigation(id=uuid.uuid4(), question="Semantic web ontology check", mode="quick")
    c = Claim(id=uuid.uuid4(), text="Ontology claim text", priority=1)
    src = Source(id=uuid.uuid4(), title="Semantics 2024", canonical_url="https://w3.org/paper", publisher="W3C", doi="10.1000/w3", source_type="institutional")

    ld = generate_json_ld_export(inv, None, [c], [src], [], [])

    assert ld["@context"]["@vocab"] == "https://schema.org/"
    assert ld["@type"] == "ScholarlyArticle"
    assert ld["headline"] == "Semantic web ontology check"
    assert len(ld["citation"]) == 1
    assert ld["citation"][0]["name"] == "Semantics 2024"
    assert len(ld["about"]) == 1
    assert ld["about"][0]["claimReviewed"] == "Ontology claim text"


def test_csv_datasets_export():
    c = Claim(id=uuid.uuid4(), text="Tabular claim", priority=2)
    src = Source(id=uuid.uuid4(), title="Tabular Source", canonical_url="https://example.org/tab", original_url="https://example.org/tab", source_type="academic", publisher="Springer", doi="10.1007/1", relevance_score=0.91)
    ev = Evidence(id=uuid.uuid4(), claim_id=c.id, source_id=src.id, exact_text="Tabular evidence passage.", evidence_type="direct", relevance_score=0.94, page_number=12, section_name="Results", traceable=True)

    ev_csv = generate_evidence_csv([c], [src], [ev])
    assert "evidence_id,claim_id,claim_text" in ev_csv
    assert "Tabular evidence passage." in ev_csv
    assert "Tabular Source" in ev_csv

    src_csv = generate_sources_csv([src])
    assert "source_id,title,canonical_url" in src_csv
    assert "Tabular Source" in src_csv
    assert "Springer" in src_csv
    assert "10.1007/1" in src_csv


def test_export_endpoints_via_test_client():
    inv_id = uuid.uuid4()
    job_id = uuid.uuid4()
    report_id = uuid.uuid4()

    async def seed():
        async with SessionFactory() as s:
            inv = Investigation(id=inv_id, question="Export test investigation topic?", mode="quick")
            job = AnalysisJob(id=job_id, investigation_id=inv_id, status="completed")
            rep = ResearchReport(id=report_id, job_id=job_id, executive_summary="Report for export", overall_assessment="qualified")
            c = Claim(id=uuid.uuid4(), investigation_id=inv_id, text="Claim for export test.", priority=1)
            src = Source(id=uuid.uuid4(), investigation_id=inv_id, title="Export Source 1", canonical_url="https://example.org/export", original_url="https://example.org/export", source_type="academic")
            s.add_all([inv, job, rep, c, src])
            await s.commit()

    asyncio.run(seed())

    try:
        with TestClient(app) as client:
            base = f"/api/v1/research/investigations/{inv_id}/export"

            # 1. Manifest
            m_resp = client.get(f"{base}/manifest")
            assert m_resp.status_code == 200
            manifest = m_resp.json()
            assert len(manifest["formats"]) == 8

            # 2. Markdown
            md_resp = client.get(f"{base}/markdown")
            assert md_resp.status_code == 200
            assert "text/markdown" in md_resp.headers["content-type"]
            assert "Export test investigation topic" in md_resp.text

            # 3. PDF
            pdf_resp = client.get(f"{base}/pdf")
            assert pdf_resp.status_code == 200
            assert "application/pdf" in pdf_resp.headers["content-type"]
            assert pdf_resp.content.startswith(b"%PDF-1.4")

            # 4. JSON
            json_resp = client.get(f"{base}/json")
            assert json_resp.status_code == 200
            assert json_resp.json()["schema_version"] == "1.0.0"

            # 5. Standalone HTML Graph
            html_resp = client.get(f"{base}/html-graph")
            assert html_resp.status_code == 200
            assert "text/html" in html_resp.headers["content-type"]
            assert "NEOMON Interactive Knowledge Graph" in html_resp.text

            # 6. SVG
            svg_resp = client.get(f"{base}/svg")
            assert svg_resp.status_code == 200
            assert "image/svg+xml" in svg_resp.headers["content-type"]
            assert "<svg" in svg_resp.text

            # 7. JSON-LD
            ld_resp = client.get(f"{base}/json-ld")
            assert ld_resp.status_code == 200
            assert ld_resp.json()["@type"] == "ScholarlyArticle"

            # 8. CSVs
            ev_resp = client.get(f"{base}/evidence-csv")
            assert ev_resp.status_code == 200
            assert "evidence_id,claim_id" in ev_resp.text

            src_resp = client.get(f"{base}/sources-csv")
            assert src_resp.status_code == 200
            assert "Export Source 1" in src_resp.text
    finally:
        async def cleanup():
            async with SessionFactory() as s:
                await s.execute(delete(ResearchReport).where(ResearchReport.id == report_id))
                await s.execute(delete(AnalysisJob).where(AnalysisJob.id == job_id))
                await s.execute(delete(Investigation).where(Investigation.id == inv_id))
                await s.commit()
        asyncio.run(cleanup())
