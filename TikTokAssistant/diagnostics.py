"""Bounded local crash diagnostics, with no automatic upload or telemetry."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import sys

from app_paths import user_data_dir


_installed = False


def install_crash_logging() -> None:
    global _installed
    if _installed:
        return
    location = user_data_dir() / 'logs'
    location.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(location / 'crash.log', maxBytes=2_000_000,
                                  backupCount=2, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    root = logging.getLogger('ven0m')
    root.setLevel(logging.WARNING)
    root.addHandler(handler)
    previous = sys.excepthook

    def handler_for_exception(exc_type, exc, tb):
        root.error('Uncaught application exception', exc_info=(exc_type, exc, tb))
        if previous is not None:
            previous(exc_type, exc, tb)

    sys.excepthook = handler_for_exception
    _installed = True
