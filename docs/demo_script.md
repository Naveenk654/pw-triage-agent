# 2-3 Minute Live Demo Script

**Speaker Setup**: Have Streamlit open (`streamlit run app.py`) in full screen, and VS Code open on `config.yaml`.

---

### [00:00 - 00:30] Introduction & Problem Framing
*(Screen showing Streamlit Dashboard)*
> "Hello everyone! Today I'm demonstrating our Support Ticket Triage Agent built for PhysicsWallah-style edtech operations. When scaling to millions of students, customer care teams face a crucial challenge: generative AI cannot be trusted with final refund or cancellation decisions because LLMs hallucinate rules, fail at arithmetic, and bypass instructions. 
> 
> Our core design principle is simple: **The LLM never makes the final decision.** Deterministic Python code enforces all business boundaries, while AI is used strictly for language understanding and grounded drafting."

---

### [00:30 - 01:15] Happy Path: Grounded Auto-Reply
*(Click Button: "1. Refund SLA (Safe Auto-Reply)")*
> "Let's test an everyday query: *'How long does a refund normally take?'*
> 
> Instantly, our hybrid retriever combines BM25 keyword search with dense semantic embeddings via Reciprocal Rank Fusion ($k=60$). We see a prominent **AUTO-REPLY** badge. 
> 
> The system retrieves section 4 from `refund.md`, verifies the numeric timeline—7 to 10 working days—and drafts a concise, verified response with explicit document citations. The agent can review, edit, and send this reply with full confidence."

---

### [01:15 - 01:50] The Safety Boundaries: High-Value & Out-of-KB Queries
*(Click Button: "2. High Value + Escalation")*
> "Now let's test a high-risk scenario: A student paid ₹25,000 three days ago without access and wants their money back. 
> 
> Watch how the dashboard changes: A bold red **ESCALATE TO HUMAN** badge appears. 
> 
> Our deterministic decision engine evaluated the ticket against a 13-step hierarchy. Because the transaction exceeds our ₹10,000 threshold and indicates repeated contact, the automated reply is intentionally withheld, and the ticket is escalated with plain-language reasons.
> 
> If we test an out-of-scope query like transferring an account to another person *(Click Button 3)*, the system flags the knowledge gap and escalates instead of fabricating an answer."

---

### [01:50 - 02:30] Live Config Tuning & Failure Resilience
*(Switch to VS Code / config.yaml)*
> "One of the best features of this architecture is instant adjustability. If operations management decides that all refunds over ₹2,000 should require supervisory review, we simply change `high_value_threshold: 2000.0` in `config.yaml`—no model retraining or code deployment needed.
> 
> Furthermore, in the sidebar failure simulator, we can simulate an upstream Jev or LLM outage. The system gracefully degrades to keyword rules and safely escalates without crashing or leaking tracebacks to the user.
> 
> Across our 60-ticket benchmark dataset, this architecture achieved **98.1% Retrieval Recall@5**, a median latency of **0.46 seconds**, and safely reduced unsafe automation from 96.7% to 33.3%. Thank you!"
