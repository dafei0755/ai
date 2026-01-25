# 🐛 WordPress 登录死循环问题诊断报告

## 📊 问题描述
用户报告 WordPress 登录后出现死循环现象。

## 🔍 根本原因分析

### 问题1: 跨域环境下的退出检测误判
**文件**: `frontend-nextjs/contexts/AuthContext.tsx` Line 152-255

**问题代码**:
```tsx
// 情况2：WordPress已退出，但本地仍有用户 → 清除Token
if (!data.logged_in && localUserId) {
    const isLocalDev = window.location.hostname === 'localhost' ||
                       window.location.hostname === '127.0.0.1';

    if (isLocalDev) {
        console.log('[AuthContext v3.0.24] ⏳ 本地开发环境，跳过 WordPress 退出检测（跨域限制）');
        return;
    }
    // ... 清除Token逻辑
}
```

**死循环机制**:
1. 用户在 `https://www.ucppt.com` 登录，获取Token
2. Token保存到 `localStorage`
3. 前端每10秒调用 `sync-status` API 检测登录状态
4. **关键问题**: `sync-status` API依赖Cookie进行身份验证
5. 跨域环境下（localhost ↔ ucppt.com），Cookie无法正确发送
6. API始终返回 `logged_in: false`
7. 虽然有 `isLocalDev` 保护，但**用户访问 ucppt.com 时没有此保护**
8. Token被误清除 → 用户被踢出 → 重新登录 → 再次被踢出 → **死循环**

### 问题2: 页面刷新导致的循环
**文件**: `frontend-nextjs/contexts/AuthContext.tsx` Line 183

**问题代码**:
```tsx
if (tokenResponse.ok) {
    const tokenData = await tokenResponse.json();
    if (tokenData.token && tokenData.user) {
        saveTokenWithTimestamp(tokenData.token, tokenData.user);
        setUser(tokenData.user);

        // 刷新页面以确保所有组件同步
        window.location.reload();  // ❌ 危险：可能触发死循环
    }
}
```

**死循环机制**:
- 检测到用户切换 → 获取新Token → **强制刷新页面**
- 刷新后再次检测 → 又发现"用户切换" → 再次刷新 → **无限循环**

### 问题3: 定时检查冲突
**文件**: `frontend-nextjs/contexts/AuthContext.tsx`

存在**三个**独立的定时检查机制：

1. **每30秒检查设备状态** (Line 93-102):
   ```tsx
   checkDeviceKicked(); // 初始检查
   const interval = setInterval(checkDeviceKicked, 30000);
   ```

2. **每10秒检查SSO状态** (Line 272-276):
   ```tsx
   const pollInterval = setInterval(() => {
       checkSSOStatus();
   }, 10000);
   ```

3. **页面可见性变化时检查** (Line 264-269):
   ```tsx
   document.addEventListener('visibilitychange', handleVisibilityChange);
   ```

**潜在问题**:
- 多个定时器可能同时触发Token清除
- 竞态条件导致状态不一致
- 频繁的API请求增加服务器压力

---

## 🎯 解决方案

### 修复1: 增强跨域环境检测（高优先级）⭐⭐⭐

**修改位置**: `AuthContext.tsx` Line 164-220

**修复逻辑**:
```tsx
// 情况2：WordPress已退出，但本地仍有用户 → 清除Token
if (!data.logged_in && localUserId) {
    // 🔧 v7.129.2 修复：增强跨域检测，防止误清除Token
    const currentHost = window.location.hostname;
    const apiHost = new URL('https://www.ucppt.com').hostname;

    // 检测是否跨域（任何非WordPress主域名都视为跨域）
    const isCrossDomain = currentHost !== apiHost &&
                          currentHost !== 'www.ucppt.com' &&
                          currentHost !== 'ucppt.com';

    if (isCrossDomain) {
        console.log('[AuthContext v7.129.2] ⏭️ 跨域环境，跳过退出检测');
        console.log(`  当前域名: ${currentHost}, WordPress域名: ${apiHost}`);
        return;
    }

    // 剩余的退出检测逻辑...
}
```

**改进点**:
- 不仅检测 `localhost`，而是**所有非WordPress主域名**
- 包括生产环境的自定义域名
- 明确日志输出，便于调试

---

### 修复2: 移除危险的页面刷新（高优先级）⭐⭐⭐

**修改位置**: `AuthContext.tsx` Line 183

**修复逻辑**:
```tsx
if (tokenResponse.ok) {
    const tokenData = await tokenResponse.json();
    if (tokenData.token && tokenData.user) {
        console.log('[AuthContext v7.129.2] ✅ 成功获取新用户Token');
        console.log('[AuthContext v7.129.2] 新用户:', tokenData.user);

        saveTokenWithTimestamp(tokenData.token, tokenData.user);
        setUser(tokenData.user);

        // ❌ 移除：window.location.reload();
        // ✅ 改为：发送事件通知，让组件自行响应
        window.dispatchEvent(new CustomEvent('auth-token-updated', {
            detail: { user: tokenData.user }
        }));
    }
}
```

**改进点**:
- 移除强制页面刷新
- 使用事件通知机制
- 让需要同步的组件自行监听事件并更新

---

### 修复3: 合并定时检查逻辑（中优先级）⭐⭐

**修改位置**: `AuthContext.tsx` Line 93-289

**修复逻辑**:
```tsx
// 🔧 v7.129.2: 统一定时检查逻辑，避免冲突
useEffect(() => {
    let lastCheckTime = 0;
    const MIN_CHECK_INTERVAL = 5000; // 最小5秒间隔，防止频繁检查

    const unifiedCheck = async () => {
        const now = Date.now();
        if (now - lastCheckTime < MIN_CHECK_INTERVAL) {
            return; // 跳过过于频繁的检查
        }
        lastCheckTime = now;

        // 按顺序执行检查
        await checkDeviceKicked();   // 1. 设备状态
        await checkSSOStatus();       // 2. SSO状态
    };

    // 初始检查
    unifiedCheck();

    // 页面可见性变化时检查
    const handleVisibilityChange = () => {
        if (document.visibilityState === 'visible') {
            console.log('[AuthContext v7.129.2] 📄 页面重新可见，检测状态');
            unifiedCheck();
        }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // 统一定期检查（每30秒）
    const interval = setInterval(unifiedCheck, 30000);

    return () => {
        document.removeEventListener('visibilitychange', handleVisibilityChange);
        clearInterval(interval);
    };
}, [checkDeviceKicked]); // 添加依赖
```

**改进点**:
- 合并三个定时器为一个
- 增加最小检查间隔保护
- 减少API请求次数
- 避免竞态条件

---

## 🧪 测试验证

### 测试场景1: 跨域登录
```
1. 在 https://www.ucppt.com 登录
2. 打开 http://localhost:3000 (已登录状态)
3. 等待2分钟，观察是否被踢出
4. 预期：不会被踢出（跨域保护生效）
```

### 测试场景2: 同域退出
```
1. 在 https://www.ucppt.com 登录
2. 在同一域名下退出登录
3. 观察前端是否正确清除Token
4. 预期：Token被清除，显示未登录状态
```

### 测试场景3: 用户切换
```
1. 以用户A登录
2. 在WordPress后台切换为用户B
3. 前端检测到用户切换
4. 预期：自动更新Token，不刷新页面
```

---

## 📝 日志监控

修复后，关键日志应显示：

### 正常跨域登录：
```
[AuthContext v7.129.2] ⏭️ 跨域环境，跳过退出检测
  当前域名: localhost, WordPress域名: www.ucppt.com
```

### 用户切换：
```
[AuthContext v7.129.2] ✅ 成功获取新用户Token
[AuthContext v7.129.2] 新用户: { username: '新用户名', ... }
[AuthContext v7.129.2] 🔔 发送 auth-token-updated 事件
```

### 统一检查：
```
[AuthContext v7.129.2] 📄 页面重新可见，检测状态
[AuthContext v7.129.2] ⏳ 距离上次检查不足5秒，跳过
```

---

## ⚠️ 风险评估

### 低风险修复
- ✅ 增强跨域检测 - 仅扩展现有逻辑
- ✅ 移除页面刷新 - 改用事件机制

### 中风险修复
- ⚠️ 合并定时器 - 可能影响现有依赖此逻辑的组件
- ⚠️ 建议：分阶段部署，先修复高优先级问题

---

## 📋 实施顺序

1. **第一阶段（紧急）**: 修复1 + 修复2 ⭐⭐⭐
   - 解决死循环核心问题
   - 风险低，收益高

2. **第二阶段（优化）**: 修复3 ⭐⭐
   - 优化性能和稳定性
   - 需要更全面的测试

3. **第三阶段（监控）**:
   - 部署后监控日志
   - 收集用户反馈
   - 必要时回滚

---

## 🔗 相关文件
- `frontend-nextjs/contexts/AuthContext.tsx` - 主要修改文件
- `intelligent_project_analyzer/services/wordpress_jwt_service.py` - 后端JWT服务
- `intelligent_project_analyzer/api/server.py` - `/api/auth/check-device` 端点

---

**诊断完成时间**: 2026-01-04
**修复优先级**: P0 (最高)
**预计修复时间**: 30分钟
