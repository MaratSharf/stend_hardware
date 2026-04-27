/**
 * Модуль авторизации и управления сессией пользователя
 */

// Глобальное состояние текущего пользователя
window.currentUser = null;

/**
 * Инициализация модуля авторизации
 */
async function initAuth() {
    try {
        const response = await fetch('/auth/api/user');
        const data = await response.json();
        
        if (data.authenticated) {
            window.currentUser = data.user;
            updateUserInterface(data.user);
        } else {
            window.currentUser = null;
            // Если мы не на странице входа, перенаправляем на неё
            if (!window.location.pathname.startsWith('/auth/login')) {
                console.log('Пользователь не авторизован. Перенаправление на страницу входа...');
                window.location.href = '/auth/login';
                return;
            }
        }
    } catch (error) {
        console.error('Ошибка получения данных пользователя:', error);
    }
}

/**
 * Обновление интерфейса в зависимости от авторизации
 */
function updateUserInterface(user) {
    // Показываем блок пользователя в сайдбаре
    const sidebarUser = document.getElementById('sidebarUser');
    if (sidebarUser) {
        sidebarUser.style.display = 'flex';
        
        const userName = document.getElementById('userName');
        const userRole = document.getElementById('userRole');
        
        if (userName) {
            userName.textContent = user.full_name || user.username;
        }
        if (userRole) {
            const roleNames = {
                'operator': 'Оператор',
                'naladchik': 'Наладчик',
                'kontroler': 'Контролер',
                'admin': 'Администратор'
            };
            userRole.textContent = roleNames[user.role] || user.role;
        }
    }
    
    // Применяем права доступа к элементам интерфейса
    applyPermissions(user);
}

/**
 * Применение прав доступа к элементам интерфейса
 */
function applyPermissions(user) {
    const permissions = user.permissions || [];
    const isAdmin = permissions.includes('*');
    
    // Скрываем элементы, требующие определенных прав
    document.querySelectorAll('[data-permission]').forEach(el => {
        const requiredPermission = el.getAttribute('data-permission');
        if (!isAdmin && !permissions.includes(requiredPermission)) {
            el.style.display = 'none';
        }
    });
    
    // Скрываем элементы для определенных ролей
    document.querySelectorAll('[data-role]').forEach(el => {
        const allowedRoles = el.getAttribute('data-role').split(',');
        if (!allowedRoles.includes(user.role) && !isAdmin) {
            el.style.display = 'none';
        }
    });
}

/**
 * Проверка наличия права у текущего пользователя
 */
function hasPermission(permission) {
    if (!window.currentUser) return false;
    if (window.currentUser.permissions.includes('*')) return true;
    return window.currentUser.permissions.includes(permission);
}

/**
 * Проверка роли текущего пользователя
 */
function hasRole(role) {
    if (!window.currentUser) return false;
    return window.currentUser.role === role;
}

/**
 * Вход через API (AJAX)
 */
async function login(username, password) {
    try {
        const response = await fetch('/auth/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            window.currentUser = data.user;
            updateUserInterface(data.user);
            return { success: true, user: data.user };
        } else {
            return { success: false, error: data.error };
        }
    } catch (error) {
        console.error('Ошибка входа:', error);
        return { success: false, error: 'Ошибка подключения к серверу' };
    }
}

/**
 * Выход из системы через API
 */
async function logout() {
    try {
        await fetch('/auth/api/logout', { method: 'POST' });
        window.currentUser = null;
        
        // Скрываем блок пользователя
        const sidebarUser = document.getElementById('sidebarUser');
        if (sidebarUser) {
            sidebarUser.style.display = 'none';
        }
        
        // Перенаправляем на страницу входа
        window.location.href = '/auth/login';
    } catch (error) {
        console.error('Ошибка выхода:', error);
    }
}

/**
 * Получение названия роли на русском
 */
function getRoleName(role) {
    const roleNames = {
        'operator': 'Оператор',
        'naladchik': 'Наладчик',
        'kontroler': 'Контролер',
        'admin': 'Администратор'
    };
    return roleNames[role] || role;
}

// Автоматическая инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', initAuth);
