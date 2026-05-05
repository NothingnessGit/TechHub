from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'techhub-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///techhub.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120))
    role = db.Column(db.String(20), default='student')  # student or teacher
    bio = db.Column(db.Text)
    skills = db.Column(db.Text)
    rating = db.Column(db.Float, default=0.0)
    reviews_count = db.Column(db.Integer, default=0)
    wallet_balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    orders_posted = db.relationship('Order', backref='customer', lazy=True, foreign_keys='Order.customer_id')
    bids = db.relationship('Bid', backref='bidder', lazy=True)
    sent_messages = db.relationship('Message', backref='sender', lazy=True, foreign_keys='Message.sender_id')
    received_messages = db.relationship('Message', backref='receiver', lazy=True, foreign_keys='Message.receiver_id')
    reviews_given = db.relationship('Review', backref='reviewer', lazy=True, foreign_keys='Review.reviewer_id')
    reviews_received = db.relationship('Review', backref='reviewee', lazy=True, foreign_keys='Review.reviewee_id')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    budget = db.Column(db.Float, nullable=False)
    deadline = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='open')  # open, in_progress, completed, cancelled
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    bids = db.relationship('Bid', backref='order', lazy=True)

class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    bidder_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    proposal = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reviewee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    orders = Order.query.filter_by(status='open').order_by(Order.created_at.desc()).limit(10).all()
    categories = ['Разработка', 'Дизайн', 'Инженерия', 'Научные исследования', 'Анализ данных', 'Другое']
    return render_template('index.html', orders=orders, categories=categories)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        role = request.form.get('role')
        
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email уже зарегистрирован', 'danger')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            full_name=full_name,
            role=role
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Регистрация успешна! Теперь войдите.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile/<int:user_id>')
def profile(user_id):
    user = User.query.get_or_404(user_id)
    reviews = Review.query.filter_by(reviewee_id=user_id).order_by(Review.created_at.desc()).all()
    return render_template('profile.html', user=user, reviews=reviews)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name')
        current_user.bio = request.form.get('bio')
        current_user.skills = request.form.get('skills')
        db.session.commit()
        flash('Профиль обновлен', 'success')
        return redirect(url_for('profile', user_id=current_user.id))
    
    return render_template('edit_profile.html')

@app.route('/orders')
def orders():
    category = request.args.get('category')
    status = request.args.get('status')
    
    query = Order.query
    
    if category:
        query = query.filter_by(category=category)
    
    if status:
        query = query.filter_by(status=status)
    else:
        query = query.filter(Order.status.in_(['open', 'in_progress']))
    
    orders = query.order_by(Order.created_at.desc()).all()
    categories = ['Разработка', 'Дизайн', 'Инженерия', 'Научные исследования', 'Анализ данных', 'Другое']
    
    return render_template('orders.html', orders=orders, categories=categories, selected_category=category)

@app.route('/order/create', methods=['GET', 'POST'])
@login_required
def create_order():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        budget_str = request.form.get('budget')
        deadline_str = request.form.get('deadline')
        
        # Валидация бюджета
        try:
            budget = float(budget_str)
            if budget < 100:
                flash('Минимальный бюджет должен быть не менее 100₽', 'danger')
                categories = ['Разработка', 'Дизайн', 'Инженерия', 'Научные исследования', 'Анализ данных', 'Другое']
                return render_template('create_order.html', categories=categories)
        except (ValueError, TypeError):
            flash('Некорректная сумма бюджета', 'danger')
            categories = ['Разработка', 'Дизайн', 'Инженерия', 'Научные исследования', 'Анализ данных', 'Другое']
            return render_template('create_order.html', categories=categories)
        
        deadline = None
        if deadline_str:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
        
        order = Order(
            title=title,
            description=description,
            category=category,
            budget=budget,
            deadline=deadline,
            customer_id=current_user.id
        )
        db.session.add(order)
        db.session.commit()
        
        flash('Заказ создан успешно!', 'success')
        return redirect(url_for('order_detail', order_id=order.id))
    
    categories = ['Разработка', 'Дизайн', 'Инженерия', 'Научные исследования', 'Анализ данных', 'Другое']
    return render_template('create_order.html', categories=categories)

@app.route('/order/<int:order_id>')
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    bids = Bid.query.filter_by(order_id=order_id).all()
    return render_template('order_detail.html', order=order, bids=bids)

@app.route('/order/<int:order_id>/bid', methods=['POST'])
@login_required
def place_bid(order_id):
    order = Order.query.get_or_404(order_id)
    
    if order.customer_id == current_user.id:
        flash('Вы не можете откликнуться на собственный заказ', 'danger')
        return redirect(url_for('order_detail', order_id=order_id))
    
    existing_bid = Bid.query.filter_by(order_id=order_id, bidder_id=current_user.id).first()
    if existing_bid:
        flash('Вы уже откликнулись на этот заказ', 'warning')
        return redirect(url_for('order_detail', order_id=order_id))
    
    proposal = request.form.get('proposal')
    amount = float(request.form.get('amount'))
    
    bid = Bid(
        order_id=order_id,
        bidder_id=current_user.id,
        proposal=proposal,
        amount=amount
    )
    db.session.add(bid)
    db.session.commit()
    
    flash('Отклик отправлен!', 'success')
    return redirect(url_for('order_detail', order_id=order_id))

@app.route('/bid/<int:bid_id>/accept', methods=['POST'])
@login_required
def accept_bid(bid_id):
    bid = Bid.query.get_or_404(bid_id)
    order = Order.query.get(bid.order_id)
    
    if order.customer_id != current_user.id:
        flash('У вас нет прав для этого действия', 'danger')
        return redirect(url_for('order_detail', order_id=order.id))
    
    # Проверка баланса заказчика
    if current_user.wallet_balance < bid.amount:
        flash('Недостаточно средств на балансе для принятия отклика. Пожалуйста, пополните кошелек.', 'danger')
        return redirect(url_for('order_detail', order_id=order.id))
    
    # Блокировка суммы на балансе (резервирование)
    bid.status = 'accepted'
    order.status = 'in_progress'
    # Резервируем сумму (списываем с баланса заказчика)
    current_user.wallet_balance -= bid.amount
    db.session.commit()
    
    flash('Отклик принят! Средства зарезервированы.', 'success')
    return redirect(url_for('order_detail', order_id=order.id))

@app.route('/chat')
@login_required
def chat_list():
    # Get all users who have messaged with current user
    messages = Message.query.filter(
        (Message.sender_id == current_user.id) | (Message.receiver_id == current_user.id)
    ).order_by(Message.created_at.desc()).all()
    
    conversations = {}
    for msg in messages:
        other_user_id = msg.sender_id if msg.receiver_id == current_user.id else msg.receiver_id
        if other_user_id not in conversations:
            other_user = User.query.get(other_user_id)
            conversations[other_user_id] = {
                'user': other_user,
                'last_message': msg,
                'unread_count': Message.query.filter_by(
                    sender_id=other_user_id,
                    receiver_id=current_user.id,
                    read=False
                ).count()
            }
    
    return render_template('chat_list.html', conversations=conversations.values())

@app.route('/chat/<int:user_id>', methods=['GET', 'POST'])
@login_required
def chat(user_id):
    other_user = User.query.get_or_404(user_id)
    
    # Проверка: чат возможен только если есть связанный заказ (отклик или заказчик)
    has_connection = False
    
    # Проверяем, есть ли заказы от current_user, где other_user сделал отклик
    orders_by_current = Order.query.filter_by(customer_id=current_user.id).all()
    for order in orders_by_current:
        bid = Bid.query.filter_by(order_id=order.id, bidder_id=user_id).first()
        if bid:
            has_connection = True
            break
    
    # Проверяем, есть ли заказы от other_user, где current_user сделал отклик
    if not has_connection:
        orders_by_other = Order.query.filter_by(customer_id=user_id).all()
        for order in orders_by_other:
            bid = Bid.query.filter_by(order_id=order.id, bidder_id=current_user.id).first()
            if bid:
                has_connection = True
                break
    
    # Также разрешаем чат если уже есть история сообщений
    if not has_connection:
        existing_message = Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
            ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
        ).first()
        if existing_message:
            has_connection = True
    
    if not has_connection and current_user.id != user_id:
        flash('Вы можете писать только пользователям, с которыми у вас есть общий заказ', 'warning')
        return redirect(url_for('chat_list'))
    
    if request.method == 'POST':
        content = request.form.get('content')
        if content:
            message = Message(
                sender_id=current_user.id,
                receiver_id=user_id,
                content=content
            )
            db.session.add(message)
            db.session.commit()
        return redirect(url_for('chat', user_id=user_id))
    
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at.asc()).all()
    
    # Mark messages as read
    for msg in messages:
        if msg.receiver_id == current_user.id:
            msg.read = True
    db.session.commit()
    
    return render_template('chat.html', other_user=other_user, messages=messages)

@app.route('/my_orders')
@login_required
def my_orders():
    """Страница с заказами пользователя: размещенные и отклики"""
    # Заказы, которые создал пользователь
    orders_posted = Order.query.filter_by(customer_id=current_user.id).order_by(Order.created_at.desc()).all()
    
    # Отклики пользователя на заказы
    bids_made = Bid.query.filter_by(bidder_id=current_user.id).order_by(Bid.created_at.desc()).all()
    orders_bidded = [bid.order for bid in bids_made]
    bids_dict = {bid.order_id: bid for bid in bids_made}
    
    return render_template('my_orders.html', 
                         orders_posted=orders_posted, 
                         orders_bidded=orders_bidded,
                         bids=bids_dict)

@app.route('/wallet')
@login_required
def wallet():
    return render_template('wallet.html')

@app.route('/wallet/deposit', methods=['POST'])
@login_required
def deposit():
    amount = float(request.form.get('amount'))
    if amount > 0:
        current_user.wallet_balance += amount
        db.session.commit()
        flash(f'Баланс пополнен на {amount}₽', 'success')
    else:
        flash('Некорректная сумма', 'danger')
    return redirect(url_for('wallet'))

@app.route('/wallet/withdraw', methods=['POST'])
@login_required
def withdraw():
    amount = float(request.form.get('amount'))
    if 0 < amount <= current_user.wallet_balance:
        current_user.wallet_balance -= amount
        db.session.commit()
        flash(f'Заявка на вывод {amount}₽ создана', 'success')
    else:
        flash('Недостаточно средств или некорректная сумма', 'danger')
    return redirect(url_for('wallet'))

@app.route('/review/create', methods=['POST'])
@login_required
def create_review():
    order_id = int(request.form.get('order_id'))
    reviewee_id = int(request.form.get('reviewee_id'))
    rating = int(request.form.get('rating'))
    comment = request.form.get('comment')
    
    order = Order.query.get(order_id)
    if order.customer_id != current_user.id and order.bids[0].bidder_id != current_user.id:
        flash('У вас нет прав для оставления отзыва', 'danger')
        return redirect(url_for('index'))
    
    existing_review = Review.query.filter_by(order_id=order_id, reviewer_id=current_user.id).first()
    if existing_review:
        flash('Вы уже оставляли отзыв для этого заказа', 'warning')
        return redirect(url_for('order_detail', order_id=order_id))
    
    review = Review(
        reviewer_id=current_user.id,
        reviewee_id=reviewee_id,
        order_id=order_id,
        rating=rating,
        comment=comment
    )
    db.session.add(review)
    
    # Update user rating
    reviewee = User.query.get(reviewee_id)
    total_rating = sum(r.rating for r in Review.query.filter_by(reviewee_id=reviewee_id).all()) + rating
    total_reviews = reviewee.reviews_count + 1
    reviewee.rating = total_rating / total_reviews
    reviewee.reviews_count = total_reviews
    
    db.session.commit()
    
    flash('Отзыв оставлен!', 'success')
    return redirect(url_for('profile', user_id=reviewee_id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
