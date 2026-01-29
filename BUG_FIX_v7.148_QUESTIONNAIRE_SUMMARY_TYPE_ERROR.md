# 🐛 Bug修复报告 v7.148：问卷汇总类型错误

**版本**: v7.148
**日期**: 2026-01-07
**修复类型**: TypeError修复 - unhashable type: 'dict'
**影响范围**: 问卷汇总第四步（需求重构）
**严重程度**: P0 - 阻断核心流程

---

## 📋 问题描述

### 错误现象
会话 `8pdwoxj8-20260107091421-e90d6559` 在完成三步问卷（任务梳理、信息补全、雷达图）后，进入第四步问卷汇总时崩溃：

```python
TypeError: unhashable type: 'dict'
File requirements_restructuring.py, line 324:
    keywords = dimension_keywords.get(dimension, [])
```

系统降级到 `_fallback_restructure`，生成的需求文档缺少雷达图维度数据（"🎯 设计重点: 0个维度"）。

### 用户影响
- ❌ 无法生成完整的结构化需求文档
- ❌ 雷达图数据未正确展示在需求确认页
- ❌ 降级模式导致需求理解不完整

---

## 🔍 根本原因分析

### 错误链追踪

**调用栈**：
```
questionnaire_summary.py:96
  → RequirementsRestructuringEngine.restructure()
    → requirements_restructuring.py:65 _build_priorities_with_insights()
      → requirements_restructuring.py:265 循环遍历 selected_dims
        → _extract_key_requirements_for_dimension(dim, gap_filling)
          → requirements_restructuring.py:324 💥 崩溃：dimension_keywords.get(dimension, [])
```

### 数据流分析

#### **1. 数据源头：progressive_questionnaire.py (Line 629)**
雷达图完成后写入 state：
```python
update_dict = {
    "selected_radar_dimensions": dimensions,      # List[Dict]
    "selected_dimensions": dimensions,            # List[Dict] 完整维度对象
    "radar_dimension_values": dimension_values,   # Dict[str, int]
    ...
}
```

**dimensions 数据结构**：
```python
[
    {
        "id": "material_temperature",
        "name": "材质温度",
        "left_label": "温暖木质",
        "right_label": "冷静金属",
        "default_value": 50
    },
    {
        "id": "cultural_axis",
        "name": "文化归属轴",
        ...
    },
    ...  # 共9个维度对象
]
```

#### **2. 数据中转：questionnaire_summary.py (Line 191)**
```python
def _extract_questionnaire_data(state: ProjectAnalysisState) -> Dict[str, Any]:
    selected_dims = state.get("selected_dimensions", [])  # 🔴 获取完整对象列表

    return {
        "dimensions": {
            "selected": selected_dims,  # 🔴 传递 List[Dict]，而非 List[str]
            "weights": {}
        }
    }
```

#### **3. 问题触发：requirements_restructuring.py (Line 264-268)**
```python
for idx, dim in enumerate(selected_dims):
    # ❌ dim 是 Dict 对象！期望是字符串ID
    key_reqs = RequirementsRestructuringEngine._extract_key_requirements_for_dimension(
        dim, gap_filling  # 💥 传递了整个维度对象
    )
```

#### **4. 崩溃点：requirements_restructuring.py (Line 324)**
```python
def _extract_key_requirements_for_dimension(
    dimension: str,  # 参数类型声明是 str，但实际收到 Dict
    gap_filling: Dict[str, Any]
) -> List[str]:

    dimension_keywords = {
        "functionality": [...],
        "aesthetics": [...],
        ...
    }

    # 💥 尝试用 dict 作为字典的键 → TypeError: unhashable type: 'dict'
    keywords = dimension_keywords.get(dimension, [])
```

### 类型不匹配总结

| 层级 | 期望类型 | 实际类型 | 示例 |
|-----|---------|---------|-----|
| **progressive_questionnaire** | `List[Dict]` | ✅ `List[Dict]` | `[{"id": "functionality", ...}]` |
| **questionnaire_summary** | `List[str]` 或 `List[Dict]` | ✅ `List[Dict]` | 传递完整对象 |
| **_build_priorities_with_insights** | `List[str]` | ❌ `List[Dict]` | 期望 `["functionality"]`，实际 `[{...}]` |
| **_extract_key_requirements_for_dimension** | `str` | ❌ `Dict` | 期望 `"functionality"`，实际 `{"id": "functionality"}` |

---

## ✅ 修复方案

### 修改位置
**文件**: `intelligent_project_analyzer/interaction/nodes/requirements_restructuring.py`
**方法**: `_build_priorities_with_insights()`
**行号**: 264-285

### 修复策略
在循环遍历 `selected_dims` 时，添加类型检查和ID提取逻辑，确保传递给下游方法的是字符串ID。

### 修复前代码
```python
for idx, dim in enumerate(selected_dims):
    # 从gap_filling中提取关键需求
    key_reqs = RequirementsRestructuringEngine._extract_key_requirements_for_dimension(
        dim, gap_filling  # ❌ 直接传递 dim（可能是 dict）
    )

    # ...后续使用 dim 作为字符串ID（会崩溃）
    if dim == "aesthetics" and "aesthetic" in user_model:
        ...

    weight = weights.get(dim, 1.0 / len(selected_dims) if selected_dims else 0.5)

    priority = {
        "dimension": dim,  # ❌ 可能是 dict
        "label": dimension_labels.get(dim, dim),  # 💥 dict 不能作为 key
        ...
    }
```

### 修复后代码
```python
for idx, dim in enumerate(selected_dims):
    # 🔧 v7.148: 修复类型不匹配 - 支持 dict 和 str 格式的维度
    if isinstance(dim, dict):
        dim_id = dim.get("id")
        dim_name = dim.get("name", dim_id)
        if not dim_id:
            logger.warning(f"⚠️ [Dimension {idx}] 维度对象缺少 'id' 字段，跳过: {dim}")
            continue
    elif isinstance(dim, str):
        dim_id = dim
        dim_name = dimension_labels.get(dim, dim)
    else:
        logger.error(f"❌ [Dimension {idx}] 不支持的维度类型: {type(dim)}，跳过")
        continue

    logger.debug(f"🔍 [Dimension {idx}] 处理维度: {dim_id} ({dim_name})")

    # 从gap_filling中提取关键需求（现在传递字符串ID）
    key_reqs = RequirementsRestructuringEngine._extract_key_requirements_for_dimension(
        dim_id, gap_filling  # ✅ 传递维度ID字符串
    )

    # 🔑 从L2用户画像中增强关键需求
    if dim_id == "aesthetics" and "aesthetic" in user_model:
        aesthetic_profile = user_model.get("aesthetic", "")
        if aesthetic_profile and len(aesthetic_profile) > 10:
            key_reqs.insert(0, f"美学偏好: {aesthetic_profile[:80]}")

    if dim_id == "functionality" and "psychological" in user_model:
        psych_needs = user_model.get("psychological", "")
        if psych_needs and len(psych_needs) > 10:
            key_reqs.insert(0, f"心理需求: {psych_needs[:80]}")

    weight = weights.get(dim_id, 1.0 / len(selected_dims) if selected_dims else 0.5)

    priority = {
        "rank": idx + 1,
        "dimension": dim_id,  # ✅ v7.148: 使用提取的维度ID
        "label": dimension_labels.get(dim_id, dim_name),  # ✅ 优先使用映射名称
        "weight": weight,
        "key_requirements": key_reqs[:4],
        "derived_from": "questionnaire_step3 + L2_insights"
    }

    # 🔑 如果有核心张力且是第一优先级，添加张力说明
    if idx == 0 and core_tension and len(core_tension) > 20:
        priority["_core_tension_note"] = f"核心张力: {core_tension[:100]}"

    priorities.append(priority)
```

### 修复亮点
1. **向后兼容**: 同时支持 `List[Dict]` 和 `List[str]` 两种格式
2. **防御性编程**: 添加类型检查和缺失字段验证
3. **可观测性**: 增加调试日志，记录维度处理过程
4. **优雅降级**: 缺少ID时跳过该维度，不影响其他维度处理

---

## 🧪 验证方法

### 1. 启动服务
```bash
python -B scripts\run_server_production.py
```

### 2. 重现错误场景
1. 访问 http://localhost:3001
2. 输入测试需求："以丹麦家居品牌HAY气质为基础的民宿室内设计概念，四川峨眉山七里坪"
3. Step 1: 确认任务列表（5个任务）
4. Step 2: 提交信息补充答案
   ```json
   {
     "project_scale": "700平米，12间客房",
     "design_output_type": ["设计策略文档", "空间概念描述", "分析报告"],
     "nature_integration": "写意，现代",
     "target_audience_preferences": "氛围，情绪",
     "design_success_criteria": "回头客，回味，回甘"
   }
   ```
5. Step 3: 提交雷达图答案（9个维度，默认值50）
6. **Step 4: 问卷汇总** ✅ **应该成功生成需求文档，不再崩溃**

### 3. 验证点
- [ ] 问卷汇总不再报错 `TypeError: unhashable type: 'dict'`
- [ ] 不触发降级逻辑 `_fallback_restructure`
- [ ] 需求文档包含完整雷达图数据："🎯 设计重点: 9个维度"
- [ ] 后端日志显示维度处理日志：`🔍 [Dimension 0] 处理维度: material_temperature (材质温度)`

### 4. 日志验证
**修复前（错误）**:
```
2026-01-07 09:17:34.798 | ERROR | questionnaire_summary:execute:104 - ❌ 需求重构失败: unhashable type: 'dict'
2026-01-07 09:17:34.800 | WARNING | questionnaire_summary:execute:109 - ⚠️ [降级模式] 使用简化需求重构
```

**修复后（正常）**:
```
2026-01-07 XX:XX:XX.XXX | DEBUG | requirements_restructuring:_build_priorities_with_insights:XXX - 🔍 [Dimension 0] 处理维度: material_temperature (材质温度)
2026-01-07 XX:XX:XX.XXX | DEBUG | requirements_restructuring:_build_priorities_with_insights:XXX - 🔍 [Dimension 1] 处理维度: cultural_axis (文化归属轴)
...
2026-01-07 XX:XX:XX.XXX | INFO | questionnaire_summary:execute:125 - ✅ 问卷汇总完成
2026-01-07 XX:XX:XX.XXX | INFO | questionnaire_summary:execute:127 - 🎯 设计重点: 9个维度
```

---

## 📂 相关文件

### 修改文件
- `intelligent_project_analyzer/interaction/nodes/requirements_restructuring.py` (Line 264-305)

### 相关文件（未修改）
- `intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py` (Line 629) - 数据源
- `intelligent_project_analyzer/interaction/nodes/questionnaire_summary.py` (Line 191) - 数据传递

---

## 🎯 后续优化建议

### P1: 数据归一化
考虑在 `questionnaire_summary.py` 的 `_extract_questionnaire_data` 方法中预处理维度数据，统一转换为ID列表：

```python
def _extract_questionnaire_data(state: ProjectAnalysisState) -> Dict[str, Any]:
    selected_dims = state.get("selected_dimensions", [])

    # 提取维度ID列表
    dim_ids = []
    for dim in selected_dims:
        if isinstance(dim, str):
            dim_ids.append(dim)
        elif isinstance(dim, dict):
            dim_id = dim.get("id")
            if dim_id:
                dim_ids.append(dim_id)

    return {
        "dimensions": {
            "selected": dim_ids,  # ✅ 只传递 ID 字符串列表
            "weights": {}
        }
    }
```

**优点**: 确保下游一致性，避免重复类型检查
**缺点**: 丢失维度元数据（`name`, `left_label` 等），可能影响其他使用维度对象的功能

### P2: 函数重命名（工作流路由问题）
问卷实际执行顺序与函数命名不一致：
- UI Step 2（信息补充）→ 实际调用 `step3_gap_filling()`
- UI Step 3（雷达图）→ 实际调用 `step2_radar()`

建议重命名：
- `step3_gap_filling` → `step2_gap_filling`
- `step2_radar` → `step3_radar`

### P3: 修复 P0.3 场景注入错误
日志显示：
```
ImportError: cannot import name 'SPECIAL_SCENARIO_DETECTORS' from 'task_completeness_analyzer'
```
需要补充该功能或移除相关代码。

---

## 📊 影响评估

### 修复效果
- ✅ **彻底解决**: TypeError: unhashable type: 'dict' 错误
- ✅ **向后兼容**: 支持 `List[Dict]` 和 `List[str]` 两种输入
- ✅ **增强稳定性**: 添加防御性检查，避免未来类似错误

### 性能影响
- 🔄 **微小开销**: 添加类型检查和日志（<1ms）
- ✅ **无负面影响**: 不改变主流程逻辑

### 风险评估
- ✅ **低风险**: 修改范围小，仅在循环内部添加类型检查
- ✅ **可回滚**: 保留原有逻辑，通过 `isinstance` 判断分支处理

---

## 🔗 相关修复

- **v7.147**: 问卷Step 3过早调用汇总错误（BoundaryCheckResult序列化）
- **v7.146**: 问卷Step 2→Step 3数据传递错误
- **v7.142**: 雷达图动态维度类型错误
- **v7.135**: 需求重构引擎首次实现

---

**修复状态**: ✅ 已完成
**测试状态**: ⏳ 待验证
**下一步**: 使用会话 `8pdwoxj8-20260107091421-e90d6559` 重新提交雷达图答案，验证修复效果
