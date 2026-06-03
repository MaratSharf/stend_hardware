from utils.database import get_database
from core.config import get_config

config = get_config()
db = get_database(config)

print("=== Пользователи в базе ===")
users = db.get_all_users()
for user in users:
    print(f"  {user['username']} ({user['role']}) - активен: {user.get('is_active', True)}")
