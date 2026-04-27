/**
 * history.js - Логика страницы истории проверок
 */

let currentPage = 1;
const pageSize = 20;
let currentFilters = {};
let totalPages = 1;

document.addEventListener('DOMContentLoaded', () => {
    setDefaultDates();
    loadStatistics();
    loadResults();
    setupFilters();
    setupPagination();
});

function setDefaultDates() {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('filterDateFrom').value = today;
    document.getElementById('filterDateTo').value = today;
}

async function loadStatistics() {
    try {
        const params = new URLSearchParams(currentFilters);
        const response = await fetch(`/api/statistics?${params}`);
        const data = await response.json();

        if (data.success) {
            const stats = data.statistics;
            document.getElementById('statTotal').textContent = stats.total;
            document.getElementById('statOk').textContent = stats.ok_count;
            document.getElementById('statNg').textContent = stats.ng_count;
            document.getElementById('statOkPercent').textContent = stats.ok_percent + '%';
        }
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
    }
}

async function loadResults() {
    const tbody = document.getElementById('resultsBody');
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
                tbody.innerHTML = results.map((r, idx) => {
                    const rowNumber = startIndex + idx;
                    return `
                        <tr>
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

function formatDateTime(isoString) {
    if (!isoString) return '—';
    const date = new Date(isoString);
    return date.toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', year: '2-digit',
        hour: '2-digit', minute: '2-digit'
    });
}

function renderImage(imagePath) {
    if (!imagePath) return '<div class="no-image">Нет</div>';
    return `<img src="/images/${imagePath}" alt="Снимок" class="thumb-image" onerror="this.parentElement.innerHTML='<div class=\\'no-image\\'>Ошибка</div>'">`;
}

function setupFilters() {
    document.getElementById('applyFilters').addEventListener('click', () => {
        const result = document.getElementById('filterResult').value;
        const dateFrom = document.getElementById('filterDateFrom').value;
        const dateTo = document.getElementById('filterDateTo').value;

        currentFilters = {};
        if (result) currentFilters.result = result;
        if (dateFrom) currentFilters.date_from = dateFrom;
        if (dateTo) currentFilters.date_to = dateTo;

        currentPage = 1;
        loadResults();
        loadStatistics();
    });

    document.getElementById('refreshBtn').addEventListener('click', () => {
        document.getElementById('filterResult').value = '';
        setDefaultDates();
        currentFilters = {};
        currentPage = 1;
        loadResults();
        loadStatistics();
    });
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