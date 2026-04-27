# web/pages/tools.py
# -*- coding: utf-8 -*-
"""
Blueprint для страницы инструментов и API переключения проектов.
"""

from flask import Blueprint, render_template, jsonify, request, current_app

tools_bp = Blueprint('tools', __name__)

@tools_bp.route('/tools')
def tools_page():
    return render_template('tools.html')

@tools_bp.route('/api/tools')
def api_tools():
    try:
        db = current_app.config.get('db')
        if not db:
            current_app.logger.error("Database not available in app config")
            return jsonify({'success': False, 'error': 'Database not available'}), 500
        
        tools = db.get_all_tools()
        categories = db.get_categories()
        return jsonify({'success': True, 'tools': tools, 'categories': categories})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_tools")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@tools_bp.route('/api/tools/<tool_id>')
def api_tool_detail(tool_id):
    try:
        db = current_app.config.get('db')
        if not db:
            return jsonify({'success': False, 'error': 'Database not available'}), 500
        tool = db.get_tool_by_id(tool_id)
        if tool:
            return jsonify({'success': True, 'tool': tool})
        return jsonify({'success': False, 'error': f'Instrument {tool_id} not found'}), 404
    except Exception as e:
        current_app.logger.exception("Ошибка в api_tool_detail")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@tools_bp.route('/api/recent_tools')
def api_recent_tools():
    """Возвращает список уникальных project_name из последних записей inspection_results (до 10)."""
    try:
        db = current_app.config.get('db')
        if not db:
            return jsonify({'success': False, 'error': 'Database not available'}), 500
        
        limit = request.args.get('limit', 10, type=int)
        with db.get_connection() as cursor:
            cursor.execute("""
                SELECT project_name
                FROM inspection_results
                WHERE project_name IS NOT NULL AND project_name != ''
                GROUP BY project_name
                ORDER BY MAX(created_at) DESC
                LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()
            recent_projects = [row['project_name'] for row in rows]
        
        return jsonify({'success': True, 'recent_projects': recent_projects})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_recent_tools")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500