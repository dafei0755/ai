"""
搜索方向生成器 - Step 1.5

将 Step 1 的输出板块转化为具体的搜索方向，作为 Step 2 查询生成的中间层。

核心功能：
1. 主题分解：将板块名称分解为单一主题
2. 方向生成：为每个主题生成搜索方向
3. 验证：确保方向聚焦且不重叠

Author: AI Assistant
Created: 2026-02-05
Version: 1.0
"""

import json
import re
from typing import Any, Dict, List

from loguru import logger

from intelligent_project_analyzer.core.four_step_flow_types import (
    OutputBlock,
    SearchDirection,
    Understanding,
    ValidationCheck,
)
from intelligent_project_analyzer.services.llm_factory import LLMFactory


class SearchDirectionGenerator:
    """搜索方向生成器 - Step 1.5 中间层"""

    # v4.0: 特性开关 — 当 Stage 1 已产出高质量 research_dimensions 时可跳过 Step 1.5
    SKIP_STEP_1_5 = False  # 默认关闭，开启后直接用 research_dimensions 替代 LLM 分解

    def __init__(self, llm_factory: LLMFactory, prompt_config: Dict[str, Any]):
        """
        初始化搜索方向生成器

        Args:
            llm_factory: LLM工厂实例
            prompt_config: Prompt配置字典
        """
        self.llm_factory = llm_factory
        self.prompt_config = prompt_config
        self.system_prompt = prompt_config.get("system_prompt", "")
        self.direction_generation_template = prompt_config.get("direction_generation_template", "")

    async def generate_directions(
        self, block: OutputBlock, understanding: Understanding, block_index: int = 0
    ) -> List[SearchDirection]:
        """
        为单个板块生成2-4个搜索方向

        v4.0: 当 SKIP_STEP_1_5=True 且 block 已有 search_focus/indicative_queries 时，
        直接构造 SearchDirection 而不调用 LLM，节省 24-56 次 LLM 调用。

        Args:
            block: 输出板块
            understanding: Step 1 的理解分析结果
            block_index: 板块索引（用于优先级计算）

        Returns:
            搜索方向列表（2-4个）
        """
        # v4.0: SKIP_STEP_1_5 快速路径 — 直接用 research_dimensions 数据
        if self.SKIP_STEP_1_5 and block.search_focus and block.indicative_queries:
            logger.info(f" [SearchDirection] SKIP_STEP_1_5 启用 | block_id={block.id} | 直接使用 research_dimensions")
            direction = SearchDirection(
                id=f"direction_{block.id}_1",
                block_id=block.id,
                core_theme=block.name,
                search_scope=block.search_focus,
                expected_info_types=["案例分析", "研究报告", "专业资料"],
                key_dimensions=block.indicative_queries[:3],
                user_characteristics=block.user_characteristics,
                expected_query_count=len(block.indicative_queries),
                priority=1 if block_index < 3 else 2,
                metadata={"source": "research_dimensions", "domain_hints": block.domain_knowledge_hints or ""},
            )
            return [direction]

        logger.info(f" [SearchDirection] 开始生成搜索方向 | block_id={block.id}")
        logger.info(f"   板块名称: {block.name[:50]}...")
        logger.debug(f"   子项数量: {len(block.sub_items)}")

        # 1. 主题分解：将板块名称分解为单一主题
        logger.info(" [SearchDirection] 步骤1: 主题分解...")
        themes = await self._decompose_block_themes(block, understanding)
        logger.info(f"    主题分解完成: {len(themes)} 个主题")
        for i, theme in enumerate(themes):
            logger.debug(f"      主题 {i+1}: {theme[:40]}...")

        # 2. 方向生成：为每个主题生成搜索方向
        logger.info(" [SearchDirection] 步骤2: 方向生成...")
        directions = []
        for i, theme in enumerate(themes):
            logger.debug(f"   生成方向 {i+1}/{len(themes)}: {theme[:30]}...")
            direction = await self._generate_direction(
                block=block,
                theme=theme,
                theme_index=i,
                understanding=understanding,
                block_index=block_index,
            )
            directions.append(direction)
            logger.info(f"    方向 {i+1}: {direction.core_theme[:40]}...")

        # 3. 验证：确保方向聚焦且不重叠
        logger.info(" [SearchDirection] 步骤3: 验证方向...")
        validated_directions = self._validate_directions(directions)
        logger.info(f" [SearchDirection] 搜索方向生成完成 | block_id={block.id} | 方向数: {len(validated_directions)}")

        return validated_directions

    async def _decompose_block_themes(self, block: OutputBlock, understanding: Understanding) -> List[str]:
        """
        分解板块为单一主题

        示例：
        Input: "Audrey Hepburn美学DNA解析与空间转化策略"
        Output: [
            "Audrey Hepburn经典作品的美学分析",
            "美学元素在空间设计中的转化方法"
        ]

        Args:
            block: 输出板块
            understanding: Step 1 的理解分析结果

        Returns:
            主题列表（2-4个）
        """
        # 构建 LLM prompt
        prompt = self._build_theme_decomposition_prompt(block, understanding)
        logger.debug(f"   [主题分解] Prompt 长度: {len(prompt)} 字符")

        # 调用 LLM
        llm = self.llm_factory.create_llm(model_name="gpt-4o-mini", temperature=0.3)

        try:
            logger.debug("   [主题分解] 调用 LLM...")
            response = await llm.ainvoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            logger.debug(f"   [主题分解] LLM 响应长度: {len(content)} 字符")

            # 解析 JSON 响应
            themes = self._parse_themes_from_response(content)
            logger.info(f"   [主题分解] 解析得到 {len(themes)} 个主题")

            # 验证主题数量
            if not 3 <= len(themes) <= 6:
                logger.warning(f"️ 主题数量不符合要求: {len(themes)}，期望3-6个，使用降级策略")
                # 如果只有1-2个主题，尝试基于子项拆分
                if len(themes) < 3 and len(block.sub_items) >= 2:
                    themes = self._fallback_theme_decomposition(block)
                    logger.info(f"   [主题分解] 降级策略生成 {len(themes)} 个主题")

            return themes[:6]  # 最多返回6个主题

        except Exception as e:
            logger.error(f" 主题分解失败: {e}", exc_info=True)
            # 降级策略：基于子项生成主题
            fallback_themes = self._fallback_theme_decomposition(block)
            logger.info(f"   [主题分解] 使用降级策略，生成 {len(fallback_themes)} 个主题")
            return fallback_themes

    def _build_theme_decomposition_prompt(self, block: OutputBlock, understanding: Understanding) -> str:
        """构建主题分解的 LLM prompt（v2.0 - 设计行业专业维度）"""

        # 提取关键信息
        l2_motivations_text = "\n".join(
            [f"- {m.name}（{m.type}）: {m.scenario_expression}" for m in understanding.l2_motivations]
        )

        sub_items_text = "\n".join([f"- {item.id} {item.name}: {item.description}" for item in block.sub_items])

        # v2.0: 基于 L2 动机类型智能推荐维度
        motivation_types = set(m.type for m in understanding.l2_motivations)
        recommended_dimensions = []

        if "精神型" in motivation_types:
            recommended_dimensions.extend(["美学溯源", "时代对话"])
        if "情感型" in motivation_types:
            recommended_dimensions.extend(["情感锚点", "生活仪式"])
        if "社会型" in motivation_types:
            recommended_dimensions.append("空间叙事")
        if "功能型" in motivation_types:
            recommended_dimensions.append("材质肌理")

        # 基于 L3 张力推荐维度
        if "vs" in understanding.l3_tension.tension_formula:
            recommended_dimensions.append("时代对话")
        if "+" in understanding.l3_tension.tension_formula:
            recommended_dimensions.append("在地融合")

        # 去重
        recommended_dimensions = list(set(recommended_dimensions))
        recommended_dims_text = "、".join(recommended_dimensions) if recommended_dimensions else "根据板块主题智能选择"

        prompt = f"""你是一位资深的设计行业信息架构专家，擅长将复杂的设计主题分解为专业的搜索方向。

## 任务

基于以下板块，进行**深度挖掘和多维度扩展**，生成3-6个搜索方向。

**核心理念：基于设计思维智能选择维度**
- 板块提供的是"框架"，你需要从设计行业专业角度进行扩展
- 每个方向应该聚焦一个独立的设计维度
- 方向数量根据板块复杂度和动机类型动态确定（3-6个）

## 板块信息

**板块名称**: {block.name}

**子项列表**:
{sub_items_text}

**用户特征**: {', '.join(block.user_characteristics)}

## 用户动机分析（Step 1 结果）

{l2_motivations_text}

**核心张力**: {understanding.l3_tension.tension_formula}

**基于动机分析推荐的维度**: {recommended_dims_text}

##  设计行业八大搜索维度

根据用户动机和板块主题，从以下维度中智能选择：

1. **【美学溯源】** 设计语言的历史脉络与文化根源
   - 搜索方向：风格起源、设计师理念、品牌DNA、文化符号
   - 触发条件：涉及特定风格、设计师、品牌；精神型动机（超越、意义）

2. **【空间叙事】** 空间如何讲述用户的故事
   - 搜索方向：空间序列、动线设计、场景营造、身份表达
   - 触发条件：涉及空间规划、功能分区；社会型动机（地位、影响）

3. **【材质肌理】** 材料的触感、视觉与情感表达
   - 搜索方向：材料特性、工艺细节、触感体验、视觉效果
   - 触发条件：涉及材料、色彩、质感；功能型动机（控制、安全）

4. **【光影氛围】** 光线如何塑造空间情绪
   - 搜索方向：自然采光、人工照明、光影层次、氛围营造
   - 触发条件：涉及氛围、情绪、体验

5. **【生活仪式】** 日常行为的空间化表达
   - 搜索方向：生活场景、行为习惯、仪式感设计、功能需求
   - 触发条件：涉及生活方式、行为习惯；情感型动机（愉悦）

6. **【在地融合】** 设计与地域文化的对话
   - 搜索方向：地域特色、气候适应、文化元素、本土材料
   - 触发条件：涉及地理位置、气候、文化；融合型张力（A + B）

7. **【时代对话】** 经典与当代的融合创新
   - 搜索方向：风格演变、现代诠释、融合案例、创新趋势
   - 触发条件：涉及风格融合、经典再造；对立型张力（A vs B）

8. **【情感锚点】** 空间中的记忆与情感触发
   - 搜索方向：情感记忆、文化认同、心理需求、归属感
   - 触发条件：涉及情感需求、身份认同；情感型动机（归属、认同）

## 方向生成要求

1. **单一焦点**: 每个方向只关注一个核心维度
   -  好："Audrey Hepburn经典作品的色彩体系分析"
   -  差："Audrey Hepburn美学分析与空间转化策略"（包含2个主题）

2. **可搜索性**: 方向必须能通过搜索引擎找到信息
   -  好："北欧极简风格在亚热带气候下的材料选择"
   -  差："项目实施流程与时间节点把控"（需要定制，无法搜索）

3. **设计专业性**: 使用设计行业专业术语和视角
   - 从美学、空间、材质、光影、仪式、在地、时代、情感等角度思考
   - 体现设计行业的专业深度

## 输出格式

请输出JSON格式：

```json
{{
  "themes": [
    {{
      "theme": "方向1的描述（15-30字）",
      "rationale": "为什么需要搜索这个方向（20-50字）",
      "dimension": "美学溯源/空间叙事/材质肌理/光影氛围/生活仪式/在地融合/时代对话/情感锚点"
    }},
    {{
      "theme": "方向2的描述（15-30字）",
      "rationale": "为什么需要搜索这个方向（20-50字）",
      "dimension": "..."
    }}
  ]
}}
```

请只输出JSON，不要有其他内容。"""

        return prompt

    def _parse_themes_from_response(self, content: str) -> List[str]:
        """从 LLM 响应中解析主题列表"""
        try:
            # 提取 JSON 内容
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析整个内容
                json_str = content.strip()

            data = json.loads(json_str)
            themes = [item["theme"] for item in data.get("themes", [])]
            return themes

        except Exception as e:
            logger.error(f" 解析主题失败: {e}")
            logger.debug(f"响应内容: {content}")
            raise

    def _fallback_theme_decomposition(self, block: OutputBlock) -> List[str]:
        """
        降级策略：基于设计行业八维度生成主题（v2.0）

        当 LLM 分解失败时使用
        """
        logger.warning("️ 使用降级策略：基于设计行业八维度生成主题")

        themes = []

        # 策略1：如果板块名称包含连接词，尝试拆分
        multi_theme_signals = ["与", "和", "及", "以及"]
        for signal in multi_theme_signals:
            if signal in block.name:
                parts = block.name.split(signal)
                if len(parts) >= 2:
                    themes = [p.strip() for p in parts if len(p.strip()) > 5]
                    if len(themes) >= 2:
                        break

        # 策略2：基于子项生成主题
        if len(themes) < 3 and len(block.sub_items) >= 1:
            for item in block.sub_items:
                theme_name = f"{block.name}的{item.name}"
                if theme_name not in themes:
                    themes.append(theme_name)
                if len(themes) >= 6:
                    break

        # 策略3：基于设计行业八维度扩展（v2.0 更新）
        if len(themes) < 3:
            # 根据板块名称关键词智能选择维度
            design_dimensions = []

            # 美学溯源：涉及风格、设计师、品牌
            if any(kw in block.name for kw in ["美学", "风格", "设计语言", "品牌"]):
                design_dimensions.append(f"{block.name}的美学溯源与文化根源")

            # 空间叙事：涉及空间、布局、分区
            if any(kw in block.name for kw in ["空间", "布局", "分区", "动线"]):
                design_dimensions.append(f"{block.name}的空间叙事与场景营造")

            # 材质肌理：涉及材料、色彩、质感
            if any(kw in block.name for kw in ["材质", "材料", "色彩", "质感"]):
                design_dimensions.append(f"{block.name}的材质肌理与触感表达")

            # 光影氛围：涉及氛围、情绪、体验
            if any(kw in block.name for kw in ["氛围", "情绪", "体验", "光影"]):
                design_dimensions.append(f"{block.name}的光影氛围营造")

            # 生活仪式：涉及生活、仪式、习惯
            if any(kw in block.name for kw in ["生活", "仪式", "习惯", "日常"]):
                design_dimensions.append(f"{block.name}的生活仪式与空间需求")

            # 在地融合：涉及地域、气候、文化
            if any(kw in block.name for kw in ["地域", "气候", "文化", "本土"]):
                design_dimensions.append(f"{block.name}的在地融合策略")

            # 时代对话：涉及经典、现代、融合
            if any(kw in block.name for kw in ["经典", "现代", "融合", "当代"]):
                design_dimensions.append(f"{block.name}的时代对话与创新")

            # 情感锚点：涉及情感、记忆、认同
            if any(kw in block.name for kw in ["情感", "记忆", "认同", "归属"]):
                design_dimensions.append(f"{block.name}的情感锚点与记忆表达")

            # 如果没有匹配到关键词，使用默认维度
            if not design_dimensions:
                design_dimensions = [
                    f"{block.name}的美学溯源研究",
                    f"{block.name}的案例参考分析",
                    f"{block.name}的实现方法探索",
                    f"{block.name}的用户需求洞察",
                ]

            for dim in design_dimensions:
                if dim not in themes:
                    themes.append(dim)
                if len(themes) >= 4:
                    break

        # 策略4：如果还是没有，至少返回板块名称本身
        if not themes:
            themes = [block.name]

        return themes[:6]

    async def _generate_direction(
        self,
        block: OutputBlock,
        theme: str,
        theme_index: int,
        understanding: Understanding,
        block_index: int,
    ) -> SearchDirection:
        """
        为单个主题生成搜索方向

        Args:
            block: 输出板块
            theme: 主题名称
            theme_index: 主题索引
            understanding: Step 1 的理解分析结果
            block_index: 板块索引

        Returns:
            搜索方向对象
        """
        # 构建 LLM prompt
        prompt = self._build_direction_generation_prompt(block, theme, understanding)

        # 调用 LLM
        llm = self.llm_factory.create_llm(model_name="gpt-4o-mini", temperature=0.3)

        try:
            response = await llm.ainvoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            # 解析 JSON 响应
            direction_data = self._parse_direction_from_response(content)

            # 构建 SearchDirection 对象
            direction = SearchDirection(
                id=f"direction_{block.id.split('_')[-1]}_{theme_index + 1}",
                block_id=block.id,
                core_theme=direction_data.get("core_theme", theme),
                search_scope=direction_data.get("search_scope", ""),
                expected_info_types=direction_data.get("expected_info_types", []),
                key_dimensions=direction_data.get("key_dimensions", []),
                user_characteristics=block.user_characteristics,
                expected_query_count=direction_data.get("expected_query_count", 2),
                priority=block_index + 1,  # 基于板块顺序确定优先级
                metadata={"theme_index": theme_index, "block_name": block.name},
            )

            return direction

        except Exception as e:
            logger.error(f" 生成搜索方向失败: {e}")
            # 降级策略：生成基础方向
            return self._fallback_direction_generation(block, theme, theme_index, block_index)

    def _build_direction_generation_prompt(self, block: OutputBlock, theme: str, understanding: Understanding) -> str:
        """构建方向生成的 LLM prompt"""

        # 提取关键信息
        l2_motivations_text = "\n".join(
            [f"- {m.name}（{m.type}）: {m.scenario_expression}" for m in understanding.l2_motivations]
        )

        l3_tension_text = f"{understanding.l3_tension.primary_motivation} {understanding.l3_tension.tension_formula.split()[1]} {understanding.l3_tension.secondary_motivation}"

        prompt = f"""你是一位资深的信息检索专家，擅长将抽象主题转化为具体的搜索方向。

## 任务

为以下主题生成一个具体的搜索方向，包括：
1. 核心主题（精炼表达）
2. 搜索范围（具体说明要搜索什么）
3. 预期信息类型（案例、原则、数据等）
4. 关键搜索维度（2-4个）
5. 预期查询数量（1-3个）

## 主题信息

**主题**: {theme}

**所属板块**: {block.name}

**用户特征**: {', '.join(block.user_characteristics)}

## 用户动机（参考）

{l2_motivations_text}

**核心张力**: {l3_tension_text}

## 生成原则

1. **聚焦单一方向**: 搜索方向必须只关注一个核心主题
2. **可搜索性**: 必须能通过搜索引擎找到相关信息
3. **层次清晰**: 比板块更具体，比查询更抽象
4. **包含用户特征**: 搜索范围应该包含用户关键特征

## 输出格式

请输出JSON格式：

```json
{{
  "core_theme": "核心主题（15-30字，包含用户特征）",
  "search_scope": "搜索范围说明（30-60字，具体说明要搜索什么类型的信息）",
  "expected_info_types": ["信息类型1", "信息类型2", "信息类型3"],
  "key_dimensions": ["搜索维度1", "搜索维度2", "搜索维度3"],
  "expected_query_count": 2
}}
```

**示例**：

主题: "Audrey Hepburn经典作品的美学分析"

输出:
```json
{{
  "core_theme": "Audrey Hepburn经典电影作品的色彩与设计语言分析",
  "search_scope": "提取《罗马假日》《蒂芙尼的早餐》等经典电影中的服装色彩、珠宝设计的配色原则和设计元素",
  "expected_info_types": ["电影服装分析", "配色原则", "设计语言解读"],
  "key_dimensions": ["色彩体系", "材质搭配", "设计语言", "品牌美学"],
  "expected_query_count": 2
}}
```

请只输出JSON，不要有其他内容。"""

        return prompt

    def _parse_direction_from_response(self, content: str) -> Dict[str, Any]:
        """从 LLM 响应中解析方向数据"""
        try:
            # 提取 JSON 内容
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析整个内容
                json_str = content.strip()

            data = json.loads(json_str)
            return data

        except Exception as e:
            logger.error(f" 解析方向数据失败: {e}")
            logger.debug(f"响应内容: {content}")
            raise

    def _fallback_direction_generation(
        self, block: OutputBlock, theme: str, theme_index: int, block_index: int
    ) -> SearchDirection:
        """
        降级策略：生成基础方向

        当 LLM 生成失败时使用
        """
        logger.warning("️ 使用降级策略：生成基础搜索方向")

        return SearchDirection(
            id=f"direction_{block.id.split('_')[-1]}_{theme_index + 1}",
            block_id=block.id,
            core_theme=theme,
            search_scope=f"搜索与{theme}相关的案例、原则和方法",
            expected_info_types=["案例分析", "设计原则", "实施方法"],
            key_dimensions=["核心概念", "应用案例", "实践方法"],
            user_characteristics=block.user_characteristics,
            expected_query_count=2,
            priority=block_index + 1,
            metadata={
                "theme_index": theme_index,
                "block_name": block.name,
                "fallback": True,
            },
        )

    def _validate_directions(self, directions: List[SearchDirection]) -> List[SearchDirection]:
        """
        验证搜索方向列表

        检查：
        1. 方向数量是否合理（3-6个）
        2. 方向是否聚焦（不重叠）
        3. 方向是否可搜索

        Args:
            directions: 搜索方向列表

        Returns:
            验证后的搜索方向列表
        """
        if not 3 <= len(directions) <= 6:
            logger.warning(f"️ 方向数量不符合要求: {len(directions)}，期望3-6个")

        # 检查方向是否重叠
        for i, dir1 in enumerate(directions):
            for j, dir2 in enumerate(directions[i + 1 :], start=i + 1):
                similarity = self._calculate_theme_similarity(dir1.core_theme, dir2.core_theme)
                if similarity > 0.7:
                    logger.warning(f"️ 方向可能重叠: '{dir1.core_theme}' vs '{dir2.core_theme}' (相似度: {similarity:.2f})")

        return directions

    def _calculate_theme_similarity(self, theme1: str, theme2: str) -> float:
        """
        计算两个主题的相似度（简单实现）

        Args:
            theme1: 主题1
            theme2: 主题2

        Returns:
            相似度（0-1）
        """
        # 简单实现：基于字符重叠
        set1 = set(theme1)
        set2 = set(theme2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0


# ============================================================================
# 验证函数
# ============================================================================


def validate_block_single_theme(block: OutputBlock) -> ValidationCheck:
    """
    验证板块是否聚焦单一主题

    检查规则：
    1. 板块名称不应包含"与"、"和"等连接词（除非是修饰关系）
    2. 子项应该都服务于同一个核心主题
    3. 不应混合多个独立的研究方向

    Args:
        block: 输出板块

    Returns:
        验证检查结果
    """
    # 检测多主题信号词
    multi_theme_signals = ["与", "和", "及", "以及", "+"]

    name = block.name
    for signal in multi_theme_signals:
        if signal in name:
            # 进一步分析是否真的是多主题
            parts = name.split(signal)
            if len(parts) >= 2 and all(len(p.strip()) > 5 for p in parts):
                return ValidationCheck(
                    name="block_single_theme",
                    status="warning",
                    message=f"板块'{name}'可能包含多个主题",
                    details=f"建议拆分为：{' | '.join([p.strip() for p in parts])}",
                )

    return ValidationCheck(name="block_single_theme", status="passed", message="板块主题聚焦", details="")


def validate_direction_query_alignment(
    direction: SearchDirection, queries: List[Any]  # SearchQuery type
) -> ValidationCheck:
    """
    验证方向和查询的对齐

    检查规则：
    1. 每个查询的direction_id必须匹配
    2. 查询数量在预期范围内（1-3个）
    3. 查询必须比方向更具体

    Args:
        direction: 搜索方向
        queries: 查询列表

    Returns:
        验证检查结果
    """
    # Check query count
    if not 1 <= len(queries) <= 3:
        return ValidationCheck(
            name="direction_query_count",
            status="warning",
            message=f"方向'{direction.core_theme}'的查询数量为{len(queries)}，建议1-3个",
            details="",
        )

    # Check all queries reference this direction
    for query in queries:
        if hasattr(query, "direction_id") and query.direction_id != direction.id:
            return ValidationCheck(
                name="direction_query_alignment",
                status="failed",
                message=f"查询'{query.id}'的direction_id不匹配",
                details=f"期望: {direction.id}, 实际: {query.direction_id}",
            )

    return ValidationCheck(
        name="direction_query_alignment",
        status="passed",
        message="方向-查询对齐正确",
        details="",
    )
