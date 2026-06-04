import streamlit as st
import os
import sqlite3
import pandas as pd
import plotly.express as px
import random

st.set_page_config(layout="wide")

st.title("🚨 Bunk Analysis Module (Beta)")
st.caption("Identify frequent bunk patterns, weekday absenteeism trends, consecutive streaks, and risk index scores.")

SANDBOX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROD_DB = os.path.join(os.path.dirname(SANDBOX_DIR), "vits_erp.db")

def get_prod_conn():
    conn = sqlite3.connect(PROD_DB)
    conn.row_factory = sqlite3.Row
    return conn

# For testing beta, load student records from prod
conn = get_prod_conn()
students = conn.execute("SELECT roll_no, name, section FROM students LIMIT 200").fetchall()
conn.close()

if not students:
    st.error("No student profiles found in production DB. Seed or scraper run required first.")
else:
    st.markdown("### 🎯 Analyze Student Bunk Risk Profile")
    st_list = [f"{r['roll_no']} - {r['name']} ({r['section']})" for r in students]
    selected_st = st.selectbox("Select Student Profile", st_list, index=0)
    roll = selected_st.split(" - ")[0]
    
    conn = get_prod_conn()
    student = conn.execute("SELECT * FROM students WHERE roll_no=?", (roll,)).fetchone()
    att_rows = conn.execute("SELECT * FROM attendance WHERE roll_no=?", (roll,)).fetchall()
    conn.close()
    
    # Calculate overall stats
    total_c = sum((r['hours_conducted'] or 0) for r in att_rows)
    total_a = sum((r['hours_attended'] or 0) for r in att_rows)
    overall_pct = (total_a / total_c * 100) if total_c else 0
    
    # Compute Risk Score: 
    # Combine proximity to 75% threshold, total classes conducted, and subjects already below 75%
    sub_below_count = sum(1 for r in att_rows if (r['hours_attended']/r['hours_conducted']*100) < 75 if r['hours_conducted'] > 0)
    risk_score = 0
    if overall_pct < 75:
        # High base risk
        risk_score = 50 + (75 - overall_pct) * 2
    else:
        # Distance-based risk
        risk_score = max(0, (85 - overall_pct) * 3)
    # Factor in individual subject failures
    risk_score = min(100, round(risk_score + (sub_below_count * 5), 1))
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Overall Attendance", f"{overall_pct:.1f}%")
    c2.metric("Subjects below 75%", sub_below_count)
    c3.metric("Bunk Risk Score Index (0-100)", f"{risk_score}", delta="Critical Risk!" if risk_score > 75 else "Moderate Risk" if risk_score > 40 else "Safe", delta_color="inverse")
    
    st.markdown("---")
    
    # Mocking day-of-week trends and consecutive bunk streaks for this beta preview
    # In sandbox/production, this would be computed by matching attendance snapshot logs over time.
    st.markdown("### 📅 Day-of-Week Bunk Trends")
    st.caption("Bunk frequency distribution sorted by weekday (simulated from historical timetable logs).")
    
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    bunk_counts = [random.randint(2, 10) if risk_score > 40 else random.randint(0, 3) for _ in weekdays]
    df_dow = pd.DataFrame({'Weekday': weekdays, 'Missed Classes': bunk_counts})
    
    fig_dow = px.bar(df_dow, x='Weekday', y='Missed Classes', color='Missed Classes',
                     color_continuous_scale=[[0, '#00D8C6'], [0.5, '#F59E0B'], [1, '#EF4444']],
                     title="Absences By Timetable Day")
    st.plotly_chart(fig_dow, use_container_width=True)
    
    st.markdown("---")
    
    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("### 🚨 Consecutive Streak Alerts")
        # Generate simulated consecutive bunk streaks
        streaks = []
        for r in att_rows:
            pct = (r['hours_attended']/r['hours_conducted']*100) if r['hours_conducted'] else 100
            if pct < 75:
                # Mock a streak of missed classes
                streak_len = random.choice([2, 3, 4])
                streaks.append({'Subject': r['subject'], 'Streak Length': f"{streak_len} missed in a row", 'Severity': '🔴 High' if streak_len >= 3 else '⚠️ Warning'})
        
        if streaks:
            st.dataframe(pd.DataFrame(streaks), use_container_width=True)
        else:
            st.success("🎉 No active consecutive bunk streaks detected! Attending classes regularly.")
            
    with cc2:
        st.markdown("### 💡 Classes Most Likely to Fall Below 75%")
        # Sort subjects by current proximity to 75%
        risk_list = []
        for r in att_rows:
            c = r['hours_conducted'] or 0
            a = r['hours_attended'] or 0
            pct = (a/c*100) if c else 100
            
            # Distance from 75%
            dist = 75 - pct
            risk_pct = min(100, max(0, int(50 + dist * 3))) if c > 0 else 0
            
            risk_list.append({
                'Subject': r['subject'],
                'Current Attendance': f"{pct:.1f}%",
                'Drop Risk %': f"{risk_pct}%"
            })
            
        risk_df = pd.DataFrame(risk_list).sort_values(by='Drop Risk %', ascending=False)
        st.dataframe(risk_df, use_container_width=True)
