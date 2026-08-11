"""
upload_photos_to_supabase.py
Automated script to upload local student photos to Supabase Storage bucket 'student-photos'
and update the photo_url column in Supabase PostgreSQL / SQLite database.
"""

import os, glob, requests
import sqlite3

# Supabase Project Credentials
SUPABASE_PROJECT_ID = "apifahyalgvjswlspfxt"
SUPABASE_BUCKET_NAME = "student-photos"
STORAGE_PUBLIC_URL_PREFIX = f"https://{SUPABASE_PROJECT_ID}.supabase.co/storage/v1/object/public/{SUPABASE_BUCKET_NAME}"

# Path to local response sheets
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BY_SECTION_DIR = os.path.join(BASE_DIR, "results", "vits_response_sheets", "by_section")
if not os.path.exists(BY_SECTION_DIR):
    BY_SECTION_DIR = os.path.join(os.path.dirname(BASE_DIR), "results", "vits_response_sheets", "by_section")

def upload_local_photos_to_supabase(anon_or_service_key=None):
    print("=== SUPABASE STORAGE PHOTO UPLOADER ===")
    print(f"[*] Project ID : {SUPABASE_PROJECT_ID}")
    print(f"[*] Bucket Name: {SUPABASE_BUCKET_NAME}")
    print(f"[*] CDN Prefix : {STORAGE_PUBLIC_URL_PREFIX}")
    
    photo_files = glob.glob(os.path.join(BY_SECTION_DIR, "*", "*", "photo.jpg"))
    print(f"[*] Found {len(photo_files)} local student photo.jpg files.")

    db_path = os.path.join(BASE_DIR, "vits_erp.db")
    if not os.path.exists(db_path):
        db_path = os.path.join(os.path.dirname(BASE_DIR), "vits-erp-streamlit", "vits_erp.db")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    uploaded_count = 0
    updated_db_count = 0

    headers = {}
    if anon_or_service_key:
        headers = {
            "Authorization": f"Bearer {anon_or_service_key}",
            "apikey": anon_or_service_key
        }

    for pfile in photo_files:
        roll_no = os.path.basename(os.path.dirname(pfile)).strip().upper()
        if not roll_no:
            continue

        public_photo_url = f"{STORAGE_PUBLIC_URL_PREFIX}/{roll_no}.jpg"

        # If anon/service key is provided, attempt HTTP upload to Supabase Storage REST API
        if anon_or_service_key:
            try:
                upload_endpoint = f"https://{SUPABASE_PROJECT_ID}.supabase.co/storage/v1/object/{SUPABASE_BUCKET_NAME}/{roll_no}.jpg"
                with open(pfile, 'rb') as f:
                    file_data = f.read()
                
                resp = requests.post(upload_endpoint, data=file_data, headers={**headers, "Content-Type": "image/jpeg", "x-upsert": "true"}, timeout=10)
                if resp.status_code in (200, 201):
                    uploaded_count += 1
            except Exception as e:
                print(f"[!] Upload error for {roll_no}: {e}")

        # Update local/Supabase DB photo_url
        try:
            cursor.execute("UPDATE students SET photo_url=? WHERE roll_no=?", (public_photo_url, roll_no))
            if cursor.rowcount > 0:
                updated_db_count += 1
        except Exception as e:
            print(f"[!] DB update error for {roll_no}: {e}")

    conn.commit()
    conn.close()

    print(f"[+] Processed {len(photo_files)} student photos.")
    print(f"[+] Updated {updated_db_count} student records in database with Supabase Storage photo URLs.")

if __name__ == "__main__":
    import sys
    key = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SUPABASE_KEY")
    upload_local_photos_to_supabase(key)
