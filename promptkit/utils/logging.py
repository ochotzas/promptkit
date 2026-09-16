from __future__ import annotations

import logging
import sys

DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def get_logger(name: str, level: str | None = None) -> logging.Logger:
    logger = logging.getLogger(name)

    if level:
        logger.setLevel(getattr(logging, level.upper()))

    return logger


def configure_logging(level: str = "INFO", format_string: str | None = None) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string or DEFAULT_FORMAT,
        stream=sys.stdout,
        force=True,
    )
