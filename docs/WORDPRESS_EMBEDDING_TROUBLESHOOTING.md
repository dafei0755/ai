# WordPress 嵌入故障排查指南 v2.1

## 🎯 快速诊断

### 请先回答以下问题：

1. **WordPress 页面上看到了什么？**
   - [ ] 完全没有显示任何内容
   - [ ] 显示了标题"精选案例展示"但没有卡片
   - [ ] 显示"正在加载..."一直转圈
   - [ ] 显示"加载失败"错误提示
   - [ ] 显示了卡片但布局错乱/间距过大

2. **使用的嵌入方式？**
   - [ ] 新版编辑器（Gutenberg）的"自定义HTML"区块
   - [ ] 经典编辑器的"文本"模式
   - [ ] 其他方式（请说明）

3. **是否修改了配置？**
   - [ ] 已将 `API_URL` 改为生产地址
   - [ ] 已将 `FRONTEND_URL` 改为前端地址
   - [ ] 仍使用 localhost

## 🔍 详细排查步骤

### 步骤1：打开浏览器开发者工具

在 WordPress 页面按 **F12**，查看两个关键标签页：

#### ① Console 标签页
**查找红色错误信息**，常见错误及解决方案：

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `CORS policy` | API 地址配置错误 | 修改代码中的 `API_URL` 为生产地址 |
| `Mixed Content` | HTTPS/HTTP 混用 | 统一使用 HTTPS |
| `Swiper is not defined` | CDN 加载失败 | 检查网络或使用国内 CDN |
| `SyntaxError: Unexpected token` | wpautop 破坏了代码 | 见下方"WordPress 干扰"部分 |
| `404 Not Found` | API 端点不存在 | 检查后端服务是否运行 |

#### ② Network 标签页
1. 刷新页面
2. 查找 `/api/showcase/featured` 请求
3. 点击查看详情：
   - **Status**：应为 `200 OK`
   - **Preview**：应能看到 JSON 数据
   - **Response**：查看返回内容

### 步骤2：检查 API 配置

#### 🔥 最常见问题：API_URL 仍然是 localhost

在嵌入代码中找到这两行：
```javascript
const API_URL = 'http://localhost:8000';  // ⚠️ 这行必须修改！
const FRONTEND_URL = 'http://localhost:3000';  // ⚠️ 这行也要修改！
```

**正确配置示例**：
```javascript
// 生产环境配置
const API_URL = 'https://api.yoursite.com';  // 不要以 / 结尾
const FRONTEND_URL = 'https://app.yoursite.com';

// 或者使用相同域名
const API_URL = 'https://ucppt.com';
const FRONTEND_URL = 'https://ucppt.com';
```

**验证方法**：在浏览器中直接访问
```
https://your-api-domain.com/api/showcase/featured
```
应该返回 JSON 数据。

### 步骤3：检查 WordPress 嵌入方式

#### ✅ 正确方式

**新版编辑器（Gutenberg）**：
1. 点击 `+` 按钮添加区块
2. 搜索"自定义 HTML"或"Custom HTML"
3. 粘贴**全部代码**（从 `<!--` 开头到 `</script>` 结尾）
4. 直接保存，不要切换到其他视图

**经典编辑器**：
1. 切换到"文本"模式（右上角）
2. 粘贴代码
3. **不要切回"可视化"模式**
4. 保存

#### ❌ 错误方式（会导致失败）

- ❌ 使用"段落"区块粘贴
- ❌ 使用"代码"区块（会转义 HTML）
- ❌ 在"可视化"模式下操作
- ❌ 只粘贴了部分代码

### 步骤4：WordPress wpautop 干扰

**症状**：
- 保存后代码自动被格式化
- JavaScript 代码被分成多行
- Console 显示 `SyntaxError`

**解决方案1：短代码方式（推荐）**

编辑主题的 `functions.php`：
```php
// 禁用特定内容的自动格式化
add_filter('the_content', function($content) {
    if (strpos($content, 'featured-showcase-container') !== false) {
        remove_filter('the_content', 'wpautop');
    }
    return $content;
}, 9);
```

**解决方案2：使用插件**
- 安装 "Raw HTML" 或 "Disable wpautop" 插件
- 针对该页面禁用自动格式化

**解决方案3：确认嵌入方式**
- 确保使用"自定义 HTML"区块
- 不要使用"段落"或其他富文本区块

### 步骤5：检查 HTTPS/HTTP 配置

如果你的 WordPress 网站使用 HTTPS（ucppt.com 应该是），确保：

```javascript
// ✅ 正确：全部使用 HTTPS
const API_URL = 'https://api.yoursite.com';
const FRONTEND_URL = 'https://app.yoursite.com';

// ❌ 错误：混用 HTTP
const API_URL = 'http://api.yoursite.com';  // 会被浏览器阻止！
```

### 步骤6：检查 CDN 资源

确认这两个资源能正常加载：
```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css">
<script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
```

**如果 CDN 被墙或加载慢**：

使用国内 CDN：
```html
<!-- 替换为国内 CDN -->
<link rel="stylesheet" href="https://unpkg.com/swiper@11/swiper-bundle.min.css">
<script src="https://unpkg.com/swiper@11/swiper-bundle.min.js"></script>
```

## 🛠️ 常见问题速查表

| 显示效果 | 可能原因 | 检查方法 | 解决方案 |
|---------|---------|---------|---------|
| 完全不显示 | 代码未正确嵌入 | 查看页面源代码 | 重新粘贴到"自定义HTML"区块 |
| 一直显示"加载中" | API 请求失败 | Console + Network 标签 | 修改 API_URL 配置 |
| 显示"加载失败" | API 返回错误 | Network 查看错误信息 | 检查后端服务状态 |
| 间距过大 | 样式被主题覆盖 | 检查元素样式 | 已修复（使用 !important） |
| JavaScript 错误 | wpautop 破坏代码 | Console 查看语法错误 | 禁用 wpautop |

## 📋 部署检查清单

部署前请逐项确认：

### 代码配置
- [ ] 将 `API_URL` 改为生产环境地址（不是 localhost）
- [ ] 将 `FRONTEND_URL` 改为前端地址
- [ ] 如果网站是 HTTPS，确保 API_URL 也使用 HTTPS
- [ ] API 地址末尾**没有** `/`（斜杠）

### WordPress 操作
- [ ] 使用"自定义 HTML"区块（不是其他类型）
- [ ] 粘贴了完整代码（从注释到 `</script>` 结尾）
- [ ] 未在"可视化"模式下编辑
- [ ] 保存后刷新查看效果

### 功能验证
- [ ] 浏览器 Console 无红色错误
- [ ] Network 看到 API 请求且返回 200
- [ ] 页面显示了案例卡片
- [ ] 轮播自动播放正常
- [ ] 点击卡片能打开详情页

## 💡 调试技巧

### 1. 查看页面源代码
右键 → 查看页面源代码 → 搜索 `featured-showcase-container`

应该能看到完整的代码块，如果看不到或代码被破坏，说明嵌入方式有问题。

### 2. 测试 API 可达性
在浏览器地址栏直接输入：
```
https://your-api-domain.com/api/showcase/featured
```

**正常**：显示 JSON 数据
**404**：后端未运行或路由错误
**CORS 错误**：后端 CORS 配置问题（需修改后端）

### 3. 逐步排查
```javascript
// 在代码开头添加调试信息
console.log('🔍 API_URL:', API_URL);
console.log('🔍 FRONTEND_URL:', FRONTEND_URL);
```

保存后打开 Console，检查配置是否正确。

## 🆘 仍然无法解决？

请提供以下截图：

1. **Console 标签页**（显示所有错误信息）
2. **Network 标签页**（显示 API 请求状态）
3. **WordPress 编辑器**（显示使用的区块类型）
4. **页面实际显示效果**
5. **浏览器地址栏**（显示访问的 URL）

同时说明：
- WordPress 版本号
- 使用的主题名称
- 后端部署方式（本地/云服务器）
- API 地址是否可公网访问

---

**文档版本**：v2.1
**最后更新**：2026-01-03
**适用环境**：WordPress 5.x / 6.x
