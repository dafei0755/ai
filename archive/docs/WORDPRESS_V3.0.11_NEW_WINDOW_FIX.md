# WordPress SSO v3.0.11 - 宣传页面新窗口打开应用

## 📋 更新内容

**版本**：v3.0.11
**发布日期**：2025-12-15
**更新类型**：功能优化

### 核心修改

✅ **宣传页面始终保留**，点击按钮在**新窗口**打开应用
✅ **已登录用户**：点击按钮 → 新窗口打开应用（带Token）
✅ **未登录用户**：登录成功后 → 新窗口打开应用（宣传页面保持在原标签页）

---

## 🎯 用户反馈

**原需求**：
> "https://www.ucppt.com/js 始终保留，点击按钮新开一个窗口打开应用"

**修改前（v3.0.10）**：
- 点击按钮后当前标签页跳转到应用
- 宣传页面被替换，无法返回

**修改后（v3.0.11）**：
- 点击按钮后在新标签页打开应用
- 宣传页面保持在原标签页
- 用户可以同时查看宣传页面和使用应用

---

## 🔧 代码修改

### 修改文件
- `nextjs-sso-integration-v3.php`

### 修改位置

#### 1. 已登录用户跳转逻辑（Line 1398-1399）

**修改前**：
```javascript
console.log('[Next.js App Entrance] 已登录用户跳转到应用:', targetUrl);
window.location.href = targetUrl;
```

**修改后**：
```javascript
console.log('[Next.js App Entrance] 已登录用户在新窗口打开应用:', targetUrl);
window.open(targetUrl, '_blank', 'noopener,noreferrer');
```

#### 2. 未登录用户登录成功后跳转逻辑（Line 1434-1435）

**修改前**：
```javascript
const finalUrl = targetUrl + separator + 'sso_token=' + encodeURIComponent(token);
window.location.href = finalUrl;
```

**修改后**：
```javascript
const finalUrl = targetUrl + separator + 'sso_token=' + encodeURIComponent(token);
window.open(finalUrl, '_blank', 'noopener,noreferrer');
```

#### 3. 代码注释更新

**已登录用户**（Line 1386）：
```javascript
// 已登录用户：点击按钮在新窗口打开应用（带Token）
```

**未登录用户**（Line 1403）：
```javascript
// 未登录用户：跳转到WordPress登录页面，登录后回到此页面，然后再在新窗口打开应用
```

**sessionStorage注释**（Line 1413）：
```javascript
// 将目标应用URL存储到sessionStorage，登录后在新窗口打开
```

**自动打开检测**（Line 1424）：
```javascript
// 检查是否刚从登录页面返回，如果是则在新窗口打开应用
```

**延迟打开注释**（Line 1430）：
```javascript
// 延迟1秒后在新窗口打开，让用户看到登录成功状态
```

---

## 📊 行为对比

### Before (v3.0.10)

#### 已登录用户
```
访问宣传页面 (标签页A)
  ↓
点击"立即使用"按钮
  ↓
❌ 当前标签页跳转到应用
  ↓
宣传页面消失，无法返回
```

#### 未登录用户
```
访问宣传页面 (标签页A)
  ↓
点击"立即使用"按钮
  ↓
跳转到WordPress登录页面（标签页A）
  ↓
输入账号密码，登录成功
  ↓
返回宣传页面（标签页A）
  ↓
1秒后自动跳转到应用（标签页A）
  ↓
❌ 宣传页面被替换，无法返回
```

---

### After (v3.0.11)

#### 已登录用户
```
访问宣传页面 (标签页A)
  ↓
点击"立即使用"按钮
  ↓
✅ 新标签页B打开应用（带Token）
  ↓
✅ 宣传页面保持在标签页A
  ↓
用户可以同时查看两个页面
```

#### 未登录用户
```
访问宣传页面 (标签页A)
  ↓
点击"立即使用"按钮
  ↓
跳转到WordPress登录页面（标签页A）
  ↓
输入账号密码，登录成功
  ↓
返回宣传页面（标签页A）
  ↓
1秒后在新标签页B打开应用（带Token）
  ↓
✅ 宣传页面保持在标签页A
  ↓
用户可以同时查看两个页面
```

---

## 🧪 测试验证

### 测试场景1: 已登录用户点击按钮

**操作步骤**：
1. 确保已在WordPress登录
2. 访问：`https://www.ucppt.com/js`
3. 点击 "立即使用 →" 按钮

**预期结果**：
- ✅ 新标签页打开应用
- ✅ 应用显示已登录状态
- ✅ Token成功传递到应用
- ✅ 宣传页面保持在原标签页
- ✅ 可以随时返回宣传页面

**检查控制台**（宣传页面标签页）：
```javascript
[Next.js App Entrance] 已登录用户在新窗口打开应用: https://ai.ucppt.com?mode=standalone&sso_token=...
```

**检查localStorage**（应用标签页）：
```javascript
console.log('Token:', localStorage.getItem('wp_jwt_token'));
console.log('User:', localStorage.getItem('wp_jwt_user'));
// 应该有值
```

---

### 测试场景2: 未登录用户完整流程

**操作步骤**：
1. 退出WordPress登录（或使用无痕模式）
2. 访问：`https://www.ucppt.com/js`
3. 点击 "立即使用 →" 按钮
4. 跳转到WordPress登录页面，输入账号密码
5. 登录成功后自动返回宣传页面
6. **等待1秒**

**预期结果**：
- ✅ 登录成功后返回宣传页面（原标签页A）
- ✅ 宣传页面显示 "✓ 您已登录为 XXX"
- ✅ 1秒后自动在新标签页B打开应用
- ✅ 应用显示已登录状态
- ✅ Token成功传递到应用
- ✅ 宣传页面保持在标签页A

**检查控制台**（宣传页面标签页）：
```javascript
[Next.js App Entrance] 检测到登录成功，在新窗口打开应用: https://ai.ucppt.com?mode=standalone
```

---

### 测试场景3: 多次点击按钮

**操作步骤**：
1. 以已登录状态访问宣传页面
2. 点击 "立即使用" 按钮（第1次）
3. 等待应用打开后，返回宣传页面标签页
4. 再次点击 "立即使用" 按钮（第2次）
5. 再次点击（第3次）

**预期结果**：
- ✅ 每次点击都在新标签页打开应用
- ✅ 可以同时打开多个应用标签页
- ✅ 宣传页面始终保持在原标签页
- ✅ 每个应用标签页都有独立的Token

**浏览器行为**：
- 浏览器可能会阻止弹窗（如果点击过快）
- 建议在浏览器设置中允许 `www.ucppt.com` 的弹窗

---

## 🔒 安全特性

### 1. window.open 安全参数

```javascript
window.open(targetUrl, '_blank', 'noopener,noreferrer');
```

**参数说明**：
- `'_blank'`: 在新标签页打开
- `'noopener'`: 防止新页面通过 `window.opener` 访问原页面
- `'noreferrer'`: 防止新页面获取原页面的 referrer 信息

**安全优势**：
- ✅ 防止 Tabnabbing 攻击（新页面篡改原页面）
- ✅ 防止 referrer 信息泄露
- ✅ 遵循Web安全最佳实践

### 2. Token传递安全

Token传递方式保持不变（v3.0.10的安全特性）：
- ✅ Token在URL中传递（暴露时间 < 1秒）
- ✅ 应用接收后立即保存到localStorage
- ✅ URL中的Token自动清除
- ✅ Token有过期时间（7天）

---

## 📈 用户体验提升

### Before (v3.0.10)

**问题**：
- ❌ 点击按钮后宣传页面消失
- ❌ 用户无法返回查看应用介绍
- ❌ 想再次分享宣传页面需要重新输入URL

**用户反馈**：
> "希望宣传页面始终保留，方便用户查看和分享"

### After (v3.0.11)

**优势**：
- ✅ 宣传页面始终保留，可以随时返回
- ✅ 用户可以同时查看宣传页面和使用应用
- ✅ 方便多次打开应用（例如：测试不同账号）
- ✅ 方便分享宣传页面（URL不变）
- ✅ 符合Web应用的常见交互模式

**典型场景**：
1. 用户访问宣传页面了解应用功能
2. 点击按钮在新窗口打开应用试用
3. 试用过程中遇到问题，返回宣传页面查看帮助文档
4. 关闭应用标签页，宣传页面仍然保持

---

## 🚀 部署步骤

### 步骤1: 停用旧插件

```bash
WordPress后台 → 插件 → 已安装的插件
找到 "Next.js SSO Integration v3"
点击 "停用"
```

### 步骤2: 上传新插件

```bash
WordPress后台 → 插件 → 安装插件 → 上传插件
选择文件: nextjs-sso-integration-v3.0.11.zip (16,521 bytes)
点击 "现在安装"
安装完成后点击 "启用插件"
```

### 步骤3: 验证版本

```bash
WordPress后台 → 插件 → 已安装的插件
确认显示：
- 名称：Next.js SSO Integration v3
- 版本：3.0.11
- 描述：WordPress 单点登录集成 Next.js（v3.0.11 - 宣传页面新窗口打开应用）
```

### 步骤4: 清除缓存

```bash
# WordPress缓存
WordPress后台 → 设置 → WP Super Cache → 删除缓存

# 浏览器缓存
Ctrl + Shift + R (强制刷新)
```

### 步骤5: 测试验证

按照上面的"测试验证"章节执行所有测试场景。

---

## ⚠️ 注意事项

### 1. 浏览器弹窗拦截

**现象**：点击按钮后没有打开新标签页

**原因**：浏览器弹窗拦截器阻止了 `window.open()`

**解决方法**：
```bash
# Chrome
1. 地址栏右侧会显示弹窗被拦截的图标
2. 点击图标 → 允许 www.ucppt.com 的弹窗
3. 或在浏览器设置中添加白名单

# Firefox
设置 → 隐私与安全 → 权限 → 弹出窗口
添加例外：https://www.ucppt.com

# Safari
偏好设置 → 网站 → 弹出式窗口
对于 www.ucppt.com，选择 "允许"
```

### 2. 多个应用标签页

**现象**：多次点击按钮后打开了多个应用标签页

**说明**：这是正常行为，用户可以手动关闭不需要的标签页

**优化建议**（可选）：
- 可以在代码中添加逻辑检测已打开的应用标签页
- 如果已有应用标签页打开，则激活该标签页而不是打开新的
- 但这需要使用 Broadcast Channel API 或 SharedWorker，增加复杂度

### 3. sessionStorage在新窗口中的行为

**说明**：
- `sessionStorage` 在新窗口中是独立的
- 登录流程的状态保持仍然在原标签页中
- 因此登录成功后返回原标签页，然后在新窗口打开应用

---

## 🐛 故障排查

### 问题1: 点击按钮后没有打开新窗口

**排查步骤**：
1. 检查浏览器控制台是否有JavaScript错误
2. 检查浏览器弹窗拦截器是否阻止
3. 尝试在其他浏览器中测试

**解决方法**：
- 允许 www.ucppt.com 的弹窗
- 清除浏览器缓存并刷新

---

### 问题2: 新窗口打开但没有Token

**排查步骤**：
```javascript
// 应用标签页控制台执行
console.log('Token:', localStorage.getItem('wp_jwt_token'));
console.log('User:', localStorage.getItem('wp_jwt_user'));
```

**可能原因**：
- Token生成失败
- URL参数未正确附加
- 应用前端未正确接收Token

**解决方法**：
1. 检查WordPress插件版本是否为 v3.0.11
2. 检查REST API端点：`/wp-json/nextjs-sso/v1/get-token`
3. 清除所有缓存

---

### 问题3: 宣传页面仍然跳转（未保留）

**排查步骤**：
1. 检查WordPress插件版本是否为 v3.0.11
2. 查看浏览器控制台日志
3. 确认日志包含 "在新窗口打开应用"

**解决方法**：
- 确认插件已更新到 v3.0.11
- 清除WordPress缓存（WP Super Cache）
- 清除浏览器缓存（Ctrl + Shift + R）
- 使用无痕模式测试

---

## 📚 相关文档

- [WORDPRESS_V3.0.10_README.md](WORDPRESS_V3.0.10_README.md) - v3.0.10功能介绍
- [WORDPRESS_ENTRANCE_PAGE_GUIDE_V3.0.10.md](WORDPRESS_ENTRANCE_PAGE_GUIDE_V3.0.10.md) - 完整部署指南
- [WORDPRESS_ENTRANCE_PAGE_TEST_CHECKLIST_V3.0.10.md](WORDPRESS_ENTRANCE_PAGE_TEST_CHECKLIST_V3.0.10.md) - 测试清单

---

## ✅ 验收标准

**全部通过以下检查，即表示更新成功**：

### 功能验收
- [ ] WordPress插件版本为 v3.0.11
- [ ] 插件描述包含："宣传页面新窗口打开应用"
- [ ] 已登录用户点击按钮在新窗口打开应用
- [ ] 宣传页面保持在原标签页
- [ ] 未登录用户登录成功后在新窗口打开应用
- [ ] Token成功传递到应用
- [ ] 应用显示已登录状态

### 日志验收
- [ ] 控制台显示："已登录用户在新窗口打开应用"
- [ ] 控制台显示："检测到登录成功，在新窗口打开应用"
- [ ] 无JavaScript错误

### 用户体验验收
- [ ] 宣传页面始终保留
- [ ] 可以多次点击按钮打开应用
- [ ] 可以随时返回宣传页面
- [ ] 浏览器标签页管理清晰

---

## 🎉 总结

**v3.0.11 核心改进**：
- ✅ 宣传页面始终保留，用户体验更好
- ✅ 新窗口打开应用，符合Web应用常见交互
- ✅ 安全特性保持不变（noopener + noreferrer）
- ✅ Token传递机制保持不变

**用户体验提升**：
- 🚀 可以同时查看宣传页面和使用应用
- 🚀 方便返回查看应用介绍和帮助文档
- 🚀 方便分享宣传页面（URL不变）
- 🚀 支持多次打开应用（测试不同账号）

**技术优势**：
- 代码修改最小化（仅2处关键修改）
- 安全性提升（noopener + noreferrer）
- 向后兼容（不影响其他功能）
- 符合Web标准和最佳实践

---

**更新完成！** 🎊

现在宣传页面会始终保留，点击按钮在新窗口打开应用！
