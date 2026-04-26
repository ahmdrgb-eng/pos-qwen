from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import check_password_hash
from datetime import datetime

db = SQLAlchemy()

# ===================== المستخدمون =====================
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    role = db.Column(db.String(50))
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    is_active = db.Column(db.Boolean, default=True)
    last_seen = db.Column(db.DateTime)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)

# ===================== الفروع =====================
class Branch(db.Model):
    __tablename__ = 'branch'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    country = db.Column(db.String(50))
    currency = db.Column(db.String(10))
    exchange_rate = db.Column(db.Float)
    is_central = db.Column(db.Boolean)
    is_active = db.Column(db.Boolean, default=True)

# ===================== المؤلفون =====================
class Author(db.Model):
    __tablename__ = 'author'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    nationality = db.Column(db.String(100))

# ===================== الناشرين =====================
class Publisher(db.Model):
    __tablename__ = 'publisher'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(100))

# ===================== التصنيفات =====================
class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)

# ===================== الكتب =====================
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
    cost_price = db.Column(db.Float)
    selling_price = db.Column(db.Float)
    discount_percent = db.Column(db.Float)
    publication_year = db.Column(db.Integer)
    edition = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    
    author = db.relationship('Author', backref='books')
    publisher = db.relationship('Publisher', backref='books')
    category = db.relationship('Category', backref='books')

# ===================== العملاء =====================
class Customer(db.Model):
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(100))
    address = db.Column(db.String(200))
    national_id = db.Column(db.String(50))
    total_purchases = db.Column(db.Float, default=0.0)
    loyalty_points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ===================== الفواتير =====================
class Invoice(db.Model):
    __tablename__ = 'invoice'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    cashier_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    subtotal = db.Column(db.Float)
    discount = db.Column(db.Float)
    tax = db.Column(db.Float)
    total = db.Column(db.Float)
    paid_amount = db.Column(db.Float)
    payment_method = db.Column(db.String(50))
    status = db.Column(db.String(20))
    currency = db.Column(db.String(10))
    exchange_rate = db.Column(db.Float)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    customer = db.relationship('Customer', backref='invoices')

class InvoiceItem(db.Model):
    __tablename__ = 'invoice_item'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float)
    total = db.Column(db.Float, nullable=False)
    
    invoice = db.relationship('Invoice', backref='items')
    book = db.relationship('Book', backref='invoice_items')

# ===================== المخزون =====================
class BranchInventory(db.Model):
    __tablename__ = 'branch_inventory'
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    quantity = db.Column(db.Integer)
    last_updated = db.Column(db.DateTime)

class StockMovement(db.Model):
    __tablename__ = 'stock_movement'
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    quantity = db.Column(db.Integer)
    movement_type = db.Column(db.String(50))
    reference = db.Column(db.String(100))
    notes = db.Column(db.String(200))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime)

# ===================== المدفوعات والمرتجعات =====================
class CustomerPayment(db.Model):
    __tablename__ = 'customer_payment'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50))
    reference = db.Column(db.String(100))
    notes = db.Column(db.String(200))
    created_at = db.Column(db.DateTime)
    
    customer = db.relationship('Customer', backref='payments')

class CustomerReturn(db.Model):
    __tablename__ = 'customer_return'
    id = db.Column(db.Integer, primary_key=True)
    return_number = db.Column(db.String(50), unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float, default=0.0)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    
    customer = db.relationship('Customer', backref='returns')

class ReturnItem(db.Model):
    __tablename__ = 'return_item'
    id = db.Column(db.Integer, primary_key=True)
    return_id = db.Column(db.Integer, db.ForeignKey('customer_return.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    reason = db.Column(db.Text)
    
    return_request = db.relationship('CustomerReturn', backref='items')

# ===================== المحاسبة والمصروفات =====================
class Account(db.Model):
    __tablename__ = 'account'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(50))
    parent_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    is_active = db.Column(db.Boolean, default=True)

class Expense(db.Model):
    __tablename__ = 'expense'
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    expense_date = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime)

# ===================== فواتير الشراء =====================
class PurchaseInvoice(db.Model):
    __tablename__ = 'purchase_invoice'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('publisher.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    total_amount = db.Column(db.Float)
    paid_amount = db.Column(db.Float)
    status = db.Column(db.String(20))
    invoice_date = db.Column(db.DateTime)
    due_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime)

class PurchaseInvoiceItem(db.Model):
    __tablename__ = 'purchase_invoice_item'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('purchase_invoice.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float, nullable=False)

# ===================== تحويلات المخزون =====================
class StockTransfer(db.Model):
    __tablename__ = 'stock_transfer'
    id = db.Column(db.Integer, primary_key=True)
    transfer_number = db.Column(db.String(50), unique=True, nullable=False)
    from_branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    to_branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    status = db.Column(db.String(20))
    requested_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    shipped_at = db.Column(db.DateTime)
    received_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime)

class TransferItem(db.Model):
    __tablename__ = 'transfer_item'
    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('stock_transfer.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

# ===================== معاملات الناشرين =====================
class PublisherTransaction(db.Model):
    __tablename__ = 'publisher_transaction'
    id = db.Column(db.Integer, primary_key=True)
    publisher_id = db.Column(db.Integer, db.ForeignKey('publisher.id'), nullable=False)
    trans_type = db.Column(db.String(50))
    reference = db.Column(db.String(100))
    debit = db.Column(db.Float)
    credit = db.Column(db.Float)
    notes = db.Column(db.String(200))
    created_at = db.Column(db.DateTime)

# ===================== الإعدادات =====================
class AppSettings(db.Model):
    __tablename__ = 'app_settings'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100))
    address = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(100))
    currency = db.Column(db.String(10))
    bank_name = db.Column(db.String(100))
    bank_account = db.Column(db.String(100))
    iban = db.Column(db.String(100))
    swift = db.Column(db.String(50))
    tax_registration_number = db.Column(db.String(100))
    tax_rate = db.Column(db.Float)
    base_currency = db.Column(db.String(10))
    logo_path = db.Column(db.String(200))