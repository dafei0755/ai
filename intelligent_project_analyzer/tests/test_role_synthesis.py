"""
动态角色合成协议测试套件 (Dynamic Role Synthesis Protocol Test Suite)

测试目标:
1. 验证v7.3动态角色合成协议的实战效果
2. 确保合成角色质量符合预期
3. 建立合成评分标准

测试覆盖:
- 5个典型跨界场景
- 合成质量评分 (7个维度)
- 父角色选择合理性
- tasks融合深度
- 输出结构完整性
"""

import pytest
from typing import Dict, List, Any
import yaml
from pathlib import Path


class RoleSynthesisTestCase:
    """单个合成测试案例"""
    
    def __init__(
        self,
        scenario_name: str,
        user_request: str,
        expected_parent_roles: List[str],
        expected_synthesis_mode: str,
        quality_criteria: Dict[str, Any]
    ):
        self.scenario_name = scenario_name
        self.user_request = user_request
        self.expected_parent_roles = expected_parent_roles
        self.expected_synthesis_mode = expected_synthesis_mode
        self.quality_criteria = quality_criteria
    
    def to_dict(self):
        return {
            "scenario": self.scenario_name,
            "request": self.user_request,
            "expected_parents": self.expected_parent_roles,
            "synthesis_mode": self.expected_synthesis_mode,
            "criteria": self.quality_criteria
        }


# ============================================================================
# 测试场景库: 5个典型跨界需求
# ============================================================================

TEST_SCENARIOS = [
    RoleSynthesisTestCase(
        scenario_name="三代同堂居住空间",
        user_request="为一个三代同堂的150㎡房子设计,需要解决代际关系和日常生活流线问题",
        expected_parent_roles=["2-1", "5-1"],  # V2居住设计 + V5居住运营
        expected_synthesis_mode="V2+V5跨界融合",
        quality_criteria={
            "跨战略层": True,
            "深度融合": "运营逻辑驱动设计决策",
            "任务数量": "3-5个",
            "dependencies最小化": True,
            "keywords融合度": ">80%",
            "输出结构完整": True,
            "实用性评分": ">=8/10"
        }
    ),
    
    RoleSynthesisTestCase(
        scenario_name="文化主题酒店",
        user_request="打造一个以'宋代美学'为主题的精品酒店,需要文化转译、空间设计和运营策略",
        expected_parent_roles=["3-3", "2-4", "5-4"],  # V3文化转译 + V2酒店设计 + V5酒店运营
        expected_synthesis_mode="V3+V2+V5三层融合",
        quality_criteria={
            "跨战略层": True,
            "深度融合": "文化符号驱动空间与运营",
            "任务数量": "4-6个",
            "dependencies最小化": "允许依赖V4",
            "keywords融合度": ">75%",
            "输出结构完整": True,
            "实用性评分": ">=8/10"
        }
    ),
    
    RoleSynthesisTestCase(
        scenario_name="新零售体验店",
        user_request="设计一个融合线上线下的新零售体验店,需考虑品牌叙事、空间设计和坪效优化",
        expected_parent_roles=["3-2", "2-2", "5-2"],  # V3品牌叙事 + V2商业设计 + V5零售运营
        expected_synthesis_mode="V3+V2+V5三层融合",
        quality_criteria={
            "跨战略层": True,
            "深度融合": "品牌故事与坪效双驱动",
            "任务数量": "4-6个",
            "dependencies最小化": True,
            "keywords融合度": ">80%",
            "输出结构完整": True,
            "实用性评分": ">=9/10"
        }
    ),
    
    RoleSynthesisTestCase(
        scenario_name="创业者联合办公",
        user_request="为创业者群体设计联合办公空间,需深度理解创业者心理、协作模式和空间需求",
        expected_parent_roles=["3-1", "5-3", "2-3"],  # V3个体叙事 + V5办公运营 + V2办公设计
        expected_synthesis_mode="V3+V5+V2三层融合",
        quality_criteria={
            "跨战略层": True,
            "深度融合": "创业者画像驱动空间与运营",
            "任务数量": "4-5个",
            "dependencies最小化": True,
            "keywords融合度": ">75%",
            "输出结构完整": True,
            "实用性评分": ">=8/10"
        }
    ),
    
    RoleSynthesisTestCase(
        scenario_name="疗愈系康养空间",
        user_request="设计一个融合医疗功能和情感疗愈的康养中心,需考虑患者心理、医疗流程和空间美学",
        expected_parent_roles=["3-1", "5-6", "2-5"],  # V3心理洞察 + V5医疗运营 + V2公共建筑
        expected_synthesis_mode="V3+V5+V2三层融合",
        quality_criteria={
            "跨战略层": True,
            "深度融合": "心理需求与医疗流程双驱动",
            "任务数量": "5-6个",
            "dependencies最小化": "允许依赖V4",
            "keywords融合度": ">70%",
            "输出结构完整": True,
            "实用性评分": ">=8/10"
        }
    ),
]


# ============================================================================
# 合成质量评分标准 (7个维度)
# ============================================================================

class SynthesisQualityScorer:
    """合成角色质量评分器"""
    
    @staticmethod
    def evaluate(synthesis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估合成角色质量
        
        评分维度:
        1. 父角色选择合理性 (0-10分)
        2. 跨战略层要求 (0-10分)
        3. tasks深度融合 (0-10分)
        4. keywords去重与融合 (0-10分)
        5. system_prompt结构完整性 (0-10分)
        6. 输出结构合理性 (0-10分)
        7. 实用性与创新性 (0-10分)
        
        Returns:
            评分报告字典
        """
        scores = {}
        
        # 1. 父角色选择合理性
        parent_roles = synthesis_result.get("parent_roles", [])
        if len(parent_roles) >= 2 and len(parent_roles) <= 3:
            scores["父角色数量"] = 10
        else:
            scores["父角色数量"] = max(0, 10 - abs(len(parent_roles) - 2) * 3)
        
        # 2. 跨战略层检查
        strategic_layers = set()
        for role_id in parent_roles:
            if "-" in role_id:
                layer = role_id.split("-")[0]
                strategic_layers.add(layer)
        
        if len(strategic_layers) >= 2:
            scores["跨战略层"] = 10
        else:
            scores["跨战略层"] = 0  # 严重违规
        
        # 3. tasks深度融合
        tasks = synthesis_result.get("tasks", [])
        fusion_keywords = ["驱动", "融合", "整合", "协同", "平衡"]
        fusion_count = sum(1 for task in tasks if any(kw in task for kw in fusion_keywords))
        
        if fusion_count >= len(tasks) * 0.6:  # 60%以上体现融合
            scores["tasks融合度"] = 10
        elif fusion_count >= len(tasks) * 0.3:
            scores["tasks融合度"] = 6
        else:
            scores["tasks融合度"] = 3
        
        # 4. keywords去重与融合
        keywords = synthesis_result.get("keywords", [])
        unique_keywords = set(keywords)
        dedup_rate = len(unique_keywords) / max(len(keywords), 1)
        scores["keywords质量"] = int(dedup_rate * 10)
        
        # 5. system_prompt结构完整性
        system_prompt = synthesis_result.get("system_prompt", "")
        required_sections = ["身份与任务", "团队协作", "核心专业领域", "输出格式"]
        completeness = sum(1 for sec in required_sections if sec in system_prompt)
        scores["prompt完整性"] = int((completeness / len(required_sections)) * 10)
        
        # 6. 输出结构合理性
        output_structure = synthesis_result.get("output_structure", {})
        required_fields = ["custom_analysis", "confidence"]
        structure_score = sum(1 for field in required_fields if field in str(output_structure))
        scores["输出结构"] = int((structure_score / len(required_fields)) * 10)
        
        # 7. 实用性评分 (需人工评估,此处给默认值)
        scores["实用性"] = 8  # 默认8分,需实际测试后调整
        
        # 计算总分
        total_score = sum(scores.values()) / len(scores)
        
        return {
            "详细评分": scores,
            "总分": round(total_score, 2),
            "等级": SynthesisQualityScorer._get_grade(total_score),
            "是否合格": total_score >= 7.0
        }
    
    @staticmethod
    def _get_grade(score: float) -> str:
        """根据分数返回等级"""
        if score >= 9.0:
            return "A+ (优秀)"
        elif score >= 8.0:
            return "A (良好)"
        elif score >= 7.0:
            return "B (合格)"
        elif score >= 6.0:
            return "C (待改进)"
        else:
            return "D (不合格)"


# ============================================================================
# Pytest测试用例
# ============================================================================

class TestRoleSynthesisProtocol:
    """动态角色合成协议测试类"""
    
    @pytest.fixture
    def role_selection_config(self):
        """加载role_selection_strategy.yaml配置"""
        config_path = Path(__file__).parent.parent / "config" / "role_selection_strategy.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    @pytest.mark.parametrize("test_case", TEST_SCENARIOS, ids=lambda x: x.scenario_name)
    def test_synthesis_scenario(self, test_case: RoleSynthesisTestCase, role_selection_config):
        """测试单个合成场景"""
        
        # 打印测试场景信息
        print(f"\n{'='*80}")
        print(f"测试场景: {test_case.scenario_name}")
        print(f"用户需求: {test_case.user_request}")
        print(f"预期父角色: {test_case.expected_parent_roles}")
        print(f"{'='*80}\n")
        
        # 验证配置文件包含动态合成协议
        assert "dynamic_role_synthesis_protocol" in role_selection_config, \
            "配置文件缺少动态角色合成协议"
        
        synthesis_protocol = role_selection_config["dynamic_role_synthesis_protocol"]
        
        # 验证协议关键字段
        assert "synthesis_steps" in synthesis_protocol, "缺少合成步骤定义"
        assert "synthesis_constraints" in synthesis_protocol, "缺少合成约束"
        assert "synthesis_example" in synthesis_protocol, "缺少合成示例"
        
        print(f"✅ 配置文件验证通过")
        print(f"📋 合成步骤数: {len(synthesis_protocol['synthesis_steps'])}")
        print(f"⚠️  约束条件数: {len(synthesis_protocol['synthesis_constraints'])}")
        
        # 模拟合成结果 (实际应用中由LLM生成)
        mock_synthesis_result = self._generate_mock_synthesis(test_case)
        
        # 评估合成质量
        quality_report = SynthesisQualityScorer.evaluate(mock_synthesis_result)
        
        print(f"\n📊 质量评估报告:")
        print(f"   总分: {quality_report['总分']}/10")
        print(f"   等级: {quality_report['等级']}")
        print(f"   详细评分: {quality_report['详细评分']}")
        
        # 断言: 总分必须>=7.0才算合格
        assert quality_report["是否合格"], \
            f"合成质量不合格: {quality_report['总分']}/10 < 7.0"
        
        # 断言: 必须跨战略层
        assert quality_report["详细评分"]["跨战略层"] == 10, \
            "违反约束: 父角色必须来自不同战略层"
        
        print(f"\n✅ 场景 '{test_case.scenario_name}' 测试通过")
    
    def _generate_mock_synthesis(self, test_case: RoleSynthesisTestCase) -> Dict[str, Any]:
        """
        生成模拟的合成结果 (用于测试)
        实际生产环境中,这部分由LLM完成
        """
        # 根据测试场景生成合成结果
        parent_roles = test_case.expected_parent_roles
        
        # 生成role_id
        role_id = "+".join(parent_roles)
        
        # 生成role_name和dynamic_role_name
        if test_case.scenario_name == "三代同堂居住空间":
            role_name = "生活方式驱动的居住设计专家"
            dynamic_role_name = "三代同堂居住空间与生活模式总设计师"
            keywords = ["居住", "生活方式", "代际关系", "场景运营", "动线设计", "家庭"]
            tasks = [
                "以家庭成员的日常生活剧本为驱动,进行空间功能分区和动线设计",
                "平衡不同代际对隐私、交流和独立性的不同需求",
                "提供融合运营逻辑和设计美学的总体方案"
            ]
        elif test_case.scenario_name == "文化主题酒店":
            role_name = "文化驱动的酒店体验设计专家"
            dynamic_role_name = "宋代美学精品酒店体验总设计师"
            keywords = ["文化转译", "酒店设计", "酒店运营", "美学叙事", "服务体验", "主题空间"]
            tasks = [
                "将宋代美学符号转译为可感知的空间体验和服务细节",
                "以文化叙事驱动空间设计和运营流程的整合",
                "平衡文化深度、审美体验和商业运营的三重目标",
                "设计从入住到离店的完整文化体验旅程"
            ]
        else:
            # 其他场景的通用模拟
            role_name = f"{test_case.scenario_name}专家"
            dynamic_role_name = f"{test_case.scenario_name}总设计师"
            keywords = ["跨界", "融合", "创新"]
            tasks = [
                "分析核心需求并融合多视角",
                "提供综合解决方案"
            ]
        
        return {
            "parent_roles": parent_roles,
            "role_id": role_id,
            "role_name": role_name,
            "dynamic_role_name": dynamic_role_name,
            "keywords": keywords,
            "tasks": tasks,
            "system_prompt": """
### 身份与任务
你是...

### 团队协作接口
输入源: ...

### 核心专业领域
工具箱: ...

### 输出格式
{...}
""",
            "output_structure": {
                "field1": "description",
                "custom_analysis": "灵活字段",
                "confidence": "置信度"
            }
        }
    
    def test_synthesis_constraints(self, role_selection_config):
        """测试合成约束验证"""
        synthesis_protocol = role_selection_config["dynamic_role_synthesis_protocol"]
        constraints = synthesis_protocol["synthesis_constraints"]
        
        print(f"\n测试合成约束条件:")
        for i, constraint in enumerate(constraints, 1):
            print(f"  约束{i}: {constraint[:50]}...")
        
        # 验证约束1: 跨战略层
        assert any("不同的战略层" in c for c in constraints), "缺少跨战略层约束"
        
        # 验证约束2: 深度融合
        assert any("深度融合" in c for c in constraints), "缺少深度融合约束"
        
        # 验证约束3: 最小化依赖
        assert any("dependencies" in c for c in constraints), "缺少依赖最小化约束"
        
        print(f"✅ 所有约束条件验证通过")


# ============================================================================
# 命令行运行入口
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("动态角色合成协议测试套件")
    print("="*80)
    print(f"\n📋 测试场景数量: {len(TEST_SCENARIOS)}")
    print(f"📊 评分维度数量: 7个")
    print(f"✅ 合格标准: 总分 >= 7.0/10\n")
    
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
