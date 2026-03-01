"""查看完整爬取数据"""
import os, json, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import sqlalchemy as sa

os.environ.setdefault("EXTERNAL_DB_URL", "postgresql://postgres:password@localhost:5432/external_projects")
engine = sa.create_engine(os.environ["EXTERNAL_DB_URL"])

with engine.connect() as conn:
    rows = conn.execute(
        sa.text(
            """
        SELECT id, source, source_id, title, description, architects, location,
               area_sqm, year, primary_category, sub_categories, tags,
               url, views, publish_date, crawled_at
        FROM external_projects
        WHERE source = 'archdaily_cn'
        ORDER BY id
    """
        )
    ).fetchall()

    print(f"共 {len(rows)} 条记录")
    print("=" * 80)

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

        print(f"[{id_}] {title}")
        print(f"  source_id  : {source_id}")
        print(f"  URL        : {url}")
        print(f"  分类       : {primary_category}")
        print(f"  年份       : {year}    面积: {area_sqm} ㎡")
        print(f"  浏览量     : {views}   发布: {publish_date}")
        arch_str = json.dumps(architects, ensure_ascii=False) if architects else "无"
        print(f"  建筑师     : {arch_str}")
        loc_str = json.dumps(location, ensure_ascii=False) if location else "无"
        print(f"  地点       : {loc_str}")
        print(f"  子分类     : {sub_categories}")
        print(f"  标签       : {tags}")
        desc = description or ""
        if len(desc) > 300:
            print(f"  描述({len(desc)}字): {desc[:300]}...")
        else:
            print(f"  描述({len(desc)}字): {desc}")
        print(f"  入库时间   : {crawled_at}")
        print()

    # 图片数量统计
    img_counts = conn.execute(
        sa.text(
            """
        SELECT p.id, p.title, COUNT(i.id) as img_count,
               SUM(CASE WHEN i.is_cover THEN 1 ELSE 0 END) as cover_count
        FROM external_projects p
        LEFT JOIN external_project_images i ON i.project_id = p.id
        WHERE p.source = 'archdaily_cn'
        GROUP BY p.id, p.title
        ORDER BY p.id
    """
        )
    ).fetchall()

    print("=" * 80)
    print("图片统计:")
    total_imgs = 0
    for pid, ptitle, cnt, cov in img_counts:
        print(f"  [{pid}] {ptitle[:40]}... 共{cnt}张图片（封面:{cov}）")
        total_imgs += cnt
    print(f"  总计图片: {total_imgs} 张")

    # 图片详情
    # 先查实际列
    img_cols = conn.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='external_project_images' ORDER BY ordinal_position"
        )
    ).fetchall()
    print(f"\n图片表列: {[c[0] for c in img_cols]}")

    print()
    print("图片详情（前15条）:")
    img_rows = conn.execute(
        sa.text(
            """
        SELECT p.id, p.title, i.url, i.caption, i.is_cover
        FROM external_project_images i
        JOIN external_projects p ON p.id = i.project_id
        ORDER BY p.id, i.id
        LIMIT 15
    """
        )
    ).fetchall()
    for pid, ptitle, iurl, cap, is_cover in img_rows:
        cover_marker = "[封面]" if is_cover else "[图片]"
        print(f"  {cover_marker} 项目{pid}  {iurl[:90]}")
        if cap:
            print(f"         说明: {cap[:60]}")

print("\n=== 完成 ===")
