import os, json, time, traceback, io
from datetime import datetime, timedelta
from functools import wraps
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from database import db, User, Branch, Author, Publisher, Category, Book, BranchInventory, Customer, Invoice, InvoiceItem, StockMovement, AppSettings, PublisherTransaction, CustomerPayment, StockTransfer, TransferItem, Account, Expense, PurchaseInvoice, PurchaseInvoiceItem
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bookstore_secure_key_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookstore.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# إعدادات البريد الإلكتروني
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'  # ⚠️ غيّر هذا
app.config['MAIL_PASSWORD'] = 'your_app_password'      # ⚠️ غيّر هذا
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

@app.context_processor
def inject_online_users():
    online = []
    if current_user.is_authenticated and current_user.role == 'admin':
        threshold = datetime.utcnow() - timedelta(minutes=3)
        online = User.query.filter(User.last_seen >= threshold, User.is_active == True).order_by(User.last_seen.desc()).all()
    return dict(online_users=online)

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

def send_email(subject, recipient, html_body):
    try:
        msg = Message(subject, recipients=[recipient])
        msg.html = html_body
        mail.send(msg)
        return {'success': True, 'message': 'تم الإرسال بنجاح'}
    except Exception as e:
        print(f"❌ خطأ في البريد: {e}")
        return {'success': False, 'error': str(e)}

def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.first():
            admin = User(username='admin', password=User.hash_password('admin123'), full_name='المدير العام', email='admin@store.com', role='admin')
            db.session.add(admin)
            b = Branch(name='الفرع الرئيسي', address='Dubai', phone='000', country='UAE', currency='د.إ', exchange_rate=1.0, is_central=True)
            db.session.add(b)
            db.session.flush()
            admin.branch_id = b.id
            db.session.add(Customer(name='عميل عام', phone='000'))
            db.session.add(User(username='cashier1', password=User.hash_password('1234'), full_name='كاشير تجريبي', role='cashier', branch_id=b.id))
            db.session.commit()

# ===================== المصادقة ولوحة التحكم =====================
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
        
        # البحث عن المستخدم
        user = User.query.filter_by(username=username).first()
        
        # التحقق من وجود المستخدم وصحة كلمة المرور باستخدام werkzeug مباشرة
        if user and check_password_hash(user.password, password):
            login_user(user)
            session['branch_id'] = user.branch_id
            flash(f'مرحباً {user.full_name}', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('❌ اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
            
    return render_template('login.html')
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.is_active:
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

@app.route('/dashboard')
@login_required
def dashboard():
    bid = session.get('branch_id') or current_user.branch_id
    
    rev = db.session.query(db.func.sum(Invoice.total)).filter(
        Invoice.branch_id==bid, 
        Invoice.status=='completed', 
        Invoice.created_at>=datetime.now()-timedelta(days=30)
    ).scalar() or 0
    
    recent_invoices = Invoice.query.filter_by(
        branch_id=bid, 
        status='completed'
    ).order_by(Invoice.created_at.desc()).limit(5).all()
    
    for inv in recent_invoices:
        inv.display_customer = Customer.query.get(inv.customer_id) if inv.customer_id else None

    return render_template('dashboard.html', 
                         total_revenue=rev, 
                         recent_invoices=recent_invoices,
                         total_books=Book.query.filter_by(is_active=True).count(), 
                         total_customers=Customer.query.count(),
                         total_invoices=Invoice.query.filter_by(branch_id=bid, status='completed').count(), 
                         low_stock=[], daily_sales=[])

# ===================== إدارة الفروع =====================
@app.route('/branches')
@login_required
@manager_required
def branches(): 
    return render_template('branches.html', branches=Branch.query.all(), editing_branch=None)

@app.route('/branches/add', methods=['POST'])
@login_required
@admin_required
def add_branch():
    is_central = 'is_central' in request.form
    if is_central: Branch.query.update({'is_central': False})
    new_branch = Branch(name=request.form['name'], address=request.form.get('address',''), phone=request.form.get('phone',''), country=request.form.get('country','UAE'), currency=request.form.get('currency','د.إ'), exchange_rate=float(request.form.get('exchange_rate', 1.0)), is_central=is_central)
    db.session.add(new_branch); db.session.commit(); flash('تم إضافة الفرع', 'success')
    return redirect(url_for('branches'))

@app.route('/branches/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_branch(id):
    branch = db.session.get(Branch, id)
    if not branch: flash('الفرع غير موجود', 'danger'); return redirect(url_for('branches'))
    if request.method == 'POST':
        is_central = 'is_central' in request.form
        if is_central: Branch.query.filter(Branch.id != id).update({'is_central': False})
        branch.name, branch.address, branch.phone = request.form['name'], request.form.get('address',''), request.form.get('phone','')
        branch.country, branch.currency = request.form.get('country','UAE'), request.form.get('currency','د.إ')
        branch.exchange_rate, branch.is_central = float(request.form.get('exchange_rate', 1.0)), is_central
        db.session.commit(); flash('تم تحديث الفرع', 'success'); return redirect(url_for('branches'))
    return render_template('branches.html', branches=Branch.query.all(), editing_branch=branch)

@app.route('/branches/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_branch(id):
    branch = db.session.get(Branch, id)
    if branch:
        if branch.is_central: flash('⚠️ لا يمكن حذف المخزن المركزي', 'warning')
        else: db.session.delete(branch); db.session.commit(); flash('تم حذف الفرع', 'success')
    return redirect(url_for('branches'))

# ===================== المستخدمين =====================
@app.route('/users')
@login_required
@admin_required
def users(): return render_template('users.html', users=User.query.all(), branches=Branch.query.all())

@app.route('/users/add', methods=['POST'])
@login_required
@admin_required
def add_user():
    un, pw = request.form.get('username','').strip(), request.form.get('password','').strip()
    if not un or len(pw)<4: flash('بيانات ناقصة أو كلمة مرور قصيرة', 'danger'); return redirect(url_for('users'))
    if User.query.filter_by(username=un).first(): flash('اسم المستخدم موجود مسبقاً', 'danger'); return redirect(url_for('users'))
    br = request.form.get('branch_id','').strip(); br = int(br) if br else None
    db.session.add(User(username=un, password=User.hash_password(pw), full_name=request.form.get('full_name',''), email=request.form.get('email',''), phone=request.form.get('phone',''), role=request.form.get('role','cashier'), branch_id=br, is_active=True))
    db.session.commit(); flash('تم إضافة المستخدم', 'success'); return redirect(url_for('users'))

@app.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    u = db.session.get(User, id)
    if not u: flash('غير موجود', 'danger'); return redirect(url_for('users'))
    if request.method == 'POST':
        un, fn = request.form.get('username','').strip(), request.form.get('full_name','').strip()
        if not un or not fn: flash('الحقول مطلوبة', 'warning'); return redirect(url_for('users'))
        if User.query.filter(User.username==un, User.id!=id).first(): flash('اسم مستخدم مكرر', 'danger'); return redirect(url_for('users'))
        br = request.form.get('branch_id','').strip(); br = int(br) if br else None
        u.username, u.full_name, u.email, u.phone, u.role, u.branch_id = un, fn, request.form.get('email',''), request.form.get('phone',''), request.form.get('role','cashier'), br
        np = request.form.get('new_password','').strip()
        if np: u.password = User.hash_password(np) if len(np)>=4 else u.password
        db.session.commit(); flash('تم تحديث المستخدم', 'success'); return redirect(url_for('users'))
    return render_template('users.html', users=User.query.all(), branches=Branch.query.all(), editing_user=u)

@app.route('/users/<int:id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(id):
    u = db.session.get(User, id)
    if u and u.id != current_user.id: u.is_active = not u.is_active; db.session.commit(); flash('تم تحديث الحالة', 'success')
    return redirect(url_for('users'))

# ===================== المؤلفون =====================
@app.route('/authors')
@login_required
def authors():
    data = [{'author': a, 'book_count': Book.query.filter_by(author_id=a.id, is_active=True).count()} for a in Author.query.all()]
    return render_template('authors.html', authors=data, editing_author=None)

@app.route('/authors/add', methods=['POST'])
@login_required
@manager_required
def add_author():
    name = request.form.get('name', '').strip()
    if not name: flash('الاسم مطلوب', 'danger'); return redirect(url_for('authors'))
    if Author.query.filter_by(name=name).first(): flash('المؤلف موجود مسبقاً', 'danger'); return redirect(url_for('authors'))
    db.session.add(Author(name=name, nationality=request.form.get('nationality', ''))); db.session.commit(); flash('تم إضافة المؤلف', 'success')
    return redirect(url_for('authors'))

@app.route('/authors/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@manager_required
def edit_author(id):
    author = db.session.get(Author, id)
    if not author: flash('غير موجود', 'danger'); return redirect(url_for('authors'))
    if request.method == 'POST':
        author.name = request.form.get('name', '').strip()
        author.nationality = request.form.get('nationality', '')
        db.session.commit(); flash('تم التحديث', 'success'); return redirect(url_for('authors'))
    data = [{'author': a, 'book_count': Book.query.filter_by(author_id=a.id, is_active=True).count()} for a in Author.query.all()]
    return render_template('authors.html', authors=data, editing_author=author)

@app.route('/authors/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_author(id):
    author = db.session.get(Author, id)
    if author:
        if Book.query.filter_by(author_id=id, is_active=True).count() > 0: flash('⚠️ مرتبط بكتب نشطة', 'warning')
        else: db.session.delete(author); db.session.commit(); flash('تم الحذف', 'success')
    return redirect(url_for('authors'))

@app.route('/authors/<int:id>/books')
@login_required
def author_books(id):
    author = db.session.get(Author, id)
    if not author: flash('غير موجود', 'danger'); return redirect(url_for('authors'))
    return render_template('author_books.html', author=author, books=Book.query.filter_by(author_id=id, is_active=True).all())

@app.route('/api/authors/search')
@login_required
def search_authors():
    query = request.args.get('q', '').strip()
    if not query:
        authors = Author.query.all()
    else:
        search_term = f"%{query}%"
        authors = Author.query.filter(
            db.or_(Author.name.like(search_term), Author.nationality.like(search_term))
        ).all()
    result = []
    for author in authors:
        book_count = Book.query.filter_by(author_id=author.id, is_active=True).count()
        result.append({
            'id': author.id, 'name': author.name, 'nationality': author.nationality or '-', 'book_count': book_count
        })
    return jsonify({'authors': result, 'total': len(result)})

# ===================== العملاء =====================
@app.route('/customers')
@login_required
def customers():
    data = [{'customer': c, 'inv_count': Invoice.query.filter_by(customer_id=c.id, status='completed').count()} for c in Customer.query.all()]
    return render_template('customers.html', customers=data)

@app.route('/customers/add', methods=['POST'])
@login_required
def add_customer(): 
    db.session.add(Customer(name=request.form['name'], phone=request.form.get('phone',''), email=request.form.get('email',''), address=request.form.get('address',''), national_id=request.form.get('national_id','')))
    db.session.commit(); flash('تم إضافة العميل', 'success'); return redirect(url_for('customers'))

@app.route('/customers/<int:id>/statement')
@login_required
def customer_statement(id):
    c = db.session.get(Customer, id)
    if not c: flash('غير موجود', 'danger'); return redirect(url_for('customers'))
    invs = Invoice.query.filter_by(customer_id=id).order_by(Invoice.created_at).all()
    pays = CustomerPayment.query.filter_by(customer_id=id).order_by(CustomerPayment.created_at).all()
    ev = [{'date':i.created_at, 'ref':i.invoice_number, 'type':'فاتورة', 'debit':i.total, 'credit':0, 'notes':''} for i in invs]
    ev += [{'date':p.created_at, 'ref':p.reference or '-', 'type':'دفعة', 'debit':0, 'credit':p.amount, 'notes':p.notes or ''} for p in pays]
    ev.sort(key=lambda x: x['date'])
    return render_template('customer_statement.html', customer=c, events=ev, current_date=datetime.now())

@app.route('/customers/<int:id>/payment', methods=['POST'])
@login_required
def add_customer_payment(id):
    c = db.session.get(Customer, id)
    if not c: return redirect(url_for('customers'))
    am = float(request.form.get('amount',0))
    if am>0: 
        db.session.add(CustomerPayment(customer_id=id, amount=am, payment_method=request.form.get('method','cash'), reference=request.form.get('reference',''), notes=request.form.get('notes','')))
        db.session.commit(); flash('تم تسجيل الدفعة', 'success')
    return redirect(url_for('customer_statement', id=id))

@app.route('/customers/<int:id>/invoices')
@login_required
def customer_invoices(id):
    customer = db.session.get(Customer, id)
    if not customer: flash('غير موجود', 'danger'); return redirect(url_for('customers'))
    invoices = Invoice.query.filter_by(customer_id=id, status='completed').order_by(Invoice.created_at.desc()).all()
    return render_template('customer_invoices.html', customer=customer, invoices=invoices)

# ===================== الناشرون =====================
@app.route('/publishers')
@login_required
def publishers():
    data = []
    for p in Publisher.query.all():
        book_ids = [b.id for b in Book.query.filter_by(publisher_id=p.id).all()]
        cnt = Invoice.query.join(InvoiceItem).filter(InvoiceItem.book_id.in_(book_ids), Invoice.status=='completed').distinct().count() if book_ids else 0
        data.append({'publisher': p, 'inv_count': cnt})
    return render_template('publishers.html', publishers=data)

@app.route('/publishers/add', methods=['POST'])
@login_required
@manager_required
def add_publisher(): 
    db.session.add(Publisher(name=request.form['name'], address=request.form.get('address',''), phone=request.form.get('phone',''), email=request.form.get('email',''))); db.session.commit(); flash('تم إضافة الناشر', 'success')
    return redirect(url_for('publishers'))

@app.route('/publishers/<int:id>/statement')
@login_required
def publisher_statement(id):
    p = db.session.get(Publisher, id)
    if not p: flash('غير موجود', 'danger'); return redirect(url_for('publishers'))
    return render_template('publisher_statement.html', publisher=p, events=PublisherTransaction.query.filter_by(publisher_id=id).order_by(PublisherTransaction.created_at).all(), current_date=datetime.now())

@app.route('/publishers/<int:id>/transaction', methods=['POST'])
@login_required
def add_publisher_transaction(id):
    p = db.session.get(Publisher, id)
    if not p: return redirect(url_for('publishers'))
    am, tp = float(request.form.get('amount',0)), request.form.get('type')
    if am>0:
        db.session.add(PublisherTransaction(publisher_id=id, trans_type=tp, reference=request.form.get('reference',''), debit=am if tp=='purchase' else 0, credit=am if tp=='payment' else 0, notes=request.form.get('notes',''))); db.session.commit(); flash('تم تسجيل العملية', 'success')
    return redirect(url_for('publisher_statement', id=id))

@app.route('/publishers/<int:id>/invoices')
@login_required
def publisher_invoices(id):
    publisher = db.session.get(Publisher, id)
    if not publisher: flash('غير موجود', 'danger'); return redirect(url_for('publishers'))
    book_ids = [b.id for b in Book.query.filter_by(publisher_id=id).all()]
    invoices = Invoice.query.join(InvoiceItem).filter(InvoiceItem.book_id.in_(book_ids), Invoice.status=='completed').distinct().order_by(Invoice.created_at.desc()).all() if book_ids else []
    return render_template('publisher_invoices.html', publisher=publisher, invoices=invoices)

# ===================== الفئات والكتب =====================
@app.route('/categories')
@login_required
def categories(): return render_template('categories.html', categories=Category.query.all())

@app.route('/categories/add', methods=['POST'])
@login_required
@manager_required
def add_category(): db.session.add(Category(name=request.form['name'], description=request.form.get('description',''))); db.session.commit(); flash('تم إضافة الفئة', 'success'); return redirect(url_for('categories'))

@app.route('/books')
@login_required
def books():
    branch_id = session.get('branch_id') or current_user.branch_id
    books = Book.query.filter_by(is_active=True).all()
    stock_map = {inv.book_id: inv.quantity for inv in BranchInventory.query.filter_by(branch_id=branch_id).all()}
    return render_template('books.html', 
        books=books, 
        stock_map=stock_map,
        authors=Author.query.all(), 
        categories=Category.query.all(), 
        publishers=Publisher.query.all(), 
        branches=Branch.query.all()
    )

@app.route('/books/add', methods=['POST'])
@login_required
@manager_required
def add_book():
    try:
        branch_id = session.get('branch_id') or current_user.branch_id
        title = request.form['title']
        isbn = request.form.get('isbn', '')
        def sf(v): return float(v) if v and v.strip() else 0.0
        def si(v): return int(v) if v and v.strip() else 0
        
        cost_price = sf(request.form.get('cost_price'))
        selling_input = request.form.get('selling_price')
        selling_price = sf(selling_input) if selling_input else (cost_price * 1.5)
        discount = sf(request.form.get('discount_percent'))
        pages = si(request.form.get('pages'))
        year = si(request.form.get('publication_year')) or 2024
        
        author_id = int(request.form.get('author_id')) if request.form.get('author_id') else None
        category_id = int(request.form.get('category_id')) if request.form.get('category_id') else None
        publisher_id = int(request.form.get('publisher_id')) if request.form.get('publisher_id') else None

        b = Book(
            isbn=isbn, title=title, author_id=author_id, category_id=category_id,
            publisher_id=publisher_id, description=request.form.get('description', ''),
            pages=pages, cost_price=cost_price, selling_price=selling_price,
            discount_percent=discount, publication_year=year,
            edition=request.form.get('edition', '')
        )
        db.session.add(b)
        db.session.flush()
        
        qty = si(request.form.get('quantity'))
        if branch_id and qty > 0:
            inv = BranchInventory.query.filter_by(branch_id=branch_id, book_id=b.id).first()
            if inv: inv.quantity += qty
            else: db.session.add(BranchInventory(branch_id=branch_id, book_id=b.id, quantity=qty))
        
        db.session.commit()
        flash('✅ تم إضافة الكتاب بنجاح', 'success')
        return redirect(url_for('books'))
    except Exception as e:
        db.session.rollback()
        flash(f'❌ خطأ: {str(e)}', 'danger')
        return redirect(url_for('books'))

@app.route('/books/<int:id>/edit', methods=['POST'])
@login_required
@manager_required
def edit_book(id):
    b = db.session.get(Book, id)
    if b:
        b.title, b.isbn, b.author_id, b.category_id, b.publisher_id = request.form['title'], request.form.get('isbn',''), request.form.get('author_id',type=int), request.form.get('category_id',type=int), request.form.get('publisher_id',type=int)
        b.cost_price, b.selling_price, b.discount_percent = float(request.form.get('cost_price',0)), float(request.form.get('selling_price',0)), float(request.form.get('discount_percent',0))
        b.pages, b.description = int(request.form.get('pages',0)), request.form.get('description','')
        db.session.commit(); flash('تم تحديث الكتاب', 'success')
    return redirect(url_for('books'))

@app.route('/books/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_book(id):
    b = db.session.get(Book, id)
    if b: b.is_active = False; db.session.commit(); flash('تم تعطيل الكتاب', 'success')
    return redirect(url_for('books'))

@app.route('/import_books', methods=['POST'])
@login_required
@manager_required
def import_books():
    if 'file' not in request.files or request.files['file'].filename == '':
        flash('الرجاء اختيار ملف Excel', 'danger')
        return redirect(url_for('books'))
    
    tbr = request.form.get('target_branch_id','').strip()
    tbr = int(tbr) if tbr else current_user.branch_id
    
    try:
        df = pd.read_excel(request.files['file'])
        added, updated, skipped = 0, 0, 0
        
        for idx, r in df.iterrows():
            raw_isbn = r.get('ISBN')
            isbn = ""
            if pd.notna(raw_isbn):
                isbn = str(int(raw_isbn)) if isinstance(raw_isbn, (int, float)) else str(raw_isbn).strip()
            
            title = str(r.get('Title', '')).strip()
            author_name = str(r.get('Author', '')).strip()
            publisher_name = str(r.get('Publisher', '')).strip()
            category_name = str(r.get('Category', '')).strip()
            
            try: cost_price = float(r.get('Cost Price', 0))
            except: cost_price = 0.0
            
            try: selling_price = float(r.get('Selling Price', 0))
            except: selling_price = 0.0
            
            try: quantity = int(r.get('Quantity', 0))
            except: quantity = 0
            
            if not title:
                skipped += 1
                continue

            author_id = None
            if author_name and author_name.lower() != 'nan':
                author = Author.query.filter_by(name=author_name).first()
                if not author:
                    author = Author(name=author_name, nationality='')
                    db.session.add(author)
                    db.session.flush()
                author_id = author.id
            
            publisher_id = None
            if publisher_name and publisher_name.lower() != 'nan':
                publisher = Publisher.query.filter_by(name=publisher_name).first()
                if not publisher:
                    publisher = Publisher(name=publisher_name, address='', phone='', email='')
                    db.session.add(publisher)
                    db.session.flush()
                publisher_id = publisher.id
            
            category_id = None
            if category_name and category_name.lower() != 'nan':
                category = Category.query.filter_by(name=category_name).first()
                if not category:
                    category = Category(name=category_name, description='')
                    db.session.add(category)
                    db.session.flush()
                category_id = category.id
            
            book = None
            if isbn and isbn != 'nan':
                book = Book.query.filter_by(isbn=isbn).first()
            
            if not book:
                if title:
                    book = Book.query.filter_by(title=title).first()
            
            if book:
                book.title = title
                if isbn and isbn != 'nan': book.isbn = isbn
                if author_id: book.author_id = author_id
                if publisher_id: book.publisher_id = publisher_id
                if category_id: book.category_id = category_id
                if cost_price > 0: book.cost_price = cost_price
                if selling_price > 0: book.selling_price = selling_price
                updated += 1
            else:
                new_book = Book(
                    isbn=isbn if isbn and isbn != 'nan' else None,
                    title=title,
                    author_id=author_id,
                    publisher_id=publisher_id,
                    category_id=category_id,
                    cost_price=cost_price,
                    selling_price=selling_price,
                    is_active=True
                )
                db.session.add(new_book)
                db.session.flush()
                book = new_book
                added += 1
            
            if quantity > 0 and tbr:
                inv = BranchInventory.query.filter_by(branch_id=tbr, book_id=book.id).first()
                if inv: inv.quantity += quantity
                else: db.session.add(BranchInventory(branch_id=tbr, book_id=book.id, quantity=quantity))
        
        db.session.commit()
        flash(f'✅ تم الاستيراد بنجاح! | أُضيف: {added} | حُدّث: {updated} | تُخطّي: {skipped}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ خطأ في الاستيراد: {str(e)}', 'danger')
    
    return redirect(url_for('books'))

# ===================== المخزون =====================
@app.route('/inventory')
@login_required
def inventory():
    branch_id = session.get('branch_id') or current_user.branch_id
    session['branch_id'] = branch_id

    all_books = Book.query.filter_by(is_active=True).all()
    for book in all_books:
        inv = BranchInventory.query.filter_by(branch_id=branch_id, book_id=book.id).first()
        if not inv:
            new_inv = BranchInventory(branch_id=branch_id, book_id=book.id, quantity=0, last_updated=datetime.utcnow())
            db.session.add(new_inv)
    
    db.session.commit()

    inventory_data = db.session.query(BranchInventory, Book).join(Book).filter(
        BranchInventory.branch_id == branch_id
    ).order_by(BranchInventory.quantity.asc()).all()

    books = Book.query.filter_by(is_active=True).order_by(Book.title).all()

    return render_template('inventory.html', 
                         inventory=inventory_data, 
                         books=books)

@app.route('/inventory/add_stock', methods=['POST'])
@login_required
def add_stock():
    try:
        bid = int(request.form['book_id'])
        q = int(request.form['quantity'])
        br = session.get('branch_id')
        
        inv = BranchInventory.query.filter_by(branch_id=br, book_id=bid).first()
        if inv: 
            inv.quantity += q
        else: 
            db.session.add(BranchInventory(branch_id=br, book_id=bid, quantity=q))
        
        db.session.add(StockMovement(branch_id=br, book_id=bid, quantity=q, movement_type='in', created_by=current_user.id))
        db.session.commit()
        flash('✅ تمت إضافة المخزون بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ خطأ في الإضافة: {str(e)}', 'danger')
        
    return redirect(url_for('inventory'))

@app.route('/inventory/<int:id>/update', methods=['POST'])
@login_required
def update_stock(id):
    inv_item = db.session.get(BranchInventory, id)
    
    if not inv_item:
        flash('❌ سجل المخزون غير موجود', 'danger')
        return redirect(url_for('inventory'))
    
    try:
        new_qty = request.form.get('quantity', type=int)
        
        if new_qty is None or new_qty < 0:
            raise ValueError("الكمية يجب أن تكون رقماً موجباً")
            
        old_qty = inv_item.quantity
        inv_item.quantity = new_qty
        inv_item.last_updated = datetime.utcnow()
        
        diff = new_qty - old_qty
        if diff != 0:
            db.session.add(StockMovement(
                branch_id=inv_item.branch_id,
                book_id=inv_item.book_id,
                quantity=abs(diff),
                movement_type='in' if diff > 0 else 'out',
                reference='تعديل يدوي',
                created_by=current_user.id
            ))
        
        db.session.commit()
        flash('✅ تم تحديث المخزون بنجاح', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ خطأ: {str(e)}', 'danger')
    
    return redirect(url_for('inventory'))

# ===================== نقطة البيع (POS) =====================
@app.route('/pos')
@login_required
def pos():
    br = session.get('branch_id'); stk = {i.book_id: i.quantity for i in BranchInventory.query.filter_by(branch_id=br).all()}
    return render_template('pos.html', books=Book.query.filter_by(is_active=True).all(), customers=Customer.query.all(), book_stock=stk)

@app.route('/mobile_pos')
@login_required
def mobile_pos():
    br = session.get('branch_id'); stk = {i.book_id: i.quantity for i in BranchInventory.query.filter_by(branch_id=br).all()}
    return render_template('mobile_pos.html', books=Book.query.filter_by(is_active=True).all(), customers=Customer.query.all(), book_stock=stk)

@app.route('/api/book_search')
@login_required
def search_book():
    try:
        q = request.args.get('q', '').strip()
        branch_id = session.get('branch_id') or getattr(current_user, 'branch_id', None)
        
        if not q or len(q) < 2:
            books = Book.query.filter_by(is_active=True).limit(5000).all()
        else:
            search_term = f"%{q}%"
            books = Book.query.filter(
                Book.is_active == True,
                db.or_(Book.title.like(search_term), Book.isbn.like(search_term))
            ).limit(5000).all()
        
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
            
            result.append({
                'id': b.id,
                'title': b.title or 'بدون عنوان',
                'isbn': b.isbn or '',
                'price': selling,
                'final_price': round(final_price, 2),
                'discount': discount,
                'stock': stock
            })
        
        return jsonify({'books': result, 'total_count': len(result)})
    except Exception as e:
        print(f"🔍 خطأ البحث: {e}")
        return jsonify({'books': [], 'total_count': 0})

@app.route('/api/add_barcode_item', methods=['POST'])
@login_required
def add_barcode_item():
    try:
        data = request.get_json()
        barcode = data.get('barcode', '').strip()
        branch_id = session.get('branch_id') or current_user.branch_id
        if not barcode: return jsonify({'error': 'الرجاء مسح باركود صحيح'}), 400
        book = Book.query.filter_by(isbn=barcode, is_active=True).first()
        if not book: return jsonify({'error': 'الكتاب غير موجود في النظام!'}), 404
        inventory = BranchInventory.query.filter_by(branch_id=branch_id, book_id=book.id).first()
        if not inventory or inventory.quantity <= 0: return jsonify({'error': 'هذا الكتاب غير متوفر في مخزون هذا الفرع!'}), 400
        final_price = book.selling_price * (1 - (book.discount_percent or 0) / 100)
        return jsonify({'success': True, 'item': {'book_id': book.id, 'title': book.title, 'price': final_price, 'original_price': book.selling_price, 'discount': book.discount_percent, 'stock': inventory.quantity, 'isbn': book.isbn}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/branch-books/<int:branch_id>')
@login_required
def get_branch_books(branch_id):
    inventory = db.session.query(BranchInventory, Book).join(Book).filter(BranchInventory.branch_id == branch_id, BranchInventory.quantity > 0, Book.is_active == True).all()
    return jsonify([{'id': b.id, 'title': b.title, 'stock': inv.quantity, 'isbn': b.isbn or ''} for inv, b in inventory])

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
        tax = sf(data.get('tax'))
        total = sf(data.get('total'))
        payment_method = data.get('payment_method', 'cash')
        save_to_db = data.get('save_to_db', True)

        if not save_to_db:
            inv_num = generate_invoice_number(branch_id)
            return jsonify({'success': True, 'print_only': True, 'invoice_number': inv_num, 'total': total})

        inv_num = generate_invoice_number(branch_id)
        branch = db.session.get(Branch, branch_id)
        extra_notes = json.dumps({'cash_discount': cash_discount, 'delivery_fee': delivery_fee}, ensure_ascii=False)
        
        new_invoice = Invoice(
            invoice_number=inv_num,
            branch_id=branch_id,
            cashier_id=current_user.id,
            customer_id=customer_id,
            subtotal=subtotal,
            discount=discount_pct,
            tax=tax,
            total=total,
            paid_amount=total,
            payment_method=payment_method,
            status='completed',
            currency=branch.currency if branch else 'د.إ',
            exchange_rate=branch.exchange_rate if branch else 1.0,
            notes=extra_notes
        )
        db.session.add(new_invoice)
        db.session.flush()

        for item in items:
            book_id = int(item.get('book_id'))
            qty = int(item.get('quantity', 1))
            unit_price = sf(item.get('unit_price'))
            
            stock = BranchInventory.query.filter_by(branch_id=branch_id, book_id=book_id).first()
            if not stock or stock.quantity < qty:
                db.session.rollback()
                return jsonify({'error': f'الكمية غير متوفرة للكتاب (رقم: {book_id})'}), 400
            
            stock.quantity -= qty
            stock.last_updated = datetime.utcnow()
            
            item_discount = (unit_price * qty) * (discount_pct / 100)
            
            db.session.add(InvoiceItem(
                invoice_id=new_invoice.id,
                book_id=book_id,
                quantity=qty,
                unit_price=unit_price,
                discount=item_discount,
                total=(unit_price * qty) - item_discount
            ))
            
            db.session.add(StockMovement(
                branch_id=branch_id,
                book_id=book_id,
                quantity=-qty,
                movement_type='out',
                reference=inv_num,
                created_by=current_user.id
            ))

        if customer_id:
            cust = db.session.get(Customer, customer_id)
            if cust:
                cust.total_purchases = (cust.total_purchases or 0) + total
                cust.loyalty_points = (cust.loyalty_points or 0) + int(total / 10)

        db.session.commit()
        return jsonify({'success': True, 'invoice_number': inv_num, 'invoice_id': new_invoice.id})

    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"\n🔥 خطأ في create_invoice: {e}\n{traceback.format_exc()}\n")
        return jsonify({'error': f'حدث خطأ أثناء حفظ الفاتورة: {str(e)}'}), 500

# ===================== الفواتير =====================
@app.route('/invoices')
@login_required
def invoices():
    invoices_list = Invoice.query.order_by(Invoice.created_at.desc()).all()
    for inv in invoices_list:
        inv.display_customer = None
        if inv.customer_id:
            inv.display_customer = Customer.query.get(inv.customer_id)
    return render_template('invoices.html', invoices=invoices_list)

@app.route('/invoices/<int:id>')
@login_required
def view_invoice(id):
    inv = db.session.get(Invoice, id)
    if not inv:
        flash('الفاتورة غير موجودة', 'danger')
        return redirect(url_for('invoices'))

    customer = None
    if inv.customer_id:
        customer = Customer.query.get(inv.customer_id)

    extra_data = {'cash_discount': 0, 'delivery_fee': 0}
    if inv.notes:
        try: extra_data = json.loads(inv.notes)
        except: pass

    items_data = db.session.query(InvoiceItem, Book).outerjoin(
        Book, InvoiceItem.book_id == Book.id
    ).filter(InvoiceItem.invoice_id == id).all()

    return render_template('invoice_detail.html', 
                         invoice=inv, 
                         customer=customer,
                         settings=AppSettings.query.first(),
                         cash_discount=extra_data.get('cash_discount', 0),
                         delivery_fee=extra_data.get('delivery_fee', 0),
                         items_data=items_data)

@app.route('/invoices/<int:id>/return', methods=['POST'])
@login_required
@manager_required
def return_invoice(id):
    inv = db.session.get(Invoice, id)
    if inv and inv.status == 'completed':
        inv.status = 'returned'
        br = session.get('branch_id')
        items = InvoiceItem.query.filter_by(invoice_id=id).all()
        
        for it in items:
            ir = BranchInventory.query.filter_by(branch_id=br, book_id=it.book_id).first()
            if ir: 
                ir.quantity += it.quantity
                db.session.add(StockMovement(branch_id=br, book_id=it.book_id, quantity=it.quantity, movement_type='in', reference=inv.invoice_number, notes='إرجاع', created_by=current_user.id))
        
        if inv.customer_id:
            c = db.session.get(Customer, inv.customer_id)
            if c: 
                c.total_purchases = max(0, (c.total_purchases or 0) - inv.total)
                c.loyalty_points = max(0, (c.loyalty_points or 0) - int(inv.total/10))
        db.session.commit()
        flash('تم إرجاع الفاتورة بنجاح', 'success')
    return redirect(url_for('invoices'))

@app.route('/invoices/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_invoice(id):
    invoice = db.session.get(Invoice, id)
    if not invoice:
        flash('❌ الفاتورة غير موجودة', 'danger')
        return redirect(url_for('invoices'))

    items = InvoiceItem.query.filter_by(invoice_id=id).all()
    for item in items:
        stock = BranchInventory.query.filter_by(branch_id=invoice.branch_id, book_id=item.book_id).first()
        if stock:
            stock.quantity += item.quantity

    InvoiceItem.query.filter_by(invoice_id=id).delete()
    StockMovement.query.filter_by(reference=invoice.invoice_number).delete()
    db.session.delete(invoice)
    db.session.commit()

    flash('✅ تم حذف الفاتورة نهائياً واسترجاع المخزون', 'success')
    return redirect(url_for('invoices'))

@app.route('/api/send-invoice-email/<int:invoice_id>', methods=['POST'])
@login_required
def send_invoice_email(invoice_id):
    invoice = db.session.get(Invoice, invoice_id)
    if not invoice: return jsonify({'error': 'الفاتورة غير موجودة'}), 404
    if not invoice.customer_obj or not invoice.customer_obj.email:
        return jsonify({'error': 'العميل ليس لديه بريد إلكتروني'}), 400
    
    items_html = ""
    for item in invoice.items:
        items_html += f"""<tr style="border-bottom: 1px solid #eee;"><td style="padding: 10px;">{item.book.title if item.book else 'صنف'}</td><td style="padding: 10px; text-align: center;">{item.quantity}</td><td style="padding: 10px; text-align: center;">{item.unit_price:.2f}</td><td style="padding: 10px; text-align: center; font-weight: bold;">{item.total:.2f}</td></tr>"""
    
    html_content = f"""<div style="font-family: 'Segoe UI', sans-serif; direction: rtl; color: #333; max-width: 600px; margin: auto;"><div style="background: #f8f9fa; padding: 20px; border-bottom: 3px solid #1e3c72;"><h2 style="color: #1e3c72; margin: 0;">{settings.company_name or 'نظام المكتبة'}</h2><p style="margin: 5px 0 0; color: #666;">فاتورة مبيعات رسمية</p></div><div style="padding: 20px;"><p>عزيزي العميل: <strong>{invoice.customer_obj.name if invoice.customer_obj else 'العميل العام'}</strong></p><p>شكراً لتعاملكم معنا. تفاصيل الفاتورة كالتالي:</p><table style="width: 100%; border-collapse: collapse; margin: 20px 0; background: #fff;"><thead style="background: #1e3c72; color: white;"><tr><th style="padding: 10px; text-align: right;">الصنف</th><th style="padding: 10px;">الكمية</th><th style="padding: 10px;">السعر</th><th style="padding: 10px;">الإجمالي</th></tr></thead><tbody>{items_html}</tbody></table><div style="background: #f1f8ff; padding: 15px; border-radius: 5px; margin-top: 20px;"><p><strong>المجموع:</strong> {invoice.subtotal:.2f} {settings.currency}</p><p><strong>الضريبة (5%):</strong> {invoice.tax:.2f}</p><h3 style="color: #1e3c72; margin: 10px 0 0;">الإجمالي النهائي: {invoice.total:.2f} {settings.currency}</h3></div><p style="margin-top: 30px; font-size: 12px; color: #888; text-align: center;">تم إنشاء هذه الفاتورة إلكترونياً وهي سارية المفعول.<br>{settings.address or ''}</p></div></div>"""
    
    result = send_email(f"فاتورة رقم {invoice.invoice_number} - {settings.company_name or 'نظام المكتبة'}", invoice.customer_obj.email, html_content)
    return jsonify(result) if result['success'] else (jsonify(result), 500)

# ===================== الإعدادات =====================
@app.route('/settings', methods=['GET','POST'])
@login_required
@admin_required
def settings():
    s = AppSettings.query.first()
    if not s: s = AppSettings(); db.session.add(s); db.session.commit()
    if request.method=='POST':
        s.company_name, s.currency, s.address, s.phone, s.email = request.form.get('company_name'), request.form.get('currency'), request.form.get('address'), request.form.get('phone'), request.form.get('email')
        s.bank_name, s.bank_account, s.iban, s.swift, s.tax_registration_number = request.form.get('bank_name'), request.form.get('bank_account'), request.form.get('iban'), request.form.get('swift'), request.form.get('tax_registration_number')
        s.tax_rate = float(request.form.get('tax_rate',5))
        s.base_currency = request.form.get('base_currency', 'د.إ')
        lf = request.files.get('logo')
        if lf and lf.filename!='':
            fn = secure_filename(lf.filename); ufn = f"{int(time.time())}_{fn}"
            lf.save(os.path.join(app.config['UPLOAD_FOLDER'], ufn)); s.logo_path = f'uploads/{ufn}'
        db.session.commit(); flash('تم حفظ الإعدادات', 'success'); return redirect(url_for('settings'))
    return render_template('settings.html', settings=s)

import os
from flask import send_file
from datetime import datetime

@app.route('/settings/backup')
@login_required
@admin_required
def backup_database():
    try:
        # تحديد مسار قاعدة البيانات ديناميكياً حسب النظام
        if os.name == 'nt':  # Windows
            db_path = os.path.join(os.path.dirname(__file__), 'bookstore.db')
        else:  # Linux/Mac
            db_path = '/var/www/pos_qwen/bookstore.db'
        
        # التحقق من وجود الملف
        if not os.path.exists(db_path):
            flash('❌ ملف قاعدة البيانات غير موجود!', 'danger')
            return redirect(url_for('settings'))
        
        # إنشاء اسم الملف بالتاريخ والوقت الحالي
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f"pos_backup_{timestamp}.db"
        
        # إرسال الملف للمستخدم للتحميل
        return send_file(
            db_path,
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Backup Error: {e}")
        flash(f'❌ حدث خطأ أثناء النسخ الاحتياطي: {str(e)}', 'danger')
        return redirect(url_for('settings'))
    try:
        # مسار قاعدة البيانات في السيرفر
        db_path = '/var/www/pos_qwen/bookstore.db'
        
        # التحقق من وجود الملف
        if not os.path.exists(db_path):
            flash('❌ ملف قاعدة البيانات غير موجود!', 'danger')
            return redirect(url_for('settings'))
        
        # إنشاء اسم الملف بالتاريخ والوقت الحالي
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f"pos_backup_{timestamp}.db"
        
        # إرسال الملف للمستخدم للتحميل
        return send_file(
            db_path,
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Backup Error: {e}")
        flash(f'❌ حدث خطأ أثناء النسخ الاحتياطي: {str(e)}', 'danger')
        return redirect(url_for('settings'))

import os
import shutil
from flask import request, redirect, url_for, flash

@app.route('/settings/restore', methods=['POST'])
@login_required
@admin_required
def restore_database():
    if 'backup_file' not in request.files:
        flash('❌ لم يتم اختيار ملف للنسخ الاحتياطي', 'danger')
        return redirect(url_for('settings'))
        
    file = request.files['backup_file']
    
    if file.filename == '':
        flash('❌ اسم الملف فارغ', 'danger')
        return redirect(url_for('settings'))
        
    # التأكد من أن الامتداد هو .db فقط للأمان
    if not file.filename.endswith('.db'):
        flash('❌ نوع الملف غير صحيح. يجب أن يكون ملف .db', 'danger')
        return redirect(url_for('settings'))
        
    try:
        # تحديد مسار قاعدة البيانات ديناميكياً حسب النظام
        if os.name == 'nt':  # Windows
            db_path = os.path.join(os.path.dirname(__file__), 'bookstore.db')
            temp_path = os.path.join(os.environ.get('TEMP', '.'), 'temp_restore.db')
        else:  # Linux/Mac
            db_path = '/var/www/pos_qwen/bookstore.db'
            temp_path = '/tmp/temp_restore.db'
        
        # 1. حفظ الملف المرفوع مؤقتاً
        file.save(temp_path)
        
        # 2. استبدال قاعدة البيانات الحالية بالملف الجديد
        shutil.copyfile(temp_path, db_path)
        
        # 3. تنظيف الملف المؤقت
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        # 4. ضبط الصلاحيات (فقط في لينكس)
        if os.name != 'nt':
            os.chown(db_path, 0, 33)  # root:www-data
            os.chmod(db_path, 0o664)
        
        flash('✅ تم استعادة قاعدة البيانات بنجاح! سيتم إعادة تحميل الصفحة...', 'success')
        
        # إعادة تشغيل الخدمة فقط في السيرفر (لينكس)
        if os.name != 'nt':
            import subprocess
            subprocess.call(['sudo', 'systemctl', 'restart', 'pos_qwen'])
        
        return redirect(url_for('settings'))
        
    except Exception as e:
        print(f"Restore Error: {e}")
        flash(f'❌ حدث خطأ أثناء الاستعادة: {str(e)}', 'danger')
        return redirect(url_for('settings'))
    if 'backup_file' not in request.files:
        flash('❌ لم يتم اختيار ملف للنسخ الاحتياطي', 'danger')
        return redirect(url_for('settings'))
        
    file = request.files['backup_file']
    
    if file.filename == '':
        flash('❌ اسم الملف فارغ', 'danger')
        return redirect(url_for('settings'))
        
    # التأكد من أن الامتداد هو .db فقط للأمان
    if not file.filename.endswith('.db'):
        flash('❌ نوع الملف غير صحيح. يجب أن يكون ملف .db', 'danger')
        return redirect(url_for('settings'))
        
    try:
        db_path = '/var/www/pos_qwen/bookstore.db'
        temp_path = '/tmp/temp_restore.db'
        
        # 1. حفظ الملف المرفوع مؤقتاً في مجلد /tmp
        file.save(temp_path)
        
        # 2. التحقق السريع من صحة الملف (اختياري: التأكد من أنه SQLite صالح)
        # يمكن إضافة كود هنا للتحقق، لكن سنكتفي بالاستبدال المباشر للسرعة
        
        # 3. استبدال قاعدة البيانات الحالية بالملف الجديد
        # نستخدم shutil.copyfile لضمان نسخ المحتوى بشكل آمن
        shutil.copyfile(temp_path, db_path)
        
        # 4. تنظيف الملف المؤقت
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        # 5. ضبط الصلاحيات مرة أخرى لضمان عمل التطبيق
        os.chown(db_path, 0, 33) # root:www-data (IDs قد تختلف حسب النظام، لكن www-data عادة 33)
        os.chmod(db_path, 0o664)
        
        flash('✅ تم استعادة قاعدة البيانات بنجاح! سيتم إعادة تحميل الصفحة...', 'success')
        
        # إعادة تشغيل الخدمة لتطبيق التغييرات (اختياري ولكن مفضل لضمان عدم وجود مشاكل في الذاكرة)
        # ملاحظة: هذا قد يقطع الاتصال لحظياً
        import subprocess
        subprocess.call(['sudo', 'systemctl', 'restart', 'pos_qwen'])
        
        return redirect(url_for('settings'))
        
    except Exception as e:
        print(f"Restore Error: {e}")
        flash(f'❌ حدث خطأ أثناء الاستعادة: {str(e)}', 'danger')
        return redirect(url_for('settings'))
# ===================== التقارير والتحليلات =====================
@app.route('/reports/income-statement')
@login_required
@manager_required
def income_statement():

    branch_id = session.get('branch_id') or current_user.branch_id
    today = datetime.now().date()
    start_str = request.args.get('start_date', (today - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_str = request.args.get('end_date', today.strftime('%Y-%m-%d'))
    
    try:
        start_dt = datetime.strptime(start_str, '%Y-%m-%d')
        end_dt = datetime.strptime(end_str, '%Y-%m-%d') + timedelta(days=1)
    except ValueError:
        flash('تاريخ غير صحيح', 'danger')
        return redirect(url_for('dashboard'))

    # جلب الفواتير المكتملة في الفترة المحددة
    inv_q = Invoice.query.filter(
        Invoice.status == 'completed', 
        Invoice.created_at >= start_dt, 
        Invoice.created_at < end_dt
    )
    
    if current_user.role != 'admin': 
        inv_q = inv_q.filter_by(branch_id=branch_id)
        
    invoices = inv_q.all()
    
    total_revenue = sum(inv.total for inv in invoices)
    
    # حساب تكلفة البضاعة المباعة (COGS)
    total_cogs = 0.0
    for inv in invoices:
        items = InvoiceItem.query.filter_by(invoice_id=inv.id).all()
        for item in items:
            book = db.session.get(Book, item.book_id)
            if book:
                total_cogs += (item.quantity * book.cost_price)
                
    gross_profit = total_revenue - total_cogs
    
    # جلب المصروفات
    exp_q = Expense.query.filter(
        Expense.expense_date >= start_dt, 
        Expense.expense_date < end_dt
    )
    if current_user.role != 'admin': 
        exp_q = exp_q.filter_by(branch_id=branch_id)
        
    expenses = exp_q.all()
    total_expenses = sum(e.amount for e in expenses)
    
    net_profit = gross_profit - total_expenses
    
    # تفاصيل المصروفات حسب الحساب
    exp_details = {}
    for e in expenses:
        acc_name = e.account.name if e.account else 'مصروفات عامة'
        exp_details[acc_name] = exp_details.get(acc_name, 0) + e.amount
        
    return render_template('income_statement.html', 
                         total_revenue=total_revenue, 
                         total_cogs=total_cogs, 
                         gross_profit=gross_profit, 
                         total_expenses=total_expenses, 
                         net_profit=net_profit, 
                         exp_details=exp_details, 
                         start_date=start_str, 
                         end_date=end_str)
@app.route('/reports/balance-sheet')
@login_required
@manager_required
def balance_sheet():
    branch_id = session.get('branch_id') or current_user.branch_id
    
    # 1. حساب قيمة المخزون الحالية
    inv_val_query = db.session.query(db.func.sum(BranchInventory.quantity * Book.cost_price))\
        .join(Book, BranchInventory.book_id == Book.id)\
        .filter(BranchInventory.branch_id == branch_id)
    
    if current_user.role != 'admin':
        inv_val_query = inv_val_query.filter(BranchInventory.branch_id == branch_id)
        
    inv_val = inv_val_query.scalar() or 0.0

    # 2. الذمم المدينة (العملاء الذين لم يدفعوا كامل الفواتير الآجلة)
    # ملاحظة: هذا تبسيط، يمكن تطويره ليكون أدق بناءً على مدفوعات العملاء
    credit_invoices_total = db.session.query(db.func.sum(Invoice.total))\
        .filter(Invoice.branch_id == branch_id, Invoice.payment_method == 'credit', Invoice.status == 'completed').scalar() or 0.0
        
    # 3. النقدية (صافي المبيعات النقدية - المصروفات)
    cash_sales = db.session.query(db.func.sum(Invoice.total))\
        .filter(Invoice.branch_id == branch_id, Invoice.payment_method.in_(['cash', 'card']), Invoice.status == 'completed').scalar() or 0.0
        
    total_expenses = db.session.query(db.func.sum(Expense.amount))\
        .filter(Expense.branch_id == branch_id).scalar() or 0.0
        
    net_cash = max(cash_sales - total_expenses, 0)

    # الأصول
    assets = {
        "📦 قيمة المخزون": round(inv_val, 2),
        "💵 النقدية/الخزينة (تقريبي)": round(net_cash, 2),
        "👥 ذمم مدينة (آجل)": round(credit_invoices_total, 2)
    }
    total_assets = sum(assets.values())

    # الالتزامات وحقوق الملكية (تبسيطية للنظام الحالي)
    # في نظام متكامل، نحتاج لجداول منفصلة للالتزامات ورأس المال
    liabilities = {
        "🏢 ديون الموردين": 0.0, # يحتاج لجدول فواتير شراء غير مدفوعة
        "📜 التزامات أخرى": 0.0
    }
    
    # صافي الربح المحتجز (كمثال لحقوق الملكية)
    net_profit_query = db.session.query(db.func.sum(Invoice.total - Expense.amount))\
        .filter(Invoice.branch_id == branch_id, Invoice.status == 'completed')
    # هذه معادلة تقريبية جداً، الأفضل ربطها بجدول الأرباح والخسائر الفعلي
    net_profit = 0.0 
    
    equity = {
        "💰 رأس المال": 0.0, # يجب إدخاله يدوياً أو من إعدادات
        "📈 الأرباح المحتجزة": round(net_profit, 2)
    }
    
    total_liab_equity = sum(liabilities.values()) + sum(equity.values())

    return render_template('balance_sheet.html', 
                         assets=assets, 
                         total_assets=round(total_assets, 2),
                         liabilities=liabilities, 
                         equity=equity, 
                         total_liab_equity=round(total_liab_equity, 2))
@app.route('/reports')
@login_required
def reports():
    branch_id = session.get('branch_id')
    today = datetime.now().date()
    
    # تحديد التواريخ الافتراضية (آخر 30 يوم)
    start_date_str = request.args.get('start_date', (today - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', today.strftime('%Y-%m-%d'))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1) # ليشمل اليوم الأخير بالكامل
    except ValueError:
        flash('تاريخ غير صحيح', 'danger')
        return redirect(url_for('dashboard'))

    # تصفية الفواتير حسب الصلاحيات والتاريخ
    inv_query = Invoice.query.filter(
        Invoice.status == 'completed',
        Invoice.created_at >= start_date,
        Invoice.created_at < end_date
    )
    
    if current_user.role != 'admin':
        if not branch_id:
            flash('لم يتم تحديد فرع', 'warning')
            return redirect(url_for('dashboard'))
        inv_query = inv_query.filter_by(branch_id=branch_id)
        branches = [Branch.query.get(branch_id)]
        selected_branch = branch_id
    else:
        branches = Branch.query.all()
        selected_branch = request.args.get('branch_id', type=int)
        if selected_branch:
            inv_query = inv_query.filter_by(branch_id=selected_branch)
        else:
            selected_branch = None

    invoices = inv_query.order_by(Invoice.created_at.desc()).all()
    
    # حساب المجاميع الأساسية
    total_sales = sum(inv.total for inv in invoices)
    total_discount = sum(inv.discount or 0 for inv in invoices)
    total_tax = sum(inv.tax or 0 for inv in invoices)
    
    # جلب عناصر الفواتير المرتبطة بهذه الفواتير فقط (استعلام واحد سريع بدلاً من حلقات متداخلة)
    invoice_ids = [inv.id for inv in invoices]
    items_data = []
    if invoice_ids:
        # جلب العناصر مع معلومات الكتاب في استعلام واحد
        items_with_books = db.session.query(InvoiceItem, Book.title).join(Book, InvoiceItem.book_id == Book.id)\
                                     .filter(InvoiceItem.invoice_id.in_(invoice_ids)).all()
        
        total_items_count = sum(item.quantity for item, _ in items_with_books)
        
        # تحضير بيانات أفضل الكتب مبيعاً
        book_sales = {}
        for item, title in items_with_books:
            bid = item.book_id
            if bid not in book_sales:
                book_sales[bid] = {'title': title, 'qty': 0, 'revenue': 0}
            book_sales[bid]['qty'] += item.quantity
            book_sales[bid]['revenue'] += item.total
        
        top_books = sorted(book_sales.values(), key=lambda x: x['revenue'], reverse=True)[:10]
    else:
        total_items_count = 0
        top_books = []

    # إحصائيات طرق الدفع
    payment_stats = {}
    for inv in invoices:
        method = inv.payment_method or 'unknown'
        payment_stats[method] = payment_stats.get(method, 0) + inv.total

    # بيانات الرسم البياني اليومي
    daily_sales = {}
    for inv in invoices:
        day_key = inv.created_at.date().strftime('%Y-%m-%d')
        daily_sales[day_key] = daily_sales.get(day_key, 0) + inv.total
    
    daily_chart = [{'date': k, 'value': v} for k, v in sorted(daily_sales.items())]
    
    avg_invoice = total_sales / len(invoices) if invoices else 0
    
    settings = AppSettings.query.first()
    
    return render_template('reports.html', 
                         branches=branches, 
                         selected_branch=selected_branch, 
                         start_date=start_date_str, 
                         end_date=end_date_str,
                         total_sales=total_sales, 
                         total_discount=total_discount, 
                         total_tax=total_tax, 
                         total_items=total_items_count,
                         avg_invoice=avg_invoice, 
                         invoice_count=len(invoices), 
                         top_books=top_books, 
                         payment_stats=payment_stats,
                         daily_chart=daily_chart, 
                         currency=settings.currency if settings else 'د.إ')

    branch_id = session.get('branch_id')
    today = datetime.now().date()
    
    # تحديد التواريخ الافتراضية (آخر 30 يوم)
    start_date_str = request.args.get('start_date', (today - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', today.strftime('%Y-%m-%d'))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1) # ليشمل اليوم الأخير بالكامل
    except ValueError:
        flash('تاريخ غير صحيح', 'danger')
        return redirect(url_for('dashboard'))

    # تصفية الفواتير حسب الصلاحيات والتاريخ
    inv_query = Invoice.query.filter(
        Invoice.status == 'completed',
        Invoice.created_at >= start_date,
        Invoice.created_at < end_date
    )
    
    if current_user.role != 'admin':
        if not branch_id:
            flash('لم يتم تحديد فرع', 'warning')
            return redirect(url_for('dashboard'))
        inv_query = inv_query.filter_by(branch_id=branch_id)
        branches = [Branch.query.get(branch_id)]
        selected_branch = branch_id
    else:
        branches = Branch.query.all()
        selected_branch = request.args.get('branch_id', type=int)
        if selected_branch:
            inv_query = inv_query.filter_by(branch_id=selected_branch)
        else:
            selected_branch = None

    invoices = inv_query.order_by(Invoice.created_at.desc()).all()
    
    # حساب المجاميع الأساسية
    total_sales = sum(inv.total for inv in invoices)
    total_discount = sum(inv.discount or 0 for inv in invoices)
    total_tax = sum(inv.tax or 0 for inv in invoices)
    
    # جلب عناصر الفواتير المرتبطة بهذه الفواتير فقط (استعلام واحد سريع بدلاً من حلقات متداخلة)
    invoice_ids = [inv.id for inv in invoices]
    items_data = []
    if invoice_ids:
        # جلب العناصر مع معلومات الكتاب في استعلام واحد
        items_with_books = db.session.query(InvoiceItem, Book.title).join(Book, InvoiceItem.book_id == Book.id)\
                                     .filter(InvoiceItem.invoice_id.in_(invoice_ids)).all()
        
        total_items_count = sum(item.quantity for item, _ in items_with_books)
        
        # تحضير بيانات أفضل الكتب مبيعاً
        book_sales = {}
        for item, title in items_with_books:
            bid = item.book_id
            if bid not in book_sales:
                book_sales[bid] = {'title': title, 'qty': 0, 'revenue': 0}
            book_sales[bid]['qty'] += item.quantity
            book_sales[bid]['revenue'] += item.total
        
        top_books = sorted(book_sales.values(), key=lambda x: x['revenue'], reverse=True)[:10]
    else:
        total_items_count = 0
        top_books = []

    # إحصائيات طرق الدفع
    payment_stats = {}
    for inv in invoices:
        method = inv.payment_method or 'unknown'
        payment_stats[method] = payment_stats.get(method, 0) + inv.total

    # بيانات الرسم البياني اليومي
    daily_sales = {}
    for inv in invoices:
        day_key = inv.created_at.date().strftime('%Y-%m-%d')
        daily_sales[day_key] = daily_sales.get(day_key, 0) + inv.total
    
    daily_chart = [{'date': k, 'value': v} for k, v in sorted(daily_sales.items())]
    
    avg_invoice = total_sales / len(invoices) if invoices else 0
    
    settings = AppSettings.query.first()
    
    return render_template('reports.html', 
                         branches=branches, 
                         selected_branch=selected_branch, 
                         start_date=start_date_str, 
                         end_date=end_date_str,
                         total_sales=total_sales, 
                         total_discount=total_discount, 
                         total_tax=total_tax, 
                         total_items=total_items_count,
                         avg_invoice=avg_invoice, 
                         invoice_count=len(invoices), 
                         top_books=top_books, 
                         payment_stats=payment_stats,
                         daily_chart=daily_chart, 
                         currency=settings.currency if settings else 'د.إ')
    branch_id = session.get('branch_id')
    today = datetime.now().date()
    start_date = request.args.get('start_date', (today - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', today.strftime('%Y-%m-%d'))
    
    if current_user.role == 'admin':
        branches = Branch.query.all()
        selected_branch = request.args.get('branch_id', type=int)
        branch_filter = Invoice.branch_id == selected_branch if selected_branch else True
    else:
        branches = [Branch.query.get(branch_id)] if branch_id else []
        branch_filter = Invoice.branch_id == branch_id
        selected_branch = branch_id

    invoices = Invoice.query.filter(branch_filter, Invoice.status == 'completed', 
                                    Invoice.created_at >= datetime.strptime(start_date, '%Y-%m-%d'), 
                                    Invoice.created_at <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)).all()
    
    total_sales = sum(inv.total for inv in invoices)
    total_discount = sum(inv.discount for inv in invoices)
    total_tax = sum(inv.tax for inv in invoices)
    total_items = sum(sum(it.quantity for it in InvoiceItem.query.filter_by(invoice_id=inv.id).all()) for inv in invoices)
    avg_invoice = total_sales / len(invoices) if invoices else 0
    
    invoice_ids = [inv.id for inv in invoices]
    all_items = InvoiceItem.query.filter(InvoiceItem.invoice_id.in_(invoice_ids)).all() if invoice_ids else []

    book_sales = {}
    for item in all_items:
        bid = item.book_id
        if bid not in book_sales: 
            book = db.session.get(Book, bid)
            book_sales[bid] = {'title': book.title if book else 'غير معروف', 'qty': 0, 'revenue': 0}
        book_sales[bid]['qty'] += item.quantity
        book_sales[bid]['revenue'] += item.total
        
    top_books = sorted(book_sales.values(), key=lambda x: x['revenue'], reverse=True)[:10]
    
    payment_stats = {}
    for inv in invoices: payment_stats[inv.payment_method] = payment_stats.get(inv.payment_method, 0) + inv.total
    
    daily = {}
    for inv in invoices: 
        d = inv.created_at.date().strftime('%Y-%m-%d')
        daily[d] = daily.get(d, 0) + inv.total
    daily_chart = [{'date': k, 'value': v} for k, v in sorted(daily.items())]
    
    settings = AppSettings.query.first()
    return render_template('reports.html', branches=branches, selected_branch=selected_branch, start_date=start_date, end_date=end_date,
                         total_sales=total_sales, total_discount=total_discount, total_tax=total_tax, total_items=total_items,
                         avg_invoice=avg_invoice, invoice_count=len(invoices), top_books=top_books, payment_stats=payment_stats,
                         daily_chart=daily_chart, currency=settings.currency if settings else 'د.إ')

@app.route('/reports/export')
@login_required
@manager_required
def export_report_excel():
    try:
        branch_id = session.get('branch_id')
        start_date_str = request.args.get('start_date', (datetime.now().date() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end_date_str = request.args.get('end_date', datetime.now().date().strftime('%Y-%m-%d'))
        
        # تحويل التواريخ
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
        except ValueError:
            flash('تاريخ غير صحيح للتصدير', 'danger')
            return redirect(url_for('reports'))

        branch_names = {b.id: b.name for b in Branch.query.all()}
        
        # تصفية الفواتير حسب الصلاحيات
        if current_user.role == 'admin':
            selected_branch = request.args.get('branch_id', type=int)
            if selected_branch:
                invs = Invoice.query.filter(
                    Invoice.branch_id == selected_branch, 
                    Invoice.status == 'completed', 
                    Invoice.created_at >= start_date, 
                    Invoice.created_at < end_date
                ).all()
                branch_name = branch_names.get(selected_branch, 'All')
            else:
                invs = Invoice.query.filter(
                    Invoice.status == 'completed', 
                    Invoice.created_at >= start_date, 
                    Invoice.created_at < end_date
                ).all()
                branch_name = 'All_Branches'
        else:
            invs = Invoice.query.filter(
                Invoice.branch_id == branch_id, 
                Invoice.status == 'completed', 
                Invoice.created_at >= start_date, 
                Invoice.created_at < end_date
            ).all()
            branch_name = branch_names.get(branch_id, 'Branch').replace(' ', '_')

        # تنظيف اسم الفرع لاسم ملف آمن
        safe_branch = "".join(c for c in branch_name if c.isalnum() or c in (' ', '_')).replace(' ', '_')
        fname = f"Sales_Report_{safe_branch}_{start_date_str}_to_{end_date_str}.xlsx"
        
        # تجهيز البيانات للتصدير
        data = []
        for i in invs:
            customer_name = i.customer_obj.name if i.customer_obj else 'Walk-in'
            cashier_name = i.cashier_user.full_name if i.cashier_user else '-'
            payment_method_map = {'cash':'Cash', 'card':'Card', 'transfer':'Transfer', 'credit':'Credit'}
            
            data.append({
                'Invoice_No': i.invoice_number,
                'Date': i.created_at.strftime('%Y-%m-%d %H:%M'),
                'Customer': customer_name,
                'Subtotal': i.subtotal,
                'Discount': i.discount or 0,
                'Tax': i.tax or 0,
                'Total': i.total,
                'Payment_Method': payment_method_map.get(i.payment_method, i.payment_method),
                'Cashier': cashier_name,
                'Branch': branch_names.get(i.branch_id, '-')
            })
            
        df = pd.DataFrame(data)
        
        # إنشاء ملف Excel في الذاكرة
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sales')
            ws = writer.sheets['Sales']
            # تعديل عرض الأعمدة تلقائياً
            for col in ws.columns:
                max_len = max(len(str(cell.value)) if cell.value else 0 for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 25)
                
        output.seek(0)
        return send_file(output, 
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                         as_attachment=True, 
                         download_name=fname)
                         
    except Exception as e:
        print(f"Export Error: {e}")
        traceback.print_exc()
        flash(f'فشل التصدير: {str(e)}', 'danger')
        return redirect(url_for('reports'))

@app.route('/books/<int:id>/statement')
@login_required
def book_statement(id):
    book = db.session.get(Book, id)
    if not book:
        flash('❌ الكتاب غير موجود', 'danger')
        return redirect(url_for('books'))

    sales_items = db.session.query(InvoiceItem, Invoice).join(
        Invoice, InvoiceItem.invoice_id == Invoice.id
    ).filter(
        InvoiceItem.book_id == id,
        Invoice.status == 'completed'
    ).order_by(Invoice.created_at.desc()).all()

    for item, inv in sales_items:
        inv.display_customer = None
        if inv.customer_id:
            inv.display_customer = Customer.query.get(inv.customer_id)

    total_qty_cash = 0
    total_qty_credit = 0
    total_revenue = 0.0

    for item, inv in sales_items:
        total_revenue += item.total
        if inv.payment_method == 'credit':
            total_qty_credit += item.quantity
        else:
            total_qty_cash += item.quantity

    return render_template('book_statement.html', 
                         book=book, 
                         sales=sales_items,
                         total_qty_cash=total_qty_cash,
                         total_qty_credit=total_qty_credit,
                         total_revenue=total_revenue)

# ===================== المحاسبة والمصروفات =====================
@app.route('/accounts')
@login_required
@admin_required
def accounts():
    accounts = Account.query.filter_by(is_active=True).order_by(Account.code).all()
    accounts_data = [{
        'id': acc.id,
        'code': acc.code,
        'name': acc.name,
        'account_type': acc.account_type,
        'parent_id': acc.parent_id
    } for acc in accounts]
    return render_template('accounts.html', accounts_data=accounts_data)

@app.route('/accounts/add', methods=['POST'])
@login_required
@admin_required
def add_account():
    code = request.form.get('code', '').strip()
    name = request.form.get('name', '').strip()
    acc_type = request.form.get('account_type')
    parent = request.form.get('parent_id', type=int)
    if not code or not name: flash('الكود والاسم مطلوبان', 'danger'); return redirect(url_for('accounts'))
    if Account.query.filter_by(code=code).first(): flash('كود الحساب مستخدم بالفعل', 'danger'); return redirect(url_for('accounts'))
    db.session.add(Account(code=code, name=name, account_type=acc_type, parent_id=parent))
    db.session.commit(); flash('تم إضافة الحساب بنجاح', 'success')
    return redirect(url_for('accounts'))

@app.route('/accounts/<int:id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_account(id):
    acc = db.session.get(Account, id)
    if acc: acc.is_active = not acc.is_active; db.session.commit(); flash('تم تحديث الحالة', 'success')
    return redirect(url_for('accounts'))

@app.route('/expenses')
@login_required
@manager_required
def expenses():
    branch_id = session.get('branch_id') or current_user.branch_id
    start = request.args.get('start', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
    q = Expense.query.filter(Expense.expense_date >= start, Expense.expense_date <= end + ' 23:59:59')
    if current_user.role != 'admin': q = q.filter_by(branch_id=branch_id)
    exp_list = q.order_by(Expense.expense_date.desc()).all()
    total = sum(e.amount for e in exp_list)
    by_branch = {}
    for e in exp_list: by_branch[e.branch.name] = by_branch.get(e.branch.name, 0) + e.amount
    return render_template('expenses.html', expenses=exp_list, total=total, by_branch=by_branch, start=start, end=end, accounts=Account.query.filter_by(account_type='expense', is_active=True).all(), branches=Branch.query.filter_by(is_active=True).all())

@app.route('/expenses/add', methods=['POST'])
@login_required
@manager_required
def add_expense():
    try:
        acc_id = request.form.get('account_id', type=int)
        branch_id = request.form.get('branch_id', type=int)
        amount = float(request.form.get('amount', 0))
        desc = request.form.get('description', '')
        exp_date = request.form.get('expense_date')
        if not acc_id or not branch_id or amount <= 0: flash('بيانات غير مكتملة', 'danger'); return redirect(url_for('expenses'))
        db.session.add(Expense(account_id=acc_id, branch_id=branch_id, amount=amount, description=desc, expense_date=datetime.strptime(exp_date, '%Y-%m-%d') if exp_date else datetime.utcnow(), created_by=current_user.id))
        db.session.commit(); flash('تم تسجيل المصروف بنجاح', 'success')
    except Exception as e: db.session.rollback(); flash(f'خطأ: {e}', 'danger')
    return redirect(url_for('expenses'))

@app.route('/expenses/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_expense(id):
    exp = db.session.get(Expense, id)
    if exp: db.session.delete(exp); db.session.commit(); flash('تم حذف المصروف', 'success')
    return redirect(url_for('expenses'))

# ===================== فواتير الشراء والموردين =====================
@app.route('/suppliers')
@login_required
@manager_required
def suppliers(): return render_template('suppliers.html', suppliers=Publisher.query.all())

@app.route('/purchase-invoices')
@login_required
@manager_required
def purchase_invoices():
    invoices = PurchaseInvoice.query.order_by(PurchaseInvoice.invoice_date.desc()).limit(50).all()
    return render_template('purchase_invoices.html', invoices=invoices)

@app.route('/purchase-invoices/<int:id>/pay', methods=['POST'])
@login_required
@manager_required
def pay_purchase_invoice(id):
    inv = db.session.get(PurchaseInvoice, id)
    if inv:
        amount = float(request.form.get('amount', 0))
        if amount > 0:
            inv.paid_amount += amount
            inv.status = 'paid' if inv.paid_amount >= inv.total_amount else 'partial'
            db.session.commit(); flash('تم تسجيل الدفعة بنجاح', 'success')
    return redirect(url_for('purchase_invoices'))

@app.route('/api/parse-purchase-excel', methods=['POST'])
@login_required
def parse_purchase_excel():
    if 'file' not in request.files: return jsonify({'error': 'لم يتم رفع ملف'}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({'error': 'اسم الملف فارغ'}), 400
    try:
        df = pd.read_excel(file)
        all_items, created_count = [], 0
        for _, row in df.iterrows():
            isbn = str(row.get('ISBN', '')).strip()
            title = str(row.get('Title', row.get('العنوان', ''))).strip()
            base_price = float(row.get('سعر الغلاف', row.get('BasePrice', 0)))
            discount_pct = float(row.get('خصم المورد', row.get('Discount', 0)))
            qty = int(row.get('الكمية', row.get('Quantity', 0)))
            if qty <= 0 or base_price <= 0: continue
            selling_price, cost_price = base_price, base_price * (1 - (discount_pct / 100))
            book = None
            if isbn: book = Book.query.filter_by(isbn=isbn).first()
            if not book and title: book = Book.query.filter_by(title=title).first()
            if book: book.cost_price, book.selling_price = cost_price, selling_price
            else:
                book = Book(isbn=isbn if isbn else None, title=title if title else f'كتاب ({isbn})', cost_price=cost_price, selling_price=selling_price, is_active=True)
                db.session.add(book); db.session.flush(); created_count += 1
            all_items.append({'book_id': book.id, 'title': book.title, 'isbn': book.isbn, 'base_price': base_price, 'discount_pct': discount_pct, 'cost_price': cost_price, 'selling_price': selling_price, 'quantity': qty})
        db.session.commit()
        return jsonify({'items': all_items, 'created_count': created_count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'خطأ: {str(e)}'}), 500

@app.route('/purchase-invoices/add', methods=['GET', 'POST'])
@login_required
@manager_required
def add_purchase_invoice():
    if request.method == 'POST':
        try:
            supplier_id = request.form.get('supplier_id', type=int)
            branch_id = request.form.get('branch_id', type=int)
            invoice_num = request.form.get('invoice_number', '').strip()
            paid = float(request.form.get('paid_amount', 0))
            inv_date = request.form.get('invoice_date')
            due_date = request.form.get('due_date')
            notes = request.form.get('notes', '')
            if not invoice_num or not supplier_id: flash('رقم الفاتورة والمورد مطلوبان', 'danger'); return redirect(url_for('add_purchase_invoice'))
            items_data = request.form.get('items_data')
            if not items_data: flash('أضف صنف واحد على الأقل', 'warning'); return redirect(url_for('add_purchase_invoice'))
            items_list = json.loads(items_data)
            total_amount = sum(it['cost_price'] * it['quantity'] for it in items_list)
            status = 'paid' if paid >= total_amount else ('partial' if paid > 0 else 'pending')
            inv = PurchaseInvoice(invoice_number=invoice_num, supplier_id=supplier_id, branch_id=branch_id, total_amount=total_amount, paid_amount=paid, status=status, invoice_date=datetime.strptime(inv_date, '%Y-%m-%d') if inv_date else datetime.utcnow(), due_date=datetime.strptime(due_date, '%Y-%m-%d') if due_date else None, notes=notes, created_by=current_user.id)
            db.session.add(inv); db.session.flush()
            for it in items_list:
                book = db.session.get(Book, it['book_id'])
                if book:
                    book.cost_price, book.selling_price = it['cost_price'], it['selling_price']
                    inv_stock = BranchInventory.query.filter_by(branch_id=branch_id, book_id=book.id).first()
                    if inv_stock: inv_stock.quantity += it['quantity']
                    else: db.session.add(BranchInventory(branch_id=branch_id, book_id=book.id, quantity=it['quantity']))
                    db.session.add(PurchaseInvoiceItem(invoice_id=inv.id, book_id=book.id, quantity=it['quantity'], unit_cost=it['cost_price'], total_cost=it['cost_price'] * it['quantity']))
            db.session.commit()
            flash(f'✅ تم تسجيل الفاتورة {invoice_num} ({len(items_list)} صنف)', 'success')
            return redirect(url_for('purchase_invoices'))
        except Exception as e:
            db.session.rollback(); flash(f'❌ خطأ: {e}', 'danger')
    suppliers = Publisher.query.all()
    branches = Branch.query.filter_by(is_active=True).all()
    books = [{'id': b.id, 'title': b.title, 'isbn': b.isbn, 'base_price': b.selling_price, 'cost_price': b.cost_price} for b in Book.query.filter_by(is_active=True).all()]
    return render_template('add_purchase_invoice.html', suppliers=suppliers, branches=branches, books=books)

# ===================== تحويلات المخزون =====================
@app.route('/transfer-stock')
@login_required
@manager_required
def transfer_stock(): return render_template('transfer_stock.html', branches=Branch.query.filter_by(is_active=True).all(), books=Book.query.filter_by(is_active=True).all())

@app.route('/transfer-stock/create', methods=['POST'])
@login_required
@manager_required
def create_transfer():
    from_branch = request.form.get('from_branch', type=int); to_branch = request.form.get('to_branch', type=int); notes = request.form.get('notes', '')
    if from_branch == to_branch: flash('⚠️ لا يمكن التحويل لنفس الفرع!', 'danger'); return redirect(url_for('transfer_stock'))
    books_data = request.form.get('books_data')
    if not books_data: flash('❌ خطأ: لم تقم بإضافة أي كتب!', 'danger'); return redirect(url_for('transfer_stock'))
    try:
        items_list = json.loads(books_data)
        if not items_list: flash('❌ قائمة الكتب فارغة!', 'danger'); return redirect(url_for('transfer_stock'))
        transfer_num = f"TRF-{datetime.now().strftime('%Y%m%d')}-{StockTransfer.query.count() + 1:05d}"
        transfer = StockTransfer(transfer_number=transfer_num, from_branch_id=from_branch, to_branch_id=to_branch, status='pending', requested_by=current_user.id, notes=notes)
        db.session.add(transfer); db.session.flush()
        for item in items_list: db.session.add(TransferItem(transfer_id=transfer.id, book_id=item['book_id'], quantity=item['qty']))
        db.session.commit(); flash(f'✅ تم إنشاء طلب التحويل {transfer_num} بنجاح ({len(items_list)} كتاب)', 'success')
        return redirect(url_for('transfer_history'))
    except Exception as e: db.session.rollback(); flash(f'❌ خطأ أثناء الحفظ: {str(e)}', 'danger'); return redirect(url_for('transfer_stock'))

@app.route('/transfer-history')
@login_required
def transfer_history(): return render_template('transfer_history.html', transfers=StockTransfer.query.order_by(StockTransfer.created_at.desc()).limit(50).all())

@app.route('/transfer/<int:id>/approve', methods=['POST'])
@login_required
@manager_required
def approve_transfer(id):
    transfer = db.session.get(StockTransfer, id)
    if transfer and transfer.status == 'pending': transfer.status = 'approved'; transfer.approved_by = current_user.id; transfer.shipped_at = datetime.now(); db.session.commit(); flash('تم اعتماد التحويل', 'success')
    return redirect(url_for('transfer_history'))

@app.route('/transfer/<int:id>/ship', methods=['POST'])
@login_required
@manager_required
def ship_transfer(id):
    transfer = db.session.get(StockTransfer, id)
    if transfer and transfer.status == 'approved':
        transfer.status = 'in_transit'
        for item in transfer.items:
            inv = BranchInventory.query.filter_by(branch_id=transfer.from_branch_id, book_id=item.book_id).first()
            if inv and inv.quantity >= item.quantity:
                inv.quantity -= item.quantity
                db.session.add(StockMovement(branch_id=transfer.from_branch_id, book_id=item.book_id, quantity=-item.quantity, movement_type='transfer', reference=transfer.transfer_number, created_by=current_user.id))
        db.session.commit(); flash('تم شحن التحويل', 'success')
    return redirect(url_for('transfer_history'))

@app.route('/transfer/<int:id>/receive', methods=['POST'])
@login_required
def receive_transfer(id):
    transfer = db.session.get(StockTransfer, id)
    if not transfer: flash('التحويل غير موجود', 'danger'); return redirect(url_for('transfer_history'))
    if transfer.status != 'in_transit': flash('لا يمكن استلام هذا التحويل حالياً', 'warning'); return redirect(url_for('transfer_history'))
    try:
        transfer.status = 'completed'; transfer.received_at = datetime.utcnow()
        for item in transfer.items:
            inv = BranchInventory.query.filter_by(branch_id=transfer.to_branch_id, book_id=item.book_id).first()
            if inv: inv.quantity += item.quantity; inv.last_updated = datetime.utcnow()
            else: inv = BranchInventory(branch_id=transfer.to_branch_id, book_id=item.book_id, quantity=item.quantity, last_updated=datetime.utcnow()); db.session.add(inv)
            db.session.add(StockMovement(branch_id=transfer.to_branch_id, book_id=item.book_id, quantity=item.quantity, movement_type='transfer_in', reference=transfer.transfer_number, created_by=current_user.id))
        db.session.commit(); flash(f'✅ تم استلام التحويل {transfer.transfer_number} وتحديث المخزون!', 'success')
    except Exception as e: db.session.rollback(); flash(f'❌ فشل استلام التحويل: {str(e)}', 'danger')
    return redirect(url_for('transfer_history'))

# ===================== APIs مساعدة =====================
@app.route('/api/current-time')
@login_required
def get_current_time():
    return datetime.now().strftime('%Y-%m-%d %H:%M')

@app.route('/api/check-transfer-alerts')
@login_required
def check_transfer_alerts():
    try:
        branch_id = session.get('branch_id') or current_user.branch_id
        if not branch_id: return jsonify({'count': 0})
        count = StockTransfer.query.filter_by(to_branch_id=branch_id, status='in_transit').count()
        return jsonify({'count': count})
    except Exception as e:
        return jsonify({'count': 0})

@app.route('/api/branch-transfer-alerts')
@login_required
def branch_transfer_alerts():
    try:
        branches = Branch.query.filter_by(is_active=True).all()
        result = {}
        for branch in branches:
            count = StockTransfer.query.filter_by(to_branch_id=branch.id, status='in_transit').count()
            result[branch.id] = count
        return jsonify(result)
    except Exception as e:
        return jsonify({})

@app.route('/currencies')
@login_required
@admin_required
def manage_currencies(): return render_template('currencies.html', branches=Branch.query.all())

@app.route('/branch/<int:id>/update-currency', methods=['POST'])
@login_required
@admin_required
def update_branch_currency(id):
    branch = db.session.get(Branch, id)
    if branch: branch.currency = request.form.get('currency'); branch.exchange_rate = request.form.get('exchange_rate', type=float, default=1.0); db.session.commit(); flash('تم تحديث العملة', 'success')
    return redirect(url_for('manage_currencies'))

if __name__ == '__main__':
    init_db()
    print("🚀 يعمل على http://0.0.0.0:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)