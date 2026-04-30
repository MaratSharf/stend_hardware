#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Точка входа для запуска сервиса стенда машинного зрения.
Запускает веб-сервер немедленно, а подключение к оборудованию выполняется асинхронно.
"""

import argparse
import sys
import os
import signal
import yaml
from waitress import serve

from hardware.owen import OwenMK210
from hardware.hikrobot import HikrobotCamera
from core.controller import StandController
from web.app import create_app
from utils.database import get_database

# Глобальные переменные для обработчика сигналов
controller = None
owen = None
camera = None


def signal_handler(sig, frame):
    """Обработчик Ctrl+C и SIGTERM."""
    print("\n[ЗАВЕРШЕНИЕ] Получен сигнал остановки.")
    global controller, owen, camera

    if controller:
        controller.stop()

    for dev in (owen, camera):
        if dev:
            try:
                dev.disconnect()
            except Exception:
                pass

    if controller and controller._thread and controller._thread.is_alive():
        controller._thread.join(timeout=2.0)

    print("[ЗАВЕРШЕНИЕ] Ресурсы освобождены. Выход.")
    os._exit(0)


def main():
    global controller, owen, camera

    parser = argparse.ArgumentParser(description='MV сервис - стенд машинного зрения')
    parser.add_argument('--scenario', type=str, choices=['A', 'B', 'C'],
                        help='Принудительный выбор сценария (переопределяет тумблер)')
    args = parser.parse_args()

    # -------------------------- Загрузка конфигурации --------------------------
    try:
        from utils.config_manager import get_config_manager
        config_manager = get_config_manager('config.yaml')
        config = config_manager.load()
    except FileNotFoundError:
        print("[ОШИБКА] Файл config.yaml не найден.")
        sys.exit(1)
    except Exception as e:
        print(f"[ОШИБКА] Не удалось загрузить config.yaml: {e}")
        sys.exit(1)

    log_dir = config.get('paths', {}).get('logs', 'data/logs')
    os.makedirs(log_dir, exist_ok=True)

    # -------------------------- База данных --------------------------
    db = get_database(config)

    # -------------------------- Восстановление последнего проекта --------------------------
    try:
        last_result = db.get_last_result()
        if last_result and last_result.get('project_name'):
            config['camera']['project_name'] = last_result['project_name']
            print(f"[БД] Восстановлен последний проект: {last_result['project_name']}")
    except Exception as e:
        print(f"[ПРЕДУПРЕЖДЕНИЕ] Ошибка восстановления проекта: {e}")

    # -------------------------- Инициализация драйверов (без подключения) --------------------------
    owen_cfg = config.get('owen', {})
    owen_log_cfg = config.get('logging', {}).get('owen', {})
    try:
        owen = OwenMK210(
            ip=owen_cfg.get('ip', '192.168.1.99'),
            port=owen_cfg.get('port', 502),
            unit=owen_cfg.get('unit', 1),
            timeout=owen_cfg.get('timeout', 1.0),
            log_max_bytes=owen_log_cfg.get('max_bytes'),
            log_backup_count=owen_log_cfg.get('backup_count')
        )
    except Exception as e:
        print(f"[ПРЕДУПРЕЖДЕНИЕ] Ошибка инициализации ОВЕН: {e}")
        owen = None

    cam_cfg = config.get('camera', {})
    cam_log_cfg = config.get('logging', {}).get('hikrobot', {})
    try:
        camera = HikrobotCamera(
            ip=cam_cfg.get('ip', '192.168.1.36'),
            port=cam_cfg.get('port', 502),
            unit=cam_cfg.get('unit', 1),
            control_offset=cam_cfg.get('control_offset', 0),
            status_offset=cam_cfg.get('status_offset', 1),
            result_offset=cam_cfg.get('result_offset', 2),
            command_offset=cam_cfg.get('command_offset', 500),
            byte_order=cam_cfg.get('byte_order', 'little'),
            command_terminator=cam_cfg.get('command_terminator', ''),
            verify_switch=cam_cfg.get('verify_switch', False),
            log_max_bytes=cam_log_cfg.get('max_bytes'),
            log_backup_count=cam_log_cfg.get('backup_count')
        )
    except Exception as e:
        print(f"[ПРЕДУПРЕЖДЕНИЕ] Ошибка инициализации камеры: {e}")
        camera = None

    # -------------------------- Контроллер (без блокирующих попыток подключения) --------------------------
    try:
        controller = StandController(owen, camera, config, db)
        # Изначально оборудование недоступно – контроллер сам попытается подключиться в фоне
        controller.hardware_available = False
        controller.owen_available = False
        controller.camera_available = False
    except Exception as e:
        print(f"[ОШИБКА] Не удалось создать контроллер: {e}")
        sys.exit(1)

    if args.scenario:
        controller.scenario_override = args.scenario

    # Запуск потока контроллера (он начнёт асинхронные попытки подключения)
    controller.start()

    # -------------------------- Веб-приложение --------------------------
    flask_app = create_app(config, controller, db)
    socketio = flask_app.config.get('socketio')

    # Установка обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # -------------------------- Запуск веб-сервера (немедленно) --------------------------
    print("[СЕРВЕР] Запуск MV сервиса на http://0.0.0.0:5001")
    try:
        # Используем Socket.IO сервер вместо Waitress для поддержки WebSocket
        socketio.run(flask_app, host='0.0.0.0', port=5001, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        pass
    finally:
        # Освобождение ресурсов (на случай нештатного завершения)
        if controller:
            controller.stop()
        for dev in (owen, camera):
            if dev:
                try:
                    dev.disconnect()
                except Exception:
                    pass
        print("[ЗАВЕРШЕНИЕ] Ресурсы освобождены.")


if __name__ == '__main__':
    main()