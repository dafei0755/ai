# 🔐 WordPress JWT 认证 - 使用密码进行完整测试

> 📅 **更新日期**: 2025-12-12  
> ✅ **状态**: 密码已配置在 `.env`，可以开始测试  
> 🚀 **目标**: 验证 WordPress 认证和 JWT Token 生成

---

## 📋 快速开始

### 方法 1：使用 Python 脚本测试（推荐）

```bash
# 运行完整的密码验证测试
python test_wordpress_with_password.py
```

**此脚本会执行**：
1. ✅ 从 `.env` 读取密码
2. ✅ 验证 WordPress 连接
3. ✅ 使用密码进行系统认证
4. ✅ 生成 JWT Token
5. ✅ 验证 Token 有效性
6. ✅ 测试公开数据访问

**预期输出**：
```
✅ WordPress URL: https://www.ucppt.com
✅ 管理员用户名: 8pdwoxj8
✅ 密码已配置: **(掩盖)

✅ WordPress REST API 可访问
✅ WordPress 认证成功！
  用户 ID: 1
  邮箱: admin@ucppt.com
  显示名: Admin
  角色: ['administrator']

✅ JWT Token 生成成功
Token 长度: 350 字符

✅ Token 验证成功
  用户: 8pdwoxj8
  过期时间: 2025-12-19 ...
```

### 方法 2：使用 Batch 脚本（Windows）

```bash
# 运行交互式测试菜单
test_with_password.bat

# 选择：[1] 快速密码验证
```

### 方法 3：直接调用 API

```bash
# 步骤 1：启动后端服务
python -m uvicorn intelligent_project_analyzer.api.server:app --reload

# 步骤 2：调用登录端点
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "8pdwoxj8", "password": "xUc5 SkfQ GF5S gp0i 0IHR Ohb3"}'

# 预期响应：
# {
#   "status": "success",
#   "message": "登录成功",
#   "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "user": {
#     "user_id": 1,
#     "username": "8pdwoxj8",
#     "email": "admin@ucppt.com",
#     "display_name": "Admin",
#     "roles": ["administrator"]
#   }
# }
```

---

## 🔧 详细测试步骤

### 步骤 1：验证密码配置

查看 `.env` 文件中的 WordPress 配置：

```bash
# Linux/Mac
grep "WORDPRESS_" .env | head -3

# Windows PowerShell
Select-String "WORDPRESS_" .env | Select-Object -First 3

# 预期输出
WORDPRESS_URL=https://www.ucppt.com
WORDPRESS_ADMIN_USERNAME=8pdwoxj8
WORDPRESS_ADMIN_PASSWORD=xUc5 SkfQ GF5S gp0i 0IHR Ohb3
```

### 步骤 2：检查 WordPress 连接

```bash
# 使用 curl 验证 REST API
curl -I https://www.ucppt.com/wp-json/wp/v2/

# 预期：HTTP 200 或 401（认证所需）
```

### 步骤 3：运行密码验证

```bash
# 运行 Python 测试脚本
python test_wordpress_with_password.py

# 脚本会：
# 1. 读取 .env 中的密码
# 2. 调用 WordPress 验证
# 3. 生成 JWT Token
# 4. 验证 Token
```

### 步骤 4：测试 API 端点

**登录**：
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "8pdwoxj8",
    "password": "xUc5 SkfQ GF5S gp0i 0IHR Ohb3"
  }' | jq .
```

**获取当前用户**（使用返回的 Token）：
```bash
TOKEN="eyJhbGci..." # 从上面的响应复制

curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**刷新 Token**：
```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### 步骤 5：测试公开数据（无需密码）

```bash
# 获取已发布的文章（无需认证）
curl https://www.ucppt.com/wp-json/wp/v2/posts?status=publish | jq .

# 获取用户列表（部分公开）
curl https://www.ucppt.com/wp-json/wp/v2/users | jq .
```

---

## 📊 测试覆盖清单

### 认证测试

- [ ] **密码读取**
  - [ ] `.env` 中的密码正确
  - [ ] 密码格式有效（带空格）
  - [ ] 密码长度合理

- [ ] **WordPress 验证**
  - [ ] REST API 连接成功
  - [ ] Basic Auth 验证通过
  - [ ] 返回用户信息

- [ ] **JWT 生成**
  - [ ] Token 格式正确（3 部分，用 . 分隔）
  - [ ] Payload 包含必要字段：user_id, username, email, roles
  - [ ] Token 有签名和有效期

- [ ] **Token 验证**
  - [ ] Token 验证通过
  - [ ] Payload 正确解析
  - [ ] 有效期检查正常
  - [ ] 过期 Token 被拒绝

### API 端点测试

- [ ] **POST /api/auth/login**
  - [ ] 正确凭证返回 Token
  - [ ] 错误凭证返回 401
  - [ ] 缺少参数返回 400

- [ ] **GET /api/auth/me**
  - [ ] 有效 Token 返回用户信息
  - [ ] 无效 Token 返回 401
  - [ ] 过期 Token 返回 401

- [ ] **POST /api/auth/refresh**
  - [ ] 有效 Token 返回新 Token
  - [ ] 新 Token 可验证

- [ ] **POST /api/auth/logout**
  - [ ] 返回成功响应
  - [ ] 客户端应清除 Token

### 安全测试

- [ ] **密码安全**
  - [ ] 密码不在日志中输出
  - [ ] 密码不在错误消息中显示
  - [ ] 密码传输使用 HTTPS

- [ ] **Token 安全**
  - [ ] Token 使用 HMAC-SHA256 签名
  - [ ] Token 包含有效期
  - [ ] 过期 Token 被拒绝
  - [ ] Token 不能被篡改

- [ ] **API 安全**
  - [ ] CORS 正确配置
  - [ ] 错误消息不泄露细节
  - [ ] 认证失败返回通用消息

### 集成测试

- [ ] **前端登录流程**
  - [ ] 表单提交用户名和密码
  - [ ] API 返回 Token
  - [ ] Token 存储到 localStorage
  - [ ] 后续请求自动附加 Token

- [ ] **Token 刷新流程**
  - [ ] Token 即将过期时自动刷新
  - [ ] 新 Token 替换旧 Token
  - [ ] 用户无感知

---

## 🐛 常见问题和解决

### Q1：运行 Python 脚本报 "缺少 WORDPRESS_ADMIN_PASSWORD"

**原因**：`.env` 中没有密码配置

**解决**：
```bash
# 编辑 .env 文件，添加密码
WORDPRESS_ADMIN_PASSWORD=xUc5 SkfQ GF5S gp0i 0IHR Ohb3
```

### Q2："WordPress 认证失败"

**可能原因**：
1. 密码错误
2. WordPress REST API 未启用
3. 网络连接问题
4. 防火墙阻止

**解决**：
```bash
# 1. 验证 REST API 可访问
curl -I https://www.ucppt.com/wp-json/wp/v2/

# 2. 使用 Basic Auth 测试凭证
curl -u 8pdwoxj8:xUc5SkfQGF5Sgp0i0IHROhb3 \
  https://www.ucppt.com/wp-json/wp/v2/users/me

# 3. 检查 WordPress 后台密码是否与应用密码一致
# 应用密码在：用户 → 编辑个人资料 → 应用密码
```

### Q3：Token 验证失败

**原因**：
1. JWT Secret Key 不匹配
2. Token 已过期
3. Token 被篡改

**解决**：
```bash
# 生成新 Token（重新登录）
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "8pdwoxj8", "password": "..."}'

# 使用新 Token 验证
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <NEW_TOKEN>"
```

### Q4：CORS 错误（前端无法调用 API）

**解决**：
```env
# 编辑 .env，更新 CORS_ORIGINS
CORS_ORIGINS=["http://localhost:3000","http://localhost:3001","https://www.ucppt.com"]
```

---

## 🚀 完整测试工作流

### Day 1：基础验证 (30 分钟)

```bash
# 1. 检查配置
grep "WORDPRESS_\|JWT_" .env

# 2. 运行 Python 测试
python test_wordpress_with_password.py

# 3. 如果失败，诊断系统
python health_check.py
```

### Day 2：API 测试 (1 小时)

```bash
# 1. 启动后端
python -m uvicorn intelligent_project_analyzer.api.server:app --reload

# 2. 启动前端
cd frontend-nextjs && npm run dev

# 3. 使用浏览器测试登录
# http://localhost:3000/auth/login
# 输入：8pdwoxj8 / xUc5 SkfQ GF5S gp0i 0IHR Ohb3

# 4. 用 curl 测试 API
test_with_password.bat  # 选择 [2] API 登录测试
```

### Day 3：集成测试 (2 小时)

```bash
# 运行所有测试
python test_wordpress_with_password.py
python integration_test.py
python health_check.py

# 部署前检查清单
# DEPLOYMENT_CHECKLIST.md
```

---

## 📈 预期测试结果

### ✅ 成功标志

```
✅ WordPress REST API 可访问 (HTTP 200 或 401)
✅ WordPress 认证成功！
   用户 ID: 1
   邮箱: admin@ucppt.com

✅ JWT Token 生成成功
   Token 长度: ~350 字符

✅ Token 验证成功
   用户: 8pdwoxj8

✅ 成功获取公开文章
   标题: ...
   ID: 1

所有测试通过！✨
```

### ❌ 失败标志

```
❌ 无法连接 WordPress
  → 检查 WORDPRESS_URL 和网络

❌ WordPress 认证失败
  → 检查密码是否正确

❌ Token 生成失败
  → 检查 JWT Secret Key

❌ Token 验证失败
  → Token 可能过期或损坏
```

---

## 📝 测试日志示例

成功的完整测试日志：

```
======================================================================
  WordPress JWT 认证系统 - 密码验证测试
======================================================================

======================================================================
  1️⃣  加载配置
======================================================================

✅ WordPress URL: https://www.ucppt.com
✅ 管理员用户名: 8pdwoxj8
✅ 密码已配置: ******* (掩盖)

======================================================================
  2️⃣  加载 JWT 服务
======================================================================

✅ JWT 服务已加载

======================================================================
  3️⃣  测试 WordPress 连接
======================================================================

ℹ️  测试连接: https://www.ucppt.com/wp-json/wp/v2/
✅ WordPress REST API 可访问 (HTTP 200)

======================================================================
  4️⃣  测试系统认证（使用 .env 密码）
======================================================================

ℹ️  使用凭证验证:
ℹ️    用户名: 8pdwoxj8
ℹ️    密码: ******* (掩盖)
✅ WordPress 认证成功！
ℹ️    用户 ID: 1
ℹ️    邮箱: admin@ucppt.com
ℹ️    显示名: Admin
ℹ️    角色: ['administrator']

======================================================================
  5️⃣  测试 JWT Token 生成
======================================================================

✅ JWT Token 生成成功
ℹ️  Token 长度: 350 字符
ℹ️  Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

======================================================================
  6️⃣  测试 Token 验证
======================================================================

✅ Token 验证成功
ℹ️    用户: 8pdwoxj8
ℹ️    User ID: 1
ℹ️    邮箱: admin@ucppt.com
ℹ️    角色: ['administrator']
ℹ️    签发时间: 2025-12-12 14:30:45
ℹ️    过期时间: 2025-12-19 14:30:45

======================================================================
  7️⃣  测试公开数据访问
======================================================================

ℹ️  获取公开发布的文章（无需认证）
✅ 成功获取公开文章
ℹ️    标题: 欢迎来到我们的网站
ℹ️    ID: 1
ℹ️    状态: publish

======================================================================
  📊 测试结果汇总
======================================================================

ℹ️  总测试数: 7
✅ 通过: 7
所有测试通过！✨
```

---

## 🎓 下一步

✅ **本地测试完成后**：
1. 检查所有 7 个测试都通过
2. 查看 Token 内容和有效期
3. 测试 API 调用

⏭️ **接下来**：
1. 前端登录表单测试
2. Token 自动刷新测试
3. 受保护端点测试
4. 生产环境部署

📖 **相关文档**：
- [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md)
- [WORDPRESS_JWT_AUTH_GUIDE.md](WORDPRESS_JWT_AUTH_GUIDE.md)
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

---

**现在运行测试**：

```bash
python test_wordpress_with_password.py
```

或

```bash
test_with_password.bat
```

祝您测试顺利！🚀
