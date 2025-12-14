# WPCOM Member Pro 用户中心集成方案

> 📅 创建日期：2025-12-12  
> 🎯 目标：实现 Python 程序调用 WPCOM Member Pro 用户中心的会员和付费信息

---

## 📋 目录

1. [方案概述](#方案概述)
2. [安装自定义 PHP API](#安装自定义-php-api)
3. [Python 客户端使用](#python-客户端使用)
4. [API 端点说明](#api-端点说明)
5. [完整示例代码](#完整示例代码)
6. [常见问题](#常见问题)

---

## 1. 方案概述

### 为什么需要自定义 API？

WPCOM Member Pro 插件**没有提供公开的 REST API**，但会员、订单、钱包等数据存储在 WordPress 数据库中。通过创建自定义 PHP API 端点，我们可以：

✅ 直接查询数据库表  
✅ 读取用户元数据（user meta）  
✅ 兼容 WooCommerce Memberships（如果使用）  
✅ 安全认证（JWT Token）  

### 数据存储位置

根据 WPCOM Member Pro 文档，数据主要存储在：

| 数据类型 | 存储位置 |
|---------|---------|
| **用户基本信息** | `wp_users` 表 |
| **会员等级/状态** | `wp_usermeta` 表（meta key: `vip_level`, `vip_status`, `vip_expire`） |
| **用户分组** | `wp_term_relationships` + `wp_terms`（分类系统） |
| **订单记录** | `wp_wpcom_orders` 表（如果存在）或 WooCommerce 订单 |
| **钱包余额** | `wp_usermeta`（meta key: `wallet_balance`, `wallet_frozen`） |
| **钱包交易** | `wp_wpcom_wallet_records` 表（如果存在） |
| **佣金信息** | `wp_usermeta` 或 `wp_wpcom_commission` 表 |

---

## 2. 安装自定义 PHP API

### 方法 A：创建独立插件（推荐）

**步骤：**

1. **创建插件文件**

在您的电脑上创建文件 `wpcom-custom-api.php`，内容如下：

```php
<?php
/**
 * Plugin Name: WPCOM Member Custom API
 * Description: 为 WPCOM Member Pro 提供 REST API 端点
 * Version: 1.0.0
 * Author: Your Name
 */

// 防止直接访问
if (!defined('ABSPATH')) {
    exit;
}

// 注册 REST API 端点
add_action('rest_api_init', function () {
    // 获取当前用户会员信息
    register_rest_route('custom/v1', '/my-membership', array(
        'methods' => 'GET',
        'callback' => 'wpcom_get_current_user_membership',
        'permission_callback' => function() {
            return is_user_logged_in();
        }
    ));
    
    // 获取指定用户会员信息
    register_rest_route('custom/v1', '/user-membership/(?P<id>\d+)', array(
        'methods' => 'GET',
        'callback' => 'wpcom_get_user_membership',
        'permission_callback' => function() {
            return current_user_can('read');
        }
    ));
    
    // 获取用户订单
    register_rest_route('custom/v1', '/user-orders/(?P<id>\d+)', array(
        'methods' => 'GET',
        'callback' => 'wpcom_get_user_orders',
        'permission_callback' => function() {
            return current_user_can('read');
        }
    ));
    
    // 获取用户钱包
    register_rest_route('custom/v1', '/user-wallet/(?P<id>\d+)', array(
        'methods' => 'GET',
        'callback' => 'wpcom_get_user_wallet',
        'permission_callback' => function() {
            return current_user_can('read');
        }
    ));
});

/**
 * 获取当前用户会员信息
 */
function wpcom_get_current_user_membership($request) {
    $user_id = get_current_user_id();
    $request['id'] = $user_id;
    return wpcom_get_user_membership($request);
}

/**
 * 获取用户会员信息
 */
function wpcom_get_user_membership($request) {
    global $wpdb;
    $user_id = $request['id'];
    
    // 获取用户基本信息
    $user = get_userdata($user_id);
    if (!$user) {
        return new WP_Error('user_not_found', '用户不存在', array('status' => 404));
    }
    
    $result = array(
        'user_id' => $user_id,
        'username' => $user->user_login,
        'nickname' => $user->display_name,
        'email' => $user->user_email,
        'roles' => $user->roles,
        'membership' => null,
        'user_group' => null,
        'wc_memberships' => array(),
        'meta' => array()
    );
    
    // 1. 获取 WPCOM 会员信息（从 user meta）
    $vip_level = get_user_meta($user_id, 'vip_level', true);
    $vip_expire = get_user_meta($user_id, 'vip_expire', true);
    $vip_status = get_user_meta($user_id, 'vip_status', true);
    $vip_type = get_user_meta($user_id, 'vip_type', true);
    
    if ($vip_level || $vip_expire || $vip_status) {
        $is_active = false;
        if ($vip_status === 'active' && $vip_expire) {
            $is_active = time() < strtotime($vip_expire);
        }
        
        $result['membership'] = array(
            'level' => $vip_level,
            'type' => $vip_type,
            'status' => $vip_status,
            'expire_date' => $vip_expire,
            'is_active' => $is_active,
            'days_remaining' => $is_active ? ceil((strtotime($vip_expire) - time()) / 86400) : 0
        );
    }
    
    // 2. 获取用户分组
    $user_groups = wp_get_object_terms($user_id, 'wpcom-member-group', array('fields' => 'all'));
    if (!empty($user_groups) && !is_wp_error($user_groups)) {
        $result['user_group'] = array(
            'id' => $user_groups[0]->term_id,
            'name' => $user_groups[0]->name,
            'slug' => $user_groups[0]->slug,
            'description' => $user_groups[0]->description
        );
    }
    
    // 3. 获取 WooCommerce Memberships（如果安装）
    if (function_exists('wc_memberships_get_user_memberships')) {
        $wc_memberships = wc_memberships_get_user_memberships($user_id);
        
        foreach ($wc_memberships as $membership) {
            $result['wc_memberships'][] = array(
                'id' => $membership->get_id(),
                'plan_id' => $membership->get_plan_id(),
                'plan_name' => $membership->get_plan()->get_name(),
                'status' => $membership->get_status(),
                'start_date' => $membership->get_start_date('Y-m-d H:i:s'),
                'end_date' => $membership->get_end_date('Y-m-d H:i:s'),
                'is_active' => $membership->is_active()
            );
        }
    }
    
    // 4. 获取所有会员相关的 meta
    $all_meta = get_user_meta($user_id);
    $member_keywords = array('vip', 'member', 'wallet', 'point', 'commission', 'wpcom');
    
    foreach ($all_meta as $key => $value) {
        foreach ($member_keywords as $keyword) {
            if (stripos($key, $keyword) !== false) {
                $result['meta'][$key] = maybe_unserialize($value[0]);
                break;
            }
        }
    }
    
    return new WP_REST_Response($result, 200);
}

/**
 * 获取用户订单
 */
function wpcom_get_user_orders($request) {
    global $wpdb;
    $user_id = $request['id'];
    
    $result = array(
        'user_id' => $user_id,
        'wpcom_orders' => array(),
        'wc_orders' => array()
    );
    
    // 1. 查询 WPCOM 订单表（如果存在）
    $table_name = $wpdb->prefix . 'wpcom_orders';
    if ($wpdb->get_var("SHOW TABLES LIKE '$table_name'") == $table_name) {
        $orders = $wpdb->get_results($wpdb->prepare(
            "SELECT * FROM $table_name WHERE user_id = %d ORDER BY created_at DESC LIMIT 100",
            $user_id
        ), ARRAY_A);
        
        $result['wpcom_orders'] = $orders;
    }
    
    // 2. 查询 WooCommerce 订单
    if (function_exists('wc_get_orders')) {
        $wc_orders = wc_get_orders(array(
            'customer_id' => $user_id,
            'limit' => 100,
            'orderby' => 'date',
            'order' => 'DESC'
        ));
        
        foreach ($wc_orders as $order) {
            $order_data = array(
                'id' => $order->get_id(),
                'status' => $order->get_status(),
                'total' => $order->get_total(),
                'currency' => $order->get_currency(),
                'date_created' => $order->get_date_created()->date('Y-m-d H:i:s'),
                'payment_method' => $order->get_payment_method(),
                'payment_method_title' => $order->get_payment_method_title(),
                'items' => array()
            );
            
            foreach ($order->get_items() as $item) {
                $order_data['items'][] = array(
                    'name' => $item->get_name(),
                    'quantity' => $item->get_quantity(),
                    'total' => $item->get_total()
                );
            }
            
            $result['wc_orders'][] = $order_data;
        }
    }
    
    return new WP_REST_Response($result, 200);
}

/**
 * 获取用户钱包信息
 */
function wpcom_get_user_wallet($request) {
    global $wpdb;
    $user_id = $request['id'];
    
    $result = array(
        'user_id' => $user_id,
        'balance' => 0,
        'frozen' => 0,
        'total' => 0,
        'points' => 0,
        'commission' => array(
            'total' => 0,
            'available' => 0,
            'withdrawn' => 0
        ),
        'records' => array()
    );
    
    // 1. 获取钱包余额
    $balance = get_user_meta($user_id, 'wallet_balance', true);
    $frozen = get_user_meta($user_id, 'wallet_frozen', true);
    
    $result['balance'] = $balance ? floatval($balance) : 0;
    $result['frozen'] = $frozen ? floatval($frozen) : 0;
    $result['total'] = $result['balance'] + $result['frozen'];
    
    // 2. 获取积分
    $points = get_user_meta($user_id, 'wpcom_points', true);
    $result['points'] = $points ? intval($points) : 0;
    
    // 3. 获取佣金信息
    $commission_total = get_user_meta($user_id, 'wpcom_commission_total', true);
    $commission_available = get_user_meta($user_id, 'wpcom_commission_available', true);
    $commission_withdrawn = get_user_meta($user_id, 'wpcom_commission_withdrawn', true);
    
    $result['commission'] = array(
        'total' => $commission_total ? floatval($commission_total) : 0,
        'available' => $commission_available ? floatval($commission_available) : 0,
        'withdrawn' => $commission_withdrawn ? floatval($commission_withdrawn) : 0
    );
    
    // 4. 获取钱包交易记录（如果表存在）
    $table_name = $wpdb->prefix . 'wpcom_wallet_records';
    if ($wpdb->get_var("SHOW TABLES LIKE '$table_name'") == $table_name) {
        $records = $wpdb->get_results($wpdb->prepare(
            "SELECT * FROM $table_name WHERE user_id = %d ORDER BY created_at DESC LIMIT 100",
            $user_id
        ), ARRAY_A);
        
        $result['records'] = $records;
    }
    
    return new WP_REST_Response($result, 200);
}
```

2. **压缩为 ZIP 文件**

将 `wpcom-custom-api.php` 压缩为 `wpcom-custom-api.zip`

3. **上传到 WordPress**

```
WordPress 后台 → 插件 → 安装插件 → 上传插件
选择 wpcom-custom-api.zip → 现在安装 → 激活插件
```

---

### 方法 B：添加到主题 functions.php

1. 进入 WordPress 后台
2. **外观 → 主题文件编辑器**
3. 找到 `functions.php` 文件
4. 将上面的 PHP 代码（去掉插件头部注释）粘贴到文件**末尾**
5. 点击**更新文件**

---

## 3. Python 客户端使用

### 安装依赖

```bash
pip install httpx python-decouple
```

### 配置 `.env`

```env
WORDPRESS_URL=https://www.ucppt.com
WORDPRESS_ADMIN_USERNAME=8pdwoxj8
WORDPRESS_ADMIN_PASSWORD=M2euRVQMdpzJp%*KLtD0#kK1
```

### Python 客户端代码

```python
import httpx
from decouple import config
from typing import Dict, Any, Optional

class WPCOMMemberAPI:
    """WPCOM Member Pro API 客户端"""
    
    def __init__(self):
        self.base_url = config("WORDPRESS_URL")
        self.username = config("WORDPRESS_ADMIN_USERNAME")
        self.password = config("WORDPRESS_ADMIN_PASSWORD")
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
        
        response = httpx.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            self.token = response.json()["data"]["jwt"]
            return self.token
        else:
            raise Exception(f"Token 获取失败: {response.text}")
    
    def _request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
        """通用请求方法"""
        token = self.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/wp-json{endpoint}"
        
        if method == "GET":
            response = httpx.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = httpx.post(url, headers=headers, json=data, timeout=30)
        else:
            raise ValueError(f"不支持的方法: {method}")
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"请求失败 ({response.status_code}): {response.text}")
    
    # ========== 会员信息 API ==========
    
    def get_my_membership(self) -> Dict[str, Any]:
        """获取当前用户会员信息"""
        return self._request("/custom/v1/my-membership")
    
    def get_user_membership(self, user_id: int) -> Dict[str, Any]:
        """获取指定用户会员信息"""
        return self._request(f"/custom/v1/user-membership/{user_id}")
    
    # ========== 订单信息 API ==========
    
    def get_user_orders(self, user_id: int) -> Dict[str, Any]:
        """获取用户订单"""
        return self._request(f"/custom/v1/user-orders/{user_id}")
    
    # ========== 钱包信息 API ==========
    
    def get_user_wallet(self, user_id: int) -> Dict[str, Any]:
        """获取用户钱包信息"""
        return self._request(f"/custom/v1/user-wallet/{user_id}")


# ========== 使用示例 ==========

if __name__ == "__main__":
    api = WPCOMMemberAPI()
    
    try:
        # 1. 获取当前用户会员信息
        print("📋 当前用户会员信息:")
        membership = api.get_my_membership()
        
        print(f"  用户名: {membership['username']}")
        print(f"  昵称: {membership['nickname']}")
        print(f"  邮箱: {membership['email']}")
        
        if membership['membership']:
            print(f"  会员等级: {membership['membership']['level']}")
            print(f"  会员状态: {membership['membership']['status']}")
            print(f"  到期时间: {membership['membership']['expire_date']}")
            print(f"  是否激活: {membership['membership']['is_active']}")
            print(f"  剩余天数: {membership['membership']['days_remaining']} 天")
        else:
            print("  ⚠️ 未开通会员")
        
        # 2. 获取订单信息
        print("\n📦 订单信息:")
        orders = api.get_user_orders(user_id=1)
        
        wpcom_count = len(orders['wpcom_orders'])
        wc_count = len(orders['wc_orders'])
        
        print(f"  WPCOM 订单: {wpcom_count} 条")
        print(f"  WooCommerce 订单: {wc_count} 条")
        
        if wc_count > 0:
            latest_order = orders['wc_orders'][0]
            print(f"\n  最新订单:")
            print(f"    订单号: {latest_order['id']}")
            print(f"    状态: {latest_order['status']}")
            print(f"    金额: {latest_order['total']} {latest_order['currency']}")
            print(f"    时间: {latest_order['date_created']}")
        
        # 3. 获取钱包信息
        print("\n💰 钱包信息:")
        wallet = api.get_user_wallet(user_id=1)
        
        print(f"  可用余额: ¥{wallet['balance']:.2f}")
        print(f"  冻结金额: ¥{wallet['frozen']:.2f}")
        print(f"  总计: ¥{wallet['total']:.2f}")
        print(f"  积分: {wallet['points']}")
        
        print(f"\n  佣金信息:")
        print(f"    累计佣金: ¥{wallet['commission']['total']:.2f}")
        print(f"    可提现: ¥{wallet['commission']['available']:.2f}")
        print(f"    已提现: ¥{wallet['commission']['withdrawn']:.2f}")
    
    except Exception as e:
        print(f"❌ 错误: {e}")
```

---

## 4. API 端点说明

| 端点 | 方法 | 说明 | 返回数据 |
|------|------|------|---------|
| `/custom/v1/my-membership` | GET | 获取当前用户会员信息 | 会员等级、状态、到期时间、用户分组、所有相关 meta |
| `/custom/v1/user-membership/{user_id}` | GET | 获取指定用户会员信息 | 同上 |
| `/custom/v1/user-orders/{user_id}` | GET | 获取用户订单列表 | WPCOM 订单 + WooCommerce 订单 |
| `/custom/v1/user-wallet/{user_id}` | GET | 获取用户钱包信息 | 余额、积分、佣金、交易记录 |

### 会员信息返回结构

```json
{
  "user_id": 1,
  "username": "8pdwoxj8",
  "nickname": "宋词",
  "email": "42841287@qq.com",
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
    "slug": "vip-member",
    "description": "高级会员分组"
  },
  "wc_memberships": [],
  "meta": {
    "vip_level": "2",
    "vip_status": "active",
    "wallet_balance": "1000.00",
    "wpcom_points": "500"
  }
}
```

---

## 5. 完整示例代码

已创建测试脚本：`test_wpcom_api_final.py`

运行测试：
```bash
python test_wpcom_api_final.py
```

---

## 6. 常见问题

### Q1: 安装插件后端点返回 404？

**解决方案**：
1. 确认插件已激活
2. 进入 **设置 → 固定链接**，点击**保存更改**（刷新 REST API 路由）
3. 清空浏览器缓存

### Q2: 返回 401 未授权错误？

**检查项**：
1. JWT Token 是否正确获取
2. Simple JWT Login 插件是否正常配置
3. Token 是否过期（默认 1 小时）

### Q3: 会员信息为空（null）？

**原因**：
- 当前用户可能还没有购买会员
- 会员数据存储的 meta key 可能不同

**解决方案**：
1. 在 WordPress 后台创建测试会员订单
2. 查看 `meta` 字段中的所有数据，找到实际的 meta key
3. 修改 PHP 代码中的 meta key（如 `vip_level` 改为实际key）

### Q4: 如何查看所有用户的元数据字段？

运行以下 SQL（在 phpMyAdmin 或 MySQL 客户端）：

```sql
SELECT meta_key, COUNT(*) as count 
FROM wp_usermeta 
WHERE user_id = 1 
GROUP BY meta_key 
ORDER BY meta_key;
```

### Q5: 钱包交易记录为空？

**原因**：`wp_wpcom_wallet_records` 表可能不存在或表名不同

**解决方案**：
1. 查看数据库中的表：`SHOW TABLES LIKE '%wallet%';`
2. 修改 PHP 代码中的表名

### Q6: 如何添加新的 API 端点？

在 `wpcom-custom-api.php` 中添加：

```php
register_rest_route('custom/v1', '/your-endpoint', array(
    'methods' => 'GET',
    'callback' => 'your_callback_function',
    'permission_callback' => function() {
        return current_user_can('read');
    }
));

function your_callback_function($request) {
    // 你的逻辑
    return new WP_REST_Response($data, 200);
}
```

---

## 📞 技术支持

如遇到问题，请提供：
1. 错误日志（HTTP 状态码和错误信息）
2. WordPress 版本
3. WPCOM Member Pro 插件版本
4. 测试脚本的完整输出

---

## 📚 相关文档

- [WPCOM 官方文档](https://www.wpcom.cn/docs/)
- [WordPress REST API 手册](https://developer.wordpress.org/rest-api/)
- [Simple JWT Login 文档](README_WORDPRESS_JWT_COMPLETE.md)

---

**最后更新**：2025-12-12  
**版本**：v1.0.0
