"""
调试 Gooood HTML 结构
"""

import requests
from bs4 import BeautifulSoup

url = "https://www.gooood.cn/page/1"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

print(f"访问: {url}\n")

response = requests.get(url, headers=headers, timeout=30)
print(f"状态码: {response.status_code}")
print(f"编码: {response.encoding}\n")

soup = BeautifulSoup(response.text, "html.parser")

# 查找article标签
articles = soup.find_all("article")
print(f"找到 {len(articles)} 个 <article> 标签\n")

if articles:
    # 显示第一个article的结构
    first = articles[0]
    print("第一个article的类名:")
    print(f"  {first.get('class', [])}\n")

    # 查找标题
    title_tags = ["h2", "h3", "h1"]
    for tag in title_tags:
        titles = first.find_all(tag)
        if titles:
            print(f"找到 {len(titles)} 个 <{tag}> 标签:")
            for t in titles[:3]:
                print(f"  - {t.get_text(strip=True)[:50]}")
                print(f"    类名: {t.get('class', [])}")
            print()

    # 查找链接
    links = first.find_all("a")
    print(f"找到 {len(links)} 个 <a> 标签:")
    for link in links[:5]:
        href = link.get("href", "")
        text = link.get_text(strip=True)
        if href and "gooood.cn" in href or "/" in href:
            print(f"  - {href[:80]}")
            print(f"    文本: {text[:50]}")
    print()

    # 显示完整HTML（缩略）
    html_str = str(first)
    print(f"完整HTML (前1000字符):\n{html_str[:1000]}\n")
else:
    # 没有article标签，看看有什么
    print("没有找到article标签，查找其他结构...\n")

    # 查找可能的项目容器
    containers = soup.find_all("div", class_=lambda x: x and ("post" in str(x).lower() or "item" in str(x).lower()))
    print(f"找到 {len(containers)} 个可能的项目容器\n")

    if containers:
        first = containers[0]
        print(f"第一个容器类名: {first.get('class', [])}")
        print(f"HTML预览:\n{str(first)[:500]}\n")

    # 显示body的前2000字符
    body = soup.find("body")
    if body:
        print(f"\n<body> 内容预览 (前2000字符):")
        print(str(body)[:2000])
