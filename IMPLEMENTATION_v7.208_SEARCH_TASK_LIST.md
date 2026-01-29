# v7.208 实现报告：搜索任务清单（宏观主线驱动）

## 📋 更新摘要

**版本**: v7.208
**日期**: 2025-01-16
**核心功能**: 在分析阶段生成明确的搜索任务清单，作为后续多轮搜索的主线锚点

## 🎯 设计理念

### 问题背景
- v7.207 已合并 L0+L1-L5 分析，但搜索过程可能"跑题"
- `KeyAspect`（信息面）是抽象的"需要什么信息"，不是"具体搜什么"
- 多轮搜索缺乏明确的任务清单和进度追踪

### 解决方案
引入 `SearchMasterLine`（搜索主线）机制：
1. **核心问题锚点**: 用一句话定义用户问题的本质
2. **边界约束**: 明确搜索的范围，防止跑题
3. **任务清单**: P1/P2/P3 优先级的具体搜索任务
4. **延展触发**: 定义何时允许探索新发现
5. **禁区定义**: 明确排除的方向

## 📁 改动文件

### 后端改动

#### 1. `intelligent_project_analyzer/services/ucppt_search_engine.py`

**新增数据结构** (~行 337-460):

```python
@dataclass
class SearchTask:
    """明确的搜索任务 - v7.208"""
    id: str                    # T1, T2, ...
    task: str                  # 具体搜索任务描述
    purpose: str               # 为什么要搜这个
    priority: int = 1          # P1(必须)/P2(重要)/P3(补充)
    status: str = "pending"    # pending/searching/complete
    expected_info: List[str]   # 期望获取的信息
    actual_findings: List[str] # 实际发现
    completion_score: float    # 完成度 0-1

@dataclass
class SearchMasterLine:
    """搜索主线 - v7.208"""
    core_question: str         # 问题一句话本质
    boundary: str              # 边界定义（防止跑题）
    search_tasks: List[SearchTask]
    exploration_triggers: List[str]  # 触发延展探索的条件
    forbidden_zones: List[str]       # 明确排除的方向
```

**修改统一分析 Prompt** (~行 1541-1720):
- 新增第5部分：搜索任务规划指南
- 输出 `search_master_line` JSON 结构
- P1/P2/P3 优先级说明

**新增解析方法** (~行 1820-1855):
```python
def _parse_search_master_line(self, data: Dict[str, Any]) -> Optional[SearchMasterLine]:
    """解析搜索主线数据 - v7.208"""
```

**修改主搜索流程 `search_deep()`**:
- 捕获 `_search_master_line` 从统一分析
- 推送 `search_master_line_ready` 事件
- 使用 `search_master_line.get_next_task()` 获取下一个任务
- 推送 `task_progress` 事件更新任务进度

**新增 SSE 事件**:
- `search_master_line_ready`: 搜索主线解析完成
- `task_progress`: 任务进度更新

### 前端改动

#### 2. `frontend-nextjs/app/search/[session_id]/page.tsx`

**新增类型定义** (~行 53-80):
```typescript
interface SearchTask {
  id: string;
  task: string;
  purpose: string;
  priority: number;
  status: 'pending' | 'searching' | 'complete';
  expected_info: string[];
}

interface SearchMasterLine {
  core_question: string;
  boundary: string;
  tasks: SearchTask[];
  task_count: number;
  exploration_triggers: string[];
  forbidden_zones: string[];
}

interface TaskProgress {
  status: string;
  score: number;
  findings: string[];
}
```

**扩展 SearchState 接口**:
```typescript
interface SearchState {
  // ... 现有字段
  searchMasterLine: SearchMasterLine | null;
  taskProgress: Record<string, TaskProgress>;
}
```

**新增事件处理** (~行 1044-1070):
- `search_master_line_ready`: 存储搜索主线
- `task_progress`: 更新任务进度

**新增展示组件** (~行 271-365):
```tsx
const SearchTaskListCard = ({ masterLine, taskProgress, isExpanded, onToggle }) => {
  // 显示任务清单，包含：
  // - 进度计数 (已完成/总数)
  // - P1/P2/P3 优先级标签
  // - 任务状态图标 (待处理/搜索中/已完成)
  // - 进度条
  // - 发现摘要
  // - 边界说明
  // - 禁区提示
}
```

## 🔄 数据流

```
用户问题
    ↓
统一分析 (DeepSeek-Reasoner)
    ↓ thinking: 对话内容
    ↓ content: JSON (含 search_master_line)
    ↓
解析 SearchMasterLine
    ↓
推送 search_master_line_ready 事件
    ↓
Phase 2: 任务驱动搜索
    ↓ get_next_task() 获取 P1 任务
    ↓ 执行搜索
    ↓ update_task_status() 更新进度
    ↓ 推送 task_progress 事件
    ↓ 循环直到所有任务完成
    ↓
Phase 3: 答案整合
```

## 📊 示例输出

### Prompt 生成的任务清单示例

```json
{
  "search_master_line": {
    "core_question": "为深圳南山独立女性设计200平欧式优雅大平层",
    "boundary": "聚焦于居住空间设计，不涉及商业空间或公共建筑",
    "search_tasks": [
      {
        "id": "T1",
        "task": "搜索Audrey Hepburn风格的标志性设计元素",
        "purpose": "为用户偏好的优雅风格提供具体参考",
        "priority": 1,
        "expected_info": ["色彩搭配", "材质选择", "家具风格"]
      },
      {
        "id": "T2",
        "task": "搜索深圳南山区域的气候与居住设计考量",
        "purpose": "确保设计方案适应当地环境",
        "priority": 1,
        "expected_info": ["通风设计", "遮阳方案", "防潮措施"]
      },
      {
        "id": "T3",
        "task": "搜索200平大平层的空间布局优秀案例",
        "purpose": "为空间规划提供参考",
        "priority": 2,
        "expected_info": ["功能分区", "动线设计", "收纳方案"]
      }
    ],
    "exploration_triggers": [
      "若发现新的优雅风格现代演绎可深入1轮",
      "若涉及智能家居整合可扩展探索"
    ],
    "forbidden_zones": [
      "商业空间设计",
      "极简工业风格",
      "预算超过100万的奢华方案"
    ]
  }
}
```

### 前端任务清单展示效果

```
┌─────────────────────────────────────────────────┐
│ 📋 搜索任务清单                           2/3   │
├─────────────────────────────────────────────────┤
│ ✅ P1 搜索Audrey Hepburn风格的标志性设计元素    │
│    目的: 为用户偏好的优雅风格提供具体参考       │
│    ✓ 发现了经典黑白灰配色和法式细节...          │
│                                                 │
│ ⏳ P1 搜索深圳南山区域的气候与居住设计考量      │
│    目的: 确保设计方案适应当地环境               │
│    ████████░░ 80%                               │
│                                                 │
│ ○  P2 搜索200平大平层的空间布局优秀案例         │
│    目的: 为空间规划提供参考                     │
│                                                 │
│ 🎯 搜索边界: 聚焦于居住空间设计，不涉及商业...  │
│ ⛔ 不涉及: 商业空间设计、极简工业风格           │
└─────────────────────────────────────────────────┘
```

## ✅ 测试验证

1. **后端导入测试**:
```bash
python -c "from intelligent_project_analyzer.services.ucppt_search_engine import SearchTask, SearchMasterLine; print('OK')"
```

2. **功能测试**:
- 启动后端: `python -B scripts\run_server_production.py`
- 启动前端: `cd frontend-nextjs && npm run dev`
- 访问 http://localhost:3001/search/test-session
- 输入测试问题，观察任务清单生成和进度更新

## 🔮 后续优化

1. **任务动态调整**: 根据搜索结果动态添加/修改任务
2. **探索触发判断**: 自动检测是否触发延展探索条件
3. **边界违规检测**: 检测搜索是否偏离边界并告警
4. **任务依赖关系**: 支持任务之间的前置依赖
