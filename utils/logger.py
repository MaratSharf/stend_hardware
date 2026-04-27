# utils/logger.py
import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger(name, log_dir='data/logs', level=logging.DEBUG, max_bytes=None, backup_count=None):
    """
    Настройка логгера с ротацией по размеру файла.
    
    :param name: имя логгера (обычно __name__)
    :param log_dir: директория для сохранения логов
    :param level: уровень логирования (для файлового обработчика)
    :param max_bytes: максимальный размер файла в байтах (по умолчанию 10 МБ)
    :param backup_count: количество сохраняемых файлов при ротации
    :return: настроенный логгер
    """
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Параметры по умолчанию
    if max_bytes is None:
        max_bytes = 10 * 1024 * 1024  # 10 МБ
    if backup_count is None:
        backup_count = 5

    # Файловый обработчик (ротация по размеру)
    log_file = os.path.join(log_dir, f'{name}.log')
    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # Консольный обработчик – только INFO и выше
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Создаём логгер
    logger = logging.getLogger(name)
    logger.setLevel(level)
    # Отключаем проброс к корневому логгеру (чтобы избежать дублирования в консоль)
    logger.propagate = False

    # Удаляем старые обработчики, чтобы избежать дублирования при повторном вызове
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger