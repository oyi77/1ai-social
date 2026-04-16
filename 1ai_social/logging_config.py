import logging
import logging.handlers
import json
import sys
from pathlib import Path
from typing import Optional
import uuid
from datetime import datetime


class ContextFilter(logging.Filter):
    """Add context fields (request_id, user_id, tenant_id) to log records."""

    def __init__(self):
        super().__init__()
        self.request_id = None
        self.user_id = None
        self.tenant_id = None

    def filter(self, record):
        if not self.request_id:
            self.request_id = str(uuid.uuid4())
        record.request_id = self.request_id
        record.user_id = self.user_id
        record.tenant_id = self.tenant_id
        return True

    def set_request_id(self, request_id: str):
        """Set request ID for tracing."""
        self.request_id = request_id

    def set_user_id(self, user_id: Optional[str]):
        """Set user ID for context."""
        self.user_id = user_id

    def set_tenant_id(self, tenant_id: Optional[str]):
        """Set tenant ID for context."""
        self.tenant_id = tenant_id


class JsonFormatter(logging.Formatter):
    """Format logs as JSON for structured logging with context fields."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "user_id": getattr(record, "user_id", None),
            "tenant_id": getattr(record, "tenant_id", None),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Format logs as human-readable text for console output."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record):
        level_color = self.COLORS.get(record.levelname, "")
        request_id = getattr(record, "request_id", None)
        request_str = f" [{request_id}]" if request_id else ""

        formatted = (
            f"{level_color}[{record.levelname}]{self.RESET} "
            f"{record.name}{request_str}: {record.getMessage()}"
        )

        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


def setup_logging(
    log_dir: Optional[str] = None,
    level: int = logging.INFO,
    enable_console: bool = True,
    enable_file: bool = True,
    env: str = "production",
) -> ContextFilter:
    """Configure structured logging with console and file handlers.

    Args:
        log_dir: Directory for log files. Defaults to ./logs
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        enable_console: Enable console output (human-readable)
        enable_file: Enable file output (JSON format)
        env: Environment (development, production). Defaults to production

    Returns:
        ContextFilter instance for setting request_id, user_id, tenant_id

    Example:
        >>> context_filter = setup_logging()
        >>> logger = logging.getLogger(__name__)
        >>> context_filter.set_request_id("req-123")
    """
    if log_dir is None:
        log_dir = Path(__file__).parent.parent / "logs"
    else:
        log_dir = Path(log_dir)

    log_dir.mkdir(parents=True, exist_ok=True)

    context_filter = ContextFilter()

    root_logger = logging.getLogger()

    if env == "development":
        root_logger.setLevel(logging.DEBUG)
    else:
        root_logger.setLevel(level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.addFilter(context_filter)

    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if env == "development" else level)
        console_handler.setFormatter(ConsoleFormatter())
        console_handler.addFilter(context_filter)
        root_logger.addHandler(console_handler)

    if enable_file:
        log_file = log_dir / "app.log"
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_file,
            when="midnight",
            interval=1,
            backupCount=30,
            utc=True,
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(JsonFormatter())
        file_handler.addFilter(context_filter)
        root_logger.addHandler(file_handler)

    return context_filter


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    return logging.getLogger(name)
