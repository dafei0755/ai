"""
洞察方法论整合测试 (v7.180)

测试需求分析方法论与搜索模块的整合：
1. InsightMethodology 公共模块
2. JTBDQueryBuilder 查询构建器
3. HumanDimensionEvaluator 人性维度评估器
4. InsightAwareQualityControl 洞察感知质量控制
5. SearchOrchestrator 需求分析上下文注入
"""

from typing import Any, Dict, List

import pytest


class TestInsightMethodology:
    """测试洞察方法论公共模块"""

    def test_parse_jtbd_standard_format(self):
        """测试标准JTBD格式解析"""
        from intelligent_project_analyzer.utils.insight_methodology import InsightMethodology

        jtbd = "为一位事业转型期的前金融律师，打造私人空间，雇佣空间完成'专业形象重塑'与'内在自我整合'两项任务"
        result = InsightMethodology.parse_jtbd(jtbd)

        assert result["identity"] == "一位事业转型期的前金融律师"
        assert result["space"] == "私人空间"
        assert len(result["tasks"]) == 2
        assert "专业形象重塑" in result["tasks"]
        assert "内在自我整合" in result["tasks"]

    def test_parse_jtbd_simple_format(self):
        """测试简化JTBD格式解析"""
        from intelligent_project_analyzer.utils.insight_methodology import InsightMethodology

        jtbd = "为年轻夫妻打造温馨的家庭空间"
        result = InsightMethodology.parse_jtbd(jtbd)

        assert "年轻夫妻" in result["identity"]
        assert "家庭空间" in result["space"] or "温馨" in result["space"]

    def test_parse_core_tension_standard_format(self):
        """测试标准核心矛盾格式解析"""
        from intelligent_project_analyzer.utils.insight_methodology import InsightMethodology

        tension = "作为[内容创作者]的[展示需求]与其对[精神庇护]的根本对立"
        pole_a, pole_b = InsightMethodology.parse_core_tension(tension)

        assert pole_a == "展示需求"
        assert pole_b == "精神庇护"

    def test_parse_core_tension_vs_format(self):
        """测试vs格式核心矛盾解析"""
        from intelligent_project_analyzer.utils.insight_methodology import InsightMethodology

        tension = "效率 vs 体验 的对立"
        pole_a, pole_b = InsightMethodology.parse_core_tension(tension)

        assert pole_a == "效率"
        assert pole_b == "体验"

    def test_parse_core_tension_known_patterns(self):
        """测试已知对立模式识别"""
        from intelligent_project_analyzer.utils.insight_methodology import InsightMethodology

        tension = "用户追求现代简约风格，但又希望保留传统元素"
        pole_a, pole_b = InsightMethodology.parse_core_tension(tension)

        assert pole_a == "现代"
        assert pole_b == "传统"

    def test_extract_human_dimensions(self):
        """测试人性维度提取"""
        from intelligent_project_analyzer.utils.insight_methodology import InsightMethodology

        text = "用户追求温馨的家庭氛围，重视传统仪式感，希望保留童年记忆"
        dimensions = InsightMethodology.extract_human_dimensions(text)

        assert "温馨" in dimensions["emotional"] or "氛围" in dimensions["emotional"]
        assert "仪式" in dimensions["ritual"] or "传统" in dimensions["ritual"]
        assert "记忆" in dimensions["memory"] or "童年" in dimensions["memory"]

    def test_get_dimension_coverage(self):
        """测试维度覆盖度计算"""
        from intelligent_project_analyzer.utils.insight_methodology import InsightMethodology

        text = "温馨舒适的空间，追求精神价值，安全私密的环境，日常仪式感，承载家族记忆"
        coverage = InsightMethodology.get_dimension_coverage(text)

        assert coverage["coverage_score"] >= 60  # 至少覆盖3个维度
        assert len(coverage["covered_dimensions"]) >= 3

    def test_calculate_human_relevance_without_user_model(self):
        """测试无用户模型时的相关性计算"""
        from intelligent_project_analyzer.utils.insight_methodology import InsightMethodology

        content = "这是一个温馨舒适的空间设计，注重情感体验"
        score = InsightMethodology.calculate_human_relevance(content)

        assert 0 <= score <= 100

    def test_calculate_human_relevance_with_user_model(self):
        """测试有用户模型时的相关性计算"""
        from intelligent_project_analyzer.utils.insight_methodology import InsightMethodology

        content = "这是一个温馨舒适的空间设计，注重情感体验和仪式感"
        user_model = {
            "psychological": "追求温馨舒适",
            "emotional": "重视情感体验",
            "ritual": "注重日常仪式感",
        }
        score = InsightMethodology.calculate_human_relevance(content, user_model)

        assert score > 0  # 有匹配应该有分数


class TestJTBDQueryBuilder:
    """测试JTBD查询构建器"""

    def test_build_from_requirements_with_jtbd(self):
        """测试从JTBD构建查询"""
        from intelligent_project_analyzer.tools.query_builder import JTBDQueryBuilder

        builder = JTBDQueryBuilder()
        requirements = {
            "project_task": "为一位事业转型期的前金融律师，打造私人空间，雇佣空间完成'专业形象重塑'与'内在自我整合'两项任务",
        }
        result = builder.build_from_requirements(requirements, "室内设计")

        assert len(result["jtbd_queries"]) > 0
        assert len(result["all_queries"]) > 0

    def test_build_from_requirements_with_tension(self):
        """测试从核心矛盾构建查询"""
        from intelligent_project_analyzer.tools.query_builder import JTBDQueryBuilder

        builder = JTBDQueryBuilder()
        requirements = {
            "core_tension": "作为[内容创作者]的[展示需求]与其对[精神庇护]的根本对立",
        }
        result = builder.build_from_requirements(requirements, "室内设计")

        assert len(result["tension_queries"]) > 0
        # 应该包含对立双方的查询
        all_queries_text = " ".join(result["tension_queries"])
        assert "展示" in all_queries_text or "精神" in all_queries_text

    def test_build_from_requirements_with_human_dimensions(self):
        """测试从人性维度构建查询"""
        from intelligent_project_analyzer.tools.query_builder import JTBDQueryBuilder

        builder = JTBDQueryBuilder()
        requirements = {
            "emotional_landscape": "从进门时的都市压力 → 玄关放下包袱的仪式感 → 客厅的社交安全感",
            "ritual_behaviors": "晨间冥想、下午拍摄、夜晚写作的三段式生活节奏",
        }
        result = builder.build_from_requirements(requirements, "室内设计")

        assert len(result["human_queries"]) > 0

    def test_build_enhanced_queries(self):
        """测试增强查询构建"""
        from intelligent_project_analyzer.tools.query_builder import JTBDQueryBuilder

        builder = JTBDQueryBuilder()
        requirements = {
            "project_task": "为年轻夫妻打造温馨的家庭空间",
            "core_tension": "现代 vs 传统",
        }
        queries = builder.build_enhanced_queries("家庭空间设计", requirements, "室内设计")

        assert len(queries) > 1  # 应该有原始查询和增强查询


class TestHumanDimensionEvaluator:
    """测试人性维度评估器"""

    def test_evaluate_single_result(self):
        """测试单个结果评估"""
        from intelligent_project_analyzer.tools.quality_control import HumanDimensionEvaluator

        evaluator = HumanDimensionEvaluator()
        result = {
            "title": "温馨家居设计案例",
            "content": "这个设计注重情感体验，创造温馨舒适的氛围，保留家族记忆",
        }
        eval_result = evaluator.evaluate(result)

        assert "human_score" in eval_result
        assert eval_result["human_score"] > 0
        assert len(eval_result["matched_dimensions"]) > 0

    def test_evaluate_batch(self):
        """测试批量评估"""
        from intelligent_project_analyzer.tools.quality_control import HumanDimensionEvaluator

        evaluator = HumanDimensionEvaluator()
        results = [
            {"title": "温馨家居设计", "content": "注重情感体验"},
            {"title": "极简办公空间", "content": "高效实用的设计"},
        ]
        evaluated = evaluator.evaluate_batch(results)

        assert len(evaluated) == 2
        assert all("human_score" in r for r in evaluated)

    def test_filter_by_human_score(self):
        """测试按人性维度分数过滤"""
        from intelligent_project_analyzer.tools.quality_control import HumanDimensionEvaluator

        evaluator = HumanDimensionEvaluator()
        results = [
            {"title": "温馨家居设计", "content": "注重情感体验，温馨舒适，仪式感"},
            {"title": "技术规范", "content": "建筑规范标准"},
        ]
        filtered = evaluator.filter_by_human_score(results, min_score=20)

        # 第一个结果应该通过，第二个可能被过滤
        assert len(filtered) >= 1

    def test_sort_by_human_score(self):
        """测试按人性维度分数排序"""
        from intelligent_project_analyzer.tools.quality_control import HumanDimensionEvaluator

        evaluator = HumanDimensionEvaluator()
        results = [
            {"title": "技术规范", "content": "建筑规范标准"},
            {"title": "温馨家居设计", "content": "注重情感体验，温馨舒适，仪式感，记忆"},
        ]
        sorted_results = evaluator.sort_by_human_score(results)

        # 第二个结果应该排在前面（人性维度分数更高）
        assert sorted_results[0]["title"] == "温馨家居设计"


class TestInsightAwareQualityControl:
    """测试洞察感知质量控制器"""

    def test_process_results_with_human_evaluation(self):
        """测试带人性维度评估的结果处理"""
        from intelligent_project_analyzer.tools.quality_control import InsightAwareQualityControl

        qc = InsightAwareQualityControl(
            enable_human_evaluation=True,
            enable_filters=False,  # 禁用URL过滤以便测试
            min_content_length=10,  # 降低内容长度要求以便测试
            human_weight=0.15,
        )
        results = [
            {
                "title": "温馨家居设计案例",
                "content": "这个设计注重情感体验，创造温馨舒适的氛围，让用户感受到家的温暖和归属感，是一个非常成功的室内设计案例。",
                "url": "https://archdaily.com/test1",
            },
            {
                "title": "建筑规范标准",
                "content": "建筑设计规范要求，包括结构安全、消防安全、无障碍设计等多个方面的技术标准和规范要求。",
                "url": "https://archdaily.com/test2",
            },
        ]
        processed = qc.process_results(results)

        assert len(processed) > 0
        # 检查是否添加了人性维度评估
        assert all("human_score" in r or "human_evaluation_applied" in r for r in processed)

    def test_process_results_with_user_model(self):
        """测试带用户模型的结果处理"""
        from intelligent_project_analyzer.tools.quality_control import InsightAwareQualityControl

        user_model = {
            "psychological": "追求温馨舒适",
            "emotional": "重视情感体验",
        }
        qc = InsightAwareQualityControl(
            enable_human_evaluation=True,
            enable_filters=False,  # 禁用URL过滤以便测试
            min_content_length=10,  # 降低内容长度要求以便测试
            user_model=user_model,
        )
        results = [
            {
                "title": "温馨家居设计",
                "content": "温馨舒适的情感体验，让用户感受到家的温暖和归属感，是一个非常成功的室内设计案例。",
                "url": "https://archdaily.com/test",
            },
        ]
        processed = qc.process_results(results)

        assert len(processed) > 0


class TestSearchOrchestratorIntegration:
    """测试搜索编排器与需求分析的整合"""

    def test_extract_requirements_context(self):
        """测试需求分析上下文提取"""
        from intelligent_project_analyzer.services.search_orchestrator import SearchOrchestrator

        orchestrator = SearchOrchestrator()

        state = {
            "structured_requirements": {
                "structured_output": {
                    "project_task": "为年轻夫妻打造温馨的家庭空间",
                    "design_challenge": "现代 vs 传统",
                    "emotional_landscape": "温馨舒适",
                },
                "analysis_layers": {
                    "L2_user_model": {"psychological": "追求温馨"},
                    "L3_core_tension": "现代与传统的平衡",
                },
            },
            "project_type": "residential",
        }

        context = orchestrator._extract_requirements_context(state)

        assert context["project_task"] == "为年轻夫妻打造温馨的家庭空间"
        assert context["emotional_landscape"] == "温馨舒适"
        assert context["project_type"] == "residential"

    def test_build_enhanced_queries(self):
        """测试增强查询构建"""
        from intelligent_project_analyzer.services.search_orchestrator import SearchOrchestrator

        orchestrator = SearchOrchestrator()

        requirements_context = {
            "structured_requirements": {
                "project_task": "为年轻夫妻打造温馨的家庭空间",
                "core_tension": "现代 vs 传统",
            },
            "project_task": "为年轻夫妻打造温馨的家庭空间",
            "core_tension": "现代 vs 传统",
        }

        queries = orchestrator._build_enhanced_queries(requirements_context, "室内设计")

        # 应该生成一些增强查询
        assert isinstance(queries, list)


# 便捷函数测试
class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_parse_jtbd_function(self):
        """测试parse_jtbd便捷函数"""
        from intelligent_project_analyzer.utils.insight_methodology import parse_jtbd

        result = parse_jtbd("为年轻夫妻打造温馨的家庭空间")
        assert "identity" in result
        assert "space" in result

    def test_parse_core_tension_function(self):
        """测试parse_core_tension便捷函数"""
        from intelligent_project_analyzer.utils.insight_methodology import parse_core_tension

        pole_a, pole_b = parse_core_tension("效率 vs 体验")
        assert pole_a or pole_b  # 至少解析出一个

    def test_extract_human_dimensions_function(self):
        """测试extract_human_dimensions便捷函数"""
        from intelligent_project_analyzer.utils.insight_methodology import extract_human_dimensions

        dimensions = extract_human_dimensions("温馨舒适的空间")
        assert isinstance(dimensions, dict)
        assert "emotional" in dimensions

    def test_build_jtbd_queries_function(self):
        """测试build_jtbd_queries便捷函数"""
        from intelligent_project_analyzer.tools.query_builder import build_jtbd_queries

        result = build_jtbd_queries({"project_task": "为年轻夫妻打造温馨的家庭空间"}, "室内设计")
        assert "all_queries" in result

    def test_evaluate_human_dimensions_function(self):
        """测试evaluate_human_dimensions便捷函数"""
        from intelligent_project_analyzer.tools.quality_control import evaluate_human_dimensions

        results = [{"title": "温馨设计", "content": "情感体验"}]
        evaluated = evaluate_human_dimensions(results)
        assert all("human_score" in r for r in evaluated)

    def test_insight_aware_quality_control_function(self):
        """测试insight_aware_quality_control便捷函数"""
        from intelligent_project_analyzer.tools.quality_control import InsightAwareQualityControl

        results = [
            {
                "title": "温馨设计",
                "content": "情感体验温馨舒适，让用户感受到家的温暖和归属感，是一个非常成功的室内设计案例。",
                "url": "https://archdaily.com/test",
            },
        ]
        # 禁用过滤器以便测试
        qc = InsightAwareQualityControl(enable_human_evaluation=True, enable_filters=False, min_content_length=10)
        processed = qc.process_results(results)
        assert len(processed) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
