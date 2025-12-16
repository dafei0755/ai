# v3.0.17 部署快速参考卡

## 📦 文件准备

✅ **文件**: `nextjs-sso-integration-v3.0.17.zip`
✅ **大小**: 18,199 字节
✅ **位置**: 项目根目录

---

## 🚀 5步部署（3分钟）

### 1. 停用旧插件
```
WordPress后台 → 插件 → Next.js SSO Integration v3 → 停用
```

### 2. 删除旧插件
```
插件列表 → Next.js SSO Integration v3 → 删除
```

### 3. 上传新插件
```
插件 → 安装插件 → 上传插件 → nextjs-sso-integration-v3.0.17.zip
```

### 4. 启用插件
```
立即安装 → 启用插件
```

### 5. 验证版本
```
确认插件列表显示: v3.0.17 ✅
```

---

## ✅ 3步验证（3分钟）

### 验证1: REST API
```
访问: https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token
预期: 返回 200 OK (不是401)
```

### 验证2: debug.log
```
查看: /wp-content/debug.log
查找: [Next.js SSO v3.0.17]
```

### 验证3: 登录测试
```
1. 在 ucppt.com/account 登录
2. 清除浏览器缓存
3. 访问 localhost:3000
预期: 自动跳转到 /analysis ✅
```

---

## 🎯 成功标志

- ✅ REST API返回200（不是401）
- ✅ debug.log有v3.0.17日志
- ✅ 已登录自动进入应用
- ✅ 未登录正常登录流程

---

## 📞 需要帮助？

**完整指南**: [WORDPRESS_SSO_V3.0.17_DEPLOYMENT_CHECKLIST.md](WORDPRESS_SSO_V3.0.17_DEPLOYMENT_CHECKLIST.md)

**诊断报告**: [WORDPRESS_SSO_V3.0.16_FULL_DIAGNOSIS.md](WORDPRESS_SSO_V3.0.16_FULL_DIAGNOSIS.md)
