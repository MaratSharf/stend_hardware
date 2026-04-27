/**
 * settings.js - Логика страницы настроек
 */

let configData = {};
let originalConfig = {};

document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    setupTabs();
    setupButtons();
    setupModals();
    loadBackups();
});

async function loadConfig() {
    try {
        const response = await fetch('/api/settings/get');
        const data = await response.json();
        if (data.success) {
            configData = data.config;
            originalConfig = JSON.parse(JSON.stringify(data.config));
            populateForm(configData);
        } else {
            showNotification('Ошибка загрузки конфигурации: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Ошибка подключения к серверу: ' + error.message, 'error');
    }
}

function populateForm(config) {
    setIfExists('owen_ip', config.owen?.ip);
    setIfExists('owen_port', config.owen?.port);
    setIfExists('owen_unit', config.owen?.unit);
    setIfExists('owen_timeout', config.owen?.timeout);

    setIfExists('camera_ip', config.camera?.ip);
    setIfExists('camera_port', config.camera?.port);
    setIfExists('camera_unit', config.camera?.unit);
    setIfExists('camera_project', config.camera?.project_name);
    setIfExists('camera_control_offset', config.camera?.control_offset);
    setIfExists('camera_status_offset', config.camera?.status_offset);
    setIfExists('camera_result_offset', config.camera?.result_offset);
    setIfExists('camera_command_offset', config.camera?.command_offset);
    setIfExists('camera_byte_order', config.camera?.byte_order);
    setIfExists('camera_scenario_a_interval', config.camera?.scenario_a_interval);

    setIfExists('controller_cycle_time', config.controller?.cycle_time);
    setIfExists('controller_debounce_ms', config.controller?.debounce_ms);
    setIfExists('controller_camera_ready_interval', config.controller?.camera_ready_interval);
    setIfExists('controller_state_timeout', config.controller?.state_timeout);
    setIfExists('controller_ejector_pulse', config.controller?.ejector_pulse);

    setIfExists('indicators_lamp_ok_duration', config.indicators?.lamp_ok_duration);
    setIfExists('indicators_error_blink_count', config.indicators?.error_blink_count);
    setIfExists('indicators_error_blink_interval', config.indicators?.error_blink_interval);

    setIfExists('logging_controller_level', config.logging?.controller?.level);
    setIfExists('logging_controller_max_bytes', config.logging?.controller?.max_bytes);
    setIfExists('logging_controller_backup_count', config.logging?.controller?.backup_count);
    setIfExists('logging_owen_level', config.logging?.owen?.level);
    setIfExists('logging_owen_max_bytes', config.logging?.owen?.max_bytes);
    setIfExists('logging_owen_backup_count', config.logging?.owen?.backup_count);
    setIfExists('logging_hikrobot_level', config.logging?.hikrobot?.level);
    setIfExists('logging_hikrobot_max_bytes', config.logging?.hikrobot?.max_bytes);
    setIfExists('logging_hikrobot_backup_count', config.logging?.hikrobot?.backup_count);
    setIfExists('logging_web_level', config.logging?.web?.level);
    setIfExists('logging_web_max_bytes', config.logging?.web?.max_bytes);
    setIfExists('logging_web_backup_count', config.logging?.web?.backup_count);

    setIfExists('paths_images', config.paths?.images);
    setIfExists('paths_logs', config.paths?.logs);
}

function setIfExists(id, value) {
    const element = document.getElementById(id);
    if (element && value !== undefined && value !== null) element.value = value;
}

function collectFormData() {
    const config = {
        owen: {
            ip: getVal('owen_ip'), port: getNum('owen_port'), unit: getNum('owen_unit'), timeout: getNum('owen_timeout')
        },
        camera: {
            ip: getVal('camera_ip'), port: getNum('camera_port'), unit: getNum('camera_unit'),
            project_name: getVal('camera_project'), control_offset: getNum('camera_control_offset'),
            status_offset: getNum('camera_status_offset'), result_offset: getNum('camera_result_offset'),
            command_offset: getNum('camera_command_offset'), byte_order: getVal('camera_byte_order'),
            scenario_a_interval: getNum('camera_scenario_a_interval')
        },
        controller: {
            cycle_time: getNum('controller_cycle_time'), debounce_ms: getNum('controller_debounce_ms'),
            camera_ready_interval: getNum('controller_camera_ready_interval'),
            state_timeout: getNum('controller_state_timeout'), ejector_pulse: getNum('controller_ejector_pulse')
        },
        indicators: {
            lamp_ok_duration: getNum('indicators_lamp_ok_duration'),
            error_blink_count: getNum('indicators_error_blink_count'),
            error_blink_interval: getNum('indicators_error_blink_interval')
        },
        logging: {
            controller: { level: getVal('logging_controller_level'), max_bytes: getNum('logging_controller_max_bytes'), backup_count: getNum('logging_controller_backup_count') },
            owen: { level: getVal('logging_owen_level'), max_bytes: getNum('logging_owen_max_bytes'), backup_count: getNum('logging_owen_backup_count') },
            hikrobot: { level: getVal('logging_hikrobot_level'), max_bytes: getNum('logging_hikrobot_max_bytes'), backup_count: getNum('logging_hikrobot_backup_count') },
            web: { level: getVal('logging_web_level'), max_bytes: getNum('logging_web_max_bytes'), backup_count: getNum('logging_web_backup_count') }
        },
        paths: { images: getVal('paths_images'), logs: getVal('paths_logs') }
    };
    return cleanConfig(config);
}

function getVal(id) {
    const element = document.getElementById(id);
    return element ? element.value : undefined;
}
function getNum(id) {
    const val = getVal(id);
    if (val === undefined || val === '') return undefined;
    const num = parseFloat(val);
    return isNaN(num) ? undefined : num;
}
function cleanConfig(obj) {
    if (Array.isArray(obj)) return obj.filter(v => v !== undefined).map(cleanConfig);
    if (typeof obj === 'object' && obj !== null) {
        const cleaned = {};
        for (const key in obj) if (obj[key] !== undefined) cleaned[key] = cleanConfig(obj[key]);
        return Object.keys(cleaned).length ? cleaned : undefined;
    }
    return obj;
}

function setupTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            tabBtns.forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(tabId + '-tab').classList.add('active');
        });
    });
}

function setupButtons() {
    document.getElementById('saveBtn').addEventListener('click', saveConfig);
    document.getElementById('exportBtn').addEventListener('click', exportConfig);
    document.getElementById('importBtn').addEventListener('click', () => document.getElementById('importModal').classList.remove('hidden'));
    document.getElementById('backupBtn').addEventListener('click', createBackup);
    document.getElementById('refreshBackupsBtn').addEventListener('click', loadBackups);
}

async function saveConfig() {
    if (!window.checkHardwareAndNotify('Сохранение конфигурации')) return;
    const newConfig = collectFormData();
    if (JSON.stringify(newConfig) === JSON.stringify(originalConfig)) {
        showNotification('Нет изменений для сохранения', 'info');
        return;
    }
    const confirmed = await showConfirm('Сохранение конфигурации', 'Изменения будут применены. Для вступления в силу некоторых настроек может потребоваться перезапуск приложения. Продолжить?');
    if (!confirmed) return;
    try {
        const response = await fetch('/api/settings/update', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config: newConfig })
        });
        const data = await response.json();
        if (data.success) {
            showNotification('Конфигурация успешно сохранена', 'success');
            originalConfig = JSON.parse(JSON.stringify(newConfig));
            configData = newConfig;
            updateLastSave();
        } else showNotification('Ошибка сохранения: ' + data.error, 'error');
    } catch (error) {
        showNotification('Ошибка подключения к серверу: ' + error.message, 'error');
    }
}

async function exportConfig() {
    try {
        const response = await fetch('/api/settings/export');
        const blob = await response.blob();
        if (response.ok) {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'config_export_' + new Date().toISOString().slice(0, 10) + '.yaml';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            showNotification('Конфигурация экспортирована', 'success');
        } else {
            const data = await response.json();
            showNotification('Ошибка экспорта: ' + data.error, 'error');
        }
    } catch (error) { showNotification('Ошибка: ' + error.message, 'error'); }
}

function setupModals() {
    document.getElementById('modalClose').addEventListener('click', () => document.getElementById('confirmModal').classList.add('hidden'));
    document.getElementById('modalCancel').addEventListener('click', () => document.getElementById('confirmModal').classList.add('hidden'));
    document.getElementById('importModalClose').addEventListener('click', () => document.getElementById('importModal').classList.add('hidden'));
    document.getElementById('importCancel').addEventListener('click', () => document.getElementById('importModal').classList.add('hidden'));
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => e.target.closest('.modal').classList.add('hidden'));
    });
    document.getElementById('importConfirm').addEventListener('click', importConfig);
}

async function importConfig() {
    if (!window.checkHardwareAndNotify('Импорт конфигурации')) return;
    const fileInput = document.getElementById('importFile');
    const file = fileInput.files[0];
    if (!file) { showNotification('Выберите файл для импорта', 'warning'); return; }
    const formData = new FormData();
    formData.append('file', file);
    try {
        const response = await fetch('/api/settings/import', { method: 'POST', body: formData });
        const data = await response.json();
        if (data.success) {
            showNotification('Конфигурация импортирована. Требуется перезагрузка.', 'success');
            document.getElementById('importModal').classList.add('hidden');
            setTimeout(() => loadConfig(), 500);
        } else showNotification('Ошибка импорта: ' + data.error, 'error');
    } catch (error) { showNotification('Ошибка: ' + error.message, 'error'); }
}

async function createBackup() {
    try {
        const response = await fetch('/api/settings/backup', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            showNotification('Резервная копия создана: ' + data.backup_filename, 'success');
            loadBackups();
        } else showNotification('Ошибка создания резервной копии: ' + data.error, 'error');
    } catch (error) { showNotification('Ошибка: ' + error.message, 'error'); }
}

async function loadBackups() {
    const backupsList = document.getElementById('backupsList');
    backupsList.innerHTML = '<div class="loading">Загрузка...</div>';
    try {
        const response = await fetch('/api/settings/backups');
        const data = await response.json();
        if (data.success && data.backups.length > 0) {
            backupsList.innerHTML = data.backups.map(backup => `
                <div class="backup-item">
                    <div class="backup-info">
                        <span class="backup-name">${backup.filename}</span>
                        <span class="backup-meta">${formatFileSize(backup.size)} • ${formatDate(backup.created)}</span>
                    </div>
                    <div class="backup-actions">
                        <button class="btn btn-secondary btn-sm" onclick="restoreBackup('${backup.filename}')">🔄 Восстановить</button>
                        <button class="btn btn-secondary btn-sm" onclick="downloadBackup('${backup.filename}')">📥 Скачать</button>
                    </div>
                </div>
            `).join('');
        } else if (data.success) backupsList.innerHTML = '<div class="loading">Резервные копии не найдены</div>';
        else backupsList.innerHTML = '<div class="loading">Ошибка загрузки</div>';
    } catch (error) { backupsList.innerHTML = '<div class="loading">Ошибка: ' + error.message + '</div>'; }
}

async function restoreBackup(filename) {
    if (!window.checkHardwareAndNotify('Восстановление из резервной копии')) return;
    const confirmed = await showConfirm('Восстановление из резервной копии', `Вы уверены, что хотите восстановить конфигурацию из файла "${filename}"? Текущая конфигурация будет сохранена как резервная копия.`);
    if (!confirmed) return;
    try {
        const response = await fetch('/api/settings/restore', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ backup_filename: filename })
        });
        const data = await response.json();
        if (data.success) {
            showNotification('Конфигурация восстановлена', 'success');
            setTimeout(() => loadConfig(), 500);
        } else showNotification('Ошибка восстановления: ' + data.error, 'error');
    } catch (error) { showNotification('Ошибка: ' + error.message, 'error'); }
}

async function downloadBackup(filename) {
    try {
        const response = await fetch('/api/settings/backup/download?filename=' + encodeURIComponent(filename));
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            const data = await response.json();
            showNotification('Ошибка загрузки: ' + data.error, 'error');
        }
    } catch (error) { showNotification('Ошибка: ' + error.message, 'error'); }
}

function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = 'notification ' + type;
    notification.classList.remove('hidden');
    setTimeout(() => notification.classList.add('hidden'), 5000);
}

function showConfirm(title, message) {
    return new Promise((resolve) => {
        document.getElementById('modalTitle').textContent = title;
        document.getElementById('modalMessage').textContent = message;
        const modal = document.getElementById('confirmModal');
        modal.classList.remove('hidden');
        const confirmBtn = document.getElementById('modalConfirm');
        const cancelBtn = document.getElementById('modalCancel');
        const closeBtn = document.getElementById('modalClose');
        const cleanup = () => {
            confirmBtn.removeEventListener('click', onConfirm);
            cancelBtn.removeEventListener('click', onCancel);
            closeBtn.removeEventListener('click', onCancel);
        };
        const onConfirm = () => { cleanup(); modal.classList.add('hidden'); resolve(true); };
        const onCancel = () => { cleanup(); modal.classList.add('hidden'); resolve(false); };
        confirmBtn.addEventListener('click', onConfirm);
        cancelBtn.addEventListener('click', onCancel);
        closeBtn.addEventListener('click', onCancel);
    });
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString('ru-RU', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}
function updateLastSave() {
    const now = new Date();
    document.getElementById('lastSave').textContent = now.toLocaleString('ru-RU');
}