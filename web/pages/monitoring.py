# web/pages/monitoring.py
# -*- coding: utf-8 -*-
"""
Blueprint для главной страницы мониторинга и связанных API.
Все длительные операции теперь асинхронны – команды отправляются в очередь контроллера.
"""

from flask import Blueprint, render_template, jsonify, request, current_app
import re
from datetime import datetime

# Импортируем перечисление команд из контроллера
from core.controller import ControllerCommand
# Импортируем декоратор авторизации
from web.pages.auth import login_required

monitoring_bp = Blueprint('monitoring', __name__)

# ---------- Вспомогательные функции ----------
def validate_project_name(name: str) -> bool:
    """Проверяет, что имя проекта состоит из букв, цифр, точки и дефиса."""
    return bool(re.match(r'^[a-zA-Z0-9\.\-_]+$', name))

# ---------- Страница ----------
@monitoring_bp.route('/')
@login_required
def index():
    from web.pages.auth import get_current_user
    from utils.database import get_database
    from core.config import get_config
    
    config_obj = get_config()
    db = get_database(config_obj)
    current_user = get_current_user(db)
    
    config = current_app.config.get('config', {})
    default_project = config.get('camera', {}).get('project_name', 'f')
    return render_template('index.html', default_project=default_project, current_user=current_user)

# ---------- API (только чтение состояния – быстрые операции) ----------
@monitoring_bp.route('/api/status')
def status():
    controller = current_app.config.get('controller')
    if controller:
        data = controller.get_last_result()
        return jsonify(data)
    return jsonify({'result': None, 'image': None, 'time': None})

@monitoring_bp.route('/api/hardware_status')
def hardware_status():
    controller = current_app.config.get('controller')
    if not controller:
        return jsonify({'error': 'Controller not available'}), 500
    try:
        inputs = controller.get_last_inputs()
        outputs = controller.get_last_outputs()
        cam_status = controller.get_last_camera_status()
        return jsonify({
            'inputs': inputs,
            'outputs': outputs,
            'camera_status': cam_status,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        current_app.logger.exception("Ошибка в hardware_status")
        return jsonify({'error': 'Internal server error'}), 500

@monitoring_bp.route('/api/connection_status')
def connection_status():
    controller = current_app.config.get('controller')
    if not controller:
        return jsonify({'success': False, 'error': 'Controller not available'}), 500
    try:
        return jsonify({
            'success': True,
            'owen_available': controller.owen_available,
            'camera_available': controller.camera_available,
            'hardware_available': controller.hardware_available,
            'offline_mode': controller.offline_mode
        })
    except Exception as e:
        current_app.logger.exception("Ошибка в connection_status")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@monitoring_bp.route('/api/offline_mode', methods=['POST'])
def set_offline_mode():
    controller = current_app.config.get('controller')
    if not controller:
        return jsonify({'success': False, 'error': 'Controller not available'}), 500
    try:
        data = request.get_json()
        if not data or 'offline_mode' not in data:
            return jsonify({'success': False, 'error': 'Missing offline_mode'}), 400
        enabled = bool(data['offline_mode'])
        current_app.logger.info(f"Переключение офлайн-режима: {enabled}")
        controller.set_offline_mode(enabled)
        return jsonify({'success': True, 'offline_mode': enabled})
    except Exception as e:
        current_app.logger.exception("Ошибка в set_offline_mode")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@monitoring_bp.route('/api/current_project')
def api_current_project():
    try:
        config = current_app.config.get('config', {})
        project_name = config.get('camera', {}).get('project_name', '—')
        return jsonify({'success': True, 'project_name': project_name})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_current_project")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@monitoring_bp.route('/api/set_project', methods=['POST'])
def api_set_project():
    """Устанавливает проект только в конфигурации (без отправки команды камере)."""
    try:
        data = request.get_json()
        if not data or 'project_name' not in data:
            return jsonify({'success': False, 'error': 'Missing project_name'}), 400
        project_name = data['project_name'].strip()
        if not project_name:
            return jsonify({'success': False, 'error': 'Project name cannot be empty'}), 400
        if not validate_project_name(project_name):
            return jsonify({'success': False, 'error': 'Invalid project name format'}), 400
        config = current_app.config.get('config', {})
        config['camera']['project_name'] = project_name
        return jsonify({'success': True, 'message': f'Проект установлен: {project_name}'})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_set_project")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@monitoring_bp.route('/api/switch_project', methods=['POST'])
def switch_project():
    """Отправляет команду переключения проекта в очередь контроллера."""
    controller = current_app.config.get('controller')
    if not controller:
        return jsonify({'success': False, 'error': 'Controller not available'}), 500
    try:
        data = request.get_json()
        if not data or 'project_name' not in data:
            return jsonify({'success': False, 'error': 'Missing project_name'}), 400
        project_name = data['project_name'].strip()
        if not project_name:
            return jsonify({'success': False, 'error': 'Project name cannot be empty'}), 400
        if not validate_project_name(project_name):
            return jsonify({'success': False, 'error': 'Invalid project name format'}), 400

        # Отправляем команду в очередь контроллера
        controller.send_command(ControllerCommand.SWITCH_PROJECT, {'project_name': project_name})
        # Обновляем конфигурацию (для отображения)
        config = current_app.config.get('config', {})
        config['camera']['project_name'] = project_name
        current_app.logger.info(f"Команда переключения проекта на '{project_name}' отправлена в очередь")
        return jsonify({'success': True, 'message': f'Команда переключения на {project_name} принята'})
    except Exception as e:
        current_app.logger.exception("Ошибка в switch_project")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@monitoring_bp.route('/api/scenario_settings', methods=['GET'])
def api_get_scenario_settings():
    controller = current_app.config.get('controller')
    if not controller:
        return jsonify({'success': False, 'error': 'Controller not available'}), 500
    try:
        return jsonify({
            'success': True,
            'web_selection_enabled': controller.web_scenario_selection,
            'selected_scenario': controller.web_selected_scenario
        })
    except Exception as e:
        current_app.logger.exception("Ошибка в api_get_scenario_settings")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@monitoring_bp.route('/api/scenario_settings', methods=['POST'])
def api_set_scenario_settings():
    controller = current_app.config.get('controller')
    if not controller:
        return jsonify({'success': False, 'error': 'Controller not available'}), 500
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Missing data'}), 400
        if 'web_selection_enabled' in data:
            current_app.logger.info(f"Установка web_selection_enabled = {data['web_selection_enabled']}")
            controller.set_web_scenario_selection(bool(data['web_selection_enabled']))
        if 'selected_scenario' in data:
            scenario = data['selected_scenario'].upper()
            if scenario in ('A', 'B', 'C'):
                current_app.logger.info(f"Установка selected_scenario = {scenario}")
                controller.set_web_selected_scenario(scenario)
            else:
                return jsonify({'success': False, 'error': 'Invalid scenario'}), 400
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_set_scenario_settings")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@monitoring_bp.route('/api/activate_scenario', methods=['POST'])
def activate_scenario():
    """
    Активирует выбранный сценарий (кнопка «Запуск»).
    Отправляет команду в очередь контроллера – немедленный ответ.
    """
    controller = current_app.config.get('controller')
    if not controller:
        return jsonify({'success': False, 'error': 'Controller not available'}), 500
    try:
        controller.activate_web_scenario()  # внутри отправляет команду в очередь
        return jsonify({'success': True, 'message': 'Команда активации сценария принята'})
    except Exception as e:
        current_app.logger.exception("Ошибка активации сценария")
        return jsonify({'success': False, 'error': str(e)}), 500

@monitoring_bp.route('/api/mode', methods=['GET'])
def api_get_mode():
    try:
        controller = current_app.config.get('controller')
        if not controller:
            return jsonify({'success': False, 'error': 'Controller not available'}), 500
        auto_mode = controller.get_auto_mode()
        return jsonify({'success': True, 'auto_mode': auto_mode})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_get_mode")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@monitoring_bp.route('/api/mode', methods=['POST'])
def api_set_mode():
    try:
        controller = current_app.config.get('controller')
        if not controller:
            return jsonify({'success': False, 'error': 'Controller not available'}), 500
        data = request.get_json()
        if not data or 'auto_mode' not in data:
            return jsonify({'success': False, 'error': 'Missing auto_mode'}), 400
        auto_mode = bool(data['auto_mode'])
        controller.set_auto_mode(auto_mode)
        mode_text = 'АВТОМАТИЧЕСКИЙ' if auto_mode else 'РУЧНОЙ'
        return jsonify({'success': True, 'auto_mode': auto_mode, 'message': f'Режим переключён: {mode_text}'})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_set_mode")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# ---------- Клиентское логирование ----------
@monitoring_bp.route('/api/client_error', methods=['POST'])
def client_error():
    try:
        data = request.get_json()
        if data:
            message = data.get('message', 'No message')
            stack = data.get('stack', '')
            url = data.get('url', '')
            user_agent = request.headers.get('User-Agent', '')
            current_app.logger.error(f"CLIENT ERROR: {message} | URL: {url} | UA: {user_agent} | Stack: {stack}")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# ---------- Вспомогательные эндпоинты для отображения ----------
@monitoring_bp.route('/api/project_russian_name')
def project_russian_name():
    """Возвращает русское название проекта из таблицы tools."""
    project_name = request.args.get('project_name', '')
    if not project_name:
        return jsonify({'success': False, 'error': 'Missing project_name'}), 400
    db = current_app.config.get('db')
    if not db:
        return jsonify({'success': False, 'error': 'Database not available'}), 500
    try:
        tool = db.get_tool_by_project_name(project_name)
        if tool and tool.get('name_ru'):
            return jsonify({'success': True, 'name_ru': tool['name_ru']})
        else:
            return jsonify({'success': True, 'name_ru': project_name})
    except Exception as e:
        current_app.logger.exception("Ошибка получения русского названия")
        return jsonify({'success': False, 'error': str(e)}), 500