"""修复 content_hash 列缺失问题"""
import sys

sys.path.insert(0, ".")

from intelligent_project_analyzer.external_data_system.models.external_projects import get_external_db
from sqlalchemy import text

db = get_external_db()
engine = db.engine
with engine.connect() as conn:
    # 查当前列
    result = conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='external_projects' ORDER BY ordinal_position"
        )
    )
    cols = [r[0] for r in result]
    print("当前列:", cols)

    # 添加缺失列
    missing = []
    if "content_hash" not in cols:
        missing.append("content_hash")
        conn.execute(text("ALTER TABLE external_projects ADD COLUMN content_hash VARCHAR(64)"))
        print("✅ 已添加 content_hash VARCHAR(64)")
    else:
        print("✓ content_hash 已存在")

    conn.commit()

    # 验证
    result2 = conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='external_projects' ORDER BY ordinal_position"
        )
    )
    cols2 = [r[0] for r in result2]
    print("修复后列:", cols2)
    print("content_hash 存在:", "content_hash" in cols2)
