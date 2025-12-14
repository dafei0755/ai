# Next.js SSO Integration v3.0.2 插件安装指南

## 📦 插件信息

- **插件名称**: Next.js SSO Integration v3
- **版本**: 3.0.2
- **发布日期**: 2025-12-14
- **功能**: WordPress 单点登录 (SSO) 集成 Next.js 应用

---

## 🆕 v3.0.2 重要更新

### ✅ 关键修复

1. **JWT 密钥统一**
   - 优先使用 Simple JWT Login 插件的 `$d4@5fg54ll_t_45gH` 密钥
   - 与 Python 后端密钥保持一致 (`.env` 中的 `JWT_SECRET_KEY`)
   - 兼容 WordPress `AUTH_KEY` 作为备用方案

2. **WPCOM Custom API 插件集成**
   - 与 WPCOM Member Custom API v1.0.0 插件配合工作
   - 支持读取会员等级、到期日期、钱包余额等数据
   - 从 WordPress meta 字段读取 VIP 信息 (`wp_vip_type`, `wp_vip_end_date`)

3. **完整 SSO 流程**
   - WordPress 登录 → 生成 JWT Token → iframe URL 传递 Token → Next.js 前端验证
   - 自动绕过跨域 Cookie 限制 (SameSite 策略)
   - iframe 自动高度调整，完美嵌入 WordPress 页面

---

## ✅ 前置条件

确保已完成以下配置：

### 1. Simple JWT Login 插件已安装并启用 ✅

- **插件**: Simple JWT Login
- **功能**: Authentication (认证功能)
- **JWT 密钥**: `$d4@5fg54ll_t_45gH` (HS256 算法)
- **端点**: `/wp-json/simple-jwt-login/v1/auth`

**验证方法**:
```bash
curl -X POST "https://www.ucppt.com/wp-json/simple-jwt-login/v1/auth" \
  -H "Content-Type: application/json" \
  -d '{"username": "8pdwoxj8", "password": "YOUR_PASSWORD"}'
```

预期返回：
```json
{
  "success": true,
  "data": {
    "jwt": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
}
```

### 2. WPCOM Member Custom API 插件已安装 ✅

- **插件**: WPCOM Member Custom API
- **版本**: 1.0.0
- **功能**: 暴露 WPCOM Member Pro 会员数据 REST API
- **端点**: `/wp-json/custom/v1/user-membership/{user_id}`

**验证方法**:
```bash
curl -s "https://www.ucppt.com/wp-json/custom/v1/my-membership" \
  -H "Authorization: Bearer {JWT_TOKEN}"
```

预期返回：
```json
{
  "user_id": "1",
  "membership": null,
  "meta": {
    "wp_vip_type": "vip-1",
    "wp_vip_begin_date": "2024-09-10",
    "wp_vip_end_date": "2025-09-10"
  }
}
```

### 3. WordPress 配置

在 `wp-config.php` 中添加（如果尚未添加）：

```php
// JWT 密钥（与 Simple JWT Login 和 Python 后端保持一致）
define('PYTHON_JWT_SECRET', '$d4@5fg54ll_t_45gH');
```

**位置**: 在 `/* That's all, stop editing! Happy publishing. */` 之前

---

## 📥 安装步骤

### 方式一：通过 WordPress 后台安装（推荐）

1. **下载插件包**
   - 文件名: `nextjs-sso-integration-v3.0.2.zip`
   - 位置: 项目根目录

2. **上传安装**
   - WordPress 后台 → **插件** → **安装插件**
   - 点击 **上传插件** 按钮
   - 选择 `nextjs-sso-integration-v3.0.2.zip` 文件
   - 点击 **现在安装**

3. **激活插件**
   - 安装完成后，点击 **激活插件**
   - 看到 "插件已激活" 提示即成功

4. **⚠️ 删除旧版本插件**
   - 如果之前安装过 v1.x 或 v2.x 版本，请先停用并删除
   - 避免多个版本冲突

### 方式二：通过 FTP/SFTP 手动安装

1. **解压插件文件**
   ```bash
   unzip nextjs-sso-integration-v3.0.2.zip
   ```

2. **上传到 WordPress**
   ```bash
   # 将 nextjs-sso-integration-v3 文件夹上传到：
   /path/to/wordpress/wp-content/plugins/nextjs-sso-integration-v3/
   ```

3. **激活插件**
   - WordPress 后台 → **插件** → **已安装的插件**
   - 找到 **Next.js SSO Integration v3**
   - 点击 **启用**

---

## 🔧 插件配置

### 1. 访问设置页面

WordPress 后台 → **设置** → **Next.js SSO v3**

### 2. 配置回调 URL

**开发环境**:
```
Next.js 回调 URL: http://localhost:3000/auth/callback
Next.js 应用 URL: http://localhost:3000
```

**生产环境**:
```
Next.js 回调 URL: https://ai.ucppt.com/auth/callback
Next.js 应用 URL: https://ai.ucppt.com
```

### 3. 配置检查清单

插件设置页面会显示以下检查项：

| 配置项 | 说明 |
|--------|------|
| ✓ **PYTHON_JWT_SECRET** | 已在 wp-config.php 中配置 |
| ✓ **回调 URL** | 当前配置有效 |
| ⚠ **嵌入页面** | 需要创建（固定链接应设为 `/nextjs`） |

---

## 🚀 创建嵌入页面

### 步骤 1: 创建 WordPress 页面

1. WordPress 后台 → **页面** → **新建页面**
2. 页面标题: `AI 设计高参` (或您喜欢的名称)
3. 页面内容: 添加以下短代码

```
[nextjs_app]
```

**可选参数**:
```
[nextjs_app height="800px"]
[nextjs_app url="/analysis/123"]
[nextjs_app height="100vh" url="/"]
```

### 步骤 2: 设置固定链接

1. 在右侧 **固定链接** 设置中
2. URL slug 设为: `nextjs`
3. 完整 URL: `https://www.ucppt.com/nextjs`

### 步骤 3: 发布页面

点击 **发布** 按钮

### 步骤 4: 刷新固定链接

**重要**: WordPress 后台 → **设置** → **固定链接** → 点击 **保存更改**

（即使不修改任何设置，也需要点击保存来刷新重写规则）

---

## 🧪 测试 SSO 流程

### 1. 未登录用户测试

1. **退出 WordPress 登录** (如果已登录)
2. **访问嵌入页面**: `https://www.ucppt.com/nextjs`
3. **预期结果**:
   - 显示 "需要登录" 提示卡片
   - 显示 "立即登录" 按钮
4. **点击 "立即登录"**:
   - 触发 WordPress 原生登录弹窗
   - 或跳转到登录页面
5. **输入凭证并登录**
6. **自动重定向回嵌入页面**
7. **Next.js 应用成功加载，显示用户信息**

### 2. 已登录用户测试

1. **在 WordPress 登录**
2. **访问嵌入页面**: `https://www.ucppt.com/nextjs`
3. **预期结果**:
   - 直接显示 Next.js 应用 iframe
   - iframe 自动接收 JWT Token (通过 URL 参数 `?sso_token=xxx`)
   - Next.js 应用验证 Token 成功
   - 显示用户头像和用户名
   - 左下角用户面板显示会员等级

### 3. 会员信息显示测试

**在 Next.js 应用中**:

1. **点击左下角用户头像**
2. **打开用户面板**
3. **预期显示**:
   - 🎨 **通用设置**: 浅色/深色/跟随系统
   - 👤 **账号管理**:
     - VIP 等级 (例如: VIP-1)
     - 到期时间 (例如: 2025-09-10)
     - 钱包余额 (例如: ¥100.50)
   - 📋 **服务协议**: 服务条款、隐私政策链接

---

## 🔍 故障排查

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

### 问题 2: [nextjs_app] 显示为纯文本

**原因**: 插件未激活或 WordPress 缓存未清除

**解决方案**:
1. 确认插件已激活
2. 清除 WordPress 缓存 (如果使用缓存插件)
3. WordPress 后台 → **设置** → **固定链接** → **保存更改**
4. 刷新页面 (Ctrl+F5 强制刷新)

### 问题 3: iframe 显示 "未登录"

**原因**: JWT Token 密钥不一致或未传递

**解决方案**:

1. **检查 wp-config.php**:
   ```php
   define('PYTHON_JWT_SECRET', '$d4@5fg54ll_t_45gH');
   ```

2. **检查 .env 文件** (Python 后端):
   ```bash
   JWT_SECRET_KEY=$d4@5fg54ll_t_45gH
   ```

3. **检查 Simple JWT Login 设置**:
   - General → JWT Decryption Key: `$d4@5fg54ll_t_45gH`
   - Authentication → JWT Decryption Key: `$d4@5fg54ll_t_45gH`

4. **重启 Python 后端**:
   ```bash
   python -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000
   ```

### 问题 4: 会员信息显示 "免费用户"

**原因**: WPCOM Custom API 插件未安装或未激活

**解决方案**:
1. 确认 WPCOM Custom API v1.0.0 插件已激活
2. 测试 API 端点:
   ```bash
   curl -s "https://www.ucppt.com/wp-json/custom/v1/my-membership" \
     -H "Authorization: Bearer {JWT_TOKEN}"
   ```
3. 如果返回 404，刷新固定链接规则
4. 检查用户 meta 数据是否存在 VIP 信息

### 问题 5: iframe 高度不自动调整

**原因**: 前端 iframe messenger 未正确加载

**解决方案**:
1. 检查浏览器控制台是否有错误
2. 确认 Next.js 应用已部署并运行
3. 检查 iframe 是否加载成功 (F12 → Network)

---

## 📋 调试信息

### 查看调试页面

WordPress 后台 → **设置** → **Next.js SSO v3 调试**

**显示内容**:
- 当前使用的 JWT 密钥源 (PYTHON_JWT_SECRET / AUTH_KEY)
- JWT 生成测试结果
- JWT 验证测试结果
- REST API 端点列表
- 系统信息 (PHP 版本、WordPress 版本、OPcache 状态)

### 查看日志

**WordPress 日志**:
- 文件: `wp-content/debug.log`
- 启用方法: 在 `wp-config.php` 中添加:
  ```php
  define('WP_DEBUG', true);
  define('WP_DEBUG_LOG', true);
  define('WP_DEBUG_DISPLAY', false);
  ```

**日志格式**:
```
[Next.js SSO v3.0] JWT 生成成功 (用户: 8pdwoxj8, 密钥: PYTHON_JWT_SECRET)
[Next.js SSO v3.0] 为用户 8pdwoxj8 生成 Token 并嵌入 iframe URL
[Next.js SSO v3.0] JWT 验证成功
```

**Python 后端日志**:
```bash
python -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000 --log-level debug
```

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

1. 访问 `https://www.ucppt.com/nextjs`
2. 使用 WordPress 登录（用户: 8pdwoxj8）
3. 点击左下角用户面板
4. 应该能看到真实的会员等级、钱包余额等信息

---

## ✅ 配置完成标志

当以下测试全部通过时，配置完成：

- ✅ WordPress 插件已激活 (版本 3.0.2)
- ✅ [nextjs_app] 短代码渲染 iframe
- ✅ 未登录用户显示 "立即登录" 按钮
- ✅ 登录后 iframe 自动加载 Next.js 应用
- ✅ JWT Token 通过 URL 参数传递成功
- ✅ Next.js 应用验证 Token 并显示用户信息
- ✅ 用户面板显示 VIP 等级、到期时间、钱包余额

---

## 🎉 完整配置总结

恭喜！您已成功配置：

1. ✅ **Simple JWT Login** - WordPress JWT 认证
2. ✅ **WPCOM Member Custom API** - 会员数据 REST API
3. ✅ **Next.js SSO Integration v3.0.2** - SSO 单点登录和 iframe 嵌入
4. ✅ **JWT 密钥统一** - 三处密钥完全一致
5. ✅ **会员信息集成** - Next.js 应用可获取 WPCOM Member Pro 数据

现在您的 Next.js 应用可以：
- 通过 WordPress 短代码嵌入页面
- 自动单点登录 (SSO)
- 显示用户会员等级
- 显示钱包余额
- 根据 VIP 等级控制功能访问

---

## 📞 需要帮助？

如果遇到问题，请提供以下信息：

1. **WordPress 插件列表截图**（显示 Next.js SSO Integration v3 已激活）
2. **插件设置页面截图**（配置检查清单）
3. **浏览器控制台错误**（F12 → Console）
4. **WordPress debug.log 日志**（最后 50 行）
5. **Python 后端日志**（运行 uvicorn 的终端输出）

---

**最后更新**: 2025-12-14
**插件版本**: 3.0.2
**文档版本**: 1.0
