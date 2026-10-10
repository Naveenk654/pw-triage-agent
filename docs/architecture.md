# Technical Architecture & Design Rationale

This document provides a comprehensive architectural deep-dive into the PW-Style Support Ticket Triage Agent, explaining every component, boundary, and trade-off for a live technical interview.

---

## 1. Core Architectural Philosophy

### "Knowing When NOT to Use an LLM"
In an edtech company handling hundreds of thousands of student inquiries across admissions, fee disputes, batch schedules, and technical bugs, delegating final action decisions to a non-deterministic generative LLM creates immense operational and financial risk:
- LLMs are prone to hallucinating exceptions or promising unapproved refunds.
- LLMs struggle with precise arithmetic comparisons (e.g. `amount >= 10,000` or `days <= 7`).
- LLM prompt instructions can be bypassed via prompt injections.

**Our Architecture Inverts the Paradigm:**
1. LLMs are restricted strictly to **bounded, grounded drafting** from retrieved text.
2. Jev 1.13 is restricted strictly to **structured judgments** (`Choice`, `Score`, `Noul`).
3. **Pure Python code owns the decision boundary**: regex checks, transaction amounts, calendar thresholds, and the final `AUTO_REPLY` vs `ESCALATE` decision.

---

## 2. End-to-End Pipeline Breakdown

### Stage 1: Preprocessing & Injection Sanitization (`src/preprocess.py`)
- Filters empty or gibberish messages (`len < 5`, no alphanumeric characters).
- Delimits user text as untrusted data.
- Scans for known prompt injection vectors (`"ignore previous instructions"`, `"system prompt"`, `"hidden policies"`).
- Any detected injection immediately triggers **Rule 2 Escalation**, completely shielding downstream models from adversarial execution.

### Stage 2: Deterministic Rule Extraction (`src/rules_extract.py`)
- Evaluates regex patterns to extract:
  - Monetary values (e.g., `Rs. 15,000`, `₹25000`)
  - Order numbers (`PW-XXXXX`) and UPI transaction references (`UPI-XXXXXXXXXXXX`)
  - Hostile sentiment indicators (`"scam"`, `"fraud"`, `"lawyer"`, `"consumer court"`)
  - Repeated contact indicators (`"contacted support twice"`, `"no reply for 3 days"`)
  - Duplicate debit signals (`"debited twice"`, `"double deduction"`)
  - Explicit out-of-KB topics (third-party subscription transfers, laptop repairs)

### Stage 3: Structured Classification (`src/classifier.py`)
- Employs an abstract `BaseClassifier` interface supporting three interchangeable backends:
  1. `JevClassifier`: Employs `typesafe-sdk` using `Choice` over 7 operational categories, `Score` for urgency (0–4 mapped to 1–5), and `Noul` questions for literal condition checks.
  2. `LLMStructuredClassifier`: Fallback JSON schema classification.
  3. `KeywordClassifier`: Deterministic baseline for offline development.
- Features safety overrides: if deterministic regex detects a legal threat, urgency is forced to 5 regardless of model output.

### Stage 4: Hybrid Retrieval without Chroma (`src/retriever.py`)
- Operates on 12 modular markdown documents chunked by section headers.
- Combines:
  1. **Dense Cosine Similarity**: Captures deep semantic meaning across multilingual student vernacular.
  2. **BM25Okapi**: Excels at exact alphanumeric tokens (error codes like `DRM-401`, policy names, specific conditions).
  3. **Reciprocal Rank Fusion (RRF, k=60)**: Combines dense and lexical ranks into a robust final ordering without requiring an external vector database like Chroma.

### Stage 5: Answerability Check (`src/answerability.py`)
- Evaluates whether the query can be safely answered from the knowledge base.
- Requires **both**:
  1. Top dense cosine score $\ge 0.65$ (`retrieval_min_score`)
  2. Max positive passage relevance $\ge 0.50$ (`passage_relevance_min` via Jev Call B)
- **Critical Principle**: RRF rank scores are never treated as semantic confidence thresholds because RRF reflects relative order, not semantic proximity.

### Stage 6: Grounded Generation (`src/draft_generator.py`)
- Assembles retrieved evidence chunks into an isolated system context.
- System prompt strictly forbids promising exceptions, inventing deadlines, or speculating outside the provided context.
- Forces document citation tagging (e.g., `[refund]`, `[batch_access]`).

### Stage 7: Citation & Claim Verification (`src/verification.py`)
- Splits draft into sentences.
- **Deterministic Numeric Grounding**: Extracts every currency amount, percentage, and time duration in the drafted sentence and asserts that the exact token exists in the cited source text.
- Sentence-level validation against cited chunks (Jev Call C: `supported`, `contradicted`, `not_stated`).
- Triggers 1 automatic regeneration attempt if ungrounded claims are detected before escalating.

### Stage 8: Deterministic Decision Engine (`src/decision_engine.py`)
Executes the strict **13-step Escalation Precedence**:
1. Preprocess failure / empty / garbage
2. Prompt injection detected
3. Money-sensitive (amount $\ge \text{Rs. } 10,000$ or double-charge/dispute)
4. Explicit refund demand with urgency words or legal/complaint threats
5. At-risk student (repeated contacts, churn threat, hostile distress)
6. Multi-issue detected (flag and escalate)
7. Urgency $\ge 4$
8. Category confidence $< 0.60$ or category == 'other'
9. Needs manual case/database investigation
10. Not answerable from KB / Explicit out-of-KB topics
11. Generation insufficient info or verification failed
12. Component failure after retry/fallback
13. Academic subject-matter explanation requested

---

## 3. Financial Tracking & Budget Architecture (`src/cost.py`)

- **List-Price Equivalent Cost**:
  - Jev 1.13: $\$0.042 \text{ / million tokens}$
  - Gemini Flash: $\$0.075 \text{ input} / \$0.30 \text{ output per million tokens}$
  - Groq Llama-3.3: $\$0.59 \text{ input} / \$0.79 \text{ output per million tokens}$
- **Actual Cash Spend**:
  - Accurately logged as **$0.00** during development on Google AI Studio's free tier.
- **Jev Budget Guard**:
  - Tracks cumulative spend against a configured $\$5.00$ ceiling, triggering automated warnings when usage crosses 80%.
