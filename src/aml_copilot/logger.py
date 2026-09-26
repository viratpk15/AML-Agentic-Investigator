"""Simple console logging utility for AML Investigation Copilot."""

import logging
import sys
from typing import Optional


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Get or configure a console logger.

    Args:
        name: Name of the logger, typically __name__ of the module.
        level: Optional log level string (e.g., 'DEBUG', 'INFO'). If not provided,
               falls back to application settings.

    Returns:
        Standard Python Logger instance with a StreamHandler attached.
    """
    logger = logging.getLogger(name)

    if level is None:
        from .config import get_settings
        level = get_settings().log_level

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logger.setLevel(numeric_level)

    # Avoid duplicate handlers if get_logger is called multiple times for same logger
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
