"""精选展示配置管理 + 搜索过滤器管理 API"""

import json
from pathlib import Path
from typing import Any, Dict

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from ...utils.config_manager import config_manager
from ..auth_middleware import require_admin

session_manager = None  # 将在请求时从 server.py 获取

router = APIRouter()


@router.get("/showcase/config")
async def get_showcase_config(_=Depends(require_admin)):
    """
    获取精选展示配置
    Returns the featured showcase configuration
    """
    try:
        config_path = Path("config/featured_showcase.yaml")
        if not config_path.exists():
            logger.warning("️ 精选展示配置文件不存在，返回默认配置")
            return {
                "session_ids": [],
                "rotation_interval_seconds": 5,
                "autoplay": True,
                "loop": True,
                "show_navigation": True,
                "show_pagination": True,
                "max_slides": 10,
                "image_selection": "random",
                "fallback_behavior": "skip",
                "cache_ttl_seconds": 300,
            }

        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        logger.info(f" 精选展示配置读取成功: {len(config.get('session_ids', []))} sessions")
        return config

    except Exception as e:
        logger.error(f" 读取精选展示配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/showcase/config")
async def update_showcase_config(config: Dict[str, Any], _=Depends(require_admin)):
    """
    更新精选展示配置
    Updates the featured showcase configuration

    Request body:
    - session_ids: List[str] - 会话ID列表（最多10个）
    - rotation_interval_seconds: int - 轮播间隔（秒）
    - autoplay: bool - 是否自动播放
    - ... 其他配置项
    """
    try:
        # 验证 session_ids
        session_ids = config.get("session_ids", [])
        if not isinstance(session_ids, list):
            raise HTTPException(status_code=400, detail="session_ids 必须是数组")

        if len(session_ids) > 10:
            raise HTTPException(status_code=400, detail="最多只能设置10个精选会话")

        # 验证会话ID是否存在
        global session_manager
        if session_manager:
            for session_id in session_ids:
                try:
                    # 尝试从Redis或归档获取会话
                    session = await session_manager.get_session_state(session_id)
                    if not session:
                        # 尝试从归档获取
                        from ..services.session_archive_manager import SessionArchiveManager

                        archive_manager = SessionArchiveManager()
                        archived = await archive_manager.get_archived_session(session_id)
                        if not archived:
                            logger.warning(f"️ 会话 {session_id} 不存在，但仍允许保存")
                except Exception as e:
                    logger.warning(f"️ 验证会话 {session_id} 时出错: {e}")

        # 保存配置
        config_path = Path("config/featured_showcase.yaml")
        config_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f" 准备保存配置到: {config_path.absolute()}")
        logger.info(f" 配置内容: {json.dumps(config, ensure_ascii=False, indent=2)}")

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

        logger.info(f" 精选展示配置更新成功: {len(session_ids)} sessions")

        # 验证保存是否成功
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                saved_config = yaml.safe_load(f)
                logger.info(f" 验证: 配置文件已保存，包含 {len(saved_config.get('session_ids', []))} 个会话")

        # 触发配置热重载
        try:
            config_manager.reload_config()
            logger.info(" 配置热重载成功")
        except Exception as e:
            logger.warning(f"️ 配置热重载失败: {e}")

        return {
            "status": "success",
            "message": "配置更新成功",
            "session_count": len(session_ids),
            "saved_path": str(config_path.absolute()),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 更新精选展示配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 搜索过滤器管理 API (黑白名单)
# ============================================================================


@router.get("/search-filters")
async def get_search_filters(_=Depends(require_admin)):
    """
    获取搜索过滤器配置（黑白名单）

    返回：
    - blacklist: 黑名单配置
    - whitelist: 白名单配置
    - statistics: 统计信息
    - metadata: 元信息
    """
    try:
        from ..services.search_filter_manager import get_filter_manager

        manager = get_filter_manager()
        config = manager.get_config()
        stats = manager.get_statistics()

        return {
            "status": "success",
            "data": {
                "blacklist": config.get("blacklist", {}),
                "whitelist": config.get("whitelist", {}),
                "scope": config.get("scope", {}),
                "metadata": config.get("metadata", {}),
                "statistics": stats,
            },
        }

    except Exception as e:
        logger.error(f" 获取搜索过滤器配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search-filters/reload")
async def reload_search_filters(_=Depends(require_admin)):
    """
    重新加载搜索过滤器配置

    用于手动触发配置热重载
    """
    try:
        from ..services.search_filter_manager import get_filter_manager

        manager = get_filter_manager()
        success = manager.reload()

        if success:
            return {"status": "success", "message": "配置重载成功", "statistics": manager.get_statistics()}
        else:
            raise HTTPException(status_code=500, detail="配置重载失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 重载搜索过滤器配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search-filters/blacklist")
async def add_to_blacklist(
    domain: str = Query(..., description="域名或模式"),
    match_type: str = Query("domains", description="匹配类型: domains/patterns/regex"),
    note: str | None = Query(None, description="备注说明"),
    _=Depends(require_admin),
):
    """
    添加到黑名单

    参数：
    - domain: 域名或模式（如 example.com 或 *.spam.com）
    - match_type: 匹配类型
      - domains: 完整域名匹配
      - patterns: 通配符匹配
      - regex: 正则表达式匹配
    - note: 添加原因备注
    """
    try:
        from ..services.search_filter_manager import get_filter_manager

        manager = get_filter_manager()
        success = manager.add_to_blacklist(domain, match_type, note)

        if success:
            return {
                "status": "success",
                "message": f"已添加到黑名单: {domain}",
                "data": {"domain": domain, "match_type": match_type, "note": note},
                "statistics": manager.get_statistics(),
            }
        else:
            raise HTTPException(status_code=400, detail="添加失败（可能已存在）")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 添加到黑名单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/search-filters/blacklist")
async def remove_from_blacklist(
    domain: str = Query(..., description="域名或模式"),
    match_type: str = Query("domains", description="匹配类型"),
    _=Depends(require_admin),
):
    """
    从黑名单移除

    参数：
    - domain: 要移除的域名或模式
    - match_type: 匹配类型
    """
    try:
        from ..services.search_filter_manager import get_filter_manager

        manager = get_filter_manager()
        success = manager.remove_from_blacklist(domain, match_type)

        if success:
            return {"status": "success", "message": f"已从黑名单移除: {domain}", "statistics": manager.get_statistics()}
        else:
            raise HTTPException(status_code=404, detail="域名不在黑名单中")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 从黑名单移除失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search-filters/whitelist")
async def add_to_whitelist(
    domain: str = Query(..., description="域名或模式"),
    match_type: str = Query("domains", description="匹配类型: domains/patterns/regex"),
    note: str | None = Query(None, description="备注说明"),
    _=Depends(require_admin),
):
    """
    添加到白名单

    参数：
    - domain: 域名或模式
    - match_type: 匹配类型
    - note: 添加原因备注
    """
    try:
        from ..services.search_filter_manager import get_filter_manager

        manager = get_filter_manager()
        success = manager.add_to_whitelist(domain, match_type, note)

        if success:
            return {
                "status": "success",
                "message": f"已添加到白名单: {domain}",
                "data": {"domain": domain, "match_type": match_type, "note": note},
                "statistics": manager.get_statistics(),
            }
        else:
            raise HTTPException(status_code=400, detail="添加失败（可能已存在）")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 添加到白名单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/search-filters/whitelist")
async def remove_from_whitelist(
    domain: str = Query(..., description="域名或模式"),
    match_type: str = Query("domains", description="匹配类型"),
    _=Depends(require_admin),
):
    """
    从白名单移除

    参数：
    - domain: 要移除的域名或模式
    - match_type: 匹配类型
    """
    try:
        from ..services.search_filter_manager import get_filter_manager

        manager = get_filter_manager()
        success = manager.remove_from_whitelist(domain, match_type)

        if success:
            return {"status": "success", "message": f"已从白名单移除: {domain}", "statistics": manager.get_statistics()}
        else:
            raise HTTPException(status_code=404, detail="域名不在白名单中")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 从白名单移除失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search-filters/test")
async def test_search_filter(url: str = Query(..., description="测试URL"), _=Depends(require_admin)):
    """
    测试 URL 是否会被黑白名单过滤

    参数：
    - url: 要测试的 URL

    返回：
    - is_blacklisted: 是否在黑名单
    - is_whitelisted: 是否在白名单
    - will_be_blocked: 是否会被过滤
    - boost_score: 白名单提升分数（如果在白名单）
    """
    try:
        from ..services.search_filter_manager import get_filter_manager

        manager = get_filter_manager()

        is_blacklisted = manager.is_blacklisted(url)
        is_whitelisted = manager.is_whitelisted(url)
        will_be_blocked = is_blacklisted
        boost_score = manager.get_boost_score() if is_whitelisted else 0

        return {
            "status": "success",
            "data": {
                "url": url,
                "is_blacklisted": is_blacklisted,
                "is_whitelisted": is_whitelisted,
                "will_be_blocked": will_be_blocked,
                "boost_score": boost_score,
                "priority_rule": "黑名单优先（黑名单 > 白名单）",
            },
        }

    except Exception as e:
        logger.error(f" 测试搜索过滤器失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
