# web/pages/auth.py
"""
Модуль простой сессионной авторизации для локальной сети.
Роли: operator, naladchik (наладчик), kontroler (контролер), admin
"""
import uuid
from functools import wraps
from flask import Blueprint, request, redirect, url_for, render_template, session, jsonify, flash
from datetime import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Определение ролей и их прав
ROLES = {
    'operator': {
        'name': 'Оператор',
        'permissions': ['view_monitoring', 'view_history', 'run_scenario']
    },
    'naladchik': {
        'name': 'Наладчик',
        'permissions': ['view_monitoring', 'view_history', 'run_scenario', 
                        'edit_settings', 'calibrate', 'edit_templates', 'view_logs']
    },
    'kontroler': {
        'name': 'Контролер',
        'permissions': ['view_monitoring', 'view_history', 'view_reports', 'view_statistics']
    },
    'admin': {
        'name': 'Администратор',
        'permissions': ['*']  # Полный доступ
    }
}

def get_current_user(db):
    """Получение текущего пользователя из сессии"""
    session_id = session.get('session_id')
    if not session_id:
        return None
    user_data = db.get_session(session_id)
    return user_data

def login_required(f):
    """Декоратор для защиты маршрутов, требующих авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from utils.database import get_database
        from core.config import get_config
        try:
            config = get_config()
            db = get_database(config)
        except:
            # Если БД не инициализирована, пропускаем проверку
            return f(*args, **kwargs)
        
        user = get_current_user(db)
        if not user:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                return jsonify({'error': 'Требуется авторизация'}), 401
            return redirect(url_for('auth.login', next=request.url))
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function

def role_required(*required_roles):
    """Декоратор для проверки роли пользователя"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from utils.database import get_database
            from core.config import get_config
            try:
                config = get_config()
                db = get_database(config)
            except:
                return f(*args, **kwargs)
            
            user = get_current_user(db)
            if not user:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                    return jsonify({'error': 'Требуется авторизация'}), 401
                return redirect(url_for('auth.login', next=request.url))
            
            if user['role'] not in required_roles and 'admin' not in required_roles:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                    return jsonify({'error': 'Недостаточно прав'}), 403
                flash('Недостаточно прав для выполнения этого действия', 'error')
                return redirect(url_for('monitoring.index'))
            
            request.current_user = user
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permission_required(permission):
    """Декоратор для проверки конкретного права доступа"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from utils.database import get_database
            from core.config import get_config
            try:
                config = get_config()
                db = get_database(config)
            except:
                return f(*args, **kwargs)
            
            user = get_current_user(db)
            if not user:
                if request.is_xhr or request.path.startswith('/api/'):
                    return jsonify({'error': 'Требуется авторизация'}), 401
                return redirect(url_for('auth.login', next=request.url))
            
            user_role = user['role']
            role_perms = ROLES.get(user_role, {}).get('permissions', [])
            
            # Админ имеет все права
            if '*' not in role_perms and permission not in role_perms:
                if request.is_xhr or request.path.startswith('/api/'):
                    return jsonify({'error': 'Недостаточно прав'}), 403
                flash('Недостаточно прав для выполнения этого действия', 'error')
                return redirect(url_for('monitoring.index'))
            
            request.current_user = user
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    from utils.database import get_database
    from core.config import get_config
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        next_url = request.form.get('next', '/')
        
        if not username or not password:
            flash('Введите имя пользователя и пароль', 'error')
            return render_template('login.html', next=next_url)
        
        try:
            config = get_config()
            db = get_database(config)
        except Exception as e:
            flash(f'Ошибка подключения к базе данных: {str(e)}', 'error')
            return render_template('login.html', next=next_url)
        
        user = db.verify_user(username, password)
        if user:
            if not user.get('is_active', True):
                flash('Учетная запись деактивирована', 'error')
                return render_template('login.html', next=next_url)
            
            # Создаем сессию
            session_id = str(uuid.uuid4())
            ip_address = request.remote_addr
            db.create_session(user['id'], session_id, ip_address, expires_hours=24)
            
            session['session_id'] = session_id
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            
            flash(f'Добро пожаловать, {user.get("full_name", user["username"])}!', 'success')
            
            if next_url and next_url.startswith('/') and 'logout' not in next_url:
                return redirect(next_url)
            return redirect(url_for('monitoring.index'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    
    next_url = request.args.get('next', '/')
    return render_template('login.html', next=next_url)

@auth_bp.route('/logout')
def logout():
    """Выход из системы"""
    from utils.database import get_database
    from core.config import get_config
    
    session_id = session.get('session_id')
    if session_id:
        try:
            config = get_config()
            db = get_database(config)
            db.delete_session(session_id)
        except:
            pass
    
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    """API для входа (AJAX)"""
    from utils.database import get_database
    from core.config import get_config
    
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Введите имя пользователя и пароль'}), 400
    
    try:
        config = get_config()
        db = get_database(config)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Ошибка БД: {str(e)}'}), 500
    
    user = db.verify_user(username, password)
    if user:
        if not user.get('is_active', True):
            return jsonify({'success': False, 'error': 'Учетная запись деактивирована'}), 403
        
        session_id = str(uuid.uuid4())
        db.create_session(user['id'], session_id, request.remote_addr, expires_hours=24)
        
        session['session_id'] = session_id
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        
        return jsonify({
            'success': True,
            'user': {
                'username': user['username'],
                'role': user['role'],
                'full_name': user.get('full_name', '')
            }
        })
    else:
        return jsonify({'success': False, 'error': 'Неверное имя пользователя или пароль'}), 401

@auth_bp.route('/api/logout', methods=['POST'])
def api_logout():
    """API для выхода (AJAX)"""
    from utils.database import get_database
    from core.config import get_config
    
    session_id = session.get('session_id')
    if session_id:
        try:
            config = get_config()
            db = get_database(config)
            db.delete_session(session_id)
        except:
            pass
    
    session.clear()
    return jsonify({'success': True})

@auth_bp.route('/api/user')
def api_current_user():
    """API для получения данных текущего пользователя"""
    from utils.database import get_database
    from core.config import get_config
    
    try:
        config = get_config()
        db = get_database(config)
    except:
        return jsonify({'authenticated': False})
    
    user = get_current_user(db)
    if user:
        return jsonify({
            'authenticated': True,
            'user': {
                'username': user['username'],
                'role': user['role'],
                'full_name': user.get('full_name', ''),
                'permissions': ROLES.get(user['role'], {}).get('permissions', [])
            }
        })
    else:
        return jsonify({'authenticated': False})