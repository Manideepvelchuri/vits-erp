import streamlit as st
import os
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

st.title("📈 Historical Data Analysis (Sandbox)")
st.caption("Dedicated sandbox pipeline processing attendance records from January 27 through today.")

# Sandbox paths
SANDBOX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(SANDBOX_DIR, "data", "sandbox_beta.db")
PROD_CSV_DIR = os.path.join(os.path.dirname(SANDBOX_DIR), "attandance database for db construction")

def get_sandbox_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_sandbox_db(conn):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS sandbox_attendance_history (
        roll_no TEXT,
        subject_code TEXT,
        snapshot_date TEXT,
        hours_attended INTEGER,
        hours_conducted INTEGER,
        percentage REAL,
        PRIMARY KEY (roll_no, subject_code, snapshot_date)
    )
    """)
    conn.commit()

conn = get_sandbox_db()
init_sandbox_db(conn)
conn.close()

st.markdown("### ⚙️ Historical Pipeline Control")
c1, c2 = st.columns([1, 2])

with c1:
    st.info("💡 Imports data from production CSV files and builds daily backdated snapshots starting from January 27.")
    if st.button("🚀 Populate / Refresh Historical Data"):
        if not os.path.exists(PROD_CSV_DIR):
            st.error("Production CSV directory not found.")
        else:
            conn = get_sandbox_db()
            # Clear existing sandbox history for clean reload
            conn.execute("DELETE FROM sandbox_attendance_history")
            
            csv_files = [f for f in os.listdir(PROD_CSV_DIR) if f.lower().endswith(".csv") and f != "attendance_master.csv"]
            
            # Seed backdated records from Jan 27 to today
            start_date = datetime(2026, 1, 27)
            end_date = datetime.now()
            total_days = (end_date - start_date).days + 1
            
            records_count = 0
            with st.spinner("Processing historical snapshots (Jan 27 → Today)..."):
                for fname in csv_files:
                    fpath = os.path.join(PROD_CSV_DIR, fname)
                    df = pd.read_csv(fpath)
                    df.columns = [c.strip() for c in df.columns]
                    
                    # Dynamically resolve roll and subjects
                    roll_col = next((c for c in df.columns if c.lower().replace(' ', '').replace('_', '') == 'rollno'), None)
                    if not roll_col:
                        continue
                        
                    # Filter columns to get subject columns
                    subjects = [c for c in df.columns if c not in (roll_col, 'S.No.', 'Student Name', 'Percentage(%)', 'Total', 'Section')]
                    
                    # Conducted hours row (Row 1 usually)
                    cond_row = df[df[roll_col].astype(str).str.contains("Conducted", case=False, na=False)]
                    if cond_row.empty:
                        continue
                    
                    # Let's mock a gradual historical accumulation
                    for _, row in df.iterrows():
                        roll = str(row[roll_col]).strip().upper()
                        if not roll or "CONDUCTED" in roll:
                            continue
                            
                        for sub in subjects:
                            try:
                                final_att = int(float(row.get(sub, 0)))
                                final_cond = int(float(cond_row.iloc[0].get(sub, 0)))
                            except Exception:
                                continue
                                
                            # Back-interpolate attendance from Jan 27 to today
                            for day_idx in range(total_days):
                                current_day = start_date + timedelta(days=day_idx)
                                day_str = current_day.strftime("%Y-%m-%d")
                                
                                # Scale values linearly to simulate snapshot histories
                                factor = (day_idx + 1) / total_days
                                c_val = int(round(final_cond * factor))
                                a_val = int(round(final_att * factor))
                                pct = round(a_val * 100.0 / c_val, 1) if c_val > 0 else 100.0
                                
                                conn.execute("""
                                    INSERT OR REPLACE INTO sandbox_attendance_history (roll_no, subject_code, snapshot_date, hours_attended, hours_conducted, percentage)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (roll, sub, day_str, a_val, c_val, pct))
                                records_count += 1
                                
            conn.commit()
            conn.close()
            st.success(f"Successfully populated {records_count} sandbox history records!")

with c2:
    st.markdown("### 🔎 Sandbox Dataset Quick Look")
    conn = get_sandbox_db()
    count_row = conn.execute("SELECT COUNT(*) FROM sandbox_attendance_history").fetchone()
    count = count_row[0] if count_row else 0
    conn.close()
    
    st.metric("Total Historical Records", count)
    
    if count > 0:
        conn = get_sandbox_db()
        sample = conn.execute("SELECT * FROM sandbox_attendance_history LIMIT 10").fetchall()
        conn.close()
        st.dataframe(pd.DataFrame([dict(r) for r in sample]))
        
        # Plot attendance curve for a sample student
        st.markdown("#### Sample Historical Trend")
        conn = get_db_connection = get_sandbox_db()
        sample_roll = conn.execute("SELECT DISTINCT roll_no FROM sandbox_attendance_history LIMIT 1").fetchone()
        if sample_roll:
            roll = sample_roll[0]
            rows = conn.execute("SELECT snapshot_date, subject_code, percentage FROM sandbox_attendance_history WHERE roll_no=? ORDER BY snapshot_date ASC", (roll,)).fetchall()
            df_plot = pd.DataFrame([dict(r) for r in rows])
            fig = px.line(df_plot, x='snapshot_date', y='percentage', color='subject_code', title=f"Historical Cumulative Attendance for {roll}")
            st.plotly_chart(fig, use_container_width=True)
        conn.close()
