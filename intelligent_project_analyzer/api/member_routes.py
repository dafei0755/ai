"""
WPCOM Member 会员信息 API 路由
提供会员等级、订单、钱包等数据查询接口
"""

import os
import sys
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from intelligent_project_analyzer.api.wpcom_member_api import WPCOMMemberAPI
except ImportError as e:
    print(f"[MemberRoutes] 警告：无法导入 WPCOMMemberAPI: {e}")
    WPCOMMemberAPI = None

from intelligent_project_analyzer.api.auth_middleware import auth_middleware

router = APIRouter(prefix="/api/member", tags=["member"])


@router.get("/my-membership")
async def get_my_membership(current_user: Dict[str, Any] = Depends(auth_middleware.get_current_user)):
    """
    获取当前登录用户的会员信息

    Returns:
        {
            "level": 1,
            "level_name": "VIP 1",
            "expire_date": "2026-10-10",
            "is_expired": false,
            "wallet_balance": 0.0
        }
    """
    if WPCOMMemberAPI is None:
        raise HTTPException(status_code=503, detail="会员API服务不可用")

    try:
        print(f"[MemberRoutes]  开始获取会员信息...")
        print(f"[MemberRoutes] 当前用户信息: {current_user}")

        api = WPCOMMemberAPI()
        user_id = current_user.get("user_id")

        if not user_id:
            print(f"[MemberRoutes]  用户ID缺失，current_user: {current_user}")
            raise HTTPException(status_code=400, detail="用户ID缺失")

        print(f"[MemberRoutes]  正在调用 WordPress API 获取用户 {user_id} 的会员信息...")

        # 获取会员信息
        print(f"[MemberRoutes]  调用 api.get_user_membership({user_id})...")
        result = api.get_user_membership(user_id)
        print(f"[MemberRoutes]  WordPress API 返回结果: {result}")

        membership = result.get("membership", {})
        meta = result.get("meta", {})
        print(f"[MemberRoutes] 会员数据: {membership}")
        print(f"[MemberRoutes] Meta 数据: {meta}")

        #  如果 membership 为空，尝试从 meta 字段读取 VIP 数据
        if not membership or membership.get("level") is None:
            # 从 WordPress meta 字段提取 VIP 信息
            vip_type = meta.get("wp_vip_type")  # "1", "2", "3"
            vip_end_date = meta.get("wp_vip_end_date")  # "2026-11-10"

            if vip_type:
                print(f"[MemberRoutes] 从 meta 字段读取 VIP 数据: type={vip_type}, end_date={vip_end_date}")

                # 构造 membership 对象
                from datetime import datetime

                is_active = False
                if vip_end_date:
                    try:
                        expire_date_obj = datetime.strptime(vip_end_date, "%Y-%m-%d")
                        is_active = expire_date_obj > datetime.now()
                    except ValueError:
                        pass

                membership = {
                    "level": vip_type,
                    "expire_date": vip_end_date or "",
                    "is_active": is_active,
                    "status": "active" if is_active else "expired",
                }
                print(f"[MemberRoutes] 构造的 membership 数据: {membership}")

        # 获取钱包信息
        try:
            wallet_result = api.get_user_wallet(user_id)
            print(f"[MemberRoutes] 钱包 API 返回结果: {wallet_result}")

            #  修复：处理多种可能的返回格式
            if isinstance(wallet_result, dict):
                # 方式1: 直接返回 balance 字段
                if "balance" in wallet_result:
                    wallet_balance = float(wallet_result.get("balance", 0))
                # 方式2: 嵌套在 wallet 对象中
                elif "wallet" in wallet_result:
                    wallet_balance = float(wallet_result.get("wallet", {}).get("balance", 0))
                else:
                    wallet_balance = 0.0
            else:
                wallet_balance = 0.0

            print(f"[MemberRoutes] 解析的钱包余额: {wallet_balance}")
        except Exception as e:
            print(f"[MemberRoutes] 获取钱包余额失败: {e}")
            import traceback

            traceback.print_exc()
            wallet_balance = 0.0

        # 格式化返回数据
        #  处理 membership 为 None 的情况（用户未购买会员）
        if membership is None:
            print(f"[MemberRoutes] ️ 用户 {user_id} 没有会员数据，返回免费用户")
            level = 0
            expire_date = ""
            is_expired = False  #  v3.0.23修复：免费用户不显示"已过期"
        else:
            level = int(membership.get("level", "0")) if membership.get("level") else 0
            expire_date = membership.get("expire_date", "")
            is_expired = not membership.get("is_active", False)

        #  会员等级名称映射（与 WordPress 显示保持一致）
        level_names = {0: "免费用户", 1: "普通会员", 2: "超级会员", 3: "钻石会员"}  # VIP 1 → 普通会员  # VIP 2 → 超级会员  # VIP 3 → 钻石会员
        level_name = level_names.get(level, f"VIP {level}")

        print(f"[MemberRoutes]  用户 {user_id} 会员等级: {level_name}")

        return {
            "level": level,
            "level_name": level_name,
            "expire_date": expire_date,
            "is_expired": is_expired,
            "wallet_balance": wallet_balance,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[MemberRoutes]  获取会员信息失败: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取会员信息失败: {str(e)}")


@router.get("/my-orders")
async def get_my_orders(current_user: Dict[str, Any] = Depends(auth_middleware.get_current_user)):
    """
    获取当前用户的订单列表

    Returns:
        {
            "orders": [...],
            "total_count": 10
        }
    """
    try:
        api = WPCOMMemberAPI()
        user_id = current_user.get("user_id")

        if not user_id:
            raise HTTPException(status_code=400, detail="用户ID缺失")

        result = api.get_user_orders(user_id)
        orders_data = result.get("orders", {})

        # 合并 WPCOM 和 WC 订单
        wpcom_orders = orders_data.get("wpcom_orders", [])
        wc_orders = orders_data.get("wc_orders", [])
        all_orders = wpcom_orders + wc_orders

        return {"orders": all_orders, "total_count": len(all_orders)}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[MemberRoutes] 获取订单失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取订单失败: {str(e)}")


@router.get("/my-wallet")
async def get_my_wallet(current_user: Dict[str, Any] = Depends(auth_middleware.get_current_user)):
    """
    获取当前用户的钱包信息

    Returns:
        {
            "balance": 0.0,
            "frozen": 0.0,
            "points": 0
        }
    """
    try:
        api = WPCOMMemberAPI()
        user_id = current_user.get("user_id")

        if not user_id:
            raise HTTPException(status_code=400, detail="用户ID缺失")

        result = api.get_user_wallet(user_id)
        wallet = result.get("wallet", {})

        return {
            "balance": float(wallet.get("balance", 0)),
            "frozen": float(wallet.get("frozen", 0)),
            "points": int(wallet.get("points", 0)),
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[MemberRoutes] 获取钱包信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取钱包信息失败: {str(e)}")


@router.get("/check-access/{level}")
async def check_access(level: int, current_user: Dict[str, Any] = Depends(auth_middleware.get_current_user)):
    """
    检查当前用户是否有指定等级的访问权限

    Args:
        level: 要求的会员等级 (1, 2, 3)

    Returns:
        {
            "has_access": true,
            "user_level": 2,
            "required_level": 1
        }
    """
    try:
        api = WPCOMMemberAPI()
        user_id = current_user.get("user_id")

        if not user_id:
            raise HTTPException(status_code=400, detail="用户ID缺失")

        result = api.get_user_membership(user_id)
        membership = result.get("membership", {})

        user_level = int(membership.get("level", "0"))
        is_active = membership.get("is_active", False)

        # 检查是否有访问权限
        has_access = is_active and user_level >= level

        return {"has_access": has_access, "user_level": user_level, "required_level": level, "is_active": is_active}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[MemberRoutes] 检查访问权限失败: {e}")
        raise HTTPException(status_code=500, detail=f"检查访问权限失败: {str(e)}")
