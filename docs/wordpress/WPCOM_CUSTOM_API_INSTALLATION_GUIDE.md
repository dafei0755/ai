# WPCOM Member Custom API 插件安装指南

## 📦 插件信息

- **插件名称**: WPCOM Member Custom API
- **版本**: 1.0.0
- **功能**: 为 WPCOM Member Pro 提供 REST API 端点，供 Next.js 前端调用

---

## ✅ 已完成的配置

### 1. Simple JWT Login 插件 Authentication 功能 ✅
- **状态**: 已成功启用
- **端点**: `/wp-json/simple-jwt-login/v1/auth` ✅ 可用
- **JWT 密钥**: `YOUR_JWT_SECRET_KEY` (HS256)
- **测试结果**: Token 获取成功！

### 2. Python 后端配置 ✅
- **JWT_SECRET_KEY**: 已同步为 `YOUR_JWT_SECRET_KEY`
- **wpcom_member_api.py**: 已修复（SSL 验证、密码解析）
- **后端服务**: ✅ 正在运行（8000端口）

---

## 📥 安装步骤

### 方式一：通过 WordPress 后台安装（推荐）

1. **下载插件**
   - 文件名: `wpcom-custom-api-v1.0.0.zip`
   - 位置: 项目根目录

2. **上传安装**
   - WordPress 后台 → **插件** → **安装插件**
   - 点击 **上传插件** 按钮
   - 选择 `wpcom-custom-api-v1.0.0.zip` 文件
   - 点击 **现在安装**

3. **激活插件**
   - 安装完成后，点击 **激活插件**
   - 看到 "插件已激活" 提示即成功

### 方式二：通过 FTP/SFTP 手动安装

1. **解压插件文件**
   ```bash
   unzip wpcom-custom-api-v1.0.0.zip
   ```

2. **上传到 WordPress**
   ```bash
   # 将 wpcom-custom-api 文件夹上传到：
   /path/to/wordpress/wp-content/plugins/wpcom-custom-api/
   ```

3. **激活插件**
   - WordPress 后台 → **插件** → **已安装的插件**
   - 找到 **WPCOM Member Custom API**
   - 点击 **启用**

---

## 🧪 验证安装

### 1. 检查插件是否激活

WordPress 后台 → **插件** → 找到 **WPCOM Member Custom API**，状态应为 **已启用**。

### 2. 测试 API 端点

```bash
# 获取 JWT Token（使用之前配置的 Simple JWT Login）
python -c "from wpcom_member_api import WPCOMMemberAPI; api = WPCOMMemberAPI(); token = api.get_token(); print('Token:', token[:50])"
```

**预期输出**:
```
Token: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOj...
```

### 3. 测试会员信息 API

```bash
python -c "from wpcom_member_api import WPCOMMemberAPI; api = WPCOMMemberAPI(); result = api.get_user_membership(1); import json; print(json.dumps(result, indent=2))"
```

**预期输出**:
```json
{
  "user_id": 1,
  "membership": {
    "level": "1",
    "expire_date": "2026-10-10",
    "status": "active",
    "is_active": true
  },
  "orders": [...],
  "meta": {...}
}
```

---

## 📋 API 端点列表

插件提供以下 REST API 端点：

### 1. 获取指定用户会员信息
```
GET /wp-json/custom/v1/user-membership/{user_id}
```

**请求头**:
```
Authorization: Bearer {JWT_Token}
```

**响应示例**:
```json
{
  "user_id": 1,
  "membership": {
    "level": "2",
    "expire_date": "2026-12-31",
    "status": "active",
    "is_active": true
  },
  "orders": [],
  "meta": {
    "vip_level": "2",
    "wallet_balance": "100.00"
  }
}
```

### 2. 获取当前用户会员信息
```
GET /wp-json/custom/v1/my-membership
```

**说明**: 自动获取当前登录用户的信息，无需传递 user_id。

### 3. 获取用户订单列表
```
GET /wp-json/custom/v1/user-orders/{user_id}
```

**响应示例**:
```json
{
  "user_id": 1,
  "wpcom_orders": [],
  "wc_orders": [
    {
      "id": 123,
      "status": "completed",
      "total": "299.00",
      "currency": "CNY",
      "date_created": "2025-12-14 10:30:00"
    }
  ]
}
```

### 4. 获取用户钱包信息
```
GET /wp-json/custom/v1/user-wallet/{user_id}
```

**响应示例**:
```json
{
  "user_id": 1,
  "balance": 100.50,
  "frozen": 0.00,
  "total": 100.50,
  "records": []
}
```

---

## 🔧 故障排查

### 问题 1: 插件上传失败

**错误信息**: "上传的文件超过了 php.ini 中定义的 upload_max_filesize 值"

**解决方案**:
1. 编辑 `php.ini` 文件：
   ```ini
   upload_max_filesize = 10M
   post_max_size = 10M
   ```
2. 重启 Web 服务器
3. 或者使用 FTP 手动安装

### 问题 2: API 返回 404

**原因**: 插件未激活或 WordPress 重写规则未刷新

**解决方案**:
1. 确认插件已激活
2. WordPress 后台 → **设置** → **固定链接**
3. 直接点击 **保存更改** 按钮（刷新重写规则）

### 问题 3: API 返回 401 Unauthorized

**原因**: JWT Token 未传递或无效

**解决方案**:
```bash
# 检查 Token 是否正确获取
python -c "from wpcom_member_api import WPCOMMemberAPI; api = WPCOMMemberAPI(); print(api.get_token())"
```

### 问题 4: 会员信息返回为空

**原因**: 用户 meta 表中没有会员数据

**解决方案**:
1. 检查 WPCOM Member Pro 插件是否已安装并激活
2. 确认用户已购买会员
3. 检查数据库 `wp_usermeta` 表中是否有 `vip_level` 等字段

---

## 🎯 下一步：启用前端会员信息显示

插件安装并测试成功后，需要修改前端代码以显示真实会员数据：

### 修改 MembershipCard.tsx

编辑 `frontend-nextjs/components/layout/MembershipCard.tsx` 第 26-45 行：

```typescript
useEffect(() => {
  if (!user) {
    setLoading(false);
    return;
  }

  // ✅ 启用 API 调用（删除下面的注释）
  fetchMembershipInfo();
}, [user]);

// ❌ 删除以下占位代码（第 35-44 行）
/*
setLoading(false);
setMembership({
  level: 0,
  level_name: '免费用户',
  expire_date: '',
  is_expired: false,
  wallet_balance: 0
});
setError(null);
*/
```

### 重启 Next.js 前端

```bash
cd frontend-nextjs
npm run dev
```

### 验证前端显示

1. 访问 http://localhost:3000
2. 使用 WordPress 登录（用户: YOUR_WORDPRESS_USERNAME）
3. 点击左下角用户面板
4. 应该能看到真实的会员等级、钱包余额等信息

---

## ✅ 配置完成标志

当以下测试全部通过时，配置完成：

- ✅ WordPress 插件已激活
- ✅ Python 可以成功获取 JWT Token
- ✅ Python 可以获取用户会员信息
- ✅ Next.js 前端显示真实会员数据（而非"免费用户"占位）
- ✅ 用户面板显示 VIP 等级、到期时间、钱包余额

---

## 📞 需要帮助？

如果遇到问题，请提供以下信息：

1. **WordPress 插件列表截图**（显示 WPCOM Member Custom API 已激活）
2. **API 测试输出**:
   ```bash
   python -c "from wpcom_member_api import WPCOMMemberAPI; api = WPCOMMemberAPI(); result = api.get_user_membership(1); print(result)"
   ```
3. **浏览器控制台错误**（F12 → Console）
4. **Python 后端日志**（运行 uvicorn 的终端输出）

---

## 🎉 安装完成！

恭喜！您已成功配置：
1. ✅ WordPress Simple JWT Login Authentication
2. ✅ WPCOM Member Custom API 插件
3. ✅ Python 后端 JWT 验证
4. ✅ Next.js SSO 单点登录

现在您的 Next.js 应用可以完整地访问 WordPress WPCOM Member Pro 会员数据了！
