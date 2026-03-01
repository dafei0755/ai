# 外部数据采集监控面板使用指南

> **版本**: v8.120
> **日期**: 2026-02-17
> **状态**: 前端UI已完成，后端API待实现

---

## 📍 访问路径

**管理后台**: http://localhost:3000/admin/external-data

**要求**: 需要管理员账号登录（从 https://www.ucppt.com/nextjs 登录）

---

## 🎯 功能概览

### 1. 数据源统计卡片（顶部）

显示每个数据源的实时状态：

- **总项目数**: 数据库中的总项目数量
- **今日新增**: 今天新爬取的项目数量（绿色↑图标）
- **质量评分**: 数据质量平均分（0-100%进度条）
- **最后更新**: 上次同步的时间（如"2小时前"）
- **刷新按钮**: 手动触发该数据源的增量同步

**支持的数据源**:
- **Archdaily** (中文建筑网，35%权重)
- **Gooood** (谷德设计网，25%权重)
- **Dezeen** (国际设计网，25%权重)
- **Architizer** (A+ Awards，15%权重)

---

### 2. 同步历史表格（中部）

实时显示最近10次同步任务的详细信息：

| 列名 | 说明 | 示例 |
|------|------|------|
| **状态** | 运行状态：完成/进行中/失败 | 🔴 失败 |
| **数据源** | 数据源名称 | archdaily |
| **分类** | 爬取的分类（可选） | 文化建筑 |
| **开始时间** | 任务开始时间 | 2小时前 |
| **耗时** | 任务执行时长 | 150秒 |
| **项目数** | 总共爬取的项目数 | 36 |
| **新增/更新** | 新增（绿色）+ 更新（蓝色）数量 | +5 / 3 |
| **失败** | 失败的项目数 | 2 |

**状态图标**:
- ✅ **完成** (绿色): 任务成功完成
- 🔄 **进行中** (蓝色，旋转): 正在爬取
- ⚠️ **失败** (红色): 任务失败（点击查看错误）

---

### 3. 质量问题表格（底部）

监控数据质量问题，按严重程度排序：

| 列名 | 说明 | 示例 |
|------|------|------|
| **严重程度** | critical/high/medium/low | 🔴 严重 |
| **问题类型** | 具体问题描述 | 缺失描述 |
| **项目ID** | 有问题的项目ID | 1037243 |
| **发现时间** | 问题检测时间 | 1小时前 |
| **操作** | 查看详情/修复操作 | [查看详情] |

**问题类型**:
- `missing_description`: 缺失描述（严重）
- `low_quality_description`: 描述质量低（中等）
- `missing_images`: 缺失图片（低）
- `invalid_metadata`: 元数据错误（高）

**严重程度颜色**:
- 🔴 **严重** (critical): 红色背景
- 🟠 **高** (high): 橙色背景
- 🟡 **中** (medium): 黄色背景
- 🔵 **低** (low): 蓝色背景

---

## 🛠️ 操作指南

### 手动触发同步

1. 点击数据源卡片右上角的 🔄 按钮
2. 确认触发增量同步（只爬取新项目）
3. 等待2秒后自动刷新状态

**示例响应**:
```
✅ 已触发 archdaily 的增量同步任务
任务ID: celery-task-12345
```

### 刷新数据

点击右上角的 **[刷新]** 按钮，重新加载所有数据（同步历史、数据源统计、质量问题）

### 查看项目详情

在质量问题表格中点击 **[查看详情]** 链接，打开项目详情页面（显示完整元数据、图片、质量评分）

---

## 🔌 后端API（待实现）

### 已创建的API端点

| 端点 | 方法 | 说明 | 状态 |
|------|------|------|------|
| `/api/external/sync-history` | GET | 获取同步历史 | ⏳ 待实现 |
| `/api/external/source-stats` | GET | 获取数据源统计 | ⏳ 待实现 |
| `/api/external/quality-issues` | GET | 获取质量问题 | ⏳ 待实现 |
| `/api/external/trigger-sync` | POST | 触发同步任务 | ⏳ 待实现 |
| `/api/external/project/{id}` | GET | 获取项目详情 | ⏳ 待实现 |

### API实现路线图

参考 [LARGE_SCALE_EXTERNAL_DATA_ARCHITECTURE.md](../LARGE_SCALE_EXTERNAL_DATA_ARCHITECTURE.md) 中的完整实现方案：

**Phase 1**: 数据库Schema设计（2周）
- PostgreSQL + pgvector 表结构
- `projects` 主表（支持10,000+项目）
- `sync_history` 同步历史表
- `quality_issues` 质量问题表

**Phase 2**: Celery任务系统（2周）
- 分布式爬取（10个Worker并发）
- 定时同步（APScheduler）
- 任务监控接口

**Phase 3**: 数据处理Pipeline（1周）
- 向量化（OpenAI Embeddings）
- 质量评分引擎
- 自动标注系统

**Phase 4**: API开发（1周）
- 实现上述5个端点
- 集成Celery任务查询
- 实时状态推送（WebSocket）

---

## 📊 当前状态（模拟数据）

由于后端API尚未实现，页面目前使用**模拟数据**演示功能：

### 模拟数据源统计
```typescript
{
  source: 'archdaily',
  total_projects: 2847,
  new_today: 5,
  avg_quality_score: 0.87,
  last_sync: '30分钟前'
}
```

### 模拟同步历史
```typescript
{
  id: 1,
  source: 'archdaily',
  category: '文化建筑',
  started_at: '2小时前',
  completed_at: '1.5小时前',
  status: 'completed',
  projects_total: 36,
  projects_new: 5,
  projects_updated: 3,
  projects_failed: 0
}
```

### 模拟质量问题
```typescript
{
  id: 1,
  project_id: 1037243,
  issue_type: 'missing_description',
  severity: 'high',
  detected_at: '2小时前'
}
```

**当后端API实现后**，模拟数据将自动替换为真实数据。

---

## 🚀 下一步工作

### 立即可做
1. ✅ **前端UI** - 已完成（本页面）
2. ✅ **API路由框架** - 已创建 `external_data_routes.py`
3. ✅ **后端路由注册** - 已在 `server.py` 中注册

### 待实施
4. ⏳ **数据库Schema** - 创建PostgreSQL表结构
   ```bash
   python scripts/init_external_db.py
   ```

5. ⏳ **Celery任务系统** - 实现分布式爬取
   ```bash
   celery -A intelligent_project_analyzer.tasks.crawl_tasks worker --loglevel=info
   ```

6. ⏳ **API实现** - 连接数据库，返回真实数据
   - 修改 `external_data_routes.py` 中的TODO部分
   - 实现数据库查询逻辑

7. ⏳ **自动化测试** - 验证API功能
   ```bash
   pytest tests/api/test_external_data_routes.py -v
   ```

---

## 📚 相关文档

- [LARGE_SCALE_EXTERNAL_DATA_ARCHITECTURE.md](../LARGE_SCALE_EXTERNAL_DATA_ARCHITECTURE.md) - 完整架构设计（10,000+项目，多网站，自动同步）
- [EXTERNAL_DATA_STORAGE_GUIDE.md](../EXTERNAL_DATA_STORAGE_GUIDE.md) - 数据存储与利用指南
- [scripts/archdaily_crawler.py](../intelligent_project_analyzer/scripts/archdaily_crawler.py) - Archdaily爬虫实现（已完成）
- [scripts/test_single_project.py](../scripts/test_single_project.py) - 单个项目爬取测试

---

## 💡 使用提示

1. **首次访问**: 所有数据为模拟数据（灰色提示框）
2. **管理员权限**: 从WordPress后台登录后自动授权
3. **实时刷新**: 建议每5分钟手动刷新一次
4. **错误处理**: API错误会显示在顶部红色提示框
5. **响应式设计**: 支持桌面端（最佳体验）

---

## 🐛 已知问题

- [ ] 后端API返回空数据（待实现数据库查询）
- [ ] 触发同步按钮无实际效果（Celery未配置）
- [ ] 项目详情链接404（路由未实现）
- [ ] WebSocket实时推送未实现（计划中）

---

**作者**: AI System Design Team
**维护者**: Claude Code
**版本**: v8.120
**最后更新**: 2026-02-17
