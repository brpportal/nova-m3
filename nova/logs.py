"""Logging for NOVA. Logs go to ~/.nova/logs/nova.log and the terminal.

SECURITY: nothing in this module may ever log cookies, tokens, passwords, or
page HTML (which can embed session identifiers). Callers log URLs, counts,
states and errors only.
"""
from __future__ import annotations

import logging
import os

from .config import nova_home

_LOGGER_NAME = "nova"


def get_logger(verbose: bool = False) -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S")
    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    logger.addHandler(stream)
    try:
        file_handler = logging.FileHandler(
            os.path.join(nova_home(), "logs", "nova.log"), encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    except OSError:
        pass
    logger.propagate = False
    return logger
