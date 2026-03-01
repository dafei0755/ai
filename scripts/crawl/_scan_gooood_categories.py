"""扫描 gooood.cn 真实分类结构"""
import urllib.request
import json
from datetime import datetime


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


print("=== 扫描 gooood.cn 分类结构 ===")

# WordPress REST API 分页获取所有分类
all_cats = []
page = 1
while True:
    url = f"https://www.gooood.cn/wp-json/wp/v2/categories?per_page=100&orderby=count&order=desc&page={page}"
    try:
        data = fetch(url)
        if not data:
            break
        all_cats.extend(data)
        print(f"  第{page}页: {len(data)} 个分类")
        if len(data) < 100:
            break
        page += 1
    except Exception as e:
        print(f"  第{page}页失败: {e}")
        break

print(f"\n总计 {len(all_cats)} 个分类\n")

# 构建层级树
cat_map = {c["id"]: c for c in all_cats}
top_cats = [c for c in all_cats if c["parent"] == 0]
top_cats.sort(key=lambda x: -x["count"])

print("=== 一级分类（按文章数排序）===")
result = {
    "source": "gooood",
    "scanned_at": datetime.now().isoformat(),
    "total_categories": len(all_cats),
    "categories": {},
}

for cat in top_cats:
    n = cat["name"]
    s = cat["slug"]
    c = cat["count"]
    url = f"https://www.gooood.cn/category/{s}"
    # 找子分类
    sub_cats = [x for x in all_cats if x["parent"] == cat["id"]]
    sub_cats.sort(key=lambda x: -x["count"])

    print(f"  [{c:5d}] {n:30s}  slug={s}  url={url}")

    sub_data = {}
    for sub in sub_cats:
        sn = sub["name"]
        ss = sub["slug"]
        sc = sub["count"]
        # 三级分类
        sub3 = [x for x in all_cats if x["parent"] == sub["id"]]
        sub3.sort(key=lambda x: -x["count"])
        sub_print = ", ".join(f"{x['name']}({x['count']})" for x in sub3[:5])
        if sub_cats:
            print(f"    [{sc:4d}] {sn:28s}  slug={ss}" + (f"  => {sub_print}" if sub3 else ""))

        sub_data[sn] = {
            "slug": ss,
            "count": sc,
            "url": f"https://www.gooood.cn/category/{ss}",
            "sub_categories": {x["name"]: {"slug": x["slug"], "count": x["count"]} for x in sub3},
        }

    result["categories"][n] = {"slug": s, "count": c, "url": url, "sub_categories": sub_data}

# 保存
out_file = "data/gooood_categories.json"
import os

os.makedirs("data", exist_ok=True)
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n已保存到 {out_file}")
print(f"一级分类 {len(top_cats)} 个")
