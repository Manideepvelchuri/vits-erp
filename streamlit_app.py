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
    page_title="VITS Academic ERP",
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
            <h1 style="color: #00D8C6; font-family: 'Outfit', sans-serif; font-size: 3rem; margin-top: 10px; margin-bottom: 5px; text-shadow: 0 0 35px rgba(0, 216, 198, 0.3);">VITS ERP</h1>
            <p style="color: #cbd5e1; font-family: 'Inter', sans-serif; font-size: 1.1rem; letter-spacing: 0.5px; font-weight: 500;">Vignan Institute of Technology and Science</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #00D8C6; font-family: 'Outfit', sans-serif; font-size: 3rem; margin-bottom: 5px; text-shadow: 0 0 35px rgba(0, 216, 198, 0.3);">🎓 VITS ERP</h1>
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

    # SGPA for this sem
    conn = get_db_connection()
    sgpa_row = conn.execute(
        'SELECT sgpa, failed FROM sgpa_records WHERE roll_no=? AND semester=?',
        (student['roll_no'], sem)).fetchone()
    
    # Completed Credits & Backlogs calculation
    final_marks = conn.execute('''
        SELECT subject, score FROM marks
        WHERE roll_no=? AND exam_type LIKE '%Final Examinations'
    ''', (student['roll_no'],)).fetchall()
    conn.close()

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
                You can miss <strong style="color:#10B981;">{can_miss}</strong> more classes and stay above 75%.</p>
                </div>""", unsafe_allow_html=True)
        elif overall >= 65:
            st.markdown(f"""<div class="status-banner" style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.3);">
                <h3 style="color:#F59E0B !important;margin:0;">🟠 Risk Zone</h3>
                <p style="margin:8px 0 0 0;color:#cbd5e1 !important;">Current Attendance: <strong style="color:#fff;">{overall}%</strong>.
                Attend <strong style="color:#F59E0B;">{need}</strong> consecutive classes to reach 75%.</p>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="status-banner" style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.3);">
                <h3 style="color:#EF4444 !important;margin:0;">🔴 Debarred Zone</h3>
                <p style="margin:8px 0 0 0;color:#cbd5e1 !important;">Current Attendance: <strong style="color:#fff;">{overall}%</strong>.
                You need <strong style="color:#EF4444;">{need}</strong> classes to recover to 75%.</p>
                </div>""", unsafe_allow_html=True)

        # Overall attendance skip predictor
        if total_c > 0:
            st.markdown("### 🔮 Overall Attendance Skip Predictor")
            conn = get_db_connection()
            sec = student['section']
            avg_classes = 7.0
            if sec:
                days_count = conn.execute('SELECT COUNT(DISTINCT day) FROM timetable WHERE section=?', (sec,)).fetchone()[0]
                total_periods = conn.execute('SELECT COUNT(*) FROM timetable WHERE section=?', (sec,)).fetchone()[0]
                if days_count > 0:
                    avg_classes = total_periods / days_count
            conn.close()

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

    # ── Full-width section below columns ──────────────────────
    if subj_data:
        best = max(subj_data, key=lambda x: x['pct'])
        worst = min(subj_data, key=lambda x: x['pct'])
        st.markdown("### 📊 Academic Summary")
        s1, s2, s3 = st.columns(3)
        s1.markdown(f"""<div class="insight-box"><div style="color:#94a3b8;font-size:0.8rem;text-transform:uppercase;">Current SGPA</div>
            <div style="color:#8B5CF6;font-size:1.6rem;font-weight:800;font-family:'Outfit';">{sgpa_text}</div></div>""", unsafe_allow_html=True)
        s2.markdown(f"""<div class="insight-box"><div style="color:#10B981;font-size:1.3rem;font-weight:700;font-family:'Outfit';">{best['subject']} ({best['pct']}%)</div></div>""", unsafe_allow_html=True)
        s3.markdown(f"""<div class="insight-box"><div style="color:#94a3b8;font-size:0.8rem;text-transform:uppercase;">Needs Attention</div>
            <div style="color:#EF4444;font-size:1.3rem;font-weight:700;font-family:'Outfit';">{worst['subject']} ({worst['pct']}%)</div></div>""", unsafe_allow_html=True)

        st.markdown("### 📈 Subject Attendance Overview")
        df = pd.DataFrame(subj_data)
        fig = px.bar(df, x='subject', y='pct', color='pct',
                     color_continuous_scale=[[0, '#EF4444'], [0.65, '#F59E0B'], [0.75, '#00D8C6'], [1, '#00D8C6']],
                     range_color=[0, 100], labels={'pct': 'Attendance %', 'subject': 'Subject'})
        fig.add_hline(y=75, line_dash="dash", line_color="green", annotation_text="75% target")
        fig.add_hline(y=65, line_dash="dash", line_color="orange", annotation_text="65% min")
        fig.update_layout(height=420, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
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

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Hours Conducted", total_c)
    c2.metric("Hours Attended", total_a)
    c3.metric("Overall %", f"{overall}%")
    if overall >= 75:
        c4.metric("Can Miss", can_miss_classes(total_a, total_c))
    else:
        c4.metric("Attend Next", classes_needed(total_a, total_c))

    if total_c > 0:
        if overall >= 75:
            st.success(f"✅ Good standing — you can miss {can_miss_classes(total_a, total_c)} classes and stay above 75%")
        elif overall >= 65:
            st.warning(f"⚠️ Condonation required — attend {classes_needed(total_a, total_c)} more classes for 75%")
        else:
            st.error(f"🚫 Debarred — attend {classes_needed(total_a, total_c)} classes to recover")
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
            "📤 CSV Upload", "📥 Results Import", "🔄 Scraper",
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
        "📥 Results Import": admin_results_import,
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


def admin_csv_upload():
    st.markdown("# 📤 Bulk CSV Upload")
    st.caption("CSV format: `roll_no, SUBJECT1, SUBJECT2, ...`")
    c1, c2 = st.columns(2)
    sem  = c1.selectbox("Semester", [f"Sem {i}" for i in range(1, 9)], index=1)
    exam = c2.selectbox("Exam Type", ['Mid 1', 'Mid 2', 'Lab Internals', f"{sem} Final Examinations"])
    uploaded = st.file_uploader("Upload CSV", type=['csv'])
    if uploaded:
        df = pd.read_csv(uploaded)
        # Bug 12 fix: normalize roll_no column name
        df.columns = [c.strip() for c in df.columns]
        roll_col = next((c for c in df.columns if c.lower().replace(' ', '').replace('_', '') == 'rollno'), None)
        if not roll_col:
            st.error("CSV must have a 'roll_no' column.")
            return
        st_premium_table(df.head())
        if st.button("📤 Import Now"):
            conn = get_db_connection(); count = 0
            for _, row in df.iterrows():
                roll = str(row.get(roll_col, '')).strip().upper()
                if not roll: continue
                for col in df.columns:
                    if col == roll_col: continue
                    val = pd.to_numeric(row[col], errors='coerce')
                    if pd.isna(val): continue
                    score = float(val); _, gp = score_to_grade(score)
                    conn.execute('''
                        INSERT INTO marks(roll_no,subject,semester,exam_type,score,grade_point)
                        VALUES(?,?,?,?,?,?)
                        ON CONFLICT(roll_no,subject,semester,exam_type) DO UPDATE SET
                            score=excluded.score, grade_point=excluded.grade_point
                    ''', (roll, col.strip(), sem, exam, score, gp))
                    count += 1
            conn.commit(); conn.close()
            st.success(f"Imported {count} mark entries.")


def admin_results_import():
    st.markdown("# 📥 Import Semester Results CSV")
    st.caption("Upload the JNTUH results format: Hall no, Name, SUB1 [Total,GP], SUB2 [Total,GP], ..., SGPA")

    conn = get_db_connection()
    cfg = get_config_map(conn)
    conn.close()
    active_sem = cfg.get('active_semester', 'Sem 2')

    c1, c2 = st.columns(2)
    try:
        active_idx = [f"Sem {i}" for i in range(1, 9)].index(active_sem)
    except ValueError:
        active_idx = 1
    semester = c1.selectbox("Semester", [f"Sem {i}" for i in range(1, 9)], index=active_idx)
    exam_type = c2.selectbox("Exam Type", ['Mid 1', 'Mid 2', 'Lab Internals', 'Final Examinations'])
    uploaded = st.file_uploader("Upload Results CSV", type=['csv'], key='results_csv')

    if uploaded and st.button("📥 Import Now"):
        try:
            # Bug 5 fix: derive numeric semester from text
            try:
                sem_num = int(semester.replace("Sem", "").strip())
            except Exception:
                sem_num = 2
            content = uploaded.read().decode('utf-8')
            parsed  = parse_sem1_results_csv(content)
            conn    = get_db_connection()
            marks_count = sgpa_count = 0

            # Determine exam type label for database marks table
            if exam_type == 'Final Examinations':
                db_exam_type = f"{semester} Final Examinations"
            else:
                db_exam_type = exam_type

            with st.spinner(f"Importing {len(parsed)} records..."):
                for record in parsed:
                    roll = record['roll_no']
                    branch = decode_roll_branch(roll) or 'ECE'
                    
                    st_row = conn.execute('SELECT section FROM students WHERE roll_no=?', (roll,)).fetchone()
                    section = st_row['section'] if st_row else f"{branch}_A"

                    conn.execute('''
                        INSERT INTO students(roll_no,name,dob,semester,branch,department,section)
                        VALUES(?,?,?,?,?,?,?)
                        ON CONFLICT(roll_no) DO UPDATE SET name=excluded.name
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
