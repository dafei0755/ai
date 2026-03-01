#!/usr/bin/env python3
"""
初始化外部项目数据库
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from intelligent_project_analyzer.external_data_system import get_external_db


def init_db():
    """初始化数据库表结构"""
    logger.info("开始初始化外部项目数据库...")

    # 获取数据库实例
    db = get_external_db()

    # 创建所有表
    db.create_tables()

    # 测试连接
    with db.get_session() as session:
        from intelligent_project_analyzer.external_data_system.models import ExternalProject

        count = session.query(ExternalProject).count()
        logger.success(f"✅ 数据库初始化成功！当前项目数: {count}")

    logger.info(f"数据库位置: {db.database_url}")


if __name__ == "__main__":
    init_db()
