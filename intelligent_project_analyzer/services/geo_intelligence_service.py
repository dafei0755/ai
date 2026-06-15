import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
import yaml
from loguru import logger

from intelligent_project_analyzer.models.geo_models import GeoThesis, GeoThesisRequest
from intelligent_project_analyzer.services.llm_factory import LLMFactory
from langchain_core.messages import HumanMessage, SystemMessage

class GeoIntelligenceService:
    CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "geo_intelligence.yaml"
    DEFAULT_GEO_TRIGGER_KEYWORDS = (
        "选址",
        "商圈",
        "周边",
        "竞品",
        "客流",
        "人流",
        "地段",
        "社区底商",
        "街区",
        "文旅",
        "目的地",
        "到达",
        "辐射",
        "城市",
        "区域",
    )

    def __init__(self, llm: Any | None = None):
        self.llm = llm

    @classmethod
    def assess_activation(
        cls,
        project_intent: str | None = None,
        has_geo_anchor: bool = False,
        administrative: Dict[str, str] | None = None,
        poi_summary: Dict[str, int] | None = None,
    ) -> Dict[str, Any]:
        """Decide whether geo intelligence should join the advisor chain."""
        if not has_geo_anchor:
            return {
                "should_activate": False,
                "reason": "missing_geo_anchor",
                "boundary": "geo_intelligence_is_optional_context",
            }

        if administrative or poi_summary:
            return {
                "should_activate": True,
                "reason": "geo_anchor_with_context",
                "boundary": "geo_intelligence_is_optional_context",
            }

        intent = project_intent or ""
        if any(keyword in intent for keyword in cls._geo_trigger_keywords()):
            return {
                "should_activate": True,
                "reason": "geo_sensitive_signal",
                "boundary": "geo_intelligence_is_optional_context",
            }

        return {
            "should_activate": False,
            "reason": "no_geo_sensitive_signal",
            "boundary": "geo_intelligence_is_optional_context",
        }

    @classmethod
    def _geo_trigger_keywords(cls) -> tuple[str, ...]:
        try:
            if cls.CONFIG_PATH.exists():
                data = yaml.safe_load(cls.CONFIG_PATH.read_text(encoding="utf-8")) or {}
                keywords = data.get("trigger_keywords") or []
                normalized = tuple(str(item).strip() for item in keywords if str(item).strip())
                if normalized:
                    return normalized
        except Exception as e:
            logger.warning(f"Failed to load geo trigger keywords config: {e}")

        return cls.DEFAULT_GEO_TRIGGER_KEYWORDS

    def _get_llm(self):
        if self.llm is not None:
            return self.llm
        try:
            self.llm = LLMFactory.create_llm(temperature=0.5, timeout=60)
            logger.info("GeoIntelligenceService initialized via LLMFactory.")
        except Exception as e:
            logger.warning(f"Failed to initialize LLMFactory, attempting fallback: {e}")
            from langchain_openai import ChatOpenAI
            import os
            self.llm = ChatOpenAI(
                model=os.getenv("DIMENSION_LLM_MODEL", "gpt-4o-mini"),
                temperature=0.5,
                timeout=60,
            )
        return self.llm

    def generate_geo_thesis(self, request: GeoThesisRequest) -> GeoThesis:
        logger.info(f"Generating Geo Thesis for project: {request.project_id}")
        
        system_prompt = """你是一个顶级的「空间商业智能引擎」(Geo Commercial Intelligence Engine)。
你的任务是基于输入的地理位置、行政区划、周边 POI（Points of Interest）分布以及用户意图，生成一份高度专业、具备洞察力的商业空间推演报告（GeoThesis）。

你必须用 JSON 格式输出结果，并且确保符合以下结构：
{
  "site_type": "地点类型标签，如社区底商、核心商圈、文旅目的地等",
  "core_assets": ["核心资产1", "核心资产2"],
  "demand_catchment": {
    "primary_persona": "核心人群画像描述",
    "travel_motivation": "出行/到访动机描述",
    "willingness_to_pay": "支付意愿特征",
    "catchment_radius_desc": "辐射半径特征"
  },
  "substitution_summary": {
    "direct_competitors": ["直接竞品1", "直接竞品2"],
    "cross_category_alternatives": ["跨品类替代选择1"],
    "no_spend_alternatives": ["不消费平替（如公园）"]
  },
  "review_signals_summary": {
    "top_praise": ["好评点1"],
    "top_complaints": ["痛点1"],
    "experience_gap_opportunities": ["未被满足的体验空白"]
  },
  "design_leverage_nodes": ["设计杠杆节点1", "节点2"],
  "commercial_risks": ["风险1", "风险2"],
  "design_commands": {
    "must_do": ["必须做的设计1"],
    "must_not": ["绝对不能做的设计1"],
    "defer": ["可延后的决策"]
  },
  "scores": {
    "place_viability": 85,
    "geo_friction_index": 30,
    "experience_gap_index": 75,
    "design_leverage_score": 90,
    "geo_premium_score": 80
  },
  "confidence": 0.92
}

注意：
- 所有分数值必须在 0 到 100 之间，置信度 confidence 在 0.0-1.0 之间。
- 请直接输出 JSON 代码，不要添加 markdown 代码块包裹 (即不要带 ```json)，或者确保输出能被直接解析。
"""
        
        user_prompt = f"""
分析请求：
- 坐标：Lat {request.lat}, Lng {request.lng}
- 行政区：{request.administrative}
- 周边 POI 概要：{json.dumps(request.poi_summary, ensure_ascii=False) if request.poi_summary else '无数据'}
- 用户初步意图/项目偏好：{request.project_intent or '未提供'}

请根据以上地理与商业信息，推演出最可能符合该地缘底盘潜力的商业方向，并生成 JSON 格式报告。
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = self._get_llm().invoke(messages)
            response_text = response.content if hasattr(response, "content") else str(response)
            
            # Extract JSON block if it happens to be wrapped
            json_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", response_text)
            if json_match:
                response_text = json_match.group(1).strip()
                
            parsed_data = json.loads(response_text)
            
            # Attach id and time
            parsed_data['project_id'] = request.project_id
            parsed_data['generated_at'] = datetime.now().isoformat()
            
            # Remove validation_metrics if LLM hallucionated it
            if "validation_metrics" in parsed_data.get("scores", {}):
                del parsed_data["scores"]["validation_metrics"]
                
            return GeoThesis(**parsed_data)
        except Exception as e:
            logger.error(f"Error generating Geo Thesis: {e}")
            # Fallback mock response
            return self._generate_fallback(request)
            
    def _generate_fallback(self, request: GeoThesisRequest) -> GeoThesis:
        logger.warning("Generating fallback Geo Thesis")
        return GeoThesis(
            project_id=request.project_id,
            site_type="默认分析标签（降级）",
            core_assets=["默认资产表现", "地段基础流量"],
            demand_catchment={
                "primary_persona": "区域内常规居民与过路客",
                "travel_motivation": "即时性需求驱动",
                "willingness_to_pay": "中等价格敏感",
                "catchment_radius_desc": "核心覆盖约1-3公里"
            },
            substitution_summary={
                "direct_competitors": ["周边同类业态", "线上竞品"],
                "cross_category_alternatives": ["其他休闲选项"],
                "no_spend_alternatives": ["居家休闲", "市政公园"]
            },
            review_signals_summary={
                "top_praise": ["位置便利", "满足基本功能"],
                "top_complaints": ["空间局促", "缺乏体验感"],
                "experience_gap_opportunities": ["空间品质跃升", "复合场景重塑"]
            },
            design_leverage_nodes=["门头吸睛昭示", "动线效率优化"],
            commercial_risks=["租金成本压力", "周边同质化竞争严重"],
            design_commands={
                "must_do": ["最大化临街展示面", "优化照明系统"],
                "must_not": ["过度复杂的内部阻隔", "脱离环境气质的突兀设计"],
                "defer": ["深度个性化软装", "大额非标设备投入"]
            },
            scores={
                "place_viability": 60,
                "geo_friction_index": 50,
                "experience_gap_index": 50,
                "design_leverage_score": 60,
                "geo_premium_score": 50
            },
            generated_at=datetime.now().isoformat(),
            confidence=0.5
        )
