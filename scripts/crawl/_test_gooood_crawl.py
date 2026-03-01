"""
Gooood 爬虫验收测试

随机选取 3 个空间分类，每个分类爬取第 1 篇文章详情，输出结构化结果。
用法：
    python _test_gooood_crawl.py
    python _test_gooood_crawl.py --cats 咖啡厅 公园 住宅建筑  # 指定分类
"""
import sys
import json
import random
import argparse
import textwrap
from pathlib import Path

# ── 确保项目根目录在 sys.path ───────────────────────────────────────────────
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from intelligent_project_analyzer.external_data_system.spiders.gooood_spider import GoooodSpider


# ════════════════════════════════════════════════════════════════════════════
# 输出格式化
# ════════════════════════════════════════════════════════════════════════════


def fmt_project(category_name: str, url: str, data) -> str:
    """将 ProjectData 格式化为可读的结构化文本"""
    if data is None:
        return f"  ❌  爬取失败（data=None）\n"

    lines = [
        f"  URL          : {url}",
        f"  Source-ID    : {data.source_id}",
        f"  Title        : {data.title}",
        f"  Title (EN)   : {data.title_en or '—'}",
        f"  Architects   : {json.dumps([a.get('name') for a in (data.architects or [])], ensure_ascii=False)}",
        f"  Location     : {json.dumps(data.location or {}, ensure_ascii=False)}",
        f"  Year         : {data.year or '—'}",
        f"  Area (m²)    : {data.area_sqm or '—'}",
        f"  Primary Cat  : {data.primary_category or '—'}",
        f"  Tags         : {', '.join((data.tags or [])[:8]) or '—'}",
        f"  Lang         : {data.lang}",
        f"  Quality      : {getattr(data, 'quality_score', '—')}",
    ]

    desc = (data.description_zh or data.description or "").strip()
    if desc:
        preview = textwrap.shorten(desc, width=200, placeholder="…")
        lines.append(f"  Description  : {preview}")

    desc_en = (data.description_en or "").strip()
    if desc_en:
        preview_en = textwrap.shorten(desc_en, width=200, placeholder="…")
        lines.append(f"  Desc (EN)    : {preview_en}")

    return "\n".join(lines) + "\n"


# ════════════════════════════════════════════════════════════════════════════
# 主流程
# ════════════════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(description="Gooood 爬虫验收测试")
    parser.add_argument("--cats", nargs="*", help="指定分类名称（如 '咖啡厅 公园'），默认随机选 3 个")
    args = parser.parse_args()

    spider = GoooodSpider(use_playwright=True)

    all_cats = list(GoooodSpider.CATEGORIES.keys())

    if args.cats:
        # 用户手动指定
        selected = []
        for c in args.cats:
            if c in GoooodSpider.CATEGORIES:
                selected.append(c)
            else:
                print(f"⚠  分类 '{c}' 不存在，跳过。可用分类：{all_cats[:10]}...")
        if not selected:
            print("没有有效分类，退出")
            sys.exit(1)
    else:
        selected = random.sample(all_cats, min(3, len(all_cats)))

    print(f"\n{'='*70}")
    print(f"  Gooood 爬虫验收测试 — 共 {len(selected)} 个分类")
    print(f"{'='*70}\n")

    results = {}

    try:
        for idx, cat_name in enumerate(selected, 1):
            cat_url = GoooodSpider.CATEGORIES[cat_name]
            print(f"[{idx}/{len(selected)}] 分类：{cat_name}")
            print(f"       URL：{cat_url}")

            # ── 1. 爬取分类列表（仅第 1 页）─────────────────────────────────
            urls = spider.crawl_category(cat_url, max_pages=1)

            # 过滤 checkpoint 哨兵，取真实项目 URL
            project_urls = [u for u in urls if not u.startswith("__checkpoint__:")]
            checkpoint = next((u for u in urls if u.startswith("__checkpoint__:")), None)

            print(
                f"       列表页获取 {len(project_urls)} 条 URL"
                + (f"，checkpoint={checkpoint.split(':', 1)[1]}" if checkpoint else "")
            )

            if not project_urls:
                print("  ⚠  该分类第 1 页无项目，跳过\n")
                results[cat_name] = None
                continue

            # ── 2. 爬取第 1 篇文章详情 ──────────────────────────────────────
            target_url = project_urls[0]
            print(f"       抓取详情：{target_url}")
            data = spider.parse_project_page(target_url)

            results[cat_name] = data
            print(f"  {'✅' if data else '❌'}  结果：")
            print(fmt_project(cat_name, target_url, data))

    finally:
        print("正在关闭 Playwright 浏览器…")
        spider.stop()

    # ── 汇总 ───────────────────────────────────────────────────────────────
    success = sum(1 for v in results.values() if v is not None)
    print(f"\n{'='*70}")
    print(f"  汇总：{success}/{len(selected)} 个分类爬取成功")
    for cat, data in results.items():
        status = "✅" if data else "❌"
        title = data.title[:30] if data else "失败"
        print(f"    {status}  {cat:<12} — {title}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
