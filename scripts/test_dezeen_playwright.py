#!/usr/bin/env python3
"""使用Playwright测试Dezeen"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time


def test_dezeen_with_playwright():
    """测试Dezeen文章页面"""

    print("启动Playwright...")
    print("=" * 80)

    # 使用已知的Dezeen文章URL（尝试多个URL）
    test_urls = [
        "https://www.dezeen.com/architecture/",  # 首页
        "https://www.dezeen.com/2024/01/08/best-architecture-january-2024/",
        "https://www.dezeen.com/2023/12/22/best-houses-2023/",
    ]

    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for url in test_urls:
            try:
                print(f"\n测试URL: {url}")
                print("-" * 80)

                # 访问页面
                response = page.goto(url, wait_until="networkidle", timeout=30000)

                print(f"状态码: {response.status}")

                if response.status == 200:
                    print("✅ 成功访问！")

                    # 等待内容加载
                    time.sleep(2)

                    # 获取HTML
                    html = page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    # 提取标题
                    title = soup.find("h1") or soup.find("title")
                    if title:
                        print(f"\n📌 标题: {title.get_text(strip=True)[:100]}")

                    # 如果是列表页面
                    if "/architecture/" in url or url.endswith(".com/"):
                        print("\n🗂️ 这是列表页面")

                        # 查找文章链接
                        articles = soup.find_all("article") or soup.find_all(
                            "div", class_=lambda x: x and "post" in x.lower() if x else False
                        )
                        print(f"找到 {len(articles)} 个article元素")

                        # 提取链接
                        article_links = []
                        for article in articles[:5]:  # 只看前5个
                            link = article.find("a", href=True)
                            if link:
                                href = link["href"]
                                # 只要文章链接（包含日期格式 /2024/01/08/）
                                if "/20" in href and href.count("/") >= 5:
                                    if href.startswith("http"):
                                        article_links.append(href)
                                    else:
                                        article_links.append(f"https://www.dezeen.com{href}")

                        print(f"\n找到 {len(article_links)} 个文章链接:")
                        for i, link in enumerate(article_links[:3], 1):
                            print(f"  {i}. {link}")

                        # 如果找到文章，测试第一篇
                        if article_links:
                            print(f"\n{'='*80}")
                            print("测试第一篇文章详情...")
                            print(f"{'='*80}")

                            article_url = article_links[0]
                            page.goto(article_url, wait_until="networkidle", timeout=30000)
                            time.sleep(2)

                            html = page.content()
                            soup = BeautifulSoup(html, "html.parser")

                            # 标题
                            h1 = soup.find("h1")
                            if h1:
                                print(f"\n📌 标题: {h1.get_text(strip=True)}")

                            # 文章主体
                            article_body = (
                                soup.find("div", class_=lambda x: x and "post-content" in x.lower() if x else False)
                                or soup.find("div", class_=lambda x: x and "entry-content" in x.lower() if x else False)
                                or soup.find("article")
                            )

                            if article_body:
                                # 段落
                                paragraphs = article_body.find_all("p")
                                valid_p = [p for p in paragraphs if len(p.get_text(strip=True)) > 50]

                                print(f"✅ 有效段落: {len(valid_p)}")

                                if valid_p:
                                    desc = "\n\n".join([p.get_text(strip=True) for p in valid_p[:2]])
                                    print(f"\n描述预览:\n{desc[:400]}...")

                                # 图片
                                images = article_body.find_all("img")
                                print(f"✅ 图片: {len(images)} 张")

                                # 元数据
                                print("\n元数据:")

                                # 建筑师/设计师
                                architect = soup.find("meta", {"property": "author"})
                                if architect:
                                    print(f"  建筑师: {architect.get('content', 'N/A')}")

                                # 日期
                                date_elem = soup.find("time") or soup.find(
                                    "meta", {"property": "article:published_time"}
                                )
                                if date_elem:
                                    date_text = (
                                        date_elem.get("datetime")
                                        or date_elem.get("content")
                                        or date_elem.get_text(strip=True)
                                    )
                                    print(f"  日期: {date_text}")

                                # 分类
                                categories = soup.find_all(
                                    "a", class_=lambda x: x and "cat" in x.lower() if x else False
                                )[:3]
                                if categories:
                                    cat_names = [c.get_text(strip=True) for c in categories]
                                    print(f"  分类: {', '.join(cat_names)}")

                            break  # 成功测试，退出循环

                    else:
                        # 详情页面
                        print("\n📄 这是详情页面")

                        article = soup.find("article")
                        if article:
                            # 段落
                            paragraphs = article.find_all("p")
                            valid_p = [p for p in paragraphs if len(p.get_text(strip=True)) > 50]
                            print(f"✅ 有效段落: {len(valid_p)}")

                            if valid_p:
                                desc = "\n\n".join([p.get_text(strip=True) for p in valid_p[:2]])
                                print(f"\n描述预览:\n{desc[:400]}...")

                            # 图片
                            images = article.find_all("img")
                            print(f"✅ 图片: {len(images)} 张")

                    break  # 成功测试，退出循环

                else:
                    print(f"❌ 状态码: {response.status}")

            except Exception as e:
                print(f"❌ 错误: {e}")
                continue

        browser.close()

    print(f"\n{'='*80}")
    print("测试完成")


if __name__ == "__main__":
    test_dezeen_with_playwright()
