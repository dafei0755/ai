"""
调试单个项目的HTML结构
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
from bs4 import BeautifulSoup

# 测试一个真实的建筑项目URL（不是专辑）
url = "https://www.gooood.cn/overseas-mingrui-jiang.htm"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

print(f"访问: {url}\n")

response = requests.get(url, headers=headers, timeout=30)
soup = BeautifulSoup(response.text, "html.parser")

print("=" * 80)
print("查找entry-content")
print("=" * 80)

# 查找entry-content
content_div = soup.find("div", class_="entry-content")
if content_div:
    print(f"\n✅ 找到 entry-content div\n")

    # 查找段落
    paragraphs = content_div.find_all("p")
    print(f"找到 {len(paragraphs)} 个 <p> 标签\n")

    if paragraphs:
        print("前5个段落内容:")
        for i, p in enumerate(paragraphs[:5], 1):
            text = p.get_text(strip=True)
            print(f"\n段落 {i} (长度: {len(text)}):")
            print(f"  {text[:200]}")

    # 显示entry-content的HTML结构（前2000字符）
    print("\n" + "=" * 80)
    print("entry-content HTML结构（前2000字符）")
    print("=" * 80)
    print(str(content_div)[:2000])
else:
    print("\n❌ 未找到 entry-content div\n")

    # 查找可能的内容容器
    possible_containers = soup.find_all(
        "div", class_=lambda x: x and ("content" in str(x).lower() or "article" in str(x).lower())
    )
    print(f"找到 {len(possible_containers)} 个可能的内容容器\n")

    for i, container in enumerate(possible_containers[:3], 1):
        print(f"容器 {i}:")
        print(f"  类名: {container.get('class', [])}")
        print(f"  子元素数: {len(list(container.children))}")
        print()
