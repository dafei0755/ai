# 🚀 WordPress JWT 认证 - 快速开始指南

## 📋 目录

1. [项目架构](#项目架构)
2. [文件清单](#文件清单)
3. [快速启动](#快速启动)
4. [测试流程](#测试流程)
5. [常见问题](#常见问题)
6. [安全建议](#安全建议)

---

## 项目架构

```
WordPress JWT 认证系统
│
├─ 后端 (FastAPI)
│  ├── services/wordpress_jwt_service.py      # JWT 服务 + WordPress REST API 集成
│  ├── api/auth_middleware.py                 # 认证中间件 (依赖注入)
│  ├── api/auth_routes.py                     # API 路由 (/api/auth/*)
│  └── api/server.py                          # FastAPI 主服务器 (已集成)
│
├─ 前端 (Next.js)
│  ├── lib/wp-auth.ts                         # JWT 工具库 (Token 管理)
│  └── app/auth/login/page.tsx                # 登录页面
│
├─ 配置
│  └── .env                                   # JWT 配置参数
│
└─ 文档
   ├── WORDPRESS_JWT_AUTH_GUIDE.md            # 详细文档
   ├── QUICK_START_GUIDE.md                   # 本文件
   ├── start_wordpress_jwt.bat                # 启动脚本
   └── test_wordpress_jwt.bat                 # 测试脚本
```

---

## 文件清单

### ✅ 已创建的文件

| 文件 | 大小 | 描述 |
|------|------|------|
| `intelligent_project_analyzer/services/wordpress_jwt_service.py` | 170 行 | JWT 服务 + WordPress 集成 |
| `intelligent_project_analyzer/api/auth_middleware.py` | 65 行 | FastAPI 认证中间件 |
| `intelligent_project_analyzer/api/auth_routes.py` | 160 行 | API 路由定义 |
| `frontend-nextjs/lib/wp-auth.ts` | 190 行 | 前端 JWT 工具库 |
| `frontend-nextjs/app/auth/login/page.tsx` | 145 行 | 登录页面组件 |
| `.env` | (已更新) | JWT 配置 |
| `intelligent_project_analyzer/api/server.py` | (已修改) | FastAPI 服务器 + 路由注册 |

### ⚙️ 配置参数

```env
WORDPRESS_URL=https://www.ucppt.com
WORDPRESS_ADMIN_USERNAME=YOUR_WORDPRESS_USERNAME
JWT_SECRET_KEY=auto_generated_secure_key_2025_wordpress
JWT_ALGORITHM=HS256
JWT_EXPIRY=604800
CORS_ORIGINS=["http://localhost:3000","http://localhost:3001","https://www.ucppt.com","https://ucppt.com"]
```

---

## 快速启动

### 方式 1：使用启动脚本（推荐）

```bash
# 进入项目目录
cd d:\11-20\langgraph-design

# 运行启动脚本
start_wordpress_jwt.bat

# 选择选项 [4] 启动后端 + 前端 + 打开浏览器
```

**预期结果**：
- ✅ FastAPI 启动在 http://localhost:8000
- ✅ Next.js 启动在 http://localhost:3000
- ✅ 自动打开登录页面 http://localhost:3000/auth/login

### 方式 2：手动启动两个终端

**终端 1 - 启动后端**：
```bash
cd d:\11-20\langgraph-design
python -B -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000 --reload
```

**终端 2 - 启动前端**：
```bash
cd d:\11-20\langgraph-design\frontend-nextjs
npm run dev
```

---

## 测试流程

### ✅ 测试 1：登录

**方式 1：使用浏览器登录页面**

1. 访问 http://localhost:3000/auth/login
2. 输入凭证：
   - 用户名：`YOUR_WORDPRESS_USERNAME`
   - 密码：**您的 WordPress 管理员密码**
3. 点击 "登录"
4. 看到成功消息并重定向到首页

**预期响应**：
```json
{
  "status": "success",
  "message": "登录成功",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "user_id": 1,
    "username": "YOUR_WORDPRESS_USERNAME",
    "email": "admin@ucppt.com",
    "display_name": "Admin",
    "roles": ["administrator"]
  }
}
```

**方式 2：使用 API 测试工具**

```bash
# 打开 API 测试工具
test_wordpress_jwt.bat

# 选择 [1] 登录
# 输入密码
# 复制返回的 token
```

### ✅ 测试 2：使用 Token 访问受保护资源

```bash
# 使用返回的 token
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**预期响应**：
```json
{
  "user_id": 1,
  "username": "YOUR_WORDPRESS_USERNAME",
  "email": "admin@ucppt.com",
  "display_name": "Admin",
  "roles": ["administrator"],
  "iat": 1702646400,
  "exp": 1703251200
}
```

### ✅ 测试 3：刷新 Token

```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Authorization: Bearer YOUR_OLD_TOKEN"
```

**预期响应**：包含新 Token 和用户信息

### ✅ 测试 4：使用前端 fetch 助手

在前端代码中使用 `fetchWithAuth()` 自动附加 Token：

```typescript
import { fetchWithAuth } from '@/lib/wp-auth';

// 自动添加 Token 到请求头
// 如果 401，自动刷新 Token 后重试
const response = await fetchWithAuth('/api/analysis/report/session123');
const data = await response.json();
```

---

## 常见问题

### ❌ 问题 1：登录返回 "Invalid username or password"

**原因**：密码错误

**解决方案**：
1. 确认您输入的是 WordPress 管理员密码
2. 在 WordPress 后台重置密码：WordPress → 用户 → 编辑个人资料 → 更改密码
3. 重新尝试登录

### ❌ 问题 2：连接被拒绝 "Cannot POST /api/auth/login"

**原因**：后端服务未启动

**解决方案**：
1. 检查后端进程：`netstat -ano | findstr :8000`
2. 启动后端：`python -B -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000`
3. 检查日志是否有错误信息

### ❌ 问题 3：CORS 错误 "Access to XMLHttpRequest ... blocked by CORS policy"

**原因**：前端域名不在 CORS 白名单中

**解决方案**：
1. 编辑 `.env` 文件
2. 修改 `CORS_ORIGINS` 参数：
   ```env
   CORS_ORIGINS=["http://localhost:3000","http://localhost:3001","https://yourdomain.com"]
   ```
3. 重启后端服务

### ❌ 问题 4：无法连接到 WordPress REST API

**原因**：WordPress REST API 未启用或 URL 错误

**解决方案**：
1. 验证 WordPress URL：https://www.ucppt.com/wp-json/wp/v2/users/me
2. 确保 WordPress REST API 已启用
3. 检查防火墙或代理设置
4. 使用 curl 测试：
   ```bash
   curl -u YOUR_WORDPRESS_USERNAME:your_password https://www.ucppt.com/wp-json/wp/v2/users/me
   ```

### ❌ 问题 5：Token 过期 "Token expired"

**原因**：JWT Token 已过期（默认 7 天）

**解决方案**：
1. 调用刷新 Token 端点：POST `/api/auth/refresh`
2. 前端会自动调用 `fetchWithAuth()` 进行刷新和重试
3. 如果手动发送请求，收到 401 时重新登录

### ❌ 问题 6："JWT 无效或格式错误"

**原因**：Token 格式不正确或已篡改

**解决方案**：
1. 确保 Authorization 头格式：`Authorization: Bearer <token>`
2. 不要修改 Token 值
3. 确保使用了最新的 Token（不是过期的）
4. 重新登录获取新 Token

---

## 使用示例

### 示例 1：React 组件中的认证

```typescript
'use client';

import { useState } from 'react';
import { loginWithWordPress, getCurrentUser, clearWPToken } from '@/lib/wp-auth';

export default function Dashboard() {
  const [user, setUser] = useState(getCurrentUser());

  const handleLogout = () => {
    clearWPToken();
    setUser(null);
    window.location.href = '/auth/login';
  };

  if (!user) {
    return <div>请先登录</div>;
  }

  return (
    <div>
      <h1>欢迎，{user.display_name}</h1>
      <button onClick={handleLogout}>登出</button>
    </div>
  );
}
```

### 示例 2：保护 API 端点

```python
# intelligent_project_analyzer/api/server.py

from fastapi import Depends
from intelligent_project_analyzer.api.auth_middleware import auth_middleware

@app.get("/api/protected-resource")
async def protected_endpoint(
    current_user = Depends(auth_middleware.get_current_user)
):
    return {
        "message": f"Hello, {current_user['username']}",
        "user": current_user
    }
```

### 示例 3：使用 Token 调用 API

```typescript
// 自动附加 Token
const data = await fetchWithAuth('/api/protected-resource');

// 手动附加 Token
import { getWPToken, getAuthHeaders } from '@/lib/wp-auth';

const token = getWPToken();
const response = await fetch('/api/protected-resource', {
  headers: getAuthHeaders()
});
```

---

## 安全建议

### 🔒 生产环境检查清单

- [ ] **更新 Secret Key**：`JWT_SECRET_KEY` 应该是强随机密钥，而不是默认值
  ```bash
  # 生成安全的 Secret Key
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

- [ ] **使用 HTTPS**：确保所有通信都使用 HTTPS（特别是在生产环境）

- [ ] **更新 CORS 配置**：仅允许信任的域名
  ```env
  CORS_ORIGINS=["https://yourdomain.com"]  # 生产环境
  ```

- [ ] **Token 过期时间**：根据安全需求调整
  ```env
  JWT_EXPIRY=3600  # 1 小时（更安全）
  JWT_EXPIRY=604800  # 7 天（更方便）
  ```

- [ ] **启用 HTTP-Only Cookie**：修改前端使用 HTTP-Only Cookie 而不是 localStorage
  ```typescript
  // 在 setWPToken 中设置
  document.cookie = `jwt_token=${token}; HttpOnly; Secure; SameSite=Strict`;
  ```

- [ ] **添加 Token 刷新定时器**：定期自动刷新 Token，避免用户 Token 过期
  ```typescript
  // 在 App.tsx 中
  useEffect(() => {
    const refreshInterval = setInterval(() => {
      if (isAuthenticated()) {
        refreshWPToken();
      }
    }, 6 * 24 * 60 * 60 * 1000); // 每 6 天刷新
    
    return () => clearInterval(refreshInterval);
  }, []);
  ```

- [ ] **防止 XSS 攻击**：避免在 HTML 中输出 Token
  - ✅ 使用 localStorage 或 HTTP-Only Cookie（安全）
  - ❌ 不要在 HTML 中直接显示 Token

- [ ] **防止 CSRF 攻击**：对敏感操作添加 CSRF Token
  - 考虑添加 CSRF 中间件保护 POST/PUT/DELETE 端点

---

## 下一步

1. ✅ **测试认证系统**：运行上述测试流程
2. ⏳ **集成到现有 API**：在 FastAPI 端点添加 `@Depends(auth_middleware.get_current_user)`
3. ⏳ **保护前端路由**：添加认证检查到 Next.js 路由
4. ⏳ **部署到生产环境**：配置 HTTPS、更新 Secret Key、调整 CORS

---

## 相关文档

- 📖 [完整认证指南](WORDPRESS_JWT_AUTH_GUIDE.md)
- 📖 [开发规范](DEVELOPMENT_RULES.md)
- 📖 [项目说明](README.md)

---

**最后更新**：2025-12-12  
**版本**：1.0  
**维护者**：AI Assistant
