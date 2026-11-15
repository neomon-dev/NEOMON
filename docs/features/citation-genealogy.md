# Feature Specification: Citation Genealogy & Study Independence Engine

## 1. Feature Overview
The **Citation Genealogy & Study Independence Engine** inspects research literature networks to detect citation incest, shared primary datasets, author group overlap, and institutional dependencies. It clusters related publications to compute an empirical **Study Independence Score**, preventing the artificial inflation of scientific consensus when multiple papers merely cite the same underlying preliminary dataset.

## 2. Purpose and Problem Solved
A widespread failure mode in scientific research synthesis is the illusion of independent replication: twenty news articles or review papers may claim a breakthrough, but all twenty trace back to a single 12-patient pilot study. The Citation Genealogy engine eliminates this false consensus:
- Maps citation trees and lineage relationships among indexed sources.
- Detects shared primary clinical trials or common patient registries across multiple publications.
- Flags author and lab overlaps between seemingly independent papers.
- Adjusts overall confidence down if "corroborating" studies are actually derivative re-analyses of one primary paper.

## 3. Where Users Access It
- **In-Investigation**: "Study Independence" section under the Overview and Quality tabs on `/investigations/[id]`.
- **Source Inspector**: Lineage Drawer on `/sources`.
- **Knowledge Graph**: "Lineage" and "Shared Primary Dataset" edge filters on `/graph`.

## 4. Step-by-Step User Workflow
1. Navigate to an investigation on `/investigations/[id]`.
2. Locate the **Study Independence & Lineage Card**:
   - **Independence Score**: Value from `0.0` (all papers derive from a single lab/dataset) to `1.0` (completely independent multi-institution replications).
   - **Primary Clusters**: Number of distinct empirical clusters identified.
3. Review the **Independence Breakdown**:
   - Primary empirical studies vs. derivative systematic reviews.
   - Author co-occurrence graph.
   - Shared data repository identifiers (e.g. ClinicalTrials.gov identifiers, GenBank accession numbers, figshare IDs).
4. Inspect **Lineage Relationships**:
   - Click a source to view its genealogical parents (sources it cites) and genealogical children (sources that cite it).
   - View relationship classification: `replicates`, `derives_from`, `critiques`, `re-analyzes`.

## 5. How the Feature Works Internally
1. When sources are retrieved, metadata is extracted from Crossref and OpenAlex:
   - Reference lists (cited DOIs).
   - Author names, ORCID identifiers, and institutional affiliations.
   - Clinical trial registration numbers (e.g. `NCT04321098`).
2. The `app.analysis.study_independence_service` constructs an undirected dependency graph among sources:
   - An edge is created if two sources share $\ge 2$ authors or reference the same primary trial ID.
3. **Clustering Algorithm**:
   - Connected components in the dependency graph are merged into `study_independence_clusters`.
4. **Independence Calculation**:
   $$\text{Independence Score} = \frac{\text{Number of Independent Clusters}}{\text{Total Indexed Sources}}$$
5. Relationships are persisted in `source_lineage_relationships`.

## 6. Relevant Frontend Pages and Components
- `app/investigations/[id]/page.tsx`: Displays independence score meters and cluster summaries.
- `components/source-intelligence.tsx`: Displays lineage badges on individual source cards.
- `components/graph-detail-panel.tsx`: Renders lineage connections and shared trial IDs in the inspector.

## 7. Relevant Backend Routes and Endpoints
- `GET /api/v1/research/study-independence/{investigation_id}`: Retrieves independence clusters and scores.
- `GET /api/v1/research/study-independence/lineage/{source_id}`: Fetches direct lineage relationships for a specific source.
- `POST /api/v1/research/study-independence/{investigation_id}/cluster`: Re-runs cluster analysis.

## 8. Relevant Services and Agents
- `app.analysis.study_independence_service`: Graph clustering, author overlap detection, and independence scoring.
- `app.research.normalization`: DOI and clinical trial ID normalizer.

## 9. Database Tables and Relationships
- `source_lineage_relationships`: Stores `id`, `source_id`, `related_source_id`, `relationship_type`, `confidence`, `shared_identifiers_json`, `explanation`.
- `study_independence_clusters`: Stores `id`, `investigation_id`, `cluster_name`, `cluster_type`, `sources_count`, `source_ids_json`.
- `sources`: Literature entities linked by lineage.

## 10. Inputs and Outputs
- **Input**: `investigation_id` (UUID).
- **Output (`StudyIndependenceResponse`)**:
  ```json
  {
    "investigation_id": "UUID",
    "independence_score": 0.82,
    "total_sources": 10,
    "cluster_count": 8,
    "clusters": [
      {
        "id": "UUID",
        "cluster_name": "STEP-1 Trial Family",
        "cluster_type": "clinical_trial_registry",
        "sources_count": 3
      }
    ]
  }
  ```

## 11. AI Provider Dependencies
None. Lineage extraction and clustering are 100% deterministic, operating over metadata matching and graph community detection.

## 12. External API Dependencies
Utilizes citation lists and author affiliations retrieved via Crossref and OpenAlex during initial source discovery.

## 13. Configuration Requirements
- `NEOMON_DATABASE_URL`: Relational database connection.

## 14. Error Handling and Limitations
- **Preprints without DOIs**: Sources lacking official DOIs are matched via normalized title levenshtein similarity and author surnames.
- **Single Source**: If an investigation has only 1 source, independence score is defined as `1.0` with a notice indicating single-source limitation.

## 15. Security and Permission Considerations
- Read-only for all authorized workspace members.
- Clustering computation is cached in the database to prevent duplicate computational load.

## 16. Related Features and Dependencies
- **Evidence Quality** (`docs/features/evidence-quality.md`): Calibrated quality score penalizes investigations with low independence scores.
- **Knowledge Graph** (`docs/features/knowledge-graph.md`): Lineage edges are visualized directly in the graph canvas.

## 17. Relevant Tests and How to Run Them
- **Backend Tests**:
  - `python -m pytest backend/tests/test_study_independence.py -q`
