# 会员 API 500 错误调试指南

## 🔍 已添加的调试日志

### 1. member_routes.py
- ✅ 请求开始日志
- ✅ 当前用户信息
- ✅ WordPress API 调用日志
- ✅ 返回结果详细输出

### 2. wpcom_member_api.py
- ✅ Token 获取过程日志
- ✅ API 请求 URL
- ✅ 响应状态码
- ✅ 错误详情输出
- ✅ 完整的 traceback

## 🚀 重启后端服务

```bash
# 停止当前运行的服务 (Ctrl+C)

# 重新启动
python -B -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000
```

## 📊 预期日志输出

### 成功的情况：

```
[MemberRoutes] 🔍 开始获取会员信息...
[MemberRoutes] 当前用户信息: {'user_id': 1, 'username': '8pdwoxj8', ...}
[MemberRoutes] 📡 正在调用 WordPress API 获取用户 1 的会员信息...
[WPCOM API] 🔍 开始请求...
[WPCOM API] Endpoint: /custom/v1/user-membership/1
[WPCOM API] 🔑 请求 JWT Token...
[WPCOM API] URL: https://www.ucppt.com/wp-json/simple-jwt-login/v1/auth
[WPCOM API] Username: 8pdwoxj8
[WPCOM API] Token 响应状态码: 200
[WPCOM API] ✅ Token 获取成功
[WPCOM API] 📞 请求 URL: https://www.ucppt.com/wp-json/custom/v1/user-membership/1
[WPCOM API] 🚀 发送 GET 请求...
[WPCOM API] 📩 响应状态码: 200
[WPCOM API] ✅ 请求成功，返回数据
[MemberRoutes] ✅ WordPress API 返回结果: {...}
```

### 失败的情况（会显示详细错误）：

```
[WPCOM API] ❌ Token 获取失败: ...
或
[WPCOM API] ⏱️ 请求超时: ...
或
[WPCOM API] ❌ 请求失败: 404
[WPCOM API] 错误详情: {"message": "No route was found..."}
```

## 🔧 可能的错误原因

### 1. Token 获取失败
- **问题**: Simple JWT Login 插件未激活或配置错误
- **检查**: WordPress 后台 → 插件 → Simple JWT Login

### 2. API 端点不存在 (404)
- **问题**: WPCOM Custom API 插件未激活
- **检查**: WordPress 后台 → 插件 → WPCOM Member Custom API

### 3. 请求超时
- **问题**: WordPress 服务器响应慢或网络问题
- **解决**: 增加 timeout 或检查服务器性能

### 4. SSL 证书错误
- **已处理**: 代码中已禁用 SSL 验证 (`verify=False`)

## 📝 下一步

1. **重启后端服务**
2. **刷新前端页面** (触发会员 API 请求)
3. **查看终端日志** (会显示详细的调试信息)
4. **根据日志定位具体问题**

## 🎯 修复策略

根据日志输出的错误类型：

| 错误类型 | 修复方法 |
|---------|---------|
| Token 获取失败 | 检查 Simple JWT Login 插件 + 用户名密码 |
| 404 Not Found | 激活 WPCOM Custom API 插件 |
| 401 Unauthorized | 检查 Token 权限设置 |
| 超时 | 增加 timeout 或优化 WordPress 性能 |
| 其他错误 | 根据详细日志分析 |
