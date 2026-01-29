#!/usr/bin/env python
"""
迁移所有包含搜索会话表的数据库
添加 v7.177 所需的新列
"""
import os
import sqlite3

# 需要迁移的两个数据库
db_files = ["data/archived_sessions.db", "data/project_analyzer.db"]

# 需要添加的列
new_columns = [
    ("is_deep_mode", "BOOLEAN DEFAULT 0"),
    ("thinking_content", "TEXT"),
    ("answer_content", "TEXT"),
    ("search_plan", "TEXT"),
    ("rounds", "TEXT"),
    ("total_rounds", "INTEGER DEFAULT 0"),
]

for db_file in db_files:
    if not os.path.exists(db_file):
        print(f"⚠️ {db_file} 不存在，跳过")
        continue

    print(f"\n📂 迁移 {db_file}")
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='archived_search_sessions'")
    if not cursor.fetchone():
        print("   表 archived_search_sessions 不存在，跳过")
        conn.close()
        continue

    # 获取现有列
    cursor.execute("PRAGMA table_info(archived_search_sessions)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    print(f"   现有列: {len(existing_columns)} 个")

    # 添加缺失的列
    added = 0
    for col_name, col_def in new_columns:
        if col_name not in existing_columns:
            try:
                sql = f"ALTER TABLE archived_search_sessions ADD COLUMN {col_name} {col_def}"
                cursor.execute(sql)
                print(f"   ✅ 添加列: {col_name}")
                added += 1
            except Exception as e:
                print(f"   ❌ 添加列 {col_name} 失败: {e}")
        else:
            print(f"   ⏭️ 列 {col_name} 已存在")

    conn.commit()
    conn.close()
    print(f"   🎉 迁移完成，添加了 {added} 个新列")

print("\n✅ 所有数据库迁移完成!")
