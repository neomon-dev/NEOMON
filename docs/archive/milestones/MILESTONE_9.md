# NEOMON Milestone 9 — Autonomous Research Workflow Engine

## Executive Overview

Milestone 9 transforms NEOMON from an advanced, on-demand research intelligence platform into an autonomous, iterative, evidence-driven scientific research system.

Rather than executing a single pass of source retrieval and multi-agent debate, the **Autonomous Research Workflow Engine** systematically:
1. Identifies what remains unknown, ungrounded, or contradictory.
2. Formulates prioritized, deterministic research actions across scholarly repositories and general-web providers.
3. Adapts queries to specific providers, avoids near-duplicate searches, and generates deliberate counter-evidence probes.
4. Executes structured research actions with strict concurrency control.
5. Ingests and routes newly retrieved literature through the canonical Milestone 8G evidence validation and credibility pipeline.
6. Re-evaluates claims, hypotheses, contradictions, and gaps using direct, contextual, and counter-evidence metrics.
7. Computes cycle-over-cycle information gain and updates calibrated quality ratings.
8. Enforces hard operational budgets (cycles, searches, sources, documents, duration) and scientific stopping criteria (evidence saturation, diminishing returns, persistent uncertainty).
9. Provides human oversight modes (`assisted`, `supervised`, `bounded`) with a dedicated human review queue.
10. Preserves state across crashes and server restarts through durable checkpointing and automated startup recovery.
11. Surfaces rich real-time observability in the `/autonomous` workspace and fully integrates workflow nodes and grounded edges into the Knowledge Graph.

---

## Architecture & Subsystems

```
                                  +---------------------------------------------+
                                  |         AutonomousWorkflowService           |
                                  | (15-State Machine, Checkpoints, Recovery)   |
                                  +---------------------------------------------+
                                                         |
         +-----------------------------------------------+-----------------------------------------------+
         |                                               |                                               |
         v                                               v                                               v
+------------------------+                     +------------------------+                     +------------------------+
|    Research Planner    |                     | Research Cycle Engine  |                     | Research Stopping Engine|
| (Deterministic-First   |                     | (Iterative Execution,  |                     | (Operational Budgets &  |
|  14 Action Types, Pri) |                     |  8G Integration, Gain) |                     |  Scientific Criteria)  |
+------------------------+                     +------------------------+                     +------------------------+
         |                                               |                                               |
         v                                               v                                               v
+------------------------+                     +------------------------+                     +------------------------+
| Adaptive Query Service |                     | Human Oversight Queue  |                     | Knowledge Graph & UI   |
| (Provider Syntax,      |                     | (Approve/Reject        |                     | (/autonomous Workspace,|
|  Deduplication, SLLM)  |                     |  Assisted Actions)     |                     |  Nodes & Grounded Edges)|
+------------------------+                     +------------------------+                     +------------------------+
```

---

## 1. Sub-Milestone Details

### 9A: Persistent State Machine & Orchestration
Implemented in `backend/app/analysis/autonomous_workflow_service.py`:
- **15 State Machine States**:
  - Initial: `created`
  - Queued: `queued`
  - Strategic: `planning`
  - In-flight: `executing`
  - Ingestion: `evaluating`
  - Adaptation: `refining`
  - Oversight: `awaiting_approval`
  - Control: `paused`
  - Terminal Success: `completed`, `completed_with_limitations`
  - Terminal Budget: `stopped_by_budget`, `stopped_by_user`
  - Terminal Abort: `failed`, `cancelled`
- Validated state transitions prevent illegal jumps (e.g. from `cancelled` to `executing`).
- Background execution via managed asyncio tasks with graceful cancellation.

### 9B: Intelligent Research Planning
Implemented in `backend/app/analysis/research_planner.py`:
- **Deterministic Action Generation**:
  - Unsupported claims (0 evidence) -> `investigate_claim`
  - Active contradictions -> `investigate_contradiction`
  - Critical evidence gaps -> `probe_evidence_gap` / `investigate_methodology`
  - Active hypotheses -> `evaluate_hypothesis`
  - Verified claims needing counter-evidence -> `find_counter_evidence`
  - General literature expansion -> `search_academic_literature`
- Actions are prioritized deterministically (Priority 1 = highest).
- Expected information gain (0.0 to 1.0) and cost estimates are bounded and defensible.

### 9C: Adaptive Research & Query Refinement
Implemented in `backend/app/analysis/adaptive_query_service.py`:
- **Near-Duplicate Detection**: Jaccard similarity and token overlap tracking across `research_query_histories` prevent redundant searches.
- **Provider Syntax Adaptation**:
  - `arxiv`: Concise technical keyword queries (`len <= 6 tokens`).
  - `crossref` / `openalex`: Methodological keywords (`empirical study`, `systematic review`).
  - `tavily`: Natural language semantic research questions.
- **Counter-Evidence Formulation**: Deliberately reformulates queries with counter-prefixes (`limitations of`, `counter-evidence for`, `confounding factors in`, `refutation of`) to challenge prevailing claims.

### 9D: Iterative Evidence & Claim Reevaluation
Implemented in `backend/app/analysis/research_cycle_service.py`:
- Routes all newly retrieved literature directly through Milestone 8G's canonical credibility classification (`evaluate_canonical_credibility`), source lineage clustering (`analyze_source_lineage`), and logical entailment heuristics (`validate_evidence_claim_entailment_heuristic`).
- Re-evaluates claims, hypotheses, and contradictions cycle-over-cycle.
- Computes mathematical information gain:
  $$\Delta I = 0.4 \cdot (\Delta \text{sources}) + 0.3 \cdot (\Delta \text{evidence}) + 0.2 \cdot (\Delta \text{claims}) + 0.1 \cdot (\Delta \text{quality})$$

### 9E & 9F: Budget Constraints & Scientific Stopping Criteria
Implemented in `backend/app/analysis/research_stopping_service.py`:
- **Hard Budget Limits**:
  - `budget_max_cycles` (default: 5)
  - `budget_max_searches` (default: 20)
  - `budget_max_sources` (default: 50)
  - `budget_max_documents` (default: 20)
  - `budget_max_duration_seconds` (default: 1800s)
- **Scientific Stopping Reasons**:
  - `SUFFICIENT_EVIDENCE`: High claim coverage (>= 85%), Strong quality tier, 0 active contradictions, 0 critical gaps.
  - `DIMINISHING_RETURNS`: Information gain below 0.05 across consecutive cycles.
  - `UNRESOLVED_SCIENTIFIC_UNCERTAINTY`: Active critical contradictions persist despite budget expiration.
  - `BUDGET_EXHAUSTED` / `MAXIMUM_CYCLES_REACHED`: Operational budget limits reached.

### 9G: Human Oversight & Autonomy Modes
- **Autonomy Modes**:
  - `bounded`: Fully autonomous within configured budgets.
  - `supervised`: Executes autonomously but pauses at cycle checkpoints for user inspection.
  - `assisted`: Generates planned actions into `awaiting_approval` state, requiring one-click researcher approval or rejection before executing searches.
- Dedicated endpoints:
  - `POST /research/autonomous/workflows/{id}/actions/{action_id}/approve`
  - `POST /research/autonomous/workflows/{id}/actions/{action_id}/reject`

### 9H: Durable Execution & Startup Crash Recovery
- Alembic migration `20261114_0012_autonomous_workflow_engine_m9.py` adds:
  - `autonomous_research_workflows`
  - `research_workflow_cycles`
  - `research_actions`
  - `research_workflow_checkpoints`
  - `research_query_histories`
  - `research_workflow_reports`
- **Startup Recovery**: `recover_workflows(session_factory)` is integrated into FastAPI `lifespan`. Any workflow interrupted by a server restart is automatically transitioned to `paused` with a `recovery` checkpoint, allowing one-click resumption.

### 9I: Autonomous Research Workspace
- Available at `/autonomous` (and linked from the sidebar navigation and investigation details):
  - **Dashboard**: Workflows table with status indicators, cycle progress, and budget metrics.
  - **Create Modal**: Configurable autonomy mode, cycle/search/source budgets.
  - **Live Monitor**: Active cycle timeline, action cards, query inspect, information gain scores.
  - **Human Review Queue**: Interactive banner and action approval/rejection modal.
  - **Synthesized Report Viewer**: Full executive summary, cycle findings, persistent contradictions, and research horizon recommendations.

### 9J: Knowledge Graph Integration
Implemented in `backend/app/routers/graph.py` and `lib/graph.ts`:
- **Nodes**:
  - `autonomous_workflow` (Node color: `#f59e0b`)
  - `research_cycle` (Node color: `#38bdf8`)
  - `research_action` (Node color: `#ec4899`)
- **Grounded Edges**:
  - `investigates`: Workflow -> Investigation
  - `executes_cycle`: Workflow -> Cycle
  - `performs_action`: Cycle -> Action
  - `targets_claim`: Action -> Claim
  - `targets_gap`: Action -> Gap
  - `targets_hypothesis`: Action -> Hypothesis

---

## 2. API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/research/autonomous/workflows` | Create a new autonomous workflow |
| `GET` | `/api/v1/research/autonomous/workflows` | List workflows (optional `investigation_id` filter) |
| `GET` | `/api/v1/research/autonomous/workflows/{id}` | Get workflow details with cycles and actions |
| `POST` | `/api/v1/research/autonomous/workflows/{id}/start` | Start workflow execution |
| `POST` | `/api/v1/research/autonomous/workflows/{id}/pause` | Pause active workflow |
| `POST` | `/api/v1/research/autonomous/workflows/{id}/resume` | Resume paused workflow |
| `POST` | `/api/v1/research/autonomous/workflows/{id}/cancel` | Cancel workflow |
| `GET` | `/api/v1/research/autonomous/workflows/{id}/cycles` | List cycle history for workflow |
| `GET` | `/api/v1/research/autonomous/workflows/{id}/actions` | List planned/executed actions |
| `POST` | `/api/v1/research/autonomous/workflows/{id}/actions/{id}/approve` | Approve action in assisted mode |
| `POST` | `/api/v1/research/autonomous/workflows/{id}/actions/{id}/reject` | Reject action with notes |
| `GET` | `/api/v1/research/autonomous/workflows/{id}/report` | Retrieve final synthesized report |
| `POST` | `/api/v1/research/autonomous/workflows/{id}/continue` | Grant additional cycles to stopped workflow |

---

## 3. Verification & Test Coverage

All tests pass with 100% success rate:
- **`backend/tests/test_autonomous_workflows.py`**:
  - `test_research_planner_action_formulation_and_prioritization`: Verified deterministic action formulation, dependency ordering, and priority sorting.
  - `test_query_deduplication_and_similarity`: Verified token overlap and Jaccard similarity deduplication.
  - `test_provider_specific_query_adaptation`: Verified syntax adaptation across arXiv, OpenAlex, Tavily.
  - `test_counter_evidence_query_formulation`: Verified deliberate skeptic probes.
  - `test_stopping_criteria_evaluation`: Verified cycle budget exhaustion, diminishing returns, and contradiction persistence.
  - `test_recover_workflows_on_startup`: Verified crash recovery transitions in-flight workflows to paused with checkpoints.
  - `test_workflow_lifecycle_and_assisted_oversight`: Verified assisted mode approval/rejection and continuation.
  - `test_autonomous_workflow_api_endpoints`: Verified full REST API CRUD integration.
  - `test_knowledge_graph_workflow_nodes_and_edges`: Verified graph node types and grounded edges.
- **Frontend Quality**:
  - `npx tsc --noEmit`: 0 TypeScript errors.
  - `npm test`: 9 passing unit tests.
  - `npm run build`: Production build succeeded with all 18 routes compiled.
