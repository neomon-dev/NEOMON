# NEOMON Milestone 3.2 Plan

## Audit findings

- `SearchResult` currently has one URL and DOI/title metadata but no open-access locations or version type.
- OpenAlex search currently discards `open_access`, `locations`, and repository metadata after selecting a landing page.
- Crossref, arXiv, and Tavily results do not expose alternate full-text locations.
- `Source` identifies an investigation result, while `Document` stores retrieved content, but there is no explicit document version or source/document relationship.
- The existing retrieval layer already validates public hosts, redirects, content types, size, timeouts, and PDF extraction.
- The research service currently attempts only `source.original_url`; it falls back to provider snippets as abstract-only content.
- Existing relevance, evidence provenance, quality gates, and frontend access labels can be reused.

## Architecture

1. Normalize provider results into source identity plus zero or more `OpenAccessLocation` records.
2. Discover locations from OpenAlex metadata and optional Unpaywall, while retaining the DOI/publisher URL.
3. Verify candidate location metadata before retrieval:
   - DOI, normalized title, authors, and publication year where available.
   - Reject candidates whose metadata does not sufficiently match the source.
4. Rank legal candidates in this order:
   - publisher-hosted open access,
   - institutional repository,
   - recognized repository/preprint,
   - other declared open-access copy.
5. Reuse SSRF-safe retrieval for the selected candidate, preserving the original source URL and selected version URL.
6. Store document versions separately from source identity and create links between versions sharing a DOI or strong metadata identity.
7. Leave abstract/metadata-only records intact when every candidate is inaccessible, with explicit failure reasons.

## Data model

Add non-destructive fields/tables:

- `Source`: open-access discovery status, version relationship key, and selected document URL.
- `Document`: document URL, version type, access route, and source metadata match status.
- `DocumentVersionRelationship`: links preprints, accepted manuscripts, repository copies, and published versions without counting them as independent sources.
- `OpenAccessLocation`: persisted candidate URL, repository, version type, license, metadata match, status, and failure reason.

Existing source and evidence rows remain valid.

## Configuration

- `NEOMON_UNPAYWALL_EMAIL` enables polite Unpaywall lookup.
- `NEOMON_UNPAYWALL_API_KEY` is optional and never exposed to the frontend.
- OpenAlex and arXiv remain keyless.

## Testing

- Mock OpenAlex locations and Unpaywall responses.
- Test DOI/title/author/year matching and rejection of unrelated PDFs.
- Test preprint/published version grouping and duplicate study identity.
- Test repository timeouts, 403 responses, SSRF rejection, PDF provenance, and persistence.
- Run the original AI/software-productivity investigation and report relevant sources, document access levels, independent study relationships, evidence, and failures.

## Scope boundary

This milestone does not bypass access controls, infer licensing when metadata is absent, or claim that a repository copy is an independent study. Full semantic study-level deduplication remains conservative and metadata-based.
