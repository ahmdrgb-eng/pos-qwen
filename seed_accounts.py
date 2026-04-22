# seed_accounts.py - تعبئة تلقائية وآمنة لشجرة الحسابات
from app import app, db
from database import Account

# هيكل محاسبي قياسي مصمم خصيصاً للمكتبات وتجارة التجزئة
ACCOUNTS_DATA = [
    # 1️⃣ الأصول (Assets)
    {"code": "1000", "name": "الأصول المتداولة", "account_type": "asset"},
    {"code": "1100", "name": "الصندوق / الخزينة", "account_type": "asset", "parent_code": "1000"},
    {"code": "1200", "name": "البنك", "account_type": "asset", "parent_code": "1000"},
    {"code": "1300", "name": "المخزون", "account_type": "asset", "parent_code": "1000"},
    {"code": "1400", "name": "ديون العملاء (ذمم مدينة)", "account_type": "asset", "parent_code": "1000"},
    {"code": "1500", "name": "الأصول الثابتة", "account_type": "asset"},
    {"code": "1510", "name": "أثاث ومعدات", "account_type": "asset", "parent_code": "1500"},

    # 2️⃣ الخصوم (Liabilities)
    {"code": "2000", "name": "الخصوم المتداولة", "account_type": "liability"},
    {"code": "2100", "name": "ديون الموردين (ذمم دائنة)", "account_type": "liability", "parent_code": "2000"},
    {"code": "2200", "name": "الضرائب المستحقة", "account_type": "liability", "parent_code": "2000"},
    {"code": "2300", "name": "رواتب مستحقة", "account_type": "liability", "parent_code": "2000"},

    # 3️⃣ حقوق الملكية (Equity)
    {"code": "3000", "name": "رأس المال", "account_type": "equity"},
    {"code": "3100", "name": "الأرباح المحتجزة", "account_type": "equity"},
    {"code": "3200", "name": "مسحوبات المالك", "account_type": "equity"},

    # 4️⃣ الإيرادات (Revenue)
    {"code": "4000", "name": "إيرادات المبيعات", "account_type": "revenue"},
    {"code": "4100", "name": "إيرادات خدمات أخرى", "account_type": "revenue"},
    {"code": "4200", "name": "خصومات مبيعات", "account_type": "revenue"},

    # 5️⃣ المصروفات (Expenses)
    {"code": "5000", "name": "تكلفة البضاعة المباعة (COGS)", "account_type": "expense"},
    {"code": "5100", "name": "مصروفات التشغيل", "account_type": "expense"},
    {"code": "5110", "name": "إيجار المحل", "account_type": "expense", "parent_code": "5100"},
    {"code": "5120", "name": "رواتب وأجور", "account_type": "expense", "parent_code": "5100"},
    {"code": "5130", "name": "مرافق (كهرباء/ماء/إنترنت)", "account_type": "expense", "parent_code": "5100"},
    {"code": "5140", "name": "نقل وتوصيل", "account_type": "expense", "parent_code": "5100"},
    {"code": "5150", "name": "صيانة وإصلاحات", "account_type": "expense", "parent_code": "5100"},
    {"code": "5160", "name": "دعاية وإعلان", "account_type": "expense", "parent_code": "5100"},
    {"code": "5170", "name": "مصاريف إدارية وعمومية", "account_type": "expense", "parent_code": "5100"},
    {"code": "5200", "name": "مصروفات مالية", "account_type": "expense"},
    {"code": "5210", "name": "عمولات بنكية", "account_type": "expense", "parent_code": "5200"},
    {"code": "5220", "name": "فروقات صرف", "account_type": "expense", "parent_code": "5200"},
]

def seed_accounts():
    with app.app_context():
        # خريطة للبحث السريع عن الحسابات عبر الكود
        code_map = {}
        
        # المرحلة 1: إضافة الحسابات غير الموجودة
        for data in ACCOUNTS_DATA:
            if not Account.query.filter_by(code=data['code']).first():
                acc = Account(code=data['code'], name=data['name'], account_type=data['account_type'], parent_id=None)
                db.session.add(acc)
                code_map[data['code']] = acc
        
        db.session.flush() # الحصول على IDs الجديدة
        
        # تحديث الخريطة بالحسابات الموجودة فعلياً في القاعدة
        for acc in Account.query.all():
            code_map[acc.code] = acc
            
        # المرحلة 2: ربط الحسابات الفرعية بآبائها
        linked = 0
        for data in ACCOUNTS_DATA:
            acc = code_map.get(data['code'])
            if acc and data.get('parent_code') and acc.parent_id is None:
                parent = code_map.get(data['parent_code'])
                if parent:
                    acc.parent_id = parent.id
                    linked += 1
        
        db.session.commit()
        print(f"✅ تم تهيئة شجرة الحسابات بنجاح! ({len(ACCOUNTS_DATA)} حساب)")
        if linked > 0:
            print(f"🔗 تم ربط {linked} حساب فرعي بحساباته الرئيسية تلقائياً.")

if __name__ == '__main__':
    seed_accounts()