#!/bin/bash
set -e
cd "$(dirname "$0")"

export PYTHONPATH="$PWD/backend"
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./channelforge.db}"
export CORS_ORIGINS="${CORS_ORIGINS:-http://127.0.0.1:3000,http://localhost:3000}"

python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend &
API_PID=$!

cd frontend
if [ ! -d node_modules ]; then
  npm install
fi
npm run dev -- -p 3000
