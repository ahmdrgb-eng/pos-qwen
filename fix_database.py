from app import app, db
from database import User, Branch, Role, Book, BranchInventory

with app.app_context():
    # 1. التأكد من وجود الفرع الرئيسي
    branch = Branch.query.filter_by(name='الفرع الرئيسي').first()
    if not branch:
        branch = Branch(
            name='الفرع الرئيسي',
            address='Dubai',
            phone='000',
            country='UAE',
            currency='د.إ',
            exchange_rate=1.0,
            is_central=True,
            is_active=True
        )
        db.session.add(branch)
        db.session.flush()
        print("✅ تم إنشاء الفرع الرئيسي")
    
    # 2. التأكد من وجود دور المدير
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(name='admin')
        db.session.add(admin_role)
        db.session.flush()
        print("✅ تم إنشاء دور المدير")
    
    # 3. تحديث المستخدم المدير
    admin_user = User.query.filter_by(username='admin').first()
    if admin_user:
        admin_user.role_id = admin_role.id
        admin_user.branch_id = branch.id
        admin_user.is_active = True
        print(f"✅ تم تحديث المستخدم: {admin_user.full_name}")
    else:
        # إنشاء مستخدم مدير جديد
        admin_user = User(
            username='admin',
            password=User.hash_password('admin123'),
            full_name='المدير العام',
            email='admin@store.com',
            role_id=admin_role.id,
            branch_id=branch.id,
            is_active=True
        )
        db.session.add(admin_user)
        print("✅ تم إنشاء مستخدم مدير جديد")
    
    # 4. التأكد من وجود كتب في المخزون
    books_count = Book.query.count()
    if books_count == 0:
        # إنشاء كتاب تجريبي
        book = Book(
            isbn='97899948350026',
            title='كتاب تجريبي - نقطة البيع',
            cost_price=50.0,
            selling_price=100.0,
            is_active=True
        )
        db.session.add(book)
        db.session.flush()
        
        # إضافة الكتاب للمخزون
        inventory = BranchInventory(
            branch_id=branch.id,
            book_id=book.id,
            quantity=10
        )
        db.session.add(inventory)
        print("✅ تم إنشاء كتاب تجريبي وإضافته للمخزون")
    else:
        # التأكد من أن الكتب الموجودة في المخزون
        all_books = Book.query.filter_by(is_active=True).all()
        for book in all_books:
            inv = BranchInventory.query.filter_by(branch_id=branch.id, book_id=book.id).first()
            if not inv:
                inv = BranchInventory(branch_id=branch.id, book_id=book.id, quantity=5)
                db.session.add(inv)
        print(f"✅ تم تحديث مخزون {books_count} كتاب")
    
    db.session.commit()
    print("\n🎉 تم الإصلاح بنجاح!")
    print(f"📝 بيانات الدخول:")
    print(f"   المستخدم: admin")
    print(f"   كلمة المرور: admin123")
    print(f"   الفرع: {branch.name}")