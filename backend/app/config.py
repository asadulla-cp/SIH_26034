from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "backend" / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
REPORT_DIR = DATA_DIR / "reports"
DB_PATH = DATA_DIR / "metalex.db"
RULES_PATH = ROOT / "rules" / "rules.json"
DEMO_DIR = ROOT / "demo"
SAMPLES_PATH = DEMO_DIR / "samples.json"

MAX_UPLOAD_MB = 12
MAX_IMAGE_PX = 4000
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
