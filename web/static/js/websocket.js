/**
 * websocket.js - WebSocket клиент для real-time обновлений в веб-интерфейсе стенда машинного зрения
 * 
 * Заменяет polling (периодические fetch-запросы) на WebSocket соединения с использованием Socket.IO
 * Обеспечивает:
 * - Автоматическое подключение к WebSocket серверу
 * - Получение обновлений статуса в реальном времени
 * - Обработку потери и восстановления соединения
 * - Fallback на polling при недоступности WebSocket
 */

// ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================
let socket = null;
let wsConnected = false;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;
const RECONNECT_DELAY_MS = 2000;

// Callback функции для обработки обновлений
let statusUpdateCallbacks = [];

// ==================== ИНИЦИАЛИЗАЦИЯ ====================

/**
 * Инициализирует WebSocket соединение
 * @returns {boolean} true если WebSocket поддерживается и инициировано подключение
 */
function initWebSocket() {
    if (!window.io) {
        console.warn('Socket.IO библиотека не загружена, используем fallback на polling');
        return false;
    }

    // Определяем URL для WebSocket (используем тот же хост что и для HTTP)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}`;
    
    console.log(`[WebSocket] Подключение к ${wsUrl}`);
    
    try {
        socket = io(wsUrl, {
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionDelay: RECONNECT_DELAY_MS,
            reconnectionDelayMax: 10000,
            reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
            timeout: 20000
        });

        // Обработчик подключения
        socket.on('connect', () => {
            console.log('[WebSocket] Подключено');
            wsConnected = true;
            reconnectAttempts = 0;
            updateConnectionIndicator('connected');
            
            // Подписываемся на обновления статуса
            socket.emit('subscribe_status');
            
            // Вызываем callback успешного подключения
            if (typeof onWebSocketConnect === 'function') {
                onWebSocketConnect();
            }
        });

        // Обработчик отключения
        socket.on('disconnect', (reason) => {
            console.log(`[WebSocket] Отключено: ${reason}`);
            wsConnected = false;
            updateConnectionIndicator('disconnected');
            
            if (typeof onWebSocketDisconnect === 'function') {
                onWebSocketDisconnect(reason);
            }
        });

        // Обработчик ошибок
        socket.on('connect_error', (error) => {
            console.error('[WebSocket] Ошибка подключения:', error);
            wsConnected = false;
            updateConnectionIndicator('error');
            
            reconnectAttempts++;
            if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
                console.warn('[WebSocket] Превышено максимальное количество попыток подключения, используем polling');
                if (typeof onWebSocketMaxRetriesExceeded === 'function') {
                    onWebSocketMaxRetriesExceeded();
                }
            }
        });

        // Обработчик обновлений статуса
        socket.on('status_update', (data) => {
            handleStatusUpdate(data);
        });

        return true;
    } catch (error) {
        console.error('[WebSocket] Ошибка инициализации:', error);
        return false;
    }
}

/**
 * Обработчик входящих обновлений статуса
 * @param {Object} data - данные обновления
 */
function handleStatusUpdate(data) {
    // Вызываем все зарегистрированные callback функции
    statusUpdateCallbacks.forEach(callback => {
        try {
            callback(data);
        } catch (error) {
            console.error('[WebSocket] Ошибка в callback обработки статуса:', error);
        }
    });
}

/**
 * Регистрирует callback функцию для обработки обновлений статуса
 * @param {Function} callback - функция, принимающая данные обновления
 */
function onStatusUpdate(callback) {
    if (typeof callback === 'function') {
        statusUpdateCallbacks.push(callback);
    }
}

/**
 * Удаляет зарегистрированный callback
 * @param {Function} callback - функция для удаления
 */
function removeStatusUpdateCallback(callback) {
    const index = statusUpdateCallbacks.indexOf(callback);
    if (index > -1) {
        statusUpdateCallbacks.splice(index, 1);
    }
}

/**
 * Проверяет, активно ли WebSocket соединение
 * @returns {boolean}
 */
function isWebSocketConnected() {
    return wsConnected && socket && socket.connected;
}

/**
 * Отправляет событие на сервер через WebSocket
 * @param {string} event - имя события
 * @param {any} data - данные для отправки
 * @returns {boolean} true если успешно отправлено
 */
function sendWebSocketEvent(event, data) {
    if (isWebSocketConnected()) {
        socket.emit(event, data);
        return true;
    }
    return false;
}

/**
 * Обновляет индикатор WebSocket соединения в UI
 * @param {string} state - 'connected', 'disconnected', 'error'
 */
function updateConnectionIndicator(state) {
    const indicator = document.getElementById('wsConnectionIndicator');
    if (!indicator) return;
    
    indicator.className = `ws-indicator ws-${state}`;
    
    switch(state) {
        case 'connected':
            indicator.title = 'WebSocket подключен';
            indicator.textContent = '🟢';
            break;
        case 'disconnected':
            indicator.title = 'WebSocket отключен';
            indicator.textContent = '🔴';
            break;
        case 'error':
            indicator.title = 'Ошибка WebSocket';
            indicator.textContent = '🟡';
            break;
        default:
            indicator.textContent = '⚪';
    }
}

// ==================== ОБРАБОТЧИКИ СОБЫТИЙ ====================

/**
 * Вызывается при успешном подключении к WebSocket
 * Переопределите эту функцию в вашем коде при необходимости
 */
function onWebSocketConnect() {
    console.log('[WebSocket] Событие: подключено');
    // По умолчанию скрываем индикаторы polling, если они есть
    const pollingIndicators = document.querySelectorAll('.polling-indicator');
    pollingIndicators.forEach(el => el.style.display = 'none');
}

/**
 * Вызывается при отключении от WebSocket
 * @param {string} reason - причина отключения
 */
function onWebSocketDisconnect(reason) {
    console.log(`[WebSocket] Событие: отключено (${reason})`);
}

/**
 * Вызывается при превышении максимального количества попыток переподключения
 */
function onWebSocketMaxRetriesExceeded() {
    console.warn('[WebSocket] Событие: превышено количество попыток подключения');
    // Можно показать пользователю уведомление о переходе на polling
    if (typeof window.showToast === 'function') {
        window.showToast('Режим реального времени недоступен, используется периодическое обновление', 'warning');
    }
}

// ==================== ЭКСПОРТ В ГЛОБАЛЬНУЮ ОБЛАСТЬ ====================
window.WebSocketClient = {
    init: initWebSocket,
    isConnected: isWebSocketConnected,
    send: sendWebSocketEvent,
    onStatusUpdate: onStatusUpdate,
    removeCallback: removeStatusUpdateCallback
};

// ==================== АВТОМАТИЧЕСКАЯ ИНИЦИАЛИЗАЦИЯ ====================
// Инициализируем WebSocket при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    // Небольшая задержка чтобы убедиться что страница полностью загружена
    setTimeout(() => {
        const wsSupported = initWebSocket();
        if (!wsSupported) {
            console.warn('[WebSocket] Не поддерживается, будет использоваться polling');
        }
    }, 100);
});
