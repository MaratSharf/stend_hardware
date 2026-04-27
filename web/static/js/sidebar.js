/**
 * sidebar.js - Управление боковым меню (свёртывание/развёртывание)
 */

document.addEventListener('DOMContentLoaded', () => {
    const burgerBtn = document.getElementById('burgerBtn');
    const sidebar = document.getElementById('sidebar');
    
    if (!burgerBtn || !sidebar) return;
    
    // Загрузка состояния из localStorage
    const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (isCollapsed) {
        sidebar.classList.add('collapsed');
        burgerBtn.classList.add('active');
    }
    
    // Обработчик клика
    burgerBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
        burgerBtn.classList.toggle('active');
        
        // Сохранение состояния
        const collapsed = sidebar.classList.contains('collapsed');
        localStorage.setItem('sidebarCollapsed', collapsed);
    });
});
