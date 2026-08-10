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
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)

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
    
    # Manual runs / workflow dispatch set force_run=True, scheduled cron runs set force_run=False to apply Smart Skip logic
    force_run = force_flag or force_env or (event_name == "workflow_dispatch")
    if "--no-force" in sys.argv:
        force_run = False
        
    print(f"[*] Active Semester : {sem}")
    print(f"[*] Date Range      : {start_date} to {end_date}")
    print(f"[*] Force Scrape     : {force_run} ({'Manual/Dispatched Run' if force_run else 'Scheduled Cron Run'})")
    print(f"[*] Starting bulk scrape of all sections...")
    
    results = harvester.bulk_scrape_all(
        semester=sem,
        start_date=start_date,
        end_date=end_date,
        force=force_run
    )
    
    print(f"\n[+] Scrape finished! Results summary:")
    ok_count = 0
    for r in results:
        status = "OK" if r['ok'] else "FAILED"
        print(f"    - {r['section']}: {status} | {r['msg']}")
        if r['ok']:
            ok_count += 1
            
    print(f"\n[+] Total sections synced successfully: {ok_count}/{len(results)}")
    
    # Send Telegram notification if credentials are provided in env/secrets
    send_telegram_summary(results, ok_count, len(results), ist_now.strftime('%Y-%m-%d %H:%M:%S'))
    
    # If all sections failed, exit with error code so GitHub Action alerts us
    if len(results) > 0 and ok_count == 0:
        print("[ERROR] All sections failed to sync. Portal might be down.")
        sys.exit(1)


def send_telegram_summary(results, ok_count, total_count, ist_now_str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("CHAT_ID")
    if not token or not chat_id:
        print("[*] Telegram notification skipped (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not configured).")
        return
    try:
        import urllib.request
        import urllib.parse
        import json
        
        status_emoji = "✅" if ok_count > 0 else "❌"
        msg = f"{status_emoji} *VITS Attendance Scrape Completed!*\n\n"
        msg += f"📅 *Time:* {ist_now_str} IST\n"
        msg += f"📊 *Synced:* {ok_count}/{total_count} sections successfully\n\n"
        
        for r in results[:10]:
            st_icon = "🟢" if r['ok'] else "🔴"
            msg += f"{st_icon} *{r['section']}*: {r['msg']}\n"
        if len(results) > 10:
            msg += f"_\n...and {len(results) - 10} more sections._"

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                print("[+] Telegram notification sent successfully to your phone!")
    except Exception as e:
        print(f"[!] Failed to send Telegram notification: {e}")

if __name__ == "__main__":
    main()
