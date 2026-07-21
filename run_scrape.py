"""
run_scrape.py
Entry-point script to run the scheduled portal attendance scraper.
Used by GitHub Actions to sync data to Supabase.
"""

import os
import sys
import datetime

# Add the current directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Auto-detect backend
is_github_action = os.environ.get("GITHUB_ACTIONS") == "true"
pg_url = os.environ.get("DATABASE_URL", "")

if is_github_action and not pg_url:
    print("[ERROR] DATABASE_URL environment variable is missing!")
    print("        Please ensure you have configured the DATABASE_URL secret in your GitHub repository secrets.")
    sys.exit(1)

if pg_url:
    print("[*] Database Backend: PostgreSQL (Supabase)")
    from database_pg import get_db_connection, get_config_map
else:
    print("[*] Database Backend: SQLite")
    from database import get_db_connection, get_config_map

import harvester

def main():
    conn = get_db_connection()
    cfg = get_config_map(conn)
    conn.close()
    
    sem = cfg.get('active_semester', 'Sem 3')
    start_date = cfg.get('start_date', '2026-01-27')
    
    # Use current date as the end date for the scrape
    ist_now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    end_date = ist_now.strftime('%Y-%m-%d')
    
    print(f"[*] Active Semester : {sem}")
    print(f"[*] Date Range      : {start_date} to {end_date}")
    print(f"[*] Starting bulk scrape of all sections...")
    
    results = harvester.bulk_scrape_all(
        semester=sem,
        start_date=start_date,
        end_date=end_date
    )
    
    print(f"\n[+] Scrape finished! Results summary:")
    ok_count = 0
    for r in results:
        status = "OK" if r['ok'] else "FAILED"
        print(f"    - {r['section']}: {status} | {r['msg']}")
        if r['ok']:
            ok_count += 1
            
    print(f"\n[+] Total sections synced successfully: {ok_count}/{len(results)}")
    
    # If all sections failed, exit with error code so GitHub Action alerts us
    if len(results) > 0 and ok_count == 0:
        print("[ERROR] All sections failed to sync. Portal might be down.")
        sys.exit(1)

if __name__ == "__main__":
    main()
