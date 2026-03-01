"""
archdaily.cn 网站结构扫描
从官方 API 获取完整三级分类树 + 文章数，作为爬虫配置基准
"""
import urllib.request, json, datetime

API = "https://www.archdaily.cn/search/api/v1/cn/projects/categories"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120",
    "Accept": "application/json",
}

print("正在请求 archdaily.cn 分类 API ...")
req = urllib.request.Request(API, headers=headers)
with urllib.request.urlopen(req, timeout=20) as r:
    data = json.loads(r.read())

total_docs = data["total_docs"]
cats = data["aggregations"]["categories"]

# 只取 level=1 的顶级分类，按文章数降序
top = sorted([c for c in cats if c.get("level") == 1], key=lambda x: -x["doc_count"])

print(f"\n全站总文章数: {total_docs:,}")
print(f"一级分类数量: {len(top)}")
print(f"扫描时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
print("=" * 70)
print(f"{'分类名':<20} {'文章数':>7}  slug")
print("-" * 70)

grand = 0
summary = {}  # 给爬虫用的配置
for c in top:
    name = c["name"]
    cnt = c["doc_count"]
    slug = c["slug"]
    grand += cnt
    print(f"{name:<20} {cnt:>7,}  {slug}")
    sub2_list = []
    for s2 in c.get("sub_categories", []):
        s3_names = [s3["name"] for s3 in s2.get("sub_categories", [])]
        sfx = "  -> " + ", ".join(s3_names) if s3_names else ""
        print(f"    {s2['name']:<18} {s2['doc_count']:>7,}  {s2['slug']}{sfx}")
        sub2_list.append({"name": s2["name"], "slug": s2["slug"], "count": s2["doc_count"]})
    summary[name] = {
        "slug": slug,
        "count": cnt,
        "url": f"https://www.archdaily.cn/search/cn/projects/categories/{slug}",
        "sub_categories": sub2_list,
    }
    print()

print("-" * 70)
print(f"{'一级合计':<20} {grand:>7,}")
print("=" * 70)

# 保存 JSON 供爬虫读取
out = {
    "source": "archdaily_cn",
    "scanned_at": datetime.datetime.now().isoformat(),
    "total_docs": total_docs,
    "top_level_total": grand,
    "categories": summary,
}
path = "data/archdaily_cn_categories.json"
import os

os.makedirs("data", exist_ok=True)
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"\n已保存到 {path}")
