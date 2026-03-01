"""
一次性迁移脚本：将 project_index.db 数据迁移到统一数据库的 project_discovery 表

用法:
    python scripts/migrate_project_index_to_discovery.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from loguru import logger

from intelligent_project_analyzer.external_data_system.models.external_projects import (
    ProjectDiscovery,
    get_external_db,
)


def migrate():
    """执行迁移"""
    old_db_path = project_root / "data" / "project_index.db"

    if not old_db_path.exists():
        logger.warning(f"旧数据库不存在: {old_db_path}，跳过迁移")
        return

    logger.info(f"开始迁移: {old_db_path}")

    # 连接旧数据库
    old_engine = create_engine(f"sqlite:///{old_db_path}", echo=False)
    OldSession = sessionmaker(bind=old_engine)
    old_session = OldSession()

    # 连接新数据库
    db = get_external_db()
    db.create_tables()

    # 读取旧数据
    try:
        rows = old_session.execute(text("SELECT * FROM project_index")).fetchall()
        columns = old_session.execute(text("PRAGMA table_info(project_index)")).fetchall()
        col_names = [c[1] for c in columns]
    except Exception as e:
        logger.error(f"读取旧数据库失败: {e}")
        old_session.close()
        return

    logger.info(f"旧数据库共 {len(rows)} 条记录，字段: {col_names}")

    migrated = 0
    skipped = 0

    with db.get_session() as session:
        for row in rows:
            row_dict = dict(zip(col_names, row))

            url = row_dict.get("url")
            if not url:
                skipped += 1
                continue

            # 检查是否已存在
            existing = session.query(ProjectDiscovery).filter_by(url=url).first()
            if existing:
                skipped += 1
                continue

            discovery = ProjectDiscovery(
                source=row_dict.get("source", "unknown"),
                source_id=row_dict.get("source_id", ""),
                url=url,
                category=row_dict.get("category"),
                sub_category=row_dict.get("sub_category"),
                title=row_dict.get("title"),
                preview_image=row_dict.get("preview_image"),
                discovered_at=row_dict.get("discovered_at") or datetime.now(),
                crawled_at=row_dict.get("crawled_at"),
                is_crawled=bool(row_dict.get("is_crawled", False)),
                crawl_attempts=row_dict.get("crawl_attempts", 0),
                last_error=row_dict.get("last_error"),
            )
            session.add(discovery)
            migrated += 1

    old_session.close()

    logger.success(f"迁移完成: 新增 {migrated}, 跳过 {skipped}")
    logger.info(f"旧数据库保留在: {old_db_path} (可手动删除)")


if __name__ == "__main__":
    migrate()
