"""
博查 API 验证脚本 (v7.160)

验证博查API端点的可用性：
1. Web Search API - 网页搜索
2. Image Search API - 图片搜索（验证是否存在）
3. Web Search 响应中的 images 字段

运行: python scripts/verify_bocha_api.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import httpx


def verify_bocha_api():
    """验证博查API端点"""

    api_key = os.getenv("BOCHA_API_KEY", "")

    print("=" * 70)
    print("🔍 博查 API 端点验证")
    print("=" * 70)

    if not api_key or api_key == "your_bocha_api_key":
        print("\n❌ 请先在 .env 中配置 BOCHA_API_KEY")
        print("   获取地址: https://open.bochaai.com/")
        return

    print(f"\n📋 API Key: {api_key[:10]}...{api_key[-4:]}")

    # 测试两个可能的域名
    domains = [
        "https://api.bochaai.com",
        "https://api.bocha.cn",
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    test_query = "日本茶庭设计"

    for domain in domains:
        print(f"\n{'=' * 70}")
        print(f"🌐 测试域名: {domain}")
        print("=" * 70)

        # ============================================
        # 1. 测试 Web Search API
        # ============================================
        print(f"\n1️⃣ Web Search API")
        print("-" * 40)

        web_url = f"{domain}/v1/web-search"
        web_payload = {
            "query": test_query,
            "count": 5,
            "freshness": "oneYear",
            "summary": True,
        }

        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(web_url, headers=headers, json=web_payload)

                print(f"   状态码: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    code = data.get("code")
                    print(f"   响应码: {code}")

                    if code == 200:
                        print(f"   ✅ Web Search 可用")

                        web_data = data.get("data", {})

                        # 检查返回的字段结构
                        print(f"\n   📦 响应字段:")
                        for key in web_data.keys():
                            print(f"      - {key}")

                        # 网页结果
                        web_pages = web_data.get("webPages", {}).get("value", [])
                        print(f"\n   📄 网页结果: {len(web_pages)} 条")

                        if web_pages:
                            first = web_pages[0]
                            print(f"      示例: {first.get('name', '')[:50]}...")
                            print(f"      URL: {first.get('url', '')[:60]}...")

                            # 检查单条结果中是否有图片字段
                            if "images" in first or "thumbnailUrl" in first or "image" in first:
                                print(f"      ⭐ 结果中包含图片字段!")

                        # 检查顶层是否有 images 字段
                        if "images" in web_data:
                            images = web_data.get("images", {})
                            if isinstance(images, dict):
                                image_values = images.get("value", [])
                                print(f"\n   🖼️ 图片结果 (顶层): {len(image_values)} 张")
                            elif isinstance(images, list):
                                print(f"\n   🖼️ 图片结果 (顶层): {len(images)} 张")
                        else:
                            print(f"\n   ⚠️ Web Search 响应中无 images 字段")
                    else:
                        print(f"   ❌ 错误: {data.get('msg', 'Unknown')}")
                else:
                    print(f"   ❌ HTTP 错误: {response.status_code}")
                    print(f"   {response.text[:200]}")

        except httpx.ConnectError as e:
            print(f"   ❌ 连接失败: {e}")
        except Exception as e:
            print(f"   ❌ 请求异常: {e}")

        # ============================================
        # 2. 测试 Image Search API (独立端点)
        # ============================================
        print(f"\n2️⃣ Image Search API (独立端点)")
        print("-" * 40)

        image_url = f"{domain}/v1/image-search"
        image_payload = {
            "query": test_query,
            "count": 5,
        }

        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(image_url, headers=headers, json=image_payload)

                print(f"   状态码: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    code = data.get("code")
                    print(f"   响应码: {code}")

                    if code == 200:
                        print(f"   ✅ Image Search 可用!")

                        image_data = data.get("data", {})

                        # 检查返回格式
                        if isinstance(image_data, dict):
                            images = image_data.get("images", image_data.get("value", []))
                        elif isinstance(image_data, list):
                            images = image_data
                        else:
                            images = []

                        print(f"   📸 图片数量: {len(images)}")

                        if images:
                            first = images[0] if isinstance(images[0], dict) else {}
                            print(f"   📦 图片字段: {list(first.keys())}")
                    else:
                        print(f"   ⚠️ API响应: {data.get('msg', 'Unknown')}")

                elif response.status_code == 404:
                    print(f"   ❌ 端点不存在 (404)")
                    print(f"   💡 建议: 从 Web Search 响应中提取图片")
                else:
                    print(f"   ❌ HTTP 错误: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"   {error_data.get('msg', response.text[:100])}")
                    except:
                        print(f"   {response.text[:100]}")

        except httpx.ConnectError as e:
            print(f"   ❌ 连接失败: {e}")
        except Exception as e:
            print(f"   ❌ 请求异常: {e}")

        # ============================================
        # 3. 测试 AI Search API
        # ============================================
        print(f"\n3️⃣ AI Search API")
        print("-" * 40)

        ai_url = f"{domain}/v1/ai-search"
        ai_payload = {
            "query": test_query,
        }

        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(ai_url, headers=headers, json=ai_payload)

                print(f"   状态码: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    print(f"   响应码: {data.get('code')}")
                    if data.get("code") == 200:
                        print(f"   ✅ AI Search 可用!")
                    else:
                        print(f"   ⚠️ {data.get('msg', 'Unknown')}")
                elif response.status_code == 404:
                    print(f"   ❌ 端点不存在 (404)")
                else:
                    print(f"   ❌ HTTP {response.status_code}")

        except Exception as e:
            print(f"   ❌ 请求异常: {e}")

    print("\n" + "=" * 70)
    print("✅ 验证完成")
    print("=" * 70)

    print("\n📋 建议:")
    print("   1. 使用返回 200 的域名")
    print("   2. 如果 Image Search 404，从 Web Search 提取图片")
    print("   3. 统一使用官方最新域名 api.bochaai.com")


if __name__ == "__main__":
    verify_bocha_api()
