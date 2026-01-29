"""
测试网页内容深度提取器 (v7.196)

验证 Trafilatura + Playwright 混合方案的效果
v7.196 新增测试: 缓存、重试、慢站点超时
"""

import asyncio
import os
import sys

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_extraction():
    """测试内容提取"""
    from intelligent_project_analyzer.services.web_content_extractor import (
        ExtractionMethod,
        cleanup_extractor,
        get_cache_stats,
        get_web_content_extractor,
    )

    extractor = get_web_content_extractor()

    # 测试用例
    test_urls = [
        # 静态网页 - 应使用 Trafilatura
        "https://www.archdaily.cn/cn/1023785/2024nian-lun-dun-jian-zhu-jie-zui-jia-zhan-ting-jian-zhu",
        # 动态网页 - 应使用 Playwright
        # "https://www.zhihu.com/question/123456789",  # 知乎需登录
        # 低质量站点 - 应跳过
        "https://baijiahao.baidu.com/s?id=1234567890",
    ]

    print("=" * 60)
    print("🧪 网页内容深度提取测试 (v7.196)")
    print("=" * 60)

    for url in test_urls:
        print(f"\n📌 测试 URL: {url[:60]}...")
        result = await extractor.extract(url)

        print(f"   方法: {result.method.value}")
        print(f"   耗时: {result.extraction_time:.2f}秒")
        print(f"   标题: {result.title[:50] if result.title else 'N/A'}...")
        print(f"   内容长度: {len(result.content)}字")
        print(f"   来自缓存: {result.from_cache}")
        print(f"   重试次数: {result.retry_count}")
        if result.error:
            print(f"   错误: {result.error}")
        if result.content:
            print(f"   内容预览: {result.content[:150]}...")

    print("\n" + "=" * 60)
    print("📊 批量提取测试")
    print("=" * 60)

    batch_urls = [
        "https://www.archdaily.cn/cn",
        "https://gooood.cn/",
        "https://www.designboom.com/",
    ]

    results = await extractor.extract_batch(batch_urls, max_concurrent=2)

    for url, result in results.items():
        print(f"\n📌 {url[:40]}...")
        print(
            f"   方法={result.method.value} | 长度={len(result.content)}字 | 耗时={result.extraction_time:.2f}秒 | 缓存={result.from_cache}"
        )

    # v7.196: 测试缓存功能
    print("\n" + "=" * 60)
    print("📦 缓存测试 (v7.196)")
    print("=" * 60)

    cache_stats = get_cache_stats()
    print(f"缓存状态: {cache_stats['cache_size']}/{cache_stats['max_size']} 条目")

    # 重复提取，应该命中缓存
    print("\n🔄 重复提取第一个 URL (应命中缓存)...")
    cached_result = await extractor.extract(batch_urls[0])
    print(f"   来自缓存: {cached_result.from_cache}")
    print(f"   耗时: {cached_result.extraction_time:.2f}秒 (缓存时为原始提取耗时)")

    # 清理资源
    await cleanup_extractor()

    print("\n✅ 测试完成!")


if __name__ == "__main__":
    asyncio.run(test_extraction())
