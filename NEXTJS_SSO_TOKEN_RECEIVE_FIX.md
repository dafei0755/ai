# Next.js 应用 SSO Token 接收修复（v3.0.12 独立窗口模式）

## 🐛 问题描述

**症状**：
- 点击宣传页面的"立即使用"按钮后，应用在新窗口打开
- URL包含 `sso_token` 参数（说明WordPress端Token传递成功）
- 但应用显示"独立模式 - 请选择登录方式"（未登录状态）
- Token未被Next.js应用接收和处理

**根本原因**：
- `AuthContext.tsx` 的Token接收逻辑只在 **iframe 模式** 下工作（Line 154: `if (isInIframe)`）
- v3.0.12 改为 **独立窗口模式**，`isInIframe` 为 false
- 跳过了URL Token的处理逻辑，直接尝试验证缓存Token
- 因为没有缓存Token，应用显示未登录状态

---

## 🔧 修复内容

### 文件: `frontend-nextjs/contexts/AuthContext.tsx`

**修改位置**: Lines 107-163

**修改前**（错误的逻辑）：
```typescript
// 如果不在登录相关页面，尝试 SSO 登录
if (pathname !== '/auth/login' && ...) {
  // 🔥 检测是否在 iframe 中
  const isInIframe = window.self !== window.top;

  if (isInIframe) {
    // 只有在iframe中才处理URL Token
    const urlParams = new URLSearchParams(window.location.search);
    const urlToken = urlParams.get('sso_token');
    // ... Token处理逻辑 ...
  } else {
    // 独立窗口模式：只尝试缓存Token，忽略URL Token ❌
    const cachedToken = localStorage.getItem('wp_jwt_token');
    // ...
  }
}
```

**修改后**（正确的逻辑）：
```typescript
// 如果不在登录相关页面，尝试 SSO 登录
if (pathname !== '/auth/login' && ...) {
  // 🆕 v3.0.12: 优先检查 URL 参数中的 sso_token（支持独立窗口模式）
  const urlParams = new URLSearchParams(window.location.search);
  const urlToken = urlParams.get('sso_token');

  if (urlToken) {
    console.log('[AuthContext] ✅ 从 URL 参数获取到 Token（独立模式），正在验证...');
    try {
      // 验证 Token
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const verifyResponse = await fetch(`${API_URL}/api/auth/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${urlToken}`
        }
      });

      if (verifyResponse.ok) {
        const verifyData = await verifyResponse.json();
        console.log('[AuthContext] ✅ SSO 登录成功（独立模式），用户:', verifyData.user);

        // 保存 Token 和用户信息
        localStorage.setItem('wp_jwt_token', urlToken);
        localStorage.setItem('wp_jwt_user', JSON.stringify(verifyData.user));
        setUser(verifyData.user);
        setIsLoading(false);

        // 🔥 清除 URL 参数，避免 Token 暴露在地址栏
        urlParams.delete('sso_token');
        const newUrl = window.location.pathname + (urlParams.toString() ? '?' + urlParams.toString() : '');
        window.history.replaceState({}, '', newUrl);

        return; // SSO 成功，停止执行
      }
    } catch (error) {
      console.error('[AuthContext] ❌ Token 验证异常（独立模式）:', error);
    }
  }

  // 然后再检查是否在iframe中（向后兼容）
  const isInIframe = window.self !== window.top;
  if (isInIframe) {
    // iframe模式的Token处理...
  } else {
    // 独立窗口模式：检查缓存Token...
  }
}
```

**关键变化**：
1. **URL Token检测提前**：在检测iframe之前，先检查URL中的 `sso_token` 参数
2. **独立模式支持**：无论是否在iframe中，都会首先尝试从URL获取Token
3. **向后兼容**：保留iframe模式的特殊处理逻辑
4. **Token清除**：验证成功后立即从URL中清除Token，避免安全风险

---

## ✅ 测试步骤

### 前提条件
- WordPress插件已更新到 v3.0.12-final
- Next.js应用的 `AuthContext.tsx` 已修复
- Python后端API服务正在运行（`http://127.0.0.1:8000`）

### 测试1: 重启Next.js开发服务器

```bash
# 终止当前运行的Next.js服务（Ctrl + C）
# 然后重新启动
cd frontend-nextjs
npm run dev
```

**验证**：
- 服务器在 `http://localhost:3000` 运行
- 没有编译错误

---

### 测试2: 已登录用户完整流程

**步骤**：
1. 确保已在WordPress登录（右上角显示用户名）
2. 访问：`https://www.ucppt.com/js`
3. 按 `F12` 打开浏览器控制台
4. 点击 "立即使用 →" 按钮
5. 观察新窗口和控制台

**预期结果**：

**新窗口行为**：
- 打开应用：`localhost:3000/?mode=standalone&sso_token=...`
- 页面先显示 "加载中..."
- 然后 **显示已登录状态**（用户头像、用户名）
- **不显示** "独立模式 - 请选择登录方式"

**控制台日志**（新窗口的控制台）：
```javascript
[AuthContext] ✅ 从 URL 参数获取到 Token（独立模式），正在验证...
[AuthContext] Token 验证状态: 200
[AuthContext] ✅ SSO 登录成功（独立模式），用户: {user_id: 123, username: "xxx", ...}
```

**localStorage**（新窗口控制台执行）：
```javascript
console.log('Token:', localStorage.getItem('wp_jwt_token'));
console.log('User:', localStorage.getItem('wp_jwt_user'));
// 应该有值
```

**URL变化**：
- 初始URL: `localhost:3000/?mode=standalone&sso_token=eyJ0eXAiOiJKV1...`
- Token验证后: `localhost:3000/?mode=standalone`（Token已清除）

**验收标准**：
- [x] 应用显示已登录状态
- [x] 控制台显示 "SSO 登录成功（独立模式）"
- [x] localStorage包含Token和User
- [x] URL中的Token已自动清除

---

### 测试3: 未登录用户完整流程

**步骤**：
1. 退出WordPress登录
2. 访问：`https://www.ucppt.com/js`
3. 点击 "立即使用 →" 按钮
4. 跳转到WPCOM登录页，输入账号密码
5. 登录成功后返回宣传页面
6. 1秒后自动在新窗口打开应用
7. 观察新窗口

**预期结果**：
- 与测试2相同
- 应用显示已登录状态
- 控制台显示 "SSO 登录成功（独立模式）"

---

### 测试4: Token验证失败处理

**模拟场景**：Token无效或过期

**手动测试**：
1. 访问：`http://localhost:3000/?mode=standalone&sso_token=invalid_token`
2. 观察控制台

**预期结果**：
```javascript
[AuthContext] ✅ 从 URL 参数获取到 Token（独立模式），正在验证...
[AuthContext] Token 验证状态: 401
[AuthContext] ❌ Token 验证失败（独立模式）: {error: "..."}
```

- 应用显示未登录状态
- 显示 "独立模式 - 请选择登录方式"
- 这是正常行为（Token无效）

---

### 测试5: 缓存Token验证（可选）

**场景**：关闭应用后重新打开，使用缓存的Token

**步骤**：
1. 完成测试2（应用已登录）
2. 关闭应用标签页
3. 重新访问：`http://localhost:3000/?mode=standalone`（不带Token）
4. 观察控制台

**预期结果**：
```javascript
[AuthContext] 发现缓存的 Token，尝试验证...
[AuthContext] ✅ 缓存 Token 有效，用户: {user_id: 123, ...}
```

- 应用显示已登录状态（使用缓存Token）
- 无需重新登录

---

## 🐛 故障排查

### 问题1: 控制台显示 "Token 验证状态: 500" 或其他错误

**原因**：Python后端API未运行或无法连接

**检查**：
```bash
# 确认后端服务运行状态
curl http://127.0.0.1:8000/health
# 应该返回: {"status": "healthy"}
```

**解决**：
```bash
# 启动Python后端
cd d:\11-20\langgraph-design
python -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000
```

---

### 问题2: 控制台显示 "Token 验证状态: 401"

**原因**：Token签名不匹配

**检查**：
1. WordPress插件的 `PYTHON_JWT_SECRET`
2. Python后端的 `PYTHON_JWT_SECRET`
3. 两者必须完全一致

**解决**：
```bash
# 检查wp-config.php
define('PYTHON_JWT_SECRET', 'auto_generated_secure_key_2025_wordpress');

# 检查.env文件
PYTHON_JWT_SECRET=auto_generated_secure_key_2025_wordpress

# 如果不一致，修改后重启后端服务
```

---

### 问题3: 控制台没有 "从 URL 参数获取到 Token" 日志

**原因**：URL中没有 `sso_token` 参数

**检查**：
1. 宣传页面的控制台是否显示 "在新窗口打开应用: ...&sso_token=..."
2. WordPress插件是否已更新到 v3.0.12-final
3. WordPress缓存是否已清除

**解决**：
- 清除WordPress缓存
- 清除浏览器缓存
- 确认WordPress插件版本

---

### 问题4: URL中的Token没有自动清除

**检查**：
```javascript
// 在应用控制台执行
console.log('当前URL:', window.location.href);
```

**如果仍包含Token**：
- 检查控制台是否有 "SSO 登录成功" 日志
- 如果有，但Token未清除，说明 `window.history.replaceState` 失败

---

## 📊 验收清单

完整功能验证：

- [ ] Next.js开发服务器已重启
- [ ] Python后端API服务正常运行
- [ ] 已登录用户点击按钮 → 新窗口显示已登录状态
- [ ] 控制台显示 "SSO 登录成功（独立模式）"
- [ ] localStorage包含 `wp_jwt_token` 和 `wp_jwt_user`
- [ ] URL中的 `sso_token` 参数已自动清除
- [ ] 未登录用户完整流程正常
- [ ] Token验证失败时正确处理（显示未登录）
- [ ] 缓存Token可以正常使用

---

## 🎉 成功标志

**全部通过的标志**：
- ✅ 应用在新窗口打开后 **立即显示已登录状态**
- ✅ **不再显示** "独立模式 - 请选择登录方式"
- ✅ 控制台有 "SSO 登录成功（独立模式）" 日志
- ✅ URL中的Token已自动清除

---

**修复完成！** 🎊

现在Next.js应用可以在独立窗口模式下正确接收和处理WordPress传递的SSO Token了！

---

## 📝 技术总结

**修复要点**：
1. **识别问题**：AuthContext只支持iframe模式的Token接收
2. **调整逻辑**：将URL Token检测提前到iframe检测之前
3. **兼容性**：保留iframe模式支持，不影响现有功能
4. **安全性**：Token验证成功后立即从URL清除

**架构变化**：
- WordPress插件：v3.0.12 移除iframe模式，改为独立窗口
- Next.js应用：AuthContext支持独立窗口模式的Token接收
- 两端协同：完整的SSO Token传递流程

**测试覆盖**：
- 已登录用户SSO
- 未登录用户完整登录流程
- Token验证失败处理
- 缓存Token复用
