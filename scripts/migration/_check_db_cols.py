"""对比模型定义列与 DB 实际列，找出所有差异"""
import sys

sys.path.insert(0, ".")

from intelligent_project_analyzer.external_data_system.models.external_projects import ExternalProject, get_external_db
from sqlalchemy import text

db = get_external_db()

# 模型中定义的列
model_cols = set(c.key for c in ExternalProject.__table__.columns)

# DB 实际的列
with db.engine.connect() as conn:
    result = conn.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name='external_projects'")
    )
    db_cols = set(r[0] for r in result)

missing = model_cols - db_cols
extra = db_cols - model_cols
print("模型定义列:", sorted(model_cols))
print()
print("DB 实际列:", sorted(db_cols))
print()
print("缺失列 (需要 ALTER TABLE):", missing)
print("多余列 (DB有但模型无):", extra)
