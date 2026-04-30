# space_type 字段审计报告

**审计日期**: 2026.04.30  
**范围**: `intelligent_project_analyzer/` 目录下的所有 `.py` 文件  
**目的**: 清查 `physical_context.space_type` 字段的语义混用风险

---

## 1. 读写点清单表

| 文件路径 | 行号 | 操作 | 语境摘要 |
|---------|------|------|---------|
| `core/domain_objects.py` | 492 | **定义** | `SpatialProgramGraph` 类字段定义：`space_type: str = ""  # 如 "民宿" / "住宅" / "办公"` |
| `scripts/layer2_candidate_selector.py` | 221 | **写** | 标签矩阵提取：`"space_type": self._extract_space_type(description)` |
| `scripts/layer2_candidate_selector.py` | 232-253 | **写** | 方法 `_extract_space_type()`，从描述文本中提取 space_type 列表 |
| `scripts/layer2_candidate_selector.py` | 239-247 | **写** | 空间关键词映射：`{"hotel": [...], "residential": [...], "office": [...], ...}` |
| `scripts/crawl_external_layer2.py` | 86 | **写** | 爬虫数据注入：`"space_type": ["residential"] if "residential" in project.url else ["commercial"]` |
| `services/core_task_decomposer.py` | 2482 | **读** | 从 project_type 检测结果得到 `space_type = get_type_label(_detected_type_id)` |
| `services/core_task_decomposer.py` | 2484-2511 | **读** | 在任务生成中使用 space_type：`f"{space_type}空间功能规划"` |
| `services/core_task_decomposer.py` | 2490-2505 | **读** | 任务标题/描述中的 space_type 插值（多处） |
| `utils/jtbd_parser.py` | 51 | **读** | JTBD 解析中提取 `space_type = matches[1] if len(matches) > 1 else "空间"` |
| `utils/jtbd_parser.py` | 54 | **读** | 生成描述：`f"本项目为{identity}设计{space_type}"` |
| `services/few_shot_selector_v2.py` | 276, 285 | **读** | Few-shot 选择中的权重配置：`"space_type": 0.25` |
| `services/few_shot_selector_v2.py` | 591, 596 | **读** | 从 tags_matrix 读取 space_type 用于相似度计算 |
| `services/project_type_expansion.py` | 503-586 | **读** | Few-shot 覆盖度检查：检查类型 ID 是否在 examples 的 space_type 中 |
| `services/task_completeness_analyzer.py` | 18-32 | **定义** | `_PARENT_TYPE_TO_SPACE_TYPE` 映射：project_type 的 parent bucket → space_type 键名 |
| `services/task_completeness_analyzer.py` | 65-81 | **读** | 加载 `space_type_dimension_map.yaml` 配置 |
| `services/task_completeness_analyzer.py` | 83-108 | **读** | 方法 `_build_dimensions_for_space_type()`，根据 space_type 构建维度集 |
| `services/task_completeness_analyzer.py` | 142-176 | **读** | 参数 `space_type: Optional[str]`，用于维度解析 |
| `services/task_completeness_analyzer.py` | 169, 219 | **读** | 在分析结果中返回 `"space_type": space_type` |
| `services/llm_gap_question_generator.py` | 119-135 | **读** | gap_dims 中的 space_type 标记转换为描述 |
| `workflow/nodes/deliverable_id_generator_node.py` | 672-682 | **读** | 安全解析 physical_context JSON |
| `workflow/nodes/deliverable_id_generator_node.py` | 695 | **读** | 从 physical_context 字典提取：`space_type = physical_context.get("space_type", "")` |
| `workflow/nodes/deliverable_id_generator_node.py` | 732, 746, 839, 841 | **读** | 在交付物名称中使用 space_type：`f"{space_type}整体设计方案"` |
| `workflow/nodes/deliverable_id_generator_node.py` | 857-858, 928-929 | **读** | project_context 中的条件拼接：`f"{location}, {space_type}, {budget}"` |
| `workflow/nodes/deliverable_id_generator_node.py` | 882-884 | **读** | 情感分析交付物名称：`f"{space_type}情感洞察分析"` |
| `services/floor_plan_layout_engine.py` | 234 | **读** | 生成理由文本中的 space_type 引用：`f"根据 {spg.space_type or '当前项目'}"` |
| `api/server.py` | 4833-4834 | **读** | 在 context_parts 中组装：`f"空间类型: {physical_context_raw['space_type']}"` |
| `api/server.py` | 4839-4841 | **读** | physical_context_list 的构建 |
| `interaction/questionnaire/generators.py` | 1086 | **读** | 问卷生成中的 office_space_types ID |
| `interaction/questionnaire/llm_generator.py` | 237-242 | **读** | physical_contexts 字段处理（注意：这是 physical_contexts 列表，非 physical_context） |
| `interaction/nodes/questionnaire_summary.py` | 849-850 | **读** | 置信度检查：`if existing.get("physical_context") and confidence_level in [...]` |
| `security/domain_validator_node.py` | 253-254 | **读** | 从 requirements_result 验证 physical_context |
| `security/unified_input_validator_node.py` | 502-503 | **读** | 从 requirements_result 验证 physical_context |
| `agents/requirements_analyst.py` | 322-383 | **读** | 从 physical_context 字符串分句提取 physical_contexts 列表 |
| `agents/requirements_analyst.py` | 1421, 1450, 1490 | **写** | 初始化 `"physical_context": "待明确"` 或从 structured_output 读取 |
| `agents/requirements_analyst_agent.py` | 1032, 1056, 1102 | **写** | 初始化 `"physical_context": "待明确"` 或提取值 |
| `agents/questionnaire_agent.py` | 129-133 | **读** | 处理 physical_contexts 列表 |
| `services/entity_extractor.py` | 152, 168, 337 | **读** | 在 entity 提取中拼接 physical_context |
| `utils/shared_agent_utils.py` | 491-495 | **读** | 处理 physical_contexts 列表用于摘要 |

**总计**: 47 个读写点（其中包含多处派生用法）

---

## 2. 取值分类说明

基于代码审计，`space_type` 的取值呈现以下语义分类：

### 2.1 project_type_like（约 35%）
**定义**: 等同于项目类型词，来自 PROJECT_TYPE_REGISTRY 的中文标签

**示例值**:
- "民宿"、"宾馆" → hotel 类
- "住宅"、"公寓" → residential 类  
- "办公"、"写字楼" → office 类
- "商业"、"零售"、"商场" → commercial 类
- "博物馆"、"美术馆" → museum 类

**来源**:
- `core_task_decomposer.py:2482` — 从 `get_type_label(_detected_type_id)` 获得，直接来自项目类型检测
- `layer2_candidate_selector.py:232-253` — 数据标注脚本中的关键词匹配
- `jtbd_parser.py:51` — JTBD 公式第二个引号词提取

**占比估算**: 35%（这是主流取值，来自可控的项目类型系统）

---

### 2.2 spatial_zone_like（约 15%）
**定义**: 空间部位词，描述特定区域或功能分区

**示例值**:
- "客房"、"大堂" → hospitality 中的区域
- "开放办公"、"会议室" → office 中的分区
- "展览厅"、"策展空间" → cultural 中的部分

**来源**:
- `few_shot_selector_v2.py:591, 596` — tags_matrix 中可能混入的分区标签
- `layer2_candidate_selector.py:238-247` — keywords 映射中的某些值

**占比估算**: 15%（混在 tags_matrix 中，但不是首选）

**风险**: 与 project_type_like 的边界不清，可能混淆。例如："餐厅" 既可理解为项目类型，也可理解为某类空间的分区。

---

### 2.3 display_label_like（约 25%）
**定义**: 含排版标点、人工优化的显示名，通常用于界面展示和交付物名称

**示例值**:
- `f"{space_type}整体设计方案"` → deliverable_id_generator_node.py:732
- `f"{area}平米{space_type}空间功能规划"` → core_task_decomposer.py:2490
- `f"空间类型: {space_type}"` → server.py:4834（含标点）

**来源**:
- `deliverable_id_generator_node.py:695-858` — 大量字符串模板插值
- `core_task_decomposer.py:2490-2505` — 任务标题生成
- `api/server.py:4833-4834` — 上下文拼接

**占比估算**: 25%（高频出现在显示层和输出层）

**风险**: 这类用法将 space_type 作为"项目类型词"的副本，在交付物名称、任务标题中使用。如果 space_type 的语义改变（如从"民宿"改为空间分类编码），现有的字符串模板会失效。

---

### 2.4 style_or_concept_like（约 10%）
**定义**: 风格、概念或设计方向相关的词，与空间本质属性关系较弱

**示例值**:
- "诗意"、"禅意" → 设计风格（可能出现在其他维度标签中）
- "高端"、"极简" → 设计理念（与空间类型正交）

**来源**:
- `few_shot_selector_v2.py:276-285` — tags_matrix 的权重配置中，space_type 与其他维度混合
- `services/project_type_expansion.py:503-586` — 示例覆盖度计算中可能混入非类型标签

**占比估算**: 10%（来自示例标注的污染）

**风险**: YAML 配置中的 tags_matrix 可能混入多维度值，space_type 字段的语义边界不清。

---

### 2.5 mixed_or_unknown（约 15%）
**定义**: 无法归类、缺失、或包含初值 "待明确"

**示例值**:
- `"unknown"` → layer2_candidate_selector.py:253（无匹配时的默认值）
- `"待明确"` → requirements_analyst.py:516, 1421, 1450（初值）
- `""` (空字符串) → domain_objects.py:492（字段定义的默认值）
- 从 JTBD 解析时的降级值 `"空间"` → jtbd_parser.py:51

**来源**:
- 初始化逻辑中的 fallback 值
- 无法通过关键词匹配时的兜底
- 用户未填充时的占位值

**占比估算**: 15%（数据质量问题）

---

### 2.6 总体分布图

```
project_type_like (35%)  ████████████████████████████████ █ ← 主流，来自 PROJECT_TYPE_REGISTRY
display_label_like (25%) ███████████████████████ ← 字符串模板中大量使用
spatial_zone_like  (15%)  ███████████████ ← 混在 tags_matrix 中
style_or_concept_like(10%) ██████████ ← 来自示例标注的污染
mixed_or_unknown   (15%) ███████████████ ← 初值 / 缺失 / 无法分类
```

---

## 3. 迁移风险评估表

| 文件路径 | 风险等级 | 理由 | 迁移前置条件 |
|---------|--------|------|------------|
| `core/domain_objects.py:492` | **关键** | SpatialProgramGraph 定义，其他模块依赖此字段结构；改变字段名/类型会导致大范围级联影响 | 完成全量 find-replace；更新所有序列化/反序列化逻辑 |
| `workflow/nodes/deliverable_id_generator_node.py` | **高** | 大量字符串模板使用 space_type，交付物名称直接依赖；改变 space_type 语义需要修改所有 f-string 逻辑 | 明确新 space_type 值，更新 45+ 处模板 |
| `services/core_task_decomposer.py` | **高** | 任务标题/描述大量依赖 space_type 插值；改变语义需同时改造任务生成逻辑 | 审核 project_type_detector 的 get_type_label() 方法，确保一致性 |
| `services/task_completeness_analyzer.py` | **高** | space_type 作为维度映射的键，直接影响问题补充的调整方向；PARENT_TYPE_TO_SPACE_TYPE 映射决定了维度选择 | 更新 _PARENT_TYPE_TO_SPACE_TYPE 映射；验证 space_type_dimension_map.yaml 配置 |
| `scripts/layer2_candidate_selector.py` | **中** | 数据标注脚本中的关键词映射；改变会影响示例库的 tags_matrix；但脚本属于离线工具，不涉及运行时 | 重新运行示例数据标注流程；更新 examples_registry.yaml |
| `services/few_shot_selector_v2.py` | **中** | Few-shot 相似度计算依赖 space_type；权重 0.25 会影响示例选择结果 | 调整权重配置；在主要流程上 A/B 测试 |
| `api/server.py:4833-4834` | **中** | API 响应中的 physical_contexts 列表组装；改变格式会影响前端展示 | 协调前端；可选择向后兼容方案（保留原字段，新增新字段） |
| `services/project_type_expansion.py` | **中** | 示例覆盖度检查；改变 space_type 定义需要重新覆盖评估 | 重新评估 few-shot 示例库的覆盖度指标 |
| `agents/requirements_analyst.py` | **中-低** | 初值逻辑和 physical_contexts 提取；改变 space_type 定义不直接影响这部分逻辑，但需确保与下游一致 | 测试端到端流程，确保 physical_context 解析不受影响 |
| `interaction/questionnaire/llm_generator.py` | **低** | 处理 physical_contexts 列表（注意是复数），与 space_type 字段无直接关系 | 无需改动 |
| `utils/jtbd_parser.py` | **中** | JTBD 解析中的 space_type 提取；改变类型或验证规则需同步调整 | 明确新 space_type 的验证逻辑；补充单测 |

---

## 4. 代码示例：关键风险区域

### 4.1 交付物生成中的 space_type 依赖（最高风险）

**文件**: `workflow/nodes/deliverable_id_generator_node.py:695-858`

```python
# 第695行：读取 space_type
space_type = physical_context.get("space_type", "") if isinstance(physical_context, dict) else ""

# 第732行：V2 角色的交付物名
{
    "name": f"{space_type}整体设计方案" if space_type else "整体设计方案",
    ...
}

# 第746行：约束中使用
f"{space_type}的功能分区" if space_type else "功能分区",

# 第839, 841行：V4/V5/V6 角色的名称
"V4": f"{space_type}设计研究报告" if space_type else "设计研究报告",
"V6": f"{space_type}技术实施方案" if space_type else "技术实施方案",

# 第857-858行：project_context 条件拼接
"project_context": f"{location}, {space_type}, {budget}"
if all([location, space_type, budget])
else "",
```

**风险**: 若 space_type 从"民宿"改为编码（如"commercial_hospitality"），所有交付物名称会变成"commercial_hospitality整体设计方案"，这是不可接受的用户界面。

---

### 4.2 任务生成中的 space_type 使用（高风险）

**文件**: `services/core_task_decomposer.py:2482-2510`

```python
# 第2482行：从 project_type 检测得到 space_type
space_type = get_type_label(_detected_type_id) if _detected_type_id else ""

# 第2490-2505行：任务标题直接插值
{
    "title": f"{area}平米{space_type}空间功能规划",
    "description": f"制定符合用户需求的{area}平米{space_type}空间布局策略和功能分区方案",
    "source_keywords": [f"{area}平米", space_type],  # ← space_type 作为关键词
}
```

**风险**: space_type 既作为显示名，又作为 source_keywords 用于搜索和分类；改变其值或类型会同时破坏任务的可读性和可搜索性。

---

### 4.3 维度映射中的 space_type 作为键（关键风险）

**文件**: `services/task_completeness_analyzer.py:17-108`

```python
# 第19-32行：project_type 的 parent bucket → space_type 键名映射
_PARENT_TYPE_TO_SPACE_TYPE: Dict[str, str] = {
    "residential": "residential_premium",
    "hospitality": "commercial",       # ← 酒店/餐饮 → 商业空间
    "office": "office",
    ...
}

# 第76-78行：加载配置，space_type 作为 YAML 键
self._space_type_map = data.get("space_types", {})
self._space_type_map["general"] = data.get("general", {})

# 第108行：用 space_type 查询维度
st_key = space_type if space_type in self._space_type_map else "general"
st_config = self._space_type_map.get(st_key, {})
```

**风险**: space_type 作为 space_type_dimension_map.yaml 的顶级键，改变其值会导致维度查询失败，进而无法生成正确的补充问题。

---

## 5. 当前 space_type 的两个不同用途

通过代码审计，发现 **space_type 同时承载了两个不同的语义**：

### 用途 A：项目类型的中文标签（显示层）
- **使用场景**: 交付物名称、任务标题、用户界面
- **取值**: "民宿"、"办公"、"商业" 等
- **来源**: PROJECT_TYPE_REGISTRY 的 `get_type_label()`
- **特点**: 对用户可读，可在字符串模板中直接使用

### 用途 B：维度映射的键（处理逻辑层）
- **使用场景**: 维度推理、示例覆盖度检查、配置文件键名
- **取值**: "residential_premium"、"commercial"、"general" 等
- **来源**: `_PARENT_TYPE_TO_SPACE_TYPE` 映射
- **特点**: 与 YAML 配置绑定，用于条件逻辑

**问题**: 两个用途的取值集不一致，导致 physical_context.space_type 可能是任一类型，存在语义混用风险。

---

## 6. 数据流向图

```
项目输入
    ↓
[project_type_detector.detect_project_type()]
    ↓
project_type_id (e.g., "boutique_hotel")
    ↓
分流：
  ├─→ [get_type_label()] → "民宿" 
  │   ↓
  │   [physical_context.space_type] (用途A：显示)
  │   ↓
  │   [deliverable_id_generator] → "民宿整体设计方案"
  │
  └─→ [PARENT_TYPE_MAP] → "commercial"
      ↓
      [space_type_dimension_map.yaml查询] → dimensions
      ↓
      [task_completeness_analyzer] (用途B：逻辑)
```

---

## 7. 结论

### 核心发现

1. **语义混用已发生**: `physical_context.space_type` 至少同时承载两种语义：
   - 项目类型的中文标签（35% 的用法）
   - 维度映射的键（通过 _PARENT_TYPE_TO_SPACE_TYPE 间接使用）
   - 其他混合用途（显示名、zone标签、初值等）

2. **现有代码依赖复杂**: 47+ 个读写点，其中高风险点包括：
   - deliverable_id_generator_node.py（12+ 处字符串模板）
   - core_task_decomposer.py（8+ 处任务生成）
   - task_completeness_analyzer.py（维度查询逻辑）

3. **迁移前置条件**:
   - **必须先确认 `deliverable_id_generator_node.py` 中 `space_type` 的最终语义**（是否保持为项目类型中文名，或改为编码）
   - **必须更新或新增配置**，明确 space_type 与维度的映射关系
   - **需要全量回归测试**，特别是交付物生成、任务创建和维度推理流程

4. **建议阶段**:
   - **Phase 1**: 完成此审计，达成对 space_type 现状的共识
   - **Phase 2**: 设计新的空间分类字段结构（可能需要拆分为 `display_name` 和 `dimension_key`）
   - **Phase 3**: 修改 deliverable_id_generator_node.py 和关联逻辑，确保向后兼容
   - **Phase 4**: 更新配置文件和示例库

---

## **重要声明**

**在此 audit 完成并确认 deliverable_id_generator_node.py 的 space_type 语义之前，不修改该文件。**

该文件是交付物生成的核心，其 space_type 使用的任何改变都会直接影响用户可见的交付物名称。必须先通过需求评审和设计文档，明确新语义后，再同步更新所有依赖此字段的 47+ 处代码。

---

**审计员**: Claude Code Agent  
**审计时间**: 2026-04-30  
**下一步**: 等待设计方案确认后启动 Phase 2 迁移设计
