# SpaceClassificationResult v1 Schema 冻结文档

**生成日期**: 2026-04-30  
**版本**: space_classification.v1  
**状态**: Frozen - 供 Task 5 代码实现参考

---

## 1. 顶层结构表 (SpaceClassificationResult)

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `schema_version` | `str` | `"space_classification.v1"` | 模式版本标识，写死此值 |
| `primary_bucket` | `Optional[str]` | `None` | **PARENT_TYPE_MAP** 中的父桶 ID（L1），为空表示未分类 |
| `project_type` | `str` | 必填 | **PROJECT_TYPE_REGISTRY** 中的权威 ID（L2），如 `"office_workspace"` |
| `project_type_name` | `Optional[str]` | `None` | 中文显示名称，如 `"办公工作空间"` |
| `confidence` | `float` | 必填 | 检测置信度，范围 `0.0 ~ 1.0` |
| `confidence_level` | `Literal["high","medium","low"]` | 自动派生 | 根据 `confidence` 的范围等级：`high ≥ 0.75`, `medium ≥ 0.5`, `low < 0.5` |
| `specialty_tags` | `List[str]` | `[]` | **SPECIALTY_TAG_MAP** 中匹配的标签列表（L3），如 `["meeting_room", "video_conference"]` |
| `secondary_candidates` | `List[SecondaryCandidate]` | `[]` | 次级候选类型列表，按置信度降序排列 |
| `runtime_modifiers` | `Dict[str, Any]` | `{}` | 运行时修饰符字典，用于动态调整分类结果，如 `{"thermal_zone": "heat_recovery", "light_quality": "high_cri"}` |
| `ambiguity` | `AmbiguityInfo` | 必填 | 歧义信息对象，描述分类的模糊度和需要澄清的方面 |
| `routing` | `RoutingInfo` | 必填 | 路由信息对象，指导下游系统如何处理该分类结果 |
| `evidence` | `List[str]` | `[]` | 支撑分类决策的证据文本片段列表 |
| `spatial_zone_refs` | `List[str]` | `[]` | 关联的空间区域 ID 列表（仅存储引用，不进入分类树）|
| `freeze_state` | `Literal["open","user_confirmed","system_locked"]` | `"open"` | 冻结状态：`open` 可修改，`user_confirmed` 用户确认，`system_locked` 系统锁定 |

---

## 2. SecondaryCandidate 子模型表

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `project_type` | `str` | 必填 | **PROJECT_TYPE_REGISTRY** 中的类型 ID |
| `confidence` | `float` | 必填 | 该候选的置信度，范围 `0.0 ~ 1.0` |
| `role` | `Literal["supporting_function","competing_primary","seasonal_variant","unknown"]` | `"unknown"` | 该候选在分类中的角色 |
| `weight` | `Optional[float]` | `None` | 相对权重（可选），用于多候选融合 |
| `weight_status` | `Literal["known","unknown"]` | `"unknown"` | 权重状态：`known` 已确定，`unknown` 待确定 |

### SecondaryCandidate role 说明

- **supporting_function**: 该类型作为主类型的辅助功能存在，如主类型为 `"office_workspace"`，辅助功能可能是 `"break_room"`
- **competing_primary**: 与主类型竞争的另一可能主类型，置信度接近
- **seasonal_variant**: 主类型的季节性变体或时间相关变体
- **unknown**: 角色未确定

---

## 3. AmbiguityInfo 子模型表

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `level` | `Literal["low","medium","high"]` | 必填 | 歧义等级：`low` 分类确定，`medium` 存在合理替代，`high` 多个等概率类型 |
| `boundary_risk` | `bool` | `False` | 是否存在边界风险（跨类型边界难以判定） |
| `competing_types` | `List[str]` | `[]` | 主要竞争类型的 ID 列表 |
| `needs_clarification` | `bool` | `False` | 是否需要用户澄清 |
| `clarification_questions` | `List[str]` | `[]` | 澄清问题列表，如 `["该空间是否配备固定办公工位?"]` |

---

## 4. RoutingInfo 子模型表

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `questionnaire_profile` | `str` | 必填 | 问卷配置 ID，指示调查问卷应采用的配置版本 |
| `ontology_key` | `str` | 必填 | 本体知识库键，指示在本体系统中的查询/映射键 |
| `deliverable_label` | `Optional[str]` | `None` | 可交付标签，用于报告生成和分类输出标签化 |
| `floorplan_profile` | `Optional[str]` | `None` | 平面图配置 ID，指示如何对该空间进行平面图分析 |
| `visual_profile` | `Optional[str]` | `None` | 视觉配置 ID，指示如何对该空间进行视觉处理（如照片分析/3D 建模参数） |

---

## 5. 与旧字段的映射关系表

### 数据迁移策略

| 旧字段 | 对应新字段 | 迁移策略 |
|--------|----------|--------|
| `state.project_type` | `space_classification.project_type` | **双写策略**：主数据链不动，新字段并行写入，Phase 2 结束后评估迁移窗口 |
| `project_classification.project_type` | `space_classification.project_type` | **新字段优先读取**：output_intent_detection 等下游系统优先读取 `space_classification.project_type`，回退到 `project_classification.project_type` |
| `physical_context.space_type` | `space_classification.routing.deliverable_label` | **延迟迁移**：Phase 3 后迁移，等待审计完成，确保映射规则正确 |

### 映射兼容性说明

- 新系统上线期间，`state.project_type` 和 `space_classification.project_type` 并行存在，通过业务规则保证一致性
- 旧 `project_classification.project_type` 将逐步被 `space_classification` 替代
- `physical_context.space_type` 的迁移需要等待本体系统和 deliverable_label 映射规则的稳定后执行

---

## 6. 四层分类核心架构

### 分类树结构

```
SpaceClassificationResult (根)
├── L1: primary_bucket (PARENT_TYPE_MAP)
│   └── L2: project_type (PROJECT_TYPE_REGISTRY)
│       ├── L3: specialty_tags (SPECIALTY_TAG_MAP) [多个标签组合]
│       │   └── 细粒度特性描述
│       └── L4: runtime_modifiers + spatial_zone_refs
│           ├── runtime_modifiers: Dict[str, Any]
│           │   └── 动态分类修饰（热恢复、光质量等）
│           └── spatial_zone_refs: List[str]
│               └── 关联空间对象引用（**不进入分类树**）
```

### 各层说明

- **L1 (primary_bucket)**: 最粗粒度分类，如 `"building_zone"`, `"functional_area"` 等父类型
- **L2 (project_type)**: 权威分类，如 `"office_workspace"`, `"meeting_room"`, `"mechanical_room"` 等
- **L3 (specialty_tags)**: 细粒度标签组合，在 L2 基础上进一步描述特殊功能，可多个存在
- **L4 (runtime_modifiers + spatial_zone_refs)**:
  - **runtime_modifiers**: 动态运行时修饰符，调整分类后行为（非树状，是属性字典）
  - **spatial_zone_refs**: 关联的空间区域 ID 引用，用于跨空间关联查询（**重要**：仅存 ID，不参与分类判定）

### 设计要点

1. **单一主类型原则**: 每个 `SpaceClassificationResult` 只有一个 `project_type`（L2），但可有多个 `specialty_tags`（L3）
2. **引用隔离**: `spatial_zone_refs` 存储的是 ID 引用，解耦空间分类树与空间关联关系
3. **歧义管理**: `ambiguity` 字段独立记录分类的模糊性，便于后续人工审核和算法优化
4. **路由驱动**: `routing` 字段直接驱动下游系统的行为（问卷、本体、可交付件等）

---

## 7. 代码实现约束

### 必填字段

```python
# 必填字段不能为 None 或空值
- project_type: str
- confidence: float
- ambiguity: AmbiguityInfo
- routing: RoutingInfo
- ambiguity.level: Literal["low","medium","high"]
- routing.questionnaire_profile: str
- routing.ontology_key: str
```

### 自动派生字段

```python
# confidence_level 由 confidence 自动派生
if confidence >= 0.75:
    confidence_level = "high"
elif confidence >= 0.5:
    confidence_level = "medium"
else:
    confidence_level = "low"
```

### 验证规则

1. `confidence` 必须在 `[0.0, 1.0]` 范围内
2. `secondary_candidates` 列表中的置信度应不超过主 `confidence`
3. `ambiguity.competing_types` 中的类型应该在 `PROJECT_TYPE_REGISTRY` 中存在
4. `freeze_state` 变更遵循状态机：`open` → `user_confirmed` → `system_locked`（单向）

---

## 8. 使用示例

### 完整示例

```python
{
    "schema_version": "space_classification.v1",
    "primary_bucket": "functional_area",
    "project_type": "office_workspace",
    "project_type_name": "办公工作空间",
    "confidence": 0.87,
    "confidence_level": "high",
    "specialty_tags": ["meeting_room", "video_conference", "open_office"],
    "secondary_candidates": [
        {
            "project_type": "collaborative_space",
            "confidence": 0.72,
            "role": "competing_primary",
            "weight": 0.15,
            "weight_status": "known"
        }
    ],
    "runtime_modifiers": {
        "thermal_zone": "heat_recovery_enabled",
        "light_quality": "high_cri",
        "acoustic_requirement": "medium"
    },
    "ambiguity": {
        "level": "low",
        "boundary_risk": false,
        "competing_types": ["collaborative_space"],
        "needs_clarification": false,
        "clarification_questions": []
    },
    "routing": {
        "questionnaire_profile": "office_standard_v2",
        "ontology_key": "workspace/office/standard",
        "deliverable_label": "workspace_office",
        "floorplan_profile": "office_furniture_analysis_v1",
        "visual_profile": "interior_design_assessment_v2"
    },
    "evidence": [
        "检测到办公桌椅布局",
        "空间中存在会议室标识",
        "视频会议设备安装检出"
    ],
    "spatial_zone_refs": ["zone_a_floor_3", "zone_b_floor_3"],
    "freeze_state": "open"
}
```

---

## 9. 版本历史

| 版本 | 日期 | 描述 |
|------|------|------|
| v1 | 2026-04-30 | 初版冻结，包含完整四层分类、歧义管理、路由驱动 |

---

## 10. 相关文档与资源

- **PROJECT_TYPE_REGISTRY**: 权威项目类型注册表（L2 维度）
- **PARENT_TYPE_MAP**: 父类型映射表（L1 维度）
- **SPECIALTY_TAG_MAP**: 特性标签映射表（L3 维度）
- **TYPE_NAMING_MAP**: 类型中文名称映射表
- **旧系统字段** (待迁移):
  - `state.project_type`
  - `project_classification.project_type`
  - `physical_context.space_type`

---

**文档维护者**: Space Classification Team  
**下一步**: Task 5 - 代码实现（基于本 schema）
