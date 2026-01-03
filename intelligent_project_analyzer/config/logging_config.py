"""
日志配置系统 (v7.119+)

根据环境（development/staging/production）自动配置日志级别、格式和存储策略
"""

import os
import sys
from pathlib import Path
from typing import Optional

from loguru import logger


class LoggingConfig:
    """日志配置管理器"""

    def __init__(self):
        self.env = os.getenv("ENVIRONMENT", "development")
        self.log_level = os.getenv("LOG_LEVEL", None)
        self.log_dir = Path("logs")
        self.structured_logging = os.getenv("STRUCTURED_LOGGING", "false").lower() == "true"

    def setup(self):
        """设置日志系统"""

        # 移除默认handler
        logger.remove()

        # 确定日志级别
        if self.log_level is None:
            if self.env == "production":
                self.log_level = "INFO"
            elif self.env == "staging":
                self.log_level = "DEBUG"
            else:
                self.log_level = "DEBUG"

        # 创建日志目录
        self.log_dir.mkdir(exist_ok=True)

        # 配置控制台输出
        self._setup_console_handler()

        # 配置文件输出
        if self.env in ["staging", "production"]:
            self._setup_file_handlers()

        logger.info(
            f"🚀 Logging configured: env={self.env}, level={self.log_level}, structured={self.structured_logging}"
        )

        return logger

    def _setup_console_handler(self):
        """配置控制台日志"""

        if self.structured_logging:
            # 结构化JSON格式
            logger.add(sys.stderr, level=self.log_level, format="{message}", serialize=True, colorize=False)  # JSON格式
        else:
            # 人类可读格式（开发环境）
            logger.add(
                sys.stderr,
                level=self.log_level,
                format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                colorize=True,
            )

    def _setup_file_handlers(self):
        """配置文件日志（分级存储）"""

        # ERROR日志（永久保留，便于排查）
        logger.add(
            self.log_dir / "error_{time:YYYY-MM-DD}.log",
            level="ERROR",
            rotation="00:00",  # 每天轮转
            retention="90 days",  # 保留90天
            compression="zip",  # 压缩旧日志
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
            serialize=self.structured_logging,  # JSON格式
            enqueue=True,  # 异步写入
            backtrace=True,  # 完整堆栈
            diagnose=True,  # 诊断信息
        )

        # INFO日志（保留7天）
        logger.add(
            self.log_dir / "info_{time:YYYY-MM-DD}.log",
            level="INFO",
            rotation="100 MB",  # 100MB轮转
            retention="7 days",
            compression="zip",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
            serialize=self.structured_logging,
            enqueue=True,
        )

        # DEBUG日志（仅staging，保留1天）
        if self.env == "staging":
            logger.add(
                self.log_dir / "debug_{time:YYYY-MM-DD}.log",
                level="DEBUG",
                rotation="500 MB",
                retention="1 days",
                compression="zip",
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
                serialize=self.structured_logging,
                enqueue=True,
            )


# 全局日志配置实例
_logging_config: Optional[LoggingConfig] = None


def setup_logging() -> logger:
    """
    初始化日志系统（应在应用启动时调用一次）

    Returns:
        配置好的logger实例
    """
    global _logging_config

    if _logging_config is None:
        _logging_config = LoggingConfig()
        _logging_config.setup()

    return logger


def get_logging_config() -> LoggingConfig:
    """获取日志配置实例"""
    global _logging_config
    if _logging_config is None:
        setup_logging()
    return _logging_config
