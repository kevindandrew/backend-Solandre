"""
Sistema de logging configurado para la aplicación.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Crear directorio de logs si no existe
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Configurar formato de logs
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Crear logger principal
logger = logging.getLogger("solandre")
logger.setLevel(logging.INFO)

# Handler para archivo (rotativo - máximo 10MB, mantener 10 archivos)
file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "app.log"),
    maxBytes=10485760,  # 10MB
    backupCount=10,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

# Handler para archivo de errores (solo errores y críticos)
error_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "error.log"),
    maxBytes=10485760,  # 10MB
    backupCount=10,
    encoding='utf-8'
)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

# Handler para consola (solo en desarrollo)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(
    '%(levelname)s: %(message)s'
))

# Agregar handlers
logger.addHandler(file_handler)
logger.addHandler(error_handler)
logger.addHandler(console_handler)


def log_request(method: str, path: str, status_code: int, duration: float):
    """Log de requests HTTP"""
    logger.info(f"{method} {path} - {status_code} ({duration:.2f}ms)")


def log_error(error: Exception, context: str = ""):
    """Log de errores con contexto"""
    logger.error(f"Error en {context}: {str(error)}", exc_info=True)


def log_info(message: str):
    """Log de información general"""
    logger.info(message)


def log_warning(message: str):
    """Log de advertencias"""
    logger.warning(message)


def log_debug(message: str):
    """Log de debug (solo en desarrollo)"""
    logger.debug(message)
