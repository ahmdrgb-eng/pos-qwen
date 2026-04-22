from app import app, db
from database import User, Branch, Role, Book, BranchInventory
from flask_login import login_user

with app.app_context():
    print("🔧 بدء إصلاح المشاكل...\n")
    
    # 1. التأكد من وجود الفرع الرئيسي
    branch = Branch.query.filter_by(name='الفرع الرئيسي').first()
    if not branch:
        branch = Branch(
            name='الفرع الرئيسي',
            address='Dubai',
            phone='+971527241974',
            country='UAE',
            currency='درهم',
            exchange_rate=1.0,
            is_central=True,
            is_active=True
        )
        db.session.add(branch)
        db.session.flush()
        print("✅ تم إنشاء الفرع الرئيسي")
    else:
        print(f"✅ الفرع الرئيسي موجود: {branch.name}")
    
    # 2. التأكد من وجود دور المدير
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(name='admin')
        db.session.add(admin_role)
        db.session.flush()
        print("✅ تم إنشاء دور المدير")
    else:
        print(f"✅ دور المدير موجود")
    
    # 3. تحديث أو إنشاء المستخدم المدير
    admin_user = User.query.filter_by(username='admin').first()
    if admin_user:
        admin_user.role_id = admin_role.id
        admin_user.branch_id = branch.id
        admin_user.is_active = True
        db.session.flush()
        print(f"✅ تم تحديث المستخدم: {admin_user.full_name}")
        print(f"   - الدور: {admin_role.name}")
        print(f"   - الفرع: {branch.name}")
    else:
        admin_user = User(
            username='admin',
            password=User.hash_password('admin123'),
            full_name='المدير العام',
            email='admin@qindeel.com',
            role_id=admin_role.id,
            branch_id=branch.id,
            is_active=True
        )
        db.session.add(admin_user)
        db.session.flush()
        print("✅ تم إنشاء مستخدم مدير جديد")
    
    # 4. إضافة جميع الكتب لمخزون الفرع
    all_books = Book.query.filter_by(is_active=True).all()
    print(f"\n📚 عدد الكتب النشطة في قاعدة البيانات: {len(all_books)}")
    
    added_count = 0
    for book in all_books:
        inventory = BranchInventory.query.filter_by(
            branch_id=branch.id,
            book_id=book.id
        ).first()
        
        if not inventory:
            # إضافة الكتاب للمخزون بكمية 1 كحد أدنى
            new_inventory = BranchInventory(
                branch_id=branch.id,
                book_id=book.id,
                quantity=1,  # كمية افتراضية
                last_updated=db.func.now()
            )
            db.session.add(new_inventory)
            added_count += 1
    
    db.session.commit()
    
    print(f"✅ تم إضافة {added_count} كتاب لمخزون الفرع")
    print(f"📊 إجمالي الكتب المتاحة الآن: {len(all_books)}")
    
    # 5. عرض ملخص الإصلاح
    print("\n" + "="*50)
    print("🎉 تم الإصلاح بنجاح!")
    print("="*50)
    print("\n📝 بيانات الدخول المحدثة:")
    print(f"   👤 المستخدم: admin")
    print(f"   🔑 كلمة المرور: admin123")
    print(f"   🏢 الفرع: {branch.name}")
    print(f"   🔐 الصلاحية: {admin_role.name}")
    print(f"\n📚 الكتب المتاحة في نقطة البيع: {len(all_books)} كتاب")
    print("\n⚠️  خطوات مهمة بعد التشغيل:")
    print("   1. أغلق البرنامج تماماً")
    print("   2. امسح كاش المتصفح (Ctrl + Shift + Del)")
    print("   3. أعد تشغيل البرنامج: python app.py")
    print("   4. سجّل خروج ثم دخول مجدداً")
    print("   5. اضغط Ctrl + F5 لتحديث الصفحة")