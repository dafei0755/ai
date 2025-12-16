# 📦 Next.js SSO v3.0.20 最终稳定版 - 部署指南

**版本**: v3.0.20 Stable
**发布日期**: 2025-12-16
**状态**: ✅ 稳定版（推荐生产环境使用）

---

## 🎉 v3.0.20 版本亮点

### 核心解决方案

✅ **跨域Cookie问题完美解决**
- 通过URL Token传递机制绕过浏览器跨域限制
- Chrome/Edge/Firefox全面测试通过
- 稳定可靠，无死循环问题

✅ **WPCOM隐藏区块架构**
- 利用WPCOM Member Pro会员内容可见性
- 登录用户自动看到应用入口
- 未登录用户引导到登录页面

✅ **JavaScript Token注入**
- 同域名获取Token（Cookie自动携带）
- 动态更新应用链接（URL参数）
- 一键进入应用，体验流畅

---

## 📋 部署清单

### WordPress端（5分钟）

#### 1. 上传并激活插件

```bash
# 上传文件
WordPress后台 → 插件 → 安装插件 → 上传插件
选择: nextjs-sso-integration-v3.0.20.zip

# 激活插件
点击"立即激活"
```

#### 2. 配置WPCOM隐藏区块

```bash
# 编辑宣传页面
WordPress后台 → 页面 → 所有页面
找到"智能设计分析"（/js）页面 → 点击"编辑"

# 添加WPCOM隐藏内容区块
1. 点击"+"添加区块
2. 搜索"WPCOM"或"会员内容"
3. 选择"WPCOM Member - 隐藏内容"
4. 设置可见条件：仅登录用户
5. 粘贴HTML + JavaScript代码（见下方）
6. 点击"更新"
```

**完整代码** (复制以下全部内容):

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

            console.log('[Token注入] ✅ Token 获取成功，长度:', token.length);

            // 🔧 生产环境请修改此URL
            const appUrl = 'http://localhost:3000'; // 开发环境
            // const appUrl = 'https://www.ucppt.com/nextjs'; // 生产环境

            const linkWithToken = appUrl + '?sso_token=' + encodeURIComponent(token);

            const linkElement = document.getElementById('app-entry-link');
            if (linkElement) {
                linkElement.href = linkWithToken;
                console.log('✅ Token已生成，应用链接已更新');
                console.log('🔗 链接预览:', linkWithToken.substring(0, 60) + '...');
            } else {
                console.error('❌ 找不到链接元素 #app-entry-link');
            }
        } else {
            console.error('❌ 获取Token失败，状态码:', response.status);
            const errorText = await response.text();
            console.error('   错误详情:', errorText);
        }
    } catch (error) {
        console.error('❌ Token获取异常:', error.message);
        console.error('   完整错误:', error);
    }
})();
</script>
```

**⚠️ 生产环境部署时**，请修改JavaScript代码中的应用URL：

```javascript
// 开发环境（本地测试）
const appUrl = 'http://localhost:3000';

// 生产环境（实际部署）
const appUrl = 'https://www.ucppt.com/nextjs';
```

#### 3. 清除缓存

```bash
# 如果使用缓存插件
WordPress后台 → 缓存插件 → 清除所有缓存

# 或通过插件管理
WP Super Cache → Delete Cache
W3 Total Cache → Empty All Caches
```

---

### Next.js应用端（已完成 ✅）

**前端代码已经正确配置**，无需修改：

- ✅ `page.tsx:466` - 跳转到 `ucppt.com/js`
- ✅ `AuthContext.tsx:110-151` - 支持URL Token参数
- ✅ `config.ts` - 版本号已更新到 v3.0.20

**启动应用**:

```bash
cd frontend-nextjs
npm run dev
```

---

## 🧪 测试验证

### 完整测试流程（5分钟）

#### 步骤1: 清除环境
```bash
# 清除浏览器缓存
按 Ctrl+Shift+Delete
选择：Cookie和其他网站数据、缓存的图片和文件
时间范围：全部
点击"清除数据"
```

#### 步骤2: 访问宣传页面
```bash
访问: https://www.ucppt.com/js
```

**预期结果**:
- ❌ 未看到"智能设计分析工具"卡片（未登录）
- ✅ 看到登录按钮

#### 步骤3: 登录WordPress
```bash
点击"登录"按钮
输入账号密码
点击登录
```

**预期结果**:
- ✅ 登录成功
- ✅ 页面自动刷新
- ✅ 看到"智能设计分析工具"卡片

#### 步骤4: 验证Token注入
```bash
按 F12 打开浏览器控制台
切换到 Console 标签
```

**预期日志**:
```javascript
[Token注入] 🚀 开始获取 Token...
[Token注入] 📡 REST API 响应状态: 200
[Token注入] ✅ Token 获取成功，长度: 250+
✅ Token已生成，应用链接已更新
🔗 链接预览: http://localhost:3000?sso_token=eyJ0eXAi...
```

#### 步骤5: 验证链接
```bash
右键点击"🚀 立即开始分析"按钮
选择"复制链接地址"
粘贴到记事本查看
```

**预期链接**:
```
http://localhost:3000?sso_token=eyJ0eXAiOiJKV1QiLCJhbGc...
```

#### 步骤6: 测试登录
```bash
点击"🚀 立即开始分析"按钮
```

**预期结果**:
- ✅ 跳转到 `localhost:3000?sso_token=...`
- ✅ 不显示"请先登录以使用应用"
- ✅ 直接进入 `/analysis` 页面
- ✅ 显示用户信息
- ✅ 控制台无401错误

---

## 📊 成功标志

### WordPress端
- [x] 插件已激活（v3.0.20）
- [x] WPCOM隐藏区块已配置
- [x] JavaScript代码已部署
- [x] 登录后可见"智能设计分析工具"卡片
- [x] 浏览器控制台显示Token生成成功

### 应用端
- [x] Next.js服务运行中（localhost:3000）
- [x] URL包含sso_token参数
- [x] 不显示登录界面
- [x] 自动进入/analysis页面
- [x] 控制台无401/400错误

---

## 🔧 故障排除

### 问题1: 控制台无Token生成日志

**症状**: 登录后浏览器控制台什么都没有

**原因**: JavaScript代码未部署或有语法错误

**解决**:
1. 检查WPCOM隐藏区块中的代码是否完整
2. 确认`<script>`标签存在
3. 清除WordPress和浏览器缓存
4. 重新保存页面

---

### 问题2: 获取Token失败401

**症状**: 控制台显示 `❌ 获取Token失败，状态码: 401`

**原因**: WordPress插件未正确安装或用户未登录

**解决**:
1. 确认插件已激活（v3.0.20）
2. 确认用户已登录WordPress
3. 检查`debug.log`：
   ```bash
   tail -f wp-content/debug.log
   ```
4. 应该看到：
   ```
   [Next.js SSO v3.0.20] 🌐 REST API /get-token 端点被调用
   [Next.js SSO v3.0.20] ✅ 准备为用户生成 Token: username (ID: 1)
   ```

---

### 问题3: 链接不包含Token

**症状**: 右键查看链接只有 `http://localhost:3000`

**原因**: 元素ID不匹配或JavaScript执行失败

**解决**:
1. 检查`<a>`标签是否有 `id="app-entry-link"`
2. 在控制台手动测试：
   ```javascript
   const link = document.getElementById('app-entry-link');
   console.log('链接元素:', link);
   console.log('当前href:', link ? link.href : '元素不存在');
   ```
3. 如果返回null，说明ID不匹配

---

### 问题4: 点击后仍显示登录界面

**症状**: 跳转到应用但显示"请先登录"

**原因**: Token验证失败或未正确传递

**调试**:
1. 检查URL是否包含`?sso_token=...`
2. 打开应用控制台（F12），查找：
   ```javascript
   [AuthContext] ✅ 从 URL 参数获取到 Token
   [AuthContext] Token 验证状态: 200
   [AuthContext] ✅ SSO 登录成功
   ```
3. 如果显示401，检查Token是否有效
4. 检查Python后端是否正常运行

---

## 🚀 生产环境部署

### 部署到同域名（推荐）

**配置结构**:
```
WordPress: https://www.ucppt.com/
应用: https://www.ucppt.com/nextjs/
```

**Nginx配置**:
```nginx
server {
    listen 443 ssl;
    server_name www.ucppt.com;

    # WordPress
    location / {
        # WordPress配置
    }

    # Next.js应用
    location /nextjs/ {
        proxy_pass http://localhost:3000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

**修改应用URL**:
1. 编辑WPCOM隐藏区块中的JavaScript
2. 修改appUrl：
   ```javascript
   const appUrl = 'https://www.ucppt.com/nextjs';
   ```
3. 保存并清除缓存

**优势**:
- ✅ 同域名，Cookie自动共享
- ✅ 无跨域问题
- ✅ 用户直接访问应用也能自动登录
- ✅ Token可以自动刷新
- ✅ 最佳用户体验

---

## 📚 相关文档

### 核心文档（必读）
- `CROSS_DOMAIN_COOKIE_FIX.md` - 跨域Cookie问题完整解决方案
- `WORDPRESS_HIDDEN_BLOCK_ARCHITECTURE.md` - WPCOM隐藏区块架构指南
- `EMERGENCY_FIX_INFINITE_LOOP.md` - 死循环问题紧急修复

### 测试文档
- `CROSS_DOMAIN_FIX_AUTO_TEST_GUIDE.md` - 自动化测试指南
- `INCOGNITO_MODE_TEST_GUIDE.md` - 无痕模式测试指南
- `e2e-tests/test-v3.0.20-cross-domain-fix.js` - 自动化测试脚本

### 历史文档（归档）
- `WPCOM_LOGIN_FIX_TEST_REPORT.md` - v3.0.18测试报告
- `WPCOM_LOGIN_FIX_QUICK_TEST.md` - v3.0.18快速测试

---

## 🎯 版本历史

### v3.0.20 (2025-12-16) - 稳定版 ✅
- ✅ 跨域Cookie问题完美解决
- ✅ WPCOM隐藏区块架构实施
- ✅ JavaScript Token注入机制
- ✅ 死循环问题修复
- ✅ 跨浏览器测试通过
- ✅ 生产环境就绪

### v3.0.17-v3.0.19 (2025-12-16) - 测试版
- 尝试不同的登录跳转方案
- 修复permission_callback问题
- 引入WPCOM隐藏区块架构

### v3.0.15-v3.0.16 (2025-12-16) - 早期版本
- 基础功能实现
- WPCOM Member Pro兼容性改进

---

## ✅ 总结

### 架构特点
1. **简单可靠** - 利用现有WPCOM功能
2. **无需后端改动** - JavaScript前端实现
3. **跨域友好** - URL Token传递机制
4. **用户体验好** - 一键登录，流程流畅

### 部署要点
1. WordPress插件v3.0.20
2. WPCOM隐藏区块配置
3. JavaScript Token注入代码
4. 前端AuthContext支持（已有）

### 成功指标
- ✅ 控制台显示Token生成成功
- ✅ 链接包含sso_token参数
- ✅ 应用自动登录
- ✅ 无死循环

---

**发布日期**: 2025-12-16
**版本**: v3.0.20 Stable
**状态**: ✅ 推荐生产环境使用
**支持**: 技术支持请查看故障排除部分
