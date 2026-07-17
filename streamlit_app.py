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
@st.cache_resource(ttl=300)
def _check_db_backend_cached():
    if os.environ.get("USE_SQLITE", "").lower() == "true":
        return "sqlite", False
        
    pg_url = ""
    try:
        import streamlit as _st
        pg_url = _st.secrets.get("database", {}).get("url", "")
    except Exception:
        pass
    if not pg_url:
        pg_url = os.environ.get("DATABASE_URL", "")

    if pg_url:
        # Automatically rewrite Supabase pooler port 5432 to 6543 for pooled connections
        if "pooler.supabase.com:5432" in pg_url:
            pg_url = pg_url.replace("pooler.supabase.com:5432", "pooler.supabase.com:6543")
            
        try:
            import psycopg2
            # Connect with a short timeout to see if PG is available and has connection slots
            conn = psycopg2.connect(pg_url, connect_timeout=3)
            conn.close()
            return "pg", False
        except Exception:
            # Fall back to SQLite if PostgreSQL fails (e.g. max connections reached)
            return "sqlite", True
            
    return "sqlite", False

_DB_BACKEND, _DB_FALLBACK = _check_db_backend_cached()

if _DB_BACKEND == "pg":
    from database_pg import (
        init_db, get_db_connection, get_config_map,
        CLASSES, SECTION_SUBJECTS, SUBJECT_CREDITS, SEM1_SUBJECTS,
        score_to_grade, gp_to_grade, compute_sgpa, backup_db, compute_cgpa,
        parse_sem1_results_csv, decode_roll_branch
    )
else:
    from database import (
        init_db, get_db_connection, get_config_map,
        CLASSES, SECTION_SUBJECTS, SUBJECT_CREDITS, SEM1_SUBJECTS,
        score_to_grade, gp_to_grade, compute_sgpa, backup_db, compute_cgpa,
        parse_sem1_results_csv, decode_roll_branch
    )
def get_subject_credits(sub):
    if not sub:
        return 3.0
    clean = str(sub).strip().upper()
    if clean in SUBJECT_CREDITS:
        return SUBJECT_CREDITS[clean]
    # Fallback to JNTUH dynamic defaults
    if 'LAB' in clean or 'PRACTICAL' in clean or 'SIMULATION' in clean:
        return 1.5
    if 'PROJECT' in clean or 'MINI' in clean:
        return 2.0
    if any(x in clean for x in ['CRT', 'TA', 'SSC', 'ES', 'NPTEL', 'IP']):
        return 0.0
    return 3.0


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

/* ── Mobile: prevent single-finger chart zoom ─────────────── */
div[data-testid="stPlotlyChart"] {
    touch-action: pan-y !important;
}
div[data-testid="stPlotlyChart"] > div {
    touch-action: pan-y !important;
}
div[data-testid="stPlotlyChart"] iframe {
    touch-action: pan-y !important;
}
.js-plotly-plot, .plot-container, .svg-container {
    touch-action: pan-y !important;
}

/* Custom Responsive KPI Cards Row */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 15px;
    margin-bottom: 25px;
}

.kpi-card {
    background: rgba(10, 14, 26, 0.45);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    backdrop-filter: blur(5px);
    height: 125px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: 'Outfit', sans-serif;
    position: relative;
    transition: all 0.3s ease;
}
.kpi-card:hover {
    border-color: rgba(255, 255, 255, 0.1);
    background: rgba(15, 23, 42, 0.55);
}
.kpi-card-attendance:hover { border-color: rgba(0, 216, 198, 0.3); }
.kpi-card-gpa:hover { border-color: rgba(139, 92, 246, 0.3); }
.kpi-card-credits:hover { border-color: rgba(16, 185, 129, 0.3); }
.kpi-card-subjects:hover { border-color: rgba(249, 115, 22, 0.3); }
.kpi-card-backlog {
    border: 1px solid rgba(239, 68, 68, 0.15);
    background: rgba(239, 68, 68, 0.03);
}
.kpi-card-backlog:hover {
    border-color: rgba(239, 68, 68, 0.3);
    background: rgba(239, 68, 68, 0.05);
}

.kpi-card-content {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
    text-align: left;
    width: 100%;
}
.kpi-card-title {
    font-size: 0.75rem;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.kpi-card-title.text-red {
    color: #EF4444;
}
.kpi-card-val {
    font-size: 2.1rem;
    font-weight: 800;
    line-height: 1.1;
    margin: 2px 0;
}
.text-teal { color: #00D8C6; }
.text-emerald { color: #10B981; }
.text-orange { color: #F97316; }
.text-white { color: #ffffff; }
.text-red { color: #EF4444; }

.kpi-card-sub {
    font-size: 0.75rem;
    color: #64748b;
}
.kpi-card-icon {
    font-size: 1.8rem;
    opacity: 0.85;
}
.text-green { color: #00e676; font-weight: 700; }
.text-purple { color: #b388ff; }

/* Concentric circular progress card responsive class */
.circular-progress-card {
    background: rgba(10, 14, 26, 0.45);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.15);
    height: 330px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: center;
}
.circular-svg-wrapper {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
    margin-top: 10px;
    width: 190px;
    height: 190px;
}
.circular-svg {
    width: 100%;
    height: 100%;
}
.circular-inner-text {
    position: absolute;
    text-align: center;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
}
.circular-legend {
    text-align: center;
    font-size: 0.72rem;
    color: #64748b;
    font-weight: 600;
    font-family: 'Inter', sans-serif;
    margin-bottom: 5px;
}

/* Subject Health card class */
.subject-health-card {
    background: rgba(10, 14, 26, 0.45);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.15);
    height: 520px;
    overflow-y: auto;
}

/* Daily Schedule card class */
.daily-schedule-card {
    background: rgba(10, 14, 26, 0.45);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 20px;
    min-height: 450px;
    max-height: 450px;
    overflow-y: auto;
    backdrop-filter: blur(10px);
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.15);
}

/* Cloud Resources card class */
.cloud-resources-card {
    background: linear-gradient(135deg, rgba(0, 216, 198, 0.08) 0%, rgba(139, 92, 246, 0.08) 100%);
    border: 1px solid rgba(0, 216, 198, 0.15);
    border-radius: 16px;
    padding: 20px;
    text-align: center;
    height: 180px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    font-family: 'Outfit', sans-serif;
}

/* Welcome badges layout class */
.greeting-badge-container {
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
    color: #94a3b8;
    margin-top: 8px;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}
.greeting-badge-pill {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.05);
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: 600;
}
.badge-roll { color: #00D8C6; }
.badge-section { color: #8B5CF6; }
.badge-sem { color: #F97316; }

/* ── Mobile Layout Optimization Media Queries ── */
@media (max-width: 1024px) {
    .block-container {
        padding-top: 3.5rem !important;
    }
    .kpi-grid {
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
    }
}

@media (max-width: 768px) {
    /* Reduce page side padding on mobile and push top down to clear Streamlit's fixed header */
    .block-container {
        padding-top: 3.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-bottom: 1.5rem !important;
    }
    
    /* Responsive header elements */
    h1 {
        font-size: 1.95rem !important;
    }
    .greeting-badge-container {
        gap: 6px !important;
        margin-top: 10px !important;
    }
    .greeting-badge-pill {
        padding: 3px 10px !important;
        font-size: 0.72rem !important;
    }
    
    /* Responsive KPI cards */
    .kpi-card {
        height: auto;
        min-height: 110px;
        padding: 12px 16px;
    }
    .kpi-card-val {
        font-size: 1.7rem;
    }
    .kpi-card-val.val-dynamic {
        font-size: 1.45rem !important;
    }
    .kpi-card-icon {
        font-size: 1.5rem;
    }
    
    /* Responsive middle section cards */
    .circular-progress-card {
        height: auto;
        padding: 16px;
    }
    .circular-svg-wrapper {
        width: 160px;
        height: 160px;
    }
    .circular-inner-text div[style*="font-size: 2.2rem"] {
        font-size: 1.8rem !important;
    }
    
    .subject-health-card {
        height: auto;
        max-height: 400px;
        padding: 16px;
    }
    
    .daily-schedule-card {
        min-height: auto;
        max-height: 350px;
        padding: 16px;
    }
    
    .cloud-resources-card {
        height: auto;
        padding: 20px 16px;
    }
}

@media (max-width: 480px) {
    .kpi-grid {
        grid-template-columns: 1fr;
        gap: 10px;
    }
}

/* College Header Bar styling */
.college-header-bar {
    position: sticky !important;
    top: 0px !important;
    z-index: 9999 !important;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(7, 9, 19, 0.95) !important;
    border: 1px solid rgba(0, 216, 198, 0.12) !important;
    border-radius: 16px !important;
    padding: 12px 24px !important;
    margin-bottom: 25px !important;
    backdrop-filter: blur(25px) !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5) !important;
    width: 100% !important;
}

.header-left {
    display: flex;
    align-items: center;
    gap: 16px;
}

.header-logo {
    width: 48px;
    height: 48px;
    filter: drop-shadow(0 2px 8px rgba(0, 216, 198, 0.3));
    object-fit: contain;
}

.header-college-info {
    display: flex;
    flex-direction: column;
}

.college-title {
    color: #00D8C6 !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 800 !important;
    font-size: 1.25rem !important;
    letter-spacing: 0.5px !important;
    text-shadow: 0 0 20px rgba(0, 216, 198, 0.2);
    margin: 0 !important;
    line-height: 1.2 !important;
}

.college-sub {
    color: #94a3b8 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
    margin: 2px 0 0 0 !important;
}

.header-right {
    display: flex;
    align-items: center;
}

.header-student-details {
    display: flex;
    align-items: center;
    gap: 12px;
    background: rgba(255, 255, 255, 0.03) !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    padding: 8px 18px !important;
    border-radius: 30px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.8rem !important;
    color: #cbd5e1 !important;
}

.detail-item {
    white-space: nowrap;
}

.detail-label {
    color: #00D8C6 !important;
    font-weight: 600;
}

.detail-divider {
    color: rgba(255, 255, 255, 0.15) !important;
}

.header-spacing {
    height: 5px;
}

@media (max-width: 992px) {
    /* Hide the header bar on mobile for all pages EXCEPT the home page */
    .college-header-bar:not(.page-home) {
        display: none !important;
    }
    .college-header-bar {
        position: relative !important;
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 12px !important;
        padding: 12px 18px !important;
    }
    .header-right {
        width: 100% !important;
    }
    .header-student-details {
        width: 100% !important;
        justify-content: space-between !important;
        border-radius: 10px !important;
        flex-wrap: wrap !important;
        gap: 6px 12px !important;
    }
    .detail-divider {
        display: none !important;
    }
}

@media (max-width: 768px) {
    .college-header-bar {
        padding: 8px 12px !important;
        margin-bottom: 15px !important;
        gap: 8px !important;
    }
    .header-logo {
        width: 32px !important;
        height: 32px !important;
    }
    .college-title {
        font-size: 0.95rem !important;
    }
    .college-sub {
        font-size: 0.62rem !important;
        letter-spacing: 0.5px !important;
    }
    .header-student-details {
        font-size: 0.68rem !important;
        padding: 5px 10px !important;
        gap: 4px 8px !important;
        border-radius: 8px !important;
    }
}
</style>
""", unsafe_allow_html=True)


# ── College Header Helper ────────────────────────────────────
def render_college_header(role="student", student_data=None, active_page=None):
    logo_path = os.path.join(os.path.dirname(__file__), 'vits_logo.png')
    logo_base64 = get_image_base64(logo_path)
    logo_html = f'<img src="data:image/png;base64,{logo_base64}" class="header-logo"/>' if logo_base64 else '🎓'
    
    college_name = "VIGNAN INSTITUTE OF TECHNOLOGY AND SCIENCE"
    
    right_html = ""
    if role == "student" and student_data:
        name_part = student_data['name'].title()
        right_html = (
            f'<div class="header-student-details">'
            f'<span class="detail-item"><strong class="detail-label">HTNo:</strong> {student_data["roll_no"]}</span>'
            f'<span class="detail-divider">|</span>'
            f'<span class="detail-item"><strong class="detail-label">Name:</strong> {name_part}</span>'
            f'<span class="detail-divider">|</span>'
            f'<span class="detail-item"><strong class="detail-label">Branch:</strong> {student_data["branch"]}</span>'
            f'<span class="detail-divider">|</span>'
            f'<span class="detail-item"><strong class="detail-label">Sem:</strong> {student_data["semester"] if "semester" in student_data else "II"}</span>'
            f'</div>'
        )
    elif role == "admin":
        right_html = (
            f'<div class="header-student-details">'
            f'<span class="detail-item"><strong class="detail-label">Role:</strong> Portal Admin</span>'
            f'<span class="detail-divider">|</span>'
            f'<span class="detail-item"><strong class="detail-label">Console:</strong> System Control</span>'
            f'</div>'
        )
        
    page_class = ""
    if active_page:
        clean_page = active_page.lower()
        for char in ['🏠', '📅', '📊', '🧮', '📈', '🗓️', '👥', '📝', '📤', '🔄', '💾', '⚙️', ' ']:
            clean_page = clean_page.replace(char, '')
        clean_page = clean_page.strip()
        if clean_page in ('home', 'dashboard', 'overview'):
            clean_page = 'home'
        page_class = f"page-{clean_page}"
        
    header_html = (
        f'<div class="college-header-bar {page_class}">'
        f'  <div class="header-left">'
        f'    {logo_html}'
        f'    <div class="header-college-info">'
        f'      <div class="college-title">{college_name}</div>'
        f'      <div class="college-sub">(Autonomous) · Deshmukhi, Hyderabad</div>'
        f'    </div>'
        f'  </div>'
        f'  <div class="header-right">'
        f'    {right_html}'
        f'  </div>'
        f'</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)


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
        dragmode=False,
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
    # ── suppress h1 anchor icons globally on this page & style login elements ────────
    st.markdown("""
    <style>
    h1 a, h2 a, h3 a { display: none !important; }
    
    /* Login Header Styling */
    .login-header {
        text-align: center;
        padding: 40px 0 24px 0;
    }
    .login-title {
        color: #00D8C6;
        font-family: 'Outfit', sans-serif;
        font-size: 2.2rem;
        font-weight: 800;
        margin: 8px 0 4px 0;
        text-shadow: 0 0 30px rgba(0,216,198,0.3);
    }
    .login-subtitle {
        color: #94a3b8;
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        letter-spacing: 0.5px;
    }
    
    /* Mobile Layout Optimizations for Login Page Columns */
    @media (max-width: 768px) {
        .login-header {
            padding: 20px 0 12px 0 !important;
        }
        .login-title {
            font-size: 1.65rem !important;
        }
        .login-subtitle {
            font-size: 0.85rem !important;
        }
        
        /* Hide empty side columns on mobile to prevent empty vertical space */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-of-type(1) {
            display: none !important;
        }
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-of-type(3) {
            display: none !important;
        }
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-of-type(2) {
            width: 100% !important;
            max-width: 100% !important;
            flex: 1 1 100% !important;
        }
        
        /* Reduce padding inside forms on mobile to maximize input field area */
        div[data-testid="stForm"] {
            padding: 16px !important;
        }
        
        /* Make alert box more compact on mobile */
        div[data-testid="stAlert"] {
            padding: 10px 14px !important;
        }
        div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {
            font-size: 0.82rem !important;
        }
        
        /* Adjust tab spacing on mobile */
        button[role="tab"] {
            padding: 8px 14px !important;
            font-size: 0.9rem !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    logo_path   = os.path.join(os.path.dirname(__file__), 'vits_logo.png')
    logo_base64 = get_image_base64(logo_path)
    logo_html   = f'<img src="data:image/png;base64,{logo_base64}" width="80" style="margin-bottom:10px;filter:drop-shadow(0 4px 12px rgba(0,216,198,0.3));"/>' if logo_base64 else '🎓'

    st.markdown(f"""
    <div class="login-header">
        {logo_html}
        <div class="login-title">VITS Student Academic Dashboard</div>
        <div class="login-subtitle">Vignan Institute of Technology and Science</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["👤 Student", "🛡️ Admin"])
        with tab1:
            with st.form("student_login"):
                st.info(
                    "🔑 **Password Instructions:**\n\n"
                    "* **First-Time Login:** Use **`vits123`** as the password. You will then set your Date of Birth (DOB) as your permanent password.\n"
                    "* **Returning Students:** Use your configured **Date of Birth** as the password (format: **`YYYY-MM-DD`** or **`DD-MM-YYYY`**, e.g., `2005-08-15` or `15-08-2005`)."
                )
                roll = st.text_input("Roll Number", placeholder="e.g. 23891A0401")
                pwd  = st.text_input("Password", type="password", placeholder="Enter 'vits123' or your DOB")
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
    conn = get_db_connection()
    st_row = conn.execute('SELECT * FROM students WHERE roll_no=?', (st.session_state.user_id,)).fetchone()
    conn.close()
    if st_row:
        render_college_header("student", st_row)
    else:
        render_college_header("student")
        
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


# ── Semester sync callbacks ─────────────────────────────────
# CRITICAL: callbacks only set selected_sem and delete the OTHER
# widget's key so it re-initialises cleanly from the index param.
# They NEVER touch student navigation state.
def on_sidebar_sem_change():
    new_sem = st.session_state.get('sidebar_sem_select', 'Sem 2')
    st.session_state['selected_sem'] = new_sem
    # Force the result selectbox to reinitialise from selected_sem
    st.session_state.pop('result_sem_select', None)

def on_result_sem_change():
    new_sem = st.session_state.get('result_sem_select', 'Sem 2')
    st.session_state['selected_sem'] = new_sem
    # Force the sidebar selectbox to reinitialise from selected_sem
    st.session_state.pop('sidebar_sem_select', None)

# ── Navigation page callback ─────────────────────────────────
# The nav page is stored SEPARATELY in _current_page so semester
# callbacks can never accidentally reset it.
def on_nav_change():
    st.session_state['_current_page'] = st.session_state.get('_nav_radio_widget', '🏠 Home')


# ══════════════════════════════════════════════════════════════
# STUDENT DASHBOARD
# ══════════════════════════════════════════════════════════════
def student_dashboard():
    # ── Initialise state ──────────────────────────────────────
    roll = st.session_state.user_id
    conn = get_db_connection()
    cfg = get_config_map(conn)
    active_sem = cfg.get('active_semester', 'Sem 2')
    
    if 'selected_sem' not in st.session_state:
        st.session_state['selected_sem'] = active_sem
    if '_current_page' not in st.session_state:
        st.session_state['_current_page'] = '🏠 Home'
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
        st.markdown(f"""
        <div style="background: rgba(10, 14, 26, 0.45); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 12px; margin-bottom: 12px; text-align: center; font-family: 'Outfit';">
            <div style="font-size: 0.72rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">CGPA</div>
            <div style="font-size: 1.85rem; font-weight: 800; color: #ffffff; margin-top: 2px;">{cgpa_display}</div>
        </div>
        """, unsafe_allow_html=True)

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
        try:
            active_num = int(active_sem.replace("Sem ", "").strip())
        except Exception:
            active_num = 2
        _sem_options = [f"Sem {i}" for i in range(1, active_num + 1)]
        _cur_sem = st.session_state.get('selected_sem', active_sem)
        st.selectbox(
            "Viewing Semester",
            _sem_options,
            index=_sem_options.index(_cur_sem) if _cur_sem in _sem_options else len(_sem_options) - 1,
            key="sidebar_sem_select",
            on_change=on_sidebar_sem_change
        )
        st.markdown("---")
        nav_options = [
            "🏠 Home", "📅 Attendance", "📊 Marks", "🧮 SGPA Calculator",
            "📈 Analytics", "🗓️ Timetable"
        ]
        _cur_page = st.session_state.get('_current_page', '🏠 Home')
        if _cur_page not in nav_options:
            _cur_page = '🏠 Home'
            st.session_state['_current_page'] = _cur_page
        # Use a dedicated widget key (_nav_radio_widget) that is separate
        # from _current_page. on_change writes to _current_page.
        st.radio(
            "Navigation",
            nav_options,
            index=nav_options.index(_cur_page),
            key="_nav_radio_widget",
            on_change=on_nav_change
        )
        # page is always read from _current_page – NEVER from the widget
        page = st.session_state.get('_current_page', '🏠 Home')
        st.markdown("---")
        if st.button("📄 Download Report PDF", use_container_width=True):
            generate_student_pdf(student, st.session_state['selected_sem'])
        if st.button("🚪 Logout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    render_college_header("student", student, active_page=page)

    sem = st.session_state['selected_sem']
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
    # Font Import
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
    """.replace('\n', ' '), unsafe_allow_html=True)

    # 1. Calculate Attendance
    total_c = sum((r['hours_conducted'] or 0) for r in att_rows)
    total_a = sum((r['hours_attended']  or 0) for r in att_rows)
    overall = round(total_a / total_c * 100, 1) if total_c else 0.0
    
    # 2. Calculate Credits Earned
    conn = get_db_connection()
    all_final_marks = conn.execute('''
        SELECT subject, score, grade_point FROM marks
        WHERE roll_no=? AND exam_type LIKE '%Final Examinations'
    ''', (student['roll_no'],)).fetchall()
    conn.close()

    completed_credits = 0.0
    for m in all_final_marks:
        sub = m['subject']
        score = m['score']
        gp_val = m['grade_point'] or 0.0
        grade = gp_to_grade(gp_val) if gp_val > 0.0 else ('Ab' if score is None else 'F')
        c_val = get_subject_credits(sub)
        if grade not in ['F', 'Ab']:
            completed_credits += c_val

    # JNTUH GPA scale conversion
    gpa_scale_10 = 0.0
    if cgpa_display != "Pending" and cgpa_display != "-":
        try: gpa_scale_10 = float(cgpa_display)
        except ValueError: pass
    gpa_display_val = f"{gpa_scale_10:.2f}" if gpa_scale_10 > 0 else cgpa_display

    # Calculate backlogs
    backlogs_count = 0
    failed_subjects = []
    for m in all_final_marks:
        sub = m['subject']
        score = m['score']
        gp_val = m['grade_point'] or 0.0
        grade = gp_to_grade(gp_val) if gp_val > 0.0 else ('Ab' if score is None else 'F')
        if grade in ['F', 'Ab']:
            backlogs_count += 1
            failed_subjects.append(sub)

    # Skip Predictor / Status calculations
    can_miss = can_miss_classes(total_a, total_c)
    need = classes_needed(total_a, total_c)
    
    sec = student['section']
    avg_classes = 7.0
    if sec:
        conn = get_db_connection()
        days_count = conn.execute('SELECT COUNT(DISTINCT day) FROM timetable WHERE section=?', (sec,)).fetchone()[0]
        total_periods = conn.execute('SELECT COUNT(*) FROM timetable WHERE section=?', (sec,)).fetchone()[0]
        if days_count > 0:
            avg_classes = total_periods / days_count
        conn.close()

    can_miss_days = round(can_miss / avg_classes, 1) if avg_classes > 0 else 0.0
    need_days = round(need / avg_classes, 1) if avg_classes > 0 else 0.0

    status_text = "SAFE ZONE" if overall >= 75 else "RISK ZONE" if overall >= 65 else "DEBARRED"
    status_color = "#10B981" if overall >= 75 else "#F59E0B" if overall >= 65 else "#EF4444"
    status_icon = "✅" if overall >= 75 else "⚠️" if overall >= 65 else "🚫"

    # Current Semester SGPA
    sem_finals = [r for r in marks_rows if r['exam_type'] == f"{sem} Final Examinations"]
    if sem_finals:
        sgpa_val = compute_sgpa([{'subject': r['subject'], 'grade_point': r['grade_point']} for r in sem_finals if r['score'] is not None])
        sgpa_display_str = f"{sgpa_val:.2f}" if sgpa_val > 0 else "-"
    else:
        sgpa_display_str = "-"

    # Subject Attendance list
    subj_data = []
    for r in att_rows:
        _c = r['hours_conducted'] or 0
        _a = r['hours_attended'] or 0
        _p = round(_a / _c * 100, 1) if _c else 0.0
        subj_data.append({
            'subject': r['subject'], 'conducted': _c,
            'attended': _a, 'pct': _p,
            'absent': _c - _a,
            'can_miss': can_miss_classes(_a, _c),
            'need': classes_needed(_a, _c)
        })

    best_subj = None
    worst_subj = None
    if subj_data:
        best_subj = max(subj_data, key=lambda x: x['pct'])
        worst_subj = min(subj_data, key=lambda x: x['pct'])

    # Welcome Header
    hour = dt.now().hour
    greeting = "Good Morning" if hour < 12 else "Good Afternoon" if hour < 17 else "Good Evening"
    st.markdown(
        f"<div style='margin-bottom:25px;margin-top:5px;'>"
        f"  <h1 style='font-family:Outfit;font-weight:800;font-size:2.5rem;color:#fff;margin:0;letter-spacing:-0.5px;'>{greeting}, {student['name'].split(' ')[0]}! 👋</h1>"
        f"  <div class='greeting-badge-container'>"
        f"    <span class='greeting-badge-pill badge-roll'>🆔 {student['roll_no']}</span>"
        f"    <span class='greeting-badge-pill badge-section'>🏫 SECTION {student['section']}</span>"
        f"    <span class='greeting-badge-pill badge-sem'>📅 {sem.upper()} SUMMARY</span>"
        f"  </div>"
        f"</div>",
        unsafe_allow_html=True
    )

    # 4 KPI ROW CARDS (Cleaned up from st.columns and inline styles to utilize responsive CSS grid)
    is_pending = (cgpa_display == "Pending" or backlogs_count > 0)

    if is_pending:
        gpa_val_display = "Pending"
        gpa_font_size_class = "val-dynamic"
    else:
        gpa_val_display = f"{gpa_display_val} / {sgpa_display_str}"
        gpa_font_size_class = "val-dynamic" if len(gpa_val_display) > 6 else ""

    val_inner = gpa_scale_10 / 10.0 if gpa_scale_10 > 0 else 0.0
    inner_label = "CGPA / SGPA"
    inner_val_text = f"{gpa_display_val} / {sgpa_display_str}" if not is_pending else "Pending"

    credits_display = f"{completed_credits:.0f}" if completed_credits.is_integer() else f"{completed_credits:.1f}"

    if backlogs_count > 0:
        short_subs = [s[:12] + ".." if len(s) > 12 else s for s in failed_subjects]
        display_subs = short_subs[:3]
        sub_stack_html = "<div style='display:flex; flex-direction:column; gap:3px; margin:4px 0;'>"
        for s in display_subs:
            sub_stack_html += f"  <div style='font-size:1.0rem; font-weight:800; color:#EF4444; line-height:1.2;'>• {s.upper()}</div>"
        if len(short_subs) > 3:
            sub_stack_html += f"  <div style='color:#64748b; font-size:0.75rem; font-weight:600;'>+ {len(short_subs) - 3} more</div>"
        else:
            sub_stack_html += f"  <div style='font-size:0.8rem; color:#64748b; font-weight:500;'>{backlogs_count} backlog(s)</div>"
        sub_stack_html += "</div>"

        backlog_card_html = (
            f'<div class="kpi-card kpi-card-backlog">'
            f'  <div class="kpi-card-content">'
            f'    <div class="kpi-card-title text-red">BACKLOGS</div>'
            f'    {sub_stack_html}'
            f'  </div>'
            f'  <div class="kpi-card-icon text-red">⚠️</div>'
            f'</div>'
        )
    else:
        backlog_card_html = (
            f'<div class="kpi-card kpi-card-subjects">'
            f'  <div class="kpi-card-content">'
            f'    <div class="kpi-card-title">SUBJECTS</div>'
            f'    <div class="kpi-card-val text-orange">{len(att_rows)}</div>'
            f'    <div class="kpi-card-sub">{backlogs_count} backlog(s)</div>'
            f'  </div>'
            f'  <div class="kpi-card-icon">📚</div>'
            f'</div>'
        )

    gpa_title = "CGPA / SGPA"
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card kpi-card-attendance">
            <div class="kpi-card-content">
                <div class="kpi-card-title">OVERALL ATTENDANCE</div>
                <div class="kpi-card-val text-teal">{overall}%</div>
                <div class="kpi-card-sub">{total_a}/{total_c} hrs attended</div>
            </div>
            <div class="kpi-card-icon text-green">↑</div>
        </div>
        <div class="kpi-card kpi-card-gpa">
            <div class="kpi-card-content">
                <div class="kpi-card-title">{gpa_title}</div>
                <div class="kpi-card-val text-white {gpa_font_size_class}">{gpa_val_display}</div>
                <div class="kpi-card-sub">academic performance</div>
            </div>
            <div class="kpi-card-icon text-purple">🎓</div>
        </div>
        <div class="kpi-card kpi-card-credits">
            <div class="kpi-card-content">
                <div class="kpi-card-title">CREDITS EARNED</div>
                <div class="kpi-card-val text-emerald">{credits_display}</div>
                <div class="kpi-card-sub">credits completed</div>
            </div>
            <div class="kpi-card-icon text-emerald">⚡</div>
        </div>
        {backlog_card_html}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

    # Status banner (glowing card below KPI cards)
    if total_c == 0:
        st.info("🔍 No attendance data yet for this semester. Visit the Attendance tab to sync.")
    elif overall >= 75:
        st.markdown(f"""
        <div class="status-banner" style="background:rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); 
                    box-shadow: 0 0 25px rgba(16, 185, 129, 0.12); margin-bottom: 25px;">
            <h3 style="color:#10B981 !important;margin:0;font-family:'Outfit';font-weight:700;font-size:1.2rem;display:flex;align-items:center;gap:8px;">
                <span>🟢</span> Safe Zone
            </h3>
            <p style="margin:8px 0 0 0;color:#cbd5e1 !important;font-size:0.92rem;line-height:1.4;font-family:'Inter';">
                Current Attendance: <strong style="color:#fff;">{overall}%</strong>. 
                You can miss <strong style="color:#10B981;font-weight:700;">{can_miss}</strong> more classes (approx. <strong style="color:#10B981;font-weight:700;">{can_miss_days}</strong> days) and stay above the 75% threshold.
            </p>
        </div>
        """, unsafe_allow_html=True)
    elif overall >= 65:
        st.markdown(f"""
        <div class="status-banner" style="background:rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.25); 
                    box-shadow: 0 0 25px rgba(245, 158, 11, 0.12); margin-bottom: 25px;">
            <h3 style="color:#F59E0B !important;margin:0;font-family:'Outfit';font-weight:700;font-size:1.2rem;display:flex;align-items:center;gap:8px;">
                <span>🟠</span> Risk Zone
            </h3>
            <p style="margin:8px 0 0 0;color:#cbd5e1 !important;font-size:0.92rem;line-height:1.4;font-family:'Inter';">
                Current Attendance: <strong style="color:#fff;">{overall}%</strong>. 
                Attend <strong style="color:#F59E0B;font-weight:700;">{need}</strong> consecutive classes (approx. <strong style="color:#F59E0B;font-weight:700;">{need_days}</strong> days) to reach the 75% target.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="status-banner" style="background:rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.25); 
                    box-shadow: 0 0 25px rgba(239, 68, 68, 0.12); margin-bottom: 25px;">
            <h3 style="color:#EF4444 !important;margin:0;font-family:'Outfit';font-weight:700;font-size:1.2rem;display:flex;align-items:center;gap:8px;">
                <span>🔴</span> Debarred Zone
            </h3>
            <p style="margin:8px 0 0 0;color:#cbd5e1 !important;font-size:0.92rem;line-height:1.4;font-family:'Inter';">
                Current Attendance: <strong style="color:#fff;">{overall}%</strong>. 
                You need <strong style="color:#EF4444;font-weight:700;">{need}</strong> classes (approx. <strong style="color:#EF4444;font-weight:700;">{need_days}</strong> days) to recover to the 75% requirement.
            </p>
        </div>
        """, unsafe_allow_html=True)

    # SPLIT COLUMNS (Circular meter + Subject Health + Weekly Timetable)
    col_l, col_m, col_r = st.columns([1.3, 1.4, 1.2])

    with col_l:
        val_outer = overall / 100.0 if overall > 0 else 0.78

        st.markdown(f"""
        <div class="circular-progress-card">
            <div class="circular-svg-wrapper">
                <svg class="circular-svg" viewBox="0 0 160 160">
                    <!-- Outer Ring: Attendance (Teal) -->
                    <circle cx="80" cy="80" r="65" fill="none" stroke="rgba(255,255,255,0.03)" stroke-width="9"/>
                    <circle cx="80" cy="80" r="65" fill="none" stroke="#00D8C6" stroke-width="9"
                            stroke-dasharray="408.4" stroke-dashoffset="{408.4 * (1 - val_outer)}" stroke-linecap="round" transform="rotate(-90 80 80)"/>
                    
                    <!-- Inner Ring: Academic Performance (GPA - Purple) -->
                    <circle cx="80" cy="80" r="50" fill="none" stroke="rgba(255,255,255,0.03)" stroke-width="9"/>
                    <circle cx="80" cy="80" r="50" fill="none" stroke="#8B5CF6" stroke-width="9"
                            stroke-dasharray="314.16" stroke-dashoffset="{314.16 * (1 - val_inner)}" stroke-linecap="round" transform="rotate(-90 80 80)"/>
                </svg>
                <div class="circular-inner-text">
                    <div style="font-family: 'Outfit'; font-size: 2.2rem; font-weight: 800; color: #fff; line-height: 1;">{overall}%</div>
                    <div style="font-family: 'Inter'; font-size: 0.65rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px;">Attendance</div>
                </div>
            </div>
            <div class="circular-legend">
                <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#00D8C6; margin-right:5px;"></span>Attendance &nbsp;&nbsp;&nbsp; 
                <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#8B5CF6; margin-right:5px;"></span>{inner_label} ({inner_val_text})
            </div>
        </div>
        """.replace('\n', ' '), unsafe_allow_html=True)

        if best_subj:
            st.markdown(f"""
            <div style="background: rgba(16, 185, 129, 0.06); border: 1px solid rgba(16, 185, 129, 0.15); border-radius: 12px; padding: 15px; margin-top: 15px; font-family: 'Outfit';">
                <div style="font-size: 0.75rem; color: #10B981; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Best Subject 🏆</div>
                <div style="font-size: 1.15rem; font-weight: 800; color: #ffffff; margin-top: 4px;">{best_subj['subject']}</div>
                <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 2px;">{best_subj['attended']}/{best_subj['conducted']} hrs - <span style="color: #10B981; font-weight: bold;">{best_subj['pct']}%</span></div>
            </div>
            """, unsafe_allow_html=True)

        if worst_subj:
            st.markdown(f"""
            <div style="background: rgba(239, 68, 68, 0.06); border: 1px solid rgba(239, 68, 68, 0.15); border-radius: 12px; padding: 15px; margin-top: 12px; font-family: 'Outfit';">
                <div style="font-size: 0.75rem; color: #EF4444; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Needs Attention ⚠️</div>
                <div style="font-size: 1.15rem; font-weight: 800; color: #ffffff; margin-top: 4px;">{worst_subj['subject']}</div>
                <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 2px;">{worst_subj['attended']}/{worst_subj['conducted']} hrs - <span style="color: #EF4444; font-weight: bold;">{worst_subj['pct']}%</span></div>
            </div>
            """, unsafe_allow_html=True)

    with col_m:
        if not subj_data:
            st.markdown(
                "<div style='background:rgba(10, 14, 26, 0.45); border:1px solid rgba(255,255,255,0.05); border-radius:16px; padding:30px; text-align:center; color:#64748b;'>No subject details available.</div>",
                unsafe_allow_html=True
            )
        else:
            health_html = (
                "<div class='subject-health-card'>"
                "<div style=\"font-family: 'Outfit'; font-weight: 700; font-size: 0.95rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 15px;\">Subject Health</div>"
            )
            for s in sorted(subj_data, key=lambda x: x['pct']):
                pct = s['pct']
                bar_color = "#10B981" if pct >= 75 else "#F59E0B" if pct >= 65 else "#EF4444"
                status_char = "✓" if pct >= 75 else "⚠️" if pct >= 65 else "🚫"
                absent_hrs = s['conducted'] - s['attended']
                subj_label = s['subject']
                
                health_html += (
                    f"<div style='margin-bottom: 15px; font-family: \"Inter\";'>"
                    f"  <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;'>"
                    f"    <span style='font-size: 0.85rem; font-weight: 700; color: #ffffff;'>{subj_label}</span>"
                    f"    <span style='font-size: 0.8rem; color: {bar_color}; font-weight: 700;'>{status_char} {pct}%</span>"
                    f"  </div>"
                    f"  <div style='background: rgba(255,255,255,0.06); border-radius: 999px; height: 7px; overflow: hidden; width: 100%;'>"
                    f"    <div style='width: {min(pct, 100)}%; height: 100%; background: {bar_color}; border-radius: 999px;'></div>"
                    f"  </div>"
                    f"  <div style='font-size: 0.7rem; color: #64748b; margin-top: 3px;'>{s['attended']}/{s['conducted']} hrs · {absent_hrs} absent</div>"
                    f"</div>"
                )
            health_html += "</div>"
            st.markdown(health_html.replace('\n', ' '), unsafe_allow_html=True)

    with col_r:
        st.markdown(
            "<div style='font-family:Outfit;font-weight:700;font-size:0.95rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:15px;'>"
            "📅 Daily Schedule"
            "</div>",
            unsafe_allow_html=True
        )
        
        today_day = dt.now().strftime('%a')
        days_list = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        default_idx = days_list.index(today_day) if today_day in days_list else 0
        
        selected_day = st.selectbox("View Day", days_list, index=default_idx, label_visibility="collapsed", key=f"schedule_day_home_{sem}")
        
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
        
        schedule_html = "<div class='daily-schedule-card'>"
        if day_classes:
            for idx, c in enumerate(day_classes):
                t_range = times_map.get(c['period'], "Class Period")
                border_color = "#00D8C6" if idx == 0 else "#8B5CF6" if idx == 1 else "rgba(255,255,255,0.15)"
                schedule_html += f"""
                <div style="background: rgba(20, 28, 48, 0.45); border: 1px solid rgba(255, 255, 255, 0.05); 
                             border-left: 3px solid {border_color}; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;
                             display: flex; justify-content: space-between; align-items: center;">
                     <div style="font-size: 0.85rem; font-weight: 700; color: #fff; font-family: 'Outfit';">
                         {c['subject']}
                     </div>
                     <div style="font-size: 0.65rem; color: #94a3b8; font-family: 'JetBrains Mono'; font-weight: 500; text-align: right;">
                         P{c['period']}<br/><span style="color:#64748b;font-size:0.6rem;">{t_range}</span>
                     </div>
                 </div>
                 """
        else:
            schedule_html += "<div style='color:#64748b;text-align:center;padding-top:180px;font-family:Inter;font-size:0.85rem;'>🎉 No classes scheduled for this day!</div>"
        schedule_html += "</div>"
        st.markdown(schedule_html.replace('\n', ' '), unsafe_allow_html=True)

    # ── Middle Section: Attendance Predictor + Bar Graph (Full Width) ──
    st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
    st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.06);margin:15px 0 25px 0;'>", unsafe_allow_html=True)
    
    # 1. Skip Predictor (Reverted back to big/full-width)
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

    # 2. Plotly Bar Graph (Reverted back)
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;
                letter-spacing:0.12em;font-weight:600;margin-bottom:8px;font-family:'Inter';">
        Subject Attendance Chart
    </div>""", unsafe_allow_html=True)
    if subj_data:
        df_bar = pd.DataFrame(subj_data)
        fig = px.bar(df_bar, x='subject', y='pct', color='pct',
                     color_continuous_scale=[[0, '#EF4444'], [0.65, '#F59E0B'], [0.75, '#00D8C6'], [1, '#00D8C6']],
                     range_color=[0, 100], labels={'pct': 'Attendance %', 'subject': 'Subject'})
        fig.add_hline(y=75, line_dash="dash", line_color="#10B981", annotation_text="75% target")
        fig.add_hline(y=65, line_dash="dash", line_color="#F59E0B", annotation_text="65% min")
        fig.update_layout(height=380, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                          margin=dict(t=10, b=10))
        fig.update_coloraxes(showscale=False)
        apply_premium_plotly_theme(fig)
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": False, "doubleClick": "reset+autosize", "displayModeBar": True})
    else:
        st.markdown("""
        <div style="background:rgba(255,255,255,0.02);border:1px dashed rgba(255,255,255,0.05);
                    border-radius:12px;padding:30px;text-align:center;color:#64748b;font-size:0.95rem;font-family:'Inter';">
            No attendance data available to display chart.
        </div>
        """, unsafe_allow_html=True)

    # ── Bottom Section: Grades Table + Cloud Resources Link ──
    st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
    st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.06);margin:15px 0 25px 0;'>", unsafe_allow_html=True)

    col_bl, col_br = st.columns([1.8, 1.2])
    with col_bl:
        st.markdown("### 📝 Exam & Assignment Grades")
        sem_final_marks = [r for r in marks_rows if r['exam_type'] == f"{sem} Final Examinations"]
        if sem_final_marks:
            grades_df = pd.DataFrame([{
                'Subject': r['subject'],
                'Exam Type': r['exam_type'].replace(f"{sem} ", ""),
                'Score': r['score'] if r['score'] is not None else 'Ab',
                'Grade': gp_to_grade(r['grade_point']) if (r['grade_point'] or 0.0) > 0.0 else ('Ab' if r['score'] is None else 'F'),
                'Credits': get_subject_credits(r['subject'])
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

    with col_br:
        st.markdown(f"""
        <div class="cloud-resources-card">
            <div style="font-size: 2rem; margin-bottom: 8px;">📂</div>
            <h4 style="margin: 0; color: #ffffff; font-family: 'Outfit', sans-serif; font-size: 1.05rem; font-weight: 700;">Cloud Resources</h4>
            <p style="margin: 6px 0 0 0; font-size: 0.8rem; color: #94a3b8; line-height: 1.3;">Access lecture slides, textbook PDF drives, syllabus copies, and previous lab materials.</p>
        </div>
        """.replace('\n', ' '), unsafe_allow_html=True)
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        st.link_button("📂 Open Cloud Drive", "https://drive.google.com/drive/folders/1bInXkRc9mQFdbVbUMNxG1VVnrpKEyoPN?usp=drive_link", use_container_width=True)



def show_attendance_page(roll, sem, att_rows):
    st.markdown("## 📅 Attendance Overview")
    if not att_rows:
        st.info("🔍 No attendance records found for this semester.")
        return
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
    fig.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', dragmode=False)
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": False, "doubleClick": "reset+autosize", "displayModeBar": True})

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
    conn = get_db_connection()
    cfg = get_config_map(conn)
    conn.close()
    active_sem = cfg.get('active_semester', 'Sem 2')
    try:
        active_num = int(active_sem.replace("Sem ", "").strip())
    except Exception:
        active_num = 2
    _sem_options = [f"Sem {i}" for i in range(1, active_num + 1)]
    _cur_sem = st.session_state.get('selected_sem', active_sem)
    col_title, col_sem = st.columns([3.5, 1.5])
    with col_title:
        st.markdown("## 📊 Academic Results")
    with col_sem:
        st.selectbox(
            "Semester",
            _sem_options,
            index=_sem_options.index(_cur_sem) if _cur_sem in _sem_options else len(_sem_options) - 1,
            key="result_sem_select",
            label_visibility="collapsed",
            on_change=on_result_sem_change
        )
    by_exam = {}
    if marks_rows:
        for r in marks_rows:
            is_final = "Final" in r['exam_type']
            if is_final:
                gp_val = r['grade_point'] or 0.0
                grade = gp_to_grade(gp_val) if gp_val > 0.0 else ('Ab' if r['score'] is None else 'F')
            else:
                grade, gp_val = '-', '-'
            by_exam.setdefault(r['exam_type'], []).append({
                'Subject': r['subject'],
                'Score': r['score'] if r['score'] is not None else 'Ab',
                'Grade': grade, 'GP': gp_val,
                'Credits': get_subject_credits(r['subject'])
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
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": False, "doubleClick": "reset+autosize", "displayModeBar": True})

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
        cr = get_subject_credits(sub)
        if cr == 0:
            continue
        # Default to 0 for projections if no actual score exists
        default_val = int(actual_scores[sub]) if sub in actual_scores and actual_scores[sub] is not None else 0
        projected[sub] = st.slider(f"{sub} ({cr} cr)", 0, 100, default_val, key=f"sgpa_{sem}_{sub}")

    total_cr, weighted = 0.0, 0.0
    for subj, score in projected.items():
        cr = get_subject_credits(subj)
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
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": False, "doubleClick": "reset+autosize", "displayModeBar": True})

    st.markdown("### 🔥 Absenteeism Heatmap")
    pivot = df.pivot_table(index='subject_code', columns='snapshot_date',
                            values='percentage', aggfunc='last')
    fig2 = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns.astype(str), y=pivot.index,
        colorscale=[[0, '#1E293B'], [0.5, '#EF4444'], [0.75, '#F59E0B'], [1, '#00D8C6']],
        zmin=0, zmax=100, xgap=4, ygap=4, colorbar={'title': '%'}))
    apply_premium_plotly_theme(fig2)
    st.plotly_chart(fig2, use_container_width=True, config={"scrollZoom": False, "doubleClick": "reset+autosize", "displayModeBar": True})

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
        
    attendance_semester = sem
    if not att:
        other_sems = conn.execute(
            'SELECT DISTINCT semester FROM attendance WHERE roll_no=?', (roll,)).fetchall()
        for os_row in other_sems:
            osem = os_row['semester']
            alt_att = conn.execute(
                'SELECT subject,hours_attended,hours_conducted FROM attendance WHERE roll_no=? AND semester=?',
                (roll, osem)).fetchall()
            if alt_att:
                att = alt_att
                attendance_semester = osem
                break

    marks = conn.execute(
        'SELECT subject,score,grade_point,exam_type FROM marks WHERE roll_no=? AND semester=?',
        (roll, sem)).fetchall()
    cgpa = compute_cgpa(roll, conn)
    conn.close()
    marks_by_type = {}
    for r in marks:
        gp_val = r['grade_point'] or 0.0
        grade = gp_to_grade(gp_val) if gp_val > 0.0 else ('Ab' if r['score'] is None else 'F')
        marks_by_type.setdefault(r['exam_type'], []).append({
            'subject': r['subject'], 'score': r['score'],
            'grade_point': r['grade_point'], 'grade': grade})
    finals = marks_by_type.get(f"{sem} Final Examinations", [])
    sgpa = compute_sgpa([{'subject': r['subject'], 'grade_point': r['grade_point']}
                         for r in finals if r['score'] is not None])
    buf = pdf_generator.generate_report_pdf(dict(student), att, marks_by_type, sgpa, cgpa, semester=sem, attendance_semester=attendance_semester)
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
        admin_options = [
            "🏠 Dashboard", "👥 Students", "📝 Marks Editor",
            "📤 CSV Upload", "🔄 Scraper",
            "📈 Analytics", "🚨 Bunk Analysis", "🗓️ Timetable", "💾 Backup", "⚙️ Settings"
        ]
        default_admin = "🏠 Dashboard"
        current_admin = st.session_state.get('admin_nav_page', default_admin)
        if current_admin not in admin_options:
            current_admin = default_admin
        page = st.radio(
            "Navigation", 
            admin_options, 
            index=admin_options.index(current_admin),
            key="admin_nav_page"
        )
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    render_college_header("admin", active_page=page)

    pages = {
        "🏠 Dashboard": admin_overview,
        "👥 Students": admin_students,
        "📝 Marks Editor": admin_marks,
        "📤 CSV Upload": admin_csv_upload,
        "🔄 Scraper": admin_scraper,
        "📈 Analytics": admin_analytics,
        "🚨 Bunk Analysis": admin_bunk_analysis,
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

    c1, c2 = st.columns([2, 1])
    section_filter = c1.selectbox("Filter by Section", ['All'] + CLASSES)
    search = c2.text_input("Search (roll/name)")

    conn = get_db_connection()
    sql = 'SELECT * FROM students WHERE 1=1'; params = []
    if section_filter != 'All':
        sql += ' AND section=?'; params.append(section_filter)
    if search:
        sql += ' AND (UPPER(roll_no) LIKE ? OR UPPER(name) LIKE ?)'
        s = f'%{search.upper()}%'; params.extend([s, s])
    sql += ''' ORDER BY 
        CASE WHEN dob IS NOT NULL AND dob != 'PENDING' AND dob != '2007-01-01' AND dob != '' THEN 0 ELSE 1 END ASC,
        section ASC, 
        roll_no ASC 
        LIMIT 200'''
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    display_df = pd.DataFrame()
    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        df['DOB Set'] = df['dob'].apply(lambda d: '⚠️ Pending' if d in ('PENDING', '2007-01-01') else '✅ Set')
        df['DOB'] = pd.to_datetime(df['dob'], errors='coerce').dt.date
        df['Reset'] = False
        display_df = df[['roll_no', 'name', 'section', 'branch', 'DOB Set', 'DOB', 'Reset']].rename(columns={
            'roll_no': 'Roll Number', 'name': 'Name',
            'section': 'Section', 'branch': 'Branch', 'DOB Set': 'Status', 'DOB': 'DOB', 'Reset': 'Reset'
        })

    def on_student_edit():
        if "student_editor" not in st.session_state:
            return
        edits = st.session_state["student_editor"].get("edited_rows", {})
        if not edits or display_df.empty:
            return
            
        conn = get_db_connection()
        updated = False
        for row_idx_str, changes in edits.items():
            row_idx = int(row_idx_str)
            if row_idx >= len(display_df):
                continue
            roll_no = display_df.iloc[row_idx]["Roll Number"]
            
            if "Reset" in changes and changes["Reset"] is True:
                conn.execute('UPDATE students SET dob=? WHERE roll_no=?', ('PENDING', roll_no))
                updated = True
            elif "DOB" in changes:
                new_dob = changes["DOB"]
                if new_dob is None or pd.isna(new_dob):
                    dob_val = 'PENDING'
                else:
                    dob_val = new_dob.strftime('%Y-%m-%d') if hasattr(new_dob, "strftime") else str(new_dob)
                conn.execute('UPDATE students SET dob=? WHERE roll_no=?', (dob_val, roll_no))
                updated = True
        if updated:
            conn.commit()
        conn.close()

    if not display_df.empty:
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
            hide_index=True,
            on_change=on_student_edit
        )
        st.caption(f"Showing {len(display_df)} students (max 200) · 💡 Edits auto-save instantly.")
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

    with st.expander("🗑️ Delete Student"):
        with st.form("delete_student"):
            del_roll = st.text_input("Roll Number to Delete").strip().upper()
            confirm  = st.checkbox("I confirm I want to permanently delete this student and all their data")
            if st.form_submit_button("🗑️ Delete Student", type="primary"):
                if not del_roll:
                    st.error("Enter a roll number.")
                elif not confirm:
                    st.warning("Check the confirmation box to proceed.")
                else:
                    conn = get_db_connection()
                    exists = conn.execute("SELECT roll_no FROM students WHERE roll_no=?", (del_roll,)).fetchone()
                    if not exists:
                        st.error(f"Roll number {del_roll} not found.")
                    else:
                        conn.execute("DELETE FROM attendance WHERE roll_no=?",  (del_roll,))
                        conn.execute("DELETE FROM marks WHERE roll_no=?",       (del_roll,))
                        conn.execute("DELETE FROM sgpa_records WHERE roll_no=?",(del_roll,))
                        conn.execute("DELETE FROM students WHERE roll_no=?",    (del_roll,))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Student {del_roll} and all their records deleted.")
                        st.rerun()


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
    st.markdown("# 📤 CSV Upload Center")

    csv_format = st.radio(
        "CSV Format",
        ["📝 Internal Marks CSV", "🎓 JNTU Results CSV"],
        horizontal=True
    )
    st.markdown("---")

    # ── Shared selectors ──────────────────────────────────────
    conn = get_db_connection()
    cfg  = get_config_map(conn)
    conn.close()
    active_sem = cfg.get('active_semester', 'Sem 2')
    try:
        active_idx = [f"Sem {i}" for i in range(1, 9)].index(active_sem)
    except ValueError:
        active_idx = 1

    c1, c2, c3 = st.columns(3)
    sem     = c1.selectbox("Semester", [f"Sem {i}" for i in range(1, 9)], index=active_idx, key="u_sem")
    section = c2.selectbox("Section", CLASSES, key="u_section")

    if "Internal" in csv_format:
        exam = c3.selectbox("Exam Type", ['Mid 1', 'Mid 2', 'Lab Internals'], key="u_exam")
        st.caption("Format: `roll_no, SUBJECT1, SUBJECT2, ...`")
        uploaded = st.file_uploader("Upload Marks CSV", type=['csv'], key="u_file")

        if uploaded:
            df = pd.read_csv(uploaded)
            df.columns = [c.strip() for c in df.columns]
            roll_col, name_col, subject_cols = resolve_csv_columns(df)

            if not roll_col:
                st.error("Could not detect Roll Number column.")
            elif not subject_cols:
                st.error("No subject columns detected.")
            else:
                st.info(f"Detected — Roll: **`{roll_col}`** | Name: **`{name_col or 'None'}`** | Subjects: {subject_cols}")
                st_premium_table(df.head())

                if st.button("📤 Import Marks", use_container_width=True, key="btn_marks"):
                    try:
                        sem_num = int(sem.replace("Sem", "").strip())
                    except Exception:
                        sem_num = 2
                    conn = get_db_connection()
                    count = 0
                    with st.spinner("Importing..."):
                        for _, row in df.iterrows():
                            roll = str(row.get(roll_col, '')).strip().upper()
                            if not roll:
                                continue
                            existing = conn.execute('SELECT name FROM students WHERE roll_no=?', (roll,)).fetchone()
                            branch = decode_roll_branch(roll) or 'ECE'
                            sname  = str(row.get(name_col, f"Student {roll}")).strip() if name_col else f"Student {roll}"
                            if not existing:
                                conn.execute('''
                                    INSERT INTO students(roll_no,name,dob,semester,branch,department,section)
                                    VALUES(?,?,'PENDING',?,?,?,?)
                                ''', (roll, sname, sem_num, branch, branch, section))
                            else:
                                conn.execute('UPDATE students SET section=? WHERE roll_no=?', (section, roll))
                                if name_col and sname:
                                    conn.execute('UPDATE students SET name=? WHERE roll_no=?', (sname, roll))
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
                    st.success(f"✅ Imported {count} mark entries.")

    else:  # JNTU Results
        exam_type = "Final Examinations"
        c3.markdown("<div style='padding-top:28px;font-size:0.85rem;color:#10B981;font-weight:600;'>✅ Final Examinations</div>", unsafe_allow_html=True)
        st.caption("Format: `Hall no, Name, SUB1 [Total,GP], SUB2 [Total,GP], ..., SGPA`")
        uploaded = st.file_uploader("Upload JNTU Results CSV", type=['csv'], key="u_file")

        if uploaded and st.button("📥 Import JNTU Results", use_container_width=True, key="btn_jntu"):
            try:
                sem_num = int(sem.replace("Sem", "").strip())
            except Exception:
                sem_num = 2
            db_exam = f"{sem} Final Examinations" if exam_type == 'Final Examinations' else exam_type
            content = uploaded.read().decode('utf-8')
            parsed  = parse_sem1_results_csv(content)
            conn = get_db_connection()
            marks_count = sgpa_count = 0
            with st.spinner(f"Importing {len(parsed)} records..."):
                for record in parsed:
                    roll   = record['roll_no']
                    branch = decode_roll_branch(roll) or 'ECE'
                    conn.execute('''
                        INSERT INTO students(roll_no,name,dob,semester,branch,department,section)
                        VALUES(?,?,'PENDING',?,?,?,?)
                        ON CONFLICT(roll_no) DO UPDATE SET name=excluded.name, section=excluded.section
                    ''', (roll, record['name'], sem_num, branch, branch, section))
                    for subj, data in record['subjects'].items():
                        if data['total'] is not None:
                            conn.execute('''
                                INSERT INTO marks(roll_no,subject,semester,exam_type,score,grade_point)
                                VALUES(?,?,?,?,?,?)
                                ON CONFLICT(roll_no,subject,semester,exam_type) DO UPDATE SET
                                    score=excluded.score, grade_point=excluded.grade_point
                            ''', (roll, subj, sem, db_exam, data['total'], data['gp']))
                            marks_count += 1
                    if exam_type == 'Final Examinations':
                        conn.execute('''
                            INSERT INTO sgpa_records(roll_no,semester,sgpa,failed)
                            VALUES(?,?,?,?)
                            ON CONFLICT(roll_no,semester) DO UPDATE SET
                                sgpa=excluded.sgpa, failed=excluded.failed
                        ''', (roll, sem, record['sgpa'], 1 if record['failed'] else 0))
                        sgpa_count += 1
                conn.commit()
            conn.close()
            if exam_type == 'Final Examinations':
                st.success(f"✅ Imported {sgpa_count} students (SGPA) + {marks_count} marks for {sem}.")
            else:
                st.success(f"✅ Imported {marks_count} mark entries ({exam_type}) for {sem}.")


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
    ist_now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    ed = c2.date_input("To", value=ist_now.date())

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
        fig.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', dragmode=False)
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": False, "doubleClick": "reset+autosize", "displayModeBar": True})

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


def admin_bunk_analysis():
    st.markdown("# 🚨 Bunk Intelligence Dashboard")
    st.markdown("<p style='color:#94a3b8;font-size:1.05rem;margin-bottom:20px;'>College-wide bunk intelligence — accurate per-student normalised metrics, subject drill-down, debarment recovery tracker & pattern analysis.</p>", unsafe_allow_html=True)

    conn = get_db_connection()
    cfg  = get_config_map(conn)
    sem  = cfg.get('active_semester', 'Sem 3')

    # ── Filters ────────────────────────────────────────────────
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        sec_filter = st.selectbox("Drilldown Section", ["All Sections"] + CLASSES)
    with col_f2:
        threshold = st.slider("Debarment Alert Threshold (%)", 30, 90, 75, 5,
                              help="Flag students whose overall attendance is below this %.")

    # ── Create Tabs ────────────────────────────────────────────
    tab_debarment, tab_patterns = st.tabs(["📋 Attendance & Debarment Tracker", "🕵️ Intermittent Bunking Patterns"])

    # ── WHERE helpers ───────────────────────────────────────────
    sec_join  = "JOIN students s ON a.roll_no = s.roll_no" if sec_filter != "All Sections" else ""
    sec_where = "AND s.section = ?" if sec_filter != "All Sections" else ""
    params_s  = (sem, sec_filter) if sec_filter != "All Sections" else (sem,)

    # ═══════════════════════════════════════════════════════════
    # TAB 1: ATTENDANCE & DEBARMENT TRACKER
    # ═══════════════════════════════════════════════════════════
    with tab_debarment:
        student_sql = f"""
            SELECT
                a.roll_no,
                SUM(a.hours_conducted)                                          AS cond,
                SUM(a.hours_attended)                                           AS att,
                SUM(a.hours_conducted) - SUM(a.hours_attended)                  AS missed,
                ROUND(SUM(a.hours_attended)*100.0/NULLIF(SUM(a.hours_conducted),0),2) AS pct
            FROM attendance a
            {sec_join}
            WHERE a.semester = ? {sec_where}
              AND a.hours_conducted > 0
            GROUP BY a.roll_no
        """
        student_rows = conn.execute(student_sql, params_s).fetchall()

        if not student_rows:
            st.warning(f"No attendance data found for {sem}. Run the scraper or import CSVs first!")
        else:
            df_stu = pd.DataFrame([dict(r) for r in student_rows])
            total_students      = len(df_stu)
            avg_attendance      = round(df_stu['pct'].mean(), 1)
            total_missed        = int(df_stu['missed'].sum())
            total_cond          = int(df_stu['cond'].sum())
            zero_bunk_count     = int((df_stu['missed'] == 0).sum())
            chronic_count       = int((df_stu['pct'] < threshold).sum())
            bunk_rate           = round(100 - avg_attendance, 2)

            # ── KPI Cards ──────────────────────────────────────────────
            def kpi(label, value, color="#f8fafc"):
                return f"""<div style="background:linear-gradient(135deg,#1e293b,#0f172a);border:1px solid #334155;
                    border-radius:14px;padding:20px;text-align:center;box-shadow:0 4px 6px -1px rgba(0,0,0,.1);">
                    <div style="font-size:.75rem;text-transform:uppercase;color:#94a3b8;font-weight:600;letter-spacing:.07em;">{label}</div>
                    <div style="font-size:1.9rem;font-weight:700;color:{color};margin-top:6px;font-family:'Outfit';">{value}</div>
                </div>"""

            st.markdown(f"""
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:24px;">
                {kpi("Total Students",    f"{total_students:,}")}
                {kpi("Avg Attendance",    f"{avg_attendance}%",   "#00D8C6")}
                {kpi("Classes Missed",    f"{total_missed:,}",    "#ef4444")}
                {kpi("Overall Bunk Rate", f"{bunk_rate}%",        "#f59e0b")}
                {kpi("Perfect Attendance",f"{zero_bunk_count}",   "#10b981")}
                {kpi("Debarment Risk",    f"{chronic_count}",     "#f43f5e")}
            </div>""", unsafe_allow_html=True)

            st.markdown("---")

            # ── Charts Row 1 ────────────────────────────────────────────
            c1, c2 = st.columns(2)

            with c1:
                if sec_filter == "All Sections":
                    st.markdown("### 📊 Class Bunk Leaderboard")
                    cls_sql = """
                        SELECT s.section,
                               ROUND(AVG(stu.pct), 1)             AS avg_att,
                               ROUND(100 - AVG(stu.pct), 1)       AS avg_bunk_rate,
                               SUM(stu.missed)                     AS total_missed,
                               COUNT(DISTINCT a.roll_no)           AS students
                        FROM attendance a
                        JOIN students s ON a.roll_no = s.roll_no
                        JOIN (
                            SELECT roll_no,
                                   SUM(hours_attended)*100.0/NULLIF(SUM(hours_conducted),0) AS pct,
                                   SUM(hours_conducted - hours_attended) AS missed
                            FROM attendance
                            WHERE semester = ?
                            GROUP BY roll_no
                        ) stu ON stu.roll_no = a.roll_no
                        WHERE a.semester = ?
                        GROUP BY s.section
                        ORDER BY avg_bunk_rate DESC
                    """
                    cls_rows = conn.execute(cls_sql, (sem, sem)).fetchall()
                    if cls_rows:
                        df_cls = pd.DataFrame([dict(r) for r in cls_rows])
                        fig_cls = px.bar(
                            df_cls, x='section', y='total_missed',
                            color='avg_bunk_rate',
                            color_continuous_scale=[[0,'#4ade80'],[0.5,'#f59e0b'],[1,'#ef4444']],
                            custom_data=['avg_att', 'avg_bunk_rate', 'students'],
                            labels={'section':'Section','total_missed':'Total Missed Classes','avg_bunk_rate':'Avg Bunk Rate (%)'}
                        )
                        fig_cls.update_traces(
                            hovertemplate="<b>%{x}</b><br>Missed: %{y}<br>Avg Attendance: %{customdata[0]}%<br>Avg Bunk Rate: %{customdata[1]}%<br>Students: %{customdata[2]}<extra></extra>"
                        )
                        apply_premium_plotly_theme(fig_cls)
                        st.plotly_chart(fig_cls, use_container_width=True)
                    else:
                        st.info("No section data found.")
                else:
                    st.markdown(f"### 📊 Top Bunkers — {sec_filter}")
                    top_sql = """
                        SELECT s.name, s.roll_no,
                               SUM(a.hours_conducted - a.hours_attended) AS missed,
                               ROUND(SUM(a.hours_attended)*100.0/NULLIF(SUM(a.hours_conducted),0),1) AS pct
                        FROM students s
                        JOIN attendance a ON s.roll_no = a.roll_no
                        WHERE a.semester = ? AND s.section = ?
                        GROUP BY s.roll_no, s.name
                        ORDER BY missed DESC
                        LIMIT 20
                    """
                    top_rows = conn.execute(top_sql, (sem, sec_filter)).fetchall()
                    if top_rows:
                        df_top = pd.DataFrame([dict(r) for r in top_rows])
                        fig_top = px.bar(
                            df_top, x='name', y='missed',
                            color='pct',
                            color_continuous_scale=[[0,'#ef4444'],[0.5,'#f59e0b'],[1,'#4ade80']],
                            custom_data=['roll_no','pct'],
                            labels={'name':'Student','missed':'Classes Missed','pct':'Attendance %'}
                        )
                        fig_top.update_traces(
                            hovertemplate="<b>%{x}</b><br>Roll: %{customdata[0]}<br>Missed: %{y}<br>Attendance: %{customdata[1]}%<extra></extra>"
                        )
                        apply_premium_plotly_theme(fig_top)
                        st.plotly_chart(fig_top, use_container_width=True)
                    else:
                        st.info("No data.")

            with c2:
                st.markdown("### 📚 Subject Bunk Analysis")
                subj_sql = f"""
                    SELECT a.subject,
                           COUNT(DISTINCT a.roll_no)                                                AS students,
                           SUM(a.hours_conducted)                                                   AS total_cond,
                           SUM(a.hours_attended)                                                    AS total_att,
                           SUM(a.hours_conducted - a.hours_attended)                                AS total_missed,
                           ROUND(SUM(a.hours_conducted - a.hours_attended)*100.0
                                 / NULLIF(SUM(a.hours_conducted),0), 1)                             AS bunk_rate
                    FROM attendance a
                    {sec_join}
                    WHERE a.semester = ? {sec_where}
                      AND a.hours_conducted > 0
                    GROUP BY a.subject
                    HAVING SUM(a.hours_conducted) >= 5
                    ORDER BY bunk_rate DESC
                    LIMIT 15
                """
                subj_rows = conn.execute(subj_sql, params_s).fetchall()
                if subj_rows:
                    df_sub = pd.DataFrame([dict(r) for r in subj_rows])
                    fig_sub = px.bar(
                        df_sub, x='bunk_rate', y='subject', orientation='h',
                        color='bunk_rate',
                        color_continuous_scale=[[0,'#4ade80'],[0.5,'#f59e0b'],[1,'#ef4444']],
                        custom_data=['students','total_missed','total_cond'],
                        labels={'bunk_rate':'Bunk Rate (%)','subject':'Subject'}
                    )
                    fig_sub.update_traces(
                        hovertemplate="<b>%{y}</b><br>Bunk Rate: %{x}%<br>Missed: %{customdata[1]} / %{customdata[2]}<br>Students: %{customdata[0]}<extra></extra>"
                    )
                    fig_sub.update_layout(yaxis={'categoryorder':'total ascending'})
                    apply_premium_plotly_theme(fig_sub)
                    st.plotly_chart(fig_sub, use_container_width=True)
                else:
                    st.info("No subject data found.")

            st.markdown("---")

            # ── Debarment Warning Table ─────────────────────────────────
            st.markdown(f"### ⚠️ Debarment Warning Directory  — below {threshold}% attendance")

            debar_sql = f"""
                SELECT s.roll_no, s.name, s.section,
                       SUM(a.hours_conducted)                                                       AS cond,
                       SUM(a.hours_attended)                                                        AS att,
                       SUM(a.hours_conducted - a.hours_attended)                                    AS missed,
                       ROUND(SUM(a.hours_attended)*100.0/NULLIF(SUM(a.hours_conducted),0),1)       AS pct,
                       -- Classes needed to attend to reach target threshold
                       CAST(CEIL(
                           (? * SUM(a.hours_conducted) / 100.0 - SUM(a.hours_attended))
                           / (1.0 - ? / 100.0)
                       ) AS INTEGER)                                                                AS classes_needed
                FROM students s
                JOIN attendance a ON s.roll_no = a.roll_no
                {sec_join}
                WHERE a.semester = ? {sec_where}
                GROUP BY s.roll_no, s.name, s.section
                HAVING SUM(a.hours_conducted) > 0
                   AND (SUM(a.hours_attended)*100.0/SUM(a.hours_conducted)) < ?
                ORDER BY pct ASC
            """
            debar_params = (threshold, threshold) + params_s + (threshold,)
            debar_rows = conn.execute(debar_sql, debar_params).fetchall()

            if debar_rows:
                df_db = pd.DataFrame([dict(r) for r in debar_rows])
                df_db['classes_needed'] = df_db['classes_needed'].apply(lambda x: max(0, x) if pd.notna(x) else 0)
                df_db.columns = ['Roll No','Name','Section','Conducted','Attended','Missed','Attendance %','Classes Needed to Recover']

                # Color-code attendance column — use .map (applymap deprecated in pandas >=2.1)
                def color_pct(val):
                    try:
                        v = float(val)
                        if v < 50:   return 'background-color:#7f1d1d;color:#fca5a5'
                        elif v < 65: return 'background-color:#78350f;color:#fcd34d'
                        elif v < 75: return 'background-color:#713f12;color:#fde68a'
                    except Exception:
                        pass
                    return ''

                try:
                    styled = df_db.style.map(color_pct, subset=['Attendance %'])
                except AttributeError:
                    styled = df_db.style.applymap(color_pct, subset=['Attendance %'])
                st.dataframe(styled, use_container_width=True, hide_index=True)

                # Download button
                csv = df_db.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Download Debarment List (CSV)", csv,
                                   file_name=f"debarment_{sem.replace(' ','_')}_{sec_filter.replace(' ','_')}.csv",
                                   mime='text/csv')
                st.caption(f"**'Classes Needed to Recover'** = consecutive classes this student must attend (without bunking) to reach {threshold}% attendance.")
            else:
                st.success(f"All students are above {threshold}% attendance!")

            st.markdown("---")

            # ── Charts: Who is NOT Coming — <65% students only ─────────
            DANGER_THRESHOLD = 65
            st.markdown(f"### 📉 Students Not Coming — Below {DANGER_THRESHOLD}% Attendance")
            st.caption(f"Charts below are scoped to students with attendance < {DANGER_THRESHOLD}% (chronic absentees).")

            # Per-student data filtered to <65%
            danger_df = df_stu[df_stu['pct'] < DANGER_THRESHOLD].copy()

            if danger_df.empty:
                st.success(f"No students below {DANGER_THRESHOLD}% attendance!")
            else:
                ca, cb = st.columns(2)

                with ca:
                    # Attendance distribution of danger students
                    st.markdown("#### 🎯 Attendance Distribution (below 65%)")
                    bins2   = [0, 30, 40, 50, 55, 60, 65]
                    labels2 = ['<30%','30-40%','40-50%','50-55%','55-60%','60-65%']
                    colors2 = ['#7f1d1d','#991b1b','#ef4444','#f97316','#fb923c','#fbbf24']
                    danger_df['bucket'] = pd.cut(danger_df['pct'], bins=bins2, labels=labels2, include_lowest=True)
                    bc2 = danger_df['bucket'].value_counts().reindex(labels2, fill_value=0).reset_index()
                    bc2.columns = ['Range','Count']
                    fig_d = px.bar(bc2, x='Range', y='Count',
                                   color='Range', color_discrete_sequence=colors2,
                                   labels={'Range':'Attendance Range','Count':'Students'})
                    fig_d.update_layout(showlegend=False)
                    apply_premium_plotly_theme(fig_d)
                    st.plotly_chart(fig_d, use_container_width=True)

                with cb:
                    # Top worst bunkers from <65% pool
                    st.markdown("#### 🏆 Worst Bunkers (< 65% only)")
                    worst_sql2 = f"""
                        SELECT s.name, s.roll_no, s.section,
                               ROUND(SUM(a.hours_attended)*100.0/NULLIF(SUM(a.hours_conducted),0),1) AS pct,
                               SUM(a.hours_conducted - a.hours_attended) AS missed
                        FROM students s
                        JOIN attendance a ON s.roll_no = a.roll_no
                        WHERE a.semester = ? {"AND s.section = ?" if sec_filter != "All Sections" else ""}
                        GROUP BY s.roll_no, s.name, s.section
                        HAVING SUM(a.hours_conducted) > 0
                           AND (SUM(a.hours_attended)*100.0/SUM(a.hours_conducted)) < {DANGER_THRESHOLD}
                        ORDER BY pct ASC
                        LIMIT 15
                    """
                    w2_params = (sem, sec_filter) if sec_filter != "All Sections" else (sem,)
                    w2_rows = conn.execute(worst_sql2, w2_params).fetchall()
                    if w2_rows:
                        df_w2 = pd.DataFrame([dict(r) for r in w2_rows])
                        fig_w2 = px.bar(
                            df_w2, x='pct', y='name', orientation='h',
                            color='pct',
                            range_color=[0, DANGER_THRESHOLD],
                            color_continuous_scale=[[0,'#7f1d1d'],[0.5,'#ef4444'],[1,'#f97316']],
                            custom_data=['roll_no','section','missed'],
                            labels={'pct':'Attendance %','name':'Student'}
                        )
                        fig_w2.update_traces(
                            hovertemplate="<b>%{y}</b><br>Roll: %{customdata[0]}<br>Section: %{customdata[1]}<br>Attendance: %{x}%<br>Missed: %{customdata[2]} classes<extra></extra>"
                        )
                        fig_w2.update_layout(
                            yaxis={'categoryorder':'total ascending'},
                            xaxis=dict(range=[0, DANGER_THRESHOLD], title='Attendance %')
                        )
                        apply_premium_plotly_theme(fig_w2)
                        st.plotly_chart(fig_w2, use_container_width=True)
                    else:
                        st.info(f"No students below {DANGER_THRESHOLD}%.")

                st.markdown(f"#### 📊 Section-wise Count of Students below {DANGER_THRESHOLD}%")
                if 'section' in danger_df.columns:
                    # Re-join with student sections
                    sec_danger_sql = f"""
                        SELECT s.section,
                               COUNT(DISTINCT s.roll_no) AS danger_students,
                               ROUND(AVG(sub.pct),1) AS avg_att
                        FROM students s
                        JOIN (
                            SELECT roll_no,
                                   SUM(hours_attended)*100.0/NULLIF(SUM(hours_conducted),0) AS pct
                            FROM attendance
                            WHERE semester = ?
                            GROUP BY roll_no
                            HAVING (SUM(hours_attended)*100.0/NULLIF(SUM(hours_conducted),0)) < {DANGER_THRESHOLD}
                        ) sub ON sub.roll_no = s.roll_no
                        {"WHERE s.section = ?" if sec_filter != "All Sections" else ""}
                        GROUP BY s.section
                        ORDER BY danger_students DESC
                    """
                    sd_params = (sem, sec_filter) if sec_filter != "All Sections" else (sem,)
                    sd_rows = conn.execute(sec_danger_sql, sd_params).fetchall()
                    if sd_rows:
                        df_sd = pd.DataFrame([dict(r) for r in sd_rows])
                        fig_sd = px.bar(
                            df_sd, x='section', y='danger_students',
                            color='avg_att',
                            color_continuous_scale=[[0,'#7f1d1d'],[0.5,'#ef4444'],[1,'#f97316']],
                            custom_data=['avg_att'],
                            labels={'section':'Section','danger_students':'Students Below 65%','avg_att':'Avg Attendance %'},
                            text='danger_students'
                        )
                        fig_sd.update_traces(
                            textposition='outside',
                            hovertemplate="<b>%{x}</b><br>Students below 65%: %{y}<br>Avg Attendance: %{customdata[0]}%<extra></extra>"
                        )
                        apply_premium_plotly_theme(fig_sd)
                        st.plotly_chart(fig_sd, use_container_width=True)

    # ═══════════════════════════════════════════════════════════
    # TAB 2: SMART BUNKING & INTERMITTENT PATTERN ANALYSIS
    # ═══════════════════════════════════════════════════════════
    with tab_patterns:
        try:
            sem_num = int(sem.replace("Sem ", "").strip())
        except Exception:
            sem_num = 3

        if sec_filter == "All Sections":
            abs_sql = """
                SELECT h.date, h.roll_no, h.hour, h.subject, s.name, s.section
                FROM hour_wise_attendance h
                JOIN students s ON h.roll_no = s.roll_no
                WHERE s.semester = ? AND h.roll_no IS NOT NULL AND h.roll_no != ''
            """
            abs_params = (sem_num,)

            cond_sql = """
                SELECT DISTINCT date, section, hour
                FROM hour_wise_attendance
                WHERE section IS NOT NULL AND section != ''
            """
            cond_params = ()
        else:
            abs_sql = """
                SELECT h.date, h.roll_no, h.hour, h.subject, s.name, s.section
                FROM hour_wise_attendance h
                JOIN students s ON h.roll_no = s.roll_no
                WHERE s.semester = ? AND s.section = ? AND h.roll_no IS NOT NULL AND h.roll_no != ''
            """
            abs_params = (sem_num, sec_filter)

            cond_sql = """
                SELECT DISTINCT date, section, hour
                FROM hour_wise_attendance
                WHERE section = ?
            """
            cond_params = (sec_filter,)

        abs_rows = conn.execute(abs_sql, abs_params).fetchall()
        cond_rows = conn.execute(cond_sql, cond_params).fetchall()
        df_abs = pd.DataFrame([dict(r) for r in abs_rows]) if abs_rows else pd.DataFrame(columns=['date', 'roll_no', 'hour', 'subject', 'name', 'section'])
        df_cond = pd.DataFrame([dict(r) for r in cond_rows]) if cond_rows else pd.DataFrame(columns=['date', 'section', 'hour'])

        if df_abs.empty or df_cond.empty:
            st.info("ℹ️ No hour-wise period attendance records found for this selection to perform pattern analysis.")
        else:
            # Group conducted hours
            cond_map = df_cond.groupby(['date', 'section'])['hour'].apply(set).to_dict()
            abs_map = df_abs.groupby(['date', 'roll_no'])['hour'].apply(set).to_dict()
            student_info = df_abs[['roll_no', 'name', 'section']].drop_duplicates().set_index('roll_no').to_dict('index')

            pattern_instances = []
            for (date, roll), abs_hours in abs_map.items():
                stud = student_info.get(roll)
                if not stud:
                    continue
                sec = stud['section']
                cond_hours = cond_map.get((date, sec), set())
                if not cond_hours:
                    continue

                pres_hours = cond_hours - abs_hours

                # 1. Specific Bunk Pattern: present 1 & 2, absent 3 & 4, present 5, absent 6 or 7
                match_specific = (
                    1 in pres_hours and 2 in pres_hours and
                    3 in abs_hours and 4 in abs_hours and
                    5 in pres_hours and
                    (6 in abs_hours or 7 in abs_hours)
                )

                # 2. General Intermittent Bunking: P-A-P-A status string
                sorted_cond = sorted(list(cond_hours))
                status_seq = []
                for h in sorted_cond:
                    status_seq.append('A' if h in abs_hours else 'P')

                status_str = "".join(status_seq)
                is_intermittent = False
                first_p = status_str.find('P')
                if first_p != -1:
                    next_a = status_str.find('A', first_p)
                    if next_a != -1:
                        next_p = status_str.find('P', next_a)
                        if next_p != -1:
                            next_a2 = status_str.find('A', next_p)
                            if next_a2 != -1:
                                is_intermittent = True

                if match_specific or is_intermittent:
                    day_of_week = pd.to_datetime(date).day_name()
                    pattern_type = 'Specific (P-P-A-A-P-A)' if match_specific else 'Intermittent (P-A-P-A)'
                    pattern_instances.append({
                        'date': date,
                        'roll_no': roll,
                        'name': stud['name'],
                        'section': sec,
                        'day_of_week': day_of_week,
                        'pattern': pattern_type,
                        'status_str': status_str,
                        'abs_hours': sorted(list(abs_hours)),
                        'cond_hours': sorted_cond
                    })

            if not pattern_instances:
                st.success("🎉 No intermittent bunking patterns detected in this section!")
            else:
                df_pat = pd.DataFrame(pattern_instances)
                unique_students = df_pat['roll_no'].nunique()
                total_instances = len(df_pat)

                # Peak day calculation
                day_counts = df_pat['day_of_week'].value_counts()
                peak_day = day_counts.index[0] if not day_counts.empty else "N/A"
                peak_day_pct = round((day_counts.iloc[0] / total_instances * 100), 1) if not day_counts.empty else 0

                # Render Pattern KPI Cards
                st.markdown(f"""
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:24px;">
                    {kpi("Intermittent Bunk Incidents", f"{total_instances}", "#ef4444")}
                    {kpi("Identified Smart Bunkers", f"{unique_students}", "#f59e0b")}
                    {kpi("Peak Bunking Day", f"{peak_day} ({peak_day_pct}%)", "#00D8C6")}
                </div>""", unsafe_allow_html=True)

                st.markdown("### 🕵️ Bunking Habit Analysis")
                st.caption("Intermittent/selective bunking pattern corresponds to students attending initial periods, escaping middle hours, and returning/leaving selectively.")

                # charts row
                c_p1, c_p2 = st.columns(2)
                with c_p1:
                    st.markdown("#### 📅 Weekly Pattern: Bunking by Day of Week")
                    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                    df_day = df_pat['day_of_week'].value_counts().reindex(weekday_order, fill_value=0).reset_index()
                    df_day.columns = ['Day', 'Incidents']
                    fig_day = px.bar(df_day, x='Day', y='Incidents',
                                     color='Day', color_discrete_sequence=['#fbbf24','#fb7185','#818cf8','#34d399','#a78bfa'],
                                     labels={'Incidents':'Bunk Incidents'})
                    fig_day.update_layout(showlegend=False)
                    apply_premium_plotly_theme(fig_day)
                    st.plotly_chart(fig_day, use_container_width=True)

                with c_p2:
                    st.markdown("#### 🕒 Hour-wise Bunking Heatmap")
                    # Calculate how many times each hour was bunked on these intermittent days
                    all_bunked_hours = []
                    for inst in pattern_instances:
                        all_bunked_hours.extend(inst['abs_hours'])

                    df_hr = pd.Series(all_bunked_hours).value_counts().reindex(range(1, 8), fill_value=0).reset_index()
                    df_hr.columns = ['Period', 'Count']
                    df_hr['Period'] = 'P' + df_hr['Period'].astype(str)

                    fig_hr = px.bar(df_hr, x='Period', y='Count',
                                    color='Count', color_continuous_scale='Burg',
                                    labels={'Count':'Bunks Recorded'})
                    fig_hr.update_layout(showlegend=False)
                    apply_premium_plotly_theme(fig_hr)
                    st.plotly_chart(fig_hr, use_container_width=True)

                st.markdown("---")

                # Habitual List Table
                st.markdown("#### 🏆 Habitual Smart Bunkers Leaderboard")
                df_leaderboard = df_pat.groupby(['roll_no', 'name', 'section']).size().reset_index(name='Incidents')
                df_leaderboard = df_leaderboard.sort_values(by='Incidents', ascending=False)
                df_leaderboard.columns = ['Roll No', 'Student Name', 'Section', 'Detected Pattern Incidents']
                st.dataframe(df_leaderboard, use_container_width=True, hide_index=True)

                # Drilldown to individual student patterns
                st.markdown("#### 🔍 Individual Student Pattern Explorer")
                selected_student_roll = st.selectbox(
                    "Select Student to View Detailed Bunk Calendar",
                    options=df_leaderboard['Roll No'].tolist(),
                    format_func=lambda r: f"{df_leaderboard[df_leaderboard['Roll No'] == r]['Student Name'].values[0]} ({r}) - {df_leaderboard[df_leaderboard['Roll No'] == r]['Section'].values[0]}"
                )

                if selected_student_roll:
                    df_stud_pat = df_pat[df_pat['roll_no'] == selected_student_roll].copy()
                    st.markdown(f"**Bunk calendar history for `{selected_student_roll}`:**")

                    details = []
                    for _, row in df_stud_pat.iterrows():
                        # Find subjects missed during absent hours
                        abs_hrs = row['abs_hours']
                        subj_missed = []
                        for h in abs_hrs:
                            r_sub = conn.execute("""
                                SELECT subject FROM hour_wise_attendance 
                                WHERE date = ? AND roll_no = ? AND hour = ?
                            """, (row['date'], selected_student_roll, h)).fetchone()
                            if r_sub:
                                subj_missed.append(f"P{h}: {r_sub['subject']}")

                        details.append({
                            'Date': row['date'],
                            'Day': row['day_of_week'],
                            'Conducted Periods': str(row['cond_hours']),
                            'Period Status Sequence': row['status_str'],
                            'Pattern Type': row['pattern'],
                            'Subjects Bunked': ", ".join(subj_missed)
                        })

                    df_det = pd.DataFrame(details)
                    st.dataframe(df_det, use_container_width=True, hide_index=True)

    conn.close()

# ROUTER
# ══════════════════════════════════════════════════════════════
if _DB_FALLBACK:
    st.warning("⚠️ PostgreSQL connection failed (database connection limit reached). Operating in offline SQLite mode.")

if not st.session_state.get('logged_in'):
    login_page()
elif st.session_state.get('needs_dob_setup'):
    setup_dob_page()
elif st.session_state.get('role') == 'admin':
    admin_dashboard()
else:
    student_dashboard()
