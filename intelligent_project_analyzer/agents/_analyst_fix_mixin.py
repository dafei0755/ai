"""
需求分析师 修复/补全 Mixin
由 scripts/refactor/_split_mt14_analyst.py 自动生成 (MT-14)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig
    from langgraph.store.base import BaseStore
    from ..workflow.state import ProjectAnalysisState


class AnalystFixMixin:
    """Mixin — 需求分析师 修复/补全 Mixin"""
    def _fix_validation_issues(
        self,
        phase2_result: Dict[str, Any],
        validation_result,
        user_input: str
    ) -> Dict[str, Any]:
        """
        Fix validation issues by generating missing L6/L7

        Args:
            phase2_result: Phase 2 result with issues
            validation_result: Validation result with errors
            user_input: Original user input

        Returns:
            Fixed phase2_result
        """
        errors = validation_result.errors

        # Check if L6 is missing
        if any("L6" in error for error in errors):
            logger.info(" [v7.270] Generating missing L6 assumption audit...")
            phase2_result = self._generate_missing_l6(phase2_result, user_input)

        # Check if L7 is missing
        if any("L7" in error for error in errors):
            logger.info(" [v7.270] Generating missing L7 systemic impact...")
            phase2_result = self._generate_missing_l7(phase2_result, user_input)

        return phase2_result

    def _generate_missing_l6(
        self,
        phase2_result: Dict[str, Any],
        user_input: str
    ) -> Dict[str, Any]:
        """
        Generate L6 assumption audit if missing

        Args:
            phase2_result: Phase 2 result
            user_input: Original user input

        Returns:
            Updated phase2_result with L6
        """
        # Extract context from phase2_result
        analysis_layers = phase2_result.get("analysis_layers", {})
        l4_jtbd = analysis_layers.get("L4_project_task", "")
        l3_tension = analysis_layers.get("L3_core_tension", "")

        prompt = f"""
基于以下项目分析，生成L6假设审计（Assumption Audit）。

**用户需求**: {user_input}

**L4 项目任务**: {l4_jtbd}

**L3 核心张力**: {l3_tension}

---

请生成至少3个核心假设的审计，每个假设必须包含：

1. **assumption**: 隐含的假设（我们认为什么是真的？）
2. **counter_assumption**: 反向假设（如果相反的情况为真会怎样？）
3. **challenge_question**: 挑战性问题（如何测试这个假设？）
4. **impact_if_wrong**: 如果假设错误的影响（后果有多严重？）
5. **alternative_approach**: 替代方案（如果假设失败，有什么其他路径？）

同时提供2-3个非常规方法（unconventional_approaches）。

**输出格式**（纯JSON）:
{{
  "identified_assumptions": [
    {{
      "assumption": "...",
      "counter_assumption": "...",
      "challenge_question": "...",
      "impact_if_wrong": "...",
      "alternative_approach": "..."
    }}
  ],
  "unconventional_approaches": ["方法1", "方法2", "方法3"]
}}
"""

        try:
            response = self.invoke_llm([{"role": "user", "content": prompt}])
            l6_data = self._parse_phase_response(response.content)

            # Inject into phase2_result
            if "analysis_layers" not in phase2_result:
                phase2_result["analysis_layers"] = {}
            phase2_result["analysis_layers"]["L6_assumption_audit"] = l6_data

            logger.info(" [v7.270] L6 assumption audit generated successfully")

        except Exception as e:
            logger.error(f" [v7.270] Failed to generate L6: {e}")
            # Create fallback L6
            phase2_result["analysis_layers"]["L6_assumption_audit"] = {
                "identified_assumptions": [
                    {
                        "assumption": "基于当前信息的假设",
                        "counter_assumption": "待深入分析",
                        "challenge_question": "需要进一步验证",
                        "impact_if_wrong": "可能影响设计方向",
                        "alternative_approach": "待探索替代方案"
                    }
                ],
                "unconventional_approaches": ["待补充非常规方法"]
            }

        return phase2_result

    def _generate_missing_l7(
        self,
        phase2_result: Dict[str, Any],
        user_input: str
    ) -> Dict[str, Any]:
        """
        Generate L7 systemic impact if missing

        Args:
            phase2_result: Phase 2 result
            user_input: Original user input

        Returns:
            Updated phase2_result with L7
        """
        # Extract context
        analysis_layers = phase2_result.get("analysis_layers", {})
        l4_jtbd = analysis_layers.get("L4_project_task", "")
        structured_output = phase2_result.get("structured_output", {})
        project_task = structured_output.get("project_task", "")

        prompt = f"""
基于以下项目分析，生成L7系统性影响分析（Systemic Impact Analysis）。

**用户需求**: {user_input}

**项目任务**: {project_task or l4_jtbd}

---

请分析项目的长期和生态系统影响，必须覆盖三个时间维度：

**1. 短期影响（0-1年）**
- social: 社会影响
- environmental: 环境影响
- economic: 经济影响
- cultural: 文化影响

**2. 中期影响（1-5年）**
- social, environmental, economic, cultural

**3. 长期影响（5年+）**
- social, environmental, economic, cultural

**4. 非预期后果（至少2个）**
- 成功可能带来的负面效应
- 设计决策的连锁反应

**5. 缓解策略**
- 针对识别的风险的应对措施

**输出格式**（纯JSON）:
{{
  "short_term": {{
    "social": "...",
    "environmental": "...",
    "economic": "...",
    "cultural": "..."
  }},
  "medium_term": {{
    "social": "...",
    "environmental": "...",
    "economic": "...",
    "cultural": "..."
  }},
  "long_term": {{
    "social": "...",
    "environmental": "...",
    "economic": "...",
    "cultural": "..."
  }},
  "unintended_consequences": [
    "后果1",
    "后果2"
  ],
  "mitigation_strategies": [
    "策略1",
    "策略2"
  ]
}}
"""

        try:
            response = self.invoke_llm([{"role": "user", "content": prompt}])
            l7_data = self._parse_phase_response(response.content)

            # Inject into phase2_result
            if "analysis_layers" not in phase2_result:
                phase2_result["analysis_layers"] = {}
            phase2_result["analysis_layers"]["L7_systemic_impact"] = l7_data

            logger.info(" [v7.270] L7 systemic impact generated successfully")

        except Exception as e:
            logger.error(f" [v7.270] Failed to generate L7: {e}")
            # Create fallback L7
            phase2_result["analysis_layers"]["L7_systemic_impact"] = {
                "short_term": {
                    "social": "待分析短期社会影响",
                    "environmental": "待分析短期环境影响",
                    "economic": "待分析短期经济影响",
                    "cultural": "待分析短期文化影响"
                },
                "medium_term": {
                    "social": "待分析中期社会影响",
                    "environmental": "待分析中期环境影响",
                    "economic": "待分析中期经济影响",
                    "cultural": "待分析中期文化影响"
                },
                "long_term": {
                    "social": "待分析长期社会影响",
                    "environmental": "待分析长期环境影响",
                    "economic": "待分析长期经济影响",
                    "cultural": "待分析长期文化影响"
                },
                "unintended_consequences": ["待识别非预期后果"],
                "mitigation_strategies": ["待制定缓解策略"]
            }

        return phase2_result

