#!/usr/bin/env python3
"""
Database Migration: Add user_id to inspections table
Links inspections to users who performed them.
"""
import sqlite3
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def migrate():
    db_path = PROJECT_ROOT / "metalex.db"
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        print("   Run the backend first to create the database.")
        return False
    
    print(f"🔄 Migrating database: {db_path}")
    print()
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if user_id column already exists
        cursor.execute("PRAGMA table_info(inspections)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "user_id" in columns:
            print("✅ Migration already applied - user_id column exists")
            return True
        
        print("📝 Adding user_id column to inspections table...")
        
        # Add user_id column (nullable for backward compatibility)
        cursor.execute("""
            ALTER TABLE inspections 
            ADD COLUMN user_id VARCHAR
        """)
        
        conn.commit()
        print("✅ Successfully added user_id column")
        
        # Get count of inspections
        cursor.execute("SELECT COUNT(*) FROM inspections")
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"📊 Found {count} existing inspection(s)")
            print("   Note: Existing inspections have user_id=NULL (no user tracking)")
            print("   New inspections will automatically track the user who performed them.")
        
        print()
        print("✅ Migration complete!")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("  MetaLex Database Migration")
    print("  Add User Tracking to Inspections")
    print("=" * 60)
    print()
    
    success = migrate()
    
    if success:
        print()
        print("🎯 Next Steps:")
        print("   1. Restart backend: pkill -f uvicorn && python3 -m uvicorn backend.main:app --reload")
        print("   2. New inspections will automatically be linked to logged-in users")
        print("   3. Users can view their own inspection history")
        sys.exit(0)
    else:
        print()
        print("❌ Migration failed. Please check the errors above.")
        sys.exit(1)
