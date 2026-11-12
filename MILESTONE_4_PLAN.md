# NEOMON Milestone 4 Plan

## Existing architecture

NEOMON currently has a Next.js investigation UI, a FastAPI `/api/v1` backend,
SQLAlchemy/Alembic persistence, a provider-independent research pipeline, safe
document retrieval, relevance scoring, evidence extraction, open-access
acquisition, and an in-memory SSE broker. The existing twelve agent modules are
typed foundations: they expose a common `BaseAgent`, but provider completion is
not yet implemented and agent output is not persisted.

Milestone 4 adds a bounded analysis layer around the completed research engine.
The existing source, document, evidence, claim, provider, and retrieval records
remain the system of record.

## Agent responsibilities and flow

1. Planner creates distinct atomic claims and research tasks.
2. Advocate and Skeptic independently produce evidence references from persisted
   evidence; they may identify an evidence gap but cannot create evidence.
3. Methodology, Source, Citation Genealogy, and Temporal agents add structured
   qualifications from persisted records.
4. Moderator creates at most the configured number of debate rounds and records
   unresolved disagreements.
5. Adjudicator compares arguments and preserves inconclusive findings.
6. Report agent assembles a report only from validated persisted claims,
   arguments, evidence, and decisions.

The default is two debate rounds, sequential execution, one concurrent agent,
and bounded per-agent timeouts. Parallel execution is available through an
explicit concurrency limit.

## Shared evidence protocol

Pydantic schemas validate claims, arguments, debate rounds, decisions, and
report sections. Argument evidence IDs and source IDs are checked against the
investigation before persistence. Invalid IDs, malformed structured output, and
ungrounded report citations fail that unit without deleting successful work.
Only concise reasoning summaries are stored; private chain-of-thought is never
requested or exposed.

## LLM integration

The existing Ollama, LM Studio, and OpenAI-compatible provider abstraction will
gain structured JSON completion with model selection, timeout, retries, and
usage metadata where a provider returns it. Provider configuration is supplied
per role with a shared default, so local systems do not need ten models.
Deterministic rule-based evidence grounding remains available when no model is
configured; it reports its mode honestly and never fabricates findings.

## Persistence and recovery

New non-destructive tables will represent analysis jobs, role executions,
validated arguments, debate rounds, adjudication decisions, and report
sections. Job status is separate from investigation research quality. Unique
active-job constraints prevent duplicate runs. Each stage commits progress so a
restart leaves a recoverable audit trail. Cancellation is persisted and checked
between bounded stages.

## API and frontend

Versioned routes will start, inspect, and cancel analysis; list executions,
claims, arguments, debate rounds, decisions, and report sections. Events are
persisted as research events and published through the existing broker. The
investigation page will add Agent Activity, Evidence Debate, and Report panels,
with refresh-safe polling/SSE updates and links to source/evidence provenance.

## Failure and resource handling

Individual agent failures become warnings and do not erase completed stages.
Planner, adjudicator, and report failures make the job incomplete rather than
producing a success-shaped fallback. Timeouts, cancellation, provider errors,
invalid JSON, nonexistent evidence references, and token/request budget
exhaustion are explicit execution errors.

## Testing strategy

- Unit-test claim distinctness, evidence-ID validation, report citation
  validation, temporal/source/methodology rules, and debate limits.
- Mock provider JSON responses for successful, malformed, timed-out, and
  unavailable models.
- Test job persistence, cancellation, restart recovery, isolation, and
  concurrency limits with SQLite.
- Test API response contracts, SSE event payloads, and frontend rendering.
- Preserve and rerun all Milestone 3, 3.1, and 3.2 tests.
- Run the requested software-productivity question and report actual evidence
  coverage, disagreements, and limitations without manufacturing agent output.
