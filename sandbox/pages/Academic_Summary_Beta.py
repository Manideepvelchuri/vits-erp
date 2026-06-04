import streamlit as st
import os
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(layout="wide")

st.title("👤 Academic Summary (Beta)")
st.caption("Enhanced sandbox-isolated student dashboard with predictions and recommendations.")

SANDBOX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SANDBOX_DB = os.path.join(SANDBOX_DIR, "data", "sandbox_beta.db")
PROD_DB = os.path.join(os.path.dirname(SANDBOX_DIR), "vits_erp.db")

def get_prod_conn():
    conn = sqlite3.connect(PROD_DB)
    conn.row_factory = sqlite3.Row
    return conn

# For beta purposes, let's load a student from production db and render the beta view
conn = get_prod_conn()
student_row = conn.execute("SELECT * FROM students LIMIT 1").fetchone()
conn.close()

if not student_row:
    st.error("No student profiles found in production DB. Seed or scraper run required first.")
else:
    # Let the user select a student to preview in Beta
    conn = get_prod_conn()
    students_list = conn.execute("SELECT roll_no, name FROM students ORDER BY roll_no").fetchall()
    conn.close()
    
    st.markdown("### 🔍 Select Student Profile to Preview")
    selected_st_str = st.selectbox(
        "Student", 
        [f"{r['roll_no']} - {r['name']}" for r in students_list],
        index=0
    )
    selected_roll = selected_st_str.split(" - ")[0]
    
    # Reload student details
    conn = get_prod_conn()
    student = conn.execute("SELECT * FROM students WHERE roll_no=?", (selected_roll,)).fetchone()
    att_rows = conn.execute("SELECT * FROM attendance WHERE roll_no=?", (selected_roll,)).fetchall()
    conn.close()
    
    total_c = sum((r['hours_conducted'] or 0) for r in att_rows)
    total_a = sum((r['hours_attended'] or 0) for r in att_rows)
    overall = round(total_a / total_c * 100, 1) if total_c else 0.0
    
    # Calculate skip limits
    def can_miss_classes(attended, conducted, target=0.75):
        if conducted == 0: return 0
        return max(0, int((attended - target * conducted) / target))
        
    def classes_needed(attended, conducted, target=0.75):
        if conducted == 0: return 0
        if attended / conducted >= target: return 0
        import math
        return max(0, int(math.ceil((target * conducted - attended) / (1 - target))))

    can_miss = can_miss_classes(total_a, total_c)
    need = classes_needed(total_a, total_c)
    avg_classes_per_day = 6.5
    can_miss_days = round(can_miss / avg_classes_per_day, 1)
    need_days = round(need / avg_classes_per_day, 1)
    
    # Visual gauge chart
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = overall,
        title = {'text': "Overall Attendance %"},
        gauge = {
            'axis': {'range': [None, 100]},
            'steps': [
                {'range': [0, 65], 'color': "rgba(239, 68, 68, 0.1)"},
                {'range': [65, 75], 'color': "rgba(245, 158, 11, 0.1)"},
                {'range': [75, 100], 'color': "rgba(0, 216, 198, 0.1)"}
            ],
            'bar': {'color': "#00D8C6"}
        }
    ))
    fig_gauge.update_layout(height=280, margin=dict(t=30, b=0, l=10, r=10))

    st.markdown("---")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        # Risk Zone Banners
        if overall >= 75:
            st.success(f"🟢 **Safe Zone**: You can miss **{can_miss} classes** (approx. **{can_miss_days} days**) and stay above 75%.")
        elif overall >= 65:
            st.warning(f"🟡 **Risk Zone**: Attend **{need} consecutive classes** (approx. **{need_days} days**) to reach 75%.")
        else:
            st.error(f"🔴 **Debarred Zone**: Critical! You need **{need} classes** (approx. **{need_days} days**) to recover to 75%.")

    with col2:
        st.markdown("### 📚 Subject-wise Performance Breakdown")
        subj_rows = []
        low_att_subjs = []
        for r in att_rows:
            c = r['hours_conducted'] or 0
            a = r['hours_attended'] or 0
            p = round(a / c * 100, 1) if c else 0.0
            
            status = "🟢 Safe" if p >= 75 else "🟡 Risk" if p >= 65 else "🔴 Critical"
            if p < 75:
                low_att_subjs.append((r['subject'], p))
                
            subj_rows.append({
                'Subject': r['subject'],
                'Conducted': c,
                'Attended': a,
                'Percentage': f"{p}%",
                'Status': status
            })
            
        if subj_rows:
            st.dataframe(pd.DataFrame(subj_rows), use_container_width=True)
        else:
            st.info("No subject-wise records found.")
            
    # Alerts and insights
    st.markdown("---")
    c_alert, c_insight = st.columns(2)
    
    with c_alert:
        st.markdown("### 🚨 Low Attendance Alerts")
        if low_att_subjs:
            for sub, p in low_att_subjs:
                st.error(f"⚠️ **{sub}** is at **{p}%** (below target threshold of 75%). Prioritize attending this class.")
        else:
            st.success("🎉 All subjects are in the safe zone (>= 75%). Keep it up!")
            
    with c_insight:
        st.markdown("### 💡 Sandbox Smart Recommendations")
        recommendations = []
        if overall < 75:
            recommendations.append("📚 **Prioritize Attendance**: Your overall attendance is below 75%. Bunking should be strictly suspended.")
        if low_att_subjs:
            recommendations.append(f"🎯 **Target Specific Subjects**: Focus on the {len(low_att_subjs)} subjects currently below 75% to bring up your average.")
        else:
            recommendations.append("🛡️ **Buffer Maintenance**: You have a strong buffer. Maintain at least 75% in each subject to avoid last-minute attendance pressure.")
        
        for rec in recommendations:
            st.info(rec)
            
    # Slider Predictor
    st.markdown("---")
    st.markdown("### 🔮 Interactive Skip Predictor")
    miss_days = st.slider("Select next consecutive days to skip:", 0, 15, 0, key="beta_predictor")
    miss_classes = int(round(miss_days * avg_classes_per_day))
    if miss_days > 0:
        proj_overall = round(total_a / (total_c + miss_classes) * 100, 1)
        if proj_overall >= 75:
            st.success(f"Projected Attendance: **{proj_overall}%** (Safe Zone) ✅ (Missing {miss_days} days / {miss_classes} classes)")
        elif proj_overall >= 65:
            st.warning(f"Projected Attendance: **{proj_overall}%** (Condonation Zone) ⚠️ (Missing {miss_days} days / {miss_classes} classes)")
        else:
            st.error(f"Projected Attendance: **{proj_overall}%** (Debarred Zone) 🚫 (Missing {miss_days} days / {miss_classes} classes)")
