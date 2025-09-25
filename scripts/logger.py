# scripts/logger.py

import logging, os
from logging.handlers import RotatingFileHandler

LOG_DIR = "/content/logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "sd_colab.log")

logger = logging.getLogger("sd-colab")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(LOG_FILE, maxBytes=2*1024*1024, backupCount=3)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)

def log_info(msg): logger.info(msg)
def log_error(msg): logger.error(msg)
def log_debug(msg): logger.debug(msg)

__all__ = ["log_info", "log_error", "log_debug", "LOG_FILE"]

def get_last_logs(n=50):
    """Возвращает последние n строк из файла лога."""
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return lines[-n:]
    except FileNotFoundError:
        return ["<no log file>"]
