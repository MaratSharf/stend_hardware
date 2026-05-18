# Список изменений — Экран "История проверок"
**Дата:** 18 мая 2026
**Версия:** MV Stend v4.5+

---

## 1. Улучшенные фильтры и поиск

### 1.1 Бэкенд

**`utils/database.py`**
- Расширен метод `get_results()` — добавлены параметры:
  - `order_number` — поиск по номеру заказа (ILIKE, частичное совпадение)
  - `project_name` — поиск по названию проекта (ILIKE, частичное совпадение)
  - `scenario` — точный фильтр по сценарию

**`web/pages/history.py`**
- Endpoint `/api/results` теперь принимает дополнительные query-параметры:
  - `order_number`
  - `project_name`
  - `scenario`
- Пустые строки корректно обрабатываются как `None` (не передаются в БД)

### 1.2 Фронтенд

**`web/templates/history.html`**
- Блок `.filters-bar` переработан:
  - Добавлена панель быстрых пресетов дат: "Сегодня", "Вчера", "Неделя", "Месяц"
  - Добавлены поля:
    - `#filterOrder` — текстовый поиск по номеру заказа
    - `#filterProject` — текстовый поиск по названию проекта
    - `#filterScenario` — выпадающий список сценариев (A, B, C)

**`web/static/css/history.css`**
- Исправлен баг: HTML использовал `.page-actions`, CSS определял `.filters-bar` → стили теперь применяются корректно
- Добавлены стили:
  - `.date-presets` — горизонтальная панель кнопок-пресетов
  - `.preset-btn` / `.preset-btn.active` — кнопки быстрого выбора дат
  - `.filters-row` — flex-контейнер для полей фильтров
  - `.date-separator` — разделитель между полями дат

**`web/static/js/history.js`**
- Добавлена функция `setupDatePresets()` — обработчики кнопок-пресетов:
  - Автоматически выставляет даты `from`/`to`
  - Подсвечивает активный пресет
  - Автоматически применяет фильтры после выбора пресета
- Добавлена функция `applyCurrentFilters()` — собирает значения всех полей:
  - result, date_from, date_to, order_number, project_name, scenario
  - Сбрасывает пагинацию на 1-ю страницу
  - Вызывает `loadResults()` + `loadStatistics()`
- Кнопка "Сбросить" теперь очищает все новые поля (заказ, проект, сценарий)

---

## 2. Детальный просмотр записи (модальное окно)

### 2.1 HTML-разметка

**`web/templates/history.html`**
- Добавлено модальное окно `#detailModal`:
  - **Левая колонка** — увеличенное изображение снимка с zoom по клику
  - **Правая колонка** — информация о проверке:
    - Заголовок: бейдж результата (OK/NG) + полная дата/время
    - Сетка полей: ID, Заказ, Сценарий, Проект
    - Блок датчиков: D1–D4, Тумблер A, Тумблер B (цветовая индикация ON/OFF)
    - Блок Raw-данных: форматированный JSON/текст в моноширинном блоке

### 2.2 Стили

**`web/static/css/history.css`**
- Добавлен блок стилей детального просмотра:
  - `.detail-modal` — фиксированное окно с backdrop-blur
  - `.detail-modal__content` — анимация появления (`detailModalIn`)
  - `.detail-modal__image-col` (55%) + `.detail-modal__info-col` (45%)
  - `.detail-image-container img.zoomed` — масштабирование изображения (×1.8)
  - `.detail-grid` — двухколоночная сетка полей
  - `.detail-sensor` — карточки датчиков с классами `.on` / `.off`
  - `.detail-raw` — блок с `font-family: monospace`, автоперенос, прокрутка
  - `tbody tr { cursor: pointer }` — указатель при наведении на строки
  - Адаптивность: на экранах < 900px колонки складываются вертикально

### 2.3 Логика JavaScript

**`web/static/js/history.js`**
- Добавлены функции:
  - `setupDetailModal()` — инициализация обработчиков (overlay, крестик, Escape, zoom)
  - `openDetailModal(resultId)` — запрос `/api/results/<id>`, показ модалки, блокировка скролла
  - `populateDetailModal(r)` — заполнение всех полей модалки:
    - Изображение: `<img src="/images/{path}">` с fallback
    - Датчики: рендер 6 индикаторов с цветом
    - Raw: попытка `JSON.parse()` + `JSON.stringify(..., null, 2)` для красивого форматирования
  - `showDetailError(message)` — отображение ошибки внутри модалки
  - `closeDetailModal()` — закрытие, разблокировка скролла, сброс zoom
  - `formatDateTimeFull()` — полная дата с секундами для деталки
- Строки таблицы (`<tr>`) теперь содержат `data-id` и обработчик `click` для открытия деталей

---

## 3. Экспорт данных (CSV/Excel)

### 3.1 Бэкенд

**`web/pages/history.py`**
- Добавлен endpoint `/api/export/csv`:
  - Принимает те же фильтры, что и `/api/results`
  - Возвращает CSV-файл с разделителем `;` (для Excel)
  - Кодировка UTF-8 с BOM (корректное отображение кириллицы)
  - Имя файла: `export_YYYYMMDD_HHMMSS.csv`

- Добавлен endpoint `/api/export/excel`:
  - Принимает те же фильтры
  - Использует `ExcelReportExporter.export_history_report()`
  - Два листа: "Сводка" (статистика) + "Результаты" (детальные данные)
  - Имя файла: `export_YYYYMMDD_HHMMSS.xlsx`

**`utils/excel_export.py`**
- Добавлен метод `export_history_report(report)`:
  - Лист "Сводка": период, всего, OK, NG, % качества
  - Лист "Результаты": все поля с русскими заголовками
  - Автоформатирование ширины колонок
  - Стили заголовков (цвет, шрифт, выравнивание)

### 3.2 Фронтенд

**`web/templates/history.html`**
- В панель фильтров добавлены кнопки:
  - `#exportCsvBtn` — экспорт в CSV (иконка 📄)
  - `#exportExcelBtn` — экспорт в Excel (иконка 📊)
  - Разделитель `.export-divider` между фильтрами и экспортом

**`web/static/css/history.css`**
- Стили кнопок экспорта:
  - `.btn-export` — базовый стиль
  - `.btn-export:hover` — эффект наведения (поднятие + цвет)
  - `.btn-export.spinner` — индикатор загрузки (анимация вращения)
  - `.export-divider` — вертикальный разделитель

**`web/static/js/history.js`**
- Добавлена функция `exportData(format)`:
  - Собирает все текущие фильтры из `currentFilters`
  - Показывает спиннер на кнопке
  - Открывает ссылку на скачивание в том же окне
  - Показывает toast-уведомление об успехе/ошибке
  - Разблокирует кнопку через 1 секунду

---

## 4. Исправления багов

| Баг | Файл | Исправление |
|-----|------|-------------|
| Фильтры не стилизовались | `history.html` | Класс изменён с `page-actions` на `filters-bar` |
| Отсутствующие миниатюры не стилизовались | `history.css` | Класс `.no-image-thumb` определён (используется в CSS), JS создаёт `div.no-image` — стили применяются через общие правила |
| `#lastUpdate` в подвале не обновлялся | `history.js` | Поле пока не заполняется (заглушка), готов к подключению автообновления |

---

## 5. API-изменения

| Endpoint | Изменение |
|----------|-----------|
| `GET /api/results` | Новые параметры: `order_number`, `project_name`, `scenario` |
| `GET /api/results/<int:result_id>` | Без изменений (используется для детального просмотра) |
| `GET /api/statistics` | Без изменений |
| `GET /api/export/csv` | **Новый** — экспорт в CSV |
| `GET /api/export/excel` | **Новый** — экспорт в Excel |

---

## Файлы, подвергшиеся изменению

1. `utils/database.py`
2. `utils/excel_export.py`
3. `web/pages/history.py`
4. `web/templates/history.html`
5. `web/static/css/history.css`
6. `web/static/js/history.js`
