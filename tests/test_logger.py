"""Unit tests for simple console logger."""

import logging
from aml_copilot.logger import get_logger


def test_get_logger_basic():
    """Verify logger creation with default level."""
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_module"
    assert logger.level == logging.INFO
    assert len(logger.handlers) == 1


def test_get_logger_custom_level():
    """Verify custom log level override."""
    logger = get_logger("test_debug_module", level="DEBUG")
    assert logger.level == logging.DEBUG


def test_get_logger_no_duplicate_handlers():
    """Verify multiple calls do not attach duplicate handlers."""
    logger1 = get_logger("test_singleton_logger")
    handler_count_1 = len(logger1.handlers)
    logger2 = get_logger("test_singleton_logger")
    assert logger1 is logger2
    assert len(logger2.handlers) == handler_count_1


def test_logger_output_capture(caplog):
    """Verify logger output handling."""
    logger = get_logger("test_capture_logger", level="INFO")
    with caplog.at_level(logging.INFO):
        logger.info("M1 foundation logging test message")
    assert "M1 foundation logging test message" in caplog.text
