/**
 * connection_monitor.js - Мониторинг связи с оборудованием (ОВЕН и камера)
 * 
 * Обеспечивает:
 * - Периодическую проверку доступности оборудования через API /api/connection_status
 * - Отображение индикаторов связи (зелёный/красный кружок + текст) в шапке страницы
 * - Глобальный флаг window.isHardwareAvailable для блокировки действий при потере связи
 * - Всплывающие уведомления (toast) при потере/восстановлении связи
 * - Вызов функций обнуления (resetHardwareDisplay) и принудительного обновления (forceUpdateHardware)
 */

let connectionCheckInterval = null;     // идентификатор интервала проверки
let lastOwenStatus = true;              // предыдущий статус ОВЕН (для отслеживания изменений)
let lastCameraStatus = true;            // предыдущий статус камеры
let offlineModeActive = false;          // активен ли офлайн-режим

// Глобальный флаг доступности оборудования (используется на всех страницах)
window.isHardwareAvailable = false;

/**
 * Обновляет индикаторы связи (кружки и текст) в верхней панели страницы
 * @param {boolean} owenOk  - доступен ли ОВЕН
 * @param {boolean} cameraOk - доступна ли камера
 */
function updateConnectionIndicators(owenOk, cameraOk) {
    const owenLed = document.getElementById('owenLed');
    const owenText = document.getElementById('owenText');
    const cameraLed = document.getElementById('cameraLed');
    const cameraText = document.getElementById('cameraText');
    if (owenLed) {
        owenLed.className = 'indicator-led ' + (owenOk ? 'online' : 'offline');
        owenText.textContent = owenOk ? 'ОВЕН: связь есть' : 'ОВЕН: связи нет';
    }
    if (cameraLed) {
        cameraLed.className = 'indicator-led ' + (cameraOk ? 'online' : 'offline');
        cameraText.textContent = cameraOk ? 'Камера: связь есть' : 'Камера: связи нет';
    }
}

/**
 * Основная функция проверки состояния связи.
 * Вызывается периодически (каждые 5 секунд) и при загрузке страницы.
 */
async function checkConnectionStatus() {
    try {
        const response = await fetch('/api/connection_status');
        const data = await response.json();
        if (!data.success) return;

        const owenOk = data.owen_available === true;
        const cameraOk = data.camera_available === true;
        offlineModeActive = data.offline_mode === true;
        const hardwareOk = owenOk && cameraOk;

        const wasAvailable = window.isHardwareAvailable;
        window.isHardwareAvailable = hardwareOk && !offlineModeActive;

        // Обновляем индикаторы в шапке
        updateConnectionIndicators(owenOk, cameraOk);


        // Показываем уведомления при изменении статуса
        if (!owenOk && lastOwenStatus) {
            window.showToast('❌ Потеря связи с контроллером ОВЕН!', 'error');
        }
        if (!cameraOk && lastCameraStatus) {
            window.showToast('❌ Потеря связи с камерой Hikrobot!', 'error');
        }
        if (owenOk && !lastOwenStatus) {
            window.showToast('✅ Связь с ОВЕН восстановлена', 'success');
        }
        if (cameraOk && !lastCameraStatus) {
            window.showToast('✅ Связь с камерой восстановлена', 'success');
        }

        lastOwenStatus = owenOk;
        lastCameraStatus = cameraOk;


        // ★★★ При восстановлении связи – принудительно обновляем данные на странице ★★★
        if (hardwareOk && !wasAvailable) {
            if (typeof window.forceUpdateHardware === 'function') {
                window.forceUpdateHardware();
            }
            // Дополнительный вызов через небольшую задержку для гарантии
            setTimeout(() => {
                if (typeof window.forceUpdateHardware === 'function') {
                    window.forceUpdateHardware();
                }
                if (typeof window.updateInputs === 'function') {
                    window.updateInputs(true);
                }
            }, 200);
        }
    } catch (error) {
        console.error('Ошибка проверки связи:', error);
        // При ошибке сети считаем оборудование недоступным
        if (window.isHardwareAvailable !== false) {
            window.isHardwareAvailable = false;
            updateConnectionIndicators(false, false);
            if (typeof window.resetHardwareDisplay === 'function') {
                window.resetHardwareDisplay();
            }
        }
    }
}

// Запускаем мониторинг после полной загрузки DOM
document.addEventListener('DOMContentLoaded', () => {
    checkConnectionStatus();                     // первая проверка сразу
    connectionCheckInterval = setInterval(checkConnectionStatus, 5000); // затем каждые 5 секунд
});

// Очищаем интервал при выгрузке страницы (чтобы не было утечек)
window.addEventListener('beforeunload', () => {
    if (connectionCheckInterval) clearInterval(connectionCheckInterval);
});