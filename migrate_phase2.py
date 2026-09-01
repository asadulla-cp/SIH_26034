"""
Migration script for Phase 2:
- Add anomaly_data (JSON) to inspections table
- Add detected_languages (JSON) to inspections table
- Create legal_notices table
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "metalex.db")

def run_migration():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Add anomaly_data to inspections if not exists
    cursor.execute("PRAGMA table_info(inspections);")
    columns = [col[1] for col in cursor.fetchall()]

    if "anomaly_data" not in columns:
        print("Adding anomaly_data column to inspections...")
        cursor.execute("ALTER TABLE inspections ADD COLUMN anomaly_data JSON;")
    else:
        print("anomaly_data column already exists.")

    if "detected_languages" not in columns:
        print("Adding detected_languages column to inspections...")
        cursor.execute("ALTER TABLE inspections ADD COLUMN detected_languages JSON;")
    else:
        print("detected_languages column already exists.")

    # Create legal_notices table if not exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS legal_notices (
        id VARCHAR PRIMARY KEY,
        notice_id VARCHAR UNIQUE NOT NULL,
        inspection_id VARCHAR NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
        manufacturer_name VARCHAR,
        manufacturer_email VARCHAR,
        total_penalty INTEGER DEFAULT 0,
        violations_summary JSON,
        status VARCHAR DEFAULT 'GENERATED',
        pdf_path VARCHAR,
        response_deadline DATETIME,
        sent_at DATETIME,
        created_at DATETIME
    );
    """)
    print("legal_notices table created / verified.")

    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    run_migration()
