"""
database_pg.py — PostgreSQL (Supabase) version of database.py
Drop-in replacement that works on Streamlit Cloud with Supabase.
All function signatures identical to database.py so streamlit_app.py
needs zero changes (just swap the import).
"""
import os
import csv
import io
import shutil
from datetime import datetime

import psycopg2
import psycopg2.extras
import streamlit as st

# ── Constants (identical to database.py) ────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_DIR  = os.path.join(BASE_DIR, 'attandance database for db construction')
RESULTS_CSV_DIR = os.path.join(BASE_DIR, 'resutls database for db construction')

DEFAULT_STUDENT_PASSWORD = 'PENDING'
ACTIVE_SEMESTER = 'Sem 2'

CLASSES = [
    'AIDS', 'AIML', 'CIVIL',
    'CSE_A', 'CSE_B', 'CSE_C', 'CSE_D',
    'CSM_A', 'CSM_B', 'CSM_C', 'CSM_D', 'CSM_E',
    'DS_A',  'DS_B',  'DS_C',
    'ECE_A', 'ECE_B',
    'EEE', 'EIE', 'IT', 'MECH'
]

SEM1_SUBJECTS = ['IEE', 'ED', 'PPS', 'ENG', 'M&C', 'AEP']

SECTION_SUBJECTS = {
    'AIDS':  ['BEE','BEE LAB','EWS','EDC','DS','DS LAB','PYTHON LAB','EC','EC LAB','ODEVC','CRT'],
    'AIML':  ['BEE','BEE LAB','EWS','EDC','DS','DS LAB','PYTHON LAB','EC','EC LAB','ODEVC','CRT'],
    'CIVIL': ['BPC','EM','EEEE','EEEE LAB','PYTHON','PYTHON LAB','EC','EC LAB','ODEVC','CRT'],
    'CSE_A': ['BEE','BEE LAB','ED&CAD','DS','DS LAB','ITW','PYTHON LAB','ODEVC','AEP','AEP LAB','CRT'],
    'CSE_B': ['BEE','BEE LAB','ED&CAD','DS','DS LAB','ITW','PYTHON LAB','ODEVC','AEP','AEP LAB','CRT'],
    'CSE_C': ['BEE','BEE LAB','ED&CAD','DS','DS LAB','ITW','PYTHON LAB','ODEVC','AEP','AEP LAB','CRT'],
    'CSE_D': ['BEE','BEE LAB','ED&CAD','DS','DS LAB','ITW','PYTHON LAB','ODEVC','AEP','AEP LAB','CRT'],
    'CSM_A': ['ED& CAD','DS','DS LAB','ITW','PHYTHON LAB','EC','EC LAB','ESE','ELCS LAB','ODEVC','CRT'],
    'CSM_B': ['ED& CAD','DS','DS LAB','ITW','PHYTHON LAB','EC','EC LAB','ESE','ELCS LAB','ODEVC','CRT'],
    'CSM_C': ['ED& CAD','DS','DS LAB','ITW','PHYTHON LAB','EC','EC LAB','ESE','ELCS LAB','ODEVC','CRT'],
    'CSM_D': ['ED& CAD','DS','DS LAB','ITW','PHYTHON LAB','EC','EC LAB','ESE','ELCS LAB','ODEVC','CRT'],
    'CSM_E': ['ED& CAD','DS','DS LAB','ITW','PHYTHON LAB','EC','EC LAB','ESE','ELCS LAB','ODEVC','CRT'],
    'DS_A':  ['EWS','EDC','DS','DS LAB','PHYTHON LAB','ESE','ELCS LAB','ODEVC','AEP','AEP LAB','CRT'],
    'DS_B':  ['EWS','EDC','DS','DS LAB','PHYTHON LAB','ESE','ELCS LAB','ODEVC','AEP','AEP LAB','CRT'],
    'DS_C':  ['EWS','EDC','DS','DS LAB','PHYTHON LAB','ESE','ELCS LAB','ODEVC','AEP','AEP LAB','CRT'],
    'ECE_A': ['BEE LAB','EWS','NAS','DS','DS LAB','PYTHON','APP PHTH LAB','EC','EC LAB','ODEVC','CRT'],
    'ECE_B': ['BEE LAB','EWS','NAS','DS','DS LAB','PYTHON','APP PHTH LAB','EC','EC LAB','ODEVC','CRT'],
    'EEE':   ['EC_II','BEE LAB','EWS','DS','DS LAB','PYTHON','PYTHON LAB','AEP','AEP LAB','ODEVC','CRT'],
    'EIE':   ['EE LAB','EWS','NAS','DS','DS LAB','PYTHON','APP PHTH LAB','ODEVC','AEP','AEP LAB','CRT'],
    'IT':    ['EWS','EDC','DS','DS LAB','PHYTHON LAB','ESE','ELCS LAB','ODEVC','AEP','AEP LAB','CRT'],
    'MECH':  ['EEEE','EEEE LAB','ED& CAD','TD','PYTHON','PYTHON LAB','EC','EC LAB','ODEVC','CRT'],
}

SUBJECT_CREDITS = {
    'IEE': 4.0, 'ED': 4.0, 'PPS': 4.0, 'ENG': 3.0, 'M&C': 4.0, 'AEP': 3.0,
    'BEE': 3.0, 'EWS': 3.0, 'NAS': 3.0, 'DS': 3.0, 'EDC': 3.0,
    'EC': 3.0, 'EC_II': 3.0, 'ODEVC': 3.0, 'BPC': 3.0, 'EM': 3.0,
    'EEEE': 3.0, 'ESE': 3.0, 'ITW': 3.0, 'TD': 3.0,
    'PYTHON': 3.0, 'ED&CAD': 3.0, 'ED& CAD': 3.0,
    'BEE LAB': 1.5, 'DS LAB': 1.5, 'PYTHON LAB': 1.5, 'PHYTHON LAB': 1.5,
    'APP PHTH LAB': 1.5, 'EC LAB': 1.5, 'EEEE LAB': 1.5, 'AEP LAB': 1.5,
    'ELCS LAB': 1.5, 'EE LAB': 1.5,
    'CRT': 0.0,
}

BRANCH_CODE_MAP = {
    '01':'CIVIL','02':'EEE','03':'MECH',
    '04':'ECE','05':'CSE','10':'EIE',
    '12':'IT','66':'CSM','67':'DS',
    '72':'AIDS','73':'AIML'
}


# ── Connection ──────────────────────────────────────────────────────

def _get_pg_url():
    """Get database URL from Streamlit secrets or environment variable."""
    try:
        return st.secrets["database"]["url"]
    except Exception:
        url = os.environ.get("DATABASE_URL", "")
        if not url:
            raise RuntimeError(
                "No DATABASE_URL found. Add it to .streamlit/secrets.toml or set as environment variable."
            )
        return url


class _RowWrapper:
    """Makes psycopg2 RealDictRow behave like sqlite3.Row (dict + index access)."""
    def __init__(self, d):
        self._d = dict(d)
        self._vals = list(self._d.values())  # for integer index access
    def __getitem__(self, key):
        if isinstance(key, int):
            return self._vals[key]   # fetchone()[0] style
        return self._d[key]          # fetchone()['column'] style
    def __contains__(self, key):
        return key in self._d
    def keys(self):
        return self._d.keys()
    def get(self, key, default=None):
        return self._d.get(key, default)


# ── Transparent Caching Mechanism ──
import time
_QUERY_CACHE = {}  # (sql_query, tuple_params): (expiry_timestamp, list_of_RowWrappers)

def _clear_cache():
    global _QUERY_CACHE
    _QUERY_CACHE.clear()


class _CachedCursor:
    def __init__(self, rows):
        self._rows = rows
        self._idx = 0

    def fetchone(self):
        if self._idx < len(self._rows):
            r = self._rows[self._idx]
            self._idx += 1
            return r
        return None

    def fetchall(self):
        res = self._rows[self._idx:]
        self._idx = len(self._rows)
        return res

    def __getitem__(self, idx):
        if not self._rows:
            return None
        # Allow conn.execute(sql)[0] style access
        return self._rows[0][idx]

    def __iter__(self):
        return self

    def __next__(self):
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row


class _PGConn:
    """
    Thin wrapper around a psycopg2 connection that mimics the sqlite3 interface
    used throughout streamlit_app.py:
      conn.execute(sql, params)  → returns cursor with .fetchone()/.fetchall()
      conn.executemany(sql, seq)
      conn.commit()
      conn.close()
    Also supports context manager usage.
    """
    def __init__(self, conn):
        self._conn = conn

    def _adapt_sql(self, sql):
        """Convert SQLite ? placeholders to PostgreSQL %s and escape literal %."""
        # 1. Convert SQLite ? placeholders to %s
        sql = sql.replace('?', '%s')
        
        # 2. Escape literal % to %% to prevent psycopg2 query interpolation issues, 
        # except when they are part of %s placeholders.
        # We replace %s with a temporary marker, double all remaining %, and swap the marker back.
        marker = "__PERCENT_S_PLACEHOLDER__"
        sql = sql.replace('%s', marker)
        sql = sql.replace('%', '%%')
        sql = sql.replace(marker, '%s')
        return sql

    def execute(self, sql, params=()):
        sql_upper = sql.strip().upper()
        # Check if it's a read query
        is_read = sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')
        
        # If it's a write query, invalidate the cache!
        if not is_read:
            _clear_cache()
            
        # Check query cache for reads
        if is_read:
            cache_key = (sql, tuple(params) if params else ())
            now = time.time()
            if cache_key in _QUERY_CACHE:
                expiry, cached_rows = _QUERY_CACHE[cache_key]
                if now < expiry:
                    return _CachedCursor(cached_rows)

        adapted_sql = self._adapt_sql(sql)
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(adapted_sql, params)
        wrapper = _CursorWrapper(cur)

        # Cache results if it's a read query
        if is_read:
            cache_key = (sql, tuple(params) if params else ())
            # Fetch all rows into RowWrappers
            rows = wrapper.fetchall()
            _QUERY_CACHE[cache_key] = (time.time() + 300, rows)  # cache for 5 minutes
            return _CachedCursor(rows)

        return wrapper

    def executemany(self, sql, seq):
        # Any bulk execute is a write, clear cache
        _clear_cache()
        sql = self._adapt_sql(sql)
        cur = self._conn.cursor()
        cur.executemany(sql, seq)

    def cursor(self):
        return _CursorProxy(self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor), self)

    def commit(self):
        self._conn.commit()

    def close(self):
        # Return to pool if available, otherwise close
        pool = getattr(self, '_pool', None)
        if pool:
            try:
                self._conn.commit()  # commit any pending tx before returning
            except Exception:
                try:
                    self._conn.rollback()
                except Exception:
                    pass
            pool.putconn(self._conn)
        else:
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class _CursorWrapper:
    def __init__(self, cur):
        self._cur = cur

    def fetchone(self):
        row = self._cur.fetchone()
        return _RowWrapper(row) if row else None

    def fetchall(self):
        return [_RowWrapper(r) for r in self._cur.fetchall()]

    def __getitem__(self, idx):
        # Allow conn.execute(...).fetchone()[0] style access
        row = self._cur.fetchone()
        if row is None:
            return None
        vals = list(dict(row).values())
        return vals[idx]

    def __iter__(self):
        return self

    def __next__(self):
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row


class _CursorProxy:
    """Proxy returned by conn.cursor() for code that calls cursor.execute() directly."""
    def __init__(self, cur, pg_conn):
        self._cur = cur
        self._pg = pg_conn

    def execute(self, sql, params=()):
        sql = self._pg._adapt_sql(sql)
        self._cur.execute(sql, params)
        return _CursorWrapper(self._cur)

    def executemany(self, sql, seq):
        sql = self._pg._adapt_sql(sql)
        self._cur.executemany(sql, seq)

    def fetchone(self):
        row = self._cur.fetchone()
        return _RowWrapper(row) if row else None

    def fetchall(self):
        return [_RowWrapper(r) for r in self._cur.fetchall()]

    def __iter__(self):
        return self

    def __next__(self):
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row


def _make_conn():
    """Create a single raw psycopg2 connection (used by pool)."""
    url = _get_pg_url()
    try:
        c = psycopg2.connect(url, sslmode='require', connect_timeout=15)
        c.autocommit = False
        return c
    except psycopg2.OperationalError:
        c = psycopg2.connect(url, connect_timeout=15)
        c.autocommit = False
        return c


@st.cache_resource
def _get_pool():
    """
    Create a ThreadedConnectionPool once per app session.
    Cached by Streamlit so it survives reruns — connections are REUSED.
    minconn=2, maxconn=8 is safe for Supabase free tier (max 20 connections).
    """
    from psycopg2 import pool as pg_pool
    url = _get_pg_url()
    try:
        p = pg_pool.ThreadedConnectionPool(
            minconn=2, maxconn=8,
            dsn=url, sslmode='require', connect_timeout=15
        )
        return p
    except Exception:
        p = pg_pool.ThreadedConnectionPool(
            minconn=2, maxconn=8,
            dsn=url, connect_timeout=15
        )
        return p


def get_db_connection():
    """
    Get a connection from the pool. Always call conn.close() when done —
    this returns the connection to the pool rather than closing it.
    Validates connection and recreates the pool if it has failed.
    """
    pool = _get_pool()
    max_retries = 3
    for attempt in range(max_retries):
        raw = None
        try:
            raw = pool.getconn()
            # Test connection health
            with raw.cursor() as cur:
                cur.execute("SELECT 1")
            raw.rollback()  # End the transaction block started by SELECT 1
            raw.autocommit = False
            conn = _PGConn(raw)
            conn._pool = pool   # store reference so close() can return to pool
            return conn
        except (psycopg2.InterfaceError, psycopg2.OperationalError) as e:
            if raw:
                try:
                    pool.putconn(raw, close=True)
                except Exception:
                    pass
            print(f"[Database Pool] Dead connection detected on attempt {attempt+1}/{max_retries}: {e}")
            if attempt == max_retries - 1:
                # Recreate the connection pool
                print("[Database Pool] Recreating Connection Pool...")
                _get_pool.clear()
                pool = _get_pool()
                raw = pool.getconn()
                raw.autocommit = False
                conn = _PGConn(raw)
                conn._pool = pool
                return conn




# ── Schema (PostgreSQL syntax) ──────────────────────────────────────

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    roll_no      TEXT PRIMARY KEY,
    name         TEXT,
    dob          TEXT DEFAULT 'PENDING',
    email        TEXT,
    semester     INTEGER DEFAULT 2,
    department   TEXT,
    section      TEXT,
    branch       TEXT,
    phone        TEXT,
    parent_phone TEXT,
    theme_pref   TEXT DEFAULT 'dark'
);

CREATE TABLE IF NOT EXISTS subjects (
    id           SERIAL PRIMARY KEY,
    subject_code TEXT NOT NULL,
    subject_name TEXT,
    semester     TEXT,
    section      TEXT,
    UNIQUE(subject_code, semester, section)
);

CREATE TABLE IF NOT EXISTS attendance (
    id              SERIAL PRIMARY KEY,
    roll_no         TEXT,
    subject         TEXT,
    semester        TEXT,
    hours_attended  INTEGER DEFAULT 0,
    hours_conducted INTEGER DEFAULT 0,
    UNIQUE(roll_no, subject, semester),
    FOREIGN KEY(roll_no) REFERENCES students(roll_no)
);

CREATE TABLE IF NOT EXISTS marks (
    id          SERIAL PRIMARY KEY,
    roll_no     TEXT,
    subject     TEXT,
    semester    TEXT,
    exam_type   TEXT,
    score       REAL,
    grade_point REAL,
    UNIQUE(roll_no, subject, semester, exam_type)
);

CREATE TABLE IF NOT EXISTS sgpa_records (
    id        SERIAL PRIMARY KEY,
    roll_no   TEXT,
    semester  TEXT,
    sgpa      REAL,
    failed    INTEGER DEFAULT 0,
    UNIQUE(roll_no, semester),
    FOREIGN KEY(roll_no) REFERENCES students(roll_no)
);

CREATE TABLE IF NOT EXISTS timetable (
    id      SERIAL PRIMARY KEY,
    section TEXT,
    day     TEXT,
    period  INTEGER,
    subject TEXT,
    UNIQUE(section, day, period)
);

CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS scrape_log (
    id         SERIAL PRIMARY KEY,
    scraped_at TEXT,
    section    TEXT,
    students   INTEGER DEFAULT 0,
    status     TEXT,
    duration   REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS attendance_history (
    id                SERIAL PRIMARY KEY,
    snapshot_date     TEXT NOT NULL DEFAULT (CURRENT_DATE::TEXT),
    roll_no           TEXT NOT NULL,
    subject_code      TEXT NOT NULL,
    running_attended  INTEGER DEFAULT 0,
    running_conducted INTEGER DEFAULT 0,
    percentage        REAL DEFAULT 0,
    UNIQUE(roll_no, subject_code, snapshot_date),
    FOREIGN KEY(roll_no) REFERENCES students(roll_no)
);

CREATE INDEX IF NOT EXISTS idx_ah_roll    ON attendance_history(roll_no);
CREATE INDEX IF NOT EXISTS idx_ah_subject ON attendance_history(subject_code);
CREATE INDEX IF NOT EXISTS idx_ah_date    ON attendance_history(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_att_roll   ON attendance(roll_no);
CREATE INDEX IF NOT EXISTS idx_marks_roll ON marks(roll_no);
CREATE INDEX IF NOT EXISTS idx_log_sec    ON scrape_log(section);
CREATE INDEX IF NOT EXISTS idx_sgpa_roll  ON sgpa_records(roll_no);
"""


def init_db():
    conn = get_db_connection()

    # Run each statement separately in its own transaction block to prevent psycopg2 transaction failures
    for stmt in _SCHEMA_SQL.split(';'):
        stmt = stmt.strip()
        if stmt:
            try:
                conn.execute(stmt)
                conn.commit()
            except Exception as e:
                try:
                    conn._conn.rollback()
                except Exception:
                    pass
                print(f"[init_db] Warning on statement: {stmt[:60]}... → {e}")

    # Seed config defaults
    today = datetime.now().strftime('%Y-%m-%d')
    for key, val in [
        ('start_date', '2026-01-27'),
        ('end_date', today),
        ('last_scraped_at', 'Never'),
        ('active_semester', 'Sem 2'),
        ('total_semester_hours', '600'),
    ]:
        try:
            conn.execute(
                "INSERT INTO config(key,value) VALUES(%s,%s) ON CONFLICT(key) DO NOTHING",
                (key, val)
            )
            conn.commit()
        except Exception as e:
            try: conn._conn.rollback()
            except: pass
            print(f"[init_db] Warning on seeding config '{key}': {e}")

    # Seed subjects if empty
    try:
        row = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()
        count = list(row._d.values())[0] if row else 0
        if count == 0:
            for section, subs in SECTION_SUBJECTS.items():
                for sub in subs:
                    conn.execute(
                        "INSERT INTO subjects(subject_code,subject_name,semester,section) "
                        "VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                        (sub, sub, ACTIVE_SEMESTER, section)
                    )
            conn.commit()
    except Exception as e:
        try: conn._conn.rollback()
        except: pass
        print(f"[init_db] Warning on seeding subjects: {e}")

    # Seed students if empty
    try:
        row = conn.execute("SELECT COUNT(*) FROM students").fetchone()
        count = list(row._d.values())[0] if row else 0
        if count == 0:
            seed_db_from_csvs(conn)
    except Exception as e:
        try: conn._conn.rollback()
        except: pass
        print(f"[init_db] Warning on seeding students: {e}")

    # Migration: reset placeholder DOBs
    try:
        conn.execute("UPDATE students SET dob='PENDING' WHERE dob='2007-01-01'")
        conn.commit()
    except Exception as e:
        try: conn._conn.rollback()
        except: pass
        print(f"[init_db] Warning on DOB reset migration: {e}")

    conn.close()


# ── Helpers (all identical logic to database.py) ────────────────────

def get_config_map(conn=None):
    close_after = False
    if conn is None:
        conn = get_db_connection()
        close_after = True
    try:
        rows = conn.execute('SELECT key,value FROM config').fetchall()
        return {r['key']: r['value'] for r in rows}
    finally:
        if close_after:
            conn.close()


def get_portal_yr_br(section, semester):
    try:
        sem_num = int(str(semester).replace('Sem', '').strip())
        yr = str((sem_num + 1) // 2)
    except Exception:
        yr = '1'
    if yr == '1':
        br = 'BSH'
    else:
        prefix = section.split('_')[0].upper() if '_' in section else section.upper()
        br = prefix
    return yr, br


def decode_roll_branch(roll_no):
    try:
        roll = roll_no.strip().upper()
        idx = roll.find('891A')
        if idx == -1:
            return None
        code = roll[idx+4:idx+6]
        return BRANCH_CODE_MAP.get(code)
    except Exception:
        return None


def parse_sem1_results_csv(csv_content):
    """Identical logic to database.py — parses JNTUH results CSV format."""
    results = []
    reader = csv.DictReader(io.StringIO(csv_content))
    headers = reader.fieldnames or []

    subj_codes = []
    i = 0
    while i < len(headers):
        h = headers[i].strip()
        if h.lower() in ('hall no', 'name', 'sgpa', 'remarks', 'result'):
            i += 1
            continue
        if i + 1 < len(headers):
            next_h = headers[i+1].strip().lower()
            if next_h in ('total', 'gp', 'grade point', 'grade_point'):
                subj_codes.append(h)
                i += 2
                continue
        i += 1

    for row in reader:
        hall_no = (row.get('Hall No') or row.get('Hall no') or '').strip().upper()
        name    = (row.get('Name') or '').strip()
        if not hall_no:
            continue

        subj_marks = {}
        for subj in subj_codes:
            total_key = None
            gp_key    = None
            for k in row.keys():
                ks = k.strip().lower()
                if k.strip() == subj:
                    total_key = k
                elif ks in ('total', 'gp', 'grade point', 'grade_point') and total_key and gp_key is None:
                    gp_key = k

            total = None
            gp    = None
            if total_key:
                try:
                    total = float(row[total_key])
                except Exception:
                    pass
            if gp_key:
                try:
                    gp = float(row[gp_key])
                except Exception:
                    pass
            subj_marks[subj] = {'total': total, 'gp': gp}

        sgpa   = None
        failed = False
        for k, v in row.items():
            ks = k.strip().lower()
            if ks == 'sgpa':
                try:
                    sgpa = float(v)
                except Exception:
                    pass
            if ks in ('result', 'remarks') and v and 'fail' in v.lower():
                failed = True

        results.append({
            'roll_no': hall_no, 'name': name,
            'subjects': subj_marks, 'sgpa': sgpa, 'failed': failed
        })
    return results


def score_to_grade(score):
    if score is None: return 'Ab', 0.0
    s = float(score)
    if s >= 90: return 'O',  10.0
    if s >= 80: return 'A+',  9.0
    if s >= 70: return 'A',   8.0
    if s >= 60: return 'B+',  7.0
    if s >= 50: return 'B',   6.0
    if s >= 40: return 'C',   5.0
    return 'F', 0.0


def gp_to_grade(gp):
    if gp >= 10: return 'O'
    if gp >= 9:  return 'A+'
    if gp >= 8:  return 'A'
    if gp >= 7:  return 'B+'
    if gp >= 6:  return 'B'
    if gp >= 5:  return 'C'
    return 'F'


def compute_sgpa(marks_rows):
    total_credits = weighted = 0.0
    for row in marks_rows:
        subj    = row['subject'] if isinstance(row, dict) else row['subject']
        credits = SUBJECT_CREDITS.get(subj, 0.0)
        if credits == 0.0: continue
        gp = (row['grade_point'] if isinstance(row, dict) else row['grade_point']) or 0.0
        weighted      += gp * credits
        total_credits += credits
    return round(weighted / total_credits, 2) if total_credits else 0.0


def sync_sgpa_records(roll_no, conn):
    sem_rows = conn.execute(
        "SELECT DISTINCT semester FROM marks WHERE roll_no=%s AND exam_type LIKE '%%Final Examinations'",
        (roll_no,)
    ).fetchall()

    for row in sem_rows:
        sem = row['semester']
        existing = conn.execute(
            'SELECT id FROM sgpa_records WHERE roll_no=%s AND semester=%s',
            (roll_no, sem)
        ).fetchone()

        if sem == 'Sem 1' and existing:
            continue

        final_marks = conn.execute(
            'SELECT subject, score, grade_point FROM marks WHERE roll_no=%s AND semester=%s AND exam_type=%s',
            (roll_no, sem, f"{sem} Final Examinations")
        ).fetchall()

        if final_marks:
            has_failed = False
            total_credits = 0.0
            weighted_gp   = 0.0
            for m in final_marks:
                sub     = m['subject']
                score   = m['score']
                gp      = m['grade_point'] or 0.0
                credits = SUBJECT_CREDITS.get(sub, 3.0)
                grade, _ = score_to_grade(score)
                if grade in ['F', 'Ab']:
                    has_failed = True
                if credits > 0:
                    weighted_gp   += gp * credits
                    total_credits += credits
            sgpa = round(weighted_gp / total_credits, 2) if total_credits > 0 else 0.0

            if existing:
                conn.execute(
                    'UPDATE sgpa_records SET sgpa=%s, failed=%s WHERE roll_no=%s AND semester=%s',
                    (sgpa, 1 if has_failed else 0, roll_no, sem)
                )
            else:
                conn.execute(
                    'INSERT INTO sgpa_records(roll_no,semester,sgpa,failed) VALUES(%s,%s,%s,%s)',
                    (roll_no, sem, sgpa, 1 if has_failed else 0)
                )
    conn.commit()


def compute_cgpa(roll_no, conn=None):
    close_after = False
    if conn is None:
        conn = get_db_connection()
        close_after = True
    try:
        sync_sgpa_records(roll_no, conn)
        rows = conn.execute(
            'SELECT sgpa FROM sgpa_records WHERE roll_no=%s AND sgpa>0 AND failed=0',
            (roll_no,)
        ).fetchall()
        if not rows: return 0.0
        return round(sum(r['sgpa'] for r in rows) / len(rows), 2)
    finally:
        if close_after:
            conn.close()


def backup_db():
    """On PostgreSQL, backup is handled by Supabase. This is a no-op stub."""
    return None


def seed_db_from_csvs(conn):
    """Seed from local CSV files (runs only once when DB is empty)."""
    if not os.path.exists(CSV_DIR):
        # Fallback: insert a single demo student
        roll = "25891A0465"
        conn.execute(
            "INSERT INTO students(roll_no,name,dob,email,semester,department,section,branch) "
            "VALUES(%s,%s,%s,%s,2,'ECE','ECE_B','ECE') ON CONFLICT DO NOTHING",
            (roll, "Demo Student", "PENDING", f"{roll.lower()}@vits.edu")
        )
        for sub in SECTION_SUBJECTS["ECE_B"]:
            conn.execute(
                "INSERT INTO attendance(roll_no,subject,semester,hours_attended,hours_conducted) "
                "VALUES(%s,%s,'Sem 2',24,30) ON CONFLICT DO NOTHING",
                (roll, sub)
            )
        conn.execute(
            "INSERT INTO sgpa_records(roll_no,semester,sgpa,failed) VALUES(%s,'Sem 1',7.5,0) ON CONFLICT DO NOTHING",
            (roll,)
        )
        conn.commit()
        return

    csv_files = [f for f in os.listdir(CSV_DIR) if f.lower().endswith(".csv") and f.lower() != "attendance_master.csv"]
    for fname in csv_files:
        fpath = os.path.join(CSV_DIR, fname)
        try:
            with open(fpath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                headers = [h.strip() for h in (reader.fieldnames or [])]
                section_name = os.path.splitext(fname)[0].strip().upper()

                for row in reader:
                    row_clean = {k.strip(): v for k, v in row.items() if k}
                    roll = (row_clean.get('Roll No') or row_clean.get('Roll Number') or '').strip().upper()
                    name = (row_clean.get('Name') or '').strip()
                    if not roll:
                        continue
                    branch = decode_roll_branch(roll) or section_name.split('_')[0]
                    conn.execute(
                        "INSERT INTO students(roll_no,name,dob,semester,branch,department,section) "
                        "VALUES(%s,%s,'PENDING',2,%s,%s,%s) ON CONFLICT(roll_no) DO UPDATE SET name=EXCLUDED.name",
                        (roll, name, branch, branch, section_name)
                    )
                    for h in headers:
                        if h.lower() in ('roll no', 'roll number', 'name', ''):
                            continue
                        try:
                            attended  = int(float(row_clean.get(h, 0) or 0))
                            conducted = attended + int(float(row_clean.get(h + '_conducted', 0) or 0))
                            if attended == 0 and conducted == 0:
                                attended = conducted = 0
                        except Exception:
                            continue
                        conn.execute(
                            "INSERT INTO attendance(roll_no,subject,semester,hours_attended,hours_conducted) "
                            "VALUES(%s,%s,'Sem 2',%s,%s) ON CONFLICT(roll_no,subject,semester) "
                            "DO UPDATE SET hours_attended=EXCLUDED.hours_attended, hours_conducted=EXCLUDED.hours_conducted",
                            (roll, h, attended, conducted)
                        )
        except Exception as e:
            print(f"[seed_db] Error reading {fname}: {e}")
    conn.commit()


def parse_and_load_csv_results(csv_path, section="ECE_B", semester="Sem 2"):
    """
    Parses JNTU/VITS results CSV format (Hall No, Name, Sub1, GP1, Sub2, GP2...) and populates marks & students.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = list(csv.reader(f))
            
        if len(reader) < 3:
            conn.close()
            return False, "Spreadsheet contains no records."
            
        header = reader[0]
        subjects = []
        sub_indices = []
        
        for idx, val in enumerate(header):
            val = val.strip()
            if val and val.lower() not in ["hall no:", "name", "sgpa", "h.t no.", "student name"]:
                subjects.append(val)
                sub_indices.append(idx)
                
        students_count = 0
        for row_idx in range(2, len(reader)):
            row = reader[row_idx]
            if not row or not row[0].strip():
                continue
                
            roll_no = row[0].strip().upper()
            name = row[1].strip()
            
            if roll_no.lower() in ["hall no:", "name", "total", "gp", "h.t no.", "student name", ""]:
                continue
                
            branch = section.split("_")[0] if "_" in section else section
            email = f"{roll_no.lower()}@vits.edu"
            
            # Upsert Student using ON CONFLICT (standard)
            cursor.execute("""
                INSERT INTO students (roll_no, name, dob, email, semester, department, section, branch)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (roll_no) DO UPDATE SET 
                    name = EXCLUDED.name, 
                    section = EXCLUDED.section,
                    branch = EXCLUDED.branch,
                    department = EXCLUDED.department
            """, (roll_no, name, DEFAULT_STUDENT_PASSWORD, email, int(semester.split(" ")[1]), branch, section, branch))
            
            # Ingest marks
            weighted_gp = 0.0
            total_credits = 0.0
            has_failed = False
            
            for sub, col_idx in zip(subjects, sub_indices):
                if col_idx < len(row):
                    score_str = row[col_idx].strip()
                    gp_str = row[col_idx + 1].strip() if col_idx + 1 < len(row) else ""
                    
                    try:
                        score = float(score_str)
                    except ValueError:
                        score = None
                        
                    try:
                        gp = float(gp_str)
                    except ValueError:
                        gp = 0.0
                        
                    exam_type = f"{semester} Final Examinations"
                    cursor.execute("""
                        INSERT INTO marks (roll_no, subject, semester, exam_type, score, grade_point)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (roll_no, subject, semester, exam_type) DO UPDATE SET
                            score = EXCLUDED.score,
                            grade_point = EXCLUDED.grade_point
                    """, (roll_no, sub, semester, exam_type, score, gp))
                    
                    credits = SUBJECT_CREDITS.get(sub, 3.0)
                    weighted_gp += gp * credits
                    total_credits += credits
                    
                    grade, _ = score_to_grade(score)
                    if grade in ['F', 'Ab']:
                        has_failed = True
            
            # Insert SGPA record
            sgpa = round(weighted_gp / total_credits, 2) if total_credits > 0 else 0.0
            cursor.execute("""
                INSERT INTO sgpa_records (roll_no, semester, sgpa, failed)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (roll_no, semester) DO UPDATE SET
                    sgpa = EXCLUDED.sgpa,
                    failed = EXCLUDED.failed
            """, (roll_no, semester, sgpa, 1 if has_failed else 0))
            
            students_count += 1
            
        conn.commit()
        conn.close()
        return True, f"Ingested {students_count} profiles successfully."
    except Exception as e:
        return False, str(e)


def import_results_from_csvs(conn=None):
    close_after = False
    if conn is None:
        conn = get_db_connection()
        close_after = True
    try:
        cursor = conn.cursor()
        if not os.path.exists(RESULTS_CSV_DIR):
            print(f"[Database] Results directory '{RESULTS_CSV_DIR}' not found.")
            return

        csv_files = [f for f in os.listdir(RESULTS_CSV_DIR) if f.lower().endswith(".csv")]
        print(f"[Database] Found {len(csv_files)} results CSV files.")

        for filename in csv_files:
            path = os.path.join(RESULTS_CSV_DIR, filename)
            
            # Match section from filename
            section = None
            name_part = os.path.splitext(filename)[0].upper().replace(" ", "").replace("_", "")
            for c in CLASSES:
                c_clean = c.upper().replace("_", "")
                if c_clean in name_part:
                    section = c
                    break

            if not section:
                print(f"[Database] Skipping results CSV {filename} (no matching section)")
                continue

            print(f"[Database] Processing results for section {section} from file {filename}...")
            
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            parsed = parse_sem1_results_csv(content)
            if not parsed:
                continue

            marks_count = 0
            sgpa_count = 0
            semester = "Sem 1"

            for record in parsed:
                roll = record['roll_no']
                name = record['name']
                branch = decode_roll_branch(roll) or 'ECE'
                
                # Ensure student exists
                cursor.execute('''
                    INSERT INTO students (roll_no, name, dob, semester, branch, department, section)
                    VALUES (%s, %s, %s, 2, %s, %s, %s)
                    ON CONFLICT(roll_no) DO UPDATE SET 
                        name=EXCLUDED.name, 
                        section=EXCLUDED.section,
                        branch=EXCLUDED.branch,
                        department=EXCLUDED.department
                ''', (roll, name, DEFAULT_STUDENT_PASSWORD, branch, branch, section))

                # Insert Sem 1 Marks
                for subj, data in record['subjects'].items():
                    if data['total'] is not None:
                        cursor.execute('''
                            INSERT INTO marks (roll_no, subject, semester, exam_type, score, grade_point)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT(roll_no, subject, semester, exam_type) DO UPDATE SET
                                score = EXCLUDED.score,
                                grade_point = EXCLUDED.grade_point
                        ''', (roll, subj, semester, f"{semester} Final Examinations", data['total'], data['gp']))
                        marks_count += 1

                # Insert Sem 1 SGPA
                cursor.execute('''
                    INSERT INTO sgpa_records (roll_no, semester, sgpa, failed)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT(roll_no, semester) DO UPDATE SET
                        sgpa = EXCLUDED.sgpa,
                        failed = EXCLUDED.failed
                ''', (roll, semester, record['sgpa'], 1 if record['failed'] else 0))
                sgpa_count += 1

            print(f"[Database] Imported {sgpa_count} student SGPA records and {marks_count} marks for {section}.")
        conn.commit()
    except Exception as e:
        print(f"[Database] Error importing results from CSVs: {e}")
    finally:
        if close_after:
            conn.close()

