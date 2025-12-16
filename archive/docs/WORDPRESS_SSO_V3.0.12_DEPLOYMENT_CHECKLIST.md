# WordPress SSO v3.0.12 - 部署验收清单

## 📦 部署包信息

✅ **插件包已准备**：
- 文件名：`nextjs-sso-integration-v3.0.12.zip`
- 大小：16,853 bytes (16 KB)
- 版本：v3.0.12
- 发布时间：2025-12-16 09:03

---

## 📋 部署前准备

### 检查清单

- [ ] 已备份当前WordPress插件（v3.0.8 或其他版本）
- [ ] 已备份 `/js` 页面内容
- [ ] 已记录当前短代码配置
- [ ] 已确认应用URL：`https://ai.ucppt.com?mode=standalone`

---

## 🚀 部署步骤（按顺序执行）

### 步骤1: 停用旧插件 ✓

```bash
WordPress后台 → 插件 → 已安装的插件
找到 "Next.js SSO Integration v3"
点击 "停用"

验收标准：
- [ ] 插件状态显示为 "已停用"
- [ ] 页面无错误提示
```

---

### 步骤2: 上传新插件 ✓

```bash
插件 → 安装插件 → 上传插件
选择文件: nextjs-sso-integration-v3.0.12.zip (16,853 bytes)
点击 "现在安装"

验收标准：
- [ ] 安装进度条显示100%
- [ ] 显示 "插件安装成功"
```

---

### 步骤3: 启用插件 ✓

```bash
安装完成页面 → 点击 "启用插件"

验收标准：
- [ ] 跳转到插件列表页面
- [ ] 插件状态显示为 "已启用"
- [ ] 插件描述显示：
      "WordPress 单点登录集成 Next.js（v3.0.12 - 简化版：仅保留宣传页面入口）"
```

---

### 步骤4: 验证插件版本 ✓

```bash
WordPress后台 → 插件 → 已安装的插件
找到 "Next.js SSO Integration v3"

验收标准：
- [ ] 版本号显示：3.0.12
- [ ] 作者：UCPPT Team
- [ ] 描述包含："v3.0.12 - 简化版：仅保留宣传页面入口"
```

---

### 步骤5: 检查插件设置页面 ✓

```bash
WordPress后台 → 设置 → Next.js SSO v3

验收标准：
- [ ] 设置页面可以正常打开
- [ ] 显示成功消息："🎉 v3.0 全新版本已激活！"
- [ ] 配置检查清单显示 ✓ PYTHON_JWT_SECRET 已配置
- [ ] 配置检查清单显示 ✓ 回调URL已配置
```

---

### 步骤6: 配置宣传页面 ✓

```bash
WordPress后台 → 页面 → 找到 "js" 页面 → 编辑

当前短代码（检查）：
[现有的短代码内容]

修改为（如果不正确）：
[nextjs-app-entrance app_url="https://ai.ucppt.com?mode=standalone"]

验收标准：
- [ ] 短代码已更新
- [ ] 包含 app_url 参数
- [ ] app_url 值为：https://ai.ucppt.com?mode=standalone
- [ ] 点击 "更新" 保存修改
```

**完整自定义版本（可选）**：
```
[nextjs-app-entrance
  app_url="https://ai.ucppt.com?mode=standalone"
  title="AI 设计高参"
  subtitle="极致概念 · 智能设计助手"
  description="基于多智能体协作的专业设计分析系统，为您的设计项目提供全方位的专家级建议。"
  button_text="立即使用"
  features="多专家协作分析|智能需求理解|专业设计建议|支持多模态输入"]
```

---

### 步骤7: 删除旧的iframe页面（如果存在）✓

```bash
WordPress后台 → 页面 → 查找包含 [nextjs_app] 短代码的页面

可能的页面名称：
- "nextjs"
- "应用嵌入"
- 其他包含iframe的页面

操作：
移至回收站或永久删除

验收标准：
- [ ] 所有使用 [nextjs_app] 短代码的页面已删除
- [ ] 页面列表中不再有iframe嵌入页面
```

---

### 步骤8: 清除WordPress缓存 ✓

```bash
WordPress后台 → 设置 → WP Super Cache → 删除缓存
（如果没有WP Super Cache插件，跳过此步骤）

验收标准：
- [ ] 显示 "缓存已清除" 确认消息
- [ ] 无错误提示
```

**其他缓存插件**：
- W3 Total Cache: Performance → Dashboard → Empty All Caches
- WP Rocket: Settings → Clear Cache
- LiteSpeed Cache: Dashboard → Purge All

---

### 步骤9: 清除浏览器缓存 ✓

```bash
方法1: 强制刷新
Ctrl + Shift + R (Windows/Linux)
Cmd + Shift + R (Mac)

方法2: 清除所有缓存
Ctrl + Shift + Delete
选择 "缓存的图像和文件"
点击 "清除数据"

验收标准：
- [ ] 缓存已清除
- [ ] 页面已刷新
```

---

### 步骤10: 首次访问测试 ✓

```bash
访问: https://www.ucppt.com/js
（以已登录状态访问）

验收标准：
- [ ] 页面正常显示（无空白页）
- [ ] 显示标题："AI 设计高参"
- [ ] 显示按钮："立即使用 →"
- [ ] 显示登录状态："✓ 您已登录为 XXX，点击按钮直接进入应用"
- [ ] 显示4个特性卡片
- [ ] 页面样式正常（渐变背景、卡片阴影）
```

---

## 🧪 功能测试

### 测试1: 浏览器控制台验证 ✓

```bash
在 https://www.ucppt.com/js 页面：
按 F12 打开控制台 → 切换到 Console 标签

验收标准：
- [ ] 显示：[Next.js SSO v3.0.12] 宣传页面脚本已加载
- [ ] 显示：[Next.js SSO v3.0.12] 已找到已登录用户按钮
- [ ] 显示：[Next.js SSO v3.0.12] app_url: https://ai.ucppt.com?mode=standalone
- [ ] 无红色错误信息
- [ ] 无 JavaScript 异常
```

❌ **如果看到 `[Next.js SSO v3.0.8]` 或其他旧版本号**：
- 说明缓存未完全清除
- 返回步骤8、步骤9重新清除缓存
- 尝试使用无痕模式测试

---

### 测试2: 已登录用户点击按钮 ✓

```bash
确保已在WordPress登录
访问: https://www.ucppt.com/js
点击 "立即使用 →" 按钮

观察浏览器行为：

验收标准：
- [ ] 新标签页打开（不是当前标签页跳转）
- [ ] 新标签页URL：https://ai.ucppt.com?mode=standalone&sso_token=...
- [ ] 宣传页面保持在原标签页（没有消失）
- [ ] 控制台显示：[Next.js SSO v3.0.12] 在新窗口打开应用: ...
- [ ] 应用加载完成后显示已登录状态
- [ ] 应用显示用户头像和用户名
```

**Token验证（在应用标签页的控制台）**：
```javascript
console.log('Token:', localStorage.getItem('wp_jwt_token'));
console.log('User:', localStorage.getItem('wp_jwt_user'));

验收标准：
- [ ] Token有值（不是null）
- [ ] User有值（包含用户信息JSON）
- [ ] URL中的 sso_token 参数已自动清除
```

---

### 测试3: 未登录用户完整流程 ✓

```bash
步骤1: 退出WordPress登录
WordPress后台 → 右上角 → 登出

步骤2: 访问宣传页面
访问: https://www.ucppt.com/js

验收标准：
- [ ] 页面正常显示
- [ ] 显示："请先登录以使用应用 · 登录后将自动跳转"
- [ ] 按钮显示："立即使用 →"

步骤3: 点击按钮
点击 "立即使用 →" 按钮

验收标准：
- [ ] 当前标签页跳转到WordPress登录页
- [ ] 登录页面URL包含：?redirect_to=https://www.ucppt.com/js

步骤4: 登录
输入用户名和密码 → 点击登录

验收标准：
- [ ] 登录成功
- [ ] 自动返回宣传页面（https://www.ucppt.com/js）
- [ ] 宣传页面显示："✓ 您已登录为 XXX"

步骤5: 自动跳转
等待约1秒

验收标准：
- [ ] 自动在新标签页打开应用
- [ ] 新标签页URL包含 sso_token 参数
- [ ] 宣传页面保持在原标签页
- [ ] 应用显示已登录状态
```

---

### 测试4: 多次点击按钮 ✓

```bash
以已登录状态访问: https://www.ucppt.com/js
点击 "立即使用" 按钮 3次

验收标准：
- [ ] 每次点击都在新标签页打开应用
- [ ] 可以同时打开多个应用标签页
- [ ] 宣传页面始终保持在原标签页
- [ ] 每个应用标签页都有独立的Token
- [ ] 每个应用标签页都显示已登录状态
```

---

### 测试5: 浏览器弹窗拦截测试 ✓

```bash
如果浏览器默认拦截弹窗：

验收标准：
- [ ] 控制台显示：[Next.js SSO v3.0.12] 新窗口被浏览器拦截
- [ ] 弹窗提示："弹窗被拦截！请允许此网站的弹窗，然后重试。"
- [ ] 地址栏右侧显示弹窗拦截图标（Chrome）

解决方法：
1. 点击地址栏右侧的弹窗拦截图标
2. 选择 "始终允许 www.ucppt.com 的弹出式窗口"
3. 刷新页面
4. 再次点击按钮
5. 应该成功打开新窗口
```

---

### 测试6: 配置错误检测 ✓

```bash
模拟配置错误（仅用于测试）：
WordPress后台 → 页面 → 编辑 "js" 页面
临时修改短代码为：
[nextjs-app-entrance]
（删除 app_url 参数）
更新 → 清除缓存 → 刷新页面

验收标准：
- [ ] 点击按钮后弹窗提示："错误：应用URL未配置。请在短代码中添加 app_url 参数。"
- [ ] 控制台显示：[Next.js SSO v3.0.12] 错误：app_url 未配置
- [ ] 不会打开新窗口

测试完成后恢复：
[nextjs-app-entrance app_url="https://ai.ucppt.com?mode=standalone"]
更新 → 清除缓存 → 刷新页面
```

---

## ✅ 最终验收

### 所有测试通过确认

- [ ] 插件版本为 v3.0.12
- [ ] 控制台显示 `[Next.js SSO v3.0.12]`
- [ ] 已登录用户点击按钮在新窗口打开应用
- [ ] 未登录用户登录后在新窗口打开应用
- [ ] 宣传页面始终保持在原标签页
- [ ] Token成功传递到应用
- [ ] 应用显示已登录状态
- [ ] 配置错误有弹窗提示
- [ ] 弹窗拦截有提示
- [ ] 旧的iframe页面已删除

---

## 📊 常见问题排查

### 问题1: 控制台显示旧版本号（v3.0.8）

**原因**：缓存未完全清除

**解决**：
```bash
1. WordPress后台 → 设置 → WP Super Cache → 删除缓存
2. 浏览器：Ctrl + Shift + Delete → 清除缓存
3. 使用无痕模式测试：Ctrl + Shift + N
4. 检查插件列表确认版本为 v3.0.12
5. 如有服务器端缓存（Nginx/CDN），也需要清除
```

---

### 问题2: 点击按钮后弹窗提示"应用URL未配置"

**原因**：短代码缺少 `app_url` 参数

**解决**：
```bash
WordPress后台 → 页面 → 编辑 "js" 页面
确认短代码为：
[nextjs-app-entrance app_url="https://ai.ucppt.com?mode=standalone"]
更新 → 清除缓存 → 刷新
```

---

### 问题3: 点击按钮后弹窗提示"弹窗被拦截"

**原因**：浏览器弹窗拦截器

**解决（Chrome）**：
```bash
1. 地址栏右侧点击弹窗拦截图标
2. 选择 "始终允许 www.ucppt.com 的弹出式窗口"
3. 刷新页面重试
```

**解决（Firefox）**：
```bash
设置 → 隐私与安全 → 权限 → 弹出窗口
添加例外：https://www.ucppt.com
选择 "允许"
```

---

### 问题4: 新窗口打开但应用未显示登录

**排查**：
```bash
在应用标签页的控制台执行：
console.log('Token:', localStorage.getItem('wp_jwt_token'));
console.log('User:', localStorage.getItem('wp_jwt_user'));

如果都是null：
1. 检查URL是否包含 sso_token 参数
2. 检查Next.js应用的Token接收逻辑
3. 检查WordPress REST API: /wp-json/nextjs-sso/v1/get-token
4. 检查 wp-config.php 中的 PYTHON_JWT_SECRET 配置
```

---

### 问题5: 页面显示空白或布局错误

**排查**：
```bash
按 F12 → Console 标签 → 查看错误

常见错误：
- "Uncaught SyntaxError" → 可能是缓存问题
- "Failed to load resource" → 可能是主题CSS冲突
- "Mixed Content" → HTTP/HTTPS混合内容问题

解决：
1. 清除所有缓存
2. 禁用其他插件测试
3. 切换到默认主题测试
4. 检查浏览器控制台的详细错误信息
```

---

## 📞 技术支持

**文档资源**：
- 快速开始：[WORDPRESS_SSO_V3.0.12_QUICK_START.md](WORDPRESS_SSO_V3.0.12_QUICK_START.md)
- 完整指南：[WORDPRESS_SSO_V3.0.12_SIMPLIFIED_VERSION.md](WORDPRESS_SSO_V3.0.12_SIMPLIFIED_VERSION.md)
- 版本日志：[WORDPRESS_SSO_V3_CHANGELOG.md](WORDPRESS_SSO_V3_CHANGELOG.md)
- 调试指南：[DEBUG_ENTRANCE_PAGE.md](DEBUG_ENTRANCE_PAGE.md)

**问题反馈**：
1. 完成本清单的所有步骤
2. 记录失败步骤的截图和错误信息
3. 提供浏览器控制台日志
4. 联系技术支持团队

---

## 🎉 部署成功！

如果所有测试都通过，恭喜您！v3.0.12 已成功部署！

**后续工作**：
- [ ] 监控生产环境运行状况
- [ ] 收集用户反馈
- [ ] 如有问题，参考故障排查章节

---

**清单最后更新**: 2025-12-16
**插件版本**: v3.0.12
**部署环境**: 生产环境（https://www.ucppt.com）
