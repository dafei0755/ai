"""
Spider爬虫模块

包含所有网站爬虫的实现。
"""

# 延迟导入，避免循环依赖
_spider_manager_instance = None


def get_spider_manager():
    """工厂方法：获取配置好的SpiderManager单例实例"""
    global _spider_manager_instance
    if _spider_manager_instance is not None:
        return _spider_manager_instance

    from .archdaily_cn_spider import ArchdailyCNSpider
    from .dezeen_spider import DezeenSpider
    from .gooood_spider import GoooodSpider
    from .spider_manager import SpiderManager

    manager = SpiderManager()
    manager.register_spider(ArchdailyCNSpider())
    manager.register_spider(GoooodSpider())
    manager.register_spider(DezeenSpider())
    _spider_manager_instance = manager
    return manager


__all__ = [
    "get_spider_manager",
]
