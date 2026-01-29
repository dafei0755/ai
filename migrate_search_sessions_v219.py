"""
v7.219: 添加需求洞察相关字段到 archived_search_sessions 表

新增字段:
- l0_content: L0分析对话内容
- problem_solving_thinking: 解题思考内容
- structured_info: 结构化用户信息 JSON

运行方式:
    python migrate_search_sessions_v219.py

说明:
    此脚本为 v7.219 版本的数据库迁移，解决需求洞察/解题思考在刷新后丢失的问题。
    根据 BUG_FIX_v7.177_SEARCH_ROUNDS_PERSISTENCE.md 的模式实现。
"""

import sqlite3
from pathlib import Path


def migrate_database(db_path: str):
    """迁移数据库，添加 v7.219 新字段"""

    print(f"📦 开始迁移数据库: {db_path}")

    if not Path(db_path).exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 获取当前表结构
        cursor.execute("PRAGMA table_info(archived_search_sessions)")
        columns = {row[1] for row in cursor.fetchall()}
        print(f"当前表列: {columns}")

        # v7.219 新增字段
        new_columns = [
            ("l0_content", "TEXT"),
            ("problem_solving_thinking", "TEXT"),
            ("structured_info", "TEXT"),
        ]

        added_count = 0
        for col_name, col_type in new_columns:
            if col_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE archived_search_sessions ADD COLUMN {col_name} {col_type}")
                    print(f"✅ 添加列: {col_name} {col_type}")
                    added_count += 1
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        print(f"⚠️ 列已存在: {col_name}")
                    else:
                        raise
            else:
                print(f"⚠️ 列已存在: {col_name}")

        conn.commit()

        if added_count > 0:
            print(f"✅ 迁移完成! 添加了 {added_count} 个新列")
        else:
            print("ℹ️ 无需迁移，所有列已存在")

        return True

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def main():
    """主函数"""

    # 默认数据库路径
    db_paths = [
        Path(__file__).parent / "data" / "archived_sessions.db",
        Path(__file__).parent / "data" / "session_archive.db",
    ]

    migrated = 0
    for db_path in db_paths:
        if db_path.exists():
            print(f"\n{'='*60}")
            if migrate_database(str(db_path)):
                migrated += 1

    if migrated == 0:
        print("\n⚠️ 未找到任何数据库文件")
        print("请确认数据库位置，或手动指定路径")
    else:
        print(f"\n✅ 成功迁移 {migrated} 个数据库")

    print("\n📋 v7.219 迁移说明:")
    print("  - l0_content: 存储L0阶段的对话分析内容")
    print("  - problem_solving_thinking: 存储解题思考过程")
    print("  - structured_info: 存储结构化用户画像(JSON)")
    print("\n这些字段用于刷新页面后恢复'需求洞察'和'解题思考'卡片")


if __name__ == "__main__":
    main()
