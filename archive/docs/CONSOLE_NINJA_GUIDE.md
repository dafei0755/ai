# Console Ninja 使用指南

## 📍 日志查看位置

### 1. VSCode 输出面板（主要方式）

**步骤:**
```
1. 按 Ctrl + J (打开底部面板)
2. 点击 "输出" 标签
3. 右上角下拉菜单 → 选择 "Console Ninja"
4. 所有浏览器日志会实时显示在这里！
```

**截图位置示意:**
```
┌────────────────────────────────────────┐
│  VSCode 窗口                            │
│  ┌──────────────────────────────────┐  │
│  │  代码编辑器区域                    │  │
│  │                                    │  │
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │ [问题] [输出▼] [调试控制台] [终端]│  │ ← 点击"输出"
│  │                                    │  │
│  │  下拉菜单: [Console Ninja ▼]      │  │ ← 选择这个
│  │                                    │  │
│  │  🎯 [AuthContext] 尝试获取Token   │  │ ← 日志显示在这里
│  │  ✅ [AuthContext] Token验证成功    │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
```

### 2. 代码内联显示（实时反馈）

Console Ninja会在代码行旁边显示日志值：

```typescript
// frontend-nextjs/contexts/AuthContext.tsx

console.log('[AuthContext] 尝试获取Token');
// 👈 运行后，这里会显示: "尝试获取Token"

const token = data.token;
console.log('[AuthContext] Token:', token);
// 👈 这里会显示: "Token: eyJ0eXAiOiJKV1..."
```

### 3. Console Ninja 专用窗口

**打开方式:**
- `Ctrl + Shift + P`
- 输入: `Console Ninja`
- 选择: `Console Ninja: Show Output`

## 🔧 配置检查

### 确认 Console Ninja 已安装

**方法1: 扩展列表**
```
1. 按 Ctrl + Shift + X (打开扩展)
2. 搜索 "Console Ninja"
3. 确认已安装并启用
```

**方法2: 命令行**
```bash
code --list-extensions | findstr console-ninja
```

应该看到: `WallabyJs.console-ninja`

### 启用 Console Ninja

在 `.vscode/settings.json` 中添加：

```json
{
  "console-ninja.featureSet": "Community",
  "console-ninja.showWhatsNew": false,
  "console-ninja.captureFunctions": true,
  "console-ninja.showOutputOnRun": true
}
```

## 🧪 快速测试

### 测试1: 使用测试页面

1. 在VSCode中打开: `test-console-ninja.html`
2. 右键 → `Open with Live Server` (需要安装Live Server扩展)
   - 或直接在浏览器打开: `file:///d:/11-20/langgraph-design/test-console-ninja.html`
3. 点击页面上的按钮
4. 查看VSCode输出面板 → Console Ninja

### 测试2: 测试 Next.js 应用

1. 启动Next.js: `cd frontend-nextjs && npm run dev`
2. 在VSCode中打开 `frontend-nextjs/contexts/AuthContext.tsx`
3. 访问 `http://localhost:3000`
4. 查看VSCode输出面板 → Console Ninja

**预期看到:**
```
[AuthContext] 尝试通过 WordPress REST API 获取 Token...
[AuthContext] WordPress 未登录，将显示登录界面
[AuthContext] 无有效登录状态，将显示登录提示界面
```

## 🐛 故障排查

### 问题1: 输出面板没有 Console Ninja 选项

**解决:**
1. 确认扩展已安装: `Ctrl + Shift + X` → 搜索 "Console Ninja"
2. 重启VSCode: `Ctrl + Shift + P` → "Reload Window"
3. 检查是否是付费功能限制（Community版本免费）

### 问题2: 没有显示任何日志

**检查清单:**
- [ ] 浏览器页面已经打开
- [ ] 代码中有 `console.log()` 语句
- [ ] 已经触发了代码执行（例如访问了页面）
- [ ] VSCode输出面板选择了 "Console Ninja"

**手动触发:**
```javascript
// 在浏览器控制台执行
console.log('测试 Console Ninja 连接');
```

然后查看VSCode输出面板。

### 问题3: 只显示部分日志

**原因:** Console Ninja 默认只捕获特定来源的日志

**解决:** 在 `.vscode/settings.json` 中添加:
```json
{
  "console-ninja.captureFunctions": true,
  "console-ninja.captureConsoleMethods": [
    "log", "info", "warn", "error", "debug"
  ]
}
```

### 问题4: Next.js 开发服务器日志不显示

**原因:** 需要配置 Next.js 的源映射

**解决:**
1. 确保 `npm run dev` 正在运行
2. Console Ninja 自动检测 `localhost:3000`
3. 刷新浏览器页面

## 🎯 实战：查看 v3.0.15 的日志

### 步骤1: 准备环境
```bash
# 终端1: 启动Next.js
cd frontend-nextjs
npm run dev

# 终端2: 启动Python后端
cd ..
python -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000
```

### 步骤2: 打开 VSCode 输出面板
- 按 `Ctrl + J`
- 选择 "输出" 标签
- 下拉菜单选择 "Console Ninja"

### 步骤3: 访问应用
浏览器打开: `http://localhost:3000`

### 步骤4: 观察日志
在VSCode输出面板中会实时看到：

```
[AuthContext] 尝试通过 WordPress REST API 获取 Token...
[AuthContext] WordPress 未登录，将显示登录界面
[AuthContext] 无有效登录状态，将显示登录提示界面
```

### 步骤5: 测试登录按钮
点击"立即登录"按钮，观察跳转日志

## 📊 Console Ninja vs 浏览器F12

| 功能 | Console Ninja | 浏览器F12 |
|------|--------------|-----------|
| 查看位置 | VSCode内 | 浏览器内 |
| 代码关联 | ✅ 可跳转到源码 | ❌ 不能直接跳转 |
| 多标签支持 | ✅ 自动聚合 | ❌ 需切换标签 |
| 历史记录 | ✅ 持久化 | ❌ 刷新即清空 |
| 实时更新 | ✅ 实时同步 | ✅ 实时显示 |
| 复杂对象 | ✅ 格式化 | ✅ 可展开 |

## 🎓 最佳实践

1. **始终打开输出面板**: 开发时保持 Console Ninja 面板可见
2. **使用有意义的前缀**: `[AuthContext]`、`[API]` 等，便于过滤
3. **关键步骤打日志**: 登录、Token获取、API调用等
4. **使用不同级别**: `console.log`、`console.warn`、`console.error`

## 🔗 相关资源

- Console Ninja 官网: https://console-ninja.com/
- VSCode扩展: `WallabyJs.console-ninja`
- 测试页面: `test-console-ninja.html`

---

**快速验证命令:**
```bash
# 打开测试页面
start test-console-ninja.html

# 或在浏览器打开后，在控制台执行：
console.log('🎯 Console Ninja 测试');
```

然后查看VSCode的输出面板！
