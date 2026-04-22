# migrate_settings.py - إضافة عمود base_currency للإعدادات
import sqlite3, os

DB_PATH = 'instance/bookstore.db'
if not os.path.exists(DB_PATH):
    DB_PATH = 'bookstore.db'

print(f"🔍 ترحيل جدول app_settings في: {DB_PATH}")

if not os.path.exists(DB_PATH):
    print("❌ قاعدة البيانات غير موجودة")
    exit(1)

try:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # التحقق من الأعمدة الحالية
    cur.execute("PRAGMA table_info(app_settings)")
    cols = [c[1] for c in cur.fetchall()]
    print(f"✅ الأعمدة الحالية: {cols}")
    
    # إضافة العمود الناقص
    if 'base_currency' not in cols:
        cur.execute("ALTER TABLE app_settings ADD COLUMN base_currency VARCHAR(10) DEFAULT 'د.إ'")
        print("✅ تمت إضافة: base_currency")
    else:
        print("⚠️ العمود base_currency موجود مسبقاً")
    
    # تحديث القيمة الافتراضية
    cur.execute("UPDATE app_settings SET base_currency='د.إ' WHERE base_currency IS NULL")
    
    conn.commit()
    print("🎉 تم ترحيل جدول app_settings بنجاح!")
    
except Exception as e:
    print(f"❌ خطأ: {e}")
    conn.rollback()
finally:
    conn.close()
    print("🔒 تم الإغلاق")