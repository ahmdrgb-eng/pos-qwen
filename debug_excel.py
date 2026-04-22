import pandas as pd

file_path = 'D:\POS QWEN\ss.xlsx'  # ضع مسار ملفك هنا
df = pd.read_excel(file_path)

print("="*60)
print("📋 أسماء الأعمدة في الملف:")
print("="*60)
for i, col in enumerate(df.columns):
    print(f"{i+1}. '{col}'")

print("\n" + "="*60)
print("📊 عينة من البيانات (الصف الأول):")
print("="*60)
first_row = df.iloc[0]
for col in df.columns:
    value = first_row[col]
    print(f"{col}: '{value}' (type: {type(value).__name__})")

print("\n" + "="*60)
print("🔍 التحقق من أعمدة المؤلف/الناشر/التصنيف:")
print("="*60)
author_cols = [c for c in df.columns if 'author' in c.lower() or 'مؤلف' in c]
publisher_cols = [c for c in df.columns if 'publisher' in c.lower() or 'ناشر' in c]
category_cols = [c for c in df.columns if 'category' in c.lower() or 'تصنيف' in c or 'فئة' in c]

print(f"أعمدة المؤلف: {author_cols}")
print(f"أعمدة الناشر: {publisher_cols}")
print(f"أعمدة التصنيف: {category_cols}")