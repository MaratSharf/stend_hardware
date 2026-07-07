#!/usr/bin/env python3
"""
Модуль конфигурации проекта.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Класс конфигурации проекта."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Инициализация конфигурации.
        
        Args:
            config_path: Путь к файлу конфигурации YAML
        """
        self.config_path = config_path or self._find_config_file()
        self._config_data: Dict[str, Any] = {}
        self._load_config()
    
    def _find_config_file(self) -> str:
        """Поиск файла конфигурации."""
        # Проверяем стандартные расположения
        possible_paths = [
            'config.yaml',
            'config.yml',
            os.path.join(os.path.dirname(__file__), '..', 'config.yaml'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml'),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Возвращаем путь по умолчанию
        return 'config.yaml'
    
    def _load_config(self) -> None:
        """Загрузка конфигурации из файла."""
        if not os.path.exists(self.config_path):
            # Создаем конфигурацию по умолчанию
            self._config_data = self._get_default_config()
            self._save_config()
        else:
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config_data = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Ошибка загрузки конфигурации: {e}")
                self._config_data = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Конфигурация по умолчанию."""
        return {
            'database': {
                'host': 'localhost',
                'port': 5432,
                'name': 'stend_db',
                'user': 'stend_user',
                'password': 'stend_password'
            },
            'server': {
                'host': '0.0.0.0',
                'port': 5000,
                'debug': True
            },
            'hardware': {
                'enabled': False,
                'plc_ip': '192.168.1.10',
                'camera_enabled': False
            },
            'auth': {
                'session_timeout': 3600,  # 1 час
                'min_password_length': 6
            }
        }
    
    def _save_config(self) -> None:
        """Сохранение конфигурации в файл."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config_data, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Получение значения конфигурации.
        
        Args:
            key: Ключ в формате 'section.key' или просто 'section'
            default: Значение по умолчанию
            
        Returns:
            Значение конфигурации
        """
        keys = key.split('.')
        value = self._config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Установка значения конфигурации.
        
        Args:
            key: Ключ в формате 'section.key'
            value: Значение
        """
        keys = key.split('.')
        config = self._config_data
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self._save_config()
    
    @property
    def database(self) -> Dict[str, Any]:
        """Настройки базы данных."""
        return self.get('database', {})
    
    @property
    def server(self) -> Dict[str, Any]:
        """Настройки сервера."""
        return self.get('server', {})
    
    @property
    def hardware(self) -> Dict[str, Any]:
        """Настройки оборудования."""
        return self.get('hardware', {})
    
    @property
    def auth(self) -> Dict[str, Any]:
        """Настройки аутентификации."""
        return self.get('auth', {})


# Глобальный экземпляр конфигурации
_config_instance: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Получение экземпляра конфигурации.
    
    Args:
        config_path: Путь к файлу конфигурации (опционально)
        
    Returns:
        Экземпляр Config
    """
    global _config_instance
    
    if _config_instance is None or config_path is not None:
        _config_instance = Config(config_path)
    
    return _config_instance


def reload_config() -> Config:
    """Перезагрузка конфигурации."""
    global _config_instance
    _config_instance = Config()
    return _config_instance
