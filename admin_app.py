import streamlit as st
import pandas as pd
import plotly.express as px
import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client, Client

st.set_page_config(page_title="PW Triage Admin", page_icon="📈", layout="wide")

# --- SUPABASE CONNECTION ---
@st.cache_resource
def init_supabase() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        st.error("Missing SUPABASE_URL or SUPABASE_KEY in environment.")
        st.stop()
    return create_client(url, key)

supabase = init_supabase()

# --- DATA FETCHING ---
@st.cache_data(ttl=10) # Refresh every 10 seconds
def load_triage_logs():
    response = supabase.table("triage_logs").select("*").order("created_at", desc=True).execute()
    df = pd.DataFrame(response.data)
    if not df.empty:
        df['created_at'] = pd.to_datetime(df['created_at'])
    return df

@st.cache_data(ttl=30)
def load_cache_logs():
    response = supabase.table("response_cache").select("*").order("created_at", desc=True).execute()
    return pd.DataFrame(response.data)

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("PW Triage Dashboard")
page = st.sidebar.radio("Navigation", [
    "📊 Performance Dashboard", 
    "📥 Live Inbox Feed", 
    "⚠️ Action Required Queue",
    "💸 Cost Optimization"
])

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh Data Now", use_container_width=True):
    load_triage_logs.clear()
    load_cache_logs.clear()
    st.rerun()

st.sidebar.info("Data auto-refreshes every 10 seconds.")

# --- PAGE 1: PERFORMANCE DASHBOARD ---
if page == "📊 Performance Dashboard":
    st.title("Performance Dashboard")
    st.markdown("Track how much time and money the AI is saving your support team in real-time.")
    df = load_triage_logs()
    
    if df.empty:
        st.warning("No data found. Send an email to the triage bot to see data!")
    else:
        # Metrics Calculation
        total_tickets = len(df)
        auto_replied = len(df[df['action_taken'].isin(['AUTO_REPLY', 'AUTO_REPLY_WITH_REVIEW', 'CLARIFY', 'TriageAction.AUTO_REPLY', 'TriageAction.AUTO_REPLY_WITH_REVIEW', 'TriageAction.CLARIFY'])])
        escalated = len(df[df['action_taken'].isin(['ESCALATE', 'APPROVAL_REQUIRED', 'TriageAction.ESCALATE', 'TriageAction.APPROVAL_REQUIRED'])])
        
        auto_rate = (auto_replied / total_tickets) * 100 if total_tickets > 0 else 0
        esc_rate = (escalated / total_tickets) * 100 if total_tickets > 0 else 0
        
        # Calculate Cost (Assuming Gemini 1.5 Flash pricing)
        total_prompt_tokens = df['prompt_tokens'].sum() if 'prompt_tokens' in df.columns else 0
        total_completion_tokens = df['completion_tokens'].sum() if 'completion_tokens' in df.columns else 0
        total_cost = (total_prompt_tokens / 1_000_000 * 0.15) + (total_completion_tokens / 1_000_000 * 0.60)

        # Layout
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Emails Processed", total_tickets)
        col2.metric("Handled by AI", auto_replied, f"{auto_rate:.1f}% Automation Rate")
        col3.metric("Sent to Human Agents", escalated, f"-{esc_rate:.1f}% Sent to Queue", delta_color="inverse")
        col4.metric("Total AI Cost ($)", f"${total_cost:.4f}", f"Approx. Cost")
        
        st.markdown("---")
        
        # Charts
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("What are students asking about?")
            if 'category' in df.columns:
                cat_counts = df['category'].value_counts().reset_index()
                cat_counts.columns = ['Category', 'Count']
                fig_pie = px.pie(cat_counts, values='Count', names='Category', hole=0.4, 
                               color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_pie, use_container_width=True)
                
        with c2:
            st.subheader("How is the AI handling them?")
            if 'action_taken' in df.columns:
                df['clean_action'] = df['action_taken'].apply(lambda x: str(x).replace("TriageAction.", ""))
                act_counts = df['clean_action'].value_counts().reset_index()
                act_counts.columns = ['AI Decision', 'Count']
                
                # Make labels user friendly
                label_map = {
                    "AUTO_REPLY": "✅ Answered Instantly",
                    "AUTO_REPLY_WITH_REVIEW": "✅ Answered (Flagged for Review)",
                    "CLARIFY": "❓ Asked for More Info",
                    "APPROVAL_REQUIRED": "⏳ Drafted (Needs Admin Click)",
                    "ESCALATE": "⚠️ Escalated to Human"
                }
                act_counts['AI Decision'] = act_counts['AI Decision'].map(lambda x: label_map.get(x, x))
                
                fig_bar = px.bar(act_counts, x='AI Decision', y='Count', 
                               color='AI Decision', color_discrete_sequence=px.colors.qualitative.Set2)
                fig_bar.update_layout(showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)


# --- PAGE 2: LIVE INBOX FEED ---
elif page == "📥 Live Inbox Feed":
    st.title("Live Inbox Feed")
    st.markdown("A real-time log of every email the AI reads and what it decides to do.")
    
    df = load_triage_logs()
    if df.empty:
        st.warning("No emails have been processed yet.")
    else:
        df['action_taken'] = df['action_taken'].apply(lambda x: str(x).replace("TriageAction.", ""))
        
        # Format table for non-tech users
        display_df = df[['created_at', 'student_email', 'category', 'urgency', 'action_taken']].copy()
        display_df.columns = ['Date & Time', 'Student Email', 'Issue Category', 'Urgency (1-5)', 'AI Decision']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)


# --- PAGE 3: ACTION REQUIRED QUEUE ---
elif page == "⚠️ Action Required Queue":
    st.title("Action Required Queue")
    st.markdown("Emails that the AI could not resolve automatically or that require human verification.")
    
    df = load_triage_logs()
    if df.empty:
        st.success("🎉 Queue is empty! The AI is handling everything.")
    else:
        # Standardize status and action
        if 'status' not in df.columns:
            df['status'] = 'PENDING'
        else:
            df['status'] = df['status'].fillna('PENDING').astype(str).str.strip().str.upper()
            
        df['action_clean'] = df['action_taken'].apply(lambda x: str(x).replace("TriageAction.", ""))
        
        tab_pending, tab_resolved = st.tabs(["⚠️ Needs Action", "✅ Resolved History"])
        
        with tab_pending:
            human_queue = df[(df['action_clean'].isin(['ESCALATE', 'APPROVAL_REQUIRED', 'AUTO_REPLY_WITH_REVIEW'])) & (df['status'] != 'RESOLVED')]
            
            if human_queue.empty:
                st.success("🎉 Queue is empty! All recent tickets were resolved automatically or approved by your team.")
            else:
                st.warning(f"You have {len(human_queue)} emails waiting in your triage queue.")
                st.markdown("---")
                
                for index, row in human_queue.iterrows():
                    with st.container():
                        col1, col2, col3 = st.columns([2, 5, 3])
                        
                        with col1:
                            st.markdown(f"**{str(row['category']).upper()}**")
                            st.caption(f"Urgency: {'🔥'*int(row.get('urgency', 1))}")
                            
                        with col2:
                            st.markdown(f"**Student:** `{row.get('student_email', 'Unknown')}`")
                            st.caption(f"Received: {row.get('created_at', 'Unknown')}")
                            act = row['action_clean']
                            if act == 'ESCALATE':
                                st.markdown("⚠️ **Escalated to Human Agent** (Out of KB / Threat / Complex)")
                            elif act == 'APPROVAL_REQUIRED':
                                st.markdown("⏳ **Draft Prepared** (Irreversible Action - Review in Gmail Drafts)")
                            elif act == 'AUTO_REPLY_WITH_REVIEW':
                                st.markdown("💬 **Auto-Replied** (At-Risk / Multi-Issue Flagged)")
                                
                        with col3:
                            st.write("")
                            if st.button("✅ Mark as Resolved", key=f"resolve_{row['id']}", use_container_width=True):
                                try:
                                    supabase.table("triage_logs").update({"status": "RESOLVED"}).eq("id", str(row['id'])).execute()
                                    st.success("Ticket resolved!")
                                    load_triage_logs.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to update: {e}")
                    
                    st.markdown("---")
                    
        with tab_resolved:
            resolved_queue = df[df['status'] == 'RESOLVED']
            if resolved_queue.empty:
                st.info("No resolved tickets yet.")
            else:
                res_display = resolved_queue[['created_at', 'student_email', 'category', 'action_clean']].copy()
                res_display.columns = ['Resolved At', 'Student', 'Category', 'Action Taken']
                st.dataframe(res_display, use_container_width=True, hide_index=True)


# --- PAGE 4: COST OPTIMIZATION ---
elif page == "💸 Cost Optimization":
    st.title("Cost Optimization (AI Memory)")
    st.markdown("Every time a student asks a common question, the AI remembers the answer instead of thinking from scratch. This saves API costs and replies instantly.")
    
    df_cache = load_cache_logs()
    if df_cache.empty:
        st.warning("No memory logs found yet.")
    else:
        st.metric("Total Answers Remembered (Money Saved)", len(df_cache))
        
        display_cache = df_cache[['created_at', 'model', 'response']].copy()
        display_cache.columns = ['Date Saved', 'AI Model Used', 'Remembered Answer']
        st.dataframe(display_cache, use_container_width=True, hide_index=True)
