"""
Structured Logging Configuration

Configures structlog for consistent, JSON-formatted logging across the application.
In development, uses colored console output. In production, uses JSON output.

Environment variables:
    LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR). Default: INFO
    LOG_FORMAT: Output format ("json" or "console"). Default: "console"
    APP_ENV: Application environment. If "production", forces JSON format.
"""

import os
import sys
import logging

import structlog


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "console")
LOG_FILE = os.getenv("LOG_FILE", "")  # Optional: /var/log/governexplus/app.log
APP_ENV = os.getenv("APP_ENV", "development")

# Force JSON in production
if APP_ENV == "production":
    LOG_FORMAT = "json"


def setup_logging() -> None:
    """Configure structlog and stdlib logging for the entire application.

    Call once at application startup (before any logging happens).
    After this, use `structlog.get_logger()` throughout the codebase.
    stdlib loggers (uvicorn, sqlalchemy, etc.) are also routed through structlog.
    """

    # Shared processors used by both structlog and stdlib integration
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if LOG_FORMAT == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib root logger so libraries (uvicorn, sqlalchemy, etc.)
    # also produce structured output
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Add a handler that formats via structlog
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    ))
    root_logger.addHandler(handler)

    # Optional file handler for log aggregation (e.g., Filebeat, Fluentd)
    if LOG_FILE:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=50 * 1024 * 1024, backupCount=5,  # 50MB, 5 files
        )
        json_renderer = structlog.processors.JSONRenderer()
        file_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                json_renderer,
            ],
            foreign_pre_chain=shared_processors,
        ))
        root_logger.addHandler(file_handler)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str | None = None, **initial_ctx) -> structlog.stdlib.BoundLogger:
    """Get a structured logger.

    Args:
        name: Logger name (typically __name__)
        **initial_ctx: Initial context key-value pairs bound to this logger

    Returns:
        A structlog BoundLogger instance

    Usage:
        from core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("user.login", user_id="JSMITH", tenant="acme")
    """
    log = structlog.get_logger(name)
    if initial_ctx:
        log = log.bind(**initial_ctx)
    return log
