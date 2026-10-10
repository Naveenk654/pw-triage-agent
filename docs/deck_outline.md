# 3-5 Slide Pitch Deck Outline

### Slide 1: The Operational Challenge at EdTech Scale
- **Headline**: Scaling Student Support Without Sacrificing Trust or Safety.
- **Problem**: 
  - PhysicsWallah handles hundreds of thousands of student interactions across payments, batch lockouts, DRM errors, and academic doubts.
  - Generative LLMs hallucinate deadlines, fail at date/currency arithmetic, and cannot be trusted with final operational decisions.
- **Our Mission**: Build an automated triage agent with strict safety guarantees where deterministic code governs every critical action.

---

### Slide 2: Core Architecture — Knowing When NOT to Use an LLM
- **Headline**: Separation of Powers Between Language Models and Rule Engines.
- **Key Columns**:
  - **Deterministic Python**: Owns security (prompt injections), financial bounds ($\ge \text{Rs. } 10,000$), duplicate payments, and the final `AUTO_REPLY` vs `ESCALATE` decision.
  - **Structured Judgments (Jev 1.13)**: Categorizes intent, judges urgency levels, and scores sentence grounding without freeform generation risks.
  - **Generative LLM (Gemini 3.5 Flash-lite / Groq)**: Restricted strictly to drafting plain-language replies from retrieved policy chunks.
  - **Hybrid Retrieval (No Chroma)**: Dense semantic matching + BM25Okapi combined via Reciprocal Rank Fusion ($k=60$).

---

### Slide 3: Safety Guardrails & 13-Step Escalation Precedence
- **Headline**: Zero Compromise on Risk: Defense in Depth.
- **Key Highlights**:
  - **Prompt Injection Defense**: Preprocessing catches jailbreaks before any LLM call.
  - **Deterministic Numeric Grounding**: Asserts every percentage, currency amount, and day count in a draft exists in cited evidence.
  - **Out-of-KB Detection**: Intentionally omitted topics (third-party transfers, hardware) cleanly escalate rather than guessing.
  - **Graceful Failure Degradation**: Complete simulation suite for component crashes with zero unhandled exceptions.

---

### Slide 4: Empirical Evaluation & Measurable Impact
- **Headline**: Measured, Transparent Performance on 60 Real-World Tickets.
- **Metrics**:
  - **98.1% Retrieval Recall@5** on dense + BM25 RRF fusion.
  - **0.46s p50 Latency** (ultra-responsive operational speed).
  - **$0.00 Actual Cash Spend** during development (free-tier optimized).
  - **Deterministic Rules Impact**: Restrains unsafe automation from $96.7\%$ down to a verified, compliant $33.3\%$.

---

### Slide 5: The Live Demo & Production Readiness
- **Headline**: Built for Real Support Operations.
- **Key Features**:
  - Clean Streamlit dashboard designed for non-technical support agents.
  - Prominent decision badges and human-readable explanations.
  - Instant on-the-spot config tuning via `config.yaml`.
  - Full SQLite audit trail capturing all latencies, tokens, and decisions.
