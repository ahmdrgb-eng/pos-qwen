from app import app, db
from database import Book, Branch, BranchInventory

with app.app_context():
    # الحصول على الفرع الرئيسي
    branch = Branch.query.filter_by(name='الفرع الرئيسي', is_active=True).first()
    
    if not branch:
        print("❌ لم يتم العثور على الفرع الرئيسي!")
        exit()
    
    print(f"📍 الفرع: {branch.name} (ID: {branch.id})")
    
    # الحصول على جميع الكتب النشطة
    all_books = Book.query.filter_by(is_active=True).all()
    total_books = len(all_books)
    print(f"📚 عدد الكتب النشطة: {total_books}")
    
    # إضافة كل كتاب للمخزون إذا لم يكن موجوداً
    added = 0
    updated = 0
    skipped = 0
    
    for book in all_books:
        inventory = BranchInventory.query.filter_by(
            branch_id=branch.id, 
            book_id=book.id
        ).first()
        
        if not inventory:
            # إنشاء مخزون جديد بكمية افتراضية (5)
            new_inventory = BranchInventory(
                branch_id=branch.id,
                book_id=book.id,
                quantity=5,  # يمكنك تغيير الكمية الافتراضية هنا
                last_updated=db.func.now()
            )
            db.session.add(new_inventory)
            added += 1
        else:
            # تحديث الكمية إذا كانت صفر أو أقل
            if inventory.quantity <= 0:
                inventory.quantity = 5
                inventory.last_updated = db.func.now()
                updated += 1
            else:
                skipped += 1
    
    db.session.commit()
    
    print("\n✅ تم الانتهاء بنجاح!")
    print(f"   📥 كتب أضيفت للمخزون: {added}")
    print(f"   🔄 كتب تم تحديث كميتها: {updated}")
    print(f"   ⏭️  كتب موجودة مسبقاً: {skipped}")
    print(f"\n🎯 الآن يمكنك رؤية {total_books} كتاب في نقطة البيع!")