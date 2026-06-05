# VITS Academic ERP — Project Architecture & Technical Analysis

This document provides a comprehensive technical analysis of the **VITS Academic ERP & Bunk Intelligence Dashboard**. It details the project's folder structure, database design, dynamic routing, scraping mechanisms, frontend components, and cloud deployment workflow on Streamlit Community Cloud.

---

## 📂 1. Directory Structure Overview

The project is structured as a monolithic Streamlit application with helper scripts for database operations, scraping, and PDF generation:

```text
d:\claude demo\vits-erp-streamlit\
│
├── .streamlit/
│   ├── config.toml           # Streamlit theme setup (dark mode, custom fonts)
│   └── secrets.toml          # Local secrets (PostgreSQL connection URL for local test)
│
├── attandance database for db construction/ # Raw CSV files from initial data dumps
├── resutls database for db construction/    # Raw results data
│
├── database.py               # Local SQLite operations & dynamic router
├── database_pg.py            # PostgreSQL (Supabase) direct port with pooling
├── migrate_sqlite_to_pg.py   # Seeding utility to copy local data to PostgreSQL
├── harvester.py              # Scraper for the internal college portal (103.52.36.11)
├── pdf_generator.py          # ReportLab generator for PDF report cards
├── streamlit_app.py          # Main web application entry point (UI & routing)
│
├── requirements.txt          # Python dependencies
└── vits_erp.db               # Local SQLite database (development)
```

---

## ⚙️ 2. Dual-Database Architecture & Dynamic Routing

One of the key engineering solutions in this project is the **Hybrid SQLite / PostgreSQL Routing**.

### The Ephemeral Disk Challenge
Streamlit Community Cloud runs your app in ephemeral containers. Any changes written to local files (like a SQLite `.db` file) are discarded when the container restarts. To ensure data persistence, the project uses **Supabase (PostgreSQL)** in cloud deployment, while retaining **SQLite** locally for fast, offline development.

```
       ┌────────────────────────────────────────────────────────┐
       │                      streamlit_app.py                  │
       └───────────────────────────┬────────────────────────────┘
                                   │ (Check for secrets / env)
                                   ▼
                   ┌───────────────┴───────────────┐
                   │                               │
         [PostgreSQL active?]             [SQLite active?]
                   │                               │
                   ▼                               ▼
       ┌───────────────────────┐       ┌───────────────────────┐
       │   database_pg.py      │       │     database.py       │
       │ (PostgreSQL/Supabase) │       │   (Local SQLite)      │
       └───────────────────────┘       └───────────────────────┘
```

### Dynamic Routing Implementation (`database.py`)
In `database.py`, the module intercepts its own function calls and routes them dynamically if PostgreSQL is detected (either through environment variables or Streamlit secrets):

```python
# database.py
import os
import streamlit as st

_DB_BACKEND = "sqlite"
if os.environ.get("DATABASE_URL") or st.secrets.get("database", {}).get("url"):
    _DB_BACKEND = "pg"

# If PG backend is active, override SQLite exports with PG exports
if _DB_BACKEND == "pg":
    import database_pg as _pg
    init_db = _pg.init_db
    get_db_connection = _pg.get_db_connection
    get_config_map = _pg.get_config_map
    # (other functions are overridden dynamically)
```

### Row Compatibility Wrapper (`database_pg.py`)
Python's `sqlite3` driver returns rows that can be accessed by both index and column name (e.g. `row[0]` and `row['name']`). PostgreSQL's `psycopg2` driver returns tuples or dictionaries, which causes runtime errors in Streamlit code written for SQLite. 

To solve this, a custom **`_RowWrapper`** class makes PostgreSQL dictionaries behave exactly like `sqlite3.Row`:

```python
class _RowWrapper:
    def __init__(self, d):
        self._d = dict(d)
        self._vals = list(self._d.values())
        
    def __getitem__(self, key):
        if isinstance(key, int):
            return self._vals[key]  # Index-based access: row[0]
        return self._d[key]         # Key-based access: row['name']
        
    def __contains__(self, key):
        return key in self._d
        
    def keys(self):
        return self._d.keys()
```

### Connection Pooling & Recovery
To prevent connection exhaustion under multi-user traffic, `database_pg.py` uses a thread-safe connection pool (`ThreadedConnectionPool`) with automatic cleanup:

```python
@st.cache_resource
def get_pg_pool():
    # Initializes connection pool once across the Streamlit lifecycle
    return ThreadedConnectionPool(minconn=1, maxconn=10, dsn=DATABASE_URL)
```

---

## 🗄️ 3. Database Schema

The database consists of 8 main tables. The schemas are syntactically adjusted for SQLite (dynamic typings) and PostgreSQL (strict types):

```mermaid
erDiagram
    STUDENTS {
        text roll_no PK
        text name
        text dob
        text email
        integer semester
        text department
        text section
        text branch
        text phone
        text parent_phone
        text theme_pref
    }
    CONFIG {
        text key PK
        text value
    }
    SUBJECTS {
        text subject_code PK
        text subject_name
    }
    ATTENDANCE {
        text roll_no PK, FK
        text subject_code PK, FK
        integer hours_attended
        integer hours_conducted
    }
    ATTENDANCE_HISTORY {
        integer id PK
        text roll_no FK
        text date
        text period
        text subject
        text status
        text scraped_at
    }
    MARKS {
        text roll_no PK, FK
        text subject PK
        integer semester PK
        text exam_type PK
        integer score
        real grade_point
    }
    TIMETABLE {
        text department PK
        text section PK
        text day PK
        text period PK
        text subject
    }
    SGPA_RECORDS {
        text roll_no PK, FK
        integer semester PK
        real sgpa
        integer failed
    }

    STUDENTS ||--o| ATTENDANCE : "tracks overall"
    STUDENTS ||--o| ATTENDANCE_HISTORY : "records logs"
    STUDENTS ||--o| MARKS : "achieves"
    STUDENTS ||--o| SGPA_RECORDS : "earns"
```

---

## 🕸️ 4. Attendance Scraper (`harvester.py`)

The attendance harvester extracts student data from the college's internal local server (`http://103.52.36.11`).

### Workflow
1. **Validation**: Submits a `POST` request to `Validate.php` with the student's Roll Number and Date of Birth (acting as password).
2. **Session Preservation**: Saves the session cookies to keep the connection authorized.
3. **Extraction**:
   - Queries `Crprint.php` to download the student's attendance summary (Subject-wise hours conducted/attended).
   - Parses the returned HTML using **BeautifulSoup4** to extract summary rows.
   - Queries individual calendar date ranges to fetch period-by-period attendance logs (e.g. Period 1: Present, Period 2: Absent).
4. **Synchronization**: Merges scraped records into the active database backend using SQL `ON CONFLICT DO UPDATE` queries to ensure no duplicate rows are created.

---

## 📊 5. Frontend & UI Flow (`streamlit_app.py`)

The user interface uses modern layout controls, featuring a custom dark theme with a vibrant `#00D8C6` neon primary color.

```
                  ┌──────────────────────────────┐
                  │          Landing Page        │
                  └──────────────┬───────────────┘
                                 ▼
                     ┌───────────┴───────────┐
                     │      Login Panel      │
                     └───────────┬───────────┘
                                 │ (Authenticates roll/dob)
                                 ▼
                     ┌───────────┴───────────┐
                     │    Role Redirect      │
                     └─────┬───────────┬─────┘
                           │           │
                 (Student) │           │ (Admin)
                           ▼           ▼
        ┌────────────────────┐       ┌────────────────────┐
        │  Student Dashboard │       │  Admin Dashboard   │
        │ - Scrape Trigger   │       │ - Analytics Graphs │
        │ - SGPA & Grades    │       │ - Bunk Intelligence│
        │ - PDF Report Card  │       │ - Student Lookup   │
        └────────────────────┘       └────────────────────┘
```

### The Bunk Intelligence Dashboard (Admin View)
The Admin panel features high-density charts constructed with Plotly:
* **KPI Metric Cards**: Real-time cards displaying total students, bunk rates, and count of chronic bunkers.
* **Period/Day Trends**: Histograms highlighting the specific days and hours classes are bunked the most (e.g. high absentee rates during P1 or Fridays).
* **Mass Bunk Detection**: Identifies dates where actual class absences exceeded expected thresholds, flagging them as mass bunk events.
* **Granular Drilldowns**: Dropdown menus to isolate analytics down to specific classes, sections, and individual student profiles.
* **Interactability Fixes**: Applied `dragmode=False` config to Plotly layouts to disable finger-dragging zooms on mobile screens, making page scrolling seamless.

---

## ☁️ 6. Cloud Deployment Model (Streamlit Community Cloud)

When deployed to Streamlit Community Cloud, the server and configuration are managed automatically:

### App Entry Point
Streamlit Community Cloud monitors your GitHub repository. It reads `requirements.txt` to install the environment dependencies and runs `streamlit_app.py` directly as the entry point.

### Secure Database Connection
Rather than exposing database passwords in the code or git, Streamlit Cloud uses its native **Secrets Manager**:

1. Under the app's **Advanced Settings** on Streamlit Cloud, the connection credentials are pasted in the **Secrets** text area using TOML format:
   ```toml
   [database]
   url = "postgresql://postgres.apifahyalgvjswlspfxt:Vits2026erp@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"
   ```
2. When the app initializes, `st.secrets` parses this configuration.
3. `streamlit_app.py` detects this active database configuration, bypasses the local SQLite fallback, and connects to the **Supabase PostgreSQL cluster**.
