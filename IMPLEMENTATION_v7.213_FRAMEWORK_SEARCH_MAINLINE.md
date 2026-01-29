# v7.213 框架性搜索任务主线增强

## 📋 实施概述

**版本**: v7.213
**日期**: 2026-01-16
**目标**: 增强问题分析阶段的搜索任务规划，建立明确的框架性主线，支持动态延展和阶段复盘

## 🎯 核心改进

### 1. 框架性搜索任务设计

#### 阶段化组织
```
阶段1: 基础信息 (P1任务) → 核心概念、定义、背景
阶段2: 深度案例 (P2任务) → 具体案例、最佳实践、经验
阶段3: 对比验证 (P3任务) → 对比分析、争议观点、补充
```

#### SearchTask 增强字段 (v7.213)
```python
@dataclass
class SearchTask:
    # 原有字段
    id: str                      # 任务ID
    task: str                    # 任务描述
    purpose: str                 # 任务目的
    priority: int                # 优先级 P1/P2/P3
    status: str                  # pending/searching/complete

    # v7.213 新增
    phase: str                   # 所属阶段（基础信息/深度案例/对比验证）
    depends_on: List[str]        # 依赖的任务ID列表
    validation_criteria: List[str]  # 验证标准
    is_extension: bool           # 是否为延展任务
    extended_from: str           # 延展来源
    extension_reason: str        # 延展原因
```

#### SearchMasterLine 增强字段 (v7.213)
```python
@dataclass
class SearchMasterLine:
    # 原有字段
    core_question: str           # 问题本质
    boundary: str                # 搜索边界
    search_tasks: List[SearchTask]
    exploration_triggers: List[str]
    forbidden_zones: List[str]

    # v7.213 新增
    framework_summary: str       # 搜索路线图概览
    search_phases: List[str]     # 阶段列表
    checkpoint_rounds: List[int] # 复盘检查点轮次
    extension_log: List[Dict]    # 延展日志
```

### 2. 阶段复盘检查点

在指定轮次（默认第2、4、6轮）触发阶段复盘：

```python
async def _generate_phase_checkpoint(self, master_line, framework, current_round, all_sources):
    """
    阶段复盘检查点：
    1. 评估当前阶段完成度
    2. 检查探索触发条件
    3. 决定是否添加延展任务
    4. 生成下一步建议
    """
```

**输出事件**: `phase_checkpoint`
```json
{
    "type": "phase_checkpoint",
    "data": {
        "round": 2,
        "checkpoint_summary": "基础信息阶段已完成80%...",
        "current_phase": "基础信息",
        "phase_completion": 0.8,
        "key_findings": ["发现1", "发现2"],
        "gaps_identified": ["缺口1"],
        "triggered_conditions": ["案例不足触发补充搜索"],
        "extension_tasks": [...],
        "next_steps": "进入深度案例阶段",
        "phase_progress": {...}
    }
}
```

### 3. 动态延展任务

当复盘检查点发现需要补充信息时，自动创建延展任务：

```python
def add_extension_task(self, task, trigger, reason):
    """添加延展任务并记录日志"""
    task.is_extension = True
    task.extended_from = trigger
    task.extension_reason = reason
    self.search_tasks.append(task)
    self.extension_log.append({
        "task_id": task.id,
        "trigger": trigger,
        "reason": reason,
        "timestamp": time.time(),
        "priority": task.priority,
    })
```

### 4. 搜索历程最终回顾

在所有搜索完成后，生成完整的搜索回顾报告：

```python
async def _generate_search_retrospective(self, master_line, framework, total_rounds, all_sources, rounds):
    """
    搜索历程回顾：
    1. 回顾搜索路径
    2. 评估任务贡献
    3. 识别关键转折点
    4. 总结有价值发现
    5. 指出知识盲区
    """
```

**输出事件**: `search_retrospective`
```json
{
    "type": "search_retrospective",
    "data": {
        "total_rounds": 6,
        "total_tasks": 5,
        "completed_tasks": 4,
        "extension_tasks_count": 1,
        "retrospective_narrative": "搜索历程回顾叙述...",
        "framework_adherence": 0.85,
        "key_discoveries": ["重要发现1", "重要发现2"],
        "turning_points": ["关键转折点"],
        "mainline_contribution": "主线任务贡献...",
        "extension_contribution": "延展任务贡献...",
        "knowledge_gaps": ["仍存在的盲区"],
        "search_efficiency_score": 0.8,
        "overall_assessment": "整体评价"
    }
}
```

### 5. 优化的提示词

`_build_unified_analysis_prompt` 提示词增强：

**框架设计要求**:
- 将搜索分为3个阶段（必须明确）
- 明确任务间的前置依赖关系
- 每个任务需有验证标准

**JSON 输出结构增强**:
```json
{
    "search_master_line": {
        "core_question": "...",
        "boundary": "...",
        "framework_summary": "分3阶段搜索-基础定义→案例分析→对比验证",
        "search_phases": ["基础信息", "深度案例", "对比验证"],
        "checkpoint_rounds": [2, 4, 6],
        "search_tasks": [
            {
                "id": "T1",
                "task": "...",
                "purpose": "...",
                "priority": 1,
                "phase": "基础信息",
                "depends_on": [],
                "expected_info": [...],
                "validation_criteria": ["获取2+权威来源", "覆盖主要定义"]
            }
        ],
        "exploration_triggers": [...],
        "forbidden_zones": [...]
    }
}
```

## 📁 修改的文件

### `intelligent_project_analyzer/services/ucppt_search_engine.py`

1. **SearchTask 数据类** (lines 340-395)
   - 新增字段: `phase`, `depends_on`, `validation_criteria`, `is_extension`, `extended_from`, `extension_reason`
   - 更新 `to_dict()` 方法

2. **SearchMasterLine 数据类** (lines 397-570)
   - 新增字段: `framework_summary`, `search_phases`, `checkpoint_rounds`, `extension_log`
   - 增强 `get_next_task()`: 支持任务依赖检查
   - 新增 `_get_current_phase()`: 获取当前阶段
   - 新增 `get_phase_progress()`: 获取阶段进度
   - 新增 `should_checkpoint()`: 检查复盘时机
   - 新增 `add_extension_task()`: 添加延展任务
   - 更新 `to_dict()` 和 `from_dict()`

3. **_build_unified_analysis_prompt** (lines 1720-1920)
   - 增强搜索任务规划说明
   - 更新 JSON 输出结构
   - 添加框架性规划指南

4. **_parse_search_master_line** (lines 2050-2100)
   - 支持解析新字段

5. **搜索循环** (lines 1555-1590)
   - 添加阶段复盘检查点调用
   - 处理延展任务添加

6. **新增方法: _generate_phase_checkpoint** (lines 3960-4090)
   - 生成阶段复盘检查点事件

7. **新增方法: _generate_search_retrospective** (lines 4095-4220)
   - 生成搜索历程最终回顾事件

8. **搜索完成后** (lines 1660-1670)
   - 添加搜索历程回顾调用

## 🔄 新增事件类型

| 事件类型 | 触发时机 | 用途 |
|---------|---------|------|
| `phase_checkpoint` | 检查点轮次 | 展示阶段复盘结果 |
| `search_retrospective` | 搜索完成后 | 展示搜索历程回顾 |
| `task_progress` (已有) | 任务完成时 | 展示任务进度 |

## 🎯 使用示例

### 前端展示建议

```typescript
// 处理阶段复盘检查点
if (event.type === 'phase_checkpoint') {
    const { checkpoint_summary, phase_progress, extension_tasks } = event.data;

    // 显示阶段进度条
    renderPhaseProgress(phase_progress);

    // 如果有延展任务，显示提示
    if (extension_tasks.length > 0) {
        showNotification(`发现${extension_tasks.length}个延展探索方向`);
    }
}

// 处理搜索历程回顾
if (event.type === 'search_retrospective') {
    const { retrospective_narrative, key_discoveries, framework_adherence } = event.data;

    // 显示回顾卡片
    renderRetrospectiveCard({
        narrative: retrospective_narrative,
        discoveries: key_discoveries,
        adherence: framework_adherence
    });
}
```

## ✅ 测试建议

1. **单元测试**:
   - 测试 `SearchTask` 新字段序列化/反序列化
   - 测试 `SearchMasterLine.get_next_task()` 依赖检查
   - 测试 `SearchMasterLine.add_extension_task()` 日志记录

2. **集成测试**:
   - 测试完整搜索流程中的阶段复盘
   - 测试延展任务自动添加
   - 测试搜索历程回顾生成

## 📝 版本历史

- **v7.208**: 初始搜索任务清单机制
- **v7.213**: 框架性搜索任务主线增强
  - 阶段化组织
  - 任务依赖
  - 阶段复盘检查点
  - 动态延展任务
  - 搜索历程回顾
