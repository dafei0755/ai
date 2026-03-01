"""
项目专属维度生成器 (v8.0)
=====================

核心思想：到雷达图时，系统已完成深度需求分析+任务梳理。
雷达图是"AI分析校准 + 不确定性决策 + 盲区捕获"的最后关口。

三层架构：
  - 校准维度 (calibration): AI已有推断，让用户确认/纠正
  - 决策维度 (decision): 真正的两难取舍，需用户做决定
  - 洞察维度 (insight): 用户没说但会深刻影响结果的

三不问原则：不问已答、不问常识、不问底线
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger


class ProjectSpecificDimensionGenerator:
    """
    项目专属维度生成器

    基于 Phase2 深度分析结果 + Step1 确认任务 + 不确定性信号，
    由 LLM 生成 7-10 个项目定制的雷达图维度。
    """

    # 合法的 source 值
    VALID_SOURCES = {"calibration", "decision", "insight"}

    # 合法的 category 值
    VALID_CATEGORIES = {"aesthetic", "functional", "technology", "resource", "experience", "special"}

    # 底线/负面词检测（标签对称性安全网）
    NEGATIVE_LABEL_PATTERNS = re.compile(
        r"不安全|违规|违法|低质量|差的|坏的|不达标|不合格|危险|有害" r"|不做|拒绝|不允许|禁止|不考虑|不可以|不能|绝对不",
        re.IGNORECASE,
    )

    def __init__(self, timeout_override: Optional[int] = None):
        """初始化生成器

        Args:
            timeout_override: 覆盖默认超时秒数（编排器重试时传入较小值）
        """
        timeout = timeout_override or 60
        logger.info(f"🎯 [v8.0] ProjectSpecificDimensionGenerator 初始化 (timeout={timeout}s)")

        # 加载 Prompt 模板
        self.prompts = self._load_prompts()

        # 创建 LLM 实例
        try:
            from intelligent_project_analyzer.services.llm_factory import LLMFactory

            self.llm = LLMFactory.create_llm(temperature=0.4, timeout=timeout)
            logger.info("  ✅ LLM 实例创建成功 (via LLMFactory)")
        except Exception as e:
            logger.warning(f"  ⚠️ LLMFactory 失败，降级: {e}")
            try:
                from langchain_openai import ChatOpenAI

                self.llm = ChatOpenAI(
                    model=os.getenv("DIMENSION_LLM_MODEL", "gpt-4o-mini"),
                    temperature=0.4,
                    timeout=timeout,
                )
            except Exception as e2:
                logger.error(f"  ❌ LLM 创建完全失败: {e2}")
                self.llm = None

    def _load_prompts(self) -> Dict[str, str]:
        """加载 Prompt 模板"""
        prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "project_specific_dimensions_prompt.yaml"

        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.info(f"  ✅ Prompt 模板加载成功: {prompt_path.name}")
            return config
        except Exception as e:
            logger.error(f"  ❌ Prompt 模板加载失败: {e}")
            return {}

    def generate_dimensions(
        self,
        user_input: str,
        structured_data: Dict[str, Any],
        confirmed_tasks: List[Dict[str, Any]],
        project_type: str = "",
        target_count: int = 9,
    ) -> Dict[str, Any]:
        """
        生成项目专属雷达图维度

        Args:
            user_input: 用户原始需求文本
            structured_data: Phase2 分析结果（含 core_tensions, stakeholder_system 等）
            confirmed_tasks: Step1 用户确认的核心任务列表
            project_type: 项目类型
            target_count: 目标维度数（默认 9，下游会补 2-3 个静态锚点）

        Returns:
            成功时: {"dimensions": [...], "generation_summary": str, "generation_method": "project_specific"}
            失败时: {} (空字典，触发降级)
        """
        if not self.llm:
            logger.warning("🎯 [v8.0] LLM 不可用，返回空结果触发降级")
            return {}

        if not self.prompts.get("system_prompt") or not self.prompts.get("user_prompt"):
            logger.warning("🎯 [v8.0] Prompt 模板不完整，返回空结果触发降级")
            return {}

        try:
            # 构建 Prompt
            system_prompt = self.prompts["system_prompt"]
            user_prompt = self._build_user_prompt(user_input, structured_data, confirmed_tasks, project_type)

            # 调用 LLM
            logger.info("🎯 [v8.0] 正在调用 LLM 生成项目专属维度...")
            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            response_text = self._call_llm(messages)
            logger.info(f"🎯 [v8.0] LLM 响应长度: {len(response_text)} 字符")

            # 解析 JSON
            dimensions = self._extract_dimensions(response_text)

            if not dimensions:
                logger.warning("🎯 [v8.0] JSON 解析失败，返回空结果")
                return {}

            # 验证每个维度
            validated = []
            existing_ids = set()
            for dim in dimensions:
                if self._validate_dimension(dim, existing_ids):
                    validated.append(dim)
                    existing_ids.add(dim["id"])

            logger.info(f"🎯 [v8.0] 验证通过: {len(validated)}/{len(dimensions)} 个维度")

            # 至少需要 5 个有效维度
            if len(validated) < 5:
                logger.warning(f"🎯 [v8.0] 有效维度不足 5 个（仅 {len(validated)}），触发降级")
                return {}

            # 统计三层分布
            calibration_count = sum(1 for d in validated if d.get("source") == "calibration")
            decision_count = sum(1 for d in validated if d.get("source") == "decision")
            insight_count = sum(1 for d in validated if d.get("source") == "insight")

            summary = (
                f"生成{len(validated)}个项目专属维度: " f"校准{calibration_count}个 + 决策{decision_count}个 + 洞察{insight_count}个"
            )
            logger.info(f"🎯 [v8.0] {summary}")

            for dim in validated:
                logger.info(
                    f"  [{dim['source']}] {dim['name']}: "
                    f"{dim['left_label']} ↔ {dim['right_label']} "
                    f"(default={dim['default_value']})"
                )

            return {
                "dimensions": validated,
                "generation_summary": summary,
                "generation_method": "project_specific",
            }

        except Exception as e:
            logger.error(f"🎯 [v8.0] 维度生成异常: {type(e).__name__}: {e}")
            return {}

    def _call_llm(self, messages) -> str:
        """
        调用 LLM 的薄封装层（便于单元测试 mock）

        Args:
            messages: langchain 消息列表

        Returns:
            LLM 响应文本
        """
        response = self.llm.invoke(messages)
        return response.content if hasattr(response, "content") else str(response)

    def _build_user_prompt(
        self,
        user_input: str,
        structured_data: Dict[str, Any],
        confirmed_tasks: List[Dict[str, Any]],
        project_type: str,
    ) -> str:
        """构建 User Prompt，注入所有上下文数据"""
        template = self.prompts.get("user_prompt", "")

        # 格式化确认的任务
        tasks_text = self._format_confirmed_tasks(confirmed_tasks)

        # 提取 Phase2 字段（安全取值，缺失时给空）
        core_tensions = self._format_field(structured_data.get("core_tensions", []))
        stakeholder_system = self._format_field(structured_data.get("stakeholder_system"))
        five_whys = self._format_field(structured_data.get("five_whys_analysis"))
        assumption_audit = self._format_field(structured_data.get("assumption_audit"))
        human_dimensions = self._format_human_dimensions(structured_data)
        ontology_params = self._format_field(structured_data.get("ontology_parameters", []))
        character_narrative = self._format_field(structured_data.get("character_narrative"))
        confidence_score = structured_data.get("confidence_score", 0.0)

        # 不确定性信号
        uncertainty_map = structured_data.get("uncertainty_map", {})
        info_quality = structured_data.get("info_quality_metadata", {})
        missing_dims = info_quality.get("missing_dimensions", [])

        return template.format(
            user_input=user_input or "（无）",
            project_type=project_type or "未指定",
            confirmed_tasks=tasks_text or "（无确认任务）",
            core_tensions=core_tensions or "（未识别）",
            stakeholder_system=stakeholder_system or "（未分析）",
            five_whys_analysis=five_whys or "（未分析）",
            assumption_audit=assumption_audit or "（未审计）",
            human_dimensions=human_dimensions or "（未分析）",
            ontology_parameters=ontology_params or "（未定位）",
            character_narrative=character_narrative or "（未建立）",
            confidence_score=f"{confidence_score:.2f}"
            if isinstance(confidence_score, (int, float))
            else str(confidence_score),
            uncertainty_map=self._format_uncertainty_map(uncertainty_map),
            missing_dimensions=", ".join(missing_dims) if missing_dims else "（无明显缺失）",
        )

    def _format_confirmed_tasks(self, tasks: List[Dict[str, Any]]) -> str:
        """格式化确认的任务列表"""
        if not tasks:
            return ""

        lines = []
        for i, task in enumerate(tasks, 1):
            if isinstance(task, dict):
                title = task.get("title", task.get("name", f"任务{i}"))
                desc = task.get("description", "")
                priority = task.get("priority", "")
                line = f"{i}. {title}"
                if desc:
                    line += f" — {desc}"
                if priority:
                    line += f" [优先级: {priority}]"
                lines.append(line)
            elif isinstance(task, str):
                lines.append(f"{i}. {task}")
        return "\n".join(lines)

    def _format_field(self, value: Any) -> str:
        """将任意字段格式化为 Prompt 可读文本"""
        if value is None:
            return ""
        if isinstance(value, str):
            return value[:800]  # 截断过长文本
        if isinstance(value, (list, dict)):
            try:
                text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
                return text[:1500]  # 截断过长 JSON
            except Exception:
                return str(value)[:800]
        return str(value)[:500]

    def _format_human_dimensions(self, structured_data: Dict[str, Any]) -> str:
        """格式化人性维度（合并多个子字段）"""
        parts = []
        human_dims = structured_data.get("human_dimensions")
        if human_dims:
            parts.append(self._format_field(human_dims))

        for key in [
            "emotional_landscape",
            "spiritual_aspirations",
            "psychological_safety_needs",
            "ritual_behaviors",
            "memory_anchors",
        ]:
            val = structured_data.get(key)
            if val and isinstance(val, str) and val not in ("", "待问卷补充后分析"):
                parts.append(f"**{key}**: {val[:200]}")

        return "\n".join(parts) if parts else ""

    def _format_uncertainty_map(self, uncertainty_map: Dict[str, str]) -> str:
        """格式化不确定性地图"""
        if not uncertainty_map:
            return "（无不确定性数据）"

        high = [k for k, v in uncertainty_map.items() if v == "high"]
        medium = [k for k, v in uncertainty_map.items() if v == "medium"]

        parts = []
        if high:
            parts.append(f"高不确定性: {', '.join(high)}")
        if medium:
            parts.append(f"中不确定性: {', '.join(medium)}")
        return "\n".join(parts) if parts else "（所有维度置信度良好）"

    def _extract_dimensions(self, response_text: str) -> List[Dict[str, Any]]:
        """从 LLM 响应中提取维度 JSON 数组"""
        # 尝试方式 1: 从 ```json ... ``` 代码块提取
        json_block_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", response_text)
        if json_block_match:
            try:
                result = json.loads(json_block_match.group(1))
                if isinstance(result, list):
                    return result
                if isinstance(result, dict) and "dimensions" in result:
                    return result["dimensions"]
            except json.JSONDecodeError:
                pass

        # 尝试方式 2: 直接解析整个响应
        try:
            result = json.loads(response_text)
            if isinstance(result, list):
                return result
            if isinstance(result, dict) and "dimensions" in result:
                return result["dimensions"]
        except json.JSONDecodeError:
            pass

        # 尝试方式 3: 提取第一个 [ ... ] 块
        array_match = re.search(r"\[[\s\S]*\]", response_text)
        if array_match:
            try:
                result = json.loads(array_match.group(0))
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        # 尝试方式 4: 使用项目内的通用 JSON 解析器
        try:
            from intelligent_project_analyzer.utils.json_parser import parse_json_list

            result = parse_json_list(response_text, extract_from_markdown=True, fix_quotes=True, default=[])
            if result:
                return result
        except ImportError:
            pass

        logger.warning("🎯 [v8.0] 所有 JSON 解析方式均失败")
        return []

    def _validate_dimension(self, dim: Dict[str, Any], existing_ids: set) -> bool:
        """
        验证单个维度（8 条规则）

        规则 1-6: 复用 DynamicDimensionGenerator 的基础验证
        规则 7: source 合法性
        规则 8: 校准维度 default ≠ 50
        规则 9: 标签对称性（底线维度过滤安全网）
        """
        # 规则 1: 必需字段
        required_fields = [
            "id",
            "name",
            "left_label",
            "right_label",
            "description",
            "category",
            "default_value",
            "source",
        ]
        for field in required_fields:
            if field not in dim:
                logger.warning(f"🎯 [验证] 缺少字段 '{field}': {dim.get('id', '?')}")
                return False

        # 规则 2: ID 格式
        if not re.match(r"^[a-z][a-z0-9_]{2,30}$", str(dim["id"])):
            logger.warning(f"🎯 [验证] ID 格式错误: {dim['id']}")
            return False

        # 规则 3: ID 唯一性
        if dim["id"] in existing_ids:
            logger.warning(f"🎯 [验证] ID 重复: {dim['id']}")
            return False

        # 规则 4: 类别合法性
        if dim["category"] not in self.VALID_CATEGORIES:
            logger.warning(f"🎯 [验证] 类别非法: {dim['category']}，自动修正为 'special'")
            dim["category"] = "special"  # 自动修正而非拒绝

        # 规则 5: 默认值范围
        default_value = dim.get("default_value", 50)
        if not isinstance(default_value, (int, float)):
            try:
                default_value = int(default_value)
            except (ValueError, TypeError):
                default_value = 50
        dim["default_value"] = max(0, min(100, int(default_value)))

        # 规则 6: 名称长度
        if len(str(dim.get("name", ""))) > 15:
            logger.warning(f"🎯 [验证] 名称过长: {dim['name']}")
            dim["name"] = dim["name"][:15]  # 截断而非拒绝

        # 规则 7: source 合法性
        if dim["source"] not in self.VALID_SOURCES:
            logger.warning(f"🎯 [验证] source 非法: {dim['source']}，改为 'decision'")
            dim["source"] = "decision"

        # 规则 8: 校准维度 default 不应为 50（45-55 区间视为无推断）
        if dim["source"] == "calibration" and 45 <= dim["default_value"] <= 55:
            logger.warning(f"🎯 [验证] 校准维度 '{dim['name']}' default={dim['default_value']} 在中间区，" f"改为 decision 类型")
            dim["source"] = "decision"

        # 规则 9: 标签对称性（底线维度安全网）
        for label_key in ("left_label", "right_label"):
            label = str(dim.get(label_key, ""))
            if self.NEGATIVE_LABEL_PATTERNS.search(label):
                logger.warning(f"🎯 [验证] 标签含负面词，疑似底线维度: {dim['name']} ({label})")
                return False

        # 补充可选字段默认值
        dim.setdefault("rationale", "")
        dim.setdefault("impact_hint", "")
        dim.setdefault("evidence", "")
        dim.setdefault("global_impact", False)

        return True
