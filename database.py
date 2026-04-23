from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# ===================== المستخدمون =====================
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    role = db.Column(db.String(50), default='cashier')
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    is_active = db.Column(db.Boolean, default=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def hash_password(password):
        return generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

# ===================== الفروع =====================
class Branch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    country = db.Column(db.String(50), default='UAE')
    currency = db.Column(db.String(10), default='د.إ')
    exchange_rate = db.Column(db.Float, default=1.0)
    is_central = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

# ===================== المؤلفون والناشرون والفئات =====================
class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    nationality = db.Column(db.String(100))

class Publisher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(100))

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)

# ===================== الكتب (نظيف 100%) =====================
class Book(db.Model):
    __tablename__ = 'book'
    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(50), unique=True)
    title = db.Column(db.String(200), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('author.id'))
    publisher_id = db.Column(db.Integer, db.ForeignKey('publisher.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    description = db.Column(db.Text)
    pages = db.Column(db.Integer)
    cost_price = db.Column(db.Float, default=0.0)
    selling_price = db.Column(db.Float, default=0.0)
    discount_percent = db.Column(db.Float, default=0.0)
    publication_year = db.Column(db.Integer)
    edition = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    
    # ✅ العلاقات فقط (لا توجد أعمدة إضافية)
    author = db.relationship('Author', backref='books', lazy=True)
    publisher = db.relationship('Publisher', backref='books', lazy=True)
    category = db.relationship('Category', backref='books', lazy=True)

# ===================== المخزون (فقط هنا توجد الكمية والفرع) =====================
class BranchInventory(db.Model):
    __tablename__ = 'branch_inventory'
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    quantity = db.Column(db.Integer)
    movement_type = db.Column(db.String(50))
    reference = db.Column(db.String(100))
    notes = db.Column(db.String(200))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ===================== العملاء والفواتير =====================
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(100))
    address = db.Column(db.String(200))
    national_id = db.Column(db.String(50))
    total_purchases = db.Column(db.Float, default=0.0)
    loyalty_points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    cashier_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    subtotal = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    paid_amount = db.Column(db.Float, default=0.0)
    payment_method = db.Column(db.String(50), default='cash')
    status = db.Column(db.String(20), default='completed')
    currency = db.Column(db.String(10), default='د.إ')
    exchange_rate = db.Column(db.Float, default=1.0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, nullable=False)

# ===================== إعدادات النظام =====================
class AppSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100))
    address = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(100))
    currency = db.Column(db.String(10), default='د.إ')
    bank_name = db.Column(db.String(100))
    bank_account = db.Column(db.String(100))
    iban = db.Column(db.String(100))
    swift = db.Column(db.String(50))
    tax_registration_number = db.Column(db.String(100))
    tax_rate = db.Column(db.Float, default=5.0)
    base_currency = db.Column(db.String(10), default='د.إ')
    logo_path = db.Column(db.String(200))

# ===================== معاملات الموردين والعملاء =====================
class PublisherTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    publisher_id = db.Column(db.Integer, db.ForeignKey('publisher.id'), nullable=False)
    trans_type = db.Column(db.String(50))
    reference = db.Column(db.String(100))
    debit = db.Column(db.Float, default=0.0)
    credit = db.Column(db.Float, default=0.0)
    notes = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CustomerPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50))
    reference = db.Column(db.String(100))
    notes = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ===================== تحويلات المخزون =====================
class StockTransfer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transfer_number = db.Column(db.String(50), unique=True, nullable=False)
    from_branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    to_branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    requested_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    shipped_at = db.Column(db.DateTime)
    received_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TransferItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('stock_transfer.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

# ===================== المحاسبة والمصروفات =====================
class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(50))
    parent_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    is_active = db.Column(db.Boolean, default=True)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    expense_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ===================== فواتير الشراء =====================
class PurchaseInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('publisher.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    total_amount = db.Column(db.Float, default=0.0)
    paid_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending')
    invoice_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PurchaseInvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('purchase_invoice.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float, nullable=False)

    class CustomerReturn(db.Model):
    __tablename__ = 'customer_return'
    
    id = db.Column(db.Integer, primary_key=True)
    return_number = db.Column(db.String(50), unique=True, nullable=False)  # رقم المرتجع: RET-2024-001
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)  # الفاتورة الأصلية
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    
    # بيانات المرتجع
    subtotal = db.Column(db.Float, default=0.0)  # قيمة البنود قبل الخصم
    discount = db.Column(db.Float, default=0.0)   # خصم إن وُجد
    tax = db.Column(db.Float, default=0.0)        # ضريبة
    total = db.Column(db.Float, default=0.0)      # الإجمالي النهائي (يُخصم من العميل)
    
    reason = db.Column(db.String(200))  # سبب المرتجع
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # العلاقات
    invoice = db.relationship('Invoice', backref='returns')
    customer = db.relationship('Customer', backref='returns')
    branch = db.relationship('Branch', backref='returns')
    creator = db.relationship('User', backref='created_returns')
    items = db.relationship('ReturnItem', backref='return_order', lazy=True, cascade='all, delete-orphan')

class ReturnItem(db.Column):
    __tablename__ = 'return_item'
    
    id = db.Column(db.Integer, primary_key=True)
    return_id = db.Column(db.Integer, db.ForeignKey('customer_return.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    invoice_item_id = db.Column(db.Integer, db.ForeignKey('invoice_item.id'))  # ربط بالعنصر الأصلي
    
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)  # سعر الوحدة وقت الشراء
    discount = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, nullable=False)  # quantity * unit_price - discount
    
    book = db.relationship('Book', backref='return_items')