# SearchFramework v7.220 迁移指南

**版本**: v7.220
**日期**: 2026-01-21
**状态**: 生产就绪

---

## 📋 概述

v7.220 引入了新的统一搜索框架，替代了原来的双系统架构：
- **旧系统**: `AnswerFramework` + `SearchMasterLine` + `KeyAspect` + `SearchTask`
- **新系统**: `SearchFramework` + `SearchTarget`

---

## 🔄 核心变更

### 1. 数据结构映射

| 旧结构 | 新结构 | 说明 |
|--------|--------|------|
| `AnswerFramework` | `SearchFramework` | 统一的搜索框架 |
| `KeyAspect` | `SearchTarget` | 统一的搜索目标 |
| `SearchTask` | `SearchTarget` | 合并到 SearchTarget |
| `SearchMasterLine` | `SearchFramework` | 合并到 SearchFramework |

### 2. 字段映射

#### AnswerFramework → SearchFramework

| 旧字段 | 新字段 | 变更说明 |
|--------|--------|----------|
| `original_query` | `original_query` | 无变化 |
| `answer_goal` | `answer_goal` | 无变化 |
| `key_aspects` | `targets` | 类型从 `List[KeyAspect]` 改为 `List[SearchTarget]` |
| `collected_evidence` | `all_sources` | 重命名并简化 |
| `overall_completeness` | `overall_completeness` | 无变化 |
| - | `core_question` | **新增**: 问题本质 |
| - | `boundary` | **新增**: 搜索边界 |
| - | `l1_facts` | **新增**: L1 事实解构 |
| - | `l2_models` | **新增**: L2 多视角建模 |
| - | `l3_tension` | **新增**: L3 核心张力 |
| - | `l4_jtbd` | **新增**: L4 用户任务 |
| - | `l5_sharpness` | **新增**: L5 锐度评估 |
| - | `user_profile` | **新增**: 用户画像 |

#### KeyAspect → SearchTarget

| 旧字段 | 新字段 | 变更说明 |
|--------|--------|----------|
| `aspect_name` | `name` | 重命名 |
| `answer_goal` | `purpose` | 重命名 |
| `importance` | `priority` | 语义变化：1(高) / 2(中) / 3(低) |
| `collected_info` | `sources` | 类型从 `List[str]` 改为 `List[Dict]` |
| `source_urls` | - | 合并到 `sources` 中 |
| `search_query` | `search_queries` | 类型从 `str` 改为 `List[str]` |
| - | `description` | **新增**: 详细描述 |
| - | `category` | **新增**: 分类（基础/案例/验证） |
| - | `expected_info` | **新增**: 期望信息类型 |

### 3. 方法映射

#### SearchFramework 方法

| 旧方法 | 新方法 | 变更说明 |
|--------|--------|----------|
| `get_next_search_target()` | `get_next_target()` | 重命名 |
| `get_missing_aspects()` | - | 已移除，使用 `[t for t in targets if not t.is_complete()]` |
| `get_incomplete_aspects()` | - | 已移除，使用 `[t for t in targets if not t.is_complete()]` |
| `calculate_completeness()` | `update_completeness()` | 重命名，现在会更新 `overall_completeness` |
| `can_answer_completely()` | - | 已移除，检查 `overall_completeness >= 0.8` |

#### SearchTarget 方法

| 旧方法 | 新方法 | 变更说明 |
|--------|--------|----------|
| - | `is_complete()` | **新增**: 判断是否完成 |
| - | `mark_complete(score)` | **新增**: 标记为完成 |
| - | `mark_searching()` | **新增**: 标记为搜索中 |

---

## 🔧 迁移步骤

### 步骤 1: 更新导入

```python
# 旧代码
from intelligent_project_analyzer.services.ucppt_search_engine import (
    AnswerFramework,
    KeyAspect,
    SearchTask,
    SearchMasterLine,
)

# 新代码
from intelligent_project_analyzer.services.ucppt_search_engine import (
    SearchFramework,
    SearchTarget,
)
```

### 步骤 2: 更新数据结构创建

```python
# 旧代码
framework = AnswerFramework(
    original_query=query,
    answer_goal="回答目标",
    created_at=time.time(),
)

aspect = KeyAspect(
    id="A1",
    aspect_name="核心概念",
    answer_goal="解释基本定义",
    importance=5,
)

framework.key_aspects.append(aspect)

# 新代码
framework = SearchFramework(
    original_query=query,
    core_question="问题本质",
    answer_goal="回答目标",
    boundary="搜索边界",
)

target = SearchTarget(
    id="T1",
    name="核心概念",
    description="核心概念的详细描述",
    purpose="解释基本定义",
    priority=1,  # 1=高, 2=中, 3=低
)

framework.targets.append(target)
```

### 步骤 3: 更新方法调用

```python
# 旧代码
next_aspect = framework.get_next_search_target()
if next_aspect:
    print(f"搜索: {next_aspect.aspect_name}")
    next_aspect.collected_info.append("新信息")
    next_aspect.status = "complete"

framework.overall_completeness = framework.calculate_completeness()

# 新代码
next_target = framework.get_next_target()
if next_target:
    print(f"搜索: {next_target.name}")
    next_target.sources.append({
        "title": "来源标题",
        "url": "https://example.com",
        "content": "新信息",
    })
    next_target.mark_complete(1.0)

framework.update_completeness()  # 自动更新 overall_completeness
```

### 步骤 4: 更新状态检查

```python
# 旧代码
if aspect.status == "complete":
    print("已完成")

if framework.can_answer_completely():
    print("可以回答")

# 新代码
if target.is_complete():
    print("已完成")

if framework.overall_completeness >= 0.8:
    print("可以回答")
```

---

## ⚠️ 重要注意事项

### 1. 向后兼容性

旧的类（`AnswerFramework`, `KeyAspect`）仍然可用，但已标记为 **DEPRECATED**：

```python
@dataclass
class AnswerFramework:
    """
    ⚠️ DEPRECATED (v7.220): 此类已被 SearchFramework 替代
    保留此类仅用于向后兼容，新代码请使用 SearchFramework
    """
```

**建议**:
- ✅ 新代码：使用 `SearchFramework` 和 `SearchTarget`
- ⚠️ 旧代码：可以继续使用，但建议逐步迁移
- 🔮 未来：旧类可能在 v8.0 中移除

### 2. 优先级语义变化

**重要**: `importance` 和 `priority` 的语义相反！

```python
# 旧代码 (KeyAspect)
importance = 5  # 5 = 最重要
importance = 1  # 1 = 最不重要

# 新代码 (SearchTarget)
priority = 1  # 1 = 最高优先级
priority = 3  # 3 = 最低优先级
```

**转换公式**:
```python
priority = 6 - importance  # 5 → 1, 4 → 2, 3 → 3, 2 → 4, 1 → 5
```

### 3. 数据类型变化

#### collected_info → sources

```python
# 旧代码
aspect.collected_info = ["信息1", "信息2"]
aspect.source_urls = ["url1", "url2"]

# 新代码
target.sources = [
    {"title": "标题1", "url": "url1", "content": "信息1"},
    {"title": "标题2", "url": "url2", "content": "信息2"},
]
```

#### search_query → search_queries

```python
# 旧代码
aspect.search_query = "搜索词"

# 新代码
target.search_queries = ["搜索词1", "搜索词2"]
```

---

## 📊 迁移检查清单

使用此清单确保完整迁移：

### 代码迁移
- [ ] 更新所有 `AnswerFramework` 引用为 `SearchFramework`
- [ ] 更新所有 `KeyAspect` 引用为 `SearchTarget`
- [ ] 更新字段名：`aspect_name` → `name`
- [ ] 更新字段名：`answer_goal` → `purpose`
- [ ] 更新字段名：`key_aspects` → `targets`
- [ ] 转换优先级：`importance` → `priority` (反向)
- [ ] 更新方法调用：`get_next_search_target()` → `get_next_target()`
- [ ] 更新方法调用：`calculate_completeness()` → `update_completeness()`
- [ ] 更新数据类型：`collected_info` → `sources` (List[str] → List[Dict])
- [ ] 更新数据类型：`search_query` → `search_queries` (str → List[str])

### 测试
- [ ] 运行单元测试
- [ ] 运行集成测试
- [ ] 验证向后兼容性
- [ ] 性能测试

### 文档
- [ ] 更新 API 文档
- [ ] 更新代码注释
- [ ] 更新示例代码
- [ ] 添加迁移指南链接

---

## 🎯 最佳实践

### 1. 渐进式迁移

不要一次性迁移所有代码，建议按模块逐步迁移：

1. **第一阶段**: 新功能使用新结构
2. **第二阶段**: 迁移核心模块
3. **第三阶段**: 迁移辅助模块
4. **第四阶段**: 清理旧代码

### 2. 使用类型提示

```python
from typing import List
from intelligent_project_analyzer.services.ucppt_search_engine import (
    SearchFramework,
    SearchTarget,
)

def process_search(framework: SearchFramework) -> List[SearchTarget]:
    """处理搜索框架"""
    return [t for t in framework.targets if not t.is_complete()]
```

### 3. 添加迁移注释

```python
# TODO(v7.220): 迁移到 SearchFramework
# 当前使用 AnswerFramework 以保持向后兼容
framework = AnswerFramework(...)
```

---

## 🆘 常见问题

### Q1: 旧代码还能用吗？

**A**: 是的，旧的 `AnswerFramework` 和 `KeyAspect` 仍然可用，但已标记为废弃。建议新代码使用 `SearchFramework` 和 `SearchTarget`。

### Q2: 什么时候会移除旧类？

**A**: 计划在 v8.0 中移除。在此之前会有充足的迁移时间。

### Q3: 如何处理混合使用的情况？

**A**: 可以在同一代码库中混合使用新旧结构，但建议在模块边界处进行转换：

```python
def convert_to_new_framework(old: AnswerFramework) -> SearchFramework:
    """将旧框架转换为新框架"""
    new = SearchFramework(
        original_query=old.original_query,
        answer_goal=old.answer_goal,
    )

    for aspect in old.key_aspects:
        target = SearchTarget(
            id=aspect.id,
            name=aspect.aspect_name,
            description=aspect.answer_goal,
            purpose=aspect.answer_goal,
            priority=6 - aspect.importance,  # 转换优先级
        )
        new.targets.append(target)

    return new
```

### Q4: 性能有影响吗？

**A**: 新结构性能更优：
- SearchTarget 创建: 1000个 < 100ms
- 完成度更新: 100次 < 100ms
- 内存占用: 相当或更少

### Q5: 如何获取帮助？

**A**:
- 查看测试文件: `tests/test_search_framework_v7220.py`
- 查看测试报告: `TEST_REPORT_v7220.md`
- 查看源码注释: `intelligent_project_analyzer/services/ucppt_search_engine.py`

---

## 📚 相关文档

- [TEST_REPORT_v7220.md](./TEST_REPORT_v7220.md) - 测试报告
- [tests/test_search_framework_v7220.py](./tests/test_search_framework_v7220.py) - 测试用例
- [CHANGELOG.md](./CHANGELOG.md) - 变更日志

---

## ✅ 迁移完成标准

当满足以下条件时，可以认为迁移完成：

1. ✅ 所有新代码使用 `SearchFramework` 和 `SearchTarget`
2. ✅ 所有测试通过（单元测试 + 集成测试）
3. ✅ 性能测试通过
4. ✅ 文档已更新
5. ✅ 代码审查通过
6. ✅ 生产环境验证通过

---

**文档版本**: v1.0
**最后更新**: 2026-01-21
**维护者**: Claude Code Team
