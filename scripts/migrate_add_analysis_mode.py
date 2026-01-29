"""
数据库迁移脚本 - 为archived_sessions表添加analysis_mode列

修复问题: sqlite3.OperationalError: no such column: archived_sessions.analysis_mode
版本: v7.178
"""

import sqlite3
from pathlib import Path

from loguru import logger


def migrate_add_analysis_mode_column():
    """为archived_sessions表添加analysis_mode列"""

    # 数据库路径
    data_dir = Path(__file__).parent.parent / "data"
    db_path = data_dir / "archived_sessions.db"

    if not db_path.exists():
        logger.warning(f"⚠️ 数据库文件不存在，跳过迁移: {db_path}")
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 检查列是否已存在
        cursor.execute("PRAGMA table_info(archived_sessions)")
        columns = [col[1] for col in cursor.fetchall()]

        if "analysis_mode" in columns:
            logger.info("✅ analysis_mode列已存在，跳过迁移")
            conn.close()
            return True

        # 添加analysis_mode列
        logger.info("🔧 开始迁移：添加analysis_mode列...")
        cursor.execute(
            """
            ALTER TABLE archived_sessions
            ADD COLUMN analysis_mode VARCHAR(50) DEFAULT 'normal'
        """
        )

        conn.commit()
        logger.success(f"✅ analysis_mode列添加成功")

        # 检查并添加其他可能缺失的列
        cursor.execute("PRAGMA table_info(archived_sessions)")
        columns = [col[1] for col in cursor.fetchall()]

        # 添加 display_name 列（如果缺失）
        if "display_name" not in columns:
            logger.info("🔧 添加display_name列...")
            cursor.execute(
                """
                ALTER TABLE archived_sessions
                ADD COLUMN display_name VARCHAR(200) DEFAULT NULL
            """
            )
            conn.commit()
            logger.success("✅ display_name列添加成功")

        # 添加 pinned 列（如果缺失）
        if "pinned" not in columns:
            logger.info("🔧 添加pinned列...")
            cursor.execute(
                """
                ALTER TABLE archived_sessions
                ADD COLUMN pinned INTEGER DEFAULT 0
            """
            )
            # 创建索引
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_pinned_created_at
                ON archived_sessions(pinned, created_at DESC)
            """
            )
            conn.commit()
            logger.success("✅ pinned列及索引添加成功")

        # 添加 tags 列（如果缺失）
        if "tags" not in columns:
            logger.info("🔧 添加tags列...")
            cursor.execute(
                """
                ALTER TABLE archived_sessions
                ADD COLUMN tags VARCHAR(500) DEFAULT NULL
            """
            )
            conn.commit()
            logger.success("✅ tags列添加成功")

        # 创建复合索引（用户+置顶+时间）如果不存在
        try:
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_pinned_created
                ON archived_sessions(user_id, pinned, created_at DESC)
            """
            )
            conn.commit()
            logger.info("✅ 复合索引创建成功")
        except Exception as e:
            logger.warning(f"⚠️ 复合索引可能已存在: {e}")

        conn.close()

        logger.success(f"✅ 迁移完成: {db_path}")
        return True

    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        raise


def verify_migration():
    """验证迁移结果"""
    data_dir = Path(__file__).parent.parent / "data"
    db_path = data_dir / "archived_sessions.db"

    if not db_path.exists():
        logger.warning(f"⚠️ 数据库文件不存在: {db_path}")
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(archived_sessions)")
        columns = [col[1] for col in cursor.fetchall()]

        required_columns = ["analysis_mode", "display_name", "pinned", "tags", "user_id"]
        missing = [col for col in required_columns if col not in columns]

        if missing:
            logger.warning(f"⚠️ 缺少列: {missing}")
            conn.close()
            return False

        logger.success(f"✅ 所有必需列都已存在: {required_columns}")
        conn.close()
        return True

    except Exception as e:
        logger.error(f"❌ 验证失败: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("📦 archived_sessions 数据库迁移工具 (v7.178+)")
    print("=" * 60)
    print()

    print("1. 执行迁移...")
    migrate_add_analysis_mode_column()

    print()
    print("2. 验证迁移结果...")
    if verify_migration():
        print()
        print("✅ 迁移成功完成！可以重启后端服务。")
    else:
        print()
        print("❌ 迁移验证失败，请检查错误信息。")
