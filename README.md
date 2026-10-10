# PW-Style EdTech Support Ticket Triage Agent

A robust, production-grade support ticket triage agent designed for high-volume Indian edtech operations (PhysicsWallah context: batches, lectures, DPPs, test series, doubt resolution, payments, refunds).

This system actively monitors a Gmail support inbox, intelligently classifies emails using a hybrid RAG approach, and automatically drafts or sends beautiful, branded HTML replies, while providing a real-time admin dashboard to monitor performance and costs.

---

## 🌟 Core Features

1. **Active Gmail Listener (`gmail_listener.py`)**: Automatically polls `supportpw6@gmail.com` for new tickets.
2. **Branded HTML Replies**: The AI sends gorgeous, full-width HTML responses featuring a sleek `#000000` header and the official PW white logo.
3. **Advanced RAG Pipeline**: Uses dense embeddings (powered by the Gemini API) to retrieve relevant policies from the Knowledge Base to ground the AI's response. Uses 0MB of local RAM!
4. **Deterministic Escalation Rules**: If a ticket involves legal threats or high-value refund demands (Rs. 10,000+), it strictly bypasses the LLM and escalates to a human.
5. **Real-time Admin Dashboard (`admin_app.py`)**: A Streamlit dashboard to monitor automation rates, AI token costs, classification accuracy, and review escalated tickets. Live at [https://pw-triage-agent-production.up.railway.app/](https://pw-triage-agent-production.up.railway.app/).
6. **Ragas Evaluation (`ragas_eval.py`)**: Built-in Ragas integration to rigorously score the AI on Faithfulness and Answer Relevancy.

---

## 🚀 Live Demo

1. **Dashboard**: View the live production dashboard here: [PW Triage Agent Dashboard](https://pw-triage-agent-production.up.railway.app/)
2. **Test the AI**: Send an email (in English or Hinglish) to **`supportpw6@gmail.com`**. Wait 30 seconds, and the AI will auto-reply and log the ticket on the dashboard!

---

## 💻 Quickstart

### 1. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/Naveenk654/pw-triage-agent.git
cd pw-triage-agent
pip install -r requirements.txt
```

### 2. Environment Setup
Copy the environment template and provide your API keys:
```bash
cp .env.example .env
```
In `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
```

### 3. Run the System

You can run the dashboard and the email listener simultaneously using the included startup script (which is also used by Railway):
```bash
bash start.sh
```

---

## ☁️ Deployment on Railway

This repository is heavily optimized for 1-click deployment on Railway's Free/Hobby Tier. 

1. Connect your GitHub repository to Railway.
2. Railway will automatically detect the `Procfile` and `start.sh` to boot both the Streamlit app and the Gmail background listener.
3. Go to the **Variables** tab in Railway and paste your keys. 
   - **Important for Gmail OAuth**: Do NOT commit your `credentials.json` or `token.json` to GitHub! Instead, copy the raw JSON text from those files and paste them directly into Railway as environment variables named `GOOGLE_CREDENTIALS_JSON` and `GOOGLE_TOKEN_JSON`. The bot will securely recreate them on boot.
4. (Recommended) Go to the **Volumes** tab and mount a volume at `/app/chroma_db` so the AI's vector database persists across server restarts.
5. Watch the unbuffered live logs (`python -u`)!

---

## 📊 Ragas Evaluation Metrics

Our rigorous offline evaluation (using Mistral/OpenAI Instructor clients) yielded the following safety and accuracy metrics:

- **Faithfulness**: 91.5% (The AI rarely hallucinates information outside the knowledge base).
- **Answer Relevancy**: 88.33% (The AI directly answers the student's core intent).

*Evaluation data is securely stored in `eval/results/evaluation_metrics.json`.*

---

> **Important**: All policy documents in this repository are **fictional sample policies** created strictly for demonstration and evaluation purposes. They do not represent official PhysicsWallah policies.
