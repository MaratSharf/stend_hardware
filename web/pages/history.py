# web/pages/history.py
# -*- coding: utf-8 -*-
"""
Blueprint для страницы истории результатов и статистики.
"""

from flask import Blueprint, render_template, jsonify, request, current_app, send_file
from web.pages.auth import login_required, get_current_user
from utils.database import get_database
from core.config import get_config
from utils.excel_export import get_excel_exporter
from utils.pdf_export import get_pdf_exporter
import io
from datetime import datetime

history_bp = Blueprint('history', __name__)

@history_bp.route('/history')
@login_required
def history_page():
    config_obj = get_config()
    db = get_database(config_obj)
    current_user = get_current_user(db)
    return render_template('history.html', current_user=current_user)

@history_bp.route('/api/results')
def api_results():
    try:
        db = current_app.config.get('db')
        if not db:
            return jsonify({'success': False, 'error': 'Database not available'}), 500
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        result_filter = request.args.get('result', None) or None
        date_from = request.args.get('date_from', None) or None
        date_to = request.args.get('date_to', None) or None
        order_number = request.args.get('order_number', None) or None
        project_name = request.args.get('project_name', None) or None
        scenario = request.args.get('scenario', None) or None
        
        # Получаем точное количество записей с учётом фильтров
        total = db.get_filtered_count(result_filter, date_from, date_to)
        results = db.get_results(limit=limit, offset=offset,
                                 result_filter=result_filter,
                                 date_from=date_from, date_to=date_to,
                                 order_number=order_number,
                                 project_name=project_name,
                                 scenario=scenario)
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
        project_stats = db.get_project_statistics(date_from=date_from, date_to=date_to)
        order_ng_stats = db.get_top_ng_orders(limit=10, date_from=date_from, date_to=date_to)
        return jsonify({
            'success': True,
            'statistics': stats,
            'daily': daily_stats,
            'project': project_stats,
            'top_ng_orders': order_ng_stats
        })
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

@history_bp.route('/api/export/csv')
@login_required
def api_export_csv():
    """Экспорт результатов в CSV с учётом фильтров."""
    try:
        db = current_app.config.get('db')
        if not db:
            return jsonify({'success': False, 'error': 'Database not available'}), 500
        
        # Получаем фильтры из запроса
        result_filter = request.args.get('result', None) or None
        date_from = request.args.get('date_from', None) or None
        date_to = request.args.get('date_to', None) or None
        order_number = request.args.get('order_number', None) or None
        project_name = request.args.get('project_name', None) or None
        scenario = request.args.get('scenario', None) or None
        limit = request.args.get('limit', 10000, type=int)  # Большой лимит для экспорта
        
        results = db.get_results(limit=limit, offset=0,
                                 result_filter=result_filter,
                                 date_from=date_from, date_to=date_to,
                                 order_number=order_number,
                                 project_name=project_name,
                                 scenario=scenario)
        
        # Формируем CSV
        import csv
        output = io.StringIO()
        fieldnames = ['id', 'timestamp', 'result', 'order_number', 'scenario', 
                      'project_name', 'sensor_d1', 'sensor_d2', 'sensor_d3', 
                      'sensor_d4', 'tumbler_a', 'tumbler_b', 'raw']
        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=';', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        
        for r in results:
            row = {k: r.get(k, '') for k in fieldnames}
            writer.writerow(row)
        
        # Формируем имя файла с датой
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'export_{timestamp}.csv'
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),  # BOM для Excel
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        current_app.logger.exception("Ошибка в api_export_csv")
        return jsonify({'success': False, 'error': str(e)}), 500

@history_bp.route('/api/export/excel')
@login_required
def api_export_excel():
    """Экспорт результатов в Excel с учётом фильтров."""
    try:
        db = current_app.config.get('db')
        if not db:
            return jsonify({'success': False, 'error': 'Database not available'}), 500
        
        # Получаем фильтры из запроса
        result_filter = request.args.get('result', None) or None
        date_from = request.args.get('date_from', None) or None
        date_to = request.args.get('date_to', None) or None
        order_number = request.args.get('order_number', None) or None
        project_name = request.args.get('project_name', None) or None
        scenario = request.args.get('scenario', None) or None
        limit = request.args.get('limit', 10000, type=int)  # Большой лимит для экспорта
        
        results = db.get_results(limit=limit, offset=0,
                                 result_filter=result_filter,
                                 date_from=date_from, date_to=date_to,
                                 order_number=order_number,
                                 project_name=project_name,
                                 scenario=scenario)
        
        # Получаем статистику за период
        stats = db.get_statistics(date_from=date_from, date_to=date_to)
        
        # Формируем отчёт для экспортера
        report = {
            'date': f"{date_from or 'Начало'} — {date_to or 'Сегодня'}",
            'total': stats['total'],
            'ok_count': stats['ok_count'],
            'ng_count': stats['ng_count'],
            'ok_percent': stats['ok_percent'],
            'results': results
        }
        
        # Экспортируем в Excel
        exporter = get_excel_exporter()
        excel_data = exporter.export_history_report(report)
        
        # Формируем имя файла с датой
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'export_{timestamp}.xlsx'
        
        return send_file(
            io.BytesIO(excel_data),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        current_app.logger.exception("Ошибка в api_export_excel")
        return jsonify({'success': False, 'error': str(e)}), 500

@history_bp.route('/api/export/pdf')
@login_required
def api_export_pdf():
    """Экспорт результатов в PDF с учётом фильтров."""
    try:
        db = current_app.config.get('db')
        if not db:
            return jsonify({'success': False, 'error': 'Database not available'}), 500
        
        # Получаем фильтры из запроса
        result_filter = request.args.get('result', None) or None
        date_from = request.args.get('date_from', None) or None
        date_to = request.args.get('date_to', None) or None
        order_number = request.args.get('order_number', None) or None
        project_name = request.args.get('project_name', None) or None
        scenario = request.args.get('scenario', None) or None
        limit = request.args.get('limit', 500, type=int)  # Ограничение для PDF (100 строк максимум)
        
        results = db.get_results(limit=limit, offset=0,
                                 result_filter=result_filter,
                                 date_from=date_from, date_to=date_to,
                                 order_number=order_number,
                                 project_name=project_name,
                                 scenario=scenario)
        
        # Получаем статистику за период
        stats = db.get_statistics(date_from=date_from, date_to=date_to)
        project_stats = db.get_project_statistics(date_from=date_from, date_to=date_to)
        
        # Формируем отчёт для экспортера
        report = {
            'date': f"{date_from or 'Начало'} — {date_to or 'Сегодня'}",
            'statistics': stats,
            'project': project_stats,
            'results': results
        }
        
        # Экспортируем в PDF
        exporter = get_pdf_exporter()
        pdf_data = exporter.export_history_report(report)
        
        # Формируем имя файла с датой
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'export_{timestamp}.pdf'
        
        return send_file(
            io.BytesIO(pdf_data),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except ImportError:
        current_app.logger.error("PDF export not available")
        return jsonify({'success': False, 'error': 'PDF export requires reportlab: pip install reportlab'}), 503
    except Exception as e:
        current_app.logger.exception("Ошибка в api_export_pdf")
        return jsonify({'success': False, 'error': str(e)}), 500


@history_bp.route('/api/export/pdf/<int:result_id>')
@login_required
def api_export_detail_pdf(result_id):
    """Экспорт одной записи в PDF (из модального окна)."""
    try:
        db = current_app.config.get('db')
        if not db:
            return jsonify({'success': False, 'error': 'Database not available'}), 500
        
        result = db.get_result_by_id(result_id)
        if not result:
            return jsonify({'success': False, 'error': 'Result not found'}), 404
        
        exporter = get_pdf_exporter()
        pdf_data = exporter.export_detail_report(result)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'record_{result_id}_{timestamp}.pdf'
        
        return send_file(
            io.BytesIO(pdf_data),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except ImportError:
        current_app.logger.error("PDF export not available")
        return jsonify({'success': False, 'error': 'PDF export requires reportlab: pip install reportlab'}), 503
    except Exception as e:
        current_app.logger.exception("Ошибка в api_export_detail_pdf")
        return jsonify({'success': False, 'error': str(e)}), 500