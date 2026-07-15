from __future__ import annotations

import logging

from fiber.platform.logger import get_logger


def test_get_logger_returns_logger_with_correct_level() -> None:
    logger = get_logger("fiber.test_x")
    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.INFO


def test_get_logger_no_duplicate_handlers_on_repeat_calls() -> None:
    get_logger("fiber.test_y")
    get_logger("fiber.test_y")
    logger = logging.getLogger("fiber.test_y")
    assert len(logger.handlers) == 1


def test_get_logger_custom_level() -> None:
    logger = get_logger("fiber.test_z", level="DEBUG")
    assert logger.level == logging.DEBUG
