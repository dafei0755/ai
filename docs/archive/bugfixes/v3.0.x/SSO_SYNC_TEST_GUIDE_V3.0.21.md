# 🧪 SSO同步系统测试指南 v3.0.21

**测试日期**: 2025-12-17
**版本**: v3.0.21
**测试目的**: 验证WordPress用户切换后，NextJS应用能够自动同步更新

---

## ✅ 前置检查

### 1. NextJS开发服务器
- ✅ NextJS已在端口3000运行
- 访问地址: http://localhost:3000
- 状态: 🟢 运行中

### 2. WordPress站点
- WordPress地址: https://www.ucppt.com
- REST API端点: https://www.ucppt.com/wp-json/nextjs-sso/v1/sync-status
- 插件版本: v3.0.21 (需确认已上传)

### 3. 浏览器准备
- 推荐: Chrome/Edge（支持完整的开发者工具）
- 清除缓存: Ctrl+Shift+Delete → 清除缓存
- 打开开发者工具: F12

---

## 🧪 测试场景1: 使用诊断工具（推荐）

### 步骤1: 打开诊断工具

在浏览器中打开：`file:///d:/11-20/langgraph-design/test-sso-sync-v3.0.21.html`

或者双击文件：`d:\11-20\langgraph-design\test-sso-sync-v3.0.21.html`

### 步骤2: 运行诊断测试

**测试顺序**:

1️⃣ **步骤1: 检查事件Cookie**
- 点击"🔍 检查事件Cookie"按钮
- **预期结果**:
  ```
  ⚠️ 未找到登录事件Cookie
  原因可能：1) WordPress未触发登录Hook, 2) Cookie已过期(5分钟), 3) 跨域限制
  ```
- **结论**: 这是正常的（localhost无法读取www.ucppt.com的Cookie）

2️⃣ **步骤2: 测试REST API**
- 点击"🌐 测试REST API"按钮
- **预期结果**（如果WordPress已登录）:
  ```
  ✅ HTTP状态码: 200
  ✅ API响应成功
  ✅ 登录状态: 已登录
  - 用户ID: XXXX
  ✅ REST API工作正常，方案2应该可以使用
  ```
- **如果返回401**: WordPress未登录，需要先登录

3️⃣ **步骤3: 测试CORS**
- 点击"🔒 测试CORS"按钮
- **预期结果**:
  ```
  ✅ CORS响应头:
  - Access-Control-Allow-Origin: http://localhost:3000 (或*)
  - Access-Control-Allow-Credentials: true
  ✅ CORS配置正确，跨域请求成功
  ```

4️⃣ **步骤4: 实时监控**
- 点击"▶️ 启动监控"按钮
- **观察**: 日志会每2秒输出一次检测结果
- **然后**: 在WordPress后台登录/切换用户
- **预期结果**（登录后2秒内）:
  ```
  🎉 [检测 #X] 发现登录事件!
  - 用户: username (ID: XXXX)
  - Token: eyJhbGciOiJIUzI1NiIsInR5cCI...
  ```

---

## 🧪 测试场景2: NextJS应用实际测试

### 步骤1: 打开NextJS应用

1. 浏览器新标签页打开: http://localhost:3000
2. 打开开发者工具（F12）→ Console

### 步骤2: 观察初始状态

**查看控制台日志**，应该看到：
```
[AuthContext v3.0.21] 📄 页面重新可见，检测SSO状态
```

或者（如果已登录）：
```
[AuthContext v3.0.21] ✅ 检测到WordPress登录事件（REST API）
[AuthContext v3.0.21] 新用户: {user_id: XXXX, username: "xxx", ...}
```

### 步骤3: WordPress登录/切换用户

**操作A：从未登录到登录**
1. 确保WordPress未登录（访问 https://www.ucppt.com/wp-admin）
2. 如果已登录，先退出
3. 重新登录用户A

**操作B：用户切换**
1. 在WordPress后台已登录用户A
2. 使用"User Switching"插件切换到用户B（或退出后登录用户B）

### 步骤4: 观察NextJS同步

**方式1：切换标签页触发（立即）**
1. 登录后，立即切换到NextJS标签页
2. 观察控制台，应该在**1秒内**看到：
   ```
   [AuthContext v3.0.21] 📄 页面重新可见，检测SSO状态
   [AuthContext v3.0.21] ✅ 检测到WordPress登录事件（REST API）
   [AuthContext v3.0.21] 新用户: {user_id: 2751, username: "testuser", ...}
   ```

**方式2：定期轮询触发（10秒内）**
1. 登录后，**保持在NextJS标签页**（不切换）
2. 等待最多10秒
3. 观察控制台，应该看到相同的日志

### 步骤5: 验证UI更新

- NextJS应用右上角应显示新用户的头像和用户名
- 如果有"会员等级"信息，应该更新为新用户的等级
- 所有需要认证的功能应该正常工作

---

## 🧪 测试场景3: 退出登录同步

### 步骤1: 当前已登录

确保NextJS应用显示已登录状态（右上角有用户头像）

### 步骤2: WordPress退出登录

1. 在WordPress后台点击"退出登录"
2. 或者：清除WordPress Cookie（开发者工具 → Application → Cookies → 删除所有Cookie）

### 步骤3: 观察NextJS同步

**切换标签页触发**:
1. 退出后，切换到NextJS标签页
2. 应该在1秒内看到：
   ```
   [AuthContext v3.0.21] 📄 页面重新可见，检测SSO状态
   [AuthContext v3.0.21] ✅ 检测到WordPress退出事件（REST API）
   ```

**定期轮询触发**:
1. 保持在NextJS标签页，等待最多10秒
2. 应该看到相同的日志

### 步骤4: 验证UI更新

- localStorage应该清除Token（开发者工具 → Application → Local Storage → 无 `wp_jwt_token`）
- NextJS应用应该显示未登录状态（登录提示界面）
- 右上角用户头像应该消失

---

## 🧪 测试场景4: 跨标签页同步（高级）

### 步骤1: 打开多个NextJS标签页

1. 打开标签页1: http://localhost:3000
2. 打开标签页2: http://localhost:3000（新标签页）
3. 打开标签页3: http://localhost:3000（再新标签页）

### 步骤2: WordPress登录

在WordPress后台登录用户A

### 步骤3: 观察所有标签页

**预期行为**:
- 标签页1（当前焦点）: 立即检测到登录（如果是active标签页）
- 标签页2（后台）: 切换到该标签页时，1秒内检测到登录
- 标签页3（后台）: 切换到该标签页时，1秒内检测到登录

**或者**:
- 所有标签页在10秒内都会通过定期轮询检测到登录

---

## 📊 测试结果记录表

| 测试场景 | 预期结果 | 实际结果 | 时间 | 备注 |
|---------|---------|---------|------|------|
| 诊断工具-Cookie检查 | ❌ 失败（跨域） | | | 正常，localhost无法读取 |
| 诊断工具-REST API | ✅ 成功 | | | 返回200 + logged_in:true |
| 诊断工具-CORS | ✅ 成功 | | | Allow-Origin正确 |
| 诊断工具-实时监控 | ✅ 2秒内检测 | | | 登录后立即检测到 |
| NextJS-切换标签页 | ✅ 1秒内同步 | | | visibilitychange触发 |
| NextJS-定期轮询 | ✅ 10秒内同步 | | | 定期检测触发 |
| NextJS-退出同步 | ✅ 清除Token | | | localStorage清空 |
| NextJS-跨标签页 | ✅ 所有标签页同步 | | | 切换时检测 |

---

## 🔍 故障排查

### 问题1: REST API返回401

**现象**: 诊断工具或NextJS都显示401错误

**排查**:
1. 确认WordPress是否真的登录了
2. 访问: https://www.ucppt.com/wp-json/nextjs-sso/v1/sync-status
3. 查看响应：
   - `{"logged_in": false, ...}` → WordPress未登录
   - `{"code": "rest_forbidden", ...}` → CORS或权限问题

**解决**:
- 在WordPress后台重新登录
- 检查WordPress插件是否激活（v3.0.21）

---

### 问题2: CORS错误

**现象**: 浏览器控制台显示 `CORS policy` 错误

**排查**:
1. 打开 `nextjs-sso-integration-v3.php`
2. 查看 Lines 761-783（CORS配置）
3. 确认 `$allowed_origins` 数组包含：
   ```php
   'http://localhost:3000',
   'http://127.0.0.1:3000',
   ```

**解决**:
- 如果不在列表中，添加当前域名
- 重新上传插件到WordPress

---

### 问题3: NextJS无日志输出

**现象**: 切换标签页后，控制台没有任何日志

**排查**:
1. 确认NextJS应用已加载（查看页面内容）
2. 确认AuthContext已挂载（查看React DevTools）
3. 手动触发检测：
   ```javascript
   // 在控制台执行
   fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/sync-status', {
     method: 'GET',
     credentials: 'include'
   }).then(r => r.json()).then(console.log)
   ```

**解决**:
- 重启NextJS服务器（Ctrl+C，然后 `npm run dev`）
- 清除浏览器缓存
- 检查是否有JavaScript错误

---

### 问题4: WordPress Hooks未触发

**现象**: 诊断工具监控时，登录后未检测到事件

**排查**:
1. 查看WordPress错误日志：`wp-content/debug.log`
2. 搜索：`[Next.js SSO v3.0.21]`
3. 应该看到：
   ```
   [Next.js SSO v3.0.21] 📡 用户登录事件触发: username (ID: XXXX)
   [Next.js SSO v3.0.21] ✅ 登录事件Cookie已设置
   ```

**如果没有日志**:
- WordPress插件未激活（WordPress后台 → 插件 → 确认激活）
- WordPress `WP_DEBUG` 未启用（wp-config.php）
- 使用了第三方用户切换插件（绕过了 `wp_login` Hook）

**解决**:
- 激活插件
- 启用调试：`wp-config.php` 添加 `define('WP_DEBUG', true);`
- 使用标准登录流程（退出后重新登录）

---

## 📈 预期性能指标

| 指标 | 目标值 | 测试值 |
|------|--------|--------|
| 页面切换检测延迟 | <1秒 | |
| 定期轮询检测延迟 | <10秒 | |
| REST API响应时间 | <500ms | |
| 跨标签页同步时间 | <10秒 | |
| Token验证成功率 | 100% | |

---

## ✅ 测试通过标准

**必须满足**:
- ✅ REST API测试成功（返回200）
- ✅ CORS测试成功
- ✅ 切换标签页时，1秒内检测到登录事件
- ✅ NextJS应用显示新用户信息（头像、用户名）
- ✅ 退出登录时，Token被清除

**可选**:
- ✅ 定期轮询在10秒内检测到变化
- ✅ 所有标签页都能同步（切换时）

---

## 🎯 下一步

### 测试通过后

1. **记录测试结果**: 填写上述"测试结果记录表"
2. **截图保存**: 保存成功日志的截图
3. **更新文档**: 如有问题，更新故障排除指南
4. **准备生产部署**: 如果测试通过，准备部署到生产环境

### 测试失败时

1. **详细记录**: 记录失败的场景、错误信息、截图
2. **查看日志**:
   - WordPress: `wp-content/debug.log`
   - NextJS: 浏览器控制台
   - 服务器: `d:\11-20\langgraph-design\logs\server.log`
3. **提供诊断信息**: 包含上述所有日志
4. **联系支持**: 提供完整的测试记录和日志

---

**测试负责人**: 待填写
**测试日期**: 2025-12-17
**测试环境**: 开发环境（localhost:3000）
**WordPress版本**: 待确认
**插件版本**: v3.0.21
**测试状态**: ⏳ 待测试
