"""第三轮：精确找 afd-specs__item 内部结构"""
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

    print("=== afd-specs __header-location ===")
    try:
        loc = page.locator(".afd-specs__header-location").first.inner_text()
        print(repr(loc))
    except Exception as e:
        print(f"ERROR: {e}")

    print("\n=== afd-specs__item (全部) ===")
    items = page.locator(".afd-specs__item").all()
    print(f"共 {len(items)} 个")
    for it in items:
        try:
            print(f"  >>> {it.inner_text().strip()!r}")
            print(f"      HTML: {it.inner_html()[:200]}")
        except:
            pass

    print("\n=== afd-char-list 全部 ===")
    items2 = page.locator(".afd-char-list li").all()
    print(f"共 {len(items2)} 个")
    for it in items2[:15]:
        try:
            print(f"  {it.inner_text().strip()!r}")
        except:
            pass

    print("\n=== 面包屑详细 ([class*=breadcrumb] a) ===")
    items3 = page.locator('[class*="breadcrumb"] a').all()
    for i, it in enumerate(items3):
        try:
            print(f"  [{i}] {it.inner_text().strip()!r}  href={it.get_attribute('href')}")
        except:
            pass

    print("\n=== [class*=tag] a (过滤分类标签) ===")
    tags = page.locator('[class*="tag"] a').all()
    for t in tags:
        try:
            href = t.get_attribute("href") or ""
            text = t.inner_text().strip()
            if text and ("categories" in href or "/tag/" in href):
                print(f"  {text!r}  {href}")
        except:
            pass

    browser.close()
print("=== 完成 ===")
