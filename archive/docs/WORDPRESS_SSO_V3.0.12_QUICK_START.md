# WordPress SSO v3.0.12 - 快速开始指南

## 📦 更新包信息

- **文件名**: `nextjs-sso-integration-v3.0.12.zip`
- **大小**: 16,853 bytes (16 KB)
- **版本**: v3.0.12
- **发布日期**: 2025-12-16

---

## 🎯 关键变化（一句话）

**移除iframe嵌入模式，仅保留宣传页面入口（`[nextjs-app-entrance]`短代码）**

---

## ⚡ 3分钟快速部署

### 步骤1: 上传插件（1分钟）

```bash
WordPress后台 → 插件 → 已安装的插件
找到 "Next.js SSO Integration v3" → 停用

插件 → 安装插件 → 上传插件
选择: nextjs-sso-integration-v3.0.12.zip
安装 → 启用插件
```

### 步骤2: 配置页面（1分钟）

```bash
WordPress后台 → 页面 → 编辑 "js" 页面
确认短代码为：
[nextjs-app-entrance app_url="https://ai.ucppt.com?mode=standalone"]

⚠️ 必须包含 app_url 参数！
```

### 步骤3: 清除缓存并测试（1分钟）

```bash
# 清除缓存
设置 → WP Super Cache → 删除缓存
Ctrl + Shift + R（浏览器强制刷新）

# 测试
访问: https://www.ucppt.com/js
点击 "立即使用" 按钮
✅ 应该在新窗口打开应用
✅ 宣传页面保持在原标签页
```

---

## 🔍 验证清单

### 验证1: 版本号
```bash
WordPress后台 → 插件
确认显示 "版本 3.0.12"
```

### 验证2: 控制台日志
按 `F12` 打开控制台，应该看到：
```javascript
[Next.js SSO v3.0.12] 宣传页面脚本已加载
[Next.js SSO v3.0.12] app_url: https://ai.ucppt.com?mode=standalone
```

❌ 如果看到 `[Next.js SSO v3.0.8]`，说明缓存未清除，需要：
1. 清除WordPress缓存
2. 清除浏览器缓存（Ctrl + Shift + Delete）
3. 使用无痕模式测试

### 验证3: 新窗口行为
- ✅ 点击按钮后在新标签页打开应用
- ✅ 宣传页面保持在原标签页
- ✅ 可以同时查看两个页面

---

## ❌ 已移除功能

### iframe嵌入模式（已废弃）
- 短代码 `[nextjs_app]` 已移除
- `/nextjs` 页面不再需要
- 如有旧页面，可以删除

### 如何删除旧页面
```bash
WordPress后台 → 页面 → 查找包含 [nextjs_app] 的页面
移至回收站或永久删除
```

---

## ⚠️ 常见问题

### 问题1: 点击按钮弹窗提示 "应用URL未配置"

**原因**: 短代码缺少 `app_url` 参数

**解决**:
```bash
编辑 "js" 页面
修改短代码为：
[nextjs-app-entrance app_url="https://ai.ucppt.com?mode=standalone"]
更新 → 清除缓存 → 刷新
```

---

### 问题2: 点击按钮弹窗提示 "弹窗被拦截"

**原因**: 浏览器弹窗拦截器阻止

**解决（Chrome）**:
```bash
1. 地址栏右侧会显示弹窗拦截图标
2. 点击 → 选择 "始终允许 www.ucppt.com 的弹出式窗口"
3. 刷新页面重试
```

---

### 问题3: 控制台显示 v3.0.8 而不是 v3.0.12

**原因**: 旧插件仍在缓存中

**解决**:
```bash
1. 确认插件版本为 3.0.12
2. 清除WordPress缓存（WP Super Cache → 删除缓存）
3. 清除浏览器缓存（Ctrl + Shift + Delete）
4. 使用无痕模式测试（Ctrl + Shift + N）
```

---

## 🔧 技术改进

### 1. 按钮实现
- **之前**: `<a href="#">` 标签 + `e.preventDefault()`
- **现在**: `<button type="button">` 标签（无需阻止默认行为）

### 2. 错误处理
- **之前**: 配置错误无提示
- **现在**: 弹窗提示 "应用URL未配置"

### 3. 弹窗拦截检测
- **之前**: 弹窗被拦截无提示
- **现在**: 弹窗提示 "弹窗被拦截！请允许此网站的弹窗"

### 4. 调试日志
- **之前**: 日志稀疏
- **现在**: 详细的控制台日志，便于调试

---

## 📚 完整文档

详细说明请查看: [WORDPRESS_SSO_V3.0.12_SIMPLIFIED_VERSION.md](WORDPRESS_SSO_V3.0.12_SIMPLIFIED_VERSION.md)

---

## ✅ 部署完成确认

部署成功的标志：
- [x] 插件版本显示 v3.0.12
- [x] 控制台显示 `[Next.js SSO v3.0.12]`
- [x] 点击按钮在新窗口打开应用
- [x] 宣传页面保持在原标签页
- [x] Token成功传递到应用
- [x] 应用显示已登录状态

---

**更新完成！** 🎊

现在您的WordPress SSO系统使用简化的单一入口架构！
