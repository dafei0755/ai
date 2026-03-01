#!/usr/bin/env python3
"""
数据库迁移：添加双语字段
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from loguru import logger


def migrate():
    """添加双语字段到SQLite数据库"""
    db_path = Path("data/external_projects.db")

    if not db_path.exists():
        logger.warning("数据库不存在，将由ORM自动创建")
        return

    logger.info(f"开始迁移数据库: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 检查字段是否存在
    cursor.execute("PRAGMA table_info(external_projects)")
    columns = {row[1] for row in cursor.fetchall()}

    fields_to_add = [
        ("title_en", "TEXT"),
        ("title_zh", "TEXT"),
        ("description_en", "TEXT"),
        ("description_zh", "TEXT"),
        ("translation_engine", "VARCHAR(50)"),
        ("translation_quality", "FLOAT"),
        ("translated_at", "DATETIME"),
        ("is_human_reviewed", "BOOLEAN DEFAULT 0"),
    ]

    added = 0
    for field_name, field_type in fields_to_add:
        if field_name not in columns:
            try:
                sql = f"ALTER TABLE external_projects ADD COLUMN {field_name} {field_type}"
                cursor.execute(sql)
                logger.success(f"✅ 添加字段: {field_name} ({field_type})")
                added += 1
            except Exception as e:
                logger.error(f"❌ 添加字段失败 {field_name}: {e}")
        else:
            logger.debug(f"  字段已存在: {field_name}")

    conn.commit()
    conn.close()

    logger.info(f"迁移完成，新增 {added} 个字段")


if __name__ == "__main__":
    migrate()
