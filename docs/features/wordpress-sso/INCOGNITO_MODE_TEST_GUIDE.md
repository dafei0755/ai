# 🕵️ 无痕模式测试指南 - 跨域Cookie修复

**测试目的**: 验证在无痕模式下，从 WordPress 登录到应用的完整流程

**测试时间**: 2025-12-16

---

## ⚠️ 无痕模式特性说明

### 什么是无痕模式

**浏览器无痕/隐私模式特点**:
- ❌ 不保存任何 Cookie
- ❌ 不保存 localStorage
- ❌ 不保存浏览历史
- ❌ 关闭窗口后所有数据清空
- ✅ 每次打开都是全新会话

**对我们应用的影响**:
1. 无法保存 WordPress 登录状态（Cookie会在关闭后清除）
2. 无法缓存 JWT Token（localStorage会清空）
3. 每次都必须重新登录

---

## ✅ 正确的测试步骤

### 完整测试流程（5分钟）

#### 步骤1: 打开无痕窗口
```
Chrome: Ctrl + Shift + N
Firefox: Ctrl + Shift + P
Edge: Ctrl + Shift + N
```

#### 步骤2: 访问 WordPress 宣传页面
```
访问: https://www.ucppt.com/js
```

**此时应该看到**:
- ✅ 页面正常加载
- ❌ **不应该**看到"智能设计分析工具"卡片（因为未登录）
- ✅ 应该看到"立即登录"或登录表单

#### 步骤3: 登录 WordPress
```
1. 点击页面上的"登录"按钮
2. 输入 WordPress 账号密码
3. 点击登录
```

**登录成功后**:
- ✅ WordPress 设置 Cookie
- ✅ WPCOM 隐藏区块变为可见
- ✅ 看到"智能设计分析工具"卡片
- ✅ 看到"🚀 立即开始分析"按钮

#### 步骤4: 验证 Token 注入
```
1. 不要急着点击按钮
2. 右键点击"🚀 立即开始分析"按钮
3. 选择"复制链接地址"
4. 粘贴到记事本查看
```

**应该看到**:
```
http://localhost:3000?sso_token=eyJ0eXAiOiJKV1QiLCJhbGc...
```

**如果链接中没有 `sso_token`**:
- ❌ JavaScript 没有成功执行
- ❌ REST API 调用失败
- ❌ WPCOM 隐藏区块中的代码有问题

#### 步骤5: 点击按钮跳转
```
1. 点击"🚀 立即开始分析"按钮
2. 等待跳转到应用
```

**预期结果**:
```
✅ 跳转到: http://localhost:3000?sso_token=...
✅ 应用检测到 URL 中的 Token
✅ 自动验证 Token
✅ 保存到 localStorage
✅ 直接进入 /analysis 页面
✅ 不显示"请先登录以使用应用"
```

#### 步骤6: 检查浏览器控制台
```
F12 → Console 标签
```

**应该看到的日志**:
```javascript
// WordPress 页面（ucppt.com/js）
✅ Token已生成，应用链接已更新

// 应用页面（localhost:3000）
[AuthContext] ✅ 从 URL 参数获取到 Token
[AuthContext] Token 验证状态: 200
[AuthContext] ✅ SSO 登录成功
```

---

## ❌ 错误场景分析

### 场景A: 未登录就点击按钮

**操作**:
```
无痕模式 → 访问 ucppt.com/js → 直接点击"立即开始分析"（未登录）
```

**问题**:
- WPCOM 隐藏区块在未登录时应该不可见
- 如果看到了按钮，说明页面有缓存或配置错误

**解决**:
1. 检查 WPCOM 隐藏区块设置
2. 确认"可见条件"设置为"仅登录用户"
3. 清除 WordPress 缓存

---

### 场景B: 登录后链接没有 Token

**症状**:
```
登录成功 → 右键查看链接 → 只有 http://localhost:3000（没有 Token）
```

**原因**:
- JavaScript 代码未执行
- REST API 调用失败
- CORS 问题

**调试步骤**:

1. **打开浏览器控制台**（F12）
2. **重新刷新页面**
3. **查找以下信息**:

```javascript
// 成功情况
✅ Token已生成，应用链接已更新

// 失败情况
❌ 获取Token失败: 401
❌ Token获取异常: Failed to fetch
```

**解决方法**:

**问题1: 401 错误**
```
原因: REST API 权限问题
解决: 确认 WordPress 插件版本为 v3.0.17+
     确认 permission_callback 设置为 __return_true
```

**问题2: CORS 错误**
```
原因: 跨域请求被阻止
解决: 在 WordPress 插件中添加 CORS 头
     或者使用同域名部署
```

**问题3: JavaScript 未执行**
```
原因: WPCOM 隐藏区块中的代码有语法错误
解决: 检查代码是否完整复制
     检查是否有多余的 HTML 标签
```

---

### 场景C: 跳转后仍显示登录界面

**症状**:
```
点击按钮 → 跳转到 localhost:3000 → 仍显示"请先登录以使用应用"
```

**调试步骤**:

1. **检查 URL 是否包含 Token**
```
查看地址栏: http://localhost:3000?sso_token=...
```

如果没有 Token → 返回场景B

2. **检查浏览器控制台**
```javascript
// 查找 AuthContext 日志
[AuthContext] ✅ 从 URL 参数获取到 Token  // 应该有这条
[AuthContext] Token 验证状态: 200       // 应该是 200
```

如果显示 401 → Token 无效或已过期

3. **检查 Network 面板**
```
F12 → Network 标签 → 查找 /api/auth/verify 请求
```

查看响应状态码和内容

---

## 🔍 详细调试指南

### 调试工具1: 浏览器控制台

**打开方式**: F12 → Console 标签

**关键日志**:

| 日志内容 | 位置 | 含义 |
|---------|------|------|
| `✅ Token已生成，应用链接已更新` | ucppt.com/js | JavaScript 成功获取 Token |
| `❌ 获取Token失败: 401` | ucppt.com/js | 未登录或 REST API 权限问题 |
| `[AuthContext] ✅ 从 URL 参数获取到 Token` | localhost:3000 | 检测到 URL Token |
| `[AuthContext] Token 验证状态: 200` | localhost:3000 | Token 验证成功 |
| `[AuthContext] ✅ SSO 登录成功` | localhost:3000 | 登录成功 |

---

### 调试工具2: 网络面板

**打开方式**: F12 → Network 标签

**关键请求**:

1. **在 ucppt.com/js 页面**:
```
GET https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token
状态: 200 (成功) 或 401 (未登录)
响应: {"success": true, "token": "eyJ0eXAi..."}
```

2. **在 localhost:3000 页面**:
```
POST http://127.0.0.1:8000/api/auth/verify
状态: 200 (成功) 或 401 (Token无效)
请求头: Authorization: Bearer eyJ0eXAi...
```

---

### 调试工具3: 元素检查

**打开方式**: F12 → Elements 标签

**检查链接元素**:
```html
<a href="http://localhost:3000?sso_token=eyJ0eXAi..." id="app-entry-link">
  🚀 立即开始分析
</a>
```

**如果 href 中没有 Token**:
- JavaScript 没有成功更新链接
- 检查元素 ID 是否匹配（应为 `app-entry-link`）

---

## ✅ 成功标志清单

测试通过需要满足所有以下条件:

### WordPress 页面（ucppt.com/js）
- [ ] 登录成功后看到"智能设计分析工具"卡片
- [ ] 浏览器控制台显示：`✅ Token已生成，应用链接已更新`
- [ ] 右键查看链接包含 `?sso_token=...`

### 应用页面（localhost:3000）
- [ ] URL 包含 `?sso_token=...` 参数
- [ ] 不显示"请先登录以使用应用"界面
- [ ] 直接进入 `/analysis` 页面
- [ ] 控制台显示：`[AuthContext] ✅ SSO 登录成功`
- [ ] 无 401/400 错误

---

## 🚀 快速故障排除

### 1分钟快速检查

```bash
# 检查清单（按顺序）
1. ✓ 是否在无痕模式下登录了 WordPress？
   → 未登录 → 先登录

2. ✓ 是否看到"智能设计分析工具"卡片？
   → 未看到 → WPCOM 隐藏区块配置错误

3. ✓ 右键查看链接是否包含 Token？
   → 不包含 → JavaScript 未执行或 REST API 失败

4. ✓ 浏览器控制台是否有错误？
   → 有错误 → 根据错误信息修复

5. ✓ 点击后是否直接进入应用？
   → 未进入 → Token 验证失败
```

---

## 📊 测试场景对比

### 场景1: 普通模式（有缓存）
```
特点: localStorage 保存 Token，可以自动登录
流程: 访问 localhost:3000 → 检测 Token → 自动登录 ✅
```

### 场景2: 无痕模式（无缓存）
```
特点: 无 localStorage，无 Cookie（关闭后）
流程: 必须从 ucppt.com/js 登录 → 获取 Token → 跳转应用 ✅
```

### 场景3: Token 过期
```
特点: localStorage 有 Token 但已过期
流程: 尝试验证 → 401 → 清除 Token → 显示登录界面 ✅
```

---

## 💡 最佳实践

### 开发环境测试

**每次修改后测试**:
```bash
1. 打开无痕窗口（确保干净环境）
2. 登录 WordPress（ucppt.com/js）
3. 检查链接是否包含 Token
4. 点击跳转验证完整流程
5. 关闭无痕窗口（清除所有数据）
```

### 生产环境测试

**部署后验证**:
```bash
1. 清除浏览器缓存和 Cookie
2. 访问生产环境宣传页面
3. 登录 WordPress
4. 验证完整流程
5. 测试 Token 过期场景（等待24小时）
```

---

## 📞 问题报告模板

如果测试失败，请提供以下信息:

### 1. 环境信息
```
浏览器: Chrome 120 / Firefox 121 / Edge 120
模式: 无痕模式 / 普通模式
操作系统: Windows 11 / macOS / Linux
```

### 2. 操作步骤
```
1. 访问 ucppt.com/js
2. 登录 WordPress（账号: xxx）
3. 看到"智能设计分析工具"卡片
4. 右键查看链接: [复制的链接]
5. 点击按钮跳转
6. 当前 URL: [当前地址]
7. 当前页面状态: [描述]
```

### 3. 控制台日志
```javascript
// WordPress 页面控制台（ucppt.com/js）
[粘贴所有日志]

// 应用页面控制台（localhost:3000）
[粘贴所有日志]
```

### 4. 网络请求
```
F12 → Network 标签 → 截图
显示 /get-token 和 /verify 请求的状态码和响应
```

### 5. 截图
- WordPress 登录后的页面
- 应用跳转后的页面
- 浏览器控制台
- Network 面板

---

## ✅ 总结

### 无痕模式测试要点

1. **必须先登录 WordPress** ⚠️
2. **验证链接包含 Token**
3. **检查浏览器控制台日志**
4. **确认完整流程通过**

### 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| 看不到隐藏区块 | 未登录 | 先登录 WordPress |
| 链接没有 Token | JavaScript 未执行 | 检查代码和 REST API |
| 跳转后显示登录界面 | Token 无效 | 检查 Token 验证逻辑 |
| 401 错误 | 权限问题 | 检查 WordPress 插件 |

---

**创建时间**: 2025-12-16
**适用版本**: v3.0.20
**测试时长**: 5分钟
**难度**: ⭐⭐ 简单（需要先登录）
