#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证会话恢复结果"""

import json
import sqlite3
from pathlib import Path

session_id = "8pdwoxj8-20260106154858-dc82c8eb"
db_path = Path(__file__).parent.parent / "data" / "archived_sessions.db"

conn = sqlite3.connect(str(db_path))
row = conn.execute("SELECT session_data FROM archived_sessions WHERE session_id = ?", (session_id,)).fetchone()

if not row:
    print(f"❌ 未找到会话: {session_id}")
else:
    data = json.loads(row[0])
    print(f"\n✅ 会话找到: {session_id}")
    print(f"归档数据字段数: {len(data)}")
    print(f"\n关键字段检查:")

    key_fields = ["structured_requirements", "strategic_analysis", "execution_batches", "agent_results"]

    for field in key_fields:
        if field in data:
            value = data[field]
            if isinstance(value, list):
                print(f"  ✅ {field}: EXISTS ({len(value)} items)")
            elif isinstance(value, dict):
                print(f"  ✅ {field}: EXISTS ({len(value)} keys)")
            else:
                print(f"  ✅ {field}: EXISTS (type: {type(value).__name__})")
        else:
            print(f"  ❌ {field}: MISSING")

    # 显示所有字段名
    print(f"\n所有字段名:")
    print(", ".join(sorted(data.keys())))

conn.close()
