# NEOMON — Technical Limitations, Vulnerabilities & Risks
**Honest Architectural Evaluation for Technical Finals Review**

---

## 1. Philosophical Grounding: Honest Engineering Over Promotional Hype

A critical criterion in competition finals is **technical honesty**. Judges evaluate whether an engineering team understands the boundaries, failure modes, and edge cases of their system.

NEOMON does not claim to have "solved scientific truth" or created an "infallible research intelligence." Automated scientific synthesis operates at the intersection of noisy literature, probabilistic language models, and complex empirical epistemologies.

This document identifies every concrete limitation in NEOMON's current implementation, explains why it exists, details its practical impact, describes current code mitigations, and outlines planned engineering solutions.

---

## 2. AI & Model-Level Limitations

### Limitation 1.1: LLM Hallucination of Evidence Identifiers & Passages
- **What it is**: Probabilistic models may fabricate plausible-sounding evidence statements or invent UUID citations that do not exist in the retrieved corpus.
- **Why it exists**: Autoregressive transformers predict the most likely next token based on statistical weights, not factual verification.
- **Practical Impact**: If unmitigated, an agent could cite non-existent data to falsely support or refute a critical scientific claim.
- **Current Code Mitigation**:
  - `backend/app/analysis/service.py:1020-1026` (`_validate_role_payload`): Enforces strict mathematical set validation. Every cited `evidence_id` in an agent argument is verified against `evidence_ids = {item.id for item in evidence}`.
  - If a model outputs unknown UUIDs, NEOMON automatically filters them out (`service.py:1120-1132`), recalculates cited source IDs, and if no valid evidence remains, forces `evidence_basis="none"` and downgrades confidence to `"insufficient"`.
  - Disallows any claim assertion that lacks verified database backing.
- **Future Improvement**: Implement constrained decoding / grammar-guided generation (via Outlines or vLLM logits masking) so the model is physically incapable of outputting non-existent UUIDs.

---

### Limitation 1.2: Structured JSON Parsing & Schema Non-Compliance
- **What it is**: Smaller models (8B parameters, local quantized models) occasionally emit conversational preambles, trailing markdown backticks, or invalid JSON syntax, violating Pydantic schemas.
- **Why it exists**: Smaller context windows and lower instruction-following fidelity in quantized open weights.
- **Practical Impact**: A single agent's failure to return valid JSON could cause an unhandled exception and crash the investigation pipeline.
- **Current Code Mitigation**:
  - Multi-tier JSON cleaning (`_extract_json_block()` in `backend/app/providers/openai_compatible.py`) strips markdown fences and conversational wrappers.
  - Two-pass validation: If structured output parsing fails, the system executes one automated repair retry with an explicit error correction prompt.
  - If the model still fails, NEOMON falls back to deterministic rule-based arguments (`_role_argument()`) grounded in lexical co-occurrence, logging a warning rather than crashing.
- **Future Improvement**: Migrate to provider-native Structured Outputs (`response_format={"type": "json_schema"}`) and native JSON-mode logits biasing across all local and cloud backends.

---

### Limitation 1.3: Context Window Saturation & Evidence Truncation
- **What it is**: When an investigation ingests 50+ papers with thousands of extracted sentences, passing the entire evidence corpus to every specialist agent exceeds context window limits or increases inference latency exponentially.
- **Why it exists**: Transformer attention scales quadratically ($O(N^2)$), and input context limits (e.g. 8k to 128k tokens) impose hard ceilings.
- **Practical Impact**: If an agent receives an arbitrary truncated subset of evidence, it might miss critical counter-evidence located later in the prompt.
- **Current Code Mitigation**:
  - `_associate_evidence()` in `backend/app/analysis/service.py` pre-filters and ranks evidence per claim using semantic relevance (`assess_text`) before prompt injection.
  - Limits evidence injection per claim to the top 15 highest-confidence empirical passages (`[:900]` characters per passage).
- **Future Improvement**: Implement a hierarchical map-reduce summarization layer and vector chunk reranking (using Cohere or BGE rerankers) to guarantee maximum information density within token budgets.

---

### Limitation 1.4: Cross-Model Output Inconsistency (LLM Variance)
- **What it is**: An investigation run using GPT-4o produces slightly different argument phrasing, emphasis, and confidence scores than a run using Llama-3.3-70B or Mistral-Small.
- **Why it exists**: Differences in pre-training corpora, RLHF alignment, tokenization, and temperature sampling.
- **Practical Impact**: Users running identical questions on different models might receive slight variations in nuance.
- **Current Code Mitigation**:
  - Default temperature is pinned low ($T=0.1$ to $0.2$) across all specialist agents to maximize determinism.
  - Claim adjudication decisions rely on empirical thresholds (e.g. ratio of supporting vs contradicting evidence passages) rather than raw LLM sentiment.
- **Future Improvement**: Build a multi-model consensus ensemble option, where critical adjudications require majority agreement between two distinct model families (e.g. OpenAI + Anthropic, or Meta + Mistral).

---

## 3. Academic Retrieval & Source Limitations

### Limitation 2.1: The Academic Paywall Barrier
- **What it is**: Many high-impact medical and scientific journals (Elsevier, Springer Nature, Wiley) lock full-text papers behind paywalls ($30–$50 per article).
- **Why it exists**: Commercial publishing models and copyright restrictions.
- **Practical Impact**: NEOMON cannot legally download the complete text of closed-access papers without institutional credentials, having to rely solely on open-access preprints or published abstracts.
- **Current Code Mitigation**:
  - Integrates **Unpaywall API** (`backend/app/research/open_access.py`), which automatically queries over 50,000 global institutional repositories to find legal open-access mirror PDFs for any DOI.
  - When no legal full-text is available, NEOMON extracts the published abstract from Crossref/OpenAlex and explicitly tags the source as `abstract_only=True`, adjusting confidence scores accordingly.
- **Future Improvement**: Implement an institutional proxy / Shibboleth authentication module allowing universities and corporate subscribers to connect their institutional subscriptions securely.

---

### Limitation 2.2: Public Academic API Rate Limits & Latency
- **What it is**: Free scholarly APIs (Crossref Polite Pool, OpenAlex, arXiv) impose strict rate limits (e.g. 10–50 requests per second) and occasionally experience high response latency (1–3 seconds).
- **Why it exists**: Public infrastructure constraints of non-profit academic indexing services.
- **Practical Impact**: Ingestion speed is bottlenecked by external API response times, preventing instantaneous multi-source retrieval.
- **Current Code Mitigation**:
  - Concurrent asynchronous HTTP requests via `httpx` with staggered connection pools.
  - Dedicated caching layer (`backend/app/cache/service.py`) caching API responses for identical query strings.
  - Circuit breakers that prevent slow APIs from blocking the remaining investigation.
- **Future Improvement**: Pre-index local mirrors of open academic datasets (e.g. OpenAlex bulk snapshots on S3/ClickHouse) for millisecond-latency local semantic search.

---

### Limitation 2.3: Inaccurate or Incomplete Citation Metadata
- **What it is**: Preprints on arXiv or newly published papers often have incomplete reference lists, missing DOIs, or unformatted author strings.
- **Why it exists**: Incomplete ingestion or metadata parsing delays in academic repositories.
- **Practical Impact**: May prevent `citation_genealogy` from discovering all downstream citations or historical predecessors.
- **Current Code Mitigation**:
  - Normalization engine (`backend/app/research/normalization.py`) cleans and sanitizes titles, extracts standard DOIs via regex, and computes cross-provider deduplication using Jaccard token similarity.
- **Future Improvement**: Cross-reference citations with Semantic Scholar API and OpenCitations database for multi-source citation graph enrichment.

---

## 4. Scientific & Epistemological Limitations

### Limitation 3.1: Distinguishing Genuine Causation from Correlation
- **What it is**: Observational studies frequently demonstrate statistically significant correlations (e.g. *"Students using AI report higher satisfaction"*) that do not establish direct causality (*"AI caused the satisfaction"*).
- **Why it exists**: LLMs and text scrapers process observational language easily, but causal inference requires rigorous counterfactual reasoning and experimental controls.
- **Practical Impact**: Risk of over-interpreting observational associations as proven causal interventions.
- **Current Code Mitigation**:
  - `MethodologyAuditService` specifically audits study designs, flagging observational studies that assert causal conclusions as `potential_concern` or `confirmed_problem`.
  - The **Methodology Auditor** agent is explicitly instructed to scrutinize confounding variables, reverse causality, and cohort self-selection.
- **Future Improvement**: Integrate formal causal inference graphs (Do-calculus, DAG analysis) into the Claim Decomposition layer.

---

### Limitation 3.2: Automated Credibility Heuristics vs. Deep Domain Expertise
- **What it is**: NEOMON evaluates source credibility using proxy signals: peer-review status, journal venue, citation velocity, and publisher reputation.
- **Why it exists**: An automated system cannot independently replicate laboratory experiments or audit raw bench data.
- **Practical Impact**: A methodologically flawed paper published in a prestigious journal might receive a higher initial credibility score than an immaculate study published in an emerging venue.
- **Current Code Mitigation**:
  - The adversarial **Skeptic** and **Methodology Auditor** evaluate the paper's *actual reported methodology* (sample size, controls, p-values), not merely its journal prestige badge.
  - Milestone 12 Human-in-the-Loop review allows domain experts to challenge and override credibility scores.
- **Future Improvement**: Integrate Retraction Watch database API to instantly flag retracted or disputed literature.

---

### Limitation 3.3: Irreconcilable Empirical Contradictions
- **What it is**: In emerging science (e.g. nutritional science, complex AI safety, economic interventions), two equally rigorous randomized controlled trials can yield directly opposing conclusions due to unmeasured contextual differences.
- **Why it exists**: Real-world scientific complexity, hidden moderators, and heterogeneous populations.
- **Practical Impact**: An automated system cannot force an artificial "true/false" consensus when empirical reality is divided.
- **Current Code Mitigation**:
  - Unlike commercial chatbots that pick one answer and hallucinate consensus, NEOMON's **Conflict Adjudicator** explicitly flags genuine scientific controversies as `contradictory` or `inconclusive`.
  - Preserves both Advocate and Skeptic arguments in Section 8 (*Contradicting Evidence*) of the final report.
- **Future Improvement**: Subgroup meta-analysis extraction to isolate why studies differed (e.g. different dosage, different age cohorts, different model prompting).

---

## 5. Engineering & Infrastructure Limitations

### Limitation 4.1: SQLite Concurrency vs. PostgreSQL Enterprise Scale
- **What it is**: In standard local execution, NEOMON defaults to SQLite with Write-Ahead Logging (WAL). While SQLite handles high read concurrency, it enforces a single-writer lock for database transactions.
- **Why it exists**: Selected to enable zero-configuration, immediate local setup without requiring Docker or a dedicated database server.
- **Practical Impact**: If dozens of concurrent users write to the database simultaneously, transactions may experience brief queue delays.
- **Current Code Mitigation**:
  - WAL mode enabled (`PRAGMA journal_mode=WAL`), allowing concurrent readers without blocking writers.
  - Codebase is fully multi-dialect: Set `DATABASE_URL=postgresql+asyncpg://...` in `.env`, and NEOMON runs on enterprise PostgreSQL with complete connection pooling (`asyncpg`).
- **Future Improvement**: Implement automated read-replica routing for heavy reporting queries.

---

### Limitation 4.2: Local LLM VRAM & Throughput Bottlenecks
- **What it is**: When running on consumer hardware (e.g. single 8GB/16GB VRAM GPU), local open models (Ollama, LM Studio) process tokens at 15–35 tokens/second.
- **Why it exists**: Hardware constraints of consumer-grade local GPUs.
- **Practical Impact**: An investigation with 8 specialist agent runs may take 2 to 4 minutes locally, compared to 20 to 40 seconds on cloud API endpoints.
- **Current Code Mitigation**:
  - `InferenceLimiter` restricts concurrency to 1 active inference when `is_local_provider=True`, preventing out-of-memory GPU crashes.
  - Live progress telemetry keeps user informed of exact queue position and active token generation.
- **Future Improvement**: Implement speculative decoding and batch-inference queuing for local vLLM / llama.cpp endpoints.

---

### Limitation 4.3: Knowledge Graph DOM Scaling Limits
- **What it is**: Rendering a knowledge graph with over 1,000 nodes and 3,000 edges using SVG/HTML in React Flow can cause UI frame-rate drops on low-end laptops.
- **Why it exists**: Browser DOM manipulation overhead for thousands of interactive SVG nodes.
- **Current Code Mitigation**:
  - Implements node filtering, branch collapsing, and viewport virtualization in `lib/graph.ts`.
  - Default view renders the core claim-evidence backbone; subsidiary nodes (queries, cycles) expand on user demand.
- **Future Improvement**: Implement WebGL-based canvas rendering (via PixiJS or Three.js) for large-scale multi-thousand-node institutional graphs.
