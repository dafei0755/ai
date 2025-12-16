# v3.0.12-final 快速测试清单（3分钟）

## 📦 插件信息
- **文件**: `nextjs-sso-integration-v3.0.12-final.zip` (16,981 bytes)
- **版本**: v3.0.12 (WPCOM登录修复版)
- **关键修复**: 跳转到WPCOM用户中心登录页（`/login`），而不是WordPress登录页（`/wp-login.php`）

---

## ⚡ 快速部署（1分钟）

```bash
WordPress后台 → 插件 → 停用旧插件 → 上传新插件 → 启用
清除缓存：WP Super Cache → 删除缓存
浏览器：Ctrl + Shift + R
```

---

## ✅ 核心测试（2分钟）

### 测试1: 检查控制台日志（30秒）

```bash
访问: https://www.ucppt.com/js
按 F12 → Console标签

✅ 应该看到:
[Next.js SSO v3.0.12] 宣传页面脚本已加载
[Next.js SSO v3.0.12] 服务器端登录状态: 已登录
[Next.js SSO v3.0.12] 当前用户: xxx (ID: xxx)
[Next.js SSO v3.0.12] Token已生成: 是

❌ 如果看到 "服务器端登录状态: 未登录"：
→ WPCOM用户中心的登录Cookie未被识别
→ 需要进一步排查（见完整测试指南）
```

---

### 测试2: 已登录用户点击按钮（30秒）

```bash
确保右上角显示已登录
点击 "立即使用 →" 按钮

✅ 预期：
- 新窗口打开应用（不是跳转到登录页！）
- 应用显示已登录状态
- 宣传页面保持在原标签页

❌ 如果跳转到登录页：
→ 服务器端登录状态检测失败
→ 查看控制台日志中的登录状态
→ 查看完整测试指南的"问题诊断"章节
```

---

### 测试3: 未登录用户跳转URL（1分钟）

```bash
退出登录
访问: https://www.ucppt.com/js
点击 "立即使用 →" 按钮

✅ 预期跳转到:
https://www.ucppt.com/login?redirect_to=https://www.ucppt.com/js
（WPCOM用户中心登录页）

❌ 如果跳转到 /wp-login.php：
→ 缓存未清除，旧代码仍在运行
→ 清除所有缓存后重试
→ 使用无痕模式测试
```

---

### 测试4: 登录后自动打开应用（可选）

```bash
在WPCOM登录页输入账号密码 → 登录
观察登录成功后的行为

✅ 预期：
- 返回宣传页面（https://www.ucppt.com/js）
- 页面显示 "✓ 您已登录为 xxx"
- 1秒后自动在新窗口打开应用

❌ 如果没有返回宣传页面：
→ WPCOM可能不支持 redirect_to 参数
→ 需要检查WPCOM的重定向参数名
```

---

## 🐛 快速诊断

### 问题：显示 "未登录" 但右上角已登录

**原因**: WPCOM登录Cookie未被识别

**排查**:
```javascript
// 在宣传页面控制台执行
console.log('Cookies:', document.cookie.split('; ').filter(c => c.includes('logged') || c.includes('wordpress') || c.includes('wpcom')));

// 检查WordPress REST API
fetch('/wp-json/nextjs-sso/v1/check-login', {credentials: 'include'}).then(r => r.json()).then(console.log);
```

**下一步**: 查看 [WORDPRESS_SSO_V3.0.12_WPCOM_LOGIN_TEST.md](WORDPRESS_SSO_V3.0.12_WPCOM_LOGIN_TEST.md) 的"问题1诊断"

---

### 问题：仍然跳转到 `/wp-login.php`

**原因**: 缓存问题

**解决**:
1. 确认插件版本为 v3.0.12
2. WordPress缓存 → 删除
3. 浏览器缓存 → 清除（Ctrl + Shift + Delete）
4. 无痕模式测试（Ctrl + Shift + N）
5. 服务器端缓存 → 清除（如适用）

---

## 📄 完整测试文档

如果快速测试失败，请查看：
- [WORDPRESS_SSO_V3.0.12_WPCOM_LOGIN_TEST.md](WORDPRESS_SSO_V3.0.12_WPCOM_LOGIN_TEST.md) - 完整测试指南
- [WORDPRESS_SSO_V3.0.12_DEPLOYMENT_CHECKLIST.md](WORDPRESS_SSO_V3.0.12_DEPLOYMENT_CHECKLIST.md) - 部署验收清单

---

## ✅ 成功标志

全部通过的标志：
- [x] 控制台显示 "服务器端登录状态: 已登录"
- [x] 已登录用户点击按钮 → 新窗口打开应用（不是登录页）
- [x] 未登录用户点击按钮 → 跳转到 `/login`（不是 `/wp-login.php`）

---

**快速测试完成！** 🎊

如果所有测试通过，v3.0.12-final 已成功部署！
