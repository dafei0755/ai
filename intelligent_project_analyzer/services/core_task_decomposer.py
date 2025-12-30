"""
核心任务拆解服务

v7.80.1: 将用户模糊输入拆解为结构化的可执行任务列表
用于 Step 1: 明确核心任务
"""

import json
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
from loguru import logger


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
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
            logger.info(f"✅ [CoreTaskDecomposer] 配置加载成功: {config_path}")
        except Exception as e:
            logger.warning(f"⚠️ [CoreTaskDecomposer] 配置加载失败: {e}")
            self._config = {}

    @property
    def config(self) -> Dict[str, Any]:
        """获取配置"""
        return self._config or {}

    def build_prompt(self, user_input: str, structured_data: Optional[Dict[str, Any]] = None) -> str:
        """
        构建 LLM 调用的 prompt

        Args:
            user_input: 用户原始输入
            structured_data: 需求分析阶段产出的结构化数据（可选）

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

        # 填充用户 prompt
        user_prompt = user_template.format(
            user_input=user_input,
            structured_data_summary=structured_summary
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
            # 🆕 P1: 增强 JSON 提取能力 - 添加 debug 日志
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
                        logger.info(f"✅ [CoreTaskDecomposer] 使用括号平衡提取 JSON (长度: {len(response_text)})")

            # 策略 3: 尝试移除 JSON 中的注释（// 或 /* */）
            import re
            response_text = re.sub(r'//.*?$', '', response_text, flags=re.MULTILINE)  # 移除单行注释
            response_text = re.sub(r'/\*.*?\*/', '', response_text, flags=re.DOTALL)  # 移除多行注释

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
                    "priority": task.get("priority", "medium")
                }
                validated_tasks.append(validated_task)

            logger.info(f"✅ [CoreTaskDecomposer] 成功解析 {len(validated_tasks)} 个任务")
            return validated_tasks

        except json.JSONDecodeError as e:
            logger.error(f"❌ [CoreTaskDecomposer] JSON 解析失败: {e}")
            logger.debug(f"[CoreTaskDecomposer] 解析失败的文本: {response_text[:200]}")
            return self._fallback_decompose(response)
        except Exception as e:
            logger.error(f"❌ [CoreTaskDecomposer] 响应解析异常: {e}")
            return []

    def _fallback_decompose(self, text: str) -> List[Dict[str, Any]]:
        """
        回退策略：当 LLM 响应格式不正确时，使用简单的规则提取

        Args:
            text: 原始文本

        Returns:
            简化的任务列表
        """
        logger.warning("⚠️ [CoreTaskDecomposer] 使用回退策略提取任务")

        # 尝试从文本中提取编号列表
        lines = text.split("\n")
        tasks = []

        for i, line in enumerate(lines):
            line = line.strip()
            # 匹配 "1." "1、" "1)" "- " 等格式
            if line and (
                (line[0].isdigit() and len(line) > 2 and line[1] in ".、)") or
                line.startswith("- ") or
                line.startswith("• ")
            ):
                # 提取任务内容
                content = line.lstrip("0123456789.、)- •").strip()
                if content and len(content) > 5:
                    tasks.append({
                        "id": f"task_{len(tasks) + 1}",
                        "title": content[:50] if len(content) > 50 else content,
                        "description": content,
                        "source_keywords": [],
                        "task_type": "research",
                        "priority": "medium"
                    })

        # 限制任务数量
        return tasks[:7] if tasks else []


async def decompose_core_tasks(
    user_input: str,
    structured_data: Optional[Dict[str, Any]] = None,
    llm: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    异步执行核心任务拆解

    Args:
        user_input: 用户原始输入
        structured_data: 需求分析阶段产出的结构化数据（可选）
        llm: LLM 实例（可选，如果不提供则使用默认 LLM）

    Returns:
        任务列表
    """
    decomposer = CoreTaskDecomposer()

    # 构建 prompt
    prompt = decomposer.build_prompt(user_input, structured_data)

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

        user_prompt = user_template.format(
            user_input=user_input,
            structured_data_summary=structured_summary
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = await llm.ainvoke(messages)
        response_text = response.content if hasattr(response, "content") else str(response)

        # 解析响应
        tasks = decomposer.parse_response(response_text)

        if not tasks:
            # 如果解析失败，使用简单回退
            logger.warning("⚠️ LLM 任务拆解为空，使用回退策略")
            tasks = _simple_fallback_decompose(user_input, structured_data)

        return tasks

    except Exception as e:
        logger.error(f"❌ [decompose_core_tasks] LLM 调用失败: {e}")
        # 回退到简单拆解
        return _simple_fallback_decompose(user_input, structured_data)


def _simple_fallback_decompose(user_input: str, structured_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    增强版回退拆解策略（v7.80.2）

    当 LLM 调用失败时，基于结构化数据的多维度信息生成高质量任务列表。

    参考：校准问卷的智能补齐机制（questionnaire_optimization_summary.md）

    Args:
        user_input: 用户原始输入
        structured_data: 需求分析产出的结构化数据（包含 design_challenge, character_narrative 等）

    Returns:
        任务列表（5-7个高质量任务）
    """
    import re

    tasks = []
    logger.info("🔄 [Fallback] 使用增强版回退策略，基于结构化数据生成任务")

    # 从结构化数据中提取关键信息
    design_challenge = ""
    character_narrative = ""
    project_type = ""
    if structured_data:
        design_challenge = structured_data.get("design_challenge", "")
        character_narrative = structured_data.get("character_narrative", "")
        project_type = structured_data.get("project_type", "")
        logger.info(f"📊 [Fallback] 提取到结构化数据: design_challenge={bool(design_challenge)}, project_type={project_type}")

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
            logger.info(f"✅ [Fallback] 提取核心张力: \"{tension_a}\" vs \"{tension_b}\"")
            tasks.append({
                "id": f"task_{len(tasks) + 1}",
                "title": f"{tension_a}与{tension_b}的平衡策略研究",
                "description": f"研究如何在设计中平衡{tension_a}和{tension_b}的需求，找到最佳解决方案",
                "source_keywords": [tension_a, tension_b],
                "task_type": "research",
                "priority": "high"
            })
        else:
            # 模式2: A vs B 或 A与其对B 格式
            match = re.search(r'(.{5,30}?)[的需求]*(?:vs|与其对)(.{5,30}?)[的需求]*', design_challenge)
            if match:
                tension_a = match.group(1).strip()
                tension_b = match.group(2).strip()
                logger.info(f"✅ [Fallback] 提取核心张力 (模式2): {tension_a} vs {tension_b}")
                tasks.append({
                    "id": f"task_{len(tasks) + 1}",
                    "title": f"{tension_a}与{tension_b}的平衡策略研究",
                    "description": f"研究如何在设计中平衡{tension_a}和{tension_b}的需求，找到最佳解决方案",
                    "source_keywords": [tension_a, tension_b],
                    "task_type": "research",
                    "priority": "high"
                })

    # ==========================================================================
    # 2. 提取对标案例任务
    # ==========================================================================
    benchmarking_keywords = ["对标", "参考", "案例", "标杆", "对比"]
    for keyword in benchmarking_keywords:
        if keyword in user_input and not any(keyword in t["title"] for t in tasks):
            # 尝试提取具体的对标对象
            benchmark_patterns = [
                r'对标([^，。、！？\n]{2,30})',  # "对标苏州黄桥菜市场"
                r'参考([^，。、！？\n]{2,30})',
                r'([^，。、！？\n]{2,30})案例',
            ]
            benchmark_target = ""
            for pattern in benchmark_patterns:
                match = re.search(pattern, user_input)
                if match:
                    benchmark_target = match.group(1).strip()
                    break

            if benchmark_target:
                tasks.append({
                    "id": f"task_{len(tasks) + 1}",
                    "title": f"对标案例深度研究",
                    "description": f"重点研究{benchmark_target}，并调研其他成功案例的设计策略和创新要素",
                    "source_keywords": [keyword, benchmark_target],
                    "task_type": "research",
                    "priority": "high"
                })
            else:
                tasks.append({
                    "id": f"task_{len(tasks) + 1}",
                    "title": "标杆案例研究",
                    "description": "调研行业内成功案例的设计策略、运营模式和创新要素",
                    "source_keywords": [keyword],
                    "task_type": "research",
                    "priority": "high"
                })
            break

    # ==========================================================================
    # 3. 提取文化要素任务
    # ==========================================================================
    culture_keywords = ["文化", "传统", "在地", "历史", "特色"]
    for keyword in culture_keywords:
        if keyword in user_input and not any(keyword in t["title"] for t in tasks):
            # 尝试提取具体的文化对象
            culture_patterns = [
                r'([^，。、！？\n]{2,15})[文化传统]',  # "蛇口渔村文化"
                r'融入([^，。、！？\n]{2,15})',
            ]
            culture_target = ""
            for pattern in culture_patterns:
                match = re.search(pattern, user_input)
                if match:
                    culture_target = match.group(1).strip()
                    if any(c in culture_target for c in ["文化", "传统", "特色"]):
                        break

            if culture_target:
                tasks.append({
                    "id": f"task_{len(tasks) + 1}",
                    "title": f"{culture_target}文化洞察与提炼",
                    "description": f"深入调研{culture_target}的历史文脉和精神内核，提炼可融入设计的文化元素",
                    "source_keywords": [keyword, culture_target],
                    "task_type": "research",
                    "priority": "high"
                })
            else:
                tasks.append({
                    "id": f"task_{len(tasks) + 1}",
                    "title": "文化调研与元素提炼",
                    "description": "调研项目相关的文化背景，提炼可融入设计的文化元素和符号",
                    "source_keywords": [keyword],
                    "task_type": "research",
                    "priority": "high"
                })
            break

    # ==========================================================================
    # 4. 提取客群分析任务
    # ==========================================================================
    audience_keywords = ["客群", "用户", "访客", "居民", "客户", "人群", "岁", "女性", "男性"]
    for keyword in audience_keywords:
        if keyword in user_input and not any("客群" in t["title"] or "生活方式" in t["title"] for t in tasks):
            # 尝试提取具体的客群描述
            audience_patterns = [
                r'(\d+岁[^，。、！？\n]{0,10})',  # "35岁单身女性"
                r'([^，。、！？\n]{2,15})[客群用户访客]',
                r'兼顾([^，。、！？\n]{5,50})',  # "兼顾蛇口老居民街坊、香港访客..."
            ]
            audience_target = ""
            for pattern in audience_patterns:
                match = re.search(pattern, user_input)
                if match:
                    audience_target = match.group(1).strip()
                    break

            # 特别处理: 35岁单身女性等年龄+特征的情况
            age_match = re.search(r'(\d+)岁([^，。、！？\n]{0,10})', user_input)
            if age_match:
                age = age_match.group(1)
                traits = age_match.group(2).strip()
                tasks.append({
                    "id": f"task_{len(tasks) + 1}",
                    "title": f"{age}岁{traits}生活方式研究",
                    "description": f"深入分析{age}岁{traits}的审美偏好、生活场景、社交需求和精神追求",
                    "source_keywords": [f"{age}岁", traits],
                    "task_type": "analysis",
                    "priority": "high"
                })
            elif audience_target:
                tasks.append({
                    "id": f"task_{len(tasks) + 1}",
                    "title": "多元客群分析",
                    "description": f"分析{audience_target}的需求差异与共性，找到设计的平衡点",
                    "source_keywords": [keyword, audience_target],
                    "task_type": "analysis",
                    "priority": "high"
                })
            else:
                tasks.append({
                    "id": f"task_{len(tasks) + 1}",
                    "title": "目标客群研究",
                    "description": "分析目标用户的需求特征、使用习惯和期望体验",
                    "source_keywords": [keyword],
                    "task_type": "analysis",
                    "priority": "high"
                })
            break

    # ==========================================================================
    # 5. 提取品牌相关任务（新增：针对 Tiffany 等品牌主题）
    # ==========================================================================
    # 检测品牌名（通常是英文或品牌关键词）
    brand_patterns = [
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # Tiffany, Louis Vuitton
        r'([^，。、！？\n]{2,10})为主题',  # "蒂芙尼为主题"
        r'([^，。、！？\n]{2,10})品牌',
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
        tasks.append({
            "id": f"task_{len(tasks) + 1}",
            "title": f"{brand_name}品牌文化洞察",
            "description": f"研究{brand_name}的品牌精神、色彩体系、经典设计元素和核心价值观",
            "source_keywords": [brand_name, "品牌"],
            "task_type": "research",
            "priority": "high"
        })

    # ==========================================================================
    # 6. 提取空间/规模相关任务
    # ==========================================================================
    space_match = re.search(r'(\d+)平米', user_input)
    space_type_keywords = ["别墅", "住宅", "公寓", "办公", "商业", "零售", "酒店"]
    space_type = next((kw for kw in space_type_keywords if kw in user_input), "")

    if (space_match or space_type) and not any("空间" in t["title"] or "规划" in t["title"] for t in tasks):
        if space_match and space_type:
            area = space_match.group(1)
            tasks.append({
                "id": f"task_{len(tasks) + 1}",
                "title": f"{area}平米{space_type}空间功能规划",
                "description": f"制定符合用户需求的{area}平米{space_type}空间布局策略和功能分区方案",
                "source_keywords": [f"{area}平米", space_type],
                "task_type": "design",
                "priority": "high"
            })
        elif space_type:
            tasks.append({
                "id": f"task_{len(tasks) + 1}",
                "title": f"{space_type}空间设计框架",
                "description": f"输出{space_type}空间的整体设计框架和功能规划策略",
                "source_keywords": [space_type],
                "task_type": "design",
                "priority": "high"
            })

    # ==========================================================================
    # 7. 补充：最终交付物任务
    # ==========================================================================
    deliverable_keywords = ["框架", "方案", "概念", "设计思路"]
    for keyword in deliverable_keywords:
        if keyword in user_input and not any(keyword in t["title"] for t in tasks):
            # 提取交付物类型
            deliverable_patterns = [
                r'([^，。、！？\n]{2,10})框架',
                r'([^，。、！？\n]{2,10})方案',
                r'([^，。、！？\n]{2,10})设计思路',
            ]
            deliverable_target = ""
            for pattern in deliverable_patterns:
                match = re.search(pattern, user_input)
                if match:
                    deliverable_target = match.group(1).strip()
                    break

            if deliverable_target:
                tasks.append({
                    "id": f"task_{len(tasks) + 1}",
                    "title": f"{deliverable_target}设计框架输出",
                    "description": f"输出{deliverable_target}的整体设计框架，融合前期研究成果和设计策略",
                    "source_keywords": [keyword, deliverable_target],
                    "task_type": "design",
                    "priority": "high"
                })
            break

    # ==========================================================================
    # 8. 确保至少有 5 个任务
    # ==========================================================================
    if len(tasks) < 5:
        logger.warning(f"⚠️ [Fallback] 当前仅生成 {len(tasks)} 个任务，补充通用任务")
        # 补充通用任务
        generic_tasks = [
            {
                "title": "项目需求明确",
                "description": "明确项目的核心需求、期望目标和关键约束条件",
                "task_type": "analysis",
                "priority": "high"
            },
            {
                "title": "设计策略制定",
                "description": "制定整体设计策略和实施路径，确定设计的核心方向",
                "task_type": "design",
                "priority": "medium"
            },
            {
                "title": "行业趋势研究",
                "description": "研究相关领域的最新趋势、成功案例和创新实践",
                "task_type": "research",
                "priority": "medium"
            },
        ]

        for generic_task in generic_tasks:
            if len(tasks) >= 5:
                break
            # 检查是否已有类似任务
            if not any(generic_task["title"] in t["title"] or t["title"] in generic_task["title"] for t in tasks):
                tasks.append({
                    "id": f"task_{len(tasks) + 1}",
                    **generic_task,
                    "source_keywords": []
                })

    # 确保不超过 7 个任务
    tasks = tasks[:7]

    logger.info(f"✅ [Fallback] 生成 {len(tasks)} 个任务（包含 {sum(1 for t in tasks if t['priority'] == 'high')} 个高优先级任务）")

    return tasks


# 同步版本（用于非异步上下文）
def decompose_core_tasks_sync(
    user_input: str,
    structured_data: Optional[Dict[str, Any]] = None,
    llm: Optional[Any] = None
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
            logger.warning("⚠️ 检测到运行中的事件循环，使用回退策略")
            return _simple_fallback_decompose(user_input)
        else:
            return loop.run_until_complete(
                decompose_core_tasks(user_input, structured_data, llm)
            )
    except RuntimeError:
        # 没有事件循环，创建一个
        return asyncio.run(
            decompose_core_tasks(user_input, structured_data, llm)
        )
