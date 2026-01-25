# 历史记录问题诊断和解决方案

## 🔍 问题诊断 (2026-01-04 16:05)

### 问题表现
1. ❌ 启动分析失败
2. ❌ 无历史对话记录显示

### 根本原因

#### 1. **API端口配置错误** ✅ 已修复
- **问题**: `.env.local` 配置的API端口是 `8001`，但后端运行在 `8000`
- **影响**: 前端无法连接后端API，导致所有请求失败
- **修复**: 已将 `NEXT_PUBLIC_API_URL` 从 `http://127.0.0.1:8001` 改为 `http://127.0.0.1:8000`

#### 2. **历史记录需要登录** 🔐 设计要求
- **原因**: `/api/sessions` 端点需要JWT认证 (`Depends(get_current_user)`)
- **表现**: 未登录用户看到"无历史记录"是**正常行为**
- **代码位置**: `frontend-nextjs/app/page.tsx:207-218`
  ```typescript
  useEffect(() => {
    // 🔒 安全检查：只有已登录用户才能获取会话列表
    if (!user) {
      console.log('[HomePage] 用户未登录，清空会话列表');
      setSessions([]);
      setHasMorePages(false);
      setCurrentPage(1);
      return;
    }
    // 加载会话...
  }, [user]);
  ```

### 系统状态确认

#### ✅ 后端服务正常
```
端口: http://localhost:8000
状态: 运行中
Redis: ✅ 已连接 (redis://localhost:6379/0)
会话数: 83个 (Redis统计)
  - 失败: 6
  - 等待输入: 58
  - 运行中: 12
  - 已完成: 3
  - 拒绝: 2
  - 错误: 1
```

#### ✅ 前端服务正常
```
端口: http://localhost:3000
状态: ✓ Ready in 2.1s
API连接: ✅ 已修复为 http://127.0.0.1:8000
```

#### ✅ Redis会话数据正常
```bash
# 检查会话数量
python -c "import redis; r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True); print(f'找到 {len(r.keys(\"session:*\"))} 个会话')"
# 输出: 找到 83 个会话
```

## 📋 用户操作指南

### 如何查看历史记录？

#### 方案1: WordPress登录（推荐）
1. 访问 http://localhost:3000
2. 点击右上角"登录"按钮
3. 使用WordPress账号登录（需要配置WordPress JWT插件）
4. 登录后左侧会显示您的历史会话

#### 方案2: 开发模式（测试用）
如果需要本地测试而无需WordPress登录：

1. **编辑配置文件**: `frontend-nextjs/.env.local`
   ```env
   # 启用开发模式（跳过WordPress认证）
   NEXT_PUBLIC_DEV_MODE=true
   ```

2. **修改后端配置**: `intelligent_project_analyzer/config/settings.py`
   ```python
   DEV_MODE = True  # 返回所有会话（不过滤用户）
   ```

3. **重启前后端服务**
   ```bash
   # 停止服务
   taskkill /F /IM python.exe
   taskkill /F /IM node.exe

   # 启动后端
   python -B scripts\run_server_production.py

   # 启动前端
   cd frontend-nextjs && npm run dev
   ```

⚠️ **注意**: 开发模式会显示所有用户的会话，**仅用于本地测试，禁止用于生产环境**

#### 方案3: 管理后台（需要管理员权限）
访问 http://localhost:3000/admin/sessions 可查看所有会话详情（需要管理员JWT Token）

### 如何测试"启动分析"功能？

1. **确保已登录**（或启用开发模式）
2. 在首页输入框输入需求，例如：
   ```
   我需要设计一个150平米的现代简约风格住宅，三室两厅，预算30万
   ```
3. 点击"开始分析"按钮
4. 如果出现错误，检查：
   - 浏览器控制台（F12）是否有错误信息
   - 后端终端是否显示错误日志
   - `.env` 文件中 `OPENAI_API_KEY` 是否配置正确

## 🔧 快速诊断命令

### 检查服务状态
```powershell
# 检查端口占用
Get-NetTCPConnection -LocalPort 8000,3000 -ErrorAction SilentlyContinue

# 检查后端健康
curl http://localhost:8000/health

# 检查Redis会话数
python -c "import redis; r = redis.Redis(decode_responses=True); print(len(r.keys('session:*')))"
```

### 查看日志
```powershell
# 后端日志
# 在运行 python -B scripts\run_server_production.py 的终端查看

# 前端日志
# 浏览器按F12，查看Console和Network标签
```

## 📚 相关文档

- [快速启动指南](QUICKSTART.md)
- [开发规范](.github/DEVELOPMENT_RULES_CORE.md)
- [会话管理系统](docs/SESSION_MANAGEMENT.md)
- [WordPress JWT认证](.github/historical_fixes/wordpress_jwt_authentication.md)

## 🐛 常见问题

### Q: 为什么我登录后还是看不到历史记录？

**可能原因**:
1. JWT Token未正确保存到localStorage
   - 打开浏览器控制台（F12） → Application → Local Storage
   - 检查是否有 `wp_jwt_token` 键
2. 该账号确实没有历史会话
   - 尝试创建一个新分析，然后刷新页面

### Q: 如何清理所有会话缓存？

```powershell
# 清理Redis会话
python -c "import redis; r = redis.Redis(); r.flushdb(); print('✅ Redis已清空')"

# 清理浏览器缓存
# 浏览器按F12 → Application → Clear site data
```

### Q: 端口被占用怎么办？

```powershell
# 方案1: 终止所有进程
taskkill /F /IM python.exe
taskkill /F /IM node.exe

# 方案2: 修改端口
# 编辑 .env.local
NEXT_PUBLIC_API_URL=http://127.0.0.1:8001

# 启动后端时指定端口
uvicorn intelligent_project_analyzer.api.server:app --port 8001
```

---

**最后更新**: 2026-01-04 16:10
**修复版本**: v7.130+
**状态**: ✅ API端口已修复，历史记录功能正常（需要登录）
