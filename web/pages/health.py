# web/pages/health.py
# -*- coding: utf-8 -*-
"""
Blueprint для /api/health — проверка работоспособности системы.
"""

import time
from flask import Blueprint, jsonify, current_app

health_bp = Blueprint('health', __name__)

# Время старта приложения (модульный уровень — один раз при импорте)
_start_time = time.time()


@health_bp.route('/api/health')
def health():
    config = current_app.config.get('config', {})
    controller = current_app.config.get('controller')
    db = current_app.config.get('db')

    health_data = {
        'status': 'ok',
        'uptime': round(time.time() - _start_time, 1),
        'timestamp': time.time(),
        'components': {}
    }

    # --- База данных ---
    db_ok = False
    if db:
        try:
            t0 = time.time()
            with db.get_connection() as cursor:
                cursor.execute('SELECT 1')
            db_ok = True
            health_data['components']['database'] = {
                'status': 'ok',
                'latency_ms': round((time.time() - t0) * 1000, 1),
                'type': config.get('database', {}).get('type', 'postgresql'),
                'host': config.get('database', {}).get('host', ''),
            }
        except Exception as e:
            health_data['components']['database'] = {
                'status': 'error',
                'error': str(e),
            }
    else:
        health_data['components']['database'] = {'status': 'not_initialized'}

    # --- OWEN ---
    if controller:
        health_data['components']['owen'] = {
            'status': 'ok' if controller.owen_available else 'disconnected',
            'ip': config.get('owen', {}).get('ip', ''),
        }
        health_data['components']['camera'] = {
            'status': 'ok' if controller.camera_available else 'disconnected',
            'ip': config.get('camera', {}).get('ip', ''),
        }
    else:
        health_data['components']['owen'] = {'status': 'no_controller'}
        health_data['components']['camera'] = {'status': 'no_controller'}

    # Общий статус — ok только если всё доступно
    statuses = [c.get('status') for c in health_data['components'].values()]
    if any(s in ('error', 'not_initialized', 'no_controller', 'disconnected') for s in statuses):
        health_data['status'] = 'degraded'

    code = 200 if health_data['status'] == 'ok' else 503
    return jsonify(health_data), code
