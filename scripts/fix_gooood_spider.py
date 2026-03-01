#!/usr/bin/env python3
"""修复gooood_spider.py文件"""

import re

# 读取文件
with open(
    r"d:\11-20\langgraph-design\intelligent_project_analyzer\external_data_system\spiders\gooood_spider.py",
    "r",
    encoding="utf-8",
) as f:
    content = f.read()

# 修复1: 替换_extract_description方法，移除[:10]限制
old_desc_method = r'''def _extract_description\(self, soup: BeautifulSoup\) -> str:
        """提取项目描述"""
        # Gooood 的内容在 <div class="entry-content">
        content_div = soup\.find\('div', class_='entry-content'\)

        if not content_div:
            return ""

        # 提取所有段落文本
        paragraphs = \[\]
        for p in content_div\.find_all\('p'\):
            text = p\.get_text\(strip=True\)
            if text and len\(text\) > 20:  # 过滤短段落
                paragraphs\.append\(text\)

        return '\\n\\n'\.join\(paragraphs\[:10\]\)  # 最多10段'''

new_desc_method = '''def _extract_description(self, soup: BeautifulSoup) -> str:
        """提取项目描述"""
        # Gooood 的内容在 <div class="entry-content">
        content_div = soup.find('div', class_='entry-content')

        if not content_div:
            return ""

        # 提取所有段落文本
        paragraphs = []
        for p in content_div.find_all('p'):
            text = p.get_text(strip=True)
            # 过滤短段落和无关内容
            if text and len(text) > 20 and text not in ['收藏本文', 'Collect this article']:
                paragraphs.append(text)

        # 返回所有段落，不再限制数量
        return '\\n\\n'.join(paragraphs)'''

# 执行替换
new_content = re.sub(old_desc_method, new_desc_method, content, flags=re.MULTILINE)

# 检查是否成功
if new_content != content:
    print("✅ 成功替换_extract_description方法")

    # 写入文件
    with open(
        r"d:\11-20\langgraph-design\intelligent_project_analyzer\external_data_system\spiders\gooood_spider.py",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(new_content)

    print("✅ 文件已更新")
else:
    print("❌ 未找到匹配的内容，尝试手动修复")

    # 查找paragraphs[:10]
    if "paragraphs[:10]" in content:
        print("找到 'paragraphs[:10]'，执行简单替换")
        new_content = content.replace(
            "return '\\n\\n'.join(paragraphs[:10])  # 最多10段",
            "# 返回所有段落，不再限制数量\\n        return '\\n\\n'.join(paragraphs)",
        )

        # 同时添加过滤无关内容
        new_content = new_content.replace(
            "if text and len(text) > 20:  # 过滤短段落",
            "# 过滤短段落和无关内容\\n            if text and len(text) > 20 and text not in ['收藏本文', 'Collect this article']:",
        )

        with open(
            r"d:\11-20\langgraph-design\intelligent_project_analyzer\external_data_system\spiders\gooood_spider.py",
            "w",
            encoding="utf-8",
        ) as f:
            f.write(new_content)

        print("✅ 简单替换成功")
    else:
        print("文件可能已修改或损坏")
