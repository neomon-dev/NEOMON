# NEOMON Milestone 7A — Research Reliability & Local LLM Orchestration

## Executive Overview

Milestone 7A hardens NEOMON's research execution engine for autonomous multi-agent operation, specifically addressing the unique resource constraints and serialization requirements of local LLM backends (LM Studio and Ollama on consumer hardware) while maintaining high-concurrency throughput for cloud providers.

**Tagline:** "Every claim is questioned. Every source is traced. Every conclusion is earned."

---

## Architecture & Implementation

### 1. Dual-Timeout Concurrency Limiter & Bounded Queues
- **Separated Deadlines**:
  - `queue_timeout_seconds` (default 300s): Enforces maximum time an agent can wait in line for inference capacity before raising `ProviderQueueTimeoutError`.
  - `inference_timeout_seconds` (default 120s): Enforces maximum active token generation duration before raising `ProviderRequestError`.
- **Bounded Capacity**: Provider queues reject overflow requests beyond `provider_queue_max_size` (default 50) with `ProviderQueueFullError`.
- **Queue Position & Duration Telemetry**: `QueueLease` tracks FIFO `queue_position` and registers transition events (`waiting_in_queue` -> `generating` -> release) via `InferenceStateCallback`.

### 2. Local Provider Sequential Scheduling
- When `is_local_provider` is detected (`lm_studio`, `ollama`, or `allow_local_runtime` with `max_concurrency == 1`):
  - Specialist agents execute sequentially: `Advocate` -> `Skeptic` -> `Methodology Auditor` -> `Source Intelligence` -> `Citation Genealogy` -> `Temporal Intelligence`.
  - Eliminates lock contention, queue wait timeouts, and out-of-order evaluation on consumer GPUs (e.g., Intel Arc, Apple Silicon, single-GPU setups).

### 3. Bounded Argument & Decision Repair
- **Evidence Provenance Validation**: Validates all evidence IDs against persisted investigation evidence, strips hallucinated/fabricated IDs, and recomputes valid source IDs.
- **Claim Preservation**: If a specialist LLM omits claims or makes formatting errors on a subset, grounded fallback arguments are synthesized for the missing claims without discarding valid arguments.
- **Consistency Verification**: `ConflictAdjudicator` requires documented conflicting evidence for `contradictory` decisions and at least one evidence ID for `supported` decisions.

### 4. Fallback Report Generation & Graceful Degradation
- When LLM report synthesis encounters an unrecoverable provider error (HTTP 400/500, schema mismatch, or timeout):
  - Synthesizes an 18-section structured report from persisted claims, specialist arguments, debate rounds, and adjudication decisions.
  - Sets job status to `completed_with_warnings`.
  - Completely prevents investigation failures after research and evidence extraction have succeeded.

### 5. Multi-Agent Coverage Telemetry
- Computes `AnalysisCoverageSummary`:
  - Required vs completed vs failed/skipped agents across all 10 roles.
  - Claims evaluated, claims without arguments/evidence, claims with supporting vs conflicting evidence.
  - Overall coverage percentage and `is_partially_completed` flag.
  - Displayed prominently in the investigation workspace UI.

---

## Verification & Test Results
- **Backend Tests**: 65 unit and integration tests passing (`pytest tests/`).
  - Added `backend/tests/test_reliability_orchestration.py` verifying bounded queues, timeout separation, queue position telemetry, fallback report generation, and coverage calculation.
- **Frontend Verification**: TypeScript type-check (`tsc --noEmit`) and Node test suite passing with 0 errors.
