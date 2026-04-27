# web/pages/users.py
# -*- coding: utf-8 -*-
"""
Blueprint для страницы управления пользователями и ролями.
Доступно только администраторам.
"""

from flask import Blueprint, render_template, jsonify, request, current_app
from web.pages.auth import login_required, role_required
from utils.database import get_database
from core.config import get_config

users_bp = Blueprint('users', __name__)


@users_bp.route('/users')
@login_required
@role_required('admin')
def users_page():
    """Страница управления пользователями"""
    from web.pages.auth import get_current_user
    from utils.database import get_database
    from core.config import get_config
    
    config_obj = get_config()
    db = get_database(config_obj)
    current_user = get_current_user(db)
    
    return render_template('users.html', active_page='users', current_user=current_user)


@users_bp.route('/api/users', methods=['GET'])
@login_required
@role_required('admin')
def api_get_users():
    """Получение списка всех пользователей"""
    try:
        config = get_config()
        db = get_database(config)
        users = db.get_all_users()
        
        # Убираем хеши паролей из ответа
        for user in users:
            if 'password_hash' in user:
                del user['password_hash']
        
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_get_users")
        return jsonify({'success': False, 'error': str(e)}), 500


@users_bp.route('/api/users', methods=['POST'])
@login_required
@role_required('admin')
def api_create_user():
    """Создание нового пользователя"""
    try:
        data = request.get_json()
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip()
        role = data.get('role', 'operator')
        is_active = data.get('is_active', True)
        
        # Валидация
        if not username:
            return jsonify({'success': False, 'error': 'Имя пользователя обязательно'}), 400
        
        if not password or len(password) < 4:
            return jsonify({'success': False, 'error': 'Пароль должен быть не менее 4 символов'}), 400
        
        valid_roles = ['operator', 'kontroler', 'naladchik', 'admin']
        if role not in valid_roles:
            return jsonify({'success': False, 'error': 'Неверная роль'}), 400
        
        config = get_config()
        db = get_database(config)
        
        # Проверка существования пользователя
        existing = db.get_user_by_username(username)
        if existing:
            return jsonify({'success': False, 'error': 'Пользователь с таким именем уже существует'}), 400
        
        # Создание пользователя
        user_id = db.create_user(username, password, role, full_name)
        
        if not is_active:
            db.deactivate_user(user_id)
        
        current_app.logger.info(f"Создан пользователь {username} (роль: {role})")
        
        return jsonify({
            'success': True, 
            'message': 'Пользователь создан',
            'user_id': user_id
        })
    except Exception as e:
        current_app.logger.exception("Ошибка в api_create_user")
        return jsonify({'success': False, 'error': str(e)}), 500


@users_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
@role_required('admin')
def api_update_user(user_id):
    """Обновление данных пользователя"""
    try:
        data = request.get_json()
        
        config = get_config()
        db = get_database(config)
        
        # Проверка существования пользователя
        user = db.get_user_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip()
        role = data.get('role', user['role'])
        is_active = data.get('is_active', user['is_active'])
        
        # Валидация имени пользователя
        if not username:
            return jsonify({'success': False, 'error': 'Имя пользователя обязательно'}), 400
        
        # Проверка уникальности имени (если изменилось)
        if username != user['username']:
            existing = db.get_user_by_username(username)
            if existing and existing['id'] != user_id:
                return jsonify({'success': False, 'error': 'Пользователь с таким именем уже существует'}), 400
        
        # Обновление данных
        with db.get_connection() as cursor:
            # Обновляем основные поля
            cursor.execute("""
                UPDATE users 
                SET username = %s, full_name = %s, role = %s, is_active = %s
                WHERE id = %s
            """, (username, full_name, role, is_active, user_id))
            
            # Обновляем пароль, если указан
            if password:
                import bcrypt
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cursor.execute("""
                    UPDATE users SET password_hash = %s WHERE id = %s
                """, (password_hash, user_id))
        
        current_app.logger.info(f"Обновлен пользователь {username} (id: {user_id})")
        
        return jsonify({'success': True, 'message': 'Пользователь обновлен'})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_update_user")
        return jsonify({'success': False, 'error': str(e)}), 500


@users_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
@role_required('admin')
def api_delete_user(user_id):
    """Удаление пользователя"""
    try:
        config = get_config()
        db = get_database(config)
        
        # Проверка существования пользователя
        user = db.get_user_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404
        
        # Нельзя удалить последнего администратора
        admins = [u for u in db.get_all_users() if u['role'] == 'admin']
        if user['role'] == 'admin' and len(admins) <= 1:
            return jsonify({
                'success': False, 
                'error': 'Нельзя удалить последнего администратора'
            }), 400
        
        db.delete_user(user_id)
        current_app.logger.info(f"Удален пользователь {user['username']} (id: {user_id})")
        
        return jsonify({'success': True, 'message': 'Пользователь удален'})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_delete_user")
        return jsonify({'success': False, 'error': str(e)}), 500
