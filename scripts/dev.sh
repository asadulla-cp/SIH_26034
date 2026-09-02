#!/bin/zsh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r backend/requirements.txt
fi
.venv/bin/python demo/generate_samples.py
cd "$ROOT/frontend"
if [ ! -d node_modules ]; then npm install; fi
cd "$ROOT"
# backend
PYTHONPATH="$ROOT/backend" "$ROOT/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000 --app-dir "$ROOT/backend" &
BACK_PID=$!
# frontend
cd "$ROOT/frontend"
npm run dev -- --host 127.0.0.1 --port 5173 &
FRONT_PID=$!
echo "MetaLex backend  http://127.0.0.1:8000/docs"
echo "MetaLex UI       http://127.0.0.1:5173"
echo "PIDs $BACK_PID $FRONT_PID  (Ctrl+C to stop this script does not kill children — kill those PIDs if needed)"
wait
