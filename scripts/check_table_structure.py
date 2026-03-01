#!/usr/bin/env python3
"""检查并修复SQLite表结构"""

import sqlite3

conn = sqlite3.connect("data/external_projects.db")
cursor = conn.cursor()

# 检查当前表结构
cursor.execute("SELECT sql FROM sqlite_master WHERE name='external_projects'")
result = cursor.fetchone()
if result:
    print("当前表结构:")
    print(result[0])
    print("\n" + "=" * 80)

    # 检查是否有AUTOINCREMENT
    if "AUTOINCREMENT" in result[0]:
        print("✅ ID字段已配置AUTOINCREMENT")
    else:
        print("❌ ID字段缺少AUTOINCREMENT，需要重建表")

conn.close()
