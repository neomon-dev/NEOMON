# NEOMON — Last-Minute Finals Revision Sheet
**15-Minute Pre-Stage Memory Refresh & Defense Cheat Sheet**

---

## 1. Key Codebase Numbers & Facts (Memorize These!)

| Metric | Exact Value | Significance for Judges |
|---|---|---|
| **Backend Test Suite** | **235 passed** (`pytest`) | 100% passing across 41 test modules; zero regressions. |
| **Frontend Test Suite** | **15 passed** (`node --test`) | Full UI coverage: collaboration, graph, reliability. |
| **Code Hygiene** | **0 ESLint errors, 0 TS errors** | Verified strict type-safety across Next.js 16 / React 19. |
| **Relational Entity Models** | **66 SQLAlchemy Models** | Enterprise schema depth; full SQLite WAL & Postgres support. |
| **Specialist AI Agent Roles** | **8 Specialist Roles** | Planner, Advocate, Skeptic, Auditor, Source, Lineage, Temporal, Moderator. |
| **Standard Report Sections** | **18 Structured Sections** | Full scientific synthesis from Executive Summary to References. |
| **Knowledge Graph Node Types** | **16 Node Types** | React Flow mapping claims, evidence, sources, decisions, arguments. |
| **Evidence Classifications** | **8 Scientific Classes** | Direct support, partial, contradiction, background, context, mentions. |
| **Methodology Dimensions** | **15 Audit Dimensions** | Sample size, selection bias, geographic bias, correlation vs causation. |

---

## 2. The 30-Second Opening Hook

> *"Every year, millions of scientific papers are published, yet synthesized intelligence takes months to produce. Meanwhile, researchers who turn to ChatGPT face fabricated citations, hallucinated statistics, and superficial confirmation bias. We built **NEOMON**—the Neural Evidence Orchestration & Multi-Agent Observation Network. NEOMON automates rigorous scientific investigations by breaking questions into atomic claims, acquiring verified papers across global academic databases, and pitting specialist AI agents—Advocates, Skeptics, and Methodology Auditors—into an adversarial dialectical debate. Every statement in our 18-section report is mathematically and textually tied to verifiable empirical passages."*

---

## 3. The End-to-End Pipeline in 5 Steps

```
[1. PLAN]      Intelligence Planner breaks Question into 1-5 Atomic Claims.
     |
[2. RETRIEVE]  Queries Crossref (DOI), OpenAlex, arXiv, Unpaywall, Tavily.
     |         SSRF-guarded scraper extracts verbatim sentence-level evidence.
[3. DEBATE]    Adversarial Triad: Advocate (pro) vs. Skeptic (con) vs. Auditor (bias).
     |         Strict Grounding: Agents can ONLY cite existing evidence UUIDs.
[4. JUDGE]     Moderator chairs debate; Conflict Adjudicator renders verdict.
     |
[5. DELIVER]   18-section report, interactive React Flow graph, SHA-256 manifest.
```

---

## 4. The 3 "Trap Questions" & How to Defend Them

### Trap 1: "Why can't I just use ChatGPT or Perplexity?"
- **The Trap**: The judge thinks this is just another wrapper around an LLM prompt.
- **Your Winning Defense**: *"Commercial LLMs suffer from **topical confirmation bias**: if an abstract mentions a topic, the model asserts the paper proves the user's premise, even if the authors concluded the opposite. Perplexity links sources, but doesn't audit sample sizes, doesn't detect syndicated echo-chambers, and doesn't run an adversarial trial. NEOMON treats research as an evidence trial with strict passage UUID grounding."*

### Trap 2: "Can your system hallucinate?"
- **The Trap**: If you say "No, our AI never hallucinates," you lose all credibility immediately.
- **Your Winning Defense**: *"LLMs are probabilistic, so any LLM can generate hallucinated text. But in NEOMON, **hallucinations cannot survive into the report**. Our `_validate_role_payload` enforces set validation: if an agent cites a non-existent evidence UUID, NEOMON strips the phantom ID and forces confidence to 'insufficient.' An ungrounded assertion simply cannot be persisted."*

### Trap 3: "What happens when a paper is paywalled behind Elsevier?"
- **The Trap**: The judge tests if you are scraping copyrighted papers illegally or pretending paywalls don't exist.
- **Your Winning Defense**: *"We strictly obey legal open-access protocols. NEOMON queries Unpaywall across 50,000 global repositories for legal open mirror PDFs. If no open copy exists, we fall back to the published peer-reviewed abstract from Crossref/OpenAlex and flag the source as `abstract_only=True`, adjusting our confidence rating downward."*

---

## 5. Live Demo Quick Checklist

1. **Browser Tab Prepared**: Have `http://localhost:3000` open in a clean, maximized browser window.
2. **Prepared Investigation**: Have a completed investigation (e.g. *"How does generative AI affect students in higher education?"*) already loaded in one tab in case of live network hiccups.
3. **Live Demonstration Tab**: Have `/investigations/new` open in another tab ready to click **"Initiate Scientific Investigation"**.
4. **Key Screen Highlights**:
   - Point to the **Active Token Velocity** and **Telemetry HUD**.
   - Show the **Atomic Claims** card.
   - Click the **Evidence Explorer** tab and hover over a passage DOI.
   - Open the **Debate tab** to show the tension between Advocate and Skeptic.
   - Switch to the **Knowledge Graph** and drag a claim node.
   - Click **Export** to show the 1-click PDF / Markdown / BibTeX bundle.

---

## 6. Closing Statement

> *"NEOMON transforms weeks of painful literature review into minutes of auditable, verifiable scientific discovery. We are fully implemented, verified by 235 automated tests, and ready to empower human researchers. Thank you."*
