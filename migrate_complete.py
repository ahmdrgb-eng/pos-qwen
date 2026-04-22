# migrate_complete.py
import sqlite3, os

DB_PATH = 'instance/bookstore.db'
if not os.path.exists(DB_PATH): DB_PATH = 'bookstore.db'
print(f"🔍 الترحيل الشامل: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 1️⃣ جدول branches
cur.execute("PRAGMA table_info(branches)")
cols = [c[1] for c in cur.fetchall()]
for col, sql in {
    'country': "ALTER TABLE branches ADD COLUMN country VARCHAR(100) DEFAULT 'UAE'",
    'currency': "ALTER TABLE branches ADD COLUMN currency VARCHAR(10) DEFAULT 'د.إ'",
    'exchange_rate': "ALTER TABLE branches ADD COLUMN exchange_rate FLOAT DEFAULT 1.0",
    'is_central': "ALTER TABLE branches ADD COLUMN is_central BOOLEAN DEFAULT 0"
}.items():
    if col not in cols: cur.execute(sql); print(f"✅ branches.{col}")

# 2️⃣ جدول invoices
cur.execute("PRAGMA table_info(invoices)")
cols = [c[1] for c in cur.fetchall()]
for col, sql in {
    'currency': "ALTER TABLE invoices ADD COLUMN currency VARCHAR(10) DEFAULT 'د.إ'",
    'exchange_rate': "ALTER TABLE invoices ADD COLUMN exchange_rate FLOAT DEFAULT 1.0"
}.items():
    if col not in cols: cur.execute(sql); print(f"✅ invoices.{col}")

# 3️⃣ جدول app_settings
cur.execute("PRAGMA table_info(app_settings)")
cols = [c[1] for c in cur.fetchall()]
if 'base_currency' not in cols:
    cur.execute("ALTER TABLE app_settings ADD COLUMN base_currency VARCHAR(10) DEFAULT 'د.إ'")
    print("✅ app_settings.base_currency")

# 4️⃣ إنشاء الجداول الجديدة
cur.execute("""CREATE TABLE IF NOT EXISTS central_warehouse (
    id INTEGER PRIMARY KEY, book_id INTEGER, quantity INTEGER DEFAULT 0,
    min_quantity INTEGER DEFAULT 10, last_updated DATETIME,
    FOREIGN KEY(book_id) REFERENCES books(id))""")
print("✅ central_warehouse")

cur.execute("""CREATE TABLE IF NOT EXISTS stock_transfers (
    id INTEGER PRIMARY KEY, transfer_number VARCHAR(50) UNIQUE,
    from_branch_id INTEGER, to_branch_id INTEGER, status VARCHAR(20) DEFAULT 'pending',
    requested_by INTEGER, approved_by INTEGER, shipped_at DATETIME,
    received_at DATETIME, notes TEXT, created_at DATETIME)""")
print("✅ stock_transfers")

cur.execute("""CREATE TABLE IF NOT EXISTS transfer_items (
    id INTEGER PRIMARY KEY, transfer_id INTEGER, book_id INTEGER,
    quantity INTEGER, received_quantity INTEGER DEFAULT 0)""")
print("✅ transfer_items")

cur.execute("UPDATE branches SET currency='د.إ', exchange_rate=1.0 WHERE currency IS NULL")
cur.execute("UPDATE invoices SET currency='د.إ', exchange_rate=1.0 WHERE currency IS NULL")
cur.execute("UPDATE app_settings SET base_currency='د.إ' WHERE base_currency IS NULL")

conn.commit()
conn.close()
print("🎉 اكتمل الترحيل الشامل بنجاح! 🚀")