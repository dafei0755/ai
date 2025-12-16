# v3.0.15 登录检测失败 - 快速诊断清单

## 🐛 问题描述

**症状**: 网站右上角显示已登录，但点击"立即使用"按钮后，应用仍然显示"请先登录以使用应用"

**预期行为**: 已登录用户点击按钮 → 新窗口打开应用 → 自动跳转到 `/analysis`（不显示登录界面）

---

## ✅ 快速检查清单（按顺序执行）

### 检查1: 确认WordPress插件版本

**操作**:
```
WordPress后台 → 插件 → 已安装的插件
找到 "Next.js SSO Integration v3"
检查版本号
```

**预期结果**: 版本号应为 **3.0.15**

**如果不是**:
1. 停用旧插件
2. 上传并安装 `nextjs-sso-integration-v3.0.15.zip`
3. 启用插件
4. 继续下一步检查

---

### 检查2: 清除WordPress缓存

**操作**:
```
WordPress后台 → 设置 → WP Super Cache → 删除缓存
```

**然后**:
```
浏览器地址栏输入: https://www.ucppt.com/js
按 Ctrl + Shift + R（强制刷新，清除浏览器缓存）
```

---

### 检查3: 确认宣传页面JavaScript版本

**操作**:
1. 访问: `https://www.ucppt.com/js`
2. 按 `F12` 打开浏览器控制台
3. 查看第一条日志

**预期日志**:
```javascript
[Next.js SSO v3.0.15] 宣传页面脚本已加载（极简模式）
[Next.js SSO v3.0.15] app_url: http://localhost:3000
```

**如果显示其他版本号（如 v3.0.14）**:
- 说明缓存未清除，返回"检查2"重新清除
- 或使用无痕模式测试: `Ctrl + Shift + N`（Chrome/Edge）

---

### 检查4: 测试REST API Token接口

**操作**: 在宣传页面的控制台执行以下命令

**已登录状态测试**:
```javascript
fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token', {
    credentials: 'include'
}).then(r => {
    console.log('REST API 状态码:', r.status);
    return r.json();
}).then(data => {
    console.log('REST API 响应数据:', data);
    console.log('Token 长度:', data.token ? data.token.length : 0);
});
```

**预期输出（已登录）**:
```javascript
REST API 状态码: 200
REST API 响应数据: {success: true, token: "eyJ0eXAiOiJKV1QiL...", user: {...}}
Token 长度: 200+ （Token应该有200+字符）
```

**如果返回 401**:
```javascript
REST API 状态码: 401
REST API 响应数据: {error: "Not logged in"}
```
→ 说明WordPress没有检测到登录状态，请检查WPCOM Member Pro的登录Cookie

**如果返回 500**:
→ 说明WordPress插件内部错误，查看 `/wp-content/debug.log`

---

### 检查5: 确认Python后端服务运行

**操作**: 打开命令提示符执行

```bash
curl http://127.0.0.1:8000/health
```

**预期输出**:
```json
{"status": "healthy"}
```

**如果连接失败**:
```
启动Python后端:
cd d:\11-20\langgraph-design
python -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000
```

---

### 检查6: 确认Next.js应用已更新

**操作**:
1. 打开文件: `d:\11-20\langgraph-design\frontend-nextjs\contexts\AuthContext.tsx`
2. 搜索: `v3.0.15`

**预期**: 应该能找到以下注释（Lines 291附近）:
```typescript
// 🆕 v3.0.15: 尝试通过 WordPress REST API 获取 Token
```

**如果找不到**:
→ 说明AuthContext代码未更新，请重新应用修改

---

### 检查7: 重启Next.js开发服务器

**操作**:
```bash
# 终止当前运行的服务（Ctrl + C）
cd d:\11-20\langgraph-design\frontend-nextjs
npm run dev
```

**验证**: 服务器在 `http://localhost:3000` 运行，无编译错误

---

### 检查8: 完整用户流程测试

**操作**:
1. 确保WordPress已登录（右上角显示用户名）
2. 访问: `https://www.ucppt.com/js`
3. 按 `F12` 打开控制台
4. 点击"立即使用"按钮
5. 观察新窗口的控制台

**预期日志（新窗口的控制台）**:
```javascript
[Next.js SSO v3.0.15] 宣传页面脚本已加载（极简模式）
[Next.js SSO v3.0.15] 在新窗口打开应用: http://localhost:3000
[Next.js SSO v3.0.15] ✅ 应用成功在新窗口打开
```

**新窗口应用的控制台（重点！）**:
```javascript
[AuthContext] 尝试通过 WordPress REST API 获取 Token...
[AuthContext] ✅ 通过 REST API 获取到 Token，验证中...
[AuthContext] Token 验证状态: 200
[AuthContext] ✅ REST API Token 验证成功，用户: {user_id: 123, username: "xxx", ...}
[AuthContext] 🔀 检测到已登录，跳转到分析页面
```

**最终结果**: 应用自动跳转到 `/analysis` 页面，显示已登录状态

---

## 🚨 常见问题诊断

### 问题A: 新窗口显示"请先登录"，控制台无REST API日志

**原因**: AuthContext代码未更新或Next.js服务未重启

**解决**:
1. 检查 `AuthContext.tsx` 是否包含 v3.0.15 代码（Lines 291-346）
2. 重启Next.js开发服务器
3. 强制刷新浏览器: `Ctrl + Shift + R`

---

### 问题B: 控制台显示"Token 验证状态: 500"

**原因**: Python后端未运行

**解决**:
```bash
cd d:\11-20\langgraph-design
python -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000
```

---

### 问题C: 控制台显示"Token 验证状态: 401"

**原因**: JWT密钥不匹配

**解决**:
1. 检查 `wp-config.php`:
   ```php
   define('PYTHON_JWT_SECRET', 'auto_generated_secure_key_2025_wordpress');
   ```
2. 检查 `.env`:
   ```
   PYTHON_JWT_SECRET=auto_generated_secure_key_2025_wordpress
   ```
3. 确保两者完全一致
4. 重启Python后端

---

### 问题D: REST API 返回 401（WordPress未检测到登录）

**可能原因**:
1. WPCOM Member Pro的Cookie不被WordPress REST API识别
2. Cookie域名配置问题
3. WPCOM插件未正确集成WordPress认证

**排查步骤**:
1. 检查浏览器Cookie:
   - 按 `F12` → Application/存储 → Cookies → https://www.ucppt.com
   - 查找 `wordpress_logged_in_*` Cookie
   - 如果没有，说明WPCOM使用自定义Cookie，WordPress无法识别

2. 测试WordPress标准登录:
   - 访问 `/wp-login.php`
   - 使用WordPress管理员账号登录
   - 重新测试REST API

3. 如果WordPress标准登录可用，但WPCOM登录不可用:
   - 联系WPCOM Member Pro插件作者
   - 或考虑使用WordPress标准登录系统

---

## 📊 验收标准

完整通过的标志:

- [ ] WordPress插件版本为 3.0.15
- [ ] 宣传页面控制台显示 `[Next.js SSO v3.0.15]`
- [ ] REST API 测试返回 200 + Token
- [ ] Python后端健康检查通过
- [ ] AuthContext包含v3.0.15代码
- [ ] Next.js开发服务器已重启
- [ ] 已登录用户点击按钮 → 新窗口打开 → 自动跳转 `/analysis`
- [ ] **不显示登录界面**（关键！）

---

## 🎯 核心诊断命令（快速版）

如果你时间紧迫，只执行这3个命令:

### 命令1: 检查WordPress REST API
```javascript
// 在宣传页面控制台执行
fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token', {
    credentials: 'include'
}).then(r => r.json()).then(console.log);
```
**期望**: `{success: true, token: "...", user: {...}}`

### 命令2: 检查Python后端
```bash
curl http://127.0.0.1:8000/health
```
**期望**: `{"status": "healthy"}`

### 命令3: 检查应用控制台（点击按钮后的新窗口）
**期望日志**:
```
[AuthContext] ✅ REST API Token 验证成功
[AuthContext] 🔀 检测到已登录，跳转到分析页面
```

如果这3个都正常，应用就会自动跳转！

---

**诊断完成后，请反馈具体的错误信息，我将提供针对性的解决方案。**

**最后更新**: 2025-12-16
**适用版本**: v3.0.15
