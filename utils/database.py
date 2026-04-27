# utils/database.py
import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import bcrypt

class Database:
    def __init__(self, config: dict):
        self.config = config
        db_cfg = config.get('database', {})
        self.db_type = db_cfg.get('type', 'postgresql')
        if self.db_type != 'postgresql':
            raise ValueError("Only PostgreSQL is supported in this version")
        self.conn_params = {
            'host': db_cfg['host'],
            'port': db_cfg['port'],
            'dbname': db_cfg['dbname'],
            'user': db_cfg['user'],
            'password': db_cfg['password']
        }
        self.init_db()

    @contextmanager
    def get_connection(self):
        conn = psycopg2.connect(**self.conn_params)
        conn.autocommit = False
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def init_db(self):
        """Создание всех необходимых таблиц"""
        with self.get_connection() as cursor:
            # Таблица пользователей с ролями и хешированными паролями
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'operator',
                    full_name TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")

            # Таблица сессий для простой сессионной авторизации
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL UNIQUE,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    ip_address TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)")

            # Таблица результатов инспекций
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inspection_results (
                    id SERIAL PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    result TEXT NOT NULL,
                    raw TEXT,
                    image_path TEXT,
                    scenario TEXT,
                    project_name TEXT,
                    sensor_d1 INTEGER,
                    sensor_d2 INTEGER,
                    sensor_d3 INTEGER,
                    sensor_d4 INTEGER,
                    tumbler_a INTEGER,
                    tumbler_b INTEGER,
                    order_number TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_inspection_timestamp ON inspection_results(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_inspection_result ON inspection_results(result)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_inspection_order ON inspection_results(order_number)")

            # Таблица ежедневной статистики
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    id SERIAL PRIMARY KEY,
                    date TEXT NOT NULL UNIQUE,
                    total_count INTEGER DEFAULT 0,
                    ok_count INTEGER DEFAULT 0,
                    ng_count INTEGER DEFAULT 0,
                    ok_percent REAL DEFAULT 0.0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date)")

            # Таблица инструментов (вместо Excel)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tools (
                    id SERIAL PRIMARY KEY,
                    tool_id TEXT NOT NULL UNIQUE,
                    category_ru TEXT,
                    category_en TEXT,
                    name_ru TEXT,
                    name_en TEXT,
                    description TEXT,
                    subroutine_ru TEXT,
                    subroutine_en TEXT,
                    project_name TEXT,
                    project_name_display TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tools_tool_id ON tools(tool_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tools_category ON tools(category_ru)")

            # Таблица заказов (для совместимости с MES, в MV не используется)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS production_orders (
                    id SERIAL PRIMARY KEY,
                    order_number TEXT NOT NULL UNIQUE,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    completed_quantity INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'buffer',
                    priority INTEGER NOT NULL DEFAULT 0,
                    camera_project TEXT,
                    notes TEXT,
                    current_station INTEGER DEFAULT 0,
                    original_station INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON production_orders(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_number ON production_orders(order_number)")

    # ==================== МЕТОДЫ ДЛЯ INSPECTION RESULTS ====================
    def add_result(self, result: str, image_path: Optional[str] = None,
                   scenario: str = '', project_name: str = '',
                   sensors: Optional[Dict] = None, raw: Optional[str] = None,
                   order_number: Optional[str] = None) -> int:
        timestamp = datetime.now().isoformat()
        sensors = sensors or {}
        with self.get_connection() as cursor:
            cursor.execute("""
                INSERT INTO inspection_results
                (timestamp, result, raw, image_path, scenario, project_name,
                 sensor_d1, sensor_d2, sensor_d3, sensor_d4,
                 tumbler_a, tumbler_b, order_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (timestamp, result, raw, image_path, scenario, project_name,
                  sensors.get('d1', 0), sensors.get('d2', 0), sensors.get('d3', 0),
                  sensors.get('d4', 0), sensors.get('tumbler_a', 0),
                  sensors.get('tumbler_b', 0), order_number))
            row = cursor.fetchone()
            return row['id'] if row else 0

    def get_results(self, limit: int = 100, offset: int = 0,
                    result_filter: Optional[str] = None,
                    date_from: Optional[str] = None,
                    date_to: Optional[str] = None) -> List[Dict]:
        query = "SELECT * FROM inspection_results WHERE 1=1"
        params = []
        if result_filter:
            query += " AND result = %s"
            params.append(result_filter)
        if date_from:
            query += " AND timestamp >= %s"
            params.append(date_from)
        if date_to:
            # Включаем весь день до 23:59:59
            date_to_inclusive = date_to + ' 23:59:59'
            query += " AND timestamp <= %s"
            params.append(date_to_inclusive)
        query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        with self.get_connection() as cursor:
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_result_by_id(self, result_id: int) -> Optional[Dict]:
        with self.get_connection() as cursor:
            cursor.execute("SELECT * FROM inspection_results WHERE id = %s", (result_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_statistics(self, date_from: Optional[str] = None,
                       date_to: Optional[str] = None) -> Dict:
        query = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN result = 'OK' THEN 1 ELSE 0 END) as ok_count,
                SUM(CASE WHEN result = 'NG' THEN 1 ELSE 0 END) as ng_count
            FROM inspection_results
            WHERE 1=1
        """
        params = []
        if date_from:
            query += " AND timestamp >= %s"
            params.append(date_from)
        if date_to:
            date_to_inclusive = date_to + ' 23:59:59'
            query += " AND timestamp <= %s"
            params.append(date_to_inclusive)
        with self.get_connection() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()
            total = row['total'] or 0
            ok_count = row['ok_count'] or 0
            ng_count = row['ng_count'] or 0
            ok_percent = (ok_count / total * 100) if total > 0 else 0.0
            return {
                'total': total,
                'ok_count': ok_count,
                'ng_count': ng_count,
                'ok_percent': round(ok_percent, 2),
                'ng_percent': round(100 - ok_percent, 2)
            }

    def get_daily_statistics(self, days: int = 30) -> List[Dict]:
        with self.get_connection() as cursor:
            cursor.execute("""
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as total,
                    SUM(CASE WHEN result = 'OK' THEN 1 ELSE 0 END) as ok_count,
                    SUM(CASE WHEN result = 'NG' THEN 1 ELSE 0 END) as ng_count
                FROM inspection_results
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
                LIMIT %s
            """, (days,))
            return [dict(row) for row in cursor.fetchall()]

    def delete_old_results(self, days: int = 90) -> int:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with self.get_connection() as cursor:
            cursor.execute("DELETE FROM inspection_results WHERE timestamp < %s", (cutoff,))
            return cursor.rowcount

    def get_count(self) -> int:
        with self.get_connection() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM inspection_results")
            row = cursor.fetchone()
            return row['count'] if row else 0

    def get_last_result(self) -> Optional[Dict]:
        """Возвращает последнюю запись из inspection_results (по timestamp)."""
        with self.get_connection() as cursor:
            cursor.execute("""
                SELECT * FROM inspection_results
                WHERE project_name IS NOT NULL AND project_name != ''           
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            return dict(row) if row else None

    # ==================== МЕТОДЫ ДЛЯ ИНСТРУМЕНТОВ (TOOLS) ====================
    def add_tool(self, tool: dict) -> int:
        with self.get_connection() as cursor:
            cursor.execute("""
                INSERT INTO tools
                (tool_id, category_ru, category_en, name_ru, name_en,
                 description, subroutine_ru, subroutine_en, project_name, project_name_display)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tool_id) DO UPDATE SET
                    category_ru = EXCLUDED.category_ru,
                    category_en = EXCLUDED.category_en,
                    name_ru = EXCLUDED.name_ru,
                    name_en = EXCLUDED.name_en,
                    description = EXCLUDED.description,
                    subroutine_ru = EXCLUDED.subroutine_ru,
                    subroutine_en = EXCLUDED.subroutine_en,
                    project_name = EXCLUDED.project_name,
                    project_name_display = EXCLUDED.project_name_display
                RETURNING id
            """, (tool['tool_id'], tool.get('category_ru', ''), tool.get('category_en', ''),
                  tool.get('name_ru', ''), tool.get('name_en', ''), tool.get('description', ''),
                  tool.get('subroutine_ru', ''), tool.get('subroutine_en', ''),
                  tool.get('project_name', ''), tool.get('project_name_display', '')))
            row = cursor.fetchone()
            return row['id'] if row else 0

    def get_all_tools(self) -> List[Dict]:
        with self.get_connection() as cursor:
            cursor.execute("SELECT * FROM tools ORDER BY tool_id")
            return [dict(row) for row in cursor.fetchall()]

    def get_tool_by_id(self, tool_id: str) -> Optional[Dict]:
        with self.get_connection() as cursor:
            cursor.execute("SELECT * FROM tools WHERE tool_id = %s", (tool_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_categories(self) -> List[Dict]:
        with self.get_connection() as cursor:
            cursor.execute("""
                SELECT DISTINCT category_ru, category_en 
                FROM tools 
                WHERE category_ru != '' 
                ORDER BY category_ru
            """)
            return [{'name_ru': row['category_ru'], 'name_en': row['category_en']} for row in cursor.fetchall()]

    def clear_tools(self):
        with self.get_connection() as cursor:
            cursor.execute("DELETE FROM tools")

    # ==================== МЕТОДЫ ДЛЯ ЗАКАЗОВ (ДЛЯ СОВМЕСТИМОСТИ С MES) ====================
    def add_order(self, order_number: str, product_name: str, quantity: int = 1,
                  priority: int = 0, camera_project: str = '', notes: str = '') -> int:
        with self.get_connection() as cursor:
            cursor.execute("""
                INSERT INTO production_orders
                (order_number, product_name, quantity, priority, camera_project, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (order_number, product_name, quantity, priority, camera_project, notes))
            row = cursor.fetchone()
            return row['id'] if row else 0

    def get_orders(self, status_filter: Optional[str] = None,
                   limit: int = 100, offset: int = 0) -> List[Dict]:
        query = "SELECT * FROM production_orders WHERE 1=1"
        params = []
        if status_filter:
            query += " AND status = %s"
            params.append(status_filter)
        query += " ORDER BY priority DESC, created_at ASC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        with self.get_connection() as cursor:
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_order_by_number(self, order_number: str) -> Optional[Dict]:
        with self.get_connection() as cursor:
            cursor.execute("SELECT * FROM production_orders WHERE order_number = %s", (order_number,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_order_status(self, order_id: int, status: str) -> bool:
        now = datetime.now().isoformat()
        with self.get_connection() as cursor:
            if status == 'production':
                cursor.execute("""
                    UPDATE production_orders 
                    SET status = %s, started_at = %s, updated_at = %s
                    WHERE id = %s
                """, (status, now, now, order_id))
            elif status == 'completed':
                cursor.execute("""
                    UPDATE production_orders 
                    SET status = %s, completed_at = %s, updated_at = %s
                    WHERE id = %s
                """, (status, now, now, order_id))
            else:
                cursor.execute("""
                    UPDATE production_orders 
                    SET status = %s, updated_at = %s
                    WHERE id = %s
                """, (status, now, order_id))
            return cursor.rowcount > 0

    def update_order_progress(self, order_id: int, completed_quantity: int) -> bool:
        now = datetime.now().isoformat()
        with self.get_connection() as cursor:
            cursor.execute("""
                UPDATE production_orders 
                SET completed_quantity = %s, updated_at = %s
                WHERE id = %s
            """, (completed_quantity, now, order_id))
            return cursor.rowcount > 0

    def update_order_station(self, order_id: int, current_station: int) -> bool:
        now = datetime.now().isoformat()
        with self.get_connection() as cursor:
            cursor.execute("""
                UPDATE production_orders
                SET current_station = %s, updated_at = %s
                WHERE id = %s
            """, (current_station, now, order_id))
            return cursor.rowcount > 0

    def delete_order(self, order_id: int) -> bool:
        with self.get_connection() as cursor:
            cursor.execute("DELETE FROM production_orders WHERE id = %s", (order_id,))
            return cursor.rowcount > 0

    def get_order_statistics(self) -> Dict:
        with self.get_connection() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'buffer' THEN 1 ELSE 0 END) as buffer_count,
                    SUM(CASE WHEN status = 'production' THEN 1 ELSE 0 END) as production_count,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count,
                    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_count
                FROM production_orders
            """)
            row = cursor.fetchone()
            return dict(row) if row else {}
    
    def get_filtered_count(self, result_filter: Optional[str] = None,
                       date_from: Optional[str] = None,
                       date_to: Optional[str] = None) -> int:
        query = "SELECT COUNT(*) as count FROM inspection_results WHERE 1=1"
        params = []
        if result_filter:
            query += " AND result = %s"
            params.append(result_filter)
        if date_from:
            query += " AND timestamp >= %s"
            params.append(date_from)
        if date_to:
            date_to_inclusive = date_to + ' 23:59:59'
            query += " AND timestamp <= %s"
            params.append(date_to_inclusive)
        with self.get_connection() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()
            return row['count'] if row else 0
    
    def get_tool_by_project_name(self, project_name: str) -> Optional[Dict]:
        with self.get_connection() as cursor:
            cursor.execute("SELECT name_ru FROM tools WHERE project_name = %s LIMIT 1", (project_name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # ==================== МЕТОДЫ ДЛЯ АВТОРИЗАЦИИ И ПОЛЬЗОВАТЕЛЕЙ ====================
    def create_user(self, username: str, password: str, role: str = 'operator', 
                    full_name: str = '') -> int:
        """Создание нового пользователя с хешированным паролем"""
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        with self.get_connection() as cursor:
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, full_name)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (username, password_hash, role, full_name))
            row = cursor.fetchone()
            return row['id'] if row else 0

    def verify_user(self, username: str, password: str) -> Optional[Dict]:
        """Проверка пароля пользователя и возврат данных пользователя при успехе"""
        with self.get_connection() as cursor:
            cursor.execute("""
                SELECT id, username, password_hash, role, full_name, is_active, created_at
                FROM users WHERE username = %s
            """, (username,))
            row = cursor.fetchone()
            if not row:
                return None
            user = dict(row)
            if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                # Обновляем время последнего входа
                cursor.execute("""
                    UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s
                """, (user['id'],))
                return user
            return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Получение данных пользователя по ID"""
        with self.get_connection() as cursor:
            cursor.execute("""
                SELECT id, username, role, full_name, is_active, created_at, last_login
                FROM users WHERE id = %s
            """, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Получение данных пользователя по имени"""
        with self.get_connection() as cursor:
            cursor.execute("""
                SELECT id, username, role, full_name, is_active, created_at, last_login
                FROM users WHERE username = %s
            """, (username,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_session(self, user_id: int, session_id: str, ip_address: str = '', 
                       expires_hours: int = 24) -> int:
        """Создание новой сессии"""
        from datetime import timedelta
        expires_at = datetime.now() + timedelta(hours=expires_hours)
        with self.get_connection() as cursor:
            cursor.execute("""
                INSERT INTO sessions (user_id, session_id, expires_at, ip_address)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (user_id, session_id, expires_at, ip_address))
            row = cursor.fetchone()
            return row['id'] if row else 0

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Получение сессии по ID"""
        with self.get_connection() as cursor:
            cursor.execute("""
                SELECT s.id, s.session_id, s.user_id, s.created_at, s.expires_at, s.ip_address,
                       u.username, u.role, u.full_name
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_id = %s AND s.expires_at > NOW()
            """, (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_session(self, session_id: str) -> bool:
        """Удаление сессии (выход из системы)"""
        with self.get_connection() as cursor:
            cursor.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))
            return cursor.rowcount > 0

    def cleanup_expired_sessions(self) -> int:
        """Удаление просроченных сессий"""
        with self.get_connection() as cursor:
            cursor.execute("DELETE FROM sessions WHERE expires_at <= NOW()")
            return cursor.rowcount

    def get_all_users(self) -> List[Dict]:
        """Получение списка всех пользователей"""
        with self.get_connection() as cursor:
            cursor.execute("""
                SELECT id, username, role, full_name, is_active, created_at, last_login
                FROM users ORDER BY username
            """)
            return [dict(row) for row in cursor.fetchall()]

    def update_user_role(self, user_id: int, role: str) -> bool:
        """Обновление роли пользователя"""
        with self.get_connection() as cursor:
            cursor.execute("""
                UPDATE users SET role = %s WHERE id = %s
            """, (role, user_id))
            return cursor.rowcount > 0

    def update_user_password(self, user_id: int, new_password: str) -> bool:
        """Обновление пароля пользователя"""
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        with self.get_connection() as cursor:
            cursor.execute("""
                UPDATE users SET password_hash = %s WHERE id = %s
            """, (password_hash, user_id))
            return cursor.rowcount > 0

    def deactivate_user(self, user_id: int) -> bool:
        """Деактивация пользователя"""
        with self.get_connection() as cursor:
            cursor.execute("""
                UPDATE users SET is_active = FALSE WHERE id = %s
            """, (user_id,))
            return cursor.rowcount > 0

    def delete_user(self, user_id: int) -> bool:
        """Удаление пользователя"""
        with self.get_connection() as cursor:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            return cursor.rowcount > 0

    def get_default_admin_exists(self) -> bool:
        """Проверка существования администратора по умолчанию"""
        with self.get_connection() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as count FROM users WHERE role = 'admin'
            """)
            row = cursor.fetchone()
            return (row['count'] or 0) > 0


# Глобальный синглтон
_db = None

def get_database(config=None):
    global _db
    if _db is None:
        if config is None:
            raise Exception("Database not initialized. Pass config first.")
        _db = Database(config)
    return _db