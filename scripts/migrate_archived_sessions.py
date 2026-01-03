"""
数据库迁移脚本 - 为archived_sessions表添加user_id列

修复问题: sqlite3.OperationalError: no such column: archived_sessions.user_id
优先级: P0 (阻断级)
"""

import sqlite3
from datetime import datetime
from pathlib import Path

from loguru import logger


def migrate_add_user_id_column():
    """为archived_sessions表添加user_id列"""

    # 数据库路径
    data_dir = Path(__file__).parent.parent / "data"
    db_path = data_dir / "archived_sessions.db"

    if not db_path.exists():
        logger.warning(f"⚠️ 数据库文件不存在，跳过迁移: {db_path}")
        return

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 检查列是否已存在
        cursor.execute("PRAGMA table_info(archived_sessions)")
        columns = [col[1] for col in cursor.fetchall()]

        if "user_id" in columns:
            logger.info("✅ user_id列已存在，跳过迁移")
            conn.close()
            return

        # 添加user_id列
        logger.info("🔧 开始迁移：添加user_id列...")
        cursor.execute(
            """
            ALTER TABLE archived_sessions
            ADD COLUMN user_id VARCHAR(100) DEFAULT NULL
        """
        )

        # 创建索引
        logger.info("🔧 创建user_id索引...")
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_id
            ON archived_sessions(user_id)
        """
        )

        # 创建复合索引（用户+创建时间）
        logger.info("🔧 创建复合索引...")
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_created
            ON archived_sessions(user_id, created_at DESC)
        """
        )

        conn.commit()
        conn.close()

        logger.success(f"✅ 迁移完成: {db_path}")
        logger.info("📊 已添加: user_id列 + 2个索引")

    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        raise


def verify_migration():
    """验证迁移结果"""
    data_dir = Path(__file__).parent.parent / "data"
    db_path = data_dir / "archived_sessions.db"

    if not db_path.exists():
        return

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 检查列
        cursor.execute("PRAGMA table_info(archived_sessions)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}

        # 检查索引
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='archived_sessions'")
        indexes = [row[0] for row in cursor.fetchall()]

        conn.close()

        # 验证结果
        logger.info("=" * 60)
        logger.info("📋 迁移验证结果")
        logger.info("=" * 60)
        logger.info(f"✓ user_id列: {'存在' if 'user_id' in columns else '❌缺失'}")
        logger.info(f"✓ idx_user_id索引: {'存在' if 'idx_user_id' in indexes else '❌缺失'}")
        logger.info(f"✓ idx_user_created索引: {'存在' if 'idx_user_created' in indexes else '❌缺失'}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 验证失败: {e}")


if __name__ == "__main__":
    logger.info("🚀 开始数据库迁移...")
    migrate_add_user_id_column()
    verify_migration()
    logger.success("✅ 迁移流程完成")
