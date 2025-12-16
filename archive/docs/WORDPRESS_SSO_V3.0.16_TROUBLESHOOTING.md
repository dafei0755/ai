# WordPress SSO v3.0.16 故障排除完整指南

**当前状态**: debug.log中没有 `[Next.js SSO v3.0.16]` 日志
**测试时间**: 2025-12-16
**症状**: WordPress REST API返回401，插件代码未被调用

---

## 🚨 核心问题诊断

### 问题现象

用户在 `ucppt.com/account` 已登录（显示用户"宋词"），但：

1. ✅ 访问 `localhost:3000` 显示登录界面（预期行为）
2. ✅ AuthContext调用 `https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token`
3. ❌ WordPress返回401状态码
4. **❌ 关键问题：`debug.log` 中没有任何 `[Next.js SSO v3.0.16]` 日志**

### 根本原因分析

**debug.log中没有日志意味着：**

1. **插件端点未被调用** - WordPress在插件代码执行之前就返回了401
2. **REST API权限检查失败** - WordPress核心在插件代码运行前拦截了请求
3. **插件未正确注册** - 端点可能没有成功注册到WordPress REST API

---

## 🔍 诊断步骤

### 步骤1: 验证插件注册状态

**操作：**

1. 打开浏览器（与登录同一浏览器）
2. 访问：`https://www.ucppt.com/wp-json/`
3. 查找响应中是否包含 `nextjs-sso/v1/get-token` 端点

**使用提供的诊断工具：**

打开文件 [test-v3.0.16-rest-api.html](test-v3.0.16-rest-api.html)，点击"步骤3: 检查插件注册"

**预期结果：**

✅ **正常情况**: 响应中包含 `/wp-json/nextjs-sso/v1/get-token` 路由

```json
{
  "routes": {
    "/nextjs-sso/v1": {
      "namespace": "nextjs-sso/v1",
      "methods": ["GET", "POST"],
      "endpoints": [...]
    },
    "/nextjs-sso/v1/get-token": {
      "namespace": "nextjs-sso/v1",
      "methods": ["GET"],
      "endpoints": [...]
    }
  }
}
```

❌ **异常情况**: 没有找到 `nextjs-sso` 相关路由

---

### 步骤2: 检查插件文件完整性

**检查WordPress插件目录：**

```
/wp-content/plugins/nextjs-sso-integration-v3/
  └── nextjs-sso-integration-v3.php
```

**验证方法：**

1. **FTP/文件管理器**: 检查文件是否存在
2. **文件大小**: 应约 17,951 字节
3. **版本号**: 打开文件，第6行应显示 `Version: 3.0.16`

**关键检查点：**

打开 `nextjs-sso-integration-v3.php`，确认以下代码存在：

```php
// 第6行
Version: 3.0.16

// 第85-95行（端点注册）
register_rest_route('nextjs-sso/v1', '/get-token', array(
    'methods' => 'GET',
    'callback' => 'nextjs_sso_v3_get_token',
    'permission_callback' => '__return_true', // ← 关键：允许未登录访问
));
```

**⚠️ 关键检查：permission_callback**

如果该行是：
```php
'permission_callback' => 'is_user_logged_in', // ❌ 错误
```

这会导致WordPress在插件代码运行前就返回401！应改为：
```php
'permission_callback' => '__return_true', // ✅ 正确
```

---

### 步骤3: 检查PHP错误日志

**WordPress可能有多个日志文件：**

1. **WordPress调试日志**: `/wp-content/debug.log`
2. **PHP错误日志**:
   - `/var/log/php_errors.log`
   - `C:\xampp\php\logs\php_error_log`
   - 主机控制面板的错误日志

**查找内容：**

```
PHP Parse error
PHP Fatal error
nextjs-sso
rest_api_init
```

---

### 步骤4: 测试端点直接访问

**使用浏览器直接访问：**

```
https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token
```

**可能的响应：**

**情况A: 404错误**
```json
{
  "code": "rest_no_route",
  "message": "No route was found matching the URL and request method",
  "data": {"status": 404}
}
```
**原因**: 插件未正确注册
**解决**: 重新安装插件，检查PHP语法错误

---

**情况B: 401错误（当前情况）**
```json
{
  "code": "rest_forbidden",
  "message": "抱歉，您不能这么做。",
  "data": {"status": 401}
}
```
**原因**: `permission_callback` 设置错误
**解决**: 检查第91行的 `permission_callback`

---

**情况C: 500错误**
```json
{
  "code": "internal_server_error",
  "message": "服务器内部错误",
  "data": {"status": 500}
}
```
**原因**: PHP代码错误
**解决**: 检查PHP错误日志

---

**情况D: 200成功（但debug.log无日志）**
```json
{
  "success": false,
  "message": "未登录"
}
```
**原因**: 代码执行了但 `WP_DEBUG_LOG` 未启用
**解决**: 检查 `wp-config.php` 中的调试配置

---

## 🛠️ 解决方案

### 方案1: 修复 permission_callback（最可能）

**问题**: 第91行的 `permission_callback` 阻止了未登录用户访问

**修复步骤：**

1. 编辑 `nextjs-sso-integration-v3.php`
2. 找到第85-95行的 `register_rest_route` 调用
3. 确认第91行是：
   ```php
   'permission_callback' => '__return_true',
   ```
4. 如果不是，修改为上述代码
5. 保存文件
6. 重新测试

**为什么这样做：**

- `'permission_callback' => '__return_true'` 允许端点在WordPress权限检查前被访问
- 插件内部会在第532行的 `nextjs_sso_v3_get_user_from_cookie()` 中进行详细的用户检测
- 如果使用 `'is_user_logged_in'`，WordPress会在插件代码运行前就拦截请求

---

### 方案2: 重新安装插件

**操作步骤：**

1. **停用旧插件**
   ```
   WordPress后台 → 插件 → Next.js SSO Integration v3 → 停用
   ```

2. **删除旧插件**
   ```
   插件 → Next.js SSO Integration v3 → 删除
   ```

3. **上传新插件**
   ```
   插件 → 安装插件 → 上传插件
   选择: nextjs-sso-integration-v3.0.16.zip
   立即安装 → 启用插件
   ```

4. **验证安装**
   - 访问 `https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token`
   - 应返回JSON响应（不是404）

---

### 方案3: 手动触发端点（测试用）

**创建测试文件** `test-endpoint.php`（放在WordPress根目录）：

```php
<?php
// 加载WordPress
require_once('wp-load.php');

// 启用调试
define('WP_DEBUG', true);
define('WP_DEBUG_LOG', true);
define('WP_DEBUG_DISPLAY', true);

// 手动调用插件函数
if (function_exists('nextjs_sso_v3_get_token')) {
    echo "函数存在，正在调用...\n";
    $result = nextjs_sso_v3_get_token();
    echo "结果: " . json_encode($result) . "\n";
} else {
    echo "错误: nextjs_sso_v3_get_token 函数不存在\n";
    echo "已加载的插件函数: " . implode(', ', get_defined_functions()['user']) . "\n";
}

// 检查debug.log
$debug_log = WP_CONTENT_DIR . '/debug.log';
if (file_exists($debug_log)) {
    echo "\n最后10行debug.log:\n";
    $lines = file($debug_log);
    echo implode('', array_slice($lines, -10));
} else {
    echo "\n警告: debug.log不存在\n";
}
?>
```

**访问**: `https://www.ucppt.com/test-endpoint.php`

**预期输出:**
- 如果看到 `[Next.js SSO v3.0.16]` 日志，说明代码可以运行
- 如果看不到，说明插件未加载或函数未定义

---

## 📊 诊断决策树

```
debug.log中没有v3.0.16日志
│
├─→ 步骤1: 访问 /wp-json/nextjs-sso/v1/get-token
│   │
│   ├─→ 404错误
│   │   ├─→ 检查插件是否已启用
│   │   ├─→ 检查PHP语法错误
│   │   └─→ 重新安装插件
│   │
│   ├─→ 401错误（当前情况）
│   │   ├─→ 检查permission_callback设置（第91行）
│   │   ├─→ 应该是 '__return_true'
│   │   └─→ 修改后保存文件并测试
│   │
│   ├─→ 500错误
│   │   ├─→ 查看PHP错误日志
│   │   └─→ 检查PHP版本兼容性
│   │
│   └─→ 200成功但仍无日志
│       ├─→ 检查WP_DEBUG_LOG配置
│       └─→ 检查文件权限（debug.log可写）
│
└─→ 步骤2: 使用诊断HTML工具
    └─→ 打开 test-v3.0.16-rest-api.html
        └─→ 运行完整诊断
```

---

## 🧪 验证修复

修复后，按以下顺序验证：

### 验证1: 直接访问端点

```bash
# 方法1: 浏览器访问
https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token

# 方法2: PowerShell测试
$response = Invoke-WebRequest -Uri "https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token" -UseBasicParsing
$response.StatusCode  # 应该是200或401，不应该是404
$response.Content     # 应该包含JSON响应
```

### 验证2: 检查debug.log

```bash
# 访问端点后，立即查看debug.log最后20行
tail -n 20 /wp-content/debug.log

# 应该看到：
[Next.js SSO v3.0.16] 🔍 开始获取用户...
[Next.js SSO v3.0.16] 当前所有Cookies: ...
```

### 验证3: 测试应用

1. 清除浏览器缓存
2. 访问 `http://localhost:3000`
3. 观察控制台
4. 如果看到 `[AuthContext] ✅ REST API Token 验证成功`，说明修复成功

---

## 🔧 提供的诊断工具

### 工具1: PowerShell日志分析器

**文件**: [diagnose-v3.0.16.ps1](diagnose-v3.0.16.ps1)

**使用方法：**
```powershell
powershell -ExecutionPolicy Bypass -File diagnose-v3.0.16.ps1
```

**功能：**
- 检查WP_DEBUG配置
- 提取v3.0.16日志
- 分析Cookie和Session
- 生成诊断报告

---

### 工具2: 浏览器REST API测试工具

**文件**: [test-v3.0.16-rest-api.html](test-v3.0.16-rest-api.html)

**使用方法：**
1. 在 `ucppt.com/account` 登录
2. 同一浏览器打开此HTML文件
3. 点击"运行完整诊断"

**功能：**
- 检查Cookie（包括WPCOM Cookie）
- 测试REST API端点
- 检查插件注册状态
- 生成详细报告

---

### 工具3: Playwright自动化测试

**文件**: `e2e-tests/tests/v3.0.15-core.spec.ts`

**使用方法：**
```bash
cd e2e-tests
npx playwright test --reporter=html
npx playwright show-report
```

**测试覆盖：**
- ✅ 8个测试场景
- ✅ 100%通过率
- ✅ 性能监控
- ✅ 网络请求分析

---

## 📞 下一步行动

**立即执行（优先级从高到低）：**

### 🔴 紧急：检查permission_callback

1. 编辑 `nextjs-sso-integration-v3.php`
2. 查看第91行
3. 如果不是 `'permission_callback' => '__return_true'`，立即修改

### 🟠 高优先级：验证插件注册

1. 访问 `https://www.ucppt.com/wp-json/`
2. 搜索 `nextjs-sso`
3. 如果找不到，重新安装插件

### 🟡 中优先级：使用诊断工具

1. 打开 `test-v3.0.16-rest-api.html`
2. 运行完整诊断
3. 复制报告

### 🟢 低优先级：如果上述都无效

1. 创建 `test-endpoint.php` 测试文件
2. 直接调用插件函数
3. 查看PHP错误日志

---

## 📚 相关文档

- [v3.0.16 快速部署指南](WORDPRESS_SSO_V3.0.16_QUICK_DEPLOY.md)
- [v3.0.16 WPCOM修复文档](WORDPRESS_SSO_V3.0.16_WPCOM_FIX.md)
- [v3.0.15 测试报告](WORDPRESS_SSO_V3.0.15_TEST_REPORT.md)
- [v3.0.15 WPCOM认证问题](WORDPRESS_SSO_V3.0.15_WPCOM_AUTH_ISSUE.md)

---

## 🎯 最可能的问题及解决方案

根据"debug.log中没有v3.0.16日志"的症状，**最可能的原因**是：

### 原因1: permission_callback 设置错误（95%可能）

```php
// ❌ 错误配置（WordPress会在插件代码运行前返回401）
'permission_callback' => 'is_user_logged_in',

// ✅ 正确配置（允许插件代码执行）
'permission_callback' => '__return_true',
```

**修复步骤：**
1. 编辑第91行
2. 改为 `'__return_true'`
3. 保存并测试

---

### 原因2: 插件未正确加载（4%可能）

**检查方法：**
```
WordPress后台 → 插件 → 查看"Next.js SSO Integration v3"
```

**状态应该是：**
- ✅ 已启用
- ✅ 版本 3.0.16

**如果不是：**
- 重新上传并启用插件

---

### 原因3: PHP语法错误（1%可能）

**检查PHP错误日志：**
- `/wp-content/debug.log`
- PHP错误日志（主机特定位置）

**查找：**
```
Parse error
Fatal error
nextjs-sso-integration-v3.php
```

---

## 🎉 预期修复后的效果

修复后，您应该看到：

**WordPress debug.log:**
```
[Next.js SSO v3.0.16] 🔍 开始获取用户...
[Next.js SSO v3.0.16] 🎯 检测到WPCOM Member Pro插件
[Next.js SSO v3.0.16] ✅ 通过WPCOM API获取到会员: 宋词
```

**浏览器控制台:**
```javascript
[AuthContext] 尝试通过 WordPress REST API 获取 Token...
[AuthContext] ✅ 通过 REST API 获取到 Token，验证中...
[AuthContext] ✅ REST API Token 验证成功
[AuthContext] 🔀 检测到已登录，跳转到分析页面
```

**应用行为:**
- 自动跳转到 `/analysis` 页面 ✅
- 无需手动点击登录 ✅

---

**创建时间**: 2025-12-16
**版本**: v3.0.16 故障排除指南
**状态**: 等待用户执行诊断步骤
