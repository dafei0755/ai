"""
动态维度生成器（LLM驱动实现）
v7.106: LLM驱动的真实实现，支持覆盖度分析和智能维度生成
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

import yaml
from langchain_openai import ChatOpenAI
from loguru import logger


class DynamicDimensionGenerator:
    """
    动态维度生成器

    v7.106: LLM驱动实现，真正的智能维度生成
    - 使用LLM分析现有维度的覆盖度
    - 根据用户需求生成定制化维度
    - 7项验证规则确保质量
    """

    def __init__(self):
        """初始化生成器"""
        logger.info("🔧 DynamicDimensionGenerator 初始化（LLM模式）")

        # 加载配置
        self.config = self._load_config()

        # 初始化LLM
        model_name = os.getenv("DIMENSION_LLM_MODEL", "gpt-4o-mini")
        self.llm = ChatOpenAI(model=model_name, temperature=0.7, timeout=30)
        logger.info(f"   LLM模型: {model_name}")

    def _load_config(self) -> Dict[str, Any]:
        """加载Prompt配置"""
        config_path = Path(__file__).parent.parent / "config" / "prompts" / "dimension_generation_prompts.yaml"

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.info(f"✅ 加载Prompt配置: {config_path}")
            return config
        except Exception as e:
            logger.error(f"❌ 加载Prompt配置失败: {e}")
            # 返回默认配置
            return {
                "coverage_analysis_prompt": "分析维度覆盖度",
                "dimension_generation_prompt": "生成新维度",
                "validation_rules": {},
            }

    def analyze_coverage(
        self, user_input: str, structured_data: Dict[str, Any], existing_dimensions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        使用LLM分析现有维度的覆盖度

        Args:
            user_input: 用户原始输入
            structured_data: 结构化数据
            existing_dimensions: 现有维度列表

        Returns:
            覆盖度分析结果:
            {
                "coverage_score": 0.85,
                "should_generate": false,
                "missing_aspects": [...],
                "analysis": "..."
            }
        """
        # � v7.120: 入口立即清理 - 防止emoji通过任何路径进入下游
        user_input = self._safe_str(user_input)

        # 🔧 v7.117: 增强调试日志
        logger.info(f"🔍 [DynamicDimensionGenerator] 开始LLM覆盖度分析")
        # 🔥 v7.120: 日志输出使用_safe_str过滤emoji
        logger.info(f"   用户输入: {user_input[:100]}...")
        logger.info(f"   现有维度ID: {[d.get('id') for d in existing_dimensions]}")
        logger.info(f"📊 [DynamicDimensionGenerator] LLM分析覆盖度（现有维度数: {len(existing_dimensions)}）")

        try:
            # 构建Prompt
            confirmed_tasks = structured_data.get("confirmed_core_tasks", [])
            # 🔧 v7.116: 修复Unicode编码问题 - 处理任务列表中的字典和字符串
            if confirmed_tasks:
                task_items = []
                for task in confirmed_tasks:
                    if isinstance(task, dict):
                        task_text = str(task.get("title", task.get("name", "")))
                    else:
                        task_text = str(task)
                    # 确保文本可以安全编码
                    task_text = task_text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
                    task_items.append(f"- {task_text}")
                tasks_str = "\n".join(task_items)
            else:
                tasks_str = "无"

            # 🔧 v7.116: 修复Unicode编码问题 - 清理维度名称中的特殊字符
            existing_dims_items = []
            for dim in existing_dimensions:
                name = str(dim.get("name", "")).encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
                left = str(dim.get("left_label", "")).encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
                right = (
                    str(dim.get("right_label", "")).encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
                )
                existing_dims_items.append(f"- {name}（{left} ← → {right}）")
            existing_dims_str = "\n".join(existing_dims_items)

            # 🔧 v7.119: 使用统一的 _safe_str 方法清理所有输入
            prompt_template = self.config.get("coverage_analysis_prompt", "")
            prompt = prompt_template.format(
                user_input=self._safe_str(user_input),
                confirmed_tasks=self._safe_str(tasks_str),
                existing_dimensions=self._safe_str(existing_dims_str),
            )

            # 🔥 v7.120: 最终清理 - 确保prompt完全无emoji字符
            prompt = self._safe_str(prompt)
            # 🔥 v7.120: 再次确保没有任何emoji进入LLM调用
            safe_prompt = self._safe_str(prompt)

            # 🔧 v7.120: 调试 - 确认prompt已清理
            if any(ord(c) >= 0x10000 for c in safe_prompt):
                logger.error(f"❌ BUG: safe_prompt仍包含emoji! {[c for c in safe_prompt if ord(c) >= 0x10000]}")

            logger.debug(f"📝 Prompt长度: {len(safe_prompt)}, 前100字符: {safe_prompt[:100]}")

            # 🔥 v7.120: 构建完全清理的message对象
            message_dict = {"role": "user", "content": safe_prompt}
            # 再次确保content字段安全（防御性编程）
            message_dict["content"] = self._safe_str(message_dict["content"])

            # 调用LLM
            response = self.llm.invoke([message_dict])
            result_text = response.content.strip()

            # 提取JSON
            result = self._extract_json(result_text)

            if result:
                logger.info(f"✅ 覆盖度分析完成: {result.get('coverage_score', 0):.2f}")
                logger.info(f"   是否需要生成: {result.get('should_generate', False)}")
                return result
            else:
                logger.warning("⚠️ LLM返回格式错误，使用默认值")
                return self._default_coverage_result()

        except Exception as e:
            # ✅ v7.120: 详细错误追踪，定位ASCII编码问题根源
            import traceback

            error_details = traceback.format_exc()
            error_msg = DynamicDimensionGenerator._safe_str(str(e))
            logger.error(f"❌ LLM覆盖度分析失败: {error_msg}")
            if "ascii" in error_msg.lower():
                logger.error(f"   完整堆栈:\n{error_details}")
            return self._default_coverage_result()

    def _default_coverage_result(self) -> Dict[str, Any]:
        """降级策略：返回默认覆盖度结果"""
        return {"coverage_score": 0.95, "should_generate": False, "missing_aspects": [], "analysis": "LLM调用失败，降级为默认覆盖度"}

    def generate_dimensions(
        self, user_input: str, structured_data: Dict[str, Any], missing_aspects: List[str], target_count: int = 2
    ) -> List[Dict[str, Any]]:
        """
        使用LLM生成新维度

        Args:
            user_input: 用户原始输入
            structured_data: 结构化数据（应包含existing_dimensions）
            missing_aspects: 缺失方面列表
            target_count: 目标生成数量

        Returns:
            新维度列表
        """
        # 🔥 v7.120: 入口立即清理 - 防止emoji通过任何路径进入下游
        user_input = self._safe_str(user_input)

        logger.info(f"🤖 [DynamicDimensionGenerator] LLM生成维度（目标数量: {target_count}）")

        if target_count <= 0:
            logger.info("   目标数量为0，跳过生成")
            return []

        try:
            # 🔧 v7.116: 修复Unicode编码问题 - 构建缺失方面描述
            missing_items = []
            for aspect in missing_aspects:
                if isinstance(aspect, dict):
                    aspect_text = str(aspect.get("aspect", ""))
                else:
                    aspect_text = str(aspect)
                # 确保文本可以安全编码
                aspect_text = aspect_text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
                missing_items.append(f"- {aspect_text}")
            missing_str = "\n".join(missing_items) if missing_items else "无"

            # 获取现有维度ID列表（支持从structured_data或外部传入）
            existing_dimensions = structured_data.get("existing_dimensions", [])
            existing_ids = [dim.get("id", "") for dim in existing_dimensions]
            existing_ids_str = ", ".join(existing_ids) if existing_ids else "无"

            # 获取Few-shot示例
            few_shot = self._get_few_shot_examples()

            # 🔧 v7.119: 使用统一的 _safe_str 方法清理所有输入
            prompt_template = self.config.get("dimension_generation_prompt", "")
            prompt = prompt_template.format(
                user_input=self._safe_str(user_input),
                missing_aspects=self._safe_str(missing_str),
                existing_dimension_ids=self._safe_str(existing_ids_str),
                few_shot_examples=self._safe_str(few_shot),
            )

            # 🔥 v7.120: 最终清理 - 确保prompt完全无emoji字符
            prompt = self._safe_str(prompt)
            # 🔥 v7.120: 再次确保没有任何emoji进入LLM调用
            safe_prompt = self._safe_str(prompt)

            # 🔥 v7.120: 构建完全清理的message对象
            message_dict = {"role": "user", "content": safe_prompt}
            # 再次确保content字段安全（防御性编程）
            message_dict["content"] = self._safe_str(message_dict["content"])

            # 调用LLM
            response = self.llm.invoke([message_dict])
            result_text = response.content.strip()

            # 提取JSON数组
            new_dimensions = self._extract_json_array(result_text)

            if new_dimensions:
                # 验证和过滤
                validated_dims = []
                for dim in new_dimensions[:target_count]:  # 限制数量
                    if self._validate_dimension(dim, existing_ids):
                        # 添加source标记
                        dim["source"] = "llm_generated"
                        validated_dims.append(dim)

                logger.info(f"✅ LLM生成 {len(new_dimensions)} 个维度，验证通过 {len(validated_dims)} 个")
                for dim in validated_dims:
                    logger.info(f"   + {dim['name']}: {dim['left_label']} ← → {dim['right_label']}")

                return validated_dims
            else:
                logger.warning("⚠️ LLM未生成有效维度")
                return []

        except Exception as e:
            # ✅ v7.118: 使用安全字符串避免emoji编码错误
            error_msg = DynamicDimensionGenerator._safe_str(str(e))
            logger.error(f"❌ LLM维度生成失败: {error_msg}")
            return []

    @staticmethod
    def _safe_str(s: Any) -> str:
        """
        🔧 v7.119: 移除可能导致编码问题的字符（如emoji）

        改进点:
        - 接受任意类型输入（Any）
        - 先转为字符串
        - 只保留 BMP 范围内的字符（U+0000 到 U+FFFF）
        - 排除 emoji 等补充平面字符（U+10000 及以上）
        """
        if not s:
            return ""
        # 确保转为字符串
        text = str(s)
        # 只保留 BMP 范围内的字符
        return "".join(c for c in text if ord(c) < 0x10000)

    def _get_few_shot_examples(self) -> str:
        """获取Few-shot示例"""
        examples_dict = self.config.get("few_shot_examples", {})

        examples_text = ""
        for category, examples in examples_dict.items():
            if isinstance(examples, list):
                for example in examples[:1]:  # 每个类别取1个示例
                    if "user_input" in example and "generated_dimensions" in example:
                        examples_text += f"\n### {category}示例\n"
                        # 🔧 v7.117: 清理 emoji 字符
                        examples_text += f"需求: {self._safe_str(example['user_input'])}\n"
                        examples_text += "生成维度:\n"
                        dims_json = json.dumps(example["generated_dimensions"], ensure_ascii=False, indent=2)
                        examples_text += self._safe_str(dims_json)
                        examples_text += "\n"

        return examples_text

    def _validate_dimension(self, dimension: Dict[str, Any], existing_ids: List[str]) -> bool:
        """
        验证维度（7项规则）

        1. 必需字段
        2. ID格式
        3. ID唯一性
        4. 类别合法性
        5. 默认值范围
        6. 字符串长度
        7. 语义去重（可选）
        """
        rules = self.config.get("validation_rules", {})

        # 规则1: 必需字段
        required_fields = ["id", "name", "left_label", "right_label", "description", "category", "default_value"]
        for field in required_fields:
            if field not in dimension:
                logger.warning(f"❌ 维度缺少必需字段: {field}")
                return False

        # 规则2: ID格式
        id_pattern = rules.get("id_pattern", r"^[a-z][a-z0-9_]{2,30}$")
        if not re.match(id_pattern, dimension["id"]):
            logger.warning(f"❌ 维度ID格式错误: {dimension['id']}")
            return False

        # 规则3: ID唯一性
        if dimension["id"] in existing_ids:
            logger.warning(f"❌ 维度ID重复: {dimension['id']}")
            return False

        # 规则4: 类别合法性
        valid_categories = rules.get("valid_categories", [])
        if valid_categories and dimension["category"] not in valid_categories:
            logger.warning(f"❌ 维度类别非法: {dimension['category']}")
            return False

        # 规则5: 默认值范围
        default_range = rules.get("default_value_range", [0, 100])
        default_value = dimension.get("default_value", 50)
        if not (default_range[0] <= default_value <= default_range[1]):
            logger.warning(f"❌ 默认值超出范围: {default_value}")
            return False

        # 规则6: 字符串长度
        name_max = rules.get("name_max_length", 10)
        if len(dimension["name"]) > name_max:
            logger.warning(f"❌ 名称过长: {dimension['name']}")
            return False

        # 规则7: 语义去重（暂不实现，需要embedding）
        # TODO: 使用OpenAI Embedding API检查语义相似度

        return True

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        🆕 P1修复: 使用统一JSON解析器
        从文本中提取JSON对象
        """
        from ..utils.json_parser import parse_json_safe

        return parse_json_safe(text, extract_from_markdown=True, fix_quotes=True, default={})

    def _extract_json_array(self, text: str) -> List[Dict[str, Any]]:
        """
        🆕 P1修复: 使用统一JSON解析器
        从文本中提取JSON数组
        """
        from ..utils.json_parser import parse_json_list

        return parse_json_list(text, extract_from_markdown=True, fix_quotes=True, default=[])
