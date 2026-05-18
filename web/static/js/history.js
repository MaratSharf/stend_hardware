/**
 * history.js - Логика страницы истории проверок
 * Оптимизированная версия с debounce, кэшированием и эффективной работой с DOM
 */

let currentPage = 1;
const pageSize = 20;
let currentFilters = {};
let totalPages = 1;
let dailyChartInstance = null;
let filterDebounceTimer = null;
const DEBOUNCE_DELAY = 300;

// Кэш для изображений чтобы избежать повторных запросов
const imageCache = new Map();

document.addEventListener('DOMContentLoaded', () => {
    setDefaultDates();
    loadStatistics();
    loadResults();
    setupFilters();
    setupPagination();
    setupDatePresets();
    setupDetailModal();
    setupLazyLoading();
});

function setDefaultDates() {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('filterDateFrom').value = today;
    document.getElementById('filterDateTo').value = today;
}

function setupDatePresets() {
    const presets = document.querySelectorAll('.preset-btn');
    presets.forEach(btn => {
        btn.addEventListener('click', () => {
            presets.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const preset = btn.dataset.preset;
            const today = new Date();
            const fmt = d => d.toISOString().split('T')[0];
            let from, to;

            switch (preset) {
                case 'today':
                    from = to = fmt(today);
                    break;
                case 'yesterday':
                    const yest = new Date(today);
                    yest.setDate(yest.getDate() - 1);
                    from = to = fmt(yest);
                    break;
                case 'week':
                    const weekAgo = new Date(today);
                    weekAgo.setDate(weekAgo.getDate() - 6);
                    from = fmt(weekAgo);
                    to = fmt(today);
                    break;
                case 'month':
                    const monthAgo = new Date(today);
                    monthAgo.setDate(monthAgo.getDate() - 29);
                    from = fmt(monthAgo);
                    to = fmt(today);
                    break;
            }

            document.getElementById('filterDateFrom').value = from;
            document.getElementById('filterDateTo').value = to;
            applyCurrentFilters();
        });
    });
}

function applyCurrentFilters() {
    const result = document.getElementById('filterResult').value;
    const dateFrom = document.getElementById('filterDateFrom').value;
    const dateTo = document.getElementById('filterDateTo').value;
    const orderNumber = document.getElementById('filterOrder').value.trim();
    const projectName = document.getElementById('filterProject').value.trim();
    const scenario = document.getElementById('filterScenario').value;

    currentFilters = {};
    if (result) currentFilters.result = result;
    if (dateFrom) currentFilters.date_from = dateFrom;
    if (dateTo) currentFilters.date_to = dateTo;
    if (orderNumber) currentFilters.order_number = orderNumber;
    if (projectName) currentFilters.project_name = projectName;
    if (scenario) currentFilters.scenario = scenario;

    currentPage = 1;
    loadResults();
    loadStatistics();
}

async function loadStatistics() {
    try {
        const params = new URLSearchParams(currentFilters);
        const response = await fetch(`/api/statistics?${params}`);
        const data = await response.json();

        if (data.success) {
            const stats = data.statistics;
            // Оптимизация: обновляем DOM только если данные изменились
            updateStatElement('statTotal', stats.total);
            updateStatElement('statOk', stats.ok_count);
            updateStatElement('statNg', stats.ng_count);
            updateStatElement('statOkPercent', stats.ok_percent + '%');
            
            // Обновляем график
            renderDailyChart(data.daily || []);
        }
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
    }
}

// Оптимизация: функция для обновления текстового содержимого только при изменении
function updateStatElement(elementId, newValue) {
    const element = document.getElementById(elementId);
    if (element && element.textContent !== String(newValue)) {
        element.textContent = newValue;
    }
}

async function loadResults() {
    const tbody = document.getElementById('resultsBody');
    // Используем DocumentFragment для оптимизации DOM операций
    tbody.innerHTML = '<tr><td colspan="7" class="loading">Загрузка...</td></tr>';

    try {
        const params = new URLSearchParams({
            limit: pageSize,
            offset: (currentPage - 1) * pageSize,
            ...currentFilters
        });

        const response = await fetch(`/api/results?${params}`);
        const data = await response.json();

        if (data.success) {
            const results = data.results || [];
            if (results.length > 0) {
                const startIndex = (currentPage - 1) * pageSize + 1;
                
                // Создаём DocumentFragment для批量 вставки
                const fragment = document.createDocumentFragment();
                const tempContainer = document.createElement('tbody');
                tempContainer.innerHTML = results.map((r, idx) => {
                    const rowNumber = startIndex + idx;
                    return `
                        <tr data-id="${r.id}">
                            <td>${rowNumber}</td>
                            <td>${formatDateTime(r.timestamp)}</td>
                            <td><span class="result-badge ${r.result.toLowerCase()}">${r.result}</span></td>
                            <td>${r.order_number ? `<span class="order-link">${r.order_number}</span>` : '<span class="no-order">—'}</td>
                            <td>${r.scenario || '—'}</td>
                            <td>${r.project_name || '—'}</td>
                            <td>${renderImage(r.image_path)}</td>
                        </tr>
                    `;
                }).join('');
                
                tbody.innerHTML = tempContainer.innerHTML;

                // Навешиваем обработчики клика на строки с использованием делегирования
                tbody.removeEventListener('click', handleRowClick);
                tbody.addEventListener('click', handleRowClick);
            } else {
                tbody.innerHTML = '<tr><td colspan="7" class="empty-state">Нет данных</td></tr>';
            }

            const total = data.total || 0;
            totalPages = Math.ceil(total / pageSize) || 1;
            if (currentPage > totalPages) {
                currentPage = totalPages;
                if (totalPages > 0) {
                    loadResults();
                    return;
                }
            }
            updatePagination();
        } else {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-state">Ошибка загрузки</td></tr>';
            totalPages = 1;
            updatePagination();
        }
    } catch (error) {
        console.error('Ошибка загрузки результатов:', error);
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state">Ошибка загрузки</td></tr>';
        totalPages = 1;
        updatePagination();
    }
}

// Обработчик клика по строке таблицы (делегирование событий)
function handleRowClick(e) {
    const row = e.target.closest('tr[data-id]');
    if (row && row.dataset.id) {
        openDetailModal(row.dataset.id);
    }
}

function formatDateTime(isoString) {
    if (!isoString) return '—';
    const date = new Date(isoString);
    return date.toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', year: '2-digit',
        hour: '2-digit', minute: '2-digit'
    });
}

function formatDateTimeFull(isoString) {
    if (!isoString) return '—';
    const date = new Date(isoString);
    return date.toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
}

function renderImage(imagePath) {
    if (!imagePath) return '<div class="no-image">Нет</div>';
    
    // Используем кэш для проверки существования изображения
    if (imageCache.has(imagePath)) {
        const cached = imageCache.get(imagePath);
        if (cached === null) {
            return '<div class="no-image">Ошибка</div>';
        }
        return `<img src="/images/${imagePath}" alt="Снимок" class="thumb-image" loading="lazy">`;
    }
    
    return `<img src="/images/${imagePath}" alt="Снимок" class="thumb-image" loading="lazy" onerror="this.parentElement.innerHTML='<div class=\'no-image\'>Ошибка</div>'; imageCache.set('${imagePath}', null)">`;
}

// Функция для настройки ленивой загрузки и оптимизации изображений
function setupLazyLoading() {
    // Нативный loading="lazy" уже используется, эта функция для дополнительной оптимизации
}


function setupFilters() {
    const applyFiltersHandler = () => {
        clearTimeout(filterDebounceTimer);
        filterDebounceTimer = setTimeout(applyCurrentFilters, DEBOUNCE_DELAY);
    };

    document.getElementById('applyFilters').addEventListener('click', applyCurrentFilters);

    // Debounce для текстовых полей
    ['filterOrder', 'filterProject'].forEach(id => {
        document.getElementById(id).addEventListener('input', applyFiltersHandler);
    });

    // Для select и date используем change без debounce
    ['filterResult', 'filterDateFrom', 'filterDateTo', 'filterScenario'].forEach(id => {
        document.getElementById(id).addEventListener('change', applyCurrentFilters);
    });

    document.getElementById('refreshBtn').addEventListener('click', () => {
        document.getElementById('filterResult').value = '';
        document.getElementById('filterOrder').value = '';
        document.getElementById('filterProject').value = '';
        document.getElementById('filterScenario').value = '';
        setDefaultDates();
        document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
        currentFilters = {};
        currentPage = 1;
        loadResults();
        loadStatistics();
    });

    // Экспорт в CSV
    document.getElementById('exportCsvBtn').addEventListener('click', () => {
        exportData('csv');
    });

    // Экспорт в Excel
    document.getElementById('exportExcelBtn').addEventListener('click', () => {
        exportData('excel');
    });
}

function exportData(format) {
    const btn = document.getElementById(format === 'csv' ? 'exportCsvBtn' : 'exportExcelBtn');
    const originalText = btn.innerHTML;
    
    // Показываем индикатор загрузки
    btn.classList.add('spinner');
    btn.disabled = true;
    
    try {
        const params = new URLSearchParams({
            ...currentFilters,
            limit: 10000  // Большой лимит для экспорта
        });
        
        const url = `/api/export/${format}?${params}`;
        
        // Создаём невидимую ссылку для скачивания
        const link = document.createElement('a');
        link.href = url;
        link.download = '';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Показываем уведомление
        showToast(`Экспорт в ${format === 'csv' ? 'CSV' : 'Excel'} начат`, 'success');
    } catch (error) {
        console.error('Ошибка экспорта:', error);
        showToast('Ошибка при экспорте', 'error');
    } finally {
        // Сбрасываем состояние кнопки
        setTimeout(() => {
            btn.classList.remove('spinner');
            btn.disabled = false;
            btn.innerHTML = originalText;
        }, 1000);
    }
}

function setupPagination() {
    document.getElementById('firstPageTop').addEventListener('click', () => goToPage(1));
    document.getElementById('prevPageTop').addEventListener('click', () => goToPage(currentPage - 1));
    document.getElementById('nextPageTop').addEventListener('click', () => goToPage(currentPage + 1));
    document.getElementById('lastPageTop').addEventListener('click', () => goToPage(totalPages));

    document.getElementById('firstPageBottom').addEventListener('click', () => goToPage(1));
    document.getElementById('prevPageBottom').addEventListener('click', () => goToPage(currentPage - 1));
    document.getElementById('nextPageBottom').addEventListener('click', () => goToPage(currentPage + 1));
    document.getElementById('lastPageBottom').addEventListener('click', () => goToPage(totalPages));
}

function goToPage(page) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    loadResults();
}

function updatePagination() {
    const update = (prefix) => {
        const infoEl = document.getElementById(`pageInfo${prefix}`);
        const firstBtn = document.getElementById(`firstPage${prefix}`);
        const prevBtn = document.getElementById(`prevPage${prefix}`);
        const nextBtn = document.getElementById(`nextPage${prefix}`);
        const lastBtn = document.getElementById(`lastPage${prefix}`);

        if (infoEl) infoEl.textContent = `Страница ${currentPage} из ${totalPages}`;
        if (firstBtn) firstBtn.disabled = currentPage === 1;
        if (prevBtn) prevBtn.disabled = currentPage === 1;
        if (nextBtn) nextBtn.disabled = currentPage === totalPages;
        if (lastBtn) lastBtn.disabled = currentPage === totalPages;
    };
    update('Top');
    update('Bottom');
}

/* ==================== ДЕТАЛЬНЫЙ ПРОСМОТР ==================== */

function setupDetailModal() {
    const modal = document.getElementById('detailModal');
    const overlay = modal.querySelector('.detail-modal__overlay');
    const closeBtn = document.getElementById('detailModalClose');

    overlay.addEventListener('click', closeDetailModal);
    closeBtn.addEventListener('click', closeDetailModal);

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeDetailModal();
    });

    // Zoom по клику на изображение в модалке
    const imgContainer = document.getElementById('detailImageContainer');
    imgContainer.addEventListener('click', (e) => {
        const img = imgContainer.querySelector('img');
        if (img) {
            img.classList.toggle('zoomed');
        }
    });
}

async function openDetailModal(resultId) {
    const modal = document.getElementById('detailModal');
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';

    try {
        const response = await fetch(`/api/results/${resultId}`);
        const data = await response.json();

        if (data.success && data.result) {
            populateDetailModal(data.result);
        } else {
            showDetailError('Запись не найдена');
        }
    } catch (error) {
        console.error('Ошибка загрузки деталей:', error);
        showDetailError('Ошибка загрузки данных');
    }
}

function populateDetailModal(r) {
    // Бейдж результата
    const badge = document.getElementById('detailResultBadge');
    badge.textContent = r.result;
    badge.className = 'result-badge ' + (r.result || '').toLowerCase();

    // Дата/время
    document.getElementById('detailTimestamp').textContent = formatDateTimeFull(r.timestamp);

    // Основная информация
    document.getElementById('detailId').textContent = r.id || '—';
    document.getElementById('detailOrder').textContent = r.order_number || '—';
    document.getElementById('detailScenario').textContent = r.scenario || '—';
    document.getElementById('detailProject').textContent = r.project_name || '—';

    // Изображение
    const imgContainer = document.getElementById('detailImageContainer');
    if (r.image_path) {
        imgContainer.innerHTML = `<img src="/images/${r.image_path}" alt="Снимок проверки #${r.id}" onerror="this.parentElement.innerHTML='<div class=\\'detail-image-placeholder\\'>Изображение недоступно</div>'">`;
    } else {
        imgContainer.innerHTML = '<div class="detail-image-placeholder">Нет изображения</div>';
    }

    // Датчики
    const sensorsContainer = document.getElementById('detailSensors');
    const sensors = [
        { key: 'sensor_d1', label: 'D1' },
        { key: 'sensor_d2', label: 'D2' },
        { key: 'sensor_d3', label: 'D3' },
        { key: 'sensor_d4', label: 'D4' },
        { key: 'tumbler_a', label: 'Тумблер A' },
        { key: 'tumbler_b', label: 'Тумблер B' }
    ];

    const sensorsHtml = sensors.map(s => {
        const val = r[s.key];
        const isOn = val === 1 || val === true;
        return `
            <div class="detail-sensor">
                <span class="detail-sensor__label">${s.label}</span>
                <span class="detail-sensor__value ${isOn ? 'on' : 'off'}">${isOn ? 'ON' : 'OFF'}</span>
            </div>
        `;
    }).join('');
    sensorsContainer.innerHTML = sensorsHtml || '<span class="text-muted">Нет данных</span>';

    // Raw-данные
    const rawEl = document.getElementById('detailRaw');
    if (r.raw) {
        // Пытаемся отформатировать JSON
        try {
            const parsed = JSON.parse(r.raw);
            rawEl.textContent = JSON.stringify(parsed, null, 2);
        } catch {
            rawEl.textContent = r.raw;
        }
    } else {
        rawEl.textContent = '—';
    }
}

function showDetailError(message) {
    document.getElementById('detailResultBadge').textContent = 'Ошибка';
    document.getElementById('detailTimestamp').textContent = message;
    document.getElementById('detailImageContainer').innerHTML = '<div class="detail-image-placeholder">' + message + '</div>';
}

function closeDetailModal() {
    const modal = document.getElementById('detailModal');
    modal.classList.remove('active');
    document.body.style.overflow = '';

    // Сбросить zoom изображения
    const img = modal.querySelector('.detail-image-container img');
    if (img) img.classList.remove('zoomed');
}

/* ==================== ГРАФИК ДИНАМИКИ ==================== */

function renderDailyChart(dailyData) {
    const canvas = document.getElementById('dailyChart');
    const noDataEl = document.getElementById('chartNoData');
    
    // Если нет данных
    if (!dailyData || dailyData.length === 0) {
        if (dailyChartInstance) {
            dailyChartInstance.destroy();
            dailyChartInstance = null;
        }
        canvas.style.display = 'none';
        noDataEl.style.display = 'flex';
        return;
    }
    
    canvas.style.display = 'block';
    noDataEl.style.display = 'none';
    
    // Подготовка данных
    // dailyData приходит в порядке DESC (свежие сначала), разворачиваем
    const reversed = [...dailyData].reverse();
    
    const labels = reversed.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
    });
    
    const okData = reversed.map(d => d.ok_count || 0);
    const ngData = reversed.map(d => d.ng_count || 0);
    
    const ctx = canvas.getContext('2d');
    
    // Уничтожаем старый график
    if (dailyChartInstance) {
        dailyChartInstance.destroy();
    }
    
    // Настраиваем размеры canvas для чёткости
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    
    // Рисуем график
    dailyChartInstance = drawChart(ctx, labels, okData, ngData, rect.width, rect.height);
}

function drawChart(ctx, labels, okData, ngData, width, height) {
    const padding = { top: 20, right: 20, bottom: 40, left: 50 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    
    // Очищаем canvas
    ctx.clearRect(0, 0, width, height);
    
    // Находим максимум для масштаба
    const allValues = [...okData, ...ngData];
    const maxVal = Math.max(...allValues, 1);
    const yStep = Math.ceil(maxVal / 5) || 1;
    
    // Рисуем сетку
    ctx.strokeStyle = 'rgba(128, 128, 128, 0.2)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
        const y = padding.top + (chartHeight / 5) * i;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
        ctx.stroke();
        
        // Подписи оси Y
        ctx.fillStyle = 'rgba(128, 128, 128, 0.8)';
        ctx.font = '11px Inter, sans-serif';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        ctx.fillText((maxVal - yStep * i).toString(), padding.left - 8, y);
    }
    
    // Рисуем подписи оси X
    ctx.fillStyle = 'rgba(128, 128, 128, 0.8)';
    ctx.font = '10px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    
    const labelStep = Math.ceil(labels.length / 10); // Показываем ~10 подписей
    labels.forEach((label, i) => {
        if (i % labelStep === 0 || i === labels.length - 1) {
            const x = padding.left + (chartWidth / (labels.length - 1)) * i;
            ctx.fillText(label, x, height - padding.bottom + 8);
        }
    });
    
    // Функция для рисования линии графика
    const drawLine = (data, color, fill) => {
        ctx.beginPath();
        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5;
        ctx.lineJoin = 'round';
        ctx.lineCap = 'round';
        
        data.forEach((val, i) => {
            const x = padding.left + (chartWidth / (data.length - 1)) * i;
            const y = padding.top + chartHeight - (val / maxVal) * chartHeight;
            
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        ctx.stroke();
        
        // Заполнение под графиком
        if (fill) {
            ctx.lineTo(padding.left + chartWidth, padding.top + chartHeight);
            ctx.lineTo(padding.left, padding.top + chartHeight);
            ctx.closePath();
            ctx.fillStyle = color.replace('1)', '0.15)').replace('rgb', 'rgba');
            ctx.fill();
        }
    };
    
    // Рисуем NG (красный) сначала, чтобы OK был сверху
    drawLine(ngData, 'rgb(255, 71, 87)', true);
    drawLine(okData, 'rgb(0, 255, 136)', true);
    
    // Рисуем точки на графиках
    const drawDots = (data, color) => {
        data.forEach((val, i) => {
            const x = padding.left + (chartWidth / (data.length - 1)) * i;
            const y = padding.top + chartHeight - (val / maxVal) * chartHeight;
            
            ctx.beginPath();
            ctx.fillStyle = color;
            ctx.arc(x, y, 4, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = 'white';
            ctx.lineWidth = 2;
            ctx.stroke();
        });
    };
    
    drawDots(ngData, 'rgb(255, 71, 87)');
    drawDots(okData, 'rgb(0, 255, 136)');
}