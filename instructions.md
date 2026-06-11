# 🎓 VITS ERP — Complete Project & Backend Guide (For First-Year Students)

> Written specifically for YOU — a first-year student who built this project and needs to explain it confidently in an interview.

---

## 📦 1. What Is "Backend" and "Frontend"?

Imagine the app is a restaurant:
* **Frontend** = the menu, tables, waiter (what the user sees — Streamlit UI)
* **Backend** = the kitchen, storage, chef logic (where data is stored and processed)
* **Database** = the fridge/pantry (where all raw data lives)

Your project has **3 backend layers**:

```
Browser (User)
     ↓
Streamlit UI  (streamlit_app.py)   ← Frontend
     ↓
Python Logic  (database.py)        ← Backend / Business Logic
     ↓
SQLite / PostgreSQL Database       ← Data Storage
```

### Is Streamlit 100% Python?
**Yes, it is 100% Python.** 
* You write all of the application logic, page routing, database queries, and data processing in pure Python (`streamlit_app.py`).
* Under the hood, Streamlit translates your Python code into a modern React-based web interface in the user's browser.
* In this specific codebase, we have also injected custom inline **HTML/CSS** inside `st.markdown()` calls to give the app a premium, custom glassmorphism design (with custom cards, colors, and gradients) that goes beyond Streamlit's default basic look.

---

## 🗃️ 2. What is SQL?

**SQL = Structured Query Language**

It's the language you use to talk to a database. Think of it like this:

| English | SQL |
|---|---|
| "Give me all students" | `SELECT * FROM students` |
| "Give me only ECE students" | `SELECT * FROM students WHERE branch='ECE'` |
| "Add a new student" | `INSERT INTO students (roll_no, name) VALUES ('25891A04C9', 'Manideep')` |
| "Update Manideep's phone" | `UPDATE students SET phone='9999' WHERE roll_no='25891A04C9'` |
| "Delete a student" | `DELETE FROM students WHERE roll_no='25891A04C9'` |

These 4 operations are called **CRUD**:
* **C**reate → `INSERT`
* **R**ead → `SELECT`
* **U**pdate → `UPDATE`
* **D**elete → `DELETE`

---

## 🏗️ 3. How Your Database Is Structured (Tables)

Your database (`vits_erp.db`) has **8 tables**. Think of each table like a spreadsheet tab:

### 1. `students` table
Stores one row per student.

| roll_no | name | dob | section | branch | semester |
|---|---|---|---|---|---|
| 25891A04C9 | Manideep Velchuri | 2007-05-12 | ECE_B | ECE | 2 |
| 25891A0465 | Harshit Ram | PENDING | ECE_B | ECE | 2 |

```sql
-- How this was created in database.py:
CREATE TABLE IF NOT EXISTS students (
    roll_no      TEXT PRIMARY KEY,   -- unique ID, like Aadhar number
    name         TEXT,
    dob          TEXT DEFAULT 'PENDING',
    section      TEXT,
    branch       TEXT,
    semester     INTEGER DEFAULT 2
);
```

### 2. `attendance` table
One row per student per subject per semester.

| roll_no | subject | semester | hours_attended | hours_conducted |
|---|---|---|---|---|
| 25891A04C9 | DS | Sem 2 | 28 | 30 |
| 25891A04C9 | PYTHON | Sem 2 | 25 | 30 |

```sql
CREATE TABLE IF NOT EXISTS attendance (
    roll_no         TEXT,
    subject         TEXT,
    semester        TEXT,
    hours_attended  INTEGER DEFAULT 0,
    hours_conducted INTEGER DEFAULT 0,
    UNIQUE(roll_no, subject, semester),        -- can't have duplicate rows
    FOREIGN KEY(roll_no) REFERENCES students(roll_no)
);
```

### 3. `marks` table
One row per student, per subject, per exam type.

| roll_no | subject | semester | exam_type | score | grade_point |
|---|---|---|---|---|---|
| 25891A04C9 | DS | Sem 1 | Sem 1 Final Examinations | 78.0 | 8.0 |
| 25891A04C9 | DS | Sem 1 | Mid 1 | 22.0 | - |

```sql
CREATE TABLE IF NOT EXISTS marks (
    roll_no     TEXT,
    subject     TEXT,
    semester    TEXT,
    exam_type   TEXT,
    score       REAL,
    grade_point REAL,
    UNIQUE(roll_no, subject, semester, exam_type),
    FOREIGN KEY(roll_no) REFERENCES students(roll_no)
);
```

### 4. `sgpa_records` table
One row per student per semester storing their SGPA.

| roll_no | semester | sgpa | failed |
|---|---|---|---|
| 25891A04C9 | Sem 1 | 9.14 | 0 |

```sql
CREATE TABLE IF NOT EXISTS sgpa_records (
    roll_no   TEXT,
    semester  TEXT,
    sgpa      REAL,
    failed    INTEGER DEFAULT 0,
    PRIMARY KEY(roll_no, semester),
    FOREIGN KEY(roll_no) REFERENCES students(roll_no)
);
```

### 5. `timetable` table — periods and subjects per section per day
### 6. `config` table — admin settings (active semester, start date)
### 7. `scrape_log` table — logs of when attendance was scraped
### 8. `attendance_history` table — daily snapshots of attendance %

---

## 🔑 4. Key SQL Concepts Used In Your Project

### PRIMARY KEY
A unique identifier for each row — like your roll number.
```sql
roll_no TEXT PRIMARY KEY   -- No two students can have the same roll_no
```

### FOREIGN KEY
Links one table to another — like a reference.
```sql
FOREIGN KEY(roll_no) REFERENCES students(roll_no)
-- This means: the roll_no in attendance MUST exist in the students table
-- You can't add attendance for a student who doesn't exist
```

### UNIQUE Constraint
Prevents duplicate data.
```sql
UNIQUE(roll_no, subject, semester)
-- A student can only have ONE attendance record per subject per semester
```

### INDEX
Makes searching faster — like the index at the back of a textbook.
```sql
CREATE INDEX IF NOT EXISTS idx_marks_roll ON marks(roll_no);
-- Now searching marks by roll_no is 10x faster
-- Without index: database checks every row (slow)
-- With index: database jumps directly to matching rows (fast)
```

### INSERT OR REPLACE
If a record exists → update it. If not → create it.
```sql
INSERT OR REPLACE INTO attendance (roll_no, subject, semester, hours_attended, hours_conducted)
VALUES ('25891A04C9', 'DS', 'Sem 2', 28, 30)
-- Used in seeding from CSV files
```

---

## ⚙️ 5. How `database.py` Works (Step by Step)

### Step 1: Connect to Database
```python
def get_db_connection():
    conn = sqlite3.connect('vits_erp.db', timeout=30)
    conn.row_factory = sqlite3.Row   # lets you access rows like a dict: row['name']
    conn.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging for better concurrent access
    return _SQLiteConn(conn)         # wrapped with caching layer
```
> Think of this like "opening a phone call" to the database. You open it, do your work, then close it.

### Step 2: Query Caching (Your custom optimization!)
* database.py has a `_QUERY_CACHE` dictionary.
* When you run `SELECT`, the result is saved for 300 seconds (5 min).
* If the same query runs again, it returns from cache — NO database hit.
* When you `INSERT`/`UPDATE`/`DELETE`, the cache is cleared automatically.
> **Interview Tip**: "I implemented an in-memory query cache that reduces database load by storing SELECT results for 5 minutes and invalidating them on any write operation."

### Step 3: The SGPA Calculation Logic
```python
def compute_sgpa(marks_rows):
    total_credits = 0
    weighted_gp = 0
    for row in marks_rows:
        subject = row['subject']
        credits = SUBJECT_CREDITS.get(subject, 3.0)  # e.g. DS = 3 credits
        grade_point = row['grade_point'] or 0.0       # e.g. 8.0 for 'A'
        weighted_gp += grade_point * credits           # 8.0 × 3 = 24
        total_credits += credits                       # total credits = 3
    return weighted_gp / total_credits                 # SGPA = 24/3 = 8.0
```
**Formula**: `SGPA = Σ(Grade Point × Credits) / Σ(Credits)`

### Step 4: CGPA Calculation
```python
def compute_cgpa(roll_no, conn):
    sync_sgpa_records(roll_no, conn)   # first update SGPA if marks changed
    rows = conn.execute(
        'SELECT sgpa FROM sgpa_records WHERE roll_no=? AND sgpa>0 AND failed=0',
        (roll_no,)
    ).fetchall()
    return sum(r['sgpa'] for r in rows) / len(rows)  # average of all SGPAs
```
> **CGPA = Average of all semester SGPAs** (only passing semesters count)

### Step 5: CSV Import Flow
```
Admin uploads CSV file
        ↓
parse_sem1_results_csv() or parse_and_load_csv_results()
        ↓
For each row in CSV:
    - Extract roll_no, name, marks, grade_points
    - INSERT OR REPLACE into students table
    - INSERT OR REPLACE into marks table
    - Calculate SGPA and INSERT into sgpa_records table
        ↓
conn.commit()  ← Save everything permanently
```

---

## 🌐 6. SQLite vs PostgreSQL — The Key Difference

This is a very common interview question!

| Feature | SQLite (your local DB) | PostgreSQL (Render/Cloud DB) |
|---|---|---|
| Where it lives | A single `.db` FILE on your computer | A separate SERVER on the internet |
| How many users | Best for 1 user at a time | Handles thousands of users at once |
| Setup | Zero setup, just import sqlite3 | Needs server, username, password, port |
| Speed for big data | Slower | Much faster |
| Used for | Local development, small apps | Production web apps |
| Cost | Free (just a file) | Free tier on Render/Supabase |
| Connection string | `sqlite3.connect('vits_erp.db')` | `psycopg2.connect("postgresql://user:pass@host/db")` |

### How Your Project Uses BOTH:
```
Local development  → SQLite (vits_erp.db file)
Deployed on Render → PostgreSQL (database_pg.py connects via DATABASE_URL)
```
Your `database_pg.py` file has the PostgreSQL version of all the same functions, but uses the `psycopg2` library instead of `sqlite3`.

---

## 🔌 7. How a Database Connection Works (Explained Simply)

```
Your Python code                   Database
─────────────                      ────────
conn = get_db_connection()  →      "Hello, I want to connect"
                                   "OK, connection open. Session ID: 5"
                            ←
conn.execute("SELECT...")   →      "Give me student data"
                                   "Here are 500 rows"
                            ←
conn.execute("INSERT...")   →      "Add this new student"
                                   "Done. 1 row inserted."
                            ←
conn.commit()               →      "Save everything permanently"
                                   "Saved to disk."
                            ←
conn.close()                →      "I'm done, close the connection"
                                   "Goodbye. Session closed."
                            ←
```
> **Important**: Always call `conn.close()` after you're done. Unclosed connections waste server memory. Your code does this correctly.

---

## 🔒 8. How Authentication Works In Your Project

There is NO dedicated `users` or `passwords` table. Instead:
* **Password = Date of Birth (DOB)**
* Stored in `students.dob` column.
* Default value is `"PENDING"` (before the student sets their own DOB).

```python
# Login flow in streamlit_app.py:
student = conn.execute(
    'SELECT * FROM students WHERE roll_no=?', (roll_no,)
).fetchone()

if student and student['dob'] == entered_password:
    st.session_state['logged_in'] = True
    st.session_state['user_id'] = roll_no
```

**Session State** = Streamlit's way of remembering who is logged in across page reruns. Like cookies in a browser.

---

## 🕷️ 9. The Web Scraper (harvester.py)

Your project can auto-fetch attendance from the VITS student portal:
```
harvester.py uses the Python requests library (no browser automation/Selenium)
        ↓
Performs HTTP POST to log in and maintain session cookies using requests.Session()
        ↓
Fetches HTML pages of attendance and marks directly via HTTP GET
        ↓
Parses HTML tables using BeautifulSoup (bs4)
        ↓
Calls database.py functions to INSERT/UPDATE attendance records
        ↓
Logs the scrape in scrape_log table
```

---

## 🤖 10. The Telegram Bot (telegram_bot.py)

Uses the **Telegram Bot API**:
```
Student sends message to @vits_student_query_bot
        ↓
Telegram sends it to your Python bot via HTTP
        ↓
Bot parses the message (e.g., "attendance")
        ↓
Bot queries the SAME vits_erp.db database
        ↓
Bot sends formatted reply back to student on Telegram
```

---

## 📊 11. The Full Data Flow When a Student Logs In

```
1. Student enters roll_no + DOB on login page
2. streamlit_app.py queries: SELECT * FROM students WHERE roll_no=?
3. DOB matches → session_state['logged_in'] = True
4. student_dashboard() loads:
   a. Queries: SELECT * FROM students WHERE roll_no=?       (profile)
   b. Queries: SELECT sgpa FROM sgpa_records WHERE roll_no=? (CGPA)
   c. Queries: SELECT ... FROM attendance WHERE roll_no=?   (attendance %)
   d. Queries: SELECT ... FROM marks WHERE roll_no=?        (exam scores)
5. All data rendered via Streamlit widgets (charts, tables, metrics)
6. conn.close()  ← connection returned to pool
```

---

## 🗂️ 12. File Structure Summary

| File | What It Does |
|---|---|
| `streamlit_app.py` | Full frontend + page routing + UI (2988 lines) |
| `database.py` | SQLite connection, all DB functions, CSV import, SGPA logic |
| `database_pg.py` | Same as database.py but for PostgreSQL (production) |
| `harvester.py` | Web scraper — fetches live attendance from portal |
| `telegram_bot.py` | Telegram bot that answers student queries |
| `pdf_generator.py` | Generates PDF report cards for students |
| `vits_erp.db` | The actual SQLite database file (58 MB of real data!) |
| `render.yaml` | Tells Render.com how to deploy the Telegram bot |
| `requirements.txt` | List of Python packages needed to run the project |

---

## 🔌 13. Specific Streamlit API Components Used

### Layout & Structure
* **`st.columns([ratio1, ratio2, ...])`**: Splits the page layout into side-by-side columns (e.g., placing the semester selector next to the Results title, or splitting the Home page into 3 columns for the circular progress meter, subject health, and daily schedule).
* **`st.sidebar`**: Creates the left side navigation panel where the student profile card, menu options, and download buttons live.
* **`st.expander("Title")`**: Creates a collapsible/expandable drawer (used to hide/show details for each subject in the Attendance tab).

### Output & Visuals
* **`st.markdown(html_string, unsafe_allow_html=True)`**: Used extensively with `unsafe_allow_html=True` to bypass standard markdown and render **custom HTML/CSS**. This is how the premium college header, circular meters, glowing KPI cards, and custom tables are drawn.
* **`st.plotly_chart(figure)`**: Renders interactive Plotly charts (such as the Marks Progression line chart and Attendance bar charts).
* **`st.link_button("Label", "URL")`**: Renders a button that opens an external link in a new tab (used to open the college Cloud Drive).

### Inputs & Interactive Controls
* **`st.selectbox("Label", options)`**: Creates the dropdown menus (used for selecting the viewing semester and picking which day of the timetable to view).
* **`st.radio("Label", options)`**: Renders a radio list selector (used for the sidebar navigation links: *Home, Attendance, Marks, etc.*).
* **`st.slider("Label", min, max)`**: Creates sliders (used in the SGPA calculator and attendance skip predictor so students can drag and simulate grades/days missed).
* **`st.button("Label")`**: A clickable trigger (used for "Download Report PDF" and "Logout").
* **`st.text_input("Label", type="password")`**: Captures text inputs (used on the login screen for Roll Numbers and passwords).
* **`st.date_input("Label")`**: Opens a calendar date-picker widget (used during onboarding for the student to select their Date of Birth).

### Feedback & Status Displays
* **`st.success("Message")`**: Displays a green confirmation box (e.g., "Login Successful" or "Safe Zone").
* **`st.info("Message")`**: Displays a blue informational alert box (e.g., "No data found for this semester").
* **`st.warning("Message")`**: Displays a yellow warning alert box (e.g., "Risk Zone").
* **`st.error("Message")`**: Displays a red error box (e.g., "Incorrect roll number or password").

### Backend Logic & Operations
* **`st.session_state`**: A global dictionary that stores persistent data across user interactions (e.g., tracking the logged-in student's ID, branch, name, and the currently selected semester).
* **`st.rerun()`**: Instantly restarts script execution from the top of the file so that changes made by one action (like switching tabs or semesters) reflect immediately on the screen.

---

## 💬 14. Comprehensive Interview Preparation Q&As

### Category A: Project Architecture & System Design

#### Q1: "What database did you use, and why?"
* **Your Answer**: 
  > *"I used **SQLite** for local development because it requires zero server setup — it's just a file. For production deployment on Render, I migrated to **PostgreSQL** which handles concurrent users better. Both use the same SQL syntax so the migration was straightforward."*

#### Q2: Can you explain the end-to-end architecture of this portal?
* **Your Answer**: 
  > *"The system uses a 4-tier architecture: 
  > 1. **Data Source**: The official college ERP portal (external).
  > 2. **Data Harvester/Scraper (`harvester.py`)**: Connects to the ERP, scrapes attendance, marks, and timetables using BeautifulSoup, and formats it.
  > 3. **Database (`vits_erp.db`)**: A local SQLite relational database storing tables for students, attendance, marks, timetables, and SGPA.
  > 4. **User Interfaces**: A **Streamlit web portal** (`streamlit_app.py`) for student/admin visual access and a **Telegram Bot** (`telegram_bot.py`) for quick mobile lookups."*

#### Q3: Difference between SQL and NoSQL databases?
* **Your Answer**:
  > *"SQL databases (like SQLite, PostgreSQL) store data in structured tables with fixed schemas and are great when relationships between data matter. NoSQL databases (like MongoDB) store data as flexible documents or key-value pairs and are better for unstructured data. We chose SQL because our data has clear relationships — students have attendance records, marks, SGPA etc."*

#### Q4: What is normalization?
* **Your Answer**:
  > *"Normalization is organizing a database to avoid repeating data. In our project, instead of storing the student's name in every attendance row, we store it once in the students table and reference it via roll_no. This saves space and keeps data consistent."*

#### Q5: What is an ORM?
* **Your Answer**:
  > *"ORM stands for Object-Relational Mapping — it lets you write Python code instead of SQL. Libraries like SQLAlchemy are ORMs. In our project we chose to write raw SQL queries directly for better control and performance. For example: `conn.execute('SELECT * FROM students WHERE roll_no=?', (roll_no,))`."*

---

### Category B: SQL Concepts

#### Q6: "What is a PRIMARY KEY?"
* **Your Answer**: 
  > *"A PRIMARY KEY is a column (or set of columns) that uniquely identifies each row in a table. In our students table, `roll_no` is the primary key — no two students can have the same roll number, just like an Aadhar number."*

#### Q7: "What is a FOREIGN KEY?"
* **Your Answer**: 
  > *"A FOREIGN KEY creates a link between two tables. In our project, the `attendance` table has a foreign key `roll_no` that references `students(roll_no)`. This means you can't insert attendance data for a student who doesn't exist in the students table. It enforces data consistency."*

#### Q8: "What is an INDEX and why do you use it?"
* **Your Answer**: 
  > *"An index is a data structure that makes database searches faster. Without an index, the database has to scan every row. We added indexes on commonly queried columns like `roll_no` in the marks table: `CREATE INDEX IF NOT EXISTS idx_marks_roll ON marks(roll_no);` which makes searching marks by roll_no 10x faster."*

#### Q9: "What is CRUD?"
* **Your Answer**: 
  > *"CRUD stands for Create, Read, Update, Delete — the four basic database operations. In SQL these are INSERT, SELECT, UPDATE, and DELETE. For example, when a student registers it's INSERT, viewing marks is SELECT, admin updating a score is UPDATE."*

#### Q10: "What is a database transaction?"
* **Your Answer**: 
  > *"A transaction is a group of SQL operations that either ALL succeed or ALL fail together. In our CSV import, we insert hundreds of student records and marks. We call `conn.commit()` only after all inserts succeed. If something fails midway, the database rolls back to the previous state."*

---

### Category C: Business Logic & Calculations

#### Q11: How did you implement the CGPA and SGPA calculation logic?
* **Your Answer**:
  > *"I implemented a credit-weighted grading system based on JNTUH regulations. In `database.py`:
  > 1. I converted marks to letter grades and grade points (e.g., Score $\ge 90$ is 'O', worth 10 points; $\ge 40$ is 'C', worth 5 points; $< 40$ is 'F', worth 0 points).
  > 2. **SGPA** is calculated as: $\frac{\sum (\text{Grade Points} \times \text{Subject Credits})}{\sum \text{Subject Credits}}$ for the current semester.
  > 3. **CGPA** is calculated by aggregating the credit-weighted grade points across all completed semesters."*

#### Q12: How does the system handle student backlogs (fails) in calculations?
* **Your Answer**:
  > *"If a student scores below 40% in a final exam, they receive an **'F' grade (0 grade points)**. The database logs this failed status. On the home page:
  > 1. The backlog is counted, and the student's status is set to 'Pending' (or backlogs are listed).
  > 2. The subject is flagged in red in the grades table.
  > 3. The SGPA calculation includes the 0 grade points in the numerator but includes the subject credits in the denominator, dragging down the overall average as per university rules."*

---

### Category D: Web Scraping & Integrations

#### Q13: How does your web scraper log into the college portal and extract data?
* **Your Answer**:
  > *"The scraper is a lightweight **requests-based scraper** (no Selenium or browser automation). It uses Python’s **`requests.Session()`** to maintain session cookies across HTTP requests. It sends credentials in a POST request to the college login endpoint. Once authenticated, it fetches the attendance and marks HTML pages directly via GET requests, and uses **`BeautifulSoup`** to parse the HTML and extract data from table cells using tags and classes."*

#### Q14: What happens if the college ERP portal changes its user interface or HTML structure?
* **Your Answer**:
  > *"Since web scrapers rely on the HTML structure of the target site, any structural change on the college ERP will cause the scraper to fail. To handle this, I wrapped scraping calls in `try-except` blocks with error logging. The database acts as a cache—if the scraper fails, students can still access their cached data. In production, I would configure alerts so CSS selectors can be updated."*

#### Q15: How does the Telegram Bot interact with the database?
* **Your Answer**:
  > *"The bot uses the **`pyTelegramBotAPI`** library running in a polling loop. When a student sends a message containing their roll number, the bot queries the SQLite database, formats their attendance and marks into clean, readable text messages, and replies back immediately. It provides a lightweight, data-friendly alternative to loading the web page."*

---

### Category E: Streamlit Portal Interactivity (The Recent Code Fixes)

#### Q16: How does Streamlit handle state, and how did you implement login sessions?
* **Your Answer**: 
  > *"By default, Streamlit is stateless and reruns the entire Python script from line 1 to the end whenever a user clicks a button or changes an input. Any local variables are lost. To maintain user login state and track who is logged in, I used **`st.session_state`** (e.g., storing `st.session_state.user_id` and `st.session_state.role`)."*

#### Q17: How did you synchronize the two semester dropdowns (sidebar and result page) dynamically?
* **Your Answer**:
  > *"Having two selectboxes modify the same state can cause a conflict because of execution order. I stored the master semester choice in `st.session_state['selected_sem']`. At the very top of the script (before any UI is rendered), I check if either widget key (`sidebar_sem_select` or `result_sem_select`) was changed by the user, update the master key, and set both widgets' default index to match. This ensures both dropdowns stay completely in sync in a single execution pass."*

#### Q18: How did you design a premium UI if Streamlit only supports generic layouts?
* **Your Answer**:
  > *"Streamlit's default UI is simple, so I customized it by injecting custom HTML templates and CSS code using **`st.markdown(html, unsafe_allow_html=True)`**. I built glassmorphic layout grids, styling tokens, custom dashboard cards, progress legends, and college headers entirely in CSS, keeping the backend logic in Python."*

#### Q19: Why do you need `st.rerun()`, and when did you use it?
* **Your Answer**:
  > *"Since Streamlit runs top-to-bottom, if a user clicks **'Logout'**, I delete the keys in `st.session_state` and call **`st.rerun()`** to force the script to restart immediately from line 1. This prevents the dashboard from throwing errors due to missing session variables and redirects the user to the login page instantly."*

#### Q20: How did you handle charts and prevent them from crashing when a semester has no data?
* **Your Answer**:
  > *"I integrated **Plotly Express** (`px.bar` and `px.line`) with Streamlit via **`st.plotly_chart`**. If a student switches to a semester with no data (like Sem 1), Plotly will throw an error because the DataFrame is empty. I added guard checks (`if subj_data:`) to bypass the chart drawing and display a clean message instead."*

---

## ✅ 15. Quick Summary For Interview

> "I built a full-stack Student ERP for VITS college using **Python + Streamlit** for the frontend, **SQLite** for local development and **PostgreSQL** for production. The backend handles authentication via DOB matching, stores attendance and marks data in a relational database with 8 tables, computes SGPA/CGPA using the JNTUH grading formula, and includes a web scraper for live portal data and a Telegram bot for student queries. The data was seeded from real CSV files exported from the college system."

---

## 🧠 16. Advanced Concepts to Impress the Interviewer (Deep Dive)

### A. Web Scraping Payload & Session Maintenance
* **HTTP POST Authentication**: In `harvester.py`, when a student requests a sync, the scraper makes an HTTP POST request to the college login URL. The request payload contains credentials in a URL-encoded form dictionary (e.g., `{'username': roll_no, 'password': password}`).
* **Session Persistence (`requests.Session`)**: In HTTP, requests are stateless. If you log in with one request, you are logged out on the next. `requests.Session()` solves this by automatically maintaining cookies (like the session ID cookie) in memory across requests. This allows us to fetch attendance data using a subsequent GET request without logging in again.
* **BeautifulSoup Parsing**: To parse tables, the code locates the `<table>` element, iterates over all `<tr>` (table row) tags, extracts text inside each `<td>` (table cell) tag using `.get_text(strip=True)`, and converts numbers (like hours attended and conducted) into Python integers for storage.

### B. Database Performance & Multi-User Architecture (WAL Mode)
* **WAL Mode (Write-Ahead Logging)**: SQLite is file-based and normally locks the entire database file during writes, blocking readers. We enable WAL mode by executing `PRAGMA journal_mode=WAL;`. This writes updates to a separate `-wal` file first, allowing readers to read the main database file concurrently while writes are happening. This is critical for web applications with multiple concurrent users.
* **Query Cache (`_QUERY_CACHE`)**: To prevent database bottlenecks, we implemented a custom in-memory caching wrapper. If the same `SELECT` query runs within 5 minutes, it returns the results from a dictionary in memory, avoiding disk I/O. Any write operation (`INSERT`, `UPDATE`, `DELETE`) immediately clears this cache to ensure students always see fresh data.

### C. Streamlit Execution Model & State Management
* **The Streamlit Lifecycle**: Unlike traditional web servers (like Flask or Django) which start a persistent process and respond to specific API routes, Streamlit executes the entire script file from top to bottom every single time a user interacts with a widget.
* **Why `st.session_state` is Essential**: Since variables are cleared on every rerun, `st.session_state` stores data in the server's memory, associated with the user's browser session. We use it to store login credentials, current navigation tabs, and the active semester selection.
* **Widget Binding**: Passing a `key` parameter to widgets (like `st.selectbox(..., key="my_key")`) automatically binds their state to `st.session_state["my_key"]`, reducing the need for manual callback functions.

### D. Git Version Control & Deployment Workflow
* **Git**: A local tool used to track revisions of code files, create branches, and rollback mistakes (using `git status`, `git diff`, `git commit`).
* **GitHub**: A cloud hosting platform for git repositories. It acts as our central repository.
* **CI/CD & Deployment**: The project is deployed on **Render.com**. Render is linked to our GitHub repository. Whenever we push changes to the `main` branch (`git push origin main`), Render detects the new commit, rebuilds the container, and deploys the updated app automatically (Continuous Deployment).

### E. PDF Flowables & reportlab Structure
* **Flowables**: In ReportLab, instead of drawing text at exact x/y pixel coordinates (which breaks if the text length changes), we use **Flowables** (like `Paragraph`, `Table`, `Spacer`) inside a `story`.
* **SimpleDocTemplate**: We build a document layout, append flowables to the `story` list, and call `doc.build(story)`. ReportLab automatically calculates page breaks and fits content dynamically, preventing text overlaps.

### F. Real-World Bug Fixes You Resolved
If the interviewer asks: *"Tell me about a challenging bug you fixed in this project."* You have two amazing answers:
1. **Markdown Parsing Bug**: *“Streamlit's markdown renderer got confused by raw HTML tags containing vertical newlines and spaces, rendering them as plain code text. I resolved this by formatting the HTML dynamically as a single-line string with `.replace('\n', ' ')`, which forced Streamlit to compile it correctly as visual components.”*
2. **Mobile Viewport Overlap**: *“On mobile screens, Streamlit's native top header was overlapping our custom college header. I resolved this by injecting custom CSS overrides that target the `.block-container` styling, adding top padding of `3.5rem !important` on smaller screens to ensure both headers sit neatly without covering each other.”*
