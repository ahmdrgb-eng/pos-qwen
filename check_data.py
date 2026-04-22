from app import app, db
from database import Book, Branch, BranchInventory, User

with app.app_context():
    print("="*60)
    print("📊 تقرير حالة قاعدة البيانات")
    print("="*60)
    
    # عدد الكتب
    books_count = Book.query.count()
    print(f"📚 إجمالي الكتب: {books_count}")
    
    # عدد الفروع
    branches = Branch.query.all()
    print(f"🏢 عدد الفروع: {len(branches)}")
    for b in branches:
        print(f"   - {b.name} (ID: {b.id})")
    
    # عدد المستخدمين
    users = User.query.all()
    print(f"👥 عدد المستخدمين: {len(users)}")
    for u in users:
        print(f"   - {u.username} | الدور: {u.role} | الفرع: {u.branch_id}")
    
    # الكتب مع المخزون
    if books_count > 0:
        branch = Branch.query.first()
        if branch:
            books_with_stock = BranchInventory.query.filter_by(branch_id=branch.id).count()
            print(f"📦 كتب في مخزون '{branch.name}': {books_with_stock}")
        else:
            print("⚠️  لا يوجد فرع!")
    
    print("="*60)