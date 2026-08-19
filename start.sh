#!/bin/sh
# Launches backend (FastAPI, internal port 8000) and frontend (Streamlit, public $PORT)
# in a single container so both share one Render instance's hour allowance.
set -e

uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

echo "Waiting for backend to become healthy..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "Backend healthy after ${i}s."
        break
    fi
    sleep 1
done

exec streamlit run app.py --server.port "${PORT:-8501}" --server.address 0.0.0.0 --server.headless true
