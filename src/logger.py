"""
日志模块：提供一个带时间+大小切分的文件日志处理器与方便的 `get_logger` 工厂函数。

设计目的：
- 为服务运行时提供持久化日志（文件）与实时终端日志（console），便于线上问题排查；
- 文件按天切分，并同时支持单文件大小限制，防止单日日志过大导致磁盘问题；
- 简单配置接口允许在测试/生产环境中通过参数调整日志目录、大小与保留天数。
"""

from __future__ import annotations

import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import Optional


class SizeAndTimeRotatingFileHandler(TimedRotatingFileHandler):
    """在 `TimedRotatingFileHandler` 基础上增加按文件大小滚动的判断。

    行为说明：
        - 首先按时间（默认每天午夜）触发轮转；
        - 其次如果当前文件大小超过 `max_bytes`，在写入新记录前也会触发轮转；
        - 该类通过重写 `shouldRollover` 合并时间与大小两个条件。
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
            # 将流定位到文件尾并计算写入后大小以判断是否需要基于大小的轮转
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
    """创建并返回一个配置好的 Logger。

    参数:
        name: 日志器名称，便于在复杂应用中区分不同模块的日志；
        log_dir: 日志文件目录；
        level: 日志级别，支持字符串（如 "INFO"、"DEBUG"）；
        filename: 日志文件名；
        max_bytes: 单文件最大字节数（超过则触发按大小轮转）；
        backup_count: 保留的历史轮转文件数量。

    返回:
        配置好的 `logging.Logger` 实例（添加了文件与控制台处理器）。

    注意:
        - 如果已存在处理器（logger.handlers 非空），函数将直接返回现有 logger，避免重复添加处理器；
        - 在多进程写同一日志文件时会有竞争问题，生产环境可考虑使用集中化日志（如 rsyslog/ELK）或进程间隔离的日志策略。
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
