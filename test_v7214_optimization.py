"""
测试 v7.214 深度搜索优化功能
"""

import asyncio
import os
import sys

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine


async def test_structured_analysis():
    """测试结构化问题分析"""
    print("🔬 测试结构化问题分析功能")

    engine = UcpptSearchEngine()

    # 测试查询
    test_query = "我想在北京设计一个100平米的咖啡厅，要有温馨的氛围"
    test_context = {"user_location": "北京", "project_type": "商业空间设计", "area": "100平米"}

    try:
        # 执行结构化分析
        analysis_session = await engine.structured_problem_analysis(test_query, test_context)

        if analysis_session:
            print(f"✅ 结构化分析成功")
            print(f"   - 总体质量: {analysis_session.overall_quality:.1%}")
            print(f"   - 执行时间: {analysis_session.total_execution_time:.1f}s")

            if analysis_session.l0_result:
                print(f"   - L0 对话质量: {analysis_session.l0_result.quality_score:.1%}")
                print(f"   - 隐性需求数量: {len(analysis_session.l0_result.implicit_needs)}")

            if analysis_session.framework_result:
                print(f"   - 框架一致性: {analysis_session.framework_result.framework_coherence:.1%}")
                print(f"   - L1 事实数量: {len(analysis_session.framework_result.l1_facts)}")

            if analysis_session.synthesis_result:
                tasks = analysis_session.synthesis_result.search_master_line.search_tasks
                print(f"   - 生成搜索任务: {len(tasks)} 个")
                for i, task in enumerate(tasks[:3], 1):
                    print(f"     {i}. {task.task[:50]}...")
        else:
            print("❌ 结构化分析失败")

    except Exception as e:
        print(f"❌ 结构化分析异常: {e}")


async def test_quality_assessment():
    """测试多层次质量评估"""
    print("\n📊 测试多层次质量评估功能")

    engine = UcpptSearchEngine()

    # 模拟搜索结果
    mock_results = [
        {
            "title": "咖啡厅设计要点详解",
            "content": "咖啡厅设计需要考虑空间布局、灯光设计、材料选择等多个方面。对于100平米的空间，建议采用开放式布局，合理规划座位区域，营造温馨舒适的氛围。" * 3,
            "url": "https://example.com/cafe-design",
            "siteName": "设计网",
        },
        {
            "title": "北京咖啡厅案例",
            "content": "北京地区咖啡厅设计案例分享，展示不同风格的设计理念。",
            "url": "https://design.example.com/beijing-cafe",
            "siteName": "建筑设计",
        },
        {
            "title": "温馨氛围营造方法",
            "content": "通过色彩搭配、家具选择、装饰元素来营造温馨的空间氛围。",
            "url": "https://decor.example.com/cozy",
            "siteName": "装饰网",
        },
    ]

    try:
        # 执行质量评估
        assessment = await engine.enhanced_quality_assessment(mock_results, "北京咖啡厅设计温馨氛围", "test")

        print(f"✅ 质量评估完成")
        print(f"   - 过滤结果: {len(assessment['filtered_results'])} 条")
        print(f"   - 总体质量: {assessment['quality_metrics']['total_score']:.1%}")
        print(f"   - 评估摘要: {assessment['assessment_summary']}")

        # 显示各层评分
        layer_scores = assessment["quality_metrics"]["layer_scores"]
        for layer, score in layer_scores.items():
            print(f"   - {layer} 评分: {score:.1%}")

    except Exception as e:
        print(f"❌ 质量评估异常: {e}")


async def test_query_enhancement():
    """测试智能关键词扩展"""
    print("\n🎯 测试智能关键词扩展功能")

    engine = UcpptSearchEngine()

    # 模拟目标方面
    class MockTargetAspect:
        def __init__(self):
            self.aspect_name = "空间布局设计"
            self.answer_goal = "了解100平米咖啡厅的最佳空间布局方案"
            self.last_searched_round = 1
            self.search_query = ""
            self.collected_info = ["之前收集的布局信息..."]

    target_aspect = MockTargetAspect()

    try:
        # 测试查询扩展
        expanded_queries = await engine._generate_expanded_queries("北京咖啡厅空间布局设计")

        print(f"✅ 查询扩展成功")
        for i, query in enumerate(expanded_queries, 1):
            print(f"   {i}. {query}")

    except Exception as e:
        print(f"❌ 查询扩展异常: {e}")


async def main():
    """主测试函数"""
    print("🧪 v7.214 深度搜索优化功能测试")
    print("=" * 50)

    # 测试各个功能模块
    await test_structured_analysis()
    await test_quality_assessment()
    await test_query_enhancement()

    print("\n" + "=" * 50)
    print("🎉 测试完成")


if __name__ == "__main__":
    asyncio.run(main())
