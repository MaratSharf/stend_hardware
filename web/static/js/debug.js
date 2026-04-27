/**
 * debug.js - Логика страницы отладки и ручного управления
 * 
 * Обеспечивает:
 * - Отправку триггера камере (одиночное измерение)
 * - Ручное управление выходами (DO0-DO3) через toggle-переключатели
 * - Отображение состояния входов в реальном времени
 * - Лог операций
 * - Корректную обработку потери/восстановления связи (обнуление индикаторов и принудительное обновление)
 */

document.addEventListener('DOMContentLoaded', () => {
    initDebugPage();
});

/**
 * Инициализация страницы отладки: кнопки, переключатели, лог, периодическое обновление входов.
 */
function initDebugPage() {
    // Кнопка триггера камеры
    const triggerBtn = document.getElementById('triggerBtn');
    if (triggerBtn) triggerBtn.addEventListener('click', () => triggerCamera());

    // Переключатели выходов
    document.querySelectorAll('.output-toggle input[type="checkbox"]').forEach(toggle => {
        toggle.addEventListener('change', (e) => {
            const output = e.target.dataset.output;
            const state = e.target.checked;
            setOutput(output, state);
        });
    });

    // Кнопка очистки лога
    const clearLogBtn = document.getElementById('clearLogBtn');
    if (clearLogBtn) {
        clearLogBtn.addEventListener('click', () => {
            const log = document.getElementById('operationLog');
            log.innerHTML = '<div class="log-entry log-info">Лог очищен</div>';
        });
    }

    updateInputs();                     // первое обновление
    setInterval(updateInputs, 500);     // затем каждые 0.5 секунды
    addLog('Страница отладки загружена', 'info');
}

/**
 * Принудительное обновление (вызывается из connection_monitor.js при восстановлении связи).
 */
window.forceUpdateHardware = function() {
    console.log('forceUpdateHardware (debug)');
    updateInputs(true);
};

/**
 * Обнуляет отображение входов и выходов при потере связи (устанавливает прочерки).
 */
window.resetHardwareDisplay = function() {
    for (let i = 0; i < 6; i++) {
        const el = document.getElementById(`di${i}`);
        if (el) {
            el.innerText = '—';
            el.setAttribute('data-value', '0');
        }
    }
    for (let i = 0; i < 4; i++) {
        const toggle = document.getElementById(`do${i}`);
        const statusEl = document.getElementById(`do${i}-status`);
        if (toggle) toggle.checked = false;
        if (statusEl) {
            statusEl.innerText = '—';
            statusEl.setAttribute('data-value', '0');
        }
    }
};

/**
 * Обновляет состояние входов и выходов (получает с сервера).
 * @param {boolean} force - если true, обновляет даже при отсутствии связи (для восстановления)
 */
async function updateInputs(force = false) {
    if (!force && !window.isHardwareAvailable) {
        window.resetHardwareDisplay();
        return;
    }
    try {
        const response = await fetch('/api/debug/inputs');
        const data = await response.json();
        if (!data.success || !data.inputs) {
            if (!force) window.resetHardwareDisplay();
            return;
        }
        // Обновляем входы (DI0-DI5)
        if (data.inputs) {
            for (let i = 0; i < Math.min(6, data.inputs.length); i++) {
                const el = document.getElementById(`di${i}`);
                if (el) {
                    const value = data.inputs[i];
                    el.innerText = value;
                    el.setAttribute('data-value', value);
                }
            }
        }
        // Обновляем выходы (DO0-DO3) и состояние переключателей
        if (data.outputs) {
            for (let i = 0; i < data.outputs.length; i++) {
                const toggle = document.getElementById(`do${i}`);
                const statusEl = document.getElementById(`do${i}-status`);
                if (toggle) toggle.checked = data.outputs[i] === 1;
                if (statusEl) {
                    statusEl.innerText = data.outputs[i];
                    statusEl.setAttribute('data-value', data.outputs[i]);
                }
            }
        }
    } catch (error) {
        console.error('Ошибка обновления входов:', error);
        if (!force) window.resetHardwareDisplay();
    }
}

/**
 * Отправка триггера камере.
 */
async function triggerCamera() {
    if (!window.checkHardwareAndNotify('Отправка триггера')) return;

    const btn = document.getElementById('triggerBtn');
    const resultDisplay = document.getElementById('cameraResult');
    btn.disabled = true;
    btn.innerHTML = '<span class="btn-icon">⏳</span> Выполняется...';
    addLog('Отправка триггера камере...', 'info');
    try {
        const response = await fetch('/api/debug/trigger', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            resultDisplay.innerHTML = `
                <div class="result-success">✅ ${data.message}</div>
                <div class="result-raw">Raw: ${data.raw || '—'}</div>
            `;
            addLog(`Результат: ${data.result} (Raw: ${data.raw})`, 'success');
        } else {
            resultDisplay.innerHTML = `<div class="result-error">❌ ${data.error}</div>`;
            addLog(`Ошибка: ${data.error}`, 'error');
        }
    } catch (error) {
        resultDisplay.innerHTML = `<div class="result-error">❌ Ошибка сети: ${error.message}</div>`;
        addLog(`Ошибка сети: ${error.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="btn-icon">📸</span> Отправить триггер';
    }
}

/**
 * Установка состояния выхода (DO0-DO3) через API.
 * @param {string} output - 'DO0', 'DO1', 'DO2', 'DO3'
 * @param {boolean} state - true = ВКЛ, false = ВЫКЛ
 */
async function setOutput(output, state) {
    if (!window.checkHardwareAndNotify('Управление выходами')) return;

    const outputName = { 'DO0': 'Конвейер', 'DO1': 'Толкатель', 'DO2': 'Лампа NG', 'DO3': 'Лампа OK' };
    addLog(`Установка ${outputName[output]}: ${state ? 'ВКЛ' : 'ВЫКЛ'}`, 'info');
    try {
        const response = await fetch('/api/debug/output', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ output, state })
        });
        const data = await response.json();
        if (data.success) {
            addLog(data.message, 'success');
            const statusEl = document.getElementById(`${output.toLowerCase()}-status`);
            if (statusEl) {
                statusEl.innerText = state ? '1' : '0';
                statusEl.setAttribute('data-value', state ? '1' : '0');
            }
        } else {
            addLog(`Ошибка: ${data.error}`, 'error');
            const toggle = document.querySelector(`input[data-output="${output}"]`);
            if (toggle) toggle.checked = !state;
        }
    } catch (error) {
        addLog(`Ошибка сети: ${error.message}`, 'error');
        const toggle = document.querySelector(`input[data-output="${output}"]`);
        if (toggle) toggle.checked = !state;
    }
}

/**
 * Добавление записи в лог операций (на странице отладки).
 * @param {string} message - текст сообщения
 * @param {string} type - тип: 'info', 'success', 'error', 'warning'
 */
function addLog(message, type = 'info') {
    const log = document.getElementById('operationLog');
    if (!log) return;
    const time = new Date().toLocaleTimeString('ru-RU');
    const entry = document.createElement('div');
    entry.className = `log-entry log-${type}`;
    entry.innerHTML = `<span class="log-time">[${time}]</span> ${message}`;
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
    // Ограничиваем количество записей в логе (не более 50)
    const entries = log.querySelectorAll('.log-entry');
    if (entries.length > 50) entries[0].remove();
}