#!/usr/bin/env python3
"""Initialize SQLite schema (create_all). Optional: python -m app.main not required."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.db import Base, ensure_dirs, get_engine  # noqa: E402
from app.models import *  # noqa: F401,E402

if __name__ == "__main__":
    ensure_dirs()
    Base.metadata.create_all(get_engine())
    print("SQLite schema ready at backend/data/metalex.db")
