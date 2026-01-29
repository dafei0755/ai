import json
import sqlite3
import sys

import msgpack

session_id = sys.argv[1] if len(sys.argv) > 1 else "8pdwoxj8-20260107203552-0a8e56cd"

conn = sqlite3.connect("data/checkpoints/workflow.db")
cursor = conn.cursor()

# 查找最后一个checkpoint
cursor.execute(
    """
    SELECT c.checkpoint_id, c.thread_id, c.checkpoint_ns, c.parent_checkpoint_id, c.checkpoint
    FROM checkpoints c
    WHERE c.thread_id = ?
    ORDER BY c.checkpoint_id DESC
    LIMIT 1
""",
    (session_id,),
)

checkpoint = cursor.fetchone()
if checkpoint:
    checkpoint_id, thread_id, ns, parent_id, checkpoint_data = checkpoint
    print(f"最后的 Checkpoint:")
    print(f"  ID: {checkpoint_id}")
    print(f"  Thread: {thread_id}")
    print(f"  Namespace: {ns}")
    print(f"  Parent: {parent_id}")

    # 解析checkpoint数据
    if checkpoint_data:
        try:
            data = msgpack.unpackb(checkpoint_data, raw=False)
            if "channel_values" in data:
                cv = data["channel_values"]
                print(f"\n=== channel_values 字段 ===")
                for key in sorted(cv.keys()):
                    val = cv[key]
                    if isinstance(val, dict):
                        print(f"  {key}: dict ({len(val)} keys)")
                    elif isinstance(val, list):
                        print(f"  {key}: list ({len(val)} items)")
                    elif isinstance(val, str) and len(val) > 50:
                        print(f"  {key}: str ({len(val)} chars)")
                    else:
                        print(f"  {key}: {val}")

                # 检查关键报告字段
                print(f"\n=== 报告相关字段 ===")
                for field in ["final_report", "aggregated_result", "report_url", "agent_results"]:
                    if field in cv:
                        val = cv[field]
                        if isinstance(val, dict):
                            print(f"  {field}: dict with keys {list(val.keys())[:10]}")
                        elif isinstance(val, str):
                            print(f"  {field}: str ({len(val)} chars)")
                            if len(val) > 0:
                                print(f"    预览: {val[:200]}...")
                        else:
                            print(f"  {field}: {type(val).__name__}")
                    else:
                        print(f"  {field}: MISSING")
        except Exception as e:
            print(f"解析checkpoint数据失败: {e}")
else:
    print(f"未找到会话 {session_id} 的checkpoint")

conn.close()
