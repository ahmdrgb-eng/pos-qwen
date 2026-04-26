import os, json, time, random
from datetime import datetime, timedelta
from functools import wraps
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from database import db, User, Branch, Author, Publisher, Category, Book, BranchInventory, Customer, Invoice, InvoiceItem, StockMovement, AppSettings, CustomerReturn, ReturnItem, CustomerPayment, Account, Expense
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash

# ===================== إعداد التطبيق =====================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'bookstore_secure_key_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookstore.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# إعدادات البريد (اختياري - غيّر القيم لاحقاً)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_app_password'
app.config['MAIL_DEFAULT_SENDER'] = 'your_email@gmail.com'

db.init_app(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.context_processor
def inject_globals():
    try:
        s = AppSettings.query.first()
        if not s:
            s = AppSettings()
            db.session.add(s)
            db.session.commit()
        return dict(settings=s, datetime=datetime)
    except:
        return dict(settings=None, datetime=datetime)

# ===================== Decorators للصلاحيات =====================
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'admin':
            flash('غير مصرح لك بالدخول', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def manager_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ['admin', 'manager']:
            flash('غير مصرح لك بالدخول', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

# ===================== دوال مساعدة =====================
def generate_invoice_number(branch_id):
    branch = db.session.get(Branch, branch_id)
    prefix = branch.name[:3].upper() if branch else 'INV'
    prefix = ''.join(c for c in prefix if c.isascii() and c.isalnum()) or 'BR'
    count = Invoice.query.filter_by(branch_id=branch_id, status='completed').count() + 1
    return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{count:05d}"

def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.first():
            admin = User(username='admin', password=User.hash_password('admin123') if hasattr(User, 'hash_password') else 'admin123', full_name='المدير العام', email='admin@store.com', role='admin')
            db.session.add(admin)
            b = Branch(name='الفرع الرئيسي', address='Dubai', phone='000', country='UAE', currency='د.إ', exchange_rate=1.0, is_central=True)
            db.session.add(b)
            db.session.flush()
            admin.branch_id = b.id
            db.session.add(Customer(name='عميل عام', phone='000'))
            db.session.add(User(username='cashier1', password=User.hash_password('1234') if hasattr(User, 'hash_password') else '1234', full_name='كاشير تجريبي', role='cashier', branch_id=b.id))
            db.session.commit()

# ===================== المصادقة =====================
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            session['branch_id'] = user.branch_id
            flash(f'مرحباً {user.full_name}', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('❌ اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج', 'info')
    return redirect(url_for('login'))

# ===================== لوحة التحكم =====================
@app.route('/dashboard')
@login_required
def dashboard():
    bid = session.get('branch_id') or current_user.branch_id
    rev = db.session.query(db.func.sum(Invoice.total)).filter(
        Invoice.branch_id==bid, Invoice.status=='completed', 
        Invoice.created_at>=datetime.now()-timedelta(days=30)
    ).scalar() or 0
    recent_invoices = Invoice.query.filter_by(branch_id=bid, status='completed').order_by(Invoice.created_at.desc()).limit(5).all()
    for inv in recent_invoices:
        inv.display_customer = Customer.query.get(inv.customer_id) if inv.customer_id else None
    return render_template('dashboard.html', 
        total_revenue=rev, recent_invoices=recent_invoices,
        total_books=Book.query.filter_by(is_active=True).count(), 
        total_customers=Customer.query.count(),
        total_invoices=Invoice.query.filter_by(branch_id=bid, status='completed').count())

# ===================== إدارة الكتب والمخزون =====================
@app.route('/books')
@login_required
def books():
    branch_id = session.get('branch_id') or current_user.branch_id
    all_books = Book.query.filter_by(is_active=True).order_by(Book.title).all()
    stock_map = {inv.book_id: inv.quantity for inv in BranchInventory.query.filter_by(branch_id=branch_id).all()}
    return render_template('books.html', books=all_books, stock_map=stock_map,
        authors=Author.query.all(), categories=Category.query.all(), 
        publishers=Publisher.query.all(), branches=Branch.query.all())

@app.route('/books/add', methods=['POST'])
@login_required
@manager_required
def add_book():
    try:
        branch_id = session.get('branch_id') or current_user.branch_id
        def sf(v): return float(v) if v and v.strip() else 0.0
        def si(v): return int(v) if v and v.strip() else 0
        b = Book(
            isbn=request.form.get('isbn', ''), title=request.form['title'],
            author_id=int(request.form.get('author_id')) if request.form.get('author_id') else None,
            category_id=int(request.form.get('category_id')) if request.form.get('category_id') else None,
            publisher_id=int(request.form.get('publisher_id')) if request.form.get('publisher_id') else None,
            description=request.form.get('description', ''), pages=si(request.form.get('pages')),
            cost_price=sf(request.form.get('cost_price')), selling_price=sf(request.form.get('selling_price')),
            discount_percent=sf(request.form.get('discount_percent')),
            publication_year=si(request.form.get('publication_year')) or 2024,
            edition=request.form.get('edition', '')
        )
        db.session.add(b); db.session.flush()
        qty = si(request.form.get('quantity'))
        if branch_id and qty > 0:
            inv = BranchInventory.query.filter_by(branch_id=branch_id, book_id=b.id).first()
            if inv: inv.quantity += qty
            else: db.session.add(BranchInventory(branch_id=branch_id, book_id=b.id, quantity=qty))
        db.session.commit(); flash('✅ تم إضافة الكتاب بنجاح', 'success')
    except Exception as e:
        db.session.rollback(); flash(f'❌ خطأ: {str(e)}', 'danger')
    return redirect(url_for('books'))

@app.route('/books/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_book(id):
    b = db.session.get(Book, id)
    if b: 
        b.is_active = False
        db.session.commit()
        flash('✅ تم حذف الكتاب بنجاح', 'success')
    return redirect(url_for('books'))

@app.route('/inventory')
@login_required
def inventory():
    branch_id = session.get('branch_id') or current_user.branch_id
    inventory_data = db.session.query(BranchInventory, Book).join(Book).filter(
        BranchInventory.branch_id == branch_id
    ).order_by(BranchInventory.quantity.asc()).all()
    return render_template('inventory.html', inventory=inventory_data, books=Book.query.filter_by(is_active=True).all())

# ===================== العملاء =====================
@app.route('/customers')
@login_required
def customers():
    data = [{'customer': c, 'inv_count': Invoice.query.filter_by(customer_id=c.id, status='completed').count()} for c in Customer.query.all()]
    return render_template('customers.html', customers=data)

@app.route('/customers/add', methods=['POST'])
@login_required
def add_customer(): 
    db.session.add(Customer(
        name=request.form['name'], phone=request.form.get('phone',''),
        email=request.form.get('email',''), address=request.form.get('address',''),
        national_id=request.form.get('national_id','')))
    db.session.commit(); flash('تم إضافة العميل', 'success')
    return redirect(url_for('customers'))

@app.route('/customers/<int:customer_id>/statement')
@login_required
def customer_statement(customer_id):
    customer = db.session.get(Customer, customer_id)
    if not customer:
        flash('❌ العميل غير موجود', 'danger')
        return redirect(url_for('customers'))
    invoices = Invoice.query.filter_by(customer_id=customer_id, status='completed').order_by(Invoice.created_at).all()
    returns = CustomerReturn.query.filter_by(customer_id=customer_id).order_by(CustomerReturn.created_at).all()
    transactions = []
    for inv in invoices:
        transactions.append({'date': inv.created_at, 'type': 'invoice', 'reference': inv.invoice_number, 'description': 'فاتورة بيع', 'amount': inv.total, 'balance': 0})
    for ret in returns:
        transactions.append({'date': ret.created_at, 'type': 'return', 'reference': ret.return_number, 'description': f'مرتجع - {ret.reason or "بدون سبب"}', 'amount': -ret.total, 'balance': 0})
    transactions.sort(key=lambda x: x['date'])
    balance = 0
    for t in transactions:
        balance += t['amount']
        t['balance'] = balance
    return render_template('customer_statement.html', customer=customer, transactions=transactions, final_balance=balance)

# ===================== الفواتير =====================
@app.route('/invoices')
@login_required
def invoices():
    invoices_list = Invoice.query.order_by(Invoice.created_at.desc()).all()
    for inv in invoices_list:
        inv.display_customer = Customer.query.get(inv.customer_id) if inv.customer_id else None
    return render_template('invoices.html', invoices=invoices_list)

@app.route('/invoices/<int:id>')
@login_required
def view_invoice(id):
    inv = db.session.get(Invoice, id)
    if not inv:
        flash('الفاتورة غير موجودة', 'danger')
        return redirect(url_for('invoices'))
    customer = Customer.query.get(inv.customer_id) if inv.customer_id else None
    extra_data = {'cash_discount': 0, 'delivery_fee': 0}
    if inv.notes:
        try: extra_data = json.loads(inv.notes)
        except: pass
    items_data = db.session.query(InvoiceItem, Book).outerjoin(Book, InvoiceItem.book_id == Book.id).filter(InvoiceItem.invoice_id == id).all()
    return render_template('invoice_detail.html', invoice=inv, customer=customer, settings=AppSettings.query.first(), cash_discount=extra_data.get('cash_discount', 0), delivery_fee=extra_data.get('delivery_fee', 0), items_data=items_data)

# ===================== الإعدادات =====================
@app.route('/settings', methods=['GET','POST'])
@login_required
@admin_required
def settings():
    s = AppSettings.query.first()
    if not s: s = AppSettings(); db.session.add(s); db.session.commit()
    if request.method=='POST':
        s.company_name, s.currency, s.address, s.phone, s.email = request.form.get('company_name'), request.form.get('currency'), request.form.get('address'), request.form.get('phone'), request.form.get('email')
        s.tax_rate = float(request.form.get('tax_rate',5))
        s.base_currency = request.form.get('base_currency', 'د.إ')
        lf = request.files.get('logo')
        if lf and lf.filename!='':
            fn = secure_filename(lf.filename); ufn = f"{int(time.time())}_{fn}"
            lf.save(os.path.join(app.config['UPLOAD_FOLDER'], ufn)); s.logo_path = f'uploads/{ufn}'
        db.session.commit(); flash('تم حفظ الإعدادات', 'success')
        return redirect(url_for('settings'))
    return render_template('settings.html', settings=s)

# ===================== التقارير =====================
@app.route('/reports')
@login_required
def reports():
    branch_id = session.get('branch_id')
    today = datetime.now().date()
    start_date_str = request.args.get('start_date', (today - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', today.strftime('%Y-%m-%d'))
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
    except ValueError:
        flash('تاريخ غير صحيح', 'danger')
        return redirect(url_for('dashboard'))
    inv_query = Invoice.query.filter(Invoice.status == 'completed', Invoice.created_at >= start_date, Invoice.created_at < end_date)
    if current_user.role != 'admin' and branch_id:
        inv_query = inv_query.filter_by(branch_id=branch_id)
    invoices = inv_query.order_by(Invoice.created_at.desc()).all()
    total_sales = sum(inv.total for inv in invoices)
    settings = AppSettings.query.first()
    return render_template('reports.html', start_date=start_date_str, end_date=end_date_str, total_sales=total_sales, invoice_count=len(invoices), currency=settings.currency if settings else 'د.إ')

# ===================== نقطة البيع (POS) - أساسي =====================
@app.route('/pos')
@login_required
def pos():
    br = session.get('branch_id') or current_user.branch_id
    stk = {i.book_id: i.quantity for i in BranchInventory.query.filter_by(branch_id=br).all()}
    return render_template('pos.html', books=Book.query.filter_by(is_active=True).all(), customers=Customer.query.all(), book_stock=stk)

@app.route('/api/book_search')
@login_required
def search_book():
    q = request.args.get('q', '').strip()
    branch_id = session.get('branch_id') or getattr(current_user, 'branch_id', None)
    if not q or len(q) < 2:
        books = Book.query.filter_by(is_active=True).limit(5000).all()
    else:
        search_term = f"%{q}%"
        books = Book.query.filter(Book.is_active == True, db.or_(Book.title.like(search_term), Book.isbn.like(search_term))).limit(5000).all()
    stock_map = {}
    if branch_id:
        all_inv = BranchInventory.query.filter_by(branch_id=branch_id).all()
        stock_map = {inv.book_id: inv.quantity for inv in all_inv}
    result = []
    for b in books:
        stock = stock_map.get(b.id, 0)
        discount = float(b.discount_percent or 0)
        selling = float(b.selling_price or 0)
        final_price = selling * (1 - discount / 100)
        result.append({'id': b.id, 'title': b.title or 'بدون عنوان', 'isbn': b.isbn or '', 'price': selling, 'final_price': round(final_price, 2), 'discount': discount, 'stock': stock})
    return jsonify({'books': result, 'total_count': len(result)})

@app.route('/api/create_invoice', methods=['POST'])
@login_required
def create_invoice():
    try:
        if not request.is_json:
            return jsonify({'error': 'خطأ: البيانات يجب أن تكون بصيغة JSON'}), 400
        data = request.get_json()
        branch_id = session.get('branch_id') or getattr(current_user, 'branch_id', None)
        if not branch_id:
            return jsonify({'error': 'لم يتم تحديد فرع'}), 400
        items = data.get('items', [])
        if not items or not isinstance(items, list):
            return jsonify({'error': 'السلة فارغة'}), 400
        def sf(v, d=0.0):
            try: return float(v) if v is not None else d
            except: return d
        customer_id = int(data['customer_id']) if data.get('customer_id') else None
        subtotal = sf(data.get('subtotal'))
        discount_pct = sf(data.get('discount_pct'))
        cash_discount = sf(data.get('cash_discount'))
        delivery_fee = sf(data.get('delivery_fee'))
        tax_received = sf(data.get('tax'))
        apply_tax = int(data.get('apply_tax', 1))
        tax_rate = sf(data.get('tax_rate', 5))
        taxable_base = max(subtotal - (subtotal * discount_pct / 100) - cash_discount, 0)
        final_tax = round(taxable_base * (tax_rate / 100), 2) if apply_tax == 1 else 0.0
        final_total = round(taxable_base + final_tax + delivery_fee, 2)
        payment_method = data.get('payment_method', 'cash')
        save_to_db = data.get('save_to_db', True)
        if not save_to_db:
            inv_num = generate_invoice_number(branch_id)
            return jsonify({'success': True, 'print_only': True, 'invoice_number': inv_num, 'total': final_total})
        inv_num = generate_invoice_number(branch_id)
        branch = db.session.get(Branch, branch_id)
        extra_notes = json.dumps({'cash_discount': cash_discount, 'delivery_fee': delivery_fee}, ensure_ascii=False)
        new_invoice = Invoice(
            invoice_number=inv_num, branch_id=branch_id, cashier_id=current_user.id, customer_id=customer_id,
            subtotal=subtotal, discount=(subtotal * discount_pct / 100) + cash_discount, tax=final_tax, total=final_total,
            paid_amount=final_total, payment_method=payment_method, status='completed',
            currency=branch.currency if branch else 'د.إ', exchange_rate=branch.exchange_rate if branch else 1.0, notes=extra_notes)
        db.session.add(new_invoice); db.session.flush()
        for item in items:
            book_id = int(item.get('book_id')); qty = int(item.get('quantity', 1)); unit_price = sf(item.get('unit_price'))
            stock = BranchInventory.query.filter_by(branch_id=branch_id, book_id=book_id).first()
            if not stock or stock.quantity < qty:
                db.session.rollback()
                return jsonify({'error': f'الكمية غير متوفرة للكتاب (رقم: {book_id})'}), 400
            stock.quantity -= qty; stock.last_updated = datetime.utcnow()
            item_discount = (unit_price * qty) * (discount_pct / 100)
            db.session.add(InvoiceItem(invoice_id=new_invoice.id, book_id=book_id, quantity=qty, unit_price=unit_price, discount=item_discount, total=(unit_price * qty) - item_discount))
            db.session.add(StockMovement(branch_id=branch_id, book_id=book_id, quantity=-qty, movement_type='out', reference=inv_num, created_by=current_user.id))
        if customer_id:
            cust = db.session.get(Customer, customer_id)
            if cust:
                cust.total_purchases = (cust.total_purchases or 0) + final_total
                cust.loyalty_points = (cust.loyalty_points or 0) + int(final_total / 10)
        db.session.commit()
        return jsonify({'success': True, 'invoice_number': inv_num, 'invoice_id': new_invoice.id})
    except Exception as e:
        db.session.rollback()
        import traceback; print(f"\n🔥 خطأ في create_invoice: {e}\n{traceback.format_exc()}\n")
        return jsonify({'error': f'حدث خطأ أثناء حفظ الفاتورة: {str(e)}'}), 500

# ===================== مرتجعات العملاء (مبسطة) =====================
@app.route('/customers/<int:customer_id>/returns')
@login_required
def customer_returns(customer_id):
    customer = db.session.get(Customer, customer_id)
    if not customer: return redirect(url_for('customers'))
    returns = CustomerReturn.query.filter_by(customer_id=customer_id).order_by(CustomerReturn.created_at.desc()).all()
    return render_template('customer_returns.html', customer=customer, returns=returns)
@app.route('/publishers')
@login_required
def publishers():
    try:
        # جلب جميع الناشرين من قاعدة البيانات
        pubs = Publisher.query.all()
        return render_template('publishers.html', publishers=pubs)
    except Exception as e:
        return f"حدث خطأ: {e}"
# ===================== التشغيل =====================
if __name__ == '__main__':
    init_db()
    print("🚀 يعمل على http://0.0.0.0:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)