# WordPress SSO v3.0.10 - 应用宣传页面入口

## 📦 快速开始

### 1. 部署包

- **插件文件**: `nextjs-sso-integration-v3.0.10.zip` (16 KB)
- **版本**: v3.0.10
- **发布日期**: 2025-12-15

### 2. 核心功能

**智能登录跳转**：
- ✅ 已登录用户：点击按钮 → 直接进入应用（带Token）
- ✅ 未登录用户：点击按钮 → WordPress登录 → 自动跳转到应用

### 3. 快速部署（3步，5分钟）

```bash
# 步骤1: 上传插件
WordPress后台 → 插件 → 上传插件
选择: nextjs-sso-integration-v3.0.10.zip → 安装 → 启用

# 步骤2: 创建页面
WordPress后台 → 页面 → 新建页面
内容添加: [nextjs-app-entrance app_url="https://ai.ucppt.com"]
固定链接: /js → 发布

# 步骤3: 清除缓存并测试
WP Super Cache → 删除缓存
Ctrl + Shift + R (浏览器强制刷新)
访问: https://www.ucppt.com/js
```

---

## 📚 完整文档

### 主要文档

1. **[WORDPRESS_V3.0.10_DEPLOYMENT_SUMMARY.md](WORDPRESS_V3.0.10_DEPLOYMENT_SUMMARY.md)** ⭐ 推荐
   - 快速部署总览
   - 技术亮点
   - 故障排查

2. **[WORDPRESS_ENTRANCE_PAGE_GUIDE_V3.0.10.md](WORDPRESS_ENTRANCE_PAGE_GUIDE_V3.0.10.md)**
   - 完整部署指南（60+ 页）
   - 短代码参数详解
   - 常见问题排查
   - 性能和安全建议

3. **[WORDPRESS_ENTRANCE_PAGE_TEST_CHECKLIST_V3.0.10.md](WORDPRESS_ENTRANCE_PAGE_TEST_CHECKLIST_V3.0.10.md)**
   - 7大测试场景（A-G）
   - 详细验证清单
   - 测试报告模板

### 历史文档

- [LOGIN_STATE_MISDETECTION_FIX_V3.0.9.md](LOGIN_STATE_MISDETECTION_FIX_V3.0.9.md) - v3.0.9 登录状态检测修复
- [DUAL_MODE_README.md](DUAL_MODE_README.md) - 双模式架构总览
- [STANDALONE_MODE_WEBSITE_LINK_FIX.md](STANDALONE_MODE_WEBSITE_LINK_FIX.md) - 独立模式主网站链接

---

## 🎯 短代码使用

### 基础版本（使用默认设置）

```
[nextjs-app-entrance]
```

### 完整自定义版本

```
[nextjs-app-entrance
  app_url="https://ai.ucppt.com?mode=standalone"
  title="AI 设计高参"
  subtitle="极致概念 · 智能设计助手"
  description="基于多智能体协作的专业设计分析系统，为您的设计项目提供全方位的专家级建议。"
  button_text="立即使用"
  features="多专家协作分析|智能需求理解|专业设计建议|支持多模态输入"]
```

### 参数说明

| 参数 | 默认值 | 说明 |
|-----|--------|------|
| `app_url` | `http://localhost:3000?mode=standalone` | ⚠️ 生产环境必须修改 |
| `title` | `AI 设计高参` | 主标题 |
| `subtitle` | `极致概念 · 智能设计助手` | 副标题 |
| `description` | `基于多智能体协作...` | 应用描述 |
| `button_text` | `立即使用` | 按钮文字 |
| `features` | `多专家协作分析\|...` | 特性列表（用\|分隔） |

---

## ✅ 验证清单

### 基本验证
- [ ] 插件版本为 v3.0.10
- [ ] 宣传页面可以访问
- [ ] 页面显示标题、描述、按钮
- [ ] 页面显示4个特性卡片

### 未登录流程
- [ ] 显示 "请先登录以使用应用"
- [ ] 点击按钮跳转到登录页
- [ ] 登录后自动返回宣传页面
- [ ] 1秒后自动跳转到应用
- [ ] 应用显示已登录状态

### 已登录流程
- [ ] 显示 "您已登录为 XXX"
- [ ] 点击按钮直接跳转到应用
- [ ] 应用显示已登录状态

### Token验证
- [ ] localStorage包含 `wp_jwt_token`
- [ ] localStorage包含 `wp_jwt_user`
- [ ] URL中的Token自动清除

---

## 🐛 常见问题

### Q: 点击按钮无反应？
**A**: 检查浏览器控制台（F12）是否有JavaScript错误，确认插件已启用

### Q: 登录后没有自动跳转？
**A**: 检查sessionStorage是否被清除，避免使用无痕模式

### Q: Token未传递到应用？
**A**:
1. 确认插件版本为 v3.0.10
2. 检查 `app_url` 参数是否正确
3. 访问REST API验证：`/wp-json/nextjs-sso/v1/get-token`
4. 清除所有缓存

**详细排查**: 查看 [完整部署指南](WORDPRESS_ENTRANCE_PAGE_GUIDE_V3.0.10.md#常见问题)

---

## 🔧 技术原理

### 智能登录跳转流程

```
未登录用户
  ↓
点击按钮 → 保存目标URL到sessionStorage
  ↓
跳转到WordPress登录页 → 输入账号密码
  ↓
登录成功 → 返回宣传页面
  ↓
检测登录成功 → 生成JWT Token
  ↓
1秒后自动跳转：app_url + &sso_token=xxx
  ↓
应用接收Token → 保存到localStorage
  ↓
显示完整应用界面
```

### Token安全传递

1. **URL参数传递**：Token在URL中传递（暴露时间 < 1秒）
2. **localStorage存储**：应用接收后立即保存到localStorage
3. **URL自动清理**：Token使用后立即从URL清除
4. **过期时间**：Token有效期7天

---

## 📞 技术支持

**文档索引**：
- [部署总结](WORDPRESS_V3.0.10_DEPLOYMENT_SUMMARY.md) - 快速开始
- [完整指南](WORDPRESS_ENTRANCE_PAGE_GUIDE_V3.0.10.md) - 详细说明
- [测试清单](WORDPRESS_ENTRANCE_PAGE_TEST_CHECKLIST_V3.0.10.md) - 验证功能

**问题反馈**：
1. 查看上述文档
2. 检查浏览器控制台日志
3. 联系技术支持团队

---

## 🎉 版本历史

### v3.0.10 (2025-12-15) - 应用宣传页面入口
✅ 新增 `[nextjs-app-entrance]` 短代码
✅ 智能登录跳转（已登录/未登录自动识别）
✅ 自动Token传递，无缝用户体验
✅ 精美UI设计，完全可自定义

### v3.0.9 (2025-12-15) - 登录状态检测修复
✅ 修复登录状态误判问题
✅ 使用专用REST API端点
✅ 提升检测可靠性和准确性

### v3.0.8 (2025-12-15) - 登录同步优化
✅ WordPress登录后自动同步到Next.js
✅ 未登录时隐藏应用界面

---

**部署完成！** 🎊

现在您的WordPress网站有了一个专业的应用宣传入口！

**下一步**：参考 [完整部署指南](WORDPRESS_ENTRANCE_PAGE_GUIDE_V3.0.10.md) 了解更多自定义选项。
