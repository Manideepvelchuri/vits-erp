# VITS ERP — Streamlit Version

## Quick Start

```bash
pip install -r requirements.txt

# Optional env vars
export ADMIN_PASSWORD="your-password"
export PORTAL_USERNAME="848"
export PORTAL_PASSWORD="vits"

# Run
streamlit run streamlit_app.py
```

Opens automatically at http://localhost:8501

## Credentials
- Admin: `admin` / `vits@admin123`
- Student first login: `<roll>` / `vits123`

## Files Needed (copy from main project)
- `database.py`
- `harvester.py`
- `pdf_generator.py`

That's it! Just 3 files + this Streamlit app.

## Deploy Free
- Streamlit Cloud: https://share.streamlit.io
- Push code to GitHub, link the repo, done!
