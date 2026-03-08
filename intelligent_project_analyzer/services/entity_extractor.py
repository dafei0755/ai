"""
Entity Extractor - v7.270

ℹ️ NOTE (v9.1): 该组件不再作为 P1 需求分析子组件被调用，
但仍被 async_post_processor 用于异步实体提取。非死代码。

Extract 6 types of structured entities from requirements analysis output:
1. Brand entities (品牌实体)
2. Location entities (地点实体)
3. Style entities (风格实体)
4. Scene entities (场景实体)
5. Competitor entities (竞品实体)
6. Person entities (人物实体)

Strategy:
- Primary: LLM-based extraction (more accurate, context-aware)
- Fallback: Rule-based extraction (keyword matching, pattern recognition)

Author: AI Assistant
Date: 2026-01-25
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from loguru import logger


@dataclass
class EntityExtractionResult:
    """Entity extraction result structure"""

    brand_entities: List[Dict[str, Any]] = field(default_factory=list)  # 品牌实体
    location_entities: List[Dict[str, Any]] = field(default_factory=list)  # 地点实体
    style_entities: List[Dict[str, Any]] = field(default_factory=list)  # 风格实体
    scene_entities: List[Dict[str, Any]] = field(default_factory=list)  # 场景实体
    competitor_entities: List[Dict[str, Any]] = field(default_factory=list)  # 竞品实体
    person_entities: List[Dict[str, Any]] = field(default_factory=list)  # 人物实体

    extraction_method: str = "unknown"  # "llm" or "rule_based"
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "brand": self.brand_entities,
            "location": self.location_entities,
            "style": self.style_entities,
            "scene": self.scene_entities,
            "competitor": self.competitor_entities,
            "person": self.person_entities,
            "extraction_method": self.extraction_method,
            "confidence": self.confidence,
        }

    def total_entities(self) -> int:
        """Count total entities extracted"""
        return (
            len(self.brand_entities)
            + len(self.location_entities)
            + len(self.style_entities)
            + len(self.scene_entities)
            + len(self.competitor_entities)
            + len(self.person_entities)
        )


class EntityExtractor:
    """Extract structured entities from requirements analysis"""

    def __init__(self, llm_model=None):
        """
        Initialize entity extractor

        Args:
            llm_model: LLM model for extraction (optional, will use rule-based if None)
        """
        self.llm_model = llm_model

    def extract_entities(self, structured_data: Dict[str, Any], user_input: str) -> EntityExtractionResult:
        """
        Extract entities from requirements analysis output

        Strategy:
        1. Try LLM-based extraction first (more accurate)
        2. Fall back to rule-based extraction if LLM fails or unavailable

        Args:
            structured_data: Requirements analysis output
            user_input: Original user input

        Returns:
            EntityExtractionResult with 6 entity types
        """
        # Try LLM extraction if model available
        if self.llm_model:
            try:
                logger.info(" [Entity Extraction] Using LLM-based extraction")
                return self._extract_with_llm(structured_data, user_input)
            except Exception as e:
                logger.warning(f"️ [Entity Extraction] LLM extraction failed: {e}")
                logger.info(" [Entity Extraction] Falling back to rule-based extraction")

        # Fallback to rule-based extraction
        return self._extract_with_rules(structured_data, user_input)

    def _extract_with_llm(self, structured_data: Dict[str, Any], user_input: str) -> EntityExtractionResult:
        """
        Use LLM to extract entities with context understanding

        Args:
            structured_data: Requirements analysis output
            user_input: Original user input

        Returns:
            EntityExtractionResult
        """
        # Build extraction prompt
        prompt = self._build_extraction_prompt(structured_data, user_input)

        # Call LLM
        from langchain_core.messages import HumanMessage

        messages = [HumanMessage(content=prompt)]
        response = self.llm_model.invoke(messages)

        # Parse response
        result = self._parse_llm_response(response.content)
        result.extraction_method = "llm"

        logger.info(f" [Entity Extraction] LLM extracted {result.total_entities()} entities")

        return result

    def _build_extraction_prompt(self, structured_data: Dict[str, Any], user_input: str) -> str:
        """Build prompt for LLM entity extraction"""

        # Extract relevant fields from structured_data
        project_task = structured_data.get("project_task", "")
        character_narrative = structured_data.get("character_narrative", "")
        physical_context = structured_data.get("physical_context", "")
        inspiration_references = structured_data.get("inspiration_references", "")

        prompt = f"""
从以下需求分析中提取6类结构化实体。

**用户原始输入**:
{user_input}

**项目任务**:
{project_task}

**人物叙事**:
{character_narrative}

**物理环境**:
{physical_context}

**灵感参考**:
{inspiration_references}

---

请提取以下6类实体，每类实体包含：name（名称）、description（描述）、source（来源字段）

**1. 品牌实体 (brand_entities)**
- 提取所有提到的品牌名称（家居品牌、设计品牌、竞品品牌等）
- 示例：HAY、IKEA、Muji、Herman Miller

**2. 地点实体 (location_entities)**
- 提取所有地理位置信息（国家、城市、区域、具体地点）
- 包括气候、海拔、建筑风格等地域特征
- 示例：四川峨眉山七里坪、北欧、日本京都

**3. 风格实体 (style_entities)**
- 提取所有设计风格、美学流派、艺术风格
- 示例：北欧简约、侘寂美学、工业风、现代主义

**4. 场景实体 (scene_entities)**
- 提取项目类型、使用场景、商业模式
- 示例：民宿、咖啡厅、办公室、住宅

**5. 竞品实体 (competitor_entities)**
- 提取提到的竞品案例、对标项目、参考案例
- 示例：莫干山裸心谷、青城山六善酒店

**6. 人物实体 (person_entities)**
- 提取提到的设计师、创始人、艺术家、历史人物
- 示例：Rolf Hay、原研哉、隈研吾

---

**输出格式**（纯JSON，不要markdown代码块）:
{{
  "brand_entities": [
    {{"name": "HAY", "description": "丹麦家居品牌，以民主设计和简约现代著称", "source": "user_input"}},
    ...
  ],
  "location_entities": [
    {{"name": "四川峨眉山七里坪", "description": "海拔1300米，亚热带湿润气候，多雾", "source": "user_input"}},
    ...
  ],
  "style_entities": [
    {{"name": "北欧简约", "description": "简洁线条、功能主义、自然材料", "source": "inspiration_references"}},
    ...
  ],
  "scene_entities": [
    {{"name": "民宿室内设计", "description": "设计驱动型民宿，目标客群为中高端游客", "source": "user_input"}},
    ...
  ],
  "competitor_entities": [
    {{"name": "莫干山裸心谷", "description": "融合自然与现代设计的高端民宿", "source": "inspiration_references"}},
    ...
  ],
  "person_entities": [
    {{"name": "Rolf Hay", "description": "HAY品牌创始人", "source": "inspiration_references"}},
    ...
  ]
}}

**注意**:
- 如果某类实体不存在，返回空数组 []
- description 要具体，包含关键特征
- source 标注实体来源（user_input, project_task, character_narrative, physical_context, inspiration_references）
"""

        return prompt

    def _parse_llm_response(self, response_content: str) -> EntityExtractionResult:
        """
        Parse LLM response to extract entities

        Args:
            response_content: LLM response text

        Returns:
            EntityExtractionResult
        """
        try:
            # Try to extract JSON from response
            json_str = self._extract_json_from_text(response_content)

            if not json_str:
                logger.warning("️ [Entity Extraction] No JSON found in LLM response")
                return EntityExtractionResult(extraction_method="llm", confidence=0.0)

            # Parse JSON
            data = json.loads(json_str)

            # Create result
            result = EntityExtractionResult(
                brand_entities=data.get("brand_entities", []),
                location_entities=data.get("location_entities", []),
                style_entities=data.get("style_entities", []),
                scene_entities=data.get("scene_entities", []),
                competitor_entities=data.get("competitor_entities", []),
                person_entities=data.get("person_entities", []),
                extraction_method="llm",
                confidence=0.9,  # High confidence for LLM extraction
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f" [Entity Extraction] JSON parse error: {e}")
            return EntityExtractionResult(extraction_method="llm", confidence=0.0)
        except Exception as e:
            logger.error(f" [Entity Extraction] Unexpected error: {e}")
            return EntityExtractionResult(extraction_method="llm", confidence=0.0)

    def _extract_json_from_text(self, text: str) -> str | None:
        """
        Extract JSON from text (handles markdown code blocks)

        Args:
            text: Text containing JSON

        Returns:
            JSON string or None
        """
        # Try to find JSON in markdown code block
        json_pattern = r"```json\s*\n(.*?)\n```"
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            return match.group(1)

        # Try to find JSON without markdown
        code_block_pattern = r"```\s*\n(\{.*?\})\n```"
        match = re.search(code_block_pattern, text, re.DOTALL)
        if match:
            return match.group(1)

        # Try to find raw JSON (first { to last })
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            return text[first_brace : last_brace + 1]

        return None

    def _extract_with_rules(self, structured_data: Dict[str, Any], user_input: str) -> EntityExtractionResult:
        """
        Rule-based entity extraction as fallback

        Uses keyword matching and pattern recognition

        Args:
            structured_data: Requirements analysis output
            user_input: Original user input

        Returns:
            EntityExtractionResult
        """
        logger.info(" [Entity Extraction] Using rule-based extraction")

        result = EntityExtractionResult(
            extraction_method="rule_based", confidence=0.6  # Lower confidence for rule-based
        )

        # Extract from user_input and structured_data
        all_text = f"{user_input} {structured_data.get('project_task', '')} {structured_data.get('character_narrative', '')} {structured_data.get('physical_context', '')} {structured_data.get('inspiration_references', '')}"

        # 1. Brand entities - look for brand keywords
        result.brand_entities = self._extract_brands(all_text, user_input)

        # 2. Location entities - look for place names
        result.location_entities = self._extract_locations(all_text, user_input)

        # 3. Style entities - look for style keywords
        result.style_entities = self._extract_styles(all_text, user_input)

        # 4. Scene entities - look for scene types
        result.scene_entities = self._extract_scenes(all_text, user_input)

        # 5. Competitor entities - look for competitor mentions
        result.competitor_entities = self._extract_competitors(all_text, user_input)

        # 6. Person entities - look for person names
        result.person_entities = self._extract_persons(all_text, user_input)

        logger.info(f" [Entity Extraction] Rule-based extracted {result.total_entities()} entities")

        return result

    def _extract_brands(self, text: str, user_input: str) -> List[Dict[str, Any]]:
        """Extract brand entities using keyword matching"""
        brands = []

        # Common brand patterns
        brand_keywords = [
            "HAY",
            "IKEA",
            "Muji",
            "无印良品",
            "Herman Miller",
            "Vitra",
            "Cassina",
            "B&B Italia",
            "Knoll",
            "Artek",
            "Fritz Hansen",
            "品牌",
            "家居品牌",
            "设计品牌",
        ]

        for keyword in brand_keywords:
            if keyword in text:
                brands.append({"name": keyword, "description": f"提到的品牌: {keyword}", "source": "rule_based_extraction"})

        return brands

    def _extract_locations(self, text: str, user_input: str) -> List[Dict[str, Any]]:
        """Extract location entities using pattern matching"""
        locations = []

        # Chinese location patterns
        location_patterns = [
            r"([\u4e00-\u9fa5]{2,}(?:省|市|区|县|镇|村|山|湖|江|河))",
            r"([\u4e00-\u9fa5]{2,}(?:峨眉山|七里坪))",
        ]

        for pattern in location_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if match not in [loc["name"] for loc in locations]:
                    locations.append({"name": match, "description": f"地点: {match}", "source": "rule_based_extraction"})

        # International locations
        international_keywords = ["北欧", "丹麦", "日本", "京都", "东京", "欧洲", "美国"]
        for keyword in international_keywords:
            if keyword in text:
                locations.append({"name": keyword, "description": f"地域: {keyword}", "source": "rule_based_extraction"})

        return locations

    def _extract_styles(self, text: str, user_input: str) -> List[Dict[str, Any]]:
        """Extract style entities using keyword matching"""
        styles = []

        style_keywords = ["北欧", "简约", "现代", "工业风", "侘寂", "极简", "日式", "中式", "新中式", "法式", "美式", "轻奢", "复古", "vintage"]

        for keyword in style_keywords:
            if keyword in text:
                styles.append({"name": keyword, "description": f"设计风格: {keyword}", "source": "rule_based_extraction"})

        return styles

    def _extract_scenes(self, text: str, user_input: str) -> List[Dict[str, Any]]:
        """Extract scene entities using keyword matching"""
        scenes = []

        scene_keywords = ["民宿", "酒店", "咖啡厅", "餐厅", "办公室", "住宅", "别墅", "公寓", "商业空间", "展厅", "会所", "工作室"]

        for keyword in scene_keywords:
            if keyword in text:
                scenes.append({"name": keyword, "description": f"场景类型: {keyword}", "source": "rule_based_extraction"})

        return scenes

    def _extract_competitors(self, text: str, user_input: str) -> List[Dict[str, Any]]:
        """Extract competitor entities using keyword matching"""
        competitors = []

        # Look for competitor mentions
        competitor_patterns = [
            r"([\u4e00-\u9fa5]{2,}(?:酒店|民宿|会所|度假村))",
        ]

        for pattern in competitor_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if match not in [comp["name"] for comp in competitors]:
                    competitors.append(
                        {"name": match, "description": f"竞品案例: {match}", "source": "rule_based_extraction"}
                    )

        return competitors

    def _extract_persons(self, text: str, user_input: str) -> List[Dict[str, Any]]:
        """Extract person entities using pattern matching"""
        persons = []

        # Common designer names
        person_keywords = ["Rolf Hay", "原研哉", "隈研吾", "安藤忠雄", "扎哈·哈迪德", "贝聿铭", "勒·柯布西耶", "密斯·凡·德·罗"]

        for keyword in person_keywords:
            if keyword in text:
                persons.append(
                    {"name": keyword, "description": f"设计师/人物: {keyword}", "source": "rule_based_extraction"}
                )

        return persons


# Convenience function
def extract_entities(structured_data: Dict[str, Any], user_input: str, llm_model=None) -> EntityExtractionResult:
    """
    Convenience function to extract entities

    Args:
        structured_data: Requirements analysis output
        user_input: Original user input
        llm_model: Optional LLM model for extraction

    Returns:
        EntityExtractionResult
    """
    extractor = EntityExtractor(llm_model=llm_model)
    return extractor.extract_entities(structured_data, user_input)
