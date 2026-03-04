"""
核心任务拆解服务

v7.80.1: 将用户模糊输入拆解为结构化的可执行任务列表
v7.110.0: 智能化任务数量评估，根据输入复杂度动态调整（3-12个弹性范围）
用于 Step 1: 任务梳理
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import yaml
from loguru import logger


class TaskComplexityAnalyzer:
    """
    任务复杂度分析器 - v7.110.0 / v7.503增强

    根据用户输入的信息密度和复杂程度，智能评估建议的任务数量。
    v7.503: 扩展任务上限到20个，支持超大型项目（城市规划、综合体设计等）。
    """

    # 配置参数（v7.503优化：扩展任务范围5-30，复杂度与面积无关）
    MIN_TASKS = 5  # 最少任务数（简单需求）
    MAX_TASKS = 30  # 最多任务数（超大型项目，v7.503提升到30）
    BASE_TASKS = 8  # 基准任务数

    @classmethod
    def analyze(cls, user_input: str, structured_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """
        分析用户输入复杂度，返回建议的任务数量范围

        Args:
            user_input: 用户原始输入
            structured_data: 结构化数据（可选）

        Returns:
            {
                "recommended_min": int,  # 建议最少任务数
                "recommended_max": int,  # 建议最多任务数
                "complexity_score": float,  # 复杂度得分（0-1）
                "reasoning": str  # 判断依据
            }
        """
        complexity_score = 0.0
        reasoning_parts = []

        # 1. 输入长度评分（基础维度）
        input_length = len(user_input)
        if input_length < 50:
            length_score = 0.2
            reasoning_parts.append("输入较简短")
        elif input_length < 150:
            length_score = 0.4
            reasoning_parts.append("输入中等长度")
        elif input_length < 300:
            length_score = 0.6
            reasoning_parts.append("输入较详细")
        else:
            length_score = 0.8
            reasoning_parts.append("输入非常详细")
        complexity_score += length_score * 0.15

        # 2. 信息维度数量（关键维度）- v7.503: 降低面积权重
        dimension_count = 0
        dimensions = {
            "项目类型": [r"别墅", r"住宅", r"办公", r"商业", r"民宿", r"酒店", r"学校", r"医院"],  # 仅识别类型，不看面积
            "预算约束": [r"\d+万", r"预算", r"资金", r"成本", r"有限"],
            "对标案例": [r"对标", r"参考", r"案例", r"标杆", r"像.*一样"],
            "文化要素": [r"文化", r"传统", r"在地", r"历史", r"特色", r"渔村", r"老街"],
            "客群分析": [r"\d+岁", r"客群", r"用户", r"访客", r"居民", r"女性", r"男性", r"人群"],
            "核心张力": [r'"[^"]+".*与.*"[^"]+"', r"vs", r"对立", r"矛盾", r"平衡"],
            "品牌主题": [r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*", r"为主题", r"品牌"],
            "设计风格": [r"风格", r"杂志级", r"高级感", r"美学", r"氛围"],
            "功能需求": [r"功能", r"需求", r"使用", r"场景", r"动线"],
            "时间约束": [r"\d+个月", r"\d+年", r"工期", r"交付"],
            "地理位置": [r"上海", r"北京", r"深圳", r"蛇口", r"弄堂", r"老城区"],
            "特殊场景": [r"老房翻新", r"旧改", r"菜市场", r"历史建筑", r"文保"],
            "多业态融合": [r"[^，。]{2,}\+[^，。]{2,}\+", r"综合体", r"复合", r"一体化"],  # 识别复杂业态
            "多阶段工程": [r"分期", r"一期", r"二期", r"首期", r"阶段"],  # 识别项目规模
        }

        for _dimension_name, patterns in dimensions.items():
            if any(re.search(pattern, user_input, re.IGNORECASE) for pattern in patterns):
                dimension_count += 1

        dimension_score = min(dimension_count / 10, 1.0)  # 10个维度为满分（增加维度数）
        complexity_score += dimension_score * 0.40  # 提高维度权重（从0.35→0.40）
        reasoning_parts.append(f"包含{dimension_count}个信息维度")

        # 3. 结构化数据深度（增强维度）
        structured_score = 0.0
        if structured_data:
            # 检查关键字段
            key_fields = [
                "design_challenge",
                "character_narrative",
                "physical_context",
                "analysis_layers",
                "project_type",
                "core_goals",
            ]
            filled_fields = sum(1 for field in key_fields if structured_data.get(field))
            structured_score = filled_fields / len(key_fields)
            reasoning_parts.append(f"结构化数据包含{filled_fields}个关键字段")
        complexity_score += structured_score * 0.25

        # 4. 特殊场景识别（可能需要更多任务）
        special_scenes = {
            "诗意表达": [r"[如似若像].*[般样]", r"意象", r"隐喻", r"诗意"],
            "多元对立": [r'"[^"]+".*"[^"]+".*"[^"]+"', r"兼顾.*与.*与"],  # 3个以上对立概念
            "跨界融合": [r"融合", r"结合", r"跨界", r"混搭"],
            "文化深度": [r"文化.*文化", r"传统.*现代", r"历史.*未来"],
        }
        special_count = 0
        for scene_name, patterns in special_scenes.items():
            if any(re.search(pattern, user_input, re.IGNORECASE) for pattern in patterns):
                special_count += 1
                reasoning_parts.append(f"检测到{scene_name}")

        special_score = min(special_count / 3, 1.0)
        complexity_score += special_score * 0.15

        # 5. 句子数量（反映思考深度）
        sentence_count = len(re.split(r"[。！？\n]", user_input))
        if sentence_count >= 5:
            sentence_score = 0.1
            reasoning_parts.append(f"包含{sentence_count}个句子/段落")
        else:
            sentence_score = 0.05
        complexity_score += sentence_score

        # 6. 具体数字的出现（反映精确度）
        number_matches = re.findall(r"\d+", user_input)
        if len(number_matches) >= 3:
            complexity_score += 0.1
            reasoning_parts.append("包含多个具体数据")

        # 计算建议任务数量范围（v7.503优化：新映射关系）
        # 复杂度 0-0.25 -> 5-8个任务（简单需求）
        # 复杂度 0.25-0.5 -> 9-15个任务（中等需求）
        # 复杂度 0.5-0.75 -> 15-20个任务（复杂需求）
        # 复杂度 0.75-1.0 -> 20-30个任务（超大型项目）

        if complexity_score < 0.25:
            recommended_min = 5
            recommended_max = 8
        elif complexity_score < 0.5:
            recommended_min = 9
            recommended_max = 15
        elif complexity_score < 0.75:
            recommended_min = 15
            recommended_max = 20
        else:
            recommended_min = 20
            recommended_max = cls.MAX_TASKS  # 30

        reasoning = "; ".join(reasoning_parts)

        logger.info(f" [TaskComplexityAnalyzer] 复杂度={complexity_score:.2f}, 建议任务数={recommended_min}-{recommended_max}")

        return {
            "recommended_min": recommended_min,
            "recommended_max": recommended_max,
            "complexity_score": complexity_score,
            "reasoning": reasoning,
        }


class CoreTaskDecomposer:
    """
    核心任务拆解器

    使用 LLM 将用户输入拆解为精准的、可执行的任务列表。
    """

    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self._load_config()

    def _load_config(self) -> None:
        """加载配置文件"""
        config_path = Path(__file__).parent.parent / "config" / "prompts" / "core_task_decomposer.yaml"
        try:
            with open(config_path, encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
            logger.info(f" [CoreTaskDecomposer] 配置加载成功: {config_path}")
        except Exception as e:
            logger.warning(f"️ [CoreTaskDecomposer] 配置加载失败: {e}")
            self._config = {}

    @property
    def config(self) -> Dict[str, Any]:
        """获取配置"""
        return self._config or {}

    def build_prompt(
        self,
        user_input: str,
        structured_data: Dict[str, Any] | None = None,
        task_count_range: tuple | None = None,
    ) -> str:
        """
        构建 LLM 调用的 prompt（v7.110.0 支持动态任务数量）

        Args:
            user_input: 用户原始输入
            structured_data: 需求分析阶段产出的结构化数据（可选）
            task_count_range: 建议的任务数量范围 (min, max)，如 (3, 5) 或 (8, 12)

        Returns:
            完整的 prompt 字符串
        """
        # 构建结构化数据摘要
        structured_summary = ""
        if structured_data:
            summary_parts = []

            # 提取关键字段
            project_task = structured_data.get("project_task", "")
            if project_task:
                summary_parts.append(f"项目任务: {project_task}")

            character_narrative = structured_data.get("character_narrative", "")
            if character_narrative:
                summary_parts.append(f"人物叙事: {character_narrative}")

            physical_context = structured_data.get("physical_context", "")
            if physical_context:
                summary_parts.append(f"物理场景: {physical_context}")

            project_type = structured_data.get("project_type", "")
            if project_type:
                summary_parts.append(f"项目类型: {project_type}")

            # L1-L5 分析层信息
            analysis_layers = structured_data.get("analysis_layers", {})
            if analysis_layers:
                l3_tension = analysis_layers.get("L3_core_tension", "")
                if l3_tension:
                    summary_parts.append(f"核心张力: {l3_tension}")

            structured_summary = "\n".join(summary_parts) if summary_parts else "暂无补充信息"

        # 获取 prompt 模板
        system_prompt = self.config.get("system_prompt", "")
        user_template = self.config.get("user_prompt_template", "")

        #  v7.118: 修复 KeyError - 使用 task_count_range 参数
        task_min = task_count_range[0] if task_count_range else 5
        task_max = task_count_range[1] if task_count_range else 7

        # 填充用户 prompt（包含任务数量占位符）
        user_prompt = user_template.format(
            user_input=user_input,
            structured_data_summary=structured_summary,
            task_count_min=task_min,
            task_count_max=task_max,
        )

        return f"{system_prompt}\n\n{user_prompt}"

    def parse_response(self, response: str) -> List[Dict[str, Any]]:
        """
        解析 LLM 响应，提取任务列表

        Args:
            response: LLM 返回的原始响应

        Returns:
            任务列表，每个任务包含 id, title, description, source_keywords, task_type, priority
        """
        try:
            #  P1: 增强 JSON 提取能力 - 添加 debug 日志
            logger.debug(f"[CoreTaskDecomposer] LLM 原始响应 (前500字符): {response[:500]}")

            response_text = response.strip()

            # 策略 1: 移除 markdown 代码块标记
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            # 策略 2: 如果还不是 JSON，尝试提取 { } 之间的内容
            if not response_text.startswith("{"):
                # 查找第一个 {
                start_idx = response_text.find("{")
                if start_idx != -1:
                    # 查找匹配的 }（平衡括号）
                    brace_count = 0
                    end_idx = -1
                    for i in range(start_idx, len(response_text)):
                        if response_text[i] == "{":
                            brace_count += 1
                        elif response_text[i] == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break

                    if end_idx != -1:
                        response_text = response_text[start_idx:end_idx]
                        logger.info(f" [CoreTaskDecomposer] 使用括号平衡提取 JSON (长度: {len(response_text)})")

            # 策略 3: 尝试移除 JSON 中的注释（// 或 /* */）
            import re

            response_text = re.sub(r"//.*?$", "", response_text, flags=re.MULTILINE)  # 移除单行注释
            response_text = re.sub(r"/\*.*?\*/", "", response_text, flags=re.DOTALL)  # 移除多行注释

            # 解析 JSON
            data = json.loads(response_text)

            # 提取任务列表
            tasks = data.get("tasks", [])

            # 如果 tasks 为空，尝试从其他可能的字段提取
            if not tasks:
                # 可能是直接返回了任务数组
                if isinstance(data, list):
                    tasks = data
                # 或者任务在其他字段中
                elif "task_list" in data:
                    tasks = data["task_list"]
                elif "core_tasks" in data:
                    tasks = data["core_tasks"]

            # 验证和规范化任务
            validated_tasks = []
            for i, task in enumerate(tasks):
                validated_task = {
                    "id": task.get("id", f"task_{i + 1}"),
                    "title": task.get("title", "未命名任务"),
                    "description": task.get("description", ""),
                    "source_keywords": task.get("source_keywords", []),
                    "task_type": task.get("task_type", "research"),
                    "priority": task.get("priority", "medium"),
                    #  v7.106: 添加依赖和执行顺序
                    "dependencies": task.get("dependencies", []),
                    "execution_order": task.get("execution_order", i + 1),
                    #  v7.109+: 添加搜索和概念图配置
                    "support_search": task.get("support_search", False),
                    "needs_concept_image": task.get("needs_concept_image", False),
                    "concept_image_count": task.get("concept_image_count", 1 if task.get("needs_concept_image") else 0),
                }
                validated_tasks.append(validated_task)

                #  v7.119: 添加概念图相关日志
                if validated_task["needs_concept_image"]:
                    logger.info(f" [任务 {validated_task['id']}] 需要生成概念图")
                    logger.info(f"   数量: {validated_task['concept_image_count']} 张")
                    logger.info(f"   任务标题: {validated_task['title']}")
                if validated_task["support_search"]:
                    logger.debug(f" [任务 {validated_task['id']}] 支持搜索功能")

            logger.info(f" [CoreTaskDecomposer] 成功解析 {len(validated_tasks)} 个任务")

            # 统计概念图相关任务
            tasks_with_images = [t for t in validated_tasks if t.get("needs_concept_image")]
            total_image_count = sum(t.get("concept_image_count", 0) for t in validated_tasks)
            if tasks_with_images:
                logger.info(f" [概念图统计] {len(tasks_with_images)} 个任务需要概念图，共 {total_image_count} 张")
                for t in tasks_with_images:
                    logger.debug(f"  • {t['title']}: {t.get('concept_image_count', 0)} 张")

            return validated_tasks

        except json.JSONDecodeError as e:
            logger.error(f" [CoreTaskDecomposer] JSON 解析失败: {e}")
            logger.debug(f"[CoreTaskDecomposer] 解析失败的文本: {response_text[:200]}")
            return self._fallback_decompose(response)
        except Exception as e:
            logger.error(f" [CoreTaskDecomposer] 响应解析异常: {e}")
            return []

    def _fallback_decompose(self, text: str) -> List[Dict[str, Any]]:
        """
        回退策略：当 LLM 响应格式不正确时，使用简单的规则提取

        Args:
            text: 原始文本

        Returns:
            简化的任务列表
        """
        logger.warning("️ [CoreTaskDecomposer] 使用回退策略提取任务")

        # 尝试从文本中提取编号列表
        lines = text.split("\n")
        tasks = []

        for _i, line in enumerate(lines):
            line = line.strip()
            # 匹配 "1." "1、" "1)" "- " 等格式
            if line and (
                (line[0].isdigit() and len(line) > 2 and line[1] in ".、)")
                or line.startswith("- ")
                or line.startswith("• ")
            ):
                # 提取任务内容
                content = line.lstrip("0123456789.、)- •").strip()
                if content and len(content) > 5:
                    #  v7.109+: 简单规则判断是否需要搜索和概念图
                    is_research_task = any(kw in content for kw in ["研究", "调研", "分析", "对标", "案例"])
                    is_design_task = any(kw in content for kw in ["设计", "方案", "规划", "框架"])

                    tasks.append(
                        {
                            "id": f"task_{len(tasks) + 1}",
                            "title": content[:50] if len(content) > 50 else content,
                            "description": content,
                            "source_keywords": [],
                            "task_type": "research" if is_research_task else "design" if is_design_task else "analysis",
                            "priority": "medium",
                            "dependencies": [],
                            "execution_order": len(tasks) + 1,
                            #  v7.109+: 默认配置
                            "support_search": is_research_task,  # 研究类任务默认需要搜索
                            "needs_concept_image": is_design_task,  # 设计类任务默认需要概念图
                            "concept_image_count": 1 if is_design_task else 0,
                        }
                    )

        # 限制任务数量
        return tasks[:7] if tasks else []

    async def _infer_task_metadata_async(
        self, tasks: List[Dict[str, Any]], user_input: str = "", structured_data: Dict[str, Any] | None = None
    ) -> None:
        """
        异步推断任务元数据（动机类型、推理依据等）

        v7.106: 为每个任务添加：
        - motivation_type: 动机类型ID（如'cultural'）
        - motivation_label: 动机类型中文标签（如'文化认同'）
        - ai_reasoning: LLM推理依据
        - confidence_score: 置信度分数

        Args:
            tasks: 任务列表
            user_input: 用户原始输入
            structured_data: 需求分析阶段产出的结构化数据
        """
        if not tasks:
            return

        from ..services.motivation_engine import get_motivation_engine

        engine = get_motivation_engine()
        logger.info(f" [v7.106] 使用动机识别引擎处理 {len(tasks)} 个任务")

        #  v7.122: 并行执行所有推断任务（优化性能）
        import asyncio
        import time

        start_time = time.time()

        # 创建所有推断协程
        async def infer_single_task(task):
            """单个任务的推断包装函数"""
            try:
                # 执行异步推断
                result = await engine.infer(task=task, user_input=user_input, structured_data=structured_data)

                # 返回成功结果
                return {"task": task, "success": True, "result": result}

            except Exception as e:
                # 返回失败结果
                return {"task": task, "success": False, "error": e}

        # 并行执行所有任务
        inference_coroutines = [infer_single_task(task) for task in tasks]
        results = await asyncio.gather(*inference_coroutines)

        # 处理结果并更新任务
        for result_data in results:
            task = result_data["task"]

            if result_data["success"]:
                result = result_data["result"]
                task["motivation_type"] = result.primary
                task["motivation_label"] = result.primary_label
                task["ai_reasoning"] = result.reasoning
                task["confidence_score"] = result.confidence
                logger.info(f"    {task['title'][:30]}: {result.primary_label} ({result.confidence:.2f})")
            else:
                error = result_data["error"]
                logger.warning(f"️ 任务 '{task.get('title', 'unknown')}' 动机推断失败: {error}")
                # 降级到默认
                task["motivation_type"] = "mixed"
                task["motivation_label"] = "综合"
                task["ai_reasoning"] = "推断失败，使用默认类型"
                task["confidence_score"] = 0.3

        elapsed_time = time.time() - start_time
        logger.info(f" [并行优化] {len(tasks)} 个任务推断完成，耗时 {elapsed_time:.2f}s")


async def decompose_core_tasks(
    user_input: str, structured_data: Dict[str, Any] | None = None, llm: Any | None = None
) -> List[Dict[str, Any]]:
    """
    异步执行核心任务拆解（v7.110.0 智能化版本）

    Args:
        user_input: 用户原始输入
        structured_data: 需求分析阶段产出的结构化数据（可选）
        llm: LLM 实例（可选，如果不提供则使用默认 LLM）

    Returns:
        任务列表（3-12个，根据输入复杂度动态决定）
    """
    decomposer = CoreTaskDecomposer()

    #  v7.110.0: 智能分析输入复杂度，动态决定任务数量
    complexity_analysis = TaskComplexityAnalyzer.analyze(user_input, structured_data)
    recommended_min = complexity_analysis["recommended_min"]
    recommended_max = complexity_analysis["recommended_max"]
    complexity_score = complexity_analysis["complexity_score"]

    logger.info(f" [智能任务数量] 推荐范围: {recommended_min}-{recommended_max}个 (复杂度={complexity_score:.2f})")
    logger.info(f"   分析依据: {complexity_analysis['reasoning']}")

    # 构建 prompt（传入智能计算的任务数量）
    decomposer.build_prompt(user_input, structured_data, task_count_range=(recommended_min, recommended_max))

    # 如果没有提供 LLM，使用默认
    if llm is None:
        from ..services.llm_factory import LLMFactory

        llm = LLMFactory.create_llm()

    try:
        # 调用 LLM
        from langchain_core.messages import HumanMessage, SystemMessage

        system_prompt = decomposer.config.get("system_prompt", "")
        user_template = decomposer.config.get("user_prompt_template", "")

        # 构建结构化数据摘要
        structured_summary = ""
        if structured_data:
            summary_parts = []
            for key in ["project_task", "character_narrative", "physical_context", "project_type"]:
                if structured_data.get(key):
                    summary_parts.append(f"{key}: {structured_data[key]}")
            structured_summary = "\n".join(summary_parts) if summary_parts else "暂无"

        #  v7.117: 直接使用占位符传入任务数量（不再使用正则替换）
        user_prompt = user_template.format(
            user_input=user_input,
            structured_data_summary=structured_summary,
            task_count_min=recommended_min,
            task_count_max=recommended_max,
        )

        #  v7.117: 增强调试日志
        logger.info(f" [智能任务数量] 输入长度={len(user_input)}字符")
        logger.info(f" [智能任务数量] 复杂度分析: {complexity_analysis['reasoning']}")
        logger.info(f" [Prompt] 任务数量要求: {recommended_min}-{recommended_max}个")

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        response = await llm.ainvoke(messages)
        response_text = response.content if hasattr(response, "content") else str(response)

        # 解析响应
        tasks = decomposer.parse_response(response_text)

        if not tasks:
            # 如果解析失败，使用简单回退
            logger.warning("️ LLM 任务拆解为空，使用回退策略")
            tasks = _simple_fallback_decompose(user_input, structured_data, complexity_analysis)
        else:
            #  v7.110.0: 智能截断 - 不超过推荐最大值
            if len(tasks) > recommended_max:
                logger.warning(f"️ LLM生成了{len(tasks)}个任务，超过推荐上限{recommended_max}，智能截断")
                # 优先保留 high priority 的任务
                high_priority_tasks = [t for t in tasks if t.get("priority") == "high"]
                other_tasks = [t for t in tasks if t.get("priority") != "high"]
                tasks = (high_priority_tasks + other_tasks)[:recommended_max]

            # 如果少于推荐最小值，记录警告但不强制补齐（让LLM判断更灵活）
            if len(tasks) < recommended_min:
                logger.info(f"ℹ️ LLM生成了{len(tasks)}个任务，少于推荐最小值{recommended_min}（可能是简单需求）")

        #  v7.106: 使用动机识别引擎为任务添加motivation_label字段
        if tasks:
            await decomposer._infer_task_metadata_async(tasks, user_input, structured_data)

        logger.info(f" [任务拆解完成] 最终生成{len(tasks)}个任务")
        return tasks

    except Exception as e:
        logger.error(f" [decompose_core_tasks] LLM 调用失败: {e}")
        # 回退到简单拆解
        return _simple_fallback_decompose(user_input, structured_data, complexity_analysis)


def _simple_fallback_decompose(
    user_input: str,
    structured_data: Dict[str, Any] | None = None,
    complexity_analysis: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """
    增强版回退拆解策略（v7.110.0 智能化版本）

    当 LLM 调用失败时，基于结构化数据的多维度信息生成高质量任务列表。
    不再硬编码5-7个，而是根据复杂度分析动态调整任务数量。

    参考：校准问卷的智能补齐机制（questionnaire_optimization_summary.md）

    Args:
        user_input: 用户原始输入
        structured_data: 需求分析产出的结构化数据（包含 design_challenge, character_narrative 等）
        complexity_analysis: 复杂度分析结果（可选）

    Returns:
        任务列表（3-12个，根据复杂度动态决定）
    """

    tasks = []
    logger.info(" [Fallback] 使用增强版回退策略，基于结构化数据生成任务")

    #  v7.110.0: 获取智能推荐的任务数量范围
    if complexity_analysis is None:
        complexity_analysis = TaskComplexityAnalyzer.analyze(user_input, structured_data)

    recommended_min = complexity_analysis["recommended_min"]
    recommended_max = complexity_analysis["recommended_max"]
    logger.info(f" [Fallback智能] 目标任务数: {recommended_min}-{recommended_max}个")

    # 从结构化数据中提取关键信息
    design_challenge = ""
    project_type = ""
    if structured_data:
        design_challenge = structured_data.get("design_challenge", "")
        structured_data.get("character_narrative", "")
        project_type = structured_data.get("project_type", "")
        logger.info(f" [Fallback] 提取到结构化数据: design_challenge={bool(design_challenge)}, project_type={project_type}")

    # ==========================================================================
    # 1. 提取核心张力任务（优先级最高）
    # ==========================================================================
    tension_a = ""
    tension_b = ""
    if design_challenge:
        # 模式1: "A"...与..."B" 格式（中文引号）
        match = re.search(r'"([^"]{2,30})"[^"]{0,50}与[^"]{0,50}"([^"]{2,30})"', design_challenge)
        if match:
            tension_a = match.group(1).strip()
            tension_b = match.group(2).strip()
            logger.info(f' [Fallback] 提取核心张力: "{tension_a}" vs "{tension_b}"')
            tasks.append(
                {
                    "id": f"task_{len(tasks) + 1}",
                    "title": f"{tension_a}与{tension_b}的平衡策略研究",
                    "description": f"研究如何在设计中平衡{tension_a}和{tension_b}的需求，找到最佳解决方案",
                    "source_keywords": [tension_a, tension_b],
                    "task_type": "research",
                    "priority": "high",
                    "dependencies": [],
                    "execution_order": len(tasks) + 1,
                }
            )
        else:
            # 模式2: A vs B 或 A与其对B 格式
            match = re.search(r"(.{5,30}?)[的需求]*(?:vs|与其对)(.{5,30}?)[的需求]*", design_challenge)
            if match:
                tension_a = match.group(1).strip()
                tension_b = match.group(2).strip()
                logger.info(f" [Fallback] 提取核心张力 (模式2): {tension_a} vs {tension_b}")
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        "title": f"{tension_a}与{tension_b}的平衡策略研究",
                        "description": f"研究如何在设计中平衡{tension_a}和{tension_b}的需求，找到最佳解决方案",
                        "source_keywords": [tension_a, tension_b],
                        "task_type": "research",
                        "priority": "high",
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )

    # ==========================================================================
    # 2. 提取对标案例任务
    # ==========================================================================
    benchmarking_keywords = ["对标", "参考", "案例", "标杆", "对比"]
    for keyword in benchmarking_keywords:
        if keyword in user_input and not any(keyword in t["title"] for t in tasks):
            # 尝试提取具体的对标对象
            benchmark_patterns = [
                r"对标([^，。、！？\n]{2,30})",  # "对标苏州黄桥菜市场"
                r"参考([^，。、！？\n]{2,30})",
                r"([^，。、！？\n]{2,30})案例",
            ]
            benchmark_target = ""
            for pattern in benchmark_patterns:
                match = re.search(pattern, user_input)
                if match:
                    benchmark_target = match.group(1).strip()
                    break

            if benchmark_target:
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        "title": "对标案例深度研究",
                        "description": f"重点研究{benchmark_target}，并调研其他成功案例的设计策略和创新要素",
                        "source_keywords": [keyword, benchmark_target],
                        "task_type": "research",
                        "priority": "high",
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )
            else:
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        "title": "标杆案例研究",
                        "description": "调研行业内成功案例的设计策略、运营模式和创新要素",
                        "source_keywords": [keyword],
                        "task_type": "research",
                        "priority": "high",
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )
            break

    # ==========================================================================
    # 3. 提取文化要素任务
    # ==========================================================================
    culture_keywords = ["文化", "传统", "在地", "历史", "特色"]
    for keyword in culture_keywords:
        if keyword in user_input and not any(keyword in t["title"] for t in tasks):
            # 尝试提取具体的文化对象
            culture_patterns = [
                r"([^，。、！？\n]{2,15})[文化传统]",  # "蛇口渔村文化"
                r"融入([^，。、！？\n]{2,15})",
            ]
            culture_target = ""
            for pattern in culture_patterns:
                match = re.search(pattern, user_input)
                if match:
                    culture_target = match.group(1).strip()
                    if any(c in culture_target for c in ["文化", "传统", "特色"]):
                        break

            if culture_target:
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        "title": f"{culture_target}文化洞察与提炼",
                        "description": f"深入调研{culture_target}的历史文脉和精神内核，提炼可融入设计的文化元素",
                        "source_keywords": [keyword, culture_target],
                        "task_type": "research",
                        "priority": "high",
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )
            else:
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        "title": "文化调研与元素提炼",
                        "description": "调研项目相关的文化背景，提炼可融入设计的文化元素和符号",
                        "source_keywords": [keyword],
                        "task_type": "research",
                        "priority": "high",
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )
            break

    # ==========================================================================
    # 4. 提取客群分析任务
    # ==========================================================================
    audience_keywords = ["客群", "用户", "访客", "居民", "客户", "人群", "岁", "女性", "男性"]
    for keyword in audience_keywords:
        if keyword in user_input and not any("客群" in t["title"] or "生活方式" in t["title"] for t in tasks):
            # 尝试提取具体的客群描述
            audience_patterns = [
                r"(\d+岁[^，。、！？\n]{0,10})",  # "35岁单身女性"
                r"([^，。、！？\n]{2,15})[客群用户访客]",
                r"兼顾([^，。、！？\n]{5,50})",  # "兼顾蛇口老居民街坊、香港访客..."
            ]
            audience_target = ""
            for pattern in audience_patterns:
                match = re.search(pattern, user_input)
                if match:
                    audience_target = match.group(1).strip()
                    break

            # 特别处理: 35岁单身女性等年龄+特征的情况
            age_match = re.search(r"(\d+)岁([^，。、！？\n]{0,10})", user_input)
            if age_match:
                age = age_match.group(1)
                traits = age_match.group(2).strip()
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        "title": f"{age}岁{traits}生活方式研究",
                        "description": f"深入分析{age}岁{traits}的审美偏好、生活场景、社交需求和精神追求",
                        "source_keywords": [f"{age}岁", traits],
                        "task_type": "analysis",
                        "priority": "high",
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )
            elif audience_target:
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        "title": "多元客群分析",
                        "description": f"分析{audience_target}的需求差异与共性，找到设计的平衡点",
                        "source_keywords": [keyword, audience_target],
                        "task_type": "analysis",
                        "priority": "high",
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )
            else:
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        "title": "目标客群研究",
                        "description": "分析目标用户的需求特征、使用习惯和期望体验",
                        "source_keywords": [keyword],
                        "task_type": "analysis",
                        "priority": "high",
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )
            break

    # ==========================================================================
    # 5. 提取品牌相关任务（新增：针对 Tiffany 等品牌主题）
    # ==========================================================================
    # 检测品牌名（通常是英文或品牌关键词）
    brand_patterns = [
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",  # Tiffany, Louis Vuitton
        r"([^，。、！？\n]{2,10})为主题",  # "蒂芙尼为主题"
        r"([^，。、！？\n]{2,10})品牌",
    ]
    brand_name = ""
    for pattern in brand_patterns:
        match = re.search(pattern, user_input)
        if match:
            potential_brand = match.group(1).strip()
            # 过滤掉不太像品牌名的内容
            if len(potential_brand) >= 2 and not any(c in potential_brand for c in ["平米", "年", "设计", "项目"]):
                brand_name = potential_brand
                break

    if brand_name and not any(brand_name in t["title"] for t in tasks):
        tasks.append(
            {
                "id": f"task_{len(tasks) + 1}",
                "title": f"{brand_name}品牌文化洞察",
                "description": f"研究{brand_name}的品牌精神、色彩体系、经典设计元素和核心价值观",
                "source_keywords": [brand_name, "品牌"],
                "task_type": "research",
                "priority": "high",
                "dependencies": [],
                "execution_order": len(tasks) + 1,
            }
        )

    # ==========================================================================
    # 6. 提取空间/规模相关任务
    # ==========================================================================
    space_match = re.search(r"(\d+)平米", user_input)
    space_type_keywords = ["别墅", "住宅", "公寓", "办公", "商业", "零售", "酒店"]
    space_type = next((kw for kw in space_type_keywords if kw in user_input), "")

    if (space_match or space_type) and not any("空间" in t["title"] or "规划" in t["title"] for t in tasks):
        if space_match and space_type:
            area = space_match.group(1)
            tasks.append(
                {
                    "id": f"task_{len(tasks) + 1}",
                    "title": f"{area}平米{space_type}空间功能规划",
                    "description": f"制定符合用户需求的{area}平米{space_type}空间布局策略和功能分区方案",
                    "source_keywords": [f"{area}平米", space_type],
                    "task_type": "design",
                    "priority": "high",
                    "dependencies": [],
                    "execution_order": len(tasks) + 1,
                }
            )
        elif space_type:
            tasks.append(
                {
                    "id": f"task_{len(tasks) + 1}",
                    "title": f"{space_type}空间设计框架",
                    "description": f"输出{space_type}空间的整体设计框架和功能规划策略",
                    "source_keywords": [space_type],
                    "task_type": "design",
                    "priority": "high",
                    "dependencies": [],
                    "execution_order": len(tasks) + 1,
                }
            )

    # ==========================================================================
    # 7. 补充：最终交付物任务
    # ==========================================================================
    deliverable_keywords = ["框架", "方案", "概念", "设计思路"]
    for keyword in deliverable_keywords:
        if keyword in user_input and not any(keyword in t["title"] for t in tasks):
            # 提取交付物类型
            deliverable_patterns = [
                r"([^，。、！？\n]{2,10})框架",
                r"([^，。、！？\n]{2,10})方案",
                r"([^，。、！？\n]{2,10})设计思路",
            ]
            deliverable_target = ""
            for pattern in deliverable_patterns:
                match = re.search(pattern, user_input)
                if match:
                    deliverable_target = match.group(1).strip()
                    break

            if deliverable_target:
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        "title": f"{deliverable_target}设计框架输出",
                        "description": f"输出{deliverable_target}的整体设计框架，融合前期研究成果和设计策略",
                        "source_keywords": [keyword, deliverable_target],
                        "task_type": "design",
                        "priority": "high",
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )
            break

    # ==========================================================================
    # 8.  v7.110.0: 智能补齐和截断（不再固定5-7个）
    # ==========================================================================
    current_count = len(tasks)

    if current_count < recommended_min:
        logger.warning(f"️ [Fallback] 当前仅生成 {current_count} 个任务，补充通用任务至{recommended_min}个")
        # 补充通用任务
        generic_tasks = [
            {"title": "项目需求明确", "description": "明确项目的核心需求、期望目标和关键约束条件", "task_type": "analysis", "priority": "high"},
            {"title": "设计策略制定", "description": "制定整体设计策略和实施路径，确定设计的核心方向", "task_type": "design", "priority": "medium"},
            {"title": "行业趋势研究", "description": "研究相关领域的最新趋势、成功案例和创新实践", "task_type": "research", "priority": "medium"},
            {"title": "设计框架输出", "description": "整合前期研究成果，输出整体设计框架和实施建议", "task_type": "output", "priority": "medium"},
        ]

        for generic_task in generic_tasks:
            if len(tasks) >= recommended_min:
                break
            # 检查是否已有类似任务
            if not any(generic_task["title"] in t["title"] or t["title"] in generic_task["title"] for t in tasks):
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        **generic_task,
                        "source_keywords": [],
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )

    #  v7.110.0: 智能截断 - 不超过推荐最大值（优先保留高优先级）
    if len(tasks) > recommended_max:
        logger.warning(f"️ [Fallback] 生成了{len(tasks)}个任务，超过推荐上限{recommended_max}，智能截断")
        # 优先保留 high priority 的任务
        high_priority_tasks = [t for t in tasks if t.get("priority") == "high"]
        other_tasks = [t for t in tasks if t.get("priority") != "high"]
        tasks = (high_priority_tasks + other_tasks)[:recommended_max]

        # 重新编号
        for idx, task in enumerate(tasks, 1):
            task["id"] = f"task_{idx}"
            task["execution_order"] = idx

    logger.info(
        f" [Fallback] 生成 {len(tasks)} 个任务（推荐范围{recommended_min}-{recommended_max}，包含 {sum(1 for t in tasks if t['priority'] == 'high')} 个高优先级任务）"
    )

    return tasks


# 同步版本（用于非异步上下文）
def decompose_core_tasks_sync(
    user_input: str, structured_data: Dict[str, Any] | None = None, llm: Any | None = None
) -> List[Dict[str, Any]]:
    """
    同步执行核心任务拆解

    Args:
        user_input: 用户原始输入
        structured_data: 需求分析阶段产出的结构化数据（可选）
        llm: LLM 实例（可选）

    Returns:
        任务列表
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果已经在事件循环中，使用回退策略
            logger.warning("️ 检测到运行中的事件循环，使用回退策略")
            return _simple_fallback_decompose(user_input)
        else:
            return loop.run_until_complete(decompose_core_tasks(user_input, structured_data, llm))
    except RuntimeError:
        # 没有事件循环，创建一个
        return asyncio.run(decompose_core_tasks(user_input, structured_data, llm))
