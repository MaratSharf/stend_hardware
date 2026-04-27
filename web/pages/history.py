# web/pages/history.py
# -*- coding: utf-8 -*-
"""
Blueprint для страницы истории результатов и статистики.
"""

from flask import Blueprint, render_template, jsonify, request, current_app

history_bp = Blueprint('history', __name__)

@history_bp.route('/history')
def history_page():
    return render_template('history.html')

@history_bp.route('/api/results')
def api_results():
    try:
        db = current_app.config.get('db')
        if not db:
            return jsonify({'success': False, 'error': 'Database not available'}), 500
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        result_filter = request.args.get('result', None)
        date_from = request.args.get('date_from', None)
        date_to = request.args.get('date_to', None)
        
        # Получаем точное количество записей с учётом фильтров
        total = db.get_filtered_count(result_filter, date_from, date_to)
        results = db.get_results(limit=limit, offset=offset,
                                 result_filter=result_filter,
                                 date_from=date_from, date_to=date_to)
        return jsonify({'success': True, 'results': results, 'total': total})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_results")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@history_bp.route('/api/statistics')
def api_statistics():
    try:
        db = current_app.config.get('db')
        if not db:
            return jsonify({'success': False, 'error': 'Database not available'}), 500
        date_from = request.args.get('date_from', None)
        date_to = request.args.get('date_to', None)
        stats = db.get_statistics(date_from=date_from, date_to=date_to)
        daily_stats = db.get_daily_statistics(days=30)
        return jsonify({'success': True, 'statistics': stats, 'daily': daily_stats})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_statistics")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@history_bp.route('/api/results/<int:result_id>')
def api_result_by_id(result_id):
    try:
        db = current_app.config.get('db')
        if not db:
            return jsonify({'success': False, 'error': 'Database not available'}), 500
        result = db.get_result_by_id(result_id)
        if result:
            return jsonify({'success': True, 'result': result})
        return jsonify({'success': False, 'error': 'Result not found'}), 404
    except Exception as e:
        current_app.logger.exception("Ошибка в api_result_by_id")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500