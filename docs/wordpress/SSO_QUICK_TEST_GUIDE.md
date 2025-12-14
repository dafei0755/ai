# 🚀 SSO 单点登录快速测试指南

## ✅ 实施完成清单

### 前端（Next.js）
- ✅ 修改登录页面：添加"使用 ucppt.com 账号登录"按钮
- ✅ 创建回调处理页面：`/auth/callback`
- ✅ 添加 Token 验证逻辑
- ✅ 集成 AuthContext 自动登录

### 后端（FastAPI）
- ✅ 添加 Token 验证端点：`POST /api/auth/verify`
- ✅ 扩展用户信息返回（包含 avatar_url）

### WordPress（待配置）
- ⏳ 上传并启用 Next.js SSO 插件（REST API 方案，见仓库根目录 `nextjs-sso-integration-v2.0.2.zip`）
- ⏳ 创建/确认 SSO 回调页（示例：`https://www.ucppt.com/js`，页面内容包含短代码 `[nextjs_sso_callback]`）
- ⏳ 在 WPCOM 用户中心配置“登录后跳转”到该回调页（用于自动获取 token 并回跳本机）

---

## 🧪 测试流程

### 步骤 1：启动前端服务

```bash
cd frontend-nextjs
npm run dev
```

访问：http://localhost:3000（若 3000 被占用，Next.js 会自动切到 http://localhost:3001，以终端输出为准）

### 步骤 2：验证自动跳转

应该自动跳转到：http://localhost:3000/auth/login（或 http://localhost:3001/auth/login）

### 步骤 3：点击 SSO 登录按钮

点击**"使用 ucppt.com 账号登录"**按钮

应该跳转到：
```
https://www.ucppt.com/login?modal-type=login&redirect_to=...
```

> ⚠️ 说明：WPCOM 用户中心不走标准 WordPress 登录 Hook，当前联调推荐使用“站点回调页 + REST API 获取 token”的方式（见下面步骤 4/5）。

### 步骤 4：WordPress 端配置（重要）

⚠️ **在测试前，必须先配置 WordPress**

1. 在 WordPress 后台上传并启用插件：`nextjs-sso-integration-v2.0.2.zip`
2. 创建（或确认已有）页面 `https://www.ucppt.com/js`，页面内容添加短代码：`[nextjs_sso_callback]`
3. 在 WPCOM 用户中心设置“登录后跳转”到 `https://www.ucppt.com/js`
4. 验证 REST API：登录状态下访问 `https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token` 应返回 200 且包含 `token`

### 步骤 5：完成登录

1. 在 WordPress 登录页面输入用户名和密码
2. 登录成功后，应先进入 `https://www.ucppt.com/js`，页面会自动获取 token 并跳转回：
   ```
    http://localhost:3000/auth/callback?token=eyJhbGciOiJIUzI1NiIs...
    # 或
    http://localhost:3001/auth/callback?token=eyJhbGciOiJIUzI1NiIs...
   ```
3. 回调页面自动处理 Token
4. 跳转到首页
5. 左下角显示用户信息 ✅

---

## 🐛 快速故障排查

### 问题：WordPress 登录后未跳转回来

**检查**：
1. WordPress SSO 插件是否激活？
2. 浏览器开发者工具 → Network 查看重定向 URL
3. WordPress 错误日志：`wp-content/debug.log`

**临时解决**：
手动在浏览器访问：
```
http://localhost:3000/auth/callback?token=YOUR_MANUAL_TOKEN
# 或
http://localhost:3001/auth/callback?token=YOUR_MANUAL_TOKEN
```

### 问题：浏览器提示 `ERR_CONNECTION_REFUSED`

**含义**：本机对应端口（`3000/3001`）没有运行 Next.js 前端服务。

**解决**：
1. 在本机启动前端 `npm run dev`
2. 以终端输出的 Local 地址为准（例如 `http://localhost:3001`）

### 问题：回调页面显示"Token 验证失败"

**检查**：
1. 后端服务是否启动？
2. Token 格式是否正确？（Base64 编码）
3. Simple JWT Login 插件配置是否正确？

**调试命令**：
```bash
# 测试后端验证端点
curl -X POST http://localhost:8000/api/auth/verify \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

### 问题：CORS 跨域错误

**症状**：浏览器控制台显示 CORS 错误

**解决**：
确认 WordPress SSO 插件中的 CORS 配置正确：
```php
// 开发环境常见端口：3000/3001
header('Access-Control-Allow-Origin: http://localhost:3000');
```

---

## 🧾 未完成任务（忠实记录）

1. 将“自动跳转到 WPCOM 登录页”的 `redirect_to` 目标与 `/js` 联调流程对齐（当前代码为 `/auth/callback`，但 token 获取链路依赖 `/js`）。
2. 完成从“本机联调（localhost）”到“生产域名（ai.ucppt.com）”的回调地址替换与验证。
3. 完成端到端回归：首次登录 / 已登录 / 退出登录 / token 失效等场景。

---

## 📋 完整测试场景

### 场景 1：首次访问（未登录）
1. ✅ 访问首页 → 自动跳转登录页
2. ✅ 点击 SSO 按钮 → 跳转 WordPress
3. ✅ WordPress 登录 → 生成 Token
4. ✅ 跳转回调页面 → 验证 Token
5. ✅ 进入首页 → 显示用户信息

### 场景 2：已登录 WordPress（自动登录）
1. ✅ 在 WordPress 网站已登录
2. ✅ 访问 Next.js 应用
3. ✅ 点击 SSO 按钮
4. ✅ WordPress 检测已登录 → 直接生成 Token
5. ✅ 无需输入密码 → 自动完成认证 ⚡

### 场景 3：Token 过期（自动重新登录）
1. ✅ Token 过期（7天后）
2. ✅ AuthContext 检测 Token 无效
3. ✅ 自动跳转登录页
4. ✅ 重新认证

---

## 🎯 预期效果

### 用户体验：
```
用户访问 Next.js 应用
    ↓
检测未登录，跳转登录页
    ↓
点击"使用 ucppt.com 账号登录"
    ↓
跳转到 WordPress（如果已登录 WordPress，此步骤自动完成）
    ↓
自动跳转回 Next.js（带 Token）
    ↓
✅ 登录成功，显示用户信息
```

**总耗时**：
- 首次登录：~5秒
- 已登录 WordPress：**~1秒**（几乎无感）⚡

---

## 📞 下一步

1. **完成 WordPress 配置**
   - 参考 `WORDPRESS_SSO_SETUP_GUIDE.md`
   - 上传插件文件
   - 激活并测试

2. **测试登录流程**
   - 清除浏览器缓存
   - 完整走一遍登录流程
   - 验证所有功能正常

3. **优化用户体验**
   - 添加登录状态保存（记住我）
   - 实现 Token 自动刷新
   - 添加退出登录功能

---

**准备好了吗？开始测试吧！** 🚀

如有问题，请查看 `WORDPRESS_SSO_SETUP_GUIDE.md` 的故障排查章节。
