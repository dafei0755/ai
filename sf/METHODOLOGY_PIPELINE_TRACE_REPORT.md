# 方法论驱动灵活输出框架 — 全流水线追踪报告

> 生成时间: 2026-02-21
> 范围: `intelligent_project_analyzer/` 主流水线中所有方法论/框架介入点

---

## 一、工作流全节点序列（StateGraph 定义）

**文件**: [intelligent_project_analyzer/workflow/main_workflow.py](intelligent_project_analyzer/workflow/main_workflow.py#L159-L360)

完整节点序列（基于 `_build_workflow_graph`，L159–L360）：

```
START
  → unified_input_validator_initial       (L176)
  → requirements_analyst                  (L184)   ★ Mode Engine 检测
  → feasibility_analyst                   (L185)
  → unified_input_validator_secondary     (L177)
  → progressive_step1_core_task           (L190)   三步递进式问卷
  → progressive_step2_radar               (L191)
  → progressive_step3_gap_filling         (L192)
  → questionnaire_summary                 (L194)
  → project_director                      (L206)   ★ 框架选择 / 模式任务注入
  → deliverable_id_generator              (L208)
  → search_query_generator                (L210)
  → role_task_unified_review              (L212)
  → quality_preflight                     (L215)
  → batch_executor                        (L220)   ★ Expert Factory 能力注入
    → batch_aggregator                    (L222)
    → batch_router                        (L223)
    → [循环: batch_strategy_review → batch_executor]
  → detect_challenges                     (L225)
  → result_aggregator                     (L232)   ★ 框架感知聚合
  → report_guard                          (L179)
  → pdf_generator                         (L233)   ★ 文本渲染 ability_core_matrix
  → user_question / END
```

---

## 二、方法论组件概要

### 2.1 sf/10_Mode_Engine（设计模式层）
**文件**: [sf/10_Mode_Engine](sf/10_Mode_Engine) — 2215行

定义了 **10种设计模式**（策略方向）：
| ID | 名称 |
|----|------|
| M1 | 概念驱动型设计 Concept-Driven |
| M2 | 功能效率型设计 Function-Efficiency |
| M3 | 情绪体验型设计 Emotional-Experience |
| M4 | 资产资本型设计 Capital-Asset |
| M5 | 乡建在地型设计 Rural-Context |
| M6 | 城市更新型设计 Urban-Regeneration |
| M7 | 技术整合型设计 Technology-Integration |
| M8 | 极端环境型设计 Extreme-Condition |
| M9 | 社会结构型设计 Social-Structure |
| M10 | 未来推演型设计 Future-Speculation |

**核心声明**（L18–24）：
> "模式（Mode）是策略方向——决定'用什么方式做这个项目'。
> 能力（Ability）是执行技能——决定'设计师需要什么本事'。
> 模式调度能力，而非等于能力。"

每种模式包含：模式定义、适用场景、核心能力组合、设计原则。

### 2.2 sf/12_Ability_Core（能力构成层）
**文件**: [sf/12_Ability_Core](sf/12_Ability_Core) — 2648行

定义了 **12种核心能力**：
| ID | 名称 |
|----|------|
| A1 | 概念建构能力 Concept Architecture |
| A2 | 空间结构能力 Spatial Structuring |
| A3 | 叙事节奏能力 Narrative Orchestration |
| A4 | 材料系统能力 Material Intelligence |
| A5 | 灯光系统能力 Lighting Architecture |
| A6 | 功能效率能力 Functional Optimization |
| A7 | 资本策略能力 Capital Strategy |
| A8 | 技术整合能力 Technology Integration |
| A9 | 社会关系建模能力 Social Structure Modeling |
| A10 | 环境适应能力 Environmental Adaptation |
| A11 | 运营与产品化能力 Operation & Productization |
| A12 | 文明表达与跨学科整合能力 Civilizational Expression |

每个能力包含：能力本质、为什么重要、5层递进（表象/策略/机制/批判/演化）、常见误区。

### 2.3 sf/13_Evaluation_Matrix（评估矩阵层）
**文件**: [sf/13_Evaluation_Matrix](sf/13_Evaluation_Matrix) — 520行

定义了 **10个评估维度**的权重矩阵。核心机制是：
**每种设计模式激活不同的评估维度权重**，例如：
- M1_concept_driven → 概念完整度(40%) + 叙事连贯度(25%)
- M5_rural_context → 文化在地(35%) + 社会影响(25%) + 跨学科整合(15%)

底线规则：技术可行评估 ≥ 10%，概念完整度评估 ≥ 10%。

### 2.4 sf/14_Output_Standards（输出标准层）
**文件**: [sf/14_Output_Standards](sf/14_Output_Standards) — 325行

定义了交付物分级标准：
- **T1 信息型**：验收=准确、有出处、覆盖核心维度
- **T2 方案型**：验收=至少2个可行方案 + 明确优劣分析
- 以及模式→交付物映射、质量底线清单、专家协同标准

---

## 三、配置文件职责

### 3.1 analysis_frameworks.yaml
**文件**: [intelligent_project_analyzer/config/analysis_frameworks.yaml](intelligent_project_analyzer/config/analysis_frameworks.yaml) — 310行

**声明式框架注册表**。框架选择权交给LLM（project_director），配置定义知识边界。

已注册框架（P0核心）：
- **ability_core**: 12 Ability Core 全维度分析框架
  - `trigger_modes`: [M1, M2, M3, M5, M6, M8, M9]
  - `knowledge_source`: `sf/12_Ability_Core`
  - `essentials_config`: `config/ability_core_essentials.yaml`
  - `layer_model`: `ability_core_5layer`
  - `dimensions`: A1–A12
- **multi_scale_integration**: 多尺度统筹框架（城市→室内→家具）

### 3.2 layer_models.yaml
**文件**: [intelligent_project_analyzer/config/layer_models.yaml](intelligent_project_analyzer/config/layer_models.yaml) — 374行

定义每个框架的 **纵深递进层结构**。核心模型 `ability_core_5layer`：

| 层 | 名称 | 写作指令摘要 | 字数上限 |
|----|------|-------------|---------|
| L1_phenomenon | 表象层: 看到什么 | 具体感官描述，避免主观评价 | 200 |
| L2_strategy | 策略层: 设计师的意图 | 策略权衡(A而非B)，约束分析 | 250 |
| L3_mechanism | 机制层: 如何运作 | 因果链，引用原理 | 300 |
| L4_critique | 批判层: 局限与代价 | — | — |
| L5_evolution | 演化层: 下一步可能 | — | — |

### 3.3 ability_core_essentials.yaml
**文件**: [intelligent_project_analyzer/config/ability_core_essentials.yaml](intelligent_project_analyzer/config/ability_core_essentials.yaml) — 215行

来源 sf/12_Ability_Core 的**精华提取**。每个能力包含：
- `essence`: 能力本质（一句话）
- `maturity_L4`: L4成熟度描述
- `highest_form`: 最高形态
- `judgment_criteria`: 判断标准（列表）
- `common_mistakes`: 常见误区（列表）

**使用方**: `core_task_decomposer.py`（能力注入增强块）、`sf_knowledge_loader.py`

### 3.4 mode_ability_activation.yaml
**文件**: [intelligent_project_analyzer/config/mode_ability_activation.yaml](intelligent_project_analyzer/config/mode_ability_activation.yaml) — 305行

**Mode × Ability 1:N 激活矩阵**。取代旧的 1:1 映射。

每个模式定义：
- `primary_abilities`: 核心能力（目标 L4），直接注入专家 prompt
- `secondary_abilities`: 次要能力（目标 L3），建议激活

示例 M1_concept_driven：
- Primary: A1_concept_architecture(L4), A3_narrative_orchestration(L4)
- Secondary: A12_civilizational_expression(L3), A2_spatial_structuring(L3)

### 3.5 MODE_HYBRID_PATTERNS.yaml
**文件**: [config/MODE_HYBRID_PATTERNS.yaml](config/MODE_HYBRID_PATTERNS.yaml) — 794行

**多模式共存时的冲突解决策略**：
- 检测阈值: `min_confidence: 0.45`, `max_confidence_gap: 0.25`
- 四种解决策略: priority_based / balanced / zoned / phased
- 预定义模式组合冲突分析（如 M1×M4: 精神表达 vs 成本控制）

---

## 四、数据流追踪：State Key 写入与消费

### Stage 1: requirements_analyst 节点 — 模式检测

**写入节点**: `_requirements_analyst_node`
**文件/行号**:
- 模式检测调用: [requirements_analyst_agent.py](intelligent_project_analyzer/agents/requirements_analyst_agent.py#L298-L333)（Phase1 内部）
- State 写入: [main_workflow.py](intelligent_project_analyzer/workflow/main_workflow.py#L544-L622)

**检测流程**:
1. `HybridModeDetector.detect_sync()` ([mode_detector.py](intelligent_project_analyzer/services/mode_detector.py#L582-L613))
   - 关键词快速检测 → `DesignModeDetector.detect()`
   - 返回 `[{"mode": str, "confidence": float, "reason": str, "detected_by": "keyword"}, ...]`
2. Phase1 节点将结果写入内部 state: `detected_design_modes` ([requirements_analyst_agent.py L418](intelligent_project_analyzer/agents/requirements_analyst_agent.py#L418))
3. Phase2 节点读取 Phase1 结果，透传 `detected_design_modes` ([requirements_analyst_agent.py L458-L542](intelligent_project_analyzer/agents/requirements_analyst_agent.py#L458-L542))

**写入的 State Keys**:
| Key | 类型 | 写入位置 |
|-----|------|---------|
| `detected_design_modes` | `List[Dict]` | [main_workflow.py L622](intelligent_project_analyzer/workflow/main_workflow.py#L622) |
| `project_classification` | `Dict` | [main_workflow.py L623](intelligent_project_analyzer/workflow/main_workflow.py#L623) |
| `structured_requirements` | `Dict` | [main_workflow.py L620](intelligent_project_analyzer/workflow/main_workflow.py#L620) |

`project_classification` 字段聚合了 ([main_workflow.py L601-L608](intelligent_project_analyzer/workflow/main_workflow.py#L601-L608)):
```python
{
    "project_type": str,
    "primary_mode": str,          # detected_design_modes[0]["mode"]
    "secondary_modes": List[str], # [1:3]
    "mode_confidence": float,
    "motivation_type": str,
    "detected_design_modes": list, # 完整原始数据
}
```

---

### Stage 2: project_director 节点 — 框架选择 + 模式任务注入

**文件**: [intelligent_project_analyzer/agents/project_director.py](intelligent_project_analyzer/agents/project_director.py#L600-L1000)

**读取的 State Keys**: `detected_design_modes`, `confirmed_core_tasks`

**关键操作**:

1. **模式任务注入** (v7.700 P0, [L612-L653](intelligent_project_analyzer/agents/project_director.py#L612-L653)):
   - 调用 `ModeTaskLibrary.get_mandatory_tasks_for_modes(detected_modes)` 获取必需任务
   - 将模式必需任务合并到 `confirmed_core_tasks`
   - 每个注入任务带 `source: "mode_library"`, `source_mode: ...`

2. **模式任务覆盖率验证** (v7.700 P0, [L937-L980](intelligent_project_analyzer/agents/project_director.py#L937-L980)):
   - `ModeTaskLibrary.validate_task_coverage(detected_modes, allocated_tasks)`
   - 结果存入 `strategic_analysis.mode_task_coverage`

**写入的 State Keys**:
| Key | 写入位置 |
|-----|---------|
| `strategic_analysis` | [L983-L990](intelligent_project_analyzer/agents/project_director.py#L983-L990) |
| `execution_batches` | [L1001](intelligent_project_analyzer/agents/project_director.py#L1001) |
| `subagents` | [L996](intelligent_project_analyzer/agents/project_director.py#L996) |

> **注意**: 当前版本的 `project_director` **不显式写入 `analysis_framework_id`** 到 State。框架选择的显式设置路径（`state["analysis_framework_id"]`）目前是预留设计，实际框架检测在 `result_aggregator` 中回退触发。

---

### Stage 3: core_task_decomposer — 能力标签生成

**文件**: [intelligent_project_analyzer/services/core_task_decomposer.py](intelligent_project_analyzer/services/core_task_decomposer.py#L1065-L1130)

**读取**: `structured_data.detected_design_modes`

**关键操作** (阶段1增强, [L1065-L1130](intelligent_project_analyzer/services/core_task_decomposer.py#L1065-L1130)):
1. 加载 `mode_ability_activation.yaml` + `ability_core_essentials.yaml`
2. 遍历检测到的模式（`confidence ≥ 0.5`），提取 `primary_abilities`
3. 为每个能力构建注入段落，包含：
   - Focus 描述
   - 判断标准（前2条，来自 essentials）
   - 常见误区（前2条，来自 essentials）
   - 最高形态（来自 essentials）
4. 将注入段落**前置**到 `user_prompt`，强制 LLM 为每个能力生成深度任务

**注入格式**:
```
## 🎯 能力激活约束（来自 Mode×Ability 矩阵 + Ability Core 5层模型）
[M5_rural_context] 必须为以下能力各生成至少1个深度任务:
  - A9_social_structure_modeling（识别社区权力结构...）
    ✓ 判断标准: 是否识别了社区中的关键决策者？ / ...
    ✗ 避免: 把村民当成同质群体 / ...
    ★ 最高形态: 社会关系成为空间组织的生成逻辑
⚠️ 任务列表中必须体现上述每个能力的深度判断标准...
```

**写入**: 生成的任务列表中每个任务可能带 `ability_tag` 字段（由 LLM 响应决定）

---

### Stage 4: batch_executor → Expert Factory 能力注入

**文件**: [intelligent_project_analyzer/agents/task_oriented_expert_factory.py](intelligent_project_analyzer/agents/task_oriented_expert_factory.py)

batch_executor 内部调用 `TaskOrientedExpertFactory` ([main_workflow.py L1240-L1466](intelligent_project_analyzer/workflow/main_workflow.py#L1240-L1466))。每次执行专家时，在构建 prompt 阶段进行两层注入：

#### 4.1 `_inject_mode_capabilities` ([L1658-L1800](intelligent_project_analyzer/agents/task_oriented_expert_factory.py#L1658-L1800))

**读取**: `state["detected_design_modes"]`

**机制**:
1. **旧路 1:1 注入** (L1682-L1755): 加载 `ability_injections.yaml`，基于 `mode_id` → `target_experts` 匹配，注入 `prompt_injection` 文本
2. **新路 1:N 激活** (L1758+): 加载 `mode_ability_activation.yaml`
   - 遍历检测模式（置信度 ≥ 0.5）
   - 提取 `primary_abilities` → 构建 `[模式本质]\n核心能力要求:\n- A1(L4/focus)` 段落
   - 合并后追加到 `base_system_prompt`

**输出**: 修改后的 `base_system_prompt`（追加能力指令段落）

#### 4.2 `_inject_sf_knowledge` ([L1803-L1865](intelligent_project_analyzer/agents/task_oriented_expert_factory.py#L1803-L1865))

**读取**: `state["detected_design_modes"]`, `role_object.task_instruction.analysis_framework`, `role_object.task_instruction.ability_tags`

**机制**:
1. **v9.0 框架感知路径**：如果 `task_instruction` 含 `framework_id` 或 `ability_tags`：
   - 调用 `get_framework_knowledge_injection(framework_id, ability_tags, detected_modes)`
   - 这会组装:
     - 层写作指令（来自 `layer_models.yaml` → `ability_core_5layer`）
     - 能力维度精华（来自 `ability_core_essentials.yaml`，仅匹配 `ability_tags`）
     - 经典评估+输出标准（来自 `sf/13_Evaluation_Matrix` + `sf/14_Output_Standards`）
2. **回退路径**：调用 `get_full_knowledge_injection(detected_modes)`
   - 注入 sf/13 的模式评估权重 + sf/14 的交付物标准

**输出**: 追加到 `base_system_prompt` 的知识文本

**sf_knowledge_loader.py 中的 `get_framework_knowledge_injection`** ([L603-L660](intelligent_project_analyzer/services/sf_knowledge_loader.py#L603-L660)):
```python
def get_framework_knowledge_injection(framework_id, ability_tags, detected_modes):
    sections = []
    sections.append(get_layer_writing_instructions(framework_id))  # 5层写作指令
    if ability_tags:
        for tag in ability_tags:
            sections.append(get_ability_injection(tag))            # 单能力精华
    if detected_modes:
        sections.append(get_full_knowledge_injection(detected_modes)) # sf/13+14
    return "\n\n---\n\n".join(sections)
```

---

### Stage 5: result_aggregator — 框架感知聚合

**文件**: [intelligent_project_analyzer/report/result_aggregator.py](intelligent_project_analyzer/report/result_aggregator.py)

#### 5.1 `_detect_analysis_framework` ([L1178-L1216](intelligent_project_analyzer/report/result_aggregator.py#L1178-L1216))

**检测优先级**:
1. `state["analysis_framework_id"]` — 由 project_director 显式设置（当前未使用）
2. `state["strategic_analysis"]["analysis_framework"]` — 从战略分析推断（当前未使用）
3. 遍历 `agent_results` → 检查 `structured_output.task_execution_report.deliverable_outputs[].ability_tag` — 如果任何交付物带 ability_tag → 返回 `"ability_core"`
4. `state["detected_design_modes"]` 非空 → 回退返回 `"ability_core"`

**实际行为**: 只要有模式检测结果，就返回 `"ability_core"`。

#### 5.2 `_build_framework_instructions` ([L1219-L1300](intelligent_project_analyzer/report/result_aggregator.py#L1219-L1300))

**读取**: `analysis_frameworks.yaml`, `layer_models.yaml`, `ability_core_essentials.yaml`

**构建内容**:
1. 框架名称、说明、维度列表
2. 层写作指令（来自 `get_layer_writing_instructions`）
3. （当 framework_id = "ability_core"）`ability_core_matrix` 填充规则 — JSON schema 示例 + 填充策略指令

**注入位置**: [L663-L667](intelligent_project_analyzer/report/result_aggregator.py#L663-L667):
```python
analysis_framework_id = self._detect_analysis_framework(state)
if analysis_framework_id:
    framework_instruction_section = self._build_framework_instructions(
        analysis_framework_id, state
    )
```
然后拼接到 human message 中 ([L676](intelligent_project_analyzer/report/result_aggregator.py#L676))：

```
{framework_instruction_section}

## 任务要求
...
6. **框架感知输出**（如果提供了框架指令）：
   - analysis_framework_id: 填写所使用的框架ID
   - ability_core_matrix: 当使用 ability_core 框架时，整合各专家的能力分析，构建12维能力矩阵
```

#### 5.3 LLM 输出结构 (Pydantic Schema)

[L482-L499](intelligent_project_analyzer/report/result_aggregator.py#L482-L499):
```python
class ProjectAnalysisReport(BaseModel):
    ...
    analysis_framework_id: Optional[str]       # 框架ID
    ability_core_matrix: Optional[Dict[str, Any]]  # 12维能力矩阵
```

---

### Stage 6: text_generator — 渲染 ability_core_matrix

**文件**: [intelligent_project_analyzer/report/text_generator.py](intelligent_project_analyzer/report/text_generator.py#L306-L450)

#### 6.1 入口 ([L306-L316](intelligent_project_analyzer/report/text_generator.py#L306-L316))
```python
ability_core_matrix = final_report.get("ability_core_matrix")
analysis_framework_id = final_report.get("analysis_framework_id")
if ability_core_matrix and isinstance(ability_core_matrix, dict):
    lines.append(f"能力矩阵分析（框架: {analysis_framework_id or 'ability_core'}）")
    lines.extend(self._render_ability_core_matrix(ability_core_matrix))
```

#### 6.2 `_render_ability_core_matrix` ([L346-L450](intelligent_project_analyzer/report/text_generator.py#L346-L450))

按 A1–A12 预定义顺序渲染每个能力维度：
```
### 能力一｜概念建构能力（A1_concept_architecture）
成熟度: L4

**L1 表象层: 看到什么**
<content>

**L2 策略层: 设计师的意图**
<content>

**L3 机制层: 如何运作**
<content>

**L4 批判层: 局限与代价**
<content>

**L5 演化层: 下一步可能**
<content>

风险/局限: <risk_notes>
---
```

最后附成熟度总览表。

---

## 五、完整数据流图谱

```
┌─────────────────────────────────────────────────────────────────────┐
│                     State Key 写入/消费关系                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  requirements_analyst                                               │
│  ├─ 写入: detected_design_modes          ←── HybridModeDetector    │
│  ├─ 写入: project_classification                                    │
│  └─ 写入: structured_requirements                                   │
│       │                                                             │
│       ▼                                                             │
│  feasibility_analyst (读取上述, 不修改方法论字段)                      │
│       │                                                             │
│       ▼                                                             │
│  progressive_questionnaire (3步, 读取 detected_design_modes         │
│       │                     用于模式感知问题生成)                     │
│       │                                                             │
│       ▼                                                             │
│  project_director                                                   │
│  ├─ 读取: detected_design_modes                                     │
│  ├─ 读取: confirmed_core_tasks                                      │
│  ├─ 操作: ModeTaskLibrary.get_mandatory_tasks_for_modes()           │
│  ├─ 操作: inject mandatory tasks → confirmed_core_tasks             │
│  ├─ 操作: ModeTaskLibrary.validate_task_coverage()                  │
│  └─ 写入: strategic_analysis { mode_task_coverage }                 │
│       │                                                             │
│       ▼                                                             │
│  core_task_decomposer (在 project_director 内部调用)                 │
│  ├─ 读取: detected_design_modes (via structured_data)               │
│  ├─ 加载: mode_ability_activation.yaml                              │
│  ├─ 加载: ability_core_essentials.yaml                              │
│  └─ 操作: 构建 ability_injection prompt → 注入 user_prompt          │
│       │                                                             │
│       ▼                                                             │
│  batch_executor → TaskOrientedExpertFactory                         │
│  ├─ _inject_mode_capabilities()                                     │
│  │   ├─ 读取: state["detected_design_modes"]                       │
│  │   ├─ 加载: ability_injections.yaml (1:1映射)                     │
│  │   └─ 加载: mode_ability_activation.yaml (1:N激活)                │
│  │                                                                  │
│  ├─ _inject_sf_knowledge()                                          │
│  │   ├─ 读取: state["detected_design_modes"]                       │
│  │   ├─ 读取: role_object.task_instruction.{analysis_framework,     │
│  │   │                                      ability_tags}           │
│  │   ├─ v9.0路径: get_framework_knowledge_injection()               │
│  │   │   ├─ layer_models.yaml → 5层写作指令                         │
│  │   │   ├─ ability_core_essentials.yaml → 能力精华                  │
│  │   │   └─ sf/13 + sf/14 → 评估矩阵 + 输出标准                    │
│  │   └─ 回退路径: get_full_knowledge_injection(detected_modes)      │
│  │       └─ sf/13 + sf/14 → 评估+输出                              │
│  └─ 写入: agent_results[agent_id].structured_output                 │
│       │                                                             │
│       ▼                                                             │
│  result_aggregator                                                  │
│  ├─ _detect_analysis_framework(state)                               │
│  │   ├─ 优先级1: state["analysis_framework_id"]                    │
│  │   ├─ 优先级2: strategic_analysis["analysis_framework"]           │
│  │   ├─ 优先级3: agent_results 中任意 ability_tag → "ability_core"  │
│  │   └─ 优先级4: detected_design_modes 非空 → "ability_core"       │
│  ├─ _build_framework_instructions(framework_id, state)              │
│  │   └─ 构建: 框架名+维度+层写作指令+ability_core_matrix填充规则    │
│  └─ 写入到 LLM prompt → LLM 返回 {analysis_framework_id,          │
│                                     ability_core_matrix}            │
│       │                                                             │
│       ▼                                                             │
│  text_generator (pdf_generator内部)                                  │
│  ├─ 读取: final_report["ability_core_matrix"]                       │
│  ├─ 读取: final_report["analysis_framework_id"]                     │
│  └─ _render_ability_core_matrix() → 渲染 A1-A12 × L1-L5 文本      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 六、关键发现与注意事项

1. **framework_id 目前为隐式检测**：`project_director` 并未显式写入 `analysis_framework_id` 到 State，`result_aggregator._detect_analysis_framework()` 通过优先级回退链检测，最终几乎总是命中 `"ability_core"`（因为有 `detected_design_modes`）。

2. **Mode 检测仅为关键词级别**：`detect_sync()` 不调用 LLM，仅使用 `DesignModeDetector.detect()` 的关键词匹配。异步版本 `detect()` 才会调用 LLM，但 requirements_analyst Phase1 使用的是同步版本。

3. **ability_tags 注入链**：从 `core_task_decomposer` 生成带 `ability_tag` 的任务 → 存入 `role_object.task_instruction` → `_inject_sf_knowledge()` 读取 → 精准注入对应能力精华。但 `ability_tag` 的实际生成取决于 LLM 是否在 task decomposition 响应中返回该字段。

4. **sf/ 知识是三段式注入**：
   - **Task级**: core_task_decomposer 注入 ability 约束到任务生成 prompt
   - **Expert级**: expert_factory 注入 mode capabilities + sf knowledge 到专家 system prompt
   - **Aggregation级**: result_aggregator 注入框架指令到聚合 prompt

5. **层模型与框架解耦**: `layer_models.yaml` 的层结构可被多个框架复用，框架通过 `layer_model` 字段引用层模型名。
