"""
示例质量分析器测试
"""

import pytest

from intelligent_project_analyzer.intelligence.example_quality_analyzer import ExampleQualityAnalyzer, QualityReport
from intelligent_project_analyzer.intelligence.usage_tracker import UsageTracker


class TestExampleQualityAnalyzer:
    """示例质量分析器测试"""

    @pytest.fixture
    def setup_test_data(self, tmp_path):
        """准备测试数据"""
        tracker = UsageTracker(data_dir=tmp_path / "logs", use_sqlite=True)

        # 模拟V2_0角色的使用数据
        role_id = "V2_0"

        # 示例1: 高质量示例（10次使用，8次正面反馈）
        for i in range(10):
            tracker.log_expert_usage(
                role_id=role_id,
                user_request=f"需求分析请求 {i}",
                selected_examples=["v2_0_targeted_requirements_classification_001"],
                output_tokens=1500,
                response_time=2.0,
                user_feedback={"liked": True} if i < 8 else {"rating": 3},
            )

        # 示例2: 低质量示例（5次使用，4次负面反馈）
        for i in range(5):
            tracker.log_expert_usage(
                role_id=role_id,
                user_request=f"综合分析请求 {i}",
                selected_examples=["v2_0_comprehensive_holistic_integration_003"],
                output_tokens=1200,
                response_time=1.5,
                user_feedback={"edited": True, "rating": 2} if i < 4 else None,
            )

        # 示例3: 中等质量示例（3次使用，混合反馈）
        for i in range(3):
            tracker.log_expert_usage(
                role_id=role_id,
                user_request=f"深度挖掘请求 {i}",
                selected_examples=["v2_0_targeted_latent_needs_exploration_002"],
                output_tokens=1800,
                response_time=2.5,
                user_feedback={"liked": True} if i % 2 == 0 else {"rating": 2},
            )

        # 示例4: 未使用示例（存在于文件中但从未被选中）
        # 这个示例不会出现在usage logs中

        analyzer = ExampleQualityAnalyzer(usage_tracker=tracker, output_dir=tmp_path / "reports")

        return analyzer, role_id

    def test_initialization(self, tmp_path):
        """测试初始化"""
        analyzer = ExampleQualityAnalyzer(output_dir=tmp_path / "reports")
        assert analyzer is not None
        assert analyzer.tracker is not None
        assert analyzer.loader is not None
        assert analyzer.output_dir.exists()

    def test_analyze_role(self, setup_test_data):
        """测试角色分析"""
        analyzer, role_id = setup_test_data

        report = analyzer.analyze_role(role_id=role_id, days=30, quality_threshold=0.5, usage_threshold=3)

        assert isinstance(report, QualityReport)
        assert report.role_id == role_id
        assert report.total_examples == 3  # V2_0有3个示例文件
        assert report.used_examples >= 1  # 至少有1个示例被使用

        print("\n分析报告摘要:")
        print(f"  总示例数: {report.total_examples}")
        print(f"  使用的示例: {report.used_examples}")
        print(f"  未使用示例: {len(report.unused_examples)}")
        print(f"  高质量示例: {len(report.high_quality_examples)}")
        print(f"  低质量示例: {len(report.low_quality_examples)}")
        print(f"  质量问题数: {len(report.issues)}")

    def test_identify_high_quality_examples(self, setup_test_data):
        """测试识别高质量示例"""
        analyzer, role_id = setup_test_data

        report = analyzer.analyze_role(role_id, days=30, quality_threshold=0.5)

        # 应该识别出示例1为高质量
        high_quality_ids = [ex["id"] for ex in report.high_quality_examples]
        assert "v2_0_targeted_requirements_classification_001" in high_quality_ids

        # 检查质量分数
        for ex in report.high_quality_examples:
            assert ex["quality_score"] > 0.5
            assert ex["usage_count"] >= 3
            print(f"\n高质量示例: {ex['id']}")
            print(f"  使用次数: {ex['usage_count']}")
            print(f"  质量分数: {ex['quality_score']:.2f}")

    def test_identify_low_quality_examples(self, setup_test_data):
        """测试识别低质量示例"""
        analyzer, role_id = setup_test_data

        report = analyzer.analyze_role(role_id, days=30, quality_threshold=0.5)

        # 应该识别出示例2为低质量
        low_quality_ids = [ex["id"] for ex in report.low_quality_examples]
        assert "v2_0_comprehensive_holistic_integration_003" in low_quality_ids

        # 检查质量分数
        for ex in report.low_quality_examples:
            assert ex["quality_score"] < 0.5
            assert ex["negative_feedback"] > 0
            print(f"\n低质量示例: {ex['id']}")
            print(f"  使用次数: {ex['usage_count']}")
            print(f"  质量分数: {ex['quality_score']:.2f}")
            print(f"  负面反馈: {ex['negative_feedback']}")

    def test_identify_unused_examples(self, setup_test_data):
        """测试识别未使用示例"""
        analyzer, role_id = setup_test_data

        report = analyzer.analyze_role(role_id, days=30)

        # 应该识别出未使用的示例
        # 注意: 这取决于实际的示例文件数量
        print(f"\n未使用示例: {len(report.unused_examples)} 个")
        for ex in report.unused_examples:
            print(f"  - {ex['id']}: {ex['reason']}")

    def test_quality_issues(self, setup_test_data):
        """测试质量问题识别"""
        analyzer, role_id = setup_test_data

        report = analyzer.analyze_role(role_id, days=30)

        assert len(report.issues) > 0

        # 检查问题类型
        issue_types = set(issue.issue_type for issue in report.issues)
        assert len(issue_types) > 0

        # 检查严重程度
        severities = set(issue.severity for issue in report.issues)
        assert severities.issubset({"high", "medium", "low"})

        print("\n质量问题:")
        for issue in report.issues:
            print(f"  [{issue.severity.upper()}] {issue.example_id}")
            print(f"    类型: {issue.issue_type}")
            print(f"    描述: {issue.description}")
            print(f"    建议: {issue.recommendation}")

    def test_recommendations(self, setup_test_data):
        """测试优化建议生成"""
        analyzer, role_id = setup_test_data

        report = analyzer.analyze_role(role_id, days=30)

        assert len(report.recommendations) > 0

        # 检查建议结构
        for rec in report.recommendations:
            assert "type" in rec
            assert "priority" in rec
            assert "description" in rec
            assert "action" in rec
            assert rec["priority"] in ["high", "medium", "low"]

        print("\n优化建议:")
        for rec in report.recommendations:
            print(f"  [{rec['priority'].upper()}] {rec['type']}")
            print(f"    {rec['description']}")
            print(f"    行动: {rec['action']}")

    def test_save_report_json(self, setup_test_data, tmp_path):
        """测试保存JSON报告"""
        analyzer, role_id = setup_test_data
        analyzer.output_dir = tmp_path / "reports"
        analyzer.output_dir.mkdir(parents=True, exist_ok=True)

        report = analyzer.analyze_role(role_id, days=30)

        filepath = analyzer.save_report(report, format="json")

        assert filepath.exists()
        assert filepath.suffix == ".json"

        # 读取并验证
        import json

        with open(filepath, "r", encoding="utf-8") as f:
            loaded_report = json.load(f)
            assert loaded_report["role_id"] == role_id
            assert "summary" in loaded_report

        print(f"\nJSON报告已保存: {filepath}")

    def test_save_report_markdown(self, setup_test_data, tmp_path):
        """测试保存Markdown报告"""
        analyzer, role_id = setup_test_data
        analyzer.output_dir = tmp_path / "reports"
        analyzer.output_dir.mkdir(parents=True, exist_ok=True)

        report = analyzer.analyze_role(role_id, days=30)

        filepath = analyzer.save_report(report, format="markdown")

        assert filepath.exists()
        assert filepath.suffix == ".md"

        # 读取并验证
        content = filepath.read_text(encoding="utf-8")
        assert "# Few-Shot示例质量报告" in content
        assert report.role_id in content

        print(f"\nMarkdown报告已保存: {filepath}")
        print(f"报告内容预览:\n{content[:500]}...")

    def test_report_summary(self, setup_test_data):
        """测试报告摘要"""
        analyzer, role_id = setup_test_data

        report = analyzer.analyze_role(role_id, days=30)

        assert "total_examples" in report.summary
        assert "usage_rate" in report.summary
        assert "high_quality_rate" in report.summary
        assert "issues_count" in report.summary
        assert "critical_issues" in report.summary

        summary = report.summary
        assert 0 <= summary["usage_rate"] <= 1
        assert 0 <= summary["high_quality_rate"] <= 1
        assert summary["issues_count"] == len(report.issues)

        print("\n报告摘要:")
        print(f"  总示例: {summary['total_examples']}")
        print(f"  使用率: {summary['usage_rate']:.1%}")
        print(f"  高质量率: {summary['high_quality_rate']:.1%}")
        print(f"  问题总数: {summary['issues_count']}")
        print(f"  严重问题: {summary['critical_issues']}")

    @pytest.mark.slow
    def test_analyze_all_roles(self, tmp_path):
        """测试分析所有角色"""
        tracker = UsageTracker(data_dir=tmp_path / "logs", use_sqlite=True)

        # 为多个角色模拟数据
        for role_id in ["V2_0", "V3_1"]:
            for i in range(3):
                tracker.log_expert_usage(
                    role_id=role_id,
                    user_request=f"请求 {i}",
                    selected_examples=[f"ex_{i}"],
                    output_tokens=1000,
                    response_time=1.0,
                    user_feedback={"liked": True},
                )

        analyzer = ExampleQualityAnalyzer(usage_tracker=tracker, output_dir=tmp_path / "reports")

        reports = analyzer.analyze_all_roles(days=30)

        # 应该生成多个报告
        assert len(reports) > 0

        # 检查报告文件
        report_files = list((tmp_path / "reports").glob("*.json"))
        assert len(report_files) > 0

        print(f"\n分析了 {len(reports)} 个角色")
        print(f"生成了 {len(report_files)} 个报告文件")


@pytest.mark.slow
def test_integration_full_workflow(tmp_path):
    """测试完整工作流"""
    # 1. 创建跟踪器并记录使用数据
    tracker = UsageTracker(data_dir=tmp_path / "logs", use_sqlite=True)

    role_id = "V2_0"
    for i in range(20):
        tracker.log_expert_usage(
            role_id=role_id,
            user_request=f"综合请求 {i}",
            selected_examples=[
                f"v2_0_targeted_requirements_classification_00{(i % 2) + 1}",
                "v2_0_comprehensive_holistic_integration_003",
            ],
            output_tokens=1500,
            response_time=2.0,
            user_feedback={"liked": True} if i % 3 == 0 else None,
        )

    # 2. 创建分析器并分析
    analyzer = ExampleQualityAnalyzer(usage_tracker=tracker, output_dir=tmp_path / "reports")

    report = analyzer.analyze_role(role_id, days=30)

    # 3. 保存报告
    json_path = analyzer.save_report(report, format="json")
    md_path = analyzer.save_report(report, format="markdown")

    # 4. 验证结果
    assert json_path.exists()
    assert md_path.exists()
    assert report.total_examples > 0
    assert report.used_examples > 0

    print("\n完整工作流测试成功!")
    print("  记录日志: 20 条")
    print("  生成报告: 2 个")
    print(f"  示例总数: {report.total_examples}")
    print(f"  使用示例: {report.used_examples}")
