/**
 * history.js - Логика страницы истории проверок
 * Оптимизированная версия с debounce, кэшированием и эффективной работой с DOM
 */

let currentPage = 1;
const pageSize = 20;
let currentFilters = {};
let totalPages = 1;
let dailyChartInstance = null;
let pieChartInstance = null;
let projectChartInstance = null;
let topNgChartInstance = null;
let filterDebounceTimer = null;
let autoUpdateTimer = null;
const DEBOUNCE_DELAY = 300;
const AUTO_UPDATE_INTERVAL = 30000; // 30 секунд

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
    setupCanvasResizing();
    startAutoUpdate();
});

// Автообновление статистики и графиков
function startAutoUpdate() {
    if (autoUpdateTimer) {
        clearInterval(autoUpdateTimer);
    }
    autoUpdateTimer = setInterval(() => {
        loadStatistics();
        updateLastUpdateTime();
    }, AUTO_UPDATE_INTERVAL);
}

function stopAutoUpdate() {
    if (autoUpdateTimer) {
        clearInterval(autoUpdateTimer);
        autoUpdateTimer = null;
    }
}

function updateLastUpdateTime() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const el = document.getElementById('lastUpdate');
    if (el) {
        el.textContent = timeStr;
    }
}

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
    let dateFrom = document.getElementById('filterDateFrom').value;
    let dateTo = document.getElementById('filterDateTo').value;
    const orderNumber = document.getElementById('filterOrder').value.trim();
    const projectName = document.getElementById('filterProject').value.trim();
    const scenario = document.getElementById('filterScenario').value;

    // Если выбрана только одна дата (в любом поле), установить её в оба поля
    if (dateFrom && !dateTo) {
        dateTo = dateFrom;
    }
    if (dateTo && !dateFrom) {
        dateFrom = dateTo;
    }

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
            
            // Обновляем все графики
            renderDailyChart(data.daily || []);
            renderPieChart(stats);
            renderProjectChart(data.project || []);
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
                            <td>${r.order_number ? `<span class="order-link">${r.order_number}</span>` : '<span class="no-order">—</span>'}</td>
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

    // Экспорт через выпадающий список
    const exportDropdownBtn = document.getElementById('exportDropdownBtn');
    const exportDropdownMenu = document.getElementById('exportDropdownMenu');

    if (exportDropdownBtn && exportDropdownMenu) {
        // Открытие/закрытие выпадающего списка
        exportDropdownBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            exportDropdownMenu.classList.toggle('show');
        });

        // Обработка выбора формата
        exportDropdownMenu.querySelectorAll('.export-dropdown-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const format = item.dataset.format;
                exportDropdownMenu.classList.remove('show');
                exportData(format);
            });
        });

        // Закрытие при клике вне
        document.addEventListener('click', () => {
            exportDropdownMenu.classList.remove('show');
        });
    }
}

function exportData(format) {
    try {
        const params = new URLSearchParams({
            ...currentFilters,
            limit: format === 'pdf' ? 500 : 10000  // Ограничение для PDF
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
        const formatName = format === 'csv' ? 'CSV' : format === 'excel' ? 'Excel' : 'PDF';
        showToast(`Экспорт в ${formatName} начат`, 'success');
    } catch (error) {
        console.error('Ошибка экспорта:', error);
        showToast('Ошибка при экспорте', 'error');
    }
}

function setupPagination() {
    document.getElementById('firstPage').addEventListener('click', () => goToPage(1));
    document.getElementById('prevPage').addEventListener('click', () => goToPage(currentPage - 1));
    document.getElementById('nextPage').addEventListener('click', () => goToPage(currentPage + 1));
    document.getElementById('lastPage').addEventListener('click', () => goToPage(totalPages));
}

function goToPage(page) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    loadResults();
}

function updatePagination() {
    const infoEl = document.getElementById('pageInfo');
    const firstBtn = document.getElementById('firstPage');
    const prevBtn = document.getElementById('prevPage');
    const nextBtn = document.getElementById('nextPage');
    const lastBtn = document.getElementById('lastPage');

    if (infoEl) infoEl.textContent = `Страница ${currentPage} из ${totalPages}`;
    if (firstBtn) firstBtn.disabled = currentPage === 1;
    if (prevBtn) prevBtn.disabled = currentPage === 1;
    if (nextBtn) nextBtn.disabled = currentPage === totalPages;
    if (lastBtn) lastBtn.disabled = currentPage === totalPages;
}

/* ==================== ДЕТАЛЬНЫЙ ПРОСМОТР ==================== */

let currentDetailResultId = null;

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

    // Экспорт в PDF из модального окна
    const exportDetailBtn = document.getElementById('exportDetailPdfBtn');
    if (exportDetailBtn) {
        exportDetailBtn.addEventListener('click', exportDetailPdf);
    }
}

async function openDetailModal(resultId) {
    currentDetailResultId = resultId;
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
        imgContainer.innerHTML = `<img src="/images/${r.image_path}" alt="Снимок проверки #${r.id}" onerror="this.parentElement.innerHTML='<div class=\'detail-image-placeholder\'>Изображение недоступно</div>'">`;
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

/**
 * Экспорт текущей записи из модального окна в PDF.
 */
function exportDetailPdf() {
    if (!currentDetailResultId) {
        showToast('Нет данных для экспорта', 'error');
        return;
    }

    const btn = document.getElementById('exportDetailPdfBtn');
    const originalText = btn.innerHTML;
    btn.classList.add('spinner');
    btn.disabled = true;

    try {
        const url = `/api/export/pdf/${currentDetailResultId}`;

        const link = document.createElement('a');
        link.href = url;
        link.download = '';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        showToast('PDF сохранён', 'success');
    } catch (error) {
        console.error('Ошибка экспорта PDF:', error);
        showToast('Ошибка при сохранении PDF', 'error');
    } finally {
        setTimeout(() => {
            btn.classList.remove('spinner');
            btn.disabled = false;
            btn.innerHTML = originalText;
        }, 1000);
    }
}

/* ==================== ГРАФИК ДИНАМИКИ ==================== */

function renderDailyChart(dailyData) {
    const canvas = document.getElementById('dailyChart');
    const noDataEl = document.getElementById('chartNoData');
    
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
    
    const reversed = [...dailyData].reverse();
    
    const labels = reversed.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
    });
    
    const okData = reversed.map(d => d.ok_count || 0);
    const ngData = reversed.map(d => d.ng_count || 0);
    
    const ctx = canvas.getContext('2d');
    
    if (dailyChartInstance) {
        dailyChartInstance.destroy();
    }
    
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    
    dailyChartInstance = drawChart(ctx, labels, okData, ngData, rect.width, rect.height);
}

function drawChart(ctx, labels, okData, ngData, width, height) {
    const padding = { top: 20, right: 20, bottom: 40, left: 50 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    
    ctx.clearRect(0, 0, width, height);
    
    const allValues = [...okData, ...ngData];
    const maxVal = Math.max(...allValues, 1);
    const yStep = Math.ceil(maxVal / 5) || 1;
    
    ctx.strokeStyle = 'rgba(128, 128, 128, 0.2)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
        const y = padding.top + (chartHeight / 5) * i;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
        ctx.stroke();
        
        ctx.fillStyle = 'rgba(128, 128, 128, 0.8)';
        ctx.font = '11px Inter, sans-serif';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        ctx.fillText((maxVal - yStep * i).toString(), padding.left - 8, y);
    }
    
    ctx.fillStyle = 'rgba(128, 128, 128, 0.8)';
    ctx.font = '10px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    
    const labelStep = Math.ceil(labels.length / 10);
    labels.forEach((label, i) => {
        if (i % labelStep === 0 || i === labels.length - 1) {
            const x = padding.left + (chartWidth / (labels.length - 1)) * i;
            ctx.fillText(label, x, height - padding.bottom + 8);
        }
    });
    
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
        
        if (fill) {
            ctx.lineTo(padding.left + chartWidth, padding.top + chartHeight);
            ctx.lineTo(padding.left, padding.top + chartHeight);
            ctx.closePath();
            ctx.fillStyle = color.replace('1)', '0.15)').replace('rgb', 'rgba');
            ctx.fill();
        }
    };
    
    drawLine(ngData, 'rgb(255, 71, 87)', true);
    drawLine(okData, 'rgb(0, 255, 136)', true);
    
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

/* ==================== КРУГОВАЯ ДИАГРАММА OK/NG ==================== */

function renderPieChart(stats) {
    const canvas = document.getElementById('pieChart');
    const noDataEl = document.getElementById('pieNoData');
    
    if (!stats || stats.total === 0) {
        canvas.style.display = 'none';
        noDataEl.style.display = 'flex';
        return;
    }
    
    canvas.style.display = 'block';
    noDataEl.style.display = 'none';
    
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    
    const okCount = stats.ok_count || 0;
    const ngCount = stats.ng_count || 0;
    const total = stats.total || 1;
    
    const okPercent = (okCount / total * 100).toFixed(1);
    const ngPercent = (ngCount / total * 100).toFixed(1);
    
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const radius = Math.min(centerX, centerY) - 30;
    const innerRadius = radius * 0.55;
    
    // Очищаем canvas
    ctx.clearRect(0, 0, rect.width, rect.height);
    
    // Рисуем дуги
    const okAngle = (okCount / total) * Math.PI * 2;
    const ngAngle = (ngCount / total) * Math.PI * 2;
    
    // NG (красный) — сначала
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, -Math.PI / 2, -Math.PI / 2 + ngAngle);
    ctx.arc(centerX, centerY, innerRadius, -Math.PI / 2 + ngAngle, -Math.PI / 2, true);
    ctx.closePath();
    ctx.fillStyle = 'rgb(255, 71, 87)';
    ctx.fill();
    
    // OK (зелёный)
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, -Math.PI / 2 + ngAngle, -Math.PI / 2 + ngAngle + okAngle);
    ctx.arc(centerX, centerY, innerRadius, -Math.PI / 2 + ngAngle + okAngle, -Math.PI / 2 + ngAngle, true);
    ctx.closePath();
    ctx.fillStyle = 'rgb(0, 255, 136)';
    ctx.fill();
    
    // Текст в центре
    ctx.fillStyle = 'var(--text-primary)';
    ctx.font = 'bold 18px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`${stats.ok_percent}%`, centerX, centerY - 8);
    
    ctx.fillStyle = 'var(--text-secondary)';
    ctx.font = '11px Inter, sans-serif';
    ctx.fillText('качество', centerX, centerY + 10);
    
    // Легенда под диаграммой
    const legendY = rect.height - 20;
    
    // OK
    ctx.fillStyle = 'rgb(0, 255, 136)';
    ctx.beginPath();
    ctx.arc(centerX - 60, legendY, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = 'var(--text-secondary)';
    ctx.font = '12px Inter, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(`OK ${okPercent}%`, centerX - 48, legendY + 4);
    
    // NG
    ctx.fillStyle = 'rgb(255, 71, 87)';
    ctx.beginPath();
    ctx.arc(centerX + 20, legendY, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = 'var(--text-secondary)';
    ctx.fillText(`NG ${ngPercent}%`, centerX + 32, legendY + 4);
}

/* ==================== ГИСТОГРАММА ПО ПРОЕКТАМ ==================== */

function renderProjectChart(projectData) {
    const canvas = document.getElementById('scenarioChart');
    const noDataEl = document.getElementById('scenarioNoData');
    
    if (!projectData || projectData.length === 0) {
        canvas.style.display = 'none';
        noDataEl.style.display = 'flex';
        return;
    }
    
    canvas.style.display = 'block';
    noDataEl.style.display = 'none';
    
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    
    ctx.clearRect(0, 0, rect.width, rect.height);
    
    const padding = { top: 20, right: 20, bottom: 50, left: 50 };
    const chartWidth = rect.width - padding.left - padding.right;
    const chartHeight = rect.height - padding.top - padding.bottom;
    
    const maxVal = Math.max(...projectData.map(d => d.total || 0), 1);
    
    // Сетка
    ctx.strokeStyle = 'rgba(128, 128, 128, 0.15)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = padding.top + (chartHeight / 4) * i;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(rect.width - padding.right, y);
        ctx.stroke();
        
        ctx.fillStyle = 'rgba(128, 128, 128, 0.6)';
        ctx.font = '10px Inter, sans-serif';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        ctx.fillText(Math.round(maxVal - (maxVal / 4) * i).toString(), padding.left - 6, y);
    }
    
    const barWidth = chartWidth / projectData.length * 0.6;
    const barGap = chartWidth / projectData.length * 0.4;
    
    projectData.forEach((d, i) => {
        const x = padding.left + (chartWidth / projectData.length) * i + barGap / 2;
        const okHeight = ((d.ok_count || 0) / maxVal) * chartHeight;
        const ngHeight = ((d.ng_count || 0) / maxVal) * chartHeight;
        
        // NG bar (снизу)
        ctx.fillStyle = 'rgb(255, 71, 87)';
        ctx.fillRect(x, padding.top + chartHeight - ngHeight, barWidth / 2, ngHeight);
        
        // OK bar (снизу, рядом)
        ctx.fillStyle = 'rgb(0, 255, 136)';
        ctx.fillRect(x + barWidth / 2, padding.top + chartHeight - okHeight, barWidth / 2, okHeight);
        
        // Подпись проекта (с обрезкой если длинная)
        ctx.fillStyle = 'rgba(128, 128, 128, 0.8)';
        ctx.font = '11px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        let projectName = d.project_name || '—';
        if (projectName.length > 12) {
            projectName = projectName.substring(0, 10) + '...';
        }
        ctx.fillText(projectName, x + barWidth / 2, padding.top + chartHeight + 8);
        
        // Значение над столбцом
        if (d.total > 0) {
            ctx.fillStyle = 'var(--text-primary)';
            ctx.font = 'bold 10px Inter, sans-serif';
            ctx.fillText(d.total.toString(), x + barWidth / 2, padding.top - 4);
        }
    });
}

// Для обратной совместимости
function renderScenarioChart(projectData) {
    renderProjectChart(projectData);
}

/* ==================== ТОП ЗАКАЗОВ ПО БРАКУ ==================== */

function renderTopNgChart(topNgData) {
    const canvas = document.getElementById('topNgChart');
    const noDataEl = document.getElementById('topNgNoData');
    
    if (!topNgData || topNgData.length === 0) {
        canvas.style.display = 'none';
        noDataEl.style.display = 'flex';
        return;
    }
    
    canvas.style.display = 'block';
    noDataEl.style.display = 'none';
    
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    
    ctx.clearRect(0, 0, rect.width, rect.height);
    
    const padding = { top: 15, right: 60, bottom: 10, left: 120 };
    const chartWidth = rect.width - padding.left - padding.right;
    const chartHeight = rect.height - padding.top - padding.bottom;
    
    const maxVal = Math.max(...topNgData.map(d => d.ng_count || 0), 1);
    const rowHeight = chartHeight / topNgData.length;
    
    topNgData.forEach((d, i) => {
        const y = padding.top + i * rowHeight + rowHeight * 0.15;
        const barHeight = rowHeight * 0.7;
        const barWidth = ((d.ng_count || 0) / maxVal) * chartWidth;
        
        // Фон полосы
        ctx.fillStyle = 'rgba(255, 71, 87, 0.08)';
        ctx.fillRect(padding.left, y, chartWidth, barHeight);
        
        // Бар
        ctx.fillStyle = 'rgb(255, 71, 87)';
        ctx.fillRect(padding.left, y, barWidth, barHeight);
        
        // Название заказа (слева)
        ctx.fillStyle = 'var(--text-primary)';
        ctx.font = '11px Inter, sans-serif';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        const label = d.order_number || 'Без заказа';
        const truncated = label.length > 18 ? label.substring(0, 15) + '...' : label;
        ctx.fillText(truncated, padding.left - 8, y + barHeight / 2);
        
        // Значение NG (справа от бара)
        ctx.fillStyle = 'var(--text-primary)';
        ctx.font = 'bold 11px Inter, sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText(d.ng_count.toString(), padding.left + barWidth + 6, y + barHeight / 2);
        
        // OK count
        ctx.fillStyle = 'var(--text-secondary)';
        ctx.font = '9px Inter, sans-serif';
        ctx.fillText(`(OK: ${d.ok_count || 0})`, padding.left + barWidth + 30, y + barHeight / 2);
    });
}

/* ==================== УТИЛИТЫ ДЛЯ CANVAS ==================== */


function setupCanvasResizing() {
    // Обновляем все графики при изменении размера окна
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            loadStatistics();
        }, 250);
    });
}
