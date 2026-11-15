# Feature Specification: Scientific Reliability & Benchmarks Engine

## 1. Feature Overview
The **Scientific Reliability & Benchmarks Engine** (`/benchmarks`) provides rigorous empirical validation of NEOMON's research capabilities against standard scientific NLP and fact-checking benchmark datasets. It packages **10 gold-standard scientific benchmarks**, computes empirical evaluation metrics (**Precision**, **Recall**, **F1 Score**, **Citation Accuracy**, and **Hallucination Rate**), and maintains an audit log of **Human Evidence Corrections**.

## 2. Purpose and Problem Solved
AI research systems often make grandiose marketing claims regarding accuracy without empirical benchmark evidence. NEOMON eliminates ambiguity by embedding scientific evaluation directly into the platform:
- Evaluates retrieval, entailment, and synthesis against established academic datasets.
- Measures whether the system correctly flags false or contradictory claims.
- Allows human researchers to submit ground-truth corrections when an AI assertion is flawed.
- Tracks regression testing across software releases to verify that model upgrades do not degrade scientific accuracy.

## 3. Where Users Access It
- **Dedicated Route**: `/benchmarks` (Scientific Benchmarks Dashboard).
- **In-Investigation**: Scientific Reliability mount on `/investigations/[id]`.
- **Navigation**: "Scientific benchmarks" link in the primary sidebar navigation.

## 4. Step-by-Step User Workflow
1. Navigate to `/benchmarks`.
2. Inspect the **10 Standard Benchmark Datasets**:
   - `SciFact-Bio`: Biomedical claim verification against peer-reviewed paper abstracts.
   - `Climate-FEVER`: Real-world climate science claims with complex evidence entailment.
   - `PubMedQA`: Biomedical research question answering requiring reasoning over full texts.
   - `COVID-Fact`: Scientific claim verification under evolving evidence conditions.
   - `BioASQ-Y/N`: Yes/no biomedical question answering benchmarks.
   - `SciQ-Physics`: Multi-step physics and chemistry conceptual evaluation.
   - `MedQA-USMLE`: Clinical medicine reasoning and diagnostic questions.
   - `Evidence-Inference`: Statistical extraction from clinical trial results.
   - `Multi-Hop-Sci`: Multi-hop scientific reasoning connecting disparate literature.
   - `Tox-Evidence`: Toxicological evidence synthesis and safety risk claims.
3. Configure and Launch an Evaluation Run:
   - Select Target Investigation UUID (or evaluate standalone dataset).
   - Select Benchmark Dataset.
   - Set Sample Size (e.g., 20, 50, 100 cases).
   - Click **"Run Benchmark Evaluation"** (or click **"Run NVIDIA Regression"**).
4. Review **Evaluation Metrics Grid**:
   - **Retrieval Precision**: % of retrieved papers that were genuinely relevant.
   - **Entailment Accuracy**: % of claims where supporting/refuting classification matched gold standard.
   - **Hallucination Rate**: % of assertions not grounded in underlying full-text evidence.
   - **F1 Score**: Harmonic mean of precision and recall.
5. Review **Human Corrections Log**:
   - View historical corrections submitted by researchers when an evidence quote was misclassified or inaccurate.

## 5. How the Feature Works Internally
1. Benchmark datasets are pre-seeded in the `benchmark_datasets` table, each referencing a structured JSON manifest of gold-standard claim-evidence pairs.
2. The `app.benchmarks.benchmark_service`:
   - Pulls test cases from the selected dataset.
   - Executes the NEOMON retrieval and entailment pipeline for each case.
   - Compares the model's output (`supports`, `refutes`, `not_enough_info`) against gold-standard labels.
   - Computes confusion matrix metrics (True Positives, False Positives, True Negatives, False Negatives).
3. Persists evaluation runs into `benchmark_runs`.
4. Human Evidence Corrections:
   - When a user submits an accuracy challenge via `POST /api/v1/benchmarks/corrections`, the platform records `human_evidence_corrections` with `original_value`, `corrected_value`, and `reason`.

## 6. Relevant Frontend Pages and Components
- `app/benchmarks/page.tsx`: Scientific Benchmarks & Reliability route.
- `components/scientific-reliability-workspace.tsx`: Benchmark selector, metric scorecards, and regression execution triggers.
- `app/investigations/[id]/page.tsx`: Mounts scientific reliability verification badges.

## 7. Relevant Backend Routes and Endpoints
- `GET /api/v1/benchmarks/datasets`: Lists all available benchmark datasets.
- `POST /api/v1/benchmarks/run`: Executes a benchmark evaluation run.
- `GET /api/v1/benchmarks/runs`: Lists historical benchmark execution results.
- `POST /api/v1/benchmarks/corrections`: Submits a human evidence correction record.
- `GET /api/v1/benchmarks/corrections`: Fetches all human correction records.

## 8. Relevant Services and Agents
- `app.benchmarks.benchmark_service.BenchmarkService`: Benchmark execution and metric computation engine.

## 9. Database Tables and Relationships
- `benchmark_datasets`: Stores `id`, `name`, `identifier`, `domain`, `total_cases`, `metrics_summary_json`.
- `benchmark_runs`: Stores `id`, `benchmark_dataset_id`, `investigation_id`, `status`, `retrieval_metrics_json`, `evidence_metrics_json`, `synthesis_metrics_json`, `overall_evaluation_summary`.
- `human_evidence_corrections`: Stores `id`, `investigation_id`, `claim_id`, `evidence_id`, `user_id`, `correction_type`, `original_value`, `corrected_value`, `reason`, `is_active`.

## 10. Inputs and Outputs
- **Run Request**:
  ```json
  {
    "dataset_identifier": "scifact-bio",
    "investigation_id": "UUID (optional)",
    "sample_size": 25
  }
  ```
- **Run Response**:
  JSON object containing run UUID, dataset name, execution latency, retrieval metrics (precision/recall), entailment metrics (accuracy/F1), and overall score summary.

## 11. AI Provider Dependencies
Evaluates the configured AI provider's reasoning accuracy against gold standards. Can run in rule-based mode to establish non-neural baseline metrics.

## 12. External API Dependencies
None. Datasets and evaluation harnesses are packaged locally.

## 13. Configuration Requirements
- `NEOMON_DATABASE_URL`: Relational database connection.

## 14. Error Handling and Limitations
- **Large Dataset Sampling**: Large benchmarks (>1000 cases) are sampled to respect user-defined sample size limits and avoid timeout bottlenecks.
- **Resilient Execution**: Individual failed test cases log error details without failing the overall benchmark run.

## 15. Security and Permission Considerations
- Launching benchmarks requires `researcher` or `admin` workspace privileges.
- Human corrections record the submitting investigator's identity for auditability.

## 16. Related Features and Dependencies
- **Evidence Quality** (`docs/features/evidence-quality.md`): Benchmark metrics calibrate overall platform confidence.
- **Methodology Audit** (`docs/features/methodology-audit.md`): Tested directly in benchmark evaluations.

## 17. Relevant Tests and How to Run Them
- **Backend Tests**:
  - `python -m pytest backend/tests/test_benchmarks_and_regressions.py -q`
  - `python -m pytest backend/tests/test_human_review_and_corrections.py -q`
- **Frontend Tests**:
  - `node --test tests/reliability-ui.test.mjs`
