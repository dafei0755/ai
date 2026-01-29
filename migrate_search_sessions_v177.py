"""
v7.177: 添加深度搜索相关字段到 archived_search_sessions 表

新增字段:
- is_deep_mode: 是否深度搜索模式
- thinking_content: 深度思考内容
- answer_content: AI 回答内容（新字段）
- search_plan: 搜索规划 JSON
- rounds: 搜索轮次记录 JSON
- total_rounds: 总轮数
"""
import logging
import os
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """执行数据库迁移"""
    # 正确的数据库路径
    db_path = os.path.join(os.path.dirname(__file__), "data", "archived_sessions.db")

    if not os.path.exists(db_path):
        logger.warning(f"数据库文件不存在: {db_path}")
        return False

    logger.info(f"📦 开始迁移数据库: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 先列出所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    logger.info(f"数据库中的表: {tables}")

    if "archived_search_sessions" not in tables:
        logger.warning("archived_search_sessions 表不存在")
        conn.close()
        return False

    # 获取当前表结构
    cursor.execute("PRAGMA table_info(archived_search_sessions)")
    columns = {row[1] for row in cursor.fetchall()}
    logger.info(f"当前表列: {columns}")

    # 需要添加的新列
    new_columns = {
        "is_deep_mode": "INTEGER DEFAULT 0",
        "thinking_content": "TEXT",
        "answer_content": "TEXT",
        "search_plan": "TEXT",
        "rounds": "TEXT",
        "total_rounds": "INTEGER DEFAULT 0",
    }

    added = []
    for col_name, col_type in new_columns.items():
        if col_name not in columns:
            try:
                cursor.execute(f"ALTER TABLE archived_search_sessions ADD COLUMN {col_name} {col_type}")
                added.append(col_name)
                logger.info(f"✅ 添加列: {col_name} {col_type}")
            except Exception as e:
                logger.error(f"❌ 添加列失败 {col_name}: {e}")
        else:
            logger.info(f"⏭️ 列已存在: {col_name}")

    conn.commit()
    conn.close()

    if added:
        logger.info(f"✅ 迁移完成! 添加了 {len(added)} 个新列: {added}")
    else:
        logger.info("✅ 无需迁移，所有列已存在")

    return True


if __name__ == "__main__":
    migrate()
