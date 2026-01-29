"""
TikHub 集成测试脚本 (v2)
测试小红书、抖音、微信视频号搜索功能

根据 TikHub API 文档:
- 小红书: XiaohongshuWeb.search_notes (SDK)
- 抖音: /api/v1/douyin/search/fetch_video_search_v1 (HTTP, Douyin-Search-API)
- 视频号: /api/v1/wechat_channels/fetch_search_ordinary (HTTP, WeChat-Channels-API)
"""

import asyncio
import json
import os
import sys

import httpx

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from tikhub import Client


def main():
    api_key = os.getenv("BOCHA_TIKHUB_API_KEY")
    base_url = os.getenv("BOCHA_TIKHUB_BASE_URL", "https://api.tikhub.io")

    if not api_key:
        print("❌ Error: BOCHA_TIKHUB_API_KEY not found in .env")
        return

    print(f"✅ API Key: {api_key[:20]}...")
    print(f"✅ Base URL: {base_url}")

    c = Client(api_key=api_key, base_url=base_url)

    # HTTP headers for direct API calls
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async def test_xiaohongshu():
        """测试小红书搜索 (SDK)"""
        print("\n" + "=" * 50)
        print("=== Testing Xiaohongshu (小红书) - SDK ===")
        print("=" * 50)
        try:
            result = await c.XiaohongshuWeb.search_notes(keyword="AI人工智能", page=1, sort="general")
            if result and result.get("data"):
                inner = result["data"].get("data", {})
                items = inner.get("items", [])
                print(f"✅ Found {len(items)} items")
                for i, item in enumerate(items[:3]):
                    note = item.get("note", item)
                    title = note.get("title") or note.get("display_title") or note.get("desc", "")[:30]
                    user = note.get("user", {})
                    print(f"  {i+1}. {title[:50]}")
                    print(f"     作者: {user.get('nickname', 'N/A')}")
                    print(f"     ID: {note.get('id', 'N/A')}")
                return True
            else:
                print(f"❌ Unexpected response: {result}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    async def test_douyin():
        """测试抖音搜索 (Douyin-Search-API via HTTP)"""
        print("\n" + "=" * 50)
        print("=== Testing Douyin (抖音) - HTTP API ===")
        print("=" * 50)
        try:
            # 使用 Douyin-Search-API (最新版本)
            # POST /api/v1/douyin/search/fetch_video_search_v1
            url = f"{base_url}/api/v1/douyin/search/fetch_video_search_v1"
            payload = {
                "keyword": "AI人工智能",
                "offset": 0,
                "count": 5,
                "sort_type": "0",  # 字符串! 0=综合
                "publish_time": "0",  # 字符串! 0=不限
                "filter_duration": "0",  # 字符串! 0=不限
            }

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, headers=headers, json=payload)
                print(f"Status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    if data.get("data"):
                        items = data["data"].get("data", []) or data["data"].get("aweme_list", [])
                        print(f"✅ Found {len(items)} items")
                        for i, item in enumerate(items[:3]):
                            aweme = item.get("aweme_info", item)
                            desc = aweme.get("desc", "N/A")
                            author = aweme.get("author", {})
                            print(f"  {i+1}. {desc[:50]}")
                            print(f"     作者: {author.get('nickname', 'N/A')}")
                        return True
                    else:
                        print(f"Response: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
                        return False
                else:
                    print(f"❌ HTTP {response.status_code}: {response.text[:500]}")
                    return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    async def test_wechat_channels():
        """测试微信视频号搜索 (WeChat-Channels-API via HTTP)"""
        print("\n" + "=" * 50)
        print("=== Testing WeChat Channels (视频号) - HTTP API ===")
        print("=" * 50)
        try:
            # 使用 WeChat-Channels-API
            # GET /api/v1/wechat_channels/fetch_search_ordinary
            url = f"{base_url}/api/v1/wechat_channels/fetch_search_ordinary"
            params = {"keywords": "AI人工智能", "offset": "0", "count": "5"}  # 注意是 keywords (复数)!

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers, params=params)
                print(f"Status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    if data.get("data"):
                        items = data["data"].get("data", []) or data["data"].get("feeds", [])
                        print(f"✅ Found {len(items)} items")
                        for i, item in enumerate(items[:3]):
                            desc = item.get("objectDesc", {}).get("description", "N/A")
                            nickname = item.get("nickname", "N/A")
                            print(f"  {i+1}. {desc[:50] if desc else nickname}")
                            print(f"     作者: {nickname}")
                        return True
                    else:
                        print(f"Response: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
                        return False
                else:
                    print(f"❌ HTTP {response.status_code}: {response.text[:500]}")
                    return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    async def run_all_tests():
        results = {
            "xiaohongshu": await test_xiaohongshu(),
            "douyin": await test_douyin(),
            "wechat_channels": await test_wechat_channels(),
        }

        print("\n" + "=" * 50)
        print("=== Test Summary ===")
        print("=" * 50)
        for platform, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {platform}: {status}")

        return all(results.values())

    asyncio.run(run_all_tests())
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
