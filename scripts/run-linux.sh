#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
command -v python3 >/dev/null || { echo "Cần Python 3"; exit 1; }
command -v node >/dev/null || { echo "Cần Node.js 20+"; exit 1; }
cd "$ROOT"; python3 -m venv .venv; source .venv/bin/activate; pip install -r backend/requirements.txt
echo "Backend: source .venv/bin/activate && cd backend && uvicorn app.main:app --reload"
echo "Frontend: cd frontend && npm install && npm run dev"
