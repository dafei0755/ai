"""
V1.5 项目可行性分析师智能体

负责验证资源约束、检测冲突、计算优先级，提供项目管理范式的可行性分析
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml
from langchain_core.runnables import RunnableConfig
from loguru import logger

from ..core.prompt_manager import PromptManager
from ..core.state import AgentType, ProjectAnalysisState
from ..core.types import AnalysisResult
from .base import LLMAgent


class FeasibilityAnalystAgent(LLMAgent):
    """V1.5 项目可行性分析师智能体"""

    def __init__(self, llm_model, config: Dict[str, Any] | None = None):
        super().__init__(
            agent_type=AgentType.REQUIREMENTS_ANALYST,  # 暂时复用，后续可扩展
            name="项目可行性分析师",
            description="验证资源约束、检测冲突、计算优先级，提供可行性分析",
            llm_model=llm_model,
            config=config
        )

        # 初始化提示词管理器
        self.prompt_manager = PromptManager()

        # 加载行业标准知识库
        self.industry_standards = self._load_industry_standards()

        # 初始化子引擎
        self.cost_calculator = CostCalculator(self.industry_standards)
        self.conflict_detector = ConflictDetector(self.industry_standards)
        self.priority_engine = PriorityEngine(self.industry_standards)

    def _load_industry_standards(self) -> Dict[str, Any]:
        """加载行业标准知识库"""
        try:
            standards_path = Path(__file__).parent.parent / "knowledge_base" / "industry_standards.yaml"

            if not standards_path.exists():
                logger.warning(f"️ 行业标准文件不存在: {standards_path}")
                return {}

            with open(standards_path, encoding='utf-8') as f:
                standards = yaml.safe_load(f)

            logger.info(f" 已加载行业标准知识库: {standards.get('version', 'unknown')}")
            return standards

        except Exception as e:
            logger.error(f" 加载行业标准失败: {e}")
            return {}

    def validate_input(self, state: ProjectAnalysisState) -> bool:
        """验证输入是否有效 - 需要V1的输出"""
        # V1.5依赖V1的输出
        structured_requirements = state.get("structured_requirements", {})
        return bool(structured_requirements.get("project_task"))

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        prompt_config = self.prompt_manager.get_prompt("feasibility_analyst", return_full_config=True)

        if not prompt_config:
            raise ValueError(
                " 未找到V1.5提示词配置: feasibility_analyst\n"
                "请确保配置文件存在: config/prompts/feasibility_analyst.yaml"
            )

        system_prompt = prompt_config.get("system_prompt", "")

        if not system_prompt:
            raise ValueError(" 配置文件中缺少 system_prompt 字段")

        logger.info(f"[V1.5] 已加载可行性分析师提示词: {len(system_prompt)} 字符")

        return system_prompt

    def get_task_description(self, state: ProjectAnalysisState) -> str:
        """获取具体任务描述"""
        # 获取V1的输出
        structured_requirements = state.get("structured_requirements", {})

        task_description = f"""
# V1.5 可行性分析任务

## 输入：V1需求分析师的输出

```json
{json.dumps(structured_requirements, ensure_ascii=False, indent=2)}
```

## 你的任务

基于V1的输出，执行以下4个阶段的分析：

1. **需求拆解与成本估算** - 识别关键词，匹配行业标准，计算总成本
2. **冲突检测** - 检查预算/时间/空间可行性，识别缺口
3. **优先级计算** - 为每个需求计算priority_score
4. **决策建议生成** - 生成3-5个可行方案（保预算/保品质/分期/降级）

## 输出要求

必须输出JSON格式，包含以下字段：
- `feasibility_assessment` - 总体可行性评估
- `conflict_detection` - 冲突检测结果
- `priority_matrix` - 优先级矩阵
- `recommendations` - 决策建议方案
- `risk_flags` - 风险标记

请严格按照系统提示词中的格式和逻辑进行分析。
"""

        return task_description

    def execute(
        self,
        state: ProjectAnalysisState,
        config: RunnableConfig,
        store: Any | None = None
    ) -> AnalysisResult:
        """
        执行V1.5可行性分析
        
        Args:
            state: 项目分析状态
            config: 运行配置
            store: 可选的存储对象
            
        Returns:
            AnalysisResult: 分析结果
        """
        import time
        start_time = time.time()
        
        try:
            logger.info(f" [V1.5] 开始可行性分析: session={state.get('session_id')}")
            
            # 验证输入
            if not self.validate_input(state):
                raise ValueError(" 无效输入: 缺少V1需求分析师的输出(structured_requirements)")
            
            # 准备消息
            messages = self.prepare_messages(state)
            
            # 调用LLM
            logger.info("[V1.5] 调用LLM进行可行性分析...")
            response = self.invoke_llm(messages)
            
            # 解析和验证结果
            result = self.parse_and_validate_result(response.content, state)
            
            end_time = time.time()
            self._track_execution_time(start_time, end_time)
            
            # AnalysisResult 使用 confidence 来表示结果质量
            if result.confidence >= 0.8:
                logger.info(f" [V1.5] 可行性分析完成，耗时: {end_time - start_time:.2f}s，置信度: {result.confidence}")
            else:
                logger.warning(f"️ [V1.5] 可行性分析完成但置信度较低: {result.confidence}")
            
            return result
            
        except Exception as e:
            logger.error(f" [V1.5] 可行性分析失败: {e}")
            error = self.handle_error(e, "V1.5 feasibility analysis")
            raise error

    def parse_and_validate_result(
        self,
        raw_response: str,
        state: ProjectAnalysisState
    ) -> AnalysisResult:
        """解析和验证LLM返回结果"""
        try:
            # 提取JSON（可能包含markdown代码块）
            json_match = re.search(r'```json\s*(.*?)\s*```', raw_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试查找JSON对象
                first_brace = raw_response.find('{')
                last_brace = raw_response.rfind('}')
                if first_brace != -1 and last_brace != -1:
                    json_str = raw_response[first_brace:last_brace + 1]
                else:
                    json_str = raw_response

            # 解析JSON
            feasibility_data = json.loads(json_str)

            # 验证必需字段
            required_fields = [
                "feasibility_assessment",
                "conflict_detection",
                "priority_matrix",
                "recommendations"
            ]

            missing_fields = [f for f in required_fields if f not in feasibility_data]

            if missing_fields:
                logger.warning(f"️ V1.5输出缺少字段: {missing_fields}")

            # 构建成功结果 - 使用正确的 AnalysisResult 构造参数
            return self.create_analysis_result(
                content=raw_response,
                structured_data=feasibility_data,
                confidence=1.0 if not missing_fields else 0.8,
                sources=["V1_requirements_analysis", "industry_standards"]
            )

        except json.JSONDecodeError as e:
            logger.error(f" V1.5 JSON解析失败: {e}")

            # 返回带有原始响应的结果
            return self.create_analysis_result(
                content=raw_response,
                structured_data={"error": f"JSON解析失败: {e}", "raw_response": raw_response},
                confidence=0.0,
                sources=[]
            )

        except Exception as e:
            logger.error(f" V1.5结果验证失败: {e}")

            return self.create_analysis_result(
                content=raw_response,
                structured_data={"error": f"结果验证失败: {e}", "raw_response": raw_response},
                confidence=0.0,
                sources=[]
            )


# ==================== 子引擎类 ====================

class CostCalculator:
    """成本计算器 - 基于行业标准估算需求成本"""

    def __init__(self, industry_standards: Dict[str, Any]):
        self.standards = industry_standards

    def estimate_cost(self, requirement_text: str) -> Tuple[int, int, int]:
        """
        估算需求成本

        Returns:
            (min_cost, typical_cost, max_cost)
        """
        # 关键词匹配
        keywords = self.standards.get("cost_keywords", {})

        total_min = 0
        total_typical = 0
        total_max = 0

        # 智能家居
        if any(kw in requirement_text for kw in ["智能家居", "全屋智能", "智能控制"]):
            smart_costs = self.standards.get("residential_costs", {}).get("smart_home", {}).get("core_system", {})
            cost_range = smart_costs.get("total_cost", [40000, 70000])
            total_min += cost_range[0]
            total_max += cost_range[1]
            total_typical += (cost_range[0] + cost_range[1]) // 2

        # 私人影院
        if any(kw in requirement_text for kw in ["影院", "私人影院", "家庭影院"]):
            theater_costs = self.standards.get("residential_costs", {}).get("home_theater", {}).get("standard", {})
            cost_range = theater_costs.get("total_cost", [60000, 120000])
            total_min += cost_range[0]
            total_max += cost_range[1]
            total_typical += (cost_range[0] + cost_range[1]) // 2

        return (total_min, total_typical, total_max)


class ConflictDetector:
    """冲突检测器 - 检测资源约束冲突"""

    def __init__(self, industry_standards: Dict[str, Any]):
        self.standards = industry_standards
        self.thresholds = industry_standards.get("conflict_thresholds", {})

    def detect_budget_conflict(
        self,
        available_budget: int | None,
        estimated_cost: int
    ) -> Dict[str, Any]:
        """检测预算冲突"""
        if available_budget is None or available_budget == 0:
            return {
                "type": "预算vs功能冲突",
                "severity": "medium",
                "detected": True,
                "description": "预算未明确，建议确定预算区间以便规划"
            }

        gap = estimated_cost - available_budget

        # 修复：gap_ratio应该是gap占available_budget的比例（而不是estimated_cost占比）
        # 例如：估算34万，预算20万，gap=14万，gap_ratio = 14/20 = 0.7 (70%)
        gap_ratio = gap / available_budget if available_budget > 0 else 999

        # 根据阈值判断严重性（注意：阈值是总成本超预算的倍数，需要转换）
        budget_thresholds = self.thresholds.get("budget", {})

        # 重新理解阈值：
        # critical: 1.5 表示总成本是预算的1.5倍以上（超预算50%+）
        # 所以应该比较 estimated_cost / available_budget 与阈值
        cost_ratio = estimated_cost / available_budget if available_budget > 0 else 999

        if cost_ratio >= budget_thresholds.get("critical", 1.5):
            severity = "critical"
        elif cost_ratio >= budget_thresholds.get("high", 1.25):
            severity = "high"
        elif cost_ratio >= budget_thresholds.get("medium", 1.1):
            severity = "medium"
        elif cost_ratio >= budget_thresholds.get("low", 1.05):
            severity = "low"
        else:
            severity = "none"

        return {
            "type": "预算vs功能冲突",
            "severity": severity,
            "detected": gap > 0,
            "details": {
                "available_budget": available_budget,
                "estimated_cost": estimated_cost,
                "gap": gap,
                "gap_percentage": int(gap_ratio * 100) if gap > 0 else 0
            },
            "description": f"预算{available_budget//10000}万，但需求成本{estimated_cost//10000}万，缺口{gap//10000}万（超预算{int(gap_ratio*100)}%）" if gap > 0 else "预算充足"
        }

    def detect_timeline_conflict(
        self,
        available_days: int | None,
        required_days: int
    ) -> Dict[str, Any]:
        """检测工期冲突"""
        if available_days is None:
            return {
                "type": "时间vs质量冲突",
                "severity": "low",
                "detected": False,
                "description": "工期未明确，建议规划合理时间线"
            }

        gap = required_days - available_days

        # 使用cost_ratio逻辑：required_days / available_days
        time_ratio = required_days / available_days if available_days > 0 else 999

        # 判断严重性
        timeline_thresholds = self.thresholds.get("timeline", {})

        if time_ratio >= timeline_thresholds.get("critical", 2.0):
            severity = "critical"
        elif time_ratio >= timeline_thresholds.get("high", 1.5):
            severity = "high"
        elif time_ratio >= timeline_thresholds.get("medium", 1.2):
            severity = "medium"
        elif time_ratio >= timeline_thresholds.get("low", 1.1):
            severity = "low"
        else:
            severity = "none"

        return {
            "type": "时间vs质量冲突",
            "severity": severity,
            "detected": gap > 0,
            "details": {
                "available_days": available_days,
                "required_days": required_days,
                "gap": gap
            },
            "description": f"可用工期{available_days}天，但需要{required_days}天，缺口{gap}天" if gap > 0 else "工期充足"
        }

    def detect_space_conflict(
        self,
        available_area: int | None,
        required_area: int
    ) -> Dict[str, Any]:
        """检测空间冲突"""
        if available_area is None:
            return {
                "type": "空间vs功能冲突",
                "severity": "low",
                "detected": False,
                "description": "面积未明确"
            }

        gap = required_area - available_area

        # 使用area_ratio逻辑：required_area / available_area
        area_ratio = required_area / available_area if available_area > 0 else 999

        # 判断严重性
        space_thresholds = self.thresholds.get("space", {})

        if area_ratio >= space_thresholds.get("critical", 1.5):
            severity = "critical"
        elif area_ratio >= space_thresholds.get("high", 1.3):
            severity = "high"
        elif area_ratio >= space_thresholds.get("medium", 1.15):
            severity = "medium"
        elif area_ratio >= space_thresholds.get("low", 1.05):
            severity = "low"
        else:
            severity = "none"

        return {
            "type": "空间vs功能冲突",
            "severity": severity,
            "detected": gap > 0,
            "details": {
                "available_area": available_area,
                "required_area": required_area,
                "gap": gap
            },
            "description": f"可用面积{available_area}㎡，但需要{required_area}㎡，缺口{gap}㎡" if gap > 0 else "空间充足"
        }


class PriorityEngine:
    """优先级计算引擎 - 计算需求优先级分数"""

    def __init__(self, industry_standards: Dict[str, Any]):
        self.standards = industry_standards
        self.stakeholder_weights = industry_standards.get("stakeholder_weights", {}).get("residential", {})
        self.necessity_levels = industry_standards.get("necessity_levels", {})
        self.time_sensitivity = industry_standards.get("time_sensitivity", {})

    def calculate_priority(
        self,
        requirement: str,
        stakeholder_type: str = "owner",
        necessity_type: str = "social",
        sensitivity_type: str = "important"
    ) -> Tuple[float, Dict[str, float]]:
        """
        计算优先级分数

        Returns:
            (priority_score, breakdown)
        """
        # 获取权重
        stakeholder_weight = self.stakeholder_weights.get(stakeholder_type, 0.40)
        necessity_level = self.necessity_levels.get(necessity_type, {}).get("weight", 0.60)
        time_weight = self.time_sensitivity.get(sensitivity_type, {}).get("weight", 0.75)

        # 计算分数
        priority_score = stakeholder_weight * necessity_level * time_weight

        breakdown = {
            "stakeholder_weight": stakeholder_weight,
            "necessity_level": necessity_level,
            "time_sensitivity": time_weight
        }

        return (priority_score, breakdown)

    def infer_necessity_type(self, requirement_text: str) -> str:
        """推断需求层次类型"""
        # 顺序很重要：先匹配更具体的类别
        if any(kw in requirement_text for kw in ["消防", "防盗", "隐私", "安全"]):
            return "safety"
        elif any(kw in requirement_text for kw in ["基本", "水电", "结构"]):
            return "survival"
        elif any(kw in requirement_text for kw in ["智能", "舒适", "便捷"]):
            return "social"
        elif any(kw in requirement_text for kw in ["品牌", "进口", "奢华", "高端"]):
            return "esteem"
        elif any(kw in requirement_text for kw in ["定制", "艺术", "收藏", "影院"]):
            return "self_actualization"
        else:
            return "social"  # 默认社交需求
