// tools.js - Логика страницы выбора инструментов

let allTools = [];
let categories = [];
let selectedTool = null;
let recentProjectIds = [];

function compareToolId(a, b) {
    const aParts = String(a).split('.').map(Number);
    const bParts = String(b).split('.').map(Number);
    const maxLen = Math.max(aParts.length, bParts.length);
    for (let i = 0; i < maxLen; i++) {
        const av = i < aParts.length ? aParts[i] : 0;
        const bv = i < bParts.length ? bParts[i] : 0;
        if (av !== bv) return av - bv;
    }
    return 0;
}

function getCategoryPrefix(categoryName) {
    const tool = allTools.find(t => t.category_ru === categoryName || t.category_en === categoryName);
    if (tool && tool.tool_id) {
        const firstDigit = parseInt(tool.tool_id.split('.')[0], 10);
        if (!isNaN(firstDigit)) return firstDigit;
    }
    const mapping = {
        'Измерение': 1, 'Подсчёт': 2, 'Распознавание': 3, 'Логика': 4,
        'Обнаружение наличия': 5, 'Позиционирование': 6, 'Глубокое обучение': 7, 'Поиск дефектов': 8
    };
    return mapping[categoryName] || 999;
}

document.addEventListener('DOMContentLoaded', async () => {
    await loadRecentProjects();
    await loadTools();
    setupModal();
});

async function loadRecentProjects() {
    try {
        const response = await fetch('/api/recent_tools?limit=10');
        const data = await response.json();
        if (data.success) recentProjectIds = data.recent_projects || [];
        else recentProjectIds = [];
    } catch (error) { recentProjectIds = []; console.error(error); }
}

async function loadTools() {
    const container = document.getElementById('toolsContainer');
    if (!container) return;
    container.innerHTML = '<div class="loading"><div class="spinner"></div><p>Загрузка инструментов...</p></div>';
    try {
        const response = await fetch('/api/tools');
        const data = await response.json();
        if (data.success) {
            allTools = data.tools || [];
            categories = data.categories || [];
            renderCategoryButtons(categories);
            filterTools('all');
        } else {
            container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><p>Ошибка загрузки: ${data.error}</p></div>`;
        }
    } catch (error) {
        container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">❌</div><p>Не удалось загрузить инструменты</p><p class="error-detail">${error.message}</p></div>`;
    }
}

function renderCategoryButtons(categories) {
    const container = document.getElementById('categoryFilterContainer');
    if (!container) return;
    container.innerHTML = '';
    const allBtn = document.createElement('button');
    allBtn.className = 'category-btn active';
    allBtn.textContent = '📋 Все';
    allBtn.dataset.category = 'all';
    allBtn.addEventListener('click', () => {
        document.querySelectorAll('.category-btn').forEach(btn => btn.classList.remove('active'));
        allBtn.classList.add('active');
        filterTools('all');
    });
    container.appendChild(allBtn);

    const categoriesWithPrefix = categories.map(cat => ({
        name: cat.name_ru || cat.name_en,
        prefix: getCategoryPrefix(cat.name_ru || cat.name_en)
    }));
    categoriesWithPrefix.sort((a, b) => a.prefix - b.prefix);

    categoriesWithPrefix.forEach(cat => {
        const btn = document.createElement('button');
        btn.className = 'category-btn';
        btn.textContent = `${cat.prefix}. ${cat.name}`;
        btn.dataset.category = cat.name;
        btn.addEventListener('click', () => {
            document.querySelectorAll('.category-btn').forEach(btn => btn.classList.remove('active'));
            btn.classList.add('active');
            filterTools(cat.name);
        });
        container.appendChild(btn);
    });
}

function filterTools(category) {
    let filtered;
    if (category === 'all') {
        if (!recentProjectIds.length) filtered = [];
        else {
            filtered = allTools.filter(tool => recentProjectIds.includes(tool.project_name));
            filtered.sort((a, b) => {
                const idxA = recentProjectIds.indexOf(a.project_name);
                const idxB = recentProjectIds.indexOf(b.project_name);
                if (idxA === -1) return 1;
                if (idxB === -1) return -1;
                return idxA - idxB;
            });
        }
    } else {
        filtered = allTools.filter(tool => (tool.category_ru && tool.category_ru === category) || (tool.category_en && tool.category_en === category));
        filtered.sort((a, b) => compareToolId(a.tool_id, b.tool_id));
    }
    renderTools(filtered);
}

function renderTools(tools) {
    const container = document.getElementById('toolsContainer');
    if (!container) return;
    if (!tools.length) {
        const activeBtn = document.querySelector('.category-btn.active');
        const isAllCategory = activeBtn && activeBtn.dataset.category === 'all';
        const message = isAllCategory ? 'Нет недавно использованных инструментов. Выберите инструмент из другой категории.' : 'Инструменты не найдены.';
        container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">📭</div><p>${message}</p></div>`;
        return;
    }
    container.innerHTML = tools.map(tool => `
        <div class="tool-card" data-id="${tool.tool_id}" data-project="${tool.project_name}">
            <div class="tool-card-content">
                <div class="tool-project"><span class="tool-project-label">Проект:</span> ${escapeHtml(tool.project_name || '—')}</div>
                <div class="tool-name-ru">${escapeHtml(tool.name_ru || tool.name_en || 'Без названия')}</div>
            </div>
        </div>
    `).join('');
    document.querySelectorAll('.tool-card').forEach(card => {
        card.addEventListener('click', () => selectTool(card));
    });
}

function selectTool(card) {
    document.querySelectorAll('.tool-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    const toolData = allTools.find(t => t.tool_id === card.dataset.id);
    selectedTool = {
        id: card.dataset.id,
        project: card.dataset.project,
        name: toolData ? (toolData.name_ru || toolData.name_en || card.dataset.id) : card.dataset.id,
    };
    showConfirmModal(selectedTool);
}

function setupModal() {
    const modal = document.getElementById('confirmModal');
    const closeBtn = document.getElementById('modalClose');
    const cancelBtn = document.getElementById('modalCancel');
    const confirmBtn = document.getElementById('modalConfirm');
    if (closeBtn) closeBtn.addEventListener('click', hideConfirmModal);
    if (cancelBtn) cancelBtn.addEventListener('click', hideConfirmModal);
    if (confirmBtn) confirmBtn.addEventListener('click', confirmSwitch);
    if (modal) modal.addEventListener('click', (e) => { if (e.target === modal) hideConfirmModal(); });
}

function showConfirmModal(tool) {
    const modal = document.getElementById('confirmModal');
    const preview = document.getElementById('toolPreview');
    const message = document.getElementById('modalMessage');
    if (!modal) return;
    if (message) message.textContent = 'Вы собираетесь переключить проект камеры на:';
    if (preview) {
        preview.innerHTML = `<div style="margin-bottom: 8px;"><span style="font-weight: 600;">Проект:</span> ${escapeHtml(tool.project)}</div>
            <div style="font-size: 1.1rem; font-weight: 500; color: var(--accent-primary);">${escapeHtml(tool.name)}</div>`;
    }
    modal.classList.add('active');
}

function hideConfirmModal() {
    const modal = document.getElementById('confirmModal');
    if (modal) modal.classList.remove('active');
}

async function confirmSwitch() {
    if (!selectedTool) return;
    if (!window.checkHardwareAndNotify('Переключение проекта')) {
        hideConfirmModal();
        return;
    }
    const confirmBtn = document.getElementById('modalConfirm');
    if (!confirmBtn) return;
    const originalText = confirmBtn.textContent;
    confirmBtn.textContent = 'Переключение...';
    confirmBtn.disabled = true;
    try {
        const response = await fetch('/api/switch_project', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_name: selectedTool.project })
        });
        const data = await response.json();
        if (data.success) {
            await loadRecentProjects();
            const activeBtn = document.querySelector('.category-btn.active');
            if (activeBtn && activeBtn.dataset.category === 'all') filterTools('all');
            window.showToast(`✅ Схема "${selectedTool.name}" активирована`, 'success');
            updateProjectInHeader(selectedTool.project, selectedTool.name);
        } else {
            window.showToast(`❌ Ошибка: ${data.error}`, 'error');
        }
    } catch (error) {
        window.showToast(`❌ Ошибка сети: ${error.message}`, 'error');
    } finally {
        confirmBtn.textContent = originalText;
        confirmBtn.disabled = false;
        hideConfirmModal();
    }
}

async function updateProjectInHeader(projectName, russianName) {
    try {
        await fetch('/api/set_project', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_name: projectName })
        });
        document.querySelectorAll('#projectName, .project-name').forEach(el => { if (el) el.innerText = russianName; });
    } catch (error) { console.error('Ошибка обновления проекта:', error); }
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, m => m === '&' ? '&amp;' : m === '<' ? '&lt;' : '&gt;');
}