# Feature Specification: Report Intelligence & Multi-Format Knowledge Export

## 1. Feature Overview
The **Report Intelligence & Knowledge Export Engine** synthesizes completed research investigations into publication-grade dossiers. It automatically structures findings into standard academic sections (Executive Summary, Background, Methodology Audit, Evidence & Claims, Adversarial Debate Findings, Identified Gaps, and References), manages **Report Versioning**, and provides multi-format export capabilities (**Markdown**, **JSON**, and **PDF / Print HTML**).

## 2. Purpose and Problem Solved
Transforming disparate search queries, evidence snippets, and agent arguments into a polished, coherent report typically takes hours of manual formatting. The Report Intelligence engine automates this synthesis while preserving total auditability:
- Structures complex multi-agent debates into clean, executive-level prose.
- Automatically compiles formatted bibliographic reference lists with DOIs and URLs.
- Version-controls reports (`v1`, `v2`, `v3`) as new evidence is acquired.
- Enables single-click export for sharing with external collaborators, grant committees, or archival repositories.

## 3. Where Users Access It
- **In-Investigation**: "Export & Reports" menu on `/investigations/[id]`.
- **Download Buttons**:
  - `Export Markdown (.md)`
  - `Export Structured JSON (.json)`
  - `Print / PDF View`
- **Report Versions**: Version history dropdown on `/investigations/[id]`.

## 4. Step-by-Step User Workflow
1. Navigate to a completed investigation on `/investigations/[id]`.
2. Click the **"Export & Reports"** dropdown in the top action bar.
3. Choose an export option:
   - **Download Markdown**: Generates a clean, GitHub-flavored Markdown file containing executive summary, claims table, debate transcripts, and citations.
   - **Download JSON**: Generates a full machine-readable JSON dossier containing raw evidence passages, confidence scores, SHA-256 hashes, and agent executions.
   - **Print / PDF Dossier**: Opens a print-optimized, publication-formatted view suitable for browser PDF printing.
4. Review **Report Sections**:
   - Inspect individual structured sections: Executive Summary, Evidence Matrix, Adversarial Analysis, Limitations.
5. Create a **New Report Version**:
   - If new evidence was added, click **"Generate New Report Version"** to increment the version number and archive previous versions.

## 5. How the Feature Works Internally
1. The `app.analysis.report_service`:
   - Aggregates all claims, evidence, sources, debate rounds, methodology findings, and calibrations.
   - Organizes content into standardized sections stored in `report_sections`.
   - Computes an overall evidence strength tier (`strong`, `moderate`, `preliminary`).
2. Persists the version record in `report_versions` linked to `investigations.id`.
3. When an export format is requested:
   - **Markdown Generator**: Converts section trees into formatted Markdown headers, blockquotes, and tables.
   - **JSON Serializer**: Dumps the complete `InvestigationDossier` Pydantic model with ISO-8601 timestamps and checksums.
   - **HTML / PDF Formatter**: Renders a clean typographic layout with academic CSS stylesheets.
4. Endpoints return payloads with `Content-Disposition: attachment; filename="neomon_investigation_<id>.md"`.

## 6. Relevant Frontend Pages and Components
- `app/investigations/[id]/page.tsx`: Houses the report version selector and export buttons.
- `lib/api.ts`: Handles blob downloads for exported files.

## 7. Relevant Backend Routes and Endpoints
- `GET /api/v1/research/export/investigations/{id}/markdown`: Generates and downloads Markdown dossier.
- `GET /api/v1/research/export/investigations/{id}/json`: Generates and downloads full JSON dataset.
- `GET /api/v1/research/investigations/{id}/reports`: Lists all versioned reports for an investigation.
- `POST /api/v1/research/investigations/{id}/reports/generate`: Compiles a new report version.

## 8. Relevant Services and Agents
- `app.analysis.report_service.ReportIntelligenceEngine`: Document structure and version manager.
- `app.agents.synthesizer`: Synthesizes section prose and executive summaries.

## 9. Database Tables and Relationships
- `report_versions`: Stores `id`, `investigation_id`, `job_id`, `version_number`, `executive_summary`, `overall_assessment`, `evidence_strength_score`, `evidence_strength_tier`, `sections_json`, `created_at`.
- `report_sections`: Normalized section items linked to `report_versions`.
- `research_reports`: High-level summary entity.

## 10. Inputs and Outputs
- **Export Trigger**: `GET /api/v1/research/export/investigations/{id}/markdown`
- **Output**: File stream with MIME type `text/markdown` and raw content containing:
  - Document Title & Metadata
  - Executive Summary & Calibrated Quality Tier
  - Claims & Grounded Citations Table
  - Methodology Audit & Limitations
  - Advocate vs. Skeptic Debate Highlights
  - References List (DOIs, Publishers, Canonical URLs)

## 11. AI Provider Dependencies
Optional. Deterministic rule-based formatting compiles structured reports from database records; AI providers enhance narrative transitions and executive summaries.

## 12. External API Dependencies
None.

## 13. Configuration Requirements
- `NEOMON_DATABASE_URL`: Relational database connection.

## 14. Error Handling and Limitations
- **Partial Investigations**: If an investigation is still in progress when exported, the report clearly watermarks sections as `[Preliminary — Investigation in Progress]`.
- **Character Encoding**: Enforces UTF-8 encoding across all exports to preserve scientific notation, Greek letters ($\alpha, \beta, \gamma$), and mathematical formulas.

## 15. Security and Permission Considerations
- Exporting requires workspace read permissions.
- Secret keys and internal database IDs are stripped from exported files to prevent infrastructure information disclosure.

## 16. Related Features and Dependencies
- **Investigations** (`docs/features/investigations.md`): Provides source data for report compilation.
- **Autonomous Workflows** (`docs/features/autonomous-workflows.md`): Automatically generates a report version upon workflow completion.

## 17. Relevant Tests and How to Run Them
- **Backend Tests**:
  - `python -m pytest backend/tests/test_report_intelligence.py -q`
- **Frontend Tests**:
  - `node --test tests/workspace-ui.test.mjs`
