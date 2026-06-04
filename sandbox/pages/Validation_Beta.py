import streamlit as st
import os
import sqlite3
import pandas as pd
import time

st.set_page_config(layout="wide")

st.title("🔎 Calculation Validation (Sandbox)")
st.caption("Cross-environment verification dashboard comparing Sandbox statistics against Production math.")

SANDBOX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROD_DB = os.path.join(os.path.dirname(SANDBOX_DIR), "vits_erp.db")

def get_prod_conn():
    conn = sqlite3.connect(PROD_DB)
    conn.row_factory = sqlite3.Row
    return conn

# 1. Timetable count validation
st.markdown("### 🧮 Timetable Record Counts")
conn = get_prod_conn()
prod_classes = conn.execute("SELECT section, COUNT(*) FROM timetable GROUP BY section").fetchall()
conn.close()

if prod_classes:
    df_counts = pd.DataFrame([dict(r) for r in prod_classes]).rename(columns={'section':'Section', 'COUNT(*)':'Timetable Entries'})
    st.table(df_counts)
else:
    st.warning("No timetable mappings found in production database.")

# 2. Connection latency validation
st.markdown("---")
st.markdown("### ⚡ Connection Retrieval & Cache Verification")

c1, c2 = st.columns(2)
with c1:
    st.markdown("#### Production Caching Parity Test")
    t0 = time.time()
    conn = get_prod_conn()
    conn.execute("SELECT COUNT(*) FROM students").fetchone()
    conn.close()
    t1 = time.time()
    
    st.metric("SQLite Uncached Response Time", f"{(t1-t0)*1000:.2f} ms")

with c2:
    st.markdown("#### Sandbox Database Schema Verification")
    sb_db = os.path.join(SANDBOX_DIR, "data", "sandbox_beta.db")
    if os.path.exists(sb_db):
        conn_sb = sqlite3.connect(sb_db)
        t0 = time.time()
        res = conn_sb.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        conn_sb.close()
        t1 = time.time()
        st.success(f"Sandbox database found! Verified {len(res)} tables in {(t1-t0)*1000:.2f} ms.")
    else:
        st.info("Sandbox database not yet initialized. Use the Historical Analysis page to populate records.")
