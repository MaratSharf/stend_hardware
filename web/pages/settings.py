# web/pages/settings.py
# -*- coding: utf-8 -*-
"""
Blueprint для страницы настроек и управления конфигурацией.
"""

from flask import Blueprint, render_template, jsonify, request, current_app, send_from_directory
import os
import yaml
from datetime import datetime
from utils.config_manager import get_config_manager
import re
from web.pages.auth import login_required, get_current_user
from utils.database import get_database
from core.config import get_config

settings_bp = Blueprint('settings', __name__)

def validate_ip_address(ip: str) -> bool:
    if not ip:
        return False
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(part) <= 255 for part in parts)
    except ValueError:
        return False

@settings_bp.route('/settings')
@login_required
def settings_page():
    config_obj = get_config()
    db = get_database(config_obj)
    current_user = get_current_user(db)
    return render_template('settings.html', current_user=current_user)

@settings_bp.route('/api/settings/get', methods=['GET'])
def api_get_settings():
    try:
        config_manager = get_config_manager()
        config = config_manager.load()
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_get_settings")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@settings_bp.route('/api/settings/update', methods=['POST'])
def api_update_settings():
    try:
        config_manager = get_config_manager()
        data = request.get_json()
        if not data or 'config' not in data:
            return jsonify({'success': False, 'error': 'Missing config'}), 400
        new_config = data['config']

        owen_cfg = new_config.get('owen', {})
        camera_cfg = new_config.get('camera', {})
        if not validate_ip_address(owen_cfg.get('ip', '')):
            return jsonify({'success': False, 'error': 'Invalid OWEN IP address'}), 400
        if not validate_ip_address(camera_cfg.get('ip', '')):
            return jsonify({'success': False, 'error': 'Invalid Camera IP address'}), 400

        config_manager.save(new_config)
        current_app.config['config'] = new_config
        controller = current_app.config.get('controller')
        if controller and controller.camera:
            new_project = new_config.get('camera', {}).get('project_name')
            if new_project:
                controller.camera.switch_project(new_project)
        current_app.logger.info(f"Конфигурация обновлена: {new_config.get('camera', {}).get('project_name', 'N/A')}")
        return jsonify({'success': True, 'message': 'Конфигурация успешно сохранена'})
    except ValueError as e:
        return jsonify({'success': False, 'error': f'Ошибка валидации: {str(e)}'}), 400
    except Exception as e:
        current_app.logger.exception("Ошибка в api_update_settings")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@settings_bp.route('/api/settings/backup', methods=['POST'])
def api_create_backup():
    try:
        config_manager = get_config_manager()
        config_manager._create_backup()
        backups = config_manager.get_backup_list()
        backup_filename = backups[0]['filename'] if backups else None
        return jsonify({'success': True, 'message': 'Резервная копия создана', 'backup_filename': backup_filename})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_create_backup")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@settings_bp.route('/api/settings/backups', methods=['GET'])
def api_get_backups():
    try:
        config_manager = get_config_manager()
        backups = config_manager.get_backup_list()
        return jsonify({'success': True, 'backups': backups})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_get_backups")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@settings_bp.route('/api/settings/restore', methods=['POST'])
def api_restore_backup():
    try:
        config_manager = get_config_manager()
        data = request.get_json()
        if not data or 'backup_filename' not in data:
            return jsonify({'success': False, 'error': 'Missing backup_filename'}), 400
        backup_filename = data['backup_filename']
        config_manager.restore_from_backup(backup_filename)
        new_config = config_manager.load(force=True)
        current_app.config['config'] = new_config
        return jsonify({'success': True, 'message': f'Конфигурация восстановлена из {backup_filename}'})
    except FileNotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        current_app.logger.exception("Ошибка в api_restore_backup")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@settings_bp.route('/api/settings/export', methods=['GET'])
def api_export_settings():
    try:
        config_manager = get_config_manager()
        config = config_manager.load()
        yaml_output = __import__('io').StringIO()
        yaml.dump(config, yaml_output, default_flow_style=False, allow_unicode=True, sort_keys=False)
        yaml_content = yaml_output.getvalue()
        return current_app.response_class(
            response=yaml_content,
            status=200,
            mimetype='application/x-yaml',
            headers={'Content-Disposition': f'attachment; filename=config_{datetime.now().strftime("%Y%m%d_%H%M%S")}.yaml'}
        )
    except Exception as e:
        current_app.logger.exception("Ошибка в api_export_settings")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@settings_bp.route('/api/settings/import', methods=['POST'])
def api_import_settings():
    try:
        config_manager = get_config_manager()
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        file_content = file.read().decode('utf-8')
        imported_config = yaml.safe_load(file_content)

        owen_cfg = imported_config.get('owen', {})
        camera_cfg = imported_config.get('camera', {})
        if not validate_ip_address(owen_cfg.get('ip', '')):
            return jsonify({'success': False, 'error': 'Invalid OWEN IP address'}), 400
        if not validate_ip_address(camera_cfg.get('ip', '')):
            return jsonify({'success': False, 'error': 'Invalid Camera IP address'}), 400

        config_manager.save(imported_config)
        current_app.config['config'] = imported_config
        return jsonify({'success': True, 'message': 'Конфигурация импортирована'})
    except ValueError as e:
        return jsonify({'success': False, 'error': f'Ошибка валидации: {str(e)}'}), 400
    except Exception as e:
        current_app.logger.exception("Ошибка в api_import_settings")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@settings_bp.route('/api/settings/backup/download', methods=['GET'])
def api_download_backup():
    try:
        config_manager = get_config_manager()
        filename = request.args.get('filename')
        if not filename:
            return jsonify({'success': False, 'error': 'Missing filename'}), 400
        backup_dir = os.path.join(os.path.dirname(config_manager.config_path), 'backups')
        backup_path = os.path.join(backup_dir, filename)
        if not os.path.exists(backup_path):
            return jsonify({'success': False, 'error': 'File not found'}), 404
        return send_from_directory(backup_dir, filename, as_attachment=True)
    except Exception as e:
        current_app.logger.exception("Ошибка в api_download_backup")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500