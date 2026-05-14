import psycopg2

# Создание базы и пользователя через admin
conn = psycopg2.connect(host="localhost", port=5432, dbname="postgres", user="postgres", password="admin")
conn.autocommit = True
cur = conn.cursor()

# Создаём пользователя
cur.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'stend_user') THEN
            CREATE USER stend_user WITH PASSWORD 'Alexej@12';
        END IF;
    END
    $$;
""")
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
