# NEOMON — Comprehensive Functionality Deep Dive
**Detailed Technical Reference Across All System Features**

---

## 1. Investigation Management

| Category | Technical Specification |
|---|---|
| **Purpose** | Provides the top-level container for scientific research, tracking question scope, lifecycle state, associated sources, claims, multi-agent debates, and generated reports. |
| **User Interaction** | User clicks **"New Investigation"**, enters a research question, selects an AI provider (OpenAI, OpenRouter, Ollama, LM Studio), configures concurrency/debate rounds, and launches the workflow. User can view previous investigations in the history table or search investigations. |
| **Internal Process** | Fast-path API `POST /api/v1/research/investigations` creates an `Investigation` record with state `queued`. If workspace ID is present in context, associates the investigation with the workspace. Enqueues the investigation execution in `AnalysisManager`. |
| **AI Involvement** | None at creation; initializes provider parameters for downstream specialist agents. |
| **Data Flow** | **In:** Question string, workspace UUID, provider settings, concurrency limits.<br>**Out:** Persisted `Investigation` entity (UUID, created_at, status). |
| **Output** | Real-time redirect to `/investigations/[id]`, displaying the live investigation dashboard. |
| **Failure Handling** | Validation errors (e.g. question < 5 chars) return HTTP 422 with exact field error. Database connection failures return HTTP 503. |
| **Current Status** | **Implemented and Verified** (Covered in `test_api.py`, `test_workspace_api.py`, and UI tests). |

---

## 2. Research Planning & Claim Decomposition

| Category | Technical Specification |
|---|---|
| **Purpose** | Deconstructs broad, ambiguous research questions into discrete, atomic, falsifiable scientific claims that can be independently queried and validated. |
| **User Interaction** | Automatic upon investigation start. User watches the **Intelligence Planner** agent card activate in the live workspace. |
| **Internal Process** | `backend/app/analysis/service.py` instantiates `intelligence_planner`. The agent analyzes semantic syntax, identifies core subjects, variables, and potential interventions, and emits 1 to 5 `ClaimPayload` objects. Each claim has a priority (1-5), search objectives, and expected evidence categories (`supporting`, `contradicting`, `contextual`). The claims are validated and persisted to the `Claim` database table. |
| **AI Involvement** | Calls configured LLM with structured Pydantic schema `PlannerPayload`. If no AI provider is configured or network is unavailable, executes deterministic rule-based syntactic decomposition (`_rule_based_claims()`). |
| **Data Flow** | **In:** Research question string.<br>**Out:** Array of validated `Claim` records with UUIDs, text, priority, and search objectives. |
| **Output** | Claims appear as interactive cards in the UI, displaying progress meters and associated evidence counts. |
| **Failure Handling** | If LLM output fails schema validation, retries once. If still failing, automatically falls back to deterministic rule-based decomposition without halting the investigation. |
| **Current Status** | **Implemented and Verified** (Tested in `test_analysis_engine.py` and `test_structured_output.py`). |

---

## 3. Academic Source Discovery

| Category | Technical Specification |
|---|---|
| **Purpose** | Discovers high-impact, peer-reviewed literature, preprints, and real-time open-access sources across global scholarly indexes. |
| **User Interaction** | Configured in investigation settings (toggle academic APIs: Crossref, OpenAlex, arXiv, Unpaywall, Tavily). User sees real-time source acquisition feed. |
| **Internal Process** | `backend/app/research/service.py` and `providers.py`: Formulates optimized boolean search queries from claim objectives. Asynchronously queries:
1. **Crossref**: Resolves DOIs, journal venues, publication years, and publisher metadata.
2. **OpenAlex**: Retrieves citation counts, open-access status, author affiliations, and concepts.
3. **arXiv**: Discovers mathematical, computational, and physical science preprints.
4. **Unpaywall**: Locates legal, open-access full-text PDF and repository URLs.
5. **Tavily**: Fetches real-time web articles, scientific press releases, and technical reports. Persists entries in `Source` and `ResearchQuery` tables. |
| **AI Involvement** | LLM-assisted query planner generates synonym expansions; API retrieval itself is direct HTTP REST. |
| **Data Flow** | **In:** Search objective strings.<br>**Out:** Persisted `Source` entities (DOI, title, authors, venue, publication year, URL, citation count). |
| **Output** | Interactive Source Intelligence table displaying journal prestige badges, open-access status, and raw metadata. |
| **Failure Handling** | Individual provider failures (e.g. arXiv timeout, Crossref 429) trigger circuit breakers; investigation continues with remaining accessible providers. |
| **Current Status** | **Implemented and Verified** (Tested in `test_research_engine.py`, `test_tavily_provider.py`). |

---

## 4. Evidence Retrieval & Passage Extraction

| Category | Technical Specification |
|---|---|
| **Purpose** | Downloads full-text documents, removes navigational web boilerplate, extracts clean text, and identifies high-density empirical evidence passages. |
| **User Interaction** | Transparently executed during the "researching" phase. User can view extracted evidence in the **Evidence Explorer** tab. |
| **Internal Process** | `backend/app/research/retrieval.py` and `evidence.py`:
1. Validates host IP against SSRF blocklist (blocking loopback/private ranges).
2. Fetches HTML/text with custom streaming HTTP client.
3. Custom `HTMLParser` strips non-content tags (`nav`, `header`, `footer`, `script`, `style`).
4. `extract_evidence()` splits text into sentences, filters boilerplate ("cookie policy", "terms of use"), detects outcome signals (`_has_outcome_signal()`), and computes confidence scores.
5. Persists verbatim slices in `Evidence` table with start/end character offsets linked to parent `Document` and `Source`. |
| **AI Involvement** | None (pure deterministic NLP parser for guaranteed speed and zero token overhead). |
| **Data Flow** | **In:** Target URLs from discovered sources.<br>**Out:** `Document` records (full clean text, SHA-256 hash) and `Evidence` records (exact text slice, confidence, evidence_type). |
| **Output** | Verbatim passages rendered with citation tooltips and source verification badges. |
| **Failure Handling** | If document download fails (403, paywall), records `retrieval_failed` on document. System automatically falls back to published abstract from OpenAlex/Crossref. |
| **Current Status** | **Implemented and Verified** (Tested in `test_research_engine.py`, `test_security_audit.py`). |

---

## 5. Multi-Agent Intelligence Engine

The core dialectical inference engine executes across 8 specialized agent roles:

```
+----------------------------------------------------------------------------------------------------+
|                                    MULTI-AGENT SPECIALIST ROLES                                    |
+----------------------+-----------------------------------------------------------------------------+
| AGENT                | ROLE & COGNITIVE MANDATE                                                    |
+----------------------+-----------------------------------------------------------------------------+
| Intelligence Planner | Deconstructs questions into atomic claims, priorities, and search vectors.  |
| Advocate             | Constructs strongest affirmative argument grounded in verified evidence.    |
| Skeptic              | Challenges assertions, exposes methodological limits, and finds null findings|
| Methodology Auditor  | Audits sample sizes, control groups, confounding variables, and bias risk.  |
| Source Intelligence  | Evaluates peer-review tier, publisher credibility, and author pedigree.     |
| Citation Genealogy   | Traces citation loops, foundational parent papers, and derivative studies.  |
| Temporal Intelligence| Evaluates chronological consensus drift, paradigm shifts, and obsolescence. |
| Debate Moderator     | Synthesizes tensions across agent outputs; chairs structured debate rounds. |
| Conflict Adjudicator | Renders calibrated claim verdicts (supported, contradictory, inconclusive). |
| Report Intelligence  | Synthesizes all findings into 18 structured, auditable report sections.     |
+----------------------+-----------------------------------------------------------------------------+
```

### Specialist Breakdown:
- **Advocate (`app/agents/advocate.py`)**:
  - *Input*: Claim text, associated evidence passages, source metadata.
  - *Processing*: Identifies positive empirical outcomes, statistical correlations, and corroborating citations.
  - *Output*: `ArgumentPayload` with `argument_type="supporting"`, citing exact evidence UUIDs.
  - *Integrity Guard*: Must cite existing evidence UUIDs; phantom IDs trigger automatic rejection.
- **Skeptic (`app/agents/skeptic.py`)**:
  - *Input*: Claim text, associated evidence passages, counter-claims.
  - *Processing*: Searches for conflicting statistics, unaddressed edge cases, lack of generalizability, and alternative explanations.
  - *Output*: `ArgumentPayload` with `argument_type="contradicting"`.
- **Methodology Auditor (`app/agents/methodology_auditor.py`)**:
  - *Input*: Full evidence corpus and study abstracts.
  - *Processing*: Evaluates study design (RCT vs observational vs case study), cohort sizes, p-hacking risks, and selection biases.
  - *Output*: `ArgumentPayload` with `argument_type="methodological_criticism"`.
- **Debate Moderator (`app/agents/debate_moderator.py`)**:
  - *Input*: All arguments submitted for each claim in the current round.
  - *Processing*: Identifies direct contradictions between Advocate and Skeptic, tracks whether criticisms have been answered, and logs unresolved disagreements.
  - *Output*: `DebateRound` record with summary of tensions and requested follow-up evidence.
- **Conflict Adjudicator (`app/agents/conflict_adjudicator.py`)**:
  - *Input*: Cumulative debate history and evidence weight.
  - *Processing*: Renders final verdict per claim (`strongly_supported`, `moderately_supported`, `weakly_supported`, `contradictory`, `insufficient_evidence`), explains reasoning, and details residual uncertainties.
  - *Output*: Persisted `AdjudicationDecision` record.
- **Current Status**: **Implemented and Verified** (Tested in `test_analysis_engine.py`, `test_agents.py`, `test_structured_output.py`).

---

## 6. Scientific Integrity & Reliability Layer (Milestone 12)

NEOMON implements five distinct scientific verification mechanisms:

### 6.1 Eight-Class Evidence Verification (`EvidenceVerificationService`)
Evaluates the relationship between an evidence passage and a claim:
1. `directly_supports`: Passage contains empirical finding proving claim.
2. `partially_supports`: Supports a subset of claim conditions.
3. `contradicts`: Empirical finding contradicts claim.
4. `contextual_background`: Background information, not proof.
5. `methodological_context`: Describes test instruments or setup.
6. `mentions_subject`: Co-occurrence of keywords without claim evidence.
7. `insufficient_information`: Incomplete data.
8. `unverifiable`: Passage cannot be validated against known sources.

*Crucial Guardrail*: Uses regex heuristics (`_STUDY_AIM_PATTERNS`) to distinguish between an author's research intent (*"We aimed to show..."*) and actual findings (*"Results demonstrated a 24% increase..."*).

### 6.2 Study Independence Clustering (`StudyIndependenceService`)
Prevents derivative publications from masquerading as independent corroboration:
- Compares titles, authors, and citation overlap using Jaccard token metrics.
- Clusters sources into: `confirmed_independent`, `likely_independent`, `related_studies`, `duplicate_publications`, `unknown_independence`.
- Computes `independence_ratio`: Prevents inflated consensus scores when multiple news outlets or review papers cite one single underlying study.

### 6.3 15-Dimension Methodology Audit (`MethodologyAuditService`)
Audits investigations across 15 scientific dimensions:
- Selection bias, geographic concentration, temporal decay, publication bias.
- Confounding variables, correlation vs causation confusion, sample size power.
- Classifies findings into three severities: `confirmed_problem`, `potential_concern`, `unassessed_limitation`.

### 6.4 Human-in-the-Loop Review & Corrections (`HumanReviewService`)
Allows domain experts to challenge and correct AI findings:
- Submit challenge with correction type (`reclassify_relationship`, `mark_invalid_evidence`, `adjust_credibility`).
- Persists immutable correction record in `HumanEvidenceCorrection` table without deleting original audit trail.

### 6.5 Versioned Scientific Benchmarking (`BenchmarkService`)
- 10 canonical benchmark datasets.
- Compares investigation performance against historical baselines (Retrieval, Evidence, Synthesis, Operational).
- Generates side-by-side regression comparisons.

- **Current Status**: **Implemented and Verified** (Tested across 8 dedicated test suites in `backend/tests/`).

---

## 7. Interactive Knowledge Graph

| Category | Technical Specification |
|---|---|
| **Purpose** | Visualizes complex scientific relationships between investigations, claims, evidence, sources, arguments, and decisions in an interactive graph. |
| **User Interaction** | User navigates to `/graph` or the Investigation Graph tab. Can drag, zoom, filter by node type, search text, collapse branches, and inspect node details in a side panel. |
| **Internal Process** | Backend endpoint `GET /api/v1/research/graph` constructs a structured node/edge payload. Frontend `lib/graph.ts` normalizes data into React Flow nodes and edges, applying deterministic hierarchical layout coordinates. |
| **AI Involvement** | None (pure deterministic relational mapping). |
| **Data Flow** | **In:** Investigation UUID.<br>**Out:** 16 node types (`claim`, `evidence`, `source`, `argument`, `decision`, etc.) and directional edges (`supports`, `contradicts`, `cites`, `adjudicates`). |
| **Output** | Cyberpunk scientific graph canvas with node glowing effects, edge labels, and provenance warning pills. |
| **Failure Handling** | Missing provenance relations trigger amber warning borders; orphaned nodes are grouped in an unlinked cluster rather than crashing the canvas. |
| **Current Status** | **Implemented and Verified** (Tested in `tests/workspace-ui.test.mjs` and `test_graph_api.py`). |

---

## 8. Autonomous Research Workflows

| Category | Technical Specification |
|---|---|
| **Purpose** | Enables self-directed, multi-cycle scientific investigations that detect evidence gaps, refine search queries, acquire additional sources, and re-evaluate claims until stopping conditions are met. |
| **User Interaction** | User navigates to `/autonomous`, selects an investigation, configures maximum cycles (e.g. 3-5), max sources, and token budget, and clicks **"Start Autonomous Loop"**. |
| **Internal Process** | `backend/app/analysis/autonomous_workflow_service.py`:
1. Executes durable state machine (`created -> queued -> planning -> executing -> evaluating -> refining -> completed`).
2. Each cycle executes:
   - Gap detection via `gap_service.py`.
   - Adaptive query generation via `adaptive_query_service.py`.
   - New source acquisition via `research_cycle_service.py`.
   - Re-evaluation and claim updating.
3. Evaluates stopping conditions via `research_stopping_service.py` (claim saturation, confidence plateau, budget exhaustion).
4. Persists state checkpoints in `ResearchWorkflowCheckpoint` after every cycle. |
| **AI Involvement** | LLM generates refined queries and evaluates evidence saturation; orchestrator manages cycle transitions. |
| **Data Flow** | **In:** Workflow configuration (cycle limits, budget, approval mode).<br>**Out:** Cycle execution logs, action history, and final synthesis report. |
| **Output** | Real-time cycle visualization timeline displaying active phase, budget spent, and newly acquired evidence. |
| **Failure Handling** | Server restart triggers `recover_workflows()`, resuming interrupted cycles from last persisted checkpoint. |
| **Current Status** | **Implemented and Verified** (Tested in `test_autonomous_workflows.py`). |

---

## 9. Reports & Multiformat Knowledge Export

| Category | Technical Specification |
|---|---|
| **Purpose** | Compiles exhaustive, publication-grade research reports and exports them into standard scientific formats. |
| **User Interaction** | User views report on `/investigations/[id]` or clicks **Export** (Markdown, JSON, PDF, CSV, BibTeX, Research Bundle). |
| **Internal Process** | `backend/app/analysis/report_service.py`: Compiles 18 standardized sections:
1. Executive Summary
2. Research Question
3. Investigation Scope
4. Search Strategy
5. Key Findings
6. Claim-by-Claim Assessment
7. Supporting Evidence
8. Contradicting Evidence
9. Advocate Perspective
10. Skeptic Perspective
11. Methodological Assessment
12. Source Quality Assessment
13. Citation Genealogy
14. Temporal Intelligence
15. Unresolved Questions
16. Limitations
17. Final Assessment
18. References Directory
`export_service.py` formats data into requested formats, including BibTeX citations and complete research bundles (ZIP with report, evidence CSV, and graph JSON). |
| **AI Involvement** | Report Intelligence agent formats prose; section assembly and citation grounding are deterministic. |
| **Data Flow** | **In:** Investigation UUID and export format.<br>**Out:** Structured document stream / file download. |
| **Output** | Formatted report on screen or downloaded file. |
| **Failure Handling** | Incomplete investigations display partial sections with explicit "Data Acquisition in Progress" banners rather than failing. |
| **Current Status** | **Implemented and Verified** (Tested in `test_report_intelligence.py`, `test_export_service.py`). |

---

## 10. Workspace Multi-Tenancy & Peer Collaboration

| Category | Technical Specification |
|---|---|
| **Purpose** | Provides enterprise multi-user isolation, workspace role-based access control, threaded discussions, inline annotations, and formal review sign-offs. |
| **User Interaction** | User navigates to `/workspaces`, invites team members via email, comments on claims, highlights text on evidence passages, and submits investigations for formal review. |
| **Internal Process** | `backend/app/collaboration/`:
- `workspace_service.py`: Manages workspaces with roles (`owner`, `admin`, `researcher`, `reviewer`, `viewer`).
- `invitation_service.py`: Generates secure 7-day token invitations.
- `comment_service.py`: Threaded comments with resolve/reopen lifecycles.
- `annotation_service.py`: Inline text highlights on evidence.
- `review_service.py`: Formal review workflows with decisions (`approved`, `rejected`, `revisions_requested`).
- `notification_service.py`: In-app notification center. |
| **AI Involvement** | None (pure collaboration and access control logic). |
| **Data Flow** | **In:** User JWT, workspace UUID, comment/review payload.<br>**Out:** Activity logs, notification items, updated review states. |
| **Output** | Collaboration drawer, unread notification badges, and review status banners. |
| **Failure Handling** | Unauthorized role actions return HTTP 403 Forbidden. |
| **Current Status** | **Implemented and Verified** (Tested in `test_auth_and_workspaces.py` and UI tests). |

---

## 11. Telemetry, Observability & Calibration Dashboard

| Category | Technical Specification |
|---|---|
| **Purpose** | Provides real-time operational monitoring of inference queue latency, token consumption, agent states, and scientific quality calibration. |
| **User Interaction** | User views the Telemetry strip at the top of the investigation page or visits `/quality-audit`. |
| **Internal Process** | Backend aggregates metrics: active agents, queue wait times, token counts, evidence density, and calibration scores (`ResearchQualityCalibration`). Telemetry is pushed over SSE and polled at interval. |
| **AI Involvement** | None. |
| **Data Flow** | **In:** Investigation ID.<br>**Out:** Live metrics payload (duration, tokens, sources, evidence count, calibration index). |
| **Output** | Cyberpunk animated counters, radar scanner animation, and calibration gauge cards. |
| **Failure Handling** | Network disconnect triggers automatic exponential reconnect without clearing current metrics. |
| **Current Status** | **Implemented and Verified** (Tested in `test_observability.py` and `test_quality_calibration.py`). |
