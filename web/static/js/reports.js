/**
 * reports.js - Логика страницы отчётов
 */

// Глобальное состояние
let currentReport = null;
let currentReportType = null;

// =============================================
// ИНИЦИАЛИЗАЦИЯ
// =============================================
document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    setupButtons();
    setupDateDefaults();
});

// =============================================
// УСТАНОВКА ДАТ ПО УМОЛЧАНИЮ
// =============================================
function setupDateDefaults() {
    const today = new Date().toISOString().split('T')[0];
    
    // Дневной отчёт - сегодня
    document.getElementById('dailyDate').value = today;
    
    // Сменный отчёт - сегодня
    document.getElementById('shiftDate').value = today;
    
    // Недельный отчёт - текущий год и неделя
    const now = new Date();
    document.getElementById('weeklyYear').value = now.getFullYear();
    const weekNum = getWeekNumber(now);
    document.getElementById('weeklyWeek').value = weekNum;
    
    // Месячный отчёт - текущий год и месяц
    document.getElementById('monthlyYear').value = now.getFullYear();
    document.getElementById('monthlyMonth').value = now.getMonth() + 1;
    
    // Анализ брака - последние 7 дней
    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    document.getElementById('ngDateFrom').value = weekAgo.toISOString().split('T')[0];
    document.getElementById('ngDateTo').value = today;
}

// =============================================
// ВКЛАДКИ
// =============================================
function setupTabs() {
    const tabBtns = document.querySelectorAll('.reports-tabs .tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;

            // Убираем активный класс у всех кнопок и контента
            tabBtns.forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            // Добавляем активный класс выбранной вкладке
            btn.classList.add('active');
            document.getElementById(tabId + '-tab').classList.add('active');
        });
    });
}

// =============================================
// КНОПКИ
// =============================================
function setupButtons() {
    // Дневной отчёт
    document.getElementById('loadDailyReport').addEventListener('click', loadDailyReport);
    
    // Сменный отчёт
    document.getElementById('loadShiftReport').addEventListener('click', loadShiftReport);
    
    // Недельный отчёт
    document.getElementById('loadWeeklyReport').addEventListener('click', loadWeeklyReport);
    
    // Месячный отчёт
    document.getElementById('loadMonthlyReport').addEventListener('click', loadMonthlyReport);
    
    // Анализ брака
    document.getElementById('loadNgAnalysis').addEventListener('click', loadNgAnalysis);
    
    // Экспорт в Excel
    document.getElementById('exportExcelBtn').addEventListener('click', exportToExcel);
    
    // Печать
    document.getElementById('printReportBtn').addEventListener('click', () => {
        window.print();
    });
}

// =============================================
// ЗАГРУЗКА ДНЕВНОГО ОТЧЁТА
// =============================================
async function loadDailyReport() {
    const date = document.getElementById('dailyDate').value;
    if (!date) {
        showNotification('Выберите дату', 'warning');
        return;
    }

    const container = document.getElementById('dailyReportContent');
    container.innerHTML = '<div class="loading-placeholder"><div class="loading-icon">⏳</div><p>Загрузка отчёта...</p></div>';

    try {
        const response = await fetch(`/api/reports/daily?date=${date}`);
        const data = await response.json();

        if (data.success) {
            currentReport = data.report;
            currentReportType = 'daily';
            container.innerHTML = renderDailyReport(data.report);
        } else {
            container.innerHTML = `<div class="loading-placeholder"><div class="loading-icon">❌</div><p>Ошибка: ${data.error}</p></div>`;
        }
    } catch (error) {
        container.innerHTML = `<div class="loading-placeholder"><div class="loading-icon">❌</div><p>Ошибка подключения: ${error.message}</p></div>`;
    }
}

// =============================================
// ЗАГРУЗКА СМЕННОГО ОТЧЁТА
// =============================================
async function loadShiftReport() {
    const date = document.getElementById('shiftDate').value;
    const shift = document.getElementById('shiftNumber').value;
    
    if (!date) {
        showNotification('Выберите дату', 'warning');
        return;
    }

    const container = document.getElementById('shiftReportContent');
    container.innerHTML = '<div class="loading-placeholder"><div class="loading-icon">⏳</div><p>Загрузка отчёта...</p></div>';

    try {
        const response = await fetch(`/api/reports/shift?date=${date}&shift=${shift}`);
        const data = await response.json();

        if (data.success) {
            currentReport = data.report;
            currentReportType = 'shift';
            container.innerHTML = renderShiftReport(data.report);
        } else {
            container.innerHTML = `<div class="loading-placeholder"><div class="loading-icon">❌</div><p>Ошибка: ${data.error}</p></div>`;
        }
    } catch (error) {
        container.innerHTML = `<div class="loading-placeholder"><div class="loading-icon">❌</div><p>Ошибка подключения: ${error.message}</p></div>`;
    }
}

// =============================================
// ЗАГРУЗКА НЕДЕЛЬНОГО ОТЧЁТА
// =============================================
async function loadWeeklyReport() {
    const year = document.getElementById('weeklyYear').value;
    const week = document.getElementById('weeklyWeek').value;

    const container = document.getElementById('weeklyReportContent');
    container.innerHTML = '<div class="loading-placeholder"><div class="loading-icon">⏳</div><p>Загрузка отчёта...</p></div>';

    try {
        const response = await fetch(`/api/reports/weekly?year=${year}&week=${week}`);
        const data = await response.json();

        if (data.success) {
            currentReport = data.report;
            currentReportType = 'weekly';
            container.innerHTML = renderWeeklyReport(data.report);
        } else {
            container.innerHTML = `<div class="loading-placeholder"><div class="loading-icon">❌</div><p>Ошибка: ${data.error}</p></div>`;
        }
    } catch (error) {
        container.innerHTML = `<div class="loading-placeholder"><div class="loading-icon">❌</div><p>Ошибка подключения: ${error.message}</p></div>`;
    }
}

// =============================================
// ЗАГРУЗКА МЕСЯЧНОГО ОТЧЁТА
// =============================================
async function loadMonthlyReport() {
    const year = document.getElementById('monthlyYear').value;
    const month = document.getElementById('monthlyMonth').value;

    const container = document.getElementById('monthlyReportContent');
    container.innerHTML = '<div class="loading-placeholder"><div class="loading-icon">⏳</div><p>Загрузка отчёта...</p></div>';

    try {
        const response = await fetch(`/api/reports/monthly?year=${year}&month=${month}`);
        const data = await response.json();

        if (data.success) {
            currentReport = data.report;
            currentReportType = 'monthly';
            container.innerHTML = renderMonthlyReport(data.report);
        } else {
            container.innerHTML = `<div class="loading-placeholder"><div class="loading-icon">❌</div><p>Ошибка: ${data.error}</p></div>`;
        }
    } catch (error) {
        container.innerHTML = `<div class="loading-placeholder"><div class="loading-icon">❌</div><p>Ошибка подключения: ${error.message}</p></div>`;
    }
}

// =============================================
// ЗАГРУЗКА АНАЛИЗА БРАКА
// =============================================
async function loadNgAnalysis() {
    const dateFrom = document.getElementById('ngDateFrom').value;
    const dateTo = document.getElementById('ngDateTo').value;

    if (!dateFrom || !dateTo) {
        showNotification('Выберите период', 'warning');
        return;
    }

    const container = document.getElementById('ngAnalysisContent');
    container.innerHTML = '<div class="loading-placeholder"><div class="loading-icon">⏳</div><p>Загрузка отчёта...</p></div>';

    try {
        const response = await fetch(`/api/reports/ng-analysis?date_from=${dateFrom}&date_to=${dateTo}`);
        const data = await response.json();

        if (data.success) {
            currentReport = data.report;
            currentReportType = 'ng-analysis';
            container.innerHTML = renderNgAnalysis(data.report);
        } else {
            container.innerHTML = `<div class="loading-placeholder"><div class="loading-icon">❌</div><p>Ошибка: ${data.error}</p></div>`;
        }
    } catch (error) {
        container.innerHTML = `<div class="loading-placeholder"><div class="loading-icon">❌</div><p>Ошибка подключения: ${error.message}</p></div>`;
    }
}

// =============================================
// РЕНДЕРИНГ ДНЕВНОГО ОТЧЁТА
// =============================================
function renderDailyReport(report) {
    return `
        <div class="report-section">
            <h2 class="report-section-title">
                <span class="report-section-icon">📅</span>
                Дневной отчёт за ${formatDate(report.date)}
            </h2>
            
            <div class="stats-cards">
                <div class="stat-card primary">
                    <div class="stat-icon">📊</div>
                    <div class="stat-value">${report.total}</div>
                    <div class="stat-label">Всего проверок</div>
                </div>
                <div class="stat-card success">
                    <div class="stat-icon">✅</div>
                    <div class="stat-value">${report.ok_count}</div>
                    <div class="stat-label">Годен (OK)</div>
                </div>
                <div class="stat-card danger">
                    <div class="stat-icon">❌</div>
                    <div class="stat-value">${report.ng_count}</div>
                    <div class="stat-label">Брак (NG)</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-icon">📈</div>
                    <div class="stat-value">${report.ok_percent}%</div>
                    <div class="stat-label">% качества</div>
                </div>
            </div>
        </div>

        ${report.hourly_stats.length > 0 ? `
        <div class="report-section">
            <h3 class="report-section-title">
                <span class="report-section-icon">🕐</span>
                Статистика по часам
            </h3>
            <table class="report-table">
                <thead>
                    <tr>
                        <th>Час</th>
                        <th>Всего</th>
                        <th>OK</th>
                        <th>NG</th>
                        <th>% качества</th>
                    </tr>
                </thead>
                <tbody>
                    ${report.hourly_stats.map(h => `
                        <tr>
                            <td>${String(h.hour).padStart(2, '0')}:00</td>
                            <td>${h.total}</td>
                            <td><span class="badge badge-ok">${h.ok}</span></td>
                            <td><span class="badge badge-ng">${h.ng}</span></td>
                            <td>
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <span>${h.ok_percent}%</span>
                                    <div class="progress-bar" style="width: 100px;">
                                        <div class="progress-fill" style="width: ${h.ok_percent}%"></div>
                                    </div>
                                </div>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
        ` : ''}

        ${report.project_stats.length > 0 ? `
        <div class="report-section">
            <h3 class="report-section-title">
                <span class="report-section-icon">🔧</span>
                Статистика по проектам
            </h3>
            <table class="report-table">
                <thead>
                    <tr>
                        <th>Проект</th>
                        <th>Всего</th>
                        <th>OK</th>
                        <th>NG</th>
                        <th>% качества</th>
                    </tr>
                </thead>
                <tbody>
                    ${report.project_stats.map(p => `
                        <tr>
                            <td>${p.project}</td>
                            <td>${p.total}</td>
                            <td><span class="badge badge-ok">${p.ok}</span></td>
                            <td><span class="badge badge-ng">${p.ng}</span></td>
                            <td>${p.ok_percent}%</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
        ` : ''}
    `;
}

// =============================================
// РЕНДЕРИНГ СМЕННОГО ОТЧЁТА
// =============================================
function renderShiftReport(report) {
    return `
        <div class="report-section">
            <h2 class="report-section-title">
                <span class="report-section-icon">🔄</span>
                Сменный отчёт за ${formatDate(report.date)} (${report.shift_name})
            </h2>
            
            <div class="stats-cards">
                <div class="stat-card primary">
                    <div class="stat-icon">📊</div>
                    <div class="stat-value">${report.total}</div>
                    <div class="stat-label">Всего проверок</div>
                </div>
                <div class="stat-card success">
                    <div class="stat-icon">✅</div>
                    <div class="stat-value">${report.ok_count}</div>
                    <div class="stat-label">Годен (OK)</div>
                </div>
                <div class="stat-card danger">
                    <div class="stat-icon">❌</div>
                    <div class="stat-value">${report.ng_count}</div>
                    <div class="stat-label">Брак (NG)</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-icon">📈</div>
                    <div class="stat-value">${report.ok_percent}%</div>
                    <div class="stat-label">% качества</div>
                </div>
            </div>
        </div>
    `;
}

// =============================================
// РЕНДЕРИНГ НЕДЕЛЬНОГО ОТЧЁТА
// =============================================
function renderWeeklyReport(report) {
    return `
        <div class="report-section">
            <h2 class="report-section-title">
                <span class="report-section-icon">📆</span>
                Недельный отчёт #${report.week} (${report.date_from} — ${report.date_to})
            </h2>
            
            <div class="stats-cards">
                <div class="stat-card primary">
                    <div class="stat-icon">📊</div>
                    <div class="stat-value">${report.total}</div>
                    <div class="stat-label">Всего проверок</div>
                </div>
                <div class="stat-card success">
                    <div class="stat-icon">✅</div>
                    <div class="stat-value">${report.ok_count}</div>
                    <div class="stat-label">Годен (OK)</div>
                </div>
                <div class="stat-card danger">
                    <div class="stat-icon">❌</div>
                    <div class="stat-value">${report.ng_count}</div>
                    <div class="stat-label">Брак (NG)</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-icon">📈</div>
                    <div class="stat-value">${report.ok_percent}%</div>
                    <div class="stat-label">% качества</div>
                </div>
            </div>
        </div>

        ${report.daily_stats.length > 0 ? `
        <div class="report-section">
            <h3 class="report-section-title">
                <span class="report-section-icon">📅</span>
                Статистика по дням
            </h3>
            <table class="report-table">
                <thead>
                    <tr>
                        <th>Дата</th>
                        <th>Всего</th>
                        <th>OK</th>
                        <th>NG</th>
                        <th>% качества</th>
                    </tr>
                </thead>
                <tbody>
                    ${report.daily_stats.map(d => `
                        <tr>
                            <td>${formatDate(d.date)}</td>
                            <td>${d.total}</td>
                            <td><span class="badge badge-ok">${d.ok}</span></td>
                            <td><span class="badge badge-ng">${d.ng}</span></td>
                            <td>${d.ok_percent}%</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
        ` : ''}
    `;
}

// =============================================
// РЕНДЕРИНГ МЕСЯЧНОГО ОТЧЁТА
// =============================================
function renderMonthlyReport(report) {
    return `
        <div class="report-section">
            <h2 class="report-section-title">
                <span class="report-section-icon">📊</span>
                Месячный отчёт: ${report.month_name} ${report.year}
            </h2>
            
            <div class="stats-cards">
                <div class="stat-card primary">
                    <div class="stat-icon">📊</div>
                    <div class="stat-value">${report.total}</div>
                    <div class="stat-label">Всего проверок</div>
                </div>
                <div class="stat-card success">
                    <div class="stat-icon">✅</div>
                    <div class="stat-value">${report.ok_count}</div>
                    <div class="stat-label">Годен (OK)</div>
                </div>
                <div class="stat-card danger">
                    <div class="stat-icon">❌</div>
                    <div class="stat-value">${report.ng_count}</div>
                    <div class="stat-label">Брак (NG)</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-icon">📈</div>
                    <div class="stat-value">${report.ok_percent}%</div>
                    <div class="stat-label">% качества</div>
                </div>
            </div>
        </div>

        ${report.shift_stats ? `
        <div class="report-section">
            <h3 class="report-section-title">
                <span class="report-section-icon">🔄</span>
                Статистика по сменам
            </h3>
            <div class="report-grid">
                ${report.shift_stats.map(s => `
                    <div class="stat-card">
                        <div class="stat-icon">👥</div>
                        <div class="stat-value">${s.total}</div>
                        <div class="stat-label">${s.shift_name}</div>
                        <div style="margin-top: 8px; font-size: 12px;">
                            <span class="badge badge-ok">OK: ${s.ok}</span>
                            <span class="badge badge-ng">NG: ${s.ng}</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
        ` : ''}
    `;
}

// =============================================
// РЕНДЕРИНГ АНАЛИЗА БРАКА
// =============================================
function renderNgAnalysis(report) {
    return `
        <div class="report-section">
            <h2 class="report-section-title">
                <span class="report-section-icon">❌</span>
                Анализ брака (${formatDate(report.date_from)} — ${formatDate(report.date_to)})
            </h2>
            
            <div class="stats-cards">
                <div class="stat-card danger">
                    <div class="stat-icon">🔴</div>
                    <div class="stat-value">${report.total_ng}</div>
                    <div class="stat-label">Всего брака</div>
                </div>
            </div>
        </div>

        <div class="report-section">
            <h3 class="report-section-title">
                <span class="report-section-icon">🕐</span>
                Распределение по времени суток
            </h3>
            <div class="report-grid">
                <div class="stat-card">
                    <div class="stat-icon">🌅</div>
                    <div class="stat-value">${report.time_distribution.morning || 0}</div>
                    <div class="stat-label">Утро (06:00-14:00)</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">☀️</div>
                    <div class="stat-value">${report.time_distribution.afternoon || 0}</div>
                    <div class="stat-label">День (14:00-22:00)</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">🌙</div>
                    <div class="stat-value">${report.time_distribution.night || 0}</div>
                    <div class="stat-label">Ночь (22:00-06:00)</div>
                </div>
            </div>
        </div>

        ${report.project_distribution && report.project_distribution.length > 0 ? `
        <div class="report-section">
            <h3 class="report-section-title">
                <span class="report-section-icon">🔧</span>
                Распределение по проектам
            </h3>
            <table class="report-table">
                <thead>
                    <tr>
                        <th>Проект</th>
                        <th>Количество брака</th>
                    </tr>
                </thead>
                <tbody>
                    ${report.project_distribution.map(p => `
                        <tr>
                            <td>${p.project}</td>
                            <td><span class="badge badge-ng">${p.ng}</span></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
        ` : ''}
    `;
}

// =============================================
// ЭКСПОРТ В EXCEL
// =============================================
async function exportToExcel() {
    if (!currentReport || !currentReportType) {
        showNotification('Сначала сформируйте отчёт', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/reports/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                report_type: currentReportType,
                report_data: currentReport
            })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `report_${currentReportType}_${new Date().toISOString().slice(0, 10)}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            showNotification('Отчёт экспортирован в Excel', 'success');
        } else {
            const data = await response.json();
            showNotification('Ошибка экспорта: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Ошибка: ' + error.message, 'error');
    }
}

// =============================================
// УТИЛИТЫ
// =============================================
function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = 'notification ' + type;
    notification.classList.remove('hidden');

    setTimeout(() => {
        notification.classList.add('hidden');
    }, 5000);
}

function formatDate(isoString) {
    if (!isoString) return '—';
    const date = new Date(isoString);
    return date.toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

function getWeekNumber(d) {
    d = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    const weekNo = Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
    return weekNo;
}
