"""
爬取5条并入库（PostgreSQL），然后展示结果
用法:
    python _sync_to_db.py [archdaily_cn|gooood|dezeen]
默认: archdaily_cn
"""
import os
import sys
from pathlib import Path

# ── 参数 ──────────────────────────────────────────────────────────────────────
source = sys.argv[1] if len(sys.argv) > 1 else "archdaily_cn"
MAX_ITEMS = 5


# ── 颜色辅助 ──────────────────────────────────────────────────────────────────
def c(text, code):
    return f"\033[{code}m{text}\033[0m"


GREEN, CYAN, YELLOW, RED = "32", "36", "33", "31"

# ── 同步入库 ──────────────────────────────────────────────────────────────────
print(c(f"\n▶ 正在同步 [{source}]  max_items={MAX_ITEMS} → PostgreSQL external_projects …\n", CYAN))

try:
    from intelligent_project_analyzer.external_data_system.spiders import get_spider_manager

    mgr = get_spider_manager()

    # 确保表已创建
    mgr.db.create_tables()

    # 获取第一个分类
    spider = mgr.get_spider(source)
    categories = spider.get_categories() if spider else {}
    if not categories:
        print(c("✗ 未找到分类，请检查 spider 注册", RED))
        sys.exit(1)

    first_cat = next(iter(categories.keys()))
    print(c(f"  使用分类: {first_cat}", YELLOW))

    ok = mgr.sync_source(source, category=first_cat, max_pages=1, max_items=MAX_ITEMS)
    if ok:
        print(c("\n✓ 同步完成", GREEN))
    else:
        print(c("\n⚠ 同步返回失败，请查看日志", YELLOW))

except Exception as e:
    import traceback

    print(c(f"\n✗ 同步失败: {e}", RED))
    traceback.print_exc()
    sys.exit(1)

# ── 查看数据库 ────────────────────────────────────────────────────────────────
print(c(f"\n{'─'*70}", CYAN))
print(c("  PostgreSQL external_projects 数据库查看", CYAN))
print(c(f"{'─'*70}", CYAN))

try:
    from sqlalchemy import text, create_engine

    db_url = os.getenv("EXTERNAL_DB_URL", "postgresql://postgres:password@localhost:5432/external_projects")
    engine = create_engine(db_url, pool_pre_ping=True)

    with engine.connect() as conn:
        # 总数统计
        rows = conn.execute(text("SELECT source, COUNT(*) as cnt FROM external_projects GROUP BY source")).fetchall()
        print(c("\n按来源统计：", YELLOW))
        for row in rows:
            print(f"  {row[0]:20s}  {row[1]} 条")

        # 最新10条
        print(c(f"\n最新10条记录（来源={source}）：", YELLOW))
        records = conn.execute(
            text(
                "SELECT id, title, url, publish_date, crawled_at "
                "FROM external_projects WHERE source = :s ORDER BY id DESC LIMIT 10"
            ),
            {"s": source},
        ).fetchall()

        if records:
            print(f"  {'ID':>5}  {'标题':<40}  {'日期':<12}  URL")
            print("  " + "─" * 90)
            for r in records:
                title = (r[1] or "")[:38]
                date = str(r[3])[:10] if r[3] else "N/A"
                url = (r[2] or "")[:50]
                print(f"  {r[0]:>5}  {title:<40}  {date:<12}  {url}")
        else:
            print(c(f"  （{source} 暂无记录）", YELLOW))

except Exception as e:
    print(c(f"\n✗ 查询失败: {e}", RED))
    import traceback

    traceback.print_exc()
