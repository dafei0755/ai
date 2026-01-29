"""
v7.235 数据库迁移脚本 - 为 archived_search_sessions 表添加新列

新增列：
- search_framework: SearchFramework JSON（搜索框架持久化）
- search_master_line: SearchMasterLine JSON（兼容旧版本）
- current_round: 当前搜索轮次
- overall_completeness: 整体完成度(0-100)
- l0_content: L0分析对话内容
- problem_solving_thinking: 解题思考内容
- structured_info: 结构化用户信息 JSON
"""

import sqlite3
from pathlib import Path


def migrate_search_sessions_table():
    """为 archived_search_sessions 表添加新列"""

    base_dir = Path(__file__).parent.parent
    db_path = base_dir / "data" / "archived_sessions.db"

    if not db_path.exists():
        print(f"⚠️ 数据库不存在: {db_path}")
        print("   如果是首次启动，这是正常的。")
        return

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='archived_search_sessions'")
        if not cursor.fetchone():
            print("⚠️ archived_search_sessions 表不存在")
            print("   表将在首次创建搜索会话时自动创建。")
            conn.close()
            return

        # 获取现有列
        cursor.execute("PRAGMA table_info(archived_search_sessions)")
        existing_cols = {col[1] for col in cursor.fetchall()}

        # 需要添加的列及其定义
        columns_to_add = [
            # v7.219: 需求洞察相关字段
            ("l0_content", "TEXT"),
            ("problem_solving_thinking", "TEXT"),
            ("structured_info", "TEXT"),
            # v7.235: 搜索框架持久化
            ("search_framework", "TEXT"),
            ("search_master_line", "TEXT"),
            ("current_round", "INTEGER DEFAULT 0"),
            ("overall_completeness", "INTEGER DEFAULT 0"),
        ]

        added = []
        skipped = []

        for col_name, col_def in columns_to_add:
            if col_name not in existing_cols:
                try:
                    sql = f"ALTER TABLE archived_search_sessions ADD COLUMN {col_name} {col_def}"
                    cursor.execute(sql)
                    added.append(col_name)
                    print(f"✅ 已添加列: {col_name} ({col_def})")
                except Exception as e:
                    print(f"❌ 添加列 {col_name} 失败: {e}")
            else:
                skipped.append(col_name)

        conn.commit()
        conn.close()

        print()
        print("=" * 60)
        print("📊 迁移结果汇总")
        print("=" * 60)
        print(f"✅ 已添加列: {len(added)} 个")
        if added:
            for col in added:
                print(f"   - {col}")

        print(f"⏭️ 已跳过列: {len(skipped)} 个（已存在）")
        if skipped:
            for col in skipped:
                print(f"   - {col}")

        if added:
            print()
            print("✅ 迁移成功！请重启后端服务。")
        else:
            print()
            print("✅ 所有列已存在，无需迁移。")

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("🔧 v7.235 数据库迁移工具")
    print("   为 archived_search_sessions 表添加新列")
    print("=" * 60)
    print()
    migrate_search_sessions_table()
