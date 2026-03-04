"""动机类型 + 本体论管理 + 候选维度审核 API"""

import json
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from loguru import logger

from ..auth_middleware import require_admin

router = APIRouter()


# ============================================================================
# 动机类型配置热更新 API (v7.262)
# ============================================================================


@router.post("/motivation-types/reload")
async def reload_motivation_types(admin: dict = Depends(require_admin)):
    """
    热更新动机类型配置

    重新加载 config/motivation_types.yaml，无需重启服务。

    影响范围：
    - MotivationTypeRegistry 单例配置
    - UCPPT框架清单生成中的动机分组
    - 动机推断引擎的关键词匹配

    Returns:
        {
            "status": "success",
            "previous_count": 更新前类型数量,
            "current_count": 更新后类型数量,
            "added": 新增的类型ID列表,
            "removed": 移除的类型ID列表,
            "updated": 更新的类型ID列表
        }
    """
    try:
        from ..services.motivation_engine import MotivationTypeRegistry

        registry = MotivationTypeRegistry()
        result = registry.reload()

        if result.get("success"):
            logger.info(
                f" 管理员 {admin.get('username')} 触发动机类型配置热更新 | "
                f"之前={result.get('previous_count')}, 现在={result.get('current_count')}"
            )
            return {
                "status": "success",
                "message": "动机类型配置已热更新",
                **result,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            logger.error(f" 动机类型配置热更新失败: {result.get('error')}")
            raise HTTPException(status_code=500, detail=f"热更新失败: {result.get('error', '未知错误')}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 动机类型配置热更新异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/motivation-types")
async def get_motivation_types(admin: dict = Depends(require_admin)):
    """
    获取当前加载的动机类型配置

    Returns:
        {
            "types": 动机类型列表,
            "count": 类型数量,
            "config_path": 配置文件路径
        }
    """
    try:
        from pathlib import Path

        from ..services.motivation_engine import MotivationTypeRegistry

        registry = MotivationTypeRegistry()
        all_types = registry.get_all_types()

        # 转换为可序列化的格式
        types_data = []
        for mtype in all_types:
            types_data.append(
                {
                    "id": mtype.id,
                    "label_zh": mtype.label_zh,
                    "label_en": mtype.label_en,
                    "priority": mtype.priority,
                    "description": mtype.description,
                    "keywords_count": len(mtype.keywords),
                    "color": mtype.color,
                    "enabled": mtype.enabled,
                }
            )

        # 按优先级排序
        priority_order = {"P0": 0, "P1": 1, "P2": 2, "BASELINE": 3, "FALLBACK": 4}
        types_data.sort(key=lambda x: priority_order.get(x["priority"], 99))

        config_path = Path(__file__).parent.parent / "config" / "motivation_types.yaml"

        return {
            "status": "success",
            "types": types_data,
            "count": len(types_data),
            "config_path": str(config_path),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f" 获取动机类型配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 本体论管理 API (Ontology Management) - v2026.2.11
# ============================================================================

@router.get("/ontology/frameworks")
async def list_ontology_frameworks(_: dict = Depends(require_admin)):
    """
    获取所有本体论框架概览
    
    Returns:
        [
            {
                "id": "personal_residential",
                "name": "个人/住宅项目框架",
                "categories": ["spiritual_world", ...],
                "total_dimensions": 25
            },
            ...
        ]
    """
    from ..services.ontology_service import get_ontology_service
    service = get_ontology_service()
    return service.get_all_frameworks()


@router.get("/ontology/framework/{project_type}")
async def get_framework_detail(
    project_type: str,
    _: dict = Depends(require_admin)
):
    """
    获取单个框架的详细维度树
    
    Args:
        project_type: 项目类型（如 "personal_residential"）
    """
    from ..services.ontology_service import get_ontology_service
    service = get_ontology_service()
    
    framework = service.get_framework_detail(project_type)
    if not framework:
        raise HTTPException(404, f"框架不存在: {project_type}")
    
    return framework


@router.get("/ontology/search")
async def search_dimensions(
    q: str = Query(..., description="搜索关键词"),
    limit: int = Query(50, ge=1, le=100),
    _: dict = Depends(require_admin)
):
    """
    按关键词搜索维度
    
    Args:
        q: 搜索关键词
        limit: 返回结果数量（1-100）
    """
    from ..services.ontology_service import get_ontology_service
    service = get_ontology_service()
    
    results = service.search_dimensions(q, limit)
    
    return {
        "query": q,
        "total": len(results),
        "results": results
    }


@router.post("/ontology/reload")
async def reload_ontology(_: dict = Depends(require_admin)):
    """重新加载本体论文件（清除缓存）"""
    from ..services.ontology_service import get_ontology_service
    service = get_ontology_service()
    
    service.reload()
    
    return {
        "status": "success",
        "message": "本体论已重新加载"
    }


@router.get("/ontology/validate")
async def validate_ontology_syntax(_: dict = Depends(require_admin)):
    """验证 ontology.yaml 语法正确性"""
    from ..services.ontology_service import get_ontology_service
    service = get_ontology_service()
    
    is_valid = service.validate_yaml_syntax()
    
    return {
        "valid": is_valid,
        "message": "语法正确" if is_valid else "语法错误，请检查日志"
    }


# ============================================================================
# 候选维度审核 API (Dimension Candidate Review) - v2026.2.11
# ============================================================================

@router.get("/dimension-learning/candidates")
async def list_pending_candidates(
    limit: int = Query(50, ge=1, le=200),
    status: str = Query("pending", description="候选状态: pending/approved/rejected"),
    _: dict = Depends(require_admin)
):
    """
    获取候选维度列表
    
    Args:
        limit: 返回数量限制
        status: 候选状态筛选
    """
    from ..learning.database_manager import get_db_manager
    
    db = get_db_manager()
    
    # 根据状态获取候选
    if status == "pending":
        candidates = db.get_pending_candidates(limit)
    else:
        # TODO: 添加按状态筛选的查询方法
        candidates = db.get_pending_candidates(limit)
    
    # 获取统计信息
    stats = db.get_candidate_statistics()
    
    return {
        "items": candidates,
        "total": len(candidates),
        "statistics": stats
    }


@router.post("/dimension-learning/candidates/{candidate_id}/approve")
async def approve_dimension_candidate(
    candidate_id: int,
    admin: dict = Depends(require_admin)
):
    """
    批准候选维度并写入 ontology.yaml
    
    Args:
        candidate_id: 候选维度ID
    """
    import json

    from ..learning.database_manager import get_db_manager
    from ..services.ontology_editor import get_ontology_editor
    
    try:
        db = get_db_manager()
        editor = get_ontology_editor()
        
        # 1. 获取候选数据
        with db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT dimension_data, confidence_score FROM dimension_candidates WHERE id = ?",
                (candidate_id,)
            )
            row = cursor.fetchone()
            
        if not row:
            raise HTTPException(404, f"候选维度不存在: {candidate_id}")
        
        dim_data = json.loads(row[0])
        confidence = row[1]
        
        # 2. 写入 ontology.yaml
        success = editor.append_dimension(
            project_type=dim_data.get("project_type", "meta_framework"),
            category=dim_data.get("category", "universal_dimensions"),
            dimension_data={
                "name": dim_data.get("name"),
                "description": dim_data.get("description"),
                "ask_yourself": dim_data.get("ask_yourself"),
                "examples": dim_data.get("examples")
            }
        )
        
        if not success:
            raise HTTPException(500, "写入 ontology.yaml 失败")
        
        # 3. 更新候选状态
        db.approve_candidate(candidate_id, reviewer_id=admin.get("username", "admin"))
        
        # 4. 重新加载本体论缓存
        from ..services.ontology_service import get_ontology_service
        get_ontology_service().reload()
        
        logger.info(f" 管理员 {admin.get('username')} 批准候选 {candidate_id}")
        
        return {
            "status": "success",
            "message": "候选维度已批准并写入本体论",
            "dimension": dim_data,
            "confidence": confidence
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 批准候选失败: {e}")
        raise HTTPException(500, f"批准失败: {str(e)}")


@router.post("/dimension-learning/candidates/{candidate_id}/reject")
async def reject_dimension_candidate(
    candidate_id: int,
    reason: str = Body("", embed=True),
    admin: dict = Depends(require_admin)
):
    """
    拒绝候选维度
    
    Args:
        candidate_id: 候选维度ID
        reason: 拒绝原因
    """
    from ..learning.database_manager import get_db_manager
    
    db = get_db_manager()
    
    success = db.reject_candidate(
        candidate_id,
        reviewer_id=admin.get("username", "admin"),
        reason=reason
    )
    
    if not success:
        raise HTTPException(404, f"候选维度不存在或操作失败: {candidate_id}")
    
    logger.info(f" 管理员 {admin.get('username')} 拒绝候选 {candidate_id}: {reason}")
    
    return {
        "status": "success",
        "message": "候选维度已拒绝",
        "candidate_id": candidate_id,
        "reason": reason
    }


@router.post("/dimension-learning/candidates/batch")
async def batch_operate_candidates(
    action: str = Body(..., embed=True, description="操作: approve/reject"),
    candidate_ids: List[int] = Body(..., embed=True),
    reason: str = Body("", embed=True),
    admin: dict = Depends(require_admin)
):
    """
    批量操作候选维度
    
    Args:
        action: 操作类型 (approve/reject)
        candidate_ids: 候选ID列表
        reason: 拒绝原因（仅在 action=reject 时使用）
    """
    from ..learning.database_manager import get_db_manager
    
    db = get_db_manager()
    reviewer_id = admin.get("username", "admin")
    
    if action == "approve":
        result = db.batch_approve_candidates(candidate_ids, reviewer_id)
    elif action == "reject":
        success = []
        failed = []
        for cid in candidate_ids:
            if db.reject_candidate(cid, reviewer_id, reason):
                success.append(cid)
            else:
                failed.append(cid)
        result = {
            "success": success,
            "failed": failed,
            "total": len(candidate_ids)
        }
    else:
        raise HTTPException(400, f"无效操作: {action}")
    
    logger.info(f" 管理员 {reviewer_id} 批量{action}: 成功 {len(result['success'])}, 失败 {len(result['failed'])}")
    
    return {
        "status": "success",
        "action": action,
        "result": result
    }
