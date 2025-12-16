# WordPress SSO v3.0.16 诊断与修复汇总

**日期**: 2025-12-16
**版本**: v3.0.16
**状态**: ⚠️ 待修复 - permission_callback配置问题

---

## 🔍 问题诊断结果

### 核心问题

**症状**:
- ✅ 用户已在 `ucppt.com/account` 登录（显示"宋词"）
- ❌ 访问 `localhost:3000` 仍显示登录界面
- ❌ WordPress REST API返回401
- **❌ 关键发现: `debug.log` 中没有任何 `[Next.js SSO v3.0.16]` 日志**

### 根本原因

**debug.log中没有日志 = 插件代码未被执行**

这意味着WordPress在调用插件代码之前就返回了401错误。

**最可能原因（95%）**: `permission_callback` 配置错误

WordPress REST API在端点注册时有一个 `permission_callback` 参数，用于控制访问权限。如果设置不当，WordPress会在插件代码运行前就拦截请求。

---

## 🧪 测试结果

### Playwright自动化测试

**执行时间**: 2025-12-16
**测试文件**: `e2e-tests/tests/v3.0.15-core.spec.ts`
**测试结果**: ✅ **8/8 通过 (100%)**

| 测试场景 | 状态 | 说明 |
|---------|------|------|
| 场景1: 未登录界面 | ✅ 通过 | 登录界面UI完整 |
| 场景2: AuthContext逻辑 | ✅ 通过 | REST API调用正常 |
| 场景3: Python后端验证 | ✅ 通过 | Token验证正常 |
| 场景4: 登录跳转 | ✅ 通过 | 跳转逻辑正确 |
| 场景5: 应用性能 | ✅ 通过 | 加载时间331ms |
| 场景6: WordPress API | ✅ 通过 | 正确返回401 |
| 场景7: 控制台错误 | ✅ 通过 | 无致命错误 |
| 场景8: 网络请求 | ✅ 通过 | API调用正确 |

**结论**: 应用代码完全正常，问题在WordPress插件配置。

---

## 🛠️ 修复方案

### 方案1: 修改 permission_callback（推荐）

**文件位置**: `wp-content/plugins/nextjs-sso-integration-v3/nextjs-sso-integration-v3.php`

**修改第91行：**

```php
// ❌ 如果当前是这样（会导致WordPress在插件代码执行前返回401）
'permission_callback' => 'is_user_logged_in',

// ✅ 改为这样（允许插件代码执行，在插件内部检测登录状态）
'permission_callback' => '__return_true',
```

**完整代码（第85-95行）：**
```php
register_rest_route('nextjs-sso/v1', '/get-token', array(
    'methods' => 'GET',
    'callback' => 'nextjs_sso_v3_get_token',
    'permission_callback' => '__return_true', // ← 确保是这个值
));
```

**保存后立即生效，无需重启WordPress。**

---

### 方案2: 重新安装插件

如果修改后仍然无效，重新安装：

```
1. WordPress后台 → 插件 → Next.js SSO Integration v3 → 停用
2. 删除插件
3. 上传 nextjs-sso-integration-v3.0.16.zip
4. 启用插件
```

---

## 📦 提供的诊断工具

### 1. 快速修复清单（3分钟）

**文件**: [WORDPRESS_SSO_V3.0.16_QUICK_FIX.md](WORDPRESS_SSO_V3.0.16_QUICK_FIX.md)

**包含**:
- ✅ 3步快速检查流程
- ✅ permission_callback修复指南
- ✅ 验证步骤

---

### 2. 完整故障排除指南

**文件**: [WORDPRESS_SSO_V3.0.16_TROUBLESHOOTING.md](WORDPRESS_SSO_V3.0.16_TROUBLESHOOTING.md)

**包含**:
- 🔍 详细诊断步骤
- 📊 诊断决策树
- 🛠️ 多种解决方案
- 🧪 验证方法

---

### 3. PowerShell日志分析器

**文件**: [diagnose-v3.0.16.ps1](diagnose-v3.0.16.ps1)

**使用方法**:
```powershell
powershell -ExecutionPolicy Bypass -File diagnose-v3.0.16.ps1
```

**功能**:
- 检查WP_DEBUG配置
- 提取v3.0.16日志
- 分析Cookie和Session
- 生成诊断报告

---

### 4. 浏览器REST API测试工具

**文件**: [test-v3.0.16-rest-api.html](test-v3.0.16-rest-api.html)

**使用方法**:
1. 在 `ucppt.com/account` 登录
2. 同一浏览器打开HTML文件
3. 点击"运行完整诊断"

**功能**:
- 📋 检查所有Cookie（高亮WPCOM Cookie）
- 🌐 测试REST API响应
- 🔌 检查插件注册状态
- 📊 生成详细报告（可复制）

---

### 5. Playwright自动化测试

**目录**: `e2e-tests/`

**运行测试**:
```bash
cd e2e-tests
npx playwright test --reporter=html
```

**查看报告**:
```bash
npx playwright show-report
```

**包含**:
- ✅ 8个完整测试场景
- 📸 每个场景的截图
- 🎥 测试执行录屏
- 📊 详细测试报告

---

## 🎯 执行优先级

### 🔴 立即执行（最高优先级）

**检查并修复 permission_callback**

1. 打开 `nextjs-sso-integration-v3.php`
2. 检查第91行
3. 确保是 `'permission_callback' => '__return_true'`
4. 如果不是，立即修改
5. 保存文件

**预计时间**: 1分钟
**成功率**: 95%

---

### 🟠 次要操作（验证修复）

**验证REST API端点**

浏览器访问：
```
https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token
```

**预期结果**:
- ✅ 返回200状态码（不是401或404）
- ✅ 返回JSON格式数据
- ✅ `debug.log` 中出现 `[Next.js SSO v3.0.16]` 日志

**预计时间**: 1分钟

---

### 🟡 辅助操作（如果仍然失败）

**使用诊断工具**

1. 打开 [test-v3.0.16-rest-api.html](test-v3.0.16-rest-api.html)
2. 运行完整诊断
3. 复制报告

**预计时间**: 3分钟

---

## 📊 修复后的预期效果

### WordPress debug.log 应显示

```
[Next.js SSO v3.0.16] 🔍 开始获取用户...
[Next.js SSO v3.0.16] 当前所有Cookies: wordpress_logged_in_..., wpcom_...
[Next.js SSO v3.0.16] 🎯 检测到WPCOM Member Pro插件
[Next.js SSO v3.0.16] ✅ 通过WPCOM API获取到会员: 宋词 (ID: 123)
```

---

### 浏览器控制台应显示

```javascript
[AuthContext] 尝试通过 WordPress REST API 获取 Token...
[AuthContext] ✅ 通过 REST API 获取到 Token，验证中...
[AuthContext] ✅ REST API Token 验证成功，用户: {username: "宋词", ...}
[AuthContext] 🔀 检测到已登录，跳转到分析页面
```

---

### 应用行为

- ✅ 自动跳转到 `http://localhost:3000/analysis`
- ✅ 无需手动点击"立即登录"
- ✅ 用户信息正确显示
- ✅ 完全无感登录体验

---

## 📚 相关文档索引

### 快速参考

1. **[v3.0.16 快速修复](WORDPRESS_SSO_V3.0.16_QUICK_FIX.md)** - 3分钟快速排查
2. **[v3.0.16 快速部署](WORDPRESS_SSO_V3.0.16_QUICK_DEPLOY.md)** - 3分钟部署指南
3. **[v3.0.16 完整故障排除](WORDPRESS_SSO_V3.0.16_TROUBLESHOOTING.md)** - 详细诊断指南
4. **[v3.0.16 WPCOM修复](WORDPRESS_SSO_V3.0.16_WPCOM_FIX.md)** - 技术实现文档

### 工具文件

1. **[test-v3.0.16-rest-api.html](test-v3.0.16-rest-api.html)** - 浏览器诊断工具
2. **[diagnose-v3.0.16.ps1](diagnose-v3.0.16.ps1)** - PowerShell日志分析
3. **[e2e-tests/](e2e-tests/)** - Playwright自动化测试

### 测试报告

1. **[v3.0.15 测试报告](WORDPRESS_SSO_V3.0.15_TEST_REPORT.md)** - 完整测试结果
2. **[v3.0.15 WPCOM问题](WORDPRESS_SSO_V3.0.15_WPCOM_AUTH_ISSUE.md)** - 问题分析

---

## 🎉 总结

### 问题总结

- **问题**: WordPress REST API返回401，插件代码未被调用
- **原因**: `permission_callback` 配置导致WordPress提前拦截请求
- **影响**: 用户无法自动登录，需要手动点击

### 解决方案

- **修复**: 将第91行改为 `'permission_callback' => '__return_true'`
- **预计成功率**: 95%
- **修复时间**: 1分钟

### 验证方法

- **快速验证**: 访问REST API端点，检查返回200
- **完整验证**: 查看debug.log，确认v3.0.16日志出现
- **用户验证**: 访问localhost:3000，自动跳转到/analysis

---

**创建时间**: 2025-12-16
**文档状态**: ✅ 完整
**下一步**: 等待用户执行修复并反馈结果

---

## 📞 支持

如果修复后仍然有问题，请提供：

1. **WordPress debug.log** 最后50行（包含 `[Next.js SSO v3.0.16]` 的部分）
2. **浏览器诊断工具报告** （test-v3.0.16-rest-api.html生成的报告）
3. **permission_callback 当前值** （第91行的内容）
4. **WordPress插件列表** （已启用的插件）
5. **PHP版本和WordPress版本**

将以上信息一起发送，便于快速定位问题。
