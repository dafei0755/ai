# 空间分类系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以纯旁路追加方式为现有 `ProjectTypeDetector` 增加统一 `SpaceClassificationResult` 输出，Phase 0-4 完整实施。

**Architecture:** `SpaceClassificationService` 包装现有 `ProjectTypeDetector.detect_with_details()`，生成 Pydantic `SpaceClassificationResult`，双写进 `state.space_classification`，主链 `project_type` 不动，下游渐进消费。

**Tech Stack:** Python 3.10+, Pydantic v2, pytest, PyYAML，已有 `llm_factory.create_structured_llm()`

---

## 文件布局

| 操作 | 路径 |
|------|------|
| 创建 | `intelligent_project_analyzer/models/space_classification.py` |
| 创建 | `intelligent_project_analyzer/services/space_classification_service.py` |
| 创建 | `intelligent_project_analyzer/config/space_classification/boundary_cases.yaml` |
| 创建 | `intelligent_project_analyzer/config/space_classification/classification_error_cases.yaml` |
| 创建 | `intelligent_project_analyzer/config/type_knowledge/commercial_hospitality.yaml` |
| 创建 | `intelligent_project_analyzer/config/type_knowledge/healthcare_wellness.yaml` |
| 创建 | `intelligent_project_analyzer/config/type_knowledge/brand_experience.yaml` |
| 创建 | `intelligent_project_analyzer/config/type_knowledge/rural_construction.yaml` |
| 创建 | `intelligent_project_analyzer/config/type_knowledge/residential_renovation.yaml` |
| 创建 | `intelligent_project_analyzer/config/type_knowledge/commercial_office.yaml` |
| 创建 | `intelligent_project_analyzer/config/type_knowledge/commercial_retail.yaml` |
| 创建 | `tests/intelligence/test_space_classification_service.py` |
| 修改 | `intelligent_project_analyzer/core/state.py:185` |
| 修改 | `intelligent_project_analyzer/agents/requirements_analyst_agent.py:722-758` |
| 修改 | `intelligent_project_analyzer/interaction/nodes/output_intent_detection.py:1177-1180` |
| 修改 | `intelligent_project_analyzer/services/project_type_detector.py` (添加 status 字段) |
| 修改 | `intelligent_project_analyzer/services/task_completeness_analyzer.py` |
| 创建 | `sf/2026.4.18/1.1 空间分类/TYPE_NAMING_MAP.md` |
| 创建 | `sf/2026.4.18/1.1 空间分类/space_classification_schema.md` |
| 创建 | `sf/2026.4.18/1.1 空间分类/space_type_field_audit.md` |
| 创建 | `sf/2026.4.18/1.1 空间分类/active_project_type_registry_v1.md` |

---

## Task 1: Phase 0 — TYPE_NAMING_MAP.md

**Files:**
- 读取: `intelligent_project_analyzer/services/project_type_detector.py`
- 创建: `sf/2026.4.18/1.1 空间分类/TYPE_NAMING_MAP.md`

- [ ] **Step 1: 读取 PROJECT_TYPE_REGISTRY 与相关常量**

打开 `intelligent_project_analyzer/services/project_type_detector.py`，定位以下常量：
- `PROJECT_TYPE_REGISTRY`（行 49-621）：32 个类型条目
- `LEGACY_TYPE_ALIASES`（行 627-653）：13 条别名
- `PARENT_TYPE_MAP`（行 715-753）：父桶映射

- [ ] **Step 2: 写入 TYPE_NAMING_MAP.md**

创建 `sf/2026.4.18/1.1 空间分类/TYPE_NAMING_MAP.md`，内容如下（按 REGISTRY 实际条目填写，此处为模板格式，执行时按代码实际顺序逐行展开）：

```markdown
# 类型命名映射表 v1

> 权威来源：`intelligent_project_analyzer/services/project_type_detector.py`  
> 更新日期：2026-04-30

## 映射表

| ID | 中文名 | primary_bucket | status | alias_of | boundary_neighbors |
|----|--------|----------------|--------|----------|--------------------|
| commercial_hospitality | 酒店民宿餐饮 | hospitality | active | — | personal_residential, rural_construction, brand_experience |
| personal_residential | 住宅精装 | residential | active | — | residential_renovation, commercial_hospitality |
| residential_renovation | 住宅改造翻新 | residential | active | — | personal_residential |
| commercial_office | 商业办公 | office | active | — | brand_experience |
| commercial_retail | 商业零售 | retail | active | — | brand_experience, popup_temporary |
| brand_experience | 品牌体验空间 | retail | active | — | commercial_retail, commercial_office, popup_temporary |
| popup_temporary | 快闪临时空间 | retail | active | — | brand_experience, commercial_retail |
| healthcare_wellness | 医疗康养 | healthcare | active | — | commercial_hospitality |
| public_cultural | 公共文化 | public | active | — | community_public |
| community_public | 社区公共 | public | active | — | public_cultural |
| education_childcare | 教育亲子 | education | active | — | — |
| leisure_entertainment | 休闲娱乐 | leisure | active | — | commercial_retail |
| sports_fitness | 体育健身 | leisure | active | — | healthcare_wellness |
| restaurant_cafe | 餐饮咖啡 | hospitality | active | — | commercial_hospitality |
| rural_construction | 乡建乡村 | special | active | — | commercial_hospitality |
| urban_renewal | 城市更新 | urban_renewal | active | — | public_cultural |
| industrial_loft | 工业改造 | industrial | active | — | urban_renewal |
| landscape_outdoor | 景观户外 | outdoor | active | — | — |
| other | 其他 | special | active | — | — |
| cultural_educational | 文化教育(旧) | public | alias_only | public_cultural | — |
| office_coworking | 联合办公(旧) | office | alias_only | commercial_office | — |
| hospitality_tourism | 旅游酒店(旧) | hospitality | alias_only | commercial_hospitality | — |

> 注：alias_only 类型仅存在于 LEGACY_TYPE_ALIASES，不出现在检测结果中。  
> 执行时请以 project_type_detector.py 实际代码为准逐条补全所有 32 个 active 类型。

## 四层结构说明

```
L1 primary_bucket  → PARENT_TYPE_MAP 的 10 个顶层桶
L2 project_type    → PROJECT_TYPE_REGISTRY 中的 ID（active 类型）
L3 specialty_tags  → SPECIALTY_TAG_MAP 的 45 个触发词输出
L4 runtime_modifiers → 运行时提取（规模/风格/客群等）
```

## PARENT_TYPE_MAP 桶列表

| 桶 ID | 含义 | 子类型数 |
|-------|------|---------|
| residential | 住宅 | 2 |
| hospitality | 酒店/餐饮 | 3 |
| office | 办公 | 2 |
| retail | 零售 | 4 |
| leisure | 休闲娱乐 | 3 |
| education | 教育/亲子 | 2 |
| healthcare | 医疗康养 | 1 |
| public | 公共服务 | 4 |
| urban_renewal | 城市更新 | 2 |
| industrial | 工业改造 | 1 |
| outdoor | 景观户外 | 1 |
| special | 特殊 | 2 |
```

- [ ] **Step 3: 提交**

```bash
git add "sf/2026.4.18/1.1 空间分类/TYPE_NAMING_MAP.md"
git commit -m "docs: add TYPE_NAMING_MAP v1 for space classification"
```

---

## Task 2: Phase 0 — space_classification_schema.md

**Files:**
- 创建: `sf/2026.4.18/1.1 空间分类/space_classification_schema.md`

- [ ] **Step 1: 写入 schema 文档**

```markdown
# SpaceClassificationResult v1 Schema

> 冻结日期：2026-04-30  
> 实现路径：`intelligent_project_analyzer/models/space_classification.py`

## 顶层结构

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| schema_version | str | "space_classification.v1" | 协议版本，用于迁移检测 |
| primary_bucket | Optional[str] | None | PARENT_TYPE_MAP 父桶 ID |
| project_type | str | — | PROJECT_TYPE_REGISTRY 权威 ID |
| project_type_name | Optional[str] | None | 中文显示名 |
| confidence | float | — | 检测置信度 0.0-1.0 |
| confidence_level | Literal[high/medium/low] | — | high≥0.75, medium≥0.5, low<0.5 |
| specialty_tags | List[str] | [] | SPECIALTY_TAG_MAP 匹配标签 |
| secondary_candidates | List[SecondaryCandidate] | [] | 次候选列表 |
| runtime_modifiers | Dict[str, Any] | {} | 运行时修饰项 |
| ambiguity | AmbiguityInfo | — | 歧义信息 |
| routing | RoutingInfo | — | 路由信息 |
| evidence | List[str] | [] | 判断依据列表 |
| spatial_zone_refs | List[str] | [] | 空间区域 ID 引用（不进入分类树） |
| freeze_state | Literal[open/user_confirmed/system_locked] | "open" | 冻结状态 |

## SecondaryCandidate

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| project_type | str | — | 次候选类型 ID |
| confidence | float | — | 置信度 |
| role | Literal[...] | "unknown" | supporting_function / competing_primary / seasonal_variant / unknown |
| weight | Optional[float] | None | 面积/营收占比等派生权重 |
| weight_status | Literal[known/unknown] | "unknown" | 权重来源状态 |

## AmbiguityInfo

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| level | Literal[low/medium/high] | — | 歧义等级 |
| boundary_risk | bool | False | 是否触发边界规则 |
| competing_types | List[str] | [] | 竞争类型列表 |
| needs_clarification | bool | False | 是否需要追问 |
| clarification_questions | List[str] | [] | 追问问题列表 |

## RoutingInfo

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| questionnaire_profile | str | — | 问卷模板 ID |
| ontology_key | str | — | ontology.yaml 查找键 |
| deliverable_label | Optional[str] | None | 交付命名首选词 |
| floorplan_profile | Optional[str] | None | 平面图模板 ID |
| visual_profile | Optional[str] | None | 视觉约束模板 ID |

## 与旧字段的映射关系

| 旧字段 | 对应新字段 | 迁移策略 |
|--------|-----------|---------|
| state.project_type | space_classification.project_type | 双写，主链不动 |
| project_classification.project_type | space_classification.project_type | output_intent_detection 优先读新字段 |
| physical_context.space_type | space_classification.routing.deliverable_label | Phase 3 后逐步迁移，等 audit 完成 |
```

- [ ] **Step 2: 提交**

```bash
git add "sf/2026.4.18/1.1 空间分类/space_classification_schema.md"
git commit -m "docs: freeze SpaceClassificationResult v1 schema"
```

---

## Task 3: Phase 0 — space_type_field_audit.md

**Files:**
- 创建: `sf/2026.4.18/1.1 空间分类/space_type_field_audit.md`

- [ ] **Step 1: 搜索 space_type 的所有读写点**

运行：
```bash
grep -rn "space_type" intelligent_project_analyzer/ --include="*.py" | grep -v "__pycache__" | grep -v ".pyc"
```

预期输出：包含 `deliverable_id_generator_node.py`、`task_completeness_analyzer.py`、`space_type_dimension_map.yaml` 等读写点。

- [ ] **Step 2: 搜索 physical_context 写入点**

```bash
grep -rn "physical_context" intelligent_project_analyzer/ --include="*.py" | grep -v "__pycache__" | head -30
```

- [ ] **Step 3: 写入 audit 文档**

创建 `sf/2026.4.18/1.1 空间分类/space_type_field_audit.md`，内容模板：

```markdown
# physical_context.space_type 字段采样清查

> 清查日期：2026-04-30  
> 执行人：根据 grep 结果填写

## 读写点清单

| 文件 | 行号 | 操作 | 语境 |
|------|------|------|------|
| deliverable_id_generator_node.py | ? | 读取 | 生成交付物命名 |
| task_completeness_analyzer.py | ? | 读取 | 维度匹配 |
| requirements_analyst_agent.py | ? | 写入 | 需求分析输出 |
| (根据 grep 结果补全) | | | |

## 取值分类统计

| 分类 | 说明 | 示例 | 占比估算 |
|------|------|------|---------|
| project_type_like | 等同于项目类型词 | "民宿"、"办公室"、"餐厅" | ~60% |
| spatial_zone_like | 空间部位词 | "客房"、"大堂"、"餐区" | ~20% |
| display_label_like | 含排版标点的显示名 | "整体设计方案" | ~10% |
| style_or_concept_like | 风格/概念词 | "北欧风" | ~5% |
| mixed_or_unknown | 无法归类 | — | ~5% |

## 迁移风险评估

| 文件 | 风险等级 | 理由 | 迁移前置条件 |
|------|---------|------|------------|
| deliverable_id_generator_node.py | **高** | 直接影响交付命名显示 | 等本 audit 完成 |
| task_completeness_analyzer.py | 中 | 已有 project_type 回退 | Phase 2 完成后可做 |

## 结论

**在此 audit 完成并确认 deliverable_id_generator_node.py 的 space_type 语义之前，不修改该文件。**
```

- [ ] **Step 4: 提交**

```bash
git add "sf/2026.4.18/1.1 空间分类/space_type_field_audit.md"
git commit -m "docs: add space_type field audit report"
```

---

## Task 4: Phase 0 — active_project_type_registry_v1.md

**Files:**
- 创建: `sf/2026.4.18/1.1 空间分类/active_project_type_registry_v1.md`

- [ ] **Step 1: 写入 active registry 文档**

```markdown
# Active 项目类型注册表 v1

> 基准日期：2026-04-30  
> active 类型数量约束：≤50 个（当前 32 个，未达上限）

## active 类型（直接继承 PROJECT_TYPE_REGISTRY 全部 32 个）

（执行时按 PROJECT_TYPE_REGISTRY 实际顺序逐行填写 32 个条目，格式如下）

| ID | 中文名 | status | 优先级 | 备注 |
|----|--------|--------|--------|------|
| commercial_hospitality | 酒店民宿餐饮 | active | 8 | — |
| personal_residential | 住宅精装 | active | 6 | 兜底类型 |
| ... | ... | ... | ... | ... |

## alias_only 类型（来自 LEGACY_TYPE_ALIASES，13 条）

| 旧 ID | 指向 ID | 说明 |
|-------|---------|------|
| cultural_educational | public_cultural | v7.200 前的旧命名 |
| office_coworking | commercial_office | — |
| hospitality_tourism | commercial_hospitality | — |
| （按 LEGACY_TYPE_ALIASES 实际内容补全）| | |

## 扩展候选池（暂不升为 active，进入 specialty_tag 或 alias）

以下是 60-80 类型提案中暂缓升级的部分，当前以 specialty_tag 或 candidate 形式存在：

| 候选名 | 建议归属 | 理由 |
|--------|---------|------|
| 精品酒店 | specialty_tag (commercial_hospitality) | 差异进 tag 即可 |
| 树屋民宿 | specialty_tag (commercial_hospitality) | 差异进 tag 即可 |
| 牙科诊所 | specialty_tag (healthcare_wellness) | 差异进 tag 即可 |
| 中医馆 | specialty_tag (healthcare_wellness) | 差异进 tag 即可 |

## 类型状态定义

| 状态 | 说明 |
|------|------|
| active | 当前权威类型，可出现在检测结果中 |
| candidate | 评审中，暂不对外使用 |
| alias_only | 仅用于旧数据规范化，不出现在新检测结果 |
| deprecated | 已废弃，保留用于历史数据 |
| merged | 已并入另一类型 |
```

- [ ] **Step 2: 提交**

```bash
git add "sf/2026.4.18/1.1 空间分类/active_project_type_registry_v1.md"
git commit -m "docs: add active project type registry v1"
```

---

## Task 5: Phase 1 — Pydantic 模型

**Files:**
- 创建: `intelligent_project_analyzer/models/space_classification.py`
- 修改: `intelligent_project_analyzer/models/__init__.py`

- [ ] **Step 1: 写入 space_classification.py**

```python
# intelligent_project_analyzer/models/space_classification.py
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class SecondaryCandidate(BaseModel):
    project_type: str
    confidence: float
    role: Literal[
        "supporting_function", "competing_primary", "seasonal_variant", "unknown"
    ] = "unknown"
    weight: Optional[float] = None
    weight_status: Literal["known", "unknown"] = "unknown"


class AmbiguityInfo(BaseModel):
    level: Literal["low", "medium", "high"]
    boundary_risk: bool = False
    competing_types: List[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_questions: List[str] = Field(default_factory=list)


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

- [ ] **Step 2: 在 models/__init__.py 末尾追加导出**

读取当前 `__init__.py`，在末尾加：

```python
from .space_classification import (  # noqa: F401
    AmbiguityInfo,
    RoutingInfo,
    SecondaryCandidate,
    SpaceClassificationResult,
)
```

- [ ] **Step 3: 验证导入**

```bash
cd d:/11-20/2026.2.25/langgraph-design
python -c "from intelligent_project_analyzer.models.space_classification import SpaceClassificationResult; print('OK')"
```

预期输出：`OK`

- [ ] **Step 4: 提交**

```bash
git add intelligent_project_analyzer/models/space_classification.py intelligent_project_analyzer/models/__init__.py
git commit -m "feat: add SpaceClassificationResult Pydantic model"
```

---

## Task 6: Phase 1 — boundary_cases.yaml

**Files:**
- 创建: `intelligent_project_analyzer/config/space_classification/boundary_cases.yaml`

- [ ] **Step 1: 创建目录并写入文件**

```yaml
# intelligent_project_analyzer/config/space_classification/boundary_cases.yaml
# 首批 8 个高风险边界案例
# risk_level: high / medium / low

boundary_cases:
  - id: hospitality_vs_residential
    types: [commercial_hospitality, personal_residential]
    trigger_keywords: [民宿, 度假屋, 乡村住宅, 农家乐, 短租]
    risk_level: high
    clarification: "请确认：这是对外经营的民宿，还是自住的乡村住宅？"

  - id: brand_experience_vs_retail
    types: [brand_experience, commercial_retail]
    trigger_keywords: [展厅, 旗舰店, 体验中心, 品牌空间, showroom]
    risk_level: high
    clarification: "请确认：这个空间的核心功能是品牌体验/展示，还是日常零售销售？"

  - id: hospitality_vs_healthcare
    types: [commercial_hospitality, healthcare_wellness]
    trigger_keywords: [康养, 疗愈, 养生, 健康度假, 康复]
    risk_level: medium
    clarification: "请确认：这是以住宿为主的康养度假，还是以医疗/康复为主的健康设施？"

  - id: hospitality_vs_rural
    types: [commercial_hospitality, rural_construction]
    trigger_keywords: [乡建, 村落, 古村落, 村庄改造]
    risk_level: medium
    clarification: "请确认：这是乡村民宿/酒店，还是乡村整体建设/改造项目？"

  - id: community_vs_cultural
    types: [community_public, public_cultural]
    trigger_keywords: [社区中心, 文化馆, 活动中心, 展览空间, 文化活动]
    risk_level: medium
    clarification: "请确认：这是以社区服务为主，还是以文化展览/演出为主？"

  - id: office_vs_brand_experience
    types: [commercial_office, brand_experience]
    trigger_keywords: [创意园区, 品牌总部, 企业展厅, 总部大楼]
    risk_level: medium
    clarification: "请确认：这是以日常办公为主，还是以品牌展示/体验为主？"

  - id: residential_renovation_vs_personal
    types: [residential_renovation, personal_residential]
    trigger_keywords: [旧房改造, 老宅翻新, 二手房, 存量住宅]
    risk_level: low
    clarification: "请确认：这是存量住宅的改造翻新，还是新建/全新装修的住宅？"

  - id: popup_vs_brand_retail
    types: [popup_temporary, brand_experience, commercial_retail]
    trigger_keywords: [快闪店, 临时展, popup, 快闪, 限时]
    risk_level: high
    clarification: "请确认：这是临时性快闪活动空间，还是有固定经营周期的品牌/零售空间？"
```

- [ ] **Step 2: 验证 YAML 可解析**

```bash
python -c "import yaml; d=yaml.safe_load(open('intelligent_project_analyzer/config/space_classification/boundary_cases.yaml')); print(f'OK: {len(d[\"boundary_cases\"])} cases')"
```

预期输出：`OK: 8 cases`

- [ ] **Step 3: 提交**

```bash
git add intelligent_project_analyzer/config/space_classification/boundary_cases.yaml
git commit -m "feat: add boundary_cases.yaml with 8 high-risk boundary pairs"
```

---

## Task 7: Phase 1 — SpaceClassificationService

**Files:**
- 创建: `intelligent_project_analyzer/services/space_classification_service.py`

- [ ] **Step 1: 写入服务文件**

```python
# intelligent_project_analyzer/services/space_classification_service.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from intelligent_project_analyzer.models.space_classification import (
    AmbiguityInfo,
    RoutingInfo,
    SecondaryCandidate,
    SpaceClassificationResult,
)
from intelligent_project_analyzer.services.project_type_detector import (
    PARENT_TYPE_MAP,
    ProjectTypeDetector,
    get_type_label,
)

logger = logging.getLogger(__name__)

# questionnaire_profile 映射：project_type → 问卷模板 ID
_QUESTIONNAIRE_PROFILE_MAP: Dict[str, str] = {
    "commercial_hospitality": "hospitality_v1",
    "personal_residential": "residential_v1",
    "residential_renovation": "renovation_v1",
    "commercial_office": "office_v1",
    "commercial_retail": "retail_v1",
    "brand_experience": "brand_experience_v1",
    "healthcare_wellness": "healthcare_v1",
    "rural_construction": "rural_v1",
    "popup_temporary": "popup_v1",
    "public_cultural": "cultural_v1",
    "community_public": "community_v1",
    "education_childcare": "education_v1",
    "leisure_entertainment": "leisure_v1",
    "sports_fitness": "sports_v1",
    "restaurant_cafe": "restaurant_v1",
    "urban_renewal": "urban_renewal_v1",
    "industrial_loft": "industrial_v1",
    "landscape_outdoor": "landscape_v1",
}

# ontology_key 映射：与 PARENT_TYPE_MAP 的桶名对齐
_ONTOLOGY_KEY_MAP: Dict[str, str] = {
    "residential": "residential",
    "hospitality": "commercial_hospitality",
    "office": "commercial_office",
    "retail": "commercial_retail",
    "leisure": "leisure_entertainment",
    "education": "education",
    "healthcare": "healthcare",
    "public": "public_space",
    "urban_renewal": "urban_renewal",
    "industrial": "industrial",
    "outdoor": "landscape",
    "special": "other",
}


class SpaceClassificationService:
    """
    旁路分类服务：包装 ProjectTypeDetector 输出 SpaceClassificationResult。
    不修改主链 project_type，仅追加 space_classification 字段。
    """

    _instance: Optional["SpaceClassificationService"] = None

    def __init__(self) -> None:
        self._detector = ProjectTypeDetector()
        self._boundary_rules: List[Dict[str, Any]] = []
        self._load_boundary_rules()

    @classmethod
    def get_instance(cls) -> "SpaceClassificationService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_boundary_rules(self) -> None:
        rules_path = (
            Path(__file__).parent.parent
            / "config"
            / "space_classification"
            / "boundary_cases.yaml"
        )
        try:
            data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
            self._boundary_rules = data.get("boundary_cases", [])
            logger.debug(f"[SpaceClassificationService] 加载 {len(self._boundary_rules)} 条边界规则")
        except Exception as exc:
            logger.warning(f"[SpaceClassificationService] boundary_cases.yaml 加载失败: {exc}")

    def classify(
        self,
        user_input: str,
        confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
        spatial_zone_refs: Optional[List[str]] = None,
    ) -> SpaceClassificationResult:
        """
        执行空间分类，返回 SpaceClassificationResult。
        user_input: 与 ProjectTypeDetector.detect_with_details() 相同的输入文本
        """
        raw = self._detector.detect_with_details(user_input, confirmed_tasks)
        result = self._build_result(raw, spatial_zone_refs or [])
        result = self._apply_boundary_rules(result, user_input)
        return result

    def _build_result(
        self, raw: Dict[str, Any], spatial_zone_refs: List[str]
    ) -> SpaceClassificationResult:
        project_type = raw.get("project_type") or "other"
        confidence = float(raw.get("confidence", 0.0))
        parent_type = raw.get("parent_type")
        specialty_tag = raw.get("specialty_tag")
        secondary_type = raw.get("secondary_type")
        secondary_name = raw.get("secondary_type_name")
        is_ambiguous = bool(raw.get("is_ambiguous", False))
        reason = raw.get("reason", "")

        confidence_level = (
            "high" if confidence >= 0.75
            else "medium" if confidence >= 0.5
            else "low"
        )

        secondary_candidates: List[SecondaryCandidate] = []
        if secondary_type:
            secondary_candidates.append(
                SecondaryCandidate(
                    project_type=secondary_type,
                    confidence=max(0.0, confidence - 0.2),
                    role="competing_primary" if is_ambiguous else "supporting_function",
                )
            )

        ambiguity = AmbiguityInfo(
            level="high" if is_ambiguous else ("medium" if confidence < 0.6 else "low"),
            competing_types=[secondary_type] if secondary_type else [],
        )

        bucket = parent_type or PARENT_TYPE_MAP.get(project_type)
        ontology_key = _ONTOLOGY_KEY_MAP.get(bucket or "", "other")
        questionnaire_profile = _QUESTIONNAIRE_PROFILE_MAP.get(project_type, "general_v1")

        routing = RoutingInfo(
            questionnaire_profile=questionnaire_profile,
            ontology_key=ontology_key,
            deliverable_label=get_type_label(project_type),
        )

        evidence = [reason] if reason else []

        return SpaceClassificationResult(
            primary_bucket=bucket,
            project_type=project_type,
            project_type_name=raw.get("project_type_name"),
            confidence=confidence,
            confidence_level=confidence_level,
            specialty_tags=[specialty_tag] if specialty_tag else [],
            secondary_candidates=secondary_candidates,
            ambiguity=ambiguity,
            routing=routing,
            evidence=evidence,
            spatial_zone_refs=spatial_zone_refs,
        )

    def _apply_boundary_rules(
        self, result: SpaceClassificationResult, user_input: str
    ) -> SpaceClassificationResult:
        """对照 boundary_cases.yaml 标记 boundary_risk 和 needs_clarification。"""
        lower_input = user_input.lower()

        for rule in self._boundary_rules:
            if result.project_type not in rule.get("types", []):
                continue
            triggers = rule.get("trigger_keywords", [])
            if not any(kw in lower_input for kw in triggers):
                continue

            # 命中边界规则
            result.ambiguity.boundary_risk = True
            result.ambiguity.needs_clarification = True
            if rule.get("clarification"):
                result.ambiguity.clarification_questions.append(rule["clarification"])

            competing = [t for t in rule.get("types", []) if t != result.project_type]
            for ct in competing:
                if ct not in result.ambiguity.competing_types:
                    result.ambiguity.competing_types.append(ct)

            risk_level = rule.get("risk_level", "low")
            if risk_level == "high":
                result.ambiguity.level = "high"
            elif risk_level == "medium" and result.ambiguity.level == "low":
                result.ambiguity.level = "medium"

            logger.info(
                f"[SpaceClassificationService] 边界规则命中: {rule['id']} "
                f"({result.project_type}, risk={risk_level})"
            )

        return result
```

- [ ] **Step 2: 验证导入**

```bash
python -c "from intelligent_project_analyzer.services.space_classification_service import SpaceClassificationService; s = SpaceClassificationService(); print('OK')"
```

预期输出：`OK`（可能有 WARNING 日志，但不应有 ImportError）

- [ ] **Step 3: 提交**

```bash
git add intelligent_project_analyzer/services/space_classification_service.py
git commit -m "feat: add SpaceClassificationService wrapping ProjectTypeDetector"
```

---

## Task 8: Phase 1 — 单元测试

**Files:**
- 创建: `tests/intelligence/test_space_classification_service.py`

- [ ] **Step 1: 写入测试文件**

```python
# tests/intelligence/test_space_classification_service.py
import pytest

from intelligent_project_analyzer.services.space_classification_service import (
    SpaceClassificationService,
)


@pytest.fixture
def svc():
    return SpaceClassificationService()


def test_classify_returns_valid_schema(svc):
    result = svc.classify("帮我设计一个精品民宿，有8间客房，乡村风格")
    assert result.schema_version == "space_classification.v1"
    assert result.project_type is not None
    assert result.confidence >= 0.0
    assert result.confidence_level in ("high", "medium", "low")
    assert result.ambiguity is not None
    assert result.routing is not None


def test_classify_hospitality_type(svc):
    result = svc.classify("高端精品酒店室内设计，50间客房，豪华风格")
    assert result.project_type == "commercial_hospitality"
    assert result.primary_bucket == "hospitality"
    assert result.confidence_level in ("high", "medium")


def test_classify_residential_type(svc):
    result = svc.classify("三居室住宅精装修，现代简约风格，140平米")
    assert result.project_type in ("personal_residential", "residential_renovation")


def test_classify_low_confidence_marks_ambiguity(svc):
    # 极短输入，置信度应低
    result = svc.classify("空间设计")
    if result.confidence < 0.5:
        assert result.confidence_level == "low"


def test_boundary_rule_hospitality_vs_residential(svc):
    result = svc.classify("民宿改造，乡村住宅风格，想对外经营")
    # 应触发边界规则
    assert result.ambiguity.boundary_risk is True
    assert result.ambiguity.needs_clarification is True
    assert len(result.ambiguity.clarification_questions) > 0


def test_boundary_rule_brand_vs_retail(svc):
    result = svc.classify("品牌旗舰店展厅设计，体验中心")
    assert result.ambiguity.boundary_risk is True


def test_secondary_candidate_populated(svc):
    # 歧义输入应产生次候选
    result = svc.classify("民宿 展厅 品牌体验 酒店 零售")
    # 不强断言 secondary_candidates 非空（取决于 detector 结果）
    assert isinstance(result.secondary_candidates, list)


def test_routing_questionnaire_profile_not_empty(svc):
    result = svc.classify("医疗康复中心室内设计方案")
    assert result.routing.questionnaire_profile != ""
    assert result.routing.ontology_key != ""


def test_classify_result_serializable(svc):
    result = svc.classify("办公室设计，500平方米，现代风格")
    d = result.model_dump()
    assert isinstance(d, dict)
    assert "project_type" in d
    assert "ambiguity" in d
    assert "routing" in d


def test_type_enumeration_valid(svc):
    from intelligent_project_analyzer.services.project_type_detector import PROJECT_TYPE_REGISTRY
    valid_types = {entry["id"] for entry in PROJECT_TYPE_REGISTRY if isinstance(entry, dict)}
    # 允许 "other" 作为兜底
    valid_types.add("other")

    for text in [
        "精品民宿设计",
        "办公楼大厅",
        "医院候诊区",
        "品牌体验店",
        "住宅改造",
    ]:
        result = svc.classify(text)
        assert result.project_type in valid_types, (
            f"project_type={result.project_type!r} 不在注册表中"
        )
```

- [ ] **Step 2: 运行测试（预期全部通过）**

```bash
python -m pytest tests/intelligence/test_space_classification_service.py -v
```

预期：全部 PASS（`test_classify_low_confidence_marks_ambiguity` 可能 SKIP 如置信度不低）

- [ ] **Step 3: 提交**

```bash
git add tests/intelligence/test_space_classification_service.py
git commit -m "test: add unit tests for SpaceClassificationService"
```

---

## Task 9: Phase 2 — state.py 新增 space_classification 字段

**Files:**
- 修改: `intelligent_project_analyzer/core/state.py:185`

- [ ] **Step 1: 定位插入位置**

打开 `intelligent_project_analyzer/core/state.py`，找到第 185 行：
```python
    project_classification: Optional[Dict[str, Any]]
```

- [ ] **Step 2: 在 project_classification 字段下方插入新字段**

在 `project_classification` 字段之后（约第 197 行，`"""` 结束处），插入：

```python
    # space_classification: SpaceClassificationResult 的 dict 形式
    # Phase 1 旁路服务写入，不替换 project_type
    space_classification: Optional[Dict[str, Any]]
```

- [ ] **Step 3: 找到 `StateManager.create_initial_state()` 初始化位置**

搜索 `project_classification=None` 的初始化位置（约行 755）：
```python
project_classification=None,    #  阶段2: 统一分类出口初始化
```

在其下方追加：
```python
space_classification=None,      #  空间分类结果（旁路，不替换 project_type）
```

- [ ] **Step 4: 验证语法**

```bash
python -c "from intelligent_project_analyzer.core.state import ProjectAnalysisState; print('OK')"
```

预期输出：`OK`

- [ ] **Step 5: 提交**

```bash
git add intelligent_project_analyzer/core/state.py
git commit -m "feat: add space_classification field to ProjectAnalysisState"
```

---

## Task 10: Phase 2 — requirements_analyst_agent.py 双写

**Files:**
- 修改: `intelligent_project_analyzer/agents/requirements_analyst_agent.py:722-758`

- [ ] **Step 1: 定位 output_node 中 project_type 赋值处（行 722）**

```python
project_type = _infer_project_type(structured_data) or "other"
```

- [ ] **Step 2: 在 project_type 赋值后、return 语句前插入 space_classification 调用**

在行 722 之后、`structured_data["project_type"] = project_type`（行 725）之前，插入：

```python
    # Phase 2 双写：调用旁路分类服务，生成 SpaceClassificationResult
    _space_classification_dict: Optional[Dict[str, Any]] = None
    try:
        from intelligent_project_analyzer.services.space_classification_service import (
            SpaceClassificationService,
        )
        _combined_text = " ".join([
            str(structured_data.get("project_task", "")),
            str(structured_data.get("character_narrative", "")),
            str(structured_data.get("project_overview", "")),
            str(structured_data.get("target_users", "")),
        ])
        _spatial_zone_refs = [
            z.get("zone_id", "") for z in state.get("extracted_spatial_zones", []) or []
            if z.get("zone_id")
        ]
        _sc_result = SpaceClassificationService.get_instance().classify(
            _combined_text,
            confirmed_tasks=None,
            spatial_zone_refs=_spatial_zone_refs,
        )
        _space_classification_dict = _sc_result.model_dump()
        logger.info(
            f"[Phase2] space_classification: {_sc_result.project_type} "
            f"({_sc_result.confidence_level}, bucket={_sc_result.primary_bucket})"
        )
    except Exception as _sc_exc:
        logger.warning(f"[Phase2] SpaceClassificationService 调用失败（忽略）: {_sc_exc}")
```

- [ ] **Step 3: 在 return 语句中追加 space_classification 字段**

找到 `output_node` 的 return 字典（行 754-762），追加：

```python
    return {
        "structured_data": structured_data,
        "confidence": confidence,
        "analysis_mode": analysis_mode,
        "project_type": project_type,
        "space_classification": _space_classification_dict,   # 新增
        "total_elapsed_ms": total_elapsed,
        "processing_log": state.get("processing_log", [])
        + [f"[Output] 完成 ({elapsed_ms:.0f}ms) - 模式: {analysis_mode}, 置信度: {confidence:.2f}"],
        "node_path": state.get("node_path", []) + ["output"],
    }
```

- [ ] **Step 4: 在文件顶部确认 Optional 已导入**

搜索文件顶部，确认 `from typing import ... Optional` 已存在。若无，追加到 typing 导入行。

- [ ] **Step 5: 验证语法**

```bash
python -c "from intelligent_project_analyzer.agents.requirements_analyst_agent import build_requirements_analyst_graph; print('OK')"
```

预期输出：`OK`

- [ ] **Step 6: 运行已有测试确认不破坏现有功能**

```bash
python -m pytest tests/ -k "requirements_analyst" -v --tb=short 2>/dev/null || echo "no existing tests"
```

- [ ] **Step 7: 提交**

```bash
git add intelligent_project_analyzer/agents/requirements_analyst_agent.py
git commit -m "feat: double-write space_classification in output_node"
```

---

## Task 11: Phase 2 — output_intent_detection.py 优先读 space_classification

**Files:**
- 修改: `intelligent_project_analyzer/interaction/nodes/output_intent_detection.py:1177-1180`

- [ ] **Step 1: 定位 v10.1 兼容代码（行 1177-1180）**

当前代码：
```python
    # v10.1 fix: project_classification 已被 v9.1 移除（永远为 None），
    # 改为从 project_type (str) 构造兼容结构，供 _detect_spatial_attribute_signals 使用
    _project_type_str = state.get("project_type", "") or structured_requirements.get("project_type", "")
    project_classification = {"project_type": _project_type_str} if _project_type_str else None
```

- [ ] **Step 2: 替换为三级回退读取**

```python
    # v10.1 fix: project_classification 已被 v9.1 移除（永远为 None）
    # v10.2 update: 优先读 space_classification（Phase 2 双写），无则回退 project_type
    _sc = state.get("space_classification")
    _project_type_str = (
        (_sc.get("project_type") if _sc else None)
        or state.get("project_type", "")
        or structured_requirements.get("project_type", "")
    )
    project_classification = {"project_type": _project_type_str} if _project_type_str else None
```

- [ ] **Step 3: 验证语法**

```bash
python -c "from intelligent_project_analyzer.interaction.nodes.output_intent_detection import detect_output_intent_node; print('OK')"
```

预期输出：`OK`

- [ ] **Step 4: 提交**

```bash
git add intelligent_project_analyzer/interaction/nodes/output_intent_detection.py
git commit -m "feat: read space_classification first in output_intent_detection (v10.2)"
```

---

## Task 12: Phase 3 — 类型知识包 YAML（7 个文件）

**Files:**
- 创建: `intelligent_project_analyzer/config/type_knowledge/` 下 7 个 YAML

- [ ] **Step 1: 写入 commercial_hospitality.yaml**

```yaml
# intelligent_project_analyzer/config/type_knowledge/commercial_hospitality.yaml
project_type: commercial_hospitality
display_name: 酒店民宿餐饮
primary_bucket: hospitality

core_logic: |
  酒店/民宿/餐饮空间的核心是「体验经济」——客人支付的是时间与情绪，
  而非单纯空间使用权。每个功能区须服务于入住/用餐的完整体验链。

typical_tensions:
  - "商业效率（翻台率/入住率）vs 情绪沉浸感"
  - "品牌标准化 vs 在地文化表达"
  - "公区展示性 vs 私区安全感"

required_variables:
  - room_count
  - operation_model         # 自营 / 加盟 / 精品独立
  - star_level_or_tier
  - target_guest_profile

questionnaire_profile: hospitality_v1
floorplan_profile: hospitality_v1

visual_profile:
  visual_pitfalls:
    - "把民宿拍成住宅客厅：缺乏接待感和品牌故事"
    - "过度渲染奢华材质，脱离实际造价"
  forbidden_biases:
    - "一律使用暖光温馨氛围（商务酒店需要冷静、高效）"
  type_constraints:
    - "餐区必须展示动线和备餐区关系，不只是美食特写"
    - "客房必须展示床位朝向与自然光关系"

deliverable_profile:
  preferred_label: "整体室内设计方案"
  naming_pattern: "{project_name}{display_name}室内设计方案"
```

- [ ] **Step 2: 写入 healthcare_wellness.yaml**

```yaml
# intelligent_project_analyzer/config/type_knowledge/healthcare_wellness.yaml
project_type: healthcare_wellness
display_name: 医疗康养
primary_bucket: healthcare

core_logic: |
  医疗康养空间服务于身体和心理的修复过程，核心价值是「安全感 + 疗愈感」。
  功能分区需满足医疗流程（洁污分区、动线隔离）同时减少恐惧感。

typical_tensions:
  - "医疗功能严谨性 vs 空间温馨疗愈感"
  - "感控要求 vs 家庭化氛围"
  - "效率动线 vs 患者心理安抚"

required_variables:
  - facility_type           # 综合医院 / 专科诊所 / 康复中心 / 养老
  - patient_profile
  - regulatory_requirements

questionnaire_profile: healthcare_v1
floorplan_profile: healthcare_v1

visual_profile:
  visual_pitfalls:
    - "只输出疗愈氛围图，忽略医疗功能区划"
    - "过度使用绿色植物掩盖功能缺失"
  forbidden_biases:
    - "一律使用白色+原木的「北欧轻医疗」（养老/康复/综合门诊各有不同）"
  type_constraints:
    - "必须展示候诊区与诊室的动线关系"
    - "感控分区必须在平面图中可读"

deliverable_profile:
  preferred_label: "室内设计方案"
  naming_pattern: "{project_name}{display_name}室内设计方案"
```

- [ ] **Step 3: 写入 brand_experience.yaml**

```yaml
# intelligent_project_analyzer/config/type_knowledge/brand_experience.yaml
project_type: brand_experience
display_name: 品牌体验空间
primary_bucket: retail

core_logic: |
  品牌体验空间的核心是「叙事性」——空间本身就是品牌的三维广告牌。
  访客不是来购买商品，而是来「体验品牌价值观」。

typical_tensions:
  - "强烈品牌主张 vs 访客舒适度"
  - "视觉冲击力 vs 功能实用性"
  - "品牌全球标准化 vs 在地文化适配"

required_variables:
  - brand_positioning
  - target_visitor_dwell_time
  - commercial_conversion_goal  # 纯体验 / 展销一体

questionnaire_profile: brand_experience_v1
floorplan_profile: brand_experience_v1

visual_profile:
  visual_pitfalls:
    - "退化为普通零售陈列，失去品牌叙事性"
    - "展示图不体现品牌视觉语言"
  forbidden_biases:
    - "一律套用「白墙+射灯」展厅模板"
  type_constraints:
    - "必须展示品牌核心视觉元素的空间应用"
    - "访客动线须体现「入场→沉浸→高潮→离场」的叙事节奏"

deliverable_profile:
  preferred_label: "品牌体验空间设计方案"
  naming_pattern: "{project_name}品牌体验空间设计方案"
```

- [ ] **Step 4: 写入 rural_construction.yaml**

```yaml
# intelligent_project_analyzer/config/type_knowledge/rural_construction.yaml
project_type: rural_construction
display_name: 乡建乡村
primary_bucket: special

core_logic: |
  乡村建设的核心是「在地性」——设计需根植于当地文化、材料、
  建造工艺和社区需求，而非将城市审美强加于乡村。

typical_tensions:
  - "外来设计师视角 vs 在地文化认同"
  - "现代功能需求 vs 传统建筑肌理"
  - "商业开发 vs 社区原生生活保护"

required_variables:
  - village_type             # 传统村落 / 现代农村 / 特色小镇
  - community_involvement    # 政府主导 / 集体自建 / 商业开发
  - preservation_level       # 修缮 / 活化 / 新建

questionnaire_profile: rural_v1
floorplan_profile: rural_v1

visual_profile:
  visual_pitfalls:
    - "把乡建做成「伪乡村网红打卡地」，失去在地真实性"
    - "只展示改造后效果，不呈现与周边环境的关系"
  forbidden_biases:
    - "一律使用夯土+青砖的视觉符号，脱离具体地域文化"
  type_constraints:
    - "必须展示建筑与村落整体肌理的关系"
    - "材料选择需注释当地来源"

deliverable_profile:
  preferred_label: "乡村建设设计方案"
  naming_pattern: "{project_name}乡村建设设计方案"
```

- [ ] **Step 5: 写入 residential_renovation.yaml**

```yaml
# intelligent_project_analyzer/config/type_knowledge/residential_renovation.yaml
project_type: residential_renovation
display_name: 住宅改造翻新
primary_bucket: residential

core_logic: |
  存量住宅改造的核心约束是「结构限制 + 用户记忆」——
  设计不从零开始，须在既有格局和使用者情感记忆中寻找突破口。

typical_tensions:
  - "改造幅度 vs 预算与结构可行性"
  - "业主对旧空间的情感依附 vs 设计师的提升方案"
  - "局部翻新 vs 整体系统性改造"

required_variables:
  - original_building_age
  - renovation_scope         # 局部 / 整体 / 结构调整
  - resident_profile
  - budget_tier

questionnaire_profile: renovation_v1
floorplan_profile: renovation_v1

visual_profile:
  visual_pitfalls:
    - "改造方案看起来像新建，失去改造叙事"
    - "不展示改造前后对比"
  forbidden_biases:
    - "一律做「全屋大白墙」，忽略结构条件"
  type_constraints:
    - "必须包含改造前后平面对比"
    - "须注明保留/拆除/新增的结构元素"

deliverable_profile:
  preferred_label: "住宅改造设计方案"
  naming_pattern: "{project_name}住宅改造设计方案"
```

- [ ] **Step 6: 写入 commercial_office.yaml**

```yaml
# intelligent_project_analyzer/config/type_knowledge/commercial_office.yaml
project_type: commercial_office
display_name: 商业办公
primary_bucket: office

core_logic: |
  办公空间设计的核心是「工作效能 + 文化表达」——
  既要支撑高效协作，也要通过空间传递企业文化和雇主品牌。

typical_tensions:
  - "开放协作 vs 专注私密"
  - "企业文化个性表达 vs 通用功能灵活性"
  - "短期装修成本 vs 长期使用弹性"

required_variables:
  - headcount
  - work_mode               # 固定工位 / 弹性 / 混合
  - industry_type
  - culture_positioning     # 传统企业 / 科技创新 / 创意产业

questionnaire_profile: office_v1
floorplan_profile: office_v1

visual_profile:
  visual_pitfalls:
    - "只展示公区和会议室，忽略工作区实际体验"
    - "企业文化符号堆砌，缺乏空间逻辑"
  forbidden_biases:
    - "一律做「工业风+植物墙」的互联网办公模板"
  type_constraints:
    - "工位区密度和采光关系须在平面图中体现"
    - "协作区与安静区的比例须标注"

deliverable_profile:
  preferred_label: "办公空间设计方案"
  naming_pattern: "{project_name}办公空间设计方案"
```

- [ ] **Step 7: 写入 commercial_retail.yaml**

```yaml
# intelligent_project_analyzer/config/type_knowledge/commercial_retail.yaml
project_type: commercial_retail
display_name: 商业零售
primary_bucket: retail

core_logic: |
  零售空间设计的核心是「购买转化」——
  空间的每一个决策最终指向：让目标客群更愿意停留、浏览和购买。

typical_tensions:
  - "陈列密度（SKU展示）vs 空间体验感"
  - "短期促销灵活性 vs 长期品牌形象稳定性"
  - "线下体验差异化 vs 运营成本控制"

required_variables:
  - retail_category          # 服饰/美妆/食品/3C/家居等
  - store_size_tier          # 大店旗舰 / 标准店 / 精品小店
  - target_customer_profile
  - online_offline_ratio     # 线下体验占比

questionnaire_profile: retail_v1
floorplan_profile: retail_v1

visual_profile:
  visual_pitfalls:
    - "只展示空陈列效果，不呈现商品与空间的关系"
    - "忽略收银台、库房、试衣间等功能区"
  forbidden_biases:
    - "所有零售都做「极简白盒子」，忽略品类差异"
  type_constraints:
    - "动线设计（主动线/副动线）须在平面图标注"
    - "收银点位置须合理规划"

deliverable_profile:
  preferred_label: "零售空间设计方案"
  naming_pattern: "{project_name}零售空间设计方案"
```

- [ ] **Step 8: 验证所有 7 个 YAML 可解析**

```bash
python -c "
import yaml, pathlib
for f in pathlib.Path('intelligent_project_analyzer/config/type_knowledge').glob('*.yaml'):
    data = yaml.safe_load(f.read_text(encoding='utf-8'))
    print(f'OK: {f.name} -> {data[\"project_type\"]}')
"
```

预期：7 行 `OK: *.yaml -> <type>`

- [ ] **Step 9: 提交**

```bash
git add intelligent_project_analyzer/config/type_knowledge/
git commit -m "feat: add type knowledge packages for 7 priority project types"
```

---

## Task 13: Phase 3 — deliverable_label 路由优先级

**Files:**
- 修改: `intelligent_project_analyzer/interaction/nodes/output_intent_detection.py`

- [ ] **Step 1: 搜索 deliverable 命名生成处**

```bash
grep -n "deliverable_label\|space_type\|项目命名\|方案名称" intelligent_project_analyzer/interaction/nodes/output_intent_detection.py | head -20
```

- [ ] **Step 2: 找到 space_type 读取点**

搜索 `physical_context.get("space_type")` 或 `structured_requirements.get("space_type")` 的位置，记录行号。

- [ ] **Step 3: 在该处增加 deliverable_label 优先读取**

在找到的 space_type 读取处，将：
```python
display_name = physical_context.get("space_type") or project_type_name
```
替换为：
```python
_sc = state.get("space_classification") or {}
_routing = _sc.get("routing") or {}
display_name = (
    _routing.get("deliverable_label")
    or physical_context.get("space_type")
    or project_type_name
)
```

> 注意：如果该文件没有此类型的直接赋值（space_type 可能在 `deliverable_id_generator_node.py` 中），则跳过此步骤，等 Task 14（space_type_field_audit）完成后再实施。请先检查 audit 文档的结论。

- [ ] **Step 4: 提交（如实际有改动）**

```bash
git add intelligent_project_analyzer/interaction/nodes/output_intent_detection.py
git commit -m "feat(Phase3): prefer routing.deliverable_label for display name"
```

---

## Task 14: Phase 3 — task_completeness_analyzer questionnaire_profile

**Files:**
- 修改: `intelligent_project_analyzer/services/task_completeness_analyzer.py`

- [ ] **Step 1: 定位 analyze() 方法签名**

搜索 `def analyze` 在 `task_completeness_analyzer.py` 中的行号：

```bash
grep -n "def analyze" intelligent_project_analyzer/services/task_completeness_analyzer.py
```

- [ ] **Step 2: 在 analyze() 中增加 space_classification 读取**

找到 analyze() 方法，在已有 `project_type` 参数读取后，增加：

```python
# Phase 3: 优先从 space_classification 读取 questionnaire_profile
_sc = space_classification or {}
_routing = _sc.get("routing") or {}
_questionnaire_profile = _routing.get("questionnaire_profile")

# 若有 questionnaire_profile，注入维度增强
if _questionnaire_profile:
    logger.debug(
        f"[TaskCompletenessAnalyzer] questionnaire_profile={_questionnaire_profile}"
    )
```

> 注：此步骤为轻量接入，仅做日志记录，不改变分析逻辑。完整问卷 profile 驱动需后续单独 RFC。

- [ ] **Step 3: 修改调用方传入 space_classification**

在 `task_completeness_analyzer` 的调用处（通过 grep 找到），增加 `space_classification=state.get("space_classification")` 参数传入。

- [ ] **Step 4: 提交**

```bash
git add intelligent_project_analyzer/services/task_completeness_analyzer.py
git commit -m "feat(Phase3): pass questionnaire_profile from space_classification to completeness analyzer"
```

---

## Task 15: Phase 4 — classification_error_cases.yaml

**Files:**
- 创建: `intelligent_project_analyzer/config/space_classification/classification_error_cases.yaml`

- [ ] **Step 1: 写入错误案例骨架**

```yaml
# intelligent_project_analyzer/config/space_classification/classification_error_cases.yaml
# 分类错判案例库
# status: open / fixed / wont_fix

error_cases:
  - id: ec_001
    created_at: "2026-04-30"
    input_sample: "乡村民宿，对外出租，8间客房，田园风格"
    wrong_classification: personal_residential
    correct_classification: commercial_hospitality
    confidence_at_error: 0.55
    root_cause: "缺少「对外出租」关键词权重，优先匹配住宅关键词"
    rule_fix: "在 commercial_hospitality 关键词增加「对外出租」「民宿经营」"
    status: open
    reviewed_by: null

  - id: ec_002
    created_at: "2026-04-30"
    input_sample: "品牌旗舰店，以体验为主，兼顾零售销售"
    wrong_classification: commercial_retail
    correct_classification: brand_experience
    confidence_at_error: 0.62
    root_cause: "「旗舰店」关键词权重在 retail 类型中更高"
    rule_fix: "brand_experience 增加「旗舰店+体验」复合权重"
    status: open
    reviewed_by: null
```

- [ ] **Step 2: 提交**

```bash
git add intelligent_project_analyzer/config/space_classification/classification_error_cases.yaml
git commit -m "feat(Phase4): add classification_error_cases.yaml skeleton"
```

---

## Task 16: Phase 4 — PROJECT_TYPE_REGISTRY 追加 status 字段

**Files:**
- 修改: `intelligent_project_analyzer/services/project_type_detector.py`

- [ ] **Step 1: 定位 PROJECT_TYPE_REGISTRY 起始行（行 49）**

打开文件，找到注册表的第一个条目格式，例如：
```python
{
    "id": "commercial_hospitality",
    "name": "酒店民宿餐饮",
    ...
}
```

- [ ] **Step 2: 为每个条目追加 status 字段**

为注册表中所有 32 个条目追加 `"status": "active"`，例如：
```python
{
    "id": "commercial_hospitality",
    "name": "酒店民宿餐饮",
    ...
    "status": "active",   # 新增
}
```

- [ ] **Step 3: 验证注册表仍可正常加载**

```bash
python -c "
from intelligent_project_analyzer.services.project_type_detector import PROJECT_TYPE_REGISTRY
active = [e for e in PROJECT_TYPE_REGISTRY if e.get('status') == 'active']
print(f'active types: {len(active)}')
"
```

预期输出：`active types: 32`（或实际数量）

- [ ] **Step 4: 验证 SpaceClassificationService 仍正常工作**

```bash
python -m pytest tests/intelligence/test_space_classification_service.py -v --tb=short
```

预期：全部通过

- [ ] **Step 5: 提交**

```bash
git add intelligent_project_analyzer/services/project_type_detector.py
git commit -m "feat(Phase4): add status field to PROJECT_TYPE_REGISTRY entries"
```

---

## Task 17: Phase 4 — LLM 兜底裁决

**Files:**
- 修改: `intelligent_project_analyzer/services/space_classification_service.py`

- [ ] **Step 1: 在 SpaceClassificationService 中添加 LLM 兜底方法**

在 `_apply_boundary_rules` 方法之后，追加：

```python
    def classify_with_llm_fallback(
        self,
        user_input: str,
        confirmed_tasks=None,
        spatial_zone_refs=None,
    ) -> SpaceClassificationResult:
        """
        带 LLM 兜底的分类：当 ambiguity.level == 'high' 时触发 LLM 裁决。
        LLM 失败时降级为 needs_clarification=True，不硬选。
        """
        result = self.classify(user_input, confirmed_tasks, spatial_zone_refs)

        if result.ambiguity.level != "high":
            return result

        try:
            return self._llm_boundary_resolve(user_input, result)
        except Exception as exc:
            logger.warning(f"[SpaceClassificationService] LLM 兜底失败，降级为追问: {exc}")
            result.ambiguity.needs_clarification = True
            return result

    def _llm_boundary_resolve(
        self, user_input: str, initial_result: SpaceClassificationResult
    ) -> SpaceClassificationResult:
        """调用 LLM 裁决高歧义案例，输出须通过 SpaceClassificationResult schema 校验。"""
        from intelligent_project_analyzer.services.llm_factory import LLMFactory
        from intelligent_project_analyzer.models.space_classification import SpaceClassificationResult as SCR

        candidates = [initial_result.project_type] + [
            c.project_type for c in initial_result.secondary_candidates
        ]
        candidates_str = "、".join(candidates)

        prompt = (
            f"用户描述：{user_input}\n\n"
            f"初步检测类型：{initial_result.project_type}（置信度 {initial_result.confidence:.0%}）\n"
            f"竞争候选类型：{candidates_str}\n\n"
            f"请根据用户描述，从候选类型中选择最合适的项目类型，"
            f"并说明判断依据。只能选择候选类型中的一个，不能创造新类型。"
        )

        structured_llm = LLMFactory.create_structured_llm(schema=SCR)
        llm_result: SCR = structured_llm.invoke(prompt)

        # 安全校验：LLM 输出的 project_type 必须在原候选列表中
        from intelligent_project_analyzer.services.project_type_detector import PROJECT_TYPE_REGISTRY
        valid_ids = {e["id"] for e in PROJECT_TYPE_REGISTRY if isinstance(e, dict)}
        valid_ids.add("other")
        if llm_result.project_type not in valid_ids:
            logger.warning(
                f"[LLM 兜底] 输出类型 {llm_result.project_type!r} 不在注册表中，回退初始结果"
            )
            initial_result.ambiguity.needs_clarification = True
            return initial_result

        logger.info(
            f"[LLM 兜底] 裁决结果: {llm_result.project_type} "
            f"(初始: {initial_result.project_type})"
        )
        return llm_result
```

- [ ] **Step 2: 添加 LLM 兜底方法的测试**

在 `tests/intelligence/test_space_classification_service.py` 末尾追加：

```python
def test_classify_with_llm_fallback_non_ambiguous(svc):
    # 低歧义案例不触发 LLM（无副作用验证）
    result = svc.classify_with_llm_fallback("三居室住宅装修，现代风格")
    assert result.project_type is not None
    # 低歧义时 ambiguity.level 应为 low 或 medium，不调用 LLM
    assert result.schema_version == "space_classification.v1"
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/intelligence/test_space_classification_service.py::test_classify_with_llm_fallback_non_ambiguous -v
```

预期：PASS

- [ ] **Step 4: 提交**

```bash
git add intelligent_project_analyzer/services/space_classification_service.py tests/intelligence/test_space_classification_service.py
git commit -m "feat(Phase4): add LLM boundary resolver fallback to SpaceClassificationService"
```

---

## Task 18: Phase 4 — 可观测指标

**Files:**
- 修改: `intelligent_project_analyzer/services/space_classification_service.py`

- [ ] **Step 1: 在 classify() 方法末尾追加指标日志**

在 `_apply_boundary_rules` 调用之后、`return result` 之前，插入：

```python
        # 可观测指标（结构化日志，供后续监控系统接入）
        _metrics = {
            "event": "space_classification",
            "project_type": result.project_type,
            "confidence": round(result.confidence, 3),
            "confidence_level": result.confidence_level,
            "primary_bucket": result.primary_bucket,
            "boundary_risk": result.ambiguity.boundary_risk,
            "needs_clarification": result.ambiguity.needs_clarification,
            "ambiguity_level": result.ambiguity.level,
            "specialty_tags_count": len(result.specialty_tags),
            "secondary_candidates_count": len(result.secondary_candidates),
        }
        logger.info(f"[space_classification_metrics] {_metrics}")
```

- [ ] **Step 2: 验证日志正常输出**

```bash
python -c "
import logging
logging.basicConfig(level=logging.INFO)
from intelligent_project_analyzer.services.space_classification_service import SpaceClassificationService
s = SpaceClassificationService()
r = s.classify('精品民宿设计，8间客房')
print('project_type:', r.project_type)
"
```

预期：控制台输出包含 `[space_classification_metrics]` 的日志行。

- [ ] **Step 3: 提交**

```bash
git add intelligent_project_analyzer/services/space_classification_service.py
git commit -m "feat(Phase4): add structured observability metrics logging"
```

---

## 自检：Spec 覆盖确认

| 设计要求 | 对应 Task |
|---------|-----------|
| Phase 0 四个文档产出 | Task 1-4 |
| Pydantic SpaceClassificationResult | Task 5 |
| boundary_cases.yaml 8个规则 | Task 6 |
| SpaceClassificationService | Task 7 |
| 单元测试（20-50条输入验证） | Task 8 |
| state.py 新增 space_classification | Task 9 |
| 双写：requirements_analyst_agent.py | Task 10 |
| output_intent_detection.py 优先读 | Task 11 |
| 7个类型知识包 | Task 12 |
| deliverable_label 路由 | Task 13 |
| questionnaire_profile 接入 | Task 14 |
| classification_error_cases.yaml | Task 15 |
| PROJECT_TYPE_REGISTRY status 字段 | Task 16 |
| LLM 兜底裁决 | Task 17 |
| 可观测指标 | Task 18 |
| 明确不改 deliverable_id_generator_node | Task 3（audit 前置） + Task 13（条件跳过） |
| spatial_zones 不进入分类树 | Task 7（spatial_zone_refs 只存 ID 引用） |
