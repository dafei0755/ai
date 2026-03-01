"""
爬虫注册表 (SpiderRegistry)

目标：新站接入只需一个文件 + 两行配置，无需改动调度器或管理器。

接入流程（新站 10 步清单见 _template_spider.py）：
  1. 在爬虫类中声明  SOURCE_NAME / DISPLAY_NAME / SCHEDULE 三个类属性
  2. 文件末尾一行：  register_spider(ClassName.SOURCE_NAME)(ClassName)
  3. 将 enabled 设为 True 开启调度

工厂方法：
  - SpiderRegistry.get_instance()          → 单例
  - SpiderRegistry.create_spider(source)   → 创建爬虫实例
  - SpiderRegistry.list_enabled_sources()  → 获取调度配置列表（供 JobSchedulerService）
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .base_spider import BaseSpider


class SpiderRegistry:
    """爬虫注册表单例

    存储 source_name → spider_class 的映射，提供统一的创建与查询入口。
    """

    _instance: Optional["SpiderRegistry"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "SpiderRegistry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._registry: Dict[str, Type["BaseSpider"]] = {}

    # ── 注册 ─────────────────────────────────────────────────────────────────

    def register(self, source_name: str, spider_class: Type["BaseSpider"]) -> None:
        """注册爬虫类。同名重复注册以最后一次为准（便于热重载）。"""
        self._registry[source_name] = spider_class
        from loguru import logger

        logger.debug(f"[SpiderRegistry] 已注册: {source_name} → {spider_class.__name__}")

    # ── 查询 ─────────────────────────────────────────────────────────────────

    def get_spider_class(self, source_name: str) -> Optional[Type["BaseSpider"]]:
        """返回爬虫类（不创建实例）。"""
        return self._registry.get(source_name)

    def create_spider(self, source_name: str) -> Optional["BaseSpider"]:
        """按名称创建爬虫实例（无参数构造）。"""
        cls = self.get_spider_class(source_name)
        if cls is None:
            from loguru import logger

            logger.error(f"[SpiderRegistry] 未知数据源: {source_name}")
            return None
        return cls()

    def list_sources(self) -> List[str]:
        """返回所有已注册源名称。"""
        return list(self._registry.keys())

    def list_enabled_sources(self) -> List[Dict[str, Any]]:
        """
        返回所有 ``SCHEDULE["enabled"] == True`` 的调度配置列表。

        每条记录格式::

            {
                "source":       "gooood",
                "display_name": "谷德设计网",
                "priority":      2,          # 并行批次优先级，越小越优先
                "day_of_week":  "tue",
                "hour":          2,
                "minute":        0,
                "enabled":       True,
            }
        """
        result: List[Dict[str, Any]] = []
        for source, cls in self._registry.items():
            schedule: Dict[str, Any] = getattr(cls, "SCHEDULE", {})
            if schedule.get("enabled", False):
                result.append(
                    {
                        "source": source,
                        "display_name": getattr(cls, "DISPLAY_NAME", source),
                        **schedule,
                    }
                )
        # 按 priority 升序排列（未声明则排末尾）
        result.sort(key=lambda x: x.get("priority", 99))
        return result

    def get_schedule(self, source_name: str) -> Dict[str, Any]:
        """返回该源的调度配置字典（不存在时返回空字典）。"""
        cls = self.get_spider_class(source_name)
        if cls is None:
            return {}
        return getattr(cls, "SCHEDULE", {})

    def __repr__(self) -> str:
        return f"<SpiderRegistry sources={self.list_sources()}>"


# ── 装饰器快捷方式 ────────────────────────────────────────────────────────────


def register_spider(source_name: str):
    """
    爬虫注册装饰器。

    用法（在爬虫文件末尾）::

        register_spider(MySpider.SOURCE_NAME)(MySpider)

    或在类定义上方::

        @register_spider("my_site")
        class MySpider(BaseSpider):
            ...
    """

    def decorator(cls: Type["BaseSpider"]) -> Type["BaseSpider"]:
        SpiderRegistry.get_instance().register(source_name, cls)
        return cls

    return decorator


# ── 自动导入所有已知爬虫（触发注册副作用）────────────────────────────────────


def _auto_import_spiders() -> None:
    """
    延迟导入所有爬虫模块，触发末尾的 ``register_spider(...)`` 调用。
    此函数在 JobSchedulerService 或 SpiderManager 首次需要枚举源时调用一次。
    """
    import importlib

    _modules = [
        ".gooood_spider",
        ".dezeen_spider",
        ".archdaily_cn_spider",
        # 新爬虫在此追加，或放入 spiders/ 包后在此 import
    ]
    for mod_name in _modules:
        try:
            importlib.import_module(mod_name, package=__package__)
        except Exception as exc:
            from loguru import logger

            logger.warning(f"[SpiderRegistry] 导入 {mod_name} 失败: {exc}")


__all__ = ["SpiderRegistry", "register_spider", "_auto_import_spiders"]
