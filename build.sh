#!/usr/bin/env bash
set -e

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Installing Node.js and building frontend..."
# Render provides Node.js — build the React frontend into frontend/dist
cd frontend
npm install
npm run build
cd ..

echo "==> Build complete. frontend/dist is ready."
