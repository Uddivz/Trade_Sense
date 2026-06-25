"""
TradeSense — Centralised Logging Configuration
===============================================
Call ``configure_logging()`` exactly once at application startup (in ``main.py``).
After that, every module in the codebase can get its own named logger with::

    import logging
    logger = logging.getLogger(__name__)

Log levels respect the ``LOG_LEVEL`` environment variable (default: INFO).
Output format is controlled by the ``ENVIRONMENT`` setting:

- ``development``  → Human-readable coloured text to stdout
- ``staging``      → JSON to stdout (structured, no colour)
- ``production``   → JSON to stdout (structured, no colour)

JSON fields emitted per record
-------------------------------
timestamp   ISO-8601 UTC string
level       DEBUG / INFO / WARNING / ERROR / CRITICAL
logger      Dotted module path  (e.g. app.services.ingestion)
message     The log message
exc_info    Stack trace string, only present when an exception is attached
"""
import json
import logging
import logging.config
import sys
import traceback
from datetime import datetime, timezone
from typing import Any


# ── JSON Formatter ─────────────────────────────────────────────────────────────

class _JsonFormatter(logging.Formatter):
    """
    Emits one JSON object per log line, suitable for log-aggregation pipelines.
    This is the production / staging formatter.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        elif record.exc_text:
            payload["exc_info"] = record.exc_text

        # Attach any extra fields passed via logger.info("msg", extra={...})
        # Note: we must never attempt to re-emit a key that shadows a protected
        # LogRecord attribute (e.g. "filename", "name", "msg") — Python raises
        # KeyError: "Attempt to overwrite 'X' in LogRecord" if you try.
        _PROTECTED = frozenset({
            "args", "asctime", "created", "exc_info", "exc_text", "filename",
            "funcName", "id", "levelname", "levelno", "lineno", "message",
            "module", "msecs", "msg", "name", "pathname", "process",
            "processName", "relativeCreated", "stack_info", "thread", "threadName",
        })
        for key, value in record.__dict__.items():
            if key not in _PROTECTED and not key.startswith("_"):
                payload[key] = value

        return json.dumps(payload, default=str)


# ── Human-readable Formatter ────────────────────────────────────────────────────

class _DevFormatter(logging.Formatter):
    """
    Coloured, easy-to-read formatter for local development.
    Uses ANSI escape codes — suppressed automatically when stdout is not a tty.
    """

    _LEVEL_COLOURS = {
        "DEBUG":    "\033[36m",   # Cyan
        "INFO":     "\033[32m",   # Green
        "WARNING":  "\033[33m",   # Yellow
        "ERROR":    "\033[31m",   # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    _RESET = "\033[0m"
    _DIM   = "\033[2m"

    _FMT = "{colour}{level:<8}{reset} {dim}{ts}  {logger:<40}{reset}  {message}"

    def format(self, record: logging.LogRecord) -> str:
        use_colour = sys.stdout.isatty()
        colour = self._LEVEL_COLOURS.get(record.levelname, "") if use_colour else ""
        reset  = self._RESET if use_colour else ""
        dim    = self._DIM   if use_colour else ""

        ts = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]  # HH:MM:SS.mmm

        line = self._FMT.format(
            colour=colour,
            level=record.levelname,
            reset=reset,
            dim=dim,
            ts=ts,
            logger=record.name,
            message=record.getMessage(),
        )

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)

        return line


# ── Public API ─────────────────────────────────────────────────────────────────

def configure_logging(environment: str = "development", log_level: str = "INFO") -> None:
    """
    Configure the root logger for the TradeSense application.

    Parameters
    ----------
    environment:
        One of ``development``, ``staging``, ``production``.
        Determines the output format (coloured text vs JSON).
    log_level:
        Minimum log level string: DEBUG, INFO, WARNING, ERROR, CRITICAL.
        Can be overridden via the ``LOG_LEVEL`` env variable.

    This function is idempotent — safe to call multiple times (subsequent
    calls are no-ops because the root logger's handlers are cleared first).
    """
    import os
    resolved_level_str = os.environ.get("LOG_LEVEL", log_level).upper()
    resolved_level = getattr(logging, resolved_level_str, logging.INFO)

    # Choose formatter based on environment
    use_json = environment in ("staging", "production")
    formatter: logging.Formatter = _JsonFormatter() if use_json else _DevFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    # Clear any existing handlers to prevent duplicate output on re-configuration
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(resolved_level)

    # Suppress overly chatty third-party loggers in all environments
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if environment == "development" else logging.WARNING
    )
    logging.getLogger("yfinance").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("hpack").setLevel(logging.WARNING)
