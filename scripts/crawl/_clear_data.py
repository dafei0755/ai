"""清空旧爬取数据"""
import os, sqlalchemy as sa

os.environ["EXTERNAL_DB_URL"] = "postgresql://postgres:password@localhost:5432/external_projects"
engine = sa.create_engine(os.environ["EXTERNAL_DB_URL"])
with engine.connect() as conn:
    conn.execute(sa.text("DELETE FROM external_project_images"))
    conn.execute(sa.text("DELETE FROM external_projects WHERE source='archdaily_cn'"))
    conn.execute(sa.text("DELETE FROM sync_history"))
    conn.commit()
    cnt = conn.execute(sa.text("SELECT COUNT(*) FROM external_projects WHERE source='archdaily_cn'")).scalar()
    print(f"archdaily_cn 剩余: {cnt} 条 -> 清理完成")
