# 空间分类系统设计文档

> 日期：2026-04-30  
> 方案：纯旁路追加（方案 A）  
> 数据结构：Pydantic BaseModel  
> LLM 接入：复用 `llm_factory.create_structured_llm()`

---

## 1. 背景与目标

空间分类是方案高参的分析路由基础设施，不是空间名称表。当前代码存在三个核心问题：

1. `project_classification` 字段语义漂移（v9.1 标记移除，v10.1 临时重建兼容）
2. `physical_context.space_type` 语义混用（可能是项目类型、空间部位、显示名或混合词）
3. 没有统一的分类结果对象，下游各节点各自读取不同字段

目标：**先消除字段和命名混乱，再逐步增强智能裁决**，让分类结果驱动问卷、本体、交付命名、平面沙盘和方案画布。

---

## 2. 核心约束

- 不重写现有 `ProjectTypeDetector` 主链
- 不直接替换 `project_type` 字段
- 不复活 `project_classification` 作为新权威入口
- 不一次新增 60-80 个正式类型（active 类型控制在 30-50）
- 不让 LLM 做主分类器（只做高歧义兜底）
- 不在未清查 `physical_context.space_type` 前改交付命名逻辑
- 不把 `spatial_zones` 纳入分类层级（它是关联对象）

---

## 3. 总体架构

```
┌─────────────────────────────────────────────────────────┐
│                     主链（不动）                          │
│  ProjectTypeDetector → project_type (str) → state       │
└─────────────────────────────────────────────────────────┘
              │ 包装（不替换）
              ▼
┌─────────────────────────────────────────────────────────┐
│         SpaceClassificationService（旁路）               │
│  输入：ProjectTypeDetector.detect_with_details()         │
│  输出：SpaceClassificationResult (Pydantic)              │
└─────────────────────────────────────────────────────────┘
              │ 写入
              ▼
┌─────────────────────────────────────────────────────────┐
│  state.space_classification (Optional[Dict])             │
│  state.project_type 继续写（双写，不替换）                │
└─────────────────────────────────────────────────────────┘
              │ 渐进消费
              ▼
┌──────────────┬──────────────┬──────────────┬────────────┐
│ output_intent│ deliverable  │ questionnaire│ floor_plan │
│ _detection   │ _id_generator│ _profile     │ _sandbox   │
│ (Phase 2)    │ (Phase 3)    │ (Phase 3)    │ (Phase 3)  │
└──────────────┴──────────────┴──────────────┴────────────┘
              │ 治理
              ▼
┌─────────────────────────────────────────────────────────┐
│  Phase 4：boundary_resolver + error_cases + 指标         │
└─────────────────────────────────────────────────────────┘
```

### 四层分类核心

```
L1 primary_bucket      — PARENT_TYPE_MAP 父桶（10 个）
L2 project_type        — 权威类型 ID（active 30-50 个）
L3 specialty_tags      — SPECIALTY_TAG_MAP 细粒度标签
L4 runtime_modifiers   — 运行时修饰项（规模、风格、客群等）

+ spatial_zone_refs    — 关联对象引用，不进入分类树
```

### 新增文件布局

```
intelligent_project_analyzer/
├── models/
│   └── space_classification.py               # Pydantic 模型
├── services/
│   └── space_classification_service.py       # 旁路分类服务
└── config/
    └── space_classification/
        ├── boundary_cases.yaml               # 边界风险规则
        └── classification_error_cases.yaml   # Phase 4 治理

sf/2026.4.18/1.1 空间分类/
├── TYPE_NAMING_MAP.md
├── space_classification_schema.md
├── space_type_field_audit.md
└── active_project_type_registry_v1.md
```

---

## 4. Phase 0：事实对齐文档

### T1 — TYPE_NAMING_MAP.md

扫描 `project_type_detector.py` 中 `PROJECT_TYPE_REGISTRY`（32 个类型）及 `LEGACY_TYPE_ALIASES`（13 条），对每个类型标注：

| 字段 | 说明 |
|------|------|
| `id` | 代码权威 ID |
| `name` | 中文显示名 |
| `primary_bucket` | PARENT_TYPE_MAP 父桶 |
| `status` | active / alias_only / candidate / deprecated |
| `alias_of` | 如果是别名，指向目标 ID |
| `boundary_neighbors` | 易混淆的邻近类型 |
| `ontology_key` | ontology.yaml 对应键 |

### T2 — space_classification_schema.md

冻结 `SpaceClassificationResult v1` 字段定义（见第 5 节），包含：
- 每个字段的类型、默认值、语义说明
- 四层分类核心与 `spatial_zone_refs` 的关系说明
- 与旧字段（`project_type`、`project_classification`）的映射关系

### T3 — space_type_field_audit.md

采样 `physical_context.space_type` 的真实取值，标注每条记录属于：

```
project_type_like      — 如"民宿"、"办公室"
spatial_zone_like      — 如"客房"、"大堂"
display_label_like     — 如"整体方案"含标点
style_or_concept_like  — 如"北欧风"
mixed_or_unknown       — 无法归类
```

**结论：在此文档完成前，不改 `deliverable_id_generator_node.py`。**

### T4 — active_project_type_registry_v1.md

以现有 `PROJECT_TYPE_REGISTRY`（32 个）为基础，标注 status，确认首批 active 类型不超过 50 个，超出部分降级为 candidate 或 specialty_tag。

---

## 5. Phase 1：核心模型与旁路服务

### 5.1 Pydantic 模型

**文件**：`intelligent_project_analyzer/models/space_classification.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal

class AmbiguityInfo(BaseModel):
    level: Literal["low", "medium", "high"]
    boundary_risk: bool = False
    competing_types: List[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_questions: List[str] = Field(default_factory=list)

class SecondaryCandidate(BaseModel):
    project_type: str
    confidence: float
    role: Literal["supporting_function", "competing_primary",
                  "seasonal_variant", "unknown"] = "unknown"
    weight: Optional[float] = None
    weight_status: Literal["known", "unknown"] = "unknown"

class RoutingInfo(BaseModel):
    questionnaire_profile: str
    ontology_key: str
    deliverable_label: Optional[str] = None
    floorplan_profile: Optional[str] = None
    visual_profile: Optional[str] = None

class SpaceClassificationResult(BaseModel):
    schema_version: str = "space_classification.v1"
    primary_bucket: Optional[str] = None
    project_type: str
    project_type_name: Optional[str] = None
    confidence: float
    confidence_level: Literal["high", "medium", "low"]
    specialty_tags: List[str] = Field(default_factory=list)
    secondary_candidates: List[SecondaryCandidate] = Field(default_factory=list)
    runtime_modifiers: Dict[str, Any] = Field(default_factory=dict)
    ambiguity: AmbiguityInfo
    routing: RoutingInfo
    evidence: List[str] = Field(default_factory=list)
    spatial_zone_refs: List[str] = Field(default_factory=list)
    freeze_state: Literal["open", "user_confirmed", "system_locked"] = "open"
```

### 5.2 SpaceClassificationService

**文件**：`intelligent_project_analyzer/services/space_classification_service.py`

核心方法：

```python
class SpaceClassificationService:
    def classify(self, context: dict) -> SpaceClassificationResult
    def _build_result(self, raw, context) -> SpaceClassificationResult
    def _apply_boundary_rules(self, result, context) -> SpaceClassificationResult
    def _extract_modifiers(self, raw, context) -> dict
    def _assess_ambiguity(self, raw) -> AmbiguityInfo
    def _build_routing(self, raw) -> RoutingInfo
```

关键实现细节：
- `secondary_candidates` 直接取 `raw.all_matches[1:]`，**不反解析 reason 字符串**
- `confidence_level`：≥0.75 → high，≥0.5 → medium，其余 → low
- `primary_bucket` 从 `PARENT_TYPE_MAP` 查找，查不到则为 None

### 5.3 边界规则配置

**文件**：`intelligent_project_analyzer/config/space_classification/boundary_cases.yaml`

首批 8 个高风险边界对：

```yaml
boundary_cases:
  - id: hospitality_vs_residential
    types: [commercial_hospitality, personal_residential]
    trigger_keywords: [民宿, 度假屋, 乡村住宅, 农家乐]
    risk_level: high
    clarification: "请确认：这是对外经营的民宿，还是自住的乡村住宅？"

  - id: brand_experience_vs_retail
    types: [brand_experience, commercial_retail]
    trigger_keywords: [展厅, 旗舰店, 体验中心, 品牌空间]
    risk_level: high
    clarification: "请确认：这个空间的核心功能是品牌体验/展示，还是日常零售销售？"

  - id: hospitality_vs_healthcare
    types: [commercial_hospitality, healthcare_wellness]
    trigger_keywords: [康养, 疗愈, 养生, 健康度假]
    risk_level: medium
    clarification: "请确认：这是以住宿为主的康养度假，还是以医疗/康复为主的健康设施？"

  - id: hospitality_vs_rural
    types: [commercial_hospitality, rural_construction]
    trigger_keywords: [乡建, 村落, 农村, 古村落改造]
    risk_level: medium
    clarification: "请确认：这是乡村民宿/酒店，还是乡村整体建设/改造项目？"

  - id: community_vs_cultural
    types: [community_public, public_cultural]
    trigger_keywords: [社区中心, 文化馆, 活动中心, 展览空间]
    risk_level: medium
    clarification: "请确认：这是以社区服务为主，还是以文化展览/演出为主？"

  - id: office_vs_brand_experience
    types: [commercial_office, brand_experience]
    trigger_keywords: [创意园区, 品牌总部, 企业展厅, showroom]
    risk_level: medium
    clarification: "请确认：这是以日常办公为主，还是以品牌展示/体验为主？"

  - id: residential_renovation_vs_personal
    types: [residential_renovation, personal_residential]
    trigger_keywords: [旧房改造, 老宅翻新, 二手房装修]
    risk_level: low
    clarification: "请确认：这是存量住宅的改造翻新，还是新建/全新装修的住宅？"

  - id: popup_vs_brand_retail
    types: [popup_temporary, brand_experience, commercial_retail]
    trigger_keywords: [快闪店, 临时展, popup, 快闪]
    risk_level: high
    clarification: "请确认：这是临时性快闪活动空间，还是有固定经营周期的品牌/零售空间？"
```

---

## 6. Phase 2：状态双写

### state.py 变更

在 `ProjectAnalysisState` 中新增一个字段（不修改其他任何字段）：

```python
space_classification: Optional[Dict[str, Any]] = None
```

### output_intent_detection.py 变更

定位 v10.1 兼容代码（约第 1177 行），改为三级回退读取：

```python
# 优先读 space_classification，无则回退 project_type
sc = state.get("space_classification")
_project_type_str = (
    (sc.get("project_type") if sc else None)
    or state.get("project_type", "")
    or structured_requirements.get("project_type", "")
)
project_classification = {"project_type": _project_type_str} if _project_type_str else None
```

`project_classification` 继续作为兼容桥接，不升级为新权威入口。

### requirements 主链写入点

在现有写入 `project_type` 的节点中，**追加**写入 `space_classification`（不替换）：

```python
state["project_type"] = result.project_type          # 保持不变
state["space_classification"] = result.model_dump()  # 新增
```

---

## 7. Phase 3：下游消费

按影响范围从小到大执行：

### 7.1 output_intent_detection.py — 交付标签优先

```python
deliverable_label = (
    sc.get("routing", {}).get("deliverable_label")
    or physical_context.get("space_type")
    or project_type_name
)
```

### 7.2 类型知识包（首批 7 个）

**目录**：`intelligent_project_analyzer/config/type_knowledge/`

首批覆盖：
1. `commercial_hospitality.yaml`
2. `healthcare_wellness.yaml`
3. `brand_experience.yaml`
4. `rural_construction.yaml`
5. `residential_renovation.yaml`
6. `commercial_office.yaml`
7. `commercial_retail.yaml`

每个知识包结构：

```yaml
project_type: commercial_hospitality
display_name: 酒店民宿餐饮
core_logic: "..."
typical_tensions: [...]
required_variables: [...]
questionnaire_profile: hospitality_v1
floorplan_profile: hospitality_v1
visual_profile:
  visual_pitfalls: [...]
  forbidden_biases: [...]
  type_constraints: [...]
deliverable_profile:
  preferred_label: "..."
  naming_pattern: "..."
```

### 7.3 task_completeness_analyzer — 问卷 profile

读取 `routing.questionnaire_profile`，匹配对应问卷模板，保留旧 fallback。

### 7.4 deliverable_id_generator_node.py

**等待 `space_type_field_audit.md` 完成后再改。** 在此之前不触碰该文件。

### 7.5 平面沙盘消费

只读取以下字段，禁止把空间部位反写为项目类型：

```python
project_type          # from space_classification
runtime_modifiers     # from space_classification
extracted_spatial_zones  # 独立字段，不进入分类树
```

---

## 8. Phase 4：治理闭环

### 8.1 分类错误案例库

**文件**：`intelligent_project_analyzer/config/space_classification/classification_error_cases.yaml`

```yaml
error_cases:
  - id: ec_001
    input_sample: "..."
    wrong_classification: residential
    correct_classification: commercial_hospitality
    root_cause: "缺少关键词'对外经营'"
    rule_fix: "增加 hospitality 关键词权重"
    status: open
```

### 8.2 类型状态机

在 `PROJECT_TYPE_REGISTRY` 每个条目追加 `status` 字段：

```python
"status": "active"  # active | candidate | alias_only | deprecated | merged
```

新类型进入流程：
```
提议 → candidate → 评审通过 → active
                  → 评审拒绝 → alias_only 或 specialty_tag
```

### 8.3 LLM 兜底裁决

触发条件：`ambiguity.level == "high"`

实现：

```python
def _llm_boundary_resolve(self, context: dict, candidates: list) -> SpaceClassificationResult:
    structured_llm = llm_factory.create_structured_llm(
        schema=SpaceClassificationResult
    )
    # 输出强制通过 Pydantic schema 校验
    # 失败时降级为追问（不硬选）
```

### 8.4 可观测指标

在现有日志层追加 `space_classification_metrics`：

```python
{
    "primary_type_accuracy": float,      # 主类型准确率（用户未修正）
    "user_correction_rate": float,       # 用户修正率
    "boundary_trigger_rate": float,      # 边界触发率
    "ontology_fallback_rate": float,     # ontology fallback 率
    "deliverable_label_fallback_rate": float,  # 交付命名回退率
    "llm_boundary_resolve_rate": float,  # LLM 兜底触发率
}
```

---

## 9. 验收标准

### Phase 0
- 能解释每个现有 `project_type` 的父桶、ontology fallback、问卷 profile
- 能明确哪些类型只是 alias 或 tag
- 能明确 `space_type` 迁移风险等级

### Phase 1
- 20-50 条典型输入可输出稳定 schema
- 类型枚举合法率 100%
- 低置信度不硬选而不标记
- 8 个边界案例能输出 `needs_clarification` 或 `boundary_risk`

### Phase 2
- 新旧字段对齐率可检查
- 无新字段时旧流程仍可运行
- 可通过配置回退到旧读取路径

### Phase 3
- 同一项目在底盘、问卷、交付命名中分类一致
- 民宿不被生成住宅客厅逻辑
- 医疗康养不只输出疗愈氛围
- 旧 `space_type` 不再主导整体项目命名

### Phase 4
- 新类型不能绕过评审直接进入 active
- 错判案例能回流规则
- LLM 裁决失败时可降级为追问
- 分类系统能解释"为什么这么判"

---

## 10. 明确不做

1. 不以 `_type_registry.py` 为实施入口（文件不存在）
2. 不直接替换 `project_type`
3. 不复活旧 `project_classification` 作为新权威
4. 不一次性新增 60-80 个正式项目类型
5. 不让 LLM 生成不存在的类型名
6. 不自动编造混合权重
7. 不在未清查 `space_type` 前改交付命名主逻辑
8. 不把 `spatial_zones` 升级为分类协议的一部分
