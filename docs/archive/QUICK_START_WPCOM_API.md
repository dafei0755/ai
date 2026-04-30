# 🚀 WPCOM Member Pro API 快速开始指南

> 5分钟完成安装和测试

---

## 📋 准备工作

- [x] WordPress 已安装 WPCOM Member Pro 插件
- [x] Simple JWT Login 插件已配置（[查看配置方法](README_WORDPRESS_JWT_COMPLETE.md)）
- [x] Python 3.10+ 环境
- [x] `.env` 文件已配置

---

## 🔧 第1步：安装 PHP API（2分钟）

### 方法 A：通过插件安装（推荐）

1. **创建插件文件** `wpcom-custom-api.php`

复制 [wpcom_custom_api.php](wpcom_custom_api.php) 的完整代码

2. **添加插件头部**（在代码最前面）

```php
<?php
/**
 * Plugin Name: WPCOM Member Custom API
 * Description: 为 WPCOM Member Pro 提供 REST API 端点
 * Version: 1.0.0
 * Author: Your Name
 */

if (!defined('ABSPATH')) exit;

// 后面跟完整的 API 代码...
```

3. **压缩为 ZIP**

```bash
# Windows
右键 wpcom-custom-api.php → 发送到 → 压缩文件夹

# Linux/Mac
zip wpcom-custom-api.zip wpcom-custom-api.php
```

4. **上传激活**

```
WordPress 后台 → 插件 → 安装插件 → 上传插件
→ 选择 wpcom-custom-api.zip → 现在安装 → 激活
```

### 方法 B：添加到主题（更快）

1. WordPress 后台 → **外观 → 主题文件编辑器**
2. 选择 `functions.php`
3. 将 `wpcom_custom_api.php` 的代码粘贴到**文件末尾**
4. 点击**更新文件**

---

## 🧪 第2步：测试 API（1分钟）

```bash
python test_wpcom_api_final.py
```

**预期输出：**

```
✅ 成功: 4
⚠️ 警告: 0
❌ 失败: 0
```

---

## 📝 第3步：集成到项目（2分钟）

### 创建 API 客户端模块

保存为 `wpcom_member_api.py`：

```python
import httpx
from decouple import config
from typing import Dict, Any

class WPCOMMemberAPI:
    def __init__(self):
        self.base_url = config("WORDPRESS_URL")
        self.username = config("WORDPRESS_ADMIN_USERNAME")
        self.password = config("WORDPRESS_ADMIN_PASSWORD")
        self.token = None
    
    def get_token(self) -> str:
        if self.token:
            return self.token
        
        url = f"{self.base_url}/wp-json/simple-jwt-login/v1/auth"
        data = {"username": self.username, "password": self.password}
        response = httpx.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            self.token = response.json()["data"]["jwt"]
            return self.token
        else:
            raise Exception(f"Token获取失败: {response.text}")
    
    def _request(self, endpoint: str) -> Dict:
        token = self.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/wp-json{endpoint}"
        response = httpx.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"请求失败({response.status_code}): {response.text}")
    
    # API 方法
    def get_my_membership(self) -> Dict[str, Any]:
        """获取当前用户会员信息"""
        return self._request("/custom/v1/my-membership")
    
    def get_user_membership(self, user_id: int) -> Dict[str, Any]:
        """获取指定用户会员信息"""
        return self._request(f"/custom/v1/user-membership/{user_id}")
    
    def get_user_orders(self, user_id: int) -> Dict[str, Any]:
        """获取用户订单"""
        return self._request(f"/custom/v1/user-orders/{user_id}")
    
    def get_user_wallet(self, user_id: int) -> Dict[str, Any]:
        """获取用户钱包"""
        return self._request(f"/custom/v1/user-wallet/{user_id}")
```

### 使用示例

```python
from wpcom_member_api import WPCOMMemberAPI

api = WPCOMMemberAPI()

# 检查用户是否为会员
membership = api.get_user_membership(user_id=1)

if membership['membership'] and membership['membership']['is_active']:
    print(f"用户是 VIP{membership['membership']['level']} 会员")
    print(f"到期时间: {membership['membership']['expire_date']}")
else:
    print("用户不是会员")

# 获取钱包余额
wallet = api.get_user_wallet(user_id=1)
print(f"余额: ¥{wallet['balance']:.2f}")
```

---

## 🎯 常用场景代码

### 场景1：会员权限验证

```python
def check_vip_access(user_id: int, required_level: int = 1) -> bool:
    """检查用户是否有VIP权限"""
    api = WPCOMMemberAPI()
    membership = api.get_user_membership(user_id)
    
    if not membership['membership']:
        return False
    
    if not membership['membership']['is_active']:
        return False
    
    user_level = int(membership['membership']['level'])
    return user_level >= required_level

# 使用
if check_vip_access(user_id=1, required_level=2):
    print("允许访问高级功能")
else:
    print("需要VIP2及以上")
```

### 场景2：获取用户消费金额

```python
def get_user_total_spending(user_id: int) -> float:
    """获取用户累计消费金额"""
    api = WPCOMMemberAPI()
    orders = api.get_user_orders(user_id)
    
    total = 0.0
    
    # 统计 WooCommerce 订单
    for order in orders['wc_orders']:
        if order['status'] == 'completed':
            total += float(order['total'])
    
    # 统计 WPCOM 订单
    for order in orders['wpcom_orders']:
        if order.get('status') == 'completed':
            total += float(order.get('amount', 0))
    
    return total

# 使用
spending = get_user_total_spending(user_id=1)
print(f"累计消费: ¥{spending:.2f}")
```

### 场景3：会员到期提醒

```python
from datetime import datetime, timedelta

def check_membership_expiry(user_id: int) -> str:
    """检查会员到期状态"""
    api = WPCOMMemberAPI()
    membership = api.get_user_membership(user_id)
    
    if not membership['membership']:
        return "未开通会员"
    
    if not membership['membership']['is_active']:
        return "会员已过期"
    
    days_remaining = membership['membership']['days_remaining']
    
    if days_remaining <= 7:
        return f"⚠️ 会员即将过期（剩余{days_remaining}天）"
    elif days_remaining <= 30:
        return f"会员剩余{days_remaining}天"
    else:
        return f"会员正常（剩余{days_remaining}天）"

# 使用
status = check_membership_expiry(user_id=1)
print(status)
```

---

## ❓ 常见问题

### Q1: 端点返回 404？

**解决方案：**

1. 确认插件已激活
2. 进入 **设置 → 固定链接** → 点击**保存更改**
3. 重新测试

### Q2: 返回 401 未授权？

**检查：**

- JWT Token 是否正确获取
- Simple JWT Login 配置是否正确
- Token 是否过期（默认1小时）

### Q3: 会员信息为空？

**原因：** 用户可能还没有购买会员

**解决：**

1. 在 WordPress 后台创建测试会员
2. 或查看 `meta` 字段找到实际的数据存储key

### Q4: 需要添加新API？

在 `wpcom-custom-api.php` 中添加：

```php
register_rest_route('custom/v1', '/your-endpoint', array(
    'methods' => 'GET',
    'callback' => 'your_function',
    'permission_callback' => function() {
        return current_user_can('read');
    }
));

function your_function($request) {
    // 你的逻辑
    return new WP_REST_Response($data, 200);
}
```

---

## 📚 完整文档

- [详细文档](README_WORDPRESS_WPCOM_MEMBER.md)
- [JWT认证配置](README_WORDPRESS_JWT_COMPLETE.md)
- [测试脚本说明](test_wpcom_api_final.py)

---

## ✅ 安装成功标志

运行测试脚本后，您应该看到：

✅ 可以获取用户基本信息  
✅ 可以获取会员状态和等级  
✅ 可以获取订单列表  
✅ 可以获取钱包余额  

**恭喜！您已完成 WPCOM Member Pro API 集成！** 🎉

---

**最后更新**：2025-12-12  
**版本**：v1.0.0
