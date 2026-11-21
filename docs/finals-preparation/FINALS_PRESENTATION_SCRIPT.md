# NEOMON — Finals Presentation Script & Demonstration Playbook
**Spoken Presentation Guides, Slide Commentary & Live Demo Script**

---

## 1. 5-Minute Competition Finals Pitch Script

*Target Duration: 4 minutes 45 seconds (leaving 15 seconds buffer).*
*Tone: Confident, authoritative, technically rigorous, measured pace.*

---

### [0:00 – 0:45] The Hook & The Problem
> "Good morning, honorable judges and fellow engineers. 
> 
> In 2026, humanity publishes over five million academic papers every single year. Yet, when an oncologist needs to know if a clinical trial succeeded, or when an AI researcher wants to know if a model architecture genuinely generalizes, they face an impossible choice.
> 
> Option one: spend four to six months conducting a manual systematic literature review.
> Option two: ask a commercial AI chatbot—and gamble on hallucinated citations, fabricated statistics, and superficial confirmation bias.
> 
> General LLMs were built to be agreeable conversationalists; they were never designed to be rigorous scientific adjudicators. When asked a complex question, they exhibit topical bias: if a paper merely mentions a keyword in its abstract, the model asserts the paper proves the user's premise, completely ignoring that the researchers may have concluded the exact opposite.
> 
> We built **NEOMON** to solve this crisis."

---

### [0:45 – 1:30] Introducing NEOMON
> "**NEOMON** stands for **Neural Evidence Orchestration & Multi-Agent Observation Network**. It is an autonomous, evidence-first research intelligence operating system.
> 
> NEOMON does not summarize papers in the dark. Instead, it treats scientific literature review as a structured, adversarial legal trial.
> 
> It connects directly to the world's scholarly databases—OpenAlex, Crossref, arXiv, and Unpaywall—as well as real-time web intelligence. It downloads full-text literature, extracts verbatim empirical evidence passages, and enforces strict cryptographic provenance: no assertion can exist in NEOMON unless it is textually and mathematically grounded in an exact, verifiable passage UUID."

---

### [1:30 – 2:45] The Dialectical Multi-Agent Engine
> "Here is how our architecture works.
> 
> When you submit a research question, our **Intelligence Planner** deconstructs it into atomic, testable empirical claims.
> 
> Next, rather than trusting a single LLM to synthesize the data, NEOMON launches an **adversarial multi-agent dialectic**:
> - An **Advocate agent** builds the strongest possible case supporting the claim, strictly citing verified evidence passages.
> - A **Skeptic agent** actively hunts for counter-evidence, unaddressed edge cases, and null results.
> - A **Methodology Auditor** examines sample sizes, control groups, and correlation-versus-causation errors across 15 scientific dimensions.
> - A **Source Intelligence agent** analyzes publisher credibility and peer-review pedigree.
> - And our **Study Independence service** clusters duplicate and syndicated papers to ensure that five derivative articles citing one study are never counted as five independent confirmations.
> 
> These agents submit structured arguments citing verified passage IDs. A **Debate Moderator** chairs multi-round debates, identifying unresolved tensions. Finally, a **Conflict Adjudicator** renders calibrated verdicts—strongly supported, contradictory, or inconclusive—with explicit confidence intervals."

---

### [2:45 – 3:45] Live Demonstration Highlights
> "Let me show you NEOMON in action on our live system.
> 
> *(Referencing screen)*
> Here we investigate: *'How does generative AI affect students in higher education?'*
> 
> Notice the live telemetry at the top: inference queue latency, active token velocity, and evidence saturation meters.
> 
> Look at the **Intelligence Planner** card: it immediately decomposed the question into four atomic claims. In the **Evidence Explorer**, we see verbatim passages extracted from peer-reviewed IEEE and arXiv papers.
> 
> In the **Debate tab**, observe the intellectual tension: the Advocate proved immediate procedural score gains, while the Skeptic cited an empirical randomized trial showing a 41% drop in unassisted recall. 
> 
> The Conflict Adjudicator didn't gloss over this contradiction—it declared the claim *moderately supported with strict caveats*, requiring active Socratic tutoring constraints.
> 
> In the **Graph tab**, every claim, source, and argument is mapped into an interactive React Flow knowledge graph. And with one click, we export a publication-ready 18-section report complete with an immutable SHA-256 reproducibility manifest."

---

### [3:45 – 4:45] Engineering Rigor & Closing
> "Under the hood, NEOMON is built on Next.js 16, FastAPI, and SQLAlchemy. It is verified by **235 automated backend tests** and **15 frontend suites**, with zero TypeScript errors and zero ESLint warnings.
> 
> It supports both cloud frontiers—OpenAI, Claude—and 100% private, local LLMs like Ollama and LM Studio on private LANs with zero external data leakage.
> 
> We are not presenting a concept; we are presenting a fully implemented, battle-tested scientific intelligence engine.
> 
> NEOMON transforms weeks of painful literature review into minutes of auditable, verifiable scientific discovery.
> 
> Thank you, and we welcome your questions."

---

## 2. 10-Minute Technical Defense Script

*Target Duration: 9 minutes 30 seconds.*
*Used for deep technical presentations with presentation slides.*

---

### Slide 1: Title & The Mission [0:00 – 1:00]
- **Speaker**: "Honorable judges, today we present NEOMON: Neural Evidence Orchestration & Multi-Agent Observation Network. Our mission is simple: to make automated scientific intelligence as rigorous, auditable, and traceable as peer-reviewed human scholarship."
- **Key Point**: General AI summarizes; NEOMON interrogates.

### Slide 2: The Core Problem in Scientific AI [1:00 – 2:15]
- **Speaker**: "Why can't researchers simply use ChatGPT or Perplexity for literature synthesis? There are three fatal failure modes in current generative search:
  1. **Topical Confirmation Bias**: Commercial models confuse semantic proximity with empirical entailment. A paper discussing 'AI risks' is cited as proof of 'AI collapse,' even if the paper concludes the risks are negligible.
  2. **Phantom Citations & Hallucinated Metrics**: Autoregressive tokenizers hallucinate plausible-looking author names, journal venues, and p-values.
  3. **The Syndication Fallacy**: Five derivative blog posts or review articles citing a single flawed study are treated as five independent corroborating proofs.
  In high-stakes research—clinical medicine, aerospace, semiconductor design—these errors are catastrophic."

### Slide 3: Architectural Overview & Data Pipeline [2:15 – 3:45]
- **Speaker**: "To solve this, we architected NEOMON as a decoupled, multi-tier reactive system:
  - **Frontend**: Next.js 16 with Turbopack, React 19, Tailwind, and an interactive `@xyflow/react` knowledge graph.
  - **Backend**: FastAPI with Python 3.12+, fully asynchronous with AsyncIO semaphores.
  - **Real-Time Telemetry**: Server-Sent Events (SSE) secured by single-use, 60-second cryptographic stream tickets (`POST /api/v1/auth/stream-ticket`), eliminating bearer token leakage in browser query strings.
  - **Data Tier**: Async SQLAlchemy 2.0 supporting SQLite WAL mode for local zero-config runs and PostgreSQL for enterprise scale across 66 relational entity models."

### Slide 4: Academic Ingestion & SSRF Security [3:45 – 5:00]
- **Speaker**: "Our retrieval subsystem interfaces directly with scholarly APIs: Crossref for DOIs, OpenAlex for citation networks, arXiv for preprints, Unpaywall for open-access PDF links, and Tavily for real-time web search.
  Crucially, our document scraper implements strict SSRF protection: private IP addresses and loopback ranges are blocked at the DNS resolution level.
  Once downloaded, our custom HTML parser removes navigational boilerplate and extracts clean article text. Our sentence-level parser then isolates empirical outcome statements, linking each passage to an immutable UUID and exact character offsets."

### Slide 5: The Adversarial Multi-Agent Engine [5:00 – 6:30]
- **Speaker**: "Rather than asking a single prompt to 'be objective,' NEOMON implements an adversarial agent triad:
  - The **Advocate** constructs the affirmative case, citing verified evidence UUIDs.
  - The **Skeptic** challenges methodology, searching for null outcomes and unaddressed limitations.
  - The **Methodology Auditor** evaluates 15 scientific dimensions: sample size power, selection bias, geographic clustering, and correlation-versus-causation errors.
  - Every agent argument is strictly validated by `_validate_role_payload`: if a model hallucinates a non-existent evidence ID, NEOMON strips the phantom ID and forces confidence to 'insufficient.'
  - A **Debate Moderator** synthesizes disagreements across rounds, and a **Conflict Adjudicator** renders calibrated verdicts with explicit residual uncertainties."

### Slide 6: Milestone 12 Scientific Reliability Suite [6:30 – 7:30]
- **Speaker**: "In Milestone 12, we introduced three breakthrough integrity services:
  1. **8-Class Evidence Classification**: Explicitly distinguishes empirical findings from introductory aspirations or study aims.
  2. **Study Independence Clustering**: Evaluates title and author Jaccard similarity to collapse syndicated reporting into single study clusters, computing an explicit `independence_ratio`.
  3. **Reproducibility Manifest**: Generates an immutable SHA-256 cryptographic snapshot of all ingested sources, agent prompts, and model parameters, allowing any researcher to independently verify or reproduce the investigation."

### Slide 7: Live Demonstration Walkthrough [7:30 – 8:30]
- **Speaker**: *(Executes the 60-second live demo flow outlined in Section 3 below).*

### Slide 8: Codebase Health, Limitations & Roadmap [8:30 – 9:30]
- **Speaker**: "NEOMON is backed by **235 automated pytest tests** and **15 frontend tests**, with zero lint warnings.
  We are completely transparent about our limitations: we do not bypass commercial journal paywalls without open-access mirrors; our local LLM throughput is constrained by consumer VRAM; and automated heuristics cannot substitute for physical laboratory replication.
  Our roadmap includes NLI cross-encoder verification, Retraction Watch database integration, and institutional Shibboleth proxy support.
  NEOMON transforms raw, chaotic academic literature into auditable scientific intelligence. Thank you."

---

## 3. Step-by-Step Live Demonstration Script

Follow this exact sequence during the live demonstration:

| Step | Time | UI Location | Exact Action | What to Say / Point Out |
|---|---|---|---|---|
| **1** | 0:00 | `/` (Dashboard) | Start on the main dashboard. | *"Notice the cyberpunk scientific HUD. We have active investigations, live agent telemetry, and zero backend connection errors."* |
| **2** | 0:10 | `/investigations/new` | Click **"New Investigation"**. | *"We launch an investigation on: 'How does generative AI affect students in higher education?' We select our local/cloud AI provider and click Initiate."* |
| **3** | 0:20 | `/investigations/[id]` | Observe real-time SSE stream. | *"Notice the live telemetry counters: elapsed time, active token velocity, and stage transitions. The server streams these updates via single-use cryptographic tickets."* |
| **4** | 0:30 | Investigation Page | Scroll to **Claims Card**. | *"The Intelligence Planner decomposed our broad question into 4 atomic, falsifiable claims. Each claim has clear priorities and search objectives."* |
| **5** | 0:40 | Tab: **Evidence** | Click **Evidence Explorer**. | *"Here are the verbatim empirical passages extracted from Crossref and arXiv. Hover over any passage to inspect its parent DOI, character offsets, and confidence score."* |
| **6** | 0:50 | Tab: **Debate** | Click **Multi-Agent Debate**. | *"Look at the adversarial dialectic: the Advocate cites empirical test score gains; the Skeptic cites a randomized trial proving a 41% drop in unassisted recall. The Conflict Adjudicator evaluates the tension and renders a calibrated verdict."* |
| **7** | 1:00 | Tab: **Graph** | Click **Knowledge Graph**. | *"This is our interactive React Flow knowledge graph. It maps 16 distinct node types, showing the direct lineage from source paper to evidence passage to agent argument."* |
| **8** | 1:10 | Tab: **Report** | Click **Report & Export**. | *"Here is the complete 18-section research report, accompanied by an immutable SHA-256 reproducibility manifest. With one click, we can export this as a PDF, Markdown, or BibTeX research bundle."* |

---

## 4. Architectural Soundbites for Presentation Slides

Use these concise, powerful soundbites when explaining specific components:

- **On Atomic Claims**: *"We don't search for answers to questions; we search for evidence that tests atomic claims."*
- **On Multi-Agent Dialectic**: *"Objectivity doesn't come from a neutral prompt; it comes from an adversarial debate between specialist agents with competing cognitive mandates."*
- **On Evidence Grounding**: *"In NEOMON, if an LLM cannot cite a verified database UUID for a statement, that statement does not exist."*
- **On Study Independence**: *"Five articles citing one paper is not five proofs; it's one proof repeated five times. NEOMON clusters derivative sources to protect scientific truth."*
- **On Reproducibility**: *"Science requires reproducibility. Every NEOMON investigation generates a cryptographic SHA-256 manifest freezing the exact queries, sources, and prompts used."*
- **On Local AI**: *"Scientific intelligence shouldn't require sending sensitive clinical or proprietary data to third-party cloud APIs. NEOMON runs 100% locally on Ollama and LM Studio."*
