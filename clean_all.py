from app import app, db
from database import Book, BranchInventory, Author, Publisher, Category

with app.app_context():
    print("⚠️ جاري تنظيف قاعدة البيانات...")
    BranchInventory.query.delete()
    Book.query.delete()
    Author.query.delete()
    Publisher.query.delete()
    Category.query.delete()
    db.session.commit()
    print("✅ تم التنظيف بنجاح! النظام جاهز للاستيراد الجديد.")