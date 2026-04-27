# -*- coding: utf-8 -*-
"""
Менеджер конфигурации для стенда машинного зрения.
Предоставляет функции для чтения, записи, валидации и резервного копирования config.yaml.
"""

import os
import shutil
import yaml
from datetime import datetime
from typing import Any, Dict, Optional


class ConfigManager:
    """Управление конфигурационным файлом."""

    def __init__(self, config_path: str = 'config.yaml'):
        """
        :param config_path: Путь к файлу конфигурации
        """
        self.config_path = config_path
        self._config_cache: Optional[Dict[str, Any]] = None
        self._last_modified: float = 0.0

    def load(self, force: bool = False) -> Dict[str, Any]:
        """
        Загрузка конфигурации из файла.
        :param force: Принудительная перезагрузка (игнорировать кэш)
        :return: Словарь конфигурации
        """
        if not force and self._config_cache is not None:
            # Проверяем, не изменился ли файл
            if os.path.exists(self.config_path):
                mtime = os.path.getmtime(self.config_path)
                if mtime <= self._last_modified:
                    return self._config_cache

        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Конфигурационный файл не найден: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self._config_cache = yaml.safe_load(f)
            self._last_modified = os.path.getmtime(self.config_path)

        return self._config_cache

    def save(self, config: Dict[str, Any]) -> bool:
        """
        Сохранение конфигурации в файл.
        :param config: Словарь конфигурации
        :return: True при успехе
        """
        # Валидация перед сохранением
        if not self._validate_config(config):
            raise ValueError("Неверная конфигурация")

        # Создаём резервную копию
        self._create_backup()

        # Сохраняем новую конфигурацию
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        self._config_cache = config
        self._last_modified = os.path.getmtime(self.config_path)

        return True

    def get(self, key: str, default: Any = None) -> Any:
        """
        Получение значения по ключу (поддерживает вложенные ключи через точку).
        :param key: Ключ (например, 'camera.ip' или 'owen')
        :param default: Значение по умолчанию
        :return: Значение конфигурации
        """
        config = self.load()

        keys = key.split('.')
        value = config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> bool:
        """
        Установка значения по ключу.
        :param key: Ключ (поддерживает вложенные ключи через точку)
        :param value: Новое значение
        :return: True при успехе
        """
        config = self.load()

        keys = key.split('.')
        current = config

        # Проходим по вложенным ключам, кроме последнего
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Устанавливаем значение
        current[keys[-1]] = value

        return self.save(config)

    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Валидация конфигурации.
        :param config: Словарь конфигурации
        :return: True если конфигурация валидна
        """
        # Обязательные секции
        required_sections = ['owen', 'camera', 'paths', 'logging', 'controller']
        for section in required_sections:
            if section not in config:
                return False

        # Проверка IP-адресов (базовая)
        owen_ip = config.get('owen', {}).get('ip', '')
        camera_ip = config.get('camera', {}).get('ip', '')

        if not self._is_valid_ip(owen_ip):
            return False
        if not self._is_valid_ip(camera_ip):
            return False

        # Проверка портов
        owen_port = config.get('owen', {}).get('port', 0)
        camera_port = config.get('camera', {}).get('port', 0)

        if not (0 < owen_port <= 65535):
            return False
        if not (0 < camera_port <= 65535):
            return False

        # Проверка числовых параметров
        controller = config.get('controller', {})
        if controller.get('cycle_time', 0) <= 0:
            return False
        if controller.get('debounce_ms', 0) < 0:
            return False

        return True

    def _is_valid_ip(self, ip: str) -> bool:
        """Простая проверка формата IP-адреса."""
        if not ip:
            return False
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        try:
            return all(0 <= int(part) <= 255 for part in parts)
        except ValueError:
            return False

    def _create_backup(self) -> None:
        """Создание резервной копии конфигурации."""
        if not os.path.exists(self.config_path):
            return

        backup_dir = os.path.join(os.path.dirname(self.config_path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'config_{timestamp}.yaml')

        shutil.copy2(self.config_path, backup_path)

        # Храним только последние 10 резервных копий
        self._cleanup_old_backups(backup_dir, keep=10)

    def _cleanup_old_backups(self, backup_dir: str, keep: int = 10) -> None:
        """Удаление старых резервных копий."""
        try:
            backups = sorted(
                [f for f in os.listdir(backup_dir) if f.startswith('config_') and f.endswith('.yaml')],
                reverse=True
            )
            for old_backup in backups[keep:]:
                os.remove(os.path.join(backup_dir, old_backup))
        except Exception:
            pass  # Игнорируем ошибки очистки

    def get_backup_list(self) -> list:
        """
        Получение списка резервных копий.
        :return: Список словарей с информацией о резервных копиях
        """
        backup_dir = os.path.join(os.path.dirname(self.config_path), 'backups')
        if not os.path.exists(backup_dir):
            return []

        backups = []
        for filename in sorted(os.listdir(backup_dir), reverse=True):
            if filename.startswith('config_') and filename.endswith('.yaml'):
                filepath = os.path.join(backup_dir, filename)
                stat = os.stat(filepath)
                backups.append({
                    'filename': filename,
                    'path': filepath,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

        return backups

    def restore_from_backup(self, backup_filename: str) -> bool:
        """
        Восстановление из резервной копии.
        :param backup_filename: Имя файла резервной копии
        :return: True при успехе
        """
        backup_dir = os.path.join(os.path.dirname(self.config_path), 'backups')
        backup_path = os.path.join(backup_dir, backup_filename)

        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Резервная копия не найдена: {backup_filename}")

        # Создаём резервную копию текущей конфигурации перед восстановлением
        self._create_backup()

        # Восстанавливаем из резервной копии
        shutil.copy2(backup_path, self.config_path)
        self._config_cache = None  # Сбрасываем кэш
        self._last_modified = 0.0

        return True

    def export_config(self, export_path: str) -> bool:
        """
        Экспорт конфигурации в файл.
        :param export_path: Путь для экспорта
        :return: True при успехе
        """
        config = self.load()
        with open(export_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        return True

    def import_config(self, import_path: str) -> bool:
        """
        Импорт конфигурации из файла.
        :param import_path: Путь к импортируемому файлу
        :return: True при успехе
        """
        if not os.path.exists(import_path):
            raise FileNotFoundError(f"Файл не найден: {import_path}")

        with open(import_path, 'r', encoding='utf-8') as f:
            imported_config = yaml.safe_load(f)

        if not self._validate_config(imported_config):
            raise ValueError("Импортируемая конфигурация не прошла валидацию")

        return self.save(imported_config)


# Глобальный экземляр (singleton)
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: str = 'config.yaml') -> ConfigManager:
    """Получение экземпляра ConfigManager (singleton)."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager
