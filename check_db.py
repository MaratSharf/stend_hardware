import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='stend_db',
    user='stend_user',
    password='Alexej@12'
)
cur = conn.cursor()

# Проверка таблиц
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
tables = [r[0] for r in cur.fetchall()]
print("Таблицы в БД:", tables)

# Проверка пользователей
if 'users' in tables:
    cur.execute("SELECT username, role, is_active FROM users")
    users = cur.fetchall()
    print("\nПользователи:")
    for u in users:
        print(f"  {u[0]} ({u[1]}) - активен: {u[2]}")
else:
    print("\nТаблица users НЕ найдена!")

# Проверка сессий
if 'sessions' in tables:
    cur.execute("SELECT COUNT(*) FROM sessions")
    count = cur.fetchone()[0]
    print(f"\nСессий в БД: {count}")
else:
    print("\nТаблица sessions НЕ найдена!")

conn.close()