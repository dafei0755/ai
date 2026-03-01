"""
数据库初始化脚本

创建外部项目数据库的所有表和索引
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from intelligent_project_analyzer.external_data_system import get_external_db


def main():
    """初始化数据库"""
    logger.info("=" * 80)
    logger.info("🔧 开始初始化外部项目数据库")
    logger.info("=" * 80)

    try:
        # 获取数据库实例
        db = get_external_db()

        # 创建所有表
        db.create_tables()

        logger.success("✅ 数据库初始化完成！")
        logger.info("📊 已创建表:")
        logger.info("  - external_projects (项目主表)")
        logger.info("  - external_project_images (项目图片)")
        logger.info("  - sync_history (同步历史)")
        logger.info("  - quality_issues (质量问题)")

        # 测试连接
        with db.get_session() as session:
            from intelligent_project_analyzer.external_data_system.models import ExternalProject

            count = session.query(ExternalProject).count()
            logger.info(f"📊 当前项目数: {count}")

        logger.info("")
        logger.info("🎉 可以开始使用外部数据系统了!")
        logger.info("   快速启动: python scripts/test_external_data_system.py")

    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        logger.exception(e)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
