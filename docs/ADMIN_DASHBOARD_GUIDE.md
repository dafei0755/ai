# 管理员后台系统 - 部署和使用指南

> **版本**: v1.0.0
> **创建日期**: 2026年1月3日
> **状态**: ✅ 已完成核心功能

---

## 📋 系统概述

管理员后台系统为 Intelligent Project Analyzer 提供完整的系统监控、配置管理、会话管理和日志查询功能。采用方案A（独立后台系统），复用现有 Next.js + FastAPI 技术栈，嵌入 Grafana 监控面板，实现配置热重载，使用60秒轮询保持数据更新。

### 核心功能

1. **系统监控** - CPU、内存、磁盘使用率实时监控，活跃会话统计
2. **Grafana集成** - 嵌入 Grafana 仪表板，查看详细性能指标
3. **配置管理** - 查看和热重载系统配置，无需重启服务
4. **会话管理** - 查看所有用户会话，强制终止会话，批量操作
5. **日志查看器** - 实时查看服务器、认证、错误、性能日志
6. **搜索过滤器管理** - 配置黑名单（屏蔽低质量站点）和白名单（优先推荐权威媒体）
7. **能力边界监控** - 监控交付物能力约束违规，防止用户选择超出系统能力范围的交付物（v7.130新增）

---

## 🚀 快速部署

### Step 1: 安装依赖

#### 后端依赖

```bash
# 激活虚拟环境（如果使用）
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 安装新增依赖
pip install -r requirements.txt
```

**新增依赖**:
- `psutil>=5.9.0` - 系统监控（CPU、内存）
- `cachetools>=5.3.0` - API响应缓存

#### 前端依赖

```bash
cd frontend-nextjs

# 安装新增依赖
npm install

# 可选：安装完整的Monaco编辑器（配置编辑功能）
# npm install @monaco-editor/react
```

**新增依赖**:
- `@monaco-editor/react@^4.6.0` - 代码编辑器（配置管理）
- `@tanstack/react-table@^8.10.0` - 表格组件（会话列表）
- `recharts@^2.10.0` - 图表库（监控仪表板）

### Step 2: 配置Grafana（可选）

如果需要使用Grafana监控面板：

```bash
cd docker

# 启动Grafana + Loki + Promtail
docker-compose -f docker-compose.logging.yml up -d

# 查看日志
docker-compose -f docker-compose.logging.yml logs -f grafana
```

**Grafana配置**（已在 `docker-compose.logging.yml` 中配置）:
- 匿名访问：`GF_AUTH_ANONYMOUS_ENABLED=true`
- 只读权限：`GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer`
- 允许iframe嵌入：`GF_SECURITY_ALLOW_EMBEDDING=true`

### Step 3: 启动服务

#### 启动后端（Python）

```bash
# 方式1：使用生产脚本（推荐）
python -B scripts\run_server_production.py

# 方式2：使用开发脚本
python -B scripts\run_server.py

# 方式3：直接使用uvicorn
python -B -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000 --reload
```

**启动成功标志**:
```
✅ 配置热重载管理器已启动（检查间隔: 10秒）
✅ 管理员后台路由已注册
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### 启动前端（Next.js）

```bash
cd frontend-nextjs
npm run dev
```

**启动成功标志**:
```
✓ Ready in 1846ms
- Local:        http://localhost:3000
```

### Step 4: 访问管理后台

**URL**: http://localhost:3000/admin

**默认登录**:
- 用户名: `admin`（需要在WordPress中配置管理员角色）
- 使用WordPress JWT认证系统登录

---

## 🔑 权限管理

### 管理员角色配置

管理员后台仅允许具有 `administrator` 角色的用户访问。

#### WordPress角色映射

| WordPress 角色 | 系统权限 | 管理后台访问 |
|---------------|---------|-------------|
| `administrator` | 超级管理员 | ✅ 允许 |
| `editor` | 编辑 | ❌ 拒绝 |
| `author` | 作者 | ❌ 拒绝 |
| `subscriber` | 订阅者 | ❌ 拒绝 |

#### 配置管理员白名单（可选）

在 `.env` 中配置：

```env
# 管理员用户白名单（逗号分隔）
ADMIN_WHITELIST=admin,superuser,devops
```

---

## 📊 功能详解

### 1. 系统监控仪表板

**路径**: `/admin/dashboard`

**功能**:
- 📈 实时系统资源监控（CPU、内存、磁盘）
- 👥 活跃会话统计
- ⚡ 性能指标（总请求数、平均响应时间、错误数）
- 🔄 60秒自动刷新

**API端点**:
- `GET /api/admin/metrics/summary` - 系统监控摘要

**示例响应**:
```json
{
  "system": {
    "cpu_percent": 15.2,
    "memory_percent": 68.5,
    "memory_used_gb": 10.96,
    "memory_total_gb": 16.0,
    "disk_percent": 45.3
  },
  "sessions": {
    "active_count": 5
  },
  "performance": {
    "total_requests": 1523,
    "avg_response_time": 287.5,
    "requests_per_minute": 12,
    "error_count": 3
  }
}
```

### 2. Grafana监控集成

**路径**: `/admin/monitoring`

**功能**:
- 📊 嵌入 Grafana 仪表板（iframe）
- 📈 API性能监控
- 📉 LLM调用统计
- 🔗 直接访问完整Grafana UI

**Grafana访问**:
- URL: http://localhost:3200
- 用户名: `admin`
- 密码: `admin123`

### 3. 配置管理

**路径**: `/admin/config`

**功能**:
- 📄 查看当前配置（脱敏）
- 🔄 热重载配置（无需重启）
- ⚙️ 配置文件编辑（Monaco Editor）

**API端点**:
- `GET /api/admin/config/current` - 获取当前配置
- `POST /api/admin/config/reload` - 触发热重载
- `GET /api/admin/config/env` - 获取.env文件内容

**配置热重载**:
```bash
# 修改 .env 文件后
# 方式1：自动检测（10秒内自动重载）
# 方式2：手动触发（点击"重载配置"按钮）
```

**支持热重载的配置项**:
- ✅ LLM配置（`LLM_PROVIDER`, `OPENAI_MODEL`, `TEMPERATURE`）
- ✅ 功能开关（`IMAGE_GENERATION_ENABLED`）
- ✅ Redis连接配置
- ✅ API密钥
- ❌ FastAPI启动参数（需重启）

### 4. 会话管理

**路径**: `/admin/sessions`

**功能**:
- 📋 查看所有用户会话
- 🔍 搜索和筛选
- 🛑 强制终止会话
- 🗑️ 批量删除会话
- 📄 分页浏览

**API端点**:
- `GET /api/admin/sessions?page=1&page_size=20` - 会话列表
- `POST /api/admin/sessions/{session_id}/force-stop` - 强制终止
- `DELETE /api/admin/sessions/batch` - 批量删除

### 5. 日志查看器

**路径**: `/admin/logs`

**功能**:
- 📜 实时查看服务器日志
- 🔍 按日志类型筛选（server/auth/error/performance）
- ⏱️ 按时间范围筛选
- 🔄 自动滚动（尾部追踪模式）

**API端点**:
- `GET /api/admin/logs?type=server&lines=100` - 获取日志
- `POST /api/admin/logs/clear` - 清空日志

### 6. 搜索过滤器管理

**路径**: `/admin/search-filters`

**功能**:
- 🚫 配置黑名单（屏蔽低质量站点，如：社交媒体、论坛、广告站点）
- ✅ 配置白名单（优先推荐权威媒体，如：行业协会、专业期刊）
- 📊 查看过滤统计（拦截次数、通过次数）
- 💾 实时保存配置到 `config/search_filters.yaml`

**API端点**:
- `GET /api/admin/search-filters/config` - 获取当前配置
- `POST /api/admin/search-filters/config` - 更新配置
- `GET /api/admin/search-filters/stats` - 查看统计数据

**配置示例**:
```yaml
blacklist:
  enabled: true
  domains:
    - youtube.com
    - facebook.com
    - twitter.com
  keywords:
    - "广告"
    - "推广"

whitelist:
  enabled: true
  domains:
    - zhihu.com
    - archdaily.com
    - designboom.com
```

**v7.130修复**: 修复页面加载时的null-safety问题，使用可选链操作符防止config加载前访问嵌套属性报错。

### 7. 能力边界监控 🆕 v7.130

**路径**: `/admin/capability-boundary`

**功能**:
- ⚠️ 监控用户选择超出系统能力范围的交付物（CAD施工图、3D效果图、精确清单等）
- 📊 查看违规统计（按节点、按交付物类型、按时间趋势）
- 🔍 分析用户误解模式（高频违规项识别）
- 📋 查看实时违规记录和自动转换日志

**三个监控标签**:

#### 7.1 节点配置

显示各工作流节点的能力边界规则配置：

| 节点名称 | 检查类型 | 支持的交付物 | 不支持的交付物 |
|---------|---------|-------------|--------------|
| progressive_step3_gap_filling | full | 设计策略文档、空间概念描述、材料选择指导、预算框架、分析报告 | CAD施工图、3D效果图、精确材料清单、精确预算清单 |
| requirements_confirmation | full | 需求分析报告、设计思路、方案建议 | 详细施工图纸、3D渲染图 |
| expert_collaboration | info | 专业分析、概念设计、策略建议 | 精确技术图纸 |

**配置文件**: `config/capability_boundary_config.yaml`

#### 7.2 违规记录

显示用户选择超出能力范围交付物的历史记录：

```typescript
{
  timestamp: "2026-01-04T10:30:15",
  node: "progressive_step3_gap_filling",
  user_id: "user_12345",
  violations: [
    {
      original: "CAD施工图",
      transformed: "设计策略文档",
      reason: "需要AutoCAD/Revit等专业工具"
    }
  ],
  session_id: "sess_abc123"
}
```

**字段说明**:
- `original`: 用户原始选择
- `transformed`: 系统自动转换后的可执行交付物
- `reason`: 不支持原始选择的原因说明

#### 7.3 违规模式分析

识别高频违规项和用户误解趋势：

| 违规交付物 | 出现次数 | 占比 | 自动转换目标 |
|-----------|---------|------|-------------|
| CAD施工图 | 127 | 35% | 设计策略文档 |
| 3D效果图 | 89 | 24% | 空间概念描述 |
| 精确材料清单 | 76 | 21% | 材料选择指导 |
| 精确预算清单 | 73 | 20% | 预算框架 |

**告警规则**:
- ⚠️ 违规率 ≥ 30%: 需要优化前端提示或用户引导
- 🚨 单个违规项 ≥ 100次/周: 说明用户对系统定位有误解，建议增加FAQ说明

**API端点**:
- `GET /api/admin/capability-boundary/stats` - 获取统计数据
- `GET /api/admin/capability-boundary/violations?page=1&page_size=20` - 查看违规记录
- `GET /api/admin/capability-boundary/patterns` - 分析违规模式

**多层防御机制**:

1. **配置层**: `capability_boundary_config.yaml` 定义每个节点的check_type（full/info/none）
2. **提示层**: `gap_question_generator.yaml` LLM提示包含40行能力边界约束说明
3. **模板层**: `task_completeness_analyzer.py` 硬编码问题选项仅包含系统支持的交付物
4. **代码层**: `progressive_questionnaire.py` 调用 `CapabilityBoundaryService.check_questionnaire_answers()` 进行实时检查和转换

**转换规则详情**:

| 用户选择（超出能力） | 系统转换（支持范围） | 原因说明 |
|---------------------|---------------------|----------|
| CAD施工图 | 设计策略文档 | 需要AutoCAD/Revit等专业工具，系统提供策略性设计思路 |
| 3D效果图 | 空间概念描述 | 需要3ds Max/SketchUp等渲染工具，系统提供文字概念描述 |
| 软装清单/精确材料清单 | 材料选择指导 | 需要现场测量和尺寸核对，系统提供材料建议和选择指导 |
| 精确预算清单 | 预算框架 | 需要实时市场询价和供应商报价，系统提供预算区间估算 |

**监控价值**:
- 识别用户对系统能力的理解偏差
- 优化前端交互提示文案
- 指导功能边界文档完善
- 为产品迭代提供数据支持（哪些功能用户期待最高）

---

**功能**:
- 📝 实时查看日志文件
- 🔍 关键词搜索
- 📂 多日志类型切换（server/auth/errors/performance）
- 🔄 60秒自动刷新

**API端点**:
- `GET /api/admin/logs?log_type=server&lines=100&search=关键词`

**支持的日志类型**:
- `server` - 服务器主日志
- `auth` - 认证相关日志
- `errors` - 错误日志
- `performance` - 性能日志
- `admin_operations` - 管理员操作审计日志

---

## 🛠️ 技术架构

### 后端技术栈

- **Web框架**: FastAPI 0.115+
- **权限验证**: WordPress JWT + 角色检查
- **系统监控**: psutil
- **性能监控**: 自定义 PerformanceMonitor
- **配置管理**: HotReloadConfigManager（轮询机制）
- **会话管理**: RedisSessionManager
- **日志系统**: Loguru

### 前端技术栈

- **框架**: Next.js 14 (App Router)
- **UI库**: TailwindCSS 3.4
- **图表**: recharts 2.10（可替换为chart.js）
- **表格**: @tanstack/react-table 8.10
- **编辑器**: @monaco-editor/react 4.6（可选）
- **HTTP客户端**: Axios 1.7

### 目录结构

```
intelligent_project_analyzer/
├── api/
│   ├── admin_routes.py          # 🔥 管理员API路由
│   ├── auth_middleware.py       # ✅ 扩展: require_admin()
│   └── server.py                # ✅ 注册admin_routes
├── utils/
│   └── config_manager.py        # 🔥 配置热重载管理器
└── services/
    ├── redis_session_manager.py # 会话管理器
    └── capability_boundary.py   # 🆕 v7.130: 能力边界检查服务

frontend-nextjs/
├── app/
│   └── admin/                   # 🔥 管理员后台
│       ├── layout.tsx           # Admin布局（侧边栏）
│       ├── page.tsx             # 重定向到dashboard
│       ├── dashboard/
│       │   └── page.tsx         # 监控仪表板
│       ├── monitoring/
│       │   └── page.tsx         # Grafana监控
│       ├── config/
│       │   └── page.tsx         # 配置管理
│       ├── sessions/
│       │   └── page.tsx         # 会话管理
│       ├── logs/
│       │   └── page.tsx         # 日志查看器
│       ├── search-filters/
│       │   └── page.tsx         # 🔥 搜索过滤器管理（黑白名单）
│       └── capability-boundary/ # 🆕 v7.130: 能力边界监控
│           └── page.tsx
└── middleware.ts                # ✅ 扩展: /admin路由保护
```

---

## 📡 API接口文档

### 认证

所有Admin API都需要JWT认证并验证管理员权限：

```http
GET /api/admin/xxx
Authorization: Bearer <jwt_token>
```

**权限检查**:
- 验证JWT Token有效性
- 检查用户角色是否包含 `administrator`

### 监控API

#### GET /api/admin/metrics/summary

获取系统监控摘要

**响应**: 见"系统监控仪表板"部分示例

**缓存**: 5秒TTL

#### GET /api/admin/metrics/performance/details

获取详细性能指标

**参数**:
- `hours`: 时间范围（小时），默认1

#### GET /api/admin/metrics/slow-requests

获取慢请求列表

**参数**:
- `limit`: 返回数量，默认20

### 配置API

#### GET /api/admin/config/current

获取当前配置（脱敏）

#### POST /api/admin/config/reload

触发配置热重载

#### GET /api/admin/config/env

获取.env文件内容（脱敏）

### 会话API

#### GET /api/admin/sessions

获取会话列表

**参数**:
- `page`: 页码
- `page_size`: 每页数量
- `status`: 筛选状态
- `search`: 搜索关键词

#### POST /api/admin/sessions/{session_id}/force-stop

强制终止会话

#### DELETE /api/admin/sessions/batch

批量删除会话

**请求体**:
```json
{
  "session_ids": ["session-id-1", "session-id-2"]
}
```

### 日志API

#### GET /api/admin/logs

查询日志

**参数**:
- `log_type`: 日志类型（server/auth/errors/performance）
- `lines`: 返回行数，默认100
- `search`: 搜索关键词

#### GET /api/admin/logs/files

列出所有日志文件

---

## 🔒 安全建议

### 生产环境配置

1. **启用HTTPS**
   ```nginx
   # Nginx配置
   server {
       listen 443 ssl;
       server_name admin.yourdomain.com;

       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       location /admin {
           proxy_pass http://localhost:3000;
       }
   }
   ```

2. **IP白名单**（可选）
   ```env
   # .env
   ADMIN_WHITELIST_IPS=192.168.1.100,10.0.0.5
   ```

3. **双因素认证**（TODO）
   - 集成Google Authenticator
   - 手机验证码

4. **操作审计日志**
   - 所有管理员操作自动记录到 `logs/admin_operations.log`
   - 包含：操作类型、用户ID、IP地址、时间戳

5. **敏感操作二次确认**
   - 批量删除会话
   - 修改配置
   - 强制终止会话

---

## 🐛 故障排查

### 问题1: 无法访问 /admin 页面

**症状**: 访问 `/admin` 自动跳转到登录页

**解决方案**:
1. 确认已登录并具有管理员权限
2. 检查 localStorage 中的 `wp_jwt_token`
3. 验证JWT Token未过期
4. 确认WordPress用户角色为 `administrator`

### 问题2: 监控数据加载失败

**症状**: Dashboard显示"获取监控数据失败"

**解决方案**:
1. 检查后端服务是否运行：http://localhost:8000/health
2. 验证psutil已安装：`pip install psutil`
3. 查看后端日志：`logs/server.log`
4. 检查CORS配置

### 问题3: Grafana无法嵌入

**症状**: Grafana iframe显示空白或拒绝连接

**解决方案**:
1. 确认Grafana已启动：http://localhost:3200
2. 检查 `docker-compose.logging.yml` 配置
3. 重启Grafana容器：
   ```bash
   docker-compose -f docker/docker-compose.logging.yml restart grafana
   ```
4. 查看Grafana日志：
   ```bash
   docker logs grafana
   ```

### 问题4: 配置热重载不生效

**症状**: 修改 `.env` 文件后配置未更新

**解决方案**:
1. 等待10秒（自动检测间隔）
2. 手动触发重载：点击"重载配置"按钮
3. 查看日志确认重载：
   ```
   🔄 检测到 .env 文件变更
   ✅ 配置已重新加载
   ```
4. 某些配置需要重启服务（如FastAPI启动参数）

---

## 📈 性能优化

### 后端优化

1. **API响应缓存**
   - 监控数据：5秒TTL
   - 会话列表：10分钟TTL（已有）

2. **异步操作**
   - 日志查询使用异步IO
   - 批量会话操作并发处理

3. **分页限制**
   - 会话列表：最大100条/页
   - 日志查看：最大1000行

### 前端优化

1. **轮询优化**
   - 仪表板：60秒间隔
   - 日志查看：60秒间隔
   - 使用 `AbortController` 取消重复请求

2. **按需加载**
   - Monaco Editor懒加载
   - Grafana iframe按需渲染

3. **数据缓存**
   - 使用React状态管理避免重复请求

---

## 🔄 后续扩展

### 短期计划

- [ ] 完整的Monaco Editor集成（配置在线编辑）
- [ ] @tanstack/react-table实现高级表格功能
- [ ] 主动学习数据分析页面
- [ ] 操作审计日志查看

### 长期计划

- [ ] 实时WebSocket推送（替代轮询）
- [ ] 权限细粒度控制（多级管理员）
- [ ] 数据导出功能（CSV/Excel）
- [ ] 系统告警配置界面
- [ ] 自定义Grafana仪表板

---

## 📞 技术支持

- **文档**: [docs/](../docs/)
- **Issues**: https://github.com/dafei0755/ai/issues
- **Discussions**: https://github.com/dafei0755/ai/discussions

**祝你使用愉快！** 🎉
