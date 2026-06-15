from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime

class GeoScores(BaseModel):
    place_viability: int = Field(..., description="地点商业成立度：地点是否适合做当前业态 (0-100)")
    geo_friction_index: int = Field(..., description="地理摩擦指数：越低越好 (0-100)")
    experience_gap_index: int = Field(..., description="体验套利指数：竞品差评可被设计转化的机会量 (0-100)")
    design_leverage_score: int = Field(..., description="设计杠杆指数：设计能对商业结果产生多大影响 (0-100)")
    geo_premium_score: int = Field(..., description="地理溢价指数：地点天然溢价能力 + 设计兑现潜力 (0-100)")

class DemandCatchment(BaseModel):
    primary_persona: str = Field(..., description="核心人群画像")
    travel_motivation: str = Field(..., description="出行/到访动机")
    willingness_to_pay: str = Field(..., description="支付意愿/客单价特征")
    catchment_radius_desc: str = Field(..., description="辐射半径及触达特征描述")

class SubstitutionSummary(BaseModel):
    direct_competitors: List[str] = Field(..., description="直接竞品类型/特征")
    cross_category_alternatives: List[str] = Field(..., description="跨品类替代选择")
    no_spend_alternatives: List[str] = Field(..., description="不消费/平替选项（如公园、家里）")

class ReviewSignalsSummary(BaseModel):
    top_praise: List[str] = Field(..., description="周边常见好评点")
    top_complaints: List[str] = Field(..., description="周边常见差评点/痛点")
    experience_gap_opportunities: List[str] = Field(..., description="体验差带来的市场空白机会")

class DesignCommands(BaseModel):
    must_do: List[str] = Field(..., description="必须做的设计动作")
    must_not: List[str] = Field(..., description="绝对不要做的设计动作")
    defer: List[str] = Field(..., description="可延后/不需要急于决定的动作")

class GeoThesis(BaseModel):
    project_id: str = Field(..., description="关联的项目ID或会话ID")
    site_type: str = Field(..., description="地点类型标签（如 社区底商、核心商圈、文旅目的地等）")
    core_assets: List[str] = Field(..., description="地点核心资产")
    demand_catchment: DemandCatchment
    substitution_summary: SubstitutionSummary
    review_signals_summary: ReviewSignalsSummary
    design_leverage_nodes: List[str] = Field(..., description="设计杠杆节点（最值得投入的空间节点）")
    commercial_risks: List[str] = Field(..., description="商业风险/挑战")
    design_commands: DesignCommands
    scores: GeoScores
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = Field(..., description="AI 置信度（0-1）")

class GeoThesisRequest(BaseModel):
    project_id: Optional[str] = Field(default="demo_project")
    lat: float
    lng: float
    administrative: Dict[str, str] = Field(default_factory=dict)
    poi_summary: Optional[Dict[str, int]] = Field(default_factory=dict)
    project_intent: Optional[str] = Field(default=None)
