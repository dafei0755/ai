# WordPress 插件 v2.5 部署清单（缓存清除版）

## 问题诊断

**症状**：插件版本显示为 2.5.0，但登录界面仍然是旧版本的样式

**根本原因**：
1. WordPress OPcache 缓存了旧的 PHP 代码
2. 有重复的插件导致冲突
3. 短代码缓存未刷新

## 完整部署步骤

### 1. 彻底删除所有旧插件

**WordPress 后台 → 插件 → 已安装插件**：

1. 找到所有 "Next.js SSO Integration" 插件（可能有 2 个）
2. 逐个点击"停用"
3. 停用后点击"删除"
4. 确认删除所有相关文件

**验证**：刷新插件页面，确保没有任何 "Next.js SSO Integration" 插件。

### 2. 清除 PHP OPcache（关键步骤）

**方法 1：通过 WordPress 插件**

如果您安装了缓存插件（如 WP Super Cache、W3 Total Cache、LiteSpeed Cache），请：

1. 进入缓存插件设置
2. 找到"清除 OPcache"或"清除所有缓存"选项
3. 点击清除

**方法 2：通过 PHP 代码（推荐）**

在 WordPress 网站根目录创建临时文件 `clear-cache.php`：

```php
<?php
// 临时缓存清除脚本
if (function_exists('opcache_reset')) {
    opcache_reset();
    echo "OPcache cleared successfully!";
} else {
    echo "OPcache not enabled.";
}

// 清除 WordPress 对象缓存
if (function_exists('wp_cache_flush')) {
    wp_cache_flush();
    echo " WordPress cache cleared!";
}
?>
```

然后访问：`https://www.ucppt.com/clear-cache.php`

看到 "OPcache cleared successfully!" 后，删除该文件。

**方法 3：通过 .htaccess（Apache 服务器）**

在网站根目录的 `.htaccess` 文件末尾添加（临时）：

```apache
# 临时禁用 OPcache
php_flag opcache.enable Off
```

刷新页面后，再删除这行配置。

**方法 4：重启 PHP-FPM（最彻底）**

如果您有服务器访问权限：

```bash
# Ubuntu/Debian
sudo systemctl restart php8.1-fpm

# CentOS/RHEL
sudo systemctl restart php-fpm
```

### 3. 上传新版插件

1. **插件 → 安装插件 → 上传插件**
2. 选择 **`nextjs-sso-integration-v2.5-clean.zip`**（新生成的干净版本）
3. 点击"现在安装"
4. 安装完成后点击"激活插件"

### 4. 验证插件版本

**WordPress 后台 → 插件 → 已安装插件**：

- 应该只有 **1 个** "Next.js SSO Integration" 插件
- 版本号：**2.5.0**
- 描述：WordPress 单点登录集成 Next.js（**v2.5 - 原生登录弹窗版**）

### 5. 强制刷新 WordPress 短代码

**WordPress 后台 → 页面**：

1. 找到 `https://www.ucppt.com/nextjs` 页面
2. 点击"编辑"
3. 不做任何修改，直接点击"更新"

这会强制 WordPress 重新解析短代码。

### 6. 重新保存固定链接

**WordPress 后台 → 设置 → 固定链接**：

1. 无需修改任何设置
2. 直接点击"保存更改"

### 7. 清除浏览器缓存

在浏览器中访问 `https://www.ucppt.com/nextjs`：

- **Windows**: `Ctrl + Shift + R` 或 `Ctrl + F5`
- **Mac**: `Cmd + Shift + R`

或者使用**隐身窗口**重新访问。

## 验证步骤

### 1. 检查插件设置页面

访问 **WordPress 后台 → 设置 → Next.js SSO**：

应该看到：
- Next.js 回调 URL
- Next.js 应用 URL
- 测试 SSO 登录

### 2. 检查前台登录界面

1. 在隐身窗口访问 `https://www.ucppt.com/nextjs`
2. 应该看到登录引导卡片
3. **右键点击"立即登录"按钮 → 检查元素**

**正确的代码应该是**：

```html
<button id="nextjs-login-button" type="button" style="...">
    立即登录
</button>

<script>
(function() {
    document.getElementById('nextjs-login-button').addEventListener('click', function() {
        // 登录触发器代码
    });
})();
</script>
```

**如果仍然是**：

```html
<a href="https://www.ucppt.com/wp-login.php?redirect_to=...">
    立即登录
</a>
```

说明缓存未清除，请重新执行步骤 2。

### 3. 测试登录触发器

打开浏览器控制台（F12），在 Console 标签输入：

```javascript
// 检查登录按钮是否存在
console.log(document.getElementById('nextjs-login-button'));
// 应该输出: <button id="nextjs-login-button" ...>

// 检查主题登录 API
console.log(window.ucpptLogin);
// 如果输出 undefined，说明主题不支持登录弹窗（正常，会降级）

// 手动触发登录
document.getElementById('nextjs-login-button').click();
```

## 常见问题排查

### Q1: 插件上传后仍然显示旧版本

**A**: 清除 WordPress 对象缓存

```bash
# 通过 WP-CLI（如果安装了）
wp cache flush
```

### Q2: 代码检查是 `<button>` 但点击无反应

**A**: JavaScript 可能有错误，打开控制台查看红色错误信息

### Q3: 点击后跳转到登录页面而不是弹窗

**A**: 这是正常的降级行为，说明 WordPress 主题不支持 `window.ucpptLogin` API

### Q4: 仍然看到两个重复的插件

**A**: 手动删除插件文件

通过 FTP 或文件管理器，删除：
```
/wp-content/plugins/nextjs-sso-integration/
/wp-content/plugins/nextjs-sso-integration-v2.1-fixed/
```

然后重新上传插件。

## 成功标准 ✅

- [ ] 只有 1 个 "Next.js SSO Integration" 插件（v2.5.0）
- [ ] 右键"立即登录"按钮，检查元素显示 `<button>` 而不是 `<a>`
- [ ] 浏览器控制台无 JavaScript 错误
- [ ] 点击登录按钮有响应（弹窗或跳转）

## 如果以上步骤都无效

请提供以下信息：

1. **浏览器控制台截图**（F12 → Console 标签）
2. **检查元素截图**（右键"立即登录" → 检查）
3. **WordPress 缓存插件名称**（如果有）
4. **服务器环境**（Apache/Nginx，PHP 版本）

我会根据具体情况提供进一步的解决方案。

## 备用方案：直接修改 WordPress 数据库

如果 OPcache 实在无法清除，可以临时修改插件文件名强制刷新：

1. 通过 FTP 进入 `/wp-content/plugins/`
2. 将 `nextjs-sso-integration` 文件夹重命名为 `nextjs-sso-integration-new`
3. 在 WordPress 后台重新激活插件
4. 这会强制 WordPress 重新加载 PHP 文件
