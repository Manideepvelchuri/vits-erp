import streamlit as st
import os

st.set_page_config(
    page_title="VITS ERP — Sandbox Console (Beta)",
    page_icon="🧪",
    layout="wide"
)

# Render a styled premium header
st.markdown("""
<div style="background: linear-gradient(135deg, rgba(139,92,246,0.15) 0%, rgba(0,216,198,0.15) 100%);
            border: 1px solid rgba(139,92,246,0.25); border-radius: 16px;
            padding: 24px; margin-bottom: 25px; text-align: center;">
    <div style="font-size: 3rem; margin-bottom: 10px;">🧪</div>
    <h1 style="color: #8B5CF6; font-family: 'Outfit', sans-serif; margin: 0; font-size: 2.8rem;">Beta Sandbox Environment</h1>
    <p style="color: #cbd5e1; font-family: 'Inter', sans-serif; font-size: 1.1rem; margin-top: 8px;">
        Local experimentation playground for testing next-generation ERP features in isolation.
    </p>
</div>
""", unsafe_allow_html=True)

st.info("👈 **Use the sidebar** to navigate between the sandbox/beta pages.")

c1, c2 = st.columns(2)
with c1:
    st.markdown("### 🛠️ Beta Features Available")
    st.markdown("""
    * **👤 Academic Summary Beta**: A redesigned comprehensive visual summary with custom progress trackers and metrics.
    * **🚨 Bunk Analysis Beta**: Day-of-week absenteeism profiling, consecutive bunk streaks, and risk index scoring.
    * **📈 Historical Analysis**: Attendance processing pipeline spanning from Jan 27 to the current date.
    * **🔎 Validation Dashboard**: Math checks comparing beta calculations against production calculations.
    """)

with c2:
    st.markdown("### 🔒 Sandbox Safety Guarantee")
    st.markdown("""
    * Runs on a isolated local sandbox database (`sandbox_beta.db`).
    * Production PostgreSQL (Supabase) and SQLite databases are completely untouched.
    * All dynamic CSV experiments can be safely run here without polluting production records.
    """)

# Initialize database mapping for sandbox
SANDBOX_DIR = os.path.dirname(os.path.abspath(__file__))
SANDBOX_DB = os.path.join(SANDBOX_DIR, "data", "sandbox_beta.db")
os.makedirs(os.path.join(SANDBOX_DIR, "data"), exist_ok=True)
os.makedirs(os.path.join(SANDBOX_DIR, "experiments"), exist_ok=True)

st.success(f"Connected to Sandbox DB: `{SANDBOX_DB}`")
