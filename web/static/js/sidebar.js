/**
 * sidebar.js - Управление боковым меню (свёртывание/развёртывание)
 */

document.addEventListener('DOMContentLoaded', () => {
    const burgerBtn = document.getElementById('burgerBtn');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    if (!burgerBtn || !sidebar) return;

    function isMobile() {
        return window.innerWidth <= 768;
    }

    function openSidebar() {
        if (isMobile()) {
            sidebar.classList.add('open');
            if (overlay) overlay.classList.add('active');
        } else {
            sidebar.classList.remove('collapsed');
            localStorage.setItem('sidebarCollapsed', 'false');
        }
        burgerBtn.classList.add('active');
    }

    function closeSidebar() {
        if (isMobile()) {
            sidebar.classList.remove('open');
            if (overlay) overlay.classList.remove('active');
        } else {
            sidebar.classList.add('collapsed');
            localStorage.setItem('sidebarCollapsed', 'true');
        }
        burgerBtn.classList.remove('active');
    }

    function toggleSidebar() {
        if (isMobile()) {
            if (sidebar.classList.contains('open')) {
                closeSidebar();
            } else {
                openSidebar();
            }
        } else {
            if (sidebar.classList.contains('collapsed')) {
                openSidebar();
            } else {
                closeSidebar();
            }
        }
    }

    // Загрузка состояния на десктопе
    if (!isMobile()) {
        const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
        if (isCollapsed) {
            sidebar.classList.add('collapsed');
            burgerBtn.classList.add('active');
        }
    }

    burgerBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleSidebar();
    });

    // Закрытие по overlay
    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }

    // Закрытие мобильного меню при клике на ссылку
    document.querySelectorAll('.sidebar-nav a').forEach(link => {
        link.addEventListener('click', () => {
            if (isMobile() && sidebar.classList.contains('open')) {
                closeSidebar();
            }
        });
    });

    // Закрытие мобильного меню при клике вне его
    document.addEventListener('click', (e) => {
        if (isMobile() && sidebar.classList.contains('open')) {
            if (!sidebar.contains(e.target) && !burgerBtn.contains(e.target)) {
                closeSidebar();
            }
        }
    });
});
