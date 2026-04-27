#!/usr/bin/env python3
"""
Скрипт для создания первого пользователя-администратора.
Запуск: python create_admin.py <username> <password> [full_name]
Пример: python create_admin.py admin Admin@123 "Администратор"
"""

import sys
import os

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import get_config
from utils.database import get_database

def create_admin(username: str, password: str, full_name: str = "Администратор"):
    """Создание пользователя с ролью admin"""
    
    # Проверка сложности пароля
    if len(password) < 6:
        print("❌ Ошибка: пароль должен быть не менее 6 символов")
        return False
    
    try:
        config = get_config()
        db = get_database(config)
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        print("Убедитесь, что PostgreSQL запущен и конфигурация верна")
        return False
    
    # Проверяем, существует ли уже пользователь с таким именем
    existing_user = db.get_user_by_username(username)
    if existing_user:
        print(f"❌ Пользователь '{username}' уже существует")
        return False
    
    # Создаем пользователя
    user_id = db.create_user(username, password, role='admin', full_name=full_name)
    
    if user_id:
        print(f"✅ Администратор успешно создан!")
        print(f"   ID: {user_id}")
        print(f"   Имя пользователя: {username}")
        print(f"   Полное имя: {full_name}")
        print(f"   Роль: admin")
        print(f"\nТеперь вы можете войти в систему под этими учетными данными")
        return True
    else:
        print("❌ Не удалось создать пользователя")
        return False

def main():
    if len(sys.argv) < 3:
        print("Использование: python create_admin.py <username> <password> [full_name]")
        print("Пример: python create_admin.py admin Admin@123 \"Администратор\"")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    full_name = sys.argv[3] if len(sys.argv) > 3 else "Администратор"
    
    success = create_admin(username, password, full_name)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
