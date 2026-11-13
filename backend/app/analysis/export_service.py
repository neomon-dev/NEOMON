import csv
import html
import io
import json
import math
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from app.analysis.protocol import ReportSectionPayload
from app.models import (
    AdjudicationDecision,
    AgentArgument,
    AnalysisJob,
    Claim,
    DebateRound,
    Document,
    Evidence,
    Investigation,
    ReportSection,
    ResearchReport,
    Source,
)
from app.schemas import AnalysisCoverageSummary, EvidenceStrengthSummary
from app.research.scientific_integrity import assess_source_credibility
from app.research.source_credibility import evaluate_canonical_credibility
from app.research.source_lineage import analyze_source_lineage
from app.analysis.entailment_service import validate_evidence_claim_entailment_heuristic
from app.analysis.quality_calibration_service import calculate_calibrated_quality


def _escape_csv(val: Any) -> str:
    if val is None:
        return ""
    return str(val)


def _wrap_text_lines(text: str, max_chars: int = 85) -> list[str]:
    lines = []
    for paragraph in text.split("\n"):
        p = paragraph.strip()
        if not p:
            lines.append("")
            continue
        words = p.split()
        cur_line = []
        cur_len = 0
        for w in words:
            if cur_len + len(w) + 1 > max_chars:
                lines.append(" ".join(cur_line))
                cur_line = [w]
                cur_len = len(w)
            else:
                cur_line.append(w)
                cur_len += len(w) + 1
        if cur_line:
            lines.append(" ".join(cur_line))
    return lines


# ---------------------------------------------------------------------------
# 1. MARKDOWN EXPORT
# ---------------------------------------------------------------------------
def generate_markdown_export(
    investigation: Investigation,
    job: AnalysisJob | None,
    report: ResearchReport | None,
    sections: list[ReportSection] | list[ReportSectionPayload],
    claims: list[Claim],
    sources: list[Source],
    evidence: list[Evidence],
    decisions: list[AdjudicationDecision],
    strength: EvidenceStrengthSummary | None,
) -> str:
    lines = [
        "---",
        f"title: \"NEOMON Research Report: {investigation.question.replace('\"', '')}\"",
        f"investigation_id: \"{investigation.id}\"",
        f"mode: \"{investigation.mode}\"",
        f"date: \"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\"",
        f"overall_assessment: \"{report.overall_assessment if report else 'unverified'}\"",
    ]
    if strength:
        lines.append(f"evidence_strength_score: {strength.score}")
        lines.append(f"evidence_strength_tier: \"{strength.tier}\"")
    lines.extend([
        "generator: \"NEOMON (Neural Evidence Orchestration & Multi-Agent Observation Network)\"",
        "tagline: \"Every claim is questioned. Every source is traced. Every conclusion is earned.\"",
        "---",
        "",
        f"# Research Report: {investigation.question}",
        "",
    ])

    # Compute or include calibrated quality evaluation
    cal_breakdown = calculate_calibrated_quality(sources, claims, evidence)

    lines.extend([
        "> [!IMPORTANT]",
        f"> **Calibrated Research Quality Tier:** **{cal_breakdown.calibrated_tier}**",
        f"> - Calibrated Score: **{cal_breakdown.calibrated_score}/100** (Raw Score: {cal_breakdown.raw_score}/100)",
        f"> - Research Coverage Score: **{cal_breakdown.coverage_score:.1f}%**",
        f"> - Provider Failure Penalty: **-{cal_breakdown.failure_penalty:.1f} pts**",
        f"> - Calibration Rationale: {'; '.join(cal_breakdown.reasons[:2]) if cal_breakdown.reasons else 'Empirically calibrated.'}",
        "",
    ])

    if strength:
        lines.extend([
            "> [!NOTE]",
            f"> **Raw Evidence Strength Rating:** **{strength.score}/100** ({strength.tier.replace('_', ' ').upper()})",
            f"> - Source Independence: {strength.breakdown.source_independence}/25",
            f"> - Source Quality: {strength.breakdown.source_quality}/25",
            f"> - Full-Text Coverage: {strength.breakdown.full_text_coverage}/20",
            f"> - Methodological Rigor: {strength.breakdown.methodological_rigor}/15",
            f"> - Conflict Resolution: {strength.breakdown.conflict_resolution}/15",
            "",
        ])

    # Table of Contents
    lines.append("## Table of Contents")
    for i, s in enumerate(sections, 1):
        slug = re.sub(r"[^a-z0-9\-]+", "", s.title.lower().replace(" ", "-"))
        lines.append(f"{i}. [{s.title}](#{slug})")
    lines.append("")

    # Sections Content
    for i, s in enumerate(sections, 1):
        lines.append(f"## {i}. {s.title}")
        lines.append("")
        lines.append(s.content)
        lines.append("")

    lines.extend([
        "---",
        "*Report autonomously synthesized by NEOMON. All claims and evidence are strictly grounded in persisted sources.*",
    ])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 2. PURE PYTHON MULTI-PAGE PDF GENERATOR
# ---------------------------------------------------------------------------
def generate_pdf_export(
    investigation: Investigation,
    report: ResearchReport | None,
    sections: list[ReportSection] | list[ReportSectionPayload],
    strength: EvidenceStrengthSummary | None,
) -> bytes:
    """Generates standard PDF 1.4 document in pure Python with multi-page text layout."""
    page_texts: list[list[str]] = []
    current_page: list[str] = []

    # Title block
    current_page.append("NEOMON Research Intelligence Report")
    current_page.append(f"Topic: {investigation.question}")
    current_page.append(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} | Mode: {investigation.mode}")
    if strength:
        q_status = (investigation.quality_status or "insufficient_evidence").replace("_", " ").upper()
        current_page.append(f"Evidence Strength Score: {strength.score}/100 ({strength.tier.upper()}) | Calibrated Quality: {q_status}")
    current_page.append("--------------------------------------------------------------------------------")
    current_page.append("")

    for idx, sec in enumerate(sections, 1):
        # Section header
        heading = f"[{idx}] {sec.title.upper()}"
        if len(current_page) > 42:
            page_texts.append(current_page)
            current_page = []

        current_page.append(heading)
        current_page.append("")
        wrapped = _wrap_text_lines(sec.content, max_chars=80)
        for line in wrapped:
            if len(current_page) > 46:
                page_texts.append(current_page)
                current_page = []
            current_page.append(line)
        current_page.append("")

    if current_page:
        page_texts.append(current_page)

    if not page_texts:
        page_texts.append(["No report sections available."])

    # Build PDF 1.4 Objects
    pdf_objects: list[bytes] = []

    # Obj 1: Catalog
    pdf_objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")

    # Obj 2: Pages container (placeholder, constructed after pages)
    total_pages = len(page_texts)

    # We will allocate:
    # 1: Catalog
    # 2: Pages
    # 3: Font
    # For each page i (0-based):
    #   Obj 4 + 2*i: Page
    #   Obj 4 + 2*i + 1: Contents stream
    font_obj_num = 3
    pdf_objects.append(b"")  # placeholder for Pages obj

    # Obj 3: Font
    pdf_objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_obj_nums = []
    for p_idx, p_lines in enumerate(page_texts):
        page_num = p_idx + 1
        page_obj_id = 4 + 2 * p_idx
        stream_obj_id = page_obj_id + 1
        page_obj_nums.append(page_obj_id)

        # Build stream text
        stream_parts = ["BT", "/F1 10 Tf", "13 TL", "45 745 Td"]
        for line_idx, line in enumerate(p_lines):
            # Escape PDF special chars: (, ), \
            sanitized = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            # Sanitize latin1 chars
            safe_chars = "".join(c if ord(c) < 128 else "?" for c in sanitized)
            if line_idx == 0 and page_num == 1:
                stream_parts.append(f"({safe_chars}) '")
            else:
                stream_parts.append(f"({safe_chars}) '")

        # Footer
        footer_text = f"NEOMON Research Intelligence  |  Page {page_num} of {total_pages}"
        stream_parts.extend(["ET", "BT", "/F1 8 Tf", f"45 35 Td", f"({footer_text}) Tj", "ET\n"])
        stream_bytes = "\n".join(stream_parts).encode("latin1", "replace")

        # Page Object
        page_obj = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_obj_num} 0 R >> >> "
            f"/Contents {stream_obj_id} 0 R >>"
        ).encode("latin1")
        pdf_objects.append(page_obj)

        # Content Stream Object
        content_obj = (
            f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin1")
            + stream_bytes
            + b"\nendstream"
        )
        pdf_objects.append(content_obj)

    # Now construct Obj 2 (Pages)
    kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_nums)
    pages_obj = f"<< /Type /Pages /Kids [{kids_str}] /Count {total_pages} >>".encode("latin1")
    pdf_objects[1] = pages_obj

    # Assemble Document
    out = io.BytesIO()
    header = b"%PDF-1.4\n"
    out.write(header)

    offsets = [0]
    for idx, obj in enumerate(pdf_objects, 1):
        offsets.append(out.tell())
        out.write(f"{idx} 0 obj\n".encode("latin1"))
        out.write(obj)
        out.write(b"\nendobj\n")

    xref_pos = out.tell()
    out.write(f"xref\n0 {len(pdf_objects) + 1}\n".encode("latin1"))
    out.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.write(f"{off:010d} 00000 n \n".encode("latin1"))

    trailer = (
        f"trailer\n<< /Size {len(pdf_objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF"
    )
    out.write(trailer.encode("latin1"))
    return out.getvalue()


# ---------------------------------------------------------------------------
# 3. STRUCTURED JSON EXPORT
# ---------------------------------------------------------------------------
def generate_structured_json_export(
    investigation: Investigation,
    job: AnalysisJob | None,
    report: ResearchReport | None,
    sections: list[ReportSection] | list[ReportSectionPayload],
    claims: list[Claim],
    sources: list[Source],
    documents: list[Document],
    evidence: list[Evidence],
    arguments: list[AgentArgument],
    debates: list[DebateRound],
    decisions: list[AdjudicationDecision],
    coverage: AnalysisCoverageSummary | None,
    strength: EvidenceStrengthSummary | None,
) -> dict[str, Any]:
    cal_breakdown = calculate_calibrated_quality(sources, claims, evidence)
    lineage_res = analyze_source_lineage(sources)
    claim_map = {c.id: c.text for c in claims}

    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "investigation": {
            "id": str(investigation.id),
            "question": investigation.question,
            "mode": investigation.mode,
            "status": investigation.status,
            "quality_status": investigation.quality_status,
            "created_at": investigation.created_at.isoformat() if investigation.created_at else None,
        },
        "quality_calibration": {
            "calibrated_tier": cal_breakdown.calibrated_tier,
            "calibrated_score": cal_breakdown.calibrated_score,
            "raw_score": cal_breakdown.raw_score,
            "coverage_score": cal_breakdown.coverage_score,
            "failure_penalty": cal_breakdown.failure_penalty,
            "dimension_breakdown": {
                "empirical_depth": cal_breakdown.empirical_depth,
                "source_credibility": cal_breakdown.source_credibility,
                "methodological_rigor": cal_breakdown.methodological_rigor,
                "consensus_stability": cal_breakdown.consensus_stability,
                "source_independence": cal_breakdown.source_independence,
            },
            "reasons": cal_breakdown.reasons,
            "lineage_clusters_count": len(lineage_res.clusters),
            "effective_independent_count": lineage_res.effective_independent_count,
            "independence_ratio": lineage_res.independence_ratio,
        },
        "evidence_strength": strength.model_dump(mode="json") if strength else None,
        "coverage": coverage.model_dump(mode="json") if coverage else None,
        "claims": [
            {
                "id": str(c.id),
                "text": c.text,
                "priority": c.priority,
                "status": c.status,
                "explanation": c.explanation,
            }
            for c in claims
        ],
        "sources": [
            {
                "id": str(s.id),
                "title": s.title,
                "canonical_url": s.canonical_url,
                "original_url": s.original_url,
                "source_type": s.source_type,
                "canonical_source_type": evaluate_canonical_credibility(
                    url=s.canonical_url or s.original_url,
                    publisher=s.publisher,
                    doi=s.doi,
                    source_type_declared=s.source_type,
                    title=s.title,
                ).source_type.value,
                "verification_status": evaluate_canonical_credibility(
                    url=s.canonical_url or s.original_url,
                    publisher=s.publisher,
                    doi=s.doi,
                    source_type_declared=s.source_type,
                    title=s.title,
                ).verification_status.value,
                "is_peer_reviewed": evaluate_canonical_credibility(
                    url=s.canonical_url or s.original_url,
                    publisher=s.publisher,
                    doi=s.doi,
                    source_type_declared=s.source_type,
                    title=s.title,
                ).is_peer_reviewed,
                "is_primary": evaluate_canonical_credibility(
                    url=s.canonical_url or s.original_url,
                    publisher=s.publisher,
                    doi=s.doi,
                    source_type_declared=s.source_type,
                    title=s.title,
                ).is_primary,
                "publisher": s.publisher,
                "doi": s.doi,
                "publication_date": s.publication_date,
                "relevance_score": s.relevance_score,
                "inclusion_status": s.inclusion_status,
                "open_access_status": s.open_access_status,
            }
            for s in sources
        ],
        "documents": [
            {
                "id": str(d.id),
                "source_id": str(d.source_id),
                "access_level": d.access_level,
                "document_url": d.document_url,
                "version_type": d.version_type,
                "extraction_quality": d.extraction_quality,
            }
            for d in documents
        ],
        "evidence": [
            {
                "id": str(e.id),
                "claim_id": str(e.claim_id) if e.claim_id else None,
                "source_id": str(e.source_id),
                "document_id": str(e.document_id) if e.document_id else None,
                "exact_text": e.exact_text,
                "evidence_type": e.evidence_type,
                "relevance_score": e.relevance_score,
                "entailment": validate_evidence_claim_entailment_heuristic(
                    claim_id=str(e.claim_id or ""),
                    claim_text=claim_map.get(e.claim_id, ""),
                    evidence_id=str(e.id),
                    evidence_text=e.exact_text,
                    surrounding_context=e.surrounding_context,
                ).entailment_classification.value,
                "correlation_vs_causation": validate_evidence_claim_entailment_heuristic(
                    claim_id=str(e.claim_id or ""),
                    claim_text=claim_map.get(e.claim_id, ""),
                    evidence_id=str(e.id),
                    evidence_text=e.exact_text,
                    surrounding_context=e.surrounding_context,
                ).correlation_vs_causation_flag,
                "page_number": e.page_number,
                "section_name": e.section_name,
                "traceable": e.traceable,
            }
            for e in evidence
        ],
        "agent_arguments": [
            {
                "id": str(a.id),
                "claim_id": str(a.claim_id),
                "agent_identifier": a.agent_identifier,
                "argument_type": a.argument_type,
                "text": a.text,
                "evidence_basis": a.evidence_basis,
                "reasoning_summary": a.reasoning_summary,
                "confidence_level": a.confidence_level,
            }
            for a in arguments
        ],
        "debate_rounds": [
            {
                "id": str(d.id),
                "round_number": d.round_number,
                "moderator_summary": d.moderator_summary,
                "unresolved_disagreements": json.loads(d.unresolved_disagreements_json) if d.unresolved_disagreements_json else [],
            }
            for d in debates
        ],
        "adjudication_decisions": [
            {
                "id": str(dec.id),
                "claim_id": str(dec.claim_id),
                "decision": dec.decision,
                "explanation": dec.explanation,
                "unresolved_disagreements": json.loads(dec.unresolved_disagreements_json) if dec.unresolved_disagreements_json else [],
            }
            for dec in decisions
        ],
        "report": {
            "overall_assessment": report.overall_assessment if report else "unverified",
            "executive_summary": report.executive_summary if report else "",
            "evidence_gap": report.evidence_gap if report else None,
            "sections": [
                {
                    "section_type": s.section_type,
                    "title": s.title,
                    "content": s.content,
                }
                for s in sections
            ],
        },
    }


# ---------------------------------------------------------------------------
# 4. STANDALONE INTERACTIVE HTML GRAPH (ZERO CDN / SELF-CONTAINED)
# ---------------------------------------------------------------------------
def generate_standalone_html_graph(
    investigation: Investigation,
    claims: list[Claim],
    sources: list[Source],
    evidence: list[Evidence],
    decisions: list[AdjudicationDecision],
) -> str:
    """Generates 100% self-contained interactive HTML graph file with zero external dependencies."""
    nodes: list[dict[str, Any]] = [
        {
            "id": f"inv-{investigation.id}",
            "type": "investigation",
            "label": investigation.question[:60],
            "title": investigation.question,
            "status": investigation.status,
            "x": 400,
            "y": 300,
            "color": "#4b9dff",
        }
    ]

    edges: list[dict[str, Any]] = []

    # Claims around investigation
    claim_count = len(claims)
    for idx, c in enumerate(claims):
        angle = (2 * math.pi * idx) / max(1, claim_count)
        cx = 400 + int(180 * math.cos(angle))
        cy = 300 + int(180 * math.sin(angle))
        cid = f"claim-{c.id}"
        nodes.append({
            "id": cid,
            "type": "claim",
            "label": f"P{c.priority}: {c.text[:45]}...",
            "title": c.text,
            "status": c.status,
            "x": cx,
            "y": cy,
            "color": "#a855f7",
        })
        edges.append({
            "source": f"inv-{investigation.id}",
            "target": cid,
            "label": "decomposed_into",
        })

    # Evidence and Sources
    src_map = {s.id: s for s in sources}
    for ev_idx, ev in enumerate(evidence[:35]):
        angle = (2 * math.pi * ev_idx) / max(1, min(len(evidence), 35))
        ex = 400 + int(310 * math.cos(angle))
        ey = 300 + int(310 * math.sin(angle))
        eid = f"ev-{ev.id}"
        nodes.append({
            "id": eid,
            "type": "evidence",
            "label": f"[{ev.evidence_type}] {ev.exact_text[:35]}...",
            "title": ev.exact_text,
            "status": ev.evidence_type,
            "x": ex,
            "y": ey,
            "color": (
                "#10b981" if ev.evidence_type in {"supporting", "direct"}
                else "#f43f5e" if ev.evidence_type in {"contradicting", "counter"}
                else "#8b5cf6" if ev.evidence_type == "mitigating"
                else "#06b6d4" if ev.evidence_type == "methodological_limitation"
                else "#eab308" if ev.evidence_type == "contextual"
                else "#64748b"
            ),
        })
        if ev.claim_id:
            edges.append({
                "source": eid,
                "target": f"claim-{ev.claim_id}",
                "label": (
                    "substantiates" if ev.evidence_type in {"supporting", "direct"}
                    else "challenges" if ev.evidence_type in {"contradicting", "counter"}
                    else "mitigates" if ev.evidence_type == "mitigating"
                    else "limits" if ev.evidence_type == "methodological_limitation"
                    else "contextualizes"
                ),
            })
        if ev.source_id in src_map:
            sid = f"src-{ev.source_id}"
            if not any(n["id"] == sid for n in nodes):
                src = src_map[ev.source_id]
                sx = 400 + int(420 * math.cos(angle))
                sy = 300 + int(420 * math.sin(angle))
                nodes.append({
                    "id": sid,
                    "type": "source",
                    "label": src.title[:40],
                    "title": src.title,
                    "status": src.source_type,
                    "x": sx,
                    "y": sy,
                    "color": "#38bdf8",
                })
            edges.append({
                "source": eid,
                "target": sid,
                "label": "extracted_from",
            })

    data_json = json.dumps({"nodes": nodes, "edges": edges})

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NEOMON Interactive Knowledge Graph — {html.escape(investigation.question)}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #080c14; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; height: 100vh; overflow: hidden; }}
    #graph-container {{ flex: 1; position: relative; overflow: hidden; background: radial-gradient(#152033 1px, transparent 1px); background-size: 24px 24px; }}
    #controls {{ position: absolute; top: 16px; left: 16px; z-index: 10; display: flex; gap: 8px; align-items: center; background: rgba(13, 20, 34, 0.9); padding: 8px 12px; border-radius: 8px; border: 1px solid #1e293b; }}
    input[type="text"] {{ background: #080c14; border: 1px solid #334155; color: #fff; padding: 6px 10px; border-radius: 6px; font-size: 12px; outline: none; width: 180px; }}
    button {{ background: #1e293b; border: 1px solid #334155; color: #cbd5e1; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; transition: all 0.15s; }}
    button:hover {{ background: #2563eb; color: #fff; border-color: #2563eb; }}
    #sidebar {{ width: 340px; border-left: 1px solid #1e293b; background: #0d1422; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; }}
    h3 {{ font-size: 14px; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; }}
    .node-title {{ font-size: 15px; font-weight: 600; color: #fff; line-height: 1.4; }}
    .node-badge {{ display: inline-block; padding: 3px 8px; border-radius: 99px; font-size: 11px; font-weight: 600; }}
    .detail-text {{ font-size: 13px; line-height: 1.6; color: #cbd5e1; white-space: pre-wrap; }}
    svg {{ width: 100%; height: 100%; cursor: grab; }}
    svg:active {{ cursor: grabbing; }}
    .node-circle {{ transition: r 0.15s, stroke-width 0.15s; cursor: pointer; }}
    .node-circle:hover {{ stroke: #fff; stroke-width: 3px; }}
    .node-text {{ font-size: 10px; fill: #cbd5e1; pointer-events: none; text-shadow: 0 1px 3px rgba(0,0,0,0.8); }}
    .edge-line {{ stroke: #334155; stroke-width: 1.5px; opacity: 0.6; }}
  </style>
</head>
<body>
  <div id="graph-container">
    <div id="controls">
      <input type="text" id="search" placeholder="Search nodes..." />
      <button onclick="resetZoom()">Reset</button>
      <button onclick="zoomBy(1.2)">+ Zoom</button>
      <button onclick="zoomBy(0.8)">- Zoom</button>
    </div>
    <svg id="svg-canvas">
      <g id="viewport">
        <g id="edges-layer"></g>
        <g id="nodes-layer"></g>
      </g>
    </svg>
  </div>

  <div id="sidebar">
    <h3>NEOMON Knowledge Graph</h3>
    <div id="detail-panel">
      <p style="color: #64748b; font-size: 13px;">Click on any node to inspect grounded evidence and connections.</p>
    </div>
  </div>

  <script id="graph-data" type="application/json">
    {data_json}
  </script>

  <script>
    const data = JSON.parse(document.getElementById('graph-data').textContent);
    const svg = document.getElementById('svg-canvas');
    const viewport = document.getElementById('viewport');
    const nodesLayer = document.getElementById('nodes-layer');
    const edgesLayer = document.getElementById('edges-layer');
    const detailPanel = document.getElementById('detail-panel');

    let scale = 1, panX = 0, panY = 0, isDragging = false, startX, startY;

    function renderGraph() {{
      edgesLayer.innerHTML = '';
      nodesLayer.innerHTML = '';

      data.edges.forEach(edge => {{
        const s = data.nodes.find(n => n.id === edge.source);
        const t = data.nodes.find(n => n.id === edge.target);
        if (!s || !t) return;
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', s.x);
        line.setAttribute('y1', s.y);
        line.setAttribute('x2', t.x);
        line.setAttribute('y2', t.y);
        line.setAttribute('class', 'edge-line');
        edgesLayer.appendChild(line);
      }});

      data.nodes.forEach(node => {{
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('transform', `translate(${{node.x}}, ${{node.y}})`);
        g.onclick = () => selectNode(node);

        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('r', node.type === 'investigation' ? 18 : node.type === 'claim' ? 14 : 10);
        circle.setAttribute('fill', node.color);
        circle.setAttribute('stroke', '#080c14');
        circle.setAttribute('stroke-width', '2px');
        circle.setAttribute('class', 'node-circle');
        g.appendChild(circle);

        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', 14);
        text.setAttribute('y', 4);
        text.setAttribute('class', 'node-text');
        text.textContent = node.label;
        g.appendChild(text);

        nodesLayer.appendChild(g);
      }});
    }}

    function selectNode(node) {{
      detailPanel.innerHTML = `
        <div class="node-badge" style="background: ${{node.color}}22; color: ${{node.color}}; border: 1px solid ${{node.color}}">
          ${{node.type.toUpperCase()}}
        </div>
        <div class="node-title">${{node.title}}</div>
        <div style="font-size: 11px; color: #64748b;">Status: ${{node.status || 'verified'}}</div>
        <div class="detail-text">${{node.title}}</div>
      `;
    }}

    function updateTransform() {{
      viewport.setAttribute('transform', `translate(${{panX}}, ${{panY}}) scale(${{scale}})`);
    }}

    function zoomBy(factor) {{
      scale *= factor;
      updateTransform();
    }}

    function resetZoom() {{
      scale = 1; panX = 50; panY = 50;
      updateTransform();
    }}

    svg.onmousedown = (e) => {{
      isDragging = true;
      startX = e.clientX - panX;
      startY = e.clientY - panY;
    }};

    window.onmousemove = (e) => {{
      if (!isDragging) return;
      panX = e.clientX - startX;
      panY = e.clientY - startY;
      updateTransform();
    }};

    window.onmouseup = () => {{ isDragging = false; }};

    svg.onwheel = (e) => {{
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
      zoomBy(zoomFactor);
    }};

    document.getElementById('search').oninput = (e) => {{
      const q = e.target.value.toLowerCase();
      const circles = nodesLayer.querySelectorAll('.node-circle');
      data.nodes.forEach((n, i) => {{
        if (!q || n.title.toLowerCase().includes(q) || n.label.toLowerCase().includes(q)) {{
          circles[i].setAttribute('opacity', '1');
          circles[i].setAttribute('stroke-width', q ? '3px' : '2px');
        }} else {{
          circles[i].setAttribute('opacity', '0.2');
        }}
      }});
    }};

    resetZoom();
    renderGraph();
  </script>
</body>
</html>"""
    return html_content


# ---------------------------------------------------------------------------
# 5. SVG VECTOR GRAPH EXPORT
# ---------------------------------------------------------------------------
def generate_svg_graph_export(
    investigation: Investigation,
    claims: list[Claim],
    sources: list[Source],
    evidence: list[Evidence],
) -> str:
    """Generates standard SVG vector graphic export of the knowledge graph."""
    width = 1400
    height = 900
    cx = width // 2
    cy = height // 2

    svg_elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        f'<rect width="{width}" height="{height}" fill="#080c14" />',
        '<!-- Defs for markers -->',
        '<defs>',
        '  <marker id="arrow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
        '    <path d="M 0 0 L 10 5 L 0 10 z" fill="#475569" />',
        '  </marker>',
        '</defs>',
    ]

    # Legend & Title
    svg_elements.extend([
        f'<text x="40" y="50" font-family="sans-serif" font-size="20" font-weight="bold" fill="#f8fafc">NEOMON Knowledge Graph: {html.escape(investigation.question[:70])}</text>',
        f'<text x="40" y="75" font-family="sans-serif" font-size="12" fill="#64748b">Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} | Grounded Traceability</text>',
        '<g transform="translate(40, 100)">',
        '  <circle cx="10" cy="10" r="8" fill="#4b9dff" /><text x="26" y="14" font-family="sans-serif" font-size="11" fill="#94a3b8">Investigation</text>',
        '  <circle cx="130" cy="10" r="8" fill="#a855f7" /><text x="146" y="14" font-family="sans-serif" font-size="11" fill="#94a3b8">Claim</text>',
        '  <circle cx="210" cy="10" r="8" fill="#10b981" /><text x="226" y="14" font-family="sans-serif" font-size="11" fill="#94a3b8">Supporting Ev.</text>',
        '  <circle cx="330" cy="10" r="8" fill="#f43f5e" /><text x="346" y="14" font-family="sans-serif" font-size="11" fill="#94a3b8">Contradicting Ev.</text>',
        '  <circle cx="470" cy="10" r="8" fill="#38bdf8" /><text x="486" y="14" font-family="sans-serif" font-size="11" fill="#94a3b8">Source</text>',
        '</g>',
    ])

    # Position claims in a ring
    claim_positions = {}
    claim_count = len(claims)
    for idx, c in enumerate(claims):
        angle = (2 * math.pi * idx) / max(1, claim_count)
        x = cx + int(240 * math.cos(angle))
        y = cy + int(240 * math.sin(angle))
        claim_positions[c.id] = (x, y)
        # Edge from center
        svg_elements.append(f'<line x1="{cx}" y1="{cy}" x2="{x}" y2="{y}" stroke="#334155" stroke-width="1.5" marker-end="url(#arrow)" />')

    # Position evidence in outer ring
    for ev_idx, ev in enumerate(evidence[:30]):
        angle = (2 * math.pi * ev_idx) / max(1, min(len(evidence), 30))
        ex = cx + int(420 * math.cos(angle))
        ey = cy + int(420 * math.sin(angle))
        col = (
            "#10b981" if ev.evidence_type in {"supporting", "direct"}
            else "#f43f5e" if ev.evidence_type in {"contradicting", "counter"}
            else "#8b5cf6" if ev.evidence_type == "mitigating"
            else "#06b6d4" if ev.evidence_type == "methodological_limitation"
            else "#eab308" if ev.evidence_type == "contextual"
            else "#64748b"
        )
        if ev.claim_id and ev.claim_id in claim_positions:
            tx, ty = claim_positions[ev.claim_id]
            svg_elements.append(f'<line x1="{ex}" y1="{ey}" x2="{tx}" y2="{ty}" stroke="#1e293b" stroke-width="1.2" stroke-dasharray="3,3" />')
        svg_elements.append(f'<circle cx="{ex}" cy="{ey}" r="6" fill="{col}" stroke="#080c14" stroke-width="1.5" />')

    # Draw claim nodes
    for c in claims:
        x, y = claim_positions[c.id]
        label = html.escape(f"P{c.priority}: {c.text[:28]}...")
        svg_elements.append(f'<circle cx="{x}" cy="{y}" r="12" fill="#a855f7" stroke="#080c14" stroke-width="2" />')
        svg_elements.append(f'<text x="{x + 16}" y="{y + 4}" font-family="sans-serif" font-size="10" fill="#e2e8f0">{label}</text>')

    # Central investigation node
    svg_elements.append(f'<circle cx="{cx}" cy="{cy}" r="18" fill="#4b9dff" stroke="#1d4ed8" stroke-width="3" />')
    svg_elements.append(f'<text x="{cx + 24}" y="{cy + 5}" font-family="sans-serif" font-size="12" font-weight="bold" fill="#fff">Investigation Hub</text>')

    svg_elements.append('</svg>')
    return "\n".join(svg_elements)


# ---------------------------------------------------------------------------
# 6. JSON-LD LINKED DATA EXPORT
# ---------------------------------------------------------------------------
def generate_json_ld_export(
    investigation: Investigation,
    report: ResearchReport | None,
    claims: list[Claim],
    sources: list[Source],
    evidence: list[Evidence],
    decisions: list[AdjudicationDecision],
) -> dict[str, Any]:
    """Generates schema.org compliant JSON-LD Linked Data payload."""
    citations = []
    for s in sources:
        citations.append({
            "@type": "ScholarlyArticle" if "academic" in (s.source_type or "").lower() else "CreativeWork",
            "name": s.title,
            "url": s.canonical_url or s.original_url,
            "publisher": {"@type": "Organization", "name": s.publisher} if s.publisher else None,
            "identifier": s.doi if s.doi else None,
        })

    claim_reviews = []
    for c in claims:
        dec = next((d for d in decisions if d.claim_id == c.id), None)
        claim_reviews.append({
            "@type": "ClaimReview",
            "claimReviewed": c.text,
            "reviewRating": {
                "@type": "Rating",
                "alternateName": dec.decision if dec else c.status,
                "ratingExplanation": dec.explanation if dec else c.explanation,
            },
        })

    cal_breakdown = calculate_calibrated_quality(sources, claims, evidence)

    return {
        "@context": {
            "@vocab": "https://schema.org/",
            "neomon": "https://neomon.dev/ontology/",
        },
        "@type": "ScholarlyArticle",
        "headline": investigation.question,
        "description": report.executive_summary if report else investigation.question,
        "dateCreated": investigation.created_at.isoformat() if investigation.created_at else None,
        "scientificQuality": {
            "@type": "QualityAssessment",
            "calibratedTier": cal_breakdown.calibrated_tier,
            "calibratedScore": cal_breakdown.calibrated_score,
            "rawScore": cal_breakdown.raw_score,
            "coverageScore": cal_breakdown.coverage_score,
            "failurePenalty": cal_breakdown.failure_penalty,
        },
        "creator": {
            "@type": "Organization",
            "name": "NEOMON Multi-Agent Research Intelligence",
            "url": "https://neomon.dev",
        },
        "citation": [c for c in citations if c],
        "about": claim_reviews,
    }


# ---------------------------------------------------------------------------
# 7. EVIDENCE & SOURCE CSV DATASETS
# ---------------------------------------------------------------------------
def generate_evidence_csv(
    claims: list[Claim],
    sources: list[Source],
    evidence: list[Evidence],
) -> str:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "evidence_id",
        "claim_id",
        "claim_text",
        "source_id",
        "source_title",
        "source_url",
        "exact_text",
        "evidence_type",
        "relevance_score",
        "entailment_classification",
        "correlation_vs_causation",
        "missing_inferential_steps",
        "page_number",
        "section_name",
        "traceable",
        "verified_provenance",
    ])

    claim_map = {c.id: c.text for c in claims}
    source_map = {s.id: (s.title, s.canonical_url or s.original_url) for s in sources}

    for ev in evidence:
        c_text = claim_map.get(ev.claim_id, "")
        s_title, s_url = source_map.get(ev.source_id, ("", ""))
        has_unresolved = "[UNRESOLVED PROVENANCE]" in (ev.relevance_reason or "")
        verified_prov = bool(ev.traceable and not has_unresolved)

        val = validate_evidence_claim_entailment_heuristic(
            claim_id=str(ev.claim_id or ""),
            claim_text=c_text,
            evidence_id=str(ev.id),
            evidence_text=ev.exact_text,
            surrounding_context=ev.surrounding_context,
        )

        writer.writerow([
            _escape_csv(ev.id),
            _escape_csv(ev.claim_id),
            _escape_csv(c_text),
            _escape_csv(ev.source_id),
            _escape_csv(s_title),
            _escape_csv(s_url),
            _escape_csv(ev.exact_text),
            _escape_csv(ev.evidence_type),
            _escape_csv(ev.relevance_score),
            _escape_csv(val.entailment_classification.value),
            _escape_csv(val.correlation_vs_causation_flag),
            _escape_csv("; ".join(val.missing_inferential_steps)),
            _escape_csv(ev.page_number),
            _escape_csv(ev.section_name),
            _escape_csv(ev.traceable),
            _escape_csv(verified_prov),
        ])

    return output.getvalue()


def generate_sources_csv(sources: list[Source]) -> str:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "source_id",
        "title",
        "canonical_url",
        "original_url",
        "source_type",
        "canonical_source_type",
        "verification_status",
        "is_peer_reviewed",
        "is_primary",
        "publisher",
        "doi",
        "publication_date",
        "relevance_score",
        "credibility_tier",
        "credibility_score",
        "inclusion_status",
        "open_access_status",
    ])

    for s in sources:
        cred = assess_source_credibility(
            publisher=s.publisher,
            url=s.canonical_url or s.original_url,
            doi=s.doi,
            source_type_declared=s.source_type,
            publication_date=s.publication_date,
        )
        canonical = evaluate_canonical_credibility(
            url=s.canonical_url or s.original_url,
            publisher=s.publisher,
            doi=s.doi,
            source_type_declared=s.source_type,
            title=s.title,
        )
        writer.writerow([
            _escape_csv(s.id),
            _escape_csv(s.title),
            _escape_csv(s.canonical_url),
            _escape_csv(s.original_url),
            _escape_csv(s.source_type),
            _escape_csv(canonical.source_type.value),
            _escape_csv(canonical.verification_status.value),
            _escape_csv(canonical.is_peer_reviewed),
            _escape_csv(canonical.is_primary),
            _escape_csv(s.publisher),
            _escape_csv(s.doi),
            _escape_csv(s.publication_date),
            _escape_csv(s.relevance_score),
            _escape_csv(cred.credibility_tier),
            _escape_csv(cred.credibility_score),
            _escape_csv(s.inclusion_status),
            _escape_csv(s.open_access_status),
        ])

    return output.getvalue()
