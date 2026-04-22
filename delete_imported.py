from app import app, db
from database import Book, BranchInventory
import pandas as pd

with app.app_context():
    # D:\POS QWEN\
    file_path = 'ss.xlsx' 
    df = pd.read_excel(file_path)
    
    isbn_list = df['ISBN'].dropna().astype(str).tolist()
    title_list = df['Title'].dropna().astype(str).tolist()
    
    print(f"🔍 جاري البحث عن {len(isbn_list)} كتاب لحذفها...")
    
    # حذف الكتب المطابقة
    query = Book.query.filter(
        (Book.isbn.in_(isbn_list)) | (Book.title.in_(title_list))
    )
    count = query.count()
    query.delete(synchronize_session=False)
    
    db.session.commit()
    print(f"✅ تم حذف {count} كتاب مستورد من قاعدة البيانات.")