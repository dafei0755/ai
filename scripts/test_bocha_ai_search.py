"""
博查 AI Search 测试脚本 (v7.161)

测试博查 API 连接和 DeepSeek-R1 推理功能

改进:
- 统一使用 api.bochaai.com 域名
- 支持从 Web Search 提取图片（备选方案）
- 增强的错误处理和日志

运行: python scripts/test_bocha_ai_search.py
"""

import asyncio
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()


async def test_bocha_search():
    """测试博查搜索功能"""
    print("=" * 60)
    print("🔍 博查 AI Search 测试")
    print("=" * 60)

    # 检查 API 密钥
    bocha_key = os.getenv("BOCHA_API_KEY", "")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")

    print(f"\n📋 配置检查:")
    print(f"  - BOCHA_API_KEY: {'✅ 已配置' if bocha_key and bocha_key != 'your_bocha_api_key' else '❌ 未配置'}")
    print(f"  - DEEPSEEK_API_KEY: {'✅ 已配置' if deepseek_key and deepseek_key != 'your_deepseek_api_key' else '❌ 未配置'}")

    if not bocha_key or bocha_key == "your_bocha_api_key":
        print("\n⚠️ 请先配置 BOCHA_API_KEY")
        return

    # 导入服务
    from intelligent_project_analyzer.services.bocha_ai_search import get_ai_search_service

    service = get_ai_search_service()

    # 测试查询
    test_query = "日本茶庭的哲学分析"
    print(f"\n🔎 测试查询: {test_query}")
    print("-" * 60)

    # 测试非流式搜索
    print("\n1️⃣ 测试非流式搜索...")
    result = await service.search(
        query=test_query,
        count=5,
        include_images=True,
        image_count=4,
    )

    print(f"  - 来源数量: {len(result.sources)}")
    print(f"  - 图片数量: {len(result.images)}")
    print(f"  - 执行时间: {result.execution_time:.2f}s")

    if result.sources:
        print(f"\n  📚 前3个来源:")
        for source in result.sources[:3]:
            print(f"    [{source.reference_number}] {source.title[:40]}...")
            print(f"        {source.site_name} | {'⭐白名单' if source.is_whitelisted else ''}")

    if result.images:
        print(f"\n  🖼️ 图片来源:")
        for img in result.images[:3]:
            title = img.title or img.url or "未知图片"
            print(f"    - {title[:50]}...")

    # 测试流式搜索
    print("\n2️⃣ 测试流式搜索 (DeepSeek-R1 推理)...")
    event_count = 0
    reasoning_chunks = 0
    content_chunks = 0
    async for event in service.search_stream(
        query=test_query,
        count=5,
        use_deepseek_r1=bool(deepseek_key and deepseek_key != "your_deepseek_api_key"),
    ):
        event_type = event.get("type", "unknown")
        event_count += 1

        if event_type == "thinking":
            print(f"  💭 {event['data'].get('message', '')}")
        elif event_type == "sources":
            print(f"  📚 收到 {len(event['data'])} 个来源")
        elif event_type == "images":
            print(f"  🖼️ 收到 {len(event['data'])} 张图片")
        elif event_type == "reasoning_chunk":
            reasoning_chunks += 1
            if reasoning_chunks <= 3 or reasoning_chunks % 10 == 0:
                print(f"  🧠 推理中... (块 #{reasoning_chunks})")
        elif event_type == "reasoning":
            print(f"  🧠 推理完成，共 {len(event['data'])} 字符")
        elif event_type == "content_chunk":
            content_chunks += 1
            if content_chunks <= 3 or content_chunks % 10 == 0:
                print(f"  ✍️ 生成中... (块 #{content_chunks})")
        elif event_type == "content":
            print(f"  📝 内容完成，共 {len(event['data'])} 字符")
        elif event_type == "done":
            print(f"  ✅ 完成! 总耗时: {event['data'].get('execution_time', 0):.2f}s")
        elif event_type == "error":
            print(f"  ❌ 错误: {event['data'].get('message', '')}")

    print(f"\n  总事件数: {event_count}")
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_bocha_search())
