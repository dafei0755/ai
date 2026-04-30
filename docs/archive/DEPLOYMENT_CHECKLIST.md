# 📋 WordPress JWT 认证系统 - 部署清单

> ⚠️ **重要**：按照本清单逐项检查和完成，确保系统正常部署

## 🔍 部署前检查 (Pre-Deployment)

### Phase 1: 文件与配置验证

- [ ] **检查所有必需文件**
  ```bash
  # 运行健康检查脚本
  python health_check.py
  ```
  
  应该看到的文件：
  - [ ] `intelligent_project_analyzer/services/wordpress_jwt_service.py`
  - [ ] `intelligent_project_analyzer/api/auth_middleware.py`
  - [ ] `intelligent_project_analyzer/api/auth_routes.py`
  - [ ] `frontend-nextjs/lib/wp-auth.ts`
  - [ ] `frontend-nextjs/app/auth/login/page.tsx`

- [ ] **验证环境配置**
  ```bash
  # 检查 .env 文件中的 JWT 配置
  grep "JWT_\|WORDPRESS_" .env
  ```
  
  应该包含：
  - [ ] `WORDPRESS_URL=https://www.ucppt.com`
  - [ ] `WORDPRESS_ADMIN_USERNAME=YOUR_WORDPRESS_USERNAME`
  - [ ] `JWT_SECRET_KEY=*` (非默认值)
  - [ ] `JWT_ALGORITHM=HS256`
  - [ ] `JWT_EXPIRY=604800`
  - [ ] `CORS_ORIGINS=` (包含前端地址)

### Phase 2: 依赖包验证

- [ ] **安装 Python 依赖**
  ```bash
  pip install -r requirements.txt
  ```

- [ ] **检查关键包**
  ```bash
  python -c "import fastapi, jwt, httpx; print('✅ 所有包已安装')"
  ```

- [ ] **安装 Node.js 依赖**
  ```bash
  cd frontend-nextjs
  npm install
  cd ..
  ```

### Phase 3: 代码集成验证

- [ ] **验证后端路由注册**
  ```bash
  grep -n "include_router.*auth" intelligent_project_analyzer/api/server.py
  ```
  
  应该包含：
  ```python
  from intelligent_project_analyzer.api.auth_routes import router as auth_router
  app.include_router(auth_router)
  ```

- [ ] **验证 CORS 配置**
  ```bash
  grep -n "CORSMiddleware" intelligent_project_analyzer/api/server.py
  ```
  
  应该看到 CORS 中间件已配置

---

## 🧪 本地测试 (Local Testing)

### Phase 4: 单元测试

- [ ] **运行集成测试**
  ```bash
  python integration_test.py
  ```
  
  检查点：
  - [ ] ✅ JWT 生成成功
  - [ ] ✅ Token 验证成功
  - [ ] ✅ Token 刷新成功
  - [ ] ✅ 无效 Token 被正确拒绝
  - [ ] ✅ 过期 Token 被正确拒绝

### Phase 5: 服务启动测试

**终端 1 - 启动后端**：
```bash
cd d:\11-20\langgraph-design
python -B -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000 --reload
```

检查项：
- [ ] ✅ 后端启动成功 (看到 "Uvicorn running on")
- [ ] ✅ 日志显示 "✅ WordPress JWT 认证路由已注册"
- [ ] ✅ API 文档可访问：http://localhost:8000/docs

**终端 2 - 启动前端**：
```bash
cd d:\11-20\langgraph-design\frontend-nextjs
npm run dev
```

检查项：
- [ ] ✅ 前端启动成功 (看到 "ready - started server on")
- [ ] ✅ 前端可访问：http://localhost:3000
- [ ] ✅ 登录页面可访问：http://localhost:3000/auth/login

### Phase 6: 端到端测试

#### 🔐 测试 1: 登录流程

```bash
# 方式 1：使用浏览器
1. 访问 http://localhost:3000/auth/login
2. 输入用户名：YOUR_WORDPRESS_USERNAME
3. 输入密码：<您的 WordPress 管理员密码>
4. 点击登录

# 预期结果：
✅ 显示 "登录成功" 消息
✅ 页面自动重定向到首页
✅ localStorage 中有 wp_jwt_token
```

#### 🔐 测试 2: Token 有效性验证

```bash
# 方式 2：使用 API 测试脚本
test_wordpress_jwt.bat

# 选择 [1] 登录，输入密码
# 复制返回的 token

# 选择 [2] 获取当前用户，粘贴 token
# 预期结果：✅ 返回用户信息
```

#### 🔐 测试 3: 保护端点测试

```bash
# 获取 token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"YOUR_WORDPRESS_USERNAME","password":"your_password"}' | \
  jq -r '.token')

# 测试受保护端点
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"

# 预期结果：✅ 返回用户信息
```

#### 🔐 测试 4: 无效 Token 处理

```bash
# 使用无效 token 访问受保护端点
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer invalid.token.value"

# 预期结果：❌ 401 Unauthorized
```

#### 🔐 测试 5: Token 刷新

```bash
# 使用旧 token 刷新
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Authorization: Bearer $TOKEN"

# 预期结果：✅ 返回新 token
```

---

## 🛡️ 安全检查 (Security Checks)

- [ ] **Secret Key 检查**
  - [ ] ✅ JWT_SECRET_KEY 不是默认值 `auto_generated_secure_key_2025_wordpress`
  - [ ] ✅ Secret Key 长度 > 32 字符
  
  生成安全的 Secret Key：
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

- [ ] **CORS 配置检查**
  - [ ] ✅ CORS_ORIGINS 仅包含信任的域名
  - [ ] ✅ 生产环境不包含 localhost
  
  示例（生产环境）：
  ```env
  CORS_ORIGINS=["https://www.ucppt.com","https://ucppt.com"]
  ```

- [ ] **HTTPS 检查** (生产环境)
  - [ ] ✅ WordPress URL 使用 HTTPS
  - [ ] ✅ FastAPI 配置了 SSL 证书
  - [ ] ✅ 前端也使用 HTTPS

- [ ] **Token 过期时间检查**
  - [ ] ✅ 生产环境使用合理的过期时间
  
  建议：
  ```env
  JWT_EXPIRY=3600      # 1 小时（更安全）
  JWT_EXPIRY=604800    # 7 天（当前配置）
  ```

- [ ] **日志安全检查**
  - [ ] ✅ 日志不会输出完整 Token
  - [ ] ✅ 日志不会输出用户密码
  - [ ] ✅ 日志级别设置为 INFO 或更高

---

## 📦 生产部署 (Production Deployment)

### Phase 7: 预部署准备

- [ ] **更新配置**
  ```env
  # .env.production
  JWT_SECRET_KEY=<secure_key_from_above>
  WORDPRESS_URL=https://www.ucppt.com
  CORS_ORIGINS=["https://www.ucppt.com","https://ucppt.com"]
  JWT_EXPIRY=3600
  ```

- [ ] **构建前端**
  ```bash
  cd frontend-nextjs
  npm run build
  npm run start  # 验证生产构建
  ```

- [ ] **创建服务监控**
  - [ ] ✅ 后端进程守护 (systemd, pm2, 或 Docker)
  - [ ] ✅ 前端部署 (Vercel, Nginx, 或 Docker)
  - [ ] ✅ 错误告警配置

- [ ] **备份与恢复计划**
  - [ ] ✅ 备份 .env 配置
  - [ ] ✅ 备份 JWT_SECRET_KEY
  - [ ] ✅ 记录部署步骤以便快速恢复

### Phase 8: 生产验证

- [ ] **健康检查端点**
  ```bash
  curl https://api.yourdomain.com/health
  ```

- [ ] **监控告警**
  - [ ] ✅ 配置 401/500 错误告警
  - [ ] ✅ 配置响应时间告警
  - [ ] ✅ 配置 Token 刷新失败告警

- [ ] **性能基准**
  - [ ] ✅ 登录响应时间 < 500ms
  - [ ] ✅ Token 刷新响应时间 < 200ms
  - [ ] ✅ API 端点响应时间 < 100ms

---

## 🚀 部署步骤

### 方案 A：Docker 部署（推荐）

```dockerfile
# Dockerfile.backend
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "intelligent_project_analyzer.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# 构建和运行
docker build -f Dockerfile.backend -t wordpress-jwt-backend .
docker run -d -p 8000:8000 --env-file .env wordpress-jwt-backend
```

### 方案 B：系统服务部署

```bash
# 创建 systemd 服务文件
sudo tee /etc/systemd/system/wordpress-jwt-api.service > /dev/null <<EOF
[Unit]
Description=WordPress JWT API Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/langgraph-design
ExecStart=/usr/bin/python3 -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl enable wordpress-jwt-api.service
sudo systemctl start wordpress-jwt-api.service
```

---

## ✅ 部署完成检查清单

部署完成后，确保：

- [ ] ✅ 后端服务正常运行
- [ ] ✅ 前端服务正常运行
- [ ] ✅ 登录功能正常
- [ ] ✅ Token 获取和验证正常
- [ ] ✅ 受保护端点正常
- [ ] ✅ Token 刷新正常
- [ ] ✅ 错误处理正常
- [ ] ✅ 日志记录正常
- [ ] ✅ 性能基准达标
- [ ] ✅ 安全检查通过

---

## 📞 故障排除

如遇到问题，参考：
- 📖 [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) - 常见问题
- 📖 [WORDPRESS_JWT_AUTH_GUIDE.md](WORDPRESS_JWT_AUTH_GUIDE.md) - 详细文档
- 📖 [健康检查输出](health_check.py) - 运行诊断

---

## 📝 部署记录

| 日期 | 步骤 | 状态 | 备注 |
|------|------|------|------|
| | Phase 1: 文件验证 | ⏳ | |
| | Phase 2: 依赖验证 | ⏳ | |
| | Phase 3: 代码验证 | ⏳ | |
| | Phase 4: 单元测试 | ⏳ | |
| | Phase 5: 服务测试 | ⏳ | |
| | Phase 6: E2E 测试 | ⏳ | |
| | Phase 7: 预部署 | ⏳ | |
| | Phase 8: 生产验证 | ⏳ | |

---

**部署日期**：____________  
**部署人员**：____________  
**部署状态**：🔄 进行中 / ✅ 完成 / ❌ 失败

---

**最后更新**：2025-12-12  
**维护者**：AI Assistant
