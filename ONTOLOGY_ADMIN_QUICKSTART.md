# 🎯 本体论管理控制台 - 快速测试指南

> 版本: v2026.2.11
> 状态: ✅ 已实现核心功能

---

## 📦 已完成的功能

### 后端 API (FastAPI)
- ✅ `/api/admin/ontology/frameworks` - 获取13个框架概览
- ✅ `/api/admin/ontology/framework/{type}` - 获取单个框架详情
- ✅ `/api/admin/ontology/search?q=关键词` - 搜索维度
- ✅ `/api/admin/ontology/reload` - 重新加载本体论
- ✅ `/api/admin/ontology/validate` - 验证YAML语法
- ✅ `/api/admin/dimension-learning/candidates` - 获取候选列表
- ✅ `/api/admin/dimension-learning/candidates/{id}/approve` - 批准候选
- ✅ `/api/admin/dimension-learning/candidates/{id}/reject` - 拒绝候选
- ✅ `/api/admin/dimension-learning/candidates/batch` - 批量操作

### 前端页面 (Next.js)
- ✅ `/admin/ontology` - 本体论浏览器（树形导航 + 维度详情）
- ✅ `/admin/ontology/review` - 候选维度审核面板（表格 + 弹窗审核）

### 核心服务
- ✅ `OntologyService` - 本体论读取服务
- ✅ `OntologyEditor` - YAML编辑器（保留注释和格式）
- ✅ `DatabaseManager` - 增强候选审核方法

---

## 🚀 快速启动测试

### 1. 安装依赖

```bash
# 后端依赖
pip install ruamel.yaml portalocker APScheduler

# 验证安装
python -c "import ruamel.yaml, portalocker; print('✅ 依赖安装成功')"
```

### 2. 启动服务

```bash
# 后端（新终端）
python -B scripts\run_server_production.py

# 前端（新终端）
cd frontend-nextjs
npm run dev
```

### 3. 访问管理后台

#### 本体论浏览器
```
http://localhost:3001/admin/ontology
```

**功能测试清单**:
- [ ] 左侧显示13个框架列表
- [ ] 点击框架加载详情
- [ ] 展开/折叠类别
- [ ] 点击维度在右侧显示详情
- [ ] 搜索框过滤维度
- [ ] "重新加载"按钮生效

#### 候选维度审核
```
http://localhost:3001/admin/ontology/review
```

**功能测试清单**:
- [ ] 显示统计卡片（待审核、已批准、已拒绝数量）
- [ ] 表格显示候选列表
- [ ] 点击"审核"按钮打开弹窗
- [ ] 弹窗显示完整维度数据
- [ ] "批准并写入本体论"按钮生效
- [ ] "拒绝"按钮生效（可填写拒绝原因）
- [ ] 多选候选进行批量批准
- [ ] 批准后 ontology.yaml 文件更新且格式保留

---

## 🔍 API 测试（使用 Swagger UI）

访问: `http://localhost:8000/docs`

### 测试本体论框架API

**1. 获取框架概览**
```
GET /api/admin/ontology/frameworks
```
期望: 返回13个框架的JSON列表

**2. 获取框架详情**
```
GET /api/admin/ontology/framework/personal_residential
```
期望: 返回个人住宅框架的完整维度树

**3. 搜索维度**
```
GET /api/admin/ontology/search?q=价值观&limit=10
```
期望: 返回包含"价值观"的维度列表

### 测试候选审核API

**1. 获取候选列表**
```
GET /api/admin/dimension-learning/candidates?limit=50
```

**2. 批准候选**（需要先有候选数据）
```
POST /api/admin/dimension-learning/candidates/1/approve
```
期望:
- 返回成功消息
- ontology.yaml 文件更新
- 候选状态变为 'approved'

**3. 拒绝候选**
```
POST /api/admin/dimension-learning/candidates/2/reject
Body: {"reason": "维度描述不清晰"}
```

---

## 🛠️ 核心技术实现验证

### YAML 编辑器测试

**验证格式和注释保留**:
```python
# 在 Python 控制台执行
from intelligent_project_analyzer.services.ontology_editor import get_ontology_editor

editor = get_ontology_editor()

# 测试追加维度
success = editor.append_dimension(
    project_type="meta_framework",
    category="universal_dimensions",
    dimension_data={
        "name": "测试维度 (Test Dimension)",
        "description": "这是一个测试维度",
        "ask_yourself": "这个维度是否有效？",
        "examples": "示例1, 示例2, 示例3"
    }
)

print(f"✅ 追加成功: {success}")

# 验证 ontology.yaml 文件
# 1. 打开文件检查是否有新维度
# 2. 确认原有注释和格式未被破坏
```

### 并发安全性测试

**模拟多管理员同时批准候选**:
```python
import asyncio
from intelligent_project_analyzer.learning.database_manager import get_db_manager

db = get_db_manager()

# 创建测试候选
candidate_id = db.add_candidate(
    dimension_data={
        "name": "并发测试维度",
        "project_type": "meta_framework",
        "category": "universal_dimensions",
        "description": "测试",
        "ask_yourself": "测试？",
        "examples": "测试"
    },
    confidence_score=0.85
)

# 模拟并发批准（应该使用文件锁）
async def approve_concurrent():
    return db.approve_candidate(candidate_id, "admin1")

# 运行测试
# 期望: 文件锁确保串行写入，无YAML损坏
```

---

## 📊 数据准备（可选）

如果候选列表为空，可以手动添加测试数据：

```python
from intelligent_project_analyzer.learning.database_manager import get_db_manager
import json

db = get_db_manager()

# 添加测试候选
test_candidates = [
    {
        "name": "文化敏感度 (Cultural Sensitivity)",
        "project_type": "cultural_educational",
        "category": "universal_dimensions",
        "description": "项目对本地文化和传统的尊重程度",
        "ask_yourself": "设计如何融入当地文化元素？",
        "examples": "传统建筑元素, 本地材料使用, 文化符号转译"
    },
    {
        "name": "社区融合度 (Community Integration)",
        "project_type": "personal_residential",
        "category": "social_coordinates",
        "description": "项目与周边社区的互动和融合程度",
        "ask_yourself": "项目如何促进社区交流？",
        "examples": "公共开放空间, 社区活动, 邻里互动"
    }
]

for candidate_data in test_candidates:
    candidate_id = db.add_candidate(
        dimension_data=candidate_data,
        confidence_score=0.82,
        source_session_id="test-session-001"
    )
    print(f"✅ 添加测试候选 {candidate_id}: {candidate_data['name']}")

print("\n✅ 测试数据准备完成，可前往审核面板测试")
```

---

## ✅ 验收标准

### 后端验收
- [ ] 所有API端点正常响应
- [ ] ontology.yaml 编辑后格式和注释保留
- [ ] 批准候选后数据库状态正确更新
- [ ] 文件锁避免并发冲突
- [ ] 写入失败时自动回滚到备份

### 前端验收
- [ ] 本体论浏览器展示13个框架
- [ ] 树形导航可展开/折叠
- [ ] 搜索功能实时过滤
- [ ] 候选审核面板显示统计和列表
- [ ] 审核弹窗显示完整信息
- [ ] 批准/拒绝操作成功并刷新列表
- [ ] 批量操作生效

---

## 🐛 已知问题和限制

1. **候选来源**: 当前候选维度需要由 `DimensionExtractor` 从专家输出中自动提取，或手动添加测试数据
2. **权限控制**: 当前仅检查 `require_admin` 中间件，未实现细粒度权限
3. **进化历史**: P2功能（进化日志、版本快照）暂未实现
4. **质量评分**: P1功能（质量监控仪表板）暂未实现

---

## 📈 下一步优化建议

### P1 优先级
- [ ] 实现质量监控仪表板（`/admin/quality`）
- [ ] 添加维度质量评分定时任务
- [ ] 完善候选状态筛选（已批准/已拒绝历史查看）

### P2 优先级
- [ ] 实现进化历史时间轴（`/admin/evolution`）
- [ ] 添加版本快照和回滚功能
- [ ] 实现候选维度编辑功能（批准前修改描述）

### 性能优化
- [ ] API响应缓存（TTLCache）
- [ ] 前端虚拟滚动（大量维度时）
- [ ] 数据库索引优化

---

## 📞 技术支持

如遇问题，请检查：
1. Python环境: `python --version` (需要 3.10+)
2. 依赖安装: `pip list | grep -E "ruamel|portalocker|APScheduler"`
3. 后端日志: 查看终端输出
4. 前端日志: 浏览器开发者工具 Console

**成功标志**: 访问 `/admin/ontology` 能看到13个框架列表，点击框架能加载维度详情 ✅

---

**实施完成时间**: 2026-02-11
**总计代码行数**: ~1200行 (后端 ~700行 + 前端 ~500行)
**核心文件**: 7个新建 + 2个修改
