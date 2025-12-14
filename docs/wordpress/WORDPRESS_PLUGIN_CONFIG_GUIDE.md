# WordPress Simple JWT Login 插件配置指南

## 🎯 目标
启用 Simple JWT Login 插件的 Authentication 功能，使 Python 后端能够获取 JWT Token 并调用 WPCOM Member Pro API。

---

## ✅ 已完成的配置

### 1. General 设置（已配置）
- **JWT Decryption Key**: `$d4@5fg54ll_t_45gH`
- **JWT Decryption Algorithm**: HS256
- **Expiration time**: 604800 秒（7天）

### 2. Login 设置（已配置）
- **Allow Autologin**: ✅ 已启用
- **Redirect URL**: `http://localhost:3001/auth/callback?token={{JWT}}`
- **Domain**: `localhost`

---

## 🔴 需要配置的功能：Authentication

根据您提供的截图，Authentication 页面显示了以下端点：

```
POST /wp-json/simple-jwt-login/v1/auth
```

这是 Python 后端 `wpcom_member_api.py` 需要调用的端点，用于获取管理员 JWT Token。

### 配置步骤

#### 步骤 1: 进入 Authentication 设置页面
1. WordPress 后台左侧菜单 → **Simple JWT Login**
2. 点击顶部 Tab: **Authentication**

#### 步骤 2: 启用 Authentication 功能
找到并勾选以下选项：
- ☑️ **Allow Authentication** (允许认证)

#### 步骤 3: 配置 JWT 密钥
确保以下设置与 General 设置一致：

| 配置项 | 值 |
|--------|-----|
| **JWT Decryption Key** | `$d4@5fg54ll_t_45gH` |
| **JWT Decryption Algorithm** | `HS256` |
| **JWT Expiration time** | `604800` (可选，默认即可) |

#### 步骤 4: 配置认证方式（可选）
根据插件提供的选项，选择以下之一：
- ☑️ **Allow Authentication with username + password**
- 或者使用其他认证方式（如 email）

#### 步骤 5: 保存设置
点击页面底部的 **Save Settings** 按钮。

---

## 🧪 验证配置是否成功

### 方法 1: 使用 Python 测试脚本

在项目根目录运行以下命令：

```bash
python -c "from wpcom_member_api import WPCOMMemberAPI; api = WPCOMMemberAPI(); print('✅ Token 获取成功:', api.get_token()[:50] + '...')"
```

**预期输出（成功）:**
```
✅ Token 获取成功: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3M...
```

**错误输出（失败）:**
```
Exception: Token获取失败: {"code":"rest_no_route","message":"未找到匹配 URL 和请求方式的路由","data":{"status":404}}
```

### 方法 2: 使用 curl 测试 API 端点

```bash
curl -X POST https://www.ucppt.com/wp-json/simple-jwt-login/v1/auth \
  -H "Content-Type: application/json" \
  -d '{"username": "8pdwoxj8", "password": "M2euRVQMdpzJp%*KLtD0#kK1"}'
```

**预期响应（成功）:**
```json
{
  "success": true,
  "data": {
    "jwt": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
}
```

**错误响应（失败）:**
```json
{
  "code": "rest_no_route",
  "message": "未找到匹配 URL 和请求方式的路由",
  "data": {
    "status": 404
  }
}
```

---

## 📋 配置完成后的下一步

### 1. 测试会员信息 API

```bash
python -c "from wpcom_member_api import WPCOMMemberAPI; api = WPCOMMemberAPI(); result = api.get_user_membership(1); print(result)"
```

**预期输出:**
```python
{
  "success": True,
  "membership": {
    "level": "1",
    "level_name": "VIP 1",
    "expire_date": "2026-10-10",
    "is_active": True
  }
}
```

### 2. 启用前端会员信息显示

修改 `frontend-nextjs/components/layout/MembershipCard.tsx` 第 32-44 行：

```typescript
useEffect(() => {
  if (!user) {
    setLoading(false);
    return;
  }

  // ✅ 启用 API 调用
  fetchMembershipInfo();
}, [user]);
```

删除以下占位代码（第 35-44 行）：
```typescript
// 显示占位信息
setLoading(false);
setMembership({
  level: 0,
  level_name: '免费用户',
  expire_date: '',
  is_expired: false,
  wallet_balance: 0
});
setError(null);
```

### 3. 重启 Next.js 前端

```bash
cd frontend-nextjs
npm run dev
```

### 4. 验证前端显示

1. 访问 http://localhost:3000
2. 使用 WordPress 登录（用户: 8pdwoxj8）
3. 点击左下角用户面板，打开设置菜单
4. 在 **账号管理** 部分，应该能看到：
   - VIP 等级徽章（VIP 1 / VIP 2 / VIP 3）
   - 到期时间
   - 钱包余额
   - 升级会员按钮（如果不是 VIP 3）

---

## 🔍 常见问题排查

### 问题 1: 404 错误 - "未找到匹配 URL"

**原因**: Authentication 功能未启用

**解决方案**:
1. WordPress 后台 → Simple JWT Login → Authentication
2. 勾选 **Allow Authentication**
3. 保存设置

### 问题 2: 401 错误 - "Invalid credentials"

**原因**: 用户名或密码错误

**解决方案**:
检查 `.env` 文件中的凭据：
```bash
WORDPRESS_ADMIN_USERNAME=8pdwoxj8
WORDPRESS_ADMIN_PASSWORD=M2euRVQMdpzJp%*KLtD0#kK1
```

### 问题 3: JWT 验证失败

**原因**: JWT 密钥不一致

**解决方案**:
确保以下三处配置一致：
1. WordPress Simple JWT Login → General → JWT Decryption Key
2. WordPress Simple JWT Login → Authentication → JWT Decryption Key
3. Python `.env` → `JWT_SECRET_KEY`

当前统一使用: `$d4@5fg54ll_t_45gH`

### 问题 4: 会员信息获取失败

**原因**: 用户 ID 不存在或 WPCOM Member Pro 插件未正确配置

**解决方案**:
```bash
# 测试获取当前登录用户的会员信息
python -c "from wpcom_member_api import WPCOMMemberAPI; api = WPCOMMemberAPI(); result = api.get_user_membership(1); print(result)"
```

如果返回空数据，检查 WordPress 后台 → WPCOM Member → 用户是否有会员等级。

---

## 📞 需要帮助？

如果配置后仍有问题，请提供以下信息：

1. **Simple JWT Login Authentication 页面截图**（显示勾选的选项）
2. **测试命令输出**:
   ```bash
   python -c "from wpcom_member_api import WPCOMMemberAPI; api = WPCOMMemberAPI(); print(api.get_token())"
   ```
3. **浏览器控制台错误**（F12 → Console）
4. **Python 后端日志**（运行 uvicorn 的终端输出）

---

## ✅ 配置完成标志

当以下测试全部通过时，配置完成：

- ✅ Python 可以成功获取 JWT Token
- ✅ Python 可以获取用户会员信息
- ✅ Next.js 前端显示真实会员数据（而非"免费用户"占位）
- ✅ 用户面板显示 VIP 等级、到期时间、钱包余额

---

**当前状态**: 🟡 等待配置 Authentication 功能

**下一步**: 按照上述步骤启用 Authentication，然后运行测试命令验证。
