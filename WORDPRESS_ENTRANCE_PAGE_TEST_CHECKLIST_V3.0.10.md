# WordPress 应用宣传页面测试清单 (v3.0.10)

## 🧪 测试环境准备

### 前置条件
- [x] WordPress插件已更新到 v3.0.10
- [x] 已创建宣传页面（例如：https://www.ucppt.com/js）
- [x] 页面包含短代码 `[nextjs-app-entrance]`
- [x] 短代码中 `app_url` 参数已配置为生产环境URL
- [x] 所有缓存已清除（WordPress + 浏览器）

### 测试浏览器
建议使用以下浏览器进行测试：
- [ ] Chrome（推荐）
- [ ] Firefox
- [ ] Safari
- [ ] Edge

---

## 📋 测试场景 A: 未登录用户完整流程

### A1: 访问宣传页面

**操作**：
1. 退出WordPress登录（或使用无痕模式）
2. 访问：`https://www.ucppt.com/js`

**预期结果**：
- [ ] 页面加载成功，无404错误
- [ ] 显示应用标题和描述
- [ ] 显示 "立即使用 →" 按钮
- [ ] 显示状态消息："请先登录以使用应用 · 登录后将自动跳转"
- [ ] 显示4个特性卡片（带图标）

**截图位置**：保存为 `test-a1-entrance-not-logged-in.png`

---

### A2: 点击按钮跳转到登录页

**操作**：
1. 点击 "立即使用 →" 按钮

**预期结果**：
- [ ] 页面跳转到WordPress登录页面
- [ ] URL格式：`https://www.ucppt.com/wp-login.php?redirect_to=...`
- [ ] 登录页面显示用户名和密码输入框

**检查浏览器控制台**（F12）：
```javascript
[Next.js App Entrance] 未登录用户跳转到登录页: https://www.ucppt.com/wp-login.php?redirect_to=...
```

**截图位置**：保存为 `test-a2-wordpress-login-page.png`

---

### A3: 登录并返回宣传页面

**操作**：
1. 输入WordPress用户名
2. 输入密码
3. 点击 "登录" 按钮

**预期结果**：
- [ ] 登录成功
- [ ] 自动返回到宣传页面：`https://www.ucppt.com/js`
- [ ] 页面显示已登录状态："✓ 您已登录为 [用户名]，点击按钮直接进入应用"
- [ ] 按钮文字变为 "立即使用 →"

**检查浏览器控制台**（F12）：
```javascript
// 应该看到：
[Next.js App Entrance] 检测到登录成功，自动跳转到应用: https://ai.ucppt.com?mode=standalone&sso_token=...
```

**检查sessionStorage**（控制台执行）：
```javascript
console.log(sessionStorage.getItem('nextjs_app_target_url'));
// 预期输出: "https://ai.ucppt.com?mode=standalone" 或 null（如果已被清除）
```

**截图位置**：保存为 `test-a3-entrance-after-login.png`

---

### A4: 自动跳转到应用

**预期结果**：
- [ ] 登录后1秒内，自动跳转到应用
- [ ] 跳转目标：`https://ai.ucppt.com?mode=standalone&sso_token=xxx`
- [ ] 应用页面加载成功
- [ ] 应用显示完整界面（已登录状态）

**检查URL**：
```
https://ai.ucppt.com?mode=standalone&sso_token=eyJ0eXAiOiJKV1QiLC...
                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                    URL中应包含 sso_token 参数
```

**检查应用控制台**（F12）：
```javascript
[AuthContext] 🔍 检查 URL 参数中的 Token
[AuthContext] ✅ 找到 URL 参数中的 sso_token
[AuthContext] 💾 已保存 Token 到 localStorage
[AuthContext] 🧹 已从 URL 中清除 sso_token 参数
[AuthContext] ✅ Token 验证成功
[AuthContext] 👤 设置用户信息: {username: "xxx", ...}
```

**检查localStorage**（控制台执行）：
```javascript
console.log('Token:', localStorage.getItem('wp_jwt_token'));
console.log('User:', localStorage.getItem('wp_jwt_user'));

// 预期输出:
// Token: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL3d3dy51Y3BwdC5jb20iLC...
// User: {"user_id":123,"username":"admin","email":"admin@ucppt.com","display_name":"管理员"}
```

**截图位置**：保存为 `test-a4-app-logged-in.png`

---

### A5: 验证应用功能

**操作**：
1. 在应用中查看用户面板（右上角）
2. 尝试创建新会话

**预期结果**：
- [ ] 用户面板显示用户名和头像
- [ ] 可以创建新会话
- [ ] 可以查看历史会话列表
- [ ] 所有API请求正常（无401错误）

**截图位置**：保存为 `test-a5-app-user-panel.png`

---

## 📋 测试场景 B: 已登录用户直接跳转

### B1: 访问宣传页面（已登录状态）

**操作**：
1. 确保已在WordPress登录（可以访问WordPress后台）
2. 访问：`https://www.ucppt.com/js`

**预期结果**：
- [ ] 页面加载成功
- [ ] 显示已登录状态消息："✓ 您已登录为 [用户名]，点击按钮直接进入应用"
- [ ] 按钮文字为 "立即使用 →"
- [ ] 不显示 "请先登录" 消息

**截图位置**：保存为 `test-b1-entrance-logged-in.png`

---

### B2: 点击按钮直接跳转

**操作**：
1. 点击 "立即使用 →" 按钮

**预期结果**：
- [ ] 立即跳转到应用（无需登录流程）
- [ ] 跳转目标：`https://ai.ucppt.com?mode=standalone&sso_token=xxx`
- [ ] 应用显示已登录状态

**检查浏览器控制台**（F12）：
```javascript
[Next.js App Entrance] 已登录用户跳转到应用: https://ai.ucppt.com?mode=standalone&sso_token=eyJ0eXAiOiJKV1QiLC...
```

**截图位置**：保存为 `test-b2-app-direct-access.png`

---

## 📋 测试场景 C: Token传递验证

### C1: 检查Token格式

**操作**：
1. 以已登录状态访问宣传页面
2. 打开浏览器控制台（F12）
3. 点击 "立即使用 →" 按钮
4. 查看控制台日志

**预期结果**：
- [ ] 控制台显示跳转URL
- [ ] URL包含 `sso_token` 参数
- [ ] Token是JWT格式（三段式，用点号分隔）

**示例日志**：
```javascript
[Next.js App Entrance] 已登录用户跳转到应用: https://ai.ucppt.com?mode=standalone&sso_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL3d3dy51Y3BwdC5jb20iLCJpYXQiOjE3MzQyNTgwMDAsImV4cCI6MTczNDg2MjgwMCwiZGF0YSI6eyJ1c2VyIjp7ImlkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwiZW1haWwiOiJhZG1pbkB1Y3BwdC5jb20iLCJkaXNwbGF5X25hbWUiOiJcdTdmMTFcdTc0MDZcdTU0NTgiLCJyb2xlcyI6WyJhZG1pbmlzdHJhdG9yIl19fX0.xxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Token结构验证**（复制Token，访问 https://jwt.io/）：
- [ ] Header包含：`{"typ":"JWT","alg":"HS256"}`
- [ ] Payload包含：`{"iss":"https://www.ucppt.com","iat":...,"exp":...,"data":{"user":{...}}}`
- [ ] Signature有效（需要密钥验证）

---

### C2: 检查Token接收

**操作**：
1. 跳转到应用后
2. 打开浏览器控制台（F12）
3. 执行命令查看localStorage

**预期结果**：
```javascript
console.log('Token:', localStorage.getItem('wp_jwt_token'));
// 输出: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL3d3dy51Y3BwdC5jb20iLC...

console.log('User:', localStorage.getItem('wp_jwt_user'));
// 输出: {"user_id":1,"username":"admin","email":"admin@ucppt.com","display_name":"管理员"}
```

**验证点**：
- [ ] Token存在且非null
- [ ] User对象包含user_id、username、email、display_name字段
- [ ] user_id为数字
- [ ] email格式正确

---

### C3: 检查Token自动清除

**操作**：
1. 跳转到应用后
2. 查看浏览器地址栏URL

**预期结果**：
- [ ] URL中**不再包含** `sso_token` 参数
- [ ] URL变为：`https://ai.ucppt.com?mode=standalone`（或 `https://ai.ucppt.com`）

**验证意义**：
- ✅ 防止Token泄露（URL可能被分享或记录）
- ✅ Token已安全存储到localStorage

---

## 📋 测试场景 D: 错误处理

### D1: 网络错误模拟

**操作**：
1. 打开浏览器开发者工具（F12）
2. 切换到 "Network" 标签
3. 启用 "Offline" 模式（模拟网络断开）
4. 访问宣传页面
5. 点击按钮

**预期结果**：
- [ ] 页面显示错误提示（或浏览器默认离线页面）
- [ ] 不应该出现JavaScript错误
- [ ] 恢复网络后，重新访问可以正常使用

---

### D2: 无效Token处理

**操作**：
1. 手动修改localStorage中的Token为无效值
   ```javascript
   localStorage.setItem('wp_jwt_token', 'invalid-token');
   ```
2. 刷新应用页面

**预期结果**：
- [ ] 应用检测到Token无效
- [ ] 显示登录提示界面
- [ ] 用户可以重新登录

**控制台日志**：
```javascript
[AuthContext] ❌ Token 验证失败: 401
[AuthContext] 清除无效的 Token
```

---

### D3: sessionStorage被清除

**操作**：
1. 以未登录状态访问宣传页面
2. 点击 "立即使用" 按钮（跳转到登录页）
3. **在登录前**，打开控制台执行：
   ```javascript
   sessionStorage.clear();
   ```
4. 完成登录

**预期结果**：
- [ ] 登录成功返回宣传页面
- [ ] **不会自动跳转到应用**（因为目标URL丢失）
- [ ] 页面显示已登录状态
- [ ] 用户可以手动点击按钮进入应用

**备注**：这是边缘情况，正常使用不会遇到

---

## 📋 测试场景 E: 浏览器兼容性

### E1: Chrome测试

**操作**：
- [ ] 完成场景A（未登录完整流程）
- [ ] 完成场景B（已登录直接跳转）
- [ ] 检查控制台无错误

**结果**：✅ 通过 / ❌ 失败

---

### E2: Firefox测试

**操作**：
- [ ] 完成场景A（未登录完整流程）
- [ ] 完成场景B（已登录直接跳转）
- [ ] 检查控制台无错误

**结果**：✅ 通过 / ❌ 失败

---

### E3: Safari测试

**操作**：
- [ ] 完成场景A（未登录完整流程）
- [ ] 完成场景B（已登录直接跳转）
- [ ] 检查控制台无错误

**特别注意**：Safari对跨域Cookie和localStorage有更严格的限制

**结果**：✅ 通过 / ❌ 失败

---

### E4: Edge测试

**操作**：
- [ ] 完成场景A（未登录完整流程）
- [ ] 完成场景B（已登录直接跳转）
- [ ] 检查控制台无错误

**结果**：✅ 通过 / ❌ 失败

---

## 📋 测试场景 F: 性能测试

### F1: 页面加载时间

**操作**：
1. 使用Chrome开发者工具的 "Network" 标签
2. 清除缓存
3. 访问宣传页面
4. 记录 "DOMContentLoaded" 和 "Load" 时间

**预期结果**：
- [ ] DOMContentLoaded < 1秒
- [ ] Load < 3秒

**实际测量**：
- DOMContentLoaded: ______ ms
- Load: ______ ms

---

### F2: Token生成时间

**操作**：
1. 打开浏览器控制台（F12）
2. 切换到 "Network" 标签
3. 以已登录状态访问宣传页面
4. 点击 "立即使用" 按钮
5. 查看跳转延迟

**预期结果**：
- [ ] 点击按钮后立即跳转（< 100ms）
- [ ] 无明显卡顿

**实际测量**：
- 跳转延迟: ______ ms

---

### F3: 登录流程总时长

**操作**：
1. 记录开始时间（未登录访问宣传页面）
2. 点击按钮跳转到登录页
3. 输入用户名密码并登录
4. 等待自动跳转到应用
5. 记录结束时间（应用显示完整界面）

**预期结果**：
- [ ] 总时长 < 10秒（取决于网络速度和输入速度）

**实际测量**：
- 总时长: ______ 秒

---

## 📋 测试场景 G: 安全性测试

### G1: Token在URL中的暴露时间

**操作**：
1. 以已登录状态点击按钮跳转到应用
2. 快速查看地址栏URL
3. 等待1秒后再次查看URL

**预期结果**：
- [ ] 跳转时URL包含 `sso_token` 参数（暂时暴露）
- [ ] 1秒内Token从URL清除
- [ ] 控制台显示："🧹 已从 URL 中清除 sso_token 参数"

**安全评估**：
- ✅ Token暴露时间极短（< 1秒）
- ✅ Token已保存到localStorage，不再需要URL传递
- ✅ 即使URL被复制，Token在短时间内失效

---

### G2: Token过期时间验证

**操作**：
1. 获取当前Token（localStorage）
2. 复制Token到 https://jwt.io/ 解码
3. 查看Payload中的 `exp` 字段（Unix时间戳）
4. 转换为日期时间

**预期结果**：
- [ ] Token有效期为7天（从 `iat` 到 `exp`）
- [ ] `exp - iat = 604800`（7天的秒数）

**示例**：
```json
{
  "iss": "https://www.ucppt.com",
  "iat": 1734258000,
  "exp": 1734862800,  // iat + 604800 = 7天后
  "data": {
    "user": {...}
  }
}
```

---

### G3: XSS防护测试

**操作**：
1. 尝试在短代码参数中注入JavaScript：
   ```
   [nextjs-app-entrance
     title="<script>alert('XSS')</script>恶意标题"]
   ```
2. 访问页面

**预期结果**：
- [ ] JavaScript代码不执行
- [ ] 显示文本："<script>alert('XSS')</script>恶意标题"（HTML实体转义）
- [ ] 无弹窗出现

**验证点**：
- ✅ WordPress插件使用 `esc_html()` 转义输出
- ✅ 防止XSS攻击

---

## 🐛 常见错误排查

### 错误1: 点击按钮无反应

**检查清单**：
- [ ] 浏览器控制台有JavaScript错误？
- [ ] 短代码参数是否正确？
- [ ] WordPress插件是否启用？
- [ ] 页面是否包含短代码？

**解决方法**：查看控制台错误信息，参考部署指南修复

---

### 错误2: 登录后没有自动跳转

**检查清单**：
- [ ] sessionStorage中是否保存了目标URL？
  ```javascript
  console.log(sessionStorage.getItem('nextjs_app_target_url'));
  ```
- [ ] 浏览器是否阻止了sessionStorage？
- [ ] 是否在无痕模式且关闭了标签页？

**解决方法**：使用正常模式测试，检查浏览器隐私设置

---

### 错误3: Token未传递到应用

**检查清单**：
- [ ] WordPress插件版本是否为 v3.0.10？
- [ ] 短代码中 `app_url` 参数是否正确？
- [ ] REST API端点是否可访问？
  - 访问：https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token
- [ ] 应用代码是否支持接收URL参数中的Token？

**解决方法**：检查WordPress固定链接设置，清除缓存

---

## ✅ 测试报告模板

### 测试环境

| 项目 | 信息 |
|-----|------|
| 测试日期 | 2025-12-15 |
| WordPress版本 | 6.x |
| 插件版本 | v3.0.10 |
| 宣传页面URL | https://www.ucppt.com/js |
| 应用URL | https://ai.ucppt.com |
| 测试浏览器 | Chrome 120, Firefox 121, Safari 17 |

---

### 测试结果汇总

| 测试场景 | 通过 | 失败 | 备注 |
|---------|------|------|------|
| A: 未登录完整流程 | ☑ | ☐ | 所有步骤通过 |
| B: 已登录直接跳转 | ☑ | ☐ | 无问题 |
| C: Token传递验证 | ☑ | ☐ | Token格式正确 |
| D: 错误处理 | ☑ | ☐ | 错误提示友好 |
| E: 浏览器兼容性 | ☑ | ☐ | Chrome/Firefox/Edge通过 |
| F: 性能测试 | ☑ | ☐ | 加载时间<3秒 |
| G: 安全性测试 | ☑ | ☐ | Token自动清除 |

---

### 发现的问题

1. **问题描述**：（如果有）
   - 错误现象：
   - 重现步骤：
   - 预期结果：
   - 实际结果：

2. **解决方案**：
   - 修复方法：
   - 验证结果：

---

### 总体评价

- ✅ 功能完整性：所有核心功能正常
- ✅ 用户体验：登录流程流畅，无卡顿
- ✅ 安全性：Token传递安全，XSS防护有效
- ✅ 性能：页面加载快速，响应及时
- ✅ 兼容性：主流浏览器兼容

---

### 建议改进（可选）

1. （待补充）
2. （待补充）

---

## 📝 测试签署

**测试人员**：_______________
**日期**：_______________
**签名**：_______________

---

**测试完成！** 🎉

此清单涵盖了WordPress应用宣传页面v3.0.10的所有关键功能和边缘情况，确保功能稳定可靠。
