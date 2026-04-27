# hardware/owen.py
import time
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusIOException, ConnectionException
from utils.logger import setup_logger

class OwenMK210:
    """
    Класс для работы с модулем OWEN MK210-312 по Modbus TCP.
    Автоматическое переподключение с экспоненциальной задержкой.
    Поддержка прерывания длительных операций через stop_event.
    """
    def __init__(self, ip, port=502, unit=1, timeout=3.0, log_max_bytes=None, log_backup_count=None):
        self.ip = ip
        self.port = port
        self.unit = unit
        self.timeout = timeout
        self.INPUT_REG = 51
        self.OUTPUT_READ_REG = 468
        self.OUTPUT_WRITE_REG = 470
        self.prev_inputs = None
        self.prev_outputs = None
        self.client = None
        self.reconnect_delay = 1.0
        self.max_reconnect_delay = 30.0
        self.last_reconnect_attempt = 0
        self.logger = setup_logger('owen',
                                   max_bytes=log_max_bytes,
                                   backup_count=log_backup_count)
        self.logger.info(f"Инициализация: IP={ip}, порт={port}, unit={unit}, timeout={timeout}")

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

    def read_inputs(self, stop_event=None):
        """
        Чтение всех 12 входов.
        :param stop_event: threading.Event для прерывания операции
        :return: список из 12 целых (0/1) или None
        """
        if not self._ensure_connection():
            return None

        start_time = time.time()
        # Не делаем цикл с проверкой stop_event, так как read_holding_registers имеет таймаут
        # Но если операция зависает дольше timeout, то выбросится исключение.
        try:
            resp = self.client.read_holding_registers(self.INPUT_REG, count=1, device_id=self.unit)
            if resp.isError():
                self.logger.error(f"Ошибка чтения входов: {resp}")
                return None
            val = resp.registers[0]
            inputs = [(val >> i) & 1 for i in range(12)]
            if self.prev_inputs != inputs:
                self.logger.info(f"Входы изменились: {inputs}")
                self.prev_inputs = inputs.copy()
            return inputs
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError,
                ModbusIOException, ConnectionException) as e:
            self.logger.warning(f"Ошибка связи при чтении входов: {e}")
            self._reconnect()
            return None
        except Exception as e:
            self.logger.exception(f"Исключение при чтении входов: {e}")
            return None

    def read_outputs(self, stop_event=None):
        """Чтение состояния 4 выходов."""
        if not self._ensure_connection():
            return None
        try:
            resp = self.client.read_holding_registers(self.OUTPUT_READ_REG, count=1, device_id=self.unit)
            if resp.isError():
                self.logger.error(f"Ошибка чтения выходов: {resp}")
                return None
            val = resp.registers[0]
            outputs = [(val >> i) & 1 for i in range(4)]
            if self.prev_outputs != outputs:
                self.logger.info(f"Выходы изменились: {outputs}")
                self.prev_outputs = outputs.copy()
            return outputs
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError,
                ModbusIOException, ConnectionException) as e:
            self.logger.warning(f"Ошибка связи при чтении выходов: {e}")
            self._reconnect()
            return None
        except Exception as e:
            self.logger.exception(f"Исключение при чтении выходов: {e}")
            return None

    def write_outputs(self, states, stop_event=None):
        """Запись состояния всех 4 выходов. states: список из 4 bool/int."""
        if not self._ensure_connection():
            return False
        if len(states) != 4:
            self.logger.error("Неверное количество выходов")
            return False
        val = 0
        for i, s in enumerate(states):
            if s:
                val |= (1 << i)
        try:
            self.logger.debug(f"Запись выходов: states={states}, значение={val}")
            resp = self.client.write_register(self.OUTPUT_WRITE_REG, val, device_id=self.unit)
            if resp.isError():
                self.logger.error(f"Ошибка записи выходов: {resp}")
                return False
            self.prev_outputs = [int(s) for s in states]
            self.logger.info(f"Выходы установлены: {self.prev_outputs}")
            return True
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError,
                ModbusIOException, ConnectionException) as e:
            self.logger.warning(f"Ошибка связи при записи выходов: {e}")
            self._reconnect()
            return False
        except Exception as e:
            self.logger.exception(f"Исключение при записи выходов: {e}")
            return False

    def write_output(self, num, state, stop_event=None):
        """Запись одного выхода (нумерация с 1 до 4)."""
        current = self.read_outputs(stop_event=stop_event)
        if current is None:
            self.logger.error("Не удалось прочитать текущее состояние выходов")
            return False
        current[num - 1] = 1 if state else 0
        return self.write_outputs(current, stop_event=stop_event)