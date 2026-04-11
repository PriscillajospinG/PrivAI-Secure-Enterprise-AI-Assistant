import logging
import os
from logging.handlers import RotatingFileHandler

from app.core.config import settings


def configure_logging() -> None:
    os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(settings.LOG_FILE, maxBytes=2_000_000, backupCount=3)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)

    # Suppress third-party telemetry noise that does not affect runtime behavior.
    logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
