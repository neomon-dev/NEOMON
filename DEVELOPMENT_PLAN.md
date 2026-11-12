# NEOMON Development Plan

## Audit result (2026-11-12)

The local `NEOMON` directory and the `neomon-dev/NEOMON` GitHub repository were empty. There was no existing frontend, backend, package manifest, database, AI integration, test suite, Git branch, or remote configuration to preserve. This is therefore a greenfield foundation, not a migration.

## Milestones

1. **Milestone 0 — Audit and documentation**: complete. Record the empty baseline and the target architecture.
2. **Milestone 1 — Foundation**: initial slice complete. Establish a runnable Next.js TypeScript dashboard shell, navigation, configuration template, and project scripts. Backend integration and persistence remain intentionally deferred.
3. **Milestone 2 — Backend and AI infrastructure**: initial slice complete. Add FastAPI `/api/v1`, provider adapters, twelve agent foundations, SQLAlchemy/Alembic schema, SSE broker, demo mode, and frontend health/provider integration.
4. **Milestone 3 — Research engine**: initial slice complete. Add real academic/web search, source retrieval, evidence extraction, normalization, persistence, SSE events, and investigation UI.
5. **Milestone 4 — Multi-agent intelligence**: add claim decomposition through configured models and bounded planner/explorer/collector orchestration.
6. **Milestone 5 — Knowledge graph**: persist and render evidence-derived provenance relationships.
7. **Milestone 6 — Live intelligence**: add backend events and SSE monitoring.
8. **Milestone 7 — Report engine**: add transparent assessments, references, and exports.
9. **Milestone 8 — Quality and deployment**: test, secure, containerize, and document deployment.

## Delivery rules

- Implement one milestone at a time and verify it before expanding scope.
- Keep provider credentials server-side and treat retrieved documents as untrusted input.
- Do not label heuristic evidence scores as probabilities.
- Keep demo mode explicit; never fabricate research results or citations.
- Keep provider credentials server-side and report connection failures explicitly.
