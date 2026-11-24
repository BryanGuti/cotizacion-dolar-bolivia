
import copy
import logging
import os
import re
import sys

from scraper.config import ENTITIES


SUCCESS_LEVEL = 25
SUCCESS_LEVEL_NAME = "SUCCESS"

logging.addLevelName(SUCCESS_LEVEL, SUCCESS_LEVEL_NAME)


class ColorFormatter(logging.Formatter):
    """Apply terminal colors to log levels and entity references."""

    COLORS = {
        logging.DEBUG: "\033[90m",       # Gray
        logging.INFO: "\033[36m",        # Cyan
        SUCCESS_LEVEL: "\033[32m",       # Green
        logging.WARNING: "\033[33m",     # Yellow
        logging.ERROR: "\033[31m",       # Red
        logging.CRITICAL: "\033[1;31m",  # Bold red
    }

    ENTITY_NAME_COLOR = "\033[35m"       # Purple
    ENTITY_ID_COLOR = "\033[38;5;208m"   # Orange
    RESET = "\033[0m"

    def __init__(self, fmt: str, datefmt: str = None):
        super().__init__(fmt=fmt, datefmt=datefmt)

        self.use_colors = (
            hasattr(sys.stderr, "isatty")
            and sys.stderr.isatty()
            and "NO_COLOR" not in os.environ
        )

        self.entity_patterns = []

        for entity in ENTITIES:
            self.entity_patterns.append(
                (entity["name"], self.ENTITY_NAME_COLOR)
            )
            self.entity_patterns.append(
                (entity["id"], self.ENTITY_ID_COLOR)
            )

        self.entity_patterns.sort(
            key=lambda item: len(item[0]),
            reverse=True,
        )

        pattern = "|".join(
            re.escape(value)
            for value, _ in self.entity_patterns
        )

        self.entity_regex = re.compile(
            rf"(?<!\w)({pattern})(?!\w)",
            re.IGNORECASE,
        )

        self.entity_colors = {
            value.casefold(): color
            for value, color in self.entity_patterns
        }

    def format(self, record: logging.LogRecord) -> str:
        record = copy.copy(record)

        if self.use_colors:
            # Color the log level.
            color = self.COLORS.get(record.levelno)

            if color:
                record.levelname = (
                    f"{color}{record.levelname:<8}{self.RESET}"
                )

            # Format the message before applying entity colors.
            message = record.getMessage()

            def color_entity(match):
                entity = match.group(0)
                color = self.entity_colors[entity.casefold()]

                return f"{color}{entity}{self.RESET}"

            message = self.entity_regex.sub(
                color_entity,
                message,
            )

            record.msg = message
            record.args = ()

        else:
            record.levelname = f"{record.levelname:<8}"

        return super().format(record)


def get_logger(name: str) -> logging.Logger:
    """Create and return a configured application logger."""

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Avoid adding duplicate handlers.
    if logger.handlers:
        return logger

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = ColorFormatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
