"""Streamlit Web UI for PhysicsWallah-Style Support Ticket Triage Agent."""

import streamlit as st
import json
import os
import time
from dotenv import load_dotenv
load_dotenv()
from src.pipeline import TriagePipeline
from src.logger import TriageLogger

st.set_page_config(
    page_title="PW Support Triage Agent",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for polished dashboard look
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 12px 16px;
        border-left: 4px solid #1E88E5;
        margin-bottom: 8px;
    }
    .badge-auto-reply {
        background-color: #D4EDDA;
        color: #155724;
        font-weight: 700;
        font-size: 22px;
        padding: 8px 16px;
        border-radius: 6px;
        display: inline-block;
        border: 1px solid #C3E6CB;
    }
    .badge-escalate {
        background-color: #F8D7DA;
        color: #721C24;
        font-weight: 700;
        font-size: 22px;
        padding: 8px 16px;
        border-radius: 6px;
        display: inline-block;
        border: 1px solid #F5C6CB;
    }
</style>
""", unsafe_allow_html=True)


DEMO_TICKETS = {
    "1. Refund SLA (Safe Auto-Reply)": "How long does a refund normally take?",
    "2. High Value + Escalation": "I paid ₹25,000 three days ago, still don't have access, contacted support twice, and want my money back.",
    "3. Out of KB (Ownership Transfer)": "Can I transfer my subscription to another student?",
    "4. Video Buffering & DRM Error": "Video keeps buffering and giving DRM error code DRM-401 whenever I open the app on my phone.",
    "5. Double Deduction via UPI": "Amount Rs. 3500 debited twice via UPI-998877665544 for Lakshya Batch order PW-99214. Please fix urgently!",
    "6. Hostile Consumer Court Threat": "This platform is a scam! Refund my full fee immediately or I am filing a case with consumer court and police today itself!"
}


@st.cache_resource
def get_pipeline(failure_mode=None):
    return TriagePipeline(simulate_failure=failure_mode)


# Sidebar controls
st.sidebar.title("⚙️ Triage Agent Controls")
st.sidebar.markdown("**PhysicsWallah EdTech Context**")

sim_fail = st.sidebar.selectbox(
    "Failure Simulation Mode:",
    ["None (Normal)", "Simulate Jev Failure", "Simulate LLM Failure", "Simulate Retriever Failure"]
)

failure_arg = None
if sim_fail == "Simulate Jev Failure":
    failure_arg = "jev"
elif sim_fail == "Simulate LLM Failure":
    failure_arg = "llm"
elif sim_fail == "Simulate Retriever Failure":
    failure_arg = "retriever"

st.sidebar.divider()
st.sidebar.markdown("### 📊 System Status")
st.sidebar.info("""
- **Primary LLM**: Gemini 3.5 Flash-lite (Groq fallback)
- **Structured Judge**: Jev 1.13
- **Embedder**: multilingual-e5-small (Local) / Gemini
- **Decision Engine**: Deterministic Python (13 Rules)
""")

# Main Navigation Tabs
tab_triage, tab_audit, tab_eval = st.tabs(["🎯 Live Ticket Triage", "📋 Audit Logs & Costs", "📈 Evaluation & Metrics"])

with tab_triage:
    st.subheader("Student Query Triage")
    st.caption("Enter a student support inquiry or pick a sample scenario to test the deterministic safety pipeline.")

    # Quick demo buttons in columns
    st.markdown("**Sample Demo Scenarios:**")
    cols = st.columns(3)
    cols_row2 = st.columns(3)
    
    selected_query = None
    keys = list(DEMO_TICKETS.keys())
    
    for i in range(3):
        if cols[i].button(keys[i], key=f"btn_{i}"):
            selected_query = DEMO_TICKETS[keys[i]]
            
    for i in range(3, 6):
        if cols_row2[i-3].button(keys[i], key=f"btn_{i}"):
            selected_query = DEMO_TICKETS[keys[i]]

    ticket_input = st.text_area(
        "Student Ticket Query:",
        value=selected_query or (st.session_state.get("current_query", "How long does a refund normally take?")),
        height=100
    )
    st.session_state["current_query"] = ticket_input

    if st.button("🚀 Analyze Ticket", type="primary"):
        with st.spinner("Processing through Preprocess -> Hybrid Retrieval -> Verification -> Decision Engine..."):
            pipeline = get_pipeline(failure_arg)
            try:
                res = pipeline.process_ticket(ticket_input)
                st.session_state["last_result"] = res
            except Exception as e:
                st.error(f"Friendly Error Notice: An unexpected exception occurred: {str(e)}")

    if "last_result" in st.session_state:
        res = st.session_state["last_result"]
        dec = res["decision"]
        cls = res["classification"]
        
        st.divider()
        
        # 1. Headline Decision Badge
        col_badge, col_meta = st.columns([1, 2])
        with col_badge:
            if dec["action"] == "AUTO_REPLY":
                st.markdown('<div class="badge-auto-reply">✅ AUTO-REPLY</div>', unsafe_allow_html=True)
            elif dec["action"] == "CLARIFY":
                st.markdown('<div class="badge-clarify" style="background-color: #FFF3CD; color: #856404; font-weight: 700; font-size: 22px; padding: 8px 16px; border-radius: 6px; display: inline-block; border: 1px solid #FFEEBA;">❓ CLARIFY</div>', unsafe_allow_html=True)
            elif dec["action"] == "APPROVAL_REQUIRED":
                st.markdown('<div class="badge-approval" style="background-color: #CCE5FF; color: #004085; font-weight: 700; font-size: 22px; padding: 8px 16px; border-radius: 6px; display: inline-block; border: 1px solid #B8DAFF;">✍️ APPROVAL REQUIRED</div>', unsafe_allow_html=True)
            elif dec["action"] == "AUTO_REPLY_WITH_REVIEW":
                st.markdown('<div class="badge-review" style="background-color: #E2E3E5; color: #383D41; font-weight: 700; font-size: 22px; padding: 8px 16px; border-radius: 6px; display: inline-block; border: 1px solid #D6D8DB;">👀 QA REVIEW</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="badge-escalate">🚨 ESCALATE TO HUMAN</div>', unsafe_allow_html=True)
                
        with col_meta:
            urgency_labels = {1: "Low", 2: "Moderate", 3: "Elevated", 4: "High", 5: "Critical"}
            urg_val = cls["urgency"]
            st.markdown(f"**Category:** `{cls['category'].upper()}` | **Urgency:** `{urg_val}/5 ({urgency_labels.get(urg_val, 'Standard')})` | **At-Risk:** `{'Yes' if cls['churn_risk'] or cls['angry_tone'] else 'No'}`")

        # 2. Plain Language Reasons
        st.markdown("### 🔍 Decision Reasons")
        for reason in dec["reasons"]:
            if dec["action"] == "ESCALATE":
                st.warning(f"⚠️ {reason}")
            else:
                st.success(f"✓ {reason}")

        # 3. Draft Reply or Escalation Guidance
        st.markdown("### ✍️ Drafted Support Action")
        if dec["action"] in ["AUTO_REPLY", "AUTO_REPLY_WITH_REVIEW", "APPROVAL_REQUIRED"] and dec["draft_reply"]:
            reply_text = st.text_area("Editable Draft Reply:", value=dec["draft_reply"], height=120)
            st.markdown(f"**Policy Citations:** `{dec['citations']}`")
            col_send, col_esc = st.columns([1, 1])
            with col_send:
                if st.button("📨 Send Verified Auto-Reply to Student", type="primary"):
                    st.success("Reply successfully dispatched via simulated WhatsApp/Email channel!")
            with col_esc:
                if st.button("👥 Escalate to Tier-2 Agent Anyway"):
                    st.info("Ticket marked for manual supervisory review.")
        elif dec["action"] == "CLARIFY" and dec.get("clarification_question"):
            reply_text = st.text_area("Clarification Request (To Student):", value=dec["clarification_question"], height=68)
            if st.button("📨 Send Clarification Request", type="primary"):
                st.success("Clarification request sent. Waiting for student response.")
        else:
            st.info("ℹ️ Automated reply was withheld for student safety. This ticket requires review by a customer care representative.")
            if dec.get("handoff_packet"):
                st.markdown("### 📋 Escalation Handoff Packet")
                st.info(dec["handoff_packet"])

        # 4. Retrieved Policy Evidence
        st.markdown("### 📚 Retrieved Policy Evidence")
        evidence = res.get("retrieval", [])
        if evidence:
            for idx, ev in enumerate(evidence[:3], 1):
                with st.expander(f"Chunk #{idx}: [{ev['document']}] - {ev['section_title']} (Dense: {ev['dense_score']:.3f}, BM25 Rank: {ev['bm25_rank']})"):
                    st.markdown(ev["content"])
        else:
            st.write("No matching policy chunks retrieved.")

        # 5. Collapsed Technical Details
        with st.expander("🛠️ Advanced Technical Execution Details"):
            st.json({
                "latency_s": res["latency_s"],
                "cost": res["cost"],
                "rewritten_search_query": res.get("search_query", ""),
                "classification": cls,
                "rule_signals": res["rule_signals"],
                "answerability": res["answerability"],
                "draft": res["draft"],
                "decision": dec
            })

with tab_audit:
    st.subheader("📋 SQLite Audit Trail & Financial Metrics")
    logger = TriageLogger()
    stats = logger.get_summary_stats()
    
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("Total Tickets Processed", stats["total_tickets_logged"])
    m_col2.metric("Estimated Cost (List Price)", f"${stats['estimated_cost_total']:.4f}")
    m_col3.metric("Actual Cash Spend", f"${stats['actual_spend_total']:.2f}")
    m_col4.metric("Jev Budget Remaining", f"${max(0.0, 5.0 - stats['estimated_cost_total']):.2f}")
    
    st.markdown("#### Decisions Breakdown")
    st.write(stats.get("decisions", {}))
    st.caption("Audit logs stored securely in `data/triage_logs.db` without fabricating missing tokens.")

with tab_eval:
    st.subheader("📈 System Evaluation & Benchmarks")
    st.markdown("""
    The system evaluation suite covers 60 structured test scenarios across 8 core categories, measuring:
    - **Classification Accuracy & F1**
    - **Escalation Precision / Recall**
    - **Retrieval Hit Rate @ 3 & @ 5**
    - **Prompt Injection Defense Rate**
    - **Citation Grounding Rate**
    """)
    st.info("Evaluation metrics will populate in Phase 4 once the benchmark dataset sweep completes.")
