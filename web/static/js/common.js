/**
 * common.js - Общие утилиты и функции для всех страниц стенда.
 * Включает клиентское логирование ошибок на сервер, экранирование HTML,
 * показ уведомлений и проверку доступности оборудования.
 */

(function() {
    'use strict';

    // ==================== ЭКРАНИРОВАНИЕ HTML (XSS ЗАЩИТА) ====================
    const entityMap = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
        '/': '&#x2F;',
        '`': '&#x60;',
        '=': '&#x3D;'
    };

    window.escapeHtml = function(string) {
        return String(string).replace(/[&<>"'`=\/]/g, function(s) {
            return entityMap[s];
        });
    };

    // ==================== УВЕДОМЛЕНИЯ (TOAST) ====================
    let toastContainer = null;
    let animationStyleAdded = false;

    function getToastContainer() {
        if (!toastContainer) {
            toastContainer = document.getElementById('toastContainer');
            if (!toastContainer) {
                toastContainer = document.createElement('div');
                toastContainer.id = 'toastContainer';
                toastContainer.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 10000;
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                    width: 350px;
                    max-width: calc(100% - 40px);
                    pointer-events: none;
                `;
                document.body.appendChild(toastContainer);
            }
        }
        return toastContainer;
    }

    function addAnimationStyle() {
        if (animationStyleAdded) return;
        const style = document.createElement('style');
        style.id = 'toast-animation-style';
        style.textContent = `
            @keyframes fadeInOut {
                0% { opacity: 0; transform: translateX(20px); }
                10% { opacity: 1; transform: translateX(0); }
                90% { opacity: 1; transform: translateX(0); }
                100% { opacity: 0; transform: translateX(20px); }
            }
        `;
        document.head.appendChild(style);
        animationStyleAdded = true;
    }

    window.showToast = function(message, type = 'info', duration = 3000) {
        const container = getToastContainer();
        addAnimationStyle();

        const toast = document.createElement('div');
        toast.className = `custom-toast toast-${type}`;
        toast.style.cssText = `
            background: ${type === 'success' ? '#00a86b' : type === 'error' ? '#d62828' : type === 'warning' ? '#f4a100' : '#0351c1'};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            animation: fadeInOut ${duration}ms ease forwards;
            pointer-events: auto;
            width: 100%;
            box-sizing: border-box;
        `;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            if (toast.parentNode) toast.remove();
        }, duration);
    };

    // ==================== ОТПРАВКА ОШИБОК НА СЕРВЕР ====================
    function sendErrorToServer(message, stack, url) {
        fetch('/api/client_error', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, stack, url })
        }).catch(() => {});
    }

    window.addEventListener('error', function(e) {
        const message = e.message || 'Unknown error';
        const stack = e.error ? e.error.stack : '';
        const url = e.filename || location.href;
        sendErrorToServer(message, stack, url);
        console.error('Client error:', message, stack);
    });

    window.addEventListener('unhandledrejection', function(e) {
        const message = e.reason?.message || 'Unhandled Promise rejection';
        const stack = e.reason?.stack || '';
        sendErrorToServer(message, stack, location.href);
        console.error('Unhandled rejection:', message, stack);
    });

})();

// ==================== ГЛОБАЛЬНЫЕ ФУНКЦИИ ====================

/**
 * Проверка доступности оборудования перед выполнением действия.
 * @param {string} actionName - название действия для сообщения
 * @returns {boolean} - true если оборудование доступно, иначе false
 */
window.checkHardwareAndNotify = function(actionName) {
    if (!window.isHardwareAvailable) {
        window.showToast(`⚠️ Связи с оборудованием нет. ${actionName} невозможно.`, 'error');
        return false;
    }
    return true;
};

/**
 * Обновление имени проекта в шапке (получение русского названия через БД).
 * @param {string} projectName - техническое имя проекта
 */
window.updateProjectInHeader = async function(projectName) {
    if (!projectName) return;
    try {
        await fetch('/api/set_project', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_name: projectName })
        });
        // Запрашиваем русское название через API (теперь данные из БД)
        const response = await fetch(`/api/project_russian_name?project_name=${encodeURIComponent(projectName)}`);
        const data = await response.json();
        const russianName = data.success && data.name_ru ? data.name_ru : projectName;
        document.querySelectorAll('#projectName, .project-name').forEach(el => {
            if (el) el.textContent = russianName;
        });
    } catch (error) {
        console.error('Ошибка обновления проекта:', error);
    }
};