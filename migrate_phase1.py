#!/usr/bin/env python3
"""
Migration script for Phase 1 MetaLex enhancements:
- Add severity_score, risk_level, latitude, longitude, barcode_data to inspections
- Add font_size_mm, min_font_size_mm to extracted_fields
- Add severity_points to violations
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("/Users/namangaur/SIH_26034/metalex.db")

def migrate():
    if not DB_PATH.exists():
        print("metalex.db does not exist yet. It will be initialized on first run.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    columns_to_add = [
        ("inspections", "severity_score", "FLOAT DEFAULT 0.0"),
        ("inspections", "risk_level", "VARCHAR DEFAULT 'low'"),
        ("inspections", "latitude", "FLOAT"),
        ("inspections", "longitude", "FLOAT"),
        ("inspections", "barcode_data", "JSON"),
        ("extracted_fields", "font_size_mm", "FLOAT"),
        ("extracted_fields", "min_font_size_mm", "FLOAT"),
        ("violations", "severity_points", "INTEGER DEFAULT 5"),
    ]

    for table, col, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};")
            print(f"Added column {col} to {table}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Column {col} already exists in {table}")
            else:
                print(f"Note on {table}.{col}: {e}")

    conn.commit()
    conn.close()
    print("Database migration completed successfully.")

if __name__ == "__main__":
    migrate()
