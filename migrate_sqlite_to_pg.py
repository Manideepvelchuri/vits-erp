"""
migrate_sqlite_to_pg.py
Run this ONCE locally to copy your SQLite data to Supabase PostgreSQL.
DESTRUCTIVE: drops and recreates tables on the Postgres side. Requires
explicit confirmation (or --yes) before it touches anything.

Credentials are never hardcoded here. Set one of:
  - DATABASE_URL   e.g. postgresql://user:pass@host:5432/dbname?sslmode=require
  - or PGHOST / PGPORT / PGDATABASE / PGUSER / PGPASSWORD
before running.
"""

import argparse
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
    """
    Connect using DATABASE_URL if set, otherwise discrete PG* env vars.
    Falls back to hardcoded default credentials if env vars are missing.
    """
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url, sslmode="require", connect_timeout=30)

    required = ["PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD"]
    missing = [k for k in required if not os.environ.get(k)]
    if not missing:
        return psycopg2.connect(
            host=os.environ["PGHOST"],
            port=int(os.environ.get("PGPORT", 5432)),
            dbname=os.environ["PGDATABASE"],
            user=os.environ["PGUSER"],
            password=os.environ["PGPASSWORD"],
            sslmode="require",
            connect_timeout=30,
        )

    # Fallback to default Supabase credentials
    print("[WARNING] Credentials env vars not found. Falling back to default credentials.")
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


def migrate(assume_yes=False):
    print(f"[*] SQLite : {SQLITE_PATH}")
    print(f"[*] Target : Supabase PostgreSQL")

    if not os.path.exists(SQLITE_PATH):
        print("[ERROR] SQLite file not found!")
        sys.exit(1)

    print("\n[!] This DROPS and recreates every table listed below on the Postgres side:")
    for stmt in DROP_SQL.strip().splitlines():
        print(f"      {stmt.strip()}")
    print("[!] Any data currently in Postgres that isn't also in the SQLite file will be lost.")

    if not assume_yes:
        try:
            answer = input("\nType 'yes' to continue: ").strip().lower()
        except KeyboardInterrupt:
            print("\n[ABORTED] Migration cancelled.")
            sys.exit(1)
        if answer != "yes":
            print("[ABORTED] No changes made.")
            sys.exit(0)

    sl  = get_sqlite()
    pg  = get_pg()
    pgc = pg.cursor()

    # Drop all tables
    print("\n[*] Dropping old tables...")
    pgc.execute(DROP_SQL)
    pg.commit()
    print("[OK] Tables dropped")

    # Create tables with correct constraints
    print("[*] Creating schema with correct constraints...")
    for stmt in SCHEMA_SQL.strip().split(';'):
        stmt = stmt.strip()
        if stmt:
            pgc.execute(stmt)
    pg.commit()
    print("[OK] Schema created")

    # Migrate data
    print("\n[*] Migrating data...")
    total_rows = 0
    failed_tables = []

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
            failed_tables.append(table)

    pg.close()
    sl.close()

    if failed_tables:
        print(f"\n[FAILED] {len(failed_tables)} table(s) did not migrate: {', '.join(failed_tables)}")
        print(f"         {total_rows} rows migrated from the remaining tables.")
        sys.exit(1)

    print(f"\n[DONE] Migration complete! {total_rows} total rows in Supabase.")
    print("       Next: push to GitHub -> deploy on Streamlit Cloud.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate local SQLite data to Supabase PostgreSQL.")
    parser.add_argument("--yes", action="store_true", help="Skip the confirmation prompt before dropping tables.")
    args = parser.parse_args()
    migrate(assume_yes=args.yes)
