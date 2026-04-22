# migrate_invoices.py - إضافة أعمدة العملات للفواتير
import sqlite3
import os

DB_PATH = 'instance/bookstore.db'
if not os.path.exists(DB_PATH):
    DB_PATH = 'bookstore.db'

print(f"🔍 ترحيل جدول invoices في: {DB_PATH}")

if not os.path.exists(DB_PATH):
    print("❌ قاعدة البيانات غير موجودة")
    exit(1)

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # التحقق من الأعمدة الحالية
    cursor.execute("PRAGMA table_info(invoices)")
    existing_cols = [col[1] for col in cursor.fetchall()]
    print(f"✅ الأعمدة الحالية: {existing_cols}")
    
    # الأعمدة الجديدة المطلوب إضافتها
    new_columns = {
        'currency': "ALTER TABLE invoices ADD COLUMN currency VARCHAR(10) DEFAULT 'د.إ'",
        'exchange_rate': "ALTER TABLE invoices ADD COLUMN exchange_rate FLOAT DEFAULT 1.0"
    }
    
    # إضافة الأعمدة الناقصة
    for col_name, sql_cmd in new_columns.items():
        if col_name not in existing_cols:
            cursor.execute(sql_cmd)
            print(f"✅ تمت إضافة العمود: {col_name}")
        else:
            print(f"⚠️ العمود {col_name} موجود مسبقاً")
    
    # تحديث الفواتير القديمة بقيم افتراضية
    cursor.execute("UPDATE invoices SET currency='د.إ', exchange_rate=1.0 WHERE currency IS NULL")
    
    conn.commit()
    print("🎉 تم ترحيل جدول invoices بنجاح!")
    
except Exception as e:
    print(f"❌ خطأ: {e}")
    conn.rollback()
finally:
    conn.close()
    print("🔒 تم الإغلاق")