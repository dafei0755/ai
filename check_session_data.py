import sqlite3

# 检查归档数据
print("=" * 80)
print("检查归档数据库")
print("=" * 80)
conn = sqlite3.connect("data/archived_sessions.db")
cursor = conn.cursor()
cursor.execute("SELECT session_data FROM archived_sessions WHERE session_id = ?", ("8pdwoxj8-20260106154858-dc82c8eb",))
row = cursor.fetchone()
if row:
    import json

    data = json.loads(row[0])
    print(f"会话数据字段数: {len(data)}")
    print(f"关键字段存在性:")
    for key in [
        "structured_requirements",
        "restructured_requirements",
        "strategic_analysis",
        "execution_batches",
        "agent_results",
        "final_report",
    ]:
        exists = key in data
        value = data.get(key) if exists else None
        print(f"  {key}: {'EXISTS' if exists else 'MISSING'} - {type(value).__name__ if value is not None else 'None'}")
conn.close()

# 检查checkpoints
print("\n" + "=" * 80)
print("检查 Checkpoints 数据库")
print("=" * 80)
try:
    conn = sqlite3.connect("data/checkpoints/workflow.db")
    cursor = conn.cursor()

    # 获取表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"表: {tables}")

    if "writes" in tables:
        # 查找该会话的writes记录
        cursor.execute(
            """
            SELECT channel, COUNT(*)
            FROM writes
            WHERE thread_id = ?
            GROUP BY channel
        """,
            ("8pdwoxj8-20260106154858-dc82c8eb",),
        )

        channels = cursor.fetchall()
        print(f"\n会话的writes记录 (按channel分组):")
        for channel, count in channels:
            print(f"  {channel}: {count} 条")

    conn.close()
except Exception as e:
    print(f"错误: {e}")
