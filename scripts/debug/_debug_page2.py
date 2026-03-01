"""第二轮探查：找年份、面积、地点的具体 HTML"""
import sys, io

sys.path.insert(0, r"d:\11-20\langgraph-design")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

TEST_URL = "https://www.archdaily.cn/cn/1038638/tian-kong-gong-yu-sanjay-puri-architects"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(TEST_URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)

    # 面包屑详细
    print("=== 面包屑 a 标签 ===")
    for sel in ['[class*="breadcrumb"] a', '[class*="breadcrumb"] li', '[class*="breadcrumb"] span']:
        items = page.locator(sel).all()
        if items:
            print(f"[{sel}] {len(items)}个:")
            for it in items:
                try:
                    print(f"  '{it.inner_text().strip()}'")
                except:
                    pass

    # 标签详细
    print("\n=== 标签详细 ===")
    for sel in ['[class*="tag"] a', 'a[class*="tag"]', ".afd-tag", 'a[href*="/tag/"]', 'a[href*="/cn/search/"]']:
        items = page.locator(sel).all()
        if items:
            print(f"[{sel}] {len(items)}个:")
            for it in items[:8]:
                try:
                    print(f"  '{it.inner_text().strip()}' href={it.get_attribute('href', timeout=1000)}")
                except:
                    pass
            break

    # 找包含数字的规格块
    print("\n=== 规格/元数据 块 ===")
    for sel in [
        ".afd-project-info",
        '[class*="project-info"]',
        '[class*="specs"]',
        '[class*="spec-"]',
        ".afd-related",
        '[class*="data"]',
        "table",
        ".afd-sidebar",
        '[class*="sidebar"]',
        '[class*="meta"]',
        ".afd-project-specs-list",
        'ul[class*="info"]',
        'dl[class*="spec"]',
    ]:
        items = page.locator(sel).all()
        if items:
            print(f"\n[{sel}] {len(items)}个, 首个HTML:")
            try:
                html = items[0].inner_html()[:400]
                print(html)
            except:
                pass

    # 查含年份和面积关键词的文本
    print("\n=== 含关键词的可见文本 (前200行) ===")
    try:
        lines = page.inner_text("body").split("\n")
        kws = ["面积", "年份", "地点", "竣工", "年", "㎡", "m²", "sqm", "Area", "Year", "Location", r"\d{4}"]
        import re

        for i, line in enumerate(lines[:300]):
            line = line.strip()
            if line and any(re.search(kw, line, re.IGNORECASE) for kw in kws):
                if len(line) < 100:
                    print(f"  L{i}: {line}")
    except Exception as e:
        print(f"ERROR: {e}")

    browser.close()

print("\n=== 完成 ===")
