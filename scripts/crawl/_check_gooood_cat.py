"""检查谷德数据的分类字段"""
from intelligent_project_analyzer.models.external_projects import get_external_db, ExternalProject

db = get_external_db()
with db.get_session() as s:
    rows = (
        s.query(
            ExternalProject.id,
            ExternalProject.primary_category,
            ExternalProject.title,
            ExternalProject.url,
            ExternalProject.crawled_at,
        )
        .filter(ExternalProject.source == "gooood")
        .order_by(ExternalProject.crawled_at.desc())
        .limit(15)
        .all()
    )

    print(f"=== 谷德项目分类检查 ({len(rows)} 条) ===")
    for r in rows:
        cat = r.primary_category or "(空)"
        title = (r.title or "?")[:50]
        crawled = r.crawled_at.strftime("%Y-%m-%d %H:%M") if r.crawled_at else "?"
        print(f"  ID={r.id:<5} 分类=[{cat:<10}] 爬取={crawled}  {title}")

    # 统计有/无分类
    total = s.query(ExternalProject).filter(ExternalProject.source == "gooood").count()
    has_cat = (
        s.query(ExternalProject)
        .filter(
            ExternalProject.source == "gooood",
            ExternalProject.primary_category.isnot(None),
            ExternalProject.primary_category != "",
        )
        .count()
    )
    no_cat = total - has_cat
    print(f"\n总计: {total} 条, 有分类: {has_cat}, 无分类: {no_cat}")

    # 检查 sync_log 看是否是通过 spider_manager 爬取的
    from sqlalchemy import text

    try:
        logs = s.execute(
            text(
                "SELECT id, source, status, total_new, started_at FROM sync_logs WHERE source='gooood' ORDER BY started_at DESC LIMIT 5"
            )
        ).fetchall()
        if logs:
            print("\n=== 同步日志 ===")
            for l in logs:
                print(f"  {l}")
    except Exception as e:
        print(f"\nsync_logs 不存在或查询失败: {e}")
