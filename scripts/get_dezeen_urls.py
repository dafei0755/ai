#!/usr/bin/env python3
"""从Dezeen获取真实文章URL"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re


def get_real_dezeen_urls():
    """访问Dezeen获取真实文章URL"""

    print("使用Playwright访问Dezeen...")
    print("=" * 80)

    # 尝试多个入口点
    entry_urls = [
        "https://www.dezeen.com/",  # 首页
        "https://www.dezeen.com/architecture/",  # 建筑分类
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080},
        )

        page = context.new_page()

        # 隐藏自动化特征
        page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
        )

        for url in entry_urls:
            print(f"\n访问: {url}")
            print("-" * 80)

            try:
                # 降低期望，只等待部分加载
                response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
                print(f"状态码: {response.status if response else 'None'}")

                if response and response.status == 200:
                    print("✅ 页面加载成功")

                    # 等待一些内容加载
                    import time

                    time.sleep(5)

                    # 获取HTML
                    html = page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    # 保存HTML用于分析
                    with open("data/dezeen_homepage.html", "w", encoding="utf-8") as f:
                        f.write(html)
                    print("✅ HTML已保存到: data/dezeen_homepage.html")

                    # 提取文章链接
                    print("\n查找文章链接...")

                    article_links = []

                    # 查找所有链接
                    for link in soup.find_all("a", href=True):
                        href = link.get("href", "")

                        # Dezeen文章URL格式: /2023/12/22/project-title/
                        if re.search(r"/\d{4}/\d{2}/\d{2}/[\w-]+/?$", href):
                            # 构建完整URL
                            if href.startswith("http"):
                                full_url = href
                            else:
                                full_url = f"https://www.dezeen.com{href}"

                            # 获取文章标题
                            title = link.get_text(strip=True) or link.get("title", "") or "(无标题)"

                            article_links.append({"url": full_url, "title": title})

                    # 去重
                    unique_links = {}
                    for item in article_links:
                        if item["url"] not in unique_links:
                            unique_links[item["url"]] = item

                    print(f"\n找到 {len(unique_links)} 个唯一文章链接:")
                    print("=" * 80)

                    for i, (url, item) in enumerate(list(unique_links.items())[:10], 1):
                        print(f"{i}. {item['title'][:60]}")
                        print(f"   {url}")
                        print()

                    # 保存链接到文件
                    with open("data/dezeen_article_urls.txt", "w", encoding="utf-8") as f:
                        for url, item in unique_links.items():
                            f.write(f"{url}\t{item['title']}\n")
                    print(f"✅ 链接已保存到: data/dezeen_article_urls.txt")

                    browser.close()
                    return list(unique_links.keys())[:10]  # 返回前10个

                elif response and response.status == 403:
                    print("❌ 403 Forbidden - 被反爬虫拦截")
                    continue

            except Exception as e:
                print(f"❌ 错误: {e}")
                continue

        browser.close()
        print("\n所有入口点都失败")
        return []


if __name__ == "__main__":
    urls = get_real_dezeen_urls()

    if urls:
        print("\n" + "=" * 80)
        print("成功获取文章URL，可以使用这些进行测试:")
        print("=" * 80)
        for url in urls[:5]:
            print(f'python scripts/test_dezeen_single.py --url "{url}"')
    else:
        print("\n未能获取有效URL")
