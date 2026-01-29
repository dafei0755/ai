"""测试博查图片搜索结果格式 - v7.176"""
import asyncio
import json
import os
import sys

import httpx

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()


async def test_raw_api():
    """测试原始 API 返回"""
    api_key = os.getenv("BOCHA_API_KEY")
    url = "https://api.bochaai.com/v1/web-search"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "query": "现代简约风格书房设计",
        "count": 10,
        "freshness": "oneYear",
        "summary": True,
    }

    print("=" * 60)
    print("🔍 博查 Web Search 原始 API 测试")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, headers=headers, json=payload)
        data = response.json()

        if data.get("code") == 200:
            web_data = data.get("data", {})

            # 检查顶层 images
            images = web_data.get("images", [])
            print(f"\n📷 images 字段类型: {type(images).__name__}")

            if isinstance(images, dict):
                image_list = images.get("value", [])
            elif isinstance(images, list):
                image_list = images
            else:
                image_list = []

            print(f"📷 图片数量: {len(image_list)}")

            if image_list:
                print(f"\n📦 图片字段结构:")
                first = image_list[0]
                for key in sorted(first.keys()):
                    val = first[key]
                    val_str = str(val)[:60] + "..." if val and len(str(val)) > 60 else str(val)
                    print(f"   {key}: {val_str}")

                print(f"\n🖼️ 前3张图片:")
                for i, img in enumerate(image_list[:3], 1):
                    title = img.get("name") or img.get("title") or "无标题"
                    title = title[:50] if title else "无标题"
                    url = img.get("contentUrl") or img.get("url") or ""
                    thumb = img.get("thumbnailUrl") or img.get("thumbnail") or ""
                    width = img.get("width") or 0
                    height = img.get("height") or 0
                    host = img.get("hostPageUrl") or img.get("sourceUrl") or ""

                    print(f"\n   [{i}] {title}")
                    print(f"       contentUrl: {url[:70]}..." if url else "       contentUrl: 无")
                    print(f"       尺寸: {width}x{height}")
                    print(f"       来源: {host[:50]}..." if host else "       来源: 无")
            else:
                print("\n⚠️ 没有图片结果")

            # 检查 videos 字段
            videos = web_data.get("videos") or []
            print(f"\n🎬 videos 字段: {len(videos)} 个")

        else:
            print(f"❌ 错误: {data}")


async def test_service():
    """测试优化后的 BochaAISearchService"""
    print("\n" + "=" * 60)
    print("🔧 BochaAISearchService 优化测试")
    print("=" * 60)

    try:
        from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearchService

        service = BochaAISearchService()

        result = await service.search(
            query="现代简约风格书房设计",
            count=10,
            include_images=True,
            image_count=8,
        )

        print(f"\n📊 搜索结果:")
        print(f"   来源数量: {len(result.sources)}")
        print(f"   图片数量: {len(result.images)}")
        print(f"   执行时间: {result.execution_time:.2f}s")

        if result.images:
            print(f"\n🖼️ 图片列表:")
            for i, img in enumerate(result.images[:5], 1):
                print(f"   [{i}] {img.title[:40]}..." if len(img.title) > 40 else f"   [{i}] {img.title}")
                print(f"       URL: {img.url[:60]}...")
                print(f"       尺寸: {img.width}x{img.height}")
                print(f"       来源: {img.source_url[:50]}..." if img.source_url else "")
        else:
            print("\n⚠️ 没有返回图片")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


async def main():
    await test_raw_api()
    await test_service()
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
