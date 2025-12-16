# WPCOM自定义登录400错误诊断报告

**问题发现时间**: 2025-12-16
**问题严重程度**: 🔴 高危
**影响范围**: 所有使用WPCOM自定义登录的用户
**涉及版本**: WordPress SSO v3.0.17 + WPCOM Member Pro

---

## 🔍 问题现象

### 用户反馈的完整流程

1. 用户访问 `localhost:3000`（未登录状态）
2. 看到"请先登录以使用应用"界面
3. 点击"立即登录"按钮
4. 跳转到 `https://www.ucppt.com/login`（WPCOM自定义登录页面）
5. 输入账号密码后点击登录
6. **显示"请求失败"** ❌
7. 浏览器控制台错误: `POST https://www.ucppt.com/wp-json/mwp-sign-sign.php 400 (Bad Request)`

### 关键信息

- **失败的API端点**: `/wp-json/mwp-sign-sign.php`
- **HTTP状态码**: 400 Bad Request
- **错误类型**: 请求参数错误或格式错误
- **WPCOM功能**: 支持微信登录、手机短信登录（标准WordPress登录不支持）

---

## 🎯 问题分析

### 为什么不能改用WordPress标准登录

**用户明确要求**: "！！我不希望用WordPress标准登录，WPCOM自定义登录拥有标准登录没有的微信登录和手机短信登录"

**WPCOM Member Pro的独特优势**:
- ✅ **微信快捷登录** - 扫码登录，无需输入密码
- ✅ **手机短信登录** - 验证码登录，更安全便捷
- ✅ **统一会员中心** - `/account` 页面管理会员信息
- ✅ **会员等级系统** - 与WPCOM Member Pro深度集成

**WordPress标准登录的局限**:
- ❌ 仅支持账号密码登录
- ❌ 无法使用微信登录
- ❌ 无法使用手机短信登录
- ❌ 与WPCOM会员系统脱节

---

## 🔧 可能的原因

### 原因1: WPCOM Member Pro API端点配置问题

**分析**:
- `/wp-json/mwp-sign-sign.php` 不是标准的WordPress REST API路径格式
- 正常的REST API路径应该是 `/wp-json/{namespace}/{version}/{endpoint}`
- 例如: `/wp-json/wpcom-member/v1/login`
- `mwp-sign-sign.php` 看起来像是直接执行PHP文件，这可能不符合WordPress REST API规范

**验证方法**:
```bash
# 访问WPCOM Member Pro的实际API端点
curl -X GET https://www.ucppt.com/wp-json/

# 查看所有可用的REST API路由
# 检查是否有 wpcom-member、member-pro 等相关namespace
```

### 原因2: 登录接口参数缺失或格式错误

**分析**:
- 400 Bad Request通常表示请求参数有问题
- WPCOM Member Pro可能需要特定的参数格式
- 可能缺少CSRF token或nonce验证

**需要检查的参数**:
- 用户名/手机号
- 密码/验证码
- nonce（WordPress安全令牌）
- redirect_to（登录后跳转地址）
- 登录类型（密码/短信/微信）

### 原因3: WPCOM Member Pro插件版本或配置问题

**分析**:
- WPCOM Member Pro可能未正确配置
- 手机快捷登录功能可能未启用
- API端点可能被禁用或限制

**验证方法**:
1. WordPress后台 → WPCOM Member Pro设置
2. 检查"手机快捷登录"是否启用
3. 检查"微信登录"是否配置
4. 查看WPCOM Member Pro错误日志

### 原因4: WordPress REST API路由冲突

**分析**:
- WPCOM Member Pro的自定义REST API端点可能与其他插件冲突
- `mwp-sign-sign.php` 路径不符合REST API规范，可能被WordPress拦截

**验证方法**:
```php
// 在WordPress debug.log中查找
[REST API] Route registration error
[WPCOM] API endpoint conflict
```

---

## 💡 推荐解决方案

### 方案A: 检查WPCOM Member Pro REST API端点（推荐 ⭐⭐⭐⭐⭐）

**步骤**:

1. **获取WPCOM Member Pro的正确API端点**:
   ```bash
   # 访问WordPress REST API索引
   curl https://www.ucppt.com/wp-json/
   ```

   查找类似以下的端点:
   - `/wp-json/wpcom-member/v1/login`
   - `/wp-json/member-pro/v1/auth`
   - `/wp-json/wpcom/v1/sign-in`

2. **更新WPCOM登录页面的API调用**:
   - 在 `https://www.ucppt.com/login` 页面中
   - 将 `POST /wp-json/mwp-sign-sign.php`
   - 改为正确的REST API端点

3. **验证新端点**:
   ```bash
   curl -X POST https://www.ucppt.com/wp-json/wpcom-member/v1/login \
     -H "Content-Type: application/json" \
     -d '{"username":"test","password":"test"}'
   ```

**优势**:
- ✅ 使用标准REST API路径
- ✅ 保留WPCOM所有功能（微信、短信登录）
- ✅ 符合WordPress最佳实践
- ✅ 更容易调试和维护

---

### 方案B: 检查WPCOM Member Pro配置（备选 ⭐⭐⭐⭐）

**步骤**:

1. **WordPress后台检查**:
   ```
   WordPress后台 → 插件 → WPCOM Member Pro → 设置
   ```

2. **启用手机快捷登录**:
   - 找到"登录设置"或"认证设置"
   - 确保"手机快捷登录"已启用
   - 确保"API登录接口"已启用

3. **检查短信服务配置**:
   - 如果使用手机短信登录，需要配置短信服务商
   - 常见服务商: 阿里云、腾讯云、华为云
   - 确认短信API密钥已正确配置

4. **查看WPCOM错误日志**:
   ```bash
   # 查看WordPress debug.log
   tail -f /wp-content/debug.log | grep -i "wpcom\|member"
   ```

**优势**:
- ✅ 不需要修改代码
- ✅ 可能是配置问题，容易解决
- ✅ 保留所有WPCOM功能

---

### 方案C: 联系WPCOM Member Pro技术支持（如果A、B都无效 ⭐⭐⭐）

**步骤**:

1. **收集诊断信息**:
   - WordPress版本号
   - WPCOM Member Pro版本号
   - PHP版本号
   - 完整的400错误信息
   - debug.log相关日志

2. **联系WPCOM技术支持**:
   - 说明 `/wp-json/mwp-sign-sign.php` 返回400错误
   - 提供上述诊断信息
   - 询问正确的API端点和参数格式

3. **请求官方文档**:
   - WPCOM Member Pro REST API文档
   - 手机快捷登录集成指南
   - API参数说明

---

## 🔍 立即诊断步骤

### 第1步: 检查WPCOM REST API端点（2分钟）

在浏览器中访问:
```
https://www.ucppt.com/wp-json/
```

**查找**:
- `wpcom-member`
- `member-pro`
- `wpcom`
- 任何与登录相关的端点

**记录下所有找到的端点路径**

---

### 第2步: 检查WPCOM Member Pro版本和配置（3分钟）

1. WordPress后台 → 插件 → 已安装的插件
2. 找到"WPCOM Member Pro"
3. 记录版本号
4. 点击"设置" → 检查"登录设置"

**重点检查**:
- [ ] 手机快捷登录是否启用
- [ ] 微信登录是否配置
- [ ] API接口是否启用
- [ ] 短信服务是否配置

---

### 第3步: 查看浏览器Network面板（2分钟）

1. 打开浏览器开发者工具（F12）
2. 切换到Network标签
3. 访问 `https://www.ucppt.com/login`
4. 输入账号密码点击登录
5. 查看失败的POST请求

**记录**:
- 请求URL（完整路径）
- 请求Method（POST/GET）
- 请求Headers
- 请求Payload（请求参数）
- 响应Status（400）
- 响应Body（错误详情）

---

### 第4步: 查看WordPress debug.log（2分钟）

```bash
# 查看最后100行日志
tail -100 /wp-content/debug.log

# 或者搜索WPCOM相关日志
grep -i "wpcom\|member" /wp-content/debug.log | tail -50
```

**查找关键信息**:
- WPCOM插件错误
- REST API错误
- 登录失败日志
- 参数验证错误

---

## 📊 诊断信息收集表

请填写以下信息以便进一步诊断:

### WordPress环境信息

- [ ] WordPress版本: ___________
- [ ] PHP版本: ___________
- [ ] WPCOM Member Pro版本: ___________
- [ ] 其他安全插件: ___________

### API端点信息

- [ ] 访问 `https://www.ucppt.com/wp-json/` 的结果:
  ```json
  {
    "找到的相关端点": [
      "..."
    ]
  }
  ```

### Network请求详情

- [ ] 失败的请求URL: ___________
- [ ] 请求Method: ___________
- [ ] 请求Headers:
  ```
  Content-Type: ___________
  Cookie: ___________
  ```
- [ ] 请求Payload:
  ```json
  {
    "username": "...",
    "password": "..."
  }
  ```
- [ ] 响应Body:
  ```json
  {
    "error": "..."
  }
  ```

### WPCOM配置

- [ ] 手机快捷登录: 已启用 / 未启用
- [ ] 微信登录: 已配置 / 未配置
- [ ] 短信服务: 已配置 / 未配置
- [ ] API接口: 已启用 / 未启用

---

## 🎯 预期结果

完成诊断后，我们应该能够:

1. ✅ 找到WPCOM Member Pro的正确REST API端点
2. ✅ 了解400错误的具体原因（参数错误/配置错误/端点错误）
3. ✅ 修复登录接口，使WPCOM自定义登录正常工作
4. ✅ 保留微信登录和手机短信登录功能

---

## 📝 下一步行动

### 立即执行

1. **访问** `https://www.ucppt.com/wp-json/` 查看可用的REST API端点
2. **检查** WPCOM Member Pro的版本和配置
3. **查看** 浏览器Network面板的详细请求信息
4. **填写** 上述诊断信息收集表

### 根据诊断结果

- **如果找到正确的API端点** → 更新WPCOM登录页面的API调用
- **如果是配置问题** → 在WordPress后台启用相关功能
- **如果是WPCOM插件Bug** → 联系WPCOM技术支持或寻找替代方案

---

**创建时间**: 2025-12-16
**状态**: 🔍 诊断中
**优先级**: 🔴 高优先级
**负责人**: 需要用户协助提供诊断信息
