# -*- coding: utf-8 -*-
"""
Генератор отчётов для стенда машинного зрения.
Предоставляет функции для создания отчётов по сменам, дням, неделям и месяцам.
"""

import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from utils.database import get_database


class ReportGenerator:
    """Генерация отчётов о производстве."""

    def __init__(self):
        self.db = get_database()

    def get_daily_report(self, date: str) -> Dict[str, Any]:
        """
        Дневной отчёт.
        :param date: Дата в формате YYYY-MM-DD
        :return: Словарь с данными отчёта
        """
        results = self.db.get_results(
            date_from=date,
            date_to=date,
            limit=10000
        )

        total = len(results)
        ok_count = sum(1 for r in results if r.get('result') == 'OK')
        ng_count = sum(1 for r in results if r.get('result') == 'NG')
        ok_percent = round((ok_count / total * 100), 2) if total > 0 else 0

        # Статистика по часам
        hourly_stats = self._get_hourly_stats(results)

        # Топ проектов по количеству проверок
        project_stats = self._get_project_stats(results)

        # Распределение по сценариям
        scenario_stats = self._get_scenario_stats(results)

        return {
            'date': date,
            'total': total,
            'ok_count': ok_count,
            'ng_count': ng_count,
            'ok_percent': ok_percent,
            'hourly_stats': hourly_stats,
            'project_stats': project_stats,
            'scenario_stats': scenario_stats,
            'results': results
        }

    def get_shift_report(self, date: str, shift: int) -> Dict[str, Any]:
        """
        Сменный отчёт.
        :param date: Дата в формате YYYY-MM-DD
        :param shift: Номер смены (1, 2, 3)
        :return: Словарь с данными отчёта
        """
        # Определяем временные рамки смены
        shift_times = {
            1: ('06:00', '14:00'),  # Утренняя смена
            2: ('14:00', '22:00'),  # Дневная смена
            3: ('22:00', '06:00')   # Ночная смена
        }

        if shift not in shift_times:
            raise ValueError(f"Неверный номер смены: {shift}")

        start_time, end_time = shift_times[shift]

        # Получаем результаты за дату
        results = self.db.get_results(
            date_from=date,
            date_to=date,
            limit=10000
        )

        # Фильтруем по времени смены
        filtered_results = self._filter_by_shift(results, start_time, end_time, shift)

        total = len(filtered_results)
        ok_count = sum(1 for r in filtered_results if r.get('result') == 'OK')
        ng_count = sum(1 for r in filtered_results if r.get('result') == 'NG')
        ok_percent = round((ok_count / total * 100), 2) if total > 0 else 0

        return {
            'date': date,
            'shift': shift,
            'shift_name': self._get_shift_name(shift),
            'total': total,
            'ok_count': ok_count,
            'ng_count': ng_count,
            'ok_percent': ok_percent,
            'results': filtered_results
        }

    def get_weekly_report(self, year: int, week: int) -> Dict[str, Any]:
        """
        Недельный отчёт.
        :param year: Год
        :param week: Номер недели (1-52)
        :return: Словарь с данными отчёта
        """
        # Находим первый день недели
        first_day = datetime.strptime(f'{year}-W{week:02d}-1', '%Y-W%W-%w')
        last_day = first_day + timedelta(days=6)

        results = self.db.get_results(
            date_from=first_day.strftime('%Y-%m-%d'),
            date_to=last_day.strftime('%Y-%m-%d'),
            limit=10000
        )

        total = len(results)
        ok_count = sum(1 for r in results if r.get('result') == 'OK')
        ng_count = sum(1 for r in results if r.get('result') == 'NG')
        ok_percent = round((ok_count / total * 100), 2) if total > 0 else 0

        # Статистика по дням
        daily_stats = self._get_daily_stats(results)

        return {
            'year': year,
            'week': week,
            'date_from': first_day.strftime('%Y-%m-%d'),
            'date_to': last_day.strftime('%Y-%m-%d'),
            'total': total,
            'ok_count': ok_count,
            'ng_count': ng_count,
            'ok_percent': ok_percent,
            'daily_stats': daily_stats,
            'results': results
        }

    def get_monthly_report(self, year: int, month: int) -> Dict[str, Any]:
        """
        Месячный отчёт.
        :param year: Год
        :param month: Месяц (1-12)
        :return: Словарь с данными отчёта
        """
        # Первый и последний день месяца
        first_day = datetime(year, month, 1)
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)

        results = self.db.get_results(
            date_from=first_day.strftime('%Y-%m-%d'),
            date_to=last_day.strftime('%Y-%m-%d'),
            limit=10000
        )

        total = len(results)
        ok_count = sum(1 for r in results if r.get('result') == 'OK')
        ng_count = sum(1 for r in results if r.get('result') == 'NG')
        ok_percent = round((ok_count / total * 100), 2) if total > 0 else 0

        # Статистика по дням
        daily_stats = self._get_daily_stats(results)

        # Статистика по сменам (агрегированная)
        shift_stats = self._get_shift_stats(results)

        return {
            'year': year,
            'month': month,
            'month_name': self._get_month_name(month),
            'total': total,
            'ok_count': ok_count,
            'ng_count': ng_count,
            'ok_percent': ok_percent,
            'daily_stats': daily_stats,
            'shift_stats': shift_stats,
            'results': results
        }

    def get_ng_analysis(self, date_from: str, date_to: str) -> Dict[str, Any]:
        """
        Анализ брака.
        :param date_from: Дата начала периода
        :param date_to: Дата окончания периода
        :return: Словарь с данными анализа
        """
        results = self.db.get_results(
            date_from=date_from,
            date_to=date_to,
            limit=10000
        )

        ng_results = [r for r in results if r.get('result') == 'NG']

        # Распределение по времени суток
        time_distribution = self._get_time_distribution(ng_results)

        # Распределение по проектам
        project_distribution = self._get_project_stats(ng_results)

        return {
            'date_from': date_from,
            'date_to': date_to,
            'total_ng': len(ng_results),
            'time_distribution': time_distribution,
            'project_distribution': project_distribution
        }

    def _get_hourly_stats(self, results: List[Dict]) -> List[Dict]:
        """Статистика по часам."""
        hourly = {}
        for r in results:
            try:
                dt = datetime.fromisoformat(r.get('timestamp', ''))
                hour = dt.hour
                if hour not in hourly:
                    hourly[hour] = {'total': 0, 'ok': 0, 'ng': 0}
                hourly[hour]['total'] += 1
                if r.get('result') == 'OK':
                    hourly[hour]['ok'] += 1
                else:
                    hourly[hour]['ng'] += 1
            except:
                pass

        return [
            {
                'hour': h,
                'total': data['total'],
                'ok': data['ok'],
                'ng': data['ng'],
                'ok_percent': round(data['ok'] / data['total'] * 100, 2) if data['total'] > 0 else 0
            }
            for h, data in sorted(hourly.items())
        ]

    def _get_daily_stats(self, results: List[Dict]) -> List[Dict]:
        """Статистика по дням."""
        daily = {}
        for r in results:
            try:
                dt = datetime.fromisoformat(r.get('timestamp', ''))
                day = dt.strftime('%Y-%m-%d')
                if day not in daily:
                    daily[day] = {'total': 0, 'ok': 0, 'ng': 0}
                daily[day]['total'] += 1
                if r.get('result') == 'OK':
                    daily[day]['ok'] += 1
                else:
                    daily[day]['ng'] += 1
            except:
                pass

        return [
            {
                'date': d,
                'total': data['total'],
                'ok': data['ok'],
                'ng': data['ng'],
                'ok_percent': round(data['ok'] / data['total'] * 100, 2) if data['total'] > 0 else 0
            }
            for d, data in sorted(daily.items())
        ]

    def _get_project_stats(self, results: List[Dict]) -> List[Dict]:
        """Статистика по проектам."""
        projects = {}
        for r in results:
            project = r.get('project_name', 'Неизвестно')
            if project not in projects:
                projects[project] = {'total': 0, 'ok': 0, 'ng': 0}
            projects[project]['total'] += 1
            if r.get('result') == 'OK':
                projects[project]['ok'] += 1
            else:
                projects[project]['ng'] += 1

        return [
            {
                'project': p,
                'total': data['total'],
                'ok': data['ok'],
                'ng': data['ng'],
                'ok_percent': round(data['ok'] / data['total'] * 100, 2) if data['total'] > 0 else 0
            }
            for p, data in sorted(projects.items(), key=lambda x: x[1]['total'], reverse=True)
        ]

    def _get_scenario_stats(self, results: List[Dict]) -> List[Dict]:
        """Статистика по сценариям."""
        scenarios = {}
        for r in results:
            scenario = r.get('scenario', 'Неизвестно')
            if scenario not in scenarios:
                scenarios[scenario] = {'total': 0, 'ok': 0, 'ng': 0}
            scenarios[scenario]['total'] += 1
            if r.get('result') == 'OK':
                scenarios[scenario]['ok'] += 1
            else:
                scenarios[scenario]['ng'] += 1

        return [
            {
                'scenario': s,
                'total': data['total'],
                'ok': data['ok'],
                'ng': data['ng'],
                'ok_percent': round(data['ok'] / data['total'] * 100, 2) if data['total'] > 0 else 0
            }
            for s, data in sorted(scenarios.items())
        ]

    def _get_shift_stats(self, results: List[Dict]) -> List[Dict]:
        """Статистика по сменам."""
        shifts = {
            1: {'total': 0, 'ok': 0, 'ng': 0},
            2: {'total': 0, 'ok': 0, 'ng': 0},
            3: {'total': 0, 'ok': 0, 'ng': 0}
        }

        for r in results:
            try:
                dt = datetime.fromisoformat(r.get('timestamp', ''))
                hour = dt.hour
                shift = self._get_shift_by_hour(hour)
                shifts[shift]['total'] += 1
                if r.get('result') == 'OK':
                    shifts[shift]['ok'] += 1
                else:
                    shifts[shift]['ng'] += 1
            except:
                pass

        return [
            {
                'shift': s,
                'shift_name': self._get_shift_name(s),
                'total': data['total'],
                'ok': data['ok'],
                'ng': data['ng'],
                'ok_percent': round(data['ok'] / data['total'] * 100, 2) if data['total'] > 0 else 0
            }
            for s, data in shifts.items()
        ]

    def _get_time_distribution(self, results: List[Dict]) -> Dict[str, int]:
        """Распределение по времени суток."""
        distribution = {'morning': 0, 'afternoon': 0, 'night': 0}

        for r in results:
            try:
                dt = datetime.fromisoformat(r.get('timestamp', ''))
                hour = dt.hour
                if 6 <= hour < 14:
                    distribution['morning'] += 1
                elif 14 <= hour < 22:
                    distribution['afternoon'] += 1
                else:
                    distribution['night'] += 1
            except:
                pass

        return distribution

    def _filter_by_shift(self, results: List[Dict], start_time: str, end_time: str, shift: int) -> List[Dict]:
        """Фильтрация результатов по смене."""
        filtered = []

        for r in results:
            try:
                dt = datetime.fromisoformat(r.get('timestamp', ''))
                hour = dt.hour
                minute = dt.minute
                time_minutes = hour * 60 + minute

                start_h, start_m = map(int, start_time.split(':'))
                end_h, end_m = map(int, end_time.split(':'))
                start_minutes = start_h * 60 + start_m
                end_minutes = end_h * 60 + end_m

                if shift == 3:  # Ночная смена переходит через полночь
                    if time_minutes >= start_minutes or time_minutes < end_minutes:
                        filtered.append(r)
                else:
                    if start_minutes <= time_minutes < end_minutes:
                        filtered.append(r)
            except:
                pass

        return filtered

    def _get_shift_by_hour(self, hour: int) -> int:
        """Определение номера смены по часу."""
        if 6 <= hour < 14:
            return 1
        elif 14 <= hour < 22:
            return 2
        else:
            return 3

    def _get_shift_name(self, shift: int) -> str:
        """Название смены."""
        names = {
            1: 'Утренняя (06:00-14:00)',
            2: 'Дневная (14:00-22:00)',
            3: 'Ночная (22:00-06:00)'
        }
        return names.get(shift, f'Смена {shift}')

    def _get_month_name(self, month: int) -> str:
        """Название месяца."""
        names = {
            1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
            5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
            9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
        }
        return names.get(month, f'Месяц {month}')


# Глобальный экземпляр
_report_generator: Optional[ReportGenerator] = None


def get_report_generator() -> ReportGenerator:
    """Получение экземпляра ReportGenerator (singleton)."""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator
