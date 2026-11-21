# NEOMON — Strategic Future Engineering Roadmap
**Prioritized Development Milestones & Scalability Blueprint**

---

## 1. Roadmap Architecture & Prioritization Methodology

To transition NEOMON from an award-winning competition project to an enterprise-ready scientific intelligence platform, future development is structured into five distinct engineering tiers prioritized by **scientific impact, architectural feasibility, and user value**:

```
+----------------------------------------------------------------------------------------------------+
|                                    NEOMON STRATEGIC ROADMAP TIERS                                  |
+--------------------------+--------------------------+----------------------------------------------+
| TIER                     | FOCUS                    | KEY DELIVERABLES                             |
+--------------------------+--------------------------+----------------------------------------------+
| Priority 1 (Immediate)   | Research Accuracy        | Constrained decoding, Retraction Watch, NLI  |
| Priority 2 (Near-Term)   | AI Performance & Cost    | Native JSON schemas, Semantic chunk reranking|
| Priority 3 (Medium-Term) | Ingestion & Sources      | Institutional proxy, OpenAlex bulk indexing  |
| Priority 4 (Long-Term)   | User Experience & Graph  | WebGL canvas, CRDT collaboration, LaTeX sync |
| Priority 5 (Enterprise)  | Production & Compliance  | K8s Helm charts, SAML SSO, SOC2 audit trails |
+--------------------------+--------------------------+----------------------------------------------+
```

---

## 2. Priority 1 — Research Accuracy & Scientific Integrity

### 1.1 Natural Language Inference (NLI) Cross-Encoder Layer
- **Why it is needed**: While the current regex and LLM-based evidence classification distinguishes broad support vs contradiction, subtle nuances in scientific hedging (e.g. *"preliminary evidence suggests"* vs *"confirmatory trials establish"*) benefit from dedicated natural language inference.
- **Problem it solves**: Eliminates residual risk of topical co-occurrence masquerading as empirical entailment.
- **Expected Benefit**: Increases claim verification precision from ~85% to >96% against human expert benchmarks.
- **Implementation Complexity**: Moderate (2–3 weeks).
- **Dependencies**: HuggingFace `transformers` integration or lightweight ONNX runtime model (e.g. `DeBERTa-v3-large-MNLI`) executed locally or via microservice.
- **Target Milestone**: Milestone 14 (Q1).

### 1.2 Automated Retraction Watch Database Integration
- **Why it is needed**: Over 10,000 academic papers are retracted annually due to data fabrication, ethical violations, or flawed methodology. Citing a retracted paper fatally undermines an investigation.
- **Problem it solves**: Prevents retracted, disputed, or heavily corrected literature from being used as positive evidence.
- **Expected Benefit**: Real-time warning banners and automatic disqualification of retracted studies from claim adjudication.
- **Implementation Complexity**: Low (1 week).
- **Dependencies**: Retraction Watch API / Crossref retraction metadata feed.
- **Target Milestone**: Milestone 14 (Q1).

### 1.3 Grammar-Constrained Decoding for Evidence Citations
- **Why it is needed**: LLMs occasionally emit non-existent UUIDs or malformed JSON syntax.
- **Problem it solves**: Makes citation hallucination mathematically impossible by masking logits at the tokenizer level so the model can only emit valid UUIDs from the investigation's active evidence set.
- **Expected Benefit**: 100% elimination of phantom evidence citations with zero fallback overhead.
- **Implementation Complexity**: Moderate (2 weeks).
- **Dependencies**: Outlines or vLLM logits processing integration.
- **Target Milestone**: Milestone 14 (Q1).

---

## 3. Priority 2 — AI Performance, Concurrency & Cost Optimization

### 2.1 Provider-Native Structured Output Enforcement
- **Why it is needed**: OpenAI, Anthropic, and newer local engines support native JSON schema guarantees (`response_format={"type": "json_schema"}`).
- **Problem it solves**: Eliminates JSON parsing retries, reduces token overhead from schema correction prompts, and cuts inference latency by ~20%.
- **Expected Benefit**: Faster, bulletproof agent completions across cloud models.
- **Implementation Complexity**: Low (1 week).
- **Dependencies**: Update `OpenAICompatibleProvider` to pass strict Pydantic schemas via native API parameter.
- **Target Milestone**: Milestone 14 (Q1).

### 2.2 Semantic Chunk Reranking (Cross-Encoder Pipeline)
- **Why it is needed**: Passing all extracted sentences to specialist agents consumes significant context window space.
- **Problem it solves**: Ranks extracted evidence passages using a high-precision cross-encoder (e.g. BGE-Reranker-v2 or Cohere Rerank) before injecting them into the specialist prompt.
- **Expected Benefit**: Reduces prompt token consumption by 50% while increasing the relevance of evidence supplied to the Advocate and Skeptic.
- **Implementation Complexity**: Moderate (2 weeks).
- **Dependencies**: Local ONNX cross-encoder or Cohere API client.
- **Target Milestone**: Milestone 15 (Q2).

### 2.3 Multi-Model Consensus Ensembling
- **Why it is needed**: Different frontier models (GPT-4o, Claude 3.5 Sonnet, Llama-3.3-70B) possess different epistemological biases and training domain strengths.
- **Problem it solves**: Allows users to configure heterogeneous specialist agents (e.g. GPT-4o as Advocate, Claude as Skeptic, Llama as Auditor) and requires cross-family agreement on final adjudications.
- **Expected Benefit**: Drastically reduces reliance on any single proprietary model provider and eliminates single-vendor blind spots.
- **Implementation Complexity**: Low-Moderate (already supported in backend `role_models` config; requires UI multi-model selector).
- **Dependencies**: Configured API keys for multiple providers.
- **Target Milestone**: Milestone 15 (Q2).

---

## 4. Priority 3 — Academic Ingestion & Source Expansion

### 4.1 Institutional Library Proxy & Shibboleth Authentication
- **Why it is needed**: High-impact paywalled medical and technical literature cannot be legally downloaded without institutional subscriptions.
- **Problem it solves**: Enables university and enterprise users to connect their EZProxy or OpenAthens credentials, allowing NEOMON to legally retrieve subscribed full-text PDFs.
- **Expected Benefit**: Expands full-text document acquisition from ~40% (open access only) to >90% for subscribed institutions.
- **Implementation Complexity**: High (4 weeks; security, credential encryption, proxy routing).
- **Dependencies**: Secure credential vault, proxy scraper worker.
- **Target Milestone**: Milestone 16 (Q2).

### 4.2 Semantic Scholar & OpenCitations Graph Expansion
- **Why it is needed**: OpenAlex and Crossref provide comprehensive catalog metadata, but Semantic Scholar offers rich semantic influence scores (*"highly influential citations"*).
- **Problem it solves**: Enhances `citation_genealogy` by distinguishing casual mentions from deep foundational dependencies.
- **Expected Benefit**: Automated identification of the seminal paper in any scientific lineage.
- **Implementation Complexity**: Low (1 week).
- **Dependencies**: Semantic Scholar API key.
- **Target Milestone**: Milestone 15 (Q2).

### 4.3 Multilingual Academic Translation & Ingestion
- **Why it is needed**: Extensive high-quality research is published in Mandarin, German, French, Japanese, and Spanish that remains unindexed in English-only reviews.
- **Problem it solves**: Translates non-English abstracts and evidence passages on-the-fly, preserving source-language provenance.
- **Expected Benefit**: Global scientific coverage without language barriers.
- **Implementation Complexity**: Moderate (2 weeks).
- **Dependencies**: Fast local NLLB-200 / DeepL API integration.
- **Target Milestone**: Milestone 16 (Q3).

---

## 5. Priority 4 — User Experience, Knowledge Graph & Collaboration

### 5.1 WebGL Hardware-Accelerated Knowledge Graph Rendering
- **Why it is needed**: Large-scale research investigations with 50+ papers and hundreds of evidence passages generate over 1,000 graph nodes, causing DOM lag in SVG/HTML-based React Flow.
- **Problem it solves**: Migrates the graph canvas to hardware-accelerated WebGL (via Three.js or PixiJS / React Flow WebGL renderer).
- **Expected Benefit**: Smooth 60 FPS exploration and interactive zooming across 10,000+ nodes and edges.
- **Implementation Complexity**: High (3–4 weeks).
- **Dependencies**: Canvas/WebGL rendering pipeline.
- **Target Milestone**: Milestone 17 (Q3).

### 5.2 Real-Time Collaborative Research Editing (CRDTs / Yjs)
- **Why it is needed**: Multiple researchers working in the same workspace need to co-edit investigation notes, review comments, and report sections simultaneously without write conflicts.
- **Problem it solves**: Implements Conflict-Free Replicated Data Types (CRDTs) over WebSockets using Yjs.
- **Expected Benefit**: Google Docs-style real-time multi-cursor collaboration on scientific reports.
- **Implementation Complexity**: Moderate-High (3 weeks).
- **Dependencies**: Yjs / WebSocket backend bridge.
- **Target Milestone**: Milestone 17 (Q3).

### 5.3 Automated Overleaf & LaTeX Synchronizer
- **Why it is needed**: Academic researchers write papers in LaTeX, not web dashboards.
- **Problem it solves**: Automatically exports the complete investigation report, evidence tables, and verified BibTeX bibliography directly into an Overleaf or Git-backed LaTeX repository.
- **Expected Benefit**: 1-click transition from NEOMON investigation to submittable journal manuscript.
- **Implementation Complexity**: Low (1–2 weeks).
- **Dependencies**: LaTeX Jinja template engine, Git export worker.
- **Target Milestone**: Milestone 16 (Q2).

---

## 6. Priority 5 — Production Scalability & Enterprise Infrastructure

### 6.1 Enterprise Kubernetes Helm Charts & Horizontal Pod Autoscaling (HPA)
- **Why it is needed**: High-volume institutional deployments require dynamic scaling of background workers and API instances based on CPU and inference queue depth.
- **Problem it solves**: Provides zero-downtime, automated scaling across cloud environments (AWS EKS, GCP GKE, Azure AKS).
- **Expected Benefit**: Handles hundreds of concurrent university research investigations effortlessly.
- **Implementation Complexity**: Moderate (2 weeks).
- **Dependencies**: Docker container hardening, Helm chart templates, Prometheus metrics exporter.
- **Target Milestone**: Milestone 18 (Q4).

### 6.2 Enterprise Single Sign-On (SAML 2.0 / Okta / Azure AD)
- **Why it is needed**: Academic institutions and corporate enterprises mandate integration with their centralized identity providers.
- **Problem it solves**: Replaces standard email/password authentication with enterprise SSO, automated user provisioning (SCIM), and role mapping.
- **Expected Benefit**: Seamless enterprise adoption and security compliance.
- **Implementation Complexity**: Moderate (2 weeks).
- **Dependencies**: SAML/OIDC authentication middleware.
- **Target Milestone**: Milestone 18 (Q4).
