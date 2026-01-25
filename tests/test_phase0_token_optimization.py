"""
Phase 0 Token优化效果测试
测试 exclude_none 和 exclude_defaults 参数对token消耗的影响
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from typing import Any, Dict, List, Optional

import pytest
from pydantic import BaseModel, Field

# ========== 模拟项目中的数据模型 ==========


class SearchReference(BaseModel):
    """搜索引用（基于项目实际模型）"""

    source_tool: str
    title: str
    url: Optional[str] = None
    snippet: str
    relevance_score: Optional[float] = None
    quality_score: Optional[float] = None
    deliverable_id: str
    query: str
    timestamp: str
    llm_relevance_score: Optional[int] = None
    llm_scoring_reason: Optional[str] = None


class DeliverableOutput(BaseModel):
    """交付物输出（基于项目实际模型）"""

    deliverable_name: str
    content: str
    completion_status: str
    completion_rate: Optional[float] = None
    quality_self_assessment: Optional[float] = None
    search_references: Optional[List[SearchReference]] = None


class TaskExecutionReport(BaseModel):
    """任务执行报告（基于项目实际模型）"""

    deliverable_outputs: List[DeliverableOutput]
    task_completion_summary: str
    additional_insights: Optional[List[str]] = None
    execution_challenges: Optional[List[str]] = None


# ========== 测试数据生成器 ==========


def create_sample_deliverable(with_optionals: bool = False) -> DeliverableOutput:
    """创建示例交付物"""
    data = {
        "deliverable_name": "空间功能分区方案",
        "content": "基于用户需求，我们提出以下空间功能分区方案：1. 玄关区域（5㎡）2. 客厅区域（30㎡）3. 餐厅区域（15㎡）",
        "completion_status": "completed",
    }

    if with_optionals:
        data["completion_rate"] = 1.0
        data["quality_self_assessment"] = 0.95
        data["search_references"] = [
            SearchReference(
                source_tool="tavily",
                title="现代住宅空间设计指南",
                url="https://example.com/guide",
                snippet="本指南介绍了现代住宅空间设计的核心原则",
                relevance_score=0.92,
                quality_score=85.0,
                deliverable_id="2-1_1_143022",
                query="现代住宅空间设计",
                timestamp="2025-01-04T10:30:00",
                llm_relevance_score=90,
                llm_scoring_reason="高度相关的专业设计资源",
            )
        ]

    return DeliverableOutput(**data)


def create_sample_task_report(num_deliverables: int = 3, with_optionals: bool = False) -> TaskExecutionReport:
    """创建示例任务执行报告"""
    deliverables = [create_sample_deliverable(with_optionals) for _ in range(num_deliverables)]

    data = {
        "deliverable_outputs": deliverables,
        "task_completion_summary": "成功完成所有任务，交付物质量优秀",
    }

    if with_optionals:
        data["additional_insights"] = ["用户对现代简约风格有明确偏好", "预算控制在合理范围内"]
        data["execution_challenges"] = ["空间限制需要创意解决方案"]

    return TaskExecutionReport(**data)


# ========== Token计数辅助函数 ==========


def count_json_tokens(json_str: str) -> int:
    """
    简单的 token 计数辅助函数，仅用于测试中对序列化方式的相对比较。
    注意：这不是精确的 token 计数实现，而是基于字符数的粗略估算。
    实际生产环境中应使用如 tiktoken 等专门库进行准确计数。
    这里使用简化版本：1 token ≈ 4 characters (GPT-4 标准) 这一经验公式，仅作近似参考。
    """
    return len(json_str) // 4

def serialize_standard(model: BaseModel) -> str:
    """标准序列化（不排除None和默认值）"""
    return json.dumps(model.model_dump(), ensure_ascii=False, indent=None)


def serialize_optimized(model: BaseModel) -> str:
    """优化序列化（Phase 0：排除None和默认值）"""
    return json.dumps(model.model_dump(exclude_none=True, exclude_defaults=True), ensure_ascii=False, indent=None)


# ========== 测试用例 ==========


class TestPhase0TokenOptimization:
    """Phase 0 Token优化效果测试套件"""

    def test_single_deliverable_without_optionals(self):
        """测试单个交付物（无可选字段）的token节省"""
        deliverable = create_sample_deliverable(with_optionals=False)

        standard_json = serialize_standard(deliverable)
        optimized_json = serialize_optimized(deliverable)

        standard_tokens = count_json_tokens(standard_json)
        optimized_tokens = count_json_tokens(optimized_json)

        savings = standard_tokens - optimized_tokens
        savings_pct = (savings / standard_tokens * 100) if standard_tokens > 0 else 0

        print(f"\n【单个交付物（无可选字段）】")
        print(f"  标准序列化: {standard_tokens} tokens ({len(standard_json)} chars)")
        print(f"  优化序列化: {optimized_tokens} tokens ({len(optimized_json)} chars)")
        print(f"  节省: {savings} tokens ({savings_pct:.1f}%)")
        print(f"  标准JSON示例:\n{standard_json[:200]}...")
        print(f"  优化JSON示例:\n{optimized_json[:200]}...")

        # 断言：应该有一定的token节省
        assert savings >= 0, "优化后应该节省或持平"

    def test_single_deliverable_with_optionals(self):
        """测试单个交付物（包含可选字段）的token节省"""
        deliverable = create_sample_deliverable(with_optionals=True)

        standard_json = serialize_standard(deliverable)
        optimized_json = serialize_optimized(deliverable)

        standard_tokens = count_json_tokens(standard_json)
        optimized_tokens = count_json_tokens(optimized_json)

        savings = standard_tokens - optimized_tokens
        savings_pct = (savings / standard_tokens * 100) if standard_tokens > 0 else 0

        print(f"\n【单个交付物（包含可选字段）】")
        print(f"  标准序列化: {standard_tokens} tokens ({len(standard_json)} chars)")
        print(f"  优化序列化: {optimized_tokens} tokens ({len(optimized_json)} chars)")
        print(f"  节省: {savings} tokens ({savings_pct:.1f}%)")

        # 由于有实际值，节省应该较少
        assert savings >= 0, "优化后应该节省或持平"

    def test_task_report_without_optionals(self):
        """测试任务报告（无可选字段）的token节省"""
        report = create_sample_task_report(num_deliverables=3, with_optionals=False)

        standard_json = serialize_standard(report)
        optimized_json = serialize_optimized(report)

        standard_tokens = count_json_tokens(standard_json)
        optimized_tokens = count_json_tokens(optimized_json)

        savings = standard_tokens - optimized_tokens
        savings_pct = (savings / standard_tokens * 100) if standard_tokens > 0 else 0

        print(f"\n【任务报告（3个交付物，无可选字段）】")
        print(f"  标准序列化: {standard_tokens} tokens ({len(standard_json)} chars)")
        print(f"  优化序列化: {optimized_tokens} tokens ({len(optimized_json)} chars)")
        print(f"  节省: {savings} tokens ({savings_pct:.1f}%)")

        # 无可选字段的情况下，应该有显著节省
        assert savings > 0, "排除None应该节省token"
        assert savings_pct >= 10, f"节省应该≥10%，实际{savings_pct:.1f}%"

    def test_task_report_with_optionals(self):
        """测试任务报告（包含可选字段）的token节省"""
        report = create_sample_task_report(num_deliverables=5, with_optionals=True)

        standard_json = serialize_standard(report)
        optimized_json = serialize_optimized(report)

        standard_tokens = count_json_tokens(standard_json)
        optimized_tokens = count_json_tokens(optimized_json)

        savings = standard_tokens - optimized_tokens
        savings_pct = (savings / standard_tokens * 100) if standard_tokens > 0 else 0

        print(f"\n【任务报告（5个交付物，包含可选字段）】")
        print(f"  标准序列化: {standard_tokens} tokens ({len(standard_json)} chars)")
        print(f"  优化序列化: {optimized_tokens} tokens ({len(optimized_json)} chars)")
        print(f"  节省: {savings} tokens ({savings_pct:.1f}%)")

        # 有实际值时节省较少，但仍应有节省
        assert savings >= 0, "优化后应该节省或持平"

    def test_large_scale_simulation(self):
        """测试大规模数据的token节省（模拟真实场景）"""
        # 模拟10个专家，每个专家3-5个交付物
        reports = [
            create_sample_task_report(num_deliverables=i % 3 + 3, with_optionals=(i % 2 == 0)) for i in range(10)
        ]

        total_standard_tokens = 0
        total_optimized_tokens = 0

        for report in reports:
            total_standard_tokens += count_json_tokens(serialize_standard(report))
            total_optimized_tokens += count_json_tokens(serialize_optimized(report))

        total_savings = total_standard_tokens - total_optimized_tokens
        savings_pct = (total_savings / total_standard_tokens * 100) if total_standard_tokens > 0 else 0

        print(f"\n【大规模模拟（10个专家报告）】")
        print(f"  标准序列化总计: {total_standard_tokens} tokens")
        print(f"  优化序列化总计: {total_optimized_tokens} tokens")
        print(f"  总节省: {total_savings} tokens ({savings_pct:.1f}%)")

        # 根据计划，Phase 0预期节省15-25%
        assert savings_pct >= 10, f"大规模数据应该节省≥10%，实际{savings_pct:.1f}%"

        # 成本节省估算（假设GPT-4价格）
        input_cost_per_1k = 0.03  # $0.03/1K tokens
        monthly_calls = 1000 * 20  # 1000会话 × 20次调用

        monthly_savings_tokens = (total_savings / 10) * monthly_calls
        monthly_cost_savings = (monthly_savings_tokens / 1000) * input_cost_per_1k
        annual_cost_savings = monthly_cost_savings * 12

        print(f"\n【成本节省估算】")
        print(f"  月调用次数: {monthly_calls}")
        print(f"  月节省tokens: {monthly_savings_tokens:,.0f}")
        print(f"  月节省成本: ${monthly_cost_savings:.2f}")
        print(f"  年节省成本: ${annual_cost_savings:.2f}")

    def test_data_integrity(self):
        """测试数据完整性（确保优化不丢失有效数据）"""
        report = create_sample_task_report(num_deliverables=2, with_optionals=True)

        standard_dict = report.model_dump()
        optimized_dict = report.model_dump(exclude_none=True, exclude_defaults=True)

        # 检查必需字段是否都存在
        assert "deliverable_outputs" in optimized_dict
        assert "task_completion_summary" in optimized_dict

        # 检查有值的可选字段是否保留
        assert "additional_insights" in optimized_dict
        assert len(optimized_dict["additional_insights"]) > 0

        # 检查deliverable数量一致
        assert len(standard_dict["deliverable_outputs"]) == len(optimized_dict["deliverable_outputs"])

        print(f"\n【数据完整性测试】")
        print(f"  标准序列化字段数: {len(standard_dict)}")
        print(f"  优化序列化字段数: {len(optimized_dict)}")
        print(f"  [OK] 所有必需字段和有值的可选字段均保留")


if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v", "-s"])
