# WordPress SSO 插件部署失败报告

**日期**: 2025-12-13  
**严重程度**: 🔴 High (P0) - 阻塞 SSO 功能上线

---

## 问题概述

WordPress SSO 插件（Next.js SSO Integration v2.0.2）线上安装失败，导致 SSO 功能无法上线。

### 目标功能

实现"必须登录才能访问前端页面，左下角显示账户信息"（类似 DeepSeek 体验）

### 当前状态

- ✅ 插件代码已完成（v2.0.2），包含 WPCOM 兼容性修复（通过 Cookie 识别用户）
- ✅ 前端 SSO 链路已对齐（登录 → /js → get-token → /auth/callback）
- ❌ **线上安装失败**（版本号不一致 + 旧插件残留）

---

## 失败原因分析

### 1. 版本标记混乱

**症状**：
- 插件头 `Version: 2.0.2`
- 但代码内日志仍显示 `v2.0.1`：
  ```php
  error_log('[Next.js SSO v2.0.1] ...');  // ❌ 应为 v2.0.2
  ```
- 调试页面硬编码显示 `2.0.1（🔥 修复WPCOM兼容性）`

**影响**：无法确认实际运行版本，用户困惑

### 2. 手动上传错误

**预期**：
- 用户按 `v2.0.2-wpcompat.zip` 安装
- 应包含 2 个文件：
  - `nextjs-sso-integration.php`（loader，触发 WP 识别）
  - `nextjs-sso-integration-v2.0.php`（主实现）

**实际**：
- 服务器只上传了 1 个文件：`nextjs-sso-integration-v2.0.php`
- 缺少 loader 文件

**影响**：WP 无法正确识别插件

### 3. 旧插件残留

**症状**：
- WordPress 后台显示两个插件条目：
  - 旧版 1.1.0
  - 新版 2.0.2
- 服务器目录中可能存在多个插件目录

**影响**：插件列表混乱，可能激活错误版本

---

## 待办清单

### 立即行动（紧急）

- [ ] **步骤1**：核对本地文件版本
  ```bash
  cd d:\11-20\langgraph-design
  grep -n "v2.0.1" nextjs-sso-integration-v2.0.php
  ```

- [ ] **步骤2**：全局替换版本号
  - 将所有 `v2.0.1` 替换为 `v2.0.2`
  - 包括：日志、注释、调试页面

- [ ] **步骤3**：验证本地文件
  ```bash
  # 确认版本号一致性
  grep -n "2.0" nextjs-sso-integration-v2.0.php | head -20
  ```

- [ ] **步骤4**：清理服务器旧插件
  - 停用所有现有插件（1.1.0 + 2.0.x）
  - 删除 `wp-content/plugins/nextjs-sso-integration/` 目录

- [ ] **步骤5**：重新上传正确文件
  - 确保上传完整的 zip 包（包含 loader + 主实现）
  - 或手动上传两个文件到同一目录

- [ ] **步骤6**：验证安装
  - WordPress 后台启用插件
  - 检查设置页显示版本号为 **2.0.2**

### 测试验证

- [ ] **测试1**：REST API Token 签发
  ```bash
  # 登录 WPCOM 后访问
  curl -H "Cookie: wordpress_logged_in_..." \
    https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token
  
  # 预期：200 + {"success": true, "token": "..."}
  ```

- [ ] **测试2**：短代码回调页
  ```
  访问: https://www.ucppt.com/js?redirect_url=http://localhost:3001/auth/callback
  
  预期：
  1. 自动获取 token
  2. 跳转到 http://localhost:3001/auth/callback?token=...
  ```

- [ ] **测试3**：前端完整流程
  ```
  1. 访问 http://localhost:3001（未登录）
  2. 自动跳转到 WPCOM 登录页
  3. 登录后回到前端，左下角显示账户信息
  ```

---

## 防范措施

### 1. 版本号管理

**强制要求**：
- 插件头 `Version:` 必须与代码内所有版本标记同步
- 发布前检查：
  ```bash
  grep -rn "v\d+\.\d+\.\d+" nextjs-sso-integration*.php
  ```

### 2. 打包规范

**文件命名规范**：
- `nextjs-sso-integration-v2.0.2-single.zip`：单文件包
- `nextjs-sso-integration-v2.0.2-wpcompat.zip`：双文件包（推荐）

**安装指南**：
- 明确说明两种包的区别和使用场景
- 提供 MD5/SHA256 校验值

### 3. 线上验证

**部署后必做**：
- 检查 WordPress 后台设置页显示的版本号
- 验证 REST API 端点可访问
- 测试完整 SSO 流程

---

## 相关文档

- [DEVELOPMENT_RULES.md](.github/DEVELOPMENT_RULES.md) 问题 8.15
- [README.md](README.md) 未完成任务章节
- WordPress 插件文件：`nextjs-sso-integration-v2.0.php`

---

## 失败教训总结

1. ❌ **版本号不一致**：导致无法确认实际运行版本
2. ❌ **手动上传未遵循指南**：缺少必要文件
3. ❌ **旧版本未清理**：导致插件列表混乱
4. ❌ **未进行文件校验**：无法确认上传文件正确性

---

**维护者**：AI Assistant  
**最后更新**：2025-12-13
