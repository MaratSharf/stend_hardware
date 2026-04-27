# web/pages/reports.py
# -*- coding: utf-8 -*-
"""
Blueprint для страницы отчётов и экспорта.
"""

from flask import Blueprint, render_template, jsonify, request, current_app
from datetime import datetime
from utils.report_generator import get_report_generator
from utils.excel_export import get_excel_exporter

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports')
def reports_page():
    return render_template('reports.html')

@reports_bp.route('/api/reports/daily', methods=['GET'])
def api_daily_report():
    try:
        date = request.args.get('date')
        if not date:
            return jsonify({'success': False, 'error': 'Missing date parameter'}), 400
        generator = get_report_generator()
        report = generator.get_daily_report(date)
        return jsonify({'success': True, 'report': report})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_daily_report")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@reports_bp.route('/api/reports/shift', methods=['GET'])
def api_shift_report():
    try:
        date = request.args.get('date')
        shift = request.args.get('shift', type=int)
        if not date:
            return jsonify({'success': False, 'error': 'Missing date parameter'}), 400
        if not shift or shift not in [1,2,3]:
            return jsonify({'success': False, 'error': 'Invalid shift number'}), 400
        generator = get_report_generator()
        report = generator.get_shift_report(date, shift)
        return jsonify({'success': True, 'report': report})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_shift_report")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@reports_bp.route('/api/reports/weekly', methods=['GET'])
def api_weekly_report():
    try:
        year = request.args.get('year', type=int)
        week = request.args.get('week', type=int)
        if not year or not week:
            return jsonify({'success': False, 'error': 'Missing year or week parameter'}), 400
        generator = get_report_generator()
        report = generator.get_weekly_report(year, week)
        return jsonify({'success': True, 'report': report})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_weekly_report")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@reports_bp.route('/api/reports/monthly', methods=['GET'])
def api_monthly_report():
    try:
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        if not year or not month:
            return jsonify({'success': False, 'error': 'Missing year or month parameter'}), 400
        generator = get_report_generator()
        report = generator.get_monthly_report(year, month)
        return jsonify({'success': True, 'report': report})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_monthly_report")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@reports_bp.route('/api/reports/ng-analysis', methods=['GET'])
def api_ng_analysis():
    try:
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        if not date_from or not date_to:
            return jsonify({'success': False, 'error': 'Missing date parameters'}), 400
        generator = get_report_generator()
        report = generator.get_ng_analysis(date_from, date_to)
        return jsonify({'success': True, 'report': report})
    except Exception as e:
        current_app.logger.exception("Ошибка в api_ng_analysis")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@reports_bp.route('/api/reports/export', methods=['POST'])
def api_export_report():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Missing data'}), 400
        report_type = data.get('report_type')
        report_data = data.get('report_data')
        if not report_type or not report_data:
            return jsonify({'success': False, 'error': 'Missing report_type or report_data'}), 400
        exporter = get_excel_exporter()
        if report_type == 'daily':
            excel_data = exporter.export_daily_report(report_data)
        elif report_type == 'shift':
            excel_data = exporter.export_shift_report(report_data)
        elif report_type == 'weekly':
            excel_data = exporter.export_weekly_report(report_data)
        elif report_type == 'monthly':
            excel_data = exporter.export_monthly_report(report_data)
        elif report_type == 'ng-analysis':
            excel_data = exporter.export_ng_analysis(report_data)
        else:
            return jsonify({'success': False, 'error': 'Unknown report type'}), 400
        return current_app.response_class(
            response=excel_data,
            status=200,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename=report_{report_type}_{datetime.now().strftime("%Y%m%d")}.xlsx'}
        )
    except ImportError as e:
        current_app.logger.error(f"Excel export not available: {e}")
        return jsonify({'success': False, 'error': 'Excel export requires pandas and openpyxl: pip install pandas openpyxl'}), 503
    except Exception as e:
        current_app.logger.exception("Ошибка в api_export_report")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500