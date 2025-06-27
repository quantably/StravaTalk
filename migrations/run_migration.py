#!/usr/bin/env python3
"""
Database migration runner for StravaTalk authentication system.
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def run_migration(migration_file):
    """Run a SQL migration file."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return False
    
    try:
        # Read migration file
        migration_path = os.path.join(os.path.dirname(__file__), migration_file)
        with open(migration_path, 'r') as f:
            sql_content = f.read()
        
        # Connect to database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Execute migration
        print(f"🚀 Running migration: {migration_file}")
        cursor.execute(sql_content)
        conn.commit()
        
        print("✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def main():
    """Run all migrations or a specific one."""
    if len(sys.argv) > 1:
        migration_file = sys.argv[1]
        run_migration(migration_file)
    else:
        # Run all migrations in order
        migrations = [
            "001_create_auth_tables.sql"
        ]
        
        for migration in migrations:
            if not run_migration(migration):
                print(f"❌ Stopping due to failed migration: {migration}")
                sys.exit(1)
        
        print("🎉 All migrations completed successfully!")

if __name__ == "__main__":
    main()