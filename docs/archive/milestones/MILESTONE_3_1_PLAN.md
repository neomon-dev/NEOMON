# NEOMON Milestone 3.1 Plan

## Audit findings

- `query_planner.py` currently repeats the complete question with generic suffixes.
- Provider adapters preserve provider order and snippets but do not evaluate whether a result addresses the question's subject.
- `deduplicate_results` removes duplicates by URL, DOI, and title, but does not score or explain relevance.
- HTML retrieval currently appends nearly all visible body text, including navigation, publisher chrome, forms, and boilerplate.
- PDF retrieval flattens all pages into one string and loses page provenance.
- Evidence extraction uses a two-token lexical overlap rule and labels every match as `contextual`; it does not reject boilerplate, distinguish findings, or retain document IDs.
- Sources, documents, and evidence do not currently expose relevance, access level, extraction quality, or rejection reasons.
- The frontend displays all sources and passages without quality filtering or inclusion explanations.

## Milestone 3.1 architecture

1. Generate a small set of complementary queries from the existing question and mode.
2. Normalize and score every provider result with an explainable, domain-neutral relevance evaluator:
   - question-term coverage,
   - subject-term coverage,
   - outcome/relationship coverage,
   - publication/source metadata,
   - abstract/full-text availability,
   - timeframe match.
3. Persist both accepted and filtered sources with scores and reasons. Only accepted sources enter retrieval and evidence extraction.
4. Retrieve documents through the existing SSRF-safe boundary. Parse semantic article/main content, remove structural boilerplate, and preserve HTML sections or PDF page passages.
5. Classify access as metadata-only, abstract-only, or full-text and assign extraction quality.
6. Extract only meaningful, traceable passages. Preserve exact text, page/section provenance, document ID, evidence type, and an explanation.
7. Compute investigation quality indicators from relevant sources, accessible documents, evidence traceability, source diversity, and unresolved provider/retrieval gaps.
8. Expose quality fields through the existing versioned API and add frontend filters for source and evidence quality.

## Database changes

Add non-destructive nullable/defaulted fields to existing tables:

- Investigation: quality status, quality summary, relevant source count, full-text count, evidence gap.
- Source: relevance score/reasons, inclusion status, rejection reason.
- Document: access level and extraction quality.
- Evidence: document ID, relevance explanation, and traceability flag.

No existing records are deleted or rewritten.

## Testing strategy

- Unit fixtures for relevant software-engineering research, unrelated medical research, publisher chrome, contradictory findings, metadata-only results, multi-page PDFs, and methodology limitations.
- Regression tests for ranking, boilerplate removal, exact quotation preservation, access-level labeling, page provenance, evidence classification, and quality gates.
- API tests for quality fields and persisted filtered sources.
- Repeat the original AI/software-productivity investigation and inspect relevant-source and evidence counts rather than target source count.

## Scope boundary

This milestone does not add model-generated semantic judgments or replace the provider abstraction. Relevance and extraction remain deterministic and explainable; model-assisted adjudication and claim decomposition remain future work.
