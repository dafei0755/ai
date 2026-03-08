"""
WPCOM Member Pro API 客户端

提供与 WordPress WPCOM Member Pro 插件交互的 Python 接口
支持获取会员信息、订单记录、钱包余额等功能

环境变量配置（.env）：
- WORDPRESS_URL: WordPress 站点地址（如 https://www.ucppt.com）
- WORDPRESS_ADMIN_USERNAME: WordPress 管理员用户名
- WORDPRESS_ADMIN_PASSWORD: WordPress 管理员密码

使用示例：
    from wpcom_member_api import WPCOMMemberAPI

    api = WPCOMMemberAPI()
    membership = api.get_user_membership(user_id=1)
    print(f"会员等级: {membership['membership']['level']}")
"""

import os
from typing import Any, Dict

import httpx
from loguru import logger


class WPCOMMemberAPI:
    """WPCOM Member Pro API 客户端"""

    def __init__(self):
        """初始化 API 客户端，从环境变量读取配置"""
        self.base_url = os.getenv("WORDPRESS_URL", "").rstrip("/")
        self.username = os.getenv("WORDPRESS_ADMIN_USERNAME", "")
        self.password = os.getenv("WORDPRESS_ADMIN_PASSWORD", "")
        self.token = None

        if not all([self.base_url, self.username, self.password]):
            logger.warning(
                "[WPCOMMemberAPI] 环境变量未完整配置: "
                f"WORDPRESS_URL={bool(self.base_url)}, "
                f"WORDPRESS_ADMIN_USERNAME={bool(self.username)}, "
                f"WORDPRESS_ADMIN_PASSWORD={bool(self.password)}"
            )

    def get_token(self) -> str:
        """
        获取 JWT Token

        使用 Simple JWT Login 插件的认证端点获取 JWT Token
        Token 会缓存在实例中，重复调用不会重新请求

        Returns:
            str: JWT Token 字符串

        Raises:
            Exception: Token 获取失败
        """
        if self.token:
            return self.token

        url = f"{self.base_url}/wp-json/simple-jwt-login/v1/auth"
        data = {"username": self.username, "password": self.password}

        logger.info(f"[WPCOMMemberAPI] 正在获取 JWT Token: {url}")

        try:
            response = httpx.post(url, json=data, timeout=30)

            if response.status_code == 200:
                response_data = response.json()
                self.token = response_data["data"]["jwt"]
                logger.success("[WPCOMMemberAPI] JWT Token 获取成功")
                return self.token
            else:
                error_msg = f"Token 获取失败 ({response.status_code}): {response.text}"
                logger.error(f"[WPCOMMemberAPI] {error_msg}")
                raise Exception(error_msg)

        except httpx.TimeoutException:
            error_msg = "Token 获取超时（30秒）"
            logger.error(f"[WPCOMMemberAPI] {error_msg}")
            raise Exception(error_msg)

        except Exception as e:
            logger.error(f"[WPCOMMemberAPI] Token 获取异常: {e}")
            raise

    def _request(self, endpoint: str, method: str = "GET", data: Dict | None = None) -> Dict[str, Any]:
        """
        通用请求方法

        Args:
            endpoint: API 端点路径（如 /custom/v1/user-membership/1）
            method: HTTP 方法（GET 或 POST）
            data: POST 请求的 JSON 数据

        Returns:
            Dict[str, Any]: API 响应的 JSON 数据

        Raises:
            ValueError: 不支持的 HTTP 方法
            Exception: 请求失败
        """
        token = self.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/wp-json{endpoint}"

        logger.debug(f"[WPCOMMemberAPI] {method} {url}")

        try:
            if method == "GET":
                response = httpx.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = httpx.post(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"不支持的方法: {method}")

            if response.status_code == 200:
                logger.debug(f"[WPCOMMemberAPI] 请求成功: {endpoint}")
                return response.json()
            else:
                error_msg = f"请求失败 ({response.status_code}): {response.text}"
                logger.error(f"[WPCOMMemberAPI] {error_msg}")
                raise Exception(error_msg)

        except httpx.TimeoutException:
            error_msg = f"请求超时（30秒）: {endpoint}"
            logger.error(f"[WPCOMMemberAPI] {error_msg}")
            raise Exception(error_msg)

        except Exception as e:
            logger.error(f"[WPCOMMemberAPI] 请求异常 {endpoint}: {e}")
            raise

    # ========== 会员信息 API ==========

    def get_my_membership(self) -> Dict[str, Any]:
        """
        获取当前用户会员信息

        获取当前登录用户（通过 JWT Token 识别）的会员信息

        Returns:
            Dict[str, Any]: 包含以下字段的字典：
                - user_id: 用户 ID
                - username: 用户名
                - nickname: 昵称
                - email: 邮箱
                - roles: 用户角色列表
                - membership: 会员信息（等级、状态、到期时间等）
                - user_group: 用户分组信息
                - wc_memberships: WooCommerce Memberships 信息
                - meta: 所有相关的用户元数据
        """
        logger.info("[WPCOMMemberAPI] 获取当前用户会员信息")
        return self._request("/custom/v1/my-membership")

    def get_user_membership(self, user_id: int) -> Dict[str, Any]:
        """
        获取指定用户会员信息

        Args:
            user_id: WordPress 用户 ID

        Returns:
            Dict[str, Any]: 会员信息字典（结构同 get_my_membership）

        示例返回数据：
            {
                "user_id": 1,
                "username": "admin",
                "nickname": "管理员",
                "email": "admin@example.com",
                "roles": ["administrator"],
                "membership": {
                    "level": "2",
                    "type": "premium",
                    "status": "active",
                    "expire_date": "2026-12-31 23:59:59",
                    "is_active": true,
                    "days_remaining": 365
                },
                "user_group": {
                    "id": 5,
                    "name": "VIP 会员",
                    "slug": "vip-member"
                },
                "wc_memberships": [],
                "meta": {...}
            }
        """
        logger.info(f"[WPCOMMemberAPI] 获取用户 {user_id} 会员信息")
        return self._request(f"/custom/v1/user-membership/{user_id}")

    # ========== 订单信息 API ==========

    def get_user_orders(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户订单列表

        获取用户的 WPCOM 订单和 WooCommerce 订单

        Args:
            user_id: WordPress 用户 ID

        Returns:
            Dict[str, Any]: 包含以下字段的字典：
                - user_id: 用户 ID
                - wpcom_orders: WPCOM 订单列表（最多 100 条）
                - wc_orders: WooCommerce 订单列表（最多 100 条）

        示例返回数据：
            {
                "user_id": 1,
                "wpcom_orders": [...],
                "wc_orders": [
                    {
                        "id": 123,
                        "status": "completed",
                        "total": "99.00",
                        "currency": "CNY",
                        "date_created": "2025-12-31 12:00:00",
                        "payment_method": "wechatpay",
                        "items": [...]
                    }
                ]
            }
        """
        logger.info(f"[WPCOMMemberAPI] 获取用户 {user_id} 订单列表")
        return self._request(f"/custom/v1/user-orders/{user_id}")

    # ========== 钱包信息 API ==========

    def get_user_wallet(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户钱包信息

        包括余额、积分、佣金、交易记录等

        Args:
            user_id: WordPress 用户 ID

        Returns:
            Dict[str, Any]: 包含以下字段的字典：
                - user_id: 用户 ID
                - balance: 可用余额（浮点数）
                - frozen: 冻结金额（浮点数）
                - total: 总计（可用 + 冻结）
                - points: 积分（整数）
                - commission: 佣金信息字典
                    - total: 累计佣金
                    - available: 可提现佣金
                    - withdrawn: 已提现佣金
                - records: 钱包交易记录列表（最多 100 条）

        示例返回数据：
            {
                "user_id": 1,
                "balance": 1000.00,
                "frozen": 0.00,
                "total": 1000.00,
                "points": 500,
                "commission": {
                    "total": 200.00,
                    "available": 100.00,
                    "withdrawn": 100.00
                },
                "records": [...]
            }
        """
        logger.info(f"[WPCOMMemberAPI] 获取用户 {user_id} 钱包信息")
        return self._request(f"/custom/v1/user-wallet/{user_id}")


# ========== 使用示例 ==========

if __name__ == "__main__":
    """
    测试脚本

    运行前确保 .env 文件已配置：
    - WORDPRESS_URL
    - WORDPRESS_ADMIN_USERNAME
    - WORDPRESS_ADMIN_PASSWORD
    """

    api = WPCOMMemberAPI()

    try:
        # 1. 获取当前用户会员信息
        print(" 当前用户会员信息:")
        membership = api.get_my_membership()

        print(f"  用户名: {membership['username']}")
        print(f"  昵称: {membership['nickname']}")
        print(f"  邮箱: {membership['email']}")

        if membership["membership"]:
            print(f"  会员等级: {membership['membership']['level']}")
            print(f"  会员状态: {membership['membership']['status']}")
            print(f"  到期时间: {membership['membership']['expire_date']}")
            print(f"  是否激活: {membership['membership']['is_active']}")
            print(f"  剩余天数: {membership['membership']['days_remaining']} 天")
        else:
            print("  ️ 未开通会员")

        # 2. 获取订单信息
        print("\n 订单信息:")
        user_id = membership["user_id"]
        orders = api.get_user_orders(user_id=user_id)

        wpcom_count = len(orders["wpcom_orders"])
        wc_count = len(orders["wc_orders"])

        print(f"  WPCOM 订单: {wpcom_count} 条")
        print(f"  WooCommerce 订单: {wc_count} 条")

        if wc_count > 0:
            latest_order = orders["wc_orders"][0]
            print("\n  最新订单:")
            print(f"    订单号: {latest_order['id']}")
            print(f"    状态: {latest_order['status']}")
            print(f"    金额: {latest_order['total']} {latest_order['currency']}")
            print(f"    时间: {latest_order['date_created']}")

        # 3. 获取钱包信息
        print("\n 钱包信息:")
        wallet = api.get_user_wallet(user_id=user_id)

        print(f"  可用余额: ¥{wallet['balance']:.2f}")
        print(f"  冻结金额: ¥{wallet['frozen']:.2f}")
        print(f"  总计: ¥{wallet['total']:.2f}")
        print(f"  积分: {wallet['points']}")

        print("\n  佣金信息:")
        print(f"    累计佣金: ¥{wallet['commission']['total']:.2f}")
        print(f"    可提现: ¥{wallet['commission']['available']:.2f}")
        print(f"    已提现: ¥{wallet['commission']['withdrawn']:.2f}")

        print("\n 所有测试通过！")

    except Exception as e:
        print(f"\n 错误: {e}")
        import traceback

        traceback.print_exc()
