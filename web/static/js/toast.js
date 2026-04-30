// toast.js - Современная система уведомлений (Toast)

/**
 * Показать toast-уведомление
 * @param {string} message - Текст сообщения
 * @param {string} type - Тип: 'success', 'error', 'warning', 'info'
 * @param {string} title - Заголовок (опционально)
 * @param {number} duration - Длительность в мс (по умолчанию 4000)
 */
function showToast(message, type = 'info', title = '', duration = 4000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    // Создаём элемент toast
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    // Иконка в зависимости от типа
    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    };
    const icon = icons[type] || icons.info;

    // HTML структура toast
    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <div class="toast-content">
            ${title ? `<div class="toast-title">${title}</div>` : ''}
            <div class="toast-message">${escapeHtml(message)}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    container.appendChild(toast);

    // Автоматическое скрытие через указанное время
    setTimeout(() => hideToast(toast), duration);
}

/**
 * Скрыть toast с анимацией
 * @param {HTMLElement} toast - Элемент toast
 */
function hideToast(toast) {
    if (!toast) return;
    
    toast.classList.add('toast-hiding');
    toast.addEventListener('animationend', () => {
        toast.remove();
    }, { once: true });
}

/**
 * Экранирование HTML для безопасности
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Устаревшие функции для обратной совместимости
 */
function showNotification(message, type = 'info') {
    console.warn('showNotification устарела, используйте showToast');
    showToast(message, type);
}

// Экспорт функций для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { showToast, hideToast };
}
