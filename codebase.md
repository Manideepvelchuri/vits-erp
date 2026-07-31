# VITS ERP Streamlit Codebase Export

This document contains the consolidated files of the codebase.

[TOC]

---

## [.gitignore](file:///d:/claude demo/vits-erp-streamlit/.gitignore)

```text
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
.Python
*.egg
*.egg-info/
dist/
build/

# Streamlit secrets — NEVER commit this
.streamlit/secrets.toml

# Local SQLite database — too large for GitHub, use Supabase instead
*.db
*.db-shm
*.db-wal
*.db.bak

# Backups (local only)
backups/
csv_backups/

# Backup files
*.bak

# Virtual environment
.venv/
venv/
env/

# OS files
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/

# Sandbox/Beta testing (local only)
sandbox/

# Local academic materials and caches
academic_materials/
academic_materials_cache/
audio_cache/
backup.zip
.agents/
graphify-out/

```

---

## [README.md](file:///d:/claude demo/vits-erp-streamlit/README.md)

```markdown
# 🎓 VITS Academic ERP Portal

A modern, fast, and feature-rich Academic ERP system built with Streamlit and Python. It offers a fully-responsive student academic dashboard and a secure administrator control console.

🌐 **Live Dashboard:** [vits-academic-dashboard.streamlit.app](https://vits-academic-dashboard.streamlit.app/)

---

## 📸 Dashboard Preview

![VITS Student Dashboard Preview](dashboard_preview.png)

---

## ✨ Key Features

### 👤 For Students
- **📈 Attendance Tracker & Analytics:** Real-time class attendance percentage, historical trend tracking, condonation planning, and monthly absent heatmaps.
- **🔮 Attendance Forecasts:** Smart estimation showing future attendance outcomes based on upcoming schedules.
- **📝 Marks & Grade Planner:** View exam marks (Mid 1, Mid 2, Lab Internals, Finals) and predict semester SGPA / overall CGPA with interactive sliders.
- **🗓️ Timetable Planner:** A clean timeline of daily classes and free periods tailored to the student's section.
- **⬇️ PDF Report Card:** Instantly generate and download official-looking semester report cards in PDF format.

### 🛡️ For Administrators
- **👥 Student Directory:** 
  - Manage student records, profiles, and sections.
  - **Reset Student Passwords:** One-click reset checkbox that resets a student's login credential back to the default setup password (`vits123`).
- **📝 Marks Editor:** Record or modify student grades for any course, semester, or exam type with validation bounds.
- **📤 CSV Upload Center:**
  - **Internal Marks CSV:** Bulk import mid-term scores and lab marks.
  - **JNTU Results CSV:** Import standard semester results with automatic SGPA calculations and student onboarding.
- **🔄 Scraper Harvester:** Scrape and sync active attendance records directly from the portal for single sections or bulk-scrape all classes.
- **💾 System Backups & Config:** Automatic database snapshots, active semester configurations, and secure admin password updates.

---

## 🛠️ Tech Stack
- **Frontend/Backend:** [Streamlit](https://streamlit.io/) (Python web framework)
- **Database:** SQLite (Local/Development) and PostgreSQL/Supabase (Production)
- **Charts:** [Plotly](https://plotly.com/) (Interactive data visualizations)
- **PDF Generation:** [ReportLab](https://www.reportlab.com/)

---

## 🚀 Getting Started (Local Run)

### 1. Clone the repository:
```bash
git clone https://github.com/Manideepvelchuri/vits-erp.git
cd vits-erp
```

### 2. Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configure Database:
- By default, the application runs on a local SQLite database file `vits_erp.db` (auto-created on first run).
- To connect to a PostgreSQL database, set your connection URL in `.streamlit/secrets.toml` or as an environment variable:
```toml
[database]
url = "your-postgresql-connection-string"
```

### 4. Run the Streamlit application:
```bash
streamlit run streamlit_app.py
```
Open `http://localhost:8501` in your browser.

---

## 🔑 Default Credentials (First-Time Setup)
- **Student Default Login:** Use your Roll Number and default password: **`vits123`**. You will be prompted to set your Date of Birth as your permanent password on first-time login.
- **Admin Default Password:** `vits@admin123` (Configurable via Environment Variable `ADMIN_PASSWORD` or the Settings tab).

```

---

## [academic_hub_proposal.md](file:///d:/claude demo/vits-erp-streamlit/academic_hub_proposal.md)

```markdown
# Technical Proposal: VITS Academic Hub & NotebookLM Integration

This document outlines the architecture, database design, user interface layout, and parsing workflow to integrate a comprehensive **Academic Hub** (Syllabus Tracker, MCQ/QB Quizzer, Lab Code Library, and NotebookLM support) into the existing **VITS Academic ERP Streamlit application**.

---

## 📋 1. Project Context & Objectives

The current application is a **VITS Academic ERP & Bunk Intelligence Dashboard** built using:
* **Frontend**: Streamlit (Python) with custom CSS styling and Plotly graphs.
* **Database**: SQLite locally (`vits_erp.db`) and Supabase PostgreSQL in production (dynamically routed via the `DATABASE_URL` environment variable).

We want to expand the **Student Dashboard** by adding a new page: **`📚 Academic Hub`**. 
This hub will leverage the student's branch and semester to dynamically serve syllabi, lab programs, descriptive question banks, and interactive MCQ practice quizzes loaded directly from their college Word documents (`.doc` and `.docx`).

---

## 📂 2. Available Local Source Materials

The user has provided a local folder: `academic_materials/I Year QB VR25 and VR23/` containing:
* **1.1 VR25 QB (Semester 1)**: `Chemistry QB.doc`, `EDC Question Bank -Mid 1.docx`, `PPS Question Bank 2025-26.doc`, etc.
* **1.2 VR25 QB (Semester 2)**: `DS.doc` (Data Structures), `EDC.docx` (Electronic Devices and Circuits), `PYTHON.doc` (Python Programming), `ECA-II.docx`, etc.

### Structure of `EDC.docx` (Sample):
1. **Header Details**: Class, Subject Code, Semester.
2. **Descriptive Question Bank**: Tables containing `[Q.No, Description, Marks, CO, PO, BTL]`.
3. **Objective Question Bank**:
   * **MCQs**: Numbered list (1, 2, 3...) containing question text followed by options `(a) ... (b) ... (c) ... (d) ...`.
   * **Fill-in-the-Blanks (FIB)**: Numbered list (11, 12, 13...) with blanks (`___`).
   * **Answer Key**: Tables containing `[Q.No., Answer, Q.No., Answer]`.

---

## ⚙️ 3. Proposed Database Schema

To support these features, the following database tables will be added to the SQLite and Supabase PostgreSQL databases:

```sql
-- 1. Subject-to-File mappings
CREATE TABLE academic_resources (
    id SERIAL PRIMARY KEY,
    branch TEXT,             -- e.g., 'ECE'
    semester INTEGER,        -- e.g., 2
    subject_code TEXT,       -- e.g., 'EC201'
    resource_type TEXT,      -- e.g., 'Syllabus', 'Lab Manual', 'Question Bank'
    file_name TEXT,          -- e.g., 'EDC.docx'
    file_url TEXT            -- Remote/local file path
);

-- 2. Syllabus topics for progress tracking
CREATE TABLE syllabus_topics (
    id SERIAL PRIMARY KEY,
    subject_code TEXT,
    unit INTEGER,            -- 1 to 5
    topic_text TEXT
);

-- 3. Student-specific syllabus study progress
CREATE TABLE student_syllabus_progress (
    roll_no TEXT,
    topic_id INTEGER,
    status TEXT DEFAULT 'NOT_STARTED', -- 'NOT_STARTED', 'IN_PROGRESS', 'MASTERED'
    PRIMARY KEY (roll_no, topic_id),
    FOREIGN KEY (topic_id) REFERENCES syllabus_topics(id)
);

-- 4. Question bank database (Descriptive & FIB)
CREATE TABLE question_banks (
    id SERIAL PRIMARY KEY,
    subject_code TEXT,
    unit INTEGER,
    q_type TEXT,            -- 'DESCRIPTIVE', 'FIB'
    question TEXT,
    answer_text TEXT,       -- Null for descriptive, populated for FIB
    marks TEXT,             -- e.g., '2M', '10M'
    co INTEGER,
    btl INTEGER
);

-- 5. Multiple choice questions for interactive practice
CREATE TABLE mcqs (
    id SERIAL PRIMARY KEY,
    subject_code TEXT,
    unit INTEGER,
    question TEXT,
    option_a TEXT,
    option_b TEXT,
    option_c TEXT,
    option_d TEXT,
    correct_option CHAR(1), -- 'A', 'B', 'C', or 'D'
    explanation TEXT        -- Optional explanation/formula
);
```

---

## 🛠️ 4. Detailed Feature Design

### Feature A: ECE Resource Center & Lab Reference Library
* **UI**: Clean card grid for each current subject. Includes filter fields and quick download links.
* **Lab Code Tab**: A sidebar or split screen showing lab programs. On click, the code displays inside a dark code block with syntax highlighting:
  ```python
  st.code(program_code, language='python')
  ```
  Includes a **Copy** button and a **Download (.py)** button.

### Feature B: Interactive Syllabus Tracker
* **UI**: Collapsible accordions for Unit 1 to Unit 5. Inside is a checkbox list of topics.
* **UX**: Checkboxes toggle completion status dynamically. A primary progress bar updates instantly.
* **State**: Uses `student_syllabus_progress` to fetch and store selections per student.

### Feature C: Question Bank Quizzer & MCQ Practice Engine
* **Descriptive Study Mode**: Displays questions with a collapsible `"Reveal Answer"` accordion containing tips or step-by-step solutions.
* **MCQ Practice Mode**:
  * Renders one question at a time using `st.radio` for options.
  * Shows instant feedback when `Check Answer` is clicked (Green `st.success` if correct, Red `st.error` showing the right key if wrong).
  * Saves mistakes to `st.session_state.quiz_history` for final review.
  * Generates a **Quiz Scoreboard** at the end with topic recommendations.

### Feature D: NotebookLM AI Integration
Google’s **NotebookLM** is a powerful tool for document analysis and AI audio generation. Since NotebookLM doesn't have an API yet, we will integrate it via:
1. **Export for NotebookLM**: A button called `"Generate NotebookLM Package"`. It compiles a student's syllabus topics, flagged question bank questions, and MCQ wrong answers into a single, clean `.md` markdown file for download. The student simply uploads this single file to NotebookLM to generate custom audio briefings or study sheets.
2. **AI Audio Briefing Player**: The admin can generate an Audio Overview (podcast) in NotebookLM, save the `.mp3`, place it in the folder, and we will stream/play it directly on the dashboard via `st.audio()`.

---

## 🧪 5. Discussion Points & Questions for Alternative AIs

*If you are copying this document to another AI, paste these questions to brainstorm optimizations:*

1. **How should we parse the old binary `.doc` files?** 
   Since `python-docx` only supports `.docx`, what is the best python-native solution to parse `.doc` question banks on a Linux cloud container (where Microsoft Word is not installed)? (e.g., should we use `pandoc`, `docx2txt`, `striprtf`, or pre-convert them using a local script before deploying?)
2. **What is the cleanest way to manage Streamlit's state for the MCQ Quiz?**
   Streamlit notoriously reruns scripts from top-to-bottom on every interaction. What state structure using `st.session_state` prevents the quiz from resetting when a student switches tabs or interacts with other parts of the dashboard?
3. **How can we write a highly robust parser for docx tables?**
   docx tables have merged cells, missing headers, or nested formats. Can you write a Python script using `python-docx` to reliably parse descriptive questions from tables with `[Q.No, Description, Marks, CO]` and handle merged cells safely?
4. **How can we correlate syllabus topics with attendance?**
   If a student is absent on a specific date, how can we map that date to the syllabus table to show them which topics they missed and need to study?

```

---

## [academic_hub_ui.py](file:///d:/claude demo/vits-erp-streamlit/academic_hub_ui.py)

```python
import streamlit as st
import pandas as pd
import datetime
import os
import json
import requests
import time
import threading

from database_academic import (
    get_academic_conn, add_lab_program, add_note, add_syllabus_delivery_log,
    get_lab_programs, get_notes, get_syllabus_delivery_log, get_drive_file,
    save_drive_file, search_academic_resources_rag
)

# ── BACKGROUND SYNC ENGINE ───────────────────────────────────

def get_all_drive_files_recursive(folder_id, api_key):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    to_scan = [folder_id]
    all_files = []
    scanned_folders = set()
    
    while to_scan:
        curr_folder_id = to_scan.pop(0)
        if curr_folder_id in scanned_folders:
            continue
        scanned_folders.add(curr_folder_id)
        
        url = "https://www.googleapis.com/drive/v3/files"
        params = {
            "q": f"'{curr_folder_id}' in parents and trashed = false",
            "fields": "files(id, name, mimeType, modifiedTime)",
            "key": api_key,
            "pageSize": 1000
        }
        try:
            res = requests.get(url, params=params, headers=headers, timeout=15)
            if res.status_code == 200:
                files_list = res.json().get("files", [])
                for f in files_list:
                    fid = f.get("id")
                    name = f.get("name")
                    mime = f.get("mimeType")
                    mod_time = f.get("modifiedTime")
                    if not fid or not name:
                        continue
                    
                    if mime == "application/vnd.google-apps.folder":
                        to_scan.append(fid)
                    else:
                        all_files.append({
                            "id": fid,
                            "name": name,
                            "mime_type": mime,
                            "modified_time": mod_time
                        })
            else:
                print(f"[Sync] API returned {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[Sync] Folder scan exception: {e}")
            
    return all_files

def download_drive_file(file_id, file_name, api_key):
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "academic_materials_cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    safe_name = "".join(c for c in file_name if c.isalnum() or c in "._- ").strip()
    local_path = os.path.join(cache_dir, f"{file_id}_{safe_name}")
    
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={api_key}"
    try:
        res = requests.get(url, timeout=30)
        if res.status_code == 200:
            with open(local_path, "wb") as f:
                f.write(res.content)
            return local_path
        else:
            print(f"[Sync] Failed to download {file_name}: Status {res.status_code}")
    except Exception as e:
        print(f"[Sync] Download exception for {file_name}: {e}")
    return None

def get_subject_from_filename(file_name):
    name_upper = file_name.upper()
    if "PYTHON" in name_upper or "PPS" in name_upper:
        return "PYTHON"
    elif "EDC" in name_upper or "ELECTRONIC" in name_upper:
        return "EDC"
    elif "BEE" in name_upper or "ELECTRICAL" in name_upper:
        return "BEE"
    elif "ODEVC" in name_upper or "ODE" in name_upper or "VECTOR" in name_upper or "DIFFERENTIAL" in name_upper:
        return "ODEVC"
    elif "CHEMISTRY" in name_upper or "EC" in name_upper:
        return "Chemistry"
    elif "NAS" in name_upper or "NETWORK" in name_upper or "SYNTHESIS" in name_upper:
        return "NAS"
    elif "DS" in name_upper or "DATA STRUCTURE" in name_upper:
        return "DS"
    return "PYTHON"

def auto_detect_subject_metadata(file_name, sample_text, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    prompt = f"""
    You are an academic file classification assistant. Analyze this file metadata and content:
    File Name: {file_name}
    Content Sample:
    {sample_text[:10000]}
    
    Classify the file and extract exactly:
    - "subject": The full name of the subject (e.g. "Electronic Devices and Circuits", "Python Programming", "Basic Electrical Engineering", "Programming for Problem Solving", "Engineering Chemistry", "Ordinary Differential Equations and Vector Calculus", "Data Structures", "Network Analysis and Synthesis", etc.)
    - "subject_code": The standardized subject code (e.g. "2566103ES" for Python, "2504103ES" for EDC, "23EE104ES" for BEE, "2512105ES" for PPS, "25CH102BS" for Chemistry, "25MA201BS" for ODEVC, "25PH102BS" for Applied Physics, "591" for DS, etc.)
    - "semester": The semester number as an integer (e.g. 1 or 2)
    - "branch": The engineering branch target (e.g. "ECE", "CSE", "CSE AIML", "CSE DS", "AIDS", "MECH", "CIVIL", "EEE", etc.)
    - "regulation": The academic regulation (e.g. "VR25", "VR23")
    - "academic_year": The academic year (e.g. "2025-2026")
    - "document_type": Type of document, choose exactly one of: "syllabus", "question_bank", "mcqs", "notes", "lab_program", "other"
    
    Respond ONLY with a valid JSON block containing these keys. Do not include markdown code block wrappers (like ```json) or any explanations.
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=20)
        if res.status_code == 200:
            text_out = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text_out.startswith("```"):
                lines = text_out.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                text_out = "\n".join(lines).strip()
            
            data = json.loads(text_out)
            return data
        else:
            print(f"[AutoDetect] Gemini returned status {res.status_code}")
    except Exception as e:
        print(f"[AutoDetect] Exception: {e}")
        
    name_upper = file_name.upper()
    doc_type = "other"
    if "SYLLABUS" in name_upper:
        doc_type = "syllabus"
    elif "QB" in name_upper or "QUESTION" in name_upper:
        doc_type = "question_bank"
    elif "MCQ" in name_upper or "OBJECTIVE" in name_upper:
        doc_type = "mcqs"
    elif "LAB" in name_upper or "RECORD" in name_upper or "PROGRAM" in name_upper or file_name.endswith((".py", ".c", ".cpp")):
        doc_type = "lab_program"
    elif "NOTES" in name_upper or "MATERIAL" in name_upper or "UNIT" in name_upper:
        doc_type = "notes"
        
    sub_code = get_actual_subject_code(get_subject_from_filename(file_name))
    
    return {
        "subject": get_subject_from_filename(file_name),
        "subject_code": sub_code,
        "semester": 2 if "SEM-II" in name_upper or "SEM 2" in name_upper or "SEM2" in name_upper else 1,
        "branch": "CSE" if "CSE" in name_upper else "ECE" if "ECE" in name_upper else "ALL",
        "regulation": "VR25" if "VR25" in name_upper else "VR23",
        "academic_year": "2025-2026",
        "document_type": doc_type
    }

def parse_zip_lab_programs(zip_path, subject_code):
    import zipfile
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                if file_info.is_dir() or "__MACOSX" in file_info.filename or file_info.filename.startswith("."):
                    continue
                ext = os.path.splitext(file_info.filename)[1].lower()
                if ext in [".py", ".c", ".cpp", ".txt"]:
                    code_content = zip_ref.read(file_info).decode('utf-8', errors='ignore')
                    file_name = os.path.basename(file_info.filename)
                    explanation = f"Source: {file_info.filename} zip archive."
                    add_lab_program(subject_code, file_name, code_content, explanation)
    except Exception as e:
        print(f"[Sync] Zip parser error: {e}")

def parse_notes_via_gemini(text, subject_code, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    prompt = f"""
    You are an expert academic study guide parser. Analyze the provided study material and extract the main topics covered, grouped by course Units (usually Unit 1 to 5).
    Generate a valid JSON array of objects, each representing a topic notes section. Do not include markdown code block wrappers or explanations.
    
    Schema:
    [
      {{
        "unit": 1,
        "topic": "Zener Diode Characteristics",
        "content": "Detailed explanatory notes about Zener diode, including definition, characteristics, breakdown regions, and applications as a voltage regulator."
      }}
    ]
    
    Only extract major topics with rich, informative content summaries.
    Text:
    {text[:25000]}
    """
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=30)
        if res.status_code == 200:
            text_out = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text_out.startswith("```"):
                lines = text_out.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                text_out = "\n".join(lines).strip()
            parsed = json.loads(text_out)
            for note in parsed:
                add_note(subject_code, note.get("unit", 3), note.get("topic"), note.get("content"))
    except Exception as e:
        print(f"[Sync] Notes parser error: {e}")

def sync_drive_files_engine():
    drive_api_key = get_drive_api_key()
    gemini_api_key = get_gemini_api_key()
    folder_id = "1bInXkRc9mQFdbVbUMNxG1VVnrpKEyoPN"
    
    st.session_state["sync_status"] = "🔄 Running Drive Sync Engine..."
    
    try:
        files = get_all_drive_files_recursive(folder_id, drive_api_key)
        st.session_state["sync_status"] = f"🔄 Found {len(files)} files on Drive. Syncing..."
        
        synced_count = 0
        for f in files:
            file_id = f["id"]
            file_name = f["name"]
            mime = f["mime_type"]
            mod_time = f["modified_time"]
            
            db_f = get_drive_file(file_id)
            if not db_f or db_f["modified_time"] != mod_time:
                st.session_state["sync_status"] = f"🔄 Downloading {file_name}..."
                local_path = download_drive_file(file_id, file_name, drive_api_key)
                if not local_path:
                    continue
                
                st.session_state["sync_status"] = f"🔄 Auto-detecting {file_name}..."
                sample_text = ""
                file_ext = file_name.split('.')[-1].lower()
                
                try:
                    if file_ext == "pdf":
                        import pdfplumber
                        with pdfplumber.open(local_path) as pdf:
                            for page in pdf.pages[:3]:
                                sample_text += (page.extract_text() or "") + "\n"
                    elif file_ext == "docx":
                        import docx
                        doc = docx.Document(local_path)
                        sample_text = "\n".join([p.text for p in doc.paragraphs[:50]])
                    elif file_ext in ["txt", "py", "c", "cpp"]:
                        with open(local_path, "r", encoding="utf-8", errors="ignore") as file_handle:
                            sample_text = file_handle.read()
                    elif file_ext == "zip":
                        sample_text = "Zip archive containing code files."
                except Exception as e:
                    print(f"Error reading file {file_name} for auto-detect: {e}")
                    
                meta = auto_detect_subject_metadata(file_name, sample_text, gemini_api_key)
                
                st.session_state["sync_status"] = f"🔄 Parsing {file_name} ({meta['document_type']})..."
                subject_code = meta.get("subject_code")
                semester = meta.get("semester", 2)
                branch = meta.get("branch", "ALL")
                doc_type = meta.get("document_type", "other")
                
                if doc_type == "syllabus":
                    with open(local_path, "rb") as f_stream:
                        parse_and_import_syllabus(f_stream, subject_code)
                elif doc_type == "question_bank" or doc_type == "mcqs":
                    with open(local_path, "rb") as f_stream:
                        parse_and_import_qb(f_stream, file_ext, subject_code, default_unit=3)
                elif doc_type == "lab_program":
                    if file_ext == "zip":
                        parse_zip_lab_programs(local_path, subject_code)
                    elif file_ext in ["py", "c", "cpp", "txt"]:
                        explanation = f"Source file: {file_name}"
                        add_lab_program(subject_code, file_name, sample_text, explanation)
                elif doc_type == "notes":
                    parse_notes_via_gemini(sample_text, subject_code, gemini_api_key)
                
                save_drive_file(file_id, file_name, mime, mod_time, branch, semester, subject_code, processed=1)
                synced_count += 1
                
        st.session_state["sync_status"] = f"✅ Sync Complete. Processed {synced_count} new/modified files."
    except Exception as e:
        st.session_state["sync_status"] = f"❌ Sync Failed: {e}"
        print(f"[Sync Engine] Failed: {e}")

def start_sync_thread(force=False):
    now = time.time()
    last_sync = st.session_state.get("last_drive_sync_time", 0)
    
    if force or (now - last_sync > 900): # 15 minutes
        st.session_state["last_drive_sync_time"] = now
        t = threading.Thread(target=sync_drive_files_engine, daemon=True)
        t.start()


def init_sm2_columns():
    try:
        conn = get_academic_conn()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(review_schedule)")
        columns = [row[1] for row in cursor.fetchall()]
        
        modified = False
        if "easiness_factor" not in columns:
            cursor.execute("ALTER TABLE review_schedule ADD COLUMN easiness_factor REAL DEFAULT 2.5")
            modified = True
        if "repetitions" not in columns:
            cursor.execute("ALTER TABLE review_schedule ADD COLUMN repetitions INTEGER DEFAULT 0")
            modified = True
        if "interval" not in columns:
            cursor.execute("ALTER TABLE review_schedule ADD COLUMN interval INTEGER DEFAULT 0")
            modified = True
            
        if modified:
            conn.commit()
        conn.close()
    except Exception:
        pass

init_sm2_columns()

def get_drive_api_key():
    import os
    import streamlit as st
    try:
        if "google_drive" in st.secrets and "api_key" in st.secrets["google_drive"]:
            return st.secrets["google_drive"]["api_key"]
    except Exception:
        pass
    env_key = os.environ.get("GOOGLE_DRIVE_API_KEY") or os.environ.get("DRIVE_API_KEY")
    if env_key:
        return env_key
    return "AIzaSyCMuWAi15u9nrqoH20xN5kqdbho2tVCVws"

def get_gemini_api_key():
    import os
    import streamlit as st
    try:
        if "gemini" in st.secrets and "api_key" in st.secrets["gemini"]:
            return st.secrets["gemini"]["api_key"]
    except Exception:
        pass
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return env_key
    return get_drive_api_key()


def parse_and_import_syllabus(uploaded_file, subject_code):
    import re
    import pdfplumber
    
    text = ""
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
    except Exception as e:
        return False, f"Failed to parse syllabus PDF: {str(e)}"
        
    lines = text.split('\n')
    current_unit = 1
    topics_imported = 0
    
    unit_pattern = re.compile(r'unit\s*[-:\s]*([iIvVxX\d]+)', re.IGNORECASE)
    
    conn = get_academic_conn()
    cursor = conn.cursor()
    
    for line in lines:
        line_str = line.strip()
        if not line_str or len(line_str) < 5 or len(line_str) > 120:
            continue
            
        # Check for unit header
        unit_match = unit_pattern.search(line_str)
        if unit_match and len(line_str) < 30:
            unit_val = unit_match.group(1).upper()
            roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5}
            current_unit = roman_map.get(unit_val, current_unit)
            continue
            
        # Ignore common layout texts or headers
        if any(w in line_str.lower() for w in ["syllabus", "page", "credits", "lecture", "l t p c"]):
            continue
            
        # Insert as syllabus topic
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO syllabus_topics (subject_code, unit, topic_text)
                VALUES (?, ?, ?)
            ''', (subject_code, current_unit, line_str))
            topics_imported += 1
        except Exception:
            pass
            
    conn.commit()
    conn.close()
    return True, f"Successfully parsed and loaded {topics_imported} syllabus topics for {subject_code}!"


def extract_options_helper(opt_text):
    import re
    opt_text = opt_text.replace('\t', ' ').replace('\n', ' ').strip()
    pattern = r'\b([a-d])\s*[\).\s]'
    matches = list(re.finditer(pattern, opt_text, re.IGNORECASE))
    
    opts = {'a': '', 'b': '', 'c': '', 'd': ''}
    
    if len(matches) >= 3:
        matches = sorted(matches, key=lambda x: x.start())
        first_m = matches[0].group(1).lower()
        if first_m != 'a':
            opts['a'] = opt_text[:matches[0].start()].strip()
            
        for i in range(len(matches)):
            m_char = matches[i].group(1).lower()
            start_pos = matches[i].end()
            end_pos = matches[i+1].start() if i + 1 < len(matches) else len(opt_text)
            
            val = opt_text[start_pos:end_pos].strip()
            val = re.sub(r'\[\s*\]\s*$', '', val).strip()
            opts[m_char] = val
    else:
        pattern_fallback = r'(?:\(?([a-d])\)|([a-d])\s*[\).\s])\s*([^(\n\t]+)'
        fallback_matches = re.findall(pattern_fallback, opt_text, re.IGNORECASE)
        for m in fallback_matches:
            char = m[0] or m[1]
            val = m[2].strip()
            opts[char.lower()] = val
            
    return opts['a'], opts['b'], opts['c'], opts['d']


def parse_and_import_qb(uploaded_file, file_type, subject_code, default_unit=3):
    import re
    import sqlite3
    
    actual_code = get_actual_subject_code(subject_code)
    
    descriptive_questions = []
    mcq_questions = []
    fib_questions = []
    
    if file_type == "pdf":
        import pdfplumber
        text = ""
        try:
            if hasattr(uploaded_file, "read"):
                uploaded_file.seek(0)
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    text += (page.extract_text() or "") + "\n"
        except Exception as e:
            return False, f"Failed to parse PDF: {str(e)}"
            
        lines = text.split('\n')
        current_unit = default_unit
        
        q_pattern = re.compile(r'^(\d+)([a-z])?\)\s*(.*)', re.IGNORECASE)
        unit_pattern = re.compile(r'unit\s*[-:\s]*([iIvVxX\d]+)', re.IGNORECASE)
        
        current_q = None
        
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
                
            unit_match = unit_pattern.search(line_str)
            if unit_match and len(line_str) < 30:
                unit_val = unit_match.group(1).upper()
                roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5}
                current_unit = roman_map.get(unit_val, current_unit)
                continue
                
            q_match = q_pattern.match(line_str)
            if q_match:
                q_num = q_match.group(1)
                q_sub = q_match.group(2) or ''
                q_text = q_match.group(3)
                
                marks = "10M"
                marks_match = re.search(r'\((\d+)\s*(?:Marks|M|Marks\))', q_text, re.IGNORECASE)
                if marks_match:
                    marks = f"{marks_match.group(1)}M"
                    q_text = re.sub(r'\((\d+)\s*(?:Marks|M|Marks\))\)', '', q_text).strip()
                elif q_text.strip().endswith('M)') or q_text.strip().endswith('Marks)'):
                    ending_match = re.search(r'\(?(\d+)\s*(?:M|Marks)\)?$', q_text.strip(), re.IGNORECASE)
                    if ending_match:
                        marks = f"{ending_match.group(1)}M"
                        q_text = re.sub(r'\(?(\d+)\s*(?:M|Marks)\)?$', '', q_text.strip()).strip()
                        
                if current_q:
                    descriptive_questions.append(current_q)
                    
                current_q = {
                    'subject_code': actual_code,
                    'unit': current_unit,
                    'q_type': 'DESCRIPTIVE',
                    'question': q_text,
                    'answer_text': '',
                    'marks': marks,
                    'co': '1',
                    'btl': 'L2'
                }
            else:
                if current_q:
                    if len(current_q['question']) < 120 and not current_q['question'].endswith('?') and not current_q['answer_text']:
                        current_q['question'] += " " + line_str
                    else:
                        current_q['answer_text'] += "\n" + line_str
                        
        if current_q:
            descriptive_questions.append(current_q)
            
    elif file_type == "docx":
        import docx
        try:
            if hasattr(uploaded_file, "read"):
                uploaded_file.seek(0)
            doc = docx.Document(uploaded_file)
        except Exception as e:
            return False, f"Failed to parse Word document: {str(e)}"
            
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        
        body_elements = []
        for child in doc.element.body:
            if child.tag.endswith('p'):
                body_elements.append(Paragraph(child, doc))
            elif child.tag.endswith('tbl'):
                body_elements.append(Table(child, doc))
                
        unit_data = {}
        current_unit = default_unit
        unit_re = re.compile(r'UNIT[-–\s]*([IVX\d]+)', re.IGNORECASE)
        
        in_objectives_global = False
        
        for element in body_elements:
            if isinstance(element, Paragraph):
                text = element.text.strip()
                if not text:
                    continue
                if "OBJECTIVE" in text.upper():
                    in_objectives_global = True
                unit_match = unit_re.search(text)
                if unit_match and ("UNIT" in text.upper() or len(text) < 50):
                    unit_str = unit_match.group(1).upper()
                    roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5}
                    current_unit = roman_map.get(unit_str, current_unit)
                    
            if current_unit not in unit_data:
                unit_data[current_unit] = []
            unit_data[current_unit].append(element)
            
        for unit, elements in sorted(unit_data.items()):
            unit_paras = [e for e in elements if isinstance(e, Paragraph)]
            unit_tables = [e for e in elements if isinstance(e, Table)]
            
            desc_table = None
            for t in unit_tables:
                headers = [cell.text.strip().upper() for cell in t.rows[0].cells]
                if any('DESCRIPTION' in h or 'QUESTION' in h for h in headers) and not any('ANSWER' in h for h in headers):
                    desc_table = t
                    break
                    
            if desc_table:
                headers = [cell.text.strip().replace('\n', ' ') for cell in desc_table.rows[0].cells]
                q_no_col = -1
                part_col = -1
                desc_col = -1
                marks_col = -1
                
                for col_idx, h in enumerate(headers):
                    hu = h.upper()
                    if 'Q.NO.' in hu or 'Q.NO' in hu or 'Q. NO' in hu or 'Q. NO.' in hu:
                        q_no_col = col_idx
                    elif 'PART' in hu or 'SUB' in hu:
                        part_col = col_idx
                    elif 'DESCRIPTION' in hu or 'QUESTION' in hu:
                        desc_col = col_idx
                    elif 'MARKS' in hu or 'MARK' in hu:
                        marks_col = col_idx
                        
                for row in desc_table.rows[1:]:
                    cells = [c.text.strip() for c in row.cells]
                    q_no_val = cells[q_no_col] if q_no_col != -1 and q_no_col < len(cells) else ""
                    part_val = cells[part_col] if part_col != -1 and part_col < len(cells) else ""
                    desc_val = cells[desc_col] if desc_col != -1 and desc_col < len(cells) else ""
                    marks_val = cells[marks_col] if marks_col != -1 and marks_col < len(cells) else "10M"
                    
                    if desc_val:
                        q_prefix = f"{q_no_val}{part_val})" if q_no_val else ""
                        descriptive_questions.append({
                            'subject_code': actual_code,
                            'unit': unit,
                            'q_type': 'DESCRIPTIVE',
                            'question': desc_val,
                            'answer_text': '',
                            'marks': marks_val,
                            'co': '1',
                            'btl': 'L2',
                            'prefix': q_prefix
                        })
                        
            objectives_paras = []
            in_obj_flow = False
            for p in unit_paras:
                t = p.text.strip()
                if not t:
                    continue
                if any(k in t.upper() for k in ["OBJECTIVE", "MULTIPLE CHOICE", "FILL-IN-THE-BLANK"]):
                    in_obj_flow = True
                    continue
                if in_objectives_global and unit_re.search(t) and len(t) < 50:
                    in_obj_flow = True
                    continue
                if in_obj_flow:
                    if unit_re.search(t) and len(t) < 40 and not any(k in t.upper() for k in ["OBJECTIVE"]):
                        break
                    objectives_paras.append(p)
                    
            clean_paras = []
            for p in objectives_paras:
                t = p.text.strip()
                if t.upper() in ["OBJECTIVE QUESTIONS", "OBJECTIVE KEY", "FILL-IN-THE-BLANK QUESTIONS"]:
                    continue
                clean_paras.append(t)
                
            fibs = []
            mcqs = []
            
            idx = 0
            while idx < len(clean_paras):
                t = clean_paras[idx]
                
                has_opts = "b)" in t.lower() or "b." in t.lower() or "(b)" in t.lower()
                next_is_options = False
                if idx + 1 < len(clean_paras):
                    next_t = clean_paras[idx+1]
                    next_has_opts = "b)" in next_t.lower() or "b." in next_t.lower() or "(b)" in next_t.lower()
                    next_is_q = next_t.endswith("?") or "[]" in next_t or "[ ]" in next_t or "___" in next_t
                    if next_has_opts and not next_is_q:
                        next_is_options = True
                        
                if has_opts or next_is_options:
                    q_text = t
                    opt_text = ""
                    if has_opts:
                        opt_text = t
                        first_opt_split = re.split(r'\b[a-d]\)|(?:\(?([a-d])\)|[a-d]\.\s+)', t, re.IGNORECASE, 1)
                        q_text_clean = first_opt_split[0].strip() if first_opt_split else t
                    else:
                        opt_text = clean_paras[idx+1]
                        idx += 1
                        q_text_clean = t
                        
                    q_text_clean = re.sub(r'\[\s*\]\s*$', '', q_text_clean).strip()
                    opt_a, opt_b, opt_c, opt_d = extract_options_helper(opt_text)
                    
                    mcqs.append({
                        "unit": unit,
                        "question": q_text_clean,
                        "option_a": opt_a,
                        "option_b": opt_b,
                        "option_c": opt_c,
                        "option_d": opt_d,
                        "answer": ""
                    })
                else:
                    q_text_clean = re.sub(r'\[\s*\]\s*$', '', t).strip()
                    fibs.append({
                        "unit": unit,
                        "question": q_text_clean,
                        "answer": ""
                    })
                idx += 1
                
            key_table = None
            for t in unit_tables:
                headers = [cell.text.strip().upper() for cell in t.rows[0].cells]
                is_k = any('ANSWER' in h for h in headers) or (len(headers) >= 4 and any(re.match(r'^\d+\.', h) for h in headers))
                if not is_k and len(t.columns) == 4 and len(t.rows) == 5:
                    is_k = True
                if is_k and t != desc_table:
                    key_table = t
                    break
                    
            answer_key_mapping = {}
            if key_table:
                headers = [cell.text.strip() for cell in key_table.rows[0].cells]
                if 'Q.No.' in headers or 'Q.NO.' in [h.upper() for h in headers]:
                    for row in key_table.rows[1:]:
                        cells = [c.text.strip() for c in row.cells]
                        if len(cells) >= 2:
                            q1, a1 = cells[0], cells[1]
                            if q1 and a1:
                                try:
                                    q_idx = int(q1)
                                    answer_key_mapping[q_idx] = a1
                                except ValueError:
                                    pass
                        if len(cells) >= 4:
                            q2, a2 = cells[2], cells[3]
                            if q2 and a2:
                                try:
                                    q_idx = int(q2)
                                    answer_key_mapping[q_idx] = a2
                                except ValueError:
                                    pass
                else:
                    for r_idx, row in enumerate(key_table.rows):
                        cells = [c.text.strip() for c in row.cells]
                        for col_idx, cell_text in enumerate(cells):
                            if not cell_text:
                                continue
                            prefix_match = re.match(r'^(\d+)\.\s*(.*)$', cell_text)
                            if prefix_match:
                                q_idx = int(prefix_match.group(1))
                                ans_val = prefix_match.group(2).strip()
                                answer_key_mapping[q_idx] = ans_val
                            else:
                                q_idx = col_idx * 5 + r_idx + 1
                                answer_key_mapping[q_idx] = cell_text
                                
            for i in range(min(len(fibs), 10)):
                fibs[i]["answer"] = answer_key_mapping.get(i+1, "")
                
            for i in range(min(len(mcqs), 10)):
                mcqs[i]["answer"] = answer_key_mapping.get(i+11, "")
                
            for fib in fibs:
                fib_questions.append(fib)
            for mcq in mcqs:
                mcq_questions.append(mcq)
                    
    else:
        return False, "Unsupported file format. Please upload PDF or DOCX."
        
    if not descriptive_questions and not mcq_questions and not fib_questions:
        api_key = get_gemini_api_key()
        if api_key:
            if file_type == "docx" and 'doc' in locals():
                text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            elif file_type == "pdf" and 'text' in locals():
                pass
            else:
                text = ""
                
            if text:
                import requests
                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                headers = {"Content-Type": "application/json"}
                prompt = f"""
                You are a strict question bank parsing assistant. Your task is to extract all Descriptive Questions, MCQs, and Fill-in-the-Blank (FIB) questions from the provided course text.
                You must output a single, raw, valid JSON object with NO markdown wrapper (do not wrap in ```json), matching this schema:
                {{
                  "descriptive": [
                    {{"question": "full question text", "marks": "Marks (e.g. 10M or 2M)", "unit": 3, "co": "1", "btl": "L2"}}
                  ],
                  "mcqs": [
                    {{"question": "question text", "option_a": "option A", "option_b": "option B", "option_c": "option C", "option_d": "option D", "answer": "A/B/C/D", "unit": 3}}
                  ],
                  "fibs": [
                    {{"question": "question text with blank", "answer": "correct answer", "unit": 3}}
                  ]
                }}
                
                Ensure the unit matches the questions. If the text has no clear unit, use 3.
                
                Text:
                {text[:30000]}
                """
                try:
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}]
                    }
                    res = requests.post(gemini_url, json=payload, headers=headers, timeout=30)
                    if res.status_code == 200:
                        json_text = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                        if json_text.startswith("```json"):
                            json_text = json_text[7:]
                        if json_text.endswith("```"):
                            json_text = json_text[:-3]
                        json_text = json_text.strip()
                        
                        parsed_data = json.loads(json_text)
                        
                        for q in parsed_data.get("descriptive", []):
                            descriptive_questions.append({
                                'subject_code': actual_code,
                                'unit': q.get('unit', default_unit),
                                'q_type': 'DESCRIPTIVE',
                                'question': q.get('question'),
                                'answer_text': '',
                                'marks': q.get('marks', '10M'),
                                'co': q.get('co', '1'),
                                'btl': q.get('btl', 'L2')
                            })
                        for q in parsed_data.get("mcqs", []):
                            mcq_questions.append({
                                'unit': q.get('unit', default_unit),
                                'question': q.get('question'),
                                'option_a': q.get('option_a'),
                                'option_b': q.get('option_b'),
                                'option_c': q.get('option_c'),
                                'option_d': q.get('option_d'),
                                'answer': q.get('answer', '')
                            })
                        for q in parsed_data.get("fibs", []):
                            fib_questions.append({
                                'unit': q.get('unit', default_unit),
                                'question': q.get('question'),
                                'answer': q.get('answer', '')
                            })
                except Exception:
                    pass

    conn = get_academic_conn()
    cursor = conn.cursor()
    
    desc_imported = 0
    mcq_imported = 0
    fib_imported = 0
    
    for q in descriptive_questions:
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO question_banks 
                (subject_code, unit, q_type, question, answer_text, marks, co, btl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (q['subject_code'], q['unit'], 'DESCRIPTIVE', q['question'].strip(), q['answer_text'].strip(), q['marks'], q['co'], q['btl']))
            desc_imported += 1
            
            topic_text = q['question'].split('?')[0].split('.')[0].strip()
            if len(topic_text) > 10 and len(topic_text) < 120:
                cursor.execute('''
                    INSERT OR IGNORE INTO syllabus_topics (subject_code, unit, topic_text)
                    VALUES (?, ?, ?)
                ''', (q['subject_code'], q['unit'], topic_text))
        except Exception:
            pass
            
    for q in fib_questions:
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO question_banks 
                (subject_code, unit, q_type, question, answer_text, marks, co, btl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (actual_code, q['unit'], 'FIB', q['question'].strip(), q['answer'].strip(), '2M', '1', 'L1'))
            fib_imported += 1
        except Exception:
            pass
            
    for q in mcq_questions:
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO mcqs
                (subject_code, unit, question, option_a, option_b, option_c, option_d, correct_option, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (actual_code, q['unit'], q['question'].strip(), q['option_a'].strip(), q['option_b'].strip(), q['option_c'].strip(), q['option_d'].strip(), q['answer'].strip(), ''))
            mcq_imported += 1
        except Exception:
            pass
            
    conn.commit()
    conn.close()
    
    msg = f"Successfully parsed and loaded: {desc_imported} descriptive questions, {mcq_imported} MCQs, and {fib_imported} FIBs for {subject_code}!"
    return True, msg

# ── DATABASE HELPERS ─────────────────────────────────────────

def get_subject_display_name(code, roll_no):
    code = get_actual_subject_code(code)
    
    subject_names = {
        "2504103ES": "Electronic Devices and Circuits",
        "2566103ES": "Python Programming",
        "23EE104ES": "Basic Electrical Engineering",
        "2512105ES": "Programming for Problem Solving",
        "25CH102BS": "Engineering Chemistry",
        "25MA201BS": "Ordinary Differential Equations and Vector Calculus",
        "NAS": "Network Analysis and Synthesis",
        "25PH102BS": "Applied Engineering Physics",
        "2502105ES": "Introduction to Electrical Engineering",
        "2503104ES": "Engineering Drawing",
        "25EN105HS": "English for Professional Success",
        "EDC": "Electronic Devices and Circuits",
        "PYTHON": "Python Programming",
        "BEE": "Basic Electrical Engineering",
        "PPS": "Programming for Problem Solving",
        "Chemistry": "Engineering Chemistry",
        "ODEVC": "Ordinary Differential Equations and Vector Calculus",
        "M&C": "Mathematics & Calculus",
        "IEE": "Introduction to Engineering Electromagnetics",
        "ED": "Engineering Drawing",
        "ENG": "English for Professional Success",
        "AEP": "Applied Engineering Physics",
        "DS": "Data Structures",
        "EC": "Engineering Chemistry"
    }
    
    full_name = subject_names.get(code, code)
    
    # Extract branch from roll number using indices [6:8]
    branch_map = {
        "01": "CIVIL", "02": "EEE", "03": "MECH",
        "04": "ECE", "05": "CSE", "10": "EIE",
        "12": "IT", "66": "CSE AIML", "67": "CSE DS",
        "72": "AIDS", "73": "AIML"
    }
    branch_name = "CSE"  # default fallback
    if roll_no and len(roll_no) >= 8:
        b_code = roll_no[6:8]
        if b_code in branch_map:
            branch_name = branch_map[b_code]
            
    return f"{full_name} [{code}] (for {branch_name} students only)"

def resolve_subject_display_name(display_name):
    if not display_name:
        return ""
    import re
    match = re.search(r'\[([^\]]+)\]', display_name)
    if match:
        return match.group(1).strip()
    return display_name.strip()

def get_actual_subject_code(code):
    mapping = {
        "EDC": "2504103ES",
        "PYTHON": "2566103ES",
        "BEE": "23EE104ES",
        "PPS": "2512105ES",
        "Chemistry": "25CH102BS",
        "ODEVC": "25MA201BS",
        "NAS": "NAS",
        "M&C": "25PH102BS",
        "IEE": "2502105ES",
        "ED": "2503104ES",
        "ENG": "25EN105HS",
        "AEP": "25PH102BS"
    }
    return mapping.get(code, code)

def get_student_backlogs(roll_no):
    import sqlite3
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_db_path = os.path.join(base_dir, "vits_erp.db")
    
    conn = sqlite3.connect(main_db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('''
        SELECT subject, semester, score
        FROM marks
        WHERE roll_no=? AND exam_type LIKE '%Final Examinations' AND (score < 40 OR score IS NULL)
    ''', (roll_no,)).fetchall()
    conn.close()
    
    backlogs = []
    for r in rows:
        backlogs.append({
            'roll_no': roll_no,
            'subject_code': r['subject'],
            'backlog_sem': int(r['semester'].replace("Sem ", "").strip()) if "Sem" in r['semester'] else 1,
            'status': 'ACTIVE'
        })
    return backlogs

def get_student_exam_warnings(roll_no):
    import sqlite3
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_db_path = os.path.join(base_dir, "vits_erp.db")
    
    conn = sqlite3.connect(main_db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('''
        SELECT subject, score, exam_type
        FROM marks
        WHERE roll_no=? AND (
            (exam_type LIKE 'Mid%' AND score < 10) OR
            (exam_type NOT LIKE 'Mid%' AND exam_type NOT LIKE '%Final%' AND score < 40)
        )
    ''', (roll_no,)).fetchall()
    conn.close()
    
    warnings = []
    for r in rows:
        warnings.append({
            'subject': r['subject'],
            'score': r['score'],
            'max_score': 25 if 'Mid' in r['exam_type'] else 100,
            'exam_type': r['exam_type']
        })
    return warnings

def get_academic_resources(branch, semester):
    conn = get_academic_conn()
    rows = conn.execute('SELECT * FROM academic_resources WHERE branch=? AND semester=?', (branch, semester)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_syllabus_topics(subject_code):
    subject_code = get_actual_subject_code(subject_code)
    conn = get_academic_conn()
    rows = conn.execute('SELECT * FROM syllabus_topics WHERE subject_code=? ORDER BY unit, id', (subject_code,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_student_progress(roll_no):
    conn = get_academic_conn()
    rows = conn.execute('SELECT topic_id, status FROM student_syllabus_progress WHERE roll_no=?', (roll_no,)).fetchall()
    conn.close()
    return {r['topic_id']: r['status'] for r in rows}

def get_backlog_subject_progress(roll_no, subject_code):
    actual_code = get_actual_subject_code(subject_code)
    conn = get_academic_conn()
    topics = conn.execute('SELECT id, unit FROM syllabus_topics WHERE subject_code=?', (actual_code,)).fetchall()
    progress_rows = conn.execute('''
        SELECT topic_id, status 
        FROM student_syllabus_progress 
        WHERE roll_no=? AND topic_id IN (
            SELECT id FROM syllabus_topics WHERE subject_code=?
        )
    ''', (roll_no, actual_code)).fetchall()
    conn.close()
    
    progress_map = {r['topic_id']: r['status'] for r in progress_rows}
    
    unit_stats = {}
    for unit in [1, 2, 3, 4, 5]:
        unit_stats[unit] = {'total': 0, 'completed': 0}
        
    for t in topics:
        unit = t['unit']
        if unit in unit_stats:
            unit_stats[unit]['total'] += 1
            if progress_map.get(t['id']) == 'MASTERED':
                unit_stats[unit]['completed'] += 1
                
    return unit_stats

def update_syllabus_progress(roll_no, topic_id, status):
    conn = get_academic_conn()
    conn.execute('INSERT OR REPLACE INTO student_syllabus_progress (roll_no, topic_id, status) VALUES (?, ?, ?)',
                 (roll_no, topic_id, status))
    conn.commit()
    conn.close()

def get_question_bank(subject_code, unit, q_type=None):
    subject_code = get_actual_subject_code(subject_code)
    conn = get_academic_conn()
    if q_type:
        rows = conn.execute('SELECT * FROM question_banks WHERE subject_code=? AND unit=? AND q_type=?', (subject_code, unit, q_type)).fetchall()
    else:
        rows = conn.execute('SELECT * FROM question_banks WHERE subject_code=? AND unit=?', (subject_code, unit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_mcqs(subject_code, unit):
    subject_code = get_actual_subject_code(subject_code)
    conn = get_academic_conn()
    rows = conn.execute('SELECT * FROM mcqs WHERE subject_code=? AND unit=?', (subject_code, unit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_class_sessions(subject_code):
    subject_code = get_actual_subject_code(subject_code)
    conn = get_academic_conn()
    rows = conn.execute('SELECT * FROM class_sessions WHERE subject_code=? ORDER BY class_date', (subject_code,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_srs_reviews(roll_no):
    import datetime
    today = datetime.date.today().isoformat()
    conn = get_academic_conn()
    rows = conn.execute('''
        SELECT r.mcq_id, r.difficulty, r.easiness_factor, r.repetitions, r.interval, r.next_review, 
               m.question, m.option_a, m.option_b, m.option_c, m.option_d, m.correct_option, m.subject_code, m.unit
        FROM review_schedule r
        JOIN mcqs m ON r.mcq_id = m.id
        WHERE r.roll_no=? AND (r.next_review <= ? OR r.next_review IS NULL)
    ''', (roll_no, today)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_srs_review(roll_no, mcq_id, quality=3):
    import datetime
    conn = get_academic_conn()
    row = conn.execute("SELECT * FROM review_schedule WHERE roll_no=? AND mcq_id=?", (roll_no, mcq_id)).fetchone()
    
    easiness_factor = 2.5
    repetitions = 0
    interval = 0
    
    if row:
        row_dict = dict(row)
        easiness_factor = row_dict.get("easiness_factor") or 2.5
        repetitions = row_dict.get("repetitions") or 0
        interval = row_dict.get("interval") or 0
        
    if quality >= 3:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = int(interval * easiness_factor)
        repetitions += 1
    else:
        repetitions = 0
        interval = 1
        
    easiness_factor = easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if easiness_factor < 1.3:
        easiness_factor = 1.3
        
    next_review_date = (datetime.date.today() + datetime.timedelta(days=interval)).isoformat()
    
    conn.execute('''
        INSERT OR REPLACE INTO review_schedule (roll_no, mcq_id, next_review, difficulty, easiness_factor, repetitions, interval)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (roll_no, mcq_id, next_review_date, quality, easiness_factor, repetitions, interval))
    conn.commit()
    conn.close()



def remove_srs_review(roll_no, mcq_id):
    conn = get_academic_conn()
    conn.execute('DELETE FROM review_schedule WHERE roll_no=? AND mcq_id=?', (roll_no, mcq_id))
    conn.commit()
    conn.close()
def show_academic_hub_page(student, sem):
    # Ensure roll_no is available in session state for helpers
    st.session_state["roll_no"] = student['roll_no']
    # Trigger the background sync thread (runs once every 15 mins, or forced)
    start_sync_thread()
    
    # Premium glassmorphic styling
    st.markdown("""
    <style>
    div.academic-card {
        background: rgba(13, 20, 38, 0.55) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(0, 216, 198, 0.15) !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4) !important;
        border-radius: 16px !important;
        padding: 24px;
        margin-bottom: 20px;
        transition: all 0.3s ease;
    }
    div.academic-card:hover {
        border-color: rgba(0, 216, 198, 0.35) !important;
        box-shadow: 0 12px 40px rgba(0, 216, 198, 0.12) !important;
    }
    div.academic-card-purple {
        background: rgba(13, 20, 38, 0.55) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(139, 92, 246, 0.18) !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4) !important;
        border-radius: 16px !important;
        padding: 24px;
        margin-bottom: 20px;
        transition: all 0.3s ease;
    }
    div.academic-card-purple:hover {
        border-color: rgba(139, 92, 246, 0.38) !important;
        box-shadow: 0 12px 40px rgba(139, 92, 246, 0.12) !important;
    }
    .subject-card {
        background: rgba(20, 28, 48, 0.4) !important;
        backdrop-filter: blur(15px) !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        border-radius: 16px !important;
        padding: 18px !important;
        margin-bottom: 12px !important;
        transition: all 0.25s ease !important;
    }
    .subject-card:hover {
        border-color: rgba(0,216,198,0.3) !important;
        box-shadow: 0 10px 30px rgba(0,216,198,0.1) !important;
    }
    .card-bar-bg {
        width: 100% !important; height: 8px !important; background: rgba(255,255,255,0.08) !important;
        border-radius: 99px !important; overflow: hidden !important; margin: 10px 0 !important;
    }
    .card-bar-fill { height: 100% !important; border-radius: 99px !important; transition: width 0.6s ease !important; }
    </style>
    """, unsafe_allow_html=True)

    # Notion/Linear Navigation menu at the top
    if "academic_hub_sub_page" not in st.session_state:
        st.session_state["academic_hub_sub_page"] = "Dashboard"
        
    nav_cols = st.columns(5)
    nav_options = [
        ("🏠 Dashboard", "Dashboard"),
        ("📚 Subjects", "Subjects"),
        ("⚡ Exam Prep", "Exam Prep"),
        ("⚠️ Recovery", "Backlog Recovery"),
        ("🤖 AI Copilot", "AI Copilot")
    ]
    
    for idx, (label, val) in enumerate(nav_options):
        is_active = (st.session_state["academic_hub_sub_page"] == val)
        if nav_cols[idx].button(label, key=f"sub_nav_btn_{val}", use_container_width=True, 
                               type="primary" if is_active else "secondary"):
            st.session_state["academic_hub_sub_page"] = val
            st.rerun()
            
    st.markdown("<hr style='border: 0; height: 1px; background: rgba(255,255,255,0.08); margin-bottom: 25px;'>", unsafe_allow_html=True)
    
    current_sub = st.session_state["academic_hub_sub_page"]
    
    if current_sub == "Dashboard":
        render_dashboard_view(student)
    elif current_sub == "Subjects":
        render_subjects_view(student)
    elif current_sub == "Exam Prep":
        render_exam_prep_view(student)
    elif current_sub == "Backlog Recovery":
        render_backlog_recovery_view(student)
    elif current_sub == "AI Copilot":
        render_ai_copilot_view(student)


def get_subjects_list_all():
    conn = get_academic_conn()
    rows = conn.execute("SELECT DISTINCT subject_code FROM question_banks UNION SELECT DISTINCT subject_code FROM syllabus_topics UNION SELECT DISTINCT subject FROM drive_files WHERE processed=1").fetchall()
    conn.close()
    
    results = []
    for r in rows:
        code = r[0]
        if code:
            results.append({
                "subject_code": code,
                "display_name": get_subject_display_name(code, st.session_state.get("roll_no", "25H41A0401"))
            })
    return results


def get_topics_missed_for_student(roll_no):
    import sqlite3
    import os
    import random
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_db_path = os.path.join(base_dir, "vits_erp.db")
    
    absences = []
    if os.path.exists(main_db_path):
        try:
            conn = sqlite3.connect(main_db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT date, subject FROM hour_wise_attendance WHERE roll_no=?", (roll_no,)).fetchall()
            absences = [dict(r) for r in rows]
            conn.close()
        except Exception as e:
            print(f"Error fetching absences: {e}")
            
    if not absences:
        return {}
        
    conn_acad = get_academic_conn()
    missed = {}
    
    cnt = conn_acad.execute("SELECT COUNT(*) FROM syllabus_delivery_log").fetchone()[0]
    if cnt == 0:
        topics_pool = {
            "2566103ES": ["Introduction to Python", "Variables & Types", "Conditional Statements", "Loops (for/while)", "Functions", "Recursion", "Lists & Tuples", "Dictionaries & Sets"],
            "2504103ES": ["PN Junction Diode", "Zener Diode Characteristics", "Half Wave Rectifier", "Full Wave Rectifier", "BJT Operation", "BJT Configurations", "JFET Characteristics", "MOSFET Characteristics"],
            "23EE104ES": ["DC Circuits Basics", "Mesh Analysis", "Nodal Analysis", "AC Circuits Introduction", "Transformers Principles", "DC Motors Operation", "Three Phase Systems", "Electrical Safety"],
            "2512105ES": ["Introduction to C", "Operators & Expressions", "Arrays in C", "Strings & Operations", "Pointers Basics", "Structures & Unions", "File Handling in C", "Dynamic Memory Allocation"],
            "25CH102BS": ["Water Chemistry", "Hardness of Water", "Electrochemistry", "Corrosion & Prevention", "Polymer Materials", "Lubricants Types", "Nanomaterials", "Spectroscopy Techniques"],
            "25MA201BS": ["Ordinary Differential Equations", "Linear ODEs", "Vector Calculus", "Gradient, Divergence, Curl", "Line Integrals", "Surface Integrals", "Green's Theorem", "Stokes' Theorem"]
        }
        
        seen_combos = set()
        for ab in absences:
            dt_val = ab["date"]
            sub_name = ab["subject"]
            sub_code = get_actual_subject_code(sub_name)
            combo_key = (dt_val, sub_code)
            if combo_key not in seen_combos:
                seen_combos.add(combo_key)
                pool = topics_pool.get(sub_code, ["Introduction to Topic", "Advanced Concepts", "Practical Applications", "Review Session"])
                chosen_topic = random.choice(pool)
                conn_acad.execute('''
                    INSERT OR IGNORE INTO syllabus_delivery_log (class_date, subject_code, topic)
                    VALUES (?, ?, ?)
                ''', (dt_val, sub_code, chosen_topic))
        conn_acad.commit()
        
    for ab in absences:
        dt_val = ab["date"]
        sub_name = ab["subject"]
        sub_code = get_actual_subject_code(sub_name)
        
        log_rows = conn_acad.execute('''
            SELECT topic FROM syllabus_delivery_log 
            WHERE class_date = ? AND subject_code = ?
        ''', (dt_val, sub_code)).fetchall()
        
        for r in log_rows:
            t = r[0]
            if sub_name not in missed:
                missed[sub_name] = []
            if t not in missed[sub_name]:
                missed[sub_name].append(t)
                
    conn_acad.close()
    return missed


def render_dashboard_view(student):
    import math
    roll = student['roll_no']
    name = student['name']
    branch = student['branch']
    
    hour = datetime.datetime.now().hour
    greeting = "Good Morning" if hour < 12 else "Good Afternoon" if hour < 17 else "Good Evening"
    
    st.markdown(f"""
    <div class="academic-card-purple">
        <h2 style="margin: 0; color: #8B5CF6; font-family: 'Outfit', sans-serif;">🌅 {greeting}, {name}!</h2>
        <p style="margin: 5px 0 0 0; font-size: 1.05rem; color: #cbd5e1;">Welcome to your AI Academic Copilot. Here is your personalized intelligence briefing for today.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if "sync_status" in st.session_state:
        status_color = "#00D8C6" if "Complete" in st.session_state["sync_status"] else "#F59E0B"
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); 
                    border-left: 4px solid {status_color}; border-radius: 8px; padding: 10px; margin-bottom: 20px; font-size: 0.85rem;">
            <b>Sync Engine Status:</b> {st.session_state["sync_status"]}
        </div>
        """, unsafe_allow_html=True)
        
    import sqlite3
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_db_path = os.path.join(base_dir, "vits_erp.db")
    
    att_rows = []
    marks_rows = []
    if os.path.exists(main_db_path):
        conn = sqlite3.connect(main_db_path)
        conn.row_factory = sqlite3.Row
        att_rows = conn.execute("SELECT * FROM attendance WHERE roll_no=?", (roll,)).fetchall()
        marks_rows = conn.execute("SELECT * FROM marks WHERE roll_no=?", (roll,)).fetchall()
        conn.close()
        
    total_conducted = sum(r['hours_conducted'] or 0 for r in att_rows)
    total_attended = sum(r['hours_attended'] or 0 for r in att_rows)
    attendance_pct = (total_attended / total_conducted * 100) if total_conducted > 0 else 0.0
    
    subjects_list = [r['subject_code'] for r in get_subjects_list_all()]
    total_topics = 0
    completed_topics = 0
    
    conn_acad = get_academic_conn()
    progress_rows = conn_acad.execute("SELECT topic_id, status FROM student_syllabus_progress WHERE roll_no=?", (roll,)).fetchall()
    progress_map = {r['topic_id']: r['status'] for r in progress_rows}
    
    for sub in subjects_list:
        sub_code = get_actual_subject_code(sub)
        t_rows = conn_acad.execute("SELECT id FROM syllabus_topics WHERE subject_code=?", (sub_code,)).fetchall()
        for tr in t_rows:
            total_topics += 1
            if progress_map.get(tr[0]) == 'MASTERED':
                completed_topics += 1
    conn_acad.close()
    
    syllabus_pct = (completed_topics / total_topics * 100) if total_topics > 0 else 0.0
    
    final_exam_scores = [r['score'] for r in marks_rows if 'Final' in r['exam_type'] and r['score'] is not None]
    avg_score = sum(final_exam_scores) / len(final_exam_scores) if final_exam_scores else 0.0
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Overall Attendance", f"{attendance_pct:.1f}%", help="Required is 75%+")
    with c2:
        st.metric("Syllabus Mastery", f"{syllabus_pct:.1f}%", f"{completed_topics}/{total_topics} Topics", help="Track syllabus topics in Subjects")
    with c3:
        st.metric("Academic Health Index", f"{avg_score:.1f}/100" if avg_score > 0 else "N/A", help="Average Final Exam Score")
        
    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    
    col_left, col_right = st.columns([1.1, 0.9])
    
    with col_left:
        st.markdown("### ⚠️ Academic Risk Analysis")
        has_alerts = False
        
        for r in att_rows:
            sub = r['subject']
            attended = r['hours_attended'] or 0
            conducted = r['hours_conducted'] or 0
            pct = (attended / conducted * 100) if conducted > 0 else 0.0
            
            if conducted > 0 and pct < 75.0:
                has_alerts = True
                needed = math.ceil((0.75 * conducted - attended) / (1 - 0.75))
                st.markdown(f"""
                <div style="background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.3); 
                            border-left: 4px solid #EF4444; border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong style="color: #fff;">Attendance Risk in {sub}</strong>
                        <span style="color: #EF4444; font-weight: 700;">{pct:.1f}%</span>
                    </div>
                    <p style="margin: 5px 0 0 0; font-size: 0.85rem; color: #cbd5e1;">
                        You are below the 75% threshold. You must attend <b>{needed}</b> consecutive classes of {sub} to restore your attendance.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
        warnings = get_student_exam_warnings(roll)
        for w in warnings:
            has_alerts = True
            st.markdown(f"""
            <div style="background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.3); 
                        border-left: 4px solid #F59E0B; border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong style="color: #fff;">Backlog Risk: {w['subject']}</strong>
                    <span style="color: #F59E0B; font-weight: 700;">{w['score']}/{w['max_score']}</span>
                </div>
                <p style="margin: 5px 0 0 0; font-size: 0.85rem; color: #cbd5e1;">
                    Your score is low in {w['exam_type']}. We recommend launching the <b>Backlog Recovery</b> program for this subject.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
        if not has_alerts:
            st.markdown("""
            <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); 
                        border-left: 4px solid #10B981; border-radius: 8px; padding: 15px; margin-bottom: 15px; text-align: center;">
                <span style="color: #10B981; font-weight: 600;">✨ No active academic risks detected. You are on track!</span>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        st.markdown("### 📴 Missed Classes & Syllabus Recovery")
        missed_topics = get_topics_missed_for_student(roll)
        if missed_topics:
            st.markdown("<p style='font-size: 0.9rem; color: #94a3b8; margin-bottom: 10px;'>Our sync engine cross-referenced your absent dates and identified the following taught topics you missed:</p>", unsafe_allow_html=True)
            for sub, topics in missed_topics.items():
                st.markdown(f"""
                <div class="academic-card" style="padding: 15px; margin-bottom: 10px; border-left: 4px solid #8B5CF6;">
                    <h5 style="margin: 0 0 8px 0; color: #fff;">{sub}</h5>
                    <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                """, unsafe_allow_html=True)
                for t in topics:
                    st.markdown(f"<span style='background: rgba(139, 92, 246, 0.15); border: 1px solid rgba(139, 92, 246, 0.3); color: #c084fc; border-radius: 6px; padding: 4px 8px; font-size: 0.8rem;'>{t}</span>", unsafe_allow_html=True)
                st.markdown(f"""
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; padding: 20px; text-align: center;">
                <p style="color: #cbd5e1; margin: 0; font-size: 0.9rem;">You have perfect attendance or no recorded lectures correspond to your absent days!</p>
            </div>
            """, unsafe_allow_html=True)
            
    with col_right:
        st.markdown("### 🗓️ Today's Study Planner")
        st.markdown("<p style='font-size: 0.9rem; color: #94a3b8; margin-bottom: 15px;'>Your AI Study Planner recommends completing these targets today to maximize recovery:</p>", unsafe_allow_html=True)
        
        tasks = []
        due_reviews = get_srs_reviews(roll)
        if due_reviews:
            tasks.append({
                "title": f"Revise {len(due_reviews)} due questions in spaced repetition",
                "tag": "SRS",
                "color": "#8B5CF6"
            })
            
        if missed_topics:
            for sub, topics in list(missed_topics.items())[:1]:
                tasks.append({
                    "title": f"Study missed topic: '{topics[0]}' in {sub}",
                    "tag": "Missed Class",
                    "color": "#EF4444"
                })
                
        tasks.append({
            "title": f"Take a practice quiz on your weak subject to build accuracy",
            "tag": "Quiz",
            "color": "#00D8C6"
        })
        
        for idx, task in enumerate(tasks):
            st.markdown(f"""
            <div class="academic-card" style="padding: 16px; margin-bottom: 12px; border-left: 4px solid {task['color']};">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 5px;">
                    <span style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); 
                                 border-radius: 4px; padding: 2px 6px; font-size: 0.7rem; color: {task['color']}; font-weight: 700; text-transform: uppercase;">
                        {task['tag']}
                    </span>
                </div>
                <p style="margin: 0; font-size: 0.9rem; color: #fff; font-weight: 500;">{task['title']}</p>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("#### 🤖 AI Generated Study Schedule")
        if st.button("✨ Generate Custom Study Plan", key="btn_gen_study_plan"):
            with st.spinner("AI is analyzing your workload..."):
                api_key = get_gemini_api_key()
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                headers = {"Content-Type": "application/json"}
                
                context = f"Student Name: {name}, Branch: {branch}, Attendance: {attendance_pct:.1f}%, Syllabus Completion: {syllabus_pct:.1f}%.\n"
                context += f"Missed Topics: {json.dumps(missed_topics)}.\n"
                context += f"Weak Exam Marks: {json.dumps(warnings)}.\n"
                
                prompt = f"""
                You are an expert AI Study Planner. Create a concise, action-oriented daily study schedule for this student based on their status:
                {context}
                
                Generate:
                1. Today's Tasks (3 items)
                2. Tomorrow's Tasks (3 items)
                3. A Weekly Focus Goal.
                
                Keep the output clear, short, and formatted in clean markdown.
                """
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}]
                }
                try:
                    res = requests.post(url, json=payload, headers=headers, timeout=25)
                    if res.status_code == 200:
                        st.markdown(res.json()["candidates"][0]["content"]["parts"][0]["text"])
                    else:
                        st.error("Failed to query Gemini API.")
                except Exception as e:
                    st.error(f"Error: {e}")


def render_subjects_view(student):
    import math
    roll = student['roll_no']
    
    subjects = get_subjects_list_all()
    if not subjects:
        st.markdown("""
        <div class="academic-card" style="text-align: center; padding: 50px;">
            <h3 style="color: #EF4444;">📭 No Academic Material Synchronized</h3>
            <p style="color: #cbd5e1; font-size: 0.95rem; margin-top: 10px;">
                We found no processed subjects in the database. Ensure that faculty have uploaded syllabus, question banks, lab code, and notes files to the Google Drive folder:
            </p>
            <p style="font-family: monospace; font-size: 0.9rem; background: rgba(255,255,255,0.05); padding: 8px; border-radius: 6px;">
                1bInXkRc9mQFdbVbUMNxG1VVnrpKEyoPN
            </p>
            <p style="color: #94a3b8; font-size: 0.85rem;">The background sync engine is active and will process them automatically.</p>
        </div>
        """, unsafe_allow_html=True)
        return
        
    active_subject = st.session_state.get("active_subject")
    
    if active_subject:
        if st.button("⬅️ Back to Subject Cards"):
            st.session_state["active_subject"] = None
            st.rerun()
            
        render_subject_deep_dive(student, active_subject)
        return
        
    st.markdown("### 📚 Subject Directory")
    st.markdown("<p style='font-size: 0.9rem; color: #94a3b8; margin-bottom: 20px;'>Explore courses, track unit checklists, practice quizzes, and view reference lab programs.</p>", unsafe_allow_html=True)
    
    rows_count = math.ceil(len(subjects) / 2)
    conn = get_academic_conn()
    
    for r_i in range(rows_count):
        cols = st.columns(2)
        for c_i in range(2):
            idx = r_i * 2 + c_i
            if idx < len(subjects):
                sub = subjects[idx]
                code = sub["subject_code"]
                
                total_topics = conn.execute("SELECT COUNT(*) FROM syllabus_topics WHERE subject_code=?", (code,)).fetchone()[0]
                completed_topics = conn.execute('''
                    SELECT COUNT(*) FROM student_syllabus_progress 
                    WHERE roll_no=? AND status='MASTERED' 
                      AND topic_id IN (SELECT id FROM syllabus_topics WHERE subject_code=?)
                ''', (roll, code)).fetchone()[0]
                total_q = conn.execute("SELECT COUNT(*) FROM question_banks WHERE subject_code=? AND q_type='DESCRIPTIVE'", (code,)).fetchone()[0]
                total_m = conn.execute("SELECT COUNT(*) FROM mcqs WHERE subject_code=?", (code,)).fetchone()[0]
                labs = conn.execute("SELECT COUNT(*) FROM lab_programs WHERE subject_code=?", (code,)).fetchone()[0]
                notes = conn.execute("SELECT COUNT(*) FROM notes WHERE subject_code=?", (code,)).fetchone()[0]
                
                last_up_row = conn.execute("SELECT modified_time FROM drive_files WHERE subject=? ORDER BY modified_time DESC LIMIT 1", (code,)).fetchone()
                last_up = last_up_row[0] if last_up_row else "N/A"
                if last_up != "N/A":
                    try:
                        dt_obj = datetime.datetime.strptime(last_up.split(".")[0].replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
                        last_up = dt_obj.strftime("%b %d, %Y")
                    except Exception:
                        pass
                
                pct = int((completed_topics / total_topics * 100)) if total_topics > 0 else 0
                
                with cols[c_i]:
                    st.markdown(f"""
                    <div class="subject-card">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                            <h4 style="margin: 0; color: #fff; font-family: 'Outfit'; font-size: 1.15rem;">
                                {get_subject_display_name(code, roll).split(" [")[0]}
                            </h4>
                            <span style="font-family: 'JetBrains Mono'; font-weight: 700; color: #00D8C6; font-size: 0.9rem;">
                                {pct}%
                            </span>
                        </div>
                        <span style="font-size: 0.75rem; color: #8B5CF6; font-family: 'JetBrains Mono'; font-weight: 600;">CODE: {code}</span>
                        <div class="card-bar-bg">
                            <div class="card-bar-fill" style="width: {pct}%; background: linear-gradient(90deg, #00D8C6 0%, #8B5CF6 100%);"></div>
                        </div>
                        
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px 15px; margin-top: 15px; font-size: 0.8rem; color: #cbd5e1;">
                            <div>📋 <b>Syllabus topics:</b> {completed_topics}/{total_topics}</div>
                            <div>❓ <b>Questions:</b> {total_q}</div>
                            <div>🎯 <b>Quiz MCQs:</b> {total_m}</div>
                            <div>💻 <b>Lab Scripts:</b> {labs}</div>
                            <div>📝 <b>Study Notes:</b> {notes}</div>
                            <div>🕒 <b>Updated:</b> {last_up}</div>
                        </div>
                    </div>
                    """.replace('\n', ' '), unsafe_allow_html=True)
                    
                    if st.button(f"🔍 Open {code} Study Deck", key=f"open_sub_btn_{code}", use_container_width=True):
                        st.session_state["active_subject"] = code
                        st.rerun()
                        
    conn.close()


def generate_tts_lecture_briefing(roll, subject_code, duration, cache_dir):
    with st.spinner("AI is generating speech narration..."):
        notes = get_notes(subject_code)
        
        text = f"Hello. This is your VITS Academic Copilot {duration} lecture briefing for subject code {subject_code}. "
        if not notes:
            text += "We do not have any notes synced in the database for this subject yet. Please make sure class notes files are uploaded to Google Drive."
        else:
            text += f"We will summarize {len(notes)} key topics. "
            limit = 3 if duration == "5 min" else 8 if duration == "15 min" else len(notes)
            for n in notes[:limit]:
                text += f"In Unit {n['unit']}, regarding {n['topic']}: {n['content'][:300]}. "
                
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang='en')
            audio_path = os.path.join(cache_dir, f"{roll}_{subject_code}_lecture.mp3")
            tts.save(audio_path)
            st.success("Narration audio generated successfully!")
        except Exception as e:
            st.error(f"Failed to generate Text-to-Speech audio: {e}")


def render_subject_deep_dive(student, subject_code):
    roll = student['roll_no']
    branch = student['branch']
    
    friendly_name = get_subject_display_name(subject_code, roll)
    
    st.markdown(f"""
    <div class="academic-card-purple" style="margin-bottom: 25px;">
        <h3 style="margin: 0; color: #8B5CF6;">{friendly_name}</h3>
        <p style="margin: 5px 0 0 0; font-size: 0.9rem; color: #cbd5e1;">Study Deck, Syllabus Checklists, Lab Codes, and Practice Quizzes.</p>
    </div>
    """, unsafe_allow_html=True)
    
    s_tabs = st.tabs(["📋 Syllabus", "📝 Notes", "❓ Questions", "💻 Labs", "🎙️ NotebookLM", "🎯 Quiz"])
    
    with s_tabs[0]:
        st.write("#### Course Syllabus Checklist")
        topics = get_syllabus_topics(subject_code)
        if not topics:
            st.info("No syllabus topics loaded yet for this subject. Sync syllabus file from Drive.")
        else:
            progress_map = get_student_progress(roll)
            completed_count = sum(1 for t in topics if progress_map.get(t['id']) == 'MASTERED')
            total_count = len(topics)
            pct = (completed_count / total_count) if total_count > 0 else 0
            
            st.markdown(f"**Overall Syllabus Progress: {completed_count}/{total_count} Topics ({int(pct*100)}%)**")
            st.progress(pct)
            
            for unit in [1, 2, 3, 4, 5]:
                unit_topics = [t for t in topics if t['unit'] == unit]
                if not unit_topics:
                    continue
                with st.expander(f"Unit {unit} Checklist", expanded=(unit == 1)):
                    for t in unit_topics:
                        is_checked = progress_map.get(t['id']) == 'MASTERED'
                        chk = st.checkbox(t['topic_text'], value=is_checked, key=f"deep_sub_chk_{t['id']}")
                        if chk != is_checked:
                            new_status = 'MASTERED' if chk else 'NOT_STARTED'
                            update_syllabus_progress(roll, t['id'], new_status)
                            st.rerun()
                            
    with s_tabs[1]:
        st.write("#### Class Notes & Reading Material")
        notes = get_notes(subject_code)
        if not notes:
            st.info("No notes processed for this subject yet. Upload study guides to Drive to index them.")
        else:
            for n in notes:
                with st.expander(f"Unit {n['unit']} Topic: {n['topic']}"):
                    st.write(n['content'])
                    
    with s_tabs[2]:
        st.write("#### Descriptive Questions Bank")
        questions = []
        conn = get_academic_conn()
        q_rows = conn.execute("SELECT * FROM question_banks WHERE subject_code=? AND q_type='DESCRIPTIVE'", (get_actual_subject_code(subject_code),)).fetchall()
        conn.close()
        questions = [dict(r) for r in q_rows]
        
        if not questions:
            st.info("No descriptive questions found in question bank. Sync question bank documents from Drive.")
        else:
            unit_filter = st.selectbox("Filter by Unit", ["All Units", "Unit 1", "Unit 2", "Unit 3", "Unit 4", "Unit 5"], key="deep_q_filter")
            filtered_qs = questions
            if unit_filter != "All Units":
                u_num = int(unit_filter.split(" ")[1])
                filtered_qs = [q for q in questions if q['unit'] == u_num]
                
            for idx, q in enumerate(filtered_qs):
                with st.expander(f"Q{idx+1}. [Unit {q['unit']}] {q['question'][:80]}..."):
                    st.markdown(f"**Question:**\\n{q['question']}")
                    st.markdown(f"**Marks:** {q['marks']} | **CO:** {q['co']} | **BTL:** {q['btl']}")
                    if q['answer_text']:
                        st.markdown(f"**Suggested Answer:**\\n{q['answer_text']}")
                    else:
                        st.info("No parsed answer notes. Copy the question to ask AI Tutor.")
                        
    with s_tabs[3]:
        st.write("#### Dynamic Lab Library")
        labs = get_lab_programs(subject_code)
        if not labs:
            st.info("No lab program scripts found for this subject. Upload code files or a ZIP to Drive under 'Lab Programs' folder.")
        else:
            selected_lab = st.selectbox("Select Lab Script", [l['file_name'] for l in labs], key="deep_lab_select")
            lab_obj = [l for l in labs if l['file_name'] == selected_lab][0]
            
            lang = "python" if selected_lab.endswith(".py") else "c" if selected_lab.endswith((".c", ".cpp")) else "text"
            st.code(lab_obj['code_content'], language=lang)
            
            c1, c2 = st.columns(2)
            c1.download_button("📥 Download Script", lab_obj['code_content'], file_name=selected_lab, use_container_width=True)
            if c2.button("📋 Copy Code to Clipboard", use_container_width=True):
                st.success("Code copy template available inside the code block's hover controls!")
                
    with s_tabs[4]:
        st.write("#### NotebookLM Studio Exporter")
        
        st.write("##### 🎙️ Generate AI Lecture briefing")
        audio_cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio_cache")
        os.makedirs(audio_cache_dir, exist_ok=True)
        
        c1, c2, c3 = st.columns(3)
        duration_sel = "5 min"
        if c1.button("📻 5 min Summary", use_container_width=True):
            duration_sel = "5 min"
            generate_tts_lecture_briefing(roll, subject_code, duration_sel, audio_cache_dir)
        if c2.button("📻 15 min Revision", use_container_width=True):
            duration_sel = "15 min"
            generate_tts_lecture_briefing(roll, subject_code, duration_sel, audio_cache_dir)
        if c3.button("📻 30 min Deep Dive", use_container_width=True):
            duration_sel = "30 min"
            generate_tts_lecture_briefing(roll, subject_code, duration_sel, audio_cache_dir)
            
        audio_file = os.path.join(audio_cache_dir, f"{roll}_{subject_code}_lecture.mp3")
        if os.path.exists(audio_file):
            with open(audio_file, "rb") as f:
                st.audio(f.read(), format="audio/mp3")
        else:
            st.info("No custom audio briefing generated yet. Select a duration option above to compile and narrate.")
            
        st.write("##### 📥 NotebookLM Custom Study Package")
        st.write("Compile a personalized study package containing course notes, descriptive questions, and spaced repetition errors. Upload it to Google NotebookLM to build audio discussions or custom tutors.")
        
        md_content = f"# NotebookLM Study Package - {friendly_name}\\n\\n"
        md_content += f"Roll Number: {roll} | Branch: {branch}\\n\\n"
        
        notes = get_notes(subject_code)
        if notes:
            md_content += "## 📝 Course Notes\\n"
            for n in notes:
                md_content += f"### Unit {n['unit']}: {n['topic']}\\n{n['content']}\\n\\n"
                
        conn = get_academic_conn()
        q_rows = conn.execute("SELECT question, answer_text, unit FROM question_banks WHERE subject_code=? AND q_type='DESCRIPTIVE'", (get_actual_subject_code(subject_code),)).fetchall()
        conn.close()
        if q_rows:
            md_content += "## ❓ Descriptive Questions & Answers\\n"
            for q in q_rows:
                ans = q[1] if q[1] else "(See AI Copilot for explanation)"
                md_content += f"### [Unit {q[2]}] Question: {q[0]}\\nSuggested Answer: {ans}\\n\\n"
                
        st.download_button("📥 Export StudyPackage.md", md_content, file_name=f"{subject_code}_NotebookLM_Pack.md", use_container_width=True)
        
    with s_tabs[5]:
        st.write("#### Subject Practice Quiz")
        render_subject_quiz_engine(roll, subject_code)


def render_subject_quiz_engine(roll, subject_code):
    actual_code = get_actual_subject_code(subject_code)
    
    q_mode = st.radio("Choose Quiz Mode", ["Practice Mode", "Exam Mode", "Revision Mode (SRS)"], horizontal=True, key=f"q_mode_{subject_code}")
    
    conn = get_academic_conn()
    if "Revision" in q_mode:
        today = datetime.date.today().isoformat()
        rows = conn.execute('''
            SELECT m.*, r.difficulty FROM review_schedule r
            JOIN mcqs m ON r.mcq_id = m.id
            WHERE r.roll_no=? AND m.subject_code=? AND (r.next_review <= ? OR r.next_review IS NULL)
        ''', (roll, actual_code, today)).fetchall()
        questions = [dict(r) for r in rows]
    else:
        rows = conn.execute("SELECT * FROM mcqs WHERE subject_code=?", (actual_code,)).fetchall()
        questions = [dict(r) for r in rows]
    conn.close()
    
    if not questions:
        st.info("No questions available for this subject in the selected mode. (Wrong answers in standard quizzes will build your Revision queue!)")
        return
        
    state_key = f"quiz_session_{subject_code}_{q_mode.replace(' ', '')}"
    if state_key not in st.session_state:
        import random
        selected_qs = list(questions)
        if len(selected_qs) > 10:
            selected_qs = random.sample(selected_qs, 10)
            
        st.session_state[state_key] = {
            "questions": selected_qs,
            "current_index": 0,
            "score": 0,
            "answers": {},
            "wrong_ids": [],
            "completed": False,
            "start_time": time.time()
        }
        
    quiz = st.session_state[state_key]
    
    if quiz["completed"]:
        duration = int(time.time() - quiz["start_time"])
        accuracy = (quiz["score"] / len(quiz["questions"]) * 100) if quiz["questions"] else 0
        
        st.balloons()
        st.markdown(f"""
        <div class="academic-card" style="text-align: center; border-left: 4px solid #00D8C6;">
            <h4 style="color: #00D8C6;">🎉 Quiz Completed!</h4>
            <p style="font-size: 1.25rem; font-weight: 700; color: #fff; margin: 10px 0;">Accuracy: {accuracy:.1f}% ({quiz['score']} / {len(quiz['questions'])})</p>
            <p style="font-size: 0.9rem; color: #cbd5e1;">Time Taken: <b>{duration} seconds</b></p>
        </div>
        """, unsafe_allow_html=True)
        
        weak_units = {}
        for q_idx in quiz["wrong_ids"]:
            q_obj = quiz["questions"][q_idx]
            u = q_obj.get("unit", 3)
            weak_units[u] = weak_units.get(u, 0) + 1
            
            if "Revision" not in q_mode:
                add_srs_review(roll, q_obj['id'], 1)
                
        if weak_units:
            st.warning("⚠️ **Weak Units Detected:**")
            for u, cnt in weak_units.items():
                st.write(f"- Unit {u}: {cnt} wrong answers. Recommend reviewing Unit {u} syllabus topics.")
                
        if st.button("🔄 Restart Quiz", key=f"restart_btn_{state_key}"):
            del st.session_state[state_key]
            st.rerun()
        return
        
    idx = quiz["current_index"]
    q_obj = quiz["questions"][idx]
    
    st.markdown(f"**Question {idx+1} of {len(quiz['questions'])}** (Unit {q_obj['unit']})")
    st.write(q_obj['question'])
    
    opts = [q_obj['option_a'], q_obj['option_b'], q_obj['option_c'], q_obj['option_d']]
    opts = [o for o in opts if o]
    ans_labels = ["A", "B", "C", "D"]
    
    if "Practice" in q_mode:
        user_select = st.radio("Select Option:", opts, key=f"radio_{state_key}_{idx}")
        sel_letter = ans_labels[opts.index(user_select)] if user_select in opts else ""
        
        if st.button("Check Answer", key=f"chk_btn_{state_key}_{idx}"):
            correct = q_obj['correct_option'].strip().upper()
            if sel_letter == correct:
                st.success("Correct! 🎉")
                quiz["score"] += 1
            else:
                st.error(f"Incorrect. Correct answer is **{correct}**.")
                if q_obj.get("explanation"):
                    st.info(f"Explanation: {q_obj['explanation']}")
                quiz["wrong_ids"].append(idx)
                
            if idx + 1 < len(quiz["questions"]):
                quiz["current_index"] += 1
            else:
                quiz["completed"] = True
            st.button("Continue", key=f"cont_btn_{state_key}_{idx}")
            
    elif "Exam" in q_mode:
        user_select = st.radio("Select Option:", opts, key=f"radio_{state_key}_{idx}")
        sel_letter = ans_labels[opts.index(user_select)] if user_select in opts else ""
        quiz["answers"][idx] = sel_letter
        
        c1, c2 = st.columns(2)
        if idx + 1 < len(quiz["questions"]):
            if c1.button("Next Question", key=f"next_btn_{state_key}_{idx}"):
                quiz["current_index"] += 1
                st.rerun()
        else:
            if c1.button("Finish Exam & Submit", key=f"finish_btn_{state_key}_{idx}"):
                for i, q in enumerate(quiz["questions"]):
                    user_ans = quiz["answers"].get(i, "")
                    correct = q['correct_option'].strip().upper()
                    if user_ans == correct:
                        quiz["score"] += 1
                    else:
                        quiz["wrong_ids"].append(i)
                quiz["completed"] = True
                st.rerun()
                
    else:
        user_select = st.radio("Select Option:", opts, key=f"radio_{state_key}_{idx}")
        sel_letter = ans_labels[opts.index(user_select)] if user_select in opts else ""
        
        if "rev_ans_state" not in st.session_state:
            st.session_state["rev_ans_state"] = None
            
        if st.button("Check Revision Answer", key=f"chk_rev_{state_key}_{idx}"):
            correct = q_obj['correct_option'].strip().upper()
            if sel_letter == correct:
                st.session_state["rev_ans_state"] = "correct"
            else:
                st.session_state["rev_ans_state"] = "incorrect"
                quiz["wrong_ids"].append(idx)
                add_srs_review(roll, q_obj['id'], 1)
                
        if st.session_state["rev_ans_state"] == "correct":
            st.success("Correct! 🎉 How easy was it to recall this?")
            c1, c2, c3 = st.columns(3)
            if c1.button("Easy (Next review far)", key="sm_easy"):
                add_srs_review(roll, q_obj['id'], 5)
                st.session_state["rev_ans_state"] = None
                if idx + 1 < len(quiz["questions"]):
                    quiz["current_index"] += 1
                else:
                    quiz["completed"] = True
                st.rerun()
            if c2.button("Good (Medium spacing)", key="sm_good"):
                add_srs_review(roll, q_obj['id'], 4)
                st.session_state["rev_ans_state"] = None
                if idx + 1 < len(quiz["questions"]):
                    quiz["current_index"] += 1
                else:
                    quiz["completed"] = True
                st.rerun()
            if c3.button("Hard (Review soon)", key="sm_hard"):
                add_srs_review(roll, q_obj['id'], 3)
                st.session_state["rev_ans_state"] = None
                if idx + 1 < len(quiz["questions"]):
                    quiz["current_index"] += 1
                else:
                    quiz["completed"] = True
                st.rerun()
        elif st.session_state["rev_ans_state"] == "incorrect":
            st.error(f"Incorrect. The correct answer is **{q_obj['correct_option'].strip().upper()}**.")
            if st.button("Retry Question / Keep in Spaced Repetition", key="sm_retry"):
                st.session_state["rev_ans_state"] = None
                if idx + 1 < len(quiz["questions"]):
                    quiz["current_index"] += 1
                else:
                    quiz["completed"] = True
                st.rerun()


def render_exam_prep_view(student):
    roll = student['roll_no']
    st.markdown("""
    <div class="academic-card-purple">
        <h3 style="margin: 0; color: #8B5CF6; font-family: 'Outfit';">⚡ Exam Prep Center</h3>
        <p style="margin: 5px 0 0 0; font-size: 0.9rem; color: #cbd5e1;">Get targeted question packs to clear exams or secure distinction scores. Dynamically compiled from college materials.</p>
    </div>
    """, unsafe_allow_html=True)
    
    subjects = get_subjects_list_all()
    if not subjects:
        st.info("No course materials indexed yet. Sync files from Drive to unlock Exam Prep Packages.")
        return
        
    selected_sub = st.selectbox("Select Subject for Exam Prep", [s['subject_code'] for s in subjects], key="exam_prep_sub_select")
    actual_code = get_actual_subject_code(selected_sub)
    
    conn = get_academic_conn()
    q_rows = conn.execute("SELECT * FROM question_banks WHERE subject_code=?", (actual_code,)).fetchall()
    questions = [dict(r) for r in q_rows]
    conn.close()
    
    if not questions:
        st.info(f"No questions loaded for subject {selected_sub}. Please sync question bank files in Drive.")
        return
        
    pkg = st.radio("Select Preparation Package", ["🎯 Pass Package (Top 10 Essential Questions)", "🏆 Distinction Package (Aim 70+ Marks)", "⏰ Last Night Revision Briefing"], horizontal=True)
    
    if "Pass Package" in pkg:
        st.write("#### 🎯 Pass Package (Highly Occurring Questions)")
        st.markdown("<p style='font-size: 0.85rem; color: #94a3b8; margin-bottom: 15px;'>These questions cover the core concepts required to pass the subject:</p>", unsafe_allow_html=True)
        display_qs = questions[:10]
        for idx, q in enumerate(display_qs):
            with st.expander(f"{idx+1}. [Unit {q['unit']}] {q['question'][:80]}..."):
                st.write(f"**Question:**\\n{q['question']}")
                if q.get("answer_text"):
                    st.write(f"**Answer:**\\n{q['answer_text']}")
                else:
                    st.info("No detailed answer text. Use the AI Copilot to generate an explanation.")
                    
    elif "Distinction Package" in pkg:
        st.write("#### 🏆 Distinction Package (Aim 70+ Marks)")
        st.markdown("<p style='font-size: 0.85rem; color: #94a3b8; margin-bottom: 15px;'>Comprehensive list of important descriptive and analytical topics:</p>", unsafe_allow_html=True)
        display_qs = questions[:25]
        for idx, q in enumerate(display_qs):
            with st.expander(f"{idx+1}. [Unit {q['unit']}] {q['question'][:80]}..."):
                st.write(f"**Question:**\\n{q['question']}")
                if q.get("answer_text"):
                    st.write(f"**Answer:**\\n{q['answer_text']}")
                else:
                    st.info("Use AI Copilot for solution.")
                    
    else:
        st.write("#### ⏰ Last Night Revision Briefing")
        st.markdown("<p style='font-size: 0.85rem; color: #94a3b8; margin-bottom: 15px;'>Ultra-condensed definitions and formulas for quick revision:</p>", unsafe_allow_html=True)
        
        conn = get_academic_conn()
        notes_rows = conn.execute("SELECT unit, topic, content FROM notes WHERE subject_code=? GROUP BY unit", (selected_sub,)).fetchall()
        conn.close()
        
        if not notes_rows:
            st.info("No quick revision notes indexed. Class notes files must be uploaded to Drive.")
        else:
            for r in notes_rows:
                st.markdown(f"""
                <div class="academic-card" style="padding: 15px; margin-bottom: 10px;">
                    <h5 style="margin: 0; color: #00D8C6;">Unit {r[0]}: {r[1]}</h5>
                    <p style="margin: 8px 0 0 0; font-size: 0.85rem; color: #cbd5e1;">{r[2][:400]}...</p>
                </div>
                """, unsafe_allow_html=True)


def render_backlog_recovery_view(student):
    roll = student['roll_no']
    branch = student['branch']
    
    st.markdown("""
    <div class="academic-card-purple">
        <h3 style="margin: 0; color: #8B5CF6; font-family: 'Outfit';">⚠️ AI Backlog Recovery Planner</h3>
        <p style="margin: 5px 0 0 0; font-size: 0.9rem; color: #cbd5e1;">Generate personalized, high-probability roadmaps to clear backlogs. Driven dynamically by your attendance and exam performance.</p>
    </div>
    """, unsafe_allow_html=True)
    
    backlogs = get_student_backlogs(roll)
    if not backlogs:
        st.success("✨ Great news! You have no recorded final exam backlogs. (Risk alerts for current courses are shown on the Dashboard).")
        return
        
    backlog_codes = [b['subject_code'] for b in backlogs]
    selected_backlog = st.selectbox("Select Backlog Subject to Plan For", backlog_codes, key="backlog_plan_select")
    
    days_left = st.slider("Days remaining until Exam", min_value=3, max_value=60, value=14, step=1)
    
    plan_duration = "7 Day Plan" if days_left <= 7 else "14 Day Plan" if days_left <= 15 else "30 Day Plan"
    
    st.markdown(f"**Recommended Plan:** `{plan_duration}` based on {days_left} days left.")
    
    if st.button("🚀 Generate Personalized Recovery Roadmap", use_container_width=True):
        with st.spinner("AI is crafting your study roadmap..."):
            api_key = get_gemini_api_key()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            
            conn = get_academic_conn()
            wrong_cnt = conn.execute("SELECT COUNT(*) FROM review_schedule r JOIN mcqs m ON r.mcq_id = m.id WHERE r.roll_no=? AND m.subject_code=?", (roll, get_actual_subject_code(selected_backlog))).fetchone()[0]
            conn.close()
            
            prompt = f"""
            You are a senior academic success coach. Design a highly focused, day-by-day {plan_duration} study plan to help this student clear their backlog in {selected_backlog}.
            
            Student Context:
            - Target Subject: {selected_backlog}
            - Days left: {days_left}
            - Repetition review errors: {wrong_cnt} wrong answers in quizzes
            
            Construct a clear, realistic day-by-day study roadmap in clean markdown. 
            Prioritize core topics, formulas, and practicing past question banks. Keep it extremely encouraging and highly structured.
            """
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            try:
                res = requests.post(url, json=payload, headers=headers, timeout=30)
                if res.status_code == 200:
                    st.markdown(res.json()["candidates"][0]["content"]["parts"][0]["text"])
                else:
                    st.error("Failed to generate plan.")
            except Exception as e:
                st.error(f"Error: {e}")


def render_ai_copilot_view(student):
    roll = student['roll_no']
    branch = student['branch']
    
    st.markdown("""
    <div class="academic-card">
        <h3 style="margin: 0; color: #00D8C6; font-family: 'Outfit';">🤖 AI Copilot (Study Assistant)</h3>
        <p style="margin: 5px 0 0 0; font-size: 0.9rem; color: #cbd5e1;">Ask conceptual questions, request code summaries, or seek math solutions. The Copilot answers using your actual college materials.</p>
    </div>
    """.replace('\n', ' '), unsafe_allow_html=True)
    
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
        
    for chat in st.session_state["chat_history"]:
        role = chat["role"]
        icon = "🧑‍🎓" if role == "user" else "🤖"
        with st.chat_message("user" if role == "user" else "assistant", avatar=icon):
            st.markdown(chat["text"])
        
    user_input = st.chat_input("Ask a question about your courses...")
    
    if user_input:
        st.session_state["chat_history"].append({"role": "user", "text": user_input})
        st.rerun()
        
    if st.session_state["chat_history"] and st.session_state["chat_history"][-1]["role"] == "user":
        q = st.session_state["chat_history"][-1]["text"]
        
        with st.spinner("AI Copilot is searching database & synthesizing..."):
            results = search_academic_resources_rag(q)
            
            context_parts = []
            for r in results[:6]:
                context_parts.append(f"Source Type: {r['type']} | Subject: {r['subject']} | Title: {r['title']}\\nContent: {r['content']}")
            context_str = "\\n\\n---\\n\\n".join(context_parts)
            
            api_key = get_gemini_api_key()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            
            system_instruction = "You are a helpful, expert VITS Engineering AI Tutor. Your goal is to explain concepts clearly using the provided local syllabus, question banks, lab codes, and notes as a primary source. Always cite which subject the question or code comes from. If the answer is not in the context, explain the concept from general engineering knowledge but mention that it was not directly found in the uploaded course materials."
            
            prompt = f"""
            Context from local question bank, syllabus, lab codes, and notes:
            {context_str if context_str else "No direct matches found in local database."}
            
            User Question: {q}
            
            Please answer the user question in detail, using clean formatting, math LaTeX notation where appropriate, and Markdown.
            """
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "systemInstruction": {"parts": [{"text": system_instruction}]}
            }
            
            try:
                res = requests.post(url, json=payload, headers=headers, timeout=25)
                if res.status_code == 200:
                    ans = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                elif res.status_code == 403 and "API_KEY_SERVICE_BLOCKED" in res.text:
                    ans = (
                        "🔒 **API Key Blocked:** The default Gemini API key is currently blocked or deactivated.\n\n"
                        "To use the AI Copilot study assistant, please configure your own Gemini API key:\n"
                        "1. Create a Gemini API key at the [Google AI Studio](https://aistudio.google.com/).\n"
                        "2. Open the file `.streamlit/secrets.toml` in the project directory.\n"
                        "3. Update the key under the `[gemini]` section:\n"
                        "   ```toml\n"
                        "   [gemini]\n"
                        "   api_key = \"YOUR_NEW_API_KEY\"\n"
                        "   ```\n"
                        "4. Save the file and restart the application."
                    )
                else:
                    ans = f"AI Tutor REST call returned error {res.status_code}: {res.text}"
            except Exception as e:
                ans = f"AI Tutor connection error: {e}"
                
            st.session_state["chat_history"].append({"role": "assistant", "text": ans})
            st.rerun()

```

---

## [database.py](file:///d:/claude demo/vits-erp-streamlit/database.py)

```python
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


import time

_QUERY_CACHE = {}

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
        return self._rows[0][idx]

    def __iter__(self):
        return self

    def __next__(self):
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row

class _SQLiteConn:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        sql_upper = sql.strip().upper()
        is_read = sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')
        
        if not is_read:
            _clear_cache()

        if is_read:
            cache_key = (sql, tuple(params) if params else ())
            now = time.time()
            if cache_key in _QUERY_CACHE:
                expiry, cached_rows = _QUERY_CACHE[cache_key]
                if now < expiry:
                    return _CachedCursor(cached_rows)

        cur = self._conn.execute(sql, params)
        
        if is_read:
            cache_key = (sql, tuple(params) if params else ())
            rows = cur.fetchall()
            _QUERY_CACHE[cache_key] = (time.time() + 300, rows)
            return _CachedCursor(rows)
            
        return cur

    def executemany(self, sql, seq):
        _clear_cache()
        return self._conn.executemany(sql, seq)

    def cursor(self):
        return _SQLiteCursorProxy(self._conn.cursor(), self)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

class _SQLiteCursorProxy:
    def __init__(self, cur, sqlite_conn):
        self._cur = cur
        self._conn = sqlite_conn

    def execute(self, sql, params=()):
        sql_upper = sql.strip().upper()
        is_read = sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')
        if not is_read:
            _clear_cache()
        self._cur.execute(sql, params)
        return self._cur

    def executemany(self, sql, seq):
        _clear_cache()
        self._cur.executemany(sql, seq)

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def __iter__(self):
        return self

    def __next__(self):
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row


def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=30000')
    return _SQLiteConn(conn)


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
            SELECT id, sgpa, failed FROM sgpa_records WHERE roll_no=? AND semester=?
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
                
                if gp == 0.0:
                    has_failed = True
                
                if credits > 0:
                    weighted_gp += gp * credits
                    total_credits += credits
            
            sgpa = round(weighted_gp / total_credits, 2) if total_credits > 0 else 0.0
            
            new_failed = 1 if has_failed else 0
            if existing:
                existing_sgpa = existing['sgpa']
                existing_failed = existing['failed']
                if abs((existing_sgpa or 0.0) - sgpa) > 0.001 or existing_failed != new_failed:
                    cursor.execute('''
                        UPDATE sgpa_records SET sgpa=?, failed=? WHERE roll_no=? AND semester=?
                    ''', (sgpa, new_failed, roll_no, sem))
            else:
                cursor.execute('''
                    INSERT INTO sgpa_records (roll_no, semester, sgpa, failed)
                    VALUES (?, ?, ?, ?)
                ''', (roll_no, sem, sgpa, new_failed))
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
                    
                    if gp == 0.0:
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


# ── Dynamic Route Overrides (PG/Supabase support on Cloud) ──
import os
import streamlit as st

def _should_use_pg():
    import sys
    if os.environ.get("SANDBOX_ACTIVE") == "true":
        return False
    # If any command-line argument contains sandbox, disable PG overrides to run locally
    for arg in sys.argv:
        if "sandbox" in str(arg).lower():
            return False
    try:
        url = st.secrets.get("database", {}).get("url", "")
        if url:
            return True
    except Exception:
        pass
    if os.environ.get("DATABASE_URL"):
        return True
    return False

if _should_use_pg():
    try:
        import database_pg
        globals().update({k: v for k, v in database_pg.__dict__.items() if not k.startswith('__')})
    except Exception as e:
        print(f"[Database Routing Error] Failed to load PostgreSQL overrides: {e}")


```

---

## [database_academic.py](file:///d:/claude demo/vits-erp-streamlit/database_academic.py)

```python
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

```

---

## [database_pg.py](file:///d:/claude demo/vits-erp-streamlit/database_pg.py)

```python
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
            _CONN_LAST_USED[id(self._conn)] = time.time()
            pool.putconn(self._conn)
        else:
            self._conn.close()
            _CONN_LAST_USED.pop(id(self._conn), None)

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
    minconn=2, maxconn=15 handles concurrent Streamlit reruns safely.
    """
    from psycopg2 import pool as pg_pool
    url = _get_pg_url()
    try:
        p = pg_pool.ThreadedConnectionPool(
            minconn=2, maxconn=15,
            dsn=url, sslmode='require', connect_timeout=15
        )
        return p
    except Exception:
        p = pg_pool.ThreadedConnectionPool(
            minconn=2, maxconn=15,
            dsn=url, connect_timeout=15
        )
        return p


_CONN_LAST_USED = {}


def get_db_connection():
    """
    Get a connection from the pool. Always call conn.close() when done —
    this returns the connection to the pool rather than closing it.
    Falls back to a direct connection if pool is exhausted.
    """
    from psycopg2 import pool as pg_pool
    pool = _get_pool()
    max_retries = 3
    for attempt in range(max_retries):
        raw = None
        try:
            raw = pool.getconn()
            if raw.closed != 0:
                raise psycopg2.OperationalError("Connection is closed locally")

            # Health-check only if idle > 10s
            now = time.time()
            last_used = _CONN_LAST_USED.get(id(raw), 0)
            if now - last_used > 10:
                with raw.cursor() as cur:
                    cur.execute("SELECT 1")
                raw.rollback()

            _CONN_LAST_USED[id(raw)] = now
            raw.autocommit = False
            conn = _PGConn(raw)
            conn._pool = pool
            return conn

        except pg_pool.PoolError:
            # Pool exhausted — create a direct (non-pooled) connection as fallback
            print("[Database Pool] Pool exhausted — using direct connection fallback")
            raw = _make_conn()
            conn = _PGConn(raw)
            conn._pool = None   # no pool → close() will truly close it
            return conn

        except (psycopg2.InterfaceError, psycopg2.OperationalError) as e:
            if raw:
                try:
                    pool.putconn(raw, close=True)
                except Exception:
                    pass
            print(f"[Database Pool] Dead connection on attempt {attempt+1}/{max_retries}: {e}")
            if attempt == max_retries - 1:
                print("[Database Pool] Recreating pool...")
                _get_pool.clear()
                pool = _get_pool()
                raw = pool.getconn()
                _CONN_LAST_USED[id(raw)] = time.time()
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
    theme_pref   TEXT DEFAULT 'dark',
    last_login   TEXT
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
            # Skip seeding on production database startup to prevent connection timeout hangs. Seeding can be done via administrative panel instead.
            print("[init_db] Student table empty. Skipping automatic CSV seeding to prevent connection hang. Seed via admin console.")
    except Exception as e:
        try: conn._conn.rollback()
        except: pass
        print(f"[init_db] Warning on checking students table: {e}")

    # Migration: reset placeholder DOBs
    try:
        conn.execute("UPDATE students SET dob='PENDING' WHERE dob='2007-01-01'")
        conn.commit()
    except Exception as e:
        try: conn._conn.rollback()
        except: pass
        print(f"[init_db] Warning on DOB reset migration: {e}")

    # Migration: ensure last_login column exists in students table
    try:
        conn.execute("ALTER TABLE students ADD COLUMN last_login TEXT")
        conn.commit()
    except Exception as e:
        try: conn._conn.rollback()
        except: pass

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
            'SELECT id, sgpa, failed FROM sgpa_records WHERE roll_no=%s AND semester=%s',
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
                if gp == 0.0:
                    has_failed = True
                if credits > 0:
                    weighted_gp   += gp * credits
                    total_credits += credits
            sgpa = round(weighted_gp / total_credits, 2) if total_credits > 0 else 0.0

            new_failed = 1 if has_failed else 0
            if existing:
                existing_sgpa = existing['sgpa']
                existing_failed = existing['failed']
                if abs((existing_sgpa or 0.0) - sgpa) > 0.001 or existing_failed != new_failed:
                    conn.execute(
                        'UPDATE sgpa_records SET sgpa=%s, failed=%s WHERE roll_no=%s AND semester=%s',
                        (sgpa, new_failed, roll_no, sem)
                    )
            else:
                conn.execute(
                    'INSERT INTO sgpa_records(roll_no,semester,sgpa,failed) VALUES(%s,%s,%s,%s)',
                    (roll_no, sem, sgpa, new_failed)
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
                    
                    if gp == 0.0:
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


```

---

## [harvester.py](file:///d:/claude demo/vits-erp-streamlit/harvester.py)

```python
"""
harvester.py — Smart portal attendance scraper.
Semester-aware. Scheduler-safe. Logs every run.
"""
import os, io, sys, logging, time
from datetime import datetime, timedelta
import pandas as pd
import requests
from database import get_db_connection, CLASSES, get_portal_yr_br

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
PORTAL_USER   = os.environ.get('PORTAL_USERNAME', '848')
PORTAL_PASS   = os.environ.get('PORTAL_PASSWORD', 'vits')

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
    payload = {'br': br, 'yr': yr, 'sc': sc,
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


def scrape_portal(start_date=None, end_date=None, section=None,
                  semester='Sem 2', dynamic_conn=None, max_retries=3):
    """Main scrape function. Returns (success, message)."""
    from database import get_config_map
    conn_cfg = dynamic_conn if dynamic_conn is not None else get_db_connection()
    cfg      = get_config_map(conn_cfg)
    if dynamic_conn is None:
        conn_cfg.close()

    fdt = start_date or cfg.get('start_date', '2026-01-27')
    tdt = end_date   or datetime.now().strftime('%Y-%m-%d')
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
            df = _fetch_df(session, sc, semester, fdt, target_date, max_retries)
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
                    ''', (roll_no, name, '2007-01-01',
                          f'{roll_no.lower()}@vits.edu', 2, branch, sc, branch))
                    student_count += 1
                elif target_date == tdt:
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

                        if target_date == tdt:
                            cursor.execute('''
                                INSERT INTO attendance(roll_no,subject,semester,hours_attended,hours_conducted)
                                VALUES(?,?,?,?,?)
                                ON CONFLICT(roll_no,subject,semester) DO UPDATE SET
                                    hours_attended=excluded.hours_attended,
                                    hours_conducted=excluded.hours_conducted
                            ''', (roll_no, sub, semester, att, cond))

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
            if target_date == tdt:
                last_df = df
        except Exception as e:
            logger.error(f'[{sc}] Failed for {target_date}: {e}')

    # Interpolate attendance gaps dynamically to populate daily records for the last 30 days
    try:
        fill_attendance_history_gaps(conn, sc, fdt, tdt)
    except Exception as fill_e:
        logger.warning(f'Failed to interpolate attendance history: {fill_e}')

    duration = round(time.time() - t_start, 2)
    status   = 'success' if success_dates else 'failed'
    now      = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        cursor.execute("UPDATE config SET value=? WHERE key='last_scraped_at'", (now,))
        cursor.execute("UPDATE config SET value=? WHERE key='start_date'",      (fdt,))
        cursor.execute("UPDATE config SET value=? WHERE key='end_date'",        (tdt,))
        cursor.execute('''
            INSERT INTO scrape_log(scraped_at,section,students,status,duration)
            VALUES(?,?,?,?,?)
        ''', (now, sc, student_count, status, duration))
    except Exception as log_e:
        logger.error(f'Failed to write scrape log: {log_e}')

    if dynamic_conn is None:
        try:
            conn.commit()
        finally:
            conn.close()

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


def bulk_scrape_all(semester='Sem 2', start_date=None, end_date=None):
    """Scrape all sections independently."""
    results = []
    for sec in CLASSES:
        ok, msg = scrape_portal(
            start_date=start_date, end_date=end_date,
            section=sec, semester=semester, dynamic_conn=None
        )
        results.append({'section': sec, 'ok': ok, 'msg': msg})
        logger.info(msg)
    return results


def start_scheduler(app):
    """Start APScheduler — only in main worker, not Flask reloader."""
    if app.debug and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        logger.info('[Scheduler] Skipping in Flask reloader process')
        return None
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
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
                continue
                
            # Discrete step-wise interpolation for gaps
            sorted_dates = sorted(existing_map.keys())
            
            if len(sorted_dates) == 1:
                att, cond = existing_map[sorted_dates[0]]
                pct = round(att / cond * 100, 2) if cond > 0 else 0.0
                for d_str in all_dates_str:
                    if d_str not in existing_map:
                        insert_data.append((d_str, roll, sub, att, cond, pct))
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
                if any(x[0] == d_str and x[1] == roll and x[2] == sub for x in insert_data):
                    continue
                    
                if d_str < first_date_str:
                    insert_data.append((d_str, roll, sub, att_f, cond_f, pct_f))
                elif d_str > last_date_str:
                    insert_data.append((d_str, roll, sub, att_l, cond_l, pct_l))
                
    if insert_data:
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

```

---

## [migrate_sqlite_to_pg.py](file:///d:/claude demo/vits-erp-streamlit/migrate_sqlite_to_pg.py)

```python
"""
migrate_sqlite_to_pg.py
Run this ONCE locally to copy your SQLite data to Supabase PostgreSQL.
Safe to run multiple times (drops and recreates tables).
"""

import sqlite3
import os
import sys

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    os.system(f"{sys.executable} -m pip install psycopg2-binary")
    import psycopg2
    import psycopg2.extras

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "vits_erp.db")


def get_sqlite():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_pg():
    return psycopg2.connect(
        host='aws-1-ap-south-1.pooler.supabase.com',
        port=5432,
        dbname='postgres',
        user='postgres.apifahyalgvjswlspfxt',
        password='Vits2026erp',
        sslmode='require',
        connect_timeout=30
    )


# Drop all tables first so we can recreate with correct constraints
DROP_SQL = """
DROP TABLE IF EXISTS attendance_history CASCADE;
DROP TABLE IF EXISTS scrape_log CASCADE;
DROP TABLE IF EXISTS timetable CASCADE;
DROP TABLE IF EXISTS sgpa_records CASCADE;
DROP TABLE IF EXISTS marks CASCADE;
DROP TABLE IF EXISTS attendance CASCADE;
DROP TABLE IF EXISTS subjects CASCADE;
DROP TABLE IF EXISTS students CASCADE;
DROP TABLE IF EXISTS config CASCADE;
"""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    roll_no TEXT PRIMARY KEY, name TEXT, dob TEXT DEFAULT 'PENDING',
    email TEXT, semester INTEGER DEFAULT 2, department TEXT,
    section TEXT, branch TEXT, phone TEXT, parent_phone TEXT,
    theme_pref TEXT DEFAULT 'dark'
);
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY, value TEXT
);
CREATE TABLE IF NOT EXISTS subjects (
    id SERIAL PRIMARY KEY, subject_code TEXT NOT NULL,
    subject_name TEXT, semester TEXT, section TEXT,
    UNIQUE(subject_code, semester, section)
);
CREATE TABLE IF NOT EXISTS attendance (
    id SERIAL PRIMARY KEY, roll_no TEXT, subject TEXT, semester TEXT,
    hours_attended INTEGER DEFAULT 0, hours_conducted INTEGER DEFAULT 0,
    UNIQUE(roll_no, subject, semester)
);
CREATE TABLE IF NOT EXISTS marks (
    id SERIAL PRIMARY KEY, roll_no TEXT, subject TEXT, semester TEXT,
    exam_type TEXT, score REAL, grade_point REAL,
    UNIQUE(roll_no, subject, semester, exam_type)
);
CREATE TABLE IF NOT EXISTS sgpa_records (
    id SERIAL PRIMARY KEY, roll_no TEXT, semester TEXT,
    sgpa REAL, failed INTEGER DEFAULT 0,
    UNIQUE(roll_no, semester)
);
CREATE TABLE IF NOT EXISTS timetable (
    id SERIAL PRIMARY KEY, section TEXT, day TEXT,
    period INTEGER, subject TEXT,
    UNIQUE(section, day, period)
);
CREATE TABLE IF NOT EXISTS scrape_log (
    id SERIAL PRIMARY KEY, scraped_at TEXT, section TEXT,
    students INTEGER DEFAULT 0, status TEXT, duration REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS attendance_history (
    id SERIAL PRIMARY KEY,
    snapshot_date TEXT NOT NULL DEFAULT (CURRENT_DATE::TEXT),
    roll_no TEXT NOT NULL, subject_code TEXT NOT NULL,
    running_attended INTEGER DEFAULT 0,
    running_conducted INTEGER DEFAULT 0,
    percentage REAL DEFAULT 0,
    UNIQUE(roll_no, subject_code, snapshot_date)
);
"""

# Table configs: (table_name, columns_to_select, conflict_columns_for_upsert)
TABLES = [
    ("config",
     ["key", "value"],
     ["key"]),
    ("students",
     ["roll_no","name","dob","email","semester","department","section","branch","phone","parent_phone","theme_pref"],
     ["roll_no"]),
    ("subjects",
     ["subject_code","subject_name","semester","section"],
     ["subject_code","semester","section"]),
    ("attendance",
     ["roll_no","subject","semester","hours_attended","hours_conducted"],
     ["roll_no","subject","semester"]),
    ("marks",
     ["roll_no","subject","semester","exam_type","score","grade_point"],
     ["roll_no","subject","semester","exam_type"]),
    ("sgpa_records",
     ["roll_no","semester","sgpa","failed"],
     ["roll_no","semester"]),
    ("timetable",
     ["section","day","period","subject"],
     ["section","day","period"]),
    ("scrape_log",
     ["scraped_at","section","students","status","duration"],
     None),  # No unique constraint - just insert
    ("attendance_history",
     ["snapshot_date","roll_no","subject_code","running_attended","running_conducted","percentage"],
     ["roll_no","subject_code","snapshot_date"]),
]


def migrate():
    print(f"[*] SQLite : {SQLITE_PATH}")
    print(f"[*] Target : Supabase PostgreSQL")

    if not os.path.exists(SQLITE_PATH):
        print("[ERROR] SQLite file not found!")
        sys.exit(1)

    sl  = get_sqlite()
    pg  = get_pg()
    pgc = pg.cursor()

    # Step 1: Drop all tables
    print("\n[*] Dropping old tables...")
    pgc.execute(DROP_SQL)
    pg.commit()
    print("[OK] Tables dropped")

    # Step 2: Create tables with correct constraints
    print("[*] Creating schema with correct constraints...")
    for stmt in SCHEMA_SQL.strip().split(';'):
        stmt = stmt.strip()
        if stmt:
            pgc.execute(stmt)
    pg.commit()
    print("[OK] Schema created")

    # Step 3: Migrate data
    print("\n[*] Migrating data...")
    total_rows = 0

    for table, cols, conflict_cols in TABLES:
        try:
            rows = sl.execute(f"SELECT {', '.join(cols)} FROM {table}").fetchall()
        except Exception as e:
            print(f"    [SKIP] {table}: {e}")
            continue

        if not rows:
            print(f"    [SKIP] {table}: empty")
            continue

        batch = [tuple(r[c] for c in cols) for r in rows]
        placeholders = ', '.join(['%s'] * len(cols))
        col_list = ', '.join(cols)

        if conflict_cols:
            update_cols = [c for c in cols if c not in conflict_cols]
            if update_cols:
                upsert = f"""
                    INSERT INTO {table} ({col_list}) VALUES ({placeholders})
                    ON CONFLICT ({', '.join(conflict_cols)}) DO UPDATE SET
                    {', '.join(f"{c}=EXCLUDED.{c}" for c in update_cols)}
                """
            else:
                upsert = f"""
                    INSERT INTO {table} ({col_list}) VALUES ({placeholders})
                    ON CONFLICT ({', '.join(conflict_cols)}) DO NOTHING
                """
        else:
            upsert = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

        try:
            psycopg2.extras.execute_batch(pgc, upsert, batch, page_size=200)
            pg.commit()
            print(f"    [OK] {table}: {len(batch)} rows")
            total_rows += len(batch)
        except Exception as e:
            pg.rollback()
            print(f"    [ERROR] {table}: {e}")

    pg.close()
    sl.close()
    print(f"\n[DONE] Migration complete! {total_rows} total rows in Supabase.")
    print("       Next: push to GitHub -> deploy on Streamlit Cloud.")


if __name__ == "__main__":
    migrate()

```

---

## [pdf_generator.py](file:///d:/claude demo/vits-erp-streamlit/pdf_generator.py)

```python
"""pdf_generator.py — ReportLab PDF report card"""
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable)
from reportlab.lib.enums import TA_CENTER

BRAND_BLUE = colors.HexColor('#00D8C6')
BRAND_DARK = colors.HexColor('#111111')
BRAND_GRAY = colors.HexColor('#6B7280')
LIGHT_BG   = colors.HexColor('#f0fdfa')
SUCCESS    = colors.HexColor('#10B981')
WARNING    = colors.HexColor('#F59E0B')
DANGER     = colors.HexColor('#EF4444')
PURPLE     = colors.HexColor('#8B5CF6')


def _att_color(pct):
    if pct >= 75: return SUCCESS
    if pct >= 65: return WARNING
    return DANGER


def generate_report_pdf(student, attendance_rows, marks_by_type, sgpa, cgpa, semester='Sem 2', attendance_semester=None):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    story  = []

    title = ParagraphStyle('T', parent=styles['Normal'], fontSize=20,
        textColor=BRAND_BLUE, alignment=TA_CENTER,
        fontName='Helvetica-Bold', spaceAfter=4)
    sub = ParagraphStyle('S', parent=styles['Normal'], fontSize=10,
        textColor=BRAND_GRAY, alignment=TA_CENTER, spaceAfter=2)
    section = ParagraphStyle('Sec', parent=styles['Normal'], fontSize=12,
        textColor=BRAND_DARK, fontName='Helvetica-Bold',
        spaceBefore=12, spaceAfter=6)

    story.append(Paragraph('VITS Academic ERP', title))
    story.append(Paragraph('Vignan Institute of Technology and Science — Code: 891', sub))
    story.append(HRFlowable(width='100%', thickness=1, color=BRAND_BLUE, spaceAfter=10))

    info_data = [
        ['Name',     student.get('name','-'),    'Roll No', student.get('roll_no','-')],
        ['Section',  student.get('section','-'), 'Branch',  student.get('branch','-')],
        ['Semester', semester,                   '',        ''],
    ]
    info_t = Table(info_data, colWidths=[3*cm, 7*cm, 3*cm, 5*cm])
    info_t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (0,0), (0,-1),  'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1),  'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (0,-1), BRAND_GRAY),
        ('TEXTCOLOR', (2,0), (2,-1), BRAND_GRAY),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [LIGHT_BG, colors.white]),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#e2e8f0')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('SPAN', (1,2), (3,2)),
    ]))
    story.append(info_t)
    story.append(Spacer(1, 12))

    # Attendance
    att_sem_label = attendance_semester if attendance_semester else semester
    story.append(Paragraph(f'Attendance Summary ({att_sem_label})', section))
    att_data = [['Subject','Conducted','Attended','%','Status']]
    tc = ta = 0
    for r in attendance_rows:
        c = r['hours_conducted'] or 0
        a = r['hours_attended']  or 0
        tc += c
        ta += a
        pct = round(a/c*100, 1) if c > 0 else 0.0
        status = 'Good' if pct >= 75 else 'Condonation' if pct >= 65 else 'Debarred'
        att_data.append([r['subject'], str(c), str(a), f'{pct}%', status])
    overall = round(ta/tc*100, 1) if tc > 0 else 0.0
    att_data.append(['OVERALL', str(tc), str(ta), f'{overall}%', ''])

    att_t = Table(att_data, colWidths=[6*cm, 2.5*cm, 2.5*cm, 2*cm, 4*cm])
    att_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BRAND_BLUE),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 9),
        ('ALIGN',      (1,0), (-1,-1), 'CENTER'),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, LIGHT_BG]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e2e8f0')),
        ('FONTNAME',   (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('GRID',       (0,0), (-1,-1), 0.3, colors.HexColor('#cbd5e1')),
        ('PADDING',    (0,0), (-1,-1), 5),
    ])
    for i, row in enumerate(att_data[1:-1], start=1):
        try:
            pv = float(row[3].replace('%', ''))
            col = _att_color(pv)
            att_style.add('TEXTCOLOR', (3,i), (3,i), col)
            att_style.add('TEXTCOLOR', (4,i), (4,i), col)
        except Exception:
            pass
    att_t.setStyle(att_style)
    story.append(att_t)
    story.append(Spacer(1, 12))

    # Marks
    from database import SUBJECT_CREDITS
    final_exam_type = f"{semester} Final Examinations"
    for et in ['Mid 1', 'Mid 2', 'Lab Internals', final_exam_type]:
        rows = marks_by_type.get(et, [])
        if not rows:
            continue
        story.append(Paragraph(et, section))
        mdata = [['Subject','Score','Grade','GP','Credits']]
        for r in rows:
            score   = r.get('score')
            gp      = r.get('grade_point') or 0.0
            grade   = r.get('grade', '-')
            credits = SUBJECT_CREDITS.get(r['subject'], 0.0)
            mdata.append([r['subject'],
                         str(score) if score is not None else 'Ab',
                         grade, str(gp), str(credits)])
        mt = Table(mdata, colWidths=[6*cm, 2.5*cm, 2.5*cm, 2*cm, 4*cm])
        mt.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), PURPLE),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 9),
            ('ALIGN',      (1,0), (-1,-1), 'CENTER'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT_BG]),
            ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cbd5e1')),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(mt)
        story.append(Spacer(1, 8))

    # SGPA / CGPA
    story.append(HRFlowable(width='100%', thickness=1, color=BRAND_BLUE, spaceBefore=8))
    # Check if student has failed semesters
    from database import get_db_connection
    conn = get_db_connection()
    try:
        failed_row = conn.execute(
            'SELECT failed FROM sgpa_records WHERE roll_no=? AND semester=?',
            (student.get('roll_no'), semester)
        ).fetchone()
        has_failed_sem = conn.execute(
            'SELECT COUNT(*) FROM sgpa_records WHERE roll_no=? AND failed=1',
            (student.get('roll_no'),)
        ).fetchone()[0] > 0
    except Exception:
        failed_row = None
        has_failed_sem = False
    finally:
        conn.close()
        
    is_failed_sem = failed_row['failed'] if failed_row else False
    sgpa_str = "Pending" if is_failed_sem else (f"{sgpa:.2f}" if sgpa > 0 else "-")
    cgpa_str = "Pending" if has_failed_sem else (f"{cgpa:.2f}" if cgpa > 0 else "-")
    gpa_data = [['SGPA', sgpa_str, 'CGPA', cgpa_str]]
    gpa_t = Table(gpa_data, colWidths=[3*cm, 5*cm, 3*cm, 5*cm])
    gpa_t.setStyle(TableStyle([
        ('FONTNAME',  (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE',  (0,0), (-1,-1), 11),
        ('TEXTCOLOR', (0,0), (0,0), BRAND_GRAY),
        ('TEXTCOLOR', (1,0), (1,0), PURPLE),
        ('TEXTCOLOR', (2,0), (2,0), BRAND_GRAY),
        ('TEXTCOLOR', (3,0), (3,0), PURPLE),
        ('ALIGN',     (0,0), (-1,-1), 'CENTER'),
        ('PADDING',   (0,0), (-1,-1), 8),
    ]))
    story.append(gpa_t)
    story.append(Spacer(1, 16))
    story.append(Paragraph('Generated by VITS Academic ERP',
        ParagraphStyle('F', parent=styles['Normal'],
            fontSize=8, textColor=BRAND_GRAY, alignment=TA_CENTER)))

    doc.build(story)
    buf.seek(0)
    return buf

```

---

## [requirements.txt](file:///d:/claude demo/vits-erp-streamlit/requirements.txt)

```text
streamlit>=1.39.0
pandas>=2.2.2
plotly>=5.24.1
requests>=2.32.3
beautifulsoup4>=4.12.3
lxml>=5.3.0
reportlab>=4.2.5
psycopg2-binary>=2.9.9
# force reboot container to clear module cache v7

```

---

## [streamlit_app.py](file:///d:/claude demo/vits-erp-streamlit/streamlit_app.py)

```python
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
    .kpi-grid {
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
    }
}

@media (max-width: 768px) {
    /* Reduce page side padding on mobile to maximize viewable area */
    .block-container {
        padding: 1.5rem 1rem !important;
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
    # ── suppress h1 anchor icons globally on this page ────────
    st.markdown("""
    <style>
    h1 a, h2 a, h3 a { display: none !important; }
    .login-card {
        background: linear-gradient(135deg, rgba(20,28,48,0.95) 0%, rgba(12,18,36,0.98) 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 20px;
        padding: 36px 32px 28px 32px;
        max-width: 480px;
        margin: 0 auto;
    }
    </style>
    """, unsafe_allow_html=True)

    logo_path   = os.path.join(os.path.dirname(__file__), 'vits_logo.png')
    logo_base64 = get_image_base64(logo_path)
    logo_html   = f'<img src="data:image/png;base64,{logo_base64}" width="80" style="margin-bottom:10px;filter:drop-shadow(0 4px 12px rgba(0,216,198,0.3));"/>' if logo_base64 else '🎓'

    st.markdown(f"""
    <div style="text-align:center; padding: 40px 0 24px 0;">
        {logo_html}
        <div style="color:#00D8C6; font-family:'Outfit',sans-serif; font-size:2.2rem;
                    font-weight:800; margin:8px 0 4px 0;
                    text-shadow:0 0 30px rgba(0,216,198,0.3);">
            VITS Student Academic Dashboard
        </div>
        <div style="color:#94a3b8; font-family:'Inter',sans-serif; font-size:1rem;
                    letter-spacing:0.5px;">
            Vignan Institute of Technology and Science
        </div>
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
                    "* **Returning Students:** Use your configured **Date of Birth** as the password (format: **`YYYY-MM-DD`** or **`DD-MM-YYYY`**, e.g., `2007-12-01` or `01-12-2007`)."
                )
                roll = st.text_input("Roll Number", placeholder="e.g. 25891A04C9")
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
        c_val = SUBJECT_CREDITS.get(sub, 3.0)
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
    st.markdown("## 📊 Academic Results")
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

```

---

## [telegram_bot.py](file:///d:/claude demo/vits-erp-streamlit/telegram_bot.py)

```python
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import sqlite3
import os
import toml
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VITS_ERP_Bot")

# Load configuration and secrets
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SECRETS_PATH = os.path.join(BASE_DIR, ".streamlit", "secrets.toml")

# Read token
token = ""
if os.path.exists(SECRETS_PATH):
    try:
        secrets = toml.load(SECRETS_PATH)
        token = secrets.get("telegram", {}).get("bot_token", "")
    except Exception as e:
        logger.error(f"Error loading secrets: {e}")

# If token is empty/placeholder, log warning
if not token or token == "YOUR_TELEGRAM_BOT_TOKEN":
    logger.warning("No valid Telegram bot token found in .streamlit/secrets.toml. "
                   "Please update secrets.toml with your token to start the bot.")
    # Initialize with dummy token to avoid startup crash if user hasn't set it yet
    token = "DUMMY_TOKEN_PLEASE_REPLACE"

bot = telebot.TeleBot(token)

# Setup telegram chats table for persistence
def init_bot_db():
    try:
        from database import get_db_connection
        conn = get_db_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS telegram_chats (
                chat_id INTEGER PRIMARY KEY,
                roll_no TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error initializing Telegram chat table: {e}")

# Database helper functions
def get_student_by_roll(roll_no):
    from database import get_db_connection
    conn = get_db_connection()
    student = conn.execute("""
        SELECT name, department, section, semester, branch FROM students WHERE roll_no=?
    """, (roll_no,)).fetchone()
    conn.close()
    return student

def get_chat_roll(chat_id):
    from database import get_db_connection
    conn = get_db_connection()
    row = conn.execute("SELECT roll_no FROM telegram_chats WHERE chat_id=?", (chat_id,)).fetchone()
    conn.close()
    return row['roll_no'] if row else None

def save_chat_roll(chat_id, roll_no):
    from database import get_db_connection
    conn = get_db_connection()
    conn.execute("INSERT OR REPLACE INTO telegram_chats (chat_id, roll_no) VALUES (?, ?)", (chat_id, roll_no))
    conn.commit()
    conn.close()

def delete_chat_roll(chat_id):
    from database import get_db_connection
    conn = get_db_connection()
    conn.execute("DELETE FROM telegram_chats WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()

# KPI and Calculations
def calculate_skips(attended, conducted):
    # Overall attendance target thresholds
    if conducted == 0:
        return 0, 0
        
    pct = (attended / conducted) * 100
    
    # How many classes can be missed to stay above 75%
    if pct >= 75:
        can_miss = 0
        temp_att = attended
        temp_cond = conducted
        while True:
            temp_cond += 1
            if (temp_att / temp_cond) * 100 >= 75:
                can_miss += 1
            else:
                break
        return can_miss, 0
    # How many classes must be attended continuously to reach 75%
    else:
        needed = 0
        temp_att = attended
        temp_cond = conducted
        while (temp_att / temp_cond) * 100 < 75:
            temp_att += 1
            temp_cond += 1
            needed += 1
        return 0, needed

# Menus and Keyboards
def get_main_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("📊 Quick Summary"), KeyboardButton("📚 Subject Details"))
    markup.row(KeyboardButton("🔮 Skip Predictor"), KeyboardButton("👤 My Profile"))
    markup.row(KeyboardButton("🔄 Change Roll Number"))
    return markup

def get_stats_inline_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📊 Summary", callback_data="show_summary"),
        InlineKeyboardButton("📚 Subjects", callback_data="show_subjects")
    )
    markup.row(
        InlineKeyboardButton("🔮 Skip Projections", callback_data="show_predictor"),
        InlineKeyboardButton("🎓 CGPA/Grades", callback_data="show_cgpa")
    )
    return markup

# Bot command handlers
@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    chat_id = message.chat.id
    roll_no = get_chat_roll(chat_id)
    
    welcome_text = (
        "👋 **Welcome to the VITS Student ERP Assistant Bot!**\n\n"
        "This bot provides *live, up-to-date* query access to student attendance metrics and academic statistics.\n\n"
    )
    
    if roll_no:
        student = get_student_by_roll(roll_no)
        if student:
            welcome_text += (
                f"Logged in as: **{student['name']}** ({roll_no})\n"
                f"Class: **{student['department']} - {student['section']}**\n\n"
                "Use the menu below to query your stats instantly."
            )
            bot.send_message(chat_id, welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
            return
            
    welcome_text += "Please send your **Roll Number** (e.g. `25891A04C9` or `24891A0465`) to get started."
    # Remove keyboard if not logged in
    bot.send_message(chat_id, welcome_text, parse_mode="Markdown", reply_markup=telebot.types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda msg: msg.text == "📊 Quick Summary")
def handler_summary(message):
    show_summary_view(message.chat.id, message.message_id, edit=False)

@bot.message_handler(func=lambda msg: msg.text == "📚 Subject Details")
def handler_subjects(message):
    show_subjects_view(message.chat.id, message.message_id, edit=False)

@bot.message_handler(func=lambda msg: msg.text == "🔮 Skip Predictor")
def handler_predictor(message):
    show_predictor_view(message.chat.id, message.message_id, edit=False)

@bot.message_handler(func=lambda msg: msg.text == "👤 My Profile")
def handler_profile(message):
    show_profile_view(message.chat.id, message.message_id, edit=False)

@bot.message_handler(func=lambda msg: msg.text == "🔄 Change Roll Number")
def handler_change_roll(message):
    chat_id = message.chat.id
    delete_chat_roll(chat_id)
    bot.send_message(
        chat_id, 
        "🔄 Roll number removed. Please type your new **Roll Number** to register.", 
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )

# Roll Number Ingestion
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip().upper()
    
    # Check if text looks like a roll number
    if len(text) >= 8 and any(char.isdigit() for char in text):
        student = get_student_by_roll(text)
        if student:
            save_chat_roll(chat_id, text)
            bot.send_message(
                chat_id,
                f"✅ **Registration Successful!**\n\n"
                f"Student: **{student['name']}**\n"
                f"Branch: **{student['branch']}** | Section: **{student['section']}**\n\n"
                "You can now query your attendance summary below.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            # Show summary automatically
            show_summary_view(chat_id, None, edit=False)
        else:
            bot.send_message(chat_id, "❌ Roll number not found in database. Please check and try again.")
    else:
        bot.send_message(chat_id, "ℹ️ Please select a menu option or reply with a valid Roll Number.")

# Inline Button Callback Handler
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    if call.data == "show_summary":
        show_summary_view(chat_id, message_id, edit=True)
    elif call.data == "show_subjects":
        show_subjects_view(chat_id, message_id, edit=True)
    elif call.data == "show_predictor":
        show_predictor_view(chat_id, message_id, edit=True)
    elif call.data == "show_cgpa":
        show_cgpa_view(chat_id, message_id, edit=True)
        
    bot.answer_callback_query(call.id)

# ─── Data Views ───

def show_summary_view(chat_id, message_id, edit=False):
    roll_no = get_chat_roll(chat_id)
    if not roll_no:
        bot.send_message(chat_id, "❌ Please enter your Roll Number first.")
        return
        
    student = get_student_by_roll(roll_no)
    if not student:
        return
        
    from database import get_db_connection, compute_cgpa
    conn = get_db_connection()
    
    # Query Attendance Summary
    att_rows = conn.execute("""
        SELECT hours_attended, hours_conducted FROM attendance WHERE roll_no=? AND semester='Sem 2'
    """, (roll_no,)).fetchall()
    
    total_att = sum(r['hours_attended'] or 0 for r in att_rows)
    total_cond = sum(r['hours_conducted'] or 0 for r in att_rows)
    overall = round((total_att / total_cond * 100), 1) if total_cond else 0.0
    
    cgpa = compute_cgpa(roll_no, conn)
    
    conn.close()
    
    # Format Text
    status_icon = "🟢" if overall >= 75 else ("🟡" if overall >= 65 else "🔴")
    status_text = "Safe Zone" if overall >= 75 else ("Risk Zone (Need Condonation)" if overall >= 65 else "Debarred Zone")
    
    msg_text = (
        f"📊 **Attendance & Statistics Summary**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Student:* {student['name']}\n"
        f"🆔 *Roll No:* `{roll_no}`\n"
        f"🏫 *Class:* {student['department']} - {student['section']}\n"
        f"🎓 *Active Sem:* {student['semester']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📈 *Overall Attendance:* **{overall}%**\n"
        f"⏱️ *Hours:* {total_att} attended / {total_cond} conducted\n"
        f"🚨 *Status:* {status_icon} **{status_text}**\n\n"
        f"⭐️ *CGPA:* **{f'{cgpa:.2f}' if cgpa > 0 else 'Pending/Fail'}**\n"
        f"🕒 *Query Time:* {logging.Formatter().formatTime(logging.LogRecord('','','','','','',''), '%H:%M:%S')}\n"
    )
    
    send_or_edit(chat_id, message_id, msg_text, get_stats_inline_keyboard(), edit)

def show_subjects_view(chat_id, message_id, edit=False):
    roll_no = get_chat_roll(chat_id)
    if not roll_no: return
    
    student = get_student_by_roll(roll_no)
    if not student: return
    
    from database import get_db_connection
    conn = get_db_connection()
    att_rows = conn.execute("""
        SELECT subject, hours_attended, hours_conducted FROM attendance WHERE roll_no=? AND semester='Sem 2'
    """, (roll_no,)).fetchall()
    conn.close()
    
    msg_text = (
        f"📚 **Subject-wise Attendance Details**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Roll No: `{roll_no}`\n"
        f"Semester: Sem 2\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    if not att_rows:
        msg_text += "_No attendance data logged for current subjects._"
    else:
        for r in sorted(att_rows, key=lambda x: (x['hours_attended']/(x['hours_conducted'] or 1)), reverse=False):
            sub = r['subject']
            att = r['hours_attended'] or 0
            cond = r['hours_conducted'] or 0
            pct = round((att / cond * 100), 1) if cond else 0.0
            
            indicator = "🟢" if pct >= 75 else ("🟡" if pct >= 65 else "🔴")
            # Truncate subject name
            short_sub = sub[:22] + "..." if len(sub) > 22 else sub
            
            msg_text += f"{indicator} **{short_sub}**\n"
            msg_text += f"    └─ *{pct}%*  ({att}/{cond} hrs conducted)\n\n"
            
    send_or_edit(chat_id, message_id, msg_text, get_stats_inline_keyboard(), edit)

def show_predictor_view(chat_id, message_id, edit=False):
    roll_no = get_chat_roll(chat_id)
    if not roll_no: return
    
    from database import get_db_connection
    conn = get_db_connection()
    att_rows = conn.execute("""
        SELECT hours_attended, hours_conducted FROM attendance WHERE roll_no=? AND semester='Sem 2'
    """, (roll_no,)).fetchall()
    conn.close()
    
    total_att = sum(r['hours_attended'] or 0 for r in att_rows)
    total_cond = sum(r['hours_conducted'] or 0 for r in att_rows)
    overall = round((total_att / total_cond * 100), 1) if total_cond else 0.0
    
    msg_text = (
        f"🔮 **Attendance Skip Predictor Projections**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Current overall attendance: **{overall}%** ({total_att}/{total_cond} hrs)\n"
        f"Target Threshold: **75.0%**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    if total_cond == 0:
        msg_text += "_No conducting data present._"
    else:
        can_miss, need = calculate_skips(total_att, total_cond)
        
        # Estimate daily averages (usually 7 periods a day)
        avg_classes = 7.0
        
        if overall >= 75:
            days = round(can_miss / avg_classes, 1)
            msg_text += (
                f"🟢 **Safe Zone Analysis:**\n"
                f"• You can miss **{can_miss} hours** of classes continuously without falling below the 75% target threshold.\n"
                f"• This is equivalent to approximately **{days} days** of absence.\n"
            )
        else:
            days = round(need / avg_classes, 1)
            msg_text += (
                f"🔴 **Risk/Debarred Zone Analysis:**\n"
                f"• You need to attend **{need} consecutive hours** of classes without skipping to recover your attendance to 75.0%.\n"
                f"• This is equivalent to approximately **{days} days** of full attendance.\n"
            )
            
    send_or_edit(chat_id, message_id, msg_text, get_stats_inline_keyboard(), edit)

def show_cgpa_view(chat_id, message_id, edit=False):
    roll_no = get_chat_roll(chat_id)
    if not roll_no: return
    
    from database import get_db_connection
    conn = get_db_connection()
    sgpa_rows = conn.execute("""
        SELECT semester, sgpa, failed FROM sgpa_records WHERE roll_no=? ORDER BY semester
    """, (roll_no,)).fetchall()
    
    backlogs = conn.execute("""
        SELECT subject, score, grade_point, exam_type FROM marks
        WHERE roll_no=? AND grade_point=0.0 AND exam_type LIKE '%Final Examinations'
    """, (roll_no,)).fetchall()
    
    conn.close()
    
    msg_text = (
        f"🎓 **Academic Grades & CGPA Record**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Roll No: `{roll_no}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    msg_text += "*Semester Performance:*\n"
    if not sgpa_rows:
        msg_text += "• _No SGPA details posted yet._\n\n"
    else:
        for r in sgpa_rows:
            sem = r['semester']
            gpa = r['sgpa'] or 0.0
            status = "🔴 FAIL" if r['failed'] else "🟢 PASS"
            msg_text += f"• **{sem}:** GPA: `{gpa:.2f}` ({status})\n"
        msg_text += "\n"
        
    msg_text += "*Active Backlogs Summary:*\n"
    if not backlogs:
        msg_text += "• ✅ **Zero active backlogs! All subjects passed.**\n"
    else:
        msg_text += f"• ⚠️ **{len(backlogs)} active backlog(s) found:**\n"
        for b in backlogs:
            msg_text += f"  └─ {b['subject']} (GP: {b['grade_point']})\n"
            
    send_or_edit(chat_id, message_id, msg_text, get_stats_inline_keyboard(), edit)

OFFLINE_MODE = False

def send_or_edit(chat_id, message_id, text, keyboard, edit=False):
    if OFFLINE_MODE:
        # Clean markdown formatting slightly for clean terminal printout
        clean_text = text.replace("**", "").replace("*", "").replace("`", "'")
        print("\n" + "="*40)
        print(clean_text)
        print("="*40)
        return
        
    try:
        if edit and message_id:
            bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=keyboard)
        else:
            bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=keyboard)

def run_offline_simulator():
    global OFFLINE_MODE
    OFFLINE_MODE = True
    
    print("\n" + "="*55)
    print("  VITS ERP BOT - OFFLINE LOCAL TERMINAL SIMULATOR")
    print("="*55)
    print("[Offline Mode: Running local test with live vits_erp.db data]")
    print("[No internet connection or Telegram token required]\n")
    
    chat_id = 99999  # Mock chat ID for local simulation
    
    # Show welcome prompt
    roll = get_chat_roll(chat_id)
    print("Bot: 👋 Welcome to the VITS Student ERP Assistant!")
    if roll:
        student = get_student_by_roll(roll)
        if student:
            print(f"     Registered as: {student['name']} ({roll})")
            print(f"     Class: {student['department']} - {student['section']}")
    else:
        print("     Please reply with a Roll Number to register and query attendance.")
        
    while True:
        roll = get_chat_roll(chat_id)
        if roll:
            print("\n" + "-"*40)
            print("📊 Menu Options:")
            print(" [1] Quick Summary")
            print(" [2] Subject Details")
            print(" [3] Skip Predictor")
            print(" [4] CGPA & Grades")
            print(" [5] Logout / Change Roll Number")
            print(" [0] Exit Simulator")
            try:
                choice = input(f"\nSelect option for {roll}: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nExiting simulator.")
                break
        else:
            try:
                choice = input("\nEnter Roll Number (or '0' to exit): ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nExiting simulator.")
                break
                
        if not choice:
            continue
            
        if choice == '0':
            print("Exiting simulator.")
            break
            
        if not roll:
            # Attempt to register
            roll_upper = choice.upper()
            student = get_student_by_roll(roll_upper)
            if student:
                save_chat_roll(chat_id, roll_upper)
                print(f"\nBot: ✅ Registration Successful!")
                print(f"     Student: {student['name']}")
                print(f"     Section: {student['section']}")
                show_summary_view(chat_id, None, edit=False)
            else:
                print("\nBot: ❌ Roll number not found in database. Please check and try again.")
        else:
            if choice == '1':
                show_summary_view(chat_id, None, edit=False)
            elif choice == '2':
                show_subjects_view(chat_id, None, edit=False)
            elif choice == '3':
                show_predictor_view(chat_id, None, edit=False)
            elif choice == '4':
                show_cgpa_view(chat_id, None, edit=False)
            elif choice == '5':
                delete_chat_roll(chat_id)
                print("\nBot: 🔄 Roll number removed. Register again with another Roll Number.")
            elif len(choice) >= 8 and any(c.isdigit() for c in choice):
                # Allow switching directly
                roll_upper = choice.upper()
                student = get_student_by_roll(roll_upper)
                if student:
                    save_chat_roll(chat_id, roll_upper)
                    print(f"\nBot: ✅ Switched Registration!")
                    print(f"     Student: {student['name']}")
                    show_summary_view(chat_id, None, edit=False)
                else:
                    print("\nBot: ❌ Roll number not found.")
            else:
                print("\nBot: ℹ️ Invalid menu choice. Please select 1-5 or 0.")

if __name__ == "__main__":
    init_bot_db()
    
    # Check if we should run in offline simulator mode
    is_dummy_token = (
        not token or 
        token == "YOUR_TELEGRAM_BOT_TOKEN" or 
        token == "DUMMY_TOKEN_PLEASE_REPLACE" or 
        "DUMMY" in token
    )
    
    if is_dummy_token:
        run_offline_simulator()
    else:
        logger.info("VITS ERP Telegram Bot started polling...")
        try:
            bot.infinity_polling()
        except Exception as e:
            logger.error(f"Critical error in bot polling: {e}")
            logger.info("Falling back to local terminal simulator...")
            run_offline_simulator()


```

---

## [.agents\rules\graphify.md](file:///d:/claude demo/vits-erp-streamlit/.agents/rules/graphify.md)

```markdown
---
trigger: always_on
description: Consult the graphify knowledge graph at graphify-out/ for codebase and architecture questions.
---

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- For codebase or architecture questions, when `graphify-out/graph.json` exists, first run `graphify query "<question>"` (CLI) or `query_graph` (MCP). Use `graphify path "<A>" "<B>"` / `shortest_path` for relationships and `graphify explain "<concept>"` / `get_node` for focused concepts. These return a scoped subgraph, usually much smaller than `GRAPH_REPORT.md` or raw grep output.
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)

```

---

## [.agents\workflows\graphify.md](file:///d:/claude demo/vits-erp-streamlit/.agents/workflows/graphify.md)

```markdown
---
name: graphify
description: Turn any folder of files into a navigable knowledge graph
---

# Workflow: graphify

Follow the graphify skill installed at ~/.gemini/config/skills/graphify/SKILL.md to run the full pipeline.

If no path argument is given, use `.` (current directory).

```

---

## [.streamlit\config.toml](file:///d:/claude demo/vits-erp-streamlit/.streamlit/config.toml)

```toml
[theme]
primaryColor = "#00D8C6"
backgroundColor = "#090b0f"
secondaryBackgroundColor = "#121620"
textColor = "#f8fafc"
font = "sans serif"

[server]
port = 8501
address = "0.0.0.0"
headless = true

```

---

## [.streamlit\secrets.toml](file:///d:/claude demo/vits-erp-streamlit/.streamlit/secrets.toml)

```toml
[database]
url = "postgresql://postgres.apifahyalgvjswlspfxt:Vits2026erp@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"

[google_drive]
api_key = "AIzaSyCMuWAi15u9nrqoH20xN5kqdbho2tVCVws"

[gemini]
api_key = "AIzaSyCMuWAi15u9nrqoH20xN5kqdbho2tVCVws"

[telegram]
bot_token = "8908610931:AAFrj1dPdJEH9UGjlk4wTSYBiNVB9U8qyiw"




```

---
