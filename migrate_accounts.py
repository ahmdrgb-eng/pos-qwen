import sqlite3, os
DB = 'instance/bookstore.db' if os.path.exists('instance/bookstore.db') else 'bookstore.db'
conn = sqlite3.connect(DB); cur = conn.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
    account_type TEXT NOT NULL, parent_id INTEGER, is_active BOOLEAN DEFAULT 1,
    created_at DATETIME, FOREIGN KEY(parent_id) REFERENCES accounts(id))''')
cur.execute('''CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL, branch_id INTEGER NOT NULL,
    amount REAL NOT NULL, description TEXT, expense_date DATETIME,
    created_by INTEGER, created_at DATETIME,
    FOREIGN KEY(account_id) REFERENCES accounts(id),
    FOREIGN KEY(branch_id) REFERENCES branches(id),
    FOREIGN KEY(created_by) REFERENCES users(id))''')
# إضافة حسابات افتراضية إذا كانت الجدول فارغاً
if cur.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0:
    defaults = [
        ('5001', 'إيجار المحل', 'expense', None), ('5002', 'رواتب الموظفين', 'expense', None),
        ('5003', 'كهرباء ومياه', 'expense', None), ('5004', 'نقل ومواصلات', 'expense', None),
        ('5005', 'صيانة وإصلاحات', 'expense', None), ('5006', 'مصاريف إدارية متنوعة', 'expense', None)
    ]
    cur.executemany("INSERT INTO accounts(code,name,account_type,parent_id) VALUES(?,?,?,?)", defaults)
conn.commit(); conn.close()
print("✅ تم إنشاء جداول الحسابات والمصروفات والحسابات الافتراضية بنجاح!")