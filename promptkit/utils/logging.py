"""
Logging utilities for PromptKit.

This module provides a unified logging configuration for the library,
ensuring consistent log formatting and levels across all components.
"""

import logging
import sys
from typing import Optional


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)
        level: Log level override (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    if level:
        logger.setLevel(getattr(logging, level.upper()))
    elif not logger.level:
        logger.setLevel(logging.INFO)

    return logger


def configure_logging(level: str = "INFO", format_string: Optional[str] = None) -> None:
    """
    Configure global logging settings for PromptKit.

    Args:
        level: Global log level (DEBUG, INFO, WARNING, ERROR)
        format_string: Custom log format string
    """
    log_format = format_string or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        stream=sys.stdout,
        force=True,
    )
