"""扫描 dezeen.com 真实分类结构"""
import urllib.request
import json
from datetime import datetime


def fetch(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


print("=== 扫描 dezeen.com 分类结构 ===")

# Dezeen 也是 WordPress，尝试 WP REST API
all_cats = []
page = 1
while True:
    url = f"https://www.dezeen.com/wp-json/wp/v2/categories?per_page=100&orderby=count&order=desc&page={page}"
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

if not all_cats:
    print("REST API 不可用，尝试直接解析导航页面...")
    # dezeen 无REST API，尝试解析 sitemap 或导航
    sitemap_url = "https://www.dezeen.com/sitemap.xml"
    try:
        req = urllib.request.Request(sitemap_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read().decode("utf-8")
        print("获取到 sitemap:", content[:500])
    except Exception as e:
        print(f"Sitemap 失败: {e}")
else:
    print(f"\n总计 {len(all_cats)} 个分类\n")

    cat_map = {c["id"]: c for c in all_cats}
    top_cats = [c for c in all_cats if c["parent"] == 0]
    top_cats.sort(key=lambda x: -x["count"])

    print("=== 一级分类（按文章数排序）===")
    result = {
        "source": "dezeen",
        "scanned_at": datetime.now().isoformat(),
        "total_categories": len(all_cats),
        "categories": {},
    }

    for cat in top_cats:
        n = cat["name"]
        s = cat["slug"]
        c = cat["count"]
        url_cat = f"https://www.dezeen.com/{s}"
        sub_cats = [x for x in all_cats if x["parent"] == cat["id"]]
        sub_cats.sort(key=lambda x: -x["count"])

        print(f"  [{c:5d}] {n:35s}  slug={s}")

        sub_data = {}
        for sub in sub_cats[:10]:
            sn = sub["name"]
            ss = sub["slug"]
            sc = sub["count"]
            print(f"    [{sc:4d}] {sn:30s}  slug={ss}")
            sub_data[sn] = {"slug": ss, "count": sc, "url": f"https://www.dezeen.com/{ss}"}

        result["categories"][n] = {"slug": s, "count": c, "url": url_cat, "sub_categories": sub_data}

    import os

    os.makedirs("data", exist_ok=True)
    out_file = "data/dezeen_categories.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n已保存到 {out_file}")
    print(f"一级分类 {len(top_cats)} 个")
