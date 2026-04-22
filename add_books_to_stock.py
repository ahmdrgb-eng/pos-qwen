from app import app, db
from database import Book, Branch, BranchInventory

with app.app_context():
    # الحصول على الفرع الرئيسي
    branch = Branch.query.filter_by(name='الفرع الرئيسي', is_active=True).first()
    
    if not branch:
        print("❌ لم يتم العثور على الفرع الرئيسي!")
        print("جاري إنشاؤه...")
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
        db.session.commit()
    
    print(f"📍 الفرع: {branch.name} (ID: {branch.id})")
    
    # الحصول على جميع الكتب النشطة
    all_books = Book.query.filter_by(is_active=True).all()
    total_books = len(all_books)
    print(f"📚 عدد الكتب النشطة في قاعدة البيانات: {total_books}")
    
    if total_books == 0:
        print("⚠️  لا توجد كتب في قاعدة البيانات!")
        print("💡 أضف كتباً من صفحة 'الكتب' أو استورد من Excel")
        exit()
    
    # إضافة كل كتاب للمخزون
    added = 0
    updated = 0
    
    for book in all_books:
        inventory = BranchInventory.query.filter_by(
            branch_id=branch.id, 
            book_id=book.id
        ).first()
        
        if not inventory:
            # إنشاء مخزون جديد بكمية 10 كحد أدنى
            new_inventory = BranchInventory(
                branch_id=branch.id,
                book_id=book.id,
                quantity=10,
                last_updated=db.func.now()
            )
            db.session.add(new_inventory)
            added += 1
            print(f"  ✅ أضيف: {book.title[:50]}")
        else:
            # تحديث الكمية إذا كانت صفر أو أقل
            if inventory.quantity <= 0:
                inventory.quantity = 10
                inventory.last_updated = db.func.now()
                updated += 1
    
    db.session.commit()
    
    print("\n" + "="*60)
    print("✅ تم الانتهاء بنجاح!")
    print("="*60)
    print(f"📥 كتب أضيفت للمخزون: {added}")
    print(f"🔄 كتب تم تحديث كميتها: {updated}")
    print(f"📊 إجمالي الكتب المتاحة الآن: {total_books}")
    print(f"\n🎯 الآن يمكنك رؤية {total_books} كتاب في نقطة البيع!")
    print("\n⚠️  خطوات مهمة:")
    print("   1. أعد تشغيل السيرفر: python app.py")
    print("   2. امسح كاش المتصفح: Ctrl + Shift + Del")
    print("   3. افتح نقطة البيع وستجد جميع الكتب")