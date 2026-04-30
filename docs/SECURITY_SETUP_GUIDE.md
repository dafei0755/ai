# 安全配置指南

**最后更新**: 2025-12-14
**版本**: 1.0
**状态**: 生产就绪

---

## 目录

1. [概述](#概述)
2. [环境变量配置](#环境变量配置)
3. [WordPress 配置](#wordpress-配置)
4. [部署安全检查清单](#部署安全检查清单)
5. [安全最佳实践](#安全最佳实践)
6. [故障排查](#故障排查)

---

## 概述

本指南提供了部署 WordPress SSO 集成系统时必需的安全配置步骤。遵循本指南可以确保：

- ✅ 凭证不硬编码到源代码中
- ✅ JWT 密钥在 WordPress 和 Python 后端之间同步
- ✅ 敏感信息不被提交到版本控制系统
- ✅ 生产环境配置与开发环境隔离

---

## 环境变量配置

### 1. 创建 `.env` 文件

在项目根目录创建 `.env` 文件（已被 `.gitignore` 排除）：

```bash
# WordPress 配置
WORDPRESS_URL=https://www.ucppt.com
WORDPRESS_ADMIN_USERNAME=YOUR_WORDPRESS_USERNAME
WORDPRESS_ADMIN_PASSWORD='YOUR_WORDPRESS_PASSWORD'

# JWT 配置
JWT_SECRET_KEY=YOUR_JWT_SECRET_KEY
JWT_ALGORITHM=HS256
JWT_EXPIRY=604800

# Next.js 配置
NEXTJS_APP_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000

# CORS 配置
CORS_ORIGINS=http://localhost:3000,https://www.ucppt.com,https://ai.ucppt.com

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# API 配置
API_HOST=0.0.0.0
API_PORT=8000
SESSION_TTL_HOURS=72

# Vision API (可选)
GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY
ENABLE_VISION_API=true
```

### 2. 特殊字符处理

**重要**: 如果密码包含特殊字符（如 `#`, `$`, `%`, `&`, `@`），必须使用单引号包裹：

```bash
# ✅ 正确：使用单引号包裹
WORDPRESS_ADMIN_PASSWORD='MyP@ssw0rd#2025'

# ❌ 错误：未包裹会导致 # 后的内容被视为注释
WORDPRESS_ADMIN_PASSWORD=MyP@ssw0rd#2025
```

### 3. 生产环境 `.env.production`

在生产环境使用单独的配置文件：

```bash
# WordPress 配置
WORDPRESS_URL=https://www.ucppt.com
WORDPRESS_ADMIN_USERNAME=YOUR_PRODUCTION_USERNAME
WORDPRESS_ADMIN_PASSWORD='YOUR_PRODUCTION_PASSWORD'

# JWT 配置（生产环境使用强密钥）
JWT_SECRET_KEY=REPLACE_WITH_LONG_RANDOM_STRING_64_CHARACTERS_MINIMUM

# Next.js 配置（生产域名）
NEXTJS_APP_URL=https://ai.ucppt.com
NEXT_PUBLIC_API_URL=https://api.ucppt.com

# CORS 配置（仅允许生产域名）
CORS_ORIGINS=https://www.ucppt.com,https://ai.ucppt.com

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# API 配置
API_HOST=0.0.0.0
API_PORT=8000
SESSION_TTL_HOURS=72
```

### 4. 生成强 JWT 密钥

使用以下命令生成安全的 JWT 密钥：

**Python**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

**Node.js**:
```bash
node -e "console.log(require('crypto').randomBytes(64).toString('base64'))"
```

**OpenSSL**:
```bash
openssl rand -base64 64
```

示例输出：
```
7xK9mP3nQ8wR5tU2vY4zB6cE1fH7jL0kN3pS8uX5yA9dG2hJ4mQ7rT0vW3xZ6bC9eF2hK5nP8sU1wY4zA7cE0gJ3lN6qT9vX2yB5dF8hK1mP4sU7wZ0cE3gJ6lN9qT2vY5zA8
```

将此密钥配置到 `.env` 的 `JWT_SECRET_KEY` 字段。

---

## WordPress 配置

### 1. 配置 wp-config.php

在 WordPress 的 `wp-config.php` 文件中添加以下常量（在 `AUTH_KEY` 定义之后）：

```php
<?php
// wp-config.php

// 标准 WordPress 配置
define('AUTH_KEY',         'put your unique phrase here');
define('SECURE_AUTH_KEY',  'put your unique phrase here');
// ... 其他标准配置 ...

// ✅ Next.js SSO 集成配置
// JWT 密钥（必须与 Python 后端 .env 中的 JWT_SECRET_KEY 一致）
define('PYTHON_JWT_SECRET', 'YOUR_JWT_SECRET_KEY');

// WordPress 管理员凭证（用于 WPCOM API 调用）
define('WP_ADMIN_USERNAME', 'YOUR_WORDPRESS_USERNAME');
define('WP_ADMIN_PASSWORD', 'YOUR_WORDPRESS_PASSWORD');

// ✅ 生产环境关闭调试模式（避免日志泄露敏感信息）
define('WP_DEBUG', false);
define('WP_DEBUG_LOG', false);
define('WP_DEBUG_DISPLAY', false);

/* That's all, stop editing! Happy publishing. */
```

**重要注意事项**:
- `PYTHON_JWT_SECRET` 必须与 Python `.env` 中的 `JWT_SECRET_KEY` 完全一致
- 生产环境必须设置 `WP_DEBUG` 为 `false`
- 不要将 `wp-config.php` 提交到版本控制系统

### 2. 安装 WordPress 插件

安装以下两个 WordPress 插件：

#### 2.1 Next.js SSO Integration v3.0.4

**文件**: `nextjs-sso-integration-v3.php`

**安装步骤**:
1. 将 `nextjs-sso-integration-v3.php` 复制到 WordPress 插件目录：
   ```
   wp-content/plugins/nextjs-sso-integration-v3/nextjs-sso-integration-v3.php
   ```
2. WordPress 后台 → 插件 → 激活 "Next.js SSO Integration v3"

**功能**: 生成 JWT Token 并在 iframe 中传递给 Next.js 应用

#### 2.2 WPCOM Custom API v1.0.0

**文件**: `wpcom-custom-api-v1.0.0.php`

**安装步骤**:
1. 将 `wpcom-custom-api-v1.0.0.php` 复制到 WordPress 插件目录：
   ```
   wp-content/plugins/wpcom-custom-api/wpcom-custom-api.php
   ```
2. WordPress 后台 → 插件 → 激活 "WPCOM Member Custom API"

**功能**: 暴露 REST API 端点用于获取会员数据（等级、订单、钱包）

### 3. 配置插件设置

**WordPress 后台 → 设置 → Next.js SSO Integration**:

- **Next.js 应用 URL**:
  - 开发环境: `http://localhost:3000`
  - 生产环境: `https://ai.ucppt.com`

- **回调 URL**:
  - 开发环境: `http://localhost:3000/auth/callback`
  - 生产环境: `https://ai.ucppt.com/auth/callback`

### 4. 创建嵌入页面

在 WordPress 中创建一个新页面（例如 `/nextjs`），添加短代码：

```
[nextjs_app]
```

发布页面后，用户访问 `https://www.ucppt.com/nextjs` 即可在 WordPress 页面中使用 Next.js 应用。

---

## 部署安全检查清单

### 开发环境部署

- [ ] 创建 `.env` 文件，配置所有必需的环境变量
- [ ] 验证 `.gitignore` 包含 `.env`（使用 `git check-ignore -v .env`）
- [ ] WordPress `wp-config.php` 添加 `PYTHON_JWT_SECRET` 常量
- [ ] 启动 Redis 服务（`redis-server`）
- [ ] 启动 Python 后端（`python -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000`）
- [ ] 启动 Next.js 前端（`cd frontend-nextjs && npm run dev`）
- [ ] 测试 SSO 登录流程（WordPress 登录 → Next.js 应用自动认证）
- [ ] 测试会员 API（`/api/member/my-membership` 返回正确数据）

### 生产环境部署

- [ ] 创建 `.env.production` 文件，使用生产凭证
- [ ] 生成强 JWT 密钥（64+ 字符）
- [ ] WordPress `wp-config.php` 设置 `WP_DEBUG = false`
- [ ] 配置 Nginx/Apache 反向代理（HTTPS 强制）
- [ ] 配置 CORS 仅允许生产域名
- [ ] 使用 Gunicorn 运行 Python 后端（4+ workers）
- [ ] 使用 PM2 或 systemd 管理 Next.js 进程
- [ ] 配置 SSL 证书（Let's Encrypt 或商业证书）
- [ ] 测试从 WordPress 嵌入页面访问 Next.js 应用
- [ ] 验证 Token 过期时间和自动续期
- [ ] 配置日志轮转（防止日志文件过大）

### 安全审计

- [ ] 运行 `grep -r "YOUR_" .` 确认无占位符
- [ ] 运行 `git log -p` 检查历史提交无敏感信息
- [ ] 检查 `.env` 文件权限（`chmod 600 .env`）
- [ ] 验证生产环境不输出调试日志
- [ ] 测试 API 端点需要有效 Token 才能访问
- [ ] 测试 Token 过期后自动拒绝请求

---

## 安全最佳实践

### 1. 密码管理

- ✅ **强密码**: 使用至少 16 字符，包含大小写字母、数字和特殊字符
- ✅ **密码轮换**: 生产环境每 90 天更换一次密码和 JWT 密钥
- ✅ **密码存储**: 仅存储在 `.env` 文件中，不提交到 Git
- ❌ **禁止**: 在代码、注释、日志中写入明文密码

### 2. JWT 安全

- ✅ **密钥强度**: 至少 64 字符随机字符串
- ✅ **过期时间**: 设置合理的过期时间（默认 7 天）
- ✅ **算法选择**: 使用 HS256 或 RS256（不使用 none）
- ❌ **禁止**: 在客户端存储敏感用户信息（如密码、信用卡）

### 3. API 安全

- ✅ **CORS**: 仅允许受信任的域名
- ✅ **HTTPS**: 生产环境强制使用 HTTPS
- ✅ **速率限制**: 配置 API 速率限制（防止暴力破解）
- ❌ **禁止**: 在 GET 请求中传递敏感参数（如密码、Token）

### 4. 日志安全

- ✅ **脱敏**: 日志中不输出完整 Token（仅输出前 10 字符）
- ✅ **轮转**: 配置日志轮转（每日或每 100MB）
- ✅ **权限**: 日志文件权限设置为 `600`（仅所有者可读写）
- ❌ **禁止**: 在生产环境开启 `WP_DEBUG` 或 `DEBUG=true`

### 5. 代码审查

- ✅ **Pre-commit Hook**: 使用 Git hooks 防止提交 `.env` 文件
- ✅ **定期审计**: 每月运行 `python sanitize_credentials.py` 检查文档
- ✅ **依赖更新**: 定期更新依赖包修复安全漏洞（`pip list --outdated`, `npm audit`）

---

## 故障排查

### 问题 1: Token 验证失败 (401 Unauthorized)

**症状**: Next.js 应用显示 "未授权" 错误

**原因**: WordPress 和 Python 使用的 JWT 密钥不一致

**解决方案**:

1. 检查 WordPress `wp-config.php`:
   ```bash
   grep PYTHON_JWT_SECRET /path/to/wp-config.php
   ```

2. 检查 Python `.env`:
   ```bash
   grep JWT_SECRET_KEY .env
   ```

3. 确保两者完全一致（包括特殊字符）

4. 重启 Python 后端:
   ```bash
   pkill -f uvicorn
   python -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000
   ```

### 问题 2: 密码包含 `#` 符号导致截断

**症状**: WordPress API 认证失败，密码错误

**原因**: `.env` 文件中 `#` 被视为注释符号

**解决方案**:

修改 `.env` 文件，使用单引号包裹密码：

```bash
# ❌ 错误
WORDPRESS_ADMIN_PASSWORD=MyP@ssw0rd#2025

# ✅ 正确
WORDPRESS_ADMIN_PASSWORD='MyP@ssw0rd#2025'
```

重启 Python 后端使配置生效。

### 问题 3: WordPress 插件报错 "PYTHON_JWT_SECRET not defined"

**症状**: WordPress 页面显示白屏或 "配置错误" 提示

**原因**: `wp-config.php` 未定义 `PYTHON_JWT_SECRET` 常量

**解决方案**:

1. 编辑 `wp-config.php`，添加：
   ```php
   define('PYTHON_JWT_SECRET', 'YOUR_JWT_SECRET_KEY');
   ```

2. 确保常量值与 Python `.env` 中的 `JWT_SECRET_KEY` 一致

3. 保存文件，刷新 WordPress 页面

### 问题 4: Next.js 应用无法获取会员数据

**症状**: 会员卡片显示空白或 "加载失败"

**原因**: WPCOM Custom API 插件未激活或 API 端点不可访问

**解决方案**:

1. 检查插件是否激活:
   - WordPress 后台 → 插件 → 确认 "WPCOM Member Custom API" 已激活

2. 测试 API 端点:
   ```bash
   curl -s https://www.ucppt.com/wp-json/custom/v1/user-membership/1 \
     -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN"
   ```

3. 如果返回 404，重新安装插件:
   - 删除 `wp-content/plugins/wpcom-custom-api/`
   - 重新上传 `wpcom-custom-api-v1.0.0.php`
   - WordPress 后台激活插件

### 问题 5: CORS 错误

**症状**: 浏览器控制台显示 "CORS policy" 错误

**原因**: FastAPI CORS 配置不包含 WordPress 域名

**解决方案**:

1. 检查 `.env` 的 `CORS_ORIGINS`:
   ```bash
   grep CORS_ORIGINS .env
   ```

2. 确保包含 WordPress 域名:
   ```bash
   CORS_ORIGINS=http://localhost:3000,https://www.ucppt.com,https://ai.ucppt.com
   ```

3. 重启 Python 后端

### 问题 6: 文档中仍有真实凭证

**症状**: 文档中仍包含 `8pdwoxj8` 或真实密码

**原因**: 文档未经过脱敏处理

**解决方案**:

运行脱敏脚本：

```bash
python sanitize_credentials.py
```

脚本会自动查找并替换所有 `.md` 文件中的真实凭证。

---

## 文件权限配置

### Linux/macOS

```bash
# .env 文件（仅所有者可读）
chmod 600 .env
chmod 600 .env.production

# wp-config.php（仅所有者可读）
chmod 600 /path/to/wp-config.php

# 日志文件（仅所有者可读写）
chmod 600 logs/*.log

# 插件文件（所有者可读写，组和其他人只读）
chmod 644 nextjs-sso-integration-v3.php
chmod 644 wpcom-custom-api-v1.0.0.php
```

### Windows

```powershell
# .env 文件（移除继承权限，仅当前用户访问）
icacls .env /inheritance:r
icacls .env /grant:r "%USERNAME%:F"

# wp-config.php
icacls C:\path\to\wp-config.php /inheritance:r
icacls C:\path\to\wp-config.php /grant:r "%USERNAME%:F"
```

---

## Git 安全配置

### .gitignore 配置

确保 `.gitignore` 包含以下规则：

```gitignore
# 环境变量
.env
.env.local
.env.production
.env.*.local

# WordPress 配置
wp-config.php

# 临时文件
*.log
*.swp
*.swo
*~

# 敏感文件
*credentials*
*secrets*
*password*
```

### Pre-commit Hook（防止泄露）

创建 `.git/hooks/pre-commit`：

```bash
#!/bin/bash

# 检查是否要提交 .env 文件
if git diff --cached --name-only | grep -E '^\.env'; then
    echo "Error: Attempting to commit .env file!"
    echo "This file contains sensitive information and should not be committed."
    exit 1
fi

# 检查是否包含真实凭证
if git diff --cached | grep -E 'YOUR_WORDPRESS_USERNAME|YOUR_WORDPRESS_PASSWORD|YOUR_JWT_SECRET_KEY'; then
    echo "Warning: Changes contain placeholder credentials."
    echo "Please ensure real credentials are replaced before deployment."
fi

exit 0
```

赋予执行权限：

```bash
chmod +x .git/hooks/pre-commit
```

---

## 参考文档

- [WordPress Integration Guide](WORDPRESS_INTEGRATION_GUIDE.md) - 完整集成开发指南
- [Python Decouple Documentation](https://pypi.org/project/python-decouple/) - 环境变量管理
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725) - JWT 安全最佳实践
- [OWASP Top 10](https://owasp.org/www-project-top-ten/) - Web 应用安全风险

---

**最后更新**: 2025-12-14
**维护者**: UCPPT Team
**版本**: 1.0
