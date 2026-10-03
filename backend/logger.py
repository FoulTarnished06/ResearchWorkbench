import logging
import sys
import os

def get_logger(name: str = "ResearchWorkbench") -> logging.Logger:
    """
    Centralized structured logger for AI Research Workbench.
    Standardizes logging across all agents and backend modules.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(handler)
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, log_level, logging.INFO))
        logger.propagate = False
    return logger

logger = get_logger()
