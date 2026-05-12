"""
Centralised logging setup.

Provides a `get_logger(name)` helper that returns a consistently
formatted logger.  Import and use instead of bare `print()` calls.

Usage:
    from utils.logger import get_logger
    log = get_logger(__name__)
    log.info("Ingesting %d chunks", len(chunks))
"""

import logging
import sys
from functools import lru_cache

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"


def _build_handler() -> logging.StreamHandler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FMT))
    return handler


@lru_cache(maxsize=None)
def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return (and cache) a named logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(_build_handler())
    logger.setLevel(level)
    logger.propagate = False
    return logger
