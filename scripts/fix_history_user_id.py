"""
修复历史会话的 user_id 字段 (v7.277)

问题：开发模式下，分析会话和搜索会话的 user_id 未正确保存，导致历史记录不显示。
解决：将所有 user_id 为空的会话设置为 "dev_user"。

使用方法：
    python scripts/fix_history_user_id.py
"""

import sqlite3
from pathlib import Path


def fix_archived_sessions():
    """修复 archived_sessions 表的 user_id"""
    db_path = Path("data/archived_sessions.db")
    if not db_path.exists():
        print(f"❌ 数据库不存在: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 查询 user_id 为空的会话数量
    cursor.execute("SELECT COUNT(*) FROM archived_sessions WHERE user_id IS NULL OR user_id = ''")
    null_count = cursor.fetchone()[0]
    print(f"📊 archived_sessions 表中 user_id 为空的会话数量: {null_count}")

    if null_count > 0:
        # 更新所有 user_id 为空的会话
        cursor.execute("UPDATE archived_sessions SET user_id = 'dev_user' WHERE user_id IS NULL OR user_id = ''")
        updated = cursor.rowcount
        conn.commit()
        print(f"✅ 已修复 {updated} 个分析会话的 user_id")
    else:
        print("✓ 无需修复")

    conn.close()


def fix_search_sessions():
    """修复 archived_search_sessions 表的 user_id"""
    db_path = Path("data/archived_sessions.db")
    if not db_path.exists():
        print(f"❌ 数据库不存在: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='archived_search_sessions'")
    if not cursor.fetchone():
        print("⚠️ archived_search_sessions 表不存在，跳过")
        conn.close()
        return

    # 查询 user_id 为空的会话数量
    cursor.execute("SELECT COUNT(*) FROM archived_search_sessions WHERE user_id IS NULL OR user_id = ''")
    null_count = cursor.fetchone()[0]
    print(f"📊 archived_search_sessions 表中 user_id 为空的会话数量: {null_count}")

    if null_count > 0:
        # 更新所有 user_id 为空的会话
        cursor.execute("UPDATE archived_search_sessions SET user_id = 'dev_user' WHERE user_id IS NULL OR user_id = ''")
        updated = cursor.rowcount
        conn.commit()
        print(f"✅ 已修复 {updated} 个搜索会话的 user_id")
    else:
        print("✓ 无需修复")

    conn.close()


def show_stats():
    """显示修复后的统计信息"""
    db_path = Path("data/archived_sessions.db")
    if not db_path.exists():
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n" + "=" * 50)
    print("📊 修复后统计")
    print("=" * 50)

    # 分析会话统计
    cursor.execute("SELECT user_id, COUNT(*) FROM archived_sessions GROUP BY user_id")
    results = cursor.fetchall()
    print("\n[archived_sessions]")
    for user_id, count in results:
        print(f"  user_id='{user_id}': {count} 个会话")

    # 搜索会话统计
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='archived_search_sessions'")
    if cursor.fetchone():
        cursor.execute("SELECT user_id, COUNT(*) FROM archived_search_sessions GROUP BY user_id")
        results = cursor.fetchall()
        print("\n[archived_search_sessions]")
        for user_id, count in results:
            print(f"  user_id='{user_id}': {count} 个会话")

    conn.close()


if __name__ == "__main__":
    print("=" * 50)
    print("🔧 修复历史会话 user_id 字段 (v7.277)")
    print("=" * 50)
    print()

    fix_archived_sessions()
    print()
    fix_search_sessions()

    show_stats()

    print("\n✅ 修复完成！请刷新前端页面查看历史记录。")
