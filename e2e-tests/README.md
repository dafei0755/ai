# WordPress SSO v3.0.15 自动化E2E测试

## 🚀 快速开始

### 1. 安装依赖

```bash
cd e2e-tests
npm install
npm run install-browsers
```

### 2. 配置环境变量

```bash
# 复制配置文件
cp .env.example .env

# 编辑 .env，填写WordPress登录凭据
WORDPRESS_USERNAME=your_username
WORDPRESS_PASSWORD=your_password
```

### 3. 运行测试

```bash
# 无界面模式（快速）
npm test

# 有界面模式（可视化）
npm run test:headed

# UI模式（交互式，最推荐）
npm run test:ui

# Debug模式（逐步调试）
npm run test:debug
```

## 📋 测试覆盖

自动化测试包含8个完整测试用例：

1. ✅ Python后端健康检查
2. ✅ WordPress REST API - 未登录状态（401）
3. ✅ WordPress WPCOM自动登录
4. ✅ WordPress REST API - 已登录状态（200 + Token）
5. ✅ Next.js应用 - 未登录显示登录界面
6. ✅ Next.js应用 - 已登录自动跳转 /analysis
7. ✅ 完整流程 - 宣传页面点击按钮 → 应用自动登录
8. ✅ Token验证流程

## 🎯 VSCode集成

### 方法1: 安装Playwright VSCode扩展（推荐）

1. 安装扩展：`ms-playwright.playwright`
2. 侧边栏会显示"Testing"图标
3. 点击可看到所有测试用例
4. 单击"▶"运行单个测试
5. 右键选择运行模式（headed/debug）

### 方法2: 使用VSCode任务

在 `.vscode/tasks.json` 中添加：

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run E2E Tests",
      "type": "shell",
      "command": "cd e2e-tests && npm test",
      "group": "test",
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    },
    {
      "label": "Run E2E Tests (UI Mode)",
      "type": "shell",
      "command": "cd e2e-tests && npm run test:ui",
      "group": "test"
    }
  ]
}
```

按 `Ctrl+Shift+P` → "Run Task" → 选择测试任务

## 📊 测试报告

测试完成后会生成HTML报告：

```bash
# 查看报告
cd e2e-tests
npx playwright show-report
```

报告包含：
- 测试结果统计
- 失败截图
- 失败录屏
- 详细日志

## 🔧 高级配置

### 并行测试

编辑 `playwright.config.ts`：

```typescript
export default defineConfig({
  workers: 4, // 并行4个测试
  fullyParallel: true,
});
```

### 多浏览器测试

```typescript
projects: [
  { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
  { name: 'webkit', use: { ...devices['Desktop Safari'] } },
],
```

### CI/CD集成（GitHub Actions）

创建 `.github/workflows/e2e-tests.yml`：

```yaml
name: E2E Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - name: Install dependencies
        run: cd e2e-tests && npm ci
      - name: Install Playwright Browsers
        run: cd e2e-tests && npx playwright install --with-deps
      - name: Run tests
        run: cd e2e-tests && npm test
        env:
          WORDPRESS_USERNAME: ${{ secrets.WORDPRESS_USERNAME }}
          WORDPRESS_PASSWORD: ${{ secrets.WORDPRESS_PASSWORD }}
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: e2e-tests/playwright-report/
```

## 🐛 故障排查

### 问题1: Playwright未安装

```bash
npm run install-browsers
```

### 问题2: Next.js服务未启动

确保运行测试前Next.js已启动：

```bash
cd frontend-nextjs
npm run dev
```

或使用配置中的 `webServer` 自动启动（已配置）

### 问题3: WordPress登录失败

检查 `.env` 中的凭据是否正确，或检查WPCOM登录页面的选择器是否改变

### 问题4: Python后端未运行

```bash
python -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000
```

## 📝 编写新测试

在 `tests/` 目录创建新文件：

```typescript
import { test, expect } from '@playwright/test';

test('我的新测试', async ({ page }) => {
  await page.goto('http://localhost:3000');
  await expect(page.locator('h1')).toHaveText('预期文本');
});
```

## 🎉 测试最佳实践

1. **使用明确的等待**：`waitForLoadState`、`waitForURL` 而不是 `page.waitForTimeout`
2. **使用语义化选择器**：`text=按钮文字` 而不是 `#btn-123`
3. **独立测试**：每个测试应该独立运行，不依赖其他测试
4. **清理状态**：测试完成后清理Cookie、localStorage
5. **详细日志**：使用 `console.log` 记录关键步骤

## 📚 相关文档

- [Playwright官方文档](https://playwright.dev/)
- [VSCode Playwright扩展](https://marketplace.visualstudio.com/items?itemName=ms-playwright.playwright)
- [v3.0.15部署指南](../WORDPRESS_SSO_V3.0.15_QUICK_DEPLOY.md)

---

**v3.0.15 自动化测试配置完成！** 🚀
