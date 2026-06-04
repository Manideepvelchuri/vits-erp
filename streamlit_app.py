"""
VITS Academic ERP — Streamlit Version (FIXED + ENHANCED)
Pure Python, multi-page web app
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os, math, hashlib
import datetime
from datetime import datetime as dt

# Auto-detect: use PostgreSQL (Supabase) if DATABASE_URL or st.secrets is set, else SQLite
def _load_db_module():
    try:
        import streamlit as _st
        _url = _st.secrets.get("database", {}).get("url", "")
        if _url:
            return "pg"
    except Exception:
        pass
    if os.environ.get("DATABASE_URL"):
        return "pg"
    return "sqlite"

_DB_BACKEND = _load_db_module()
if _DB_BACKEND == "pg":
    from database_pg import (
        init_db, get_db_connection, get_config_map,
        CLASSES, SECTION_SUBJECTS, SUBJECT_CREDITS, SEM1_SUBJECTS,
        score_to_grade, compute_sgpa, backup_db, compute_cgpa,
        parse_sem1_results_csv, decode_roll_branch
    )
else:
    from database import (
        init_db, get_db_connection, get_config_map,
        CLASSES, SECTION_SUBJECTS, SUBJECT_CREDITS, SEM1_SUBJECTS,
        score_to_grade, compute_sgpa, backup_db, compute_cgpa,
        parse_sem1_results_csv, decode_roll_branch
    )
import harvester
import pdf_generator


def get_image_base64(path):
    import base64
    if os.path.exists(path):
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    return ""


def parse_period_string(p_val):
    p_val = p_val.strip().replace(" ", "")
    
    # Check if it's a standard period range like 1-3 or single digit like 5
    if '-' in p_val and not ':' in p_val:
        try:
            start_p, end_p = map(int, p_val.split('-'))
            return list(range(start_p, end_p + 1))
        except ValueError:
            pass
            
    if p_val.isdigit():
        return [int(p_val)]
        
    # Check if it's a time range like 8:45-9:35
    if ':' in p_val:
        def to_mins(t_str):
            if len(t_str) == 3:
                h = int(t_str[0])
                m = int(t_str[1:])
            elif len(t_str) == 4:
                h = int(t_str[:2])
                m = int(t_str[2:])
            else:
                raise ValueError
            
            if h < 8:
                h += 12
            return h * 60 + m
            
        try:
            parts = p_val.replace('to', '-').split('-')
            if len(parts) == 2:
                start_m = to_mins(parts[0].replace(':', ''))
                end_m = to_mins(parts[1].replace(':', ''))
                
                period_intervals = {
                    1: (525, 575),  # 8:45 - 9:35
                    2: (575, 625),  # 9:35 - 10:25
                    3: (640, 690),  # 10:40 - 11:30
                    4: (690, 740),  # 11:30 - 12:20
                    5: (790, 840),  # 1:10 - 2:00
                    6: (840, 885),  # 2:00 - 2:45
                    7: (885, 930)   # 2:45 - 3:30
                }
                
                matched = []
                for p_num, (p_start, p_end) in period_intervals.items():
                    if max(start_m, p_start) + 5 < min(end_m, p_end):
                        matched.append(p_num)
                if matched:
                    return matched
        except Exception:
            pass
            
    try:
        return [int(float(p_val))]
    except ValueError:
        pass
        
    return []


# ── Admin password helpers (DB-stored, hashed) ────────────────
def _hash_pwd(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def ensure_admin_pwd():
    conn = get_db_connection()
    row = conn.execute("SELECT value FROM config WHERE key='admin_pwd_hash'").fetchone()
    if not row:
        default = os.environ.get('ADMIN_PASSWORD', 'vits@admin123')
        conn.execute("INSERT INTO config(key,value) VALUES('admin_pwd_hash',?) ON CONFLICT(key) DO NOTHING",
                     (_hash_pwd(default),))
        conn.commit()
    conn.close()

def verify_admin_pwd(pwd):
    conn = get_db_connection()
    row = conn.execute("SELECT value FROM config WHERE key='admin_pwd_hash'").fetchone()
    conn.close()
    if row:
        return _hash_pwd(pwd) == row['value']
    return pwd == os.environ.get('ADMIN_PASSWORD', 'vits@admin123')

def change_admin_pwd(new_pwd):
    conn = get_db_connection()
    conn.execute("INSERT INTO config(key,value) VALUES('admin_pwd_hash',?) "
                 "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (_hash_pwd(new_pwd),))
    conn.commit()
    conn.close()


# ── Attendance intelligence math ──────────────────────────────
def can_miss_classes(attended, conducted, target=0.75):
    """How many future classes can be skipped staying >= target."""
    if conducted == 0:
        return 0
    x = math.floor((attended - target * conducted) / target)
    return max(0, x)

def classes_needed(attended, conducted, target=0.75):
    """How many to attend continuously to reach target."""
    if conducted == 0:
        return 0
    cur = attended / conducted
    if cur >= target:
        return 0
    n = math.ceil((target * conducted - attended) / (1 - target))
    return max(0, n)


# ── Background Automation Scheduler ───────────────────────────
# Only run on local deployments (APScheduler crashes on Streamlit Cloud)
@st.cache_resource
def start_global_scheduler():
    is_cloud = bool(os.environ.get("DATABASE_URL") or os.environ.get("STREAMLIT_SHARING_MODE"))
    try:
        is_cloud = is_cloud or bool(st.secrets.get("database"))
    except Exception:
        pass
    if is_cloud:
        print("[Scheduler] Cloud deployment detected — scheduler disabled. Use manual Fetch button.")
        return None
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler(daemon=True)
        def _scheduled_scrape():
            try:
                conn = get_db_connection()
                cfg = get_config_map(conn)
                conn.close()
                sem = cfg.get('active_semester', 'Sem 2')
                harvester.bulk_scrape_all(semester=sem)
                backup_db()
            except Exception as e:
                print(f"[Scheduler] error: {e}")
        scheduler.add_job(_scheduled_scrape, 'cron', hour=18, minute=0,
                          id='daily_scrape', replace_existing=True)
        scheduler.start()
        return scheduler
    except Exception as e:
        print(f"[Scheduler] Could not start: {e}")
        return None

global_scheduler = start_global_scheduler()


# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="VITS Student Academic Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize DB once per app lifetime (cached globally)
@st.cache_resource
def startup_db_init():
    init_db()
    ensure_admin_pwd()

startup_db_init()

defaults = {
    'logged_in': False, 'role': None, 'user_id': None,
    'user_name': None, 'section': None
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Custom CSS (dark glassmorphism) ──────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 10% 10%, rgba(139, 92, 246, 0.08) 0%, transparent 40%),
                radial-gradient(circle at 90% 90%, rgba(0, 216, 198, 0.08) 0%, transparent 40%),
                #070913 !important;
}
[data-testid="stSidebar"] {
    background: rgba(10, 14, 26, 0.8) !important;
    backdrop-filter: blur(25px) !important;
    border-right: 1px solid rgba(0, 216, 198, 0.12) !important;
}
h1, h2, h3, h4, h5, h6 {
    color: #ffffff !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}
h1 { text-shadow: 0 0 30px rgba(0, 216, 198, 0.25) !important; }
p, label, li, [data-testid="stMarkdownContainer"] p {
    color: #cbd5e1 !important;
    font-family: 'Inter', sans-serif !important;
}
div[data-testid="stForm"] {
    background: rgba(15, 23, 42, 0.45) !important;
    backdrop-filter: blur(20px) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 20px !important;
    padding: 28px !important;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25) !important;
}
div[data-testid="stMetric"] {
    background: rgba(20, 28, 48, 0.45) !important;
    backdrop-filter: blur(15px) !important;
    border: 1px solid rgba(0, 216, 198, 0.1) !important;
    border-radius: 16px !important;
    padding: 18px 24px !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
div[data-testid="stMetric"]:hover {
    border-color: rgba(0, 216, 198, 0.3) !important;
    box-shadow: 0 12px 40px rgba(0, 216, 198, 0.12) !important;
}
div[data-testid="stMetricValue"] > div {
    color: #ffffff !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 800 !important;
    font-size: 1.55rem !important;
    text-shadow: 0 0 10px rgba(0, 216, 198, 0.25);
    white-space: nowrap !important;
    overflow: visible !important;
}
div[data-testid="stMetricLabel"] > div {
    color: #94a3b8 !important;
    font-size: 0.95rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}
.stButton>button {
    background: linear-gradient(135deg, #00D8C6 0%, #8B5CF6 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 12px 28px !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    font-family: 'Outfit', sans-serif !important;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
    box-shadow: 0 4px 15px rgba(0, 216, 198, 0.2) !important;
}
.stButton>button:hover {
    box-shadow: 0 8px 25px rgba(0, 216, 198, 0.4), 0 0 15px rgba(139, 92, 246, 0.3) !important;
    color: #ffffff !important;
}
div[data-baseweb="input"], div[data-baseweb="select"], .stTextArea textarea, .stDateInput input {
    background-color: rgba(13, 18, 30, 0.8) !important;
    border-radius: 12px !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    color: #ffffff !important;
}
div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within {
    border-color: #00D8C6 !important;
    box-shadow: 0 0 10px rgba(0, 216, 198, 0.2) !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] {
    display: flex !important; flex-direction: column !important;
    gap: 8px !important; margin-top: 15px !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] label {
    background: rgba(255, 255, 255, 0.02) !important;
    border: 1px solid rgba(255, 255, 255, 0.04) !important;
    border-radius: 12px !important;
    padding: 10px 16px !important;
    margin: 0 !important;
    color: #cbd5e1 !important;
    font-weight: 500 !important;
    font-family: 'Inter', sans-serif !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background: rgba(0, 216, 198, 0.08) !important;
    border-color: rgba(0, 216, 198, 0.25) !important;
    color: #ffffff !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] [data-baseweb="radio"] > div:first-child {
    display: none !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] label [data-testid="stMarkdownContainer"] p {
    margin-left: 0 !important; color: inherit !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input[type="radio"]:checked) {
    background: linear-gradient(135deg, rgba(0, 216, 198, 0.15) 0%, rgba(139, 92, 246, 0.15) 100%) !important;
    border-color: #00D8C6 !important;
    color: #00D8C6 !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 15px rgba(0, 216, 198, 0.1) !important;
}
button[role="tab"] {
    background-color: transparent !important;
    color: #94a3b8 !important;
    border: none !important;
    font-weight: 600 !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 1rem !important;
    padding: 12px 24px !important;
}
button[role="tab"][aria-selected="true"] {
    color: #00D8C6 !important;
    border-bottom: 2px solid #00D8C6 !important;
}
button[role="tab"]:hover { color: #ffffff !important; }
details[data-testid="stExpander"] {
    background: rgba(20, 28, 48, 0.3) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    border-radius: 14px !important;
    margin-bottom: 12px !important;
}
details[data-testid="stExpander"] summary {
    padding: 14px 20px !important;
    font-weight: 600 !important;
    font-family: 'Outfit', sans-serif !important;
    color: #ffffff !important;
}
details[data-testid="stExpander"] summary:hover {
    background: rgba(255, 255, 255, 0.02) !important;
    color: #00D8C6 !important;
}
div[data-testid="stAlert"] {
    background-color: rgba(15, 23, 42, 0.45) !important;
    border-radius: 14px !important;
    border-width: 1px !important;
    backdrop-filter: blur(10px) !important;
}
@keyframes fadeInUp {
    from { opacity: 0; }
    to { opacity: 1; }
}
div[data-testid="stDataFrame"] {
    background: rgba(10, 14, 26, 0.4) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 12px !important;
}
table.premium-table {
    width: 100% !important; border-collapse: collapse !important;
    margin: 15px 0 !important; font-family: 'Inter', sans-serif !important;
    background: rgba(20, 28, 48, 0.35) !important;
    backdrop-filter: blur(15px) !important;
    border: 1px solid rgba(0, 216, 198, 0.12) !important;
    border-radius: 12px !important; overflow: hidden !important;
}
table.premium-table th {
    background: linear-gradient(135deg, rgba(0, 216, 198, 0.15) 0%, rgba(139, 92, 246, 0.15) 100%) !important;
    color: #00D8C6 !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important; text-transform: uppercase !important;
    font-size: 0.85rem !important; letter-spacing: 0.05em !important;
    padding: 14px 18px !important; text-align: left !important;
    border-bottom: 1px solid rgba(0, 216, 198, 0.15) !important;
}
table.premium-table td {
    padding: 12px 18px !important; color: #e2e8f0 !important;
    font-size: 0.9rem !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
}
table.premium-table tr:hover { background: rgba(0, 216, 198, 0.05) !important; }
table.premium-table tr:last-child td { border-bottom: none !important; }

/* Subject card */
.subject-card {
    background: rgba(20, 28, 48, 0.4);
    backdrop-filter: blur(15px);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 12px;
    transition: all 0.25s ease;
}
.subject-card:hover {
    border-color: rgba(0,216,198,0.3);
    box-shadow: 0 10px 30px rgba(0,216,198,0.1);
}
.card-bar-bg {
    width: 100%; height: 8px; background: rgba(255,255,255,0.08);
    border-radius: 99px; overflow: hidden; margin: 10px 0;
}
.card-bar-fill { height: 100%; border-radius: 99px; transition: width 0.6s ease; }
.insight-box {
    background: linear-gradient(135deg, rgba(0,216,198,0.06) 0%, rgba(139,92,246,0.06) 100%);
    border: 1px solid rgba(0,216,198,0.12);
    border-radius: 16px; padding: 18px; margin: 8px 0;
}
.status-banner {
    border-radius: 18px; padding: 20px 24px; margin: 16px 0;
    backdrop-filter: blur(15px); font-family: 'Inter', sans-serif;
}
</style>
""", unsafe_allow_html=True)


# ── Premium Table Helper ─────────────────────────────────────
def st_premium_table(df):
    html = df.to_html(index=False, classes='premium-table')
    st.markdown(html, unsafe_allow_html=True)


def apply_premium_plotly_theme(fig, title_text=""):
    fig.update_layout(
        font_family="Inter, sans-serif",
        title={
            'text': title_text,
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 16, 'color': '#ffffff', 'family': 'Outfit, sans-serif'}
        },
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend={
            'font': {'color': '#cbd5e1', 'size': 10},
            'bgcolor': 'rgba(10, 14, 26, 0.6)',
            'bordercolor': 'rgba(255, 255, 255, 0.08)',
            'borderwidth': 1
        },
        margin=dict(l=40, r=0, t=50, b=40)
    )
    fig.update_xaxes(
        gridcolor='rgba(255, 255, 255, 0.06)',
        zerolinecolor='rgba(255, 255, 255, 0.1)',
        tickfont={'color': '#94a3b8', 'size': 10},
        title_font={'color': '#cbd5e1', 'size': 11}
    )
    fig.update_yaxes(
        gridcolor='rgba(255, 255, 255, 0.06)',
        zerolinecolor='rgba(255, 255, 255, 0.1)',
        tickfont={'color': '#94a3b8', 'size': 10},
        title_font={'color': '#cbd5e1', 'size': 11}
    )


def color_for_pct(p):
    if p >= 90: return '#10B981'
    if p >= 75: return '#00D8C6'
    if p >= 70: return '#F59E0B'
    return '#EF4444'


# ══════════════════════════════════════════════════════════════
# AUTH PAGES
# ══════════════════════════════════════════════════════════════
def login_page():
    logo_path = os.path.join(os.path.dirname(__file__), 'vits_logo.png')
    logo_base64 = get_image_base64(logo_path)
    if logo_base64:
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 25px;">
            <img src="data:image/png;base64,{logo_base64}" width="100" style="filter: drop-shadow(0px 6px 15px rgba(0,216,198,0.25)); margin-bottom: 10px;"/>
            <h1 style="color: #00D8C6; font-family: 'Outfit', sans-serif; font-size: 2.4rem; margin-top: 10px; margin-bottom: 5px; text-shadow: 0 0 35px rgba(0, 216, 198, 0.3);">VITS Student Academic Dashboard</h1>
            <p style="color: #cbd5e1; font-family: 'Inter', sans-serif; font-size: 1.1rem; letter-spacing: 0.5px; font-weight: 500;">Vignan Institute of Technology and Science</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #00D8C6; font-family: 'Outfit', sans-serif; font-size: 2.4rem; margin-bottom: 5px; text-shadow: 0 0 35px rgba(0, 216, 198, 0.3);">🎓 VITS Student Academic Dashboard</h1>
            <p style="color: #94a3b8; font-family: 'Inter', sans-serif; font-size: 1.1rem; letter-spacing: 0.5px;">Vignan Institute of Technology and Science</p>
        </div>
        """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["👤 Student", "🛡️ Admin"])
        with tab1:
            with st.form("student_login"):
                st.info("**First-time login?** Use password: **`vits123`** — you'll set your DOB after login.")
                roll = st.text_input("Roll Number", placeholder="24891A0465")
                pwd  = st.text_input("Password (DOB: YYYY-MM-DD or vits123)", type="password")
                if st.form_submit_button("Sign In", use_container_width=True):
                    handle_student_login(roll.strip().upper(), pwd.strip())
        with tab2:
            with st.form("admin_login"):
                u = st.text_input("Admin Username")
                p = st.text_input("Admin Password", type="password")
                if st.form_submit_button("Sign In as Admin", use_container_width=True):
                    if u.strip() == 'admin' and verify_admin_pwd(p.strip()):
                        st.session_state.update({
                            'logged_in': True, 'role': 'admin',
                            'user_id': 'admin', 'user_name': 'Administrator',
                            'section': ''
                        })
                        st.rerun()
                    else:
                        st.error("Invalid credentials")


def handle_student_login(roll, pwd):
    conn = get_db_connection()
    st_row = conn.execute('SELECT roll_no,name,dob,section FROM students WHERE roll_no=?', (roll,)).fetchone()
    conn.close()
    if not st_row:
        st.error("Roll number not found.")
        return
    def _set():
        st.session_state.update({
            'logged_in': True, 'role': 'student',
            'user_id': st_row['roll_no'], 'user_name': st_row['name'],
            'section': st_row['section']
        })

    # Normalize date password input
    import datetime as dt_mod
    norm_pwd = pwd.strip().replace('/', '-').replace('\\', '-').replace('.', '-')
    for fmt in ('%Y-%m-%d', '%d-%m-%Y'):
        try:
            norm_pwd = dt_mod.datetime.strptime(norm_pwd, fmt).date().strftime('%Y-%m-%d')
            break
        except Exception:
            pass

    db_dob = st_row['dob']
    
    # First-time setup redirect if DB DOB is PENDING or default '2007-01-01'
    is_first_time = db_dob in ('PENDING', '2007-01-01')
    is_default_pwd = norm_pwd in ('vits123', '2007-01-01', '01-01-2007')

    if is_first_time and is_default_pwd:
        _set()
        st.session_state['needs_dob_setup'] = True
        st.rerun()
        return

    if norm_pwd == db_dob:
        _set()
        st.rerun()
        return
    st.error("Invalid date of birth.")


def setup_dob_page():
    st.markdown(f"## 🔐 Welcome, {st.session_state.user_name}")
    st.info("Please set your **Date of Birth** as your permanent password.")
    with st.form("setup_dob"):
        new_dob = st.date_input("Date of Birth", value=None,
            min_value=datetime.date(1985, 1, 1),
            max_value=datetime.date.today())
        if st.form_submit_button("Save & Continue", use_container_width=True):
            if not new_dob:
                st.error("Please select a date."); return
            dob_str = new_dob.strftime('%Y-%m-%d')
            # Accept any DOB chosen by the user
            conn = get_db_connection()
            conn.execute('UPDATE students SET dob=? WHERE roll_no=?',
                         (dob_str, st.session_state.user_id))
            conn.commit(); conn.close()
            st.session_state.pop('needs_dob_setup', None)
            st.success("Password set successfully!")
            st.rerun()


# ══════════════════════════════════════════════════════════════
# STUDENT DASHBOARD
# ══════════════════════════════════════════════════════════════
def student_dashboard():
    roll = st.session_state.user_id
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE roll_no=?', (roll,)).fetchone()
    cgpa = compute_cgpa(roll, conn)
    has_failed_sem = conn.execute(
        'SELECT COUNT(*) FROM sgpa_records WHERE roll_no=? AND failed=1', (roll,)
    ).fetchone()[0] > 0
    cgpa_display = "Pending" if has_failed_sem else (f"{cgpa:.2f}" if cgpa > 0 else "-")

    with st.sidebar:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(0,216,198,0.08) 0%, rgba(139,92,246,0.08) 100%);
                    border: 1px solid rgba(0,216,198,0.15); border-radius: 16px;
                    padding: 18px; margin-bottom: 20px; text-align: center;">
            <div style="font-size: 2.5rem; margin-bottom: 8px;">🎓</div>
            <h4 style="margin: 0; color: #ffffff; font-family: 'Outfit', sans-serif;">{student['name']}</h4>
            <p style="margin: 4px 0 0 0; font-size: 0.85rem; color: #00D8C6; font-family: 'JetBrains Mono', monospace; font-weight: 600;">{student['roll_no']}</p>
            <div style="display: flex; justify-content: space-around; margin-top: 15px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 10px;">
                <div><div style="font-size: 0.72rem; color: #94a3b8; text-transform: uppercase;">Section</div>
                     <div style="font-weight: 600; color: #ffffff; font-size: 0.85rem;">{student['section']}</div></div>
                <div><div style="font-size: 0.72rem; color: #94a3b8; text-transform: uppercase;">Branch</div>
                     <div style="font-weight: 600; color: #ffffff; font-size: 0.85rem;">{student['branch']}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.metric("CGPA", cgpa_display)

        sems_in_db = [r['semester'] for r in conn.execute(
            'SELECT DISTINCT semester FROM sgpa_records WHERE roll_no=?', (roll,)
        ).fetchall()]
        cgpa_note = ""
        if sems_in_db:
            try:
                sems_sorted = sorted(sems_in_db, key=lambda s: int(s.replace("Sem ", "").strip()))
            except Exception:
                sems_sorted = sorted(sems_in_db)
            cgpa_note = (f"{sems_sorted[0]} Results" if len(sems_sorted) == 1
                         else " & ".join(sems_sorted) + " Results")
        if cgpa_note:
            st.markdown(f"""<div style="text-align:center;margin-top:-12px;margin-bottom:12px;">
                <span style="background:rgba(0,216,198,0.08);color:#00D8C6;border:1px solid rgba(0,216,198,0.2);
                padding:4px 10px;border-radius:20px;font-size:0.72rem;font-weight:600;
                font-family:'Inter',sans-serif;letter-spacing:0.5px;display:inline-block;">💡 {cgpa_note}</span>
                </div>""", unsafe_allow_html=True)

        st.markdown("---")
        selected_sem = st.selectbox("Viewing Semester",
            [f"Sem {i}" for i in range(1, 9)], index=1)
        st.markdown("---")
        page = st.radio("Navigation", [
            "🏠 Home", "📅 Attendance", "📊 Marks", "🧮 SGPA Calculator",
            "📈 Analytics", "🗓️ Timetable"
        ])
        st.markdown("---")
        if st.button("📄 Download Report PDF", use_container_width=True):
            generate_student_pdf(student, selected_sem)
        if st.button("🚪 Logout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    sem = selected_sem
    att_rows = conn.execute(
        'SELECT subject,hours_attended,hours_conducted FROM attendance WHERE roll_no=? AND semester=?',
        (roll, sem)).fetchall()
    marks_rows = conn.execute(
        'SELECT subject,score,grade_point,exam_type FROM marks WHERE roll_no=? AND semester=?',
        (roll, sem)).fetchall()
    conn.close()

    if page == "🏠 Home":
        show_home_page(student, sem, att_rows, marks_rows, cgpa_display)
    elif page == "📅 Attendance":
        show_attendance_page(roll, sem, att_rows)
    elif page == "📊 Marks":
        show_marks_page(sem, marks_rows)
    elif page == "🧮 SGPA Calculator":
        show_sgpa_page(sem, marks_rows)
    elif page == "📈 Analytics":
        show_analytics_page(roll, sem)
    elif page == "🗓️ Timetable":
        show_timetable_page(student['section'])


# ── HOME / SUMMARY PAGE ───────────────────────────────────────
def show_home_page(student, sem, att_rows, marks_rows, cgpa_display):
    hour = dt.now().hour
    greeting = "Good Morning" if hour < 12 else "Good Afternoon" if hour < 17 else "Good Evening"

    total_c = sum((r['hours_conducted'] or 0) for r in att_rows)
    total_a = sum((r['hours_attended']  or 0) for r in att_rows)
    overall = round(total_a / total_c * 100, 1) if total_c else 0.0
    can_miss = can_miss_classes(total_a, total_c)
    need = classes_needed(total_a, total_c)

    # SGPA for this sem and average timetable classes
    conn = get_db_connection()
    sgpa_row = conn.execute(
        'SELECT sgpa, failed FROM sgpa_records WHERE roll_no=? AND semester=?',
        (student['roll_no'], sem)).fetchone()
    
    # Completed Credits & Backlogs calculation
    final_marks = conn.execute('''
        SELECT subject, score FROM marks
        WHERE roll_no=? AND exam_type LIKE '%Final Examinations'
    ''', (student['roll_no'],)).fetchall()

    sec = student['section']
    avg_classes = 7.0
    if sec:
        days_count = conn.execute('SELECT COUNT(DISTINCT day) FROM timetable WHERE section=?', (sec,)).fetchone()[0]
        total_periods = conn.execute('SELECT COUNT(*) FROM timetable WHERE section=?', (sec,)).fetchone()[0]
        if days_count > 0:
            avg_classes = total_periods / days_count
    conn.close()

    can_miss_days = round(can_miss / avg_classes, 1) if avg_classes > 0 else 0.0
    need_days = round(need / avg_classes, 1) if avg_classes > 0 else 0.0

    if sgpa_row and not sgpa_row['failed'] and sgpa_row['sgpa'] > 0:
        sgpa_text = f"{sgpa_row['sgpa']:.2f}"
    elif sgpa_row and sgpa_row['failed']:
        sgpa_text = "Pending"
    else:
        sgpa_text = "-"

    completed_credits = 0.0
    backlogs_count = 0
    for m in final_marks:
        sub = m['subject']
        score = m['score']
        grade, _ = score_to_grade(score)
        c_val = SUBJECT_CREDITS.get(sub, 3.0)
        if grade in ['F', 'Ab']:
            backlogs_count += 1
        else:
            completed_credits += c_val

    status = "✅ SAFE" if overall >= 75 else "⚠️ RISK" if overall >= 65 else "🚫 DEBARRED"

    # Build subject data before columns so it's accessible full-width below
    subj_data = []
    for r in att_rows:
        _c = r['hours_conducted'] or 0
        _a = r['hours_attended'] or 0
        _p = round(_a / _c * 100, 1) if _c else 0.0
        subj_data.append({'subject': r['subject'], 'conducted': _c,
                          'attended': _a, 'pct': _p,
                          'absent': _c - _a,
                          'can_miss': can_miss_classes(_a, _c),
                          'need': classes_needed(_a, _c)})

    # Set up column layout
    col_main, col_side = st.columns([2.2, 1.0])

    with col_main:
        st.markdown(f"# {greeting}, {student['name'].split(' ')[0]}! 👋")
        st.caption(f"Here's your {sem} academic summary · Roll: {student['roll_no']} · {student['section']}")
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

        # 4 KPI cards
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Attendance", f"{overall}%")
        k2.metric("SGPA", sgpa_text)
        k3.metric("Credits Earned", f"{completed_credits:.1f}")
        k4.metric("Backlogs", backlogs_count)

        # Status banner
        if total_c == 0:
            st.info("🔍 No attendance data yet for this semester. Visit the Attendance tab to sync.")
        elif overall >= 75:
            st.markdown(f"""<div class="status-banner" style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.3);">
                <h3 style="color:#10B981 !important;margin:0;">🟢 Safe Zone</h3>
                <p style="margin:8px 0 0 0;color:#cbd5e1 !important;">Current Attendance: <strong style="color:#fff;">{overall}%</strong>.
                You can miss <strong style="color:#10B981;">{can_miss}</strong> more classes (approx. <strong style="color:#10B981;">{can_miss_days}</strong> days) and stay above 75%.</p>
                </div>""", unsafe_allow_html=True)
        elif overall >= 65:
            st.markdown(f"""<div class="status-banner" style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.3);">
                <h3 style="color:#F59E0B !important;margin:0;">🟠 Risk Zone</h3>
                <p style="margin:8px 0 0 0;color:#cbd5e1 !important;">Current Attendance: <strong style="color:#fff;">{overall}%</strong>.
                Attend <strong style="color:#F59E0B;">{need}</strong> consecutive classes (approx. <strong style="color:#F59E0B;">{need_days}</strong> days) to reach 75%.</p>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="status-banner" style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.3);">
                <h3 style="color:#EF4444 !important;margin:0;">🔴 Debarred Zone</h3>
                <p style="margin:8px 0 0 0;color:#cbd5e1 !important;">Current Attendance: <strong style="color:#fff;">{overall}%</strong>.
                You need <strong style="color:#EF4444;">{need}</strong> classes (approx. <strong style="color:#EF4444;">{need_days}</strong> days) to recover to 75%.</p>
                </div>""", unsafe_allow_html=True)

        # Overall attendance skip predictor
        if total_c > 0:
            st.markdown("### 🔮 Overall Attendance Skip Predictor")
            st.caption(f"💡 One calendar day corresponds to an average of **{avg_classes:.1f}** classes scheduled for your section.")

            miss_days = st.slider("If I miss the next ___ days (overall)", 0, 15, 0, key=f"skip_days_home_{sem}")
            miss_classes = int(round(miss_days * avg_classes))
            if miss_days > 0:
                proj_overall = round(total_a / (total_c + miss_classes) * 100, 1)
                if proj_overall >= 75:
                    st.success(f"Projected Overall Attendance: **{proj_overall}%** (Safe Zone) ✅ (Missing {miss_days} days / {miss_classes} classes)")
                elif proj_overall >= 65:
                    st.warning(f"Projected Overall Attendance: **{proj_overall}%** (Condonation Zone) ⚠️ (Missing {miss_days} days / {miss_classes} classes)")
                else:
                    st.error(f"Projected Overall Attendance: **{proj_overall}%** (Debarred Zone) 🚫 (Missing {miss_days} days / {miss_classes} classes)")

    with col_side:
        # View schedule scheduler at the top
        today_day = dt.now().strftime('%a')
        days_list = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        default_idx = days_list.index(today_day) if today_day in days_list else 0
        
        selected_day = st.selectbox("📅 View Schedule Day", days_list, index=default_idx)
        
        conn = get_db_connection()
        day_classes = conn.execute(
            'SELECT period, subject FROM timetable WHERE section=? AND day=? ORDER BY period',
            (student['section'], selected_day)
        ).fetchall()
        conn.close()
        
        times_map = {
            1: "08:45 - 09:35",
            2: "09:35 - 10:25",
            3: "10:40 - 11:30",
            4: "11:30 - 12:20",
            5: "01:10 - 02:00",
            6: "02:00 - 02:45",
            7: "02:45 - 03:30"
        }
        
        if day_classes:
            st.markdown(f"### ⏰ {selected_day}'s Schedule")
            for idx, c in enumerate(day_classes):
                t_range = times_map.get(c['period'], "Class Period")
                border_color = "#00D8C6" if idx == 0 else "#8B5CF6" if idx == 1 else "rgba(255,255,255,0.15)"
                st.markdown(f"""
                <div style="background: rgba(20, 28, 48, 0.45); border: 1px solid rgba(255, 255, 255, 0.05); 
                            border-left: 3px solid {border_color}; border-radius: 8px; padding: 6px 12px; margin-bottom: 5px;
                            backdrop-filter: blur(10px); display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-size: 0.85rem; font-weight: 700; color: #fff; font-family: 'Outfit';">
                        {c['subject']}
                    </div>
                    <div style="font-size: 0.65rem; color: #94a3b8; font-family: 'JetBrains Mono'; font-weight: 500; text-align: right;">
                        P{c['period']} · {t_range}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ── Full-width Academic Summary — REDESIGNED ──────────────────────
    if subj_data:
        best  = max(subj_data, key=lambda x: x['pct'])
        worst = min(subj_data, key=lambda x: x['pct'])

        # ── Section header ─────────────────────────────────────────────
        st.markdown("""
        <div style="display:flex;align-items:center;gap:12px;margin:28px 0 18px 0;">
            <div style="width:4px;height:32px;background:linear-gradient(180deg,#00D8C6,#8B5CF6);border-radius:2px;"></div>
            <h2 style="margin:0;font-family:'Outfit',sans-serif;font-size:1.55rem;font-weight:800;
                        background:linear-gradient(90deg,#fff 0%,#94a3b8 100%);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                Academic Summary
            </h2>
        </div>
        """, unsafe_allow_html=True)

        # ── Hero Stats Row (4 cards) ───────────────────────────────────
        if overall >= 75:
            risk_color = "#10B981"; risk_icon = "✅"; risk_label = "SAFE ZONE"
            risk_detail = f"Can skip <strong style='color:#10B981'>{can_miss} hrs</strong> ≈ {can_miss_days} days"
        elif overall >= 65:
            risk_color = "#F59E0B"; risk_icon = "⚠️"; risk_label = "RISK ZONE"
            risk_detail = f"Attend <strong style='color:#F59E0B'>{need} more hrs</strong> ≈ {need_days} days"
        else:
            risk_color = "#EF4444"; risk_icon = "🚫"; risk_label = "DEBARRED"
            risk_detail = f"Need <strong style='color:#EF4444'>{need} hrs</strong> to recover"

        sgpa_display = sgpa_text if sgpa_text and sgpa_text != "-" else "N/A"
        sgpa_color = "#8B5CF6" if sgpa_display != "N/A" else "#475569"

        h1, h2, h3, h4 = st.columns(4)
        hero_css = """
            background: linear-gradient(135deg, rgba(20,28,48,0.9) 0%, rgba(12,18,36,0.95) 100%);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 16px;
            padding: 20px 18px;
            text-align: center;
            position: relative;
            overflow: hidden;
        """
        h1.markdown(f"""
        <div style="{hero_css} border-top: 3px solid #00D8C6;">
            <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.12em;font-family:'Inter';font-weight:600;">Overall Attendance</div>
            <div style="font-size:2.4rem;font-weight:900;color:#00D8C6;font-family:'Outfit';line-height:1.1;margin:6px 0 2px 0;">{overall}%</div>
            <div style="font-size:0.72rem;color:#94a3b8;">{total_a}/{total_c} hrs</div>
        </div>""", unsafe_allow_html=True)

        h2.markdown(f"""
        <div style="{hero_css} border-top: 3px solid {sgpa_color};">
            <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.12em;font-family:'Inter';font-weight:600;">Current SGPA</div>
            <div style="font-size:2.4rem;font-weight:900;color:{sgpa_color};font-family:'Outfit';line-height:1.1;margin:6px 0 2px 0;">{sgpa_display}</div>
            <div style="font-size:0.72rem;color:#94a3b8;">{completed_credits:.0f} credits earned</div>
        </div>""", unsafe_allow_html=True)

        h3.markdown(f"""
        <div style="{hero_css} border-top: 3px solid {risk_color};">
            <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.12em;font-family:'Inter';font-weight:600;">Status</div>
            <div style="font-size:1.4rem;font-weight:900;color:{risk_color};font-family:'Outfit';line-height:1.1;margin:6px 0 4px 0;">{risk_icon} {risk_label}</div>
            <div style="font-size:0.72rem;color:#94a3b8;">{risk_detail}</div>
        </div>""", unsafe_allow_html=True)

        h4.markdown(f"""
        <div style="{hero_css} border-top: 3px solid #F59E0B;">
            <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:0.12em;font-family:'Inter';font-weight:600;">Subjects</div>
            <div style="font-size:2.4rem;font-weight:900;color:#F59E0B;font-family:'Outfit';line-height:1.1;margin:6px 0 2px 0;">{len(subj_data)}</div>
            <div style="font-size:0.72rem;color:#94a3b8;">{backlogs_count} backlog(s)</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

        # ── Two-column layout: Donut + Subject Health Bars ─────────────
        left_col, right_col = st.columns([1, 1.6])

        with left_col:
            # Donut chart for overall attendance
            donut_color = "#10B981" if overall >= 75 else "#F59E0B" if overall >= 65 else "#EF4444"
            fig_donut = go.Figure(go.Pie(
                values=[overall, 100 - overall],
                hole=0.72,
                marker_colors=[donut_color, "rgba(255,255,255,0.04)"],
                textinfo="none",
                hoverinfo="skip",
                sort=False,
            ))
            fig_donut.add_annotation(
                text=f"<b>{overall}%</b>",
                x=0.5, y=0.55, showarrow=False,
                font=dict(size=30, color=donut_color, family="Outfit"),
                xanchor="center"
            )
            fig_donut.add_annotation(
                text="Attendance",
                x=0.5, y=0.38, showarrow=False,
                font=dict(size=13, color="#94a3b8", family="Inter"),
                xanchor="center"
            )
            fig_donut.update_layout(
                height=260,
                showlegend=False,
                margin=dict(t=10, b=10, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_donut, use_container_width=True)

            # Best vs Worst mini cards
            st.markdown(f"""
            <div style="background:rgba(16,185,129,0.07);border:1px solid rgba(16,185,129,0.2);
                        border-radius:12px;padding:12px 14px;margin-bottom:8px;">
                <div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;font-weight:600;">Best Subject 🏆</div>
                <div style="font-size:1.05rem;font-weight:800;color:#10B981;font-family:'Outfit';margin-top:3px;">{best['subject']}</div>
                <div style="font-size:0.8rem;color:#94a3b8;">{best['attended']}/{best['conducted']} hrs · <strong style='color:#10B981'>{best['pct']}%</strong></div>
            </div>
            <div style="background:rgba(239,68,68,0.07);border:1px solid rgba(239,68,68,0.2);
                        border-radius:12px;padding:12px 14px;">
                <div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;font-weight:600;">Needs Attention ⚠️</div>
                <div style="font-size:1.05rem;font-weight:800;color:#EF4444;font-family:'Outfit';margin-top:3px;">{worst['subject']}</div>
                <div style="font-size:0.8rem;color:#94a3b8;">{worst['attended']}/{worst['conducted']} hrs · <strong style='color:#EF4444'>{worst['pct']}%</strong></div>
            </div>
            """, unsafe_allow_html=True)

        with right_col:
            st.markdown("""
            <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;
                        letter-spacing:0.12em;font-weight:600;margin-bottom:12px;font-family:'Inter';">
                Subject Health
            </div>""", unsafe_allow_html=True)

            sorted_subjs = sorted(subj_data, key=lambda x: x['pct'])
            for s in sorted_subjs:
                pct = s['pct']
                bar_color = "#10B981" if pct >= 75 else "#F59E0B" if pct >= 65 else "#EF4444"
                status_icon = "✅" if pct >= 75 else "⚠️" if pct >= 65 else "🚫"
                absent_hrs = s['conducted'] - s['attended']
                # truncate long subject names
                subj_label = s['subject'][:16] + "…" if len(s['subject']) > 16 else s['subject']
                st.markdown(f"""
                <div style="margin-bottom:10px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">
                        <span style="font-size:0.8rem;font-weight:600;color:#e2e8f0;font-family:'Inter';">{subj_label}</span>
                        <span style="font-size:0.75rem;color:{bar_color};font-weight:700;font-family:'JetBrains Mono';">{status_icon} {pct}%</span>
                    </div>
                    <div style="background:rgba(255,255,255,0.06);border-radius:999px;height:7px;overflow:hidden;">
                        <div style="width:{min(pct,100)}%;height:100%;
                                    background:linear-gradient(90deg,{bar_color}aa,{bar_color});
                                    border-radius:999px;transition:width 0.4s ease;"></div>
                    </div>
                    <div style="font-size:0.65rem;color:#475569;margin-top:2px;">{s['attended']}/{s['conducted']} hrs · {absent_hrs} absent</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown("""<hr style="border:none;border-top:1px solid rgba(255,255,255,0.06);margin:8px 0 20px 0;">""", unsafe_allow_html=True)

        # ── Bar chart (kept below) ─────────────────────────────────────
        st.markdown("""
        <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;
                    letter-spacing:0.12em;font-weight:600;margin-bottom:8px;font-family:'Inter';">
            Subject Attendance Chart
        </div>""", unsafe_allow_html=True)
        df = pd.DataFrame(subj_data)
        fig = px.bar(df, x='subject', y='pct', color='pct',
                     color_continuous_scale=[[0, '#EF4444'], [0.65, '#F59E0B'], [0.75, '#00D8C6'], [1, '#00D8C6']],
                     range_color=[0, 100], labels={'pct': 'Attendance %', 'subject': 'Subject'})
        fig.add_hline(y=75, line_dash="dash", line_color="#10B981", annotation_text="75% target")
        fig.add_hline(y=65, line_dash="dash", line_color="#F59E0B", annotation_text="65% min")
        fig.update_layout(height=380, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                          margin=dict(t=10, b=10))
        fig.update_coloraxes(showscale=False)
        apply_premium_plotly_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

    # Grades table – full width
    st.markdown("### 📝 Exam & Assignment Grades")
    sem_final_marks = [r for r in marks_rows if r['exam_type'] == f"{sem} Final Examinations"]
    if sem_final_marks:
        grades_df = pd.DataFrame([{
            'Subject': r['subject'],
            'Exam Type': r['exam_type'].replace(f"{sem} ", ""),
            'Score': r['score'] if r['score'] is not None else 'Ab',
            'Grade': score_to_grade(r['score'])[0],
            'Credits': SUBJECT_CREDITS.get(r['subject'], 3.0)
        } for r in sem_final_marks])
        st_premium_table(grades_df)
    else:
        mid_marks = [r for r in marks_rows if 'Mid' in r['exam_type'] or 'Lab' in r['exam_type']]
        if mid_marks:
            grades_df = pd.DataFrame([{
                'Subject': r['subject'],
                'Exam': r['exam_type'].replace(f"{sem} ", ""),
                'Score': r['score'] if r['score'] is not None else 'Ab'
            } for r in mid_marks])
            st_premium_table(grades_df)
        else:
            st.info("🔍 No academic marks uploaded for this semester yet.")



def show_attendance_page(roll, sem, att_rows):
    st.markdown("## 📅 Attendance Overview")
    total_c = sum((r['hours_conducted'] or 0) for r in att_rows)
    total_a = sum((r['hours_attended']  or 0) for r in att_rows)
    overall = round(total_a / total_c * 100, 1) if total_c else 0.0

    conn = get_db_connection()
    student = conn.execute('SELECT section FROM students WHERE roll_no=?', (roll,)).fetchone()
    sec = student['section'] if student else 'ECE_B'
    avg_classes = 7.0
    if sec:
        days_count = conn.execute('SELECT COUNT(DISTINCT day) FROM timetable WHERE section=?', (sec,)).fetchone()[0]
        total_periods = conn.execute('SELECT COUNT(*) FROM timetable WHERE section=?', (sec,)).fetchone()[0]
        if days_count > 0:
            avg_classes = total_periods / days_count
    conn.close()

    can_miss = can_miss_classes(total_a, total_c)
    need = classes_needed(total_a, total_c)
    can_miss_days = round(can_miss / avg_classes, 1) if avg_classes > 0 else 0.0
    need_days = round(need / avg_classes, 1) if avg_classes > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Hours Conducted", total_c)
    c2.metric("Hours Attended", total_a)
    c3.metric("Overall %", f"{overall}%")
    if overall >= 75:
        c4.metric("Can Miss", f"{can_miss} ({can_miss_days} d)")
    else:
        c4.metric("Attend Next", f"{need} ({need_days} d)")

    if total_c > 0:
        if overall >= 75:
            st.success(f"✅ Good standing — you can miss {can_miss} classes (approx. {can_miss_days} days) and stay above 75%")
        elif overall >= 65:
            st.warning(f"⚠️ Condonation required — attend {need} more classes (approx. {need_days} days) for 75%")
        else:
            st.error(f"🚫 Debarred — attend {need} classes (approx. {need_days} days) to recover")
    else:
        st.markdown("""<div style="background:rgba(239,68,68,0.04);border:1px dashed rgba(239,68,68,0.25);
            border-radius:12px;padding:16px;text-align:center;color:#ef4444;font-size:0.95rem;
            font-weight:500;margin:10px 0;font-family:'Inter',sans-serif;">
            🔍 No attendance data found for this semester.</div>""", unsafe_allow_html=True)

    if st.button("🔄 Fetch Live Attendance from Portal"):
        with st.spinner("Scraping portal... 30-60s"):
            ok, msg = harvester.scrape_portal(section=st.session_state.section, semester=sem)
            st.success(msg) if ok else st.error(msg)
            if ok: st.rerun()

    if not att_rows:
        st.info("No attendance data yet. Click 'Fetch Live' above to sync from portal.")
        return

    # Overall attendance skip predictor (new feature)
    if total_c > 0:
        st.markdown("### 🔮 Overall Attendance Skip Predictor")
        st.caption(f"💡 One calendar day corresponds to an average of **{avg_classes:.1f}** classes scheduled for your section.")

        miss_days = st.slider("If I miss the next ___ days (overall)", 0, 15, 0, key=f"skip_days_att_{sem}")
        miss_classes = int(round(miss_days * avg_classes))
        if miss_days > 0:
            proj_overall = round(total_a / (total_c + miss_classes) * 100, 1)
            if proj_overall >= 75:
                st.success(f"Projected Overall Attendance: **{proj_overall}%** (Safe Zone) ✅ (Missing {miss_days} days / {miss_classes} classes)")
            elif proj_overall >= 65:
                st.warning(f"Projected Overall Attendance: **{proj_overall}%** (Condonation Zone) ⚠️ (Missing {miss_days} days / {miss_classes} classes)")
            else:
                st.error(f"Projected Overall Attendance: **{proj_overall}%** (Debarred Zone) 🚫 (Missing {miss_days} days / {miss_classes} classes)")

    df = pd.DataFrame([{
        'Subject': r['subject'], 'Conducted': r['hours_conducted'] or 0,
        'Attended': r['hours_attended'] or 0,
        'Percentage': round((r['hours_attended'] or 0)/(r['hours_conducted'] or 1)*100, 1),
    } for r in att_rows])
    df['Status'] = df['Percentage'].apply(
        lambda p: 'Safe (≥75%)' if p >= 75 else 'Below 75%')

    fig = px.bar(df, x='Subject', y='Percentage', color='Percentage',
                 color_continuous_scale=[[0, '#EF4444'], [0.65, '#F59E0B'], [0.75, '#00D8C6'], [1, '#00D8C6']],
                 range_color=[0, 100])
    fig.add_hline(y=75, line_dash="dash", line_color="green", annotation_text="75% target")
    fig.add_hline(y=65, line_dash="dash", line_color="orange", annotation_text="65% min")
    fig.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 📊 Subject-wise Details + Intelligence")
    for idx, row in df.iterrows():
        cm = can_miss_classes(row['Attended'], row['Conducted'])
        nd = classes_needed(row['Attended'], row['Conducted'])
        intel = f"Can miss {cm} classes" if row['Percentage'] >= 75 else f"Attend {nd} more for 75%"
        with st.expander(f"**{row['Subject']}** — {row['Percentage']}% · {intel}"):
            c1, c2, c3 = st.columns(3)
            c1.write(f"**Conducted:** {row['Conducted']}")
            c2.write(f"**Attended:** {row['Attended']}")
            c3.write(f"**Absent:** {row['Conducted'] - row['Attended']}")
            if row['Subject'] != 'CRT':
                st.markdown("**🔮 Attendance Predictor**")
                pc1, pc2 = st.columns(2)
                fa = pc1.number_input("If I attend ___ classes", 0, 100, 5,
                                      key=f"att_{sem}_{row['Subject']}")
                ft = pc2.number_input("Out of next ___ classes", 0, 100, 5,
                                      key=f"tot_{sem}_{row['Subject']}")
                if ft > 0:
                    np_ = (row['Attended'] + fa) / (row['Conducted'] + ft) * 100
                    color = color_for_pct(np_)
                    st.markdown(f"""
                        <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); 
                                    padding: 8px 12px; border-radius: 8px; margin-top: 5px;">
                            <span style="color: #94a3b8; font-size: 0.85rem;">Projected Attendance: </span>
                            <strong style="color: {color}; font-size: 1.05rem; font-family: 'JetBrains Mono';">{np_:.1f}%</strong>
                        </div>
                    """, unsafe_allow_html=True)


def show_marks_page(sem, marks_rows):
    st.markdown("## 📊 Academic Results")
    by_exam = {}
    if marks_rows:
        for r in marks_rows:
            is_final = "Final" in r['exam_type']
            if is_final:
                grade, _ = score_to_grade(r['score'])
                gp_val = r['grade_point'] or 0
            else:
                grade, gp_val = '-', '-'
            by_exam.setdefault(r['exam_type'], []).append({
                'Subject': r['subject'],
                'Score': r['score'] if r['score'] is not None else 'Ab',
                'Grade': grade, 'GP': gp_val,
                'Credits': SUBJECT_CREDITS.get(r['subject'], 0)
            })

    trend_data = []
    for et in ['Mid 1', 'Mid 2', f"{sem} Final Examinations"]:
        for r in by_exam.get(et, []):
            if isinstance(r['Score'], (int, float)):
                trend_data.append({'Exam': et, 'Subject': r['Subject'], 'Score': r['Score']})
    if trend_data:
        st.markdown("### 📈 Marks Progression (Mid 1 → Mid 2 → Finals)")
        fig = px.line(pd.DataFrame(trend_data), x='Exam', y='Score', color='Subject', markers=True, render_mode='svg')
        fig.update_traces(line_shape='spline', line=dict(width=3))
        apply_premium_plotly_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

    for et in [f"{sem} Final Examinations", 'Mid 1', 'Mid 2', 'Lab Internals']:
        st.markdown(f"### {et}")
        rows = by_exam.get(et, [])
        if not rows:
            st.markdown("""<div style="background:rgba(239,68,68,0.04);border:1px dashed rgba(239,68,68,0.25);
                border-radius:12px;padding:16px;text-align:center;color:#ef4444;font-size:0.95rem;
                font-weight:500;margin:10px 0;font-family:'Inter',sans-serif;">
                🔍 No data found for this examination.</div>""", unsafe_allow_html=True)
        else:
            st_premium_table(pd.DataFrame(rows))
            if et == f"{sem} Final Examinations":
                conn = get_db_connection()
                sgpa_row = conn.execute(
                    'SELECT sgpa, failed FROM sgpa_records WHERE roll_no=? AND semester=?',
                    (st.session_state.user_id, sem)).fetchone()
                conn.close()
                if sgpa_row:
                    sgpa_text = "Pending" if sgpa_row['failed'] else (
                        f"{sgpa_row['sgpa']:.2f}" if sgpa_row['sgpa'] > 0 else "-")
                    st.markdown(f"""<div style="background:rgba(0,216,198,0.05);border:1px solid rgba(0,216,198,0.15);
                        border-radius:12px;padding:10px 20px;margin-top:12px;margin-bottom:20px;display:inline-block;">
                        <span style="color:#94a3b8;font-size:0.85rem;font-weight:500;font-family:'Inter';text-transform:uppercase;letter-spacing:0.5px;">Semester SGPA:</span>
                        <span style="color:#00D8C6;font-size:1.1rem;font-weight:700;font-family:'Outfit';margin-left:8px;">{sgpa_text}</span>
                        </div>""", unsafe_allow_html=True)


def show_sgpa_page(sem, marks_rows):
    st.markdown("## 🧮 SGPA Calculator")
    st.caption("Adjust sliders to project your SGPA based on possible scores.")
    conn = get_db_connection()
    st_row = conn.execute('SELECT section FROM students WHERE roll_no=?',
                          (st.session_state.user_id,)).fetchone()
    section = st_row['section'] if st_row else 'ECE_B'
    if sem == 'Sem 1':
        subjects = SEM1_SUBJECTS
    else:
        subjects = [r['subject_code'] for r in conn.execute(
            'SELECT DISTINCT subject_code FROM subjects WHERE section=? AND semester=?',
            (section, sem)).fetchall()]
        if not subjects:
            subjects = SECTION_SUBJECTS.get(section, [])
    conn.close()
    if not subjects:
        st.info("No subjects found for this semester to calculate SGPA.")
        return

    actual_scores = {r['subject']: r['score'] for r in marks_rows
                     if r['exam_type'] == f"{sem} Final Examinations"}
    has_actuals = len(actual_scores) > 0
    if not has_actuals:
        st.info("ℹ️ No actual final marks yet — sliders start at 0. Drag to simulate.")

    projected = {}
    for sub in subjects:
        cr = SUBJECT_CREDITS.get(sub, 0)
        if cr == 0:
            continue
        # Default to 0 for projections if no actual score exists
        default_val = int(actual_scores[sub]) if sub in actual_scores and actual_scores[sub] is not None else 0
        projected[sub] = st.slider(f"{sub} ({cr} cr)", 0, 100, default_val, key=f"sgpa_{sem}_{sub}")

    total_cr, weighted = 0.0, 0.0
    for subj, score in projected.items():
        cr = SUBJECT_CREDITS.get(subj, 0)
        _, gp = score_to_grade(score)
        weighted += gp * cr; total_cr += cr
    sgpa = round(weighted / total_cr, 2) if total_cr else 0.0

    conn = get_db_connection()
    other = conn.execute(
        'SELECT sgpa FROM sgpa_records WHERE roll_no=? AND semester!=? AND failed=0 AND sgpa>0',
        (st.session_state.user_id, sem)).fetchall()
    conn.close()
    all_sgpas = [r['sgpa'] for r in other] + [sgpa]
    projected_cgpa = round(sum(all_sgpas) / len(all_sgpas), 2) if all_sgpas else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Projected SGPA", sgpa)
    c2.metric("Projected CGPA", f"{projected_cgpa:.2f}" if projected_cgpa > 0 else "-")
    c3.metric("Total Credits", total_cr)

    with st.expander("📚 JNTUH Grade Scale"):
        st_premium_table(pd.DataFrame([
            {'Range': '90-100', 'Grade': 'O', 'GP': 10},
            {'Range': '80-89', 'Grade': 'A+', 'GP': 9},
            {'Range': '70-79', 'Grade': 'A', 'GP': 8},
            {'Range': '60-69', 'Grade': 'B+', 'GP': 7},
            {'Range': '50-59', 'Grade': 'B', 'GP': 6},
            {'Range': '40-49', 'Grade': 'C', 'GP': 5},
            {'Range': '<40', 'Grade': 'F', 'GP': 0},
        ]))


def show_analytics_page(roll, sem):
    st.markdown("## 📈 Attendance Analytics")
    days = st.radio("Time Range", [7, 30, 180], index=1, horizontal=True,
                    format_func=lambda d: f"Last {d} Days" if d < 180 else "Full Semester")

    if sem == 'Sem 1':
        st.info("ℹ️ Attendance trends are only available for scraped semesters (Sem 2+). Sem 1 shows results only.")
        return

    import datetime as dt_mod
    cutoff_date = (dt_mod.date.today() - dt_mod.timedelta(days=days)).strftime('%Y-%m-%d')
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT snapshot_date, subject_code, percentage, running_attended, running_conducted
        FROM attendance_history
        WHERE roll_no=? AND snapshot_date >= ?
        ORDER BY snapshot_date ASC
    ''', (roll, cutoff_date)).fetchall()
    conn.close()

    if not rows:
        st.info(f"No historical attendance data yet for {sem}. Trigger 'Fetch Live' on Attendance tab.")
        return

    df = pd.DataFrame([dict(r) for r in rows])

    st.markdown("### 📈 Attendance Trend Over Time")
    fig = px.line(df, x='snapshot_date', y='percentage', color='subject_code', markers=True, render_mode='svg')
    fig.update_traces(line_shape='spline', line=dict(width=3))
    fig.add_hline(y=75, line_dash="dash", line_color="#00D8C6")
    fig.add_hline(y=65, line_dash="dash", line_color="#F59E0B")
    apply_premium_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 🔥 Absenteeism Heatmap")
    pivot = df.pivot_table(index='subject_code', columns='snapshot_date',
                            values='percentage', aggfunc='last')
    fig2 = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns.astype(str), y=pivot.index,
        colorscale=[[0, '#1E293B'], [0.5, '#EF4444'], [0.75, '#F59E0B'], [1, '#00D8C6']],
        zmin=0, zmax=100, xgap=4, ygap=4, colorbar={'title': '%'}))
    apply_premium_plotly_theme(fig2)
    st.plotly_chart(fig2, use_container_width=True)

    # Attendance forecast (NEW — feature #12)
    st.markdown("### 🔮 Attendance Forecast")
    latest = df.sort_values('snapshot_date').groupby('subject_code').last().reset_index()
    fc_rows = []
    for _, r in latest.iterrows():
        cur = r['percentage']
        a = r['running_attended']; c = r['running_conducted']
        # Project if attends all future (assume 5/week, 4 weeks)
        future = 20
        proj = round((a + future) / (c + future) * 100, 1) if c else cur
        fc_rows.append({'Subject': r['subject_code'], 'Current %': cur,
                        'If attend all (1 month)': f"{proj}%"})
    st_premium_table(pd.DataFrame(fc_rows))

    conn = get_db_connection()
    cfg = get_config_map(conn)
    conn.close()
    default_total = int(cfg.get('total_semester_hours', '600'))

    st.markdown("### 🎯 Condonation Planner")
    c1, c2, c3 = st.columns(3)
    a = c1.number_input("Hours Attended", min_value=0, value=0)
    c = c2.number_input("Hours Conducted", min_value=0, value=0)
    t = c3.number_input("Total Semester Hours", min_value=0, value=default_total)
    if c > 0:
        pct = a / c * 100; remaining = t - c
        if a + remaining < 0.65 * t:
            st.error("🚫 Debarred — 65% mathematically impossible.")
        elif a + remaining < 0.75 * t:
            h65 = math.ceil((0.65 * c - a) / 0.35) if a < 0.65*c else 0
            st.error(f"⚠️ 75% unattainable. Need {max(0, h65)} classes for 65%.")
        elif pct >= 75:
            st.success(f"✅ Good standing at {pct:.1f}%.")
        elif pct >= 65:
            h75 = math.ceil((0.75 * c - a) / 0.25)
            st.warning(f"⚠️ Attend {h75} consecutive classes for 75%.")
        else:
            h65 = math.ceil((0.65 * c - a) / 0.35)
            h75 = math.ceil((0.75 * c - a) / 0.25)
            st.error(f"🚫 Below 65%. Need {h65} for 65%, {h75} for 75%.")


def show_timetable_page(section):
    st.markdown(f"## 🗓️ Weekly Timetable — {section}")
    conn = get_db_connection()
    tt = conn.execute('SELECT day, period, subject FROM timetable WHERE section=? ORDER BY day, period',
                      (section,)).fetchall()
    conn.close()
    if not tt:
        st.info("No timetable uploaded yet. Ask admin to upload via CSV.")
        return

    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    grid = {d: {} for d in days}
    for row in tt:
        grid[row['day']][row['period']] = row['subject']

    # Grid view with actual times
    table_data = []
    for d in days:
        rowd = {'Day': d}
        rowd['08:45-09:35 (P1)'] = grid[d].get(1, '-')
        rowd['09:35-10:25 (P2)'] = grid[d].get(2, '-')
        rowd['10:25-10:40'] = '☕ BREAK'
        rowd['10:40-11:30 (P3)'] = grid[d].get(3, '-')
        rowd['11:30-12:20 (P4)'] = grid[d].get(4, '-')
        rowd['12:20-01:10'] = '🍱 LUNCH'
        rowd['01:10-02:00 (P5)'] = grid[d].get(5, '-')
        rowd['02:00-02:45 (P6)'] = grid[d].get(6, '-')
        rowd['02:45-03:30 (P7)'] = grid[d].get(7, '-')
        table_data.append(rowd)

    st.markdown("### 📊 Timetable Grid")
    st_premium_table(pd.DataFrame(table_data))

    # Daily timeline styled like "Upcoming Events" scheduler in the reference image
    st.markdown("### 📅 Daily Schedule (Upcoming Events)")

    times = {
        1: "08:45 - 09:35",
        2: "09:35 - 10:25",
        3: "10:40 - 11:30",
        4: "11:30 - 12:20",
        5: "01:10 - 02:00",
        6: "02:00 - 02:45",
        7: "02:45 - 03:30"
    }

    active_tab = st.tabs(days)
    for i, d in enumerate(days):
        with active_tab[i]:
            sched = []
            p = 1
            while p <= 7:
                subj = grid[d].get(p, '-')
                start_p = p
                while p < 7 and grid[d].get(p+1, '-') == subj and subj != '-':
                    p += 1
                end_p = p

                time_range = times[start_p] if start_p == end_p else f"{times[start_p].split(' - ')[0]} - {times[end_p].split(' - ')[1]}"

                sched.append({
                    'periods': f"Period {start_p}" if start_p == end_p else f"Periods {start_p} - {end_p}",
                    'time': time_range,
                    'subject': subj
                })

                if p == 2:
                    sched.append({'periods': '-', 'time': '10:25 - 10:40', 'subject': '☕ BREAK'})
                elif p == 4:
                    sched.append({'periods': '-', 'time': '12:20 - 01:10', 'subject': '🍱 LUNCH BREAK'})

                p += 1

            for item in sched:
                if item['subject'] in ('-', '☕ BREAK', '🍱 LUNCH BREAK'):
                    bg = 'rgba(255,255,255,0.02)'
                    border = 'rgba(255,255,255,0.05)'
                    color = '#94a3b8'
                    icon = '⏳' if item['subject'] == '-' else '☕' if 'BREAK' in item['subject'] else '🍱'
                else:
                    colors = [
                        ('rgba(0,216,198,0.12)', '#00D8C6', '📘'),
                        ('rgba(139,92,246,0.12)', '#8B5CF6', '📙'),
                        ('rgba(245,158,11,0.12)', '#F59E0B', '📗'),
                        ('rgba(239,68,68,0.12)', '#EF4444', '📕'),
                        ('rgba(16,185,129,0.12)', '#10B981', '📓'),
                        ('rgba(236,72,153,0.12)', '#EC4899', '📔')
                    ]
                    idx = sum(ord(c) for c in item['subject']) % len(colors)
                    bg, color, icon = colors[idx]
                    border = color.replace(')', ',0.35)')

                st.markdown(f"""
                <div style="background: {bg}; border: 1px solid {border}; border-radius: 16px; 
                            padding: 14px 20px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between;
                            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);">
                    <div style="display: flex; align-items: center;">
                        <span style="font-size: 1.6rem; margin-right: 18px;">{icon}</span>
                        <div>
                            <div style="font-weight: 700; color: #fff; font-family: 'Outfit'; font-size: 1.1rem; letter-spacing: 0.3px;">{item['subject']}</div>
                            <div style="color: #94a3b8; font-size: 0.85rem; font-family: 'Inter'; margin-top: 2px;">
                                {item['periods'] + '  ·  ' if item['periods'] != '-' else ''}{item['time']}
                            </div>
                        </div>
                    </div>
                    <div style="color: {color}; font-weight: 700; font-family: 'JetBrains Mono'; font-size: 0.85rem; 
                                border: 1px solid {color}33; padding: 4px 10px; border-radius: 20px; text-transform: uppercase;">
                        { 'Free' if item['subject'] == '-' else 'Class' if 'BREAK' not in item['subject'] else 'Rest' }
                    </div>
                </div>
                """, unsafe_allow_html=True)


def generate_student_pdf(student, sem="Sem 2"):
    roll = student['roll_no']
    conn = get_db_connection()
    att = conn.execute(
        'SELECT subject,hours_attended,hours_conducted FROM attendance WHERE roll_no=? AND semester=?',
        (roll, sem)).fetchall()
    marks = conn.execute(
        'SELECT subject,score,grade_point,exam_type FROM marks WHERE roll_no=? AND semester=?',
        (roll, sem)).fetchall()
    cgpa = compute_cgpa(roll, conn)
    conn.close()
    marks_by_type = {}
    for r in marks:
        grade, _ = score_to_grade(r['score'])
        marks_by_type.setdefault(r['exam_type'], []).append({
            'subject': r['subject'], 'score': r['score'],
            'grade_point': r['grade_point'], 'grade': grade})
    finals = marks_by_type.get(f"{sem} Final Examinations", [])
    sgpa = compute_sgpa([{'subject': r['subject'], 'grade_point': r['grade_point']}
                         for r in finals if r['score'] is not None])
    buf = pdf_generator.generate_report_pdf(dict(student), att, marks_by_type, sgpa, cgpa, semester=sem)
    st.download_button("⬇️ Click to Download Report",
        data=buf.getvalue(), file_name=f"Report_{roll}_{sem.replace(' ', '')}.pdf",
        mime="application/pdf")


# ══════════════════════════════════════════════════════════════
# ADMIN DASHBOARD
# ══════════════════════════════════════════════════════════════
def admin_dashboard():
    with st.sidebar:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(239,68,68,0.08) 0%, rgba(139,92,246,0.08) 100%);
                    border: 1px solid rgba(239,68,68,0.15); border-radius: 16px;
                    padding: 18px; margin-bottom: 20px; text-align: center;">
            <div style="font-size: 2.5rem; margin-bottom: 8px;">🛡️</div>
            <h4 style="margin: 0; color: #ffffff; font-family: 'Outfit', sans-serif;">Portal Admin</h4>
            <p style="margin: 4px 0 0 0; font-size: 0.85rem; color: #EF4444; font-family: 'JetBrains Mono', monospace; font-weight: 600;">System Console</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        page = st.radio("Navigation", [
            "🏠 Dashboard", "👥 Students", "📝 Marks Editor",
            "📤 CSV Upload", "🔄 Scraper",
            "📈 Analytics", "🗓️ Timetable", "💾 Backup", "⚙️ Settings"
        ])
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    pages = {
        "🏠 Dashboard": admin_overview,
        "👥 Students": admin_students,
        "📝 Marks Editor": admin_marks,
        "📤 CSV Upload": admin_csv_upload,
        "🔄 Scraper": admin_scraper,
        "📈 Analytics": admin_analytics,
        "🗓️ Timetable": admin_timetable,
        "💾 Backup": admin_backup_page,
        "⚙️ Settings": admin_settings,
    }
    pages[page]()


def admin_overview():
    st.markdown("# 🏠 Admin Dashboard")
    conn = get_db_connection()
    cfg = get_config_map(conn)
    total = conn.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    sem = cfg.get('active_semester', 'Sem 2')
    overall_avg = conn.execute('''
        SELECT ROUND(AVG(pct),1) FROM (
            SELECT SUM(hours_attended)*100.0/NULLIF(SUM(hours_conducted),0) pct
            FROM attendance WHERE semester=? GROUP BY roll_no) AS subquery
    ''', (sem,)).fetchone()[0] or 0
    below75 = conn.execute('''
        SELECT COUNT(DISTINCT roll_no) FROM (
            SELECT roll_no, SUM(hours_attended)*100.0/NULLIF(SUM(hours_conducted),0) pct
            FROM attendance WHERE semester=? GROUP BY roll_no 
            HAVING SUM(hours_attended)*100.0/NULLIF(SUM(hours_conducted),0) < 75) AS subquery
    ''', (sem,)).fetchone()[0]
    conn.close()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Students", total)
    c2.metric("Sections", len(CLASSES))
    c3.metric("Avg Attendance", f"{overall_avg}%")
    c4.metric("Below 75%", below75, delta_color="inverse")
    st.markdown(f"### Active Semester: **{sem}**")
    st.markdown(f"**Last sync:** {cfg.get('last_scraped_at', 'Never')}")


def admin_students():
    st.markdown("# 👥 Student Directory")
    conn = get_db_connection()
    c1, c2 = st.columns([2, 1])
    section_filter = c1.selectbox("Filter by Section", ['All'] + CLASSES)
    search = c2.text_input("Search (roll/name)")

    sql = 'SELECT * FROM students WHERE 1=1'; params = []
    if section_filter != 'All':
        sql += ' AND section=?'; params.append(section_filter)
    if search:
        sql += ' AND (UPPER(roll_no) LIKE ? OR UPPER(name) LIKE ?)'
        s = f'%{search.upper()}%'; params.extend([s, s])
    sql += ' ORDER BY section, roll_no LIMIT 200'
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        df['DOB Set'] = df['dob'].apply(lambda d: '⚠️ Pending' if d in ('PENDING', '2007-01-01') else '✅ Set')
        df['DOB'] = pd.to_datetime(df['dob'], errors='coerce').dt.date
        df['Reset'] = False
        display_df = df[['roll_no', 'name', 'section', 'branch', 'DOB Set', 'DOB', 'Reset']].rename(columns={
            'roll_no': 'Roll Number', 'name': 'Name',
            'section': 'Section', 'branch': 'Branch', 'DOB Set': 'Status', 'DOB': 'DOB', 'Reset': 'Reset'
        })

        st.data_editor(
            display_df,
            column_config={
                "Roll Number": st.column_config.TextColumn("Roll Number", disabled=True),
                "Name": st.column_config.TextColumn("Name", disabled=True),
                "Section": st.column_config.TextColumn("Section", disabled=True),
                "Branch": st.column_config.TextColumn("Branch", disabled=True),
                "Status": st.column_config.TextColumn("Status", disabled=True),
                "DOB": st.column_config.DateColumn(
                    "DOB",
                    format="YYYY-MM-DD",
                    min_value=datetime.date(1985, 1, 1),
                    max_value=datetime.date.today(),
                    required=False
                ),
                "Reset": st.column_config.CheckboxColumn(
                    "Reset Password",
                    help="Check this box to reset the student password back to default.",
                    default=False
                )
            },
            key="student_editor",
            use_container_width=True,
            hide_index=True
        )
        st.caption(f"Showing {len(rows)} students (max 200)")

        if st.button("💾 Save Directory Changes", use_container_width=True):
            if "student_editor" in st.session_state:
                edits = st.session_state["student_editor"].get("edited_rows", {})
                if edits:
                    conn = get_db_connection()
                    updated = False
                    for row_idx, changes in edits.items():
                        roll_no = display_df.iloc[int(row_idx)]["Roll Number"]
                        if "Reset" in changes and changes["Reset"] is True:
                            conn.execute('UPDATE students SET dob=? WHERE roll_no=?', ('PENDING', roll_no))
                            updated = True
                        elif "DOB" in changes:
                            new_dob = changes["DOB"]
                            if new_dob is None:
                                dob_val = 'PENDING'
                            else:
                                dob_val = new_dob.strftime('%Y-%m-%d') if hasattr(new_dob, "strftime") else str(new_dob)
                            conn.execute('UPDATE students SET dob=? WHERE roll_no=?', (dob_val, roll_no))
                            updated = True
                    if updated:
                        conn.commit()
                    conn.close()
                    if updated:
                        st.success("Student records updated successfully!")
                        st.rerun()
                    else:
                        st.info("No modifications detected.")
                else:
                    st.info("No changes to save.")
    else:
        st.info("No students found.")

    with st.expander("➕ Add / Edit Student"):
        with st.form("edit_student"):
            c1, c2 = st.columns(2)
            roll = c1.text_input("Roll Number").upper()
            name = c2.text_input("Full Name")
            sec  = c1.selectbox("Section", CLASSES)
            dob  = c2.date_input("DOB", value=None,
                min_value=datetime.date(1985, 1, 1),
                max_value=datetime.date.today())
            if st.form_submit_button("💾 Save Student"):
                if roll and name:
                    branch = sec.split('_')[0] if '_' in sec else sec
                    conn = get_db_connection()
                    if dob:
                        dob_str = dob.strftime('%Y-%m-%d')
                        conn.execute('''
                            INSERT INTO students(roll_no,name,dob,section,branch,department,semester)
                            VALUES(?,?,?,?,?,?,2)
                            ON CONFLICT(roll_no) DO UPDATE SET
                                name=excluded.name, dob=excluded.dob, section=excluded.section, branch=excluded.branch
                        ''', (roll, name, dob_str, sec, branch, branch))
                    else:
                        conn.execute('''
                            INSERT INTO students(roll_no,name,dob,section,branch,department,semester)
                            VALUES(?,?,?,?,?,?,2)
                            ON CONFLICT(roll_no) DO UPDATE SET
                                name=excluded.name, section=excluded.section, branch=excluded.branch
                        ''', (roll, name, 'PENDING', sec, branch, branch))
                    conn.commit(); conn.close()
                    st.success(f"Student {roll} saved."); st.rerun()


def admin_marks():
    st.markdown("# 📝 Marks Editor")
    c1, c2, c3 = st.columns(3)
    roll = c1.text_input("Roll Number").upper()
    sem  = c2.selectbox("Semester", [f"Sem {i}" for i in range(1, 9)], index=1)
    exam = c3.selectbox("Exam Type", ['Mid 1', 'Mid 2', 'Lab Internals', f"{sem} Final Examinations"])

    if roll:
        conn = get_db_connection()
        subjects = [r['subject'] for r in conn.execute(
            'SELECT DISTINCT subject FROM attendance WHERE roll_no=? AND semester=?', (roll, sem)
        ).fetchall()]
        if not subjects:
            st_row = conn.execute('SELECT section FROM students WHERE roll_no=?', (roll,)).fetchone()
            if st_row:
                subjects = SECTION_SUBJECTS.get(st_row['section'], [])

        # Pre-fill existing scores (Bug 7 fix: allows 0, supports -1 to skip/unchanged)
        existing = {r['subject']: r['score'] for r in conn.execute(
            'SELECT subject, score FROM marks WHERE roll_no=? AND semester=? AND exam_type=?',
            (roll, sem, exam)).fetchall()}

        if subjects:
            with st.form("marks_form"):
                scores = {}
                cols = st.columns(2)
                for i, subj in enumerate(subjects):
                    prefill = int(existing[subj]) if subj in existing and existing[subj] is not None else 0
                    scores[subj] = cols[i % 2].number_input(
                        subj, min_value=-1, max_value=100, value=prefill,
                        key=f"score_{sem}_{exam}_{subj}",
                        help="Set -1 to skip / leave unchanged")
                if st.form_submit_button("💾 Save Marks"):
                    count = 0
                    for subj, score in scores.items():
                        if score < 0:   # -1 = skip
                            continue
                        _, gp = score_to_grade(score)
                        conn.execute('''
                            INSERT INTO marks(roll_no,subject,semester,exam_type,score,grade_point)
                            VALUES(?,?,?,?,?,?)
                            ON CONFLICT(roll_no,subject,semester,exam_type) DO UPDATE SET
                                score=excluded.score, grade_point=excluded.grade_point
                        ''', (roll, subj, sem, exam, float(score), gp))
                        count += 1
                    conn.commit()
                    st.success(f"Saved {count} mark entries.")
        else:
            st.warning("No subjects found. Add the student first via Students page.")
        conn.close()


def resolve_csv_columns(df):
    """
    Returns (roll_col, name_col, subject_cols) dynamically resolved from df.columns.
    """
    import re
    # 1. Resolve roll_col
    roll_synonyms = {'rollno', 'roll_no', 'rollnumber', 'roll number', 'htno', 'h.tno', 'h.tno.', 'h.t no.', 'hallticket', 'hall ticket', 'rollno.', 'hallno', 'hallno.'}
    roll_col = None
    for c in df.columns:
        norm = str(c).strip().lower().replace(' ', '').replace('_', '').replace('.', '')
        if norm in roll_synonyms:
            roll_col = c
            break
            
    if not roll_col:
        # Check values to find a column with roll-like strings (e.g., 24891A0465)
        roll_pattern = re.compile(r'^\d{2}891A\w{4}$', re.IGNORECASE)
        for c in df.columns:
            # Check first 5 non-null values
            sample = df[c].dropna().head(5).astype(str).str.strip().tolist()
            if sample and any(roll_pattern.match(val) for val in sample):
                roll_col = c
                break
                
    # 2. Resolve name_col
    name_synonyms = {'name', 'studentname', 'student name', 'fullname', 'full name', 'student_name'}
    name_col = None
    for c in df.columns:
        norm = str(c).strip().lower().replace(' ', '').replace('_', '').replace('.', '')
        if norm in name_synonyms:
            name_col = c
            break
            
    # 3. Resolve subject columns
    ignored_cols = {
        'sno', 's.no', 's.no.', 'total', 'percentage', 'percentage(%)', 'pct', 
        'sgpa', 'gpa', 'failed', 'result', 'status', 'section', 'class', 'sno.'
    }
    subject_cols = []
    for c in df.columns:
        if c == roll_col or c == name_col:
            continue
        norm = str(c).strip().lower().replace(' ', '').replace('_', '').replace('.', '').replace('(', '').replace(')', '').replace('%', '')
        if norm in ignored_cols:
            continue
        subject_cols.append(c)
        
    return roll_col, name_col, subject_cols


def admin_csv_upload():
    st.markdown("# 📤 CSV & Results Upload Center")
    
    # Switch between Internal Marks and JNTU Results
    upload_type = st.tabs(["📤 Internal Marks CSV", "📥 JNTU Results CSV"])
    
    # ──────────────────────────────────────────────────────────
    # TAB 1: Internal Marks CSV
    # ──────────────────────────────────────────────────────────
    with upload_type[0]:
        st.markdown("### Import Student Marks")
        st.caption("CSV format: `roll_no, SUBJECT1, SUBJECT2, ...` (Ensure first column contains Roll Numbers)")
        
        c1, c2 = st.columns(2)
        sem = c1.selectbox("Semester", [f"Sem {i}" for i in range(1, 9)], index=1, key="marks_sem")
        exam = c2.selectbox("Exam Type", ['Mid 1', 'Mid 2', 'Lab Internals', f"{sem} Final Examinations"], key="marks_exam")
        
        # Upload mode selector: Bulk vs Per-Class
        mode = st.radio("Upload Mode", ["Bulk Upload (All Sections)", "Per-Class Upload (Specific Section)"], horizontal=True, key="marks_mode")
        
        section = None
        if "Per-Class Upload" in mode:
            section = st.selectbox("Select Class/Section", CLASSES, key="marks_section")
            
        uploaded = st.file_uploader("Upload Marks CSV", type=['csv'], key="marks_uploader")
        if uploaded:
            df = pd.read_csv(uploaded)
            df.columns = [c.strip() for c in df.columns]
            roll_col, name_col, subject_cols = resolve_csv_columns(df)
            
            if not roll_col:
                st.error("⚠️ Could not dynamically identify a Roll Number/Hall Ticket column in this CSV. Please ensure a column contains roll numbers like '24891A0465'.")
            elif not subject_cols:
                st.error("⚠️ No subject columns detected. Ensure columns representing subjects are present (not snooze, totals, or percentages).")
            else:
                st.info(f"✅ Dynamically detected columns: Roll Number = **`{roll_col}`**, Name = **`{name_col or 'None'}`**, Subjects = {subject_cols}")
                st_premium_table(df.head())
                
                if st.button("📤 Import Marks Now", use_container_width=True, key="btn_import_marks"):
                    try:
                        sem_num = int(sem.replace("Sem", "").strip())
                    except Exception:
                        sem_num = 2
                        
                    conn = get_db_connection()
                    count = 0
                    with st.spinner("Importing marks..."):
                        for _, row in df.iterrows():
                            roll = str(row.get(roll_col, '')).strip().upper()
                            if not roll:
                                continue
                            
                            # Validate / Register student if Per-Class mode
                            if section:
                                # Verify if student exists
                                row_st = conn.execute('SELECT name FROM students WHERE roll_no=?', (roll,)).fetchone()
                                branch = decode_roll_branch(roll) or 'ECE'
                                student_name = str(row.get(name_col, f"Student {roll}")).strip() if name_col else f"Student {roll}"
                                if not row_st:
                                    conn.execute('''
                                        INSERT INTO students(roll_no, name, dob, semester, branch, department, section)
                                        VALUES(?, ?, 'PENDING', ?, ?, ?, ?)
                                    ''', (roll, student_name, sem_num, branch, branch, section))
                                else:
                                    conn.execute('UPDATE students SET section=? WHERE roll_no=?', (section, roll))
                                    if name_col and student_name:
                                        conn.execute('UPDATE students SET name=? WHERE roll_no=?', (student_name, roll))
                            
                            for col in subject_cols:
                                val = pd.to_numeric(row[col], errors='coerce')
                                if pd.isna(val):
                                    continue
                                score = float(val)
                                _, gp = score_to_grade(score)
                                conn.execute('''
                                    INSERT INTO marks(roll_no,subject,semester,exam_type,score,grade_point)
                                    VALUES(?,?,?,?,?,?)
                                    ON CONFLICT(roll_no,subject,semester,exam_type) DO UPDATE SET
                                        score=excluded.score, grade_point=excluded.grade_point
                                ''', (roll, col.strip(), sem, exam, score, gp))
                                count += 1
                        conn.commit()
                    conn.close()
                    st.success(f"✅ Imported {count} mark entries successfully.")
                
    # ──────────────────────────────────────────────────────────
    # TAB 2: JNTU Results CSV
    # ──────────────────────────────────────────────────────────
    with upload_type[1]:
        st.markdown("### Import JNTU Semester Results")
        st.caption("Upload the JNTUH results format: `Hall no, Name, SUB1 [Total,GP], SUB2 [Total,GP], ..., SGPA`")
        
        conn = get_db_connection()
        cfg = get_config_map(conn)
        conn.close()
        active_sem = cfg.get('active_semester', 'Sem 2')
        
        c1, c2 = st.columns(2)
        try:
            active_idx = [f"Sem {i}" for i in range(1, 9)].index(active_sem)
        except ValueError:
            active_idx = 1
        semester = c1.selectbox("Semester", [f"Sem {i}" for i in range(1, 9)], index=active_idx, key="res_sem")
        exam_type = c2.selectbox("Exam Type", ['Mid 1', 'Mid 2', 'Lab Internals', 'Final Examinations'], index=3, key="res_exam")
        
        # Upload mode selector for Results: Bulk vs Per-Class
        res_mode = st.radio("Upload Mode", ["Bulk Upload (Auto Section)", "Per-Class Upload (Specific Section)"], horizontal=True, key="res_mode")
        
        res_section = None
        if "Per-Class Upload" in res_mode:
            res_section = st.selectbox("Select Class/Section", CLASSES, key="res_section")
            
        uploaded_res = st.file_uploader("Upload Results CSV", type=['csv'], key='results_csv')
        
        if uploaded_res and st.button("📥 Import Results Now", use_container_width=True, key="btn_import_results"):
            try:
                try:
                    sem_num = int(semester.replace("Sem", "").strip())
                except Exception:
                    sem_num = 2
                content = uploaded_res.read().decode('utf-8')
                parsed = parse_sem1_results_csv(content)
                conn = get_db_connection()
                marks_count = sgpa_count = 0
                
                # Determine exam type label for database marks table
                if exam_type == 'Final Examinations':
                    db_exam_type = f"{semester} Final Examinations"
                else:
                    db_exam_type = exam_type
                    
                with st.spinner(f"Importing {len(parsed)} JNTU records..."):
                    for record in parsed:
                        roll = record['roll_no']
                        branch = decode_roll_branch(roll) or 'ECE'
                        
                        if res_section:
                            # User selected a specific section for this CSV
                            section = res_section
                        else:
                            st_row = conn.execute('SELECT section FROM students WHERE roll_no=?', (roll,)).fetchone()
                            section = st_row['section'] if st_row else f"{branch}_A"
                            
                        conn.execute('''
                            INSERT INTO students(roll_no,name,dob,semester,branch,department,section)
                            VALUES(?,?,?,?,?,?,?)
                            ON CONFLICT(roll_no) DO UPDATE SET name=excluded.name, section=excluded.section
                        ''', (roll, record['name'], 'PENDING', sem_num, branch, branch, section))
                        
                        for subj, data in record['subjects'].items():
                            if data['total'] is not None:
                                conn.execute('''
                                    INSERT INTO marks(roll_no,subject,semester,exam_type,score,grade_point)
                                    VALUES(?,?,?,?,?,?)
                                    ON CONFLICT(roll_no,subject,semester,exam_type) DO UPDATE SET
                                        score=excluded.score, grade_point=excluded.grade_point
                                ''', (roll, subj, semester, db_exam_type, data['total'], data['gp']))
                                marks_count += 1
                                
                        if exam_type == 'Final Examinations':
                            conn.execute('''
                                INSERT INTO sgpa_records(roll_no,semester,sgpa,failed)
                                VALUES(?,?,?,?)
                                ON CONFLICT(roll_no,semester) DO UPDATE SET
                                    sgpa=excluded.sgpa, failed=excluded.failed
                            ''', (roll, semester, record['sgpa'], 1 if record['failed'] else 0))
                            sgpa_count += 1
                    conn.commit()
                conn.close()
                
                if exam_type == 'Final Examinations':
                    st.success(f"✅ Imported {sgpa_count} students (SGPA), {marks_count} mark entries for {semester}.")
                else:
                    st.success(f"✅ Imported {marks_count} mark entries ({exam_type}) for {semester}.")
            except Exception as e:
                st.error(f"Import error: {e}")


def admin_scraper():
    st.markdown("# 🔄 Portal Scraper")
    conn = get_db_connection()
    cfg = get_config_map(conn)
    logs = conn.execute('SELECT * FROM scrape_log ORDER BY scraped_at DESC LIMIT 50').fetchall()
    conn.close()

    st.markdown("### 📅 Active Semester")
    sem = st.selectbox(
        "Currently scraping:",
        [f"Sem {i}" for i in range(1, 9)],
        index=int(cfg.get('active_semester', 'Sem 2').replace('Sem ', '')) - 1
    )
    if st.button("Save Semester Config"):
        conn = get_db_connection()
        conn.execute('UPDATE config SET value=? WHERE key=?', (sem, 'active_semester'))
        conn.commit()
        conn.close()
        st.success("Semester updated.")

    st.markdown("### 📆 Date Range")
    c1, c2 = st.columns(2)
    sd = c1.date_input("From", value=dt.strptime(cfg.get('start_date', '2026-01-27'), '%Y-%m-%d'))
    ed = c2.date_input("To", value=dt.now())

    st.markdown("### 🎯 Scrape Single Section")
    section = st.selectbox("Section", CLASSES)
    if st.button("🔄 Scrape Section", use_container_width=True):
        with st.spinner(f"Scraping {section}... 30-60s"):
            ok, msg = harvester.scrape_portal(
                start_date=sd.strftime('%Y-%m-%d'),
                end_date=ed.strftime('%Y-%m-%d'),
                section=section, semester=sem
            )
            if ok: st.success(msg)
            else:  st.error(msg)

    st.markdown("### 🚀 Bulk Scrape ALL Sections")
    st.warning(f"Will scrape all {len(CLASSES)} sections. Takes 5-10 minutes.")
    if st.button("🚀 Scrape ALL Sections", use_container_width=True):
        progress = st.progress(0)
        status = st.empty()
        results = []
        # Bulk scrape sequentially without sharing single dynamic_conn to avoid SQLite locks
        for i, sec in enumerate(CLASSES):
            status.text(f"Scraping {sec} ({i+1}/{len(CLASSES)})...")
            ok, msg = harvester.scrape_portal(
                start_date=sd.strftime('%Y-%m-%d'),
                end_date=ed.strftime('%Y-%m-%d'),
                section=sec, semester=sem
            )
            results.append({'section': sec, 'ok': ok})
            progress.progress((i+1) / len(CLASSES))
        ok_count = sum(1 for r in results if r['ok'])
        st.success(f"Done! {ok_count}/{len(CLASSES)} sections synced.")

    st.markdown("### 📜 Sync History")
    if logs:
        log_df = pd.DataFrame([dict(r) for r in logs])
        display_df = log_df[['scraped_at', 'section', 'students', 'status', 'duration']].rename(columns={
            'scraped_at': 'Synced At',
            'section': 'Section',
            'students': 'Students Synced',
            'status': 'Status',
            'duration': 'Duration (s)'
        })
        st_premium_table(display_df)
    else:
        st.info("No sync history yet.")


def query_to_dataframe(conn, query, params=()):
    cur = conn.execute(query, params)
    rows = cur.fetchall()
    if not rows:
        return pd.DataFrame()
    data = []
    for r in rows:
        if hasattr(r, 'keys'):
            data.append({k: r[k] for k in r.keys()})
        elif isinstance(r, dict):
            data.append(r)
        else:
            data.append(dict(r))
    return pd.DataFrame(data)


def get_active_filter(prefix=""):
    col = f"{prefix}roll_no" if prefix else "roll_no"
    return f"{col} IN (SELECT roll_no FROM attendance GROUP BY roll_no HAVING (CAST(SUM(hours_attended) AS REAL) / SUM(hours_conducted) * 100) >= 20.0)"


def get_hour_where_clause(ignore_late, prefix=""):
    col = f"{prefix}hour" if prefix else "hour"
    return f"WHERE {col} >= 3" if ignore_late else ""


def get_hour_and_clause(ignore_late, prefix=""):
    col = f"{prefix}hour" if prefix else "hour"
    return f"AND {col} >= 3" if ignore_late else ""


def get_timetable_for_section(conn, section):
    rows = conn.execute("SELECT day, period, subject FROM timetable WHERE section=?", (section,)).fetchall()
    if rows:
        return [dict(r) for r in rows]
    
    # Generate mock timetable based on section subjects
    subjects = [r['subject'] for r in conn.execute("""
        SELECT DISTINCT subject as subject FROM attendance JOIN students USING(roll_no)
        WHERE section=?
    """, (section,)).fetchall() if r['subject']]
    
    if not subjects:
        subjects = ['NAS', 'DS', 'PYTHON', 'EC', 'ODEVC', 'CRT']
        
    import random
    random.seed(hash(section))
    timetable = []
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    for day in weekdays:
        for period in range(1, 7):
            sub = random.choice(subjects)
            timetable.append({'day': day, 'period': period, 'subject': sub})
    return timetable


@st.cache_data
def get_precise_bunks_v3(ignore_late=True):
    conn = get_db_connection()
    df_students = query_to_dataframe(conn, "SELECT roll_no, name, section FROM students")
    student_info = df_students.set_index('roll_no').to_dict('index')
    
    query = "SELECT date, section, hour, subject, roll_no FROM hour_wise_attendance"
    if ignore_late:
        query += " WHERE hour >= 3"
    df_absences = query_to_dataframe(conn, query)
    
    df_conducted = df_absences[['date', 'section', 'hour', 'subject']].drop_duplicates()
    
    active_filter_query = """
        SELECT roll_no 
        FROM attendance 
        GROUP BY roll_no 
        HAVING (CAST(SUM(hours_attended) AS REAL) / SUM(hours_conducted) * 100) >= 20.0
    """
    active_rolls = set(query_to_dataframe(conn, active_filter_query)['roll_no'])
    conn.close()
    
    cond_grouped = df_conducted.groupby(['date', 'section'])['hour'].apply(set).to_dict()
    subject_map = df_conducted.set_index(['date', 'section', 'hour'])['subject'].to_dict()
    
    df_abs_active = df_absences[df_absences['roll_no'].isin(active_rolls)]
    abs_grouped = df_abs_active.groupby(['date', 'roll_no'])['hour'].apply(set).to_dict()
    
    bunk_records = []
    for (date, roll), abs_hours in abs_grouped.items():
        stud = student_info.get(roll)
        if not stud:
            continue
        section = stud['section']
        
        cond_hours = cond_grouped.get((date, section), set())
        if not cond_hours:
            continue
            
        present_hours = cond_hours - abs_hours
        if not present_hours:
            continue
            
        min_present = min(present_hours)
        bunk_hours = [h for h in abs_hours if h > min_present]
        for h in bunk_hours:
            sub = subject_map.get((date, section, h), 'Unknown')
            bunk_records.append({
                'date': date,
                'roll_no': roll,
                'name': stud['name'],
                'section': section,
                'hour': h,
                'subject': sub
            })
            
    if bunk_records:
        return pd.DataFrame(bunk_records)
    else:
        return pd.DataFrame(columns=['date', 'roll_no', 'name', 'section', 'hour', 'subject'])


@st.cache_data
def get_cached_daily_bunk_trends():
    conn = get_db_connection()
    df = query_to_dataframe(conn, '''
        SELECT roll_no, subject_code, snapshot_date, running_attended, running_conducted
        FROM attendance_history
        WHERE roll_no IN (SELECT roll_no FROM attendance GROUP BY roll_no HAVING (CAST(SUM(hours_attended) AS REAL) / SUM(hours_conducted) * 100) >= 20.0)
        ORDER BY roll_no, subject_code, snapshot_date
    ''')
    conn.close()
    
    if df.empty:
        return pd.DataFrame()
        
    df['prev_cond'] = df.groupby(['roll_no', 'subject_code'])['running_conducted'].shift(1).fillna(0).astype(int)
    df['prev_att'] = df.groupby(['roll_no', 'subject_code'])['running_attended'].shift(1).fillna(0).astype(int)
    
    df['cond_today'] = df['running_conducted'] - df['prev_cond']
    df['att_today'] = df['running_attended'] - df['prev_att']
    
    df['bunks_today'] = (df['cond_today'] - df['att_today']).clip(lower=0)
    df_classes = df[df['cond_today'] > 0]
    
    daily = df_classes.groupby('snapshot_date')[['bunks_today', 'cond_today']].sum().reset_index()
    
    # Map dates to months and weekdays
    daily['date_obj'] = pd.to_datetime(daily['snapshot_date'])
    daily['weekday'] = daily['date_obj'].dt.day_name()
    daily['month'] = daily['date_obj'].dt.strftime('%b')
    return daily


def get_college_period_distribution(conn):
    active_f = get_active_filter("attendance.")
    bunks_data = conn.execute(f"""
        SELECT section, subject, SUM(hours_conducted - hours_attended) as total_bunks
        FROM attendance JOIN students USING(roll_no)
        WHERE {active_f}
        GROUP BY section, subject
    """).fetchall()
    
    period_bunks = {f"P{i}": 0.0 for i in range(1, 7)}
    period_weights = {1: 1.0, 2: 0.9, 3: 1.2, 4: 2.2, 5: 2.8, 6: 3.2}
    
    section_timetables = {}
    for r in bunks_data:
        sec = r['section']
        sub = r['subject']
        bunks = r['total_bunks']
        if bunks <= 0:
            continue
            
        if sec not in section_timetables:
            section_timetables[sec] = get_timetable_for_section(conn, sec)
            
        tt = section_timetables[sec]
        periods = [item['period'] for item in tt if item['subject'] == sub]
        if not periods:
            continue
            
        total_w = sum(period_weights[p] for p in periods)
        for p in periods:
            period_bunks[f"P{p}"] += bunks * (period_weights[p] / total_w)
            
    df_periods = pd.DataFrame({
        'Period': list(period_bunks.keys()),
        'Missed Classes': [round(v) for v in period_bunks.values()]
    })
    return df_periods


def admin_bunk_analysis():
    st.markdown("# 🚨 Bunk Intelligence Dashboard")
    conn = get_db_connection()
    
    # Custom premium CSS styling
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Inter:wght@300;400;500;600&display=swap');
        
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 25px;
        }
        
        .metric-card {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid #334155;
            border-radius: 14px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s, border-color 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            border-color: #8b5cf6;
        }
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            color: #f8fafc;
            margin-top: 5px;
            font-family: 'Outfit', sans-serif;
        }
        .metric-label {
            font-size: 0.8rem;
            text-transform: uppercase;
            color: #94a3b8;
            font-weight: 600;
            letter-spacing: 0.07em;
        }
        
        .custom-subtitle {
            color: #94a3b8;
            font-size: 1.1rem;
            margin-bottom: 30px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<p class='custom-subtitle'>College-wide bunk intelligence dashboard with section and student level drilldown capabilities.</p>", unsafe_allow_html=True)
    
    # Sidebar options for precise hourly vs cumulative
    st.sidebar.markdown("### ⚙️ Bunk Options")
    data_source = st.sidebar.radio(
        "Select Bunk Analytics Mode",
        ["📊 Real Scraped Hour-Wise (Precise)", "📈 Cumulative ERP Snapshots (Estimate)"]
    )
    
    ignore_late = False
    if data_source == "📊 Real Scraped Hour-Wise (Precise)":
        ignore_late = st.sidebar.checkbox(
            "Ignore First 2 Hours (Late Arrivals)",
            value=True,
            help="Filters out absences in Hour 1 and Hour 2 to focus on active period-bunking."
        )

    # SQL filters helper
    def get_hour_where_clause_local():
        return "WHERE hour >= 3" if ignore_late else ""

    students_count = 0
    hour_wise_count = 0
    try:
        students_count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    except Exception:
        pass
        
    try:
        conn.execute("SELECT 1 FROM hour_wise_attendance LIMIT 1")
        hour_wise_count = 1
    except Exception:
        pass
        
    if students_count == 0:
        st.warning("⚠️ **Database is empty.** Please seed the database first.")
        conn.close()
        return
        
    if data_source == "📊 Real Scraped Hour-Wise (Precise)" and hour_wise_count == 0:
        st.error("⚠️ **No hour-wise attendance records found in database.** Please run the hour-wise scraper first, or switch to Cumulative ERP mode in the sidebar.")
        conn.close()
        return

    df_precise_bunks = get_precise_bunks_v3(ignore_late)
    
    # Page Tabs
    tab_overall, tab_drilldown = st.tabs(["📊 College-Wide Bunk Analytics", "🔍 Class & Student Drilldown"])
    
    # ──────────────────────────────────────────────────────────
    # TAB 1: COLLEGE-WIDE BUNK ANALYTICS
    # ──────────────────────────────────────────────────────────
    with tab_overall:
        # 1. Fetch KPI Metrics based on selected data source
        if data_source == "📊 Real Scraped Hour-Wise (Precise)":
            where_c = get_hour_where_clause_local()
            active_f_stud = get_active_filter("students.")
            total_students = conn.execute(f"SELECT COUNT(*) FROM students WHERE {active_f_stud}").fetchone()[0]
            
            # Count of debarred students by section for adjusting class conducted hours
            debarred_by_sec = {}
            debarred_rows = conn.execute("""
                SELECT section, COUNT(*) as cnt FROM students 
                WHERE roll_no NOT IN (SELECT roll_no FROM attendance GROUP BY roll_no HAVING (CAST(SUM(hours_attended) AS REAL) / SUM(hours_conducted) * 100) >= 20.0)
                GROUP BY section
            """).fetchall()
            for r in debarred_rows:
                debarred_by_sec[r['section']] = r['cnt']

            # Sum total conducted hours from class-level aggregates in hourly report, excluding debarred students
            # Using MAX to make it PostgreSQL/SQLite compatible (group by date, section, hour, subject)
            hourly_classes = conn.execute(f"""
                SELECT date, section, hour, subject, 
                       MAX(total_present) as total_present, 
                       MAX(total_absent) as total_absent
                FROM hour_wise_attendance
                {where_c}
                GROUP BY date, section, hour, subject
            """).fetchall()
            
            total_cond_hours = 0
            for r in hourly_classes:
                deb_cnt = debarred_by_sec.get(r['section'], 0)
                total_cond_hours += max(0, r['total_present'] + r['total_absent'] - deb_cnt)
                
            total_bunks = len(df_precise_bunks)
            bunk_rate = (total_bunks / total_cond_hours * 100) if total_cond_hours > 0 else 0.0
            
            bunking_students = set(df_precise_bunks['roll_no']) if not df_precise_bunks.empty else set()
            zero_bunk_count = total_students - len(bunking_students)
            
            if not df_precise_bunks.empty:
                chronic_bunker_count = (df_precise_bunks.groupby('roll_no').size() > 15).sum()
            else:
                chronic_bunker_count = 0
            
        else: # Cumulative ERP Snapshots
            active_f_stud = get_active_filter("students.")
            total_students = conn.execute(f"SELECT COUNT(*) FROM students WHERE {active_f_stud}").fetchone()[0]
            
            active_f_att = get_active_filter("attendance.")
            total_cond_hours = conn.execute(f"SELECT SUM(hours_conducted) FROM attendance WHERE {active_f_att}").fetchone()[0] or 0
            total_att_hours = conn.execute(f"SELECT SUM(hours_attended) FROM attendance WHERE {active_f_att}").fetchone()[0] or 0
            total_bunks = total_cond_hours - total_att_hours
            bunk_rate = (total_bunks / total_cond_hours * 100) if total_cond_hours > 0 else 0.0
            
            zero_bunk_count = conn.execute(f"""
                SELECT COUNT(*) FROM (
                    SELECT roll_no, SUM(hours_conducted - hours_attended) as tb
                    FROM attendance 
                    WHERE {get_active_filter()}
                    GROUP BY roll_no HAVING tb = 0
                ) as subq
            """).fetchone()[0]
            
            chronic_bunker_count = conn.execute(f"""
                SELECT COUNT(*) FROM (
                    SELECT roll_no, SUM(hours_conducted - hours_attended) as tb
                    FROM attendance 
                    WHERE {get_active_filter()}
                    GROUP BY roll_no HAVING tb > 20
                ) as subq
            """).fetchone()[0]
            
        # Display Custom Premium KPI Cards
        st.markdown(f"""
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Total Students</div>
                <div class="metric-value">{total_students:,}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Classes Conducted (Student-Hours)</div>
                <div class="metric-value">{total_cond_hours:,}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Bunk Records</div>
                <div class="metric-value" style="color: #ef4444;">{total_bunks:,}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Overall Bunk Rate</div>
                <div class="metric-value" style="color: #f59e0b;">{bunk_rate:.2f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Students with Zero Bunks</div>
                <div class="metric-value" style="color: #10b981;">{zero_bunk_count}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Chronic Bunkers</div>
                <div class="metric-value" style="color: #f43f5e;">{chronic_bunker_count}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("## Overall Visual Analytics")
        
        # Load visual data based on datasource
        if data_source == "📊 Real Scraped Hour-Wise (Precise)":
            if not df_precise_bunks.empty:
                df_stud_bunks = df_precise_bunks.groupby('roll_no').size().reset_index(name='total_bunks')
            else:
                df_stud_bunks = pd.DataFrame(columns=['roll_no', 'total_bunks'])
            
            # Add active students with 0 bunks
            active_f_stud = get_active_filter("students.")
            active_rolls_df = query_to_dataframe(conn, f"SELECT roll_no FROM students WHERE {active_f_stud}")
            bunking_rolls = set(df_stud_bunks['roll_no']) if not df_stud_bunks.empty else set()
            zero_bunk_df = pd.DataFrame([
                {'roll_no': r.roll_no, 'total_bunks': 0}
                for r in active_rolls_df.itertuples()
                if r.roll_no not in bunking_rolls
            ])
            df_stud_bunks = pd.concat([df_stud_bunks, zero_bunk_df], ignore_index=True)
        else:
            active_f_att = get_active_filter("attendance.")
            df_stud_bunks = query_to_dataframe(conn, f"""
                SELECT roll_no, SUM(hours_conducted - hours_attended) as total_bunks
                FROM attendance 
                WHERE {active_f_att}
                GROUP BY roll_no
            """)
            
        # Bunk Distribution
        if not df_stud_bunks.empty:
            bunks = df_stud_bunks['total_bunks']
            bins = [0, 5, 10, 20, 99999]
            labels = ['0-5 bunks', '6-10 bunks', '11-20 bunks', '20+ bunks']
            df_stud_bunks['bin'] = pd.cut(bunks, bins=bins, labels=labels, include_lowest=True)
            bin_counts = df_stud_bunks['bin'].value_counts().reindex(labels).reset_index()
            bin_counts.columns = ['Bunk Range', 'Number of Students']
        else:
            bin_counts = pd.DataFrame(columns=['Bunk Range', 'Number of Students'])
        
        c_v1, c_v2 = st.columns(2)
        with c_v1:
            if not bin_counts.empty and bin_counts['Number of Students'].sum() > 0:
                fig_hist = px.bar(
                    bin_counts, x='Bunk Range', y='Number of Students',
                    color='Bunk Range',
                    color_discrete_sequence=['#10b981', '#f59e0b', '#f97316', '#ef4444'],
                    title="Bunk Distribution Histogram"
                )
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.info("No distribution data available.")
            
        with c_v2:
            if data_source == "📊 Real Scraped Hour-Wise (Precise)":
                if not df_precise_bunks.empty:
                    df_top = df_precise_bunks.groupby(['name', 'section']).size().reset_index(name='total_bunks')
                    df_top = df_top.sort_values(by='total_bunks', ascending=False).head(20)
                else:
                    df_top = pd.DataFrame(columns=['name', 'section', 'total_bunks'])
            else:
                active_f_att = get_active_filter("attendance.")
                top_bunkers = conn.execute(f"""
                    SELECT name, section, SUM(hours_conducted - hours_attended) as total_bunks
                    FROM attendance JOIN students USING(roll_no)
                    WHERE {active_f_att}
                    GROUP BY roll_no, name, section
                    ORDER BY total_bunks DESC
                    LIMIT 20
                """).fetchall()
                df_top = pd.DataFrame([dict(r) for r in top_bunkers])
                
            if not df_top.empty:
                df_top['Student'] = df_top['name'] + " (" + df_top['section'] + ")"
                fig_top = px.bar(
                    df_top, x='total_bunks', y='Student', orientation='h',
                    color='total_bunks',
                    color_continuous_scale=[[0, '#a78bfa'], [1, '#ef4444']],
                    title="Top 20 Bunkers (College Wide)"
                )
                fig_top.update_layout(yaxis={'categoryorder':'total ascending'}, height=450)
                st.plotly_chart(fig_top, use_container_width=True)
            else:
                st.info("No bunkers detected matching the filter.")
                
        st.markdown("---")
        
        c_v3, c_v4 = st.columns(2)
        with c_v3:
            if data_source == "📊 Real Scraped Hour-Wise (Precise)":
                active_f_stud = get_active_filter("students.")
                sec_active_counts = query_to_dataframe(conn, f"""
                    SELECT section, COUNT(*) as active_count 
                    FROM students WHERE {active_f_stud} GROUP BY section
                """)
                
                if not df_precise_bunks.empty:
                    sec_bunk_counts = df_precise_bunks.groupby('section').size().reset_index(name='total_bunks')
                    df_sec = pd.merge(sec_active_counts, sec_bunk_counts, on='section', how='left').fillna(0)
                    df_sec['avg_bunks'] = (df_sec['total_bunks'] / df_sec['active_count']).round(1)
                    df_sec = df_sec.sort_values(by='avg_bunks', ascending=False)
                else:
                    df_sec = sec_active_counts.copy()
                    df_sec['avg_bunks'] = 0.0
            else:
                active_f_stud = get_active_filter("students.")
                sec_ranking = conn.execute(f"""
                    SELECT section, 
                           ROUND(CAST(SUM(hours_conducted - hours_attended) AS REAL) / COUNT(DISTINCT roll_no), 1) as avg_bunks
                    FROM attendance JOIN students USING(roll_no)
                    WHERE {active_f_stud}
                    GROUP BY section
                    ORDER BY avg_bunks DESC
                """).fetchall()
                df_sec = pd.DataFrame([dict(r) for r in sec_ranking])
                
            if not df_sec.empty:
                fig_sec = px.bar(
                    df_sec, x='section', y='avg_bunks',
                    color='avg_bunks',
                    color_continuous_scale='OrRd',
                    title="Section-wise Bunk Ranking (Avg Bunks/Student)"
                )
                st.plotly_chart(fig_sec, use_container_width=True)
            else:
                st.info("No section rankings available.")
            
        with c_v4:
            if data_source == "📊 Real Scraped Hour-Wise (Precise)":
                if not df_precise_bunks.empty:
                    df_sub = df_precise_bunks.groupby('subject').size().reset_index(name='total_bunks')
                    df_sub = df_sub.sort_values(by='total_bunks', ascending=False)
                else:
                    df_sub = pd.DataFrame(columns=['subject', 'total_bunks'])
            else:
                active_f_att = get_active_filter("attendance.")
                sub_ranking = conn.execute(f"""
                    SELECT subject, SUM(hours_conducted - hours_attended) as total_bunks
                    FROM attendance
                    WHERE {active_f_att}
                    GROUP BY subject
                    ORDER BY total_bunks DESC
                """).fetchall()
                df_sub = pd.DataFrame([dict(r) for r in sub_ranking])
                
            if not df_sub.empty:
                fig_sub = px.bar(
                    df_sub, x='subject', y='total_bunks',
                    color='total_bunks',
                    color_continuous_scale='Viridis',
                    title="Most Bunked Subjects (Total Absences)"
                )
                st.plotly_chart(fig_sub, use_container_width=True)
            else:
                st.info("No subject rankings available.")
 
        st.markdown("---")
        
        # Load daily trends
        if data_source == "📊 Real Scraped Hour-Wise (Precise)":
            if not df_precise_bunks.empty:
                daily_trends = df_precise_bunks.groupby('date').size().reset_index(name='bunks_today')
                daily_trends = daily_trends.rename(columns={'date': 'snapshot_date'})
                daily_trends['date_obj'] = pd.to_datetime(daily_trends['snapshot_date'])
                daily_trends['weekday'] = daily_trends['date_obj'].dt.day_name()
                daily_trends['month'] = daily_trends['date_obj'].dt.strftime('%b')
            else:
                daily_trends = pd.DataFrame(columns=['snapshot_date', 'bunks_today'])
        else:
            daily_trends = get_cached_daily_bunk_trends()
            
        c_v5, c_v6 = st.columns(2)
        with c_v5:
            # Weekday Trend
            if not daily_trends.empty:
                weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                df_wd = daily_trends.groupby('weekday')['bunks_today'].sum().reindex(weekday_order).reset_index()
                fig_wd = px.bar(
                    df_wd, x='weekday', y='bunks_today',
                    color='bunks_today',
                    color_continuous_scale='Tealrose',
                    title="Day-wise Bunk Pattern (College Wide)"
                )
                st.plotly_chart(fig_wd, use_container_width=True)
            else:
                st.info("No weekday trend data available.")
            
        with c_v6:
            # Period Trend
            if data_source == "📊 Real Scraped Hour-Wise (Precise)":
                if not df_precise_bunks.empty:
                    df_periods = df_precise_bunks.groupby('hour').size().reset_index(name='Missed Classes')
                    df_periods['Period'] = 'P' + df_periods['hour'].astype(str)
                    df_periods = df_periods.sort_values(by='hour').drop(columns=['hour'])
                else:
                    df_periods = pd.DataFrame(columns=['Period', 'Missed Classes'])
            else:
                df_periods = get_college_period_distribution(conn)
                
            if not df_periods.empty:
                fig_periods = px.bar(
                    df_periods, x='Period', y='Missed Classes',
                    color='Missed Classes',
                    color_continuous_scale='Magenta',
                    title="Period-wise Bunk Pattern (College Wide)"
                )
                st.plotly_chart(fig_periods, use_container_width=True)
            else:
                st.info("No period trend data available.")
            
        st.markdown("---")
        
        c_v7, c_v8 = st.columns(2)
        with c_v7:
            # Monthly Trend
            if not daily_trends.empty and 'month' in daily_trends.columns:
                month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
                df_month = daily_trends.groupby('month')[['bunks_today']].sum().reindex(month_order).dropna().reset_index()
                if not df_month.empty:
                    fig_month = px.line(
                        df_month, x='month', y='bunks_today',
                        markers=True,
                        line_shape='spline',
                        title="Monthly Bunk Trend (Absences over Time)"
                    )
                    fig_month.update_traces(line_color='#8b5cf6', line_width=3)
                    st.plotly_chart(fig_month, use_container_width=True)
                else:
                    st.info("No monthly trend data available.")
            else:
                st.info("No monthly trend data available.")
            
        with c_v8:
            # Mass Bunk Detection
            st.markdown("### 🚨 Mass Bunk Event Detection")
            st.caption("Flagging dates where college-wide absences significantly exceed normal levels.")
            if not daily_trends.empty:
                mean_val = int(daily_trends['bunks_today'].mean())
                std_val = daily_trends['bunks_today'].std()
                threshold = mean_val + 1.8 * (std_val if not pd.isna(std_val) else 0)
                
                mass_days = daily_trends[daily_trends['bunks_today'] > threshold].copy()
                if not mass_days.empty:
                    mass_days['Expected Absences'] = mean_val
                    mass_days['Actual Absences'] = mass_days['bunks_today'].astype(int)
                    mass_days['Flag'] = "🚨 Mass Bunk Event"
                    mass_days_display = mass_days[['snapshot_date', 'Expected Absences', 'Actual Absences', 'Flag']].sort_values(by='snapshot_date', ascending=False)
                    st.dataframe(mass_days_display, use_container_width=True, height=220)
                else:
                    st.success("🎉 No institution-wide mass bunk events detected.")
            else:
                st.info("No daily tracking records available.")
 
    # ──────────────────────────────────────────────────────────
    # TAB 2: CLASS & STUDENT DRILLDOWN
    # ──────────────────────────────────────────────────────────
    with tab_drilldown:
        available_sections = [r['section'] for r in conn.execute("SELECT DISTINCT section FROM students ORDER BY section").fetchall()]
        
        st.markdown("### 🏢 Drilldown to Class / Section")
        selected_section = st.selectbox("Select Section", available_sections, index=available_sections.index("ECE_B") if "ECE_B" in available_sections else 0)
        
        st.markdown("---")
        
        # Calculate section-level details based on selected data source
        active_f_stud = get_active_filter("students.")
        active_f_att = get_active_filter("attendance.")
        
        if data_source == "📊 Real Scraped Hour-Wise (Precise)":
            where_pref = "AND hour_wise_attendance.hour >= 3" if ignore_late else ""
            sec_students_count = conn.execute(f"SELECT COUNT(*) FROM students WHERE section=? AND {active_f_stud}", (selected_section,)).fetchone()[0]
            
            # Count debarred students in section to exclude from conducted hours
            debarred_count = conn.execute(f"""
                SELECT COUNT(*) FROM students 
                WHERE section=? 
                  AND roll_no NOT IN (SELECT roll_no FROM attendance GROUP BY roll_no HAVING (CAST(SUM(hours_attended) AS REAL) / SUM(hours_conducted) * 100) >= 20.0)
            """, (selected_section,)).fetchone()[0]
            
            # Sum total conducted hours from class-level aggregates in hourly report
            # Using subquery with MAX to align with PG requirements
            sec_cond = conn.execute(f"""
                SELECT SUM(total_present + total_absent - {debarred_count}) FROM (
                    SELECT date, hour, subject, 
                           MAX(total_present) as total_present, 
                           MAX(total_absent) as total_absent
                    FROM hour_wise_attendance
                    WHERE section=? {where_pref}
                    GROUP BY date, hour, subject
                ) as subq
            """, (selected_section,)).fetchone()[0] or 0
            
            if not df_precise_bunks.empty:
                df_sec_bunks = df_precise_bunks[df_precise_bunks['section'] == selected_section]
                sec_bunks = len(df_sec_bunks)
                if not df_sec_bunks.empty:
                    highest_bunker_counts = df_sec_bunks.groupby('name').size().reset_index(name='total_bunks')
                    highest_bunker_row = highest_bunker_counts.sort_values(by='total_bunks', ascending=False).iloc[0]
                    highest_bunker_row = {'name': highest_bunker_row['name'], 'total_bunks': highest_bunker_row['total_bunks']}
                else:
                    highest_bunker_row = None
            else:
                sec_bunks = 0
                highest_bunker_row = None
                
            sec_avg_bunks = round(sec_bunks / sec_students_count, 1) if sec_students_count > 0 else 0.0
            
        else: # Cumulative ERP Mode
            sec_students_count = conn.execute(f"SELECT COUNT(*) FROM students WHERE section=? AND {active_f_stud}", (selected_section,)).fetchone()[0]
            sec_cond = conn.execute(f"""
                SELECT SUM(hours_conducted) FROM attendance JOIN students USING(roll_no) 
                WHERE section=? AND {active_f_att}
            """, (selected_section,)).fetchone()[0] or 0
            sec_att = conn.execute(f"""
                SELECT SUM(hours_attended) FROM attendance JOIN students USING(roll_no) 
                WHERE section=? AND {active_f_att}
            """, (selected_section,)).fetchone()[0] or 0
            sec_bunks = sec_cond - sec_att
            sec_avg_bunks = round(sec_bunks / sec_students_count, 1) if sec_students_count > 0 else 0.0
            
            highest_bunker_row = conn.execute(f"""
                SELECT name, SUM(hours_conducted - hours_attended) as total_bunks
                FROM attendance JOIN students USING(roll_no)
                WHERE section=? AND {active_f_att}
                GROUP BY roll_no, name
                ORDER BY total_bunks DESC
                LIMIT 1
            """, (selected_section,)).fetchone()
            
        highest_bunker_name = highest_bunker_row['name'] if highest_bunker_row else "N/A"
        highest_bunker_val = highest_bunker_row['total_bunks'] if highest_bunker_row else 0
        
        # Section KPI Cards
        st.markdown(f"""
        <div class="metric-grid">
            <div class="metric-card" style="background: linear-gradient(135deg, #1e293b 0%, #1e1b4b 100%);">
                <div class="metric-label">Section Students</div>
                <div class="metric-value">{sec_students_count}</div>
            </div>
            <div class="metric-card" style="background: linear-gradient(135deg, #1e293b 0%, #1e1b4b 100%);">
                <div class="metric-label">Total Section Bunks</div>
                <div class="metric-value" style="color: #f43f5e;">{sec_bunks}</div>
            </div>
            <div class="metric-card" style="background: linear-gradient(135deg, #1e293b 0%, #1e1b4b 100%);">
                <div class="metric-label">Avg Bunks / Student</div>
                <div class="metric-value" style="color: #f59e0b;">{sec_avg_bunks}</div>
            </div>
            <div class="metric-card" style="background: linear-gradient(135deg, #1e293b 0%, #1e1b4b 100%);">
                <div class="metric-label">Highest Bunker</div>
                <div class="metric-value" style="color: #ef4444; font-size: 1.3rem;">{highest_bunker_name} ({highest_bunker_val})</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Visual breakdown for selected section
        cs1, cs2 = st.columns(2)
        with cs1:
            st.markdown("#### 🏆 Top Bunkers in Section")
            if data_source == "📊 Real Scraped Hour-Wise (Precise)":
                if not df_precise_bunks.empty:
                    df_sec_bunks = df_precise_bunks[df_precise_bunks['section'] == selected_section]
                    if not df_sec_bunks.empty:
                        df_sec_top = df_sec_bunks.groupby('name').size().reset_index(name='total_bunks')
                        df_sec_top = df_sec_top.sort_values(by='total_bunks', ascending=False).head(10)
                    else:
                        df_sec_top = pd.DataFrame(columns=['name', 'total_bunks'])
                else:
                    df_sec_top = pd.DataFrame(columns=['name', 'total_bunks'])
            else:
                top_sec_bunkers = conn.execute(f"""
                    SELECT name, SUM(hours_conducted - hours_attended) as total_bunks
                    FROM attendance JOIN students USING(roll_no)
                    WHERE section=? AND {active_f_att}
                    GROUP BY roll_no, name
                    ORDER BY total_bunks DESC
                    LIMIT 10
                """, (selected_section,)).fetchall()
                df_sec_top = pd.DataFrame([dict(r) for r in top_sec_bunkers])
                
            if not df_sec_top.empty:
                st.dataframe(df_sec_top.rename(columns={'name':'Student', 'total_bunks':'Bunks'}), use_container_width=True)
                fig_sec_top = px.bar(
                    df_sec_top, x='total_bunks', y='name', orientation='h',
                    color='total_bunks',
                    color_continuous_scale='Reds',
                    labels={'total_bunks':'Bunk Count', 'name':'Student'}
                )
                fig_sec_top.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, height=300)
                st.plotly_chart(fig_sec_top, use_container_width=True)
            else:
                st.info("No absences recorded for this section.")
                
        with cs2:
            st.markdown("#### 📚 Subject-wise Bunk Analysis")
            if data_source == "📊 Real Scraped Hour-Wise (Precise)":
                if not df_precise_bunks.empty:
                    df_sec_bunks = df_precise_bunks[df_precise_bunks['section'] == selected_section]
                    if not df_sec_bunks.empty:
                        df_sec_sub = df_sec_bunks.groupby('subject').size().reset_index(name='total_bunks')
                        df_sec_sub = df_sec_sub.sort_values(by='total_bunks', ascending=False)
                    else:
                        df_sec_sub = pd.DataFrame(columns=['subject', 'total_bunks'])
                else:
                    df_sec_sub = pd.DataFrame(columns=['subject', 'total_bunks'])
            else:
                sec_sub_bunks = conn.execute(f"""
                    SELECT subject, SUM(hours_conducted - hours_attended) as total_bunks
                    FROM attendance JOIN students USING(roll_no)
                    WHERE section=? AND {active_f_att}
                    GROUP BY subject
                    ORDER BY total_bunks DESC
                """, (selected_section,)).fetchall()
                df_sec_sub = pd.DataFrame([dict(r) for r in sec_sub_bunks])
                
            if not df_sec_sub.empty:
                st.dataframe(df_sec_sub.rename(columns={'subject':'Subject', 'total_bunks':'Total Bunks'}), use_container_width=True)
                fig_sec_sub = px.bar(
                    df_sec_sub, x='subject', y='total_bunks',
                    color='total_bunks',
                    color_continuous_scale='Purples',
                    labels={'total_bunks':'Absences', 'subject':'Subject'}
                )
                fig_sec_sub.update_layout(showlegend=False, height=300)
                st.plotly_chart(fig_sec_sub, use_container_width=True)
            else:
                st.info("No subject-wise records found.")
                
        st.markdown("---")
        
        # Section Heatmap Filtered to Active Bunkers
        st.markdown("#### 🗺️ Student vs Subject Absences Heatmap (Active Bunkers Only)")
        st.caption("Grid visualization comparing relative subject-bunk profiles for selected students.")
        
        if data_source == "📊 Real Scraped Hour-Wise (Precise)":
            if not df_precise_bunks.empty:
                df_sec_bunks = df_precise_bunks[df_precise_bunks['section'] == selected_section]
                if not df_sec_bunks.empty:
                    df_heatmap_all = df_sec_bunks.groupby(['name', 'subject']).size().reset_index(name='Bunks')
                    df_heatmap_all = df_heatmap_all.rename(columns={'name': 'Student', 'subject': 'Subject'})
                else:
                    df_heatmap_all = pd.DataFrame(columns=['Student', 'Subject', 'Bunks'])
            else:
                df_heatmap_all = pd.DataFrame(columns=['Student', 'Subject', 'Bunks'])
        else:
            df_heatmap_all = query_to_dataframe(conn, f"""
                SELECT name as "Student", subject as "Subject", (hours_conducted - hours_attended) as "Bunks"
                FROM attendance JOIN students USING(roll_no)
                WHERE section=? AND {active_f_att}
            """, (selected_section,))
            
        if not df_heatmap_all.empty:
            # Normalize column casing for pandas operations
            df_heatmap_all.columns = [c.capitalize() if c.lower() in ('student', 'subject', 'bunks') else c for c in df_heatmap_all.columns]
            
            student_totals = df_heatmap_all.groupby('Student')['Bunks'].sum()
            max_bunks_val = int(student_totals.max()) if not student_totals.empty else 10
            
            min_bunks_filter = st.slider(
                "Filter Heatmap: Show only students with total bunks ≥",
                min_value=0,
                max_value=max(5, max_bunks_val),
                value=min(10, max(0, max_bunks_val // 3)),
                key="sec_heatmap_filter"
            )
            
            active_students = student_totals[student_totals >= min_bunks_filter].index.tolist()
            
            if active_students:
                df_heatmap_filtered = df_heatmap_all[df_heatmap_all['Student'].isin(active_students)]
                df_pivot = df_heatmap_filtered.pivot(index='Student', columns='Subject', values='Bunks').fillna(0)
                
                ordered_students = student_totals.loc[df_pivot.index].sort_values(ascending=True).index
                df_pivot = df_pivot.loc[ordered_students]
                
                fig_heatmap = go.Figure(data=go.Heatmap(
                    z=df_pivot.values,
                    x=df_pivot.columns,
                    y=df_pivot.index,
                    colorscale='YlOrRd',
                    colorbar=dict(title="Bunks")
                ))
                fig_heatmap.update_layout(height=max(250, len(active_students)*18 + 100), margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig_heatmap, use_container_width=True)
                st.caption(f"Showing {len(active_students)} active bunkers in the section (total bunks ≥ {min_bunks_filter}).")
            else:
                st.info(f"No students have total bunks ≥ {min_bunks_filter} in this section.")
        else:
            st.info("No data available to plot heatmap.")
            
        # Section Smart Insights Panel
        st.markdown("---")
        st.markdown("### 💡 Section Smart Insights")
        
        insights = []
        if not df_sec_sub.empty:
            most_bunked_sub = df_sec_sub.iloc[0]['subject']
            sub_bunk_share = round(df_sec_sub.iloc[0]['total_bunks'] / max(1, sec_bunks) * 100)
            insights.append(f"• **{most_bunked_sub}** is the most skipped subject, accounting for **{sub_bunk_share}%** of all absences in this section.")
            
        if highest_bunker_row and sec_bunks > 0:
            share = round(highest_bunker_val / sec_bunks * 100, 1)
            insights.append(f"• **{highest_bunker_name}** is the highest bunker and contributes **{share}%** of this section's total absences.")
            
        # Timetable day correlation
        tt_sec = get_timetable_for_section(conn, selected_section)
        day_map = {
            'Mon': 'Monday', 'Tue': 'Tuesday', 'Wed': 'Wednesday', 'Thu': 'Thursday', 'Fri': 'Friday',
            'Monday': 'Monday', 'Tuesday': 'Tuesday', 'Wednesday': 'Wednesday', 'Thursday': 'Thursday', 'Friday': 'Friday'
        }
        weekday_map = {'Monday':0, 'Tuesday':0, 'Wednesday':0, 'Thursday':0, 'Friday':0}
        for item in tt_sec:
            sub = item['subject']
            day = item['day']
            mapped_day = day_map.get(day)
            if mapped_day and not df_sec_sub.empty and 'subject' in df_sec_sub.columns:
                sub_rows = df_sec_sub[df_sec_sub['subject'] == sub]
                if not sub_rows.empty:
                    weekday_map[mapped_day] += int(sub_rows.iloc[0]['total_bunks'])
                
        max_day = max(weekday_map, key=weekday_map.get)
        if weekday_map[max_day] > 0:
            insights.append(f"• **{max_day}** has the highest correlated bunk weight based on subject scheduling distributions.")
            
        # Monthly progression
        sec_students_rolls = [r['roll_no'] for r in conn.execute(f"SELECT roll_no FROM students WHERE section=? AND {active_f_stud}", (selected_section,)).fetchall()]
        if sec_students_rolls:
            placeholders = ','.join('%s' if _DB_BACKEND == "pg" else '?' for _ in sec_students_rolls)
            if data_source == "📊 Real Scraped Hour-Wise (Precise)":
                if not df_precise_bunks.empty:
                    df_sec_bunks = df_precise_bunks[(df_precise_bunks['section'] == selected_section) & (df_precise_bunks['roll_no'].isin(sec_students_rolls))]
                    if not df_sec_bunks.empty:
                        df_sec_daily = df_sec_bunks.groupby('date').size().reset_index(name='total_bunks')
                        df_sec_daily = df_sec_daily.rename(columns={'date': 'snapshot_date'})
                        df_sec_daily = df_sec_daily.sort_values(by='snapshot_date')
                    else:
                        df_sec_daily = pd.DataFrame(columns=['snapshot_date', 'total_bunks'])
                else:
                    df_sec_daily = pd.DataFrame(columns=['snapshot_date', 'total_bunks'])
            else:
                sec_daily_rows = conn.execute(f"""
                    SELECT snapshot_date, SUM(running_conducted - running_attended) as total_bunks
                    FROM attendance_history
                    WHERE roll_no IN ({placeholders})
                    GROUP BY snapshot_date
                    ORDER BY snapshot_date
                """, sec_students_rolls).fetchall()
                df_sec_daily = pd.DataFrame([dict(r) for r in sec_daily_rows])
            if not df_sec_daily.empty:
                df_sec_daily['date'] = pd.to_datetime(df_sec_daily['snapshot_date'])
                df_sec_daily['month'] = df_sec_daily['date'].dt.strftime('%b')
                monthly_aggregates = df_sec_daily.groupby('month')['total_bunks'].max().reindex(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']).dropna()
                if len(monthly_aggregates) >= 2:
                    last_two = monthly_aggregates.tail(2)
                    pct_change = round((last_two.iloc[1] - last_two.iloc[0]) / max(1, last_two.iloc[0]) * 100, 1)
                    direction = "increased" if pct_change > 0 else "decreased"
                    insights.append(f"• Monthly cumulative absences **{direction} by {abs(pct_change)}%** compared to the previous month.")
                    
        for insight in insights:
            st.info(insight)
            
        st.markdown("---")
        
        # ──────────────────────────────────────────────────────────
        # STUDENT-LEVEL DRILLDOWN SECTION
        # ──────────────────────────────────────────────────────────
        st.markdown("### 👤 Student-Level Detailed Drilldown")
        sec_students = conn.execute("SELECT roll_no, name FROM students WHERE section=? ORDER BY roll_no", (selected_section,)).fetchall()
        
        if sec_students:
            selected_student_str = st.selectbox(
                "Select Student Profile",
                [f"{r['roll_no']} - {r['name']}" for r in sec_students]
            )
            selected_roll = selected_student_str.split(" - ")[0]
            
            # Fetch overall attendance to check if debarred
            student_overall_att = conn.execute("""
                SELECT SUM(hours_attended), SUM(hours_conducted)
                FROM attendance
                WHERE roll_no = ?
            """, (selected_roll,)).fetchone()
            total_att = student_overall_att[0] or 0
            total_cond = student_overall_att[1] or 1
            overall_pct = (total_att / total_cond * 100)
            is_debarred = overall_pct < 20.0
            
            if is_debarred:
                st.warning(f"⚠️ **Debarred / Long-Term Absent Profile**: This student's overall attendance is **{overall_pct:.2f}%**, which is below the 20% threshold. They did not attend standard classes and are excluded from active bunker rankings and metrics.")
            
            # Fetch student profile details based on data source
            if data_source == "📊 Real Scraped Hour-Wise (Precise)":
                where_pref = "AND hour_wise_attendance.hour >= 3" if ignore_late else ""
                if not df_precise_bunks.empty:
                    df_stud_bunks = df_precise_bunks[df_precise_bunks['roll_no'] == selected_roll]
                    st_total_bunks = len(df_stud_bunks)
                else:
                    st_total_bunks = 0
                
                # Count debarred students in section to exclude from conducted hours
                debarred_count = conn.execute(f"""
                    SELECT COUNT(*) FROM students 
                    WHERE section=? 
                      AND roll_no NOT IN (SELECT roll_no FROM attendance GROUP BY roll_no HAVING (CAST(SUM(hours_attended) AS REAL) / SUM(hours_conducted) * 100) >= 20.0)
                """, (selected_section,)).fetchone()[0]
                
                # Fetch section-level conducted hours for this section
                # Using MAX and group by for PostgreSQL compatibility
                sec_conducted_rows = conn.execute(f"""
                    SELECT MAX(total_present) as total_present, MAX(total_absent) as total_absent
                    FROM hour_wise_attendance
                    WHERE section=? {where_pref}
                    GROUP BY date, hour, subject
                """, (selected_section,)).fetchall()
                
                sec_conducted_total = sum(max(0, r['total_present'] + r['total_absent'] - debarred_count) for r in sec_conducted_rows)
                st_total_conducted = round(sec_conducted_total / max(1, sec_students_count))
                st_attendance_pct = overall_pct
                
                # Calculate Section Bunk Rank (only ranking active/non-debarred students)
                if not df_precise_bunks.empty:
                    df_sec_bunks = df_precise_bunks[df_precise_bunks['section'] == selected_section]
                    if not df_sec_bunks.empty:
                        sec_bunks_ranking_df = df_sec_bunks.groupby('roll_no').size().reset_index(name='total_bunks')
                        sec_bunks_ranking_df = sec_bunks_ranking_df.sort_values(by='total_bunks', ascending=False)
                        sec_bunks_ranking = sec_bunks_ranking_df.to_dict('records')
                    else:
                        sec_bunks_ranking = []
                else:
                    sec_bunks_ranking = []
                
            else: # Cumulative Mode
                student_att_rows = conn.execute("""
                    SELECT subject, hours_attended, hours_conducted, (hours_conducted - hours_attended) as bunks
                    FROM attendance WHERE roll_no=?
                """, (selected_roll,)).fetchall()
                
                st_total_conducted = sum(r['hours_conducted'] for r in student_att_rows)
                st_total_bunks = sum(r['bunks'] for r in student_att_rows)
                st_attendance_pct = (sum(r['hours_attended'] for r in student_att_rows) / max(1, st_total_conducted) * 100)
                
                # Calculate Section Bunk Rank (only ranking active/non-debarred students)
                sec_bunks_ranking = conn.execute(f"""
                    SELECT roll_no, SUM(hours_conducted - hours_attended) as total_bunks
                    FROM attendance JOIN students USING(roll_no)
                    WHERE section=? AND {active_f_att}
                    GROUP BY roll_no
                    ORDER BY total_bunks DESC
                """, (selected_section,)).fetchall()
                
            if is_debarred:
                rank_str = "Excluded (Debarred)"
            else:
                rank = 1
                for r in sec_bunks_ranking:
                    if r['roll_no'] == selected_roll:
                        break
                    rank += 1
                rank_str = f"#{rank} / {sec_students_count}"
                
            # Display Student KPI Cards
            st.markdown(f"""
            <div class="metric-grid" style="margin-top: 15px;">
                <div class="metric-card" style="background: #181825; border-color: #45475a;">
                    <div class="metric-label">Student Total Bunks</div>
                    <div class="metric-value" style="color: #f43f5e;">{st_total_bunks}</div>
                </div>
                <div class="metric-card" style="background: #181825; border-color: #45475a;">
                    <div class="metric-label">Section Bunk Rank</div>
                    <div class="metric-value" style="color: #f59e0b;">{rank_str}</div>
                </div>
                <div class="metric-card" style="background: #181825; border-color: #45475a;">
                    <div class="metric-label">Attendance Percentage</div>
                    <div class="metric-value" style="color: {'#10b981' if st_attendance_pct >= 75 else '#f59e0b' if st_attendance_pct >= 65 else '#ef4444'};">{st_attendance_pct:.1f}%</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Sub-plots for student
            cds1, cds2 = st.columns(2)
            with cds1:
                st.markdown("#### 📚 Subject-wise Absences")
                if data_source == "📊 Real Scraped Hour-Wise (Precise)":
                    if not df_precise_bunks.empty:
                        df_stud_bunks = df_precise_bunks[df_precise_bunks['roll_no'] == selected_roll]
                        if not df_stud_bunks.empty:
                            df_sub_break = df_stud_bunks.groupby('subject').size().reset_index(name='bunks')
                        else:
                            df_sub_break = pd.DataFrame(columns=['subject', 'bunks'])
                    else:
                        df_sub_break = pd.DataFrame(columns=['subject', 'bunks'])
                else:
                    df_sub_break = pd.DataFrame([dict(r) for r in student_att_rows])
                    
                if not df_sub_break.empty:
                    fig_sub_break = px.bar(
                        df_sub_break, x='subject', y='bunks',
                        color='bunks', color_continuous_scale='Reds',
                        labels={'subject':'Subject', 'bunks':'Missed Hours'}
                    )
                    fig_sub_break.update_layout(showlegend=False, height=280)
                    st.plotly_chart(fig_sub_break, use_container_width=True)
                else:
                    st.success("🎉 No absences recorded for this student.")
                    
            with cds2:
                st.markdown("#### 📅 Weekday Absence Distribution")
                if data_source == "📊 Real Scraped Hour-Wise (Precise)":
                    if not df_precise_bunks.empty:
                        df_stud_bunks = df_precise_bunks[df_precise_bunks['roll_no'] == selected_roll]
                        if not df_stud_bunks.empty:
                            df_wd_raw = df_stud_bunks.groupby('date').size().reset_index(name='absences')
                            df_wd_raw = df_wd_raw.rename(columns={'date': 'snapshot_date'})
                            df_wd_raw['date_obj'] = pd.to_datetime(df_wd_raw['snapshot_date'])
                            df_wd_raw['Day'] = df_wd_raw['date_obj'].dt.day_name()
                            weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                            df_wd_stud = df_wd_raw.groupby('Day')['absences'].sum().reindex(weekday_order).fillna(0).reset_index()
                        else:
                            df_wd_stud = pd.DataFrame()
                    else:
                        df_wd_stud = pd.DataFrame()
                else:
                    tt_stud = get_timetable_for_section(conn, selected_section)
                    weekday_dist = {'Monday':0, 'Tuesday':0, 'Wednesday':0, 'Thursday':0, 'Friday':0}
                    period_dist = {f"P{i}":0 for i in range(1, 7)}
                    period_weights = {1:1.0, 2:0.9, 3:1.2, 4:2.2, 5:2.8, 6:3.2}
                    for r in student_att_rows:
                        sub = r['subject']
                        bunks = r['bunks']
                        if bunks <= 0:
                            continue
                        occurrences = [item for item in tt_stud if item['subject'] == sub]
                        if not occurrences:
                            continue
                        total_w = sum(period_weights[item['period']] for item in occurrences)
                        for occ in occurrences:
                            w = period_weights[occ['period']] / total_w
                            weekday_dist[occ['day']] += bunks * w
                            period_dist[f"P{occ['period']}"] += bunks * w
                    df_wd_stud = pd.DataFrame({
                        'Day': list(weekday_dist.keys()),
                        'absences': [round(v, 1) for v in weekday_dist.values()]
                    })
                    
                if not df_wd_stud.empty:
                    fig_wd_stud = px.bar(
                        df_wd_stud, x='Day', y='absences',
                        color='absences', color_continuous_scale='Sunset',
                        labels={'absences':'Missed periods'}
                    )
                    fig_wd_stud.update_layout(showlegend=False, height=280)
                    st.plotly_chart(fig_wd_stud, use_container_width=True)
                else:
                    st.info("No day-wise records available.")
                    
            st.markdown("---")
            
            # Period Pattern & Streak Analysis
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.markdown("#### 🕒 Period Absence Distribution")
                if data_source == "📊 Real Scraped Hour-Wise (Precise)":
                    if not df_precise_bunks.empty:
                        df_stud_bunks = df_precise_bunks[df_precise_bunks['roll_no'] == selected_roll]
                        if not df_stud_bunks.empty:
                            df_p_stud = df_stud_bunks.groupby('hour').size().reset_index(name='absences')
                            df_p_stud['Period'] = 'P' + df_p_stud['hour'].astype(str)
                            df_p_stud = df_p_stud.sort_values(by='hour').drop(columns=['hour'])
                        else:
                            df_p_stud = pd.DataFrame(columns=['Period', 'absences'])
                    else:
                        df_p_stud = pd.DataFrame(columns=['Period', 'absences'])
                else:
                    df_p_stud = pd.DataFrame({
                        'Period': list(period_dist.keys()),
                        'absences': [round(v, 1) for v in period_dist.values()]
                    })
                    
                if not df_p_stud.empty:
                    fig_p_stud = px.bar(
                        df_p_stud, x='Period', y='absences',
                        color='absences', color_continuous_scale='Burg',
                        labels={'absences':'Missed hours'}
                    )
                    fig_p_stud.update_layout(showlegend=False, height=280)
                    st.plotly_chart(fig_p_stud, use_container_width=True)
                else:
                    st.info("No period-wise records available.")
                    
            with col_p2:
                st.markdown("#### 🚨 Consecutive Streak Analysis")
                # Calculate consecutive missed hours
                if data_source == "📊 Real Scraped Hour-Wise (Precise)":
                    longest_streak = 0
                    current_streak = 0
                    if not df_precise_bunks.empty:
                        df_stud_bunks = df_precise_bunks[df_precise_bunks['roll_no'] == selected_roll]
                        if not df_stud_bunks.empty:
                            df_events = df_stud_bunks.sort_values(by=['date', 'hour']).copy()
                            df_events['datetime'] = pd.to_datetime(df_events['date'])
                            prev_dt = None
                            prev_hr = None
                            for _, row in df_events.iterrows():
                                curr_dt = row['datetime']
                                curr_hr = row['hour']
                                if prev_dt is None:
                                    current_streak = 1
                                else:
                                    # Check if consecutive hour on same day
                                    if curr_dt == prev_dt and curr_hr == prev_hr + 1:
                                        current_streak += 1
                                    else:
                                        current_streak = 1
                                longest_streak = max(longest_streak, current_streak)
                                prev_dt = curr_dt
                                prev_hr = curr_hr
                else:
                    df_stud_history = query_to_dataframe(conn, """
                        SELECT snapshot_date, subject_code, running_attended, running_conducted
                        FROM attendance_history
                        WHERE roll_no=?
                        ORDER BY snapshot_date
                    """, (selected_roll,))
                    longest_streak = 0
                    if not df_stud_history.empty:
                        df_stud_history['prev_cond'] = df_stud_history.groupby('subject_code')['running_conducted'].shift(1).fillna(0).astype(int)
                        df_stud_history['prev_att'] = df_stud_history.groupby('subject_code')['running_attended'].shift(1).fillna(0).astype(int)
                        df_stud_history['cond_today'] = df_stud_history['running_conducted'] - df_stud_history['prev_cond']
                        df_stud_history['att_today'] = df_stud_history['running_attended'] - df_stud_history['prev_att']
                        df_stud_history['bunks_today'] = (df_stud_history['cond_today'] - df_stud_history['att_today']).clip(lower=0)
                        
                        df_stud_events = df_stud_history[df_stud_history['cond_today'] > 0].copy()
                        current_streak = 0
                        for _, row in df_stud_events.iterrows():
                            if row['bunks_today'] > 0:
                                current_streak += int(row['bunks_today'])
                                longest_streak = max(longest_streak, current_streak)
                            else:
                                current_streak = 0
                                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(244, 63, 94, 0.1) 100%);
                            border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 14px;
                            padding: 25px; text-align: center; margin-top: 20px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                    <div style="font-size: 2.5rem; margin-bottom: 5px;">🔥</div>
                    <h4 style="color: #ef4444; margin: 0; font-size: 1.3rem;">Longest Consecutive Absence Streak</h4>
                    <div style="font-size: 3rem; font-weight: 700; color: #f8fafc; font-family: 'Outfit', sans-serif; margin-top: 8px;">{longest_streak} Classes</div>
                    <p style="color: #94a3b8; font-size: 0.9rem; margin-top: 5px;">Maximum consecutive missed subject periods without attendance check-in.</p>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown("---")
            
            # Bunk Chronological Timeline
            st.markdown("#### 📅 Chronological Bunk Timeline")
            st.caption("Log of all historical class absences mapped sequentially by date.")
            
            if data_source == "📊 Real Scraped Hour-Wise (Precise)":
                if not df_precise_bunks.empty:
                    df_stud_bunks = df_precise_bunks[df_precise_bunks['roll_no'] == selected_roll]
                    if not df_stud_bunks.empty:
                        df_stud_bunk_events = df_stud_bunks.groupby(['date', 'subject']).size().reset_index(name='bunks_today')
                        df_stud_bunk_events = df_stud_bunk_events.rename(columns={'date': 'snapshot_date', 'subject': 'subject_code'})
                        df_stud_bunk_events = df_stud_bunk_events.sort_values(by='snapshot_date')
                    else:
                        df_stud_bunk_events = pd.DataFrame(columns=['snapshot_date', 'subject_code', 'bunks_today'])
                else:
                    df_stud_bunk_events = pd.DataFrame(columns=['snapshot_date', 'subject_code', 'bunks_today'])
            else:
                if not df_stud_history.empty:
                    df_stud_bunk_events = df_stud_events[df_stud_events['bunks_today'] > 0].copy()
                else:
                    df_stud_bunk_events = pd.DataFrame()
                    
            if not df_stud_bunk_events.empty:
                fig_timeline = px.scatter(
                    df_stud_bunk_events, x='snapshot_date', y='subject_code',
                    size='bunks_today', color='bunks_today',
                    color_continuous_scale='Reds',
                    labels={'snapshot_date':'Date', 'subject_code':'Subject', 'bunks_today':'Classes Missed'},
                    title="Timeline of Missed Classes"
                )
                fig_timeline.update_layout(height=350, margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig_timeline, use_container_width=True)
            else:
                st.success("🎉 This student has not missed any classes since January 27!")
        else:
            st.info("No student profiles registered in this section.")
            
    conn.close()


def admin_analytics():
    st.markdown("# 📈 Admin Analytics")
    conn = get_db_connection()
    cfg = get_config_map(conn)
    sem = cfg.get('active_semester', 'Sem 2')

    # Top absentees
    absentees = conn.execute('''
        SELECT s.roll_no, s.name, s.section,
               ROUND(SUM(a.hours_attended)*100.0/NULLIF(SUM(a.hours_conducted),0), 1) pct
        FROM students s JOIN attendance a ON s.roll_no=a.roll_no AND a.semester=?
        GROUP BY s.roll_no, s.name, s.section 
        HAVING ROUND(SUM(a.hours_attended)*100.0/NULLIF(SUM(a.hours_conducted),0), 1) <= 65 
        ORDER BY pct ASC LIMIT 50
    ''', (sem,)).fetchall()

    # Condonation list (NEW)
    condonation = conn.execute('''
        SELECT s.roll_no, s.name, s.section,
               ROUND(SUM(a.hours_attended)*100.0/NULLIF(SUM(a.hours_conducted),0), 1) pct,
               SUM(a.hours_attended) ta, SUM(a.hours_conducted) tc
        FROM students s JOIN attendance a ON s.roll_no=a.roll_no AND a.semester=?
        GROUP BY s.roll_no, s.name, s.section 
        HAVING ROUND(SUM(a.hours_attended)*100.0/NULLIF(SUM(a.hours_conducted),0), 1) > 65 
           AND ROUND(SUM(a.hours_attended)*100.0/NULLIF(SUM(a.hours_conducted),0), 1) < 75 
        ORDER BY pct ASC LIMIT 50
    ''', (sem,)).fetchall()

    # Section health
    sec_health = conn.execute('''
        SELECT s.section, COUNT(DISTINCT s.roll_no) students,
               ROUND(AVG(a.hours_attended*100.0/NULLIF(a.hours_conducted,0)), 1) avg_pct
        FROM students s JOIN attendance a ON s.roll_no=a.roll_no AND a.semester=?
        GROUP BY s.section ORDER BY avg_pct ASC
    ''', (sem,)).fetchall()
    conn.close()

    st.markdown("### 🏥 Section Health Dashboard")
    if sec_health:
        sh_df = pd.DataFrame([dict(r) for r in sec_health])
        fig = px.bar(sh_df, x='section', y='avg_pct', color='avg_pct',
                     color_continuous_scale=[[0, '#EF4444'], [0.65, '#F59E0B'], [0.75, '#00D8C6'], [1, '#00D8C6']],
                     range_color=[0, 100])
        fig.add_hline(y=75, line_dash="dash", line_color="green")
        fig.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("### 🚨 Top Absentees (≤65%)")
        if absentees:
            ab_df = pd.DataFrame([dict(r) for r in absentees])
            st_premium_table(ab_df[['roll_no','name','section','pct']].rename(columns={
                'roll_no':'Roll','name':'Name','section':'Sec','pct':'%'}))
        else:
            st.success("🎉 No students below 65%!")
    with cc2:
        st.markdown("### ⚠️ Condonation Zone (65-75%)")
        if condonation:
            cond_data = []
            for r in condonation:
                c = r['tc'] or 0; a = r['ta'] or 0
                h75 = math.ceil((0.75*c-a)/0.25) if c>0 and a<0.75*c else 0
                cond_data.append({'Roll': r['roll_no'], 'Name': r['name'],
                                  'Sec': r['section'], '%': r['pct'], 'Need': h75})
            st_premium_table(pd.DataFrame(cond_data))
        else:
            st.info("None in condonation zone.")


def admin_timetable():
    st.markdown("# 🗓️ Timetable Management")
    section = st.selectbox("Section", CLASSES)
    uploaded = st.file_uploader("Upload Timetable CSV (columns: day, period, subject)", type=['csv'])
    if uploaded and st.button("📤 Upload"):
        df = pd.read_csv(uploaded)
        conn = get_db_connection()
        success = True
        for _, row in df.iterrows():
            p_val = str(row['period']).strip()
            periods_list = parse_period_string(p_val)

            if not periods_list:
                st.error(f"⚠️ Invalid period format in CSV: '{p_val}'")
                success = False
                break

            for p in periods_list:
                conn.execute('''
                    INSERT INTO timetable(section, day, period, subject)
                    VALUES(?,?,?,?)
                    ON CONFLICT(section, day, period) DO UPDATE SET subject=excluded.subject
                ''', (section, str(row['day']).strip(), p, str(row['subject']).strip()))
        if success:
            conn.commit()
            st.success(f"Timetable uploaded for {section}")
        conn.close()

    # Show current
    conn = get_db_connection()
    tt = conn.execute('SELECT * FROM timetable ORDER BY section, day, period').fetchall()
    conn.close()
    if tt:
        tt_df = pd.DataFrame([dict(r) for r in tt])
        display_df = tt_df[['section', 'day', 'period', 'subject']].rename(columns={
            'section': 'Section',
            'day': 'Day',
            'period': 'Period',
            'subject': 'Subject'
        })
        st_premium_table(display_df)


def admin_backup_page():
    st.markdown("# 💾 Database Backup")
    st.info("Create a timestamped backup of the database. Keeps last 10 backups.")
    if st.button("📦 Create Backup Now", use_container_width=True):
        path = backup_db()
        if path:
            st.success(f"✅ Backup created: `{os.path.basename(path)}`")
        else:
            st.error("Backup failed.")

    # List existing backups
    backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
    if os.path.exists(backup_dir):
        backups = sorted(os.listdir(backup_dir), reverse=True)
        st.markdown(f"### 📁 Existing Backups ({len(backups)})")
        for b in backups:
            full_path = os.path.join(backup_dir, b)
            size_mb = os.path.getsize(full_path) / 1024 / 1024
            st.text(f"📄 {b} ({size_mb:.2f} MB)")


def admin_settings():
    st.markdown("# ⚙️ Admin Settings")
    st.markdown("### 🔑 Change Admin Password")
    with st.form("change_admin_pwd"):
        cur = st.text_input("Current Password", type="password")
        new1 = st.text_input("New Password", type="password")
        new2 = st.text_input("Confirm New Password", type="password")
        if st.form_submit_button("💾 Update Password"):
            if not verify_admin_pwd(cur.strip()):
                st.error("Current password is incorrect.")
            elif not new1 or new1 != new2:
                st.error("New passwords don't match or are empty.")
            elif len(new1) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                change_admin_pwd(new1.strip())
                st.success("✅ Admin password changed successfully!")

    st.markdown("---")
    st.markdown("### 📅 Semester & Date Configuration")
    conn = get_db_connection()
    cfg = get_config_map(conn)
    conn.close()
    with st.form("config_form"):
        active = st.selectbox("Active Semester", [f"Sem {i}" for i in range(1, 9)],
            index=int(cfg.get('active_semester', 'Sem 2').replace('Sem ', '')) - 1)
        sd = st.date_input("Semester Start", value=dt.strptime(cfg.get('start_date', '2026-01-27'), '%Y-%m-%d'))
        total_hours = st.number_input("Total Semester Hours (Default)", min_value=1, value=int(cfg.get('total_semester_hours', '600')))
        if st.form_submit_button("💾 Save Config"):
            conn = get_db_connection()
            conn.execute("INSERT INTO config (key, value) VALUES ('active_semester', ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (active,))
            conn.execute("INSERT INTO config (key, value) VALUES ('start_date', ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (sd.strftime('%Y-%m-%d'),))
            conn.execute("INSERT INTO config (key, value) VALUES ('total_semester_hours', ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (str(total_hours),))
            conn.commit(); conn.close()
            st.success("Configuration saved.")


# ══════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════
if not st.session_state.get('logged_in'):
    login_page()
elif st.session_state.get('needs_dob_setup'):
    setup_dob_page()
elif st.session_state.get('role') == 'admin':
    admin_dashboard()
else:
    student_dashboard()
