# Member API 500 错误根本原因分析

## 🔍 问题现象

- **症状**: GET `/api/member/my-membership` 返回 HTTP 500 Internal Server Error
- **响应时间**: 约 2.78 秒（说明后端确实在尝试请求 WordPress）
- **前端用户**: `宋词 - 42841287@qq.com` (username: `8pdwoxj8`) 已通过 SSO 成功登录
- **JWT 验证**: 前端 Token 验证成功，用户已认证

## 🎯 根本原因定位

### 通过增强日志发现的问题

运行 `test_system_health.py` 和 `test_wpcom_import.py` 后，stderr 日志显示：

```
[WPCOM API] 🚀 初始化中...
[WPCOM API] Base URL: https://www.ucppt.com
[WPCOM API] Username: 8pdwoxj8
[WPCOM API] 🔑 请求 JWT Token...
[WPCOM API] URL: https://www.ucppt.com/wp-json/simple-jwt-login/v1/auth
[WPCOM API] Token 响应状态码: 400
[WPCOM API] ❌ Token 获取失败: {"success":false,"data":{"message":"Wrong user credentials.","errorCode":48}}
```

### 核心问题

**后端 Python API (`wpcom_member_api.py`) 无法通过 Simple JWT Login 插件获取 Token。**

具体错误：
- **错误代码**: 48
- **错误信息**: "Wrong user credentials"
- **HTTP 状态**: 400 Bad Request

### 为什么前端 SSO 成功，但后端 API 失败？

#### 前端 SSO 流程（✅ 成功）：
1. 用户在 WordPress 网站 (`www.ucppt.com`) 登录
2. WordPress 生成 JWT Token
3. 通过 PostMessage 将 Token 传递给 Next.js iframe
4. Next.js 使用这个 Token 进行 API 认证

#### 后端 Member API 流程（❌ 失败）：
1. Next.js 调用后端 `/api/member/my-membership`
2. 后端需要调用 WordPress API 获取会员信息
3. **关键点**: 后端需要自己获取 WordPress Token（不能使用前端的 Token）
4. 后端使用 `.env` 中的 `WORDPRESS_ADMIN_USERNAME` 和 `WORDPRESS_ADMIN_PASSWORD` 调用 Simple JWT Login API
5. **失败**: Simple JWT Login 返回 "Wrong user credentials"

## 🔍 可能的原因

### 1. Simple JWT Login 插件权限限制（⭐ 最可能）

Simple JWT Login 插件可能限制了哪些用户可以通过 `/wp-json/simple-jwt-login/v1/auth` 端点获取 Token。

**检查项**:
- WordPress 后台 → Simple JWT Login → Settings → Authentication
- 查看是否有 "Allowed User Roles" 配置
- 用户 `8pdwoxj8` 的角色可能不在允许列表中

### 2. 密码格式问题

当前 `.env` 配置：
```bash
WORDPRESS_ADMIN_USERNAME=8pdwoxj8
WORDPRESS_ADMIN_PASSWORD='DRMHVswK%@NKS@ww1Sric&!e'
```

密码包含特殊字符：`%`, `@`, `&`, `!`

**可能的问题**:
- Python `decouple` 库可能没有正确处理单引号
- 特殊字符可能需要不同的转义方式

### 3. 用户账户问题

- 用户 `8pdwoxj8` 是否是管理员账户？
- 该用户是否被 Simple JWT Login 插件封禁或限制？

### 4. WordPress REST API 权限

WordPress REST API 默认需要管理员权限才能进行身份验证。普通会员用户可能无法通过 Simple JWT Login 获取 Token。

## 🛠️ 解决方案（按优先级）

### ✅ 方案 1: 检查 Simple JWT Login 配置（推荐）

**步骤**:
1. 登录 WordPress 后台
2. 进入 **Plugins → Simple JWT Login → Settings**
3. 检查 **Authentication** 标签页：
   - 找到 "Allowed User Roles" 或类似设置
   - 确保用户 `8pdwoxj8` 的角色在允许列表中
   - 或者设置为 "Allow all users"
4. 保存设置后重新测试

**验证命令**:
```bash
python test_system_health.py
```

### ✅ 方案 2: 使用管理员账户

如果 `8pdwoxj8` 不是管理员，需要创建或使用具有管理员权限的账户。

**步骤**:
1. 在 WordPress 后台创建新管理员用户（或使用现有管理员）
2. 更新 `.env` 配置：
   ```bash
   WORDPRESS_ADMIN_USERNAME=admin_username
   WORDPRESS_ADMIN_PASSWORD='admin_password'
   ```
3. 重启后端服务

### ✅ 方案 3: 修复密码格式

如果是密码格式问题，尝试以下两种方式：

**方式 A: 移除单引号**
```bash
WORDPRESS_ADMIN_PASSWORD=DRMHVswK%@NKS@ww1Sric&!e
```

**方式 B: 使用双引号**
```bash
WORDPRESS_ADMIN_PASSWORD="DRMHVswK%@NKS@ww1Sric&!e"
```

**方式 C: 创建 WordPress 应用程序密码（最安全）**
1. WordPress 后台 → 用户 → 个人资料 → 应用程序密码
2. 生成新密码（例如：`xg65 JScg 1lOk SdfG`）
3. 移除所有空格：`xg65JScg1lOkSdfG`
4. 更新 `.env`：
   ```bash
   WORDPRESS_ADMIN_PASSWORD=xg65JScg1lOkSdfG
   ```

### ✅ 方案 4: 直接使用前端 Token（架构调整）

**当前架构问题**: 后端重新获取 Token，增加了一次额外的 WordPress API 调用和失败点。

**优化方案**: 前端将 Token 传递给后端

**修改 `member_routes.py`**:
```python
@router.get("/my-membership")
async def get_my_membership(current_user: Dict[str, Any] = Depends(auth_middleware.get_current_user)):
    # 从 current_user 中获取 JWT Token
    token = current_user.get("token")  # 需要在 auth_middleware 中传递 Token

    # 直接使用 Token 调用 WordPress API，不需要重新获取
    url = f"{WORDPRESS_URL}/wp-json/custom/v1/user-membership/{user_id}"
    headers = {"Authorization": f"Bearer {token}"}
    response = httpx.get(url, headers=headers, timeout=30, verify=False)
    ...
```

**优势**:
- 减少一次 WordPress API 调用（更快）
- 不需要存储管理员密码
- 使用用户自己的 Token（更安全，符合最小权限原则）

## 🧪 验证步骤

### 1. 测试 Token 获取
```bash
python test_wpcom_import.py
```

**预期成功输出**:
```
[WPCOM API] ✅ Token 获取成功
Token (前50字符): eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

### 2. 测试完整系统
```bash
python test_system_health.py
```

**预期成功输出**:
```
总计: 5/5 通过
[OK] 所有测试通过！系统运行正常。
```

### 3. 测试前端 Member API
1. 重启后端服务：
   ```bash
   python -B -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000
   ```
2. 刷新浏览器页面：`https://www.ucppt.com/nextjs`
3. 检查终端日志，应该看到：
   ```
   [MemberRoutes] ✅ WordPress API 返回结果: {"success": true, "membership": {...}}
   ```

## 📋 检查清单

- [ ] 检查 Simple JWT Login 插件的 "Allowed User Roles" 设置
- [ ] 确认用户 `8pdwoxj8` 是否为管理员或在允许列表中
- [ ] 测试密码格式（移除单引号/使用双引号/应用程序密码）
- [ ] 考虑使用前端 Token 而非重新获取 Token（架构优化）
- [ ] 运行 `test_wpcom_import.py` 验证 Token 获取
- [ ] 运行 `test_system_health.py` 验证完整流程
- [ ] 测试前端 Member API 功能

## 🎯 推荐方案

**短期修复**（立即可行）：
1. 检查 Simple JWT Login 设置，允许用户 `8pdwoxj8` 获取 Token
2. 如果无法修改插件设置，使用管理员账户

**长期优化**（架构改进）：
1. 修改后端代码，直接使用前端传递的 Token
2. 移除 `.env` 中的 `WORDPRESS_ADMIN_PASSWORD`
3. 减少 WordPress API 调用次数，提升性能

## 📚 相关文档

- [Simple JWT Login 文档](https://wordpress.org/plugins/simple-jwt-login/)
- [WPCOM Member Custom API 安装指南](docs/wordpress/WPCOM_CUSTOM_API_INSTALLATION_GUIDE.md)
- [Member API 调试指南](MEMBER_API_DEBUG_GUIDE.md)
- [WordPress SSO v3.0.5 修复说明](docs/wordpress/WORDPRESS_SSO_V3.0.5_LOGIN_SYNC_FIX.md)
