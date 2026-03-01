#!/usr/bin/env python3
"""调试description内容完整性"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright
import requests
from bs4 import BeautifulSoup
import time


def debug_description_extraction(url: str):
    """对比静态和动态提取的description"""

    print(f"\n{'='*80}")
    print(f"调试URL: {url}")
    print(f"{'='*80}\n")

    # 方法1: Playwright
    print("方法1: Playwright提取")
    print("-" * 80)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_selector("div.client-render", timeout=10000)
        page.wait_for_timeout(2000)

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    # 提取entry-content区域
    entry_content = soup.find("div", class_="entry-content")
    if entry_content:
        print(f"✅ 找到 entry-content")

        # 查看client-render内容
        client_render = entry_content.find("div", class_="client-render")
        if client_render:
            print(f"✅ 找到 client-render div")

            # 提取所有段落
            paragraphs = client_render.find_all("p")
            print(f"\n找到 {len(paragraphs)} 个段落:")

            total_chars = 0
            for idx, p in enumerate(paragraphs, 1):
                text = p.get_text(strip=True)
                if text and text != "收藏本文":  # 跳过无关段落
                    print(f"\n段落 {idx} (长度: {len(text)}):")
                    print(f"  {text[:200]}..." if len(text) > 200 else f"  {text}")
                    total_chars += len(text)

            print(f"\n总字符数: {total_chars}")

            # 查看是否有其他内容容器
            print("\n" + "-" * 80)
            print("检查其他可能的内容容器:")

            # 检查所有div
            divs = client_render.find_all("div", recursive=False)
            print(f"找到 {len(divs)} 个直接子div")

            for idx, div in enumerate(divs, 1):
                classes = div.get("class", [])
                print(f"  Div {idx}: class={classes}")
                inner_p = div.find_all("p")
                if inner_p:
                    print(f"    → 包含 {len(inner_p)} 个段落")

            # 提取所有文本（包括嵌套的）
            print("\n" + "-" * 80)
            print("提取所有文本内容（包括嵌套）:")
            all_text = client_render.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in all_text.split("\n") if line.strip() and line.strip() != "收藏本文"]

            print(f"总行数: {len(lines)}")
            print(f"总字符数: {sum(len(line) for line in lines)}")

            if len(lines) > 0:
                print("\n前5行内容:")
                for line in lines[:5]:
                    print(f"  {line[:100]}..." if len(line) > 100 else f"  {line}")
        else:
            print("❌ 未找到 client-render div")
    else:
        print("❌ 未找到 entry-content")

    # 检查HTML结构
    print("\n" + "=" * 80)
    print("HTML结构分析:")
    print("-" * 80)

    # 保存完整HTML到文件
    output_file = Path(__file__).parent.parent / "data" / "debug_html.html"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"完整HTML已保存到: {output_file}")

    # 查看client-render的完整结构
    if entry_content and client_render:
        print("\nclient-render完整HTML结构:")
        print(client_render.prettify()[:2000])


if __name__ == "__main__":
    # 测试URL
    test_url = "https://www.gooood.cn/overseas-mingrui-jiang.htm"

    debug_description_extraction(test_url)
