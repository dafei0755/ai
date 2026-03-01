"""
调试 Gooood 分类页面HTML
"""

import requests
from bs4 import BeautifulSoup

url = "https://www.gooood.cn/category/type/architecture/page/1"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

print(f"访问: {url}\n")

response = requests.get(url, headers=headers, timeout=30)
print(f"状态码: {response.status_code}\n")

soup = BeautifulSoup(response.text, "html.parser")

# 查找article标签
articles = soup.find_all("article")
print(f"找到 {len(articles)} 个 <article> 标签\n")

if articles:
    # 显示第一个article
    first = articles[0]
    print("第一个article:")
    print(f"  类名: {first.get('class', [])}")
    print(f"  HTML (前1500字符):\n{str(first)[:1500]}\n")

    # 查找链接
    links = first.find_all("a")
    print(f"\n包含 {len(links)} 个链接:")
    for link in links:
        href = link.get("href", "")
        title = link.get("title", "")
        text = link.get_text(strip=True)[:50]
        if href:
            print(f"  - href: {href}")
            if title:
                print(f"    title: {title}")
            if text:
                print(f"    text: {text}")

    # 查找所有article的类名（去重）
    print(f"\n所有article类名:")
    classes = set()
    for article in articles[:20]:
        article_classes = article.get("class", [])
        if article_classes:
            classes.add(tuple(article_classes))

    for cls in classes:
        print(f"  - {list(cls)}")
else:
    print("未找到article标签，查找其他容器...")

    # 查找可能的项目容器
    containers = soup.find_all(
        ["div", "li"],
        class_=lambda x: x and ("item" in str(x).lower() or "post" in str(x).lower() or "article" in str(x).lower()),
    )
    print(f"\n找到 {len(containers)} 个可能的项目容器\n")

    if containers:
        first = containers[0]
        print(f"第一个容器:")
        print(f"  标签: {first.name}")
        print(f"  类名: {first.get('class', [])}")
        print(f"  HTML:\n{str(first)[:1000]}\n")

# 检查页面主体
print("\n" + "=" * 80)
print("页面主体内容检查")
print("=" * 80)

body = soup.find("body")
if body:
    # 查找主内容区域
    main_areas = body.find_all(
        ["div", "main", "section"],
        class_=lambda x: x
        and ("content" in str(x).lower() or "main" in str(x).lower() or "container" in str(x).lower()),
    )
    print(f"\n找到 {len(main_areas)} 个主内容区域\n")

    for i, area in enumerate(main_areas[:3], 1):
        print(f"主内容区域 {i}:")
        print(f"  标签: {area.name}")
        print(f"  类名: {area.get('class', [])}")
        print(f"  ID: {area.get('id', 'N/A')}")

        # 统计子元素
        children = list(area.children)
        print(f"  子元素数: {len([c for c in children if c.name])}")
        print()

# 查找所有img标签（通常项目卡片会有图片）
images = soup.find_all("img", src=True)
print(f"\n找到 {len(images)} 个图片\n")
if images:
    print("前5个图片:")
    for img in images[:5]:
        src = img.get("src", "")
        alt = img.get("alt", "")
        print(f"  - {src[:80]}")
        if alt:
            print(f"    alt: {alt}")

# 输出body的前5000字符
print("\n" + "=" * 80)
print("Body内容预览 (前5000字符)")
print("=" * 80)
print(str(body)[:5000])
