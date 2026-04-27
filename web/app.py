# web/app.py
import os
from flask import Flask, request, send_from_directory
from utils.logger import setup_logger

def create_app(config: dict, controller, db) -> Flask:
    app = Flask(__name__)

    app.config['config'] = config
    app.config['controller'] = controller
    app.config['db'] = db

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

    app.register_blueprint(monitoring_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(debug_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(reports_bp)

    @app.after_request
    def add_cache_headers(response):
        if request.path.startswith('/static/'):
            response.cache_control.max_age = 3600
            response.cache_control.public = True
        return response

    return app