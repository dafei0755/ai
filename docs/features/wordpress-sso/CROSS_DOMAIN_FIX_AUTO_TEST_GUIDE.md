# 🤖 跨域Cookie修复自动测试指南 v3.0.20

**测试文件**: `e2e-tests/test-v3.0.20-cross-domain-fix.js`
**创建时间**: 2025-12-16
**测试目的**: 验证URL Token传递机制是否正确解决跨域Cookie问题

---

## 🎯 测试覆盖范围

### 自动测试项目

1. ✅ **访问宣传页面** (`ucppt.com/js`)
2. ✅ **检测登录状态**（如未登录，等待用户手动登录）
3. ✅ **验证WPCOM隐藏区块可见性**
4. ✅ **检查应用入口链接是否包含 Token**
5. ✅ **点击链接并跳转到应用**
6. ✅ **验证URL包含 `sso_token` 参数**
7. ✅ **检查应用是否自动登录**（不显示"请先登录"）
8. ✅ **验证用户信息显示**
9. ✅ **检查是否进入 `/analysis` 页面**
10. ✅ **监控网络错误**（401/400）
11. ✅ **捕获浏览器控制台日志**

---

## 🚀 快速开始

### 前置条件

1. **WordPress配置完成**:
   - WPCOM隐藏区块已添加到 `ucppt.com/js` 页面
   - JavaScript Token注入代码已部署（方案B）
   - 隐藏区块设置为"仅登录用户可见"

2. **应用运行中**:
   ```bash
   cd frontend-nextjs
   npm run dev
   ```
   确认 `http://localhost:3000` 可访问

3. **依赖已安装**:
   ```bash
   cd e2e-tests
   npm install
   ```

---

## 📋 执行测试

### 方法1：Node.js直接运行（推荐）

```bash
cd e2e-tests
node test-v3.0.20-cross-domain-fix.js
```

### 方法2：使用npm脚本

```bash
cd e2e-tests
npm test test-v3.0.20-cross-domain-fix.js
```

---

## 📊 测试流程详解

### 步骤1：访问宣传页面
```
访问: https://www.ucppt.com/js
检测: 登录状态
```

**如果未登录**:
- 测试会暂停并提示手动登录
- 最多等待5分钟
- 登录成功后自动继续

### 步骤2：检查隐藏区块
```
验证: WPCOM隐藏区块是否可见
查找: 应用入口链接
检查: 链接是否包含 sso_token 参数
```

**预期输出**:
```
✅ 隐藏区块可见（用户已登录）
✅ 找到应用入口链接: "立即开始分析"
✅ 链接包含 sso_token 参数（修复已生效）
Token 预览: eyJ0eXAiOiJKV1QiLCJh...
```

### 步骤3：点击链接跳转
```
操作: 自动点击应用入口链接
等待: 跳转到 localhost:3000
```

### 步骤4：验证URL参数
```
检查: URL 是否包含 ?sso_token=...
提取: Token 值并显示预览
```

### 步骤5：检查登录状态
```
验证: 是否显示登录界面（应该不显示）
检查: 是否在 /analysis 页面
验证: 是否显示用户信息
```

**成功标志**:
```
✅ 不显示登录界面
✅ 在分析页面
✅ 显示用户信息
```

### 步骤6：网络错误监控
```
监控: 401/400 错误
记录: 所有错误请求
```

### 步骤7：浏览器控制台
```
捕获: AuthContext 相关日志
输出: Token 验证过程
```

---

## ✅ 成功标准

测试通过需要满足**所有**以下条件:

1. ✅ **URL包含Token**: `http://localhost:3000?sso_token=eyJ0eXA...`
2. ✅ **不显示登录界面**: 无"请先登录以使用应用"文本
3. ✅ **成功进入应用**: 在 `/analysis` 页面或显示用户信息
4. ✅ **无网络错误**: 无 401/400 错误

**预期输出**:
```
=======================================================================
📊 测试结果汇总
=======================================================================

✅✅✅ 测试通过！跨域Cookie修复生效 ✅✅✅

✓ URL 包含 sso_token 参数
✓ 应用自动登录成功
✓ 用户直接进入应用（无登录界面）
✓ 无 401/400 错误

🎉 v3.0.20 跨域Cookie修复完全成功！
```

---

## ❌ 失败场景及解决方案

### 场景A：URL不包含 sso_token

**症状**:
```
❌ URL 不包含 sso_token
   → 需要在 WPCOM 隐藏区块中添加 JavaScript Token 注入代码
```

**原因**: JavaScript代码尚未部署或未正确执行

**解决**:
1. 检查 `ucppt.com/js` 页面源代码
2. 确认 WPCOM 隐藏区块中包含 JavaScript 代码
3. 验证代码如下:
```javascript
<script>
(async function() {
    const response = await fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token', {
        credentials: 'include'
    });
    if (response.ok) {
        const data = await response.json();
        const token = data.token;
        const appUrl = 'http://localhost:3000';
        const linkWithToken = appUrl + '?sso_token=' + encodeURIComponent(token);
        document.getElementById('app-entry-link').href = linkWithToken;
    }
})();
</script>
```

### 场景B：仍然显示登录界面

**症状**:
```
❌ 仍然显示登录界面
   → Token 验证可能失败
```

**原因**: Token验证失败或REST API问题

**解决**:
1. 打开浏览器控制台（F12）
2. 查找 AuthContext 日志:
   ```
   [AuthContext] ✅ 从 URL 参数获取到 Token
   [AuthContext] Token 验证状态: 200
   ```
3. 如果显示 401/403，检查:
   - WordPress SSO插件是否已部署（v3.0.17+）
   - REST API端点是否正常工作
   - JWT密钥是否正确配置

### 场景C：找不到隐藏区块

**症状**:
```
❌ 隐藏区块不可见
   可能原因：
     1. WPCOM隐藏区块未正确配置
     2. 用户未登录
     3. 会员权限不足
```

**解决**:
1. WordPress后台 → 页面 → 编辑"智能设计分析" (`/js`)
2. 检查 WPCOM 隐藏内容区块设置:
   - 可见条件: 仅登录用户
   - 会员等级: 所有会员
3. 确认用户已登录 WordPress
4. 清除 WordPress 缓存

### 场景D：网络错误 (401/400)

**症状**:
```
❌ 发现 2 个错误请求:
  1. [401] https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token
  2. [401] https://www.ucppt.com/wp-json/nextjs-sso/v1/verify
```

**解决**:
1. 检查 WordPress 插件版本（应为 v3.0.17+）
2. 验证 `permission_callback` 设置为 `__return_true`
3. 查看 WordPress `debug.log`:
   ```bash
   tail -f wp-content/debug.log
   ```
4. 测试 REST API:
   ```bash
   curl -X GET "https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token" \
        -H "Cookie: wordpress_logged_in_xxx=..."
   ```

---

## 🔍 调试模式

### 查看详细网络请求

测试会自动记录所有网络请求，失败时会输出:
```
📋 诊断信息
=======================================================================
当前 URL: http://localhost:3000/analysis
总请求数: 15
错误请求数: 0
=======================================================================
```

### 手动检查关键点

测试过程中，浏览器会保持打开10秒，你可以:
1. 打开开发者工具（F12）
2. 切换到 Console 标签查看日志
3. 切换到 Network 标签查看请求
4. 手动测试应用功能

---

## 📈 测试报告

### 自动生成信息

测试完成后会输出:
- ✅/❌ 每个测试步骤的结果
- 📊 网络请求统计
- 🔍 错误详情（如有）
- 💡 修复建议（如失败）

### 手动记录建议

建议记录以下信息:
```
测试时间: 2025-12-16 14:30
测试环境: Windows 11, Chrome 120
WordPress版本: 6.4
WPCOM Member Pro版本: 3.0.4
Next.js SSO插件版本: v3.0.17
测试结果: ✅ 通过 / ❌ 失败
失败原因: [如果失败]
截图保存路径: [如果需要]
```

---

## 🎯 测试最佳实践

### 首次测试

1. **确认所有前置条件**
2. **手动测试一次流程**（确保基本功能正常）
3. **运行自动化测试**
4. **对比结果**

### 持续测试

1. **每次修改WordPress配置后运行**
2. **每次更新插件版本后运行**
3. **定期运行（每周一次）**

### 回归测试

如果修复后又出现问题:
1. 运行此测试确认问题
2. 对比之前的成功日志
3. 检查WordPress/插件是否有变更
4. 回滚到上一个工作版本

---

## 📞 问题排查流程

如果测试失败，按以下顺序检查:

### 1. WordPress端 (5分钟)
```
□ 登录 WordPress 后台
□ 访问 ucppt.com/js 页面
□ 检查 WPCOM 隐藏区块是否可见
□ 右键点击应用入口链接 → 复制链接地址
□ 检查链接是否包含 ?sso_token=...
```

### 2. 浏览器端 (5分钟)
```
□ F12 打开开发者工具
□ 访问 ucppt.com/js
□ 点击应用入口链接
□ 检查 Console 是否有错误
□ 检查 Network 是否有 401/400
```

### 3. 应用端 (5分钟)
```
□ 检查 localhost:3000 是否运行
□ 手动访问 localhost:3000?sso_token=test
□ 查看 AuthContext 是否响应
□ 检查 Next.js 控制台日志
```

### 4. REST API端 (5分钟)
```bash
# 测试 Token 生成
curl -X GET "https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token" \
     -H "Cookie: wordpress_logged_in_xxx=..." \
     -v

# 检查返回值
{
  "success": true,
  "token": "eyJ0eXAi..."
}
```

---

## 🎉 测试成功后

### 确认修复完成

1. ✅ 自动化测试通过
2. ✅ 手动测试通过
3. ✅ 多次测试稳定

### 更新文档

1. 标记 v3.0.20 为稳定版本
2. 更新部署文档
3. 记录测试结果

### 通知用户

1. 跨域Cookie问题已完全解决
2. 用户可以从 ucppt.com 直接进入应用
3. 无需手动输入密码

---

## 📚 相关文档

- **修复方案**: `CROSS_DOMAIN_COOKIE_FIX.md`
- **架构指南**: `WORDPRESS_HIDDEN_BLOCK_ARCHITECTURE.md`
- **测试报告**: `WPCOM_LOGIN_FIX_TEST_REPORT.md`
- **快速测试**: `WPCOM_LOGIN_FIX_QUICK_TEST.md`

---

**创建时间**: 2025-12-16
**测试文件**: `e2e-tests/test-v3.0.20-cross-domain-fix.js`
**预计测试时间**: 3-5分钟
**成功率预期**: 95%+（WordPress配置正确的情况下）
**难度**: ⭐⭐⭐ 中等（需要WordPress端配置）
