from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# Создаем приложение Flask
app = Flask(__name__)

#КОНФИГУРАЦИЯ
# Определяем, где запущено приложение
IS_PYTHONANYWHERE = 'pythonanywhere' in os.environ.get('HOME', '')

if IS_PYTHONANYWHERE:
    # Настройки для PythonAnywhere
    app.config['SECRET_KEY'] = 'pythonanywhere-secret-key-change-this'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/aphezbtw/game_collection/games.db'
    app.config['DEBUG'] = False
else:
    # Настройки для локального сервера
    app.config['SECRET_KEY'] = 'dev-secret-key-for-local-development'
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "games.db")}'
    app.config['DEBUG'] = True

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#ИНИЦИАЛИЗАЦИЯ
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

#МОДЕЛИ БАЗЫ ДАННЫХ
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
    return User.query.get(int(user_id))

#ФУНКЦИИ ПОМОЩНИКИ
def init_database():
    """Инициализация базы данных и создание тестовых данных"""
    with app.app_context():
        # Создаем таблицы
        db.create_all()

        # Создаем тестового пользователя
        if not User.query.first():
            admin = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123')
            )
            db.session.add(admin)

            # Добавляем тестовые игры
            sample_games = [
                Game(
                    title='The Witcher 3: Wild Hunt',
                    genre='RPG, Action',
                    developer='CD Projekt Red',
                    release_year=2015,
                    playtime_hours=100,
                    description='Эпическая ролевая игра в открытом мире с богатым сюжетом и персонажами.',
                    platforms='PC, PlayStation 4, Xbox One, Nintendo Switch',
                    requirements='Процессор: Intel Core i5-2500K\nОперативная память: 6 GB\nВидеокарта: NVIDIA GeForce GTX 660',
                    instructions='1. Исследуйте мир\n2. Выполняйте квесты\n3. Развивайте навыки',
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
                    instructions='1. Кастомизируйте персонажа\n2. Исследуйте Найт-Сити\n3. Прокачивайте навыки',
                    rating=8.5,
                    user_id=1
                )
            ]

            for game in sample_games:
                db.session.add(game)

            db.session.commit()

#МАРШРУТЫ
@app.route('/')
def index():
    """Главная страница"""
    games = Game.query.order_by(Game.created_at.desc()).all()
    return render_template('index.html', games=games)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация пользователя"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        # Валидация
        if not username or not email or not password:
            flash('Все поля обязательны для заполнения', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email уже зарегистрирован', 'error')
            return redirect(url_for('register'))

        # Создание пользователя
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
    """Вход в систему"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('index'))

        flash('Неверное имя пользователя или пароль', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

@app.route('/add_game', methods=['GET', 'POST'])
@login_required
def add_game():
    """Добавление новой игры"""
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

            # Валидация обязательных полей
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

        except ValueError:
            flash('Некорректные данные в числовых полях', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении игры: {str(e)}', 'error')

    return render_template('add_game.html')

@app.route('/game/<int:game_id>')
def game_detail(game_id):
    """Страница с детальной информацией об игре"""
    game = Game.query.get_or_404(game_id)
    return render_template('game_detail.html', game=game)

@app.route('/my_games')
@login_required
def my_games():
    """Страница с играми текущего пользователя"""
    games = Game.query.filter_by(user_id=current_user.id).order_by(Game.created_at.desc()).all()
    return render_template('index.html', games=games, my_games=True)

@app.route('/delete_game/<int:game_id>', methods=['POST'])
@login_required
def delete_game(game_id):
    """Удаление игры"""
    game = Game.query.get_or_404(game_id)

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
    """Поиск игр"""
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

#ОБРАБОТЧИКИ ОШИБОК
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    flash('Внутренняя ошибка сервера. Пожалуйста, попробуйте позже.', 'error')
    return redirect(url_for('index'))

#ЗАПУСК ПРИЛОЖЕНИЯ
if __name__ == '__main__':
    # Инициализируем базу данных
    with app.app_context():
        init_database()

    app.run(host='0.0.0.0', port=5000, debug=True)

