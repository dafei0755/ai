"""输出完整爬取数据到文件（避免终端编码问题）"""
import os, json
import sqlalchemy as sa

os.environ.setdefault("EXTERNAL_DB_URL", "postgresql://postgres:password@localhost:5432/external_projects")
engine = sa.create_engine(os.environ["EXTERNAL_DB_URL"])

lines = []

with engine.connect() as conn:
    rows = conn.execute(
        sa.text(
            """
        SELECT id, source, source_id, title, description, architects, location,
               area_sqm, year, primary_category, sub_categories, tags,
               url, views, publish_date, crawled_at
        FROM external_projects
        ORDER BY source, id
    """
        )
    ).fetchall()

    lines.append(f"共 {len(rows)} 条记录")
    lines.append("=" * 80)

    current_source = None
    for r in rows:
        (
            id_,
            source,
            source_id,
            title,
            description,
            architects,
            location,
            area_sqm,
            year,
            primary_category,
            sub_categories,
            tags,
            url,
            views,
            publish_date,
            crawled_at,
        ) = r

        if source != current_source:
            current_source = source
            lines.append(f"\n{'=' * 80}")
            lines.append(f"  数据源: {source}")
            lines.append(f"{'=' * 80}")

        lines.append(f"\n[{id_}] {title}")
        lines.append(f"  source     : {source}")
        lines.append(f"  source_id  : {source_id}")
        lines.append(f"  URL        : {url}")
        lines.append(f"  分类       : {primary_category}")
        lines.append(f"  年份       : {year}    面积: {area_sqm} ㎡")
        lines.append(f"  浏览量     : {views}   发布: {publish_date}")
        lines.append(f"  建筑师     : {json.dumps(architects, ensure_ascii=False) if architects else '无'}")
        lines.append(f"  地点       : {json.dumps(location, ensure_ascii=False) if location else '无'}")
        lines.append(f"  子分类     : {sub_categories}")
        lines.append(f"  标签       : {json.dumps(tags, ensure_ascii=False) if tags else '[]'}")
        lines.append(f"  入库时间   : {crawled_at}")
        lines.append(f"")
        desc = description or ""
        lines.append(f"  ── 完整描述（{len(desc)} 字）──")
        lines.append(desc)
        lines.append("-" * 80)

    # 同步历史（按数据源分组，每个源展示最近3条）
    hist = conn.execute(
        sa.text(
            """
        SELECT source, started_at, completed_at, status,
               projects_total, projects_new, projects_updated, projects_failed
        FROM sync_history
        WHERE (source, started_at) IN (
            SELECT source, started_at FROM (
                SELECT source, started_at,
                       ROW_NUMBER() OVER (PARTITION BY source ORDER BY started_at DESC) AS rn
                FROM sync_history
            ) ranked WHERE rn <= 3
        )
        ORDER BY source, started_at DESC
    """
        )
    ).fetchall()
    lines.append("\n同步历史（每个数据源最近3条）：")
    current_source = None
    for h in hist:
        if h[0] != current_source:
            current_source = h[0]
            lines.append(f"\n  ── {current_source} ──")
        lines.append(f"    status={h[3]}  total={h[4]}  new={h[5]}  updated={h[6]}  failed={h[7]}")
        lines.append(f"    {h[1]} -> {h[2]}")

out_path = r"d:\11-20\langgraph-design\_crawl_full_data.txt"
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"已写入: {out_path}")
print(f"共 {len(rows)} 条记录")
