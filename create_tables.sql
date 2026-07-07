-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'operator',
    full_name TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- Таблица сессий
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    ip_address TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);

-- Таблица результатов инспекций
CREATE TABLE IF NOT EXISTS inspection_results (
    id SERIAL PRIMARY KEY,
    timestamp TEXT NOT NULL,
    result TEXT NOT NULL,
    raw TEXT,
    image_path TEXT,
    image_name TEXT,
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
);
CREATE INDEX IF NOT EXISTS idx_inspection_timestamp ON inspection_results(timestamp);
CREATE INDEX IF NOT EXISTS idx_inspection_result ON inspection_results(result);
CREATE INDEX IF NOT EXISTS idx_inspection_order ON inspection_results(order_number);
CREATE INDEX IF NOT EXISTS idx_inspection_image_path ON inspection_results(image_path);

-- Таблица использованных изображений
CREATE TABLE IF NOT EXISTS used_images (
    id SERIAL PRIMARY KEY,
    image_name TEXT NOT NULL UNIQUE,
    image_path TEXT NOT NULL,
    inspection_result_id INTEGER REFERENCES inspection_results(id) ON DELETE CASCADE,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_used_images_name ON used_images(image_name);

-- Таблица дневной статистики
CREATE TABLE IF NOT EXISTS daily_stats (
    id SERIAL PRIMARY KEY,
    date TEXT NOT NULL UNIQUE,
    total_count INTEGER DEFAULT 0,
    ok_count INTEGER DEFAULT 0,
    ng_count INTEGER DEFAULT 0,
    ok_percent REAL DEFAULT 0.0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date);

-- Таблица инструментов Hikrobot
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
    project_name_display TEXT,
    is_favorite BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_tools_tool_id ON tools(tool_id);
CREATE INDEX IF NOT EXISTS idx_tools_category ON tools(category_ru);
CREATE INDEX IF NOT EXISTS idx_tools_favorite ON tools(is_favorite);

-- Таблица производственных заказов
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
);
CREATE INDEX IF NOT EXISTS idx_orders_status ON production_orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_number ON production_orders(order_number);
