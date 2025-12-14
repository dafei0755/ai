# 🔐 WordPress 原生 JWT 认证集成指南 (v7.10)

## ✅ 已完成的配置

### 1️⃣ 后端服务
✅ **WordPress JWT 服务** - `intelligent_project_analyzer/services/wordpress_jwt_service.py`
- WordPress REST API 集成
- JWT Token 生成与验证
- Token 刷新机制

✅ **认证中间件** - `intelligent_project_analyzer/api/auth_middleware.py`
- HTTP 请求认证拦截
- Token 自动提取与验证
- 依赖注入支持

✅ **认证路由** - `intelligent_project_analyzer/api/auth_routes.py`
- POST `/api/auth/login` - 用户登录
- POST `/api/auth/refresh` - Token 刷新
- POST `/api/auth/logout` - 用户登出
- GET `/api/auth/me` - 获取当前用户信息

### 2️⃣ 前端工具
✅ **JWT 工具库** - `frontend-nextjs/lib/wp-auth.ts`
- Token 生成与验证
- 本地存储管理
- 自动刷新机制
- 请求头自动认证

✅ **登录页面** - `frontend-nextjs/app/auth/login/page.tsx`
- 用户友好的登录界面
- 错误提示与成功反馈
- 响应式设计

### 3️⃣ 环境配置
✅ **更新 `.env`**
```env
WORDPRESS_URL=https://www.ucppt.com
WORDPRESS_ADMIN_USERNAME=8pdwoxj8
JWT_SECRET_KEY=auto_generated_secure_key_2025_wordpress
JWT_ALGORITHM=HS256
JWT_EXPIRY=604800
CORS_ORIGINS=["http://localhost:3000","http://localhost:3001","https://www.ucppt.com","https://ucppt.com"]
```

---

## 🚀 立即测试

### 1. 启动后端服务
```bash
cd d:\11-20\langgraph-design
python -B -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000
```

### 2. 启动前端服务
```bash
cd d:\11-20\langgraph-design\frontend-nextjs
npm run dev
```

### 3. 访问登录页面
```
http://localhost:3000/auth/login
```

---

## 🧪 API 测试命令

### 登录
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "8pdwoxj8",
    "password": "your_password"
  }'

# 成功返回：
# {
#   "status": "success",
#   "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
#   "user": {
#     "user_id": 1,
#     "username": "8pdwoxj8",
#     "email": "admin@ucppt.com",
#     "name": "Administrator",
#     "roles": ["administrator"]
#   },
#   "message": "欢迎 Administrator！"
# }
```

### 获取当前用户
```bash
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <your_token>"
```

### 刷新 Token
```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Authorization: Bearer <your_old_token>"
```

---

## 🔗 在 FastAPI 端点中使用认证

### 保护端点示例
```python
from fastapi import Depends
from intelligent_project_analyzer.api.auth_middleware import auth_middleware

@app.get("/api/protected-endpoint")
async def protected_endpoint(
    current_user: dict = Depends(auth_middleware.get_current_user)
):
    return {
        "message": f"Hello {current_user['username']}!",
        "user": current_user
    }
```

### 可选认证示例
```python
@app.get("/api/optional-auth")
async def optional_endpoint(
    current_user: Optional[dict] = Depends(auth_middleware.optional_auth)
):
    if current_user:
        return {"message": f"Welcome {current_user['username']}"}
    else:
        return {"message": "Anonymous user"}
```

---

## 🎯 前端集成示例

### 在 React 组件中使用
```typescript
import { loginWithWordPress, getWPToken, getCurrentUser } from '@/lib/wp-auth';

export function MyComponent() {
  const handleLogin = async (username: string, password: string) => {
    const result = await loginWithWordPress(username, password);
    if (result.status === 'success') {
      console.log('✅ 登录成功:', result.user);
    }
  };

  const handleFetchData = async () => {
    const response = await fetch('/api/protected-data', {
      headers: {
        Authorization: `Bearer ${getWPToken()}`
      }
    });
    const data = await response.json();
    console.log(data);
  };

  return (
    <div>
      <p>当前用户: {getCurrentUser()?.name}</p>
      <button onClick={() => handleLogin('8pdwoxj8', 'password')}>登录</button>
      <button onClick={handleFetchData}>获取数据</button>
    </div>
  );
}
```

---

## ⚙️ 常见配置

### 改变 Token 有效期
编辑 `.env`:
```env
JWT_EXPIRY=86400  # 改为 1 天（86400 秒）
JWT_EXPIRY=3600   # 改为 1 小时（3600 秒）
JWT_EXPIRY=604800 # 默认 7 天（604800 秒）
```

### 更改 Secret Key
```env
# 首次运行时自动生成，也可手动设置：
JWT_SECRET_KEY=your_secure_random_string_here
```

### 调整 CORS
```env
CORS_ORIGINS=["http://localhost:3000","https://yourdomain.com"]
```

---

## 🔒 安全最佳实践

✅ **已实现**
- JWT Token 加密存储（localStorage）
- HTTP-only Cookie 支持（可选）
- Token 自动过期机制
- Token 刷新机制
- WordPress 密码验证（不存储明文）

⚠️ **生产环境建议**
1. **HTTPS 只**: 始终使用 HTTPS，不要在 HTTP 上传输 Token
2. **限制 CORS**: 将 `allow_origins` 改为具体的域名列表
3. **更强 Secret Key**: 使用长且随机的密钥
4. **监控日志**: 定期检查认证失败日志
5. **定期更新**: 保持依赖包最新版本

---

## 📋 已支持的功能

✅ 用户认证（用户名 + 密码）
✅ JWT Token 生成与验证
✅ Token 自动刷新
✅ 用户信息获取
✅ 登出（客户端清除 Token）
✅ 跨域请求支持
✅ 异常处理与友好错误提示

---

## 🆘 故障排除

### 问题 1: 登录返回 401
**原因**: WordPress 用户名或密码错误
**解决**: 检查 `.env` 中的 `WORDPRESS_ADMIN_USERNAME` 是否正确

### 问题 2: Token 无效错误
**原因**: Secret Key 不匹配或 Token 过期
**解决**: 检查 `JWT_SECRET_KEY` 配置，或重新登录获取新 Token

### 问题 3: CORS 错误
**原因**: 请求来源未在 `CORS_ORIGINS` 白名单中
**解决**: 更新 `.env` 中的 `CORS_ORIGINS`

### 问题 4: WordPress API 连接失败
**原因**: `WORDPRESS_URL` 不可访问或 WordPress REST API 被禁用
**解决**: 
- 验证 WordPress 网站是否在线
- 检查 `wp-json` 端点是否可访问
- 确保 WordPress REST API 未被禁用

---

## 📚 相关文件

| 文件 | 用途 |
|------|------|
| `intelligent_project_analyzer/services/wordpress_jwt_service.py` | JWT 服务逻辑 |
| `intelligent_project_analyzer/api/auth_middleware.py` | 认证中间件 |
| `intelligent_project_analyzer/api/auth_routes.py` | 认证 API 端点 |
| `frontend-nextjs/lib/wp-auth.ts` | 前端工具库 |
| `frontend-nextjs/app/auth/login/page.tsx` | 登录页面 |
| `.env` | 环境配置 |

---

## 📞 支持

如有问题，请检查：
1. ✅ 后端日志: `logs/server.log`
2. ✅ 前端浏览器控制台: F12 → Console
3. ✅ 网络请求: F12 → Network
4. ✅ 本文档的故障排除部分

**创建时间**: 2025-12-12  
**版本**: v7.10 WordPress 原生 JWT 认证
