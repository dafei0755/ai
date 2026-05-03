import json
from typing import Any, Literal, Optional
from pydantic import BaseModel

from intelligent_project_analyzer.advisor.skill_registry import SkillRegistry
from intelligent_project_analyzer.services.llm_factory import LLMFactory


class SkillInput(BaseModel):
    project_id: str
    raw_description: str
    context_hints: Optional[list[str]] = None


class SkillOutput(BaseModel):
    structured_data: dict[str, Any]
    evidence_status: Literal["none", "internal_hint", "verified"] = "none"
    confidence: Literal["high", "medium", "low"]
    missing_fields: list[str] = []
    suggestions: list[str] = []


_SYSTEM_PROMPT = """你是一个需求结构化专家。将用户的项目描述解析为结构化 JSON，包含以下字段（如有）：
- project_type: 项目类型（如民宿、办公、餐厅等）
- location: 地点/环境特征
- area_sqm: 建筑面积（数值，如已知）
- room_count: 房间数量（数值，如已知）
- key_requirements: 核心需求列表
- style_keywords: 风格关键词列表
- missing_fields: 明显缺失但重要的信息列表
- confidence: 你对结构化结果的置信度（high/medium/low）

只返回 JSON，不要有任何其他文字。"""


class RequirementStructuringSkill:
    SKILL_ID = "req_structuring_v1"

    def __init__(self, registry: SkillRegistry):
        self._manifest = registry.require(self.SKILL_ID)
        self._llm = LLMFactory.create_llm(temperature=0.1, max_tokens=1000)

    def run(self, inp: SkillInput) -> SkillOutput:
        if not inp.raw_description.strip():
            raise ValueError("422: raw_description 不能为空")

        try:
            messages = [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": inp.raw_description},
            ]
            response = self._llm.invoke(messages)
            raw = response.content.strip()
            data = json.loads(raw)
            confidence = data.pop("confidence", "medium")
            missing_fields = data.pop("missing_fields", [])
            return SkillOutput(
                structured_data=data,
                evidence_status="internal_hint",
                confidence=confidence,
                missing_fields=missing_fields,
            )
        except Exception:
            return SkillOutput(
                structured_data={},
                evidence_status="none",
                confidence="low",
                missing_fields=[],
                suggestions=["原始描述解析失败，请检查输入或重试"],
            )
