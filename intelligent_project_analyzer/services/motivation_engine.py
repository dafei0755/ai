"""
动机识别引擎

v7.106: 配置化、可扩展、自学习的动机类型识别系统
"""

import asyncio
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from loguru import logger


@dataclass
class MotivationType:
    """动机类型定义"""

    id: str
    label_zh: str
    label_en: str
    priority: str
    description: str
    keywords: Dict[str, float]  # 关键词及其权重
    llm_examples: List[str]
    enabled: bool = True
    color: str = "#808080"


@dataclass
class MotivationResult:
    """动机识别结果"""

    primary: str  # 主要动机类型
    primary_label: str  # 主要动机中文标签
    scores: Dict[str, float]  # 所有类型的评分 0-1
    confidence: float  # 置信度
    reasoning: str  # 推理说明
    method: str  # 识别方法: llm/keyword/rule/default
    secondary: Optional[List[str]] = None  # 次要动机类型
    tags: List[str] = field(default_factory=list)  # 细粒度标签
    requires_human_review: bool = False  # 是否需要人工审核
    fallback_used: bool = False  # 是否使用了降级策略


@dataclass
class UnmatchedCase:
    """未匹配案例（用于学习）"""

    timestamp: str
    task_title: str
    task_description: str
    user_input_snippet: str
    assigned_type: str
    confidence: float
    method: str
    session_id: Optional[str] = None


class MotivationTypeRegistry:
    """动机类型注册表 - 支持动态加载"""

    _instance = None
    _types: Dict[str, MotivationType] = {}
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._types:
            self.load_from_config()

    def load_from_config(self, config_path: Optional[str] = None):
        """从配置文件加载动机类型"""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "motivation_types.yaml"

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)

            # 加载动机类型
            for item in self._config.get("motivation_types", []):
                if item.get("enabled", True):
                    # 转换keywords：如果是列表，转为字典（默认权重1.0）
                    keywords = item.get("keywords", [])
                    if isinstance(keywords, list):
                        item["keywords"] = {kw: 1.0 for kw in keywords}

                    motivation_type = MotivationType(**item)
                    self._types[motivation_type.id] = motivation_type

            logger.info(f" [MotivationRegistry] 加载 {len(self._types)} 个动机类型")
            logger.debug(f"   启用类型: {list(self._types.keys())}")

        except Exception as e:
            logger.error(f" [MotivationRegistry] 配置加载失败: {e}")
            self._load_fallback_types()

    def _load_fallback_types(self):
        """降级：加载最小必需类型"""
        logger.warning("️ [MotivationRegistry] 使用硬编码降级类型")
        basic_types = [
            MotivationType(
                id="functional",
                label_zh="功能性需求",
                label_en="Functional",
                priority="BASELINE",
                description="基础功能需求",
                keywords={"功能": 1.0, "空间": 1.0, "布局": 1.0},
                llm_examples=[],
                enabled=True,
            ),
            MotivationType(
                id="mixed",
                label_zh="综合需求",
                label_en="Mixed",
                priority="FALLBACK",
                description="综合需求",
                keywords={},
                llm_examples=[],
                enabled=True,
            ),
        ]
        for t in basic_types:
            self._types[t.id] = t

    def get_type(self, type_id: str) -> Optional[MotivationType]:
        """获取指定类型"""
        return self._types.get(type_id)

    def get_all_types(self) -> List[MotivationType]:
        """获取所有启用的类型"""
        return [t for t in self._types.values() if t.enabled]

    def reload(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        热更新配置 - v7.261

        重新从配置文件加载动机类型，无需重启服务。

        Args:
            config_path: 配置文件路径，默认使用 config/motivation_types.yaml

        Returns:
            更新结果字典，包含:
            - success: 是否成功
            - previous_count: 更新前类型数量
            - current_count: 更新后类型数量
            - added: 新增的类型ID列表
            - removed: 移除的类型ID列表
            - updated: 更新的类型ID列表
        """
        previous_types = set(self._types.keys())
        previous_count = len(self._types)

        # 清空现有配置
        self._types.clear()
        self._config.clear()

        # 重新加载
        try:
            self.load_from_config(config_path)

            current_types = set(self._types.keys())
            current_count = len(self._types)

            # 计算变更
            added = list(current_types - previous_types)
            removed = list(previous_types - current_types)
            updated = list(current_types & previous_types)

            logger.info(
                f" [MotivationRegistry] 热更新完成 | 之前={previous_count}, 现在={current_count}, 新增={len(added)}, 移除={len(removed)}"
            )

            return {
                "success": True,
                "previous_count": previous_count,
                "current_count": current_count,
                "added": added,
                "removed": removed,
                "updated": updated,
            }

        except Exception as e:
            logger.error(f" [MotivationRegistry] 热更新失败: {e}")
            # 恢复降级类型
            self._load_fallback_types()
            return {
                "success": False,
                "error": str(e),
                "previous_count": previous_count,
                "current_count": len(self._types),
            }

    def get_types_by_priority(self, priority: str) -> List[MotivationType]:
        """按优先级获取类型"""
        return [t for t in self._types.values() if t.priority == priority and t.enabled]

    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value if value is not None else default


class MotivationLearningSystem:
    """动机识别学习系统"""

    def __init__(self, registry: MotivationTypeRegistry):
        self.registry = registry
        self.feedback_log = Path(registry.get_config("learning.feedback_log_path", "logs/motivation_feedback.jsonl"))
        self.enabled = registry.get_config("learning.enabled", True)
        self.min_confidence = registry.get_config("learning.min_confidence_threshold", 0.7)

        # 确保日志目录存在
        self.feedback_log.parent.mkdir(parents=True, exist_ok=True)

    def record_unmatched_case(self, task: Dict[str, Any], user_input: str, result: MotivationResult):
        """记录低置信度或未匹配的案例"""

        if not self.enabled:
            return

        if result.confidence < self.min_confidence or result.primary == "mixed":
            case = UnmatchedCase(
                timestamp=datetime.now().isoformat(),
                task_title=task.get("title", ""),
                task_description=task.get("description", ""),
                user_input_snippet=user_input[:200] if user_input else "",
                assigned_type=result.primary,
                confidence=result.confidence,
                method=result.method,
                session_id=task.get("session_id"),
            )

            try:
                with open(self.feedback_log, "a", encoding="utf-8") as f:
                    f.write(json.dumps(asdict(case), ensure_ascii=False) + "\n")
                logger.debug(f" [Learning] 记录待学习案例: {case.task_title[:30]}...")
            except Exception as e:
                logger.warning(f"️ [Learning] 记录失败: {e}")

    def get_recent_cases(self, days: int = 7) -> List[UnmatchedCase]:
        """获取最近N天的待学习案例"""
        if not self.feedback_log.exists():
            return []

        cases = []
        cutoff = datetime.now().timestamp() - (days * 86400)

        try:
            with open(self.feedback_log, "r", encoding="utf-8") as f:
                for line in f:
                    case_dict = json.loads(line)
                    case_time = datetime.fromisoformat(case_dict["timestamp"]).timestamp()
                    if case_time >= cutoff:
                        cases.append(UnmatchedCase(**case_dict))
        except Exception as e:
            logger.warning(f"️ [Learning] 读取日志失败: {e}")

        return cases

    async def weekly_pattern_analysis(self) -> Dict[str, Any]:
        """
        每周分析学习案例，发现新模式

        Returns:
            分析报告字典，包含：
            - status: 分析状态
            - case_count: 案例数量
            - type_distribution: 类型分布
            - llm_analysis: LLM聚类分析结果
            - recommendation: 配置更新建议
        """

        if not self.enabled:
            return {"status": "disabled", "message": "学习系统未启用"}

        cases = self.get_recent_cases(days=7)

        if len(cases) < 5:
            return {"status": "insufficient_data", "case_count": len(cases), "message": "案例不足5个，跳过分析"}

        logger.info(f" [Learning] 开始分析 {len(cases)} 个案例...")

        # 统计类型分布
        type_distribution = {}
        low_confidence_cases = []

        for case in cases:
            type_distribution[case.assigned_type] = type_distribution.get(case.assigned_type, 0) + 1
            if case.confidence < self.min_confidence:
                low_confidence_cases.append(case)

        # 提取高频短语
        frequent_phrases = self._extract_frequent_phrases(cases)

        # LLM聚类分析
        try:
            llm_analysis = await self._llm_pattern_discovery(cases, frequent_phrases)
        except Exception as e:
            logger.warning(f"️ [Learning] LLM分析失败: {e}")
            llm_analysis = {"error": str(e)}

        # 生成报告
        report = {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "case_count": len(cases),
            "low_confidence_count": len(low_confidence_cases),
            "mixed_count": type_distribution.get("mixed", 0),
            "type_distribution": type_distribution,
            "frequent_phrases": frequent_phrases[:20],  # 前20个
            "llm_analysis": llm_analysis,
            "recommendation": self._generate_recommendation(llm_analysis, type_distribution),
        }

        # 保存报告
        report_path = self.feedback_log.parent / f"analysis_{datetime.now().strftime('%Y%m%d')}.json"
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f" [Learning] 分析报告已保存: {report_path}")
        except Exception as e:
            logger.warning(f"️ [Learning] 保存报告失败: {e}")

        return report

    def _extract_frequent_phrases(self, cases: List[UnmatchedCase], top_n: int = 50) -> List[Dict[str, Any]]:
        """提取高频短语（使用jieba分词）"""
        try:
            from collections import Counter

            import jieba

            # 合并所有文本
            all_text = " ".join(
                [f"{case.task_title} {case.task_description} {case.user_input_snippet}" for case in cases]
            )

            # 分词并统计
            words = jieba.lcut(all_text)
            # 过滤停用词和单字
            words = [w for w in words if len(w) >= 2 and w.strip()]

            # 统计词频
            counter = Counter(words)

            return [{"phrase": phrase, "count": count} for phrase, count in counter.most_common(top_n)]

        except Exception as e:
            logger.warning(f"️ [Learning] 提取短语失败: {e}")
            return []

    async def _llm_pattern_discovery(
        self, cases: List[UnmatchedCase], frequent_phrases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """使用LLM进行聚类分析，发现新模式"""

        # 构建案例摘要
        case_summaries = []
        for i, case in enumerate(cases[:30], 1):  # 限制30个案例
            case_summaries.append(
                f"{i}. [{case.assigned_type}] {case.task_title} " f"(置信度: {case.confidence:.2f}, 方法: {case.method})"
            )

        # 构建短语列表
        phrase_list = [f"- {p['phrase']} ({p['count']}次)" for p in frequent_phrases[:15]]

        # 构建prompt
        prompt = f"""你是一个设计研究专家，正在分析设计任务的动机类型识别问题。

当前动机类型系统包含以下类型：
{', '.join([t.label_zh for t in self.registry.get_all_types()])}

以下是最近一周收集的 {len(cases)} 个低置信度或未识别案例：

{chr(10).join(case_summaries)}

高频关键词/短语：
{chr(10).join(phrase_list)}

请分析：
1. 这些案例是否存在共同的模式或聚类？
2. 是否发现新的动机维度（当前类型未覆盖）？
3. 哪些现有类型的关键词配置需要加强？

请以JSON格式返回分析结果：
{{
  "discovered_patterns": [
    {{
      "pattern_name": "模式名称",
      "case_count": 相关案例数量,
      "description": "模式描述",
      "example_keywords": ["关键词1", "关键词2"]
    }}
  ],
  "new_dimensions": [
    {{
      "dimension_name": "新维度名称",
      "description": "维度描述",
      "rationale": "为什么需要这个维度",
      "suggested_keywords": ["关键词1", "关键词2"]
    }}
  ],
  "enhancement_suggestions": [
    {{
      "type_id": "类型ID",
      "add_keywords": ["建议添加的关键词"],
      "reason": "原因说明"
    }}
  ]
}}"""

        try:
            from langchain_core.messages import HumanMessage

            from intelligent_project_analyzer.services.llm_factory import LLMFactory

            llm = LLMFactory.create_llm()
            response = await asyncio.wait_for(llm.ainvoke([HumanMessage(content=prompt)]), timeout=60)  # 60秒超时

            # 提取JSON
            import re

            json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"error": "LLM未返回有效JSON", "raw_response": response.content[:500]}

        except Exception as e:
            logger.error(f" [Learning] LLM模式发现失败: {e}")
            return {"error": str(e)}

    def _generate_recommendation(
        self, llm_analysis: Dict[str, Any], type_distribution: Dict[str, int]
    ) -> Dict[str, Any]:
        """基于分析结果生成建议"""

        recommendations = {"priority": "low", "actions": []}

        # 检查mixed比例
        total_cases = sum(type_distribution.values())
        mixed_ratio = type_distribution.get("mixed", 0) / total_cases if total_cases > 0 else 0

        if mixed_ratio > 0.3:
            recommendations["priority"] = "high"
            recommendations["actions"].append(
                {"type": "high_mixed_ratio", "message": f"Mixed类型占比 {mixed_ratio:.1%}，建议检查关键词配置或增加新类型"}
            )

        # 处理LLM发现的新维度
        if "new_dimensions" in llm_analysis and llm_analysis["new_dimensions"]:
            recommendations["priority"] = "medium"
            recommendations["actions"].append(
                {
                    "type": "new_dimensions_discovered",
                    "count": len(llm_analysis["new_dimensions"]),
                    "dimensions": llm_analysis["new_dimensions"],
                }
            )

        # 处理增强建议
        if "enhancement_suggestions" in llm_analysis and llm_analysis["enhancement_suggestions"]:
            recommendations["actions"].append(
                {"type": "keyword_enhancement", "suggestions": llm_analysis["enhancement_suggestions"]}
            )

        return recommendations


class MotivationInferenceEngine:
    """动机推断引擎 - 4级降级策略"""

    def __init__(self):
        self.registry = MotivationTypeRegistry()
        self.learning = MotivationLearningSystem(self.registry)

    async def infer(
        self, task: Dict[str, Any], user_input: str, structured_data: Optional[Dict[str, Any]] = None
    ) -> MotivationResult:
        """
        推断任务的动机类型（4级降级策略）

        Level 1: LLM智能推理（首选）
        Level 2: 增强关键词匹配
        Level 3: 规则引擎
        Level 4: 默认mixed + 记录
        """

        # Level 1: LLM智能推理
        if self.registry.get_config("llm_inference.enabled", False):
            try:
                result = await self._llm_inference(task, user_input, structured_data)
                threshold = self.registry.get_config("llm_inference.min_confidence_threshold", 0.7)

                if result.confidence >= threshold:
                    logger.info(f" [Level 1] LLM识别: {result.primary} (置信度: {result.confidence:.2f})")
                    self.learning.record_unmatched_case(task, user_input, result)
                    return result
                else:
                    logger.debug(f"️ [Level 1] LLM置信度低 ({result.confidence:.2f})，降级")
            except Exception as e:
                logger.warning(f"️ [Level 1] LLM失败: {e}，降级到关键词匹配")

        # Level 2: 增强关键词匹配
        result = self._keyword_matching(task, user_input, structured_data)
        if result.confidence >= 0.6:
            logger.info(f" [Level 2] 关键词匹配: {result.primary} (置信度: {result.confidence:.2f})")
            self.learning.record_unmatched_case(task, user_input, result)
            return result

        # Level 3: 规则引擎
        result = self._rule_based_inference(task, structured_data)
        if result.confidence >= 0.5:
            logger.info(f" [Level 3] 规则推断: {result.primary} (置信度: {result.confidence:.2f})")
            self.learning.record_unmatched_case(task, user_input, result)
            return result

        # Level 4: 默认mixed
        logger.warning(f"️ [Level 4] 使用默认mixed，置信度低 ({result.confidence:.2f})")
        result = MotivationResult(
            primary="mixed",
            primary_label="综合需求",
            scores={"mixed": 1.0},
            confidence=0.3,
            reasoning="未找到明确动机模式，建议人工review",
            method="default",
            requires_human_review=True,
        )
        self.learning.record_unmatched_case(task, user_input, result)
        return result

    async def _llm_inference(
        self, task: Dict[str, Any], user_input: str, structured_data: Optional[Dict[str, Any]]
    ) -> MotivationResult:
        """Level 1: LLM智能推理"""

        # 构建动机类型列表描述
        type_descriptions = []
        for mtype in self.registry.get_all_types():
            if mtype.id != "mixed":  # 排除mixed
                examples = mtype.llm_examples[:2] if mtype.llm_examples else []
                examples_text = f"\n     示例: {', '.join(examples)}" if examples else ""
                # 使用更完整的格式，帮助LLM理解每个类型
                type_descriptions.append(f"  {mtype.id} ({mtype.label_zh}动机): {mtype.description}{examples_text}")

        types_text = "\n".join(type_descriptions)

        # 构建结构化数据摘要
        context_parts = []
        if structured_data:
            if structured_data.get("project_task"):
                context_parts.append(f"项目任务: {structured_data['project_task']}")
            if structured_data.get("design_challenge"):
                context_parts.append(f"设计挑战: {structured_data['design_challenge']}")
            if structured_data.get("character_narrative"):
                context_parts.append(f"人物叙事: {structured_data['character_narrative']}")

        context_text = "\n".join(context_parts) if context_parts else "无额外上下文"

        prompt = f"""你是一位资深室内设计顾问，需要分析项目**单个任务**的核心动机类型。

【可选动机类型】
{types_text}

【当前任务】（重点分析）
- 标题: {task.get('title', '')}
- 描述: {task.get('description', '')}
- 关键词: {', '.join(task.get('source_keywords', []))}

【项目背景】（仅供参考）
用户整体需求: {user_input[:300] if user_input else "无"}

【补充上下文】
{context_text}

️ **任务独立性原则**（最重要）:
1. **专注分析当前任务本身**，忽略项目整体描述的干扰
2. **同一项目中不同任务必然有不同的动机类型**（禁止所有任务都选择同一类型）
3. **根据任务动作词判断**：
   - "调研"、"搜索"、"分析" → 看调研的对象（文化=cultural, 案例=aesthetic, 产业=commercial）
   - "对标"、"收集案例" → aesthetic（审美）或professional（专业职能）
   - "设计"、"规划"、"方案" → functional（功能性）或aesthetic（审美）
4. **避免过度解读**：不要因为项目涉及文化就将所有任务都标记为cultural

 **项目任务示例对照**（学习如何区分）:
假设项目："四川狮岭村民宿集群设计，融合中日设计大师智慧"

正确标注示例:
-  错误: "调研狮岭村文化" → cultural（文化认同） 
  "收集安藤忠雄案例" → cultural（错误！案例研究是审美，不是文化）
  "分析多元设计趋势" → cultural（错误！趋势分析是专业，不是文化）
  
-  正确: 
  "调研狮岭村在地文化与产业" → commercial（商业价值）或cultural（文化认同，取决于重点）
  "收集安藤忠雄与隈研吾民宿案例" → aesthetic（审美）- 设计大师案例研究
  "查找刘家琨、王澍作品和理念" → aesthetic（审美）或professional（专业职能）
  "分析中日设计融合趋势" → aesthetic（审美）- 设计风格分析
  "民宿群空间规划与概念方案" → functional（功能性）- 空间布局规划

关键区分点:
- 文化调研（cultural）≠ 设计案例研究（aesthetic）≠ 商业模式研究（commercial）
- 同一个项目涉及"文化"，但不同任务的动机完全不同

请分析当前任务的动机类型：
1. 选择最匹配的主要动机类型（primary）- 优先考虑任务的动作和对象
2. 如果有明显的次要动机，列出1-2个（secondary）
3. 给出0-1之间的置信度（confidence）
4. 用简短一句话说明推理过程（reasoning，30字以内）

以JSON格式输出：
{{
    "primary": "类型英文ID",
    "secondary": ["类型1", "类型2"],
    "confidence": 0.XX,
    "reasoning": "推理说明"
}}"""

        # 调试日志：输出Prompt的前500字符
        logger.debug(f" [LLM Prompt Preview] 任务: {task.get('title', '')[:30]}")
        logger.debug(f" [动机类型列表] {types_text[:300]}...")

        try:
            # 导入LLM
            from langchain_core.messages import HumanMessage

            from ..services.llm_factory import LLMFactory

            llm = LLMFactory.create_llm()
            timeout = self.registry.get_config("llm_inference.timeout", 30)

            # 异步调用LLM
            response = await asyncio.wait_for(llm.ainvoke([HumanMessage(content=prompt)]), timeout=timeout)

            # 解析响应
            response_text = response.content if hasattr(response, "content") else str(response)

            # 提取JSON
            import re

            json_match = re.search(r"\{[^{}]*\}", response_text, re.DOTALL)
            if not json_match:
                raise ValueError("未找到JSON格式响应")

            result_data = json.loads(json_match.group())

            # 验证结果
            primary_id = result_data.get("primary", "mixed")
            primary_type = self.registry.get_type(primary_id)

            if not primary_type:
                logger.warning(f"️ LLM返回未知类型: {primary_id}，使用mixed")
                primary_id = "mixed"
                primary_type = self.registry.get_type("mixed")

            confidence = float(result_data.get("confidence", 0.5))
            reasoning = result_data.get("reasoning", "LLM分析结果")
            secondary = result_data.get("secondary", [])

            # 构建评分字典
            scores = {primary_id: confidence}
            for sec_id in secondary:
                if self.registry.get_type(sec_id):
                    scores[sec_id] = confidence * 0.6  # 次要动机评分为主要的60%

            logger.info(f" [LLM] 推断完成: {primary_type.label_zh} (置信度: {confidence:.2f})")

            return MotivationResult(
                primary=primary_id,
                primary_label=primary_type.label_zh,
                scores=scores,
                confidence=confidence,
                reasoning=reasoning,
                method="llm",
                secondary=secondary if secondary else None,
            )

        except asyncio.TimeoutError:
            logger.warning(f"️ [LLM] 超时 ({timeout}s)，降级到关键词匹配")
            raise
        except Exception as e:
            logger.warning(f"️ [LLM] 推理失败: {e}")
            raise

    def _keyword_matching(
        self, task: Dict[str, Any], user_input: str, structured_data: Optional[Dict[str, Any]]
    ) -> MotivationResult:
        """Level 2: 增强关键词匹配"""

        title = task.get("title", "").lower()
        desc = task.get("description", "").lower()
        user_text = (user_input or "").lower()

        # 获取权重配置
        title_weight = self.registry.get_config("keyword_matching.title_weight", 2.0)
        desc_weight = self.registry.get_config("keyword_matching.description_weight", 1.0)
        context_weight = self.registry.get_config("keyword_matching.context_weight", 0.5)

        # 计算每个类型的匹配分数
        scores = {}
        for mtype in self.registry.get_all_types():
            if not mtype.keywords:
                continue

            score = 0.0
            matched_keywords = []

            for keyword in mtype.keywords:
                kw = keyword.lower()
                if kw in title:
                    score += title_weight
                    matched_keywords.append(keyword)
                if kw in desc:
                    score += desc_weight
                    matched_keywords.append(keyword)
                if kw in user_text:
                    score += context_weight

            if score > 0:
                scores[mtype.id] = min(score / 10.0, 1.0)  # 归一化到0-1
                logger.debug(f"   {mtype.label_zh}: {scores[mtype.id]:.2f} (关键词: {matched_keywords[:3]})")

        # 找到最高分
        if not scores:
            return MotivationResult(
                primary="mixed",
                primary_label="综合需求",
                scores={"mixed": 1.0},
                confidence=0.3,
                reasoning="未匹配到任何关键词",
                method="keyword",
            )

        primary_id = max(scores.items(), key=lambda x: x[1])[0]
        primary_type = self.registry.get_type(primary_id)
        confidence = scores[primary_id]

        # 找次要类型
        secondary = [k for k, v in sorted(scores.items(), key=lambda x: -x[1])[1:3] if v >= 0.4]

        return MotivationResult(
            primary=primary_id,
            primary_label=primary_type.label_zh,
            scores=scores,
            confidence=confidence,
            reasoning=f"基于关键词匹配识别为{primary_type.label_zh}",
            method="keyword",
            secondary=secondary if secondary else None,
        )

    def _rule_based_inference(
        self, task: Dict[str, Any], structured_data: Optional[Dict[str, Any]]
    ) -> MotivationResult:
        """Level 3: 规则引擎（基于项目类型等）"""

        # 简单规则：基于任务类型
        task_type = task.get("task_type", "").lower()

        if task_type == "research":
            return MotivationResult(
                primary="functional",
                primary_label="功能性需求",
                scores={"functional": 0.6},
                confidence=0.5,
                reasoning="研究类任务默认为功能性需求",
                method="rule",
            )

        # 默认
        return MotivationResult(
            primary="mixed",
            primary_label="综合需求",
            scores={"mixed": 0.5},
            confidence=0.4,
            reasoning="无匹配规则，默认综合需求",
            method="rule",
        )


# 全局单例
_engine: Optional[MotivationInferenceEngine] = None


def get_motivation_engine() -> MotivationInferenceEngine:
    """获取动机推断引擎单例"""
    global _engine
    if _engine is None:
        _engine = MotivationInferenceEngine()
    return _engine


# ==================== 深度洞察分析 ====================


@dataclass
class MotivationInsight:
    """动机深度洞察结果"""

    l1_surface: Dict[str, Any]  # L1层：表层需求
    l2_implicit: Dict[str, Any]  # L2层：隐含动机
    l3_deep: Dict[str, Any]  # L3层：深层驱动
    core_tensions: List[str]  # 核心张力
    unspoken_expectations: List[str]  # 未说出口的期待
    risk_blind_spots: List[str]  # 风险盲区


async def deep_motivation_analysis(
    task: Dict[str, Any],
    user_input: str,
    basic_result: MotivationResult,
    structured_data: Optional[Dict[str, Any]] = None,
) -> MotivationInsight:
    """
    深度动机洞察分析（L1/L2/L3层次）

    Args:
        task: 任务信息
        user_input: 用户原始输入
        basic_result: 基础动机识别结果
        structured_data: 结构化上下文

    Returns:
        MotivationInsight: 深度洞察结果
    """

    # L1层：表层需求（直接从basic_result提取）
    l1_surface = {
        "primary_motivation": basic_result.primary,
        "primary_label": basic_result.primary_label,
        "confidence": basic_result.confidence,
        "scores": basic_result.scores,
        "explicit_keywords": _extract_explicit_keywords(user_input, basic_result),
    }

    # L2/L3层需要LLM深度分析
    try:
        llm_insight = await _llm_deep_analysis(task, user_input, basic_result, structured_data)

        l2_implicit = llm_insight.get("l2_implicit", {})
        l3_deep = llm_insight.get("l3_deep", {})
        core_tensions = llm_insight.get("core_tensions", [])
        unspoken_expectations = llm_insight.get("unspoken_expectations", [])
        risk_blind_spots = llm_insight.get("risk_blind_spots", [])

    except Exception as e:
        logger.warning(f"️ [Deep Insight] LLM分析失败: {e}")

        # 降级：基于规则的简化分析
        l2_implicit = _rule_based_implicit_analysis(basic_result)
        l3_deep = _rule_based_deep_analysis(basic_result)
        core_tensions = []
        unspoken_expectations = []
        risk_blind_spots = []

    return MotivationInsight(
        l1_surface=l1_surface,
        l2_implicit=l2_implicit,
        l3_deep=l3_deep,
        core_tensions=core_tensions,
        unspoken_expectations=unspoken_expectations,
        risk_blind_spots=risk_blind_spots,
    )


def _extract_explicit_keywords(user_input: str, result: MotivationResult) -> List[str]:
    """提取用户输入中的显性关键词"""
    registry = MotivationTypeRegistry()
    motivation_type = registry.get_type(result.primary)

    if not motivation_type:
        return []

    # 检查哪些关键词出现在用户输入中
    explicit_keywords = []
    for keyword, weight in motivation_type.keywords.items():
        if keyword in user_input.lower():
            explicit_keywords.append(keyword)

    return explicit_keywords[:10]  # 最多10个


async def _llm_deep_analysis(
    task: Dict[str, Any], user_input: str, basic_result: MotivationResult, structured_data: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """使用LLM进行L2/L3深度分析"""

    # 构建上下文
    context_parts = []
    if structured_data:
        for key, value in structured_data.items():
            if value:
                context_parts.append(f"- {key}: {value}")
    context_text = "\n".join(context_parts) if context_parts else "（无额外上下文）"

    # 构建prompt
    prompt = f"""你是一位经验丰富的设计研究专家，擅长洞察用户的深层需求和动机。

**任务信息：**
- 标题：{task.get('title', '未知')}
- 描述：{task.get('description', '未知')}

**用户原始输入：**
{user_input}

**上下文信息：**
{context_text}

**初步动机识别：**
- 主要动机：{basic_result.primary_label} ({basic_result.primary})
- 置信度：{basic_result.confidence:.2f}
- 推理：{basic_result.reasoning}

请进行三层深度分析：

**L1层 - 表层需求**（已识别）：
{basic_result.primary_label}

**L2层 - 隐含动机**：
从用户的表述、语气、关注点中，推断出未明确说出的隐含动机。这些动机可能影响决策方向，但用户自己可能未意识到。

**L3层 - 深层驱动**：
结合马斯洛需求层次理论，分析更深层的心理驱动：
- 生理需求：基本功能、舒适度
- 安全需求：稳定性、可靠性、风险规避
- 社交需求：归属感、认同感、关系建立
- 尊重需求：地位、声誉、成就感
- 自我实现：创新、意义、价值创造

**关键分析点：**
1. 核心张力：用户需求中存在哪些矛盾或张力？（如成本vs质量、创新vs稳妥）
2. 未说出口的期待：用户可能期待但未明确提及的东西？
3. 风险盲区：用户可能忽视但重要的风险点？

请以JSON格式返回：
{{
  "l2_implicit": {{
    "hidden_motivations": ["隐含动机1", "隐含动机2"],
    "emotional_drivers": ["情绪驱动1", "情绪驱动2"],
    "stakeholder_concerns": ["利益相关者关注1", "关注2"]
  }},
  "l3_deep": {{
    "maslow_level": "对应的马斯洛层次",
    "psychological_drivers": ["心理驱动1", "驱动2"],
    "underlying_values": ["底层价值观1", "价值观2"],
    "long_term_impact": "长期影响分析"
  }},
  "core_tensions": ["张力1：A vs B", "张力2：X vs Y"],
  "unspoken_expectations": ["期待1", "期待2"],
  "risk_blind_spots": ["风险1：描述", "风险2：描述"]
}}"""

    try:
        import re

        from langchain_core.messages import HumanMessage

        from intelligent_project_analyzer.services.llm_factory import LLMFactory

        llm = LLMFactory.create_llm()
        response = await asyncio.wait_for(llm.ainvoke([HumanMessage(content=prompt)]), timeout=45)  # 45秒超时

        # 提取JSON
        json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            raise ValueError("LLM未返回有效JSON")

    except Exception as e:
        logger.error(f" [Deep Analysis] LLM失败: {e}")
        raise


def _rule_based_implicit_analysis(basic_result: MotivationResult) -> Dict[str, Any]:
    """基于规则的L2层简化分析"""

    # 根据动机类型映射常见隐含动机
    implicit_mapping = {
        "cultural": {
            "hidden_motivations": ["文化认同焦虑", "传统与现代的平衡"],
            "emotional_drivers": ["归属感", "文化自豪"],
            "stakeholder_concerns": ["社区反馈", "文化专家认可"],
        },
        "commercial": {
            "hidden_motivations": ["投资回报压力", "市场竞争焦虑"],
            "emotional_drivers": ["成功欲望", "经济安全感"],
            "stakeholder_concerns": ["投资人期待", "财务可持续性"],
        },
        "wellness": {
            "hidden_motivations": ["健康焦虑", "生活质量提升"],
            "emotional_drivers": ["安全感", "关怀"],
            "stakeholder_concerns": ["用户健康", "医疗专业性"],
        },
        "functional": {
            "hidden_motivations": ["效率焦虑", "技术能力证明"],
            "emotional_drivers": ["控制感", "成就感"],
            "stakeholder_concerns": ["用户体验", "技术可行性"],
        },
    }

    return implicit_mapping.get(
        basic_result.primary,
        {"hidden_motivations": ["待深度分析"], "emotional_drivers": ["待深度分析"], "stakeholder_concerns": ["待深度分析"]},
    )


def _rule_based_deep_analysis(basic_result: MotivationResult) -> Dict[str, Any]:
    """基于规则的L3层简化分析"""

    # 根据动机类型映射马斯洛层次
    maslow_mapping = {
        "wellness": {
            "maslow_level": "安全需求",
            "psychological_drivers": ["健康保障", "风险规避"],
            "underlying_values": ["生命价值", "预防理念"],
            "long_term_impact": "提升用户长期健康水平和生活质量",
        },
        "social": {
            "maslow_level": "社交需求",
            "psychological_drivers": ["归属感", "连接感"],
            "underlying_values": ["关系价值", "社群认同"],
            "long_term_impact": "建立持久的社交关系和社区联结",
        },
        "aesthetic": {
            "maslow_level": "尊重需求",
            "psychological_drivers": ["品味认同", "审美表达"],
            "underlying_values": ["美学价值", "个性表达"],
            "long_term_impact": "塑造品牌形象和用户感知",
        },
        "commercial": {
            "maslow_level": "安全需求",
            "psychological_drivers": ["经济稳定", "商业成功"],
            "underlying_values": ["价值创造", "可持续性"],
            "long_term_impact": "实现商业价值和财务可持续",
        },
        "cultural": {
            "maslow_level": "自我实现",
            "psychological_drivers": ["意义追寻", "文化传承"],
            "underlying_values": ["文化价值", "历史责任"],
            "long_term_impact": "保护和传承文化遗产，建立文化认同",
        },
    }

    return maslow_mapping.get(
        basic_result.primary,
        {
            "maslow_level": "待深度分析",
            "psychological_drivers": ["待深度分析"],
            "underlying_values": ["待深度分析"],
            "long_term_impact": "待深度分析",
        },
    )
