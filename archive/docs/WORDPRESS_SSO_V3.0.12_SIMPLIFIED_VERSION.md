# WordPress SSO v3.0.12 - 简化版（仅保留宣传页面入口）

## 📋 版本信息

- **版本号**: v3.0.12
- **发布日期**: 2025-12-16
- **更新类型**: 架构简化
- **文件大小**: 16,853 bytes (16 KB)

---

## 🎯 核心更新

### ❌ 已移除功能

**iframe嵌入模式已废弃**：
- 短代码 `[nextjs_app]` 已移除
- 整个iframe嵌入功能已注释（Lines 897-1223）
- `/nextjs` 页面不再需要

### ✅ 保留功能

**宣传页面入口模式**：
- 短代码 `[nextjs-app-entrance]` 正常工作
- `/js` 页面作为唯一入口
- 智能登录跳转（已登录/未登录自动识别）
- 新窗口打开应用（宣传页面保持）

### 🔧 技术改进

1. **按钮实现优化**：
   - 从 `<a href="#">` 改为 `<button type="button">`
   - 避免默认跳转行为
   - 更好的语义化和可访问性

2. **JavaScript增强**：
   - 详细的控制台日志（便于调试）
   - `app_url` 配置验证（未配置时弹窗提示）
   - 浏览器弹窗拦截检测（被拦截时提示用户）

3. **错误处理**：
   - 配置错误：友好的用户提示
   - 弹窗拦截：提示用户允许弹窗

---

## 🚀 快速部署（3分钟）

### 步骤1: 停用旧插件（30秒）

```bash
WordPress后台 → 插件 → 已安装的插件
找到 "Next.js SSO Integration v3"
点击 "停用"
```

### 步骤2: 上传新插件（1分钟）

```bash
插件 → 安装插件 → 上传插件
选择文件: nextjs-sso-integration-v3.0.12.zip
点击 "现在安装"
安装完成后点击 "启用插件"
```

### 步骤3: 验证版本（30秒）

```bash
插件列表确认显示：
- 名称：Next.js SSO Integration v3
- 版本：3.0.12
- 描述：WordPress 单点登录集成 Next.js（v3.0.12 - 简化版：仅保留宣传页面入口）
```

### 步骤4: 配置宣传页面（1分钟）

#### 编辑 `/js` 页面

```bash
WordPress后台 → 页面 → 找到 "js" 页面 → 编辑
```

**短代码配置**：
```
[nextjs-app-entrance app_url="https://ai.ucppt.com?mode=standalone"]
```

⚠️ **重要**：必须配置 `app_url` 参数，默认值 `http://localhost:3000` 仅用于开发环境。

#### 删除旧的 `/nextjs` 页面（可选）

如果存在使用 `[nextjs_app]` 短代码的页面，可以删除：

```bash
WordPress后台 → 页面 → 找到包含 [nextjs_app] 的页面
移至回收站或永久删除
```

### 步骤5: 清除缓存（30秒）

```bash
# WordPress缓存
设置 → WP Super Cache → 删除缓存

# 浏览器缓存
Ctrl + Shift + R（强制刷新）
```

### 步骤6: 测试验证（1分钟）

```bash
# 测试已登录流程
访问: https://www.ucppt.com/js
点击 "立即使用" 按钮
✅ 应该在新窗口打开应用
✅ 宣传页面保持在原标签页

# 测试未登录流程
退出WordPress登录
访问: https://www.ucppt.com/js
点击 "立即使用" 按钮
✅ 跳转到WordPress登录页
✅ 登录后返回宣传页面
✅ 1秒后在新窗口打开应用
```

---

## 🔄 版本对比

### v3.0.8-v3.0.11（旧版）

**架构**：
- ✅ iframe嵌入模式（`[nextjs_app]` 短代码）
- ✅ 宣传页面入口模式（`[nextjs-app-entrance]` 短代码）
- ⚠️ 两种模式并存，配置复杂

**按钮实现**：
- `<a href="#">` 标签
- 需要 `e.preventDefault()` 阻止默认行为

**错误处理**：
- ❌ 配置错误无提示
- ❌ 弹窗拦截无提示

---

### v3.0.12（新版）

**架构**：
- ❌ iframe嵌入模式（已移除）
- ✅ 宣传页面入口模式（唯一模式）
- ✅ 架构简化，配置清晰

**按钮实现**：
- `<button type="button">` 标签
- 无需 `e.preventDefault()`
- 更语义化，更可靠

**错误处理**：
- ✅ 配置错误：弹窗提示用户
- ✅ 弹窗拦截：提示用户允许

---

## 📊 功能验证

### 验证点1: 插件版本

```bash
WordPress后台 → 插件 → 已安装的插件
确认显示 "版本 3.0.12"
```

### 验证点2: 短代码配置

**正确配置**：
```
[nextjs-app-entrance app_url="https://ai.ucppt.com?mode=standalone"]
```

**错误配置**：
```
[nextjs-app-entrance]  ← 缺少 app_url 参数
```

如果缺少 `app_url`，点击按钮时会弹窗提示：
> 错误：应用URL未配置。请在短代码中添加 app_url 参数。

### 验证点3: 浏览器控制台日志

按 `F12` 打开控制台，访问 `/js` 页面，应该看到：

```javascript
[Next.js SSO v3.0.12] 宣传页面脚本已加载
[Next.js SSO v3.0.12] 已找到已登录用户按钮
[Next.js SSO v3.0.12] app_url: https://ai.ucppt.com?mode=standalone
```

点击按钮后应该看到：

```javascript
[Next.js SSO v3.0.12] 在新窗口打开应用: https://ai.ucppt.com?mode=standalone&sso_token=...
```

❌ **如果看到**：
```javascript
[Next.js SSO v3.0.8] ...  ← 说明旧插件仍在运行，需要清除缓存
```

### 验证点4: 新窗口行为

**已登录用户**：
1. 访问 `https://www.ucppt.com/js`
2. 点击 "立即使用" 按钮
3. ✅ 新标签页打开应用（标签页B）
4. ✅ 宣传页面保持在原标签页（标签页A）
5. ✅ 可以随时切换回宣传页面

**未登录用户**：
1. 访问 `https://www.ucppt.com/js`
2. 点击 "立即使用" 按钮
3. ✅ 跳转到WordPress登录页（当前标签页A）
4. ✅ 登录成功后返回宣传页面（标签页A）
5. ✅ 1秒后在新标签页B打开应用
6. ✅ 宣传页面保持在标签页A

### 验证点5: Token传递

在应用标签页的控制台执行：

```javascript
console.log('Token:', localStorage.getItem('wp_jwt_token'));
console.log('User:', localStorage.getItem('wp_jwt_user'));
```

**预期输出**：
```javascript
Token: eyJ0eXAiOiJKV1QiLCJhbGc...
User: {"user_id":1,"username":"admin",...}
```

---

## 🐛 常见问题排查

### 问题1: 点击按钮无反应

**检查1: 浏览器控制台是否有JavaScript错误**
```bash
F12 → Console 标签 → 查看红色错误
```

**检查2: 插件版本是否为 v3.0.12**
```bash
WordPress后台 → 插件 → 查看版本号
```

**检查3: 短代码是否配置正确**
```bash
WordPress后台 → 页面 → 编辑 "js" 页面
确认包含: [nextjs-app-entrance app_url="https://ai.ucppt.com?mode=standalone"]
```

**解决方法**：
1. 清除WordPress缓存
2. 清除浏览器缓存（Ctrl + Shift + R）
3. 使用无痕模式测试

---

### 问题2: 弹窗提示 "应用URL未配置"

**原因**：短代码缺少 `app_url` 参数

**解决方法**：
```bash
WordPress后台 → 页面 → 编辑 "js" 页面
修改短代码为：
[nextjs-app-entrance app_url="https://ai.ucppt.com?mode=standalone"]
点击 "更新"
清除缓存并刷新页面
```

---

### 问题3: 弹窗提示 "弹窗被拦截"

**原因**：浏览器弹窗拦截器阻止了 `window.open()`

**解决方法（Chrome）**：
```bash
1. 地址栏右侧会显示弹窗被拦截的图标
2. 点击图标 → 选择 "始终允许 www.ucppt.com 的弹出式窗口"
3. 刷新页面后重试
```

**解决方法（Firefox）**：
```bash
设置 → 隐私与安全 → 权限 → 弹出窗口
点击 "例外..." → 添加：https://www.ucppt.com → 选择 "允许"
```

**解决方法（Safari）**：
```bash
偏好设置 → 网站 → 弹出式窗口
对于 www.ucppt.com，选择 "允许"
```

---

### 问题4: 控制台显示 v3.0.8 而不是 v3.0.12

**原因**：旧插件仍在缓存中运行

**解决方法**：
```bash
# 步骤1: 确认插件版本
WordPress后台 → 插件 → 已安装的插件
确认显示 "版本 3.0.12"

# 步骤2: 清除所有缓存
WordPress后台 → 设置 → WP Super Cache → 删除缓存

# 步骤3: 清除浏览器缓存
Ctrl + Shift + Delete → 选择 "缓存的图像和文件" → 清除数据

# 步骤4: 清除服务器缓存（如适用）
如果使用 Nginx/Apache 缓存或 CDN，需要清除服务器端缓存

# 步骤5: 强制刷新
Ctrl + Shift + R（Windows/Linux）
Cmd + Shift + R（Mac）

# 步骤6: 使用无痕模式测试
Ctrl + Shift + N（Chrome）
Ctrl + Shift + P（Firefox）
```

---

### 问题5: 新窗口打开但没有Token

**检查1: 控制台查看Token传递日志**
```javascript
[Next.js SSO v3.0.12] 在新窗口打开应用: https://ai.ucppt.com?mode=standalone&sso_token=...
```

**检查2: 应用是否正确接收Token**
```javascript
// 在应用标签页控制台执行
console.log('URL参数:', window.location.href);
console.log('Token:', localStorage.getItem('wp_jwt_token'));
```

**可能原因**：
1. Token生成失败（WordPress JWT配置错误）
2. Next.js应用未正确处理URL参数中的Token
3. Next.js应用的Token接收逻辑有问题

**解决方法**：
```bash
# 检查WordPress JWT配置
WordPress后台 → 设置 → Next.js SSO v3 → 查看密钥配置
确认 PYTHON_JWT_SECRET 已在 wp-config.php 中定义

# 测试REST API端点
访问: https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token
应该返回包含 token 的JSON响应

# 检查Next.js应用
确认应用有处理 sso_token 参数的逻辑
确认Token保存到 localStorage 的代码正常运行
```

---

## 📖 短代码参数完整说明

### 基础用法

```
[nextjs-app-entrance app_url="https://ai.ucppt.com?mode=standalone"]
```

### 完整自定义

```
[nextjs-app-entrance
  app_url="https://ai.ucppt.com?mode=standalone"
  title="AI 设计高参"
  subtitle="极致概念 · 智能设计助手"
  description="基于多智能体协作的专业设计分析系统，为您的设计项目提供全方位的专家级建议。"
  button_text="立即使用"
  features="多专家协作分析|智能需求理解|专业设计建议|支持多模态输入"]
```

### 参数说明

| 参数 | 默认值 | 必需 | 说明 |
|-----|--------|------|------|
| `app_url` | `http://localhost:3000?mode=standalone` | ⚠️ 是 | 应用URL，生产环境必须修改 |
| `title` | `AI 设计高参` | 否 | 主标题 |
| `subtitle` | `极致概念 · 智能设计助手` | 否 | 副标题 |
| `description` | `基于多智能体协作...` | 否 | 应用描述 |
| `button_text` | `立即使用` | 否 | 按钮文字 |
| `features` | `多专家协作分析\|...` | 否 | 特性列表（用 `\|` 分隔） |

**重要提示**：
- ⚠️ `app_url` 是唯一必需参数
- ⚠️ 生产环境必须修改 `app_url`
- ⚠️ 不配置 `app_url` 会弹窗提示错误

---

## 🔐 安全特性

### 1. window.open 安全参数

```javascript
window.open(targetUrl, '_blank', 'noopener,noreferrer');
```

**安全优势**：
- `noopener`: 防止新页面通过 `window.opener` 访问原页面（防止 Tabnabbing 攻击）
- `noreferrer`: 防止新页面获取 referrer 信息（隐私保护）

### 2. Token安全传递

- Token在URL参数中传递（暴露时间 < 1秒）
- Next.js应用接收后立即保存到localStorage
- URL中的Token自动清除
- Token有效期：7天

### 3. JWT密钥管理

- 密钥存储在 `wp-config.php` 中（不在代码中硬编码）
- 使用 `PYTHON_JWT_SECRET` 常量
- HS256算法签名
- 与Python后端密钥一致

---

## 📚 相关文档

### v3.0.12 文档
- 本文档（快速部署指南）

### v3.0.11 文档
- [WORDPRESS_V3.0.11_NEW_WINDOW_FIX.md](WORDPRESS_V3.0.11_NEW_WINDOW_FIX.md) - 新窗口打开功能说明
- [WORDPRESS_V3.0.11_QUICK_UPDATE.md](WORDPRESS_V3.0.11_QUICK_UPDATE.md) - 快速更新指南

### v3.0.10 文档
- [WORDPRESS_V3.0.10_README.md](WORDPRESS_V3.0.10_README.md) - 功能总览
- [WORDPRESS_ENTRANCE_PAGE_GUIDE_V3.0.10.md](WORDPRESS_ENTRANCE_PAGE_GUIDE_V3.0.10.md) - 完整部署指南
- [WORDPRESS_ENTRANCE_PAGE_TEST_CHECKLIST_V3.0.10.md](WORDPRESS_ENTRANCE_PAGE_TEST_CHECKLIST_V3.0.10.md) - 测试清单

### 调试文档
- [DEBUG_ENTRANCE_PAGE.md](DEBUG_ENTRANCE_PAGE.md) - 宣传页面问题诊断指南

---

## ✅ 部署验收清单

### 基础验收
- [ ] WordPress插件版本显示为 v3.0.12
- [ ] 插件描述包含："简化版：仅保留宣传页面入口"
- [ ] `/js` 页面可以正常访问
- [ ] 页面显示标题、描述、按钮、特性卡片
- [ ] 短代码包含 `app_url` 参数

### 已登录流程验收
- [ ] 显示 "✓ 您已登录为 XXX"
- [ ] 点击按钮后在新窗口打开应用
- [ ] 宣传页面保持在原标签页
- [ ] 应用显示已登录状态
- [ ] localStorage包含 `wp_jwt_token`
- [ ] localStorage包含 `wp_jwt_user`

### 未登录流程验收
- [ ] 显示 "请先登录以使用应用"
- [ ] 点击按钮跳转到WordPress登录页
- [ ] 登录成功后返回宣传页面
- [ ] 1秒后在新窗口打开应用
- [ ] 宣传页面保持在原标签页
- [ ] 应用显示已登录状态

### 控制台日志验收
- [ ] 显示 `[Next.js SSO v3.0.12]` 日志前缀
- [ ] 显示 "宣传页面脚本已加载"
- [ ] 显示 "在新窗口打开应用"
- [ ] 无JavaScript错误

### 错误处理验收
- [ ] 缺少 `app_url` 时弹窗提示
- [ ] 浏览器拦截弹窗时有提示
- [ ] 所有错误都有用户友好的提示

---

## 🎉 总结

### v3.0.12 核心改进

**架构简化**：
- ✅ 移除iframe嵌入模式（架构简化）
- ✅ 仅保留宣传页面入口模式（单一入口）
- ✅ 配置更清晰，维护更容易

**技术优化**：
- ✅ 按钮从 `<a>` 改为 `<button>`（更可靠）
- ✅ 详细的控制台日志（便于调试）
- ✅ 配置验证和错误提示（用户友好）
- ✅ 弹窗拦截检测（更好的用户体验）

**用户体验提升**：
- ✅ 新窗口打开应用（宣传页面保持）
- ✅ 错误提示清晰（配置错误、弹窗拦截）
- ✅ 智能登录跳转（已登录/未登录自动识别）

---

## 📞 技术支持

**文档索引**：
- 快速部署：本文档
- 调试指南：[DEBUG_ENTRANCE_PAGE.md](DEBUG_ENTRANCE_PAGE.md)
- 历史版本：查看 `WORDPRESS_V3.0.*` 系列文档

**问题反馈**：
1. 查看本文档的"常见问题排查"章节
2. 检查浏览器控制台日志（F12）
3. 确认插件版本为 v3.0.12
4. 联系技术支持团队

---

**部署完成！** 🎊

现在您的WordPress网站使用简化的单一入口架构，配置更清晰，维护更容易！

**下一步**：
1. 访问 `https://www.ucppt.com/js` 测试功能
2. 如有问题，参考"常见问题排查"章节
3. 删除旧的 `/nextjs` 页面（如果存在）
