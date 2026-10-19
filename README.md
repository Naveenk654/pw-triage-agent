# PW Triage Agent
### Multimodal AI support automation for Physics Wallah-style EdTech workflows

PW Triage Agent is an AI-assisted email triage system designed to help support teams process repetitive student queries written in English, Hindi, and Hinglish. It combines structured ticket classification, hybrid retrieval-augmented generation (RAG), screenshot understanding, response verification, and deterministic decision rules to decide whether a ticket can receive an automated reply or should be routed for human review.

> **Project status:** This README describes the capabilities reported in the project audit. Model quality, deployment behavior, and live Gmail integration should be validated in the target environment before the system is used for real student support.

---

## Live Demo: Round 1 Assignment

(currently not working)**Deployed website:** https://pw-triage-agent-production.up.railway.app/
**Support inbox:** supportpw6@gmail.com

PW Triage Agent is an email-based support automation system. The Gmail integration is implemented: incoming support emails are processed by the agent, which retrieves relevant knowledge, decides whether the query can be answered safely, and follows the configured response or human-review path.

### How to evaluate the live email workflow

1. Open the [deployed PW Triage Agent site](https://pw-triage-agent-production.up.railway.app/).
2. From an email account you can access, compose a new email addressed to **supportpw6@gmail.com**.
3. Write a clear student-support question in the email body. For example, ask for help with a course, class access, an app issue, or a learning-platform question. Do not include passwords, OTPs, payment credentials, or other sensitive information.
4. Send the email and allow the configured Gmail listener and processing pipeline time to handle it.
5. Check the **same email account you sent the message from** for the response. Also check Spam if it does not appear.
6. Depending on the query and the system's safety/answerability checks, the agent may reply automatically or route the case for clarification, approval, or escalation.

### What this demo is intended to show

- **Gmail integration:** support requests enter through the configured support inbox and responses are delivered by email.
- **Query understanding:** the system classifies support intent and handles English/Hinglish queries.
- **Knowledge-grounded responses:** hybrid retrieval combines semantic and lexical search, followed by reranking.
- **Screenshot-aware support:** image/screenshot content can be extracted through the implemented vision-language flow.
- **Safety-aware routing:** the decision engine distinguishes automatic replies from cases needing clarification, approval, or escalation.
- **Auditability:** processing and evaluation components record operational information for review.

**Demo note:** This is an email workflow, not just a website chatbot. Sending a message to the support inbox is the key test. The live site provides the deployed project entry point; the email response is expected in the sender's inbox. Delivery time and the selected response path can depend on service availability and the query.

---

## Cost- and Latency-Aware Orchestration

**The system does not call an LLM for every step.** It uses deterministic logic and the Jev classifier where appropriate, reserving LLM calls for stages that benefit from language-model reasoning. This reduces unnecessary token usage and helps control response latency and API cost.

Key design choices include:

- **Deterministic rules first:** common support patterns and structured signals can be handled without asking a generative LLM to rediscover them.
- **Jev-based classification and verification:** Jev is used for selected classification/verification tasks instead of routing every decision through a general-purpose LLM.
- **Fallbacks and caching:** the configured Gemini → Groq → mock fallback chain and LLM caching help improve resilience and avoid repeated calls where cached results apply.
- **Targeted LLM use:** model calls are used for language-intensive stages such as query rewriting and grounded response generation when needed by the pipeline.
- **Hybrid retrieval:** dense retrieval, BM25, RRF fusion, and reranking help find relevant evidence before response generation, rather than relying on an LLM's unsupported memory.

This is an intentional architecture choice: **use cheaper deterministic or specialized components for tasks they can handle, and use generative LLMs only where they add value.** The goal is to reduce avoidable token consumption and improve end-to-end efficiency without removing answerability checks or safety-aware routing.

---

## Highlights

- **Email intake:** Polls a Gmail support inbox using OAuth and processes unread messages.
- **Hinglish-aware triage:** Uses a structured Jev classifier with a keyword-based fallback and deterministic extraction rules.
- **Screenshot understanding:** Extracts image attachments/inline images and incorporates vision-model findings into query rewriting and downstream retrieval.
- **Hybrid RAG:** Combines dense vector retrieval, BM25 lexical retrieval, Reciprocal Rank Fusion (RRF), and CrossEncoder reranking.
- **Grounded drafting:** Builds responses using retrieved policy context and extracts citations/evidence.
- **Answerability and verification stages:** Includes an answerability gate and citation/claim verification components; production activation depends on configuration.
- **Safety-oriented routing:** Uses a four-tier decision flow: escalation, clarification, approval, or automated reply.
- **Human-in-the-loop workflow:** Creates Gmail drafts for cases that need review rather than automatically replying to every ticket.
- **Fallbacks and caching:** Reports a Gemini → Groq → mock fallback chain and response caching.
- **Observability:** Logs ticket activity to SQLite and Supabase and exposes a Streamlit admin dashboard.
- **Evaluation tooling:** Includes classification, retrieval, escalation, and response-quality evaluation scripts plus a golden ticket dataset.

## 🏗️ System Architecture

```text
                 ┌─────────────────────┐
                 │   Gmail Inbox       │
                 └──────────┬──────────┘
                            ▼
                 ┌─────────────────────┐
                 │ Listener & Parsing  │
                 │ Idempotency Checks  │
                 └──────────┬──────────┘
                            ▼
              ┌─────────────┴─────────────┐
              ▼             ▼             ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │  Rules   │  │   Jev    │  │ VLM for  │
        │  Engine  │  │Classifier│  │Screenshots│
        └────┬─────┘  └────┬─────┘  └────┬─────┘
             └─────────────┼─────────────┘
                           ▼
                 ┌─────────────────────┐
                 │  Hybrid RAG         │
                 │ Dense + BM25 + RRF  │
                 │ Cross-Encoder       │
                 └──────────┬──────────┘
                            ▼
                 ┌─────────────────────┐
                 │ Answerability &     │
                 │ Claim Verification  │
                 └──────────┬──────────┘
                            ▼
                 ┌─────────────────────┐
                 │  Decision Engine    │
                 └──────────┬──────────┘
                            ▼
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
   ┌────────────┐    ┌────────────┐    ┌────────────┐
   │ Auto Reply │    │ Clarify    │    │ Approval / │
   │ via Gmail  │    │ Query      │    │ Escalation │
   └──────┬─────┘    └──────┬─────┘    └──────┬─────┘
          └─────────────────┼─────────────────┘
                            ▼
                 ┌─────────────────────┐
                 │ Supabase + Streamlit│
                 │       Dashboard     │
                 └─────────────────────┘
```

**Efficiency:** Deterministic rules and Jev handle suitable tasks,
while LLM calls are reserved for stages that need language reasoning.
```


The decision engine chooses one of three outcomes:
- **Auto-reply:** send a branded email response through Gmail.
- **Clarification:** request the missing information.
- **Approval/escalation:** create a Gmail draft for human review.

All outcomes feed into **SQLite and Supabase logging**, which powers the **Streamlit dashboard**.

### Ticket lifecycle

1. **Ingest:** The listener polls Gmail, extracts message content and relevant thread context, and checks whether the message has already been processed.
2. **Preprocess:** Email text is cleaned, likely prompt-injection patterns are flagged, and deterministic facts such as amounts or issue indicators are extracted.
3. **Classify:** The classifier produces structured ticket attributes such as intent and urgency, with a keyword fallback when the primary classifier is unavailable.
4. **Understand images:** Screenshot attachments and inline images can be extracted for vision-model analysis. The resulting information is used in the vision-aware query-rewriting/retrieval path.
5. **Retrieve evidence:** Dense semantic search and BM25 keyword search are fused with RRF, with CrossEncoder reranking reported in the implementation.
6. **Check answerability:** The system checks whether the knowledge base appears to contain enough relevant information to answer.
7. **Draft and verify:** The LLM drafts a response from the available evidence. Citation/claim verification components are present, but verify the `require_claim_verification` configuration before assuming this stage is enforced in production.
8. **Choose an action:** Deterministic rules route the ticket to automated reply, clarification, approval, or escalation.
9. **Dispatch and log:** Replies or drafts are handled through Gmail, and ticket data is recorded for dashboard visibility.

## Technology Stack

| Area | Technologies |
|---|---|
| Language and application | Python, Streamlit |
| Email integration | Gmail API, Google OAuth |
| Classification | Jev structured classifier, keyword fallback, deterministic regex rules |
| Language model providers | Gemini, Groq fallback |
| Embeddings | Gemini Embedding API; local backend is also present |
| Retrieval | ChromaDB, BM25, Reciprocal Rank Fusion, CrossEncoder |
| Generation and verification | Grounded draft generation, answerability checks, citation/claim verification |
| Data and audit logs | Supabase PostgreSQL, SQLite |
| Evaluation and tests | Pytest, custom RAG/response evaluation scripts, classification and retrieval evaluation |

Exact model identifiers, thresholds, and provider settings are defined in `config.yaml` and the relevant source modules. Check the current configuration rather than relying on model names in older documentation.

## Repository Guide

```text
.
├── admin_app.py                 # Streamlit administration dashboard
├── config.yaml                  # Model settings and decision thresholds
├── start.sh                     # Application startup script
├── Procfile                     # Deployment process declaration
├── run_sample.py                # Local sample runner
├── populate_db.py               # Demo/sample data utility
├── clear_db.py                  # Database cleanup utility; use with care
├── send_test_emails.py          # Email test utility; can send real messages
├── src/
│   ├── gmail_listener.py        # Gmail polling, parsing, dispatch, drafts
│   ├── pipeline.py              # Main ticket orchestration
│   ├── preprocess.py            # Text cleaning and injection-pattern checks
│   ├── rules_extract.py         # Deterministic rule extraction
│   ├── classifier.py            # Jev classifier and keyword fallback
│   ├── embedder.py              # Embedding backends
│   ├── retriever.py             # Hybrid retrieval and reranking
│   ├── answerability.py         # Knowledge-base answerability gate
│   ├── draft_generator.py       # Grounded response drafting
│   ├── verification.py          # Citation/claim verification
│   ├── llm_client.py            # LLM calls, fallback behavior, caching
│   ├── decision_engine.py       # Action selection and safety rules
│   ├── kb_loader.py             # Knowledge-base parsing and chunking
│   ├── cost.py                  # Token cost calculations
│   ├── logger.py                # SQLite audit logging
│   └── models.py                # Structured data models
├── knowledge_base/              # Policy and support knowledge documents
├── eval/                        # Evaluation scripts and datasets
├── tests/                       # Automated tests
└── docs/                         # Architecture documentation
```

Some utilities are destructive or can interact with real services. Review them before running them.

## Setup

### 1. Prerequisites

- Python version compatible with the project's pinned dependencies
- Gmail API project and OAuth credentials, if testing email integration
- Gemini API key for the configured model/embedding calls
- Groq credentials if using the fallback provider
- Supabase project and database credentials if enabling cloud analytics
- Access to the Jev API if using the primary structured classifier

### 2. Create an environment

```bash
python -m venv .venv
```

Activate it:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Use the Python version supported by the dependency lock/pins in this repository. If installation fails, check the project's dependency versions before upgrading packages.

### 3. Configure environment variables

Create a local `.env` file if the application loads one, or configure variables in your shell/deployment environment. Use the exact names referenced by the source code and deployment configuration; do not commit secrets.

Typical integrations may require credentials for:

- Gemini
- Jev
- Groq
- Supabase URL and key
- Gmail OAuth credentials/token

**Important:** Never commit `credentials.json`, `token.json`, API keys, refresh tokens, or `.env` files. If a credential has already been committed or exposed, revoke/rotate it; deleting the local file alone does not invalidate it.

### 4. Prepare the knowledge base

Review the documents in `knowledge_base/`. Use the repository's ingestion utility only after checking its target collection, persistence path, and whether it overwrites existing data.

```bash
python populate_db.py
```

The exact ingestion workflow depends on the current configuration and existing ChromaDB state. Confirm the command's behavior before running it against a shared or production database.

### 5. Run the dashboard

```bash
streamlit run admin_app.py
```

The dashboard may require valid Supabase configuration and a populated database. Do not expose it publicly without authentication and appropriate access controls.

### 6. Run the application listener

Review `start.sh`, `Procfile`, and `src/gmail_listener.py` before starting the listener. The listener can process messages and may send replies or create drafts through Gmail.

Start it only with a dedicated test inbox and explicit test credentials until end-to-end behavior has been verified. For local development, prefer mocked Gmail/API integrations when available.

## Configuration

`config.yaml` centralizes model/provider choices and decision settings. Before running the system, verify:

- The selected generation and embedding model identifiers
- Classifier configuration and fallback behavior
- Retrieval limits and thresholds
- Answerability and claim-verification settings
- Urgency and monetary escalation thresholds
- Sentiment, human-request, and multi-issue routing flags
- Cost assumptions used by the dashboard and evaluation scripts

Configuration keys should not be assumed to work just because they exist. Confirm that each key is read by the implementation. In the audited version, several decision flags were reported as unused, and claim verification was configured off; validate the current code/config before relying on those controls.

## Evaluation

**Evaluation scope:** Faithfulness and answer relevancy were evaluated on a 60-question set. Of those, 41 questions were used to test the automatic-reply path. The 41-question auto-reply subset is distinct from the full 60-question evaluation set.


The repository includes evaluation assets for classification, retrieval, escalation, and response quality. The audit report records the following results or stored claims:

| Metric | Reported value | Interpretation / caveat |
|---|---:|---|
| Classification accuracy | 76.7% | Reported for a 60-ticket dataset; not independently reproduced without required API access |
| Classification macro F1 | 0.677 | Reported; reproduction requires the configured classifier and matching evaluation setup |
| Faithfulness | 91.5% | Evaluated on a 60-question evaluation set |nd the custom evaluator; not a guarantee of zero hallucinations |
| Answer relevancy | 88.3% | Evaluated on a 60-question evaluation set |nds on the custom evaluator and its embedding/judging setup |
| Retrieval Recall@5 | 70.4% | Value recorded in `evaluation_metrics.json`; a walkthrough reportedly contains a conflicting older claim |
| Median latency (p50) | 5.80 s | Value recorded in `evaluation_metrics.json`; actual runtime varies by model, network, and service availability |
| p95 latency | 10.41 s | Value recorded in `evaluation_metrics.json`; confirm with a fresh benchmark before publishing |

These are **reported project evaluation results**, not independent guarantees of production performance. Results can change with the model version, prompts, knowledge base, thresholds, dataset, and external API behavior. Keep classification, retrieval, answer quality, and escalation safety as separate measurements.

Useful evaluation files include:

- `eval/run_eval.py`
- `eval/ragas_eval.py`
- `eval/custom_ragas.py`
- `eval/threshold_sweep.py`
- `eval/tickets.csv`
- `eval/manual_grading.csv` (if present and populated)

Run evaluation scripts only after inspecting their API calls, costs, and output paths. Some evaluations may require external credentials or paid requests.

## Tests

Run the local test suite:

```bash
python -m pytest tests/ -v
```

The audit report recorded **24 passing tests** and noted that `tests/test_ui_scenarios.py` referenced a missing `app.py` and was not executed successfully. Re-run the suite on the current branch and report the fresh results; do not assume the earlier result still applies.

Important coverage areas to add or verify include:

- End-to-end pipeline behavior with mocked services
- Hybrid retrieval, RRF fusion, and reranking
- LLM cache and provider fallback behavior
- Answerability and claim-verification decisions
- Gmail idempotency, thread handling, and send failures
- Screenshot/VLM extraction and interpretation
- Image prompt injection and evidence grounding
- Dashboard metrics and access control
- Database failures and partial writes
- Cost calculations and configuration validation

## Screenshot / VLM Handling

The implementation audit reports MIME extraction for screenshot/image attachments and a vision-aware query-rewriting path. The exact vision provider/model and supported image formats should be confirmed in the current source and configuration.

A robust screenshot workflow should treat visual output as evidence, not as proof of external state. For example, a payment screenshot may show a visible status or reference number, but the system should not claim that a payment settled unless the available evidence supports that conclusion. Missing, unclear, or contradictory evidence should lead to clarification or human review.

Before using this feature with real student data, test attachment size/type handling, corrupted images, API timeouts, prompt injection in image content, privacy/logging behavior, and the effect of visual findings on escalation decisions.

## Safety, Privacy, and Operational Notes

- Use a dedicated test inbox before enabling automatic replies.
- Keep OAuth credentials and provider API keys out of version control.
- Rotate credentials that may have been exposed in Git history.
- Restrict dashboard access and avoid exposing student emails or raw ticket content unnecessarily.
- Escape untrusted content before inserting it into HTML email templates.
- Keep escalation rules conservative for legal, high-value refund, ambiguous-policy, and insufficient-evidence cases.
- Check whether claim verification is enabled in the active configuration.
- Verify that the bot cannot process its own replies and create a reply loop.
- Treat `clear_db.py` as destructive; inspect its target tables before use.
- Treat `send_test_emails.py` as capable of sending real messages; use only a controlled test account.
- Review data retention, access permissions, and Supabase Row Level Security before handling real student data.

This repository is a project implementation, not a claim of affiliation with or endorsement by Physics Wallah.

## Roadmap

Potential next steps, subject to the current code state:

- Expand automated tests for the complete ticket lifecycle and screenshot/VLM path.
- Validate claim-verification behavior and make decision configuration consistent with runtime logic.
- Add robust self-reply prevention and recovery for revoked/expired OAuth credentials.
- Reconcile evaluation claims across README, walkthrough, and machine-readable reports.
- Add authenticated dashboard access and reduce stored personal information.
- Measure VLM-specific grounding, classification impact, escalation correctness, latency, and cost.
- Benchmark cold starts and memory usage under the actual deployment limits.

## Contributing

1. Create a focused branch.
2. Add or update tests for behavioral changes.
3. Run the relevant test suite.
4. Document configuration changes and evaluation methodology.
5. Never include secrets, real student emails, or unredacted support messages in commits or fixtures.

## License

Add the license applicable to this repository before distributing or reusing the project. No license is assumed by this README.

---

**Built as an engineering project exploring multimodal support automation, hybrid RAG, deterministic safety routing, and human-in-the-loop email workflows.**
