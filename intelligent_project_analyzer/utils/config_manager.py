"""
配置热重载管理器
支持运行时动态更新配置而无需重启服务

Features:
- 监听 .env 文件变化
- 自动重新加载配置
- 线程安全
- 支持手动触发重载
"""

import os
import threading
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

from ..settings import Settings


class HotReloadConfigManager:
    """
    配置热重载管理器

    使用轻量级轮询机制监听配置文件变化
    避免引入 watchdog 依赖（降低复杂度）
    """

    def __init__(self, check_interval: int = 10):
        """
        初始化配置管理器

        Args:
            check_interval: 检查配置文件的间隔（秒）
        """
        self.check_interval = check_interval
        self.env_path = Path(__file__).parent.parent.parent / ".env"
        self._settings: Optional[Settings] = None
        self._last_modified = 0.0
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._polling_thread: Optional[threading.Thread] = None

        # 初始加载配置
        self._reload_settings()

        # 启动后台监听线程
        self._start_polling()

        logger.info(f"✅ 配置热重载管理器已启动（检查间隔: {check_interval}秒）")

    def _reload_settings(self):
        """重新加载配置（内部方法）"""
        try:
            # 重新加载 .env 文件
            if self.env_path.exists():
                load_dotenv(self.env_path, override=True)
                self._last_modified = os.path.getmtime(self.env_path)

            # 重新创建 Settings 实例
            self._settings = Settings()

            logger.info("🔄 配置已重新加载")
        except Exception as e:
            logger.error(f"❌ 配置重载失败: {e}")

    def reload(self) -> bool:
        """
        手动触发配置重载（线程安全）

        Returns:
            bool: 是否成功重载
        """
        with self._lock:
            try:
                self._reload_settings()
                return True
            except Exception as e:
                logger.error(f"❌ 手动重载配置失败: {e}")
                return False

    def _start_polling(self):
        """启动后台轮询线程"""

        def poll():
            logger.debug("🔍 配置文件监听线程已启动")
            while not self._stop_event.is_set():
                try:
                    # 检查文件是否被修改
                    if self.env_path.exists():
                        current_modified = os.path.getmtime(self.env_path)

                        if current_modified > self._last_modified:
                            logger.info("📝 检测到 .env 文件变更")
                            with self._lock:
                                self._reload_settings()

                    # 等待下一次检查
                    self._stop_event.wait(self.check_interval)

                except Exception as e:
                    logger.error(f"❌ 配置文件监听错误: {e}")
                    self._stop_event.wait(self.check_interval)

        self._polling_thread = threading.Thread(target=poll, daemon=True, name="ConfigReloadThread")
        self._polling_thread.start()

    def stop(self):
        """停止配置监听"""
        if self._polling_thread and self._polling_thread.is_alive():
            logger.info("⏹️ 停止配置文件监听")
            self._stop_event.set()
            self._polling_thread.join(timeout=5)

    @property
    def settings(self) -> Settings:
        """获取当前配置（线程安全）"""
        with self._lock:
            if self._settings is None:
                self._reload_settings()
            return self._settings

    def get(self, key: str, default=None):
        """
        获取配置值（点号路径支持）

        Args:
            key: 配置键（支持 'llm.model' 格式）
            default: 默认值

        Returns:
            配置值或默认值

        Example:
            >>> config_manager.get('llm.model')
            'gpt-4o'
        """
        try:
            value = self.settings
            for part in key.split("."):
                value = getattr(value, part, None)
                if value is None:
                    return default
            return value
        except Exception as e:
            logger.warning(f"⚠️ 获取配置 {key} 失败: {e}")
            return default

    def get_sanitized_config(self) -> dict:
        """
        获取脱敏后的配置（用于管理后台展示）

        移除所有敏感信息（API Key、密码等）
        """
        settings = self.settings

        return {
            "environment": settings.environment,
            "debug": settings.debug,
            "log_level": settings.log_level,
            "llm": {
                "provider": settings.llm.provider,
                "model": settings.llm.model,
                "max_tokens": settings.llm.max_tokens,
                "temperature": settings.llm.temperature,
                "api_base_configured": bool(settings.llm.api_base),
            },
            "image_generation": {
                "enabled": settings.image_generation.enabled,
                "model": settings.image_generation.model,
                "max_images_per_report": settings.image_generation.max_images_per_report,
            },
            "storage": {
                "upload_dir": settings.storage.upload_dir,
                "output_dir": settings.storage.output_dir,
                "database_url": settings.storage.database_url,
            },
            "redis": {
                "redis_url": settings.redis_url,
            },
            "concurrency": {
                "max_concurrent_agents": settings.concurrency.max_concurrent_agents,
            },
        }


# 全局配置管理器实例
_config_manager: Optional[HotReloadConfigManager] = None


def get_config_manager() -> HotReloadConfigManager:
    """获取全局配置管理器单例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = HotReloadConfigManager(check_interval=10)
    return _config_manager


# 便捷访问
config_manager = get_config_manager()
