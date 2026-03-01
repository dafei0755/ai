"""
智能Few-Shot选择器测试
"""

import pytest
import time

# 检查依赖是否可用
try:
    from intelligent_project_analyzer.intelligence.intelligent_few_shot_selector import (
        IntelligentFewShotSelector,
        SelectorConfig,
        DEPENDENCIES_AVAILABLE,
    )

    SKIP_TESTS = not DEPENDENCIES_AVAILABLE
    SKIP_REASON = "缺少依赖: pip install sentence-transformers faiss-cpu"
except Exception as e:
    SKIP_TESTS = True
    SKIP_REASON = f"导入失败: {e}"


@pytest.mark.skipif(SKIP_TESTS, reason=SKIP_REASON)
@pytest.mark.slow
class TestIntelligentFewShotSelector:
    """智能Few-Shot选择器测试"""

    @pytest.fixture
    def selector(self, tmp_path):
        """创建选择器实例"""
        config = SelectorConfig(
            model_name="paraphrase-multilingual-MiniLM-L12-v2",
            cache_dir=tmp_path / "embeddings_cache",
            diversity_threshold=0.7,
            use_faiss=True,
        )
        return IntelligentFewShotSelector(config)

    def test_initialization(self, selector):
        """测试初始化"""
        assert selector is not None
        assert selector.model is not None
        assert selector.config is not None

    def test_build_index_for_role(self, selector):
        """测试构建索引"""
        role_id = "V2_0"

        # 首次构建
        start_time = time.time()
        selector.build_index_for_role(role_id)
        build_time = time.time() - start_time

        assert role_id in selector.indices
        assert role_id in selector.examples_cache
        assert len(selector.examples_cache[role_id]) > 0

        print(f"\n首次构建索引耗时: {build_time:.2f}秒")

        # 从缓存加载
        start_time = time.time()
        selector.build_index_for_role(role_id)
        cache_time = time.time() - start_time

        print(f"从缓存加载耗时: {cache_time:.2f}秒")
        assert cache_time < build_time, "缓存加载应该更快"

    def test_select_relevant_examples(self, selector):
        """测试选择相关示例"""
        role_id = "V2_0"
        selector.build_index_for_role(role_id)

        # 测试查询
        query = "我需要分析一个住宅项目的需求，包括用户需求和技术要求"

        examples = selector.select_relevant_examples(role_id=role_id, user_query=query, top_k=2)

        assert len(examples) <= 2
        assert all(hasattr(ex, "example_id") for ex in examples)
        assert all(hasattr(ex, "user_request") for ex in examples)

        print("\n选中示例:")
        for ex in examples:
            print(f"  - {ex.example_id}: {ex.description}")

    def test_category_filtering(self, selector):
        """测试分类过滤"""
        role_id = "V2_0"
        selector.build_index_for_role(role_id)

        query = "分析项目需求"

        # 测试targeted_mode分类
        targeted_examples = selector.select_relevant_examples(
            role_id=role_id, user_query=query, top_k=2, category="targeted_mode"
        )

        # 测试comprehensive_mode分类
        comprehensive_examples = selector.select_relevant_examples(
            role_id=role_id, user_query=query, top_k=2, category="comprehensive_mode"
        )

        print(f"\nTargeted模式: {len(targeted_examples)} 个示例")
        print(f"Comprehensive模式: {len(comprehensive_examples)} 个示例")

        # 至少有一种模式返回了示例
        assert len(targeted_examples) > 0 or len(comprehensive_examples) > 0

    def test_diversity_filtering(self, selector):
        """测试多样性筛选"""
        role_id = "V2_0"
        selector.build_index_for_role(role_id)

        query = "项目需求分析"

        # 高多样性阈值（更严格）
        high_diversity_examples = selector.select_relevant_examples(
            role_id=role_id, user_query=query, top_k=3, diversity_threshold=0.8
        )

        # 低多样性阈值（更宽松）
        low_diversity_examples = selector.select_relevant_examples(
            role_id=role_id, user_query=query, top_k=3, diversity_threshold=0.5
        )

        print(f"\n高阈值(0.8): {len(high_diversity_examples)} 个示例")
        print(f"低阈值(0.5): {len(low_diversity_examples)} 个示例")

        # 低阈值应该返回更多或相同数量的示例
        assert len(low_diversity_examples) >= len(high_diversity_examples)

    def test_compare_with_baseline(self, selector):
        """测试与基线方法对比"""
        role_id = "V2_0"

        test_queries = ["分析住宅项目的功能需求", "商业综合体的技术需求评估", "办公楼的用户需求调研"]

        results = selector.compare_with_baseline(role_id=role_id, test_queries=test_queries)

        assert "intelligent" in results
        assert "baseline" in results
        assert "agreement_rate" in results

        print("\n与基线对比结果:")
        print(f"  一致率: {results['agreement_rate']:.1%}")
        print("\n智能方法选择:")
        for i, ids in enumerate(results["intelligent"]):
            print(f"  Query {i+1}: {ids}")
        print("\n基线方法选择:")
        for i, ids in enumerate(results["baseline"]):
            print(f"  Query {i+1}: {ids}")

    def test_fallback_to_baseline(self, selector):
        """测试回退到基线方法"""
        # 使用一个不存在的角色
        non_existent_role = "V99_9"

        query = "测试查询"

        # 应该回退到传统方法，不抛出异常
        examples = selector.select_relevant_examples(role_id=non_existent_role, user_query=query, top_k=2)

        # 应该返回空列表（因为没有示例文件）
        assert isinstance(examples, list)

    def test_performance(self, selector):
        """测试性能"""
        role_id = "V2_0"
        selector.build_index_for_role(role_id)

        query = "分析项目需求"

        # 测试100次查询
        start_time = time.time()
        for _ in range(100):
            selector.select_relevant_examples(role_id=role_id, user_query=query, top_k=2)
        total_time = time.time() - start_time
        avg_time = total_time / 100

        print("\n性能测试:")
        print(f"  100次查询总耗时: {total_time:.2f}秒")
        print(f"  平均单次查询: {avg_time*1000:.1f}ms")

        # 平均查询时间应该小于100ms
        assert avg_time < 0.1, f"查询性能不足: {avg_time*1000:.1f}ms > 100ms"


@pytest.mark.skipif(SKIP_TESTS, reason=SKIP_REASON)
def test_selector_with_custom_config(tmp_path):
    """测试自定义配置"""
    config = SelectorConfig(
        model_name="paraphrase-multilingual-MiniLM-L12-v2",
        cache_dir=tmp_path / "custom_cache",
        diversity_threshold=0.6,
        use_faiss=False,  # 不使用FAISS
    )

    selector = IntelligentFewShotSelector(config)
    assert selector.config.diversity_threshold == 0.6
    assert selector.config.use_faiss is False
