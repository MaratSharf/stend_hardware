import psycopg2

# Проверка 1: подключение к postgres
try:
    conn = psycopg2.connect(host="localhost", port=5432, dbname="postgres", user="postgres", password="postgres")
    print("OK: Подключение к postgres (admin) успешно")
    cur = conn.cursor()
    cur.execute("SELECT datname FROM pg_database WHERE datname = 'stend_db'")
    row = cur.fetchone()
    if row:
        print(f"OK: База stend_db существует")
    else:
        print("ERROR: База stend_db НЕ существует")
    cur.execute("SELECT usename FROM pg_user WHERE usename = 'stend_user'")
    row = cur.fetchone()
    if row:
        print(f"OK: Пользователь stend_user существует")
    else:
        print("ERROR: Пользователь stend_user НЕ существует")
    cur.close()
    conn.close()
except Exception as e:
    print(f"ERROR admin: {e}")

# Проверка 2: подключение к stend_db с правильными кредами
print("\n--- Попытка подключения к stend_db ---")
try:
    conn = psycopg2.connect(host="localhost", port=5432, dbname="stend_db", user="stend_user", password="stend_password")
    print("OK: Подключение к stend_db успешно")
    conn.close()
except Exception as e:
    print(f"ERROR stend_db: {e}")
