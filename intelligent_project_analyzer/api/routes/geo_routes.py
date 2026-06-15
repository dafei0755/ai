import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from intelligent_project_analyzer.models.geo_models import GeoThesisRequest, GeoThesis
from intelligent_project_analyzer.services.geo_intelligence_service import GeoIntelligenceService

router = APIRouter(prefix="/api/v1/geo", tags=["地理商业智能"])
logger = logging.getLogger(__name__)

# 依赖注入 service，确保全局可以使用也可以方便 mock 测试
def get_geo_service() -> GeoIntelligenceService:
    return GeoIntelligenceService()

@router.post("/thesis", response_model=GeoThesis)
async def generate_geo_thesis(
    request: GeoThesisRequest,
    service: GeoIntelligenceService = Depends(get_geo_service)
):
    """
    根据地理底盘（经纬度及周边数据）和初步意图，
    调用大语言模型进行空间商业智能推演，生成 G3-G4 商业报告。
    """
    try:
        thesis = service.generate_geo_thesis(request)
        return thesis
    except Exception as e:
        logger.error(f"Generate geo thesis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
