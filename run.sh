#!/bin/bash
# Quick start script
export ADMIN_PASSWORD="${ADMIN_PASSWORD:-vits@admin123}"
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
