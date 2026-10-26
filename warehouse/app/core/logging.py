import logging
import sys
from contextvars import ContextVar

from app.core.config import settings

# Context variable for request correlation ID
correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id_ctx", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id_ctx", default=None)


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = correlation_id_ctx.get() or "-"
        record.user_id = user_id_ctx.get() or "-"
        return True


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("sln_warehouse")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Avoid duplicate handlers if already initialized
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

        if settings.is_production:
            # Production: structured format
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", '
                '"request_id": "%(request_id)s", "user_id": "%(user_id)s", "message": "%(message)s"}'
            )
        else:
            # Development: readable color-coded format
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [req:%(request_id)s] [%(name)s]: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        handler.setFormatter(formatter)
        handler.addFilter(CorrelationIdFilter())
        logger.addHandler(handler)

    # Configure root logger with same level and filter
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_handler = logging.StreamHandler(sys.stdout)
        root_handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] [req:%(request_id)s]: %(message)s")
        )
        root_handler.addFilter(CorrelationIdFilter())
        root_logger.addHandler(root_handler)
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    return logger


logger = setup_logging()
