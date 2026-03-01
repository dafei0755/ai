"""扫描 gooood.cn 真实空间类型分类 (via dashboard API)

运行结果保存至 data/gooood_types.json
输出：
  1. 所有分类完整列表（含子类层级）
  2. 仅空间/建筑类型汇总表（排除摄影/绘画/工业设计等非空间类）

使用方法：
  python _scan_gooood_types.py
"""
import urllib.request
import json
from datetime import datetime
import os

BASE = "https://dashboard.gooood.cn/api/wp/v2/type?page={page}&per_page=100&hide_empty=true&orderby=count&order=desc"

# 顶级非空间分类 slug（排除，不纳入爬取范围）
NON_SPATIAL_SLUGS = {
    "industry-design",  # 工业设计（产品/家具/灯具）
    "photography",  # 摄影
    "painting",  # 绘画
    "illustration",  # 插画
    "graphic-design",  # 平面设计
    "fashion-design",  # 服装设计
    "branding",  # 品牌术
    "parametric-design",  # 参数化设计（偏手法而非空间类型）
    "digital-art",  # 数码艺术
    "oil-painting",  # 油画
    "stationery",  # 文具
    "film",  # 电影
    "booklet",  # 书籍
    "material",  # 材料（非建筑类型）
    "visual-identity",  # 视觉识别系统
}


def fetch(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
            "Referer": "https://www.gooood.cn/",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read()), resp.headers.get("X-WP-Total"), resp.headers.get("X-WP-TotalPages")


print("=== 扫描 gooood.cn 空间类型分类 ===")
print("API: dashboard.gooood.cn/api/wp/v2/type")

all_types = []
page = 1
while True:
    data, total, total_pages = fetch(BASE.format(page=page))
    if not data:
        break
    all_types.extend(data)
    tp = int(total_pages) if total_pages else 1
    print(f"  第{page}/{tp}页: {len(data)} 条  (累计 {len(all_types)} / {total})")
    if page >= tp:
        break
    page += 1

print(f"\n总计 {len(all_types)} 个空间类型\n")

# 构建层级树（parent=0 为顶级）
cat_map = {c["id"]: c for c in all_types}
top_types = [c for c in all_types if c["parent"] == 0]
top_types.sort(key=lambda x: -x["count"])

result = {
    "source": "gooood",
    "scanned_at": datetime.now().isoformat(),
    "api": "https://dashboard.gooood.cn/api/wp/v2/type",
    "total_types": len(all_types),
    "top_level_count": len(top_types),
    "note": "所有类型=空间/项目类型，来自复合检索筛选器",
    "types": {},
}

# ── 完整列表（含子类层级）────────────────────────────────────────────────────
print(f"{'序号':>4} {'文章数':>6}  {'类型名':30}  slug")
print("-" * 80)
for i, t in enumerate(sorted(all_types, key=lambda x: -x["count"]), 1):
    slug = t["slug"]
    name = t["name"]
    count = t["count"]
    parent = t["parent"]
    parent_name = cat_map[parent]["name"] if parent and parent in cat_map else ""

    prefix = "    " if parent else ""
    print(f"{i:4d} [{count:6d}]  {prefix}{name:28}  {slug}" + (f"  (parent: {parent_name})" if parent_name else ""))

    if not parent:  # 仅记录顶级（子级合并进来）
        sub = [c for c in all_types if c["parent"] == t["id"]]
        sub.sort(key=lambda x: -x["count"])
        result["types"][name] = {
            "slug": slug,
            "count": count,
            "url": f"https://www.gooood.cn/filter/type/{slug}/country/all/material/all/office/all",
            "is_spatial": slug not in NON_SPATIAL_SLUGS,
            "sub_types": {
                s["name"]: {
                    "slug": s["slug"],
                    "count": s["count"],
                    "url": f"https://www.gooood.cn/filter/type/{s['slug']}/country/all/material/all/office/all",
                }
                for s in sub
            },
        }

# ── 空间类型汇总表（排除非空间）───────────────────────────────────────────────
spatial_top = [t for t in top_types if t["slug"] not in NON_SPATIAL_SLUGS]
total_spatial_articles = sum(t["count"] for t in spatial_top)

print("\n")
print("=" * 80)
print(f"▶ gooood.cn 空间/建筑 分类汇总（{datetime.now().strftime('%Y-%m-%d')} 扫描）")
print(f"  顶级空间类型: {len(spatial_top)} 个  |  含子类总计: {len(all_types)} 个  |  空间类文章总数 ≈ {total_spatial_articles:,}")
print("=" * 80)
print(f"  {'文章数':>6}  {'类型名（中文）':20}  {'主要子类（Top5）'}")
print("  " + "-" * 76)
for t in spatial_top:
    sub = sorted([c for c in all_types if c["parent"] == t["id"]], key=lambda x: -x["count"])
    sub_str = "  ".join(f"{s['name'].split('|')[0]}({s['count']})" for s in sub[:5])
    cn_name = t["name"].split("|")[0]  # 取中文部分（有些名称带中英双语）
    print(f"  [{t['count']:6d}]  {cn_name:20}  {sub_str}")

print("=" * 80)
print(f"\n[非空间类型，已排除，共 {len(top_types) - len(spatial_top)} 类]")
for t in top_types:
    if t["slug"] in NON_SPATIAL_SLUGS:
        cn_name = t["name"].split("|")[0]
        print(f"  [{t['count']:6d}]  {cn_name}  (slug={t['slug']})")

# ── 保存 JSON ────────────────────────────────────────────────────────────────
os.makedirs("data", exist_ok=True)
with open("data/gooood_types.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n已保存到 data/gooood_types.json")
print(f"顶级类型: {len(top_types)} 个  其中空间类: {len(spatial_top)} 个  非空间: {len(top_types) - len(spatial_top)} 个")
