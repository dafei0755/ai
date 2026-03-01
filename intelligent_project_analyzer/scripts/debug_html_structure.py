"""
调试爬虫HTML结构

用于查看目标网站的实际HTML结构，帮助优化选择器

Author: AI Architecture Team
Version: v8.110.0
Date: 2026-02-17
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Archdaily
print("=" * 80)
print("🔍 Archdaily HTML结构分析")
print("=" * 80)

url = "https://www.archdaily.cn/cn/search/cn/projects/categories/houses?page=1"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

try:
    response = requests.get(url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, "html.parser")

    # 1. 查找所有article标签
    articles = soup.find_all("article")
    print(f"\n1. Articles找到: {len(articles)} 个")
    if articles:
        print(f"   第1个article classes: {articles[0].get('class')}")
        print(f"   第1个article内容预览:\n{str(articles[0])[:500]}...\n")

    # 2. 查找所有包含/cn/数字的链接
    links = soup.find_all("a", href=True)
    project_links = [l for l in links if "/cn/" in l.get("href", "") and any(c.isdigit() for c in l.get("href", ""))]
    print(f"\n2. 包含/cn/数字的链接: {len(project_links)} 个")
    if project_links:
        for i, link in enumerate(project_links[:5], 1):
            href = link.get("href")
            text = link.get_text(strip=True)[:50]
            print(f"   {i}. {href}")
            print(f"      文本: {text}")

    # 3. 查找所有class包含project/item/card的元素
    elements = soup.find_all(
        class_=lambda x: x and any(k in str(x).lower() for k in ["project", "item", "card", "post"])
    )
    print(f"\n3. Class包含project/item/card的元素: {len(elements)} 个")
    if elements:
        print(f"   第1个元素: {elements[0].name}, class={elements[0].get('class')}")
        print(f"   内容预览:\n{str(elements[0])[:300]}...\n")

    # 4. 保存完整HTML以供检查
    with open("d:/11-20/langgraph-design/_debug_archdaily.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    print("✅ 完整HTML已保存到: d:/11-20/langgraph-design/_debug_archdaily.html")

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback

    traceback.print_exc()

# Gooood
print("\n" + "=" * 80)
print("🔍 Gooood HTML结构分析")
print("=" * 80)

url = "https://www.gooood.cn/residential/page/1/"

try:
    response = requests.get(url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, "html.parser")

    # 1. 查找所有article标签
    articles = soup.find_all("article")
    print(f"\n1. Articles找到: {len(articles)} 个")
    if articles:
        print(f"   第1个article classes: {articles[0].get('class')}")
        print(f"   第1个article内容预览:\n{str(articles[0])[:500]}...\n")

    # 2. 查找所有指向gooood.cn的链接
    links = soup.find_all("a", href=True)
    project_links = [l for l in links if "gooood.cn" in l.get("href", "") and l.get("href", "").count("/") == 3]
    print(f"\n2. 项目链接（gooood.cn/xxx）: {len(project_links)} 个")
    if project_links:
        for i, link in enumerate(project_links[:5], 1):
            href = link.get("href")
            text = link.get_text(strip=True)[:50]
            print(f"   {i}. {href}")
            print(f"      文本: {text}")

    # 3. 查找所有class包含post/project/item的元素
    elements = soup.find_all(
        class_=lambda x: x and any(k in str(x).lower() for k in ["post", "project", "item", "entry"])
    )
    print(f"\n3. Class包含post/project/item的元素: {len(elements)} 个")
    if elements:
        print(f"   第1个元素: {elements[0].name}, class={elements[0].get('class')}")
        print(f"   内容预览:\n{str(elements[0])[:300]}...\n")

    # 4. 保存完整HTML
    with open("d:/11-20/langgraph-design/_debug_gooood.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    print("✅ 完整HTML已保存到: d:/11-20/langgraph-design/_debug_gooood.html")

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 80)
print("📝 下一步:")
print("   1. 检查保存的HTML文件")
print("   2. 根据实际结构更新选择器")
print("   3. 重新运行爬虫测试")
print("=" * 80)
