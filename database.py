"""
database.py — Complete with Sem 1 + Sem 2 from real CSVs.
"""
import sqlite3, os, shutil, csv, io
from datetime import datetime
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'vits_erp.db')
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
    # Sem 1 (from real results CSV)
    'IEE': 4.0, 'ED': 4.0, 'PPS': 4.0, 'ENG': 3.0, 'M&C': 4.0, 'AEP': 3.0,
    # Theory (Sem 2)
    'BEE': 3.0, 'EWS': 3.0, 'NAS': 3.0, 'DS': 3.0, 'EDC': 3.0,
    'EC': 3.0, 'EC_II': 3.0, 'ODEVC': 3.0, 'BPC': 3.0, 'EM': 3.0,
    'EEEE': 3.0, 'AEP': 3.0, 'ESE': 3.0, 'ITW': 3.0, 'TD': 3.0,
    'PYTHON': 3.0, 'ED&CAD': 3.0, 'ED& CAD': 3.0,
    # Labs
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
    """Parse: Hall no, Name, IEE[Total,GP], ED[Total,GP], ..., SGPA"""
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)
    if len(rows) < 3:
        return []
    header = rows[0]
    subjects_in_order = []
    i = 2
    while i < len(header) - 1:
        if header[i].strip():
            subjects_in_order.append(header[i].strip())
        i += 2

    results = []
    for row in rows[2:]:
        if not row or len(row) < 4 or not row[0].strip():
            continue
        roll_no = row[0].strip().upper()
        name = row[1].strip()
        subj_marks = {}
        col = 2
        for subj in subjects_in_order:
            if col + 1 < len(row):
                try:    total = float(row[col]) if row[col].strip() else None
                except: total = None
                try:    gp = float(row[col+1]) if row[col+1].strip() else 0.0
                except: gp = 0.0
                subj_marks[subj] = {'total': total, 'gp': gp}
            col += 2
        sgpa_val = row[col].strip() if col < len(row) else ''
        failed = sgpa_val.lower() == 'fail'
        try:
            sgpa = float(sgpa_val) if not failed and sgpa_val else 0.0
        except ValueError:
            sgpa, failed = 0.0, True
        results.append({
            'roll_no': roll_no, 'name': name,
            'subjects': subj_marks, 'sgpa': sgpa, 'failed': failed
        })
    return results


def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=30000')
    return conn


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


def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.executescript('''
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
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code TEXT NOT NULL,
            subject_name TEXT,
            semester     TEXT,
            section      TEXT,
            UNIQUE(subject_code, semester, section)
        );
        CREATE TABLE IF NOT EXISTS attendance (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no         TEXT,
            subject         TEXT,
            semester        TEXT,
            hours_attended  INTEGER DEFAULT 0,
            hours_conducted INTEGER DEFAULT 0,
            UNIQUE(roll_no, subject, semester),
            FOREIGN KEY(roll_no) REFERENCES students(roll_no)
        );
        CREATE TABLE IF NOT EXISTS marks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no     TEXT,
            subject     TEXT,
            semester    TEXT,
            exam_type   TEXT,
            score       REAL,
            grade_point REAL,
            UNIQUE(roll_no, subject, semester, exam_type)
        );
        CREATE TABLE IF NOT EXISTS sgpa_records (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no   TEXT,
            semester  TEXT,
            sgpa      REAL,
            failed    INTEGER DEFAULT 0,
            UNIQUE(roll_no, semester),
            FOREIGN KEY(roll_no) REFERENCES students(roll_no)
        );
        CREATE TABLE IF NOT EXISTS timetable (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            scraped_at TEXT,
            section    TEXT,
            students   INTEGER DEFAULT 0,
            status     TEXT,
            duration   REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS attendance_history (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date     TEXT NOT NULL DEFAULT (date('now')),
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
    ''')
    today = datetime.now().strftime('%Y-%m-%d')
    for key, val in [
        ('start_date', '2026-01-27'),
        ('end_date', today),
        ('last_scraped_at', 'Never'),
        ('active_semester', 'Sem 2'),
        ('total_semester_hours', '600'),
    ]:
        c.execute('INSERT OR IGNORE INTO config(key,value) VALUES(?,?)', (key, val))
    conn.commit()

    # Seed Subjects from our 12-section mapping if empty
    c.execute("SELECT COUNT(*) FROM subjects")
    if c.fetchone()[0] == 0:
        for section, subs in SECTION_SUBJECTS.items():
            for sub in subs:
                c.execute("""
                    INSERT OR IGNORE INTO subjects (subject_code, subject_name, semester, section)
                    VALUES (?, ?, ?, ?)
                """, (sub, sub, ACTIVE_SEMESTER, section))
        conn.commit()

    # Seed Students and Attendance from CSVs if empty
    c.execute("SELECT COUNT(*) FROM students")
    if c.fetchone()[0] == 0:
        seed_db_from_csvs(conn)

    # Migration: Update existing unconfigured default passwords to PENDING
    conn.execute("UPDATE students SET dob = 'PENDING' WHERE dob = '2007-01-01'")
    conn.commit()

    conn.close()


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
    cursor = conn.cursor()
    # Find all semesters where the student has final marks
    sem_rows = cursor.execute('''
        SELECT DISTINCT semester FROM marks 
        WHERE roll_no=? AND exam_type LIKE '%Final Examinations'
    ''', (roll_no,)).fetchall()
    
    for row in sem_rows:
        sem = row['semester']
        
        # Check if record already exists in sgpa_records
        existing = cursor.execute('''
            SELECT id FROM sgpa_records WHERE roll_no=? AND semester=?
        ''', (roll_no, sem)).fetchone()
        
        # For Sem 1, if it already exists, DO NOT recalculate or overwrite
        # (since Sem 1 SGPA comes from the CSV and has actual SGPA including labs)
        if sem == 'Sem 1' and existing:
            continue
            
        # Fetch final marks for calculation
        final_marks = cursor.execute('''
            SELECT subject, score, grade_point FROM marks
            WHERE roll_no=? AND semester=? AND exam_type=?
        ''', (roll_no, sem, f"{sem} Final Examinations")).fetchall()
        
        if final_marks:
            has_failed = False
            total_credits = 0.0
            weighted_gp = 0.0
            
            for m in final_marks:
                sub = m['subject']
                score = m['score']
                gp = m['grade_point'] or 0.0
                credits = SUBJECT_CREDITS.get(sub, 3.0)
                
                grade, _ = score_to_grade(score)
                if grade in ['F', 'Ab']:
                    has_failed = True
                
                if credits > 0:
                    weighted_gp += gp * credits
                    total_credits += credits
            
            sgpa = round(weighted_gp / total_credits, 2) if total_credits > 0 else 0.0
            
            if existing:
                cursor.execute('''
                    UPDATE sgpa_records SET sgpa=?, failed=? WHERE roll_no=? AND semester=?
                ''', (sgpa, 1 if has_failed else 0, roll_no, sem))
            else:
                cursor.execute('''
                    INSERT INTO sgpa_records (roll_no, semester, sgpa, failed)
                    VALUES (?, ?, ?, ?)
                ''', (roll_no, sem, sgpa, 1 if has_failed else 0))
    conn.commit()


def compute_cgpa(roll_no, conn=None):
    close_after = False
    if conn is None:
        conn = get_db_connection()
        close_after = True
    try:
        sync_sgpa_records(roll_no, conn)
        rows = conn.execute(
            'SELECT sgpa FROM sgpa_records WHERE roll_no=? AND sgpa>0 AND failed=0',
            (roll_no,)
        ).fetchall()
        if not rows: return 0.0
        return round(sum(r['sgpa'] for r in rows) / len(rows), 2)
    finally:
        if close_after:
            conn.close()


def backup_db():
    if not os.path.exists(DB_PATH):
        return None
    backup_dir = os.path.join(BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest  = os.path.join(backup_dir, f'vits_erp_{stamp}.db')
    shutil.copy2(DB_PATH, dest)
    backups = sorted(os.listdir(backup_dir))
    for old in backups[:-10]:
        try: os.remove(os.path.join(backup_dir, old))
        except: pass
    return dest


def seed_db_from_csvs(conn):
    """Seed database with CSV records in attandance database directory."""
    cursor = conn.cursor()
    if not os.path.exists(CSV_DIR):
        print(f"[Database] Seeding folder '{CSV_DIR}' not found. Seeding fallback student.")
        # Seeding a default student for ECE_B
        roll = "25891A0465"
        cursor.execute("""
            INSERT OR REPLACE INTO students (roll_no, name, dob, email, semester, department, section, branch)
            VALUES (?, ?, ?, ?, 2, 'ECE', 'ECE_B', 'ECE')
        """, (roll, "Yalangi Harshit Ram", DEFAULT_STUDENT_PASSWORD, f"{roll.lower()}@vits.edu"))
        
        # Seed attendance for ECE_B subjects
        for sub in SECTION_SUBJECTS["ECE_B"]:
            cursor.execute("""
                INSERT OR REPLACE INTO attendance (roll_no, subject, semester, hours_attended, hours_conducted)
                VALUES (?, ?, 'Sem 2', 24, 30)
            """, (roll, sub))
        
        # Mock SGPA for fallback student
        cursor.execute("""
            INSERT OR REPLACE INTO sgpa_records (roll_no, semester, sgpa, failed)
            VALUES (?, 'Sem 1', 7.5, 0)
        """, (roll,))
        cursor.execute("""
            INSERT OR REPLACE INTO sgpa_records (roll_no, semester, sgpa, failed)
            VALUES (?, 'Sem 2', 8.0, 0)
        """, (roll,))
        conn.commit()
        return

    csv_files = [f for f in os.listdir(CSV_DIR) if f.lower().endswith(".csv") and f.lower() != "attendance_master.csv"]
    print(f"[Database] Found {len(csv_files)} CSV files in seed folder.")
    
    random.seed(42)
    
    for filename in csv_files:
        path = os.path.join(CSV_DIR, filename)
        
        # Match section name from filename (e.g. attendance_AIDS.csv -> AIDS, Attendance_Report_ECE_B.csv -> ECE_B)
        section = None
        name_part = os.path.splitext(filename)[0].upper()
        for c in CLASSES:
            if c in name_part or c.replace("_", "") in name_part:
                section = c
                break
                
        if not section:
            print(f"[Database] Skipping CSV {filename} (no matching section in CLASSES)")
            continue
            
        print(f"[Database] Seeding section {section} from file {filename}...")
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = list(csv.reader(f))
                
            if len(reader) < 3:
                continue
                
            headers = [h.strip() for h in reader[0]]
            
            try:
                roll_idx = headers.index("H.T No.")
                name_idx = headers.index("Student Name")
            except ValueError:
                print(f"[Database] Error seeding {filename}: Missing 'H.T No.' or 'Student Name'")
                continue
                
            # Filter subjects from headers
            skip_cols = {"Section", "S.No.", "H.T No.", "Student Name", "Total", "Percentage(%)"}
            subjects = [col for col in headers if col and col not in skip_cols and not col.startswith("Unnamed")]
            
            # Conducted hours row
            conducted_row = reader[1]
            conducted_hours = {}
            for sub in subjects:
                try:
                    col_idx = headers.index(sub)
                    conducted_hours[sub] = int(conducted_row[col_idx])
                except (ValueError, IndexError):
                    conducted_hours[sub] = 30
                    
            # Insert student records and attendance
            student_count = 0
            for row_idx in range(2, len(reader)):
                row = reader[row_idx]
                if not row or len(row) <= max(roll_idx, name_idx) or not row[roll_idx].strip():
                    continue
                    
                roll_no = row[roll_idx].strip().upper()
                name = row[name_idx].strip()
                
                if roll_no.lower() in ["h.t no.", "student name", "number of hours conducted", "total", "percentage(%)", ""]:
                    continue
                    
                branch = section.split("_")[0] if "_" in section else section
                email = f"{roll_no.lower()}@vits.edu"
                
                # Insert Student (active semester = 2 for all new students)
                cursor.execute("""
                    INSERT OR REPLACE INTO students (roll_no, name, dob, email, semester, department, section, branch)
                    VALUES (?, ?, ?, ?, 2, ?, ?, ?)
                """, (roll_no, name, DEFAULT_STUDENT_PASSWORD, email, branch, section, branch))
                
                # Insert Attendance for both Sem 1 and Sem 2 (here we default to Sem 2 active, but seed attendance for Sem 2)
                for sub in subjects:
                    try:
                        col_idx = headers.index(sub)
                        att_val = int(row[col_idx])
                    except (ValueError, TypeError, IndexError):
                        att_val = 0
                    cond_val = conducted_hours.get(sub, 30)
                    if att_val > cond_val:
                        att_val = cond_val
                        
                    # Save current attendance (Sem 2)
                    cursor.execute("""
                        INSERT OR REPLACE INTO attendance (roll_no, subject, semester, hours_attended, hours_conducted)
                        VALUES (?, ?, 'Sem 2', ?, ?)
                    """, (roll_no, sub, att_val, cond_val))
                    
                    # Also insert a snapshot for today
                    today = "2026-05-23" # Seeding target date
                    pct = round((att_val / cond_val * 100), 2) if cond_val > 0 else 0.0
                    cursor.execute("""
                        INSERT OR REPLACE INTO attendance_history (snapshot_date, roll_no, subject_code, running_attended, running_conducted, percentage)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (today, roll_no, sub, att_val, cond_val, pct))
                    
                # Seed Marks for Sem 1 Final Exams to support CGPA calculations
                # Generate correlated performance factor
                is_failing_student = (roll_no == "25891A04B4")
                if is_failing_student:
                    factor = random.uniform(0.18, 0.38)
                else:
                    factor = random.uniform(0.48, 0.96)
                    
                # We seed only Sem 1 Final Marks (Sem 2 has not happened yet)
                for sem in ["Sem 1"]:
                    # Select subjects appropriate for this section
                    sem_subs = SECTION_SUBJECTS.get(section, []) if sem == "Sem 2" else SEM1_SUBJECTS
                    
                    weighted_gp = 0.0
                    total_credits = 0.0
                    has_failed = False
                    
                    for sub in sem_subs:
                        sub_factor = min(1.0, max(0.0, factor + random.uniform(-0.08, 0.08)))
                        final_score = int(sub_factor * 100)
                        
                        # Apply failing correction for mock consistency
                        if final_score < 40 and not is_failing_student:
                            if random.random() > 0.15:
                                final_score = random.randint(40, 48)
                                
                        # JNTUH GP conversions
                        grade, gp = score_to_grade(final_score)
                        if grade in ['F', 'Ab']:
                            has_failed = True
                            
                        cursor.execute("""
                            INSERT OR REPLACE INTO marks (roll_no, subject, semester, exam_type, score, grade_point)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (roll_no, sub, sem, f"{sem} Final Examinations", float(final_score), gp))
                        
                        credits = SUBJECT_CREDITS.get(sub, 3.0)
                        weighted_gp += gp * credits
                        total_credits += credits
                        
                        if sem == "Sem 2":
                            # Seed Mid 1 & Mid 2 marks (Sem 2)
                            mid1 = min(25, max(0, int(sub_factor * 25 + random.uniform(-1.5, 1.5))))
                            cursor.execute("""
                                INSERT OR REPLACE INTO marks (roll_no, subject, semester, exam_type, score, grade_point)
                                VALUES (?, ?, ?, 'Mid 1', ?, 0.0)
                            """, (roll_no, sub, sem, float(mid1)))
                            
                            mid2 = min(25, max(0, int(sub_factor * 25 + random.uniform(-1.5, 1.5))))
                            cursor.execute("""
                                INSERT OR REPLACE INTO marks (roll_no, subject, semester, exam_type, score, grade_point)
                                VALUES (?, ?, ?, 'Mid 2', ?, 0.0)
                            """, (roll_no, sub, sem, float(mid2)))
                            
                            # Lab internals (if lab)
                            if "LAB" in sub.upper() or sub in ["EWS", "ITW"]:
                                lab_int = min(30, max(0, int(sub_factor * 30 + random.uniform(-2.0, 2.0))))
                                cursor.execute("""
                                    INSERT OR REPLACE INTO marks (roll_no, subject, semester, exam_type, score, grade_point)
                                    VALUES (?, ?, ?, 'Lab Internals', ?, 0.0)
                                """, (roll_no, sub, sem, float(lab_int)))
                                
                    # Insert SGPA record
                    sgpa = round(weighted_gp / total_credits, 2) if total_credits > 0 else 0.0
                    cursor.execute("""
                        INSERT OR REPLACE INTO sgpa_records (roll_no, semester, sgpa, failed)
                        VALUES (?, ?, ?, ?)
                    """, (roll_no, sem, sgpa, 1 if has_failed else 0))
                            
                student_count += 1
            print(f"[Database] Seeding complete. Loaded {student_count} students for section {section}.")
        except Exception as e:
            print(f"[Database] Error reading {filename}: {e}")
            
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
            
            # Upsert Student
            cursor.execute("""
                INSERT OR REPLACE INTO students (roll_no, name, dob, email, semester, department, section, branch)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
                        INSERT OR REPLACE INTO marks (roll_no, subject, semester, exam_type, score, grade_point)
                        VALUES (?, ?, ?, ?, ?, ?)
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
                INSERT OR REPLACE INTO sgpa_records (roll_no, semester, sgpa, failed)
                VALUES (?, ?, ?, ?)
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
                    VALUES (?, ?, ?, 2, ?, ?, ?)
                    ON CONFLICT(roll_no) DO UPDATE SET 
                        name=excluded.name, 
                        section=excluded.section,
                        branch=excluded.branch,
                        department=excluded.department
                ''', (roll, name, DEFAULT_STUDENT_PASSWORD, branch, branch, section))

                # Insert Sem 1 Marks
                for subj, data in record['subjects'].items():
                    if data['total'] is not None:
                        cursor.execute('''
                            INSERT OR REPLACE INTO marks (roll_no, subject, semester, exam_type, score, grade_point)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (roll, subj, semester, f"{semester} Final Examinations", data['total'], data['gp']))
                        marks_count += 1

                # Insert Sem 1 SGPA
                cursor.execute('''
                    INSERT OR REPLACE INTO sgpa_records (roll_no, semester, sgpa, failed)
                    VALUES (?, ?, ?, ?)
                ''', (roll, semester, record['sgpa'], 1 if record['failed'] else 0))
                sgpa_count += 1

            print(f"[Database] Imported {sgpa_count} student SGPA records and {marks_count} marks for {section}.")
        conn.commit()
    except Exception as e:
        print(f"[Database] Error importing results from CSVs: {e}")
    finally:
        if close_after:
            conn.close()
