import logging
import sys
from typing import List

MEMORY_LOGS: List[str] = []

class MemoryLogHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            MEMORY_LOGS.append(msg)
            if len(MEMORY_LOGS) > 100:
                MEMORY_LOGS.pop(0)
        except Exception:
            pass

def setup_logger(name: str = "MMW_PRO") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s : %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        mem_handler = MemoryLogHandler()
        mem_handler.setFormatter(formatter)
        logger.addHandler(mem_handler)
    return logger

logger = setup_logger()
