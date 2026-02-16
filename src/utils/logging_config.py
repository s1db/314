import logging
import logging.config
from pathlib import Path
from typing import Optional


class ColorFormatter(logging.Formatter):
    """
    Custom formatter to add colors to log levels and prefix with 'c ' for SAT competition compliance.
    """

    # ANSI escape codes
    GREY = "\x1b[38;20m"
    BLUE = "\x1b[34;20m"
    GREEN = "\x1b[32;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"

    FORMAT_TEMPLATE = "c %(asctime)s [%(levelname)s] %(message)s"

    FORMATS = {
        logging.DEBUG: "c %(asctime)s ["
        + BLUE
        + "%(levelname)s"
        + RESET
        + "] %(message)s",
        logging.INFO: "c %(asctime)s ["
        + GREEN
        + "%(levelname)s"
        + RESET
        + "] %(message)s",
        logging.WARNING: "c %(asctime)s ["
        + YELLOW
        + "%(levelname)s"
        + RESET
        + "] %(message)s",
        logging.ERROR: "c %(asctime)s ["
        + RED
        + "%(levelname)s"
        + RESET
        + "] %(message)s",
        logging.CRITICAL: "c %(asctime)s ["
        + BOLD_RED
        + "%(levelname)s"
        + RESET
        + "] %(message)s",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.FORMAT_TEMPLATE)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_logging(log_level: str = "INFO", log_file: Optional[Path] = None):
    """
    Sets up logging configuration.

    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional path to a log file.
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")

    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
            "formatter": "color",
            "level": numeric_level,
        }
    }

    loggers = {
        "": {  # Root logger
            "handlers": ["console"],
            "level": numeric_level,
            "propagate": True,
        }
    }

    if log_file:
        handlers["file"] = {
            "class": "logging.FileHandler",
            "filename": str(log_file),
            "formatter": "file",
            "level": numeric_level,
            "mode": "w",
        }
        loggers[""]["handlers"].append("file")

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "color": {
                "()": ColorFormatter,
            },
            "file": {
                "format": "%(asctime)s [%(levelname)s] %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": handlers,
        "loggers": loggers,
    }

    logging.config.dictConfig(logging_config)
