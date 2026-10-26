"""
Logging configuration.

Centralises log formatting so every module uses the same timestamped format.
Call configure_logging() once at application startup (in main.py) before any
other module emits log messages.
"""

import logging

from app.core.config import settings


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
