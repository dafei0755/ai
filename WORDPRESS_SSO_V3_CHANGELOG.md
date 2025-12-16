# WordPress SSO Integration v3 - 版本变更日志

## v3.0.12 (2025-12-16) - 架构简化

### ❌ 移除功能

**iframe嵌入模式已废弃**：
- 移除 `[nextjs_app]` 短代码
- 注释整个iframe嵌入功能（Lines 897-1223）
- `/nextjs` 页面不再需要
- 如有旧页面，建议删除

**为什么移除**：
- 简化架构，减少配置复杂度
- 用户反馈：iframe模式容易出现Token传递问题
- 宣传页面入口模式更直观，用户体验更好

### ✅ 保留功能

**宣传页面入口模式**：
- `[nextjs-app-entrance]` 短代码正常工作
- 智能登录跳转（已登录/未登录自动识别）
- 新窗口打开应用（宣传页面保持）

### 🔧 技术改进

**1. 按钮实现优化** (Lines 1355-1381):
```php
// Before:
<a href="#" class="entrance-button" id="entrance-button-logged-in">

// After:
<button type="button" class="entrance-button" id="entrance-button-logged-in"
        style="border: none; cursor: pointer;">
```

**优势**：
- 无需 `e.preventDefault()` 阻止默认行为
- 更语义化的HTML标签
- 避免可能的锚点跳转问题

**2. JavaScript错误处理增强** (Lines 1399-1485):

```javascript
// 配置验证
if (!appUrl) {
    console.error('[Next.js SSO v3.0.12] 错误：app_url 未配置');
    alert('错误：应用URL未配置。请在短代码中添加 app_url 参数。');
    return;
}

// 弹窗拦截检测
const newWindow = window.open(targetUrl, '_blank', 'noopener,noreferrer');
if (!newWindow) {
    console.error('[Next.js SSO v3.0.12] 新窗口被浏览器拦截');
    alert('弹窗被拦截！请允许此网站的弹窗，然后重试。');
}
```

**优势**：
- 配置错误时立即提示用户
- 浏览器拦截弹窗时有友好提示
- 所有关键步骤都有控制台日志

**3. 详细的调试日志**:

```javascript
console.log('[Next.js SSO v3.0.12] 宣传页面脚本已加载');
console.log('[Next.js SSO v3.0.12] 已找到已登录用户按钮');
console.log('[Next.js SSO v3.0.12] app_url:', loggedInButton.dataset.appUrl);
console.log('[Next.js SSO v3.0.12] 在新窗口打开应用:', targetUrl);
```

**优势**：
- 便于调试和问题排查
- 版本号清晰（`v3.0.12` 标识）
- 每个关键步骤都有日志输出

### 📦 部署说明

**升级路径**：
- v3.0.8 → v3.0.12: 需要删除旧的 `/nextjs` iframe页面
- v3.0.9 → v3.0.12: 需要删除旧的 `/nextjs` iframe页面
- v3.0.10 → v3.0.12: 仅需更新插件，无需其他修改
- v3.0.11 → v3.0.12: 仅需更新插件，无需其他修改

**配置要求**：
```
[nextjs-app-entrance app_url="https://ai.ucppt.com?mode=standalone"]
```
⚠️ `app_url` 参数现在是必需的（会验证并提示）

**文档**：
- 快速开始: [WORDPRESS_SSO_V3.0.12_QUICK_START.md](WORDPRESS_SSO_V3.0.12_QUICK_START.md)
- 完整指南: [WORDPRESS_SSO_V3.0.12_SIMPLIFIED_VERSION.md](WORDPRESS_SSO_V3.0.12_SIMPLIFIED_VERSION.md)

---

## v3.0.11 (2025-12-15) - 新窗口打开

### ✅ 新增功能

**新窗口打开应用**：
- 宣传页面始终保留
- 点击按钮在新标签页打开应用
- 已登录用户：直接在新窗口打开（带Token）
- 未登录用户：登录后在新窗口打开

### 🔧 技术修改

**JavaScript跳转逻辑** (v3.0.10 → v3.0.11):

```javascript
// v3.0.10: 当前标签页跳转
window.location.href = targetUrl;

// v3.0.11: 新窗口打开
window.open(targetUrl, '_blank', 'noopener,noreferrer');
```

**安全参数**：
- `noopener`: 防止 Tabnabbing 攻击
- `noreferrer`: 防止 referrer 信息泄露

**文档**：
- [WORDPRESS_V3.0.11_NEW_WINDOW_FIX.md](WORDPRESS_V3.0.11_NEW_WINDOW_FIX.md)
- [WORDPRESS_V3.0.11_QUICK_UPDATE.md](WORDPRESS_V3.0.11_QUICK_UPDATE.md)

---

## v3.0.10 (2025-12-15) - 宣传页面入口

### ✅ 新增功能

**宣传页面入口模式**：
- 新增 `[nextjs-app-entrance]` 短代码
- 精美的宣传页面UI设计
- 智能登录跳转（已登录/未登录自动识别）
- 完全可自定义（标题、描述、按钮、特性）

### 🎨 用户体验

**智能登录流程**：
- 已登录用户：点击按钮 → 直接进入应用（带Token）
- 未登录用户：点击按钮 → WordPress登录 → 自动跳转到应用

**Token传递**：
- Token在URL参数中传递（暴露时间 < 1秒）
- Next.js应用接收后保存到localStorage
- URL中的Token自动清除

**文档**：
- [WORDPRESS_V3.0.10_README.md](WORDPRESS_V3.0.10_README.md)
- [WORDPRESS_ENTRANCE_PAGE_GUIDE_V3.0.10.md](WORDPRESS_ENTRANCE_PAGE_GUIDE_V3.0.10.md)
- [WORDPRESS_ENTRANCE_PAGE_TEST_CHECKLIST_V3.0.10.md](WORDPRESS_ENTRANCE_PAGE_TEST_CHECKLIST_V3.0.10.md)

---

## v3.0.9 (2025-12-15) - 登录状态检测修复

### 🐛 关键修复

**登录状态误判问题**：
- 使用专用REST API端点 `/wp-json/nextjs-sso/v1/check-login`
- 从字符串匹配改为API调用
- 提升检测可靠性和准确性

**防止误清除Token**：
- 已登录用户不会被误判为未登录
- Token不会被意外清除
- 减少5秒检测频率（从10秒）

**文档**：
- [LOGIN_STATE_MISDETECTION_FIX_V3.0.9.md](LOGIN_STATE_MISDETECTION_FIX_V3.0.9.md)

---

## v3.0.8 (2025-12-15) - 登录同步优化

### ✅ 新增功能

**自动登录同步**：
- WordPress登录后自动同步到Next.js
- 5秒检测 + 页面刷新机制
- 未登录时隐藏Next.js应用界面

**统一登录入口**：
- 使用WordPress右上角登录/退出按钮
- 单一入口原则，避免混淆

**文档**：
- [WORDPRESS_SSO_V3_FINAL_FIX_SUMMARY.md](docs/wordpress/WORDPRESS_SSO_V3_FINAL_FIX_SUMMARY.md)

---

## v3.0.7 (2025-12-15) - 退出登录同步

### ✅ 新增功能

**退出登录自动通知**：
- WordPress退出时自动通知Next.js清除Token
- 双重检测：即时（退出链接点击）+ 轮询（10秒状态检查）
- postMessage安全通信

**覆盖所有退出场景**：
- 主动退出
- Session过期
- 跨标签页同步

---

## v3.0.6 (2025-12-15) - Token缓存支持

### 🔧 关键修复

**始终渲染iframe**：
- 不再检测WordPress登录状态
- 让Next.js应用自己处理登录逻辑
- 支持Token缓存（localStorage）

**用户体验提升**：
- 无需在WordPress层面保持登录
- Token缓存可跨会话使用
- 解决WordPress未登录时无法使用Token缓存的问题

---

## v3.0.5 (2025-12-15) - postMessage通信

### 🔧 关键修复

**登录状态同步**：
- 使用postMessage通信（跨域安全）
- WordPress父页面实时向iframe传递Token
- iframe加载时 + 每30秒同步

**解决问题**：
- 刷新页面后URL参数丢失
- 不受Cookie跨域限制影响

---

## v3.0.4 (2025-12-14) - 安全优化

### 🔒 安全修复

**密钥安全**：
- 从 wp-config.php 读取 `PYTHON_JWT_SECRET`
- 不再硬编码密钥
- 生产环境不输出敏感日志

---

## v3.0.3 (2025-12-14) - JWT密钥配置

### 🔧 关键修复

**JWT密钥配置**：
- 使用 Simple JWT Login 的密钥
- 与 WPCOM Custom API 插件配合
- 支持从WordPress meta字段读取会员等级

---

## v3.0.1 (2025-12-13) - 跨域Cookie修复

### 🐛 关键修复

**跨域iframe Cookie限制**：
- 解决 SameSite 策略问题
- WordPress插件直接在iframe URL中传递JWT Token
- Next.js优先从URL参数读取Token

**安全优化**：
- 读取Token后自动清除URL参数
- 向后兼容REST API方式

---

## v3.0 (2025-12-13) - 全新版本

### 🎉 重大更新

**彻底解决缓存问题**：
- 新插件标识符（`nextjs_sso_v3_*`）
- 强制刷新机制
- OPcache自动清除

**原生登录弹窗**：
- 触发WordPress主题登录弹窗
- 多种触发方式（主题API、导航栏链接、降级方案）

**统一SSO流程**：
- 所有流程统一到 `https://www.ucppt.com/nextjs`
- iframe自动高度调整
- 完整的CORS跨域支持

---

## 版本对比总览

| 版本 | 发布日期 | 核心特性 | 架构 |
|-----|---------|---------|------|
| v3.0.12 | 2025-12-16 | 移除iframe模式，按钮优化 | 单一入口 |
| v3.0.11 | 2025-12-15 | 新窗口打开应用 | 双模式 |
| v3.0.10 | 2025-12-15 | 宣传页面入口 | 双模式 |
| v3.0.9 | 2025-12-15 | 登录状态检测修复 | 双模式 |
| v3.0.8 | 2025-12-15 | 登录同步优化 | 双模式 |
| v3.0.7 | 2025-12-15 | 退出登录同步 | 双模式 |
| v3.0.6 | 2025-12-15 | Token缓存支持 | 双模式 |
| v3.0.5 | 2025-12-15 | postMessage通信 | 双模式 |
| v3.0.4 | 2025-12-14 | 安全优化 | 双模式 |
| v3.0.3 | 2025-12-14 | JWT密钥配置 | 双模式 |
| v3.0.1 | 2025-12-13 | 跨域Cookie修复 | 双模式 |
| v3.0 | 2025-12-13 | 全新版本 | 双模式 |

**架构演进**：
- v3.0 - v3.0.11: 双模式架构（iframe + 宣传页面）
- v3.0.12: 单一入口架构（仅宣传页面）

---

## 推荐版本

### 生产环境
**推荐**: v3.0.12
- ✅ 架构最简化
- ✅ 配置最清晰
- ✅ 错误处理最完善
- ✅ 维护最容易

### 开发环境
**推荐**: v3.0.12 或 v3.0.11
- v3.0.12: 如需简化架构
- v3.0.11: 如需保留iframe模式（可降级）

### 遗留系统
如需iframe嵌入模式：
- 使用 v3.0.11 或更早版本
- 注意：iframe模式在 v3.0.12 已移除

---

## 升级建议

### 从 v3.0.8-v3.0.9 升级到 v3.0.12
1. 上传新插件
2. 删除旧的 `/nextjs` iframe页面
3. 确认 `/js` 页面使用 `[nextjs-app-entrance]` 短代码
4. 确认短代码包含 `app_url` 参数
5. 清除所有缓存

### 从 v3.0.10-v3.0.11 升级到 v3.0.12
1. 上传新插件
2. 清除缓存
3. 无需其他修改

### 从 v3.0.4-v3.0.7 升级到 v3.0.12
1. 上传新插件
2. 创建 `/js` 页面（如不存在）
3. 添加短代码：`[nextjs-app-entrance app_url="..."]`
4. 删除旧的 `/nextjs` iframe页面
5. 清除所有缓存

---

## 技术支持

**文档索引**：
- v3.0.12: [WORDPRESS_SSO_V3.0.12_QUICK_START.md](WORDPRESS_SSO_V3.0.12_QUICK_START.md)
- 调试指南: [DEBUG_ENTRANCE_PAGE.md](DEBUG_ENTRANCE_PAGE.md)
- 完整文档: 查看 `docs/wordpress/` 目录

**常见问题**：
- 点击按钮无反应 → 检查控制台错误和插件版本
- Token未传递 → 检查 `app_url` 参数配置
- 缓存问题 → 清除WordPress和浏览器缓存

---

**最后更新**: 2025-12-16
