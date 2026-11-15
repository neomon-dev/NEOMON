# Feature Specification: Source Discovery & Academic Normalization

## 1. Feature Overview
The **Source Discovery & Normalization Engine** manages the retrieval, indexing, content hashing, and classification of primary academic and web literature. It queries multiple independent scholarly databases (arXiv, Crossref, OpenAlex, PubMed/Europe PMC) and optional real-time web search (Tavily), harmonizing heterogeneous metadata into uniform, verifiable source records.

> [!NOTE]
> **TAVILY API INTEGRATION**: Tavily is an optional web search provider. Academic repositories (arXiv, Crossref, OpenAlex, PubMed) are open-access and operate without paid subscriptions. If web search is desired, users must configure `TAVILY_API_KEY` or `NEOMON_TAVILY_API_KEY`.

## 2. Purpose and Problem Solved
Generic AI tools synthesize knowledge from unverified training data, resulting in hallucinated claims and dead citations. The Source Discovery engine ensures every claim in NEOMON is anchored in actual retrieved documents with verifiable provenance:
- Normalizes disparate academic metadata formats into a unified schema.
- Assigns cryptographic SHA-256 hashes to raw documents to guarantee audit immutability.
- Discovers open-access PDF/HTML full-text links via Unpaywall and Europe PMC.
- Eliminates duplicate records across repositories using canonical URLs and DOIs.

## 3. Where Users Access It
- **Dedicated Route**: `/sources` (Source Intelligence Library).
- **In-Investigation**: Sources tab on `/investigations/[id]`.
- **Knowledge Graph**: Source nodes on `/graph`.

## 4. Step-by-Step User Workflow
1. Navigate to `/sources`.
2. Inspect the **Source Intelligence Overview**:
   - Total indexed sources count.
   - Domain breakdown (e.g., `arxiv.org`, `nature.com`, `ncbi.nlm.nih.gov`).
   - Verification status distribution (`verified`, `unverified`, `peer_reviewed`).
3. Search and filter sources:
   - Enter text into the search box to match titles, publishers, or authors.
   - Filter by **Credibility Tier**: All, Tier 1 (Peer-Reviewed Major Journal), Tier 2 (Preprint / Conference), Tier 3 (Web Source).
   - Filter by **Specific Investigation**.
4. Click any source card or table row:
   - View full citation details, publication date, authors list, and DOI.
   - Inspect the SHA-256 content hash and retrieval timestamp.
   - Click the external link button to view the original publication.

## 5. How the Feature Works Internally
1. When queries are dispatched during research orchestration, client adapters fetch results:
   - **arXiv**: Queries arXiv API via Atom feed; extracts arXiv ID, PDF links, and abstracts.
   - **Crossref**: Queries Crossref REST API; resolves DOIs, journal venues, and publication years.
   - **OpenAlex**: Resolves concepts, citation counts, and open-access locations.
   - **Europe PMC**: Fetches biomedical citations and full-text PMCID links.
   - **Tavily**: Executes semantic web search if API key is provided.
2. Results are converted into `SourceCandidate` structures.
3. The normalizer computes canonical URLs, strips tracking parameters, and checks for existing records in the database.
4. For new sources, raw text/HTML is fetched (within the 5MB size limit), hashed via SHA-256, and persisted into the `sources` and `documents` tables.

## 6. Relevant Frontend Pages and Components
- `app/sources/page.tsx`: Full-screen Source Intelligence dashboard.
- `components/source-intelligence.tsx`: Reusable source grid and credibility viewer.
- `components/graph-detail-panel.tsx`: Source node inspector within the Knowledge Graph.

## 7. Relevant Backend Routes and Endpoints
- `GET /api/v1/research/sources`: Returns paginated, searchable sources for the active workspace.
- `GET /api/v1/research/sources/{id}`: Returns single source metadata and associated document text.
- `GET /api/v1/research/investigations/{id}/sources`: Fetches sources belonging to a specific investigation.

## 8. Relevant Services and Agents
- `app.research.retrieval`: Adapters for arXiv, Crossref, OpenAlex, PubMed, and Tavily.
- `app.research.normalization`: DOI cleaner, URL canonicalizer, and content hasher.
- `app.research.service`: Source persistence and relational linking.

## 9. Database Tables and Relationships
- `sources`: Stores `id`, `investigation_id`, `title`, `canonical_url`, `original_url`, `source_type`, `publisher`, `authors_json`, `publication_date`, `doi`, `content_hash`, `retrieval_timestamp`.
- `documents`: Stores raw full-text `content`, `headings_json`, `page_count`, linked to `sources.id` (1:1 or 1:N).
- `evidence`: Linked to `sources.id` via `source_id`.

## 10. Inputs and Outputs
- **Query Filter**:
  `GET /api/v1/research/sources?q=superconductivity&limit=20&offset=0&investigation_id=<UUID>`
- **Response**: Array of `SourceResponse` objects containing full bibliographic details, credibility ratings, and linked evidence counts.

## 11. AI Provider Dependencies
None for basic retrieval and normalization. Model providers are optionally used during claim extraction from raw document text.

## 12. External API Dependencies
- Public Academic Endpoints (No API key required):
  - arXiv API (`http://export.arxiv.org/api/query`)
  - Crossref API (`https://api.crossref.org/works`)
  - OpenAlex API (`https://api.openalex.org/works`)
  - Europe PMC API (`https://www.ebi.ac.uk/europepmc/webservices/rest/search`)
- Optional Web API:
  - Tavily Search (`https://api.tavily.com/search`)

## 13. Configuration Requirements
- `TAVILY_API_KEY` / `NEOMON_TAVILY_API_KEY`: Optional key for web search.
- `NEOMON_RESEARCH_USER_AGENT`: User agent string compliant with Crossref and arXiv API policies.
- `NEOMON_UNPAYWALL_EMAIL`: Optional email for enhanced Unpaywall open-access resolution.

## 14. Error Handling and Limitations
- **Rate Limits**: Academic APIs (especially arXiv) enforce rate limits. The engine implements backoff retry queues and graceful degradation.
- **Paywalled Papers**: When full text cannot be legally retrieved without credentials, the engine indexes abstracts and metadata, marking `access_level="metadata_only"`.

## 15. Security and Permission Considerations
- SSRF Safeguard: External retrieval disallows loopback IPs and internal network ranges.
- Content Verification: The SHA-256 `content_hash` ensures documents cannot be silently swapped or modified in the database.

## 16. Related Features and Dependencies
- **Evidence Workspace** (`docs/features/evidence-workspace.md`): Evidence passages are extracted directly from indexed sources.
- **Citation Genealogy** (`docs/features/citation-genealogy.md`): Lineage and independence clustering operates over sources.

## 17. Relevant Tests and How to Run Them
- **Backend Tests**:
  - `python -m pytest backend/tests/test_research_engine.py -q`
  - `python -m pytest backend/tests/test_tavily_provider.py -q`
