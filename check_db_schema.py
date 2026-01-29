"""检查数据库表结构"""
import sqlite3

conn = sqlite3.connect("data/sessions.db")
cursor = conn.cursor()

# 先列出所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print("所有表:", tables)

if "archived_search_sessions" in tables:
    cursor.execute("PRAGMA table_info(archived_search_sessions)")
    columns = [row[1] for row in cursor.fetchall()]
    print("\narchived_search_sessions 表结构:", columns)

    # 检查是否有新列
    new_columns = ["is_deep_mode", "thinking_content", "answer_content", "search_plan", "rounds", "total_rounds"]
    for col in new_columns:
        if col in columns:
            print(f"✅ {col} 已存在")
        else:
            print(f"❌ {col} 不存在")
else:
    print("\n❌ archived_search_sessions 表不存在!")

conn.close()
