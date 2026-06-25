"""Lightweight structured logging shared across the agent."""

from __future__ import annotations

import logging
import os
import sys


def get_logger(name: str, level: str = "INFO", log_dir: str = "logs") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:  # already configured
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    fmt = logging.Formatter(
        "%(asctime)s.%(msecs)03d | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    try:
        os.makedirs(log_dir, exist_ok=True)
        fileh = logging.FileHandler(os.path.join(log_dir, "agent.log"))
        fileh.setFormatter(fmt)
        logger.addHandler(fileh)
    except OSError:
        pass  # file logging is best-effort

    logger.propagate = False
    return logger
