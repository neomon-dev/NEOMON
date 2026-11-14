# NEOMON Development Plan

## Audit result (2026-11-12)

The local `NEOMON` directory and the `neomon-dev/NEOMON` GitHub repository were empty. There was no existing frontend, backend, package manifest, database, AI integration, test suite, Git branch, or remote configuration to preserve. This is therefore a greenfield foundation, not a migration.

## Milestones

1. **Milestone 0 — Audit and documentation**: complete. Record the empty baseline and the target architecture.
2. **Milestone 1 — Foundation**: initial slice complete. Establish a runnable Next.js TypeScript dashboard shell, navigation, configuration template, and project scripts. Backend integration and persistence remain intentionally deferred.
3. **Milestone 2 — Backend and AI infrastructure**: initial slice complete. Add FastAPI `/api/v1`, provider adapters, twelve agent foundations, SQLAlchemy/Alembic schema, SSE broker, demo mode, and frontend health/provider integration.
4. **Milestone 3 — Research engine**: initial slice complete. Add real academic/web search, source retrieval, evidence extraction, normalization, persistence, SSE events, and investigation UI.
5. **Milestone 5 — MVP Completion**: complete. Bounded multi-agent debates (Advocate/Skeptic/Adjudicator), SSRF protection, live investigation monitoring, and persisted SSE replay.
6. **Milestone 6 — Evidence Intelligence & Interactive Knowledge Graph**: complete. Evidence Explorer (`/evidence`), Source Intelligence (`/sources`), Agent Observatory (`/agents`), and React Flow Knowledge Graph (`/graph`).
7. **Milestone 7 — Research Reliability, Report Intelligence & Knowledge Export**: complete. Local concurrency limiter (7A), 18-section academic reports (7B), and 9 standard export formats (7C).
8. **Milestone 8A–8F — Advanced Research Intelligence System**: complete. Autonomous research gaps (8A), hypothesis generation (8B), cross-investigation synthesis (8C), contradiction intelligence (8D), longitudinal research trends (8E), and unified research intelligence hub (8F).
9. **Milestone 8G — Research Quality Calibration & Scientific Evidence Validation**: complete. Unified canonical credibility (8G.1), publication lineage and explainable independence (8G.2), evidence-to-claim entailment validation (8G.3), calibrated 5D scoring and coverage separation (8G.4), provider failure penalties (8G.5), Scientific Quality Audit Workspace (`/quality-audit`, 8G.6), and export integration across all 9 formats (8G.7).
10. **Milestone 9 — Autonomous Research Workflow Engine**: complete. Persistent 15-state machine (9A), deterministic research planning (9B), adaptive query refinement and counter-evidence probes (9C), iterative evidence calibration (9D), budget constraints (9E), scientific stopping criteria (9F), human oversight modes and review queue (9G), startup crash recovery (9H), `/autonomous` workspace (9I), and knowledge graph integration (9J).
11. **Milestone 10 — Production Deployment & Autonomous Monitoring**: containerization, periodic background literature re-evaluation, and production operations.

## Delivery rules

- Implement one milestone at a time and verify it before expanding scope.
- Keep provider credentials server-side and treat retrieved documents as untrusted input.
- Do not label heuristic evidence scores as probabilities.
- Keep demo mode explicit; never fabricate research results or citations.
- Keep provider credentials server-side and report connection failures explicitly.
