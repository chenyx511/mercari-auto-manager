import logging
import os
from src.utils.config import get

LOG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')


def setup_logger(name: str = "mercari") -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level = getattr(logging, get('logging.level', 'INFO'))
    logger.setLevel(level)

    log_file = get('logging.file', os.path.join(LOG_DIR, 'mercari_tool.log'))
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
