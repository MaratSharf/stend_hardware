#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт импорта tools.csv в таблицу PostgreSQL.
Очищает таблицу tools и заполняет её заново из CSV.
"""

import csv
import os
import sys

import psycopg2
import yaml


def load_config():
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_db_connection(config):
    db_cfg = config['database']
    password = os.environ.get('DB_PASSWORD')
    if not password:
        # Попробуем прочитать из .env файла
        if os.path.exists('.env'):
            with open('.env', 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith('DB_PASSWORD='):
                        password = line.strip().split('=', 1)[1].strip().strip('"\'')
                        break
    if not password:
        print("ERROR: Не найден пароль БД. Установите переменную окружения DB_PASSWORD или укажите в .env")
        sys.exit(1)

    conn = psycopg2.connect(
        host=db_cfg['host'],
        port=db_cfg['port'],
        dbname=db_cfg['dbname'],
        user=db_cfg['user'],
        password=password
    )
    return conn


def detect_encoding(file_path):
    """Пробуем разные кодировки для чтения CSV."""
    for encoding in ['cp1251', 'utf-8-sig', 'utf-8', 'cp1252']:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1024)
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
    return 'utf-8'


def import_tools(csv_path='tools.csv'):
    config = load_config()
    conn = get_db_connection(config)
    cursor = conn.cursor()

    encoding = detect_encoding(csv_path)
    print(f"Detected encoding: {encoding}")

    with open(csv_path, 'r', encoding=encoding, newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("CSV файл пуст или не содержит данных.")
        return

    print(f"Найдено записей в CSV: {len(rows)}")

    # Очищаем таблицу
    cursor.execute("DELETE FROM tools")
    print("Таблица tools очищена.")

    # Вставляем данные
    insert_sql = """
        INSERT INTO tools
        (tool_id, category_ru, category_en, name_ru, name_en,
         description, subroutine_ru, subroutine_en, project_name, project_name_display)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    inserted = 0
    for row in rows:
        cursor.execute(insert_sql, (
            row.get('tool_id', ''),
            row.get('category_ru', ''),
            row.get('category_en', ''),
            row.get('name_ru', ''),
            row.get('name_en', ''),
            row.get('description', ''),
            row.get('subroutine_ru', ''),
            row.get('subroutine_en', ''),
            row.get('project_name', ''),
            row.get('project_name_display', ''),
        ))
        inserted += 1

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Успешно импортировано {inserted} инструментов.")


if __name__ == '__main__':
    import_tools()
