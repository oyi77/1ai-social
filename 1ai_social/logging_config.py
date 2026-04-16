import logging
import logging.handlers
import json
import sys
from pathlib import Path
from typing import Optional
import uuid
from datetime import datetime


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records for request tracing."""

    def __init__(self):
        super().__init__()
        self.correlation_id = None

    def filter(self, record):
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())
        record.correlation_id = self.correlation_id
        return True

    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for tracing."""
        self.correlation_id = correlation_id


class JsonFormatter(logging.Formatter):
    """Format logs as JSON for structured logging."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None),
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
        correlation_id = getattr(record, "correlation_id", None)
        correlation_str = f" [{correlation_id}]" if correlation_id else ""

        formatted = (
            f"{level_color}[{record.levelname}]{self.RESET} "
            f"{record.name}{correlation_str}: {record.getMessage()}"
        )

        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


def setup_logging(
    log_dir: Optional[str] = None,
    level: int = logging.INFO,
    enable_console: bool = True,
    enable_file: bool = True,
) -> CorrelationIdFilter:
    """Configure structured logging with console and file handlers.

    Args:
        log_dir: Directory for log files. Defaults to ./logs
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        enable_console: Enable console output (human-readable)
        enable_file: Enable file output (JSON format)

    Returns:
        CorrelationIdFilter instance for setting correlation IDs

    Example:
        >>> correlation_filter = setup_logging()
        >>> logger = logging.getLogger(__name__)
        >>> correlation_filter.set_correlation_id("request-123")
    """
    if log_dir is None:
        log_dir = Path(__file__).parent.parent / "logs"
    else:
        log_dir = Path(log_dir)

    log_dir.mkdir(parents=True, exist_ok=True)

    # Create correlation ID filter
    correlation_filter = CorrelationIdFilter()

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.addFilter(correlation_filter)

    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(ConsoleFormatter())
        console_handler.addFilter(correlation_filter)
        root_logger.addHandler(console_handler)

    # File handler (JSON format with rotation)
    if enable_file:
        log_file = log_dir / "app.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(JsonFormatter())
        file_handler.addFilter(correlation_filter)
        root_logger.addHandler(file_handler)

    return correlation_filter


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
