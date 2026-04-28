# web/app.py
import os
import secrets
import threading
import time
from flask import Flask, request, send_from_directory
from flask_socketio import SocketIO, emit
from utils.logger import setup_logger

def create_app(config: dict, controller, db) -> Flask:
    app = Flask(__name__)
    
    # Секретный ключ для сессий
    app.secret_key = config.get('web', {}).get('secret_key', secrets.token_hex(32))
    
    # Время жизни сессии (24 часа)
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400

    app.config['config'] = config
    app.config['controller'] = controller
    app.config['db'] = db

    # Инициализация Socket.IO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    app.config['socketio'] = socketio

    # Логгер
    log_cfg = config.get('logging', {}).get('web', {})
    log_dir = config.get('paths', {}).get('logs', 'data/logs')
    app.logger = setup_logger(
        'web',
        log_dir=log_dir,
        level=getattr(__import__('logging'), log_cfg.get('level', 'DEBUG').upper()),
        max_bytes=log_cfg.get('max_bytes'),
        backup_count=log_cfg.get('backup_count')
    )
    app.logger.info("===== WEB APP STARTED =====")

    # Маршрут для раздачи изображений из папки data/images
    images_dir = os.path.abspath(config.get('paths', {}).get('images', 'data/images'))
    @app.route('/images/<path:filename>')
    def serve_image(filename):
        return send_from_directory(images_dir, filename)

    # Регистрация Blueprints
    from web.pages.monitoring import monitoring_bp
    from web.pages.tools import tools_bp
    from web.pages.history import history_bp
    from web.pages.debug import debug_bp
    from web.pages.settings import settings_bp
    from web.pages.reports import reports_bp
    from web.pages.auth import auth_bp
    from web.pages.users import users_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(monitoring_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(debug_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(users_bp)

    @app.after_request
    def add_cache_headers(response):
        if request.path.startswith('/static/'):
            response.cache_control.max_age = 3600
            response.cache_control.public = True
        return response

    # Обработчики WebSocket событий
    @socketio.on('connect')
    def handle_connect():
        app.logger.info(f"Клиент подключился к WebSocket: {request.sid}")

    @socketio.on('disconnect')
    def handle_disconnect():
        app.logger.info(f"Клиент отключился от WebSocket: {request.sid}")

    @socketio.on('subscribe_status')
    def handle_subscribe():
        """Клиент подписался на обновления статуса"""
        app.logger.info(f"Клиент {request.sid} подписался на обновления статуса")

    # Фоновый поток для периодической рассылки обновлений статуса
    def broadcast_status():
        """Периодически отправляет обновления статуса всем подключенным клиентам"""
        while True:
            try:
                time.sleep(0.5)  # Обновление каждые 500мс для real-time ощущения
                
                if controller:
                    # Получаем данные от контроллера
                    result_data = controller.get_last_result()
                    inputs = controller.get_last_inputs()
                    outputs = controller.get_last_outputs()
                    cam_status = controller.get_last_camera_status()
                    status = controller.get_status()
                    
                    # Формируем полное обновление
                    update_data = {
                        'result': result_data,
                        'inputs': inputs,
                        'outputs': outputs,
                        'camera_status': cam_status,
                        'hardware_available': status.get('hardware_available', False),
                        'owen_available': status.get('owen_available', False),
                        'camera_available': status.get('camera_available', False),
                        'offline_mode': status.get('offline_mode', False),
                        'auto_mode': status.get('auto_mode', True),
                        'current_scenario': status.get('current_scenario'),
                        'timestamp': time.time()
                    }
                    
                    # Отправляем всем подключенным клиентам
                    socketio.emit('status_update', update_data)
                    
            except Exception as e:
                app.logger.error(f"Ошибка в broadcast_status: {e}")
    
    # Запускаем фоновый поток рассылки
    broadcast_thread = threading.Thread(target=broadcast_status, daemon=True)
    broadcast_thread.start()
    app.logger.info("Запущен фоновый поток WebSocket обновлений")

    return app