"""探查 archdaily.cn 项目页面的真实 HTML 结构，找出正确选择器"""
import sys

sys.path.insert(0, r"d:\11-20\langgraph-design")

from playwright.sync_api import sync_playwright

TEST_URL = "https://www.archdaily.cn/cn/1038767/shuang-yu-dao-yong-qi-yan-hua-suo-shi-yan-xing-shui-shang-yun-dong-pei-tao-jian-zhu-she-ji-studio-10"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(TEST_URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)

    print("=" * 60)
    print("=== og:title ===")
    try:
        print(page.locator('meta[property="og:title"]').get_attribute("content"))
    except:
        print("NONE")

    print("\n=== 规格面板 (specs/info) 候选 HTML ===")
    for sel in [
        ".afd-project-specs",
        ".project-specs",
        ".spec-list",
        "ul.specs",
        '[class*="spec"]',
        '[class*="info"]',
        "dl",
        ".afd-slideshow-info",
    ]:
        elems = page.locator(sel).all()
        if elems:
            print(f"\n  [找到] {sel} ({len(elems)}个):")
            try:
                print(elems[0].inner_html()[:500])
            except:
                pass

    print("\n=== li.info-item (旧选择器) ===")
    items = page.locator("li.info-item").all()
    print(f"  共 {len(items)} 个")
    for it in items[:3]:
        try:
            print(" ", it.inner_text())
        except:
            pass

    print("\n=== 面包屑 nav ===")
    for sel in ["nav.breadcrumb", 'nav[aria-label*="bread"]', ".breadcrumb", '[class*="breadcrumb"]']:
        elems = page.locator(sel).all()
        if elems:
            print(f"  [{sel}] {len(elems)}个:")
            try:
                print(" ", elems[0].inner_text()[:200])
            except:
                pass

    print("\n=== 标签 a.afd-tag ===")
    tags = page.locator("a.afd-tag").all()
    if tags:
        print(f"  找到 {len(tags)} 个标签")
        for t in tags[:5]:
            try:
                print("  ", t.inner_text())
            except:
                pass
    else:
        # 尝试找其他标签选择器
        for sel in ['[class*="tag"]', '[class*="category"]', ".afd-taxonomies", '[class*="taxonom"]']:
            elems = page.locator(sel).all()
            if elems:
                print(f"  [{sel}] {len(elems)}个:")
                try:
                    print(" ", elems[0].inner_text()[:200])
                except:
                    pass

    print("\n=== page title/h1 ===")
    try:
        print(" ", page.locator("h1").first.inner_text()[:100])
    except:
        pass

    # 倾印整页文字中含"面积"、"年份"、"地点"的片段
    print("\n=== 全文搜索关键词 ===")
    body = page.inner_text("body")
    import re

    for kw in ["面积", "年份", "地点", "竣工", "建筑面积", "Area", "Year", "Location"]:
        idx = body.find(kw)
        if idx >= 0:
            snippet = body[max(0, idx - 20) : idx + 80].replace("\n", " ")
            print(f"  [{kw}]: ...{snippet}...")

    # 找所有 dt/dd 配对
    print("\n=== dt/dd 键值对 ===")
    dts = page.locator("dt").all()
    dds = page.locator("dd").all()
    for i, (dt, dd) in enumerate(zip(dts[:15], dds[:15])):
        try:
            print(f"  {dt.inner_text().strip()}: {dd.inner_text().strip()}")
        except:
            pass

    browser.close()

print("\n=== 探查完成 ===")
