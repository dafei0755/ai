"""
archdaily.cn 爬取测试 — 抓5条入库后查看结果
"""
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:password@localhost:5432/project_analyzer")
os.environ.setdefault("EXTERNAL_DB_URL", "postgresql://postgres:password@localhost:5432/external_projects")

# ── 1. 初始化数据库表 ──────────────────────────────────────────────────
print("=== [1] 初始化数据库表 ===")
from intelligent_project_analyzer.external_data_system.models.external_projects import get_external_db

db = get_external_db()
db.create_tables()
print("✅ 表已就绪")

# ── 2. 创建爬虫管理器 ──────────────────────────────────────────────────
print("\n=== [2] 启动爬虫管理器 ===")
from intelligent_project_analyzer.external_data_system.spiders.spider_manager import SpiderManager
from intelligent_project_analyzer.external_data_system.spiders.archdaily_cn_spider import ArchdailyCNSpider

manager = SpiderManager(db=db)
manager.register_spider(ArchdailyCNSpider())

# ── 3. 执行爬取（住宅分类，限5条）──────────────────────────────────────
print("\n=== [3] 开始爬取 archdaily.cn / 住宅（max_items=5）===")
success = manager.sync_source(
    source="archdaily_cn",
    category="住宅",
    max_pages=2,
    max_items=5,
)
print(f"\n爬取结果: {'✅ 成功' if success else '❌ 失败'}")

# ── 4. 查询数据库结果 ──────────────────────────────────────────────────
print("\n=== [4] 数据库结果 ===")
import sqlalchemy as sa

engine = sa.create_engine(os.environ["EXTERNAL_DB_URL"], echo=False)
with engine.connect() as conn:
    # 总数
    total = conn.execute(sa.text("SELECT COUNT(*) FROM external_projects WHERE source='archdaily_cn'")).scalar()
    print(f"archdaily_cn 总条数: {total}")

    # 最新5条
    rows = conn.execute(
        sa.text(
            """
        SELECT id, title, primary_category, year, area_sqm, url, crawled_at
        FROM external_projects
        WHERE source = 'archdaily_cn'
        ORDER BY crawled_at DESC
        LIMIT 5
    """
        )
    ).fetchall()

    print(f"\n最新 {len(rows)} 条记录:")
    print("-" * 80)
    for r in rows:
        print(f"  id={r[0]}")
        print(f"  标题: {r[1]}")
        print(f"  分类: {r[2]}  年份: {r[3]}  面积: {r[4]}")
        print(f"  URL:  {r[5]}")
        print(f"  入库: {r[6]}")
        print()

    # 同步历史
    hist = conn.execute(
        sa.text(
            """
        SELECT source, started_at, completed_at, status,
               projects_total, projects_new, projects_updated, projects_failed
        FROM sync_history
        ORDER BY started_at DESC
        LIMIT 3
    """
        )
    ).fetchall()
    print("同步历史（最近3条）:")
    print("-" * 80)
    for h in hist:
        print(f"  source={h[0]}  status={h[3]}  total={h[4]}  new={h[5]}  updated={h[6]}  failed={h[7]}")
        print(f"  开始: {h[1]}  完成: {h[2]}")
        print()

print("=== 完成 ===")
