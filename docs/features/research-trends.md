# Feature Specification: Longitudinal Research Trend Intelligence

## 1. Feature Overview
The **Research Trend Intelligence Engine** (`/trends`) tracks longitudinal scientific shifts, topic momentum, and emerging concepts across workspace literature. It models research topics along a four-stage evolutionary trajectory: **Emerging Topic**, **Rapid Growth**, **Established Consensus**, and **Saturated / Declining**, generating empirical momentum scores and strategic recommendations for researchers and grant writers.

## 2. Purpose and Problem Solved
Researchers often struggle to identify whether a topic is an emerging paradigm, an established field with incremental progress, or a saturated topic with diminishing returns. The Trend Intelligence engine provides empirical clarity:
- Computes publication velocity and citation momentum.
- Identifies newly co-occurring keyword clusters across recent literature.
- Classifies topics into standard bibliometric lifecycle phases.
- Generates strategic recommendations: highlighting under-explored niches within established domains.

## 3. Where Users Access It
- **Dedicated Route**: `/trends` (Research Trend Intelligence Workspace).
- **Navigation**: "Trend intelligence" link in the primary sidebar navigation.
- **Knowledge Graph**: Trend topic nodes and classification filters on `/graph`.

## 4. Step-by-Step User Workflow
1. Navigate to `/trends`.
2. Inspect the **Trend Intelligence Overview**:
   - Total tracked longitudinal topic trajectories.
   - Stage distribution: Emerging, Rapid Growth, Established, Saturated.
   - Average field velocity and momentum metrics.
3. Click **"Run Trend Analysis"**:
   - Triggers a longitudinal scan across all indexed sources, publication dates, and concept frequencies.
4. Review **Topic Trajectory Cards**:
   - Topic name and classification tag (e.g., `Emerging Topic`, `Rapid Growth`).
   - Momentum score (e.g., `+78% velocity YoY`).
   - Primary publication timeline and representative papers.
   - Strategic recommendation: actionable guidance on whether to initiate new research or seek novel intersections.
5. Filter by Trajectory Stage:
   - Toggle filters to view exclusively `Emerging Topics` to discover novel research frontiers.

## 5. How the Feature Works Internally
1. The `app.analysis.trend_service`:
   - Extracts publication dates and normalized keywords/concepts from all indexed sources in the workspace.
   - Analyzes frequency distributions across time buckets (e.g. past 1 year, 3 years, 5 years, 10 years).
   - Computes annual growth rate and acceleration:
     $$\text{Momentum Score} = \frac{\Delta \text{Volume}_{\text{recent}}}{\text{Volume}_{\text{historical}}} \times \text{Citation Multiplier}$$
2. Topic Classification:
   - `emerging_topic`: Low historical volume, high recent acceleration ($\ge +50\%$).
   - `rapid_growth`: High volume, strong upward acceleration.
   - `established`: High stable volume, moderate growth.
   - `saturated`: High volume, negative growth or declining citations.
3. Results are saved into `research_trend_analyses` and `research_trend_topics`.
4. Renders interactive topic cards and trajectory trend lines.

## 6. Relevant Frontend Pages and Components
- `app/trends/page.tsx`: Full Trend Intelligence page container.
- `components/research-trends-workspace.tsx`: Trend overview cards, trajectory filters, and execution button.

## 7. Relevant Backend Routes and Endpoints
- `GET /api/v1/research/trends/latest`: Returns the most recently computed trend intelligence report (generates on-demand if none exists).
- `POST /api/v1/research/trends/analyze`: Triggers a comprehensive re-analysis across workspace sources.
- `GET /api/v1/research/trends`: Returns paginated historical trend analyses.

## 8. Relevant Services and Agents
- `app.analysis.trend_service.TrendIntelligenceEngine`: Longitudinal statistical analysis service.
- `app.agents.synthesizer`: AI agent providing strategic qualitative research recommendations.

## 9. Database Tables and Relationships
- `research_trend_analyses`: Stores analysis run metadata (`id`, `workspace_id`, `topics_count`, `summary`, `created_at`).
- `research_trend_topics`: Stores individual topics (`id`, `analysis_id`, `topic_name`, `classification`, `momentum_score`, `timeline_data_json`, `recommendation`).

## 10. Inputs and Outputs
- **Analysis Request (`ResearchTrendAnalyzeRequest`)**:
  ```json
  {
    "provider_kind": "optional model override",
    "temperature": 0.2
  }
  ```
  *(Endpoint supports empty body via `Body(default=None)`)*.
- **Analysis Response (`ResearchTrendAnalysisResponse`)**:
  JSON object with analysis UUID, timestamp, executive trend summary, and array of classified topic items.

## 11. AI Provider Dependencies
Optional. Statistical velocity calculations are deterministic; LLM assistance is used for strategic qualitative recommendations when available.

## 12. External API Dependencies
None. Utilizes dates, titles, and concepts from indexed workspace sources.

## 13. Configuration Requirements
- `NEOMON_DATABASE_URL`: Relational database connection.

## 14. Error Handling and Limitations
- **Sparse Historical Dates**: If sources lack publication dates, the engine defaults to the retrieval timestamp with an advisory notice.
- **Resilient Request Parsing**: The `/analyze` POST route accepts empty body payloads cleanly.

## 15. Security and Permission Considerations
- Read-only for viewers and researchers; re-running trend analysis requires workspace write privileges.
- Data is strictly isolated to the active workspace.

## 16. Related Features and Dependencies
- **Gap Discovery** (`docs/features/research-gaps.md`): Emerging trends highlight fertile territory for gap analysis.
- **Knowledge Graph** (`docs/features/knowledge-graph.md`): Trend nodes connect to related investigations and claims.

## 17. Relevant Tests and How to Run Them
- **Backend Tests**:
  - `python -m pytest backend/tests/test_trend_intelligence.py -q`
