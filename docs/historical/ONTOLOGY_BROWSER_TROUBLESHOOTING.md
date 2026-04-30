# 本体论浏览器问题诊断指南

## ✅ 后端API测试结果

已验证后端API完全正常：
- ✅ 框架列表API: 返回13个框架
- ✅ 框架详情API: 正常返回类别和维度
- ✅ 搜索API: 正常工作

## 🔍 前端诊断步骤

### 1. 刷新前端页面
确保使用最新的前端代码：
```bash
# 如果前端正在运行，按 Ctrl+C 停止
# 然后重新启动
cd frontend-nextjs
npm run dev
```

### 2. 打开浏览器开发者工具
1. 访问 http://localhost:3001/admin/ontology
2. 按 `F12` 打开开发者工具
3. 切换到 **Console** 标签页

### 3. 点击框架名称并观察日志

**正常情况下应该看到：**
```
🔍 正在加载框架详情: meta_framework
✅ 框架详情加载成功: {id: "meta_framework", name: "通用元框架", categories: Array(2)}
```

**如果出现错误，可能看到：**
```
❌ 加载框架详情失败: [错误信息]
```

### 4. 常见问题排查

#### 问题A: 401 Unauthorized (未授权)
**现象：** Console显示 401 错误
**原因：** 未登录或token过期
**解决：**
1. 访问 https://www.ucppt.com/nextjs 登录WordPress
2. 登录成功后会自动跳转回前端
3. 检查 localStorage 中是否有 `wp_jwt_token`

#### 问题B: 404 Not Found
**现象：** API路径找不到
**原因：** 后端服务器未启动或端口不对
**解决：**
```bash
# 启动后端服务器
python -B scripts\run_server_production.py
```

#### 问题C: Network Error
**现象：** 网络错误
**原因：** 后端服务器未运行或端口被占用
**解决：**
1. 检查后端是否在 http://localhost:8000 运行
2. 访问 http://localhost:8000/docs 查看API文档

#### 问题D: CORS Error
**现象：** 跨域错误
**原因：** 跨域配置问题
**解决：** 这种情况很少见，因为next.config.mjs已经配置了代理

### 5. 测试API可访问性

在浏览器Console中运行：
```javascript
// 测试框架列表
fetch('/api/admin/ontology/frameworks', {
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('wp_jwt_token')
  }
})
  .then(r => r.json())
  .then(d => console.log('✅ 框架列表:', d))
  .catch(e => console.error('❌ 错误:', e));

// 测试框架详情
fetch('/api/admin/ontology/framework/meta_framework', {
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('wp_jwt_token')
  }
})
  .then(r => r.json())
  .then(d => console.log('✅ 框架详情:', d))
  .catch(e => console.error('❌ 错误:', e));
```

## 🎯 前端代码更新说明

已对 `/admin/ontology/page.tsx` 进行以下改进：

### 1. 添加加载状态
- 框架列表加载时显示加载动画
- 点击框架加载详情时按钮禁用并显示等待状态
- 详情加载期间显示"加载中..."提示

### 2. 添加错误提示
- 顶部显示错误消息（红色文字）
- 加载失败时弹出alert提示
- Console中输出详细的调试日志

### 3. 添加调试日志
所有API调用都会在Console中显示：
- 🔍 开始加载
- ✅ 加载成功（附带数据）
- ❌ 加载失败（附带错误详情）

## 📝 操作步骤总结

1. **确保后端运行**：http://localhost:8000
2. **确保前端运行**：http://localhost:3001
3. **登录WordPress**：https://www.ucppt.com/nextjs
4. **访问本体论页面**：http://localhost:3001/admin/ontology
5. **打开Console（F12）**
6. **点击任意框架**（如"通用元框架"）
7. **查看Console日志和页面反应**
8. **如有错误，根据错误信息对照上述常见问题排查**

## 💡 快速验证

如果一切正常，点击"通用元框架"后应该看到：
- 左侧出现两个类别：
  - 📂 通用维度 (6个维度)
  - 📂 当代命题 (6个维度)
- 点击类别可展开查看维度列表
- 点击维度名称，右侧显示详细信息

---

**最后更新：** 2026-02-11
**版本：** v1.0
