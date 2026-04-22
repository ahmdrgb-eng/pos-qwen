import sqlite3
import os

# البحث عن قاعدة البيانات
db_file = 'bookstore.db'
if not os.path.exists(db_file) and os.path.exists('instance/bookstore.db'):
    db_file = 'instance/bookstore.db'

if not os.path.exists(db_file):
    print("❌ قاعدة البيانات غير موجودة!")
    exit()

print(f"🔧 جاري إصلاح عمود المستخدم في: {db_file}")
conn = sqlite3.connect(db_file)
c = conn.cursor()

# التحقق من الأعمدة الحالية في جدول user
c.execute("PRAGMA table_info(user)")
cols = [row[1] for row in c.fetchall()]
print(f"📋 الأعمدة الحالية: {cols}")

# إذا كان هناك role_id نضيف عمود role النصي
if 'role_id' in cols and 'role' not in cols:
    c.execute("ALTER TABLE user ADD COLUMN role TEXT DEFAULT 'cashier'")
    
    # نسخ الأدوار من جدول role إذا كان موجوداً
    try:
        c.execute("""
            UPDATE user 
            SET role = (SELECT name FROM role WHERE role.id = user.role_id)
            WHERE user.role_id IS NOT NULL
        """)
        print("✅ تم نقل الأدوار من role_id إلى role")
    except:
        print("⚠️ جدول الأدوار غير موجود، تم تعيين 'cashier' كافتراضي")
    
    conn.commit()
    print("✅ تم إصلاح قاعدة البيانات بنجاح!")
elif 'role' in cols:
    print("✅ عمود role موجود بالفعل، لا حاجة للإصلاح")
else:
    print("⚠️ هيكل جدول المستخدم غير متوقع")

conn.close()
print("\n🚀 الآن شغّل: python app.py")