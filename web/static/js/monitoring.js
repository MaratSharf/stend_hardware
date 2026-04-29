/**
 * monitoring.js - Клиентская логика страницы мониторинга стенда машинного зрения
 * 
 * Обеспечивает:
 * - Обновление в реальном времени результатов инспекции (статус, изображение, распознанные данные)
 * - Отображение статуса камеры, входов (DI) и выходов (DO)
 * - Переключение режимов АВТО/РУЧНОЙ и офлайн-режима
 * - Выбор сценария из веб-интерфейса и кнопку «Запуск»
 * - Корректную обработку потери/восстановления связи (обнуление и принудительное обновление)
 */

// ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================
// Кэш русских названий проектов (заполняется из БД)
let projectRussianNamesCache = {};

// ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

/**
 * Определяет тип инструмента по имени проекта камеры.
 * Используется для правильного отображения распознанных данных (код, текст, цвет).
 * @param {string} projectName - имя проекта камеры
 * @returns {string} 'code', 'color', 'text' или 'unknown'
 */
function getInstrumentType(projectName) {
    if (!projectName) return 'unknown';
    if (projectName.includes('CodeRecognition') || projectName.includes('3.2')) return 'code';
    if (projectName.includes('ColorRecognition') || projectName.includes('3.4')) return 'color';
    if (projectName.includes('OCR') || projectName.includes('3.7')) return 'text';
    return 'unknown';
}

/**
 * Преобразует название цвета в RGB-строку для отображения.
 * @param {string} colorName - название цвета на английском
 * @returns {string|null} строка вида "255,0,0" или null
 */
function getColorRgb(colorName) {
    const colorMap = {
        'red': '255,0,0', 'green':'0,128,0', 'blue':'0,0,255', 'yellow':'255,255,0',
        'cyan':'0,255,255', 'magenta':'255,0,255', 'white':'255,255,255', 'black':'0,0,0',
        'orange':'255,165,0', 'purple':'128,0,128', 'pink':'255,192,203', 'brown':'165,42,42',
        'gray':'128,128,128', 'grey':'128,128,128'
    };
    return colorMap[colorName?.toLowerCase()] || null;
}

/**
 * Получает русское название проекта с сервера (из таблицы tools)
 * @param {string} projectName - техническое имя проекта
 * @returns {Promise<string>} русское название
 */
async function getRussianProjectName(projectName) {
    if (!projectName) return '—';
    if (projectRussianNamesCache[projectName]) return projectRussianNamesCache[projectName];
    try {
        const response = await fetch(`/api/project_russian_name?project_name=${encodeURIComponent(projectName)}`);
        const data = await response.json();
        if (data.success && data.name_ru) {
            projectRussianNamesCache[projectName] = data.name_ru;
            return data.name_ru;
        }
    } catch (error) {
        console.error('Ошибка получения русского названия:', error);
    }
    return projectName; // fallback
}

// ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ POLLING ====================
let statusPollingInterval = null;
let hardwarePollingInterval = null;

// ==================== ИНИЦИАЛИЗАЦИЯ ====================
document.addEventListener('DOMContentLoaded', () => {
    initSidebar();               // активируем бургер-меню для мобильных
    initModeSwitch();           // настраиваем переключатель режима (АВТО/РУЧНОЙ)
    initOfflineModeSwitch();    // настраиваем переключатель офлайн-режима
    initScenarioSelection();    // настраиваем выбор сценария из веб-интерфейса
    updateProjectDisplay();     // загружаем и отображаем текущий проект камеры
    updateStatus();             // первое обновление результата
    updateHardwareStatus();     // первое обновление статусов оборудования
    
    // Регистрируем обработчик WebSocket обновлений
    if (window.WebSocketClient) {
        window.WebSocketClient.onStatusUpdate(handleWebSocketStatusUpdate);
        console.log('[Monitoring] WebSocket обновления подключены');
    }
    
    // Запускаем polling только как fallback
    // Если WebSocket активен, polling будет отключён автоматически
    startPollingFallback();
});

/**
 * Запускает polling интервалы только если WebSocket не подключён
 * Автоматически отключает polling при успешном WebSocket соединении
 */
function startPollingFallback() {
    // Проверяем состояние WebSocket через небольшую задержку
    setTimeout(() => {
        if (window.WebSocketClient && window.WebSocketClient.isConnected()) {
            console.log('[Monitoring] WebSocket активен, polling отключён');
            stopPolling();
        } else {
            console.log('[Monitoring] WebSocket недоступен, запускаем polling');
            statusPollingInterval = setInterval(updateStatus, 2000);
            hardwarePollingInterval = setInterval(updateHardwareStatus, 1000);
        }
    }, 500);
}

/**
 * Останавливает все polling интервалы
 */
function stopPolling() {
    if (statusPollingInterval) {
        clearInterval(statusPollingInterval);
        statusPollingInterval = null;
    }
    if (hardwarePollingInterval) {
        clearInterval(hardwarePollingInterval);
        hardwarePollingInterval = null;
    }
}

// Экспортируем функцию для использования в websocket.js
window.stopPolling = stopPolling;

/**
 * Обработчик WebSocket обновлений статуса
 * @param {Object} data - данные обновления от сервера
 */
function handleWebSocketStatusUpdate(data) {
    // Обновляем результат инспекции
    if (data.result) {
        applyStatusData(data.result);
    }
    
    // Обновляем статус оборудования (входы/выходы/камера)
    if (data.inputs || data.outputs || data.camera_status) {
        applyHardwareData({
            inputs: data.inputs,
            outputs: data.outputs,
            camera_status: data.camera_status
        });
    }
    
    // Обновляем индикаторы доступности оборудования
    if (data.hardware_available !== undefined) {
        window.isHardwareAvailable = data.hardware_available;
        if (!data.hardware_available) {
            window.resetHardwareDisplay();
        }
    }
}

/**
 * Инициализирует боковое меню: обработчик клика по бургеру (для мобильных устройств).
 */
function initSidebar() {
    const burger = document.getElementById('burgerBtn');
    const sidebar = document.getElementById('sidebar');
    if (burger && sidebar) {
        burger.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            burger.classList.toggle('t-menuburger-opened');
        });
    }
}

// ==================== РЕЖИМ РАБОТЫ (АВТО / РУЧНОЙ) ====================

/**
 * Инициализирует переключатель режима: загружает текущее состояние с сервера,
 * обрабатывает изменение переключателя, блокирует действие при отсутствии связи.
 */
async function initModeSwitch() {
    const toggle = document.getElementById('autoModeToggle');
    const modeText = document.getElementById('modeText');
    try {
        const response = await fetch('/api/mode');
        const data = await response.json();
        if (data.success) {
            toggle.checked = data.auto_mode;
            updateModeText(modeText, data.auto_mode);
        }
    } catch (error) {
        console.error('Ошибка загрузки режима:', error);
    }

    toggle.addEventListener('change', async (e) => {
        const autoMode = e.target.checked;
        // Проверяем доступность оборудования
        if (!window.checkHardwareAndNotify('Переключение режима')) {
            toggle.checked = !autoMode;
            return;
        }
        try {
            const response = await fetch('/api/mode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ auto_mode: autoMode })
            });
            const data = await response.json();
            if (data.success) {
                updateModeText(modeText, autoMode);
            }
        } catch (error) {
            console.error('Ошибка переключения режима:', error);
            toggle.checked = !autoMode;
            window.showToast('Ошибка при переключении режима', 'error');
        }
    });
}

/**
 * Обновляет текстовое отображение режима (АВТО/РУЧН).
 * @param {HTMLElement} element - элемент для текста
 * @param {boolean} autoMode - true = АВТО, false = РУЧНОЙ
 */
function updateModeText(element, autoMode) {
    if (autoMode) {
        element.innerText = 'АВТО';
        element.setAttribute('data-mode', 'auto');
    } else {
        element.innerText = 'РУЧН';
        element.setAttribute('data-mode', 'manual');
    }
}

// ==================== ОФЛАЙН-РЕЖИМ ====================

/**
 * Инициализирует переключатель офлайн-режима.
 */
async function initOfflineModeSwitch() {
    const toggle = document.getElementById('offlineModeToggle');
    const modeText = document.getElementById('offlineModeText');
    if (!toggle || !modeText) return;

    async function loadOfflineMode() {
        try {
            const response = await fetch('/api/connection_status');
            const data = await response.json();
            if (data.success) {
                toggle.checked = data.offline_mode === true;
                updateOfflineModeText(modeText, toggle.checked);
            }
        } catch (error) {
            console.error('Ошибка загрузки офлайн-режима:', error);
        }
    }
    await loadOfflineMode();

    toggle.addEventListener('change', async (e) => {
        const enabled = e.target.checked;
        updateOfflineModeText(modeText, enabled);
        try {
            const response = await fetch('/api/offline_mode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ offline_mode: enabled })
            });
            const data = await response.json();
            if (data.success) {
                window.showToast(enabled ? 'Офлайн-режим включён' : 'Офлайн-режим выключен', 'info');
                if (typeof checkConnectionStatus === 'function') {
                    setTimeout(checkConnectionStatus, 500);
                }
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Ошибка переключения офлайн-режима:', error);
            window.showToast('Ошибка подключения к серверу', 'error');
            toggle.checked = !enabled;
            updateOfflineModeText(modeText, !enabled);
        }
    });
}

function updateOfflineModeText(element, enabled) {
    element.innerText = enabled ? 'Вкл' : 'Выкл';
    element.setAttribute('data-offline', enabled ? 'true' : 'false');
}

// ==================== ВЫБОР СЦЕНАРИЯ ИЗ ВЕБ + КНОПКА ЗАПУСК ====================

/**
 * Инициализирует выбор сценария: загружает настройки с сервера,
 * обрабатывает изменения чекбокса, селекта и кнопки «Запуск».
 * Блокирует изменения при отсутствии связи.
 */
async function initScenarioSelection() {
    const checkbox = document.getElementById('webScenarioToggle');
    const select = document.getElementById('scenarioSelect');
    const runBtn = document.getElementById('runScenarioBtn');
    if (!checkbox || !select) return;

    async function loadSettings() {
        try {
            const response = await fetch('/api/scenario_settings');
            const data = await response.json();
            if (data.success) {
                checkbox.checked = data.web_selection_enabled;
                select.disabled = !data.web_selection_enabled;
                select.value = data.selected_scenario;
            } else {
                window.showToast('Не удалось загрузить настройки сценария', 'error');
            }
        } catch (error) {
            window.showToast('Ошибка подключения к серверу', 'error');
        }
    }
    await loadSettings();

    // Обработчик чекбокса
    checkbox.addEventListener('change', async () => {
        if (!window.checkHardwareAndNotify('Изменение настроек сценария')) {
            checkbox.checked = !checkbox.checked;
            select.disabled = !checkbox.checked;
            return;
        }
        const enabled = checkbox.checked;
        select.disabled = !enabled;
        try {
            const response = await fetch('/api/scenario_settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ web_selection_enabled: enabled })
            });
            const data = await response.json();
            if (!data.success) throw new Error(data.error);
            window.showToast(enabled ? 'Выбор сценария из веб включён' : 'Выбор сценария из веб выключен', 'success');
            await loadSettings();
        } catch (error) {
            window.showToast('Ошибка: ' + error.message, 'error');
            checkbox.checked = !enabled;
            select.disabled = enabled;
        }
    });

    // Обработчик изменения выбранного сценария (только запоминаем, не запускаем)
    select.addEventListener('change', async () => {
        if (!checkbox.checked) return;
        if (!window.checkHardwareAndNotify('Выбор сценария')) {
            await loadSettings();
            return;
        }
        const scenario = select.value;
        try {
            const response = await fetch('/api/scenario_settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ selected_scenario: scenario })
            });
            const data = await response.json();
            if (data.success) {
                window.showToast(`Выбран сценарий ${scenario}. Нажмите «Запуск» для активации.`, 'info');
                await loadSettings();
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            window.showToast(`Ошибка: ${error.message}`, 'error');
            await loadSettings();
        }
    });

    // Кнопка «Запуск» – активирует выбранный сценарий
    if (runBtn) {
        runBtn.addEventListener('click', async () => {
            if (!checkbox.checked) {
                window.showToast('Сначала включите "Выбор сценария из веб"', 'warning');
                return;
            }
            if (!window.checkHardwareAndNotify('Запуск сценария')) return;
            if (runBtn.disabled) return;
            runBtn.disabled = true;
            try {
                const response = await fetch('/api/activate_scenario', { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    window.showToast(`Сценарий ${select.value} запущен`, 'success');
                } else {
                    window.showToast(`Ошибка: ${data.error}`, 'error');
                }
            } catch (error) {
                window.showToast(`Ошибка сети: ${error.message}`, 'error');
            } finally {
                runBtn.disabled = false;
            }
        });
    }
}

// ==================== ОТОБРАЖЕНИЕ ПРОЕКТА КАМЕРЫ ====================

/**
 * Загружает с сервера текущий проект камеры и обновляет отображение.
 * Использует русские названия через getRussianProjectName.
 */
async function updateProjectDisplay() {
    try {
        const response = await fetch('/api/current_project');
        const data = await response.json();
        if (data.success) {
            const projectName = data.project_name || '—';
            const russianName = await getRussianProjectName(projectName);
            const projectElement = document.getElementById('projectName');
            if (projectElement) projectElement.innerText = russianName;
        }
    } catch (error) {
        console.error('Ошибка получения проекта:', error);
    }
}

// ==================== ОБНОВЛЕНИЕ СТАТУСА ОБОРУДОВАНИЯ (ВХОДЫ/ВЫХОДЫ/КАМЕРА) ====================

/**
 * Применяет данные статуса оборудования к UI (используется WebSocket и polling)
 * @param {Object} data - данные от сервера (inputs, outputs, camera_status)
 */
function applyHardwareData(data) {
    if (!data) return;
    
    // Статус камеры
    if (data.camera_status) {
        const cam = data.camera_status;
        setElementValue('cam_trigger_ready', cam.trigger_ready);
        setElementValue('cam_results_available', cam.results_available);
        setElementValue('cam_command_success', cam.command_success);
        setElementValue('cam_general_fault', cam.general_fault);
    }

    // Входы (DI0-DI5)
    if (data.inputs) {
        for (let i = 0; i < 6; i++) {
            const el = document.getElementById(`di${i}`);
            if (el) {
                const val = data.inputs[i] !== undefined ? (data.inputs[i] ? '1' : '0') : '—';
                el.innerText = val;
                el.setAttribute('data-value', val === '1' ? '1' : '0');
            }
        }
    }

    // Выходы (DO0, DO2, DO3)
    const outputIndices = [0, 2, 3];
    if (data.outputs) {
        outputIndices.forEach(idx => {
            const el = document.getElementById(`do${idx}`);
            if (el) {
                const val = data.outputs[idx] !== undefined ? (data.outputs[idx] ? '1' : '0') : '—';
                el.innerText = val;
                el.setAttribute('data-value', val === '1' ? '1' : '0');
            }
        });
    }
}

/**
 * Обновляет состояние входов, выходов и статус камеры на странице.
 * Вызывается периодически (раз в секунду) как fallback для WebSocket.
 * @param {boolean} force - если true, обновляет даже при отсутствии связи (для восстановления)
 */
async function updateHardwareStatus(force = false) {
    if (!force && !window.isHardwareAvailable) {
        window.resetHardwareDisplay();
        return;
    }
    try {
        const response = await fetch('/api/hardware_status');
        const data = await response.json();
        if (data.error || !data.camera_status || !data.inputs) {
            if (!force) window.resetHardwareDisplay();
            return;
        }
        applyHardwareData(data);
    } catch (error) {
        console.error('Ошибка обновления статуса оборудования:', error);
        if (!force) window.resetHardwareDisplay();
    }
}

/**
 * Устанавливает текстовое значение элемента и его атрибут data-value.
 * @param {string} elementId - ID элемента
 * @param {boolean} value - значение (true/false)
 */
function setElementValue(elementId, value) {
    const el = document.getElementById(elementId);
    if (el) {
        el.innerText = value ? 'Да' : 'Нет';
        el.setAttribute('data-value', value ? 'true' : 'false');
    }
}

/**
 * Принудительное обновление статуса оборудования (вызывается из connection_monitor.js при восстановлении связи).
 */
window.forceUpdateHardware = async function() {
    console.log('forceUpdateHardware (monitoring)');
    await updateHardwareStatus(true);
};

/**
 * Обнуляет отображение датчиков и выходов при потере связи (устанавливает прочерки).
 */
window.resetHardwareDisplay = function() {
    setElementValue('cam_trigger_ready', false);
    setElementValue('cam_results_available', false);
    setElementValue('cam_command_success', false);
    setElementValue('cam_general_fault', false);
    for (let i = 0; i < 6; i++) {
        const el = document.getElementById(`di${i}`);
        if (el) {
            el.innerText = '—';
            el.setAttribute('data-value', '0');
        }
    }
    [0, 2, 3].forEach(idx => {
        const el = document.getElementById(`do${idx}`);
        if (el) {
            el.innerText = '—';
            el.setAttribute('data-value', '0');
        }
    });
};

// ==================== ОБНОВЛЕНИЕ РЕЗУЛЬТАТА ИНСПЕКЦИИ ====================

/**
 * Применяет данные результата инспекции к UI (используется WebSocket и polling)
 * @param {Object} data - данные результата от сервера
 */
function applyStatusData(data) {
    const resultCard = document.getElementById('resultCard');
    const resultIcon = document.getElementById('resultIcon');
    const resultTitle = document.getElementById('resultTitle');
    const resultTimestamp = document.getElementById('resultTimestamp');
    const inspectionImage = document.getElementById('inspectionImage');
    const noImage = document.getElementById('noImage');

    if (!data.result) {
        resultCard.setAttribute('data-result', 'waiting');
        resultIcon.innerText = '⏳';
        resultTitle.innerText = 'Ожидание';
        resultTimestamp.innerText = '—';
        inspectionImage.style.display = 'none';
        noImage.style.display = 'flex';
        hideRawData();
        return;
    }

    const isOk = data.result === 'OK';
    const isNg = data.result === 'NG';
    resultCard.setAttribute('data-result', isOk ? 'ok' : 'ng');
    if (isOk) {
        resultIcon.innerText = '✅';
        resultTitle.innerText = 'Годен';
    } else if (isNg) {
        resultIcon.innerText = '❌';
        resultTitle.innerText = 'Брак';
    } else {
        resultIcon.innerText = '⚠️';
        resultTitle.innerText = 'Ошибка';
    }

    if (data.time) {
        const d = new Date(data.time);
        resultTimestamp.innerText = d.toLocaleString('ru-RU');
    }
    if (data.image) {
        inspectionImage.src = '/images/' + data.image + '?t=' + Date.now();
        inspectionImage.style.display = 'block';
        noImage.style.display = 'none';
    } else {
        inspectionImage.style.display = 'none';
        noImage.style.display = 'flex';
    }
    inspectionImage.onerror = function() {
        noImage.style.display = 'flex';
        inspectionImage.style.display = 'none';
    };

    if (data.raw) {
        showRawData(data.raw);
    } else {
        hideRawData();
    }
}

/**
 * Загружает последний результат инспекции с сервера и обновляет интерфейс.
 * Вызывается периодически (раз в 2 секунды) как fallback для WebSocket.
 */
async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        applyStatusData(data);
    } catch (error) {
        console.error('Ошибка обновления статуса:', error);
    }
}

// ==================== ОТОБРАЖЕНИЕ РАСПОЗНАННЫХ ДАННЫХ (КОД, ТЕКСТ, ЦВЕТ) ====================

async function showRawData(raw) {
    let projectName = '';
    try {
        const response = await fetch('/api/current_project');
        const data = await response.json();
        if (data.success) projectName = data.project_name || '';
    } catch (error) {
        console.error('Ошибка получения проекта:', error);
    }

    const instrumentType = getInstrumentType(projectName);
    let recognitionSection = document.getElementById('recognitionResultSection');
    if (!recognitionSection) {
        const resultCard = document.getElementById('resultCard');
        recognitionSection = document.createElement('div');
        recognitionSection.id = 'recognitionResultSection';
        recognitionSection.className = 't-card__recognition';
        if (instrumentType === 'code') {
            recognitionSection.innerHTML = `
                <div class="t-recognition-header"><span>📊</span><span>Считанный код</span></div>
                <div class="t-code-display"><span class="t-code-value" id="codeValue">—</span></div>
            `;
        } else if (instrumentType === 'text') {
            recognitionSection.innerHTML = `
                <div class="t-recognition-header"><span>📝</span><span>Распознанный текст</span></div>
                <div class="t-text-display"><span class="t-text-value" id="textValue">—</span></div>
            `;
        } else if (instrumentType === 'color') {
            recognitionSection.innerHTML = `
                <div class="t-recognition-header"><span>🎨</span><span>Распознанный цвет</span></div>
                <div class="t-color-display">
                    <div class="t-color-sample" id="colorSample"></div>
                    <div class="t-color-info">
                        <span class="t-color-name" id="colorName">—</span>
                        <span class="t-color-rgb" id="colorRgb">—</span>
                    </div>
                </div>
            `;
        } else {
            recognitionSection.innerHTML = `
                <div class="t-recognition-header"><span>📋</span><span>Данные распознавания</span></div>
                <div class="t-raw-display"><span class="t-raw-value" id="rawValue">—</span></div>
            `;
        }
        resultCard.appendChild(recognitionSection);
        recognitionSection = document.getElementById('recognitionResultSection');
    }
    if (instrumentType === 'code') {
        const parts = raw.split(';');
        const code = parts.length > 1 ? parts[1] : raw;
        const codeEl = document.getElementById('codeValue');
        if (codeEl) codeEl.innerText = code || '—';
    } else if (instrumentType === 'text') {
        const textEl = document.getElementById('textValue');
        if (textEl) textEl.innerText = raw || '—';
    } else if (instrumentType === 'color') {
        const parts = raw.split(';');
        const colorName = parts.length > 1 ? parts[1] : raw;
        const colorSampleEl = document.getElementById('colorSample');
        const colorNameEl = document.getElementById('colorName');
        const colorRgbEl = document.getElementById('colorRgb');
        if (colorSampleEl && colorNameEl) {
            colorSampleEl.style.backgroundColor = colorName || '#808080';
            colorNameEl.innerText = colorName ? colorName.charAt(0).toUpperCase() + colorName.slice(1) : '—';
            if (colorRgbEl) colorRgbEl.innerText = getColorRgb(colorName) || '—';
        }
    } else {
        const rawEl = document.getElementById('rawValue');
        if (rawEl) rawEl.innerText = raw || '—';
    }
    recognitionSection.style.display = 'block';
}

function hideRawData() {
    const recognitionSection = document.getElementById('recognitionResultSection');
    if (recognitionSection) recognitionSection.style.display = 'none';
}