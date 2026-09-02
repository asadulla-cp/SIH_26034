#!/usr/bin/env bash
# MetaLex Prototype Launcher
# Smart India Hackathon 2026

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "============================================================"
echo "⚖️  MetaLex — Legal Metrology Compliance Checking System"
echo "   Smart India Hackathon Prototype (36-Hour Edition)"
echo "============================================================"

# Ensure directories exist
mkdir -p uploads annotated reports

# Check Python environment
echo "🔍 Checking Python dependencies..."
python3 -c "import fastapi, uvicorn, reportlab, PIL, cv2" 2>/dev/null || {
  echo "📦 Installing required Python dependencies..."
  pip3 install fastapi uvicorn reportlab pillow opencv-python sqlalchemy pydantic easyocr python-multipart aiofiles jinja2
}

# Start Backend Server in background
echo "🚀 Starting FastAPI Backend Server on port 8000..."
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Trap signals to clean up background processes
trap "kill $BACKEND_PID 2>/dev/null; exit" SIGINT SIGTERM EXIT

# Start Frontend Dev Server
echo "🌐 Starting Vite Frontend on port 5173..."
cd "$DIR/frontend"
npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM EXIT

echo ""
echo "============================================================"
echo "✅ MetaLex is running!"
echo "   Frontend Web Application: http://localhost:5173"
echo "   Backend REST API & Docs:  http://localhost:8000/docs"
echo "   Sample Test Images:       $DIR/demo/sample_images/"
echo "============================================================"
echo "Press Ctrl+C to stop all servers."
echo ""

wait
