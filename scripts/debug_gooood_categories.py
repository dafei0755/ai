"""
调试 Gooood 分类结构
"""

import requests
from bs4 import BeautifulSoup

url = "https://www.gooood.cn"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

print(f"访问: {url}\n")

response = requests.get(url, headers=headers, timeout=30)
print(f"状态码: {response.status_code}\n")

soup = BeautifulSoup(response.text, "html.parser")

# 查找导航菜单
print("=" * 80)
print("查找分类导航")
print("=" * 80)

# 查找导航栏
nav_items = soup.find_all(
    ["nav", "ul", "div"], class_=lambda x: x and ("menu" in str(x).lower() or "nav" in str(x).lower())
)

print(f"\n找到 {len(nav_items)} 个可能的导航容器\n")

for i, nav in enumerate(nav_items[:5], 1):
    print(f"\n导航容器 {i}:")
    print(f"  标签: {nav.name}")
    print(f"  类名: {nav.get('class', [])}")

    # 查找链接
    links = nav.find_all("a", href=True)
    if links:
        print(f"  包含 {len(links)} 个链接:")
        for link in links[:10]:
            href = link.get("href", "")
            text = link.get_text(strip=True)
            if text and href:
                print(f"    - {text}: {href}")

# 直接查找所有包含"category"的链接
print("\n" + "=" * 80)
print("所有包含 'category' 的链接")
print("=" * 80)

all_links = soup.find_all("a", href=lambda x: x and "category" in x.lower())
print(f"\n找到 {len(all_links)} 个分类链接\n")

categories = {}
for link in all_links[:20]:
    href = link.get("href", "")
    text = link.get_text(strip=True)
    if text and href:
        categories[text] = href
        print(f"  {text}: {href}")

# 查找主菜单
print("\n" + "=" * 80)
print("主菜单项")
print("=" * 80)

menu = soup.find("ul", id=lambda x: x and "menu" in str(x).lower())
if menu:
    print(f"\n找到主菜单: {menu.get('id')}\n")
    menu_items = menu.find_all("li")
    for item in menu_items[:15]:
        link = item.find("a")
        if link:
            href = link.get("href", "")
            text = link.get_text(strip=True)
            print(f"  {text}: {href}")
else:
    print("\n未找到id包含'menu'的主菜单，尝试其他方式...\n")

    # 查找所有li > a结构
    all_menu_links = []
    for li in soup.find_all("li")[:50]:
        link = li.find("a", href=True)
        if link:
            href = link.get("href", "")
            text = link.get_text(strip=True)
            if text and href and ("gooood.cn" in href or href.startswith("/")):
                if len(text) < 20:  # 菜单项通常较短
                    all_menu_links.append((text, href))

    # 去重
    seen = set()
    unique_links = []
    for text, href in all_menu_links:
        if href not in seen:
            seen.add(href)
            unique_links.append((text, href))

    print(f"找到 {len(unique_links)} 个可能的菜单链接:\n")
    for text, href in unique_links[:30]:
        print(f"  {text}: {href}")

# 保存完整HTML（前10000字符）
print("\n" + "=" * 80)
print("HTML结构预览")
print("=" * 80)
print(str(soup)[:5000])
