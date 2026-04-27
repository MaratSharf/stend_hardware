# hardware/hikrobot.py
import time
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusIOException, ConnectionException
from utils.logger import setup_logger

# Словарь соответствия коротких имён полным названиям проектов камеры
PROJECT_NAME_MAP = {
    '3.2': '3.2CodeRecognition',
    '3.4': '3.4ColorRecognition',
    '3.7': '3.7OCR',
    '3.1': '3.1Classification',
    '1.1': '1.1Measurement',
    '1.2': '1.2Diameter',
    '2.1': '2.1Counting',
    '2.2': '2.2ColorCount',
}

class HikrobotCamera:
    """
    Класс для работы с камерой Hikrobot через Modbus TCP.
    Автоматическое переподключение с экспоненциальной задержкой.
    Поддержка прерывания длительных операций через stop_event.
    """
    def __init__(self, ip, port=502, unit=1,
                 control_offset=0, status_offset=1,
                 result_offset=2, command_offset=500,
                 byte_order='little', command_terminator='',
                 verify_switch=False,
                 log_max_bytes=None, log_backup_count=None):
        self.ip = ip
        self.port = port
        self.unit = unit
        self.control_offset = control_offset
        self.status_offset = status_offset
        self.result_offset = result_offset
        self.command_offset = command_offset
        self.byte_order = byte_order
        self.command_terminator = command_terminator
        self.verify_switch = verify_switch
        self.timeout = 3.0
        self.client = None
        self.reconnect_delay = 1.0
        self.max_reconnect_delay = 30.0
        self.last_reconnect_attempt = 0
        self.logger = setup_logger('hikrobot',
                                   max_bytes=log_max_bytes,
                                   backup_count=log_backup_count)
        self.logger.info(f"Инициализация: IP={ip}, порт={port}, unit={unit}, verify_switch={verify_switch}")
        self._last_status = None

    def _create_client(self):
        return ModbusTcpClient(self.ip, port=self.port, timeout=self.timeout)

    def connect(self):
        self.logger.info("Попытка подключения...")
        try:
            if self.client:
                self.client.close()
                time.sleep(0.5)
            self.client = self._create_client()
            result = self.client.connect()
            if result:
                self.logger.info("Подключение успешно")
                self.reconnect_delay = 1.0
            else:
                self.logger.error("Ошибка подключения")
            return result
        except Exception as e:
            self.logger.error(f"Исключение при подключении: {e}")
            return False

    def disconnect(self):
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.logger.info("Соединение закрыто")

    def _reconnect(self):
        now = time.time()
        if now - self.last_reconnect_attempt < self.reconnect_delay:
            return False
        self.last_reconnect_attempt = now
        self.logger.warning(f"Попытка переподключения (задержка {self.reconnect_delay:.1f}с)...")
        success = self.connect()
        if not success:
            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
        return success

    def _ensure_connection(self):
        if self.client is None:
            return self._reconnect()
        return True

    def read_status(self, stop_event=None):
        """Чтение статуса камеры (9 флагов)."""
        if not self._ensure_connection():
            return None
        try:
            resp = self.client.read_holding_registers(self.status_offset, count=1)
            if resp.isError():
                self.logger.error(f"Ошибка чтения статуса: {resp}")
                return None
            val = resp.registers[0]
            status = {
                'trigger_ready': bool(val & 0x0001),
                'trigger_ack': bool(val & 0x0002),
                'acquiring': bool(val & 0x0004),
                'decoding': bool(val & 0x0008),
                'results_available': bool(val & 0x0100),
                'results_timeout': bool(val & 0x0200),
                'command_success': bool(val & 0x0400),
                'command_failed': bool(val & 0x0800),
                'general_fault': bool(val & 0x8000),
            }
            if status != self._last_status:
                self.logger.debug(f"Статус прочитан: {status}")
                self._last_status = status.copy()
            return status
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError,
                ModbusIOException, ConnectionException) as e:
            self.logger.warning(f"Ошибка связи при чтении статуса: {e}")
            self._reconnect()
            return None
        except Exception as e:
            self.logger.exception("Исключение при чтении статуса")
            return None

    def write_ctrl(self, value, stop_event=None):
        """Запись в управляющий регистр."""
        if not self._ensure_connection():
            return False
        try:
            self.logger.debug(f"Запись в управляющий регистр: {value} (0x{value:04X})")
            resp = self.client.write_register(self.control_offset, value)
            if resp.isError():
                self.logger.error(f"Ошибка записи: {resp}")
                return False
            return True
        except (ConnectionResetError, BrokenPipeError, OSError,
                ModbusIOException, ConnectionException) as e:
            self.logger.warning(f"Ошибка связи при записи: {e}")
            self._reconnect()
            return False
        except Exception as e:
            self.logger.exception("Исключение при записи")
            return False

    def _string_to_registers(self, text):
        data = text.encode('ascii')
        length = len(data)
        regs = []
        if self.byte_order == 'little':
            for i in range(0, length, 2):
                if i + 1 < length:
                    word = (data[i+1] << 8) | data[i]
                else:
                    word = data[i]
                regs.append(word)
        else:
            for i in range(0, length, 2):
                if i + 1 < length:
                    word = (data[i] << 8) | data[i+1]
                else:
                    word = data[i] << 8
                regs.append(word)
        return regs

    def _write_register(self, reg, value, stop_event=None):
        if not self._ensure_connection():
            return False
        try:
            self.logger.debug(f"Запись регистра {reg} = {value}")
            resp = self.client.write_register(reg, value)
            if resp.isError():
                self.logger.error(f"Ошибка записи регистра {reg}: {resp}")
                return False
            return True
        except (ConnectionResetError, BrokenPipeError, OSError,
                ModbusIOException, ConnectionException) as e:
            self.logger.warning(f"Ошибка связи при записи регистра: {e}")
            self._reconnect()
            return False

    def _read_register(self, reg, stop_event=None):
        if not self._ensure_connection():
            return None
        try:
            resp = self.client.read_holding_registers(reg, count=1)
            if resp.isError():
                self.logger.error(f"Ошибка чтения регистра {reg}: {resp}")
                return None
            return resp.registers[0]
        except (ConnectionResetError, BrokenPipeError, OSError,
                ModbusIOException, ConnectionException) as e:
            self.logger.warning(f"Ошибка связи при чтении регистра: {e}")
            self._reconnect()
            return None

    def _send_command(self, command_string, timeout=5, stop_event=None):
        """Отправка команды (например, 'switch project', 'start', 'stop')."""
        if not self._ensure_connection():
            return False
        cmd = command_string + self.command_terminator
        self.logger.info(f"Отправка команды: {repr(cmd)}")

        if not self.write_ctrl(0x8000, stop_event=stop_event):
            return False
        time.sleep(0.1)

        length = len(cmd)
        if not self._write_register(self.command_offset, length, stop_event=stop_event):
            return False

        regs = self._string_to_registers(cmd)
        if regs:
            try:
                resp = self.client.write_registers(self.command_offset + 1, regs)
                if resp.isError():
                    self.logger.error(f"Ошибка записи команды: {resp}")
                    return False
            except Exception as e:
                self.logger.exception("Исключение при записи команды")
                return False

        control = self._read_register(self.control_offset, stop_event=stop_event)
        if control is None:
            return False
        control |= 0x0100
        if not self.write_ctrl(control, stop_event=stop_event):
            return False

        start = time.time()
        success = False
        while time.time() - start < timeout:
            if stop_event and stop_event.is_set():
                self.logger.info("Прерывание ожидания команды по stop_event")
                break
            time.sleep(0.1)
            status = self.read_status(stop_event=stop_event)
            if not status:
                continue
            if status.get('command_success'):
                self.logger.info("Команда выполнена успешно")
                success = True
                break
            if status.get('command_failed'):
                self.logger.error("Команда завершилась ошибкой")
                break
        else:
            self.logger.error("Таймаут ожидания выполнения команды")

        control &= ~0x0100
        self.write_ctrl(control, stop_event=stop_event)
        return success

    def get_current_project(self, timeout=5, stop_event=None):
        if not self._ensure_connection():
            return None
        if not self._send_command("getparam ProjectName", timeout, stop_event=stop_event):
            self.logger.warning("Не удалось выполнить getparam ProjectName")
            return None
        resp = self.client.read_holding_registers(self.result_offset, count=50)
        if resp.isError():
            self.logger.error("Ошибка чтения результата getparam")
            return None
        parsed = self._parse_results(resp.registers)
        if parsed and parsed.get('raw'):
            raw = parsed['raw'].strip()
            if ':' in raw:
                project = raw.split(':', 1)[1].strip()
                self.logger.debug(f"Текущий проект: {project}")
                return project
            else:
                self.logger.warning(f"Неожиданный формат ответа: {raw}")
                return raw
        return None

    def switch_project(self, project_name, timeout=5, stop_event=None):
        resolved_name = PROJECT_NAME_MAP.get(project_name, project_name)
        self.logger.info(f"Переключение проекта: {resolved_name}")

        if not self._send_command(f"switch {resolved_name}", timeout, stop_event=stop_event):
            self.logger.error(f"Ошибка выполнения switch {resolved_name}")
            return False

        if not self.verify_switch:
            self.logger.info(f"Проект предположительно переключён на {resolved_name} (верификация отключена)")
            return True

        current = self.get_current_project(timeout=3, stop_event=stop_event)
        if current is None:
            self.logger.warning("Не удалось подтвердить переключение проекта (getparam не работает)")
            return True

        if current != resolved_name:
            self.logger.error(f"Проект не сменился! Ожидалось '{resolved_name}', получено '{current}'")
            return False

        self.logger.info(f"Проект успешно переключён на {current}")
        return True

    def start_continuous(self, timeout=5, stop_event=None):
        return self._send_command("start", timeout, stop_event=stop_event)

    def stop_continuous(self, timeout=5, stop_event=None):
        return self._send_command("stop", timeout, stop_event=stop_event)

    def trigger_measurement(self, timeout=10, stop_event=None):
        """
        Выполняет одиночное измерение.
        Поддерживает прерывание через stop_event.
        """
        if not self._ensure_connection():
            return None
        self.logger.info("Запуск цикла измерения")

        # Сброс состояния
        status = self.read_status(stop_event=stop_event)
        if status:
            self.write_ctrl(0x8000, stop_event=stop_event)
            time.sleep(0.2)
            self.write_ctrl(5, stop_event=stop_event)
            time.sleep(0.2)

        # Включение Trigger Enable
        if not self.write_ctrl(1, stop_event=stop_event):
            self.logger.error("Ошибка включения Trigger Enable")
            return None
        time.sleep(0.1)

        # Ожидание Trigger Ready
        start = time.time()
        while time.time() - start < timeout:
            if stop_event and stop_event.is_set():
                self.logger.info("Прерывание ожидания Trigger Ready")
                self.write_ctrl(5, stop_event=stop_event)
                return None
            status = self.read_status(stop_event=stop_event)
            if status and status.get('trigger_ready'):
                self.logger.info("Trigger Ready получен")
                break
            time.sleep(0.05)
        else:
            self.logger.error("Таймаут ожидания Trigger Ready")
            self.write_ctrl(5, stop_event=stop_event)
            return None

        # Отправка триггера
        if not self.write_ctrl(3, stop_event=stop_event):
            self.logger.error("Ошибка отправки триггера")
            return None

        # Ожидание результата
        start = time.time()
        while time.time() - start < timeout:
            if stop_event and stop_event.is_set():
                self.logger.info("Прерывание ожидания результата")
                self.write_ctrl(5, stop_event=stop_event)
                return None
            status = self.read_status(stop_event=stop_event)
            if not status:
                time.sleep(0.1)
                continue
            if status.get('results_available'):
                self.logger.info("Результат готов")
                break
            if status.get('results_timeout'):
                self.logger.warning("Таймаут результата")
                self.write_ctrl(5, stop_event=stop_event)
                return None
            time.sleep(0.05)
        else:
            self.logger.error("Превышено время ожидания результата")
            self.write_ctrl(5, stop_event=stop_event)
            return None

        # Чтение результата
        resp = self.client.read_holding_registers(self.result_offset, count=50)
        if resp.isError():
            self.logger.error(f"Ошибка чтения результата: {resp}")
            self.write_ctrl(5, stop_event=stop_event)
            return None

        self.write_ctrl(5, stop_event=stop_event)
        parsed = self._parse_results(resp.registers)
        if parsed:
            self.logger.info(f"✅ Результат: {parsed.get('result')} | Raw: {parsed.get('raw')}")
        else:
            self.logger.warning("Не удалось распарсить результат")
        return parsed

    def _parse_results(self, registers):
        if not registers:
            return None
        data_len = registers[0]
        data_bytes = b''.join(r.to_bytes(2, 'little') for r in registers[1:])
        if data_len > 0:
            data_bytes = data_bytes[:data_len]
        try:
            text = data_bytes.decode('ascii', errors='ignore').strip()
        except:
            text = None
        result = None
        if text:
            if 'OK' in text.upper():
                result = 'OK'
            elif 'NG' in text.upper():
                result = 'NG'
        return {'raw': text, 'result': result, 'bytes': data_bytes.hex()}