"""
harvester.py — Smart portal attendance scraper.
Semester-aware. Scheduler-safe. Logs every run.
"""
import os, io, sys, logging, time
from datetime import datetime, timedelta, timezone
import pandas as pd
import requests
from database import CLASSES, get_portal_yr_br

def _check_pg_available():
    if os.environ.get("USE_SQLITE", "").lower() == "true":
        return False
    pg_url = ""
    try:
        import streamlit as _st
        pg_url = _st.secrets.get("database", {}).get("url", "")
    except Exception:
        pass
    if not pg_url:
        pg_url = os.environ.get("DATABASE_URL", "")
    if pg_url:
        try:
            import psycopg2
            if "pooler.supabase.com:5432" in pg_url:
                pg_url = pg_url.replace("pooler.supabase.com:5432", "pooler.supabase.com:6543")
            conn = psycopg2.connect(pg_url, connect_timeout=3)
            conn.close()
            return True
        except Exception:
            pass
    return False

def get_db_connection():
    if _check_pg_available():
        import database_pg
        return database_pg.get_db_connection()
    else:
        import database
        return database.get_db_connection()


logger = logging.getLogger('harvester')
logger.setLevel(logging.INFO)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('[%(levelname)s] %(asctime)s — %(message)s'))
    logger.addHandler(h)

BASE_DIR        = os.path.dirname(__file__)
CSV_BACKUP_DIR  = os.path.join(BASE_DIR, 'csv_backups')

PORTAL_BASE_URL = (os.environ.get('PORTAL_BASE_URL') or 'http://103.52.36.11').rstrip('/')
PORTAL_LOGIN  = f'{PORTAL_BASE_URL}/Attendance/Validate.php'
PORTAL_REPORT = f'{PORTAL_BASE_URL}/Attendance/Crprint.php'
PORTAL_HR     = f'{PORTAL_BASE_URL}/Attendance/Hrprint.php'
PORTAL_SR     = f'{PORTAL_BASE_URL}/Attendance/Srprint.php'
PORTAL_USER   = os.environ.get('PORTAL_USERNAME') or '848'
PORTAL_PASS   = os.environ.get('PORTAL_PASSWORD') or 'vits'


SKIP_COLS = {'S.No.', 'H.T No.', 'Student Name', 'Total', 'Percentage(%)', 'Section'}


def _make_session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Connection': 'keep-alive'
    })
    proxy_url = os.environ.get('PROXY_URL') or os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    if proxy_url:
        s.proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
    return s


def _fetch_student_name_from_srprint(session, roll_no):
    """Fetch official student name from Srprint.php if missing in class report."""
    try:
        url = PORTAL_SR
        payload = {'rno': roll_no, 'fdt': '2026-07-06', 'tdt': '2026-08-10', 'Submit': 'Submit'}
        resp = session.post(url, data=payload, timeout=8)
        if resp.status_code == 200 and 'Name' in resp.text:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')
            for t in soup.find_all('table'):
                txt = t.get_text(separator=' ', strip=True)
                if 'Roll No.' in txt and 'Name' in txt:
                    trs = t.find_all('tr')
                    if len(trs) >= 2:
                        cols = [c.get_text(strip=True) for c in trs[1].find_all(['td', 'th'])]
                        if len(cols) >= 2 and cols[0].strip().upper() == str(roll_no).strip().upper():
                            nm = cols[1].strip()
                            if nm and nm.lower() not in ('name', 'nan', 'none', ''):
                                return nm
    except Exception:
        pass
    return ""


def _login(session):
    session.post(PORTAL_LOGIN,
                 data={'uname': PORTAL_USER, 'pass': PORTAL_PASS},
                 timeout=15)


def is_valid_real_name(name):
    if not name or not isinstance(name, str):
        return False
    s = name.strip().lower()
    if not s or s in ('nan', 'none', 'null', 'student name', 'h.t no.', 'student', 'undefined', 'pending', '-'):
        return False
    if s.startswith('student') or s.startswith('student (') or s.startswith('student('):
        return False
    if s.startswith('24891') or s.startswith('25891') or s.startswith('26895'):
        return False
    return True


def _fetch_df(session, sc, semester, fdt, tdt, max_retries=3):
    """Fetch attendance DataFrame from portal."""
    yr, br = get_portal_yr_br(sc, semester)
    
    # For Year >= 2, section codes on the portal are B, A, C instead of ECE_B, CSE_A
    portal_sc = sc
    if int(yr) >= 2:
        if '_' in sc:
            portal_sc = sc.split('_')[1]
        else:
            portal_sc = 'A'
            
    payload = {'br': br, 'yr': yr, 'sc': portal_sc,
               'fdt': fdt, 'tdt': tdt, 'Submit': 'Submit'}

    for attempt in range(1, max_retries + 1):
        try:
            _login(session)
            resp = session.post(PORTAL_REPORT, data=payload, timeout=(15, 110))
            if resp.status_code != 200:
                raise ValueError(f'HTTP {resp.status_code}')
            html = resp.text
            if 'uname' in html and 'pass' in html:
                raise ValueError('Portal session expired')

            tables = pd.read_html(io.StringIO(html))
            if not tables:
                raise ValueError('No HTML tables found')

            df = None
            for t in tables:
                if not t.empty and 'H.T No.' in t.columns:
                    df = t
                    break

            if df is None:
                for t in tables:
                    if t.empty:
                        continue
                    if t.iloc[0].astype(str).str.contains('H.T No.').any():
                        t.columns = t.iloc[0]
                        t = t[1:].reset_index(drop=True)
                        if 'H.T No.' in t.columns:
                            df = t
                            break

            if df is None:
                raise ValueError('No attendance table with H.T No. found')
            if len(df) < 2:
                raise ValueError('Table has no student rows')

            if 'Section' not in df.columns:
                df.insert(0, 'Section', sc)
            return df
        except Exception as e:
            logger.error(f'[{sc}] Attempt {attempt} failed: {e}')
            if attempt < max_retries:
                time.sleep(2 ** attempt)
            else:
                raise



PORTAL_BRANCH_MAP = {
    'AI&DS': {'single': True,  'sec_name': 'AIDS'},
    'AIML':  {'single': True,  'sec_name': 'AIML'},
    'CE':    {'single': True,  'sec_name': 'CIVIL'},
    'ME':    {'single': True,  'sec_name': 'MECH'},
    'EEE':   {'single': True,  'sec_name': 'EEE'},
    'EIE':   {'single': True,  'sec_name': 'EIE'},
    'IT':    {'single': True,  'sec_name': 'IT'},
    'ECE':   {'single': False, 'prefix': 'ECE'},
    'CSE':   {'single': False, 'prefix': 'CSE'},
    'CSM':   {'single': False, 'prefix': 'CSM'},
    'CSD':   {'single': False, 'prefix': 'DS'},
}


def _sync_hour_wise_for_date(session, conn, sc, semester, target_date):
    """Sync hour-wise attendance for a single section for target_date."""
    yr, br = get_portal_yr_br(sc, semester)
    cursor = conn.cursor()
    
    from concurrent.futures import ThreadPoolExecutor
    
    def fetch_hour_data(hr):
        try:
            payload = {'br': br, 'dt': target_date, 'hr': str(hr), 'Submit': 'Submit'}
            resp = session.post(PORTAL_HR, data=payload, timeout=12)
            if resp.status_code != 200 or 'uname' in resp.text:
                return []
                
            tables = pd.read_html(io.StringIO(resp.text))
            if not tables or tables[0].empty:
                return []
                
            df = tables[0]
            required_cols = {'Section', 'Hour', 'Subject', 'Total Present', 'Total Absent', 'Absentees List'}
            if not required_cols.issubset(df.columns):
                return []
                
            records = []
            for _, row in df.iterrows():
                row_year = str(row.get('Year', '')).strip()
                if row_year != str(yr):
                    continue
                    
                portal_sec = str(row.get('Section')).strip()
                info = PORTAL_BRANCH_MAP.get(br)
                if info:
                    db_sec = info['sec_name'] if info['single'] else f"{info['prefix']}_{portal_sec}"
                else:
                    db_sec = f"{br}_{portal_sec}"

                if db_sec != sc:
                    continue

                subject = str(row.get('Subject', '--')).strip()
                hour_val = int(row.get('Hour', hr))
                tot_pres = row.get('Total Present')
                tot_abs = row.get('Total Absent')
                
                try:
                    tot_pres = int(tot_pres) if str(tot_pres).isdigit() else 0
                    tot_abs = int(tot_abs) if str(tot_abs).isdigit() else 0
                except Exception:
                    tot_pres, tot_abs = 0, 0
                    
                absentees_val = str(row.get('Absentees List', '--')).strip()
                
                if not absentees_val or absentees_val in ('--', 'nan', 'None', ''):
                    records.append((target_date, br, db_sec, hour_val, subject, tot_pres, tot_abs, ''))
                else:
                    roll_nos = [r.strip().upper() for r in absentees_val.split(',') if r.strip() and r.strip() != '--']
                    for r_no in roll_nos:
                        records.append((target_date, br, db_sec, hour_val, subject, tot_pres, tot_abs, r_no))
            return records
        except Exception as e:
            logger.warning(f'Failed to fetch hour-wise for {sc} hour {hr} on {target_date}: {e}')
            return []

    all_records = []
    with ThreadPoolExecutor(max_workers=7) as executor:
        results = executor.map(fetch_hour_data, range(1, 8))
        for res in results:
            if res:
                all_records.extend(res)
                
    if all_records:
        cursor.executemany('''
            INSERT INTO hour_wise_attendance 
            (date, branch, section, hour, subject, total_present, total_absent, roll_no)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (date, section, hour, subject, roll_no) DO NOTHING
        ''', all_records)


def sync_campus_hour_wise(target_date, session=None, conn=None):
    """
    High-speed whole campus hour-wise sync for target_date.
    Scrapes all 11 branches x 7 hours in ~45s and commits to hour_wise_attendance.
    """
    logger.info(f"[HourSync] Scraping campus hour-wise attendance for {target_date}...")
    close_session = False
    close_conn = False
    if session is None:
        session = _make_session()
        _login(session)
        close_session = True
    if conn is None:
        conn = get_db_connection()
        close_conn = True
        
    cursor = conn.cursor()
    all_records = []
    
    for br, info in PORTAL_BRANCH_MAP.items():
        for hr in range(1, 8):
            try:
                r = session.post(PORTAL_HR, data={'br': br, 'dt': target_date, 'hr': str(hr), 'Submit': 'Submit'}, timeout=12)
                if 'TOTAL PRESENT' in r.text.upper() or 'ABSENTEES' in r.text.upper():
                    tables = pd.read_html(io.StringIO(r.text))
                    if tables and not tables[0].empty:
                        df = tables[0]
                        df_y2 = df[df['Year'].astype(str) == '2']
                        for _, row in df_y2.iterrows():
                            portal_sec = str(row.get('Section')).strip()
                            subject = str(row.get('Subject', '--')).strip()
                            tot_pres = int(row['Total Present']) if str(row.get('Total Present', '')).isdigit() else 0
                            tot_abs  = int(row['Total Absent']) if str(row.get('Total Absent', '')).isdigit() else 0
                            db_sec = info['sec_name'] if info['single'] else f"{info['prefix']}_{portal_sec}"
                            
                            abs_list = str(row.get('Absentees List', '--')).strip()
                            if not abs_list or abs_list in ('--', 'nan', 'None', ''):
                                all_records.append((target_date, br, db_sec, hr, subject, tot_pres, tot_abs, ''))
                            else:
                                rolls = [x.strip().upper() for x in abs_list.split(',') if x.strip() and x.strip() != '--']
                                for roll in rolls:
                                    all_records.append((target_date, br, db_sec, hr, subject, tot_pres, tot_abs, roll))
            except Exception as e:
                logger.warning(f"[HourSync] Error {br} Hr {hr} on {target_date}: {e}")
                
    if all_records:
        logger.info(f"[HourSync] Inserting {len(all_records)} hour-attendance rows for {target_date}...")
        try:
            cursor.executemany('''
                INSERT INTO hour_wise_attendance 
                (date, branch, section, hour, subject, total_present, total_absent, roll_no)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (date, section, hour, subject, roll_no) DO NOTHING
            ''', all_records)
            conn.commit()
            logger.info(f"[HourSync] Saved {len(all_records)} records for {target_date} successfully!")
        except Exception as e:
            logger.error(f"[HourSync] Failed to commit records for {target_date}: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
                
    if close_conn:
        try:
            conn.close()
        except Exception:
            pass
    return len(all_records)


def sync_campus_hour_wise_catchup(session=None, conn=None, days_back=7):
    """
    Checks hour_wise_attendance for missing dates in the last `days_back` days (excluding Sundays),
    and scrapes all missing dates plus today. Guarantees 0-gap bunk analysis data.
    """
    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    today_str = ist_now.strftime('%Y-%m-%d')
    cutoff_dt = (ist_now - timedelta(days=days_back)).date()
    cutoff_str = cutoff_dt.strftime('%Y-%m-%d')
    
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    cursor = conn.cursor()
    
    # Get existing dates in DB
    existing_dates = set()
    try:
        cursor.execute("SELECT DISTINCT date FROM hour_wise_attendance WHERE date >= ?", (cutoff_str,))
        for r in cursor.fetchall():
            d_val = r[0] if isinstance(r, (list, tuple)) else r['date']
            if d_val:
                existing_dates.add(str(d_val)[:10])
    except Exception as e:
        logger.warning(f"[CatchUp] Could not query existing hour-wise dates: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
            
    # Compute dates needing sync (Mon-Sat only)
    dates_to_sync = []
    curr = cutoff_dt
    today_dt = ist_now.date()
    while curr <= today_dt:
        if curr.weekday() != 6:  # Skip Sunday
            c_str = curr.strftime('%Y-%m-%d')
            # If not in DB, or if it is today (to get today's latest classes)
            if c_str not in existing_dates or c_str == today_str:
                dates_to_sync.append(c_str)
        curr += timedelta(days=1)
        
    logger.info(f"[CatchUp] Missing/pending hour-wise dates to scrape: {dates_to_sync}")
    
    if session is None:
        session = _make_session()
        _login(session)
        
    total_synced = 0
    for d in dates_to_sync:
        n = sync_campus_hour_wise(d, session=session, conn=conn)
        total_synced += n
        
    if close_conn:
        try:
            conn.close()
        except Exception:
            pass
            
    return total_synced


def scrape_portal(start_date=None, end_date=None, section=None,
                  semester=None, dynamic_conn=None, max_retries=3, force=False):
    """Main scrape function. Returns (success, message)."""
    if _check_pg_available():
        from database_pg import get_config_map
    else:
        from database import get_config_map
    conn_cfg = dynamic_conn if dynamic_conn is not None else get_db_connection()
    cfg      = get_config_map(conn_cfg)
    if dynamic_conn is None:
        conn_cfg.close()

    # Resolve active semester from config if not specified
    if semester is None:
        semester = cfg.get('active_semester', 'Sem 3')

    try:
        sem_num = int(str(semester).replace('Sem', '').strip())
    except Exception:
        sem_num = 2

    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    tdt = end_date   or ist_now.strftime('%Y-%m-%d')
    sc  = section    or 'ECE_B'

    # Class-wise report queries the cumulative semester data directly from start_date to today
    sem_start = cfg.get('start_date', '2026-07-06')
    fdt = start_date or sem_start

    logger.info(f'Scraping {sc} | {semester} | {fdt} → {tdt}')

    session       = _make_session()
    conn          = dynamic_conn if dynamic_conn is not None else get_db_connection()
    cursor        = conn.cursor()

    # 1. Evening Scrape (after 16:00 IST / 4:00 PM IST) OR Manual force=True:
    #    -> 100% MANDATORY DAILY SCRAPE. NEVER SKIPS!
    # 2. Morning Scrape (before 16:00 IST / 4:00 PM IST):
    #    -> Precautionary check. Skip ONLY if yesterday's mandatory evening scrape (after 4:00 PM IST)
    #       already succeeded within the last 18 hours.
    if not force:
        try:
            curr_hour = ist_now.hour
            is_evening_slot = (curr_hour >= 16)

            if not is_evening_slot:
                # Precautionary Morning Slot (< 16:00 IST):
                # Check if an evening scrape succeeded within the last 18 hours
                cutoff_dt = ist_now - timedelta(hours=18)
                cutoff_time = cutoff_dt.strftime('%Y-%m-%d %H:%M:%S')
                skip_msg = "Recent evening attendance already synced within last 18 hours"

                cursor.execute('''
                    SELECT scraped_at FROM scrape_log 
                    WHERE section = ? AND status = 'success' AND scraped_at >= ?
                    ORDER BY id DESC LIMIT 1
                ''', (sc, cutoff_time))

                res = cursor.fetchone()
                if res:
                    scraped_time = res[0]
                    logger.info(f'[{sc}] {skip_msg} (at {scraped_time}). Skipping precautionary morning run.')
                    if dynamic_conn is None:
                        conn.close()
                    return True, f'[{sc}] {skip_msg} (at {scraped_time}).'
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

    # Target today's date [tdt] (with last 3 days fallback) for fast 3-minute scrape!
    target_dates = [tdt]
    success_dates = []
    student_count = 0
    last_df       = None
    t_start       = time.time()

    for target_date in target_dates:
        try:
            valid_df = None
            actual_date = target_date
            dates_to_try = [target_date]
            yesterday_str = (datetime.strptime(target_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
            if yesterday_str >= fdt and yesterday_str != target_date:
                dates_to_try.append(yesterday_str)
                
            last_err = None
            for test_date in dates_to_try:
                try:
                    res_df = _fetch_df(session, sc, semester, fdt, test_date, max_retries=2)
                    if res_df is not None and len(res_df) > 1:
                        valid_df = res_df
                        actual_date = test_date
                        break
                except Exception as e:
                    last_err = e
                    continue
                        
            if valid_df is None or len(valid_df) <= 1:
                raise ValueError(f"No valid attendance data found for {sc}: {last_err}")

            df = valid_df
            target_date = actual_date
            student_count = max(student_count, len(df) - 1)
            conducted_row = df.iloc[0]
            subjects = [c for c in df.columns
                        if c not in SKIP_COLS and not str(c).startswith('Unnamed')]

            for sub in subjects:
                try:
                    cursor.execute('''
                        INSERT INTO subjects(subject_code,subject_name,semester,section)
                        VALUES(?,?,?,?)
                        ON CONFLICT(subject_code, semester, section) DO NOTHING
                    ''', (sub, sub, semester, sc))
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

            branch = sc.split('_')[0] if '_' in sc else sc

            for idx in range(1, len(df)):
                row     = df.iloc[idx]
                roll_no = str(row.get('H.T No.', '')).strip().upper()
                if not roll_no or roll_no.lower() in ('nan', 'none', '', 'h.t no.', 'student name'):
                    continue

                raw_name = str(row.get('Student Name', '')).strip()
                clean_name = raw_name if raw_name.lower() not in ('nan', 'none', '', 'null', 'student name', 'h.t no.') else ''

                try:
                    cursor.execute('SELECT name FROM students WHERE roll_no=?', (roll_no,))
                    existing_row = cursor.fetchone()
                    existing_name = existing_row[0] if existing_row else None

                    if not existing_row:
                        ins_name = clean_name if is_valid_real_name(clean_name) else f"Student ({roll_no})"
                        cursor.execute('''
                            INSERT INTO students(roll_no,name,dob,email,semester,department,section,branch)
                            VALUES(?,?,?,?,?,?,?,?)
                        ''', (roll_no, ins_name, 'PENDING',
                              f'{roll_no.lower()}@vits.edu', sem_num, branch, sc, branch))
                        student_count += 1
                    else:
                        # Existing student row found. NEVER overwrite a valid real full name!
                        if is_valid_real_name(clean_name) and not is_valid_real_name(existing_name):
                            cursor.execute('UPDATE students SET name=? WHERE roll_no=?', (clean_name, roll_no))
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

                for sub in subjects:
                    try:
                        cond_v = pd.to_numeric(conducted_row[sub], errors='coerce')
                        att_v  = pd.to_numeric(row[sub],           errors='coerce')
                        if pd.isna(cond_v) or pd.isna(att_v):
                            continue
                        cond, att = int(cond_v), int(att_v)

                        pct = round(att / cond * 100, 2) if cond > 0 else 0.0
                        cursor.execute('''
                            INSERT INTO attendance_history
                                (snapshot_date,roll_no,subject_code,running_attended,running_conducted,percentage)
                            VALUES(?,?,?,?,?,?)
                            ON CONFLICT(roll_no,subject_code,snapshot_date) DO UPDATE SET
                                running_attended=excluded.running_attended,
                                running_conducted=excluded.running_conducted,
                                percentage=excluded.percentage
                        ''', (target_date, roll_no, sub, att, cond, pct))
                    except Exception:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        continue

            # Commit after each successful date to save progress
            try:
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass

            success_dates.append(target_date)
            last_df = df
        except Exception as e:
            logger.error(f'[{sc}] Failed for {target_date}: {e}')
            try:
                conn.rollback()
            except Exception:
                pass

    # After processing all dates, update aggregate attendance/student tables using the latest successful date's data
    if last_df is not None:
        try:
            conducted_row = last_df.iloc[0]
            subjects = [c for c in last_df.columns
                        if c not in SKIP_COLS and not str(c).startswith('Unnamed')]
            branch = sc.split('_')[0] if '_' in sc else sc
            
            for idx in range(1, len(last_df)):
                row     = last_df.iloc[idx]
                roll_no = str(row.get('H.T No.', '')).strip().upper()
                name    = str(row.get('Student Name', '')).strip()

                if not roll_no or roll_no.lower() in ('nan', 'none', ''):
                    continue

                # Update student details from latest data (NEVER overwrite valid real names with placeholders)
                try:
                    if is_valid_real_name(name):
                        cursor.execute('''
                            UPDATE students SET name=?,section=?,department=?,branch=?
                            WHERE roll_no=?
                        ''', (name, sc, branch, branch, roll_no))
                    else:
                        cursor.execute('''
                            UPDATE students SET section=?,department=?,branch=?
                            WHERE roll_no=?
                        ''', (sc, branch, branch, roll_no))
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

                for sub in subjects:
                    try:
                        cond_v = pd.to_numeric(conducted_row[sub], errors='coerce')
                        att_v  = pd.to_numeric(row[sub],           errors='coerce')
                        if pd.isna(cond_v) or pd.isna(att_v):
                            continue
                        cond, att = int(cond_v), int(att_v)

                        cursor.execute('''
                            INSERT INTO attendance(roll_no,subject,semester,hours_attended,hours_conducted)
                            VALUES(?,?,?,?,?)
                            ON CONFLICT(roll_no,subject,semester) DO UPDATE SET
                                hours_attended=excluded.hours_attended,
                                hours_conducted=excluded.hours_conducted
                        ''', (roll_no, sub, semester, att, cond))
                    except Exception:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        continue

            # Commit aggregate updates
            try:
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
        except Exception as update_e:
            logger.error(f'[{sc}] Failed to update aggregate attendance/students tables: {update_e}')
            try:
                conn.rollback()
            except Exception:
                pass

    # Interpolate attendance gaps dynamically to populate daily records for the last 30 days
    if success_dates:
        try:
            fill_attendance_history_gaps(conn, sc, fdt, tdt)
            conn.commit()
        except Exception as fill_e:
            logger.warning(f'Failed to interpolate attendance history: {fill_e}')
            try:
                conn.rollback()
            except Exception:
                pass
    # Sync hour-wise attendance details for the successfully scraped dates
    for s_date in success_dates:
        try:
            _sync_hour_wise_for_date(session, conn, sc, semester, s_date)
            conn.commit()
        except Exception as hw_e:
            logger.warning(f'[{sc}] Failed to sync hour-wise attendance for {s_date}: {hw_e}')
            try:
                conn.rollback()
            except Exception:
                pass


    duration = round(time.time() - t_start, 2)
    status   = 'success' if success_dates else 'failed'
    ist_now_ts = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    now      = ist_now_ts.strftime('%Y-%m-%d %H:%M:%S')

    # Always ensure clean transaction state before writing logs
    try:
        cursor.execute("SELECT 1")
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass

    # Write scrape log
    try:
        if success_dates:
            cursor.execute("UPDATE config SET value=? WHERE key='last_scraped_at'", (now,))
            cursor.execute("UPDATE config SET value=? WHERE key='start_date'",      (fdt,))
            cursor.execute("UPDATE config SET value=? WHERE key='end_date'",        (tdt,))
        cursor.execute('''
            INSERT INTO scrape_log(scraped_at,section,students,status,duration)
            VALUES(?,?,?,?,?)
        ''', (now, sc, student_count, status, duration))
        conn.commit()
    except Exception as log_e:
        logger.error(f'Failed to write scrape log: {log_e}')
        try:
            conn.rollback()
        except Exception:
            pass

    if dynamic_conn is None:
        try:
            conn.close()
        except Exception:
            pass

    # Save per-section CSV backup
    if last_df is not None:
        try:
            os.makedirs(CSV_BACKUP_DIR, exist_ok=True)
            last_df.to_csv(os.path.join(CSV_BACKUP_DIR, f'attendance_{sc}.csv'), index=False)
        except Exception as e:
            logger.warning(f'CSV backup failed: {e}')

    if not success_dates:
        return False, f'[{sc}] Failed to scrape any data.'
    return True, f'[{sc}] Synced {student_count} students | {len(success_dates)} snapshots | {duration}s'


def bulk_scrape_all(semester=None, start_date=None, end_date=None, progress_callback=None, force=False):
    """Scrape all sections sequentially."""
    total = len(CLASSES)
    results = []

    def _write_progress(section, current, pct_done):
        """Write scrape status to DB config table — shared across all sessions."""
        try:
            conn = get_db_connection()
            conn.execute("UPDATE config SET value=? WHERE key='scrape_status'",
                         (f'running:{section}:{current}:{total}',))
            conn.commit()
            conn.close()
        except Exception:
            pass

    # Mark as started
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO config(key,value) VALUES('scrape_status','running:Starting:0:" + str(total) + "') "
                     "ON CONFLICT(key) DO UPDATE SET value=excluded.value")
        conn.commit()
        conn.close()
    except Exception:
        pass

    # 1. Run whole-campus hour-wise catch-up first (~45-60s for all branches and any missing days)
    try:
        logger.info("[BulkScrape] Running campus-wide hour attendance catch-up...")
        sync_campus_hour_wise_catchup()
    except Exception as hw_err:
        logger.warning(f"[BulkScrape] Hour-wise catchup encountered an issue: {hw_err}")

    # 2. Scrape cumulative class-wise reports for each section concurrently (max 3 workers)
    completed_count = 0
    results_dict = {}
    import threading
    import concurrent.futures
    lock = threading.Lock()

    def _worker(sec):
        nonlocal completed_count
        ok, msg = scrape_portal(
            start_date=start_date, end_date=end_date,
            section=sec, semester=semester, dynamic_conn=None, force=force
        )
        with lock:
            completed_count += 1
            cur_idx = completed_count
            results_dict[sec] = {'section': sec, 'ok': ok, 'msg': msg}
            _write_progress(sec, cur_idx, cur_idx / total)
            if progress_callback:
                try:
                    progress_callback(sec, cur_idx, total)
                except Exception:
                    pass
        logger.info(f"[{cur_idx}/{total}] {sec}: {msg}")
        return {'section': sec, 'ok': ok, 'msg': msg}

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(_worker, sec): sec for sec in CLASSES}
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                sec = futures[future]
                logger.error(f"[{sec}] Worker thread failed: {e}")
                with lock:
                    if sec not in results_dict:
                        results_dict[sec] = {'section': sec, 'ok': False, 'msg': str(e)}

    results = [results_dict.get(sec, {'section': sec, 'ok': False, 'msg': 'Unknown error'}) for sec in CLASSES]

    # Mark as done
    try:
        conn = get_db_connection()
        conn.execute("UPDATE config SET value='idle' WHERE key='scrape_status'")
        conn.commit()
        conn.close()
    except Exception:
        pass

    return results


def start_scheduler(app):
    """Start APScheduler — only in main worker, not Flask reloader."""
    if app.debug and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        logger.info('[Scheduler] Skipping in Flask reloader process')
        return None
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        if _check_pg_available():
            from database_pg import get_config_map, backup_db
        else:
            from database import get_config_map, backup_db

        def _daily_job():
            with app.app_context():
                conn_cfg = get_db_connection()
                cfg      = get_config_map(conn_cfg)
                conn_cfg.close()
                sem = cfg.get('active_semester', 'Sem 2')
                logger.info(f'[Scheduler] Daily auto-scrape | {sem}')
                results = bulk_scrape_all(semester=sem)
                ok      = sum(1 for r in results if r['ok'])
                logger.info(f'[Scheduler] {ok}/{len(results)} sections synced')
                bp = backup_db()
                if bp:
                    logger.info(f'[Scheduler] Backup: {bp}')

        scheduler = BackgroundScheduler(timezone='Asia/Kolkata')
        scheduler.add_job(_daily_job, 'cron', hour=18, minute=0, id='daily_scrape')
        scheduler.start()
        logger.info('[Scheduler] Daily scrape scheduled at 18:00 IST')
        return scheduler
    except ImportError:
        logger.warning('[Scheduler] apscheduler not installed — daily scrape disabled')
        return None


def _row_to_dict(row, cursor_description=None):
    """Convert a DB row to dict safely — works on SQLite Row, psycopg2 tuples, and _RowWrapper."""
    if row is None:
        return None
    # If it already has .keys() and [] access (SQLite Row, _RowWrapper), build dict from keys
    if hasattr(row, 'keys'):
        try:
            return {k: row[k] for k in row.keys()}
        except Exception:
            pass
    # psycopg2 RealDictRow supports dict()
    try:
        return dict(row)
    except (TypeError, ValueError):
        pass
    # Tuple with cursor description
    if cursor_description:
        return dict(zip([d[0] for d in cursor_description], row))
    return {}


def fill_attendance_history_gaps(conn, section, fdt, tdt):
    cursor = conn.cursor()
    # Get all students in this section
    cursor.execute('SELECT roll_no FROM students WHERE section=?', (section,))
    students = []
    for r in cursor.fetchall():
        try:
            students.append(r['roll_no'])
        except Exception:
            students.append(r[0])

    # Get all subjects for this section
    cursor.execute('SELECT DISTINCT subject_code FROM subjects WHERE section=?', (section,))
    subjects = []
    for r in cursor.fetchall():
        try:
            subjects.append(r['subject_code'])
        except Exception:
            subjects.append(r[0])
    
    if not students or not subjects:
        return
        
    start_date = datetime.strptime(fdt, '%Y-%m-%d').date()
    end_date = datetime.strptime(tdt, '%Y-%m-%d').date()
    
    # Generate list of all calendar dates
    delta = (end_date - start_date).days
    all_dates = [start_date + timedelta(days=i) for i in range(delta + 1)]
    all_dates_str = [d.strftime('%Y-%m-%d') for d in all_dates]
    
    # Fetch all history snapshots for students in this section in one single query
    placeholders = ','.join('?' for _ in students)
    history_rows = cursor.execute(f'''
        SELECT roll_no, subject_code, snapshot_date, running_attended, running_conducted
        FROM attendance_history
        WHERE snapshot_date BETWEEN ? AND ? AND roll_no IN ({placeholders})
        ORDER BY snapshot_date ASC
    ''', (fdt, tdt, *students)).fetchall()
    
    # Group history by (roll_no, subject_code)
    history_by_student_subject = {}
    for r in history_rows:
        key = (r['roll_no'], r['subject_code'])
        history_by_student_subject.setdefault(key, []).append(r)
        
    insert_data = []
    filled_keys = set()
    
    for roll in students:
        for sub in subjects:
            key = (roll, sub)
            rows = history_by_student_subject.get(key, [])
            
            if not rows:
                continue
                
            # Build a map of date -> (attended, conducted)
            existing_map = {}
            for r in rows:
                existing_map[r['snapshot_date']] = (r['running_attended'], r['running_conducted'])
                
            # If we only have 1 snapshot, forward fill it to all dates
            if len(rows) == 1:
                att, cond = rows[0]['running_attended'], rows[0]['running_conducted']
                pct = round(att / cond * 100, 2) if cond > 0 else 0.0
                for d_str in all_dates_str:
                    if d_str not in existing_map:
                        insert_data.append((d_str, roll, sub, att, cond, pct))
                        filled_keys.add((d_str, roll, sub))
                continue
                
            # Discrete step-wise interpolation for gaps
            sorted_dates = sorted(existing_map.keys())
            
            if len(sorted_dates) == 1:
                att, cond = existing_map[sorted_dates[0]]
                pct = round(att / cond * 100, 2) if cond > 0 else 0.0
                for d_str in all_dates_str:
                    if d_str not in existing_map:
                        insert_data.append((d_str, roll, sub, att, cond, pct))
                        filled_keys.add((d_str, roll, sub))
                continue
                
            # For each consecutive pair of dates, fill the gap discretely
            for idx in range(len(sorted_dates) - 1):
                prev_date_str = sorted_dates[idx]
                next_date_str = sorted_dates[idx+1]
                
                p_date = datetime.strptime(prev_date_str, '%Y-%m-%d').date()
                n_date = datetime.strptime(next_date_str, '%Y-%m-%d').date()
                
                delta_days = (n_date - p_date).days
                if delta_days <= 1:
                    continue
                    
                gap_dates = [p_date + timedelta(days=i) for i in range(1, delta_days)]
                
                att_p, cond_p = existing_map[prev_date_str]
                att_n, cond_n = existing_map[next_date_str]
                
                diff_cond = cond_n - cond_p
                diff_att = att_n - att_p
                diff_bunks = max(0, diff_cond - diff_att)
                
                # Weekdays in this gap
                gap_weekdays_indices = [i for i, d in enumerate(gap_dates) if d.weekday() < 5]
                if not gap_weekdays_indices:
                    gap_weekdays_indices = list(range(len(gap_dates)))
                    
                conducted_distribution = [0] * len(gap_dates)
                if gap_weekdays_indices and diff_cond > 0:
                    import random
                    random.seed(hash(roll + sub + prev_date_str))
                    for _ in range(diff_cond):
                        idx_choice = random.choice(gap_weekdays_indices)
                        conducted_distribution[idx_choice] += 1
                        
                bunk_distribution = [0] * len(gap_dates)
                conducted_events = []
                for i, count in enumerate(conducted_distribution):
                    for _ in range(count):
                        conducted_events.append(i)
                        
                if conducted_events and diff_bunks > 0:
                    import random
                    random.seed(hash(roll + sub + next_date_str))
                    bunk_indices = random.sample(conducted_events, min(diff_bunks, len(conducted_events)))
                    for idx_choice in bunk_indices:
                        bunk_distribution[idx_choice] += 1
                        
                current_cond = cond_p
                current_att = att_p
                for i, d in enumerate(gap_dates):
                    d_str = d.strftime('%Y-%m-%d')
                    current_cond += conducted_distribution[i]
                    current_att += conducted_distribution[i] - bunk_distribution[i]
                    pct = round(current_att / current_cond * 100, 2) if current_cond > 0 else 0.0
                    insert_data.append((d_str, roll, sub, current_att, current_cond, pct))
                    filled_keys.add((d_str, roll, sub))
                    
            # Extrapolate outside sorted_dates range if all_dates_str starts earlier or ends later
            first_date_str = sorted_dates[0]
            last_date_str = sorted_dates[-1]
            att_f, cond_f = existing_map[first_date_str]
            pct_f = round(att_f / cond_f * 100, 2) if cond_f > 0 else 0.0
            
            att_l, cond_l = existing_map[last_date_str]
            pct_l = round(att_l / cond_l * 100, 2) if cond_l > 0 else 0.0
            
            for d_str in all_dates_str:
                if d_str in existing_map:
                    continue
                # Check if it was filled by the gap loop
                if (d_str, roll, sub) in filled_keys:
                    continue
                    
                if d_str < first_date_str:
                    insert_data.append((d_str, roll, sub, att_f, cond_f, pct_f))
                    filled_keys.add((d_str, roll, sub))
                elif d_str > last_date_str:
                    insert_data.append((d_str, roll, sub, att_l, cond_l, pct_l))
                    filled_keys.add((d_str, roll, sub))
                
    if insert_data:
        # Check if we are running on PostgreSQL (which wraps cursor with _CursorProxy)
        if hasattr(cursor, '_cur') and hasattr(cursor._pg, '_conn'):
            import psycopg2.extras
            # Batch into chunks of 500 to avoid Supabase statement timeout
            batch_size = 500
            for i in range(0, len(insert_data), batch_size):
                batch = insert_data[i:i + batch_size]
                try:
                    psycopg2.extras.execute_values(
                        cursor._cur,
                        '''
                        INSERT INTO attendance_history
                            (snapshot_date, roll_no, subject_code, running_attended, running_conducted, percentage)
                        VALUES %s
                        ON CONFLICT(roll_no, subject_code, snapshot_date) DO UPDATE SET
                            running_attended = EXCLUDED.running_attended,
                            running_conducted = EXCLUDED.running_conducted,
                            percentage = EXCLUDED.percentage
                        ''',
                        batch
                    )
                    conn.commit()
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
        else:
            # Fallback for SQLite
            cursor.executemany('''
                INSERT INTO attendance_history
                    (snapshot_date, roll_no, subject_code, running_attended, running_conducted, percentage)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(roll_no, subject_code, snapshot_date) DO UPDATE SET
                    running_attended = EXCLUDED.running_attended,
                    running_conducted = EXCLUDED.running_conducted,
                    percentage = EXCLUDED.percentage
            ''', insert_data)


if __name__ == '__main__':
    sec = sys.argv[1] if len(sys.argv) > 1 else 'ECE_B'
    sem = sys.argv[2] if len(sys.argv) > 2 else 'Sem 2'
    ok, msg = scrape_portal(section=sec, semester=sem)
    logger.info(msg)
    sys.exit(0 if ok else 1)
