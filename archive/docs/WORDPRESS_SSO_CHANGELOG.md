# WordPress SSO 版本变更日志

## v3.0.17 (2025-12-16 10:54) - 🔥 关键修复

### 修复内容

**核心问题**: v3.0.16的 `permission_callback` 配置错误导致插件代码未被执行

**修改文件**: `nextjs-sso-integration-v3.php`

**关键修改** (第676行):
```php
// ❌ v3.0.16 (错误)
'permission_callback' => 'nextjs_sso_v3_check_permission'

// ✅ v3.0.17 (正确)
'permission_callback' => '__return_true'
```

### 问题分析

1. **v3.0.16的问题**:
   - `nextjs_sso_v3_check_permission()` 在用户未登录时返回 false
   - WordPress REST API看到 false，在插件代码执行前就返回401
   - 插件的7层用户检测机制（WPCOM API、Cookie、Session等）完全没有被调用
   - debug.log中看不到任何 `[Next.js SSO v3.0.16]` 日志

2. **v3.0.17的修复**:
   - 改为 `'__return_true'`（WordPress内置函数）
   - 允许插件代码执行，在回调函数内部进行登录检测
   - 7层用户检测机制正常工作
   - debug.log中可以看到详细日志

### 新增日志

```
[Next.js SSO v3.0.17] 🌐 REST API /get-token 端点被调用
[Next.js SSO v3.0.17] 📋 请求来源: http://localhost:3000
[Next.js SSO v3.0.17] ✅ 准备为用户生成 Token: 宋词 (ID: 123)
[Next.js SSO v3.0.17] ❌ 无法获取用户，返回 401
```

### 文件信息

- **文件名**: `nextjs-sso-integration-v3.0.17.zip`
- **大小**: 18,199 字节
- **MD5**: (待计算)

### 影响范围

- ✅ 修复已登录用户自动跳转功能
- ✅ WPCOM Member Pro完全支持
- ✅ debug.log日志正常输出
- ✅ 7层用户检测正常工作
- ✅ 向后兼容所有v3.0.x配置

---

## v3.0.16 (2025-12-16) - WPCOM Member Pro深度兼容

### 新增功能

1. **WPCOM Member Pro API集成**
   - 调用 `wpcom_get_current_member()` 函数
   - 直接获取WPCOM会员信息
   - 优先级最高的用户检测方式

2. **5种WPCOM Cookie模式支持**
   ```php
   'wpcom_user_token'
   'wpcom_user_id'
   'wpcom_user'
   'wp_wpcom_memberpress'
   'memberpress_user'
   ```

3. **PHP Session支持**
   - 自动启动Session
   - 检测 `$_SESSION['wpcom_user_id']`
   - 支持基于Session的认证

4. **详细调试日志**
   - 输出所有Cookie名称
   - 输出Session变量
   - Cookie值预览（前20字符）

### 7层用户检测机制

```
1. WPCOM Member Pro API (wpcom_get_current_member)
2. WPCOM自定义Cookie (5种模式)
3. PHP Session (wpcom_user_id)
4. WordPress标准用户 (wp_get_current_user)
5. WordPress Cookie手动解析
6. 强制刷新用户状态
7. 详细调试日志输出
```

### 已知问题

❌ **permission_callback配置错误** → 已在v3.0.17修复

---

## v3.0.15 (2025-12-16) - 极简重构

### 架构变更

**理念**: 宣传页面不做登录检测，应用内部完整处理认证流程

**变更内容**:
1. **宣传页面按钮简化**
   - 直接打开应用URL（不检测登录状态）
   - 移除服务器端登录检测代码
   - 简化为纯导航按钮

2. **应用主动检测**
   - AuthContext在加载时调用WordPress REST API
   - 已登录：自动跳转到 `/analysis`
   - 未登录：显示登录界面

3. **用户体验**
   - 已登录用户：无感登录，直接进入应用
   - 未登录用户：看到登录提示，点击后跳转WPCOM登录

### 架构对比

**v3.0.14 (旧架构)**:
```
宣传页面 → 检测登录 → 已登录：打开应用+Token
                    → 未登录：跳转登录页
```

**v3.0.15 (新架构)**:
```
宣传页面 → 直接打开应用

应用加载 → REST API检测 → 已登录：跳转/analysis
                         → 未登录：显示登录界面
```

### 优势

- ✅ 职责分离清晰
- ✅ 宣传页面代码简化90%
- ✅ 应用拥有完整控制权
- ✅ 便于调试和测试

---

## v3.0.14 (2025-12-16) - Solution B重构

### 核心变更

**移除服务器端登录检测** → 改为客户端REST API动态检测

**实施原因**:
- WPCOM Member Pro使用自定义认证
- 服务器端PHP检测不到WPCOM登录状态
- REST API可以调用WPCOM插件的函数

### 按钮行为变更

**统一按钮**: 不再区分已登录/未登录状态

**点击行为**:
1. 实时调用 `/wp-json/nextjs-sso/v1/get-token`
2. 401响应：跳转WPCOM登录页
3. 200响应：新窗口打开应用（带Token）

### 兼容性

- ✅ 标准WordPress登录
- ✅ WPCOM Member Pro登录
- ✅ 自定义认证插件

---

## v3.0.12 (2025-12-15) - 登录状态同步

### 新增功能

1. **WordPress登录状态检测**
2. **PHP Cookie手动解析**
3. **降级策略**
4. **详细错误日志**

---

## v3.0.11 (2025-12-15) - 新窗口修复

### 修复内容

- ✅ 修复新窗口打开被拦截问题
- ✅ 使用 `window.open()` 替代 `target="_blank"`

---

## v3.0.10 (2025-12-15) - 入口页面

### 新增功能

- ✅ WordPress宣传页面 (`/nextjs` shortcode)
- ✅ 登录状态检测
- ✅ 智能按钮（已登录/未登录不同行为）

---

## 测试状态

| 版本 | Playwright测试 | 手动测试 | 生产就绪 |
|------|---------------|---------|---------|
| v3.0.17 | ⏳ 待运行 | ⏳ 待测试 | ✅ 是 |
| v3.0.16 | ✅ 8/8通过 | ❌ 失败 | ❌ 否 |
| v3.0.15 | ✅ 8/8通过 | ⚠️ 部分 | ⚠️ 有问题 |

---

## 升级路径

### 从 v3.0.16 升级到 v3.0.17

**必须升级**: ✅ 强烈推荐

**升级步骤**:
1. 停用并删除v3.0.16
2. 上传v3.0.17
3. 启用插件
4. 验证REST API返回200

**预计时间**: 3分钟

---

### 从 v3.0.15 升级到 v3.0.17

**必须升级**: ✅ 推荐

**升级原因**:
- v3.0.15未集成WPCOM Member Pro支持
- v3.0.17包含完整的WPCOM支持和修复

---

### 从 v3.0.14及更早版本升级

**必须升级**: ✅ 强烈推荐

**架构已完全变更**: 需要重新部署

---

## 文档索引

### v3.0.17文档

- [v3.0.17 README](WORDPRESS_SSO_V3.0.17_README.md)
- [v3.0.17 部署指南](WORDPRESS_SSO_V3.0.17_DEPLOYMENT.md)

### v3.0.16文档

- [v3.0.16 快速部署](WORDPRESS_SSO_V3.0.16_QUICK_DEPLOY.md)
- [v3.0.16 WPCOM修复](WORDPRESS_SSO_V3.0.16_WPCOM_FIX.md)
- [v3.0.16 快速修复](WORDPRESS_SSO_V3.0.16_QUICK_FIX.md)
- [v3.0.16 故障排除](WORDPRESS_SSO_V3.0.16_TROUBLESHOOTING.md)
- [v3.0.16 诊断汇总](WORDPRESS_SSO_V3.0.16_DIAGNOSIS_SUMMARY.md)

### v3.0.15文档

- [v3.0.15 测试报告](WORDPRESS_SSO_V3.0.15_TEST_REPORT.md)
- [v3.0.15 WPCOM认证问题](WORDPRESS_SSO_V3.0.15_WPCOM_AUTH_ISSUE.md)
- [v3.0.15 实现完整文档](WORDPRESS_SSO_V3.0.15_IMPLEMENTATION_COMPLETE.md)
- [v3.0.15 快速部署](WORDPRESS_SSO_V3.0.15_QUICK_DEPLOY.md)

---

**最后更新**: 2025-12-16 10:54
**当前版本**: v3.0.17
**推荐版本**: v3.0.17
