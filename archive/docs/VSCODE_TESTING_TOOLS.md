# VSCode推荐扩展 - WordPress SSO项目

## 必装扩展

1. **REST Client**
   - ID: humao.rest-client
   - 用途: 测试WordPress REST API
   - 使用: 打开 test-v3.0.15-auth.http，点击"Send Request"

2. **Python Test Explorer**
   - ID: littlefoxteam.vscode-python-test-adapter
   - 用途: 可视化Python测试
   - 使用: 侧边栏"测试"图标

3. **Jest Runner** (可选)
   - ID: firsttris.vscode-jest-runner
   - 用途: Next.js组件测试
   - 使用: 代码行旁的"▶ Run"按钮

4. **Error Lens**
   - ID: usernamehw.errorlens
   - 用途: 实时显示错误和警告
   - 特点: 错误直接显示在代码旁边

5. **Console Ninja** (强烈推荐)
   - ID: WallabyJs.console-ninja
   - 用途: 在VSCode中直接显示浏览器console.log
   - 特点: 不用打开浏览器就能看到日志

## 安装命令

在VSCode终端执行:

```bash
code --install-extension humao.rest-client
code --install-extension littlefoxteam.vscode-python-test-adapter
code --install-extension firsttris.vscode-jest-runner
code --install-extension usernamehw.errorlens
code --install-extension WallabyJs.console-ninja
```

## 使用示例

### 1. REST Client测试
打开: test-v3.0.15-auth.http
点击请求上方的"Send Request"

### 2. PowerShell自动化测试
在终端执行:
```powershell
powershell -ExecutionPolicy Bypass -File test-v3.0.15-flow.ps1
```

### 3. Console Ninja (最强大)
- 启动Next.js: `npm run dev`
- VSCode会自动捕获所有console.log
- 无需打开浏览器F12
- 日志直接显示在VSCode的"输出"面板

## 项目特定配置

在.vscode/settings.json中添加:

```json
{
  "rest-client.environmentVariables": {
    "$shared": {
      "wordpressUrl": "https://www.ucppt.com",
      "apiUrl": "http://127.0.0.1:8000",
      "nextjsUrl": "http://localhost:3000"
    }
  },
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "console-ninja.featureSet": "Community"
}
```
