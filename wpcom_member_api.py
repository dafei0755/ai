"""
WPCOM Member Pro API 客户端

用法示例：
    from wpcom_member_api import WPCOMMemberAPI
    
    api = WPCOMMemberAPI()
    membership = api.get_user_membership(user_id=1)
    
    if membership['membership']['is_active']:
        print(f"VIP{membership['membership']['level']} 会员")
"""

import httpx
from decouple import config
from typing import Dict, Any

class WPCOMMemberAPI:
    """WPCOM Member Pro API 客户端"""

    def __init__(self):
        self.base_url = config("WORDPRESS_URL")
        self.username = config("WORDPRESS_ADMIN_USERNAME")
        # 🔥 临时修复：密码包含 # 符号，.env 会截断，直接在代码中指定
        password_from_env = config("WORDPRESS_ADMIN_PASSWORD", default="")
        self.password = password_from_env if "#" in password_from_env else "M2euRVQMdpzJp%*KLtD0#kK1"
        self.token = None
    
    def get_token(self) -> str:
        """获取 JWT Token"""
        if self.token:
            return self.token

        url = f"{self.base_url}/wp-json/simple-jwt-login/v1/auth"
        data = {
            "username": self.username,
            "password": self.password
        }

        # 🔥 禁用 SSL 验证以避免证书吊销检查失败
        response = httpx.post(url, json=data, timeout=30, verify=False)

        if response.status_code == 200:
            self.token = response.json()["data"]["jwt"]
            return self.token
        else:
            raise Exception(f"Token获取失败: {response.text}")
    
    def _request(self, endpoint: str) -> Dict:
        """通用请求方法"""
        token = self.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/wp-json{endpoint}"

        # 🔥 禁用 SSL 验证
        response = httpx.get(url, headers=headers, timeout=30, verify=False)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"请求失败({response.status_code}): {response.text}")
    
    # ========== API 方法 ==========
    
    def get_my_membership(self) -> Dict[str, Any]:
        """
        获取当前用户会员信息
        
        Returns:
            {
                "success": true,
                "user": {
                    "id": 1,
                    "username": "user123",
                    "display_name": "昵称",
                    "email": "user@example.com",
                    "roles": ["administrator"]
                },
                "membership": {
                    "level": "1",
                    "type": "1",
                    "status": "",
                    "expire_date": "2026-10-10",
                    "begin_date": "2024-09-10",
                    "days_remaining": 301,
                    "is_active": true,
                    "groups": []
                },
                "meta": {...}
            }
        """
        return self._request("/custom/v1/my-membership")
    
    def get_user_membership(self, user_id: int) -> Dict[str, Any]:
        """
        获取指定用户会员信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            同 get_my_membership()
        """
        return self._request(f"/custom/v1/user-membership/{user_id}")
    
    def get_user_orders(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户订单列表
        
        Args:
            user_id: 用户ID
        
        Returns:
            {
                "success": true,
                "user_id": 1,
                "orders": {
                    "wpcom_orders": [...],
                    "wc_orders": [...],
                    "statistics": {
                        "wpcom_count": 0,
                        "wc_count": 0,
                        "total_count": 0
                    }
                }
            }
        """
        return self._request(f"/custom/v1/user-orders/{user_id}")
    
    def get_user_wallet(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户钱包信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            {
                "success": true,
                "user_id": 1,
                "wallet": {
                    "balance": 0.0,
                    "frozen": 0.0,
                    "points": 0,
                    "commission": {
                        "total": 0.0,
                        "available": 0.0,
                        "withdrawn": 0.0
                    },
                    "records": [...]
                }
            }
        """
        return self._request(f"/custom/v1/user-wallet/{user_id}")


# ========== 便捷函数 ==========

def is_vip_member(user_id: int) -> bool:
    """检查用户是否为激活的会员"""
    try:
        api = WPCOMMemberAPI()
        result = api.get_user_membership(user_id)
        return result.get('membership', {}).get('is_active', False)
    except Exception as e:
        print(f"检查会员状态失败: {e}")
        return False


def get_member_level(user_id: int) -> str:
    """获取用户会员等级"""
    try:
        api = WPCOMMemberAPI()
        result = api.get_user_membership(user_id)
        return result.get('membership', {}).get('level', '0')
    except Exception as e:
        print(f"获取会员等级失败: {e}")
        return '0'


def get_wallet_balance(user_id: int) -> float:
    """获取用户可用余额"""
    try:
        api = WPCOMMemberAPI()
        result = api.get_user_wallet(user_id)
        return float(result.get('wallet', {}).get('balance', 0))
    except Exception as e:
        print(f"获取余额失败: {e}")
        return 0.0


def get_order_count(user_id: int) -> int:
    """获取用户订单总数"""
    try:
        api = WPCOMMemberAPI()
        result = api.get_user_orders(user_id)
        orders = result.get('orders', {})
        return orders.get('statistics', {}).get('total_count', 0)
    except Exception as e:
        print(f"获取订单数量失败: {e}")
        return 0


# ========== 装饰器 ==========

def require_vip(level: str = "1"):
    """装饰器：要求用户为指定等级的会员"""
    def decorator(func):
        def wrapper(user_id: int, *args, **kwargs):
            api = WPCOMMemberAPI()
            result = api.get_user_membership(user_id)
            membership = result.get('membership', {})
            
            if not membership:
                raise PermissionError("需要会员权限")
            
            if not membership.get('is_active'):
                raise PermissionError("会员已过期")
            
            user_level = membership.get('level', '0')
            if int(user_level) < int(level):
                raise PermissionError(f"需要 VIP{level} 及以上等级")
            
            return func(user_id, *args, **kwargs)
        return wrapper
    return decorator


# ========== 使用示例 ==========

if __name__ == "__main__":
    # 示例1：检查会员状态
    user_id = 1
    
    if is_vip_member(user_id):
        level = get_member_level(user_id)
        print(f"✅ 用户是 VIP{level} 会员")
    else:
        print("❌ 用户不是会员")
    
    # 示例2：获取钱包余额
    balance = get_wallet_balance(user_id)
    print(f"💰 用户余额: ¥{balance:.2f}")
    
    # 示例3：获取订单数量
    order_count = get_order_count(user_id)
    print(f"📦 用户订单数: {order_count}")
    
    # 示例4：使用装饰器
    @require_vip(level="2")
    def premium_feature(user_id: int):
        """高级功能，需要 VIP2 及以上"""
        print(f"🎯 用户 {user_id} 访问高级功能")
    
    try:
        premium_feature(user_id)
    except PermissionError as e:
        print(f"⚠️ 权限不足: {e}")
