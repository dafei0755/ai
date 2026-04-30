"""
V1.5 项目可行性分析师测试用例

测试三大核心功能：
1. 冲突检测（预算/时间/空间）
2. 优先级计算
3. 决策建议生成
"""

import pytest
from intelligent_project_analyzer.agents.feasibility_analyst import (
    CostCalculator,
    ConflictDetector,
    PriorityEngine
)


# ==================== 测试数据 ====================

# 模拟行业标准数据
MOCK_INDUSTRY_STANDARDS = {
    "version": "1.0",
    "residential_costs": {
        "smart_home": {
            "core_system": {
                "total_cost": [40000, 70000]
            }
        },
        "home_theater": {
            "standard": {
                "total_cost": [60000, 120000]
            }
        }
    },
    "conflict_thresholds": {
        "budget": {
            "critical": 1.5,
            "high": 1.25,
            "medium": 1.1,
            "low": 1.05
        },
        "timeline": {
            "critical": 2.0,
            "high": 1.5,
            "medium": 1.2,
            "low": 1.1
        },
        "space": {
            "critical": 1.5,
            "high": 1.3,
            "medium": 1.15,
            "low": 1.05
        }
    },
    "stakeholder_weights": {
        "residential": {
            "owner": 0.40,
            "family_members": 0.30,
            "guests": 0.15,
            "investment_value": 0.15
        }
    },
    "necessity_levels": {
        "survival": {"weight": 1.0},
        "safety": {"weight": 0.85},
        "social": {"weight": 0.70},
        "esteem": {"weight": 0.60},
        "self_actualization": {"weight": 0.50}
    },
    "time_sensitivity": {
        "urgent": {"weight": 1.0},
        "important": {"weight": 0.75},
        "normal": {"weight": 0.50},
        "nice_to_have": {"weight": 0.30}
    }
}


# ==================== CostCalculator 测试 ====================

class TestCostCalculator:
    """成本计算器测试"""

    def test_estimate_smart_home_cost(self):
        """测试智能家居成本估算"""
        calculator = CostCalculator(MOCK_INDUSTRY_STANDARDS)

        min_cost, typical_cost, max_cost = calculator.estimate_cost("全屋智能家居系统")

        assert min_cost == 40000
        assert max_cost == 70000
        assert typical_cost == 55000

    def test_estimate_home_theater_cost(self):
        """测试私人影院成本估算"""
        calculator = CostCalculator(MOCK_INDUSTRY_STANDARDS)

        min_cost, typical_cost, max_cost = calculator.estimate_cost("私人影院")

        assert min_cost == 60000
        assert max_cost == 120000
        assert typical_cost == 90000

    def test_estimate_combined_cost(self):
        """测试组合需求成本估算"""
        calculator = CostCalculator(MOCK_INDUSTRY_STANDARDS)

        # 智能家居 + 私人影院
        min_cost, typical_cost, max_cost = calculator.estimate_cost(
            "全屋智能家居系统和私人影院"
        )

        # 应该是两者之和
        assert min_cost == 100000  # 40000 + 60000
        assert max_cost == 190000  # 70000 + 120000
        assert typical_cost == 145000  # 55000 + 90000


# ==================== ConflictDetector 测试 ====================

class TestConflictDetector:
    """冲突检测器测试"""

    def test_budget_conflict_critical(self):
        """测试严重预算冲突（用户案例2）"""
        detector = ConflictDetector(MOCK_INDUSTRY_STANDARDS)

        # 20万预算，但需求成本34万
        conflict = detector.detect_budget_conflict(
            available_budget=200000,
            estimated_cost=340000
        )

        assert conflict["detected"] is True
        assert conflict["severity"] == "critical"  # 超预算70%，达到critical阈值（50%）
        assert conflict["details"]["gap"] == 140000
        assert "预算20万" in conflict["description"]
        assert "缺口14万" in conflict["description"]

    def test_budget_conflict_high(self):
        """测试高等级预算冲突"""
        detector = ConflictDetector(MOCK_INDUSTRY_STANDARDS)

        # 20万预算，但需求成本27万
        conflict = detector.detect_budget_conflict(
            available_budget=200000,
            estimated_cost=270000
        )

        assert conflict["detected"] is True
        assert conflict["severity"] == "high"  # 超预算35%，在high范围（25-50%）
        assert conflict["details"]["gap"] == 70000

    def test_budget_conflict_none(self):
        """测试无预算冲突"""
        detector = ConflictDetector(MOCK_INDUSTRY_STANDARDS)

        # 30万预算，需求成本25万
        conflict = detector.detect_budget_conflict(
            available_budget=300000,
            estimated_cost=250000
        )

        assert conflict["detected"] is False
        assert conflict["severity"] == "none"
        assert "预算充足" in conflict["description"]

    def test_timeline_conflict_critical(self):
        """测试严重工期冲突（用户案例3）"""
        detector = ConflictDetector(MOCK_INDUSTRY_STANDARDS)

        # 2个月（60天）要求，但需要90天
        # 90/60 = 1.5，达到high阈值（1.5）
        conflict = detector.detect_timeline_conflict(
            available_days=60,
            required_days=90
        )

        assert conflict["detected"] is True
        assert conflict["severity"] == "high"  # 修正：ratio=1.5，是high而不是medium
        assert conflict["details"]["gap"] == 30
        assert "可用工期60天" in conflict["description"]

    def test_space_conflict_critical(self):
        """测试严重空间冲突（用户案例4）"""
        detector = ConflictDetector(MOCK_INDUSTRY_STANDARDS)

        # 60㎡要放4房2厅，需要86㎡
        # 86/60 = 1.43，达到high阈值（1.3-1.5）
        conflict = detector.detect_space_conflict(
            available_area=60,
            required_area=86
        )

        assert conflict["detected"] is True
        assert conflict["severity"] == "high"  # 修正：ratio=1.43，是high而不是critical
        assert conflict["details"]["gap"] == 26
        assert "可用面积60㎡" in conflict["description"]
        assert "缺口26㎡" in conflict["description"]

    def test_budget_undefined(self):
        """测试预算未明确的情况"""
        detector = ConflictDetector(MOCK_INDUSTRY_STANDARDS)

        conflict = detector.detect_budget_conflict(
            available_budget=None,
            estimated_cost=200000
        )

        assert conflict["detected"] is True
        assert conflict["severity"] == "medium"
        assert "预算未明确" in conflict["description"]


# ==================== PriorityEngine 测试 ====================

class TestPriorityEngine:
    """优先级计算引擎测试"""

    def test_calculate_priority_high(self):
        """测试高优先级需求（业主+社交需求+重要）"""
        engine = PriorityEngine(MOCK_INDUSTRY_STANDARDS)

        priority_score, breakdown = engine.calculate_priority(
            requirement="智能家居系统",
            stakeholder_type="owner",  # 0.40
            necessity_type="social",  # 0.70
            sensitivity_type="important"  # 0.75
        )

        expected_score = 0.40 * 0.70 * 0.75  # = 0.21
        assert abs(priority_score - expected_score) < 0.01
        assert breakdown["stakeholder_weight"] == 0.40
        assert breakdown["necessity_level"] == 0.70
        assert breakdown["time_sensitivity"] == 0.75

    def test_calculate_priority_low(self):
        """测试低优先级需求（访客+自我实现+锦上添花）"""
        engine = PriorityEngine(MOCK_INDUSTRY_STANDARDS)

        priority_score, breakdown = engine.calculate_priority(
            requirement="私人影院",
            stakeholder_type="guests",  # 0.15
            necessity_type="self_actualization",  # 0.50
            sensitivity_type="nice_to_have"  # 0.30
        )

        expected_score = 0.15 * 0.50 * 0.30  # = 0.0225
        assert abs(priority_score - expected_score) < 0.001
        assert breakdown["stakeholder_weight"] == 0.15

    def test_infer_necessity_type_smart_home(self):
        """测试推断需求层次：智能家居 → 社交需求"""
        engine = PriorityEngine(MOCK_INDUSTRY_STANDARDS)

        necessity_type = engine.infer_necessity_type("全屋智能家居系统")
        assert necessity_type == "social"

    def test_infer_necessity_type_luxury(self):
        """测试推断需求层次：奢侈品 → 尊重需求"""
        engine = PriorityEngine(MOCK_INDUSTRY_STANDARDS)

        necessity_type = engine.infer_necessity_type("全进口材料和高端品牌家具")
        assert necessity_type == "esteem"

    def test_infer_necessity_type_theater(self):
        """测试推断需求层次：私人影院 → 自我实现"""
        engine = PriorityEngine(MOCK_INDUSTRY_STANDARDS)

        necessity_type = engine.infer_necessity_type("定制私人影院")
        assert necessity_type == "self_actualization"

    def test_infer_necessity_type_safety(self):
        """测试推断需求层次：安全 → 安全需求"""
        engine = PriorityEngine(MOCK_INDUSTRY_STANDARDS)

        necessity_type = engine.infer_necessity_type("消防安全和防盗系统")
        assert necessity_type == "safety"


# ==================== 集成测试 ====================

class TestIntegration:
    """端到端集成测试 - 使用用户提供的案例"""

    def test_case1_smart_home_flexible_budget(self):
        """用户案例1：智能家居系统，弹性预算"""
        # 模拟V1输出
        v1_output = {
            "project_task": "为[追求便捷生活的现代家庭]+打造[全屋智能空间]+雇佣空间完成[设备自动化联动]与[语音便捷控制]",
            "resource_constraints": "预算: 弹性; 工期: 未明确"
        }

        # 成本估算
        calculator = CostCalculator(MOCK_INDUSTRY_STANDARDS)
        min_cost, typical_cost, max_cost = calculator.estimate_cost(v1_output["project_task"])

        assert min_cost == 40000
        assert typical_cost == 55000

        # 预算冲突检测（预算未明确）
        detector = ConflictDetector(MOCK_INDUSTRY_STANDARDS)
        conflict = detector.detect_budget_conflict(
            available_budget=None,
            estimated_cost=typical_cost
        )

        assert conflict["detected"] is True
        assert "预算未明确" in conflict["description"]

    def test_case2_budget_conflict_20w_for_luxury_villa(self):
        """用户案例2：20万预算装修200㎡别墅，要求全进口材料+智能家居+私人影院"""
        # 成本估算
        calculator = CostCalculator(MOCK_INDUSTRY_STANDARDS)
        min_cost, typical_cost, max_cost = calculator.estimate_cost(
            "全进口材料、智能家居系统、私人影院"
        )

        # 智能家居(5.5万) + 私人影院(9万) = 14.5万
        # 加上200㎡×1500元/㎡=30万装修 → 总计约45万
        # 简化测试：仅计算智能+影院
        assert typical_cost >= 145000  # 14.5万

        # 冲突检测
        detector = ConflictDetector(MOCK_INDUSTRY_STANDARDS)
        conflict = detector.detect_budget_conflict(
            available_budget=200000,
            estimated_cost=340000  # 假设总成本34万
        )

        assert conflict["detected"] is True
        assert conflict["severity"] == "critical"
        assert conflict["details"]["gap"] == 140000  # 缺口14万

    def test_case3_timeline_conflict_2months_for_fine_work(self):
        """用户案例3：2个月完成精装修，要求工艺精细"""
        # 工期冲突检测
        detector = ConflictDetector(MOCK_INDUSTRY_STANDARDS)
        conflict = detector.detect_timeline_conflict(
            available_days=60,  # 2个月
            required_days=90  # 精装修标准工期
        )

        assert conflict["detected"] is True
        assert conflict["severity"] in ["medium", "high"]
        assert conflict["details"]["gap"] == 30  # 缺口30天

    def test_case4_space_conflict_60sqm_4bedroom(self):
        """用户案例4：60㎡小户型要4房2厅，每个房间独立卫生间"""
        # 空间冲突检测
        detector = ConflictDetector(MOCK_INDUSTRY_STANDARDS)

        # 最小空间需求：4房(10㎡×4) + 2厅(15㎡×2) + 4卫(4㎡×4) = 86㎡
        # 86/60 = 1.43，达到high阈值
        conflict = detector.detect_space_conflict(
            available_area=60,
            required_area=86
        )

        assert conflict["detected"] is True
        assert conflict["severity"] == "high"  # 修正：ratio=1.43，是high
        assert conflict["details"]["gap"] == 26  # 缺口26㎡

    def test_priority_ranking_smart_home_vs_theater(self):
        """测试优先级排序：智能家居 vs 私人影院"""
        engine = PriorityEngine(MOCK_INDUSTRY_STANDARDS)

        # 智能家居：业主+社交需求+重要
        smart_score, _ = engine.calculate_priority(
            requirement="智能家居",
            stakeholder_type="owner",  # 0.40
            necessity_type="social",  # 0.70
            sensitivity_type="important"  # 0.75
        )

        # 私人影院：业主+自我实现+一般
        theater_score, _ = engine.calculate_priority(
            requirement="私人影院",
            stakeholder_type="owner",  # 0.40
            necessity_type="self_actualization",  # 0.50
            sensitivity_type="normal"  # 0.50
        )

        # 智能家居优先级应该更高
        assert smart_score > theater_score
        # 智能家居: 0.40 × 0.70 × 0.75 = 0.21
        # 私人影院: 0.40 × 0.50 × 0.50 = 0.10
        assert abs(smart_score - 0.21) < 0.01
        assert abs(theater_score - 0.10) < 0.01


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
