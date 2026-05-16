import logging
import sys

import structlog

from app.core.config import get_settings

_SENSITIVE_KEYS = {"password", "secret", "api_key", "api_secret", "token", "jwt", "master_key"}


def _redact(_, __, event_dict):
    for k in list(event_dict.keys()):
        if any(s in k.lower() for s in _SENSITIVE_KEYS):
            event_dict[k] = "***REDACTED***"
    return event_dict


def configure_logging() -> None:
    s = get_settings()
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=s.log_level)

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _redact,
    ]
    if s.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,  # type: ignore[arg-type]
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, s.log_level)),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None):
    return structlog.get_logger(name)
