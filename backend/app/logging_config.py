"""Structured logging configuration for NEOMON."""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from app.config import settings

SENSITIVE_PATTERNS = [
    re.compile(r'(["\']?(?:password|token|secret|access_token|refresh_token|api_key|authorization)["\']?\s*[:=]\s*["\'])([^"\']+)(["\'])', re.IGNORECASE),
    re.compile(r'(Bearer\s+)([A-Za-z0-9_\-\.]+)', re.IGNORECASE),
]


def mask_sensitive_data(message: str) -> str:
    """Mask sensitive keys in strings to prevent credential leaks."""
    if not isinstance(message, str):
        return message
    for pattern in SENSITIVE_PATTERNS:
        message = pattern.sub(r'\1***REDACTED***\3' if '\\3' in pattern.pattern else r'\1***REDACTED***', message)
    return message


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": mask_sensitive_data(record.getMessage()),
            "environment": settings.environment,
            "service": settings.app_name,
        }

        # Include request ID if present
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id

        # Include exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


class StandardMaskingFormatter(logging.Formatter):
    """Formats log records for standard console output with sensitive masking."""

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        orig = super().format(record)
        return mask_sensitive_data(orig)


def setup_logging() -> None:
    """Configures application-wide logging based on environment."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(log_level)

    # Clear existing handlers
    for handler in list(root.handlers):
        root.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    if settings.log_format.lower() == "json" or settings.environment == "production":
        console_handler.setFormatter(StructuredJsonFormatter())
    else:
        fmt = "%(asctime)s [%(levelname)s] %(name)s (req_id=%(request_id)s): %(message)s"
        console_handler.setFormatter(StandardMaskingFormatter(fmt))

    root.addHandler(console_handler)

    # Silence overly verbose external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
