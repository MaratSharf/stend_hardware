# web/pages/debug.py
# -*- coding: utf-8 -*-
"""
Blueprint для страницы отладки и ручного управления.
Все операции управления выходами и триггер камеры выполняются асинхронно через очередь команд.
"""

from flask import Blueprint, render_template, jsonify, request, current_app
from core.controller import ControllerCommand
from web.pages.auth import login_required, get_current_user
from utils.database import get_database
from core.config import get_config

debug_bp = Blueprint('debug', __name__)

@debug_bp.route('/debug')
@login_required
def debug_page():
    config_obj = get_config()
    db = get_database(config_obj)
    current_user = get_current_user(db)
    return render_template('debug.html', current_user=current_user)

@debug_bp.route('/api/debug/trigger', methods=['POST'])
def debug_trigger_camera():
    """
    Отправляет команду на выполнение одиночного измерения (сценарий B).
    Команда ставится в очередь контроллера, ответ приходит немедленно.
    """
    controller = current_app.config.get('controller')
    if not controller:
        return jsonify({'success': False, 'error': 'Controller not available'}), 500

    # Проверяем, что контроллер находится в ручном режиме или авторежиме с возможностью ручного триггера
    # По логике, на странице отладки разрешаем ручной триггер только если не в авторежиме?
    # В исходном коде – можно всегда, но контроллер сам решит, обрабатывать или нет.
    # Отправляем команду в очередь
    controller.send_command(ControllerCommand.TRIGGER_B)
    return jsonify({
        'success': True,
        'message': 'Команда измерения отправлена. Результат появится на главной странице.'
    })

@debug_bp.route('/api/debug/output', methods=['POST'])
def debug_set_output():
    """
    Устанавливает состояние выхода (DO0..DO3) в ручном режиме.
    Команда ставится в очередь контроллера.
    """
    controller = current_app.config.get('controller')
    if not controller:
        return jsonify({'success': False, 'error': 'Controller not available'}), 500

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Missing data'}), 400

    output_num = data.get('output')
    state = data.get('state')

    if output_num not in ['DO0', 'DO1', 'DO2', 'DO3']:
        return jsonify({'success': False, 'error': 'Invalid output number'}), 400
    if not isinstance(state, bool):
        return jsonify({'success': False, 'error': 'State must be boolean'}), 400

    # Преобразуем строковый идентификатор в числовой индекс
    output_map = {
        'DO0': controller.DO_CONVEYOR,
        'DO1': controller.DO_EJECTOR,
        'DO2': controller.DO_LAMP_RED,
        'DO3': controller.DO_LAMP_GREEN
    }
    output_index = output_map[output_num]

    # Отправляем команду в очередь
    controller.send_command(ControllerCommand.SET_OUTPUT, {
        'output': output_index,
        'state': state
    })

    output_names = {'DO0': 'Конвейер', 'DO1': 'Толкатель', 'DO2': 'Лампа NG', 'DO3': 'Лампа OK'}
    state_text = "ВКЛ" if state else "ВЫКЛ"
    return jsonify({
        'success': True,
        'message': f"Команда на {output_names.get(output_num, output_num)} {state_text} отправлена"
    })

@debug_bp.route('/api/debug/inputs', methods=['GET'])
def debug_get_inputs():
    """Возвращает текущее состояние входов и выходов (только чтение, быстро)."""
    controller = current_app.config.get('controller')
    if not controller:
        return jsonify({'success': False, 'error': 'Controller not available'}), 500
    try:
        inputs = controller.get_last_inputs()
        outputs = controller.get_last_outputs()
        return jsonify({'success': True, 'inputs': inputs, 'outputs': outputs})
    except Exception as e:
        current_app.logger.exception("Ошибка в debug_get_inputs")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@debug_bp.route('/api/debug/all-outputs', methods=['GET'])
def debug_get_all_outputs():
    """Возвращает все выходы (для отладки)."""
    controller = current_app.config.get('controller')
    if not controller:
        return jsonify({'success': False, 'error': 'Controller not available'}), 500
    try:
        # Просто берём последние известные выходы из контроллера (быстро)
        outputs = controller.get_last_outputs()
        return jsonify({'success': True, 'outputs': outputs})
    except Exception as e:
        current_app.logger.exception("Ошибка в debug_get_all_outputs")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500