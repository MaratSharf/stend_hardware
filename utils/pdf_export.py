# -*- coding: utf-8 -*-
"""
PDF экспортёр для отчётов по истории проверок.
Генерирует красиво оформленный PDF с логотипом, KPI, графиками и таблицей.
"""

import io
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageTemplate,
    Frame,
    Image as RLImage,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.barcharts import VerticalBarChart


# === Регистрация шрифтов с поддержкой кириллицы ===
_FONT_DIR = os.path.join(os.path.dirname(__file__), '..', 'web', 'static', 'fonts', 'ttf')


def _register_fonts():
    """Регистрирует шрифты Inter, если доступны."""
    registered = []
    for name, filename in [
        ('Inter', 'Inter-Regular.ttf'),
        ('Inter-Bold', 'Inter-Bold.ttf'),
        ('Inter-Medium', 'Inter-Medium.ttf'),
    ]:
        path = os.path.join(_FONT_DIR, filename)
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                registered.append(name)
            except Exception:
                pass
    return registered


_REGISTERED = _register_fonts()

# Цветовая палитра проекта
_COLOR_OK = colors.Color(0 / 255, 255 / 255, 136 / 255)
_COLOR_NG = colors.Color(255 / 255, 71 / 255, 87 / 255)
_COLOR_PRIMARY = colors.Color(102 / 255, 126 / 255, 234 / 255)
_COLOR_PRIMARY_DARK = colors.Color(82 / 255, 106 / 255, 214 / 255)
_COLOR_TEXT = colors.Color(51 / 255, 51 / 255, 51 / 255)
_COLOR_TEXT_LIGHT = colors.Color(120 / 255, 120 / 255, 120 / 255)
_COLOR_BG = colors.Color(248 / 255, 249 / 255, 250 / 255)


def _get_font_name(bold=False):
    if bold and 'Inter-Bold' in _REGISTERED:
        return 'Inter-Bold'
    if 'Inter' in _REGISTERED:
        return 'Inter'
    return 'Helvetica-Bold' if bold else 'Helvetica'


class PDFExporter:
    """Экспортёр истории проверок в PDF."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        font = _get_font_name()
        font_bold = _get_font_name(bold=True)

        self.title_style = ParagraphStyle(
            'PDFTitle',
            parent=self.styles['Heading1'],
            fontName=font_bold,
            fontSize=20,
            textColor=_COLOR_PRIMARY,
            spaceAfter=6 * mm,
            alignment=1,  # center
        )
        self.subtitle_style = ParagraphStyle(
            'PDFSubtitle',
            parent=self.styles['Normal'],
            fontName=font,
            fontSize=10,
            textColor=_COLOR_TEXT_LIGHT,
            spaceAfter=4 * mm,
            alignment=1,
        )
        self.heading_style = ParagraphStyle(
            'PDFHeading',
            parent=self.styles['Heading2'],
            fontName=font_bold,
            fontSize=13,
            textColor=_COLOR_PRIMARY_DARK,
            spaceAfter=3 * mm,
            spaceBefore=4 * mm,
        )
        self.normal_style = ParagraphStyle(
            'PDFNormal',
            parent=self.styles['Normal'],
            fontName=font,
            fontSize=9,
            textColor=_COLOR_TEXT,
            leading=12,
        )
        self.cell_style = ParagraphStyle(
            'PDFCell',
            parent=self.styles['Normal'],
            fontName=font,
            fontSize=8,
            textColor=_COLOR_TEXT,
            leading=10,
        )
        self.cell_header_style = ParagraphStyle(
            'PDFCellHeader',
            parent=self.styles['Normal'],
            fontName=font_bold,
            fontSize=8,
            textColor=colors.whitesmoke,
            leading=10,
        )
        self.footer_style = ParagraphStyle(
            'PDFFooter',
            parent=self.styles['Normal'],
            fontName=font,
            fontSize=8,
            textColor=_COLOR_TEXT_LIGHT,
            alignment=1,
        )

    def export_history_report(self, report: dict) -> bytes:
        """
        Генерирует PDF-отчёт на основе словаря report.

        report = {
            'date': str,
            'statistics': {'total': int, 'ok_count': int, 'ng_count': int, 'ok_percent': float},
            'project': [{'project_name': str, 'total': int, 'ok_count': int, 'ng_count': int}, ...],
            'results': [{...}, ...],
        }
        """
        buffer = io.BytesIO()
        doc = BaseDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
        )

        frame = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height,
            id='normal',
        )
        template = PageTemplate(id='main', frames=frame, onPage=self._draw_header_footer)
        doc.addPageTemplates([template])

        story = []

        # Заголовок
        story.append(Paragraph("Отчёт по истории проверок", self.title_style))
        story.append(Paragraph(f"Период: {report.get('date', '')}", self.subtitle_style))
        story.append(Spacer(1, 4 * mm))

        # KPI таблица
        story.append(self._build_kpi_table(report.get('statistics', {})))
        story.append(Spacer(1, 4 * mm))

        # Гистограмма по проектам
        project_data = report.get('project', [])
        if project_data:
            story.append(Paragraph("Статистика по проектам", self.heading_style))
            story.append(self._build_project_chart(project_data))
            story.append(Spacer(1, 4 * mm))

        # Таблица результатов (макс 100 строк)
        results = report.get('results', [])[:100]
        if results:
            story.append(Paragraph(f"Результаты проверок (первые {len(results)} записей)", self.heading_style))
            story.append(self._build_results_table(results))
            story.append(Spacer(1, 2 * mm))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def export_detail_report(self, result: dict) -> bytes:
        """Генерирует PDF-карточку одной проверки (для модального окна)."""
        buffer = io.BytesIO()
        doc = BaseDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
        )

        frame = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height,
            id='normal',
        )
        template = PageTemplate(id='main', frames=frame, onPage=self._draw_header_footer)
        doc.addPageTemplates([template])

        story = []

        # Заголовок
        story.append(Paragraph("Карточка проверки", self.title_style))
        story.append(Paragraph(f"Запись № {result.get('id', '—')}", self.subtitle_style))
        story.append(Spacer(1, 4 * mm))

        # Результат
        result_val = result.get('result', '—')
        result_color = _COLOR_OK if result_val == 'OK' else _COLOR_NG
        result_style = ParagraphStyle(
            'DetailResult',
            parent=self.normal_style,
            fontName=_get_font_name(bold=True),
            fontSize=14,
            textColor=result_color,
            alignment=1,
            spaceAfter=4 * mm,
        )
        story.append(Paragraph(f"Результат: {result_val}", result_style))

        # Изображение (если есть)
        image_path = result.get('image_path')
        if image_path:
            # Пробуем несколько возможных путей к изображению
            possible_paths = [
                # Путь относительно pdf_export.py -> data/images/foto/...
                os.path.join(os.path.dirname(__file__), '..', 'data', 'images', image_path),
                # Путь с подкаталогом foto (если image_path уже содержит OK/NG)
                os.path.join(os.path.dirname(__file__), '..', 'data', 'images', 'foto', image_path),
                # Прямой путь (если image_path абсолютный или относительный от корня проекта)
                os.path.join(os.path.dirname(__file__), '..', image_path),
            ]
            
            full_image_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    full_image_path = path
                    break
            
            if full_image_path:
                story.append(Paragraph("Изображение детали", self.heading_style))
                story.append(self._build_detail_image(full_image_path))
                story.append(Spacer(1, 4 * mm))

        # Основная информация
        story.append(Paragraph("Основная информация", self.heading_style))
        story.append(self._build_detail_info_table(result))
        story.append(Spacer(1, 4 * mm))

        # Датчики
        sensors = [
            ('sensor_d1', 'D1'),
            ('sensor_d2', 'D2'),
            ('sensor_d3', 'D3'),
            ('sensor_d4', 'D4'),
            ('tumbler_a', 'Тумблер A'),
            ('tumbler_b', 'Тумблер B'),
        ]
        story.append(Paragraph("Датчики", self.heading_style))
        story.append(self._build_sensors_table(result, sensors))
        story.append(Spacer(1, 4 * mm))

        # Raw-данные
        raw = result.get('raw')
        if raw:
            story.append(Paragraph("Raw-данные", self.heading_style))
            try:
                import json
                parsed = json.loads(raw)
                raw_text = json.dumps(parsed, ensure_ascii=False, indent=2)
            except Exception:
                raw_text = str(raw)
            raw_style = ParagraphStyle(
                'RawStyle',
                parent=self.normal_style,
                fontName='Courier',
                fontSize=8,
                leading=10,
            )
            story.append(Paragraph(raw_text.replace('\n', '<br/>').replace(' ', '&nbsp;'), raw_style))
            story.append(Spacer(1, 2 * mm))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def _build_detail_image(self, image_path: str):
        """Создаёт изображение для карточки проверки."""
        try:
            img = RLImage(image_path, width=120 * mm, height=90 * mm)
            return img
        except Exception:
            return Paragraph("Изображение недоступно", self.normal_style)

    def _build_detail_info_table(self, result: dict):
        """Создаёт таблицу с основной информацией о проверке."""
        data = [
            [Paragraph("<b>Поле</b>", self.cell_header_style), Paragraph("<b>Значение</b>", self.cell_header_style)],
            [Paragraph("ID записи", self.cell_style), Paragraph(str(result.get('id', '—')), self.cell_style)],
            [Paragraph("Дата/время", self.cell_style), Paragraph(str(result.get('timestamp', '—')), self.cell_style)],
            [Paragraph("Результат", self.cell_style), Paragraph(str(result.get('result', '—')), self.cell_style)],
            [Paragraph("Заказ", self.cell_style), Paragraph(str(result.get('order_number') or '—'), self.cell_style)],
            [Paragraph("Сценарий", self.cell_style), Paragraph(str(result.get('scenario') or '—'), self.cell_style)],
            [Paragraph("Проект", self.cell_style), Paragraph(str(result.get('project_name') or '—'), self.cell_style)],
        ]

        col_widths = [50 * mm, 110 * mm]
        table = Table(data, colWidths=col_widths, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), _COLOR_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), _get_font_name(bold=True)),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), _COLOR_BG),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        return table

    def _build_sensors_table(self, result: dict, sensors: list):
        """Создаёт таблицу состояния датчиков."""
        data = [
            [Paragraph("<b>Датчик</b>", self.cell_header_style), Paragraph("<b>Состояние</b>", self.cell_header_style)],
        ]
        for key, label in sensors:
            val = result.get(key)
            is_on = val == 1 or val is True
            state_text = 'ON' if is_on else 'OFF'
            state_color = 'green' if is_on else 'red'
            state_cell = Paragraph(
                f'<font color="{state_color}"><b>{state_text}</b></font>',
                self.cell_style,
            )
            data.append([
                Paragraph(label, self.cell_style),
                state_cell,
            ])

        col_widths = [50 * mm, 50 * mm]
        table = Table(data, colWidths=col_widths, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), _COLOR_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), _get_font_name(bold=True)),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), _COLOR_BG),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        return table

    def _draw_header_footer(self, canvas, doc):
        """Рисует логотип в шапке и номер страницы в подвале."""
        width, height = A4

        # Логотип VDT (если есть изображение)
        logo_path = os.path.join(
            os.path.dirname(__file__), '..', 'web', 'static', 'images',
            'VDT-Service_logo (compact)_medium_2.jpg'
        )
        if os.path.exists(logo_path):
            try:
                img = RLImage(logo_path, width=30 * mm, height=10 * mm)
                img.drawOn(canvas, doc.leftMargin, height - doc.topMargin + 2 * mm)
            except Exception:
                pass
        else:
            # Fallback: текстовый логотип
            canvas.setFont(_get_font_name(bold=True), 14)
            canvas.setFillColor(_COLOR_PRIMARY)
            canvas.drawString(doc.leftMargin, height - doc.topMargin + 6 * mm, "VDT Service")

        # Линия под шапкой
        canvas.setStrokeColor(_COLOR_PRIMARY)
        canvas.setLineWidth(0.5)
        canvas.line(
            doc.leftMargin,
            height - doc.topMargin - 2 * mm,
            width - doc.rightMargin,
            height - doc.topMargin - 2 * mm,
        )

        # Подвал с номером страницы
        canvas.setFont(_get_font_name(), 8)
        canvas.setFillColor(_COLOR_TEXT_LIGHT)
        page_text = f"Страница {doc.page} | Сгенерировано: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        canvas.drawCentredString(width / 2, 10 * mm, page_text)

        # Линия над подвалом
        canvas.setStrokeColor(colors.Color(0.9, 0.9, 0.9))
        canvas.setLineWidth(0.5)
        canvas.line(
            doc.leftMargin,
            14 * mm,
            width - doc.rightMargin,
            14 * mm,
        )

    def _build_kpi_table(self, stats: dict):
        """Создаёт таблицу с ключевыми показателями."""
        total = stats.get('total', 0)
        ok = stats.get('ok_count', 0)
        ng = stats.get('ng_count', 0)
        ok_percent = stats.get('ok_percent', 0.0)

        data = [
            [
                Paragraph("<b>Всего проверок</b>", self.cell_header_style),
                Paragraph("<b>Годен (OK)</b>", self.cell_header_style),
                Paragraph("<b>Брак (NG)</b>", self.cell_header_style),
                Paragraph("<b>% качества</b>", self.cell_header_style),
            ],
            [
                Paragraph(str(total), self.cell_style),
                Paragraph(str(ok), self.cell_style),
                Paragraph(str(ng), self.cell_style),
                Paragraph(f"{ok_percent:.1f}%", self.cell_style),
            ],
        ]

        col_widths = [45 * mm, 45 * mm, 45 * mm, 45 * mm]
        table = Table(data, colWidths=col_widths, hAlign='CENTER')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), _COLOR_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), _get_font_name(bold=True)),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), _COLOR_BG),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        return table

    def _build_project_chart(self, project_data: list):
        """Создаёт гистограмму по проектам с помощью Drawing."""
        # Ограничиваем количество проектов для читаемости
        project_data = project_data[:12]

        drawing = Drawing(400, 180)

        chart = VerticalBarChart()
        chart.x = 40
        chart.y = 30
        chart.height = 120
        chart.width = 340
        chart.barWidth = 12
        chart.groupSpacing = 15
        chart.barSpacing = 2

        chart.valueAxis.valueMin = 0
        max_val = max((d.get('total', 0) for d in project_data), default=1)
        chart.valueAxis.valueMax = max_val + max(1, int(max_val * 0.1))
        chart.valueAxis.valueStep = max(1, int((max_val + 1) / 5))

        chart.categoryAxis.labels.boxAnchor = 'ne'
        chart.categoryAxis.labels.dx = 8
        chart.categoryAxis.labels.dy = -2
        chart.categoryAxis.labels.angle = 30
        chart.categoryAxis.categoryNames = [d.get('project_name', '—') for d in project_data]

        ok_vals = [d.get('ok_count', 0) for d in project_data]
        ng_vals = [d.get('ng_count', 0) for d in project_data]
        chart.data = [ok_vals, ng_vals]
        chart.bars[0].fillColor = _COLOR_OK
        chart.bars[1].fillColor = _COLOR_NG

        # Легенда
        legend_ok = Rect(320, 160, 10, 10, fillColor=_COLOR_OK, strokeColor=None)
        legend_ng = Rect(320, 145, 10, 10, fillColor=_COLOR_NG, strokeColor=None)
        label_ok = String(335, 162, 'OK', fontName=_get_font_name(), fontSize=8, fillColor=_COLOR_TEXT)
        label_ng = String(335, 147, 'NG', fontName=_get_font_name(), fontSize=8, fillColor=_COLOR_TEXT)

        drawing.add(chart)
        drawing.add(legend_ok)
        drawing.add(legend_ng)
        drawing.add(label_ok)
        drawing.add(label_ng)

        return drawing

    def _build_results_table(self, results: list):
        """Создаёт таблицу с результатами проверок."""
        headers = [
            "№", "Дата/время", "Результат", "Заказ", "Сценарий", "Проект"
        ]
        header_paras = [Paragraph(f"<b>{h}</b>", self.cell_header_style) for h in headers]

        data = [header_paras]
        for i, r in enumerate(results, start=1):
            result_val = r.get('result', '')
            result_color = 'green' if result_val == 'OK' else 'red'
            result_cell = Paragraph(
                f'<font color="{result_color}"><b>{result_val}</b></font>',
                self.cell_style,
            )
            row = [
                Paragraph(str(i), self.cell_style),
                Paragraph(str(r.get('timestamp', '')), self.cell_style),
                result_cell,
                Paragraph(str(r.get('order_number', '') or '—'), self.cell_style),
                Paragraph(str(r.get('scenario', '') or '—'), self.cell_style),
                Paragraph(str(r.get('project_name', '') or '—'), self.cell_style),
            ]
            data.append(row)

        col_widths = [12 * mm, 32 * mm, 18 * mm, 30 * mm, 20 * mm, 38 * mm]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), _COLOR_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('ALIGN', (4, 0), (4, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), _get_font_name(bold=True)),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            # Чередование фона строк
            ('BACKGROUND', (0, 2), (-1, 2), _COLOR_BG),
            ('BACKGROUND', (0, 4), (-1, 4), _COLOR_BG),
            ('BACKGROUND', (0, 6), (-1, 6), _COLOR_BG),
            ('BACKGROUND', (0, 8), (-1, 8), _COLOR_BG),
            ('BACKGROUND', (0, 10), (-1, 10), _COLOR_BG),
        ]))
        return table


# Глобальный singleton
_pdf_exporter = None


def get_pdf_exporter():
    global _pdf_exporter
    if _pdf_exporter is None:
        _pdf_exporter = PDFExporter()
    return _pdf_exporter
