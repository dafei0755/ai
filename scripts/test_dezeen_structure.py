#!/usr/bin/env python3
"""测试Dezeen网站结构"""

import requests
from bs4 import BeautifulSoup
from pathlib import Path

# 测试一个Dezeen文章
test_url = "https://www.dezeen.com/2024/01/15/minimalist-house-japan-architecture/"

print(f"测试URL: {test_url}")
print("=" * 80)

try:
    response = requests.get(
        test_url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )

    print(f"状态码: {response.status_code}")

    soup = BeautifulSoup(response.content, "html.parser")

    # 查找标题
    title = soup.find("h1")
    print(f"\n标题: {title.get_text(strip=True) if title else 'Not found'}")

    # 查找文章内容
    article = soup.find("article")
    if article:
        print(f"✅ 找到article标签")

        # 查找描述
        paragraphs = article.find_all("p")
        print(f"✅ 找到 {len(paragraphs)} 个段落")

        if paragraphs:
            print(f"\n前3段预览:")
            for i, p in enumerate(paragraphs[:3], 1):
                text = p.get_text(strip=True)
                if text:
                    print(f"  {i}. {text[:100]}...")

    # 查找图片
    images = soup.find_all("img")
    print(f"\n✅ 找到 {len(images)} 张图片")

    # 查找建筑师信息
    architect_keywords = ["architect", "design", "studio", "firm"]
    for p in soup.find_all("p"):
        text = p.get_text().lower()
        if any(kw in text for kw in architect_keywords):
            print(f"\n可能的建筑师信息: {p.get_text(strip=True)[:200]}")
            break

    # 查找分类/标签
    categories = soup.find_all("a", class_=lambda x: x and ("category" in x.lower() or "tag" in x.lower()))
    if categories:
        print(f"\n分类/标签: {', '.join([c.get_text(strip=True) for c in categories[:5]])}")

    # 保存HTML用于分析
    output_file = Path(__file__).parent.parent / "data" / "dezeen_sample.html"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(soup.prettify())

    print(f"\n✅ HTML已保存到: {output_file}")

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback

    traceback.print_exc()
