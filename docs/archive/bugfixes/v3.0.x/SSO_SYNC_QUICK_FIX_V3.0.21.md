# ⚡ SSO同步问题快速修复 (v3.0.21)

**日期**: 2025-12-17
**版本**: v3.0.21
**状态**: ✅ 修复完成

---

## 🔴 问题根因

**用户报告**: WordPress用户切换后，NextJS应用显示的用户信息未同步更新

**根本原因**: **Cookie跨域限制**
- WordPress在 `www.ucppt.com` 域下设置Cookie
- NextJS在 `localhost:3000` 域下运行
- 浏览器的**同源策略**阻止了Cookie共享
- 导致方案3（Cookie事件检测）**完全失效**

**技术细节**:
```
WordPress PHP: setcookie(..., 'www.ucppt.com', ...)  // 设置Cookie
NextJS JS:     document.cookie  // 在localhost:3000无法读取www.ucppt.com的Cookie
```

---

## ✅ 解决方案

### 实施方案：增强版方案2（REST API轮询）

**核心改动**:
1. **移除方案3**（Cookie轮询） - 因为跨域无法工作
2. **保留并增强方案2**（REST API轮询）
3. **增加定期轮询**（每10秒） - 确保最终一致性

**修改文件**:
- [frontend-nextjs/contexts/AuthContext.tsx](frontend-nextjs/contexts/AuthContext.tsx) (Lines 38-111)

**关键代码**:
```typescript
// 🆕 v3.0.21增强版: 方案2 - REST API轮询（主要机制）
useEffect(() => {
  const checkSSOStatus = async () => {
    // 调用WordPress REST API检查SSO事件
    const response = await fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/sync-status', {
      method: 'GET',
      credentials: 'include',
      headers: { 'Accept': 'application/json' }
    });

    if (response.ok) {
      const data = await response.json();

      // 检测到登录事件
      if (data.event === 'user_login' && data.token) {
        localStorage.setItem('wp_jwt_token', data.token);
        localStorage.setItem('wp_jwt_user', JSON.stringify(data.user));
        setUser(data.user);
      }

      // 检测到退出事件
      if (data.event === 'user_logout') {
        localStorage.removeItem('wp_jwt_token');
        localStorage.removeItem('wp_jwt_user');
        setUser(null);
      }
    }
  };

  // 1. 页面可见性变化时检测（即时响应）
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      checkSSOStatus();
    }
  });

  // 2. 定期轮询（每10秒，确保最终一致性）
  const pollInterval = setInterval(checkSSOStatus, 10000);

  // 3. 初始检测
  checkSSOStatus();
}, []);
```

---

## 📊 预期效果

| 指标 | 修改前 | 修改后 | 改进 |
|------|--------|--------|------------|
| **开发环境工作** | ❌ 跨域失效 | ✅ 完全工作 | ✅ 100%修复 |
| **实时性** | <2秒（理论） | <10秒（实际） | ⚠️ 略有降低 |
| **跨标签页同步** | ❌ 跨域限制 | ✅ REST API | ✅ 修复 |
| **可靠性** | 低 | 高 | ✅ 显著提升 |
| **服务器请求** | 0次（理论） | 6次/分钟 | ⚠️ 增加 |

---

## 🧪 测试方法

### 方法1：使用诊断工具

**文件**: [test-sso-sync-v3.0.21.html](test-sso-sync-v3.0.21.html)

**步骤**:
1. 在浏览器中打开 `test-sso-sync-v3.0.21.html`
2. 按顺序点击4个测试按钮：
   - 步骤1: 检查事件Cookie（预期失败 - 跨域限制）
   - 步骤2: 测试REST API（预期成功）
   - 步骤3: 测试CORS（预期成功）
   - 步骤4: 实时监控（启动后在WordPress登录/切换用户）

**预期结果**:
- Cookie检测：❌ 失败（跨域，这是正常的）
- REST API：✅ 成功（返回登录状态和事件）
- CORS：✅ 成功（允许跨域）
- 实时监控：✅ 在WordPress登录后2秒内检测到事件

---

### 方法2：手动测试

**步骤**:
1. 启动NextJS开发服务器：`cd frontend-nextjs && npm run dev`
2. 打开浏览器：`http://localhost:3000`
3. 打开浏览器开发者工具（F12）→ Console
4. 在WordPress后台（`https://www.ucppt.com/wp-admin`）登录或切换用户
5. 切换回NextJS标签页（触发 `visibilitychange`）
6. 观察控制台日志

**预期日志**:
```
[AuthContext v3.0.21] 📄 页面重新可见，检测SSO状态
[AuthContext v3.0.21] ✅ 检测到WordPress登录事件（REST API）
[AuthContext v3.0.21] 新用户: {user_id: 2751, username: "testuser", ...}
```

**如果10秒后仍无日志**:
- 检查WordPress是否真的登录了（访问 `https://www.ucppt.com/wp-json/nextjs-sso/v1/sync-status` 查看响应）
- 检查WordPress插件是否激活（v3.0.21）
- 查看WordPress错误日志（`wp-content/debug.log`）

---

## 🚀 部署清单

### NextJS应用更新

- [x] 修改 `frontend-nextjs/contexts/AuthContext.tsx` (Lines 38-111)
- [x] 更新版本号 `frontend-nextjs/lib/config.ts` → VERSION: '3.0.21'
- [ ] 重启NextJS开发服务器（`npm run dev`）
- [ ] 清除浏览器缓存（Ctrl+Shift+Delete）
- [ ] 重新测试SSO同步

### WordPress插件（无需修改）

- [x] WordPress插件v3.0.21已包含所有必要功能
- [x] REST API端点 `/sync-status` 已实现
- [x] WordPress Hooks (`wp_login`, `wp_logout`) 已实现
- ℹ️ 无需重新上传插件

---

## 📁 相关文件

| 文件 | 说明 | 状态 |
|------|------|------|
| [docs/SSO_SYNC_TROUBLESHOOTING_GUIDE.md](SSO_SYNC_TROUBLESHOOTING_GUIDE.md) | 完整故障排除指南 | ✅ 已创建 |
| [test-sso-sync-v3.0.21.html](../test-sso-sync-v3.0.21.html) | 诊断工具（HTML） | ✅ 已创建 |
| [frontend-nextjs/contexts/AuthContext.tsx](../frontend-nextjs/contexts/AuthContext.tsx) | NextJS认证上下文 | ✅ 已修改 |
| [frontend-nextjs/lib/config.ts](../frontend-nextjs/lib/config.ts) | 应用配置 | ✅ 已更新 |
| [nextjs-sso-integration-v3.php](../nextjs-sso-integration-v3.php) | WordPress插件 | ℹ️ 无需修改 |
| [nextjs-sso-integration-v3.0.21.zip](../nextjs-sso-integration-v3.0.21.zip) | 插件包 | ℹ️ 已存在 |

---

## 🎯 用户操作指南

### 立即测试

1. **重启NextJS应用**:
   ```bash
   cd frontend-nextjs
   npm run dev
   ```

2. **打开诊断工具**:
   - 在浏览器中打开 `test-sso-sync-v3.0.21.html`
   - 点击"步骤4: 实时监控" → "启动监控"

3. **WordPress登录测试**:
   - 打开 `https://www.ucppt.com/wp-admin`
   - 登录用户A
   - 观察诊断工具日志（2秒内应检测到登录事件）

4. **NextJS应用测试**:
   - 打开 `http://localhost:3000`
   - 在WordPress登录后，切换到NextJS标签页
   - 观察控制台日志（应显示新用户信息）

---

## ❓ 常见问题

### Q1: 为什么移除方案3（Cookie轮询）？

**A**: 因为开发环境（`localhost:3000`）无法读取生产环境（`www.ucppt.com`）的Cookie（浏览器同源策略限制）。方案3只在**生产环境部署到同域名**（如 `ai.ucppt.com`）时才能工作。

---

### Q2: 如果我部署到 `ai.ucppt.com` 呢？

**A**: 如果部署到同一主域名（`*.ucppt.com`），方案3（Cookie轮询）就能正常工作。届时可以：
1. 修改Cookie域名为 `.ucppt.com`（nextjs-sso-integration-v3.php Line 1600）
2. 恢复方案3代码（AuthContext.tsx Lines 98-168，v3.0.21之前的版本）
3. 实时性会提升到 <2秒

---

### Q3: 为什么要定期轮询（每10秒）？

**A**: 确保最终一致性。即使用户在NextJS页面停留，不切换标签页，10秒后也能检测到WordPress的登录变化。

---

### Q4: 10秒延迟太长了怎么办？

**A**: 可以调整轮询频率：
```typescript
const pollInterval = setInterval(checkSSOStatus, 5000); // 改为5秒
```

但会增加服务器请求：
- 10秒：6次/分钟
- 5秒：12次/分钟
- 2秒：30次/分钟（过于频繁）

---

### Q5: REST API返回401怎么办？

**A**:
1. 确认在同一浏览器中登录了WordPress
2. 检查CORS配置（WordPress插件 Lines 761-783）
3. 确认 `credentials: 'include'` 已设置
4. 使用诊断工具测试CORS（`test-sso-sync-v3.0.21.html`）

---

## 🔗 延伸阅读

- [SSO_SYNC_DUAL_MECHANISM_V3.0.21.md](SSO_SYNC_DUAL_MECHANISM_V3.0.21.md) - 双机制实施完整文档（原理）
- [SSO_SYNC_TROUBLESHOOTING_GUIDE.md](SSO_SYNC_TROUBLESHOOTING_GUIDE.md) - 故障排除详细指南
- [CROSS_DOMAIN_COOKIE_FIX.md](../CROSS_DOMAIN_COOKIE_FIX.md) - 跨域Cookie问题深度分析

---

## 📞 联系支持

如果按照本指南操作后问题仍未解决：

1. 运行诊断工具，截图所有测试结果
2. 查看WordPress错误日志（`wp-content/debug.log`），搜索 `[Next.js SSO v3.0.21]`
3. 查看NextJS控制台日志，搜索 `[AuthContext v3.0.21]`
4. 提供以上信息进行进一步诊断

---

**实施者**: Claude Code
**最后更新**: 2025-12-17
**版本**: v3.0.21
**状态**: ✅ 修复完成，待用户测试
