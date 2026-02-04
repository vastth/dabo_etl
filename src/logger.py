from __future__ import annotations

import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import Optional


class SizeAndTimeRotatingFileHandler(TimedRotatingFileHandler):
    """Rotate logs by time and size.

    - Time: daily at midnight
    - Size: max_bytes
    """

    def __init__(
        self,
        filename: str,
        when: str = "midnight",
        interval: int = 1,
        backupCount: int = 7,
        encoding: Optional[str] = "utf-8",
        delay: bool = False,
        utc: bool = False,
        atTime=None,
        max_bytes: int = 10 * 1024 * 1024,
    ) -> None:
        self.max_bytes = max_bytes
        super().__init__(
            filename=filename,
            when=when,
            interval=interval,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
            utc=utc,
            atTime=atTime,
        )

    def shouldRollover(self, record: logging.LogRecord) -> bool:
        if self.stream is None:  # pragma: no cover
            self.stream = self._open()

        if self.max_bytes > 0:
            msg = "%s\n" % self.format(record)
            self.stream.seek(0, os.SEEK_END)
            if self.stream.tell() + len(msg.encode(self.encoding or "utf-8")) >= self.max_bytes:
                return True

        return super().shouldRollover(record)


def get_logger(
    name: str = "dabo_etl",
    log_dir: str = "logs",
    level: str = "INFO",
    filename: str = "dabo_etl.log",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 7,
) -> logging.Logger:
    """Create or return a configured logger.

    - Console + file handlers
    - File rotation by date and size
    - Format: time, level, message
    """

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level.upper())
    logger.propagate = False

    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, filename)

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = SizeAndTimeRotatingFileHandler(
        filename=log_path,
        when="midnight",
        interval=1,
        backupCount=backup_count,
        encoding="utf-8",
        max_bytes=max_bytes,
    )
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
