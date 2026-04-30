# 🧪 SSO同步修复测试指南 v3.0.22

**测试版本：** v3.0.22
**测试日期：** 2025-12-17

---

## 📋 准备工作

### 1. 重启Next.js应用

```bash
# 在 frontend-nextjs 目录下
cd frontend-nextjs

# 停止当前服务（Ctrl+C）
# 重新启动
npm run dev
```

### 2. 清除浏览器缓存（仅首次）

打开浏览器开发者工具（F12），在Console执行：

```javascript
localStorage.clear();
location.reload();
```

---

## 🧪 测试场景1：用户切换同步

### 步骤：

1. **登录用户A（宋词）**
   ```
   访问：https://www.ucppt.com/login
   账号：宋词 (42841287@qq.com)
   ```

2. **进入Next.js应用**
   ```
   访问：http://localhost:3000
   或点击WordPress网站的"立即开始分析"按钮
   ```

3. **验证用户显示**
   - 查看左下角用户头像
   - 应显示：宋词 (42841287@qq.com) ✅

4. **切换到用户B（2751）**
   ```
   1. 返回 https://www.ucppt.com
   2. 点击右上角头像 → 退出登录
   3. 重新登录2751账号
   ```

5. **再次进入Next.js应用**
   ```
   方式1：直接切换到Next.js标签页（立即触发检测）
   方式2：点击WordPress的"立即开始分析"按钮
   ```

6. **等待自动同步**
   - ⏱️ 最多等待10秒
   - 查看浏览器Console日志

### ✅ 预期结果：

**Console日志：**
```
[AuthContext v3.0.22] ⚠️ 检测到用户切换
[AuthContext v3.0.22] 本地用户ID: 42841287 → WordPress用户ID: 2751
[AuthContext v3.0.22] ✅ 成功获取新用户Token
[AuthContext v3.0.22] 新用户: {user_id: 2751, username: "2751", ...}
```

**页面自动刷新**，显示新用户：2751 ✅

---

## 🧪 测试场景2：退出登录同步

### 步骤：

1. **确保已登录**
   - Next.js应用显示当前用户

2. **在WordPress退出登录**
   ```
   访问：https://www.ucppt.com
   点击：右上角头像 → 退出登录
   ```

3. **返回Next.js应用**
   - 切换到Next.js标签页
   - 或刷新Next.js页面

4. **等待自动同步**
   - ⏱️ 最多等待10秒

### ✅ 预期结果：

**Console日志：**
```
[AuthContext v3.0.22] ✅ 检测到WordPress已退出，清除本地Token
```

**页面显示：** 登录提示或跳转到登录页面 ✅

---

## 🧪 测试场景3：跨标签页同步

### 步骤：

1. **打开两个Next.js标签页**
   ```
   标签页A：http://localhost:3000
   标签页B：http://localhost:3000
   ```

2. **在WordPress切换用户**
   ```
   在第三个标签页：https://www.ucppt.com
   退出当前用户，登录新用户
   ```

3. **切换到标签页A**
   - ⏱️ 等待10秒
   - 查看用户信息是否更新

4. **切换到标签页B**
   - ⏱️ 等待10秒
   - 查看用户信息是否更新

### ✅ 预期结果：

**两个标签页都应该：**
- 在10秒内检测到用户切换
- 自动刷新并显示新用户 ✅

---

## 🧪 测试场景4：长时间停留

### 步骤：

1. **登录用户A，进入Next.js应用**
   - 停留在Next.js页面，不切换标签页

2. **在另一个标签页切换WordPress用户**
   - 退出用户A，登录用户B
   - 不要切换回Next.js标签页

3. **等待10秒**
   - Next.js应用会自动检测（定期轮询）

4. **查看Next.js页面**
   - 应该自动刷新并显示新用户

### ✅ 预期结果：

**即使不切换标签页，10秒后：**
- Console出现检测日志
- 页面自动刷新
- 显示新用户 ✅

---

## 🐛 问题排查

### 问题1：10秒后仍未同步

**检查项：**
1. 确认Next.js应用已重启（npm run dev）
2. 确认浏览器已清除缓存（localStorage.clear()）
3. 查看Console是否有错误日志

**手动触发同步：**
```javascript
// 在Console执行
const resync = async () => {
  const res = await fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token', {
    method: 'GET',
    credentials: 'include'
  });
  const data = await res.json();
  console.log('Token:', data);
  if (data.token) {
    localStorage.setItem('wp_jwt_token', data.token);
    localStorage.setItem('wp_jwt_user', JSON.stringify(data.user));
    location.reload();
  }
};
resync();
```

---

### 问题2：Console没有日志

**可能原因：**
- AuthContext未加载
- Next.js版本不是v3.0.22

**验证版本：**
```javascript
// 在Console执行
console.log('Version:', document.querySelector('[data-version]')?.dataset.version);
```

**手动检查代码：**
```bash
# 查看AuthContext.tsx Line 62
grep -n "v3.0.22" frontend-nextjs/contexts/AuthContext.tsx
```

---

### 问题3：CORS错误

**错误信息：**
```
Access to fetch at 'https://www.ucppt.com/...' has been blocked by CORS policy
```

**解决方案：**
1. 确认WordPress CORS配置（nextjs-sso-integration插件）
2. 确认请求包含 `credentials: 'include'`

**验证CORS：**
```javascript
// 在Console执行
fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/sync-status', {
  method: 'GET',
  credentials: 'include'
})
.then(res => res.json())
.then(data => console.log('✅ CORS正常:', data))
.catch(err => console.error('❌ CORS错误:', err));
```

---

## 📊 测试检查清单

### 启动前：
- [ ] Next.js应用已重启（npm run dev）
- [ ] 浏览器缓存已清除（localStorage.clear()）
- [ ] 浏览器Console已打开（F12）

### 测试中：
- [ ] 场景1：用户切换同步（10秒内） ✅
- [ ] 场景2：退出登录同步（10秒内） ✅
- [ ] 场景3：跨标签页同步（10秒内） ✅
- [ ] 场景4：长时间停留同步（10秒内） ✅

### 验证项：
- [ ] Console出现 `[AuthContext v3.0.22]` 日志 ✅
- [ ] 用户信息自动更新 ✅
- [ ] 页面自动刷新 ✅
- [ ] 无CORS错误 ✅
- [ ] 无其他JavaScript错误 ✅

---

## 🎯 成功标准

**所有测试场景都应该：**
1. ✅ 在10秒内检测到WordPress用户变化
2. ✅ 自动调用get-token API获取新Token
3. ✅ 自动刷新页面并显示新用户
4. ✅ Console出现清晰的日志信息
5. ✅ 无任何JavaScript错误

**如果所有测试通过，v3.0.22修复成功！🎉**

---

## 📝 测试报告模板

```markdown
## SSO同步测试报告

**测试版本：** v3.0.22
**测试日期：** 2025-12-17
**测试人员：** [您的名字]

### 测试结果：
- [ ] 场景1：用户切换同步 - ✅ 通过 / ❌ 失败
- [ ] 场景2：退出登录同步 - ✅ 通过 / ❌ 失败
- [ ] 场景3：跨标签页同步 - ✅ 通过 / ❌ 失败
- [ ] 场景4：长时间停留同步 - ✅ 通过 / ❌ 失败

### 备注：
[记录任何问题或观察]

### 总结：
- ✅ 所有测试通过，修复成功
- ⚠️ 部分测试失败，需要进一步调查
```

---

**祝测试顺利！如有问题，请查看 [SSO_SYNC_TROUBLESHOOTING_GUIDE.md](SSO_SYNC_TROUBLESHOOTING_GUIDE.md)**
