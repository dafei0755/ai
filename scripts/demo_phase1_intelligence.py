"""
Phase 1 快速演示脚本

演示智能Few-Shot选择、使用数据跟踪和质量分析功能。
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from intelligent_project_analyzer.intelligence import (
    IntelligentFewShotSelector,
    UsageTracker,
    ExampleQualityAnalyzer,
    SelectorConfig,
)
from datetime import datetime
import time


def demo_intelligent_selector():
    """演示智能选择器"""
    print("\n" + "=" * 60)
    print("演示 1: 智能Few-Shot选择器")
    print("=" * 60)

    try:
        # 创建选择器
        print("\n[1/3] 初始化选择器...")
        selector = IntelligentFewShotSelector()

        # 构建索引
        print("[2/3] 构建索引 (首次运行会下载模型，请耐心等待)...")
        role_id = "V2_0"
        start_time = time.time()
        selector.build_index_for_role(role_id)
        build_time = time.time() - start_time
        print(f"✅ 索引构建完成! 耗时 {build_time:.2f}秒")

        # 选择示例
        print("[3/3] 选择相关示例...")
        test_queries = ["分析住宅项目的功能需求和技术要求", "商业综合体的用户体验优化", "办公楼的智能化系统设计"]

        for i, query in enumerate(test_queries, 1):
            print(f"\n查询 {i}: {query}")

            start_time = time.time()
            examples = selector.select_relevant_examples(role_id=role_id, user_query=query, top_k=2)
            query_time = time.time() - start_time

            print(f"  选中示例 ({query_time*1000:.1f}ms):")
            for ex in examples:
                print(f"    • {ex.example_id}")
                print(f"      {ex.description[:60]}...")

        # 对比基线
        print("\n[对比] 与传统关键词匹配对比...")
        comparison = selector.compare_with_baseline(role_id=role_id, test_queries=test_queries[:2])
        print(f"  一致率: {comparison['agreement_rate']:.1%}")

        return True

    except Exception as e:
        print(f"❌ 演示失败: {e}")
        print("提示: 请先安装依赖: pip install sentence-transformers faiss-cpu")
        return False


def demo_usage_tracker():
    """演示使用数据跟踪"""
    print("\n" + "=" * 60)
    print("演示 2: 使用数据跟踪器")
    print("=" * 60)

    # 创建跟踪器
    print("\n[1/4] 初始化跟踪器...")
    tracker = UsageTracker(use_sqlite=True)
    print("✅ 跟踪器已就绪")

    # 模拟记录
    print("\n[2/4] 模拟记录使用数据...")
    test_data = [
        {
            "role_id": "V2_0",
            "request": "分析住宅项目需求",
            "examples": ["v2_0_targeted_requirements_classification_001"],
            "feedback": {"liked": True, "rating": 5},
        },
        {
            "role_id": "V2_0",
            "request": "商业综合体功能规划",
            "examples": ["v2_0_comprehensive_holistic_integration_003"],
            "feedback": {"rating": 3},
        },
        {"role_id": "V3_1", "request": "结构设计优化建议", "examples": ["v3_1_targeted_001"], "feedback": {"liked": True}},
    ]

    for data in test_data:
        tracker.log_expert_usage(
            role_id=data["role_id"],
            user_request=data["request"],
            selected_examples=data["examples"],
            output_tokens=1500,
            response_time=2.0,
            user_feedback=data["feedback"],
            session_id=f"demo_session_{datetime.now().timestamp()}",
        )
    print(f"✅ 已记录 {len(test_data)} 条数据")

    # 查询日志
    print("\n[3/4] 查询使用日志...")
    logs = tracker.get_logs(limit=3)
    print(f"  最近 {len(logs)} 条记录:")
    for log in logs:
        print(f"    • [{log['role_id']}] {log['user_request'][:40]}...")

    # 统计信息
    print("\n[4/4] 获取统计信息...")
    stats = tracker.get_statistics(days=7)
    print(f"  总调用: {stats['total_calls']}")
    print(f"  平均响应: {stats['avg_response_time']:.2f}秒")
    print(f"  角色分布: {stats['role_distribution']}")


def demo_quality_analyzer():
    """演示质量分析"""
    print("\n" + "=" * 60)
    print("演示 3: 示例质量分析器")
    print("=" * 60)

    # 创建分析器
    print("\n[1/3] 初始化分析器...")
    analyzer = ExampleQualityAnalyzer()
    print("✅ 分析器已就绪")

    # 分析角色
    print("\n[2/3] 分析 V2_0 角色...")
    print("  (这需要一些时间，请稍候...)")

    try:
        report = analyzer.analyze_role(role_id="V2_0", days=30, quality_threshold=0.5)

        print(f"\n✅ 分析完成!")
        print(f"\n📊 质量报告摘要:")
        print(f"    总示例数: {report.total_examples}")
        print(f"    使用率: {report.summary['usage_rate']:.1%}")
        print(f"    高质量示例: {len(report.high_quality_examples)} 个")
        print(f"    低质量示例: {len(report.low_quality_examples)} 个")
        print(f"    未使用示例: {len(report.unused_examples)} 个")

        if report.recommendations:
            print(f"\n💡 优化建议:")
            for rec in report.recommendations[:3]:
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}[rec["priority"]]
                print(f"    {priority_icon} {rec['description']}")

        # 保存报告
        print("\n[3/3] 保存报告...")
        json_path = analyzer.save_report(report, format="json")
        md_path = analyzer.save_report(report, format="markdown")
        print(f"  ✅ JSON报告: {json_path}")
        print(f"  ✅ Markdown报告: {md_path}")

    except Exception as e:
        print(f"⚠️ 分析跳过 (需要使用数据): {e}")


def main():
    """主函数"""
    print("\n" + "🌟" * 30)
    print("    Phase 1 智能化演进系统 - 快速演示")
    print("🌟" * 30)

    # 演示1: 智能选择器
    success = demo_intelligent_selector()

    # 如果选择器演示成功，继续其他演示
    if success:
        # 演示2: 使用跟踪
        demo_usage_tracker()

        # 演示3: 质量分析
        demo_quality_analyzer()

    print("\n" + "=" * 60)
    print("演示完成! 🎉")
    print("=" * 60)
    print("\n下一步:")
    print("  1. 查看完整文档: docs/INTELLIGENCE_PHASE1_GUIDE.md")
    print("  2. 运行测试: pytest tests/intelligence/ -v")
    print('  3. 集成到系统: 参考文档中的"集成到现有系统"章节')
    print("\n")


if __name__ == "__main__":
    main()
