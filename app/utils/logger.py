import logging
import sys
import os

def setup_logger(name: str = "MMW_PRO") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, log_level_str, logging.INFO)
        logger.setLevel(level)

        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | [%(filename)s:%(lineno)d] %(name)s : %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        logger.propagate = False
    return logger

logger = setup_logger()
