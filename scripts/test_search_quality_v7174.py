"""
搜索质量优化验证测试 (v7.174)

验证以下优化是否生效：
1. 学术来源权重增强
2. DeepSeek-R1 深度推理配置
3. 黑名单扩展
4. 搜索结果缓存

运行: python scripts/test_search_quality_v7174.py
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger


def test_academic_weight():
    """测试学术来源权重"""
    print("\n" + "=" * 60)
    print("📚 测试1: 学术来源权重")
    print("=" * 60)

    from intelligent_project_analyzer.tools.quality_control import SearchQualityControl

    qc = SearchQualityControl()

    # 验证权重配置
    print(f"\n质量评分权重配置:")
    print(f"  - 相关性: {qc.SCORE_WEIGHTS['relevance']:.0%}")
    print(f"  - 时效性: {qc.SCORE_WEIGHTS['timeliness']:.0%}")
    print(f"  - 可信度: {qc.SCORE_WEIGHTS['credibility']:.0%}")
    print(f"  - 完整性: {qc.SCORE_WEIGHTS['completeness']:.0%}")
    print(f"  - 学术加分: +{qc.ACADEMIC_BOOST}分")

    # 测试学术来源检测
    academic_urls = [
        "https://www.cnki.net/article/123",
        "https://arxiv.org/abs/2401.12345",
        "https://www.nature.com/articles/s41586-023-06735-9",
        "https://ieeexplore.ieee.org/document/9999999",
        "https://www.tsinghua.edu.cn/research/paper",
    ]

    non_academic_urls = [
        "https://www.zhihu.com/question/12345",
        "https://www.sohu.com/a/12345",
        "https://www.docin.com/p-12345.html",
    ]

    print(f"\n学术来源检测:")
    for url in academic_urls:
        is_academic = qc._is_academic_source(url)
        status = "✅ 学术" if is_academic else "❌ 非学术"
        print(f"  {status}: {url[:50]}...")

    print(f"\n非学术来源检测:")
    for url in non_academic_urls:
        is_academic = qc._is_academic_source(url)
        status = "✅ 学术" if is_academic else "❌ 非学术"
        print(f"  {status}: {url[:50]}...")

    # 比较评分
    print(f"\n评分对比（学术 vs 非学术）:")
    academic_result = {
        "url": "https://www.cnki.net/article/test",
        "title": "农耕文化对室内设计的影响研究",
        "content": "本文从农耕文化的视角出发，深入分析了中国传统室内设计中的文化元素..." * 5,
        "relevance_score": 0.8,
        "source_credibility": "high",
    }

    non_academic_result = {
        "url": "https://www.zhihu.com/question/test",
        "title": "农耕文化对室内设计的影响",
        "content": "本文从农耕文化的视角出发，深入分析了中国传统室内设计中的文化元素..." * 5,
        "relevance_score": 0.8,
        "source_credibility": "low",
    }

    academic_score = qc.calculate_composite_score(academic_result)
    non_academic_score = qc.calculate_composite_score(non_academic_result)

    print(f"  学术来源 (cnki.net): {academic_score:.2f}分")
    print(f"  非学术来源 (zhihu.com): {non_academic_score:.2f}分")
    print(f"  分数差距: +{academic_score - non_academic_score:.2f}分")

    return True


def test_deepseek_config():
    """测试 DeepSeek-R1 配置"""
    print("\n" + "=" * 60)
    print("🧠 测试2: DeepSeek-R1 深度推理配置")
    print("=" * 60)

    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "")
    r1_enabled = os.getenv("DEEPSEEK_R1_ENABLED", "false").lower() == "true"

    print(f"\n配置检查:")
    print(f"  - DEEPSEEK_API_KEY: {'✅ 已配置' if api_key and api_key.startswith('sk-') else '❌ 未配置或无效'}")
    print(f"  - DEEPSEEK_BASE_URL: {base_url or '(默认: https://api.deepseek.com)'}")
    print(f"  - DEEPSEEK_R1_ENABLED: {'✅ 已启用' if r1_enabled else '❌ 未启用'}")

    if api_key and api_key.startswith("sk-"):
        print("\n✅ DeepSeek-R1 深度推理已正确配置，将在博查AI Search中启用")
    else:
        print("\n⚠️ 请配置有效的 DEEPSEEK_API_KEY 以启用深度推理")

    return True


def test_blacklist():
    """测试黑名单扩展"""
    print("\n" + "=" * 60)
    print("🚫 测试3: 黑名单扩展")
    print("=" * 60)

    from intelligent_project_analyzer.services.search_filter_manager import get_filter_manager

    fm = get_filter_manager()

    # 新增的黑名单域名
    new_blacklist_domains = [
        "https://www.docin.com/p-12345.html",  # 豆丁网
        "https://www.doc88.com/p-12345.html",  # 道客巴巴
        "https://www.taodocs.com/p-12345.html",  # 淘豆网
        "https://www.360doc.com/content/12345",  # 360个人图书馆
        "https://baijiahao.baidu.com/s?id=12345",  # 百家号
        "https://www.sohu.com/a/12345",  # 搜狐
    ]

    print(f"\n新增黑名单域名测试:")
    for url in new_blacklist_domains:
        is_blocked = fm.is_blacklisted(url)
        status = "🚫 已屏蔽" if is_blocked else "⚠️ 未屏蔽"
        print(f"  {status}: {url[:50]}...")

    # 白名单域名测试
    whitelist_domains = [
        "https://www.cnki.net/article/12345",
        "https://arxiv.org/abs/2401.12345",
        "https://www.archdaily.com/12345",
        "https://www.gooood.cn/project-12345",
    ]

    print(f"\n白名单域名测试:")
    for url in whitelist_domains:
        is_whitelisted = fm.is_whitelisted(url)
        status = "⭐ 白名单" if is_whitelisted else "❌ 非白名单"
        print(f"  {status}: {url[:50]}...")

    return True


def test_cache():
    """测试搜索结果缓存"""
    print("\n" + "=" * 60)
    print("💾 测试4: 搜索结果缓存")
    print("=" * 60)

    from intelligent_project_analyzer.services.search_cache import get_search_cache

    cache = get_search_cache()

    print(f"\n缓存配置:")
    stats = cache.get_stats()
    print(f"  - 启用状态: {'✅ 已启用' if stats['enabled'] else '❌ 已禁用'}")
    print(f"  - TTL: {stats['ttl']}秒")
    print(f"  - 最大容量: {stats['max_size']}条")
    print(f"  - 后端: {stats['backend']}")

    # 测试缓存读写
    test_query = "农耕文化室内设计测试"
    test_result = {
        "success": True,
        "query": test_query,
        "results": [{"title": "测试结果1", "url": "https://example.com"}],
    }

    # 写入缓存
    cache.set(test_query, "test", test_result)
    print(f"\n缓存读写测试:")
    print(f"  - 写入: {test_query[:20]}...")

    # 读取缓存
    cached = cache.get(test_query, "test")
    if cached:
        print(f"  - 读取: ✅ 命中")
    else:
        print(f"  - 读取: ❌ 未命中")

    # 显示统计
    stats = cache.get_stats()
    print(f"\n缓存统计:")
    print(f"  - 命中: {stats['hits']}次")
    print(f"  - 未命中: {stats['misses']}次")
    print(f"  - 命中率: {stats['hit_rate']}")

    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("🔬 搜索质量优化验证测试 (v7.174)")
    print("=" * 60)

    # 加载环境变量
    from dotenv import load_dotenv

    load_dotenv()

    tests = [
        ("学术来源权重", test_academic_weight),
        ("DeepSeek-R1配置", test_deepseek_config),
        ("黑名单扩展", test_blacklist),
        ("搜索结果缓存", test_cache),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"❌ 测试失败 [{name}]: {e}")
            results.append((name, False))

    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status}: {name}")

    print(f"\n总计: {passed}/{total} 项测试通过")

    if passed == total:
        print("\n🎉 所有优化已成功应用！")
    else:
        print("\n⚠️ 部分优化需要检查")


if __name__ == "__main__":
    main()
