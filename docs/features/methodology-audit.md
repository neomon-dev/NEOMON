# Feature Specification: Scientific Methodology Audit Engine

## 1. Feature Overview
The **Scientific Methodology Audit Engine** inspects empirical research literature for statistical, structural, and experimental flaws. It autonomously identifies **sample size inadequacy**, **underpowered statistical analyses**, **selection bias**, **temporal misalignment**, **lack of blinding/randomization**, and **confounding variables**, attaching structured audit findings directly to claims and sources.

## 2. Purpose and Problem Solved
Much of published scientific literature suffers from methodological deficiencies: underpowered studies claim outsized effect sizes, and correlational data is mistaken for causal mechanisms. The Methodology Audit engine acts as an automated peer-reviewer:
- Audits sample size ($N$) against expected statistical power.
- Checks whether study populations exhibit geographic, demographic, or temporal bias.
- Flags studies lacking control groups or proper blinding.
- Prevents weak studies from skewing meta-analytic syntheses.

## 3. Where Users Access It
- **In-Investigation**: "Methodology Audit" sub-tab on `/investigations/[id]`.
- **Quality Audit Workspace**: Integrated into `/quality-audit`.
- **Evidence Card Tags**: Specific methodological warnings attached to evidence cards.

## 4. Step-by-Step User Workflow
1. Navigate to `/investigations/[id]`.
2. Open the **Methodology Audit** panel.
3. Review the **Audit Summary Banner**:
   - Total studies audited.
   - Identified methodological risks by severity (**Critical**, **Moderate**, **Low**).
   - Methodological rigor score (0.0 to 1.0).
4. Inspect categorized findings:
   - **Sample Size & Statistical Power**: Identifies studies where $N < 30$ or where statistical significance thresholds ($p$-values) hover near arbitrary boundaries without correction for multiple testing.
   - **Selection & Sampling Bias**: Highlights non-randomized recruitment, cohort attrition, or single-center limitations.
   - **Temporal Relevance**: Identifies older studies superseded by recent high-powered multi-center clinical trials.
   - **Confounding Variables**: Uncovers unadjusted lifestyle, demographic, or co-intervention confounders.
5. Click any finding to inspect the underlying source document, verbatim text, and recommended remediation.

## 5. How the Feature Works Internally
1. When documents are ingested, the `app.analysis.methodology_service` scans text sections (Methods, Results, Limitations) using regular expressions and domain heuristics.
2. Extracts quantitative metadata:
   - Sample size integers ($N = \dots$).
   - Study design strings (`randomized controlled trial`, `observational cohort`, `case report`, `in vitro`).
   - Blinding status (`double-blind`, `open-label`, `unblinded`).
3. Evaluates findings against predefined scientific thresholds:
   - If design is `observational` and claim asserts `causes`, flags **Causal Overreach**.
   - If $N < 20$ in a clinical intervention study, flags **Underpowered Sample Size**.
4. Persists findings into the `methodology_audit_findings` database table.

## 6. Relevant Frontend Pages and Components
- `app/investigations/[id]/page.tsx`: Renders methodology findings and bias alerts.
- `components/quality-audit-workspace.tsx`: Visualizes methodology breakdown charts.
- `components/evidence-explorer.tsx`: Displays methodology limitation tags on evidence items.

## 7. Relevant Backend Routes and Endpoints
- `GET /api/v1/research/methodology-audit/{investigation_id}`: Returns all audit findings for an investigation.
- `POST /api/v1/research/methodology-audit/{investigation_id}/run`: Triggers a comprehensive re-audit.

## 8. Relevant Services and Agents
- `app.analysis.methodology_service.MethodologyAuditor`: Core heuristic and LLM analysis service.
- `app.agents.methodology_auditor`: Multi-agent role providing qualitative critiques.

## 9. Database Tables and Relationships
- `methodology_audit_findings`: Stores `id`, `investigation_id`, `source_id`, `finding_type`, `severity`, `description`, `recommendation`, `evidence_passage`, `created_at`.
- `investigations`: Parent investigation.
- `sources`: Literature entity scrutinized by the audit.

## 10. Inputs and Outputs
- **Input**: `investigation_id` (UUID).
- **Output (`MethodologyAuditResponse`)**:
  ```json
  {
    "investigation_id": "UUID",
    "methodological_rigor_score": 0.74,
    "findings": [
      {
        "finding_type": "sample_size_limitation",
        "severity": "moderate",
        "description": "Small sample size (N=18) limits statistical generalizability.",
        "source_id": "UUID",
        "recommendation": "Confirm findings in larger multi-center cohorts."
      }
    ]
  }
  ```

## 11. AI Provider Dependencies
Operates primarily via deterministic pattern matching and heuristic rules; can be enhanced with an LLM for nuanced qualitative methodology evaluations.

## 12. External API Dependencies
None. Evaluates extracted document text locally.

## 13. Configuration Requirements
- `NEOMON_DATABASE_URL`: Relational database connection.

## 14. Error Handling and Limitations
- **Abstract-Only Sources**: If only an abstract is available, the auditor notes that full methodology details could not be verified and adjusts confidence accordingly.
- **Novel Experimental Paradigms**: Unconventional experimental setups that do not match traditional clinical trial keywords are marked `preliminary_unclassified` rather than penalized.

## 15. Security and Permission Considerations
- Read-only for viewers; re-auditing requires researcher write access.
- Audit findings are immutable historical evidence.

## 16. Related Features and Dependencies
- **Evidence Quality** (`docs/features/evidence-quality.md`): Incorporates methodology audit scores into calibrated tiers.
- **Advocate-Skeptic Debate** (`docs/features/advocate-skeptic.md`): Skeptic agent uses audit findings to construct rebuttals.

## 17. Relevant Tests and How to Run Them
- **Backend Tests**:
  - `python -m pytest backend/tests/test_methodology_audit.py -q`
