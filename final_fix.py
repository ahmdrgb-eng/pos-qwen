import sqlite3
import os
import glob
from werkzeug.security import generate_password_hash

# البحث التلقائي عن قاعدة البيانات (تستبعد مجلد venv)
db_files = [f for f in glob.glob("**/*.db", recursive=True) if 'venv' not in f and '__pycache__' not in f]

if not db_files:
    print("❌ لم يتم العثور على قاعدة بيانات SQLite!")
    print("💡 تأكد من تشغيل الأمر: dir /s /b *.db")
    exit()

DB_FILE = db_files[0]
print(f"🔍 تم العثور على قاعدة البيانات: {DB_FILE}")
print("🔧 جاري إصلاح البيانات وربط المستخدمين والكتب...\n")

conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# 1. ضمان وجود جداول الأدوار والفروع
c.execute("""CREATE TABLE IF NOT EXISTS role (
    id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL)""")
c.execute("""CREATE TABLE IF NOT EXISTS branch (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, address TEXT, phone TEXT,
    country TEXT DEFAULT 'UAE', currency TEXT DEFAULT 'د.إ',
    exchange_rate REAL DEFAULT 1.0, is_central BOOLEAN DEFAULT 0, is_active BOOLEAN DEFAULT 1)""")

c.execute("INSERT OR IGNORE INTO role (id, name) VALUES (1, 'admin')")
c.execute("INSERT OR IGNORE INTO role (id, name) VALUES (2, 'manager')")
c.execute("INSERT OR IGNORE INTO role (id, name) VALUES (3, 'cashier')")
c.execute("INSERT OR IGNORE INTO branch (id, name, address, phone, is_central, is_active) VALUES (1, 'الفرع الرئيسي', 'Dubai', '+971527241974', 1, 1)")

# 2. إصلاح جدول المستخدمين وإضافة الأعمدة الناقصة
c.execute("PRAGMA table_info(user)")
cols = [row[1] for row in c.fetchall()]
if 'role_id' not in cols: c.execute("ALTER TABLE user ADD COLUMN role_id INTEGER")
if 'branch_id' not in cols: c.execute("ALTER TABLE user ADD COLUMN branch_id INTEGER")

# تحديث المدير العام وربطه بالفرع والدور
admin_pass = generate_password_hash('admin123')
c.execute("""INSERT OR IGNORE INTO user 
    (id, username, password, full_name, email, role_id, branch_id, is_active)
    VALUES (1, 'admin', ?, 'المدير العام', 'admin@store.com', 1, 1, 1)""", (admin_pass,))
c.execute("UPDATE user SET role_id=1, branch_id=1, is_active=1 WHERE username='admin'")

# 3. ربط جميع الكتب النشطة بمخزون الفرع الرئيسي
c.execute("""INSERT OR IGNORE INTO branch_inventory (branch_id, book_id, quantity)
    SELECT 1, id, 5 FROM book WHERE is_active=1
    AND id NOT IN (SELECT book_id FROM branch_inventory WHERE branch_id=1)""")

conn.commit()
conn.close()

print("✅ تم إصلاح قاعدة البيانات بنجاح!")
print("📌 الخطوات الأخيرة (مهمة جداً):")
print("   1. أغلق السيرفر إذا كان يعمل (Ctrl+C)")
print("   2. امسح كاش المتصفح والكوكيز تماماً (Ctrl+Shift+Del)")
print("   3. شغّل السيرفر: python app.py")
print("   4. افتح الرابط واذهب لـ /logout أولاً")
print("   5. سجّل دخول جديد بـ admin / admin123")