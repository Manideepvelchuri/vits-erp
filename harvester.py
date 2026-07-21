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

PORTAL_LOGIN  = 'http://103.52.36.11/Attendance/Validate.php'
PORTAL_REPORT = 'http://103.52.36.11/Attendance/Crprint.php'
PORTAL_USER   = os.environ.get('PORTAL_USERNAME') or '848'
PORTAL_PASS   = os.environ.get('PORTAL_PASSWORD') or 'vits'

SKIP_COLS = {'S.No.', 'H.T No.', 'Student Name', 'Total', 'Percentage(%)', 'Section'}


def _make_session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Content-Type': 'application/x-www-form-urlencoded'
    })
    return s


def _login(session):
    session.post(PORTAL_LOGIN,
                 data={'uname': PORTAL_USER, 'pass': PORTAL_PASS},
                 timeout=15)


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
            resp = session.post(PORTAL_REPORT, data=payload, timeout=(10, 180))
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



def _sync_hour_wise_for_date(session, conn, sc, semester, target_date):
    yr, br = get_portal_yr_br(sc, semester)
    cursor = conn.cursor()
    
    from concurrent.futures import ThreadPoolExecutor
    
    def fetch_hour_data(hr):
        try:
            payload = {'br': br, 'dt': target_date, 'hr': str(hr), 'Submit': 'Submit'}
            resp = session.post('http://103.52.36.11/Attendance/Hrprint.php', data=payload, timeout=10)
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
                    
                section = str(row.get('Section')).strip()
                subject = str(row.get('Subject')).strip()
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
                    records.append((target_date, br, section, hour_val, subject, tot_pres, tot_abs, ''))
                else:
                    roll_nos = [r.strip().upper() for r in absentees_val.split(',') if r.strip()]
                    for r_no in roll_nos:
                        records.append((target_date, br, section, hour_val, subject, tot_pres, tot_abs, r_no))
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


def scrape_portal(start_date=None, end_date=None, section=None,
                  semester=None, dynamic_conn=None, max_retries=3):
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

    fdt = start_date or cfg.get('start_date', '2026-01-27')
    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    tdt = end_date   or ist_now.strftime('%Y-%m-%d')
    sc  = section    or 'ECE_B'

    logger.info(f'Scraping {sc} | {semester} | {fdt} → {tdt}')

    session       = _make_session()
    conn          = dynamic_conn if dynamic_conn is not None else get_db_connection()
    cursor        = conn.cursor()

    # Check if section has history. If it does, only scrape today's date to keep it 5x faster.
    has_history = False
    try:
        has_history = cursor.execute('''
            SELECT COUNT(*) FROM attendance_history 
            WHERE roll_no IN (SELECT roll_no FROM students WHERE section = ?)
        ''', (sc,)).fetchone()[0] > 0
    except Exception:
        pass

    target_dates = []
    if has_history:
        target_dates = [tdt]
    else:
        try:
            base  = datetime.strptime(tdt, '%Y-%m-%d').date()
            start = datetime.strptime(fdt, '%Y-%m-%d').date()
            # Fetch weekly snapshots to build initial history
            for offset in [28, 21, 14, 7, 0]:
                d = base - timedelta(days=offset)
                if d >= start:
                    target_dates.append(d.strftime('%Y-%m-%d'))
        except Exception:
            target_dates = [tdt]

    if tdt not in target_dates:
        target_dates.append(tdt)
    success_dates = []
    student_count = 0
    last_df       = None
    t_start       = time.time()

    for target_date in target_dates:
        try:
            valid_df = None
            actual_date = target_date
            ist_today_str = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d')
            max_fallback_days = 5 if target_date == ist_today_str else 1
            
            for offset in range(max_fallback_days):
                test_date = (datetime.strptime(target_date, '%Y-%m-%d') - timedelta(days=offset)).strftime('%Y-%m-%d')
                if test_date < fdt:
                    break
                try:
                    valid_df = _fetch_df(session, sc, semester, fdt, test_date, max_retries)
                    actual_date = test_date
                    break
                except Exception as e:
                    if offset == max_fallback_days - 1:
                        raise ValueError(f"All fallback dates failed: {e}")
                        
            df = valid_df
            target_date = actual_date
            conducted_row = df.iloc[0]
            subjects = [c for c in df.columns
                        if c not in SKIP_COLS and not str(c).startswith('Unnamed')]

            for sub in subjects:
                cursor.execute('''
                    INSERT INTO subjects(subject_code,subject_name,semester,section)
                    VALUES(?,?,?,?)
                    ON CONFLICT(subject_code, semester, section) DO NOTHING
                ''', (sub, sub, semester, sc))

            branch = sc.split('_')[0] if '_' in sc else sc

            for idx in range(1, len(df)):
                row     = df.iloc[idx]
                roll_no = str(row.get('H.T No.', '')).strip().upper()
                name    = str(row.get('Student Name', '')).strip()

                if not roll_no or roll_no.lower() in ('nan', 'none', ''):
                    continue

                cursor.execute('SELECT COUNT(*) FROM students WHERE roll_no=?', (roll_no,))
                if not cursor.fetchone()[0]:
                    cursor.execute('''
                        INSERT INTO students(roll_no,name,dob,email,semester,department,section,branch)
                        VALUES(?,?,?,?,?,?,?,?)
                    ''', (roll_no, name, 'PENDING',
                          f'{roll_no.lower()}@vits.edu', sem_num, branch, sc, branch))
                    student_count += 1
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
                        continue

            success_dates.append(target_date)
            last_df = df
        except Exception as e:
            logger.error(f'[{sc}] Failed for {target_date}: {e}')

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

                # Update student details from latest data
                cursor.execute('''
                    UPDATE students SET name=?,section=?,department=?,branch=?
                    WHERE roll_no=?
                ''', (name, sc, branch, branch, roll_no))

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
                        continue
        except Exception as update_e:
            logger.error(f'[{sc}] Failed to update aggregate attendance/students tables: {update_e}')

    # Interpolate attendance gaps dynamically to populate daily records for the last 30 days
    if success_dates:
        try:
            fill_attendance_history_gaps(conn, sc, fdt, tdt)
        except Exception as fill_e:
            logger.warning(f'Failed to interpolate attendance history: {fill_e}')
    # Sync hour-wise attendance details for the successfully scraped dates
    for s_date in success_dates:
        try:
            _sync_hour_wise_for_date(session, conn, sc, semester, s_date)
        except Exception as hw_e:
            logger.warning(f'[{sc}] Failed to sync hour-wise attendance for {s_date}: {hw_e}')



    duration = round(time.time() - t_start, 2)
    status   = 'success' if success_dates else 'failed'
    ist_now_ts = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    now      = ist_now_ts.strftime('%Y-%m-%d %H:%M:%S')

    # Detect if transaction has been aborted
    is_aborted = False
    try:
        cursor.execute("SELECT 1")
    except Exception:
        is_aborted = True
        try:
            conn.rollback()
        except Exception:
            pass

    # If the transaction was aborted, or we scraped 0 dates successfully, write a failed log
    if is_aborted or not success_dates:
        try:
            # Open a fresh log insert (which is clean now after rollback)
            cursor.execute('''
                INSERT INTO scrape_log(scraped_at,section,students,status,duration)
                VALUES(?,?,?,?,?)
            ''', (now, sc, 0, 'failed', duration))
            conn.commit()
        except Exception as log_e:
            logger.error(f'Failed to write scrape log: {log_e}')
            try:
                conn.rollback()
            except Exception:
                pass
    else:
        # Success path! Update config and write success log
        try:
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


def bulk_scrape_all(semester=None, start_date=None, end_date=None, progress_callback=None):
    """Scrape all sections. Writes live progress to DB config so all sessions can see it."""
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

    for idx, sec in enumerate(CLASSES):
        _write_progress(sec, idx + 1, (idx + 1) / total)
        if progress_callback:
            try:
                progress_callback(sec, idx + 1, total)
            except Exception:
                pass
        ok, msg = scrape_portal(
            start_date=start_date, end_date=end_date,
            section=sec, semester=semester, dynamic_conn=None
        )
        results.append({'section': sec, 'ok': ok, 'msg': msg})
        logger.info(msg)

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


def fill_attendance_history_gaps(conn, section, fdt, tdt):
    import sqlite3
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Get all students in this section
    students = [r['roll_no'] for r in cursor.execute(
        'SELECT roll_no FROM students WHERE section=?', (section,)
    ).fetchall()]
    
    # Get all subjects for this section
    subjects = [r['subject_code'] for r in cursor.execute(
        'SELECT DISTINCT subject_code FROM subjects WHERE section=?', (section,)
    ).fetchall()]
    
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
                insert_data
            )
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
