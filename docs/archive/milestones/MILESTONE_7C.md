# NEOMON Milestone 7C — Knowledge Export & Reproducibility

## Executive Overview

Milestone 7C completes NEOMON's core mission: transforming multi-agent research from ephemeral generation into verifiable, archivable, and fully reproducible scientific intelligence.

**Tagline:** "Every claim is questioned. Every source is traced. Every conclusion is earned."

In high-stakes research, scientific inquiry, and intelligence analysis, conclusions cannot exist solely inside an active web application. They must be exportable in formats suitable for peer review, long-term archival, programmatic ingestion, and air-gapped offline analysis. Milestone 7C delivers a modular, pure-Python export service supporting 8 distinct standard formats, backed by dedicated REST endpoints and an integrated export panel in the web interface.

---

## 1. The 8 Standard Export Formats

### 1. Research Report Markdown (`.md`)
- **MIME Type:** `text/markdown; charset=utf-8`
- **Route:** `GET /api/v1/research/investigations/{id}/export/markdown`
- **Features:**
  - Standard YAML frontmatter containing investigation ID, title, research question, generation timestamp, evidence strength score, and tier.
  - Complete Table of Contents with Markdown anchor links.
  - All 18 structured research sections authored in Milestone 7B.
  - Blockquoted evidence excerpts with explicit page, section, and extraction method citations.
  - Comprehensive references directory cataloging all discovered academic and institutional sources.

### 2. Paginated Document PDF (`.pdf`)
- **MIME Type:** `application/pdf`
- **Route:** `GET /api/v1/research/investigations/{id}/export/pdf`
- **Implementation Architecture:**
  - **Pure Python PDF 1.4 Generation**: Generated entirely via standard Python byte manipulation and font stream assembly in `export_service.py`.
  - **Zero Heavy Dependencies**: Operates without headless browsers (Puppeteer/Chromium), without external paid SaaS APIs, and without heavy compiled binary extensions (ReportLab/WeasyPrint).
  - **Features**:
    - Proper PDF document header (`%PDF-1.4`), font dictionaries (`Helvetica`, `Helvetica-Bold`), content streams, and cross-reference (`xref`) table.
    - Title banner with investigation question and evidence strength breakdown box.
    - Running headers, page dividers, and dynamic page numbering (`Page X of Y`).
    - Deterministic line-wrapping algorithm preserving margins and layout integrity across multi-page outputs.
    - Verified compliant and readable via `pypdf.PdfReader`.

### 3. Machine-Readable Research Snapshot (`.json`)
- **MIME Type:** `application/json; charset=utf-8`
- **Route:** `GET /api/v1/research/investigations/{id}/export/json`
- **Features:**
  - Standardized JSON schema (`schema_version: "1.0.0"`).
  - Exhaustive serialization of the investigation graph:
    - Root investigation metadata and parameters.
    - All atomic research claims with status and explanations.
    - Discovered sources with publisher, DOI, and open access metadata.
    - Full-text document records and storage locations.
    - Extracted evidence passages with relevance scores and claim associations.
    - Advocate and Skeptic agent debate arguments.
    - Conflict adjudicator decisions and compromise rationales.
    - Multi-dimensional evidence strength evaluation.
    - Agent execution telemetry and test coverage summary.

### 4. Standalone Interactive Knowledge Graph (`.html`)
- **MIME Type:** `text/html; charset=utf-8`
- **Route:** `GET /api/v1/research/investigations/{id}/export/html-graph`
- **Features:**
  - **Zero External CDN Dependencies**: Works completely offline in air-gapped environments without loading scripts, fonts, or stylesheets from external CDNs.
  - **Embedded Vector Canvas**: SVG-based force/hierarchical rendering of claims, evidence, and sources.
  - **Interactive Controls**:
    - Smooth pan (pointer drag on background) and zoom (mouse wheel / slider).
    - Draggable nodes with real-time edge realignment.
    - Live text search highlighting matched nodes and dimming unrelated entities.
    - Entity-type filter toggles (claims, evidence, sources).
    - Fit-to-screen and reset layout buttons.
    - Interactive inspection side drawer displaying full passage text, relevance score, and source provenance upon node selection.

### 5. Vector Knowledge Graph (`.svg`)
- **MIME Type:** `image/svg+xml; charset=utf-8`
- **Route:** `GET /api/v1/research/investigations/{id}/export/svg`
- **Features:**
  - High-resolution standalone vector graphic (1200x800 viewBox) suitable for publication figures and vector illustration editors (Inkscape, Illustrator).
  - Distinct color-coded nodes: Claims (Blue/Purple), Evidence (Green/Orange), Sources (Cyan).
  - Directed relationship marker arrows (`#arrow-supports`, `#arrow-contradicts`, `#arrow-source`).
  - Integrated visual legend and title watermark.

### 6. Semantic Linked Data (`.jsonld`)
- **MIME Type:** `application/ld+json; charset=utf-8`
- **Route:** `GET /api/v1/research/investigations/{id}/export/json-ld`
- **Features:**
  - Compliant with **Schema.org** vocabularies for academic indexing and open science discovery.
  - Root entity: `ScholarlyArticle` with headline, description, author agent network, and dates.
  - Nested `ClaimReview` entities representing adjudicated claims, verdicts, and evidence citations.
  - Fully resolvable `@context: "https://schema.org"`.

### 7. Evidence Dataset (`.csv`)
- **MIME Type:** `text/csv; charset=utf-8`
- **Route:** `GET /api/v1/research/investigations/{id}/export/evidence-csv`
- **Features:**
  - Strict RFC 4180 CSV compliance with escaped multiline passage strings.
  - Tabular schema:
    `evidence_id, claim_id, source_id, source_title, evidence_type, relevance_score, extraction_method, page_number, section_name, exact_text, surrounding_context`
  - Ready for import into statistical packages (R, Python pandas, Stata) for quantitative meta-analysis.

### 8. Sources Catalog (`.csv`)
- **MIME Type:** `text/csv; charset=utf-8`
- **Route:** `GET /api/v1/research/investigations/{id}/export/sources-csv`
- **Features:**
  - Strict RFC 4180 CSV compliance.
  - Tabular schema:
    `source_id, title, authors, publication_date, publisher, doi, original_url, source_type, open_access_status, inclusion_status, extraction_quality, relevance_score, rejection_reason`
  - Enables audit of academic literature discovery and institutional source diversity.

---

## 2. Security, Redaction & Integrity Guarantees

1. **Secret & Credential Sanitization**:
   - The export generator explicitly scrubs all internal API keys, Bearer tokens, LLM endpoint authorization headers, and environment paths.
   - Provider configs in JSON snapshots include only `provider_kind` and `model` identifiers.
2. **Reproducibility Guarantee**:
   - Every export contains cryptographic or deterministic IDs linking claims to evidence to sources.
   - No synthetic or hallucinated citation records are injected; only persisted database entities are exported.
3. **HTTP Content-Disposition**:
   - All export endpoints return `Content-Disposition: attachment; filename="neomon_{investigation_id}_{format}.{ext}"` headers for immediate browser file downloads.

---

## 3. Web Workspace Integration

In `app/investigations/[id]/page.tsx`:
- Added **Export Knowledge (8 Formats) ⤓** toggle button in the investigation quick-action bar.
- Responsive **Knowledge Export & Reproducibility** panel featuring 8 downloadable cards:
  - Formatted file type badges (`.MD`, `.PDF`, `.JSON`, `.HTML`, `.SVG`, `.JSONLD`, `.CSV`).
  - Clear functional descriptions for each format.
  - Direct download links pointing to backend export endpoints with browser download triggers.

---

## 4. Verification & Testing

- **Backend Unit & Integration Tests (`backend/tests/test_export_service.py`)**:
  - `test_markdown_export`: Verifies frontmatter, sections, and references.
  - `test_pure_python_pdf_export`: Validates PDF 1.4 byte structure, xref tables, and multi-page text rendering via `pypdf.PdfReader`.
  - `test_structured_json_export`: Validates schema structure, claims, evidence, and coverage objects.
  - `test_standalone_html_graph`: Verifies zero CDN dependencies, SVG canvas elements, and interactive script functions.
  - `test_svg_graph_export`: Validates SVG nodes, marker tags, and visual legend.
  - `test_json_ld_export`: Validates Schema.org `ScholarlyArticle` and `ClaimReview` structure.
  - `test_csv_exports`: Validates RFC 4180 column headers and rows for evidence and sources.
  - `test_export_router_endpoints`: Tests all 9 HTTP endpoints (`/manifest`, `/markdown`, `/pdf`, `/json`, `/html-graph`, `/svg`, `/json-ld`, `/evidence-csv`, `/sources-csv`).
- **Frontend Verification (`tests/workspace-ui.test.mjs`)**:
  - Validates export panel presence, format cards, and download URL structures.
  - `npm test`: 8 passed, 0 failed.
  - `npx tsc --noEmit`: 0 errors.
  - `npm run build`: Static & dynamic route compilation completed successfully.
