"""
维度提取器 (Dimension Extractor)

从专家输出中自动提取可复用的分析维度。

核心策略:
1. 规则匹配 - 快速识别明显的维度标记
2. LLM语义理解 - 深度语义分析
3. 结构化提取 - 组织成维度候选
4. 质量评分 - 置信度排序

版本: v3.0
创建日期: 2026-02-10
"""

import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from loguru import logger

# 暂时注释LLM调用，先实现框架
# import openai


@dataclass
class ExtractedDimension:
    """提取的维度候选"""

    name: str  # 维度名称（中英文）
    category: str  # 所属分类（如 spiritual_world, business_positioning 等）
    description: str  # 详细描述
    ask_yourself: str  # 引导性问题
    examples: str  # 具体示例（逗号分隔）
    confidence: float  # 置信度 (0.0-1.0)
    source_context: str  # 来源上下文
    project_type: str  # 适用项目类型

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)

    def to_yaml_format(self) -> str:
        """转换为YAML格式"""
        return f"""      - name: "{self.name}"
        description: "{self.description}"
        ask_yourself: "{self.ask_yourself}"
        examples: "{self.examples}"
"""


class DimensionExtractor:
    """
    从专家输出中自动提取分析维度

    核心能力:
    1. NLP分析识别关键问题
    2. 模式匹配提取结构化信息
    3. LLM驱动的语义理解
    4. 置信度评分
    """

    def __init__(self, llm_model: str = "gpt-4o", enable_llm: bool = False):
        """
        初始化提取器

        Args:
            llm_model: LLM模型名称
            enable_llm: 是否启用LLM（默认False，先用规则）
        """
        self.llm_model = llm_model
        self.enable_llm = enable_llm
        self.patterns = self._compile_patterns()

        logger.info(f" 初始化维度提取器 (LLM: {enable_llm})")

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """编译正则表达式模式"""
        return {
            # 识别"如何"问题（优先级最高，放在最前面）
            "how_questions": re.compile(r"[0-9\.\s]*(?:如何|怎样|怎么|how to|how can).{5,80}?[？\?]", re.IGNORECASE),
            # 识别"是否"问题
            "whether_questions": re.compile(r"[0-9\.\s]*(?:是否|能否|会不会|whether|can we).{5,80}?[？\?]", re.IGNORECASE),
            # 识别"核心问题"模式（不包含具体问题，只是标题）
            "core_question": re.compile(r"(?:关键问题|核心问题|需要考虑|need to consider|should ask)[:：]", re.IGNORECASE),
            # 识别"分析维度"模式
            "dimension_marker": re.compile(
                r"(?:从|分析|考虑|评估)(.{2,20}?)(?:角度|维度|层面|方面)",
            ),
            # 识别建议或示例
            "examples": re.compile(r"(?:例如|such as|including|比如)[:：]\s*(.+?)(?:\n|$)", re.IGNORECASE),
        }

    async def extract_from_expert_output(
        self, expert_output: str, project_type: str, expert_role: str, session_id: str
    ) -> List[ExtractedDimension]:
        """
        从专家输出中提取维度

        Args:
            expert_output: 专家分析输出文本
            project_type: 项目类型
            expert_role: 专家角色
            session_id: 会话ID

        Returns:
            提取的维度候选列表
        """
        logger.info(f" 开始从 {expert_role} 的输出中提取维度 (项目类型: {project_type})")

        # 第1步：规则匹配
        pattern_matches = self._apply_pattern_matching(expert_output)
        logger.debug(f" 规则匹配结果: {len(pattern_matches)} 个模式匹配")

        # 第2步：基于规则构建候选（不依赖LLM）
        rule_candidates = self._build_candidates_from_patterns(pattern_matches, project_type, expert_role)

        # 第3步：如果启用LLM，进行深度分析（目前跳过）
        if self.enable_llm:
            llm_candidates = await self._llm_extract_dimensions(
                expert_output=expert_output,
                project_type=project_type,
                expert_role=expert_role,
                pattern_hints=pattern_matches,
            )
            all_candidates = rule_candidates + llm_candidates
        else:
            all_candidates = rule_candidates

        # 第4步：去重和质量过滤
        candidates = self._deduplicate_and_filter(all_candidates)

        # 第5步：打分和排序
        scored_candidates = self._score_candidates(candidates, expert_output)

        logger.info(f" 提取到 {len(scored_candidates)} 个候选维度")
        return scored_candidates

    def _apply_pattern_matching(self, text: str) -> Dict[str, List[str]]:
        """应用正则表达式模式"""
        matches = {}
        for pattern_name, pattern in self.patterns.items():
            found = pattern.findall(text)
            if found:
                matches[pattern_name] = found
                logger.debug(f"  • {pattern_name}: 找到 {len(found)} 个匹配")
        return matches

    def _build_candidates_from_patterns(
        self, pattern_matches: Dict[str, List[str]], project_type: str, expert_role: str
    ) -> List[ExtractedDimension]:
        """基于规则匹配结果构建候选维度"""
        candidates = []

        # 从问题中提取维度
        how_questions = pattern_matches.get("how_questions", [])
        whether_questions = pattern_matches.get("whether_questions", [])

        for question in how_questions[:3]:  # 限制数量
            # 简单启发式：从问题中提取关键词作为维度名
            name = self._extract_dimension_name_from_question(question)
            if name:
                candidate = ExtractedDimension(
                    name=name,
                    category="extracted_from_expert",  # 临时分类
                    description=f"基于专家问题提取: {question[:100]}",
                    ask_yourself=question,
                    examples="待补充",
                    confidence=0.6,  # 规则提取的置信度较低
                    source_context=question,
                    project_type=project_type,
                )
                candidates.append(candidate)

        return candidates

    def _extract_dimension_name_from_question(self, question: str) -> str | None:
        """从问题中提取维度名称（简单启发式）"""
        # 移除"如何"、"怎样"等词
        cleaned = re.sub(r"(如何|怎样|怎么|是否|能否|会不会)", "", question)
        # 提取前15个字符作为名称
        name = cleaned.strip()[:15]
        if len(name) >= 4:
            return name
        return None

    async def _llm_extract_dimensions(
        self, expert_output: str, project_type: str, expert_role: str, pattern_hints: Dict[str, List[str]]
    ) -> List[ExtractedDimension]:
        """使用LLM进行深度语义提取"""
        try:
            from ..services.llm_factory import LLMFactory

            llm = LLMFactory.create_llm(model_name="deepseek-chat", temperature=0.3)

            # 构建提取 prompt
            hints_text = ""
            if pattern_hints:
                hints_text = "\n已通过规则匹配发现的线索:\n"
                for ptype, matches in pattern_hints.items():
                    hints_text += f"- {ptype}: {', '.join(m[:50] for m in matches[:3])}\n"

            prompt = f"""从以下设计专家的分析输出中，提取可复用的分析维度。

专家角色: {expert_role}
项目类型: {project_type}
{hints_text}

专家输出（截取前2000字）:
{expert_output[:2000]}

请提取3-5个有价值的分析维度，每个维度用JSON格式输出:
```json
[
  {{
    "name": "维度名称（简洁，4-15字）",
    "category": "分类（如 spatial_experience, material_system, user_behavior, business_logic, environmental_response）",
    "description": "维度描述（50-150字）",
    "ask_yourself": "引导性问题（以？结尾）",
    "examples": "具体示例（逗号分隔，2-4个）"
  }}
]
```

要求:
- 只提取具有跨项目复用价值的维度，不要提取过于具体的项目细节
- 维度应该是分析角度，不是结论
- 置信度高的维度优先"""

            response = await llm.ainvoke(prompt)
            response_text = response.content if hasattr(response, "content") else str(response)

            # 解析 JSON
            json_match = re.search(r"\[[\s\S]*\]", response_text)
            if not json_match:
                logger.debug(" [LLM提取] 未找到JSON格式输出")
                return []

            dims_data = json.loads(json_match.group())
            candidates = []
            for d in dims_data:
                if not isinstance(d, dict) or not d.get("name"):
                    continue
                candidates.append(
                    ExtractedDimension(
                        name=d["name"][:15],
                        category=d.get("category", "llm_extracted"),
                        description=d.get("description", "")[:200],
                        ask_yourself=d.get("ask_yourself", ""),
                        examples=d.get("examples", ""),
                        confidence=0.75,  # LLM 提取置信度高于规则
                        source_context=f"LLM extracted from {expert_role}",
                        project_type=project_type,
                    )
                )

            logger.info(f" [LLM提取] 从 {expert_role} 输出中提取 {len(candidates)} 个维度")
            return candidates

        except Exception as e:
            logger.warning(f" [LLM提取] 失败: {e}")
            return []

    def _deduplicate_and_filter(self, candidates: List[ExtractedDimension]) -> List[ExtractedDimension]:
        """去重和质量过滤"""
        seen_names = set()
        filtered = []

        for cand in candidates:
            name = cand.name.lower()

            # 去重
            if name in seen_names:
                continue
            seen_names.add(name)

            # 质量过滤：置信度阈值
            if cand.confidence < 0.5:
                continue

            filtered.append(cand)

        return filtered

    def _score_candidates(self, candidates: List[ExtractedDimension], expert_output: str) -> List[ExtractedDimension]:
        """对候选维度打分"""
        # 简单打分：检查维度名在输出中的出现频率
        for cand in candidates:
            # 统计名称中关键词的出现次数
            keywords = cand.name.split()
            count = sum(expert_output.lower().count(kw.lower()) for kw in keywords)

            # 根据出现频率调整置信度
            if count >= 3:
                cand.confidence = min(cand.confidence + 0.2, 1.0)
            elif count >= 2:
                cand.confidence = min(cand.confidence + 0.1, 1.0)

        return sorted(candidates, key=lambda x: x.confidence, reverse=True)

    def extract_from_text_sync(
        self, text: str, project_type: str = "unknown", expert_role: str = "unknown"
    ) -> List[ExtractedDimension]:
        """同步版本的提取方法（用于测试）"""
        import asyncio

        return asyncio.run(
            self.extract_from_expert_output(
                expert_output=text, project_type=project_type, expert_role=expert_role, session_id="test"
            )
        )
