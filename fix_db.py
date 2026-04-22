# fix_db.py - Simple database migration
import sqlite3
import os

# Find the database file
db_file = None
for path in ['instance/bookstore.db', 'bookstore.db', 'data/bookstore.db']:
    if os.path.exists(path):
        db_file = path
        break

if not db_file:
    print("ERROR: Could not find bookstore.db")
    print("Please check where your database file is located.")
    exit(1)

print(f"Found database: {db_file}")

try:
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Check current columns
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Current columns: {columns}")
    
    # Add last_seen if missing
    if 'last_seen' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN last_seen DATETIME")
        cursor.execute("UPDATE users SET last_seen = datetime('now')")
        conn.commit()
        print("SUCCESS: Added last_seen column and updated records")
    else:
        print("INFO: last_seen column already exists")
    
    conn.close()
    print("DONE: Database migration complete")
    
except Exception as e:
    print(f"ERROR: {e}")
    print("Try running this script as Administrator")