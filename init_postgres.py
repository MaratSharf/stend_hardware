import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Получаем пароль из переменной окружения или запрашиваем у пользователя
db_password = os.getenv('DB_PASSWORD')
if not db_password:
    db_password = input("Введите пароль для пользователя stend_user: ")

# Получаем пароль администратора PostgreSQL
pg_admin_password = os.getenv('PG_ADMIN_PASSWORD')
if not pg_admin_password:
    pg_admin_password = input("Введите пароль администратора PostgreSQL (postgres): ")

# Создание базы и пользователя через admin
conn = psycopg2.connect(host="localhost", port=5432, dbname="postgres", user="postgres", password=pg_admin_password)
conn.autocommit = True
cur = conn.cursor()

# Создаём пользователя
cur.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'stend_user') THEN
            CREATE USER stend_user WITH PASSWORD %s;
        END IF;
    END
    $$;
""", (db_password,))
print("OK: Пользователь stend_user создан (или уже существует)")

# Создаём базу
cur.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'stend_db') THEN
            CREATE DATABASE stend_db OWNER stend_user;
        END IF;
    END
    $$;
""")
print("OK: База stend_db создана (или уже существует)")

# Права
cur.execute("GRANT ALL PRIVILEGES ON DATABASE stend_db TO stend_user;")
print("OK: Права выданы")

cur.close()
conn.close()
print("Готово. Теперь можно запускать python run.py")
