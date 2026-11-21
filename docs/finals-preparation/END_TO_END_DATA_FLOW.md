# NEOMON — End-to-End Technical Data Flow
**Complete Execution Trace for a Real Scientific Investigation**

---

## 1. Example Investigation Case Study

To understand the exact internal mechanics of NEOMON, we trace a complete run of the canonical research question:

> **"How does generative AI affect students in higher education?"**

---

## 2. Step-by-Step Execution Trace

```
+----------------------------------------------------------------------------------------------------+
|                                    10-STAGE INVESTIGATION LIFECYCLE                                |
+----------------------------------------------------------------------------------------------------+
[STAGE 1]  User Submission & API Ingestion (POST /api/v1/research/investigations)
     |
[STAGE 2]  Intelligence Planning & Atomic Claim Decomposition (intelligence_planner)
     |
[STAGE 3]  Multi-Source Search Strategy & Academic Ingestion (Crossref, OpenAlex, arXiv, Tavily)
     |
[STAGE 4]  SSRF Validation, Full-Text Retrieval & Boilerplate Stripping
     |
[STAGE 5]  Sentence-Level Evidence Extraction & Outcome Signal Detection
     |
[STAGE 6]  Scientific Integrity Classification & Study Independence Clustering
     |
[STAGE 7]  Concurrent Specialist Agent Invocations (Advocate, Skeptic, Auditor, Lineage, Temporal)
     |
[STAGE 8]  Moderated Dialectical Debate Rounds (Debate Moderator)
     |
[STAGE 9]  Conflict Adjudication & Verdict Determination (Conflict Adjudicator)
     |
[STAGE 10] 18-Section Report Synthesis, Knowledge Graph Generation & SSE Client Broadcast
```

---

### Stage 1: User Submission & API Ingestion
1. **Frontend Action**: User enters `"How does generative AI affect students in higher education?"` on `/investigations/new` and clicks **"Initiate Scientific Investigation"**.
2. **HTTP Request**:
   ```http
   POST /api/v1/research/investigations
   Authorization: Bearer <jwt_token>
   Content-Type: application/json

   {
     "question": "How does generative AI affect students in higher education?",
     "workspace_id": "8f3b2011-e402-4b68-98e1-d24c88741290",
     "provider_config": {
       "kind": "openai",
       "model": "gpt-4o",
       "temperature": 0.2
     },
     "max_concurrent_agents": 4,
     "max_debate_rounds": 2
   }
   ```
3. **Backend Execution**:
   - `backend/app/routers/research.py`: Validates request payload against Pydantic schema `InvestigationCreateRequest`.
   - Inserts new row into `investigations` table: `id="inv_982a..."`, `status="queued"`.
   - Returns HTTP 201 Created with investigation entity.
   - Client automatically redirects to `/investigations/inv_982a...`.

---

### Stage 2: Planning & Atomic Claim Decomposition
1. **Manager Dispatch**: `AnalysisManager` starts background task `run_analysis()` in `backend/app/analysis/service.py`.
2. **State Transition**: `job.status = "planning"`. Backend emits SSE event `analysis_stage_changed` (`stage="planning"`).
3. **Agent Invocation**: Instantiates `intelligence_planner`.
4. **LLM Structured Generation**:
   The planner analyzes semantic variables and decomposes the overarching question into four atomic, independently testable claims:
   - **Claim 1 (Academic Performance)**: *"Generative AI tools improve student learning efficiency and comprehension in undergraduate STEM disciplines."* (Priority: 1)
   - **Claim 2 (Cognitive Dependency)**: *"Reliance on LLMs for assignment drafting diminishes critical thinking and independent problem-solving skills."* (Priority: 1)
   - **Claim 3 (Academic Integrity)**: *"Institutional adoption of automated AI detection software produces unacceptably high false-positive rates for non-native English speakers."* (Priority: 2)
   - **Claim 4 (Educational Equity)**: *"Disparities in commercial AI subscription access widen socioeconomic attainment gaps among university students."* (Priority: 2)
5. **Persistence**: Four records are inserted into `claims` table, each linked to `investigation_id`.

---

### Stage 3: Search Strategy & Academic Query Formulation
1. **State Transition**: `job.status = "researching"`. SSE event emitted.
2. **Query Formulation**: `QueryPlanner` converts claim objectives into targeted academic search queries:
   - `Q1`: `"generative AI" OR "large language models" AND ("higher education" OR "university") AND ("learning outcomes" OR "comprehension")`
   - `Q2`: `"ChatGPT" AND "higher education" AND ("critical thinking" OR "cognitive offloading")`
   - `Q3`: `AI detector "false positive" "non-native" English university`
3. **Multi-Source Dispatch**:
   - **Crossref**: Queries metadata for peer-reviewed journal papers (IEEE, Elsevier, Springer).
   - **OpenAlex**: Retrieves citation counts, concept tags, and author affiliations.
   - **arXiv**: Searches preprints under `cs.AI` and `cs.CY` (Computers and Society).
   - **Unpaywall**: Checks open-access repository links for identified DOIs.
   - **Tavily**: Searches recent university case studies and educational policy announcements.
4. **Persistence**: 24 sources inserted into `sources` table with metadata (title, DOI, journal, author list, year).

---

### Stage 4: Document Acquisition & SSRF-Protected Scraper
1. **Retrieval Dispatch**: For each discovered source URL, `backend/app/research/retrieval.py` executes `retrieve_document(url)`:
   - **SSRF Check**: Resolves hostname IP; strictly blocks loopback (`127.0.0.1`), private LAN (`192.168.x.x`), and link-local ranges.
   - **Fetch**: Streams HTTP response with 10-second timeout.
   - **HTML Parsing**: Custom `HTMLParser` removes navigation, ads, header, and footer tags. Extracts clean article body text.
   - **OpenAccess Fallback**: For paywalled DOIs, queries Unpaywall API; if open PDF repository exists, downloads open version; otherwise captures published abstract.
2. **Persistence**: Clean text stored in `documents` table with SHA-256 content hash and word count.

---

### Stage 5: Sentence-Level Evidence Extraction
1. **Extraction Dispatch**: `backend/app/research/evidence.py` executes `extract_evidence()`:
   - Splits document text into discrete sentences.
   - Filters out boilerplate (*"All rights reserved"*, *"Conflict of interest statement"*).
   - Evaluates sentences for **outcome signals** (*"demonstrated a 28% increase"*, *"p < 0.01"*, *"significant decline in exam scores"*).
   - Assigns `evidence_type`: `statistical`, `empirical`, `observational`, `contextual`.
2. **Sample Evidence Extracted**:
   - `EV-01`: *"Students using AI-assisted tutoring scored on average 0.42 standard deviations higher on post-module algebra assessments compared to the control group (p=0.003)."* (Confidence: 0.88, Type: `statistical`)
   - `EV-02`: *"In a randomized trial of 180 undergraduate writers, students with unrestricted ChatGPT access spent 41% less time analyzing source literature and exhibited significantly lower recall during unassisted testing."* (Confidence: 0.84, Type: `empirical`)
   - `EV-03`: *"Commercial AI text classifiers misidentified essays written by non-native English speakers as AI-generated in 61.3% of test samples."* (Confidence: 0.92, Type: `empirical`)
3. **Persistence**: Extracted passages inserted into `evidence` table with exact character start/end offsets.

---

### Stage 6: Scientific Integrity & Study Independence
1. **Evidence Verification**: `EvidenceVerificationService` evaluates each evidence passage against the 4 claims:
   - Classifies `EV-01` -> `directly_supports` Claim 1.
   - Classifies `EV-02` -> `directly_supports` Claim 2 / `contradicts` Claim 1.
   - Classifies `EV-03` -> `directly_supports` Claim 3.
   - Flags introductory remarks (*"We hoped to show AI improves all learning"*) as `mentions_subject` rather than empirical proof.
2. **Study Independence Analysis**: `StudyIndependenceService` compares the 24 sources:
   - Identifies that 3 university news releases all report on the exact same underlying Stanford study.
   - Collapses them into a single `StudyIndependenceCluster` (`category="duplicate_publications"`).
   - Calculates `independence_ratio = 18 unique studies / 24 sources = 0.75`.

---

### Stage 7: Concurrent Specialist Agent Invocations
1. **Execution Concurrency**: Under `asyncio.Semaphore(4)`, the backend invokes specialist agents:
2. **Agent Arguments Generated**:
   - **Advocate (`advocate.py`)**: Submits argument for Claim 1 citing `EV-01`. Argues personalized pacing significantly improves lower-quartile comprehension.
   - **Skeptic (`skeptic.py`)**: Submits counter-argument for Claim 1 citing `EV-02`. Argues that learning efficiency is an illusion created by cognitive offloading; long-term retention drops when AI is removed.
   - **Methodology Auditor (`methodology_auditor.py`)**: Reviews `EV-01` and `EV-02`. Notes that `EV-01` tested only immediate post-test outcomes without longitudinal follow-up; sample was restricted to STEM undergraduates in a private institution (high risk of selection bias).
   - **Source Intelligence (`source_intelligence.py`)**: Confirms `EV-01` was published in a high-impact peer-reviewed journal (Q1, Nature Learning), while an opposing paper was an unreviewed conference preprint.
   - **Citation Genealogy (`citation_genealogy.py`)**: Traces lineage back to foundational 2023 cognitive load models.
   - **Temporal Intelligence (`temporal_intelligence.py`)**: Observes that 2023 papers emphasized fear of cheating, while 2025-2026 papers shifted to curricular integration and cognitive scaffolding.
3. **Persistence**: Arguments inserted into `agent_arguments` table.

---

### Stage 8: Moderated Dialectical Debate Rounds
1. **State Transition**: `job.status = "debating"`.
2. **Round 1**: `debate_moderator` reviews submitted arguments across all 4 claims:
   - Identifies active tension between Advocate (`EV-01`: immediate task score gains) and Skeptic (`EV-02`: long-term recall degradation).
   - Emits `DebateRound` 1 summary: *"Primary disagreement centers on immediate procedural assistance versus long-term conceptual retention. Further distinction required between AI as an interactive tutor vs. AI as an assignment generator."*
3. **Round 2**: Agents refine positions:
   - Advocate concedes that passive text generation degrades retention, but maintains that Socratic AI tutoring improves conceptual grasp.
   - Skeptic agrees that interactive tutoring differs from text generation, but highlights that 85% of student usage is passive generation.
4. **Persistence**: Debate round summaries and tension logs stored in `debate_rounds` table.

---

### Stage 9: Conflict Adjudication & Verdict Determination
1. **Adjudicator Dispatch**: `conflict_adjudicator` evaluates arguments, debate rounds, evidence weights, and methodology findings.
2. **Claim Verdicts Rendered**:
   - **Claim 1 (Academic Performance)**: `moderately_supported` with caveats. AI improves immediate task execution and formative learning, but long-term retention remains unproven without active Socratic constraints.
   - **Claim 2 (Cognitive Dependency)**: `strongly_supported`. Empirical data demonstrates significant cognitive offloading when students use AI for text generation without guidance.
   - **Claim 3 (Academic Integrity)**: `strongly_supported`. Heavy empirical consensus that detector false-positive rates disproportionately penalize ESL students.
   - **Claim 4 (Educational Equity)**: `inconclusive`. Insufficient empirical literature isolating paid tier advantages from general institutional access.
3. **Persistence**: Verdicts, confidence scores, and trade-off rationales stored in `adjudication_decisions` table.

---

### Stage 10: Report Generation, Knowledge Graph & Export
1. **Report Compilation**: `ReportIntelligence` compiles the 18 standardized sections in `backend/app/analysis/report_service.py`.
2. **Reproducibility Manifest**: Generates SHA-256 hash snapshot of all sources, queries, evidence passages, and agent prompts (`ResearchExecutionManifest`).
3. **Knowledge Graph Generation**: Computes graph view (`4 claims`, `24 sources`, `38 evidence nodes`, `12 arguments`, `4 decisions`).
4. **State Transition**: `job.status = "completed"`. Broadcasts `analysis_stage_changed` (`stage="completed"`) via SSE.
5. **Frontend Presentation**:
   - Live dashboard updates without page refresh.
   - Report tab renders complete 18 sections with clickable citation badges linking to exact text passages.
   - Graph tab renders interactive interactive visualization with color-coded nodes.
   - Export dropdown enables immediate 1-click download of PDF, Markdown, BibTeX, or complete Research Bundle.

---

## 3. High-Level Architecture Diagram

```
+---------------------------------------------------------------------------------------+
|                                  USER WORKSPACE (Next.js)                              |
|   Enter Research Question  ->  Live Telemetry Stream  ->  Interactive Graph & Report  |
+-------------------------------------------+-------------------------------------------+
                                            | REST / SSE
                                            v
+---------------------------------------------------------------------------------------+
|                                    FASTAPI BACKEND                                    |
|   Request Validation  ->  EventBroker (SSE)  ->  Database Context (SQLAlchemy Async)  |
+-------------------------------------------+-------------------------------------------+
                                            |
         +----------------------------------+----------------------------------+
         |                                                                     |
         v                                                                     v
+-----------------------------------------------+     +-----------------------------------------------+
|             ACADEMIC RETRIEVAL PIPELINE       |     |            MULTI-AGENT INFERENCE ENGINE       |
| - IntelligencePlanner decomposes question     |     | - Concurrency Limiter (Semaphore control)     |
| - QueryPlanner targets Crossref, arXiv, Alex  |     | - Advocate (builds affirmative defense)       |
| - SSRF-guarded Scraper downloads clean text   |     | - Skeptic (hunts counter-evidence and flaws)  |
| - ExtractEvidence isolates outcome passages   |     | - Methodology Auditor (audits 15 dimensions)  |
| - StudyIndependence clusters duplicate papers |     | - Debate Moderator & Adjudicator             |
+-----------------------+-----------------------+     +-----------------------+-----------------------+
                        |                                                     |
                        +--------------------------+--------------------------+
                                                   |
                                                   v
                        +-----------------------------------------------------+
                        |                  PERSISTENCE TIER                   |
                        | - 66 Relational Models (SQLite WAL / PostgreSQL)    |
                        | - 18-Section Scientific Research Report             |
                        | - Cryptographic SHA-256 Reproducibility Manifest    |
                        +-----------------------------------------------------+
```

---

## 4. Multi-Agent Dialectical Interaction Diagram

```
                              [ Research Question ]
                                        |
                                        v
                            [ Intelligence Planner ]
                                        |
             +--------------------------+--------------------------+
             | Formulates Claims & Objectives                      |
             v                                                     v
   [ Claim 1: Learning Gains ]                           [ Claim 2: Cognitive Offload ]
             |                                                     |
             +--------------------------+--------------------------+
                                        |
                   Discovers Sources & Extracts Evidence
                                        |
                                        v
                       +---------------------------------+
                       |    ADVERSARIAL AGENT MATRIX     |
                       +----------------+----------------+
                                        |
         +------------------------------+------------------------------+
         |                              |                              |
         v                              v                              v
   [ ADVOCATE ]                   [ SKEPTIC ]               [ METHODOLOGY AUDITOR ]
  "EV-01 shows 0.42 SD           "EV-02 proves 41% decline   "EV-01 lacks longitudinal
   score improvement in           in analytical recall        follow-up; high risk of
   STEM assessments."             during unassisted tests."   short-term measurement bias."
         |                              |                              |
         +------------------------------+------------------------------+
                                        |
                                        v
                             [ DEBATE MODERATOR ]
                    "Tension identified: Immediate task gains
                     vs. long-term conceptual retention."
                                        |
                                        v
                           [ CONFLICT ADJUDICATOR ]
                     Verdict: Moderately Supported with caveats.
                     Requires active Socratic constraints.
                                        |
                                        v
                            [ REPORT INTELLIGENCE ]
                        Assembles 18 Standard Sections
```
