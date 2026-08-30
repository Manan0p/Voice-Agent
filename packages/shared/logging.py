import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure structured console logging."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Obtain a namespaced logger instance."""
    return logging.getLogger(name)
