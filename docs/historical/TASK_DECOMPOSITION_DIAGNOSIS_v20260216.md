# 任务梳理质量诊断报告 v20260216

## 问题描述

用户反馈：analysis-20260216135722-a98fe3898d79 和 analysis-20260216135001-af54b821fc95 两个会话的任务梳理存在以下问题：
1. 任务分类混乱，层次不够清晰
2. 任务数量和质量都不对

## 日志分析

### 会话 analysis-20260216135001-af54b821fc95

#### 任务生成流程

```
Phase 1: 生成15个任务类别
Phase 2: 每个类别生成3个任务 = 45个任务
最终截断到: 36个任务（推荐上限）
```

#### 生成的15个类别

1. 狮岭村农耕文化与传统工艺挖掘
2. 安藤忠雄精神性空间在民宿集群的转译
3. 隈研吾材料诗性在乡村民宿中的应用
4. 刘家琨地域建筑智慧与在地材料体系解读
5. 云峰镇乡村经济逻辑与产业结构优化研究
6. 王澍建筑纹理与乡土空间表达在项目中的延伸
7. 新农村民宿商业模式的融合与可持续运营模型
8. 狮岭村自然景观与空间格局分析
9. 室内设计语言对乡村人文气质的诠释
10. 地域气候条件对于建筑设计的技术性影响分析
11. 村庄公共空间组织与社区文化纽带的构建
12. 谢柯建筑原则与村落场所精神的结合尝试
13. 乡村手工艺品展示与文旅商业空间规划
14. 低碳理念在乡村建筑改造中的设计策略
15. 融合传统工艺与现代技术的材料创新尝试

## 根本原因分析

### 1. 类别设计问题

**问题**: Phase 1 生成的类别名称过长、过于具体化

**代码位置**: `core_task_decomposer.py:1962-1972`

```python
要求：
1. 生成13-15个**任务类别**（category），每个类别对应设计流程的一个关键领域
2. **类别名称必须体现项目的具体特征**（如地点、文化元素、设计师风格、特殊需求等）
```

**问题分析**:
- 提示词要求"类别名称必须体现项目的具体特征"导致类别名称过度具体化
- 例如："狮岭村农耕文化与传统工艺挖掘" 本应是一个简洁的类别名（如"文化调研"），但被要求包含地点、文化元素等具体信息
- 这导致类别本身就像是任务标题，而不是任务分类

### 2. 任务粒度问题

**问题**: 每个类别固定生成3个任务，粒度控制不灵活

**代码位置**: `core_task_decomposer.py:1964`

```python
3. 为每个类别指定**子任务数量**（subtask_count: 固定3个）
```

**问题分析**:
- 所有类别都固定3个子任务，缺乏灵活性
- 某些重要类别可能需要更多任务（如文化调研可能需要5-6个任务）
- 某些简单类别可能只需要1-2个任务（如气候分析）

### 3. 类别层次混乱

**问题**: 15个类别之间缺乏清晰的层次结构和逻辑关系

**问题分析**:
- 类别1-7: 混合了文化调研、设计师风格、商业模式等不同维度
- 类别8-11: 场地分析和空间设计
- 类别12-15: 技术策略和材料创新
- 缺乏统一的分类逻辑（按设计阶段？按专业维度？按空间层次？）

### 4. 任务截断机制问题

**代码位置**: `core_task_decomposer.py:1712-1714`

```python
if len(merged) > max_tasks:
    logger.warning(f"⚠️ [Merge] 任务总数 {len(merged)} 超过上限 {max_tasks}, 智能截断")
    merged = merged[:max_tasks]
```

**问题分析**:
- 生成45个任务后简单截断到36个
- 截断逻辑只按优先级排序，可能导致某些类别的任务被完全删除
- 缺乏类别平衡机制

## 解决方案

### 方案A: 优化类别设计（推荐）

**修改点1**: 简化类别名称，使用标准化的设计流程分类

```python
# 修改 core_task_decomposer.py:1962-1972
要求：
1. 生成8-10个**标准任务类别**，覆盖设计流程的关键阶段
2. 类别名称应简洁通用（如"场地调研"、"文化分析"、"概念设计"等）
3. 类别描述中体现项目具体特征
4. 为每个类别指定**灵活的子任务数量**（2-5个，根据类别重要性）
```

**修改点2**: 调整类别数量和子任务分配

```python
# 目标: 8-10个类别 × 3-4个任务 = 28-36个任务
outline_prompt = f"""
生成8-10个任务类别，每个类别2-5个子任务：

标准类别参考：
1. 场地调研与分析（4-5个任务）
2. 文化背景与元素提炼（4-5个任务）
3. 用户需求与行为研究（3-4个任务）
4. 设计对标与参考研究（3-4个任务）
5. 概念设计与空间策略（4-5个任务）
6. 技术系统与材料策略（3-4个任务）
7. 商业模式与运营策略（2-3个任务）
8. 可持续性与创新策略（2-3个任务）

输出格式：
{{
  "outline": [
    {{
      "category": "场地调研与分析",
      "description": "针对狮岭村的地形、气候、景观等进行系统调研",
      "subtask_count": 4,
      "priority": "high"
    }}
  ]
}}
"""
```

### 方案B: 改进截断机制

**修改点**: 实现类别平衡的智能截断

```python
def _balanced_truncate(tasks: List[Dict], max_tasks: int, categories: List[str]) -> List[Dict]:
    """
    类别平衡的智能截断

    策略:
    1. 统计每个类别的任务数
    2. 优先保留high priority任务
    3. 确保每个类别至少保留1-2个任务
    4. 按优先级和类别平衡性截断
    """
    # 按类别分组
    category_tasks = {}
    for task in tasks:
        cat = task.get('category', 'unknown')
        if cat not in category_tasks:
            category_tasks[cat] = []
        category_tasks[cat].append(task)

    # 每个类别至少保留2个high priority任务
    result = []
    for cat, cat_tasks in category_tasks.items():
        high_priority = [t for t in cat_tasks if t.get('priority') == 'high']
        result.extend(high_priority[:2])

    # 剩余配额按优先级分配
    remaining = max_tasks - len(result)
    all_remaining = [t for t in tasks if t not in result]
    all_remaining.sort(key=lambda x: {'high': 3, 'medium': 2, 'low': 1}.get(x.get('priority', 'medium'), 2), reverse=True)
    result.extend(all_remaining[:remaining])

    return result
```

### 方案C: 添加质量验证

**修改点**: 在Phase 2完成后添加质量检查

```python
# 在 core_task_decomposer.py:2120 之后添加
logger.info(f"🎉 Phase 2完成: 总计生成{len(llm_tasks)}个任务")

# 质量验证
quality_issues = []
category_distribution = {}
for task in llm_tasks:
    cat = task.get('category', 'unknown')
    category_distribution[cat] = category_distribution.get(cat, 0) + 1

# 检查类别分布
if len(category_distribution) > 12:
    quality_issues.append(f"类别过多: {len(category_distribution)}个（建议8-10个）")

# 检查类别任务数分布
for cat, count in category_distribution.items():
    if count < 2:
        quality_issues.append(f"类别'{cat}'任务过少: {count}个")
    if count > 6:
        quality_issues.append(f"类别'{cat}'任务过多: {count}个")

if quality_issues:
    logger.warning(f"⚠️ 任务质量问题 ({len(quality_issues)}个):")
    for issue in quality_issues:
        logger.warning(f"  - {issue}")
```

## 推荐实施顺序

1. **立即修复**: 方案A - 优化类别设计（修改提示词）
2. **短期优化**: 方案B - 改进截断机制（修改代码逻辑）
3. **长期改进**: 方案C - 添加质量验证（增强监控）

## 预期效果

修复后的任务梳理应该：
- 类别清晰: 8-10个标准化类别，层次分明
- 任务合理: 每个类别2-5个任务，总计28-36个
- 分布均衡: 避免某些类别任务过多或过少
- 质量可控: 有明确的质量验证机制
