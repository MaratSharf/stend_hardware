# core/controller.py
import threading
import time
import os
import glob
from datetime import datetime
from enum import Enum
from queue import Queue, Empty
from typing import Optional, Dict, Any

from utils.logger import setup_logger
from utils.database import get_database


class ScenarioCState(Enum):
    IDLE = 0
    CONVEYOR_RUNNING_TO_CAMERA = 1
    POSITIONED = 2
    CONVEYOR_RUNNING_TO_EXIT = 3


class ControllerCommand(Enum):
    """Команды, отправляемые из веб-потоков в главный цикл контроллера."""
    TRIGGER_B = "trigger_b"
    ACTIVATE_SCENARIO = "activate_scenario"
    SWITCH_PROJECT = "switch_project"
    SET_OUTPUT = "set_output"


class StandController:
    # Индексы входов (DI)
    DI_DETECT_LEFT = 0
    DI_POS_LEFT = 1
    DI_POS_RIGHT = 2
    DI_EXIT = 3
    DI_TOGGLE_A = 4
    DI_TOGGLE_B = 5

    # Индексы выходов (DO)
    DO_CONVEYOR = 0
    DO_EJECTOR = 1
    DO_LAMP_RED = 2
    DO_LAMP_GREEN = 3

    DEFAULT_CYCLE_TIME = 0.2
    DEFAULT_DEBOUNCE_MS = 10
    DEFAULT_CAMERA_READY_INTERVAL = 10
    DEFAULT_EJECTOR_PULSE = 0.5
    DEFAULT_STATE_TIMEOUT = 30.0
    SCENARIO_SWITCH_DELAY = 3.0
    DEFAULT_SCENARIO_A_INTERVAL = 0.5
    RECONNECT_CHECK_INTERVAL = 10.0

    def __init__(self, owen, camera, config, db=None):
        self.owen = owen
        self.camera = camera
        self.config = config
        self.db = db if db else get_database()

        # Флаги доступности (обновляются динамически)
        self.hardware_available = False
        self.owen_available = False
        self.camera_available = False

        # Режим офлайн (принудительное отключение оборудования)
        self.offline_mode = False

        # Флаг активности сценария (запущен ли он по кнопке «Запуск»)
        self.scenario_active = False

        # Логгер
        log_cfg = config.get('logging', {}).get('controller', {})
        log_dir = config.get('paths', {}).get('logs', 'data/logs')
        self.logger = setup_logger(
            'controller',
            log_dir=log_dir,
            level=log_cfg.get('level', 'DEBUG'),
            max_bytes=log_cfg.get('max_bytes'),
            backup_count=log_cfg.get('backup_count')
        )
        self.logger.info("=" * 50)
        self.logger.info("КОНТРОЛЛЕР ЗАПУЩЕН (MV-сервис)")
        self.logger.info("=" * 50)

        # Состояние входов
        self.di = [0] * 6
        self.prev_di = [0] * 6
        self.di_debounce = [None] * 6
        self.di_change_time = [0.0] * 6
        self.input_read_errors = 0

        # Состояние выходов
        self.do = [0] * 4
        self._last_written_do = None

        # Режимы и сценарии
        self.auto_mode = True
        self.current_scenario = None
        self.scenario_override = None
        self.web_scenario_selection = False
        self.web_selected_scenario = 'C'

        # Загружаем состояние веб-выбора из файла
        self._load_web_scenario_state()

        # Готовность камеры
        self.camera_ready = False
        self.last_camera_check = 0.0
        self._camera_error_blink_started = False

        # Состояние автомата сценария C
        self.scenario_c_state = ScenarioCState.IDLE
        self.scenario_c_data = {
            'target_sensor': None,
            'result': None,
            'state_start_time': 0.0,
            'measurement_done': False,
        }

        # Мигание ламп
        self.blink_active = False
        self.blink_start = 0.0
        self.blink_duration = 0.0
        self.blink_green = False
        self.blink_red = False
        self.blink_period = 0.0
        self.blink_callback = None

        # Детектор смены сценария
        self.pending_scenario = None
        self.pending_scenario_start = 0.0

        # Сценарий A
        self.last_a_trigger = 0.0
        self.a_active = False
        self.waiting_for_ng_stop = False
        self.has_valid_measurement = False

        # Для веб-интерфейса
        self.last_inputs = None
        self.last_outputs = None
        self.last_camera_status = None
        self.last_result = {'result': None, 'image': None, 'time': None, 'raw': None}

        # Папки для изображений
        image_dir = config.get('paths', {}).get('images', 'data/images')
        os.makedirs(os.path.join(image_dir, 'foto/OK'), exist_ok=True)
        os.makedirs(os.path.join(image_dir, 'foto/NG'), exist_ok=True)

        # Поток управления
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._stop_event = threading.Event()          # сигнал принудительной остановки
        self.command_queue = Queue()                  # очередь команд от веб-потоков

        # Параметры из конфига
        ctrl_cfg = config.get('controller', {})
        self.cycle_time = ctrl_cfg.get('cycle_time', self.DEFAULT_CYCLE_TIME)
        self.debounce_ms = ctrl_cfg.get('debounce_ms', self.DEFAULT_DEBOUNCE_MS)
        self.camera_ready_interval = ctrl_cfg.get('camera_ready_interval', self.DEFAULT_CAMERA_READY_INTERVAL)
        self.ejector_pulse = ctrl_cfg.get('ejector_pulse', self.DEFAULT_EJECTOR_PULSE)
        self.state_timeout = ctrl_cfg.get('state_timeout', self.DEFAULT_STATE_TIMEOUT)
        self.scenario_a_interval = config.get('camera', {}).get('scenario_a_interval', self.DEFAULT_SCENARIO_A_INTERVAL)

        self._no_tool_warning_shown = False
        self._last_reconnect_attempt = 0.0

        # Загружаем последний результат из БД (если есть)
        self._load_last_result_from_db()

        self.logger.info(f"Параметры: cycle_time={self.cycle_time}, debounce={self.debounce_ms}мс, "
                         f"state_timeout={self.state_timeout}с, scenario_a_interval={self.scenario_a_interval}с")
        self.logger.info(f"Режим работы: {'АВТО' if self.auto_mode else 'РУЧНОЙ'} (по умолчанию)")
        self.logger.info(f"Веб-выбор сценария: {'включён' if self.web_scenario_selection else 'выключён'}, "
                         f"выбранный сценарий: {self.web_selected_scenario}")

    # -------------------------------------------------------------------------
    # Публичные методы для управления контроллером (вызываются из веб-потоков)
    # -------------------------------------------------------------------------
    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            self.logger.info("Контроллер запущен")

    def stop(self):
        self.logger.info("Остановка контроллера...")
        self._stop_event.set()
        with self._lock:
            self._running = False
        # Очищаем очередь команд, чтобы не блокировать завершение
        while not self.command_queue.empty():
            try:
                self.command_queue.get_nowait()
            except Empty:
                break
        if self._thread:
            self._thread.join(timeout=3.0)
            if self._thread.is_alive():
                self.logger.warning("Поток контроллера не завершился, продолжаем освобождение ресурсов")
        self._reset_outputs()
        self.logger.info("Контроллер остановлен")

    def send_command(self, command: ControllerCommand, data: Optional[Dict[str, Any]] = None):
        """
        Неблокирующая отправка команды из веб-потока в главный цикл контроллера.
        """
        self.command_queue.put((command, data or {}))
        self.logger.debug(f"Команда добавлена в очередь: {command}")

    def set_auto_mode(self, auto: bool):
        with self._lock:
            old_mode = self.auto_mode
            self.auto_mode = auto
            if old_mode and not auto:
                self.logger.info("РУЧНОЙ РЕЖИМ из веб")
                self._reset_outputs()
                self.current_scenario = None
                self.scenario_c_state = ScenarioCState.IDLE
                self.scenario_active = False
            elif not old_mode and auto:
                self.logger.info("АВТОМАТИЧЕСКИЙ РЕЖИМ из веб")
                # Не активируем сценарий автоматически – ждём команды activate_scenario

    def get_auto_mode(self) -> bool:
        with self._lock:
            return self.auto_mode

    def set_offline_mode(self, enabled: bool):
        with self._lock:
            if self.offline_mode == enabled:
                return
            self.offline_mode = enabled
            if enabled:
                self.logger.info("Включён офлайн-режим. Оборудование отключено.")
                self.hardware_available = False
                self.owen_available = False
                self.camera_available = False
                self.camera_ready = False
                self.scenario_active = False
                self._reset_outputs()
                if self.current_scenario:
                    self.current_scenario = None
                self.scenario_c_state = ScenarioCState.IDLE
            else:
                self.logger.info("Офлайн-режим выключен. Попытка восстановления связи с оборудованием.")
                self._last_reconnect_attempt = 0.0

    def get_last_result(self):
        with self._lock:
            return self.last_result.copy()

    def get_last_inputs(self):
        with self._lock:
            return self.last_inputs.copy() if self.last_inputs else None

    def get_last_outputs(self):
        with self._lock:
            return self.last_outputs.copy() if self.last_outputs else None

    def get_last_camera_status(self):
        with self._lock:
            return self.last_camera_status.copy() if self.last_camera_status else None

    def get_status(self):
        with self._lock:
            return {
                'di': self.di.copy(),
                'do': self.do.copy(),
                'auto_mode': self.auto_mode,
                'current_scenario': self.current_scenario,
                'camera_ready': self.camera_ready,
                'scenario_c_state': self.scenario_c_state.name,
                'hardware_available': self.hardware_available,
                'owen_available': self.owen_available,
                'camera_available': self.camera_available,
                'offline_mode': self.offline_mode,
                'scenario_active': self.scenario_active,
            }

    def manual_set_output(self, output_num, state):
        # Используется только при обработке команды SET_OUTPUT из главного цикла
        if not self.auto_mode and self.hardware_available and not self.offline_mode:
            if 0 <= output_num < 4:
                self.do[output_num] = 1 if state else 0
                self._apply_outputs()
                self.logger.info(f"Ручное управление: выход {output_num} = {state}")
                return True
        return False

    def set_web_scenario_selection(self, enabled: bool):
        with self._lock:
            self.web_scenario_selection = enabled
            self.logger.info(f"Выбор сценария из веб: {'включён' if enabled else 'выключен'}")
            self._save_web_scenario_state()
            if not enabled:
                # Если выбор из веб выключен, переключаемся по тумблерам
                toggle = (self.di[self.DI_TOGGLE_A], self.di[self.DI_TOGGLE_B])
                scenario = self._toggle_to_scenario(toggle)
                if scenario:
                    self.send_command(ControllerCommand.ACTIVATE_SCENARIO, {'scenario': scenario})

    def set_web_selected_scenario(self, scenario: str):
        with self._lock:
            if scenario in ('A', 'B', 'C'):
                self.web_selected_scenario = scenario
                self.logger.info(f"Установлен сценарий из веб: {scenario}")
                self._save_web_scenario_state()
                # Не активируем автоматически – ждём команды ACTIVATE_SCENARIO
            else:
                self.logger.warning(f"Попытка установить недопустимый сценарий: {scenario}")

    def activate_web_scenario(self):
        """
        Запускает выбранный в веб-интерфейсе сценарий.
        Вызывается из веб-потока, отправляет команду в очередь.
        """
        with self._lock:
            scenario = self.web_selected_scenario
            if not scenario:
                self.logger.warning("Нет выбранного сценария для активации")
                return
        self.send_command(ControllerCommand.ACTIVATE_SCENARIO, {'scenario': scenario})
        self.logger.info(f"Команда активации сценария {scenario} отправлена в очередь")

    # -------------------------------------------------------------------------
    # Внутренние методы (выполняются только в главном цикле)
    # -------------------------------------------------------------------------
    def _reset_outputs(self):
        self.do = [0, 0, 0, 0]
        self._apply_outputs()
        self.logger.info("Выходы сброшены")

    def _apply_outputs(self):
        if not self.hardware_available or self.offline_mode:
            return
        if self.do != self._last_written_do:
            self.logger.debug(f"Попытка записи выходов: {self.do}")
            success = self.owen.write_outputs(self.do)
            if success:
                self._last_written_do = self.do.copy()
                self.logger.debug(f"Выходы установлены: {self.do}")
            else:
                self.logger.error("Ошибка записи выходов")
                self.owen_available = False
                self.hardware_available = False

    def _save_image(self, result):
        base_dir = os.path.abspath(self.config.get('paths', {}).get('images', 'data/images'))
        subfolder = 'foto/OK' if result == 'OK' else 'foto/NG'
        folder = os.path.join(base_dir, subfolder)
        if not os.path.exists(folder):
            self.logger.error(f"Папка {folder} не существует")
            return None
        time.sleep(0.2)
        files = glob.glob(os.path.join(folder, '*.jpg')) + glob.glob(os.path.join(folder, '*.jpeg')) + \
                glob.glob(os.path.join(folder, '*.png')) + glob.glob(os.path.join(folder, '*.bmp'))
        if not files:
            self.logger.warning("Нет файлов в папке")
            return None
        latest = max(files, key=os.path.getmtime)
        rel_path = os.path.relpath(latest, base_dir).replace('\\', '/')
        return rel_path

    def _update_camera_ready(self):
        if not self.camera_available or self.offline_mode:
            self.camera_ready = False
            return
        self.logger.debug("Чтение статуса камеры для проверки готовности...")
        status = self.camera.read_status()
        if status is None:
            self.camera_ready = False
            self.camera_available = False
            self.hardware_available = False
            self.logger.warning("Статус камеры не получен, camera_available = False")
        else:
            self.camera_available = True
            self.camera_ready = not status.get('general_fault', True)
            self.logger.debug(f"camera_ready = {self.camera_ready}")

    def _init_hardware_state(self):
        """Инициализация состояния оборудования после успешного подключения."""
        self.logger.info("Инициализация состояния оборудования...")
        self.logger.debug("Вызов owen.read_inputs()...")
        raw = self.owen.read_inputs()
        self.logger.debug("owen.read_inputs() завершён")
        if raw is not None:
            self.di = raw[:6].copy()
            self.prev_di = self.di.copy()
            self.logger.info(f"Состояние входов: {self.di}")
            self.owen_available = True
        else:
            self.di = [1] * 6
            self.prev_di = self.di.copy()
            self.owen_available = False
            self.hardware_available = False
            self.logger.warning("Не удалось прочитать входы, используются значения по умолчанию")
            return False

        # Сброс выходов
        self._reset_outputs()

        # НЕ активируем сценарий автоматически – ждём команды activate_scenario
        self.scenario_active = False
        self.logger.info("Инициализация завершена. Сценарий не активен, ожидание команды «Запуск».")
        return True

    def _run(self):
        self.logger.info("Цикл управления запущен")
        self._check_hardware()

        if self.hardware_available and not self.offline_mode:
            self.logger.info("Оборудование доступно – запуск в полном режиме")
            self._init_hardware_state()
        else:
            if self.offline_mode:
                self.logger.warning("ОФЛАЙН-РЕЖИМ – работа с оборудованием отключена")
            else:
                self.logger.warning("ОБОРУДОВАНИЕ НЕДОСТУПНО – работа в демо-режиме")
            self.di = [1] * 6
            self.prev_di = self.di.copy()

        next_cycle = time.time()
        last_reconnect_check = 0.0

        while self._running and not self._stop_event.is_set():
            loop_start = time.time()
            self.logger.debug(f"=== НАЧАЛО ИТЕРАЦИИ ЦИКЛА {loop_start:.3f} ===")
            try:
                now = time.time()

                # Обработка команд из очереди (неблокирующая)
                self._process_commands()

                # Если включён офлайн-режим, не работаем с оборудованием
                if self.offline_mode:
                    self.logger.debug("Офлайн-режим активен, пропускаем работу с оборудованием")
                    self.hardware_available = False
                    self.owen_available = False
                    self.camera_available = False
                    self.camera_ready = False
                    time.sleep(1.0)
                    continue

                if not self.hardware_available:
                    if now - last_reconnect_check >= self.RECONNECT_CHECK_INTERVAL:
                        last_reconnect_check = now
                        self.logger.info("Попытка восстановления связи с оборудованием...")
                        self._check_hardware()
                        if self.hardware_available:
                            self.logger.info("Оборудование снова доступно, инициализация...")
                            if self._init_hardware_state():
                                pass
                            else:
                                self.hardware_available = False
                    time.sleep(1.0)
                    continue

                # --- Оборудование доступно ---
                self.logger.debug("Вызов _update_inputs()...")
                inputs_ok = self._update_inputs()
                self.logger.debug(f"_update_inputs() завершён, inputs_ok={inputs_ok}")
                if not self._running or self._stop_event.is_set():
                    break
                if inputs_ok:
                    self.owen_available = True
                    self.hardware_available = True
                else:
                    self.owen_available = False
                    self.hardware_available = False
                    self.logger.warning("ОВЕН недоступен")

                with self._lock:
                    self.last_inputs = self.di.copy()

                if now - self.last_camera_check >= self.camera_ready_interval:
                    self.logger.debug(f"Обновление готовности камеры (интервал {self.camera_ready_interval} сек)")
                    self._update_camera_ready()
                    if not self._running or self._stop_event.is_set():
                        break
                    self.last_camera_check = now

                self._update_blink(now)

                if not self.camera_ready:
                    self.logger.debug("Камера не готова, вызов _handle_camera_not_ready()")
                    self._handle_camera_not_ready()
                    self._apply_outputs()
                    time.sleep(self.cycle_time)
                    self.prev_di = self.di.copy()
                    continue

                self._process_toggle(now)

                if not self.blink_active:
                    if self.auto_mode and self.scenario_active:
                        self.logger.debug("Вызов _run_auto()")
                        self._run_auto(now)
                    elif not self.auto_mode:
                        self.logger.debug("Вызов _run_manual()")
                        self._run_manual()
                    # Если auto_mode включен, но scenario_active == False – ничего не делаем

                self._apply_outputs()
                self.prev_di = self.di.copy()

                self.logger.debug("Чтение выходов ОВЕН...")
                outputs = self.owen.read_outputs()
                self.logger.debug(f"Чтение выходов завершено: {outputs}")
                if not self._running or self._stop_event.is_set():
                    break
                if outputs:
                    with self._lock:
                        self.last_outputs = outputs.copy()
                else:
                    self.owen_available = False
                    self.hardware_available = False

                self.logger.debug("Чтение статуса камеры...")
                cam_status = self.camera.read_status()
                self.logger.debug(f"Чтение статуса камеры завершено: {cam_status}")
                if not self._running or self._stop_event.is_set():
                    break
                if cam_status:
                    self.camera_available = True
                    with self._lock:
                        if cam_status != self.last_camera_status:
                            self.last_camera_status = cam_status.copy()
                            self.logger.debug(f"Статус камеры изменился: {cam_status}")
                else:
                    self.camera_available = False
                    self.hardware_available = False

                next_cycle += self.cycle_time
                sleep_time = max(0, next_cycle - time.time())
                # Разбиваем длительный сон на короткие интервалы для возможности остановки
                while sleep_time > 0 and self._running and not self._stop_event.is_set():
                    step = min(sleep_time, 0.1)
                    time.sleep(step)
                    sleep_time -= step

                self.logger.debug(f"=== ИТЕРАЦИЯ ЦИКЛА ЗАВЕРШЕНА за {time.time() - loop_start:.3f} с ===")

            except Exception as e:
                self.logger.exception(f"Ошибка в главном цикле: {e}")
                time.sleep(self.cycle_time)

        self.logger.info("Цикл управления завершён")

    def _process_commands(self):
        """Обработка команд из очереди (вызывается в главном цикле)."""
        try:
            while True:
                cmd, data = self.command_queue.get_nowait()
                self.logger.info(f"Обработка команды: {cmd}, данные: {data}")
                if cmd == ControllerCommand.TRIGGER_B:
                    self._trigger_and_process_B()
                elif cmd == ControllerCommand.ACTIVATE_SCENARIO:
                    scenario = data.get('scenario')
                    self._perform_scenario_switch(scenario)
                    self.scenario_active = True
                    self.logger.info(f"Сценарий {scenario} активирован через команду")
                elif cmd == ControllerCommand.SWITCH_PROJECT:
                    project = data.get('project_name')
                    if self.camera:
                        self.camera.switch_project(project)
                elif cmd == ControllerCommand.SET_OUTPUT:
                    output = data.get('output')
                    state = data.get('state')
                    if output is not None and state is not None:
                        self.manual_set_output(output, state)
        except Empty:
            pass

    def _check_hardware(self):
        try:
            owen_ip = self.config.get('owen', {}).get('ip', '192.168.1.99')
            self.logger.info(f"Проверка связи с ОВЕН ({owen_ip})...")
            self.logger.debug("Вызов owen.read_inputs()...")
            raw = self.owen.read_inputs()
            self.logger.debug("owen.read_inputs() завершён")
            if raw is not None:
                self.owen_available = True
                self.logger.info(f"✅ ОВЕН доступен — входы: {raw[:6]}")
            else:
                self.owen_available = False
                self.logger.warning(f"⚠️ ОВЕН ({owen_ip}) не ответил")
        except Exception as e:
            self.owen_available = False
            self.logger.warning(f"⚠️ Ошибка подключения к ОВЕН: {e}")

        try:
            cam_ip = self.config.get('camera', {}).get('ip', '192.168.1.36')
            self.logger.info(f"Проверка связи с камерой ({cam_ip})...")
            self.logger.debug("Вызов camera.read_status()...")
            status = self.camera.read_status()
            self.logger.debug("camera.read_status() завершён")
            if status is not None:
                self.camera_available = True
                self.logger.info(f"✅ Камера доступна — статус: {status}")
            else:
                self.camera_available = False
                self.logger.warning(f"⚠️ Камера ({cam_ip}) не ответила")
        except Exception as e:
            self.camera_available = False
            self.logger.warning(f"⚠️ Ошибка подключения к камере: {e}")

        self.hardware_available = self.owen_available and self.camera_available
        if not self.hardware_available:
            self.logger.warning("⚠️ Станция будет работать в демо-режиме без оборудования")

    def _update_inputs(self):
        self.logger.debug("Вызов owen.read_inputs()...")
        raw_inputs = self.owen.read_inputs()
        self.logger.debug("owen.read_inputs() завершён")
        if raw_inputs is None:
            self.input_read_errors += 1
            if self.input_read_errors % 10 == 1:
                self.logger.error(f"Не удалось прочитать входы (ошибок: {self.input_read_errors})")
            return False

        self.input_read_errors = 0
        now_ms = time.time() * 1000
        for i in range(6):
            current_raw = raw_inputs[i]
            if current_raw == self.di[i]:
                self.di_debounce[i] = None
                continue
            if self.di_debounce[i] is not None:
                cand_time, cand_value = self.di_debounce[i]
                if cand_value == current_raw and (now_ms - cand_time) >= self.debounce_ms:
                    self.di[i] = current_raw
                    self.di_debounce[i] = None
                    self.di_change_time[i] = now_ms / 1000.0
                    self.logger.info(f"DI{i} изменился на {current_raw} (после дребезга)")
                elif cand_value != current_raw:
                    self.di_debounce[i] = (now_ms, current_raw)
            else:
                self.di_debounce[i] = (now_ms, current_raw)
        return True

    def _process_toggle(self, now):
        if not self.auto_mode or self.web_scenario_selection:
            self.pending_scenario = None
            return

        toggle = (self.di[self.DI_TOGGLE_A], self.di[self.DI_TOGGLE_B])

        if (self.di[self.DI_TOGGLE_A] != self.prev_di[self.DI_TOGGLE_A] or
            self.di[self.DI_TOGGLE_B] != self.prev_di[self.DI_TOGGLE_B]):

            self.pending_scenario = None
            self.pending_scenario_start = 0.0
            self.pending_scenario = self._toggle_to_scenario(toggle)
            if self.pending_scenario:
                self.pending_scenario_start = now
                self.logger.debug(f"Ожидание подтверждения сценария {self.pending_scenario} (3с)")
        else:
            if self.pending_scenario:
                if (now - self.pending_scenario_start) >= self.SCENARIO_SWITCH_DELAY:
                    self.logger.info(f"Смена сценария по тумблеру: {self.pending_scenario}")
                    self._perform_scenario_switch(self.pending_scenario)
                    self.scenario_active = True
                    self.pending_scenario = None

    def _toggle_to_scenario(self, toggle):
        if toggle == (1, 0):
            return 'A'
        elif toggle == (0, 1):
            return 'B'
        elif toggle == (0, 0):
            return 'C'
        else:
            return None

    def _perform_scenario_switch(self, new_scenario):
        if not self.hardware_available or self.offline_mode:
            self.logger.warning("Оборудование недоступно или офлайн-режим — смена сценария невозможна")
            return
        self.logger.info(f"СМЕНА СЦЕНАРИЯ на {new_scenario}")
        if self.current_scenario == 'A' and self.a_active:
            self.logger.debug("Остановка непрерывного режима камеры (stop_continuous)")
            self.camera.stop_continuous()
            self.a_active = False
        self.do = [0, 0, 0, 0]
        self._apply_outputs()
        self._after_scenario_switch(new_scenario)

    def _after_scenario_switch(self, new_scenario):
        self._update_camera_ready()
        self.current_scenario = new_scenario
        self.logger.info(f"Сценарий {new_scenario} активирован")
        if new_scenario == 'C':
            self.scenario_c_state = ScenarioCState.IDLE
            self.scenario_c_data = {
                'target_sensor': None,
                'result': None,
                'state_start_time': 0.0,
                'measurement_done': False
            }
            if self.camera_ready:
                self.do[self.DO_LAMP_GREEN] = 1
        elif new_scenario == 'A':
            self.last_a_trigger = 0.0
            self.a_active = False
            self.waiting_for_ng_stop = False
            self.has_valid_measurement = False

    def _handle_camera_not_ready(self):
        if not self._camera_error_blink_started:
            self._camera_error_blink_started = True
            self.logger.warning("Камера не готова – мигание красной лампы")
            self._start_blink(green=False, red=True, frequency=1.0, duration=3.0,
                              callback=self._camera_error_steady)
        self.do[self.DO_CONVEYOR] = 0

    def _camera_error_steady(self):
        self.do[self.DO_LAMP_RED] = 1
        self._camera_error_blink_started = False
        self.logger.warning("Камера не готова – красная лампа горит постоянно")

    def _run_auto(self, now):
        if self.scenario_override:
            forced = self.scenario_override
            if forced != self.current_scenario:
                self.logger.info(f"Принудительный сценарий: {forced}")
                self._perform_scenario_switch(forced)
            self.scenario_override = None
            return

        if self.web_scenario_selection:
            target = self.web_selected_scenario
            # Не переключаем автоматически – только если уже активен какой-то сценарий,
            # и он не соответствует текущему, то переключаем (но только если scenario_active == True)
            if self.scenario_active and target != self.current_scenario:
                self.logger.info(f"Сценарий из веб изменился на {target}, переключаем")
                self._perform_scenario_switch(target)
            if self.current_scenario == 'A':
                self._run_scenario_A(now)
            elif self.current_scenario == 'B':
                self._run_scenario_B()
            elif self.current_scenario == 'C':
                self._run_scenario_C()
            return

        # Если выбор из веб выключен, используем текущий сценарий
        if self.current_scenario == 'A':
            self._run_scenario_A(now)
        elif self.current_scenario == 'B':
            self._run_scenario_B()
        elif self.current_scenario == 'C':
            self._run_scenario_C()

    # -------------------------------------------------------------------------
    # Сценарий A
    # -------------------------------------------------------------------------
    def _run_scenario_A(self, now):
        if not self.camera_ready:
            self.logger.warning("Сценарий A: камера не готова, сценарий не выполняется")
            self.do[self.DO_LAMP_RED] = 1
            return

        if not self.a_active:
            self.logger.info("Сценарий A: запуск периодических измерений (интервал 0.25 сек)")
            self.do[self.DO_LAMP_GREEN] = 1
            self.do[self.DO_CONVEYOR] = 1
            self._apply_outputs()
            self.a_active = True
            self.last_a_trigger = now
            self.waiting_for_ng_stop = False
            self.has_valid_measurement = False
            return

        if now - self.last_a_trigger >= self.scenario_a_interval:
            self.logger.debug("Сценарий A: отправка триггера")
            self.logger.debug("Вызов camera.trigger_measurement()...")
            result = self.camera.trigger_measurement(timeout=10)
            self.logger.debug("camera.trigger_measurement() завершён")
            if not self._running or self._stop_event.is_set():
                return

            raw_text = result.get('raw') if result else None
            is_valid_result = False
            result_text = None

            if raw_text is not None:
                if isinstance(raw_text, str) and 'null' in raw_text.lower():
                    is_valid_result = False
                else:
                    is_valid_result = True
                    result_text = result.get('result') if result.get('result') in ('OK', 'NG') else None
            else:
                is_valid_result = False

            if result:
                self._save_measurement_result(result)

            if is_valid_result and result_text in ('OK', 'NG'):
                if not self.has_valid_measurement:
                    self.logger.info("Сценарий A: получено первое валидное измерение")
                    self.has_valid_measurement = True
                    self.waiting_for_ng_stop = False

                if result_text == 'NG':
                    if self.waiting_for_ng_stop:
                        self.logger.info("Сценарий A: обнаружен брак (NG после OK или NG) – останов")
                        self.do[self.DO_CONVEYOR] = 0
                        self.do[self.DO_LAMP_GREEN] = 0
                        self.do[self.DO_LAMP_RED] = 1
                        self.a_active = False
                        self.current_scenario = None
                        self.scenario_active = False
                        self.waiting_for_ng_stop = False
                        self.has_valid_measurement = False
                    else:
                        self.logger.info("Сценарий A: обнаружен брак (NG) – конвейер продолжает работу")
                        self.do[self.DO_LAMP_RED] = 1
                        self.waiting_for_ng_stop = True
                elif result_text == 'OK':
                    self.logger.info("Сценарий A: OK")
                    self.do[self.DO_LAMP_RED] = 0
                    self.waiting_for_ng_stop = True
                else:
                    self.logger.warning(f"Сценарий A: неизвестный результат {result_text}")
                    self._start_blink(green=False, red=True, frequency=2.0, duration=1.5)
            else:
                if self.has_valid_measurement:
                    self.logger.info("Сценарий A: получен null/невалидный результат после валидных измерений, сброс флагов")
                    self.waiting_for_ng_stop = False
                    self.do[self.DO_LAMP_RED] = 0

            self.last_a_trigger = now

    # -------------------------------------------------------------------------
    # Сценарий B
    # -------------------------------------------------------------------------
    def _run_scenario_B(self):
        if self.di[self.DI_TOGGLE_B] == 1 and self.prev_di[self.DI_TOGGLE_B] == 0:
            self.logger.info("Сценарий B: фронт DI5, запуск измерения")
            self._start_blink(green=True, red=False, frequency=0, duration=1.0,
                              callback=self._trigger_and_process_B)

    def _trigger_and_process_B(self):
        self.logger.info("Сценарий B: измерение...")
        self.logger.debug("Вызов camera.trigger_measurement()...")
        result = self.camera.trigger_measurement(timeout=10)
        self.logger.debug("camera.trigger_measurement() завершён")
        if not self._running or self._stop_event.is_set():
            return
        if result and result.get('result') == 'OK':
            self.logger.info("Сценарий B: OK")
            self._start_blink(green=True, red=False, frequency=0, duration=2.0)
        elif result and result.get('result') == 'NG':
            self.logger.info("Сценарий B: NG")
            self._start_blink(green=False, red=True, frequency=0, duration=2.0)
        else:
            self.logger.error("Сценарий B: ошибка")
            self._start_blink(green=False, red=True, frequency=2.0, duration=1.5)
        self._save_measurement_result(result)

    # -------------------------------------------------------------------------
    # Сценарий C
    # -------------------------------------------------------------------------
    def _run_scenario_C(self):
        current_project = self.config.get('camera', {}).get('project_name', '')
        if not current_project:
            if not self._no_tool_warning_shown:
                self.logger.warning("Сценарий C: не выбран инструмент (проект камеры пуст). Работа заблокирована. Выберите инструмент на странице 'Инструменты'.")
                self._no_tool_warning_shown = True
                self._start_blink(green=False, red=True, frequency=1.0, duration=1.0)
            if self.scenario_c_state != ScenarioCState.IDLE:
                self.scenario_c_state = ScenarioCState.IDLE
                self.do[self.DO_CONVEYOR] = 0
                self.do[self.DO_LAMP_GREEN] = 0
                self.do[self.DO_LAMP_RED] = 0
            return

        if self._no_tool_warning_shown:
            self._no_tool_warning_shown = False

        now = time.time()
        if self.state_timeout > 0 and self.scenario_c_state != ScenarioCState.IDLE:
            if now - self.scenario_c_data['state_start_time'] > self.state_timeout:
                self.logger.error(f"Сценарий C: таймаут в {self.scenario_c_state.name}")
                self._scenario_c_error()
                return

        if self.scenario_c_state == ScenarioCState.IDLE:
            self.do[self.DO_LAMP_GREEN] = 1 if self.camera_ready else 0
            self.do[self.DO_LAMP_RED] = 0
            self.do[self.DO_CONVEYOR] = 0
            if self.di[self.DI_DETECT_LEFT] == 0 and self.prev_di[self.DI_DETECT_LEFT] == 1:
                if not self.camera_ready:
                    self.logger.warning("Сценарий C: камера не готова, деталь не будет обработана")
                    return
                self.logger.info("Сценарий C: деталь на входе (спад DI0), запуск")
                self.do[self.DO_LAMP_GREEN] = 0
                self.do[self.DO_CONVEYOR] = 1
                self.scenario_c_state = ScenarioCState.CONVEYOR_RUNNING_TO_CAMERA
                self.scenario_c_data['state_start_time'] = now

        elif self.scenario_c_state == ScenarioCState.CONVEYOR_RUNNING_TO_CAMERA:
            if self.di[self.DI_POS_LEFT] == 0 and self.prev_di[self.DI_POS_LEFT] == 1:
                self.logger.info("Сценарий C: деталь под камерой (спад DI1), останов")
                self.do[self.DO_CONVEYOR] = 0
                self.scenario_c_state = ScenarioCState.POSITIONED
                self.scenario_c_data['state_start_time'] = now
                self.scenario_c_data['measurement_done'] = False

        elif self.scenario_c_state == ScenarioCState.POSITIONED:
            if not self.scenario_c_data['measurement_done']:
                self.logger.info("Сценарий C: запуск измерения")
                self.logger.debug("Вызов camera.trigger_measurement()...")
                result = self.camera.trigger_measurement(timeout=10)
                self.logger.debug("camera.trigger_measurement() завершён")
                if not self._running or self._stop_event.is_set():
                    return
                if result and result.get('result') in ('OK', 'NG'):
                    self.scenario_c_data['result'] = result['result']
                    self.scenario_c_data['measurement_done'] = True
                    self._save_measurement_result(result, sensors=self.di)
                    if result['result'] == 'OK':
                        self.scenario_c_data['target_sensor'] = self.DI_EXIT
                        self.do[self.DO_LAMP_GREEN] = 1
                        self.logger.info("Сценарий C: OK – движение до DI4")
                    else:
                        self.scenario_c_data['target_sensor'] = self.DI_POS_RIGHT
                        self.do[self.DO_LAMP_RED] = 1
                        self.logger.info("Сценарий C: NG – движение до DI3")
                    self.do[self.DO_CONVEYOR] = 1
                    self.scenario_c_state = ScenarioCState.CONVEYOR_RUNNING_TO_EXIT
                    self.scenario_c_data['state_start_time'] = now
                else:
                    self.logger.error("Сценарий C: ошибка измерения")
                    self._scenario_c_error()

        elif self.scenario_c_state == ScenarioCState.CONVEYOR_RUNNING_TO_EXIT:
            target = self.scenario_c_data['target_sensor']
            if self.di[target] == 0 and self.prev_di[target] == 1:
                sensor_name = "DI3" if target == self.DI_POS_RIGHT else "DI4"
                self.logger.info(f"Сценарий C: деталь достигла {sensor_name} (спад), останов")
                self._scenario_c_finish()

    def _scenario_c_finish(self):
        self.logger.info("Сценарий C: обработка завершена")
        self.do[self.DO_CONVEYOR] = 0
        self.do[self.DO_LAMP_GREEN] = 0
        self.do[self.DO_LAMP_RED] = 0
        self.do[self.DO_EJECTOR] = 0
        self.scenario_c_state = ScenarioCState.IDLE
        self.scenario_c_data = {
            'target_sensor': None,
            'result': None,
            'state_start_time': 0.0,
            'measurement_done': False
        }

    def _scenario_c_error(self):
        self.logger.error("Сценарий C: ошибка, возврат в IDLE")
        self.do[self.DO_CONVEYOR] = 0
        self.do[self.DO_LAMP_GREEN] = 0
        self.do[self.DO_LAMP_RED] = 0
        self.do[self.DO_EJECTOR] = 0
        self._start_blink(green=False, red=True, frequency=2.0, duration=1.5,
                          callback=self._scenario_c_reset)
        self.scenario_c_state = ScenarioCState.IDLE

    def _scenario_c_reset(self):
        self.scenario_c_data = {
            'target_sensor': None,
            'result': None,
            'state_start_time': 0.0,
            'measurement_done': False
        }

    # -------------------------------------------------------------------------
    # Ручной режим
    # -------------------------------------------------------------------------
    def _run_manual(self):
        if self.di[self.DI_TOGGLE_A] == 1:
            self.do[self.DO_CONVEYOR] = 1
        else:
            self.do[self.DO_CONVEYOR] = 0

        if self.di[self.DI_TOGGLE_B] == 1 and self.prev_di[self.DI_TOGGLE_B] == 0:
            self.logger.info("Ручной режим: фронт DI5, запуск измерения")
            self._manual_trigger()
        elif self.di[self.DI_TOGGLE_B] == 0 and self.prev_di[self.DI_TOGGLE_B] == 1:
            self.logger.debug("Ручной режим: спад DI5, гашение ламп")
            self.do[self.DO_LAMP_GREEN] = 0
            self.do[self.DO_LAMP_RED] = 0

    def _manual_trigger(self):
        self.logger.info("Ручной режим: измерение...")
        self.logger.debug("Вызов camera.trigger_measurement()...")
        result = self.camera.trigger_measurement(timeout=10)
        self.logger.debug("camera.trigger_measurement() завершён")
        if not self._running or self._stop_event.is_set():
            return
        if result and result.get('result') == 'OK':
            self.logger.info("Ручной режим: OK")
            self.do[self.DO_LAMP_GREEN] = 1
            self.do[self.DO_LAMP_RED] = 0
        elif result and result.get('result') == 'NG':
            self.logger.info("Ручной режим: NG")
            self.do[self.DO_LAMP_GREEN] = 0
            self.do[self.DO_LAMP_RED] = 1
        else:
            self.logger.error("Ручной режим: ошибка измерения")
            self._start_blink(green=False, red=True, frequency=2.0, duration=1.5)
        self._save_measurement_result(result)

    # -------------------------------------------------------------------------
    # Сохранение результатов
    # -------------------------------------------------------------------------
    def _save_measurement_result(self, result, sensors=None):
        if not result:
            return
        result_text = result.get('result', 'NO_RESULT')
        raw_text = result.get('raw', None)
        image_path = self._save_image(result_text)
        with self._lock:
            self.last_result['result'] = result_text
            self.last_result['image'] = image_path
            self.last_result['time'] = datetime.now().isoformat()
            self.last_result['raw'] = raw_text
            self.last_result['project_name'] = self.config.get('camera', {}).get('project_name', '')

        try:
            db = get_database(self.config)  # передаём config, если требуется
            if sensors is None:
                sensors_dict = {
                    'd1': self.di[self.DI_DETECT_LEFT],
                    'd2': self.di[self.DI_POS_LEFT],
                    'd3': self.di[self.DI_POS_RIGHT],
                    'd4': self.di[self.DI_EXIT],
                    'tumbler_a': self.di[self.DI_TOGGLE_A],
                    'tumbler_b': self.di[self.DI_TOGGLE_B]
                }
            elif isinstance(sensors, list):
                sensors_dict = {
                    'd1': sensors[self.DI_DETECT_LEFT] if len(sensors) > self.DI_DETECT_LEFT else 0,
                    'd2': sensors[self.DI_POS_LEFT] if len(sensors) > self.DI_POS_LEFT else 0,
                    'd3': sensors[self.DI_POS_RIGHT] if len(sensors) > self.DI_POS_RIGHT else 0,
                    'd4': sensors[self.DI_EXIT] if len(sensors) > self.DI_EXIT else 0,
                    'tumbler_a': sensors[self.DI_TOGGLE_A] if len(sensors) > self.DI_TOGGLE_A else 0,
                    'tumbler_b': sensors[self.DI_TOGGLE_B] if len(sensors) > self.DI_TOGGLE_B else 0
                }
            else:
                sensors_dict = sensors
            db.add_result(
                result=result_text,
                image_path=image_path,
                scenario=self.current_scenario or 'UNKNOWN',
                project_name=self.config.get('camera', {}).get('project_name', ''),
                sensors=sensors_dict,
                raw=raw_text,
                order_number=None
            )
            self.logger.info(f"Результат сохранён в БД: {result_text} | Raw: {raw_text}")
        except Exception as e:
            self.logger.exception(f"Ошибка сохранения в БД: {e}")

    # -------------------------------------------------------------------------
    # Мигание ламп
    # -------------------------------------------------------------------------
    def _start_blink(self, green, red, frequency, duration, callback=None):
        with self._lock:
            self.blink_active = True
            self.blink_start = time.time()
            self.blink_duration = duration
            self.blink_green = green
            self.blink_red = red
            self.blink_period = 1.0 / frequency if frequency > 0 else 0
            self.blink_callback = callback
            self.logger.debug(f"Мигание: g={green}, r={red}, {frequency}Гц, {duration}с")

    def _update_blink(self, now):
        if not self.blink_active:
            return
        elapsed = now - self.blink_start
        if elapsed >= self.blink_duration:
            self.blink_active = False
            self.do[self.DO_LAMP_GREEN] = 0
            self.do[self.DO_LAMP_RED] = 0
            if self.blink_callback:
                self.blink_callback()
            return
        if self.blink_period == 0:
            if self.blink_green:
                self.do[self.DO_LAMP_GREEN] = 1
            if self.blink_red:
                self.do[self.DO_LAMP_RED] = 1
        else:
            half = self.blink_period / 2
            cycle = elapsed % self.blink_period
            state = 1 if cycle < half else 0
            if self.blink_green:
                self.do[self.DO_LAMP_GREEN] = state
            if self.blink_red:
                self.do[self.DO_LAMP_RED] = state

    # -------------------------------------------------------------------------
    # Состояние веб-выбора сценария (сохранение/загрузка)
    # -------------------------------------------------------------------------
    def _get_state_file_path(self):
        state_dir = self.config.get('paths', {}).get('data', 'data')
        os.makedirs(state_dir, exist_ok=True)
        return os.path.join(state_dir, 'web_scenario_state.json')

    def _save_web_scenario_state(self):
        import json
        state = {
            'web_scenario_selection': self.web_scenario_selection,
            'web_selected_scenario': self.web_selected_scenario
        }
        try:
            with open(self._get_state_file_path(), 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
            self.logger.debug(f"Состояние веб-сценария сохранено: {state}")
        except Exception as e:
            self.logger.error(f"Не удалось сохранить состояние веб-сценария: {e}")

    def _load_web_scenario_state(self):
        import json
        state_file = self._get_state_file_path()
        if not os.path.exists(state_file):
            self.logger.debug("Файл состояния веб-сценария не найден, используются значения по умолчанию")
            return
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            self.web_scenario_selection = state.get('web_scenario_selection', False)
            self.web_selected_scenario = state.get('web_selected_scenario', 'C')
            self.logger.info(f"Состояние веб-сценария загружено: selection={self.web_scenario_selection}, scenario={self.web_selected_scenario}")
        except Exception as e:
            self.logger.error(f"Не удалось загрузить состояние веб-сценария: {e}")

    def _load_last_result_from_db(self):
        try:
            last = self.db.get_last_result()
            if last:
                self.last_result = {
                    'result': last.get('result'),
                    'image': last.get('image_path'),
                    'time': last.get('timestamp'),
                    'raw': last.get('raw'),
                    'project_name': last.get('project_name', '')
                }
                self.logger.info(f"Loaded last result from DB: {self.last_result['result']} at {self.last_result['time']}")
            else:
                self.logger.info("No previous results in database")
        except Exception as e:
            self.logger.exception(f"Failed to load last result from DB: {e}")