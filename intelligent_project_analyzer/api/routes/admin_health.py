"""系统健康检查 + 用户分析 API"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from ..auth_middleware import require_admin
from .admin_shared import metrics_cache

router = APIRouter()


@router.get("/health")
async def admin_health_check(admin: dict = Depends(require_admin)):
    """
    管理员系统健康检查（详细版）

    返回更多内部状态信息
    """
    try:
        return {
            "status": "healthy",
            "admin": admin.get("username"),
            "components": {
                "api": "up",
                "redis": "up",  # TODO: 实际检查
                "config_manager": "up",
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f" 健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 用户分析 API
# ============================================================================


@router.get("/users/analytics")
async def get_users_analytics(
    time_range: str = Query("7d", description="时间范围: 1d/7d/30d/365d"), admin: dict = Depends(require_admin)
):
    """
    获取用户分析数据

    返回：
    - 在线用户数量（按天/周/月/年统计）
    - 用户地区分布（基于session中的城市信息）
    - 用户对话数量排行（可按时间筛选）

    缓存策略：60秒TTL
    """
    cache_key = f"users_analytics_{time_range}"

    # 检查缓存
    if cache_key in metrics_cache:
        logger.debug(f" 返回缓存的用户分析数据: {time_range}")
        return metrics_cache[cache_key]

    try:
        # 计算时间范围
        time_ranges = {"1d": 1, "7d": 7, "30d": 30, "365d": 365}
        days = time_ranges.get(time_range, 7)
        cutoff_date = datetime.now() - timedelta(days=days)

        # 从 server.py 导入全局 session_manager
        from ..api.server import session_manager as global_session_manager

        if not global_session_manager:
            raise HTTPException(status_code=503, detail="Session manager 未初始化")

        # 获取所有会话
        all_sessions = await global_session_manager.get_all_sessions()

        # 过滤时间范围内的会话
        filtered_sessions = []
        for session in all_sessions:
            created_str = session.get("created_at")
            if created_str:
                try:
                    created_at = datetime.fromisoformat(created_str)
                    if created_at >= cutoff_date:
                        filtered_sessions.append(session)
                except Exception:
                    continue

        # 1. 统计在线用户数量（按日期分组）
        daily_users = {}  # {date: set(user_ids)}
        weekly_users = {}  # {week_number: set(user_ids)}
        monthly_users = {}  # {month: set(user_ids)}
        yearly_users = {}  # {year: set(user_ids)}

        for session in filtered_sessions:
            user_id = session.get("user_id") or session.get("username", "guest")
            created_str = session.get("created_at")

            if not created_str:
                continue

            try:
                created_at = datetime.fromisoformat(created_str)

                # 按日统计
                date_key = created_at.strftime("%Y-%m-%d")
                if date_key not in daily_users:
                    daily_users[date_key] = set()
                daily_users[date_key].add(user_id)

                # 按周统计
                week_key = f"{created_at.year}-W{created_at.isocalendar()[1]:02d}"
                if week_key not in weekly_users:
                    weekly_users[week_key] = set()
                weekly_users[week_key].add(user_id)

                # 按月统计
                month_key = created_at.strftime("%Y-%m")
                if month_key not in monthly_users:
                    monthly_users[month_key] = set()
                monthly_users[month_key].add(user_id)

                # 按年统计
                year_key = str(created_at.year)
                if year_key not in yearly_users:
                    yearly_users[year_key] = set()
                yearly_users[year_key].add(user_id)
            except Exception:
                continue

        # 转换为列表格式
        daily_trend = [{"date": k, "count": len(v)} for k, v in sorted(daily_users.items())]
        weekly_trend = [{"week": k, "count": len(v)} for k, v in sorted(weekly_users.items())]
        monthly_trend = [{"month": k, "count": len(v)} for k, v in sorted(monthly_users.items())]
        yearly_trend = [{"year": k, "count": len(v)} for k, v in sorted(yearly_users.items())]

        # 2. 地区分布（优先使用IP定位的metadata数据）
        region_distribution = {}
        region_coords = {}  # 存储经纬度用于地图可视化

        for session in filtered_sessions:
            metadata = session.get("metadata", {})

            #  优先使用IP定位的城市信息
            location = metadata.get("location")
            geo_info = metadata.get("geo_info", {})

            if not location or location == "未知":
                # 回退：从用户输入中检测城市（中国主要城市列表）
                user_input = session.get("user_input", "")
                cities = [
                    "北京",
                    "上海",
                    "广州",
                    "深圳",
                    "杭州",
                    "成都",
                    "重庆",
                    "武汉",
                    "西安",
                    "天津",
                    "南京",
                    "苏州",
                    "长沙",
                    "郑州",
                    "济南",
                    "青岛",
                    "厦门",
                    "福州",
                    "昆明",
                    "南宁",
                    "海口",
                    "兰州",
                    "银川",
                    "西宁",
                    "乌鲁木齐",
                    "拉萨",
                    "哈尔滨",
                    "长春",
                    "沈阳",
                    "大连",
                    "石家庄",
                    "太原",
                    "呼和浩特",
                    "合肥",
                    "南昌",
                    "贵阳",
                ]

                detected_city = None
                for city in cities:
                    if city in user_input:
                        detected_city = city
                        break

                location = detected_city or "未知地区"

            # 统计地区分布
            region_distribution[location] = region_distribution.get(location, 0) + 1

            # 收集经纬度数据（用于前端地图可视化）
            if geo_info.get("latitude") and geo_info.get("longitude"):
                if location not in region_coords:
                    region_coords[location] = {
                        "lat": geo_info["latitude"],
                        "lng": geo_info["longitude"],
                        "country": geo_info.get("country", ""),
                        "province": geo_info.get("province", ""),
                    }

        # 转换为列表格式并排序（附带经纬度信息）
        region_list = []
        for region, count in sorted(region_distribution.items(), key=lambda x: x[1], reverse=True):
            item = {"region": region, "count": count}
            if region in region_coords:
                item.update(region_coords[region])
            region_list.append(item)

        # 3. 用户对话数量排行
        user_conversation_counts = {}

        for session in filtered_sessions:
            user_id = session.get("user_id") or session.get("username", "guest")
            user_conversation_counts[user_id] = user_conversation_counts.get(user_id, 0) + 1

        # 排序并取Top 50
        user_rankings = sorted(
            [{"user_id": k, "conversation_count": v} for k, v in user_conversation_counts.items()],
            key=lambda x: x["conversation_count"],
            reverse=True,
        )[:50]

        # 构建响应
        result = {
            "status": "success",
            "time_range": time_range,
            "total_users": len(set(s.get("user_id") or s.get("username", "guest") for s in filtered_sessions)),
            "total_sessions": len(filtered_sessions),
            "date_range": {"start": cutoff_date.strftime("%Y-%m-%d"), "end": datetime.now().strftime("%Y-%m-%d")},
            "online_users": {
                "daily": daily_trend[-30:],  # 最近30天
                "weekly": weekly_trend[-12:],  # 最近12周
                "monthly": monthly_trend[-12:],  # 最近12个月
                "yearly": yearly_trend[-5:],  # 最近5年
            },
            "region_distribution": region_list,
            "user_rankings": user_rankings,
            "timestamp": datetime.now().isoformat(),
        }

        # 缓存结果（60秒）
        metrics_cache[cache_key] = result

        logger.info(f" 用户分析数据生成完成: {len(filtered_sessions)} sessions, {result['total_users']} users")
        return result

    except Exception as e:
        logger.error(f" 获取用户分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
