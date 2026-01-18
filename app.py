from flask import Flask, render_template, request, redirect, url_for, flash, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gamecollection-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'games.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Модели базы данных
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    games = db.relationship('Game', backref='author', lazy=True, cascade='all, delete-orphan')

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    genre = db.Column(db.String(100), nullable=False)
    developer = db.Column(db.String(150), nullable=False)
    release_year = db.Column(db.Integer, nullable=False)
    playtime_hours = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)
    platforms = db.Column(db.String(200), nullable=False)
    requirements = db.Column(db.Text)
    instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Float, default=0.0)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Инициализация базы данных
def init_db():
    with app.app_context():
        db.create_all()
        # Создаем тестового пользователя, если база пуста
        if not User.query.first():
            admin = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123')
            )
            db.session.add(admin)
            
            # Добавляем несколько тестовых игр
            sample_games = [
                Game(
                    title='The Witcher 3: Wild Hunt',
                    genre='RPG, Action',
                    developer='CD Projekt Red',
                    release_year=2015,
                    playtime_hours=100,
                    description='Эпическая ролевая игра в открытом мире с богатым сюжетом и персонажами.',
                    platforms='PC, PlayStation 4, Xbox One, Nintendo Switch',
                    requirements='Процессор: Intel Core i5-2500K 3.3GHz\nОперативная память: 6 GB\nВидеокарта: NVIDIA GeForce GTX 660',
                    instructions='1. Исследуйте мир, выполняйте квесты\n2. Развивайте навыки Геральта\n3. Принимайте моральные решения\n4. Собирайте лучшие доспехи и оружие',
                    rating=9.7,
                    user_id=1
                ),
                Game(
                    title='Cyberpunk 2077',
                    genre='Action RPG',
                    developer='CD Projekt Red',
                    release_year=2020,
                    playtime_hours=60,
                    description='Приключение в открытом мире в темном будущем Найт-Сити.',
                    platforms='PC, PlayStation 5, Xbox Series X/S',
                    requirements='Процессор: Intel Core i7-4790\nОперативная память: 12 GB\nВидеокарта: NVIDIA GeForce GTX 1060',
                    instructions='1. Кастомизируйте своего персонажа\n2. Выбирайте стиль игры: скрытность или экшен\n3. Прокачивайте навыки\n4. Исследуйте каждый уголок Найт-Сити',
                    rating=8.5,
                    user_id=1
                ),
                Game(
                    title='Red Dead Redemption 2',
                    genre='Action-Adventure',
                    developer='Rockstar Games',
                    release_year=2018,
                    playtime_hours=80,
                    description='История банды Ван дер Линде на Диком Западе.',
                    platforms='PC, PlayStation 4, Xbox One',
                    requirements='Процессор: Intel Core i7-4770K\nОперативная память: 12 GB\nВидеокарта: NVIDIA GeForce GTX 1060',
                    instructions='1. Исследуйте открытый мир\n2. Заботьтесь о своей лошади\n3. Выполняйте основные и побочные квесты\n4. Участвуйте в перестрелках и ограблениях',
                    rating=9.8,
                    user_id=1
                )
            ]
            
            for game in sample_games:
                db.session.add(game)
            
            db.session.commit()

init_db()

# Маршруты
@app.route('/')
def index():
    games = Game.query.order_by(Game.created_at.desc()).all()
    return render_template('index.html', games=games)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not email or not password:
            flash('Все поля обязательны для заполнения', 'error')
            return redirect(url_for('register'))
        
        if len(username) < 3:
            flash('Имя пользователя должно содержать минимум 3 символа', 'error')
            return redirect(url_for('register'))
        
        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email уже зарегистрирован', 'error')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при регистрации: {str(e)}', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Введите имя пользователя и пароль', 'error')
            return redirect(url_for('login'))
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Вы успешно вошли в систему!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        
        flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

@app.route('/add_game', methods=['GET', 'POST'])
@login_required
def add_game():
    if request.method == 'POST':
        try:
            game = Game(
                title=request.form.get('title', '').strip(),
                genre=request.form.get('genre', '').strip(),
                developer=request.form.get('developer', '').strip(),
                release_year=int(request.form.get('release_year', 2023)),
                playtime_hours=int(request.form.get('playtime_hours', 10)),
                description=request.form.get('description', '').strip(),
                platforms=request.form.get('platforms', '').strip(),
                requirements=request.form.get('requirements', '').strip(),
                instructions=request.form.get('instructions', '').strip(),
                rating=float(request.form.get('rating', 7.0)),
                user_id=current_user.id
            )
            
            if not game.title or not game.genre or not game.developer:
                flash('Заполните обязательные поля: название, жанр и разработчик', 'error')
                return redirect(url_for('add_game'))
            
            if game.rating < 0 or game.rating > 10:
                flash('Рейтинг должен быть от 0 до 10', 'error')
                return redirect(url_for('add_game'))
            
            db.session.add(game)
            db.session.commit()
            
            flash('Игра успешно добавлена в коллекцию!', 'success')
            return redirect(url_for('index'))
            
        except ValueError as e:
            flash('Некорректные данные в числовых полях (год, время, рейтинг)', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении игры: {str(e)}', 'error')
    
    return render_template('add_game.html')

@app.route('/game/<int:game_id>')
def game_detail(game_id):
    game = db.session.get(Game, game_id)
    if not game:
        flash('Игра не найдена', 'error')
        return redirect(url_for('index'))
    return render_template('game_detail.html', game=game)

@app.route('/my_games')
@login_required
def my_games():
    games = Game.query.filter_by(user_id=current_user.id).order_by(Game.created_at.desc()).all()
    return render_template('index.html', games=games, my_games=True)

@app.route('/delete_game/<int:game_id>', methods=['POST'])
@login_required
def delete_game(game_id):
    game = db.session.get(Game, game_id)
    
    if not game:
        flash('Игра не найдена', 'error')
        return redirect(url_for('index'))
    
    if game.user_id != current_user.id:
        flash('Вы не можете удалить эту игру', 'error')
        return redirect(url_for('index'))
    
    try:
        db.session.delete(game)
        db.session.commit()
        flash('Игра успешно удалена', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении: {str(e)}', 'error')
    
    return redirect(url_for('my_games'))

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    if query:
        games = Game.query.filter(
            db.or_(
                Game.title.ilike(f'%{query}%'),
                Game.genre.ilike(f'%{query}%'),
                Game.developer.ilike(f'%{query}%'),
                Game.description.ilike(f'%{query}%')
            )
        ).order_by(Game.created_at.desc()).all()
    else:
        games = Game.query.order_by(Game.created_at.desc()).all()
    
    return render_template('index.html', games=games, search_query=query)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    flash('Внутренняя ошибка сервера. Пожалуйста, попробуйте позже.', 'error')
    return redirect(url_for('index'))

# Главная функция для PythonAnywhere
def create_app():
    return app

if __name__ == '__main__':
    app.run(debug=True)