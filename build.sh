#!/usr/bin/env bash
set -e

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Pre-downloading EasyOCR models into .easyocr_models/ ..."
python3 -c "
import os, ssl, easyocr
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass
model_dir = os.path.join(os.path.dirname(os.path.abspath('.')), 'src', '.easyocr_models')
os.makedirs(model_dir, exist_ok=True)
print(f'Model dir: {model_dir}')
print('Downloading English + Hindi models...')
easyocr.Reader(['en', 'hi'], gpu=False, verbose=True, model_storage_directory=model_dir)
print('EasyOCR models cached successfully.')
"

echo "==> Build complete. frontend/dist is pre-built and committed to repo."
