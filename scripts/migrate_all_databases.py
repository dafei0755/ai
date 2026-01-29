"""
批量数据库迁移脚本 - 为所有数据库添加缺失的列
"""

import sqlite3
from pathlib import Path


def migrate_all_databases():
    """批量迁移所有相关数据库"""

    # 需要迁移的数据库列表
    base_dir = Path(__file__).parent.parent
    db_files = [
        base_dir / "data" / "archived_sessions.db",
        base_dir / "data" / "project_analyzer.db",
        base_dir / "data" / "sessions.db",
        base_dir / "data" / "session_archive.db",
    ]

    columns_to_add = [
        ("analysis_mode", "VARCHAR(50) DEFAULT 'normal'"),
        ("display_name", "VARCHAR(200) DEFAULT NULL"),
        ("pinned", "INTEGER DEFAULT 0"),
        ("tags", "VARCHAR(500) DEFAULT NULL"),
        ("user_id", "VARCHAR(100) DEFAULT NULL"),
    ]

    for db_path in db_files:
        if not db_path.exists():
            print(f"⏭️ 跳过（不存在）: {db_path.name}")
            continue

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # 检查表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='archived_sessions'")
            if not cursor.fetchone():
                print(f"⏭️ 跳过（无archived_sessions表）: {db_path.name}")
                conn.close()
                continue

            # 获取现有列
            cursor.execute("PRAGMA table_info(archived_sessions)")
            existing_cols = [col[1] for col in cursor.fetchall()]

            added = []
            for col_name, col_def in columns_to_add:
                if col_name not in existing_cols:
                    try:
                        sql = f"ALTER TABLE archived_sessions ADD COLUMN {col_name} {col_def}"
                        cursor.execute(sql)
                        added.append(col_name)
                    except Exception as e:
                        print(f"  ⚠️ 添加{col_name}失败: {e}")

            conn.commit()
            conn.close()

            if added:
                print(f"✅ 已迁移 {db_path.name}: 添加 {added}")
            else:
                print(f"✅ 无需迁移 {db_path.name}: 所有列已存在")

        except Exception as e:
            print(f"❌ 迁移失败 {db_path.name}: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("📦 批量数据库迁移工具")
    print("=" * 60)
    print()
    migrate_all_databases()
    print()
    print("✅ 迁移完成！请重启后端服务。")
