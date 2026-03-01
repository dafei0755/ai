"""
测试爬虫调度器

简单测试智能调度器的基本功能
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from intelligent_project_analyzer.external_data_system.crawler_scheduler import IntelligentCrawlerScheduler, BatchConfig
from intelligent_project_analyzer.external_data_system.project_index import ProjectIndexManager
from loguru import logger


def mock_crawl_func(item):
    """模拟爬取函数"""
    import time
    import random

    # 模拟爬取延迟
    time.sleep(random.uniform(0.1, 0.3))

    # 90%成功率
    return random.random() < 0.9


def test_scheduler():
    """测试调度器"""
    logger.info("=" * 60)
    logger.info("测试爬虫调度器")
    logger.info("=" * 60)

    # 创建测试配置（加速测试）
    config = BatchConfig(
        batch_size=5,
        min_delay=0.5,
        max_delay=1.0,
        batch_rest=3.0,  # 3秒
        max_requests_per_hour=1000,
        max_requests_per_day=10000,
        work_hours=list(range(24)),  # 全天工作
    )

    # 创建调度器
    scheduler = IntelligentCrawlerScheduler(config)

    # 注册回调
    def progress_callback(data):
        logger.info(f"📊 进度更新: {data['completed']}/{data['total']} ({data['progress_percent']:.1f}%)")

    def log_callback(data):
        logger.info(f"📝 日志: [{data['level']}] {data['message']}")

    scheduler.register_progress_callback(progress_callback)
    scheduler.register_log_callback(log_callback)

    # 创建测试数据
    class MockProject:
        def __init__(self, url):
            self.url = url

    test_items = [MockProject(f"https://test.com/project/{i}") for i in range(20)]

    # 执行爬取
    logger.info(f"开始测试爬取: {len(test_items)} 个项目")
    result = scheduler.crawl_batch(task_id="test_task", source="test", items=test_items, crawl_func=mock_crawl_func)

    logger.info("=" * 60)
    logger.info("测试完成")
    logger.info("=" * 60)
    logger.info(f"总数: {result['total']}")
    logger.info(f"成功: {result['completed']}")
    logger.info(f"失败: {result['failed']}")
    logger.info(f"成功率: {result['success_rate']:.1%}")
    logger.info(f"耗时: {result['elapsed_seconds']:.1f}秒")


def test_index_stats():
    """测试索引统计"""
    logger.info("=" * 60)
    logger.info("查询索引统计")
    logger.info("=" * 60)

    try:
        index_manager = ProjectIndexManager()
        stats = index_manager.get_statistics()

        logger.info("索引统计:")
        logger.info(f"  总数: {stats['total']}")
        logger.info(f"  已爬: {stats['crawled']}")
        logger.info(f"  未爬: {stats['uncrawled']}")

        if "by_source" in stats:
            logger.info("\n按来源分布:")
            for source, data in stats["by_source"].items():
                logger.info(f"  {source}:")
                logger.info(f"    总数: {data['total']}")
                logger.info(f"    已爬: {data['crawled']}")
                logger.info(f"    未爬: {data['uncrawled']}")

    except Exception as e:
        logger.error(f"查询索引失败: {e}")


if __name__ == "__main__":
    # 测试调度器
    test_scheduler()

    print("\n")

    # 查询索引统计
    test_index_stats()
