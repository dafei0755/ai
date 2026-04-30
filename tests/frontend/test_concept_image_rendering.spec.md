# 前端概念图渲染测试规范

## 测试目标
验证前端正确接收和显示概念图，特别是URL代理配置修复后的功能。

## 测试环境要求
- Next.js 开发服务器运行在 localhost:3000
- FastAPI 后端服务器运行在 127.0.0.1:8000
- 已配置 next.config.mjs 的 rewrites 代理规则

## 测试用例

### 1. URL代理配置测试

#### 1.1 API代理正确性
**目标**: 验证 `/api/*` 路径正确代理到后端

**步骤**:
1. 访问 `http://localhost:3000/api/health`
2. 检查 Network 请求实际转发到 `http://127.0.0.1:8000/api/health`

**预期结果**:
- ✅ 状态码 200
- ✅ 返回 JSON: `{"status": "ok"}`

#### 1.2 概念图URL代理
**目标**: 验证 `/generated_images/*` 路径正确代理

**步骤**:
1. 确保后端有测试图片: `data/generated_images/test-session/test.png`
2. 浏览器访问 `http://localhost:3000/generated_images/test-session/test.png`
3. 检查 Network 请求

**预期结果**:
- ✅ 图片正常显示
- ✅ Network 显示请求到 `localhost:3000/generated_images/...`
- ✅ 实际代理到 `127.0.0.1:8000/generated_images/...`
- ✅ 状态码 200

#### 1.3 其他静态资源代理
**目标**: 验证其他静态路径代理

**测试路径**:
- `/followup_images/:path*`
- `/archived_images/:path*`
- `/uploads/:path*`

**预期**: 所有路径都应正确代理到后端

---

### 2. 报告页面概念图显示测试

#### 2.1 基本渲染测试
**目标**: 验证报告页面正确接收和显示概念图

**前置条件**:
- 有包含概念图的完整会话报告
- 报告数据中包含 `generated_images_by_expert` 字段

**步骤**:
1. 访问 `http://localhost:3000/report/{sessionId}`
2. 展开任一专家报告
3. 滚动到专家内容底部

**预期结果**:
- ✅ 看到 "💡 概念图 (X)" 标题（X为图片数量）
- ✅ 显示图片网格
- ✅ 每张图片包含：
  - 图片预览
  - Prompt描述
  - 宽高比标签（如 "16:9"）
  - 风格类型标签（如 "interior"）

#### 2.2 控制台日志验证
**目标**: 验证调试日志正确输出

**步骤**:
1. F12 打开浏览器控制台
2. 访问报告页面
3. 查找日志

**预期日志**:
```javascript
ExpertReportAccordion 渲染, sessionId: {sessionId}
🔥 v7.39: 图片数据: {
  "2-1": {
    "expert_name": "V2 设计总监",
    "images": [
      {
        "id": "...",
        "image_url": "/generated_images/...",
        "prompt": "...",
        "aspect_ratio": "16:9"
      }
    ]
  }
}
```

#### 2.3 图片加载状态测试
**目标**: 验证图片加载进度显示

**步骤**:
1. 清空浏览器缓存
2. 刷新报告页面
3. 观察图片加载过程

**预期**:
- ✅ 显示加载进度（如 "2/5" 表示已加载2张，共5张）
- ✅ 加载完成后进度消失
- ✅ 加载失败的图片显示占位符或错误提示

---

### 3. 图片交互功能测试

#### 3.1 图片轮播预览
**步骤**:
1. 点击任一概念图
2. 验证轮播模态框打开
3. 使用左右箭头切换图片
4. 使用键盘方向键切换
5. 按 ESC 关闭

**预期**:
- ✅ 模态框全屏显示
- ✅ 图片居中显示
- ✅ 显示当前索引（如 "2 / 5"）
- ✅ 显示图片信息（prompt、宽高比、风格）
- ✅ 缩略图导航正常工作

#### 3.2 图片下载功能
**步骤**:
1. 点击图片上的下载按钮
2. 检查浏览器下载

**预期**:
- ✅ 触发浏览器下载
- ✅ 文件名格式: `{expert_name}_{id}_{aspect_ratio}.png`
- ✅ Toast提示 "图片下载成功"

#### 3.3 批量下载
**步骤**:
1. 点击 "批量下载" 按钮
2. 等待下载完成

**预期**:
- ✅ Toast显示下载进度
- ✅ 所有图片依次下载
- ✅ 完成后显示 "成功下载 X 张图片"

---

### 4. 网络请求验证测试

#### 4.1 报告API响应检查
**步骤**:
1. F12 → Network
2. 刷新报告页面
3. 找到 `/api/sessions/{id}/report` 请求
4. 查看响应 JSON

**验证点**:
```json
{
  "structuredReport": {
    "generated_images_by_expert": {
      "2-1": {
        "expert_name": "V2 设计总监",
        "images": [
          {
            "id": "2-1_1_143022_abc",
            "image_url": "/generated_images/...",  // 注意：应该是相对路径
            "prompt": "...",
            "aspect_ratio": "16:9",
            "style_type": "interior"
          }
        ]
      }
    }
  }
}
```

**关键验证**:
- ✅ `generated_images_by_expert` 字段存在
- ✅ `image_url` 字段存在（不是 `url`）
- ✅ `image_url` 是相对路径（以 `/` 开头）

#### 4.2 图片请求验证
**步骤**:
1. Network → Filter: "generated_images"
2. 检查所有图片请求

**验证点**:
- ✅ 请求URL: `http://localhost:3000/generated_images/...`
- ✅ 状态码: `200 OK`（不是404）
- ✅ Content-Type: `image/png`
- ✅ 响应包含图片数据

---

### 5. 边界情况测试

#### 5.1 无概念图的会话
**步骤**: 访问没有生成概念图的会话报告

**预期**:
- ✅ 不显示 "💡 概念图" 区域
- ✅ 专家报告正常显示
- ✅ 无错误日志

#### 5.2 部分专家有概念图
**步骤**: 访问只有部分专家生成了概念图的报告

**预期**:
- ✅ 有图的专家显示概念图区域
- ✅ 无图的专家不显示该区域
- ✅ 布局正常

#### 5.3 图片加载失败
**步骤**:
1. 修改图片URL为不存在的路径（临时测试）
2. 刷新页面

**预期**:
- ✅ 显示加载失败提示
- ✅ 不阻塞其他内容渲染
- ✅ Console有错误日志

---

### 6. 回归测试

#### 6.1 已有功能不受影响
**验证**:
- ✅ 专家报告折叠/展开正常
- ✅ 报告下载功能正常
- ✅ 其他报告区域（摘要、交付物等）正常显示
- ✅ 追问历史显示正常

#### 6.2 性能测试
**场景**: 一个报告包含5个专家，每个专家3张概念图（共15张）

**验证**:
- ✅ 页面加载时间 < 3秒
- ✅ 图片懒加载正常（滚动到才加载）
- ✅ 内存占用合理（< 200MB）

---

## 测试执行清单

### 冒烟测试（必须通过）
- [ ] Next.js代理配置生效
- [ ] 概念图URL返回200（不是404）
- [ ] 报告页面显示概念图标题
- [ ] 图片正常显示

### 完整测试
- [ ] 所有URL代理测试通过
- [ ] 所有报告页面显示测试通过
- [ ] 所有交互功能测试通过
- [ ] 所有网络请求验证通过
- [ ] 所有边界情况测试通过
- [ ] 所有回归测试通过

---

## 自动化测试建议

可以使用 Playwright 或 Cypress 编写自动化测试：

```typescript
// 示例: Playwright测试
test('概念图正确显示', async ({ page }) => {
  await page.goto('http://localhost:3000/report/test-session-id');

  // 等待专家报告加载
  await page.waitForSelector('[data-testid="expert-report"]');

  // 展开第一个专家
  await page.click('[data-testid="expert-toggle"]');

  // 验证概念图区域存在
  const conceptImageSection = await page.locator('text=💡 概念图');
  await expect(conceptImageSection).toBeVisible();

  // 验证图片加载
  const images = await page.locator('[data-testid="concept-image"]');
  await expect(images.first()).toBeVisible();

  // 验证图片请求状态
  const imageResponse = await page.waitForResponse(
    resp => resp.url().includes('/generated_images/') && resp.status() === 200
  );
  expect(imageResponse).toBeTruthy();
});
```

---

## 问题排查指南

### 问题：图片404
**检查**:
1. `next.config.mjs` 是否正确配置rewrites
2. Next.js是否重启（配置修改后必须重启）
3. 后端图片文件是否存在: `data/generated_images/{session_id}/`
4. FastAPI静态文件服务是否正常

### 问题：图片数据为空
**检查**:
1. 浏览器控制台 `🔥 v7.39: 图片数据:` 日志内容
2. Network中报告API响应是否包含 `generated_images_by_expert`
3. 后端日志是否有 `[v7.108] 已提取` 日志
4. 环境变量 `IMAGE_GENERATION_ENABLED=true`

### 问题：图片不显示但无404
**检查**:
1. 检查 `renderConceptImages` 函数是否被调用
2. 检查 `generatedImagesByExpert` prop是否正确传递
3. 检查React DevTools中组件state
