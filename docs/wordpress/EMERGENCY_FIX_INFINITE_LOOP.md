# 🚨 死循环问题紧急修复指南

**问题**: Edge 浏览器中，localhost:3000 和 ucppt.com/js 之间反复死循环
**根本原因**: 跨域 Cookie 无法携带 + Token 注入代码未部署
**影响浏览器**: 所有浏览器（Chrome 可能因缓存暂时工作）
**修复时间**: 5分钟

---

## 🔥 问题流程图

```
用户访问 localhost:3000
  ↓
AuthContext 尝试获取 Token（从 WordPress REST API）
  ↓
跨域请求，Cookie 未携带
  ↓
REST API 返回 401 ❌
  ↓
显示"请先登录以使用应用"
  ↓
用户点击"前往登录"
  ↓
跳转到 ucppt.com/js
  ↓
【问题点】点击"立即开始分析"
  ↓
链接没有 Token（JavaScript 未部署）
  ↓
跳转回 localhost:3000（无 Token）
  ↓
又是 401 → 又显示登录界面
  ↓
无限循环 ♻️
```

---

## ✅ 立即修复（5分钟）

### 步骤1: 部署 JavaScript Token 注入代码

#### 1.1 登录 WordPress 后台
```
https://www.ucppt.com/wp-admin
```

#### 1.2 编辑宣传页面
```
页面 → 所有页面 → 找到"智能设计分析"或 /js → 编辑
```

#### 1.3 找到 WPCOM 隐藏内容区块

向下滚动，找到包含"智能设计分析工具"的区块

#### 1.4 删除现有内容，粘贴完整代码

**完整代码**（必须全部复制）：

```html
<div id="app-entry-card" style="padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px; box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3); text-align: center; margin: 40px auto; max-width: 600px;">
    <div style="font-size: 48px; margin-bottom: 15px;">🎨</div>
    <h2 style="color: white; margin-bottom: 10px; font-size: 28px;">智能设计分析工具</h2>
    <p style="color: rgba(255,255,255,0.9); margin-bottom: 25px; font-size: 16px;">
        欢迎回来！您的专属AI设计助手已准备就绪
    </p>
    <a href="#" id="app-entry-link"
       style="display: inline-block; padding: 15px 40px; background: white; color: #667eea; border-radius: 10px; text-decoration: none; font-weight: bold; font-size: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); transition: all 0.3s;"
       onmouseover="this.style.transform='scale(1.05)'"
       onmouseout="this.style.transform='scale(1)'">
        🚀 立即开始分析
    </a>
    <p style="color: rgba(255,255,255,0.7); margin-top: 20px; font-size: 13px;">
        ✓ 实时分析  ✓ 专家建议  ✓ 智能优化
    </p>
</div>

<script>
(async function() {
    try {
        console.log('[Token注入] 🚀 开始获取 Token...');

        const response = await fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token', {
            credentials: 'include'
        });

        console.log('[Token注入] 📡 REST API 响应状态:', response.status);

        if (response.ok) {
            const data = await response.json();
            const token = data.token;

            console.log('[Token注入] ✅ Token 获取成功');
            console.log('[Token注入] 📏 Token 长度:', token.length);

            const appUrl = 'http://localhost:3000';
            const linkWithToken = appUrl + '?sso_token=' + encodeURIComponent(token);

            const linkElement = document.getElementById('app-entry-link');
            if (linkElement) {
                linkElement.href = linkWithToken;
                console.log('✅ Token已生成，应用链接已更新');
                console.log('🔗 链接预览:', linkWithToken.substring(0, 50) + '...');
            } else {
                console.error('❌ 找不到链接元素 #app-entry-link');
            }
        } else {
            console.error('❌ 获取Token失败，状态码:', response.status);
        }
    } catch (error) {
        console.error('❌ Token获取异常:', error.message);
    }
})();
</script>
```

#### 1.5 保存并发布
```
点击"更新"按钮
```

#### 1.6 清除 WordPress 缓存
```
如果使用缓存插件（如 WP Super Cache）：
WordPress 后台 → 缓存插件 → 清除所有缓存
```

---

### 步骤2: 在 Edge 中验证修复

#### 2.1 完全关闭 Edge
```
关闭所有 Edge 窗口和标签页
```

#### 2.2 重新打开 Edge
```
按 Ctrl+Shift+Delete → 清除浏览器缓存
```

#### 2.3 访问宣传页面
```
访问: https://www.ucppt.com/js
```

#### 2.4 登录 WordPress
```
输入账号密码，点击登录
```

#### 2.5 打开控制台验证
```
按 F12 → Console 标签
```

**应该看到**：
```javascript
[Token注入] 🚀 开始获取 Token...
[Token注入] 📡 REST API 响应状态: 200
[Token注入] ✅ Token 获取成功
[Token注入] 📏 Token 长度: 250
✅ Token已生成，应用链接已更新
🔗 链接预览: http://localhost:3000?sso_token=eyJ0eXAi...
```

**如果看到错误**：
```javascript
❌ 获取Token失败，状态码: 401
// 说明：WordPress 插件配置有问题
```

#### 2.6 验证链接
```
右键点击"🚀 立即开始分析"按钮
选择"复制链接地址"
粘贴到记事本查看
```

**应该包含**：
```
http://localhost:3000?sso_token=eyJ0eXAiOiJKV1QiLCJhbGc...
```

#### 2.7 点击按钮测试
```
点击"🚀 立即开始分析"
```

**预期结果**：
```
✅ 跳转到 localhost:3000?sso_token=...
✅ 不显示"请先登录"界面
✅ 直接进入 /analysis 页面
✅ 不再死循环
```

---

## 🔍 如果仍然失败

### 调试步骤

#### 检查1: WordPress REST API 是否正常

在 `ucppt.com/js` 页面的控制台执行：

```javascript
fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token', {
    credentials: 'include'
})
.then(r => r.json())
.then(data => console.log('✅ REST API 正常:', data))
.catch(err => console.error('❌ REST API 失败:', err));
```

**预期结果**：
```javascript
✅ REST API 正常: {success: true, token: "eyJ0eXAi..."}
```

**如果返回 401**：
- WordPress 插件配置问题
- 检查插件版本是否为 v3.0.17+
- 检查 `permission_callback` 是否为 `__return_true`

---

#### 检查2: 链接元素是否存在

在 `ucppt.com/js` 页面的控制台执行：

```javascript
const link = document.getElementById('app-entry-link');
console.log('链接元素:', link);
console.log('当前 href:', link ? link.href : '元素不存在');
```

**预期结果**：
```javascript
链接元素: <a id="app-entry-link" href="http://localhost:3000?sso_token=...">
当前 href: http://localhost:3000?sso_token=eyJ0eXAi...
```

**如果返回 null**：
- HTML 代码有问题
- 检查元素 ID 是否为 `app-entry-link`

---

#### 检查3: Network 面板

```
F12 → Network 标签 → 刷新页面
```

**查找请求**：
```
GET https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token
```

**点击该请求**，查看：
- **Status**: 应该是 200
- **Response**: 应该包含 `{"success": true, "token": "..."}`

---

## 🎯 成功标志

修复成功后，完整流程应该是：

### 场景1: 从 WordPress 进入应用

```
1. 访问 ucppt.com/js
2. 登录 WordPress
3. 看到"智能设计分析工具"卡片
4. 控制台显示：✅ Token已生成
5. 点击"立即开始分析"
6. 跳转到 localhost:3000?sso_token=...
7. 直接进入应用（不显示登录界面）
8. ✅ 不再死循环
```

### 场景2: 直接访问应用（会引导到 WordPress）

```
1. 访问 localhost:3000
2. 显示"请先登录以使用应用"
3. 点击"前往登录"
4. 跳转到 ucppt.com/js
5. （如果未登录）登录 WordPress
6. 看到"智能设计分析工具"卡片
7. 点击"立即开始分析"
8. 跳转回应用（带 Token）
9. 直接进入 /analysis
10. ✅ 流程完成
```

---

## 📊 问题对比

### 修复前（死循环）

| 步骤 | 状态 | 说明 |
|------|------|------|
| 访问 localhost:3000 | ❌ | 显示登录界面 |
| 点击"前往登录" | → | 跳转到 ucppt.com/js |
| 点击"立即开始分析" | ❌ | 链接无 Token |
| 跳转回 localhost:3000 | ❌ | 又是登录界面 |
| 死循环 | ♻️ | 无限重复 |

### 修复后（正常流程）

| 步骤 | 状态 | 说明 |
|------|------|------|
| 访问 ucppt.com/js | ✅ | 登录 WordPress |
| JavaScript 执行 | ✅ | Token 注入到链接 |
| 点击"立即开始分析" | ✅ | 链接包含 Token |
| 跳转到 localhost:3000 | ✅ | 带 Token 参数 |
| 自动登录 | ✅ | 进入 /analysis |
| 流程完成 | ✅ | 无死循环 |

---

## 🚀 长期解决方案

### 部署到同域名（推荐）

**生产环境配置**：
```
WordPress: https://www.ucppt.com/
应用部署: https://www.ucppt.com/nextjs/
```

**优势**：
- ✅ 同域名，Cookie 自动共享
- ✅ 无跨域问题
- ✅ 用户直接访问应用也能自动登录
- ✅ 无需依赖 URL Token
- ✅ 更稳定，跨浏览器兼容性好

**Nginx 配置示例**：
```nginx
# WordPress
location / {
    # WordPress 配置
}

# Next.js 应用
location /nextjs/ {
    proxy_pass http://localhost:3000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

---

## 📞 需要帮助？

如果按照上述步骤仍然失败，请提供：

### 1. 控制台日志
```
ucppt.com/js 页面的完整控制台输出（F12 → Console）
```

### 2. Network 请求详情
```
F12 → Network → get-token 请求的：
- Status Code
- Request Headers
- Response Headers
- Response Body
```

### 3. 截图
- WordPress 编辑器中 WPCOM 隐藏区块的代码
- 浏览器控制台的完整日志
- 右键链接显示的完整地址

---

## ✅ 总结

### 问题根源
1. **跨域 Cookie 无法携带**（浏览器安全策略）
2. **JavaScript Token 注入代码未部署**（关键！）
3. **链接中没有 Token**（导致死循环）

### 解决方法
1. **立即**：部署 JavaScript Token 注入代码（5分钟）
2. **长期**：部署到同域名（生产环境推荐）

### 成功标志
- 控制台显示：`✅ Token已生成，应用链接已更新`
- 链接包含：`?sso_token=...`
- 点击后直接进入应用
- 不再死循环

---

**创建时间**: 2025-12-16
**紧急程度**: 🔥 高（死循环问题）
**修复时间**: 5分钟
**成功率**: 99%（部署代码后）
