# 📚 WPCOM Member Pro API 集成文档索引

> 完整的会员系统 API 集成方案，5分钟快速开始

---

## 🚀 快速开始

**新用户从这里开始** → [快速开始指南](QUICK_START_WPCOM_API.md) ⭐

---

## 📖 完整文档

### 1. 核心文档

| 文档 | 说明 | 适用对象 |
|------|------|---------|
| [快速开始指南](QUICK_START_WPCOM_API.md) | 5分钟完成安装和测试 | **新用户必读** ⭐ |
| [完整集成方案](README_WORDPRESS_WPCOM_MEMBER.md) | 详细的技术文档（1500行） | 技术人员参考 |
| [JWT 认证配置](README_WORDPRESS_JWT_COMPLETE.md) | Simple JWT Login 完整配置 | 首次配置必读 |

### 2. 代码文件

| 文件 | 说明 | 用途 |
|------|------|------|
| [wpcom-custom-api.php](wpcom-custom-api.php) | PHP 插件（完整代码） | 上传到 WordPress |
| [test_wpcom_api_final.py](test_wpcom_api_final.py) | 完整测试脚本 | 验证 API 可用性 |
| [diagnose_wpcom_member.py](diagnose_wpcom_member.py) | 诊断工具 | 排查问题 |

### 3. 参考文档

| 文档 | 说明 |
|------|------|
| [WordPress JWT 实施总结](README_WORDPRESS_JWT.md) | JWT 认证原理 |
| [WordPress 安全配置](WORDPRESS_JWT_AUTH_GUIDE.md) | 安全最佳实践 |

---

## 🎯 按场景查找

### 场景 1：首次安装

1. ✅ 配置 JWT 认证 → [JWT 认证配置](README_WORDPRESS_JWT_COMPLETE.md)
2. ✅ 安装 PHP API → [快速开始 - 第1步](QUICK_START_WPCOM_API.md#%F0%9F%94%A7-%E7%AC%AC1%E6%AD%A5%E5%AE%89%E8%A3%85-php-api2%E5%88%86%E9%92%9F)
3. ✅ 测试 API → [快速开始 - 第2步](QUICK_START_WPCOM_API.md#%F0%9F%A7%AA-%E7%AC%AC2%E6%AD%A5%E6%B5%8B%E8%AF%95-api1%E5%88%86%E9%92%9F)

### 场景 2：集成到项目

1. ✅ 创建 API 客户端 → [快速开始 - 第3步](QUICK_START_WPCOM_API.md#%F0%9F%93%9D-%E7%AC%AC3%E6%AD%A5%E9%9B%86%E6%88%90%E5%88%B0%E9%A1%B9%E7%9B%AE2%E5%88%86%E9%92%9F)
2. ✅ 常用场景代码 → [快速开始 - 常用场景](QUICK_START_WPCOM_API.md#%F0%9F%8E%AF-%E5%B8%B8%E7%94%A8%E5%9C%BA%E6%99%AF%E4%BB%A3%E7%A0%81)

### 场景 3：排查问题

1. ✅ 常见问题 FAQ → [快速开始 - 常见问题](QUICK_START_WPCOM_API.md#%E2%9D%93-%E5%B8%B8%E8%A7%81%E9%97%AE%E9%A2%98)
2. ✅ 运行诊断工具 → [诊断工具使用](README_WORDPRESS_WPCOM_MEMBER.md#%E8%AF%8A%E6%96%AD%E5%B7%A5%E5%85%B7)

### 场景 4：API 定制

1. ✅ 添加新端点 → [完整集成方案 - API 端点说明](README_WORDPRESS_WPCOM_MEMBER.md#4-api-%E7%AB%AF%E7%82%B9%E8%AF%B4%E6%98%8E)
2. ✅ 修改返回数据 → [wpcom-custom-api.php](wpcom-custom-api.php)

---

## 🔥 核心功能

### API 端点（4个）

| 端点 | 功能 | 返回数据 |
|------|------|---------|
| `GET /custom/v1/my-membership` | 获取当前用户会员信息 | 用户信息、会员等级/状态/到期、用户分组、所有 meta |
| `GET /custom/v1/user-membership/{id}` | 获取指定用户会员信息 | 同上 |
| `GET /custom/v1/user-orders/{id}` | 获取用户订单 | WPCOM 订单 + WooCommerce 订单 |
| `GET /custom/v1/user-wallet/{id}` | 获取用户钱包 | 余额、积分、佣金、交易记录 |

### Python 客户端方法

```python
from wpcom_member_api import WPCOMMemberAPI

api = WPCOMMemberAPI()

# 4 个核心方法
api.get_my_membership()         # 当前用户会员信息
api.get_user_membership(1)      # 指定用户会员信息
api.get_user_orders(1)          # 用户订单
api.get_user_wallet(1)          # 用户钱包
```

### 常用场景函数

- ✅ `check_vip_access(user_id, required_level)` - 会员权限验证
- ✅ `get_user_total_spending(user_id)` - 累计消费金额
- ✅ `check_membership_expiry(user_id)` - 会员到期提醒

---

## 📋 安装检查清单

### 前置条件

- [x] WordPress 站点已搭建
- [x] WPCOM Member Pro 插件已安装
- [x] Simple JWT Login 插件已安装
- [x] Python 3.10+ 环境
- [x] `.env` 文件已配置

### 安装步骤

- [ ] 步骤1：配置 Simple JWT Login
  - [ ] 设置 JWT Parameter Key 为 `username`
  - [ ] 启用 Auth Codes
  - [ ] 测试 Token 获取
- [ ] 步骤2：安装 `wpcom-custom-api.php`
  - [ ] 压缩为 ZIP
  - [ ] 上传激活
  - [ ] 刷新固定链接
- [ ] 步骤3：测试 API
  - [ ] 运行 `python test_wpcom_api_final.py`
  - [ ] 确认 4/4 端点成功
- [ ] 步骤4：集成到项目
  - [ ] 创建 `wpcom_member_api.py`
  - [ ] 测试会员信息查询
  - [ ] 测试订单和钱包查询

---

## ❓ 常见问题（FAQ）

### Q1: API 返回 404？

**原因**：
- 插件未激活
- REST API 路由未刷新

**解决方案**：
```
WordPress 后台 → 设置 → 固定链接 → 保存更改
```

### Q2: 返回 401 未授权？

**原因**：
- JWT Token 未获取
- Token 已过期
- Simple JWT Login 配置错误

**解决方案**：
1. 检查 `.env` 配置
2. 测试 Token 获取：`python test_wordpress_jwt.py`
3. 查看 [JWT 认证配置](README_WORDPRESS_JWT_COMPLETE.md)

### Q3: 会员信息为空？

**原因**：
- 用户未购买会员
- Meta key 名称不匹配

**解决方案**：
1. 查看 `meta` 字段找到实际的 key
2. 修改 `wpcom-custom-api.php` 中的 meta key
3. 在 WordPress 后台手动设置测试数据

### Q4: 需要添加新功能？

**方案**：
1. 修改 `wpcom-custom-api.php` 添加新端点
2. 更新 `wpcom_member_api.py` 添加新方法
3. 刷新固定链接重新测试

---

## 🆘 获取帮助

### 调试工具

```bash
# 1. 运行完整诊断
python diagnose_wpcom_member.py

# 2. 测试 JWT Token
python diagnose_jwt_token.py

# 3. 测试 API 端点
python test_wpcom_api_final.py
```

### 日志位置

- **WordPress 日志**：`wp-content/debug.log`（需启用 WP_DEBUG）
- **REST API 请求**：浏览器开发者工具 → Network
- **Python 输出**：终端控制台

### 联系支持

- **WPCOM Member Pro**：https://www.wpcom.cn/
- **Simple JWT Login**：https://wordpress.org/plugins/simple-jwt-login/
- **技术讨论**：GitHub Issues

---

## 🎉 完成标志

安装成功后，您应该能够：

✅ 通过 Python 获取用户会员信息  
✅ 查询用户订单列表���WPCOM + WooCommerce）  
✅ 获取用户钱包余额和佣金  
✅ 在项目中实现会员权限验证  

**恭喜！您已完成 WPCOM Member Pro API 集成！** 🎉

---

## 📅 更新记录

| 日期 | 版本 | 更新内容 |
|------|------|---------|
| 2025-12-12 | v1.0.0 | 初始版本，完整功能实现 |

---

**技术栈**：
- WordPress 6.x
- WPCOM Member Pro（用户中心高级版）
- Simple JWT Login v3.7.6
- Python 3.10+
- HTTPX

**兼容性**：
- ✅ WordPress 6.0+
- ✅ PHP 7.4+
- ✅ WooCommerce 7.0+（可选）
- ✅ WooCommerce Memberships（可选）

---

**最后更新**：2025-12-12  
**维护者**：Your Name  
**License**：GPL v2 or later
