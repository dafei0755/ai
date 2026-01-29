"""
LLM维度推荐器 - 使用LLM深度理解用户需求并推荐雷达图维度

v7.138 Phase 2: LLM需求理解层
基于用户输入、确认的任务、问卷答案，通过LLM智能推荐维度和默认值
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from .llm_factory import get_llm


class LLMDimensionRecommender:
    """
    LLM维度推荐器

    核心功能：
    1. 融合user_input、confirmed_tasks、gap_filling_answers三层信息
    2. 调用LLM深度理解用户需求
    3. 返回推荐维度ID + 默认值 + 推理原因
    4. 支持降级策略（LLM失败时回退到规则引擎）
    """

    _instance = None
    _prompt_config: Optional[Dict[str, Any]] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if LLMDimensionRecommender._prompt_config is None:
            self._load_prompt_config()
        self.enabled = os.getenv("ENABLE_LLM_DIMENSION_RECOMMENDER", "false").lower() == "true"
        logger.info(f"🤖 [v7.138] LLM维度推荐器初始化: enabled={self.enabled}")

    def _load_prompt_config(self) -> None:
        """加载Prompt配置文件"""
        config_path = Path(__file__).parent.parent / "config" / "prompts" / "llm_dimension_prompt.yaml"

        if not config_path.exists():
            logger.warning(f"⚠️ LLM维度Prompt配置文件不存在: {config_path}，功能降级")
            LLMDimensionRecommender._prompt_config = {}
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                LLMDimensionRecommender._prompt_config = yaml.safe_load(f)
            logger.info("✅ [v7.138] LLM维度Prompt配置加载成功")
        except Exception as e:
            logger.error(f"❌ LLM维度Prompt配置加载失败: {e}")
            LLMDimensionRecommender._prompt_config = {}

    @property
    def config(self) -> Dict[str, Any]:
        """获取配置"""
        return LLMDimensionRecommender._prompt_config or {}

    def is_enabled(self) -> bool:
        """检查LLM推荐器是否启用"""
        return self.enabled

    def recommend_dimensions(
        self,
        project_type: str,
        user_input: str,
        all_dimensions: Dict[str, Dict[str, Any]],
        required_dimensions: List[str],
        confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
        gap_filling_answers: Optional[Dict[str, str]] = None,
        min_dimensions: int = 9,
        max_dimensions: int = 12,
    ) -> Optional[Dict[str, Any]]:
        """
        使用LLM推荐维度

        Args:
            project_type: 项目类型
            user_input: 用户原始输入
            all_dimensions: 所有可用维度配置
            required_dimensions: 必选维度列表（规则引擎返回）
            confirmed_tasks: Step1确认的任务列表
            gap_filling_answers: Step2问卷答案
            min_dimensions: 最小维度数量
            max_dimensions: 最大维度数量

        Returns:
            {
                "recommended_dimensions": [
                    {
                        "dimension_id": "cultural_axis",
                        "default_value": 25,
                        "reason": "用户偏好新中式风格，倾向东方美学"
                    },
                    ...
                ],
                "reasoning": "综合分析...",
                "confidence": 0.95
            }
            如果LLM失败，返回None
        """
        if not self.enabled:
            logger.debug("ℹ️ LLM维度推荐器未启用，跳过")
            return None

        if not self.config:
            logger.warning("⚠️ LLM Prompt配置缺失，跳过推荐")
            return None

        try:
            logger.info("🤖 [v7.138] 开始LLM维度推荐")

            # 构建Prompt
            system_prompt = self._build_system_prompt(all_dimensions)
            user_prompt = self._build_user_prompt(
                project_type=project_type,
                user_input=user_input,
                required_dimensions=required_dimensions,
                confirmed_tasks=confirmed_tasks,
                gap_filling_answers=gap_filling_answers,
                min_dimensions=min_dimensions,
                max_dimensions=max_dimensions,
            )

            # 调用LLM
            llm = get_llm()
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

            logger.debug(f"📤 发送请求到LLM (system: {len(system_prompt)}字, user: {len(user_prompt)}字)")
            response = llm.invoke(messages)
            response_text = response.content

            logger.debug(f"📥 收到LLM响应: {len(response_text)}字")

            # 解析JSON
            result = self._parse_llm_response(response_text, all_dimensions, required_dimensions)

            if result:
                confidence = result.get("confidence", "N/A")
                logger.info(f"✅ [v7.138] LLM推荐完成: {len(result['recommended_dimensions'])} 个维度, 置信度={confidence}")
                return result
            else:
                logger.warning("⚠️ LLM响应解析失败，降级到规则引擎")
                return None

        except Exception as e:
            logger.error(f"❌ LLM维度推荐失败: {e}，降级到规则引擎")
            return None

    def _build_system_prompt(self, all_dimensions: Dict[str, Dict[str, Any]]) -> str:
        """构建系统提示词"""
        system_template = self.config.get("system_prompt", "")

        # 构建维度库说明
        dimensions_desc = self._build_dimensions_description(all_dimensions)

        # 替换占位符
        system_prompt = system_template.replace("{dimensions_library}", dimensions_desc)

        return system_prompt

    def _build_dimensions_description(self, all_dimensions: Dict[str, Dict[str, Any]]) -> str:
        """构建维度库的文字说明"""
        lines = []
        lines.append("## 可用维度库（35个维度）\n")

        # 按类别分组
        categories = {
            "aesthetic": "美学维度",
            "functional": "功能维度",
            "technology": "科技维度",
            "resource": "资源维度",
            "experience": "体验维度",
        }

        for category_id, category_name in categories.items():
            lines.append(f"### {category_name}\n")

            # 找到该类别的维度
            dims_in_category = [
                (dim_id, dim_cfg)
                for dim_id, dim_cfg in all_dimensions.items()
                if dim_cfg.get("category") == category_id
            ]

            for dim_id, dim_cfg in dims_in_category:
                name = dim_cfg.get("name", dim_id)
                left = dim_cfg.get("left_label", "低")
                right = dim_cfg.get("right_label", "高")
                desc = dim_cfg.get("description", "")
                keywords = ", ".join(dim_cfg.get("keywords", []))

                lines.append(f"- **{dim_id}**（{name}）: {left} ←→ {right}")
                lines.append(f"  - 说明: {desc}")
                lines.append(f"  - 关键词: {keywords}\n")

        return "\n".join(lines)

    def _build_user_prompt(
        self,
        project_type: str,
        user_input: str,
        required_dimensions: List[str],
        confirmed_tasks: Optional[List[Dict[str, Any]]],
        gap_filling_answers: Optional[Dict[str, str]],
        min_dimensions: int,
        max_dimensions: int,
    ) -> str:
        """构建用户提示词"""
        user_template = self.config.get("user_prompt", "")

        # 构建任务摘要
        tasks_summary = self._build_tasks_summary(confirmed_tasks)

        # 构建答案摘要
        answers_summary = self._build_answers_summary(gap_filling_answers)

        # 替换占位符
        user_prompt = (
            user_template.replace("{project_type}", project_type)
            .replace("{user_input}", user_input)
            .replace("{required_dimensions}", ", ".join(required_dimensions))
            .replace("{confirmed_tasks}", tasks_summary)
            .replace("{gap_filling_answers}", answers_summary)
            .replace("{min_dimensions}", str(min_dimensions))
            .replace("{max_dimensions}", str(max_dimensions))
        )

        return user_prompt

    def _build_tasks_summary(self, confirmed_tasks: Optional[List[Dict[str, Any]]]) -> str:
        """构建任务列表摘要"""
        if not confirmed_tasks:
            return "（无）"

        lines = []
        for i, task in enumerate(confirmed_tasks, 1):
            # 兼容title和name字段
            title = task.get("title") or task.get("name", "")
            desc = task.get("description", "")
            priority = task.get("priority", "medium")
            lines.append(f"{i}. {title}（{priority}）: {desc}")

        return "\n".join(lines)

    def _build_answers_summary(self, gap_filling_answers: Optional[Dict[str, str]]) -> str:
        """构建问卷答案摘要"""
        if not gap_filling_answers:
            return "（无）"

        lines = []
        for question, answer in gap_filling_answers.items():
            lines.append(f"- Q: {question}")
            lines.append(f"  A: {answer}")

        return "\n".join(lines)

    def _parse_llm_response(
        self,
        response_text: str,
        all_dimensions: Dict[str, Dict[str, Any]],
        required_dimensions: List[str],
    ) -> Optional[Dict[str, Any]]:
        """
        解析LLM返回的JSON

        返回格式：
        {
            "recommended_dimensions": [
                {
                    "dimension_id": "cultural_axis",
                    "default_value": 25,
                    "reason": "..."
                }
            ],
            "reasoning": "综合分析...",
            "confidence": 0.95
        }
        """
        try:
            # 提取JSON（可能包含Markdown代码块）
            json_text = self._extract_json(response_text)

            if not json_text:
                logger.warning("⚠️ 无法从LLM响应中提取JSON")
                return None

            # 解析JSON
            data = json.loads(json_text)

            # 验证必选维度
            recommended_ids = [dim["dimension_id"] for dim in data.get("recommended_dimensions", [])]

            missing_required = [rid for rid in required_dimensions if rid not in recommended_ids]

            if missing_required:
                logger.warning(f"⚠️ LLM遗漏了必选维度: {missing_required}，自动补充")

                # 自动补充必选维度
                for dim_id in missing_required:
                    dim_cfg = all_dimensions.get(dim_id, {})
                    data["recommended_dimensions"].append(
                        {
                            "dimension_id": dim_id,
                            "default_value": dim_cfg.get("default_value", 50),
                            "reason": "规则引擎必选维度（自动补充）",
                        }
                    )

            # 验证维度ID合法性
            valid_dimensions = []
            for dim_rec in data.get("recommended_dimensions", []):
                dim_id = dim_rec.get("dimension_id")
                if dim_id in all_dimensions:
                    # 限制default_value在0-100之间
                    default_value = max(0, min(100, dim_rec.get("default_value", 50)))
                    valid_dimensions.append(
                        {
                            "dimension_id": dim_id,
                            "default_value": default_value,
                            "reason": dim_rec.get("reason", ""),
                            "recommended_by_llm": True,  # 标记为LLM推荐
                        }
                    )
                else:
                    logger.warning(f"⚠️ LLM推荐了不存在的维度: {dim_id}，忽略")

            if not valid_dimensions:
                logger.warning("⚠️ 没有有效的维度推荐")
                return None

            return {
                "recommended_dimensions": valid_dimensions,
                "reasoning": data.get("reasoning", ""),
                "confidence": data.get("confidence", 0.8),
            }

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ 解析LLM响应失败: {e}")
            return None

    def _extract_json(self, text: str) -> Optional[str]:
        """从文本中提取JSON（支持Markdown代码块）"""
        # 尝试直接解析
        text = text.strip()

        # 移除Markdown代码块
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()

        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()

        # 查找JSON对象
        if "{" in text and "}" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            return text[start:end]

        return text
