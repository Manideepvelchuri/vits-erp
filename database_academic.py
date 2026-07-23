import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "academic_hub.db")

def get_academic_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_academic_db():
    conn = get_academic_conn()
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS student_backlogs (
            roll_no      TEXT,
            subject_code TEXT,
            backlog_sem  INTEGER,
            status       TEXT DEFAULT 'ACTIVE',
            PRIMARY KEY(roll_no, subject_code)
        );
        CREATE TABLE IF NOT EXISTS question_frequency (
            question_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code    TEXT,
            unit            INTEGER,
            q_text          TEXT,
            occurrence_count INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS student_weakness (
            roll_no        TEXT,
            subject_code   TEXT,
            unit_no        INTEGER,
            weakness_score REAL DEFAULT 0.0,
            PRIMARY KEY(roll_no, subject_code, unit_no)
        );
        CREATE TABLE IF NOT EXISTS academic_resources (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            branch        TEXT,
            semester      INTEGER,
            subject_code  TEXT,
            resource_type TEXT,
            file_name     TEXT,
            file_url      TEXT,
            unit_no       INTEGER,
            academic_year TEXT,
            regulation    TEXT
        );
        CREATE TABLE IF NOT EXISTS syllabus_topics (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code TEXT,
            unit         INTEGER,
            topic_text   TEXT,
            UNIQUE(subject_code, unit, topic_text)
        );
        CREATE TABLE IF NOT EXISTS student_syllabus_progress (
            roll_no    TEXT,
            topic_id   INTEGER,
            status     TEXT DEFAULT 'NOT_STARTED',
            PRIMARY KEY(roll_no, topic_id),
            FOREIGN KEY(topic_id) REFERENCES syllabus_topics(id)
        );
        CREATE TABLE IF NOT EXISTS question_banks (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code TEXT,
            unit         INTEGER,
            q_type       TEXT,
            question     TEXT,
            answer_text  TEXT,
            marks        TEXT,
            co           TEXT,
            btl          TEXT,
            UNIQUE(subject_code, unit, q_type, question)
        );
        CREATE TABLE IF NOT EXISTS mcqs (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code   TEXT,
            unit           INTEGER,
            question       TEXT,
            option_a       TEXT,
            option_b       TEXT,
            option_c       TEXT,
            option_d       TEXT,
            correct_option TEXT,
            explanation    TEXT,
            UNIQUE(subject_code, unit, question)
        );
        CREATE TABLE IF NOT EXISTS class_sessions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code   TEXT,
            class_date     TEXT,
            unit_no        INTEGER,
            topic_covered  TEXT,
            faculty_name   TEXT
        );
        CREATE TABLE IF NOT EXISTS review_schedule (
            roll_no     TEXT,
            mcq_id      INTEGER,
            next_review TEXT,
            difficulty  INTEGER DEFAULT 1,
            PRIMARY KEY(roll_no, mcq_id)
        );
        
        -- New tables for dynamic redesigned hub
        CREATE TABLE IF NOT EXISTS drive_files (
            file_id TEXT PRIMARY KEY,
            file_name TEXT,
            mime_type TEXT,
            modified_time TEXT,
            branch TEXT,
            semester INTEGER,
            subject TEXT,
            processed INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS syllabus_delivery_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_date TEXT,
            subject_code TEXT,
            topic TEXT,
            UNIQUE(class_date, subject_code, topic)
        );
        CREATE TABLE IF NOT EXISTS lab_programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code TEXT,
            file_name TEXT,
            code_content TEXT,
            explanation TEXT,
            UNIQUE(subject_code, file_name)
        );
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code TEXT,
            unit INTEGER,
            topic TEXT,
            content TEXT,
            UNIQUE(subject_code, unit, topic)
        );
    ''')
    
    # Try creating FTS5 virtual tables for RAG
    try:
        c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS question_banks_fts USING fts5(qb_id, subject_code, question, answer_text)")
        c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS syllabus_topics_fts USING fts5(topic_id, subject_code, topic_text)")
        c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS mcqs_fts USING fts5(mcq_id, subject_code, question, explanation)")
        c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS lab_programs_fts USING fts5(lab_id, subject_code, file_name, code_content, explanation)")
        c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(notes_id, subject_code, unit, topic, content)")
    except Exception as e:
        # SQLite compiled without FTS5, fallback will be used
        pass
        
    conn.commit()
    conn.close()

def add_lab_program(subject_code, file_name, code_content, explanation=""):
    conn = get_academic_conn()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO lab_programs (subject_code, file_name, code_content, explanation)
            VALUES (?, ?, ?, ?)
        ''', (subject_code, file_name, code_content, explanation))
        
        # Sync with FTS5
        lab_id = cursor.lastrowid
        try:
            conn.execute("DELETE FROM lab_programs_fts WHERE lab_id = ?", (lab_id,))
            conn.execute('''
                INSERT INTO lab_programs_fts (lab_id, subject_code, file_name, code_content, explanation)
                VALUES (?, ?, ?, ?, ?)
            ''', (lab_id, subject_code, file_name, code_content, explanation))
        except Exception:
            pass
            
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

def add_note(subject_code, unit, topic, content):
    conn = get_academic_conn()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO notes (subject_code, unit, topic, content)
            VALUES (?, ?, ?, ?)
        ''', (subject_code, unit, topic, content))
        
        # Sync with FTS5
        note_id = cursor.lastrowid
        try:
            conn.execute("DELETE FROM notes_fts WHERE notes_id = ?", (note_id,))
            conn.execute('''
                INSERT INTO notes_fts (notes_id, subject_code, unit, topic, content)
                VALUES (?, ?, ?, ?, ?)
            ''', (note_id, subject_code, unit, topic, content))
        except Exception:
            pass
            
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

def add_syllabus_delivery_log(class_date, subject_code, topic):
    conn = get_academic_conn()
    try:
        conn.execute('''
            INSERT OR IGNORE INTO syllabus_delivery_log (class_date, subject_code, topic)
            VALUES (?, ?, ?)
        ''', (class_date, subject_code, topic))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

def get_lab_programs(subject_code):
    conn = get_academic_conn()
    rows = conn.execute("SELECT * FROM lab_programs WHERE subject_code=?", (subject_code,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_notes(subject_code):
    conn = get_academic_conn()
    rows = conn.execute("SELECT * FROM notes WHERE subject_code=? ORDER BY unit, topic", (subject_code,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_syllabus_delivery_log(subject_code):
    conn = get_academic_conn()
    rows = conn.execute("SELECT * FROM syllabus_delivery_log WHERE subject_code=? ORDER BY class_date DESC", (subject_code,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_drive_file(file_id):
    conn = get_academic_conn()
    row = conn.execute("SELECT * FROM drive_files WHERE file_id=?", (file_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def save_drive_file(file_id, file_name, mime_type, modified_time, branch, semester, subject, processed=0):
    conn = get_academic_conn()
    try:
        conn.execute('''
            INSERT OR REPLACE INTO drive_files (file_id, file_name, mime_type, modified_time, branch, semester, subject, processed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (file_id, file_name, mime_type, modified_time, branch, semester, subject, processed))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

def search_academic_resources_rag(query, subject_code=None):
    conn = get_academic_conn()
    results = []
    
    # Clean query for safety in FTS5 syntax
    clean_query = "".join(c if c.isalnum() or c.isspace() else " " for c in query).strip()
    
    try:
        # FTS5 search on question banks
        q = "SELECT qb_id, question, answer_text, subject_code FROM question_banks_fts WHERE question_banks_fts MATCH ?"
        params = [clean_query]
        if subject_code:
            q += " AND subject_code = ?"
            params.append(subject_code)
        q_rows = conn.execute(q, params).fetchall()
        for r in q_rows:
            results.append({
                "type": "question_bank",
                "id": r[0],
                "title": f"Question: {r[1][:100]}",
                "content": f"Q: {r[1]}\nAnswer: {r[2]}",
                "subject": r[3]
            })
            
        # FTS5 search on notes
        q = "SELECT notes_id, subject_code, unit, topic, content FROM notes_fts WHERE notes_fts MATCH ?"
        params = [clean_query]
        if subject_code:
            q += " AND subject_code = ?"
            params.append(subject_code)
        n_rows = conn.execute(q, params).fetchall()
        for r in n_rows:
            results.append({
                "type": "notes",
                "id": r[0],
                "title": f"Unit {r[2]} Notes: {r[3]}",
                "content": r[4],
                "subject": r[1]
            })
            
        # FTS5 search on syllabus topics
        q = "SELECT topic_id, subject_code, topic_text FROM syllabus_topics_fts WHERE syllabus_topics_fts MATCH ?"
        params = [clean_query]
        if subject_code:
            q += " AND subject_code = ?"
            params.append(subject_code)
        s_rows = conn.execute(q, params).fetchall()
        for r in s_rows:
            results.append({
                "type": "syllabus",
                "id": r[0],
                "title": f"Syllabus Topic in {r[1]}",
                "content": r[2],
                "subject": r[1]
            })
            
        # FTS5 search on lab programs
        q = "SELECT lab_id, subject_code, file_name, code_content, explanation FROM lab_programs_fts WHERE lab_programs_fts MATCH ?"
        params = [clean_query]
        if subject_code:
            q += " AND subject_code = ?"
            params.append(subject_code)
        l_rows = conn.execute(q, params).fetchall()
        for r in l_rows:
            results.append({
                "type": "lab_program",
                "id": r[0],
                "title": f"Lab Program: {r[2]}",
                "content": f"Code:\n{r[3]}\n\nExplanation:\n{r[4]}",
                "subject": r[1]
            })
            
    except Exception:
        # Fallback to standard LIKE search
        # Search question_banks
        q = "SELECT id, question, answer_text, subject_code FROM question_banks WHERE question LIKE ? OR answer_text LIKE ?"
        params = [f"%{query}%", f"%{query}%"]
        if subject_code:
            q = "SELECT id, question, answer_text, subject_code FROM question_banks WHERE (question LIKE ? OR answer_text LIKE ?) AND subject_code = ?"
            params.append(subject_code)
        q_rows = conn.execute(q, params).fetchall()
        for r in q_rows:
            results.append({
                "type": "question_bank",
                "id": r[0],
                "title": f"Question: {r[1][:100]}",
                "content": f"Q: {r[1]}\nAnswer: {r[2]}",
                "subject": r[3]
            })
            
        # Search notes
        q = "SELECT id, subject_code, unit, topic, content FROM notes WHERE topic LIKE ? OR content LIKE ?"
        params = [f"%{query}%", f"%{query}%"]
        if subject_code:
            q = "SELECT id, subject_code, unit, topic, content FROM notes WHERE (topic LIKE ? OR content LIKE ?) AND subject_code = ?"
            params.append(subject_code)
        n_rows = conn.execute(q, params).fetchall()
        for r in n_rows:
            results.append({
                "type": "notes",
                "id": r[0],
                "title": f"Unit {r[2]} Notes: {r[3]}",
                "content": r[4],
                "subject": r[1]
            })
            
        # Search syllabus_topics
        q = "SELECT id, subject_code, topic_text FROM syllabus_topics WHERE topic_text LIKE ?"
        params = [f"%{query}%"]
        if subject_code:
            q = "SELECT id, subject_code, topic_text FROM syllabus_topics WHERE topic_text LIKE ? AND subject_code = ?"
            params.append(subject_code)
        s_rows = conn.execute(q, params).fetchall()
        for r in s_rows:
            results.append({
                "type": "syllabus",
                "id": r[0],
                "title": f"Syllabus Topic in {r[1]}",
                "content": r[2],
                "subject": r[1]
            })
            
        # Search lab_programs
        q = "SELECT id, subject_code, file_name, code_content, explanation FROM lab_programs WHERE file_name LIKE ? OR code_content LIKE ?"
        params = [f"%{query}%", f"%{query}%"]
        if subject_code:
            q = "SELECT id, subject_code, file_name, code_content, explanation FROM lab_programs WHERE (file_name LIKE ? OR code_content LIKE ?) AND subject_code = ?"
            params.append(subject_code)
        l_rows = conn.execute(q, params).fetchall()
        for r in l_rows:
            results.append({
                "type": "lab_program",
                "id": r[0],
                "title": f"Lab Program: {r[2]}",
                "content": f"Code:\n{r[3]}\n\nExplanation:\n{r[4]}",
                "subject": r[1]
            })
            
    conn.close()
    return results

if __name__ == "__main__":
    init_academic_db()
    print("Academic Database initialized successfully at academic_hub.db!")
