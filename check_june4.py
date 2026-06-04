from utils.database import get_database
from core.config import get_config

db = get_database(get_config())

# Проверка записей за 2026-06-04
query = """
    SELECT COUNT(*) as cnt, DATE(timestamp) as date_val
    FROM inspection_results 
    WHERE timestamp >= '2026-06-04' 
    GROUP BY DATE(timestamp) 
    ORDER BY date_val DESC
"""

with db.get_connection() as cur:
    cur.execute(query)
    rows = cur.fetchall()
    print("Записи за 2026-06-04 и позже:")
    for row in rows:
        print(f"  {row['date_val']}: {row['cnt']} записей")
    
    if not rows:
        print("  Нет данных за этот период")

# Проверка записей за 2026-06-03
query2 = """
    SELECT COUNT(*) as cnt, DATE(timestamp) as date_val
    FROM inspection_results 
    WHERE timestamp >= '2026-06-03' AND timestamp < '2026-06-04'
    GROUP BY DATE(timestamp)
"""

with db.get_connection() as cur:
    cur.execute(query2)
    rows2 = cur.fetchall()
    print("\nЗаписи за 2026-06-03:")
    for row in rows2:
        print(f"  {row['date_val']}: {row['cnt']} записей")
