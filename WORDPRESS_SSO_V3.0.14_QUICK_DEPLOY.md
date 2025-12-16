# v3.0.14 快速部署指南（Solution B）

## 📦 插件信息

- **文件**: `nextjs-sso-integration-v3.0.14.zip` (17,949 bytes)
- **版本**: v3.0.14
- **方案**: Solution B - REST API 模式
- **关键特性**: 完美兼容 WPCOM Member Pro

---

## ⚡ 1分钟部署

```bash
1. WordPress后台 → 插件 → 停用旧插件
2. 插件 → 上传插件 → 选择 nextjs-sso-integration-v3.0.14.zip → 安装 → 启用
3. 设置 → WP Super Cache → 删除缓存
4. 浏览器：Ctrl + Shift + R（强制刷新）
5. 访问：https://www.ucppt.com/js → 测试
```

---

## ✅ 核心测试（30秒）

### 测试：已登录用户点击按钮

**前提**: 已通过 WPCOM 用户中心登录（右上角显示用户名）

**步骤**:
```
访问: https://www.ucppt.com/js
按 F12 → Console 标签
点击 "立即使用 →" 按钮
```

**成功标志**:
```javascript
[Next.js SSO v3.0.14] REST API 响应状态: 200
[Next.js SSO v3.0.14] ✅ Token 获取成功
[Next.js SSO v3.0.14] ✅ 应用成功在新窗口打开
```

**关键验收**:
- [x] **不跳转到登录页**（关键！）
- [x] 新窗口打开应用
- [x] 应用显示已登录状态
- [x] 宣传页面保持在原标签页

---

## 🎯 与 v3.0.12 的关键区别

| 项目 | v3.0.12 | v3.0.14 (Solution B) |
|------|---------|----------------------|
| **登录检测** | 服务器端 `wp_get_current_user()` | 客户端 REST API |
| **按钮渲染** | 两种按钮（已登录/未登录） | 统一按钮 |
| **Token 生成** | 页面加载时生成 | 点击按钮时生成 |
| **WPCOM 兼容** | ❌ Cookie 不兼容 | ✅ REST API 兼容 |
| **核心优势** | - | 绕过 Cookie 解析问题 |

---

## 🐛 快速诊断

### 问题：点击按钮后仍跳转到 `/wp-login.php`

**原因**: 缓存未清除

**解决**:
```bash
1. 确认插件版本为 v3.0.14（插件列表）
2. WordPress缓存 → 删除
3. 浏览器缓存 → 清除（Ctrl + Shift + Delete）
4. 无痕模式测试（Ctrl + Shift + N）
```

---

### 问题：REST API 返回 401 但右上角已登录

**排查**:
```javascript
// 在控制台执行
fetch('/wp-json/nextjs-sso/v1/get-token', {
    credentials: 'include'
}).then(r => {
    console.log('Status:', r.status);
    return r.json();
}).then(console.log);
```

**如果返回 401**:
- WPCOM Member Pro 可能未正确集成 WordPress 认证
- 检查 WPCOM 插件设置
- 联系 WPCOM 插件作者

---

### 问题：REST API 返回 500 错误

**排查**:
1. 检查 WordPress Debug 日志：`/wp-content/debug.log`
2. 检查 `wp-config.php` 中的 `PYTHON_JWT_SECRET` 是否配置
3. 禁用其他插件测试

---

## 📄 完整文档

如果部署失败，请查看：
- [WORDPRESS_SSO_V3.0.14_SOLUTION_B.md](WORDPRESS_SSO_V3.0.14_SOLUTION_B.md) - 完整实施说明
- [NEXTJS_SSO_TOKEN_RECEIVE_FIX.md](NEXTJS_SSO_TOKEN_RECEIVE_FIX.md) - Next.js Token 接收修复

---

## 🎉 成功标志

**v3.0.14 部署成功的标志**:

✅ 控制台显示版本号 `v3.0.14`
✅ 控制台显示 "REST API模式"
✅ 已登录用户点击按钮 → REST API 返回 200 → 新窗口打开应用
✅ 未登录用户点击按钮 → REST API 返回 401 → 跳转到 `/login`
✅ **关键**：不再跳转到 `/wp-login.php`
✅ **关键**：WPCOM 登录状态被正确识别

---

**v3.0.14 Solution B - 快速部署完成！** 🚀

**最后更新**: 2025-12-16
**插件版本**: v3.0.14
**部署时间**: < 1 分钟
**测试时间**: < 30 秒
