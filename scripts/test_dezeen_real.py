#!/usr/bin/env python3
"""测试Dezeen真实文章"""

import requests
from bs4 import BeautifulSoup
import time

# 先访问首页获取最新文章链接
print("访问Dezeen首页...")
print("=" * 80)

try:
    response = requests.get(
        "https://www.dezeen.com/architecture/",
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )

    print(f"首页状态码: {response.status_code}")

    soup = BeautifulSoup(response.content, "html.parser")

    # 查找文章链接
    articles = soup.find_all("article")[:3]  # 前3篇

    if not articles:
        # 尝试其他方式找文章
        articles = soup.find_all("div", class_=lambda x: x and "post" in x.lower())[:3]

    print(f"找到 {len(articles)} 篇文章\n")

    # 提取第一篇文章URL
    article_url = None
    for article in articles:
        link = article.find("a", href=True)
        if link:
            href = link["href"]
            if href.startswith("http") and "dezeen.com" in href and "/20" in href:
                article_url = href
                print(f"找到文章: {href}")
                break

    if not article_url:
        print("未找到有效文章链接，使用已知文章")
        # 使用Dezeen的经典文章
        article_url = "https://www.dezeen.com/2024/12/20/best-architecture-2024/"

    print(f"\n{'='*80}")
    print(f"测试文章: {article_url}")
    print(f"{'='*80}\n")

    time.sleep(2)

    # 爬取文章详情
    response = requests.get(
        article_url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )

    print(f"文章状态码: {response.status_code}")

    soup = BeautifulSoup(response.content, "html.parser")

    # 标题
    title = soup.find("h1") or soup.find("title")
    print(f"\n📌 标题: {title.get_text(strip=True) if title else 'Not found'}")

    # 查找文章主体
    article_body = (
        soup.find("div", class_=lambda x: x and "post-content" in x.lower() if x else False)
        or soup.find("div", class_=lambda x: x and "entry-content" in x.lower() if x else False)
        or soup.find("article")
    )

    if article_body:
        print(f"✅ 找到文章主体")

        # 段落
        paragraphs = article_body.find_all("p")
        valid_paragraphs = [p for p in paragraphs if len(p.get_text(strip=True)) > 50]

        print(f"✅ 有效段落: {len(valid_paragraphs)}")

        if valid_paragraphs:
            print(f"\n描述预览（前500字符）:")
            desc = "\n\n".join([p.get_text(strip=True) for p in valid_paragraphs[:3]])
            print(desc[:500])

        # 图片
        images = article_body.find_all("img")
        print(f"\n✅ 图片: {len(images)} 张")

        if images:
            print(f"图片URL示例:")
            for img in images[:3]:
                src = img.get("src", "") or img.get("data-src", "")
                if src:
                    print(f"  - {src}")

    # 元数据
    print(f"\n{'='*80}")
    print("元数据:")

    # 建筑师
    author = soup.find("meta", {"name": "author"}) or soup.find(
        "span", class_=lambda x: x and "author" in x.lower() if x else False
    )
    if author:
        print(f"  作者/建筑师: {author.get('content' if author.name == 'meta' else 'text', 'N/A')}")

    # 日期
    date_meta = soup.find("meta", {"property": "article:published_time"}) or soup.find("time")
    if date_meta:
        date_value = date_meta.get("content") if date_meta.name == "meta" else date_meta.get_text(strip=True)
        print(f"  发布日期: {date_value}")

    # 分类
    categories = soup.find_all("a", href=lambda x: x and "/tag/" in x or "/category/" in x if x else False)[:5]
    if categories:
        cat_names = [c.get_text(strip=True) for c in categories]
        print(f"  分类/标签: {', '.join(cat_names)}")

    print(f"\n✅ 测试完成")

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback

    traceback.print_exc()
