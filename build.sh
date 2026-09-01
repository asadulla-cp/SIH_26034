#!/usr/bin/env bash
set -e

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Pre-downloading EasyOCR models (English + Hindi)..."
python3 -c "
import easyocr
print('Downloading English model...')
easyocr.Reader(['en'], gpu=False, verbose=True)
print('Downloading Hindi model...')
easyocr.Reader(['en', 'hi'], gpu=False, verbose=True)
print('EasyOCR models ready.')
"

echo "==> Build complete. frontend/dist is pre-built and committed to repo."
