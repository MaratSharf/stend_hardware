// theme.js - Управление темой оформления

/**
 * Инициализация темы при загрузке страницы
 */
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    createThemeToggle();
});

/**
 * Инициализация сохранённой темы
 */
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
}

/**
 * Создание кнопки переключения темы
 */
function createThemeToggle() {
    const toggle = document.createElement('button');
    toggle.className = 'theme-toggle';
    toggle.setAttribute('aria-label', 'Переключить тему');
    toggle.setAttribute('title', 'Переключить тему (тёмная/светлая)');
    toggle.innerHTML = getThemeIcon();
    
    toggle.addEventListener('click', () => toggleTheme());
    
    document.body.appendChild(toggle);
}

/**
 * Переключение темы
 */
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    // Обновляем иконку
    const toggle = document.querySelector('.theme-toggle');
    if (toggle) {
        toggle.innerHTML = getThemeIcon();
    }
    
    // Анимация переключения
    document.body.style.transition = 'background 0.3s ease, color 0.3s ease';
}

/**
 * Получение иконки для текущей темы
 */
function getThemeIcon() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    return currentTheme === 'light' ? '🌙' : '☀️';
}
