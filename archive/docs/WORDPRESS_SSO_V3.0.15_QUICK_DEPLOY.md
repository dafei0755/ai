# v3.0.15 快速部署指南

## ⚡ 1分钟部署

### 步骤1: 部署WordPress插件
```bash
1. WordPress后台 → 插件 → 停用旧插件
2. 插件 → 上传插件 → nextjs-sso-integration-v3.0.15.zip → 安装 → 启用
3. 设置 → WP Super Cache → 删除缓存
4. 浏览器：Ctrl + Shift + R（强制刷新）
```

### 步骤2: 部署Next.js应用
```bash
cd frontend-nextjs

# 确认修改
git status

# 看到修改的文件：
# - app/page.tsx
# - contexts/AuthContext.tsx

# 重启开发服务器
npm run dev
```

### 步骤3: 启动Python后端
```bash
cd d:\11-20\langgraph-design
python -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000
```

---

## ✅ 10秒快速测试

### 测试：已登录用户流程

```
1. 确保已通过WPCOM登录（右上角显示用户名）
2. 访问：https://www.ucppt.com/js
3. 按 F12 → Console 标签
4. 点击"立即使用"按钮
5. 观察新窗口
```

**成功标志**:
```javascript
[Next.js SSO v3.0.15] 在新窗口打开应用
[AuthContext] ✅ REST API Token 验证成功
[AuthContext] 🔀 检测到已登录，跳转到分析页面
```

- [x] 新窗口自动跳转到 `/analysis`
- [x] **不显示登录界面**（关键！）
- [x] 显示应用主界面

---

## 🎯 核心变化（与v3.0.14对比）

| 项目 | v3.0.14 | v3.0.15 |
|------|---------|---------|
| **宣传页按钮** | REST API检测 → 打开应用 | 直接打开应用 |
| **应用首页** | 3种模式选择 | 简洁登录界面 |
| **登录检测** | 宣传页检测 | 应用内检测 |
| **已登录行为** | Token传递 → 显示主界面 | REST API → 跳转 `/analysis` |
| **职责分离** | 混合 | 清晰（宣传/应用） |

---

## 🐛 快速诊断

### 问题：已登录但仍显示登录界面

**检查**:
```javascript
// 在应用控制台执行
fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token', {
    credentials: 'include'
}).then(r => r.json()).then(console.log);

// 预期：{success: true, token: "...", user: {...}}
// 如果返回 401：WPCOM登录未被识别
```

---

### 问题：Python后端未运行

**症状**: 控制台显示"Token 验证状态: 500"

**解决**:
```bash
# 启动后端
python -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000

# 检查健康状态
curl http://127.0.0.1:8000/health
```

---

## 📄 完整文档

如果部署失败，请查看：
- [WORDPRESS_SSO_V3.0.15_IMPLEMENTATION_COMPLETE.md](WORDPRESS_SSO_V3.0.15_IMPLEMENTATION_COMPLETE.md) - 完整实施文档

---

## 🎉 成功标志

**v3.0.15 部署成功的标志**:

✅ 宣传页面控制台显示 `[Next.js SSO v3.0.15]`
✅ 已登录用户点击按钮 → 新窗口打开 → 自动跳转 `/analysis`
✅ 未登录用户看到"立即登录"按钮 → 点击 → 跳转 `/login`
✅ 登录后返回应用 → 自动跳转 `/analysis`

---

**v3.0.15 快速部署完成！** 🚀

**最后更新**: 2025-12-16
**部署时间**: < 1 分钟
**测试时间**: < 10 秒
