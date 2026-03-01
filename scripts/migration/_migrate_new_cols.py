"""迁移：添加 cover_image_url + extra_fields 两列"""
import sys

sys.path.insert(0, ".")

from intelligent_project_analyzer.external_data_system.models.external_projects import get_external_db
from sqlalchemy import text

db = get_external_db()
with db.engine.connect() as conn:
    result = conn.execute(
        text("SELECT column_name FROM information_schema.columns " "WHERE table_name='external_projects'")
    )
    existing = {r[0] for r in result}
    print("现有列:", sorted(existing))

    added = []
    if "cover_image_url" not in existing:
        conn.execute(text("ALTER TABLE external_projects ADD COLUMN cover_image_url TEXT"))
        added.append("cover_image_url TEXT")
    if "extra_fields" not in existing:
        conn.execute(text("ALTER TABLE external_projects ADD COLUMN extra_fields JSONB"))
        added.append("extra_fields JSONB")

    conn.commit()

    if added:
        print("✅ 已添加:", added)
    else:
        print("✓ 两列均已存在，跳过")

    # 验证
    result2 = conn.execute(
        text("SELECT column_name FROM information_schema.columns " "WHERE table_name='external_projects'")
    )
    final_cols = sorted(r[0] for r in result2)
    print("最终列:", final_cols)
    print()
    print("cover_image_url:", "cover_image_url" in final_cols)
    print("extra_fields:   ", "extra_fields" in final_cols)
