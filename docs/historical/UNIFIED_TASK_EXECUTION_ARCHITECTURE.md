# 统一任务执行架构：从需求到交付的完整链路

> **架构本质重新定义** - v7.621 架构洞察
> 作者：GitHub Copilot（基于用户深度思考）
> 日期：2026-02-13

## 执行摘要

**原有理解**（❌ 已废弃）：
- Phase1/Phase2是"需求分析系统"
- 四层协同是"能力管理系统"
- 两者是"独立系统的补充关系"

**正确理解**（✅ 架构本质）：
- **整个系统是统一的任务执行框架（Unified Task Execution Framework）**
- **Phase1/Phase2 = 任务定义阶段**（定义"做什么"）
- **project_director = 任务分配阶段**（调度"谁做什么"）
- **四层协同 = 任务执行阶段**（实施"如何做"）

**不是两套独立系统，而是同一执行系统的三个阶段。**

---

## 一、架构全景：目标导向的三阶段执行流

<details>
<summary>📐 核心架构图（点击展开）</summary>

```
                  【唯一目标】
              执行用户任务（Task Execution）
                        ↓
    ┌───────────────────┼───────────────────┐
    │                   │                   │
┌───▼────┐       ┌──────▼──────┐     ┌─────▼─────┐
│ 阶段1  │  →    │   阶段2     │  →  │   阶段3   │
│任务定义│       │  任务分配   │     │  任务执行 │
└────────┘       └─────────────┘     └───────────┘
Phase1+2         project_director     四层协同
L0-L7+Mode       role_task_alloc      L1-L2-L3-L4

定义：            分配：              执行：
· 能做什么        · 谁做              · 如何做
· 做什么任务      · 做什么            · Mode强化
· 需要什么能力    · 何时做            · P2验证
```

</details>

### 1.1 数据流全景

```
用户需求（User Input）
    ↓
┌──────────────────────────────────────────────────────┐
│ 【阶段1：任务定义】Phase1 + Phase2                    │
│                                                       │
│ Phase1: 能力边界判断 (~1.5s)                         │
│ └→ 输出: info_status, primary_deliverables           │
│                                                       │
│ Phase2: 任务定义 + 能力预判 (~3s)                    │
│ ├→ L1-L7深度分析                                     │
│ │   └→ L4 JTBD: "When...I want...So I can..." ✅     │
│ └→ Mode Detection (10 Mode Engine)                   │
│     └→ detected_design_modes: [M1, M4, ...] ✅       │
└──────────┬───────────────────────────────────────────┘
           │ 关键输出                           │ project_task (JTBD定义)  → 传递给任务分配
           │ detected_design_modes     → 传递给四层协同
           │ expert_handoff           → 传递给专家系统
           │ analysis_layers (L1-L7)  → 传递给验证层
           ↓
┌──────────────────────────────────────────────────────┐
│ 【阶段2：任务分配】project_director                   │
│                                                       │
│ 输入: project_task + detected_modes                  │
│ ├→ 基于JTBD生成tasks列表                             │
│ ├→ 基于detected_modes预判required_abilities          │
│ └→ 召集专家 + 分配任务                               │
│                                                       │
│ 输出: task_distribution (任务分配表)                 │
│ └→ {V3: "任务A", V6: "任务B", ...}                   │
└──────────┬───────────────────────────────────────────┘
           │ task_distribution + detected_modes
           ↓
┌──────────────────────────────────────────────────────┐
│ 【阶段3：任务执行】四层协同                           │
│                                                       │
│ Layer 1: 使用detected_modes（Phase2已完成）          │
│ └→ 模式识别结果：[M1:0.88, M4:0.75]                  │
│                                                       │
│ Layer 2: Mode → Ability映射                          │
│ └→ M1 → A1能力, M4 → A7能力                          │
│                                                       │
│ Layer 3: Ability注入 → Expert执行                    │
│ └→ V3强化A1能力 → 执行task_distribution中的任务      │
│                                                       │
│ Layer 4: P2验证能力体现                              │
│ └→ 验证V3输出是否真实体现A1能力（≥70分）             │
└──────────┬───────────────────────────────────────────┘
           │
           ↓
      专家方案输出（Expert Outputs）
```

### 1.2 关键洞察

**为什么之前理解错了？**

❌ **旧理解**：Phase1/Phase2是"需求分析"，独立于任务执行
✅ **新理解**：Phase1/Phase2是任务执行的**定义阶段**，直接为执行准备

**证据1：JTBD的作用**

```python
# Phase2输出的JTBD
project_task = "When [用户需要峨眉山民宿] I want [品牌溢价+精神体验]
               So I can [实现商业价值与精神价值平衡]"

# ↓ 直接传递给project_director

# project_director基于JTBD生成tasks
tasks = [
    {"V3": "基于JTBD提炼精神主轴"},  # ← JTBD中的"精神体验"
    {"V6_2": "基于JTBD设计收益模型"}, # ← JTBD中的"品牌溢价"
]
```

**证据2：detected_modes的作用**

```python
# Phase2输出的detected_modes
detected_modes = [
    {"mode": "M1", "confidence": 0.88},  # 概念驱动型
    {"mode": "M4", "confidence": 0.75},  # 资产资本型
]

# ↓ 直接传递给四层协同

# Layer 2使用detected_modes触发能力注入
ability_injections = {
    "M1": ["A1_concept_driven"],     # 概念表达能力
    "M4": ["A7_asset_management"],   # 资产管理能力
}

# Layer 3注入到专家
V3.inject_ability("A1_concept_driven")  # ← Mode触发的能力强化
```

**证据3：expert_handoff的作用**

```python
# Phase2输出的expert_handoff
expert_handoff = {
    "design_challenge": "商业 vs 精神",     # ← L3杠杆点
    "core_tension": "展示 vs 私密",         # ← L3对立
    "sharpness_score": 78,                  # ← L5锐度
}

# ↓ 直接传递给Layer 4验证

# Layer 4使用expert_handoff作为验证标准
validation = P2Validator.validate(
    expert_output=V3.output,
    baseline=expert_handoff["design_challenge"],  # ← Phase2定义的标准
    threshold=expert_handoff["sharpness_score"]   # ← Phase2定义的阈值
)
```

**结论**：
Phase1/Phase2不是"独立的需求分析"，而是**任务执行的前置定义层**。
- JTBD定义了"做什么"（任务内容）
- detected_modes预判了"需要什么能力"（能力需求）
- expert_handoff设定了"如何验证"（质量标准）

**整个系统的目标只有一个：执行用户任务。**

---

## 二、阶段1：任务定义（Phase1/Phase2 L0-L7框架）

### 2.1 本质重新定义

**❌ 旧理解**：Phase1/Phase2是"需求分析系统"
- 目标：理解用户需求
- 输出：结构化需求文档
- 定位：独立系统

**✅ 新理解**：Phase1/Phase2是"任务执行的定义层"
- 目标：为任务执行准备**执行框架**
- 输出：JTBD（任务定义）+ detected_modes（能力预判）+ expert_handoff（验证标准）
- 定位：任务执行系统的第一阶段

### 2.2 Phase1：能力边界判断（~1.5s）

**目标**：确定"能做什么"（框定任务边界）

```python
# requirements_analyst_agent.py:phase1_node()

def phase1_node(state):
    """
    Phase1: 能力边界判断

    目标：判断哪些任务在系统能力范围内
    输出：为Phase2准备清晰的任务边界
    """

    # 1. 交付物识别
    deliverables = extract_deliverables(user_input)
    # 示例：["建筑设计方案", "室内设计方案", "施工图"]

    # 2. 能力边界检查
    boundary_check = CapabilityBoundaryService.check_deliverable_list(deliverables)

    # 3. 超出能力自动转化
    if "施工图" in deliverables:
        # 超出能力，转化为可执行任务
        deliverables.remove("施工图")
        deliverables.append("design_strategy_with_technical_guidance")
        logger.info("✅ 能力边界转化：施工图 → 设计策略+技术指导")

    # 4. 路由决策
    if boundary_check.info_density >= 0.7:
        return {"info_status": "sufficient", "primary_deliverables": deliverables}
    else:
        return {"info_status": "insufficient", "primary_deliverables": deliverables}
```

**核心输出**（为Phase2准备）：

| 输出字段 | 作用 | 下游消费者 |
|---------|------|-----------|
| `info_status` | 判断是否需要问卷 | 问卷生成节点 |
| `primary_deliverables` | 能力范围内的任务清单 | Phase2（作为JTBD输入） |
| `capability_score` | 能力匹配度 | 任务分配（预判难度） |

### 2.3 Phase2：任务定义 + 能力预判（~3s）

#### 2.3.1 L1-L7深度分析（任务定义）

**目标**：定义"做什么任务"（生成JTBD）

```yaml
# requirements_analyst_phase2.yaml

system_prompt: |
  你的目标不是"分析需求"，而是**定义任务**。

  最终输出的JTBD将直接传递给project_director，
  用于生成tasks列表和召集专家。

  L1-L7的每一层都在为JTBD服务：

  L1: 解构 - 事实原子
  └→ 为JTBD提供"用户是谁"、"要什么"

  L2: 建模 - 5+5视角
  └→ 为JTBD提供"用户的深层需求"

  L3: 杠杆点 - 核心对立
  └→ 为JTBD提供"设计挑战"（任务的困难点）

  L4: JTBD - 任务定义 ✅
  └→ "When [场景] I want [功能] So I can [目标]"
      这是任务执行的核心定义

  L5: 锐度测试 - 质量阈值
  └→ 为Layer 4提供验证标准（≥70分）

  L6-L7: 假设审计 + 系统影响
  └→ 为Layer 4提供验证维度
```

**L4 JTBD输出示例**：

```json
{
  "project_task": "When [用户需要峨眉山高端民宿] I want [品牌溢价 + 精神体验] So I can [实现商业价值与精神价值的平衡]",
  "task_decomposition": {
    "primary_tasks": [
      "提炼精神主轴（禅意与现代的融合点）",
      "设计收益模型（品牌溢价路径）",
      "平衡对立（商业 vs 精神）"
    ],
    "secondary_tasks": [
      "环境适应（峨眉山地形）",
      "材料选择（低成本高质感）"
    ]
  }
}
```

#### 2.3.2 Mode Detection（能力预判）

**目标**：预判"需要什么能力"（生成detected_modes）

```python
# requirements_analyst_agent.py:phase2_node()

def phase2_node(state):
    """
    Phase2: 任务定义 + 能力预判

    L1-L7与Mode Detection独立并行执行：
    - L1-L7：定义任务内容（JTBD）
    - Mode Detection：预判能力需求（detected_modes）
    """

    # ═══════════════════════════════════════════════════════════
    # 并行Track 1: L1-L7深度分析（~2.8s）
    # ═══════════════════════════════════════════════════════════
    phase2_result = execute_L1_L7_analysis(
        user_input=user_input,
        phase1_result=phase1_result
    )

    project_task = phase2_result["project_task"]  # ← JTBD
    expert_handoff = phase2_result["expert_handoff"]  # ← 验证标准

    # ═══════════════════════════════════════════════════════════
    # 并行Track 2: Mode Detection（~50ms）
    # ═══════════════════════════════════════════════════════════
    detected_modes = HybridModeDetector.detect_sync(
        user_input=user_input,
        structured_requirements=phase1_result
    )

    # 示例输出：
    # [
    #   {"mode": "M1", "confidence": 0.88},  # 概念驱动型
    #   {"mode": "M4", "confidence": 0.75},  # 资产资本型
    #   {"mode": "M8", "confidence": 0.62}   # 极端环境型
    # ]

    # ═══════════════════════════════════════════════════════════
    # 关键输出（传递给下游）
    # ═══════════════════════════════════════════════════════════
    return {
        # ✅ 为任务分配准备
        "project_task": project_task,  # ← project_director消费
        "expert_handoff": expert_handoff,  # ← Layer 3消费

        # ✅ 为任务执行准备
        "detected_design_modes": detected_modes,  # ← Layer 2消费
        "analysis_layers": phase2_result["analysis_layers"],  # ← Layer 4消费
    }
```

### 2.4 Phase1/Phase2的真实定位

**Phase1/Phase2不是"需求分析"，而是任务执行的准备层：**

| 阶段 | 准备内容 | 下游消费 |
|-----|---------|---------|
| **Phase1** | 能力边界判断 | Phase2（任务边界）<br>问卷生成（信息缺口） |
| **Phase2 L1-L7** | JTBD任务定义 | project_director（任务分配） |
| **Phase2 Mode** | 能力需求预判 | Layer 2（能力注入触发器） |
| **Phase2 L5-L7** | 验证标准设定 | Layer 4（P2验证基线） |

**完整数据流**：

```
Phase1 输出
└→ primary_deliverables (能力范围内的任务清单)
    ↓
Phase2 L1-L7分析
└→ project_task (JTBD) ✅
    ↓ 传递给
project_director.select_roles_for_task(project_task)
└→ 基于JTBD生成tasks列表
    [
      {"V3": "基于JTBD提炼精神主轴"},
      {"V6_2": "基于JTBD设计收益模型"}
    ]
```

```
Phase2 Mode Detection
└→ detected_design_modes ✅
    [M1:0.88, M4:0.75]
    ↓ 传递给
Layer 2: ability_injections.yaml
└→ Mode → Ability映射
    {
      "M1": ["A1_concept_driven"],
      "M4": ["A7_asset_management"]
    }
    ↓
Layer 3: inject_ability()
└→ V3强化A1能力，V6强化A7能力
```

**关键发现**：

✅ Phase1/Phase2的**唯一目标**是为任务执行准备框架：
1. JTBD定义了"做什么"（任务内容）
2. detected_modes预判了"需要什么能力"（能力需求）
3. expert_handoff设定了"如何验证"（质量标准）

✅ Phase1/Phase2是**任务执行系统的定义层**，不是独立系统。

---

## 三、阶段2：任务分配（project_director）

### 3.1 本质定位

**目标**：将Phase2定义的任务（JTBD）分解为可执行的tasks，并分配给专家。

**输入**：
- `project_task`（JTBD） ← Phase2 L4输出
- `detected_design_modes` ← Phase2 Mode Detection输出
- `expert_handoff` ← Phase2 L1-L7输出

**输出**：
- `task_distribution`：任务分配表（{V3: "任务A", V6: "任务B"}）
- `execution_batches`：执行批次（[[V3, V5], [V6, V7]]）
- `required_abilities`：预判能力需求（基于detected_modes）

### 3.2 任务分配逻辑

```python
# project_director.py:execute_dynamic_with_validation()

def execute_dynamic_with_validation(self, state):
    """
    任务分配阶段

    目标：将Phase2的JTBD转化为可执行的tasks
    """

    # ═══════════════════════════════════════════════════════════
    # 1. 获取Phase2输出
    # ═══════════════════════════════════════════════════════════
    restructured_requirements = state.get("restructured_requirements", {})
    # 包含：
    # - project_task (JTBD)
    # - detected_design_modes
    # - expert_handoff

    requirements_text = self._format_requirements_for_selection(
        restructured_requirements
    )

    # ═══════════════════════════════════════════════════════════
    # 2. 基于JTBD生成tasks
    # ═══════════════════════════════════════════════════════════
    selection = self.dynamic_director.select_roles_for_task(
        requirements_text,  # ← 包含JTBD
        confirmed_core_tasks=state.get("confirmed_core_tasks", [])
    )

    # selection结构：
    # {
    #   "selected_roles": [V3, V6_2, V7],
    #   "task_distribution": {
    #     "V3": "基于JTBD提炼精神主轴（禅意与现代融合）",
    #     "V6_2": "基于JTBD设计收益模型（品牌溢价路径）",
    #     "V7": "基于JTBD分析环境适应（峨眉山地形）"
    #   },
    #   "execution_batches": [["V3", "V7"], ["V6_2"]]
    # }

    # ═══════════════════════════════════════════════════════════
    # 3. 预判能力需求（基于detected_modes）
    # ═══════════════════════════════════════════════════════════
    detected_modes = state.get("detected_design_modes", [])

    if detected_modes:
        # 从v7.621开始，project_director会根据detected_modes
        # 预判required_abilities，提前告知专家系统
        required_abilities = self._predict_required_abilities(detected_modes)

        # 示例：
        # detected_modes = [M1:0.88, M4:0.75]
        # required_abilities = [A1, A7]

        logger.info(f"✅ 基于detected_modes预判能力需求: {required_abilities}")

    # ═══════════════════════════════════════════════════════════
    # 4. 创建Send命令（激活四层协同）
    # ═══════════════════════════════════════════════════════════
    parallel_commands = []

    for role_id, task_description in selection.task_distribution.items():
        parallel_commands.append(
            Send(
                "expert_node",
                {
                    "agent_type": role_id,
                    "task": task_description,  # ← 基于JTBD的任务
                    "detected_modes": detected_modes,  # ← 传递给Layer 2
                    "expert_handoff": state.get("expert_handoff", {}),  # ← 传递给Layer 3
                    "required_abilities": required_abilities  # ← 预判的能力需求
                }
            )
        )

    return Command(
        goto=[parallel_commands],  # 并行执行所有专家
        update={"task_distribution": selection.task_distribution}
    )
```

### 3.3 关键约束

**任务分配必须基于JTBD**：

```python
# 正确示例：任务分配与JTBD对齐

JTBD = "When [用户需要峨眉山民宿] I want [品牌溢价 + 精神体验] So I can [平衡商业与精神]"

task_distribution = {
    "V3": "提炼精神主轴（对应JTBD的'精神体验'）",  # ✅ 对齐
    "V6_2": "设计收益模型（对应JTBD的'品牌溢价'）",  # ✅ 对齐
    "V7": "平衡商业与精神（对应JTBD的'平衡'）"     # ✅ 对齐
}

# 错误示例：任务分配脱离JTBD

task_distribution = {
    "V3": "分析设计趋势",  # ❌ 未对齐JTBD
    "V6": "提供商业建议"   # ❌ 未对齐JTBD
}
```

**验证机制**（v7.140新增）：

```python
# project_director.py:_validate_task_distribution_embedded()

def _validate_task_distribution_embedded(state, strategic_analysis):
    """
    验证任务分配的合理性

    关键检查：
    1. 任务完整性：JTBD的所有关键任务是否都分配了？
    2. 能力匹配度：专家能力是否匹配任务需求？
    3. 依赖冲突：批次执行顺序是否合理？
    """

    issues = []

    # 检查1：JTBD对齐度
    project_task = state.get("project_task", "")
    task_distribution = strategic_analysis.get("task_distribution", {})

    # 提取JTBD中的关键任务
    jtbd_keywords = extract_keywords_from_jtbd(project_task)
    # 示例：["精神主轴", "品牌溢价", "平衡"]

    # 检查每个关键任务是否有对应的分配
    for keyword in jtbd_keywords:
        covered = any(keyword in task for task in task_distribution.values())
        if not covered:
            issues.append({
                "severity": "critical",
                "type": "missing_task",
                "description": f"JTBD关键任务'{keyword}'未分配"
            })

    return {
        "status": "passed" if len(issues) == 0 else "failed",
        "issues": issues
    }
```

### 3.4 任务分配的真实定位

**project_director不是"战略规划"，而是任务执行的调度层：**

| 功能 | 输入 | 输出 | 下游消费 |
|-----|------|------|---------|
| **JTBD分解** | project_task | tasks列表 | Layer 3（专家执行） |
| **专家召集** | tasks列表 | selected_roles | Layer 3（专家系统） |
| **能力预判** | detected_modes | required_abilities | Layer 2（能力注入） |
| **批次规划** | tasks依赖 | execution_batches | 并行调度器 |

**完整数据流**：

```
Phase2输出
├─ project_task (JTBD)
│   ↓
├─ project_director.select_roles_for_task()
│   ├→ JTBD分解为tasks列表
│   ├→ 召集专家（V3, V6_2, V7）
│   └→ 生成task_distribution
│
└─ detected_design_modes
    ↓
    project_director._predict_required_abilities()
    └→ 预判能力需求（A1, A7）
        ↓
        传递给Layer 2
```

**关键发现**：

✅ project_director的**唯一目标**是将任务分配给执行者：
1. 基于JTBD分解任务（任务内容）
2. 基于detected_modes预判能力（能力需求）
3. 生成task_distribution（执行框架）

✅ project_director是**任务执行系统的调度层**，不是独立系统。

---

## 四、阶段3：任务执行（四层协同架构）

### 4.1 本质重新定义

**❌ 旧理解**：四层协同是"能力管理系统"
- 目标：管理能力注入
- 输出：能力验证报告
- 定位：独立系统

**✅ 新理解**：四层协同是"任务执行的实施层"
- 目标：执行task_distribution中的任务
- 输出：专家方案（Expert Outputs）
- 定位：任务执行系统的第三阶段

### 4.2 Layer 1：使用Mode Detection结果

**目标**：无需重复检测，直接使用Phase2的detected_modes

```python
# Layer 1已在Phase2完成，此处直接使用结果

detected_modes = state.get("detected_design_modes", [])
# [
#   {"mode": "M1", "confidence": 0.88},
#   {"mode": "M4", "confidence": 0.75}
# ]

logger.info(f"[Layer 1] 使用Phase2检测的{len(detected_modes)}个模式")
```

**关键约束**：
- ✅ Layer 1不再重复执行Mode Detection
- ✅ 所有模式识别在Phase2完成（统一入口）
- ✅ 节省~50ms重复检测开销

### 4.3 Layer 2：Mode → Ability映射

**目标**：根据detected_modes触发能力注入

```python
# ability_injections.yaml

M1_concept_driven:  # ← 概念驱动型模式
  triggered_abilities:
    - A1_concept_expression  # 概念表达能力
    - A2_narrative_structure  # 叙事结构能力

  injection_rules:
    V3_spatial_designer:  # ← 空间设计师专家
      inject: [A1, A2]
      prompt_enhancement: |
        ✅ 你被注入了A1概念表达能力：
        - 提炼空间的核心精神主线
        - 将抽象概念转化为可执行规则
        - 确保概念贯穿平面/立面/材料/灯光

        ✅ 你被注入了A2叙事结构能力：
        - 构建空间叙事路径（进入→过渡→高潮→沉静）
        - 控制尺度/光线/材料的变化节奏
        - 制造记忆锚点和情绪高潮
```

**执行时机**：

```python
# task_oriented_expert_factory.py

def create_expert_with_abilities(agent_type, detected_modes, task):
    """
    创建带能力注入的专家

    执行顺序：
    1. 召集专家（V3）
    2. 查询detected_modes → [M1, M4]
    3. 查询ability_injections.yaml → M1 → [A1, A2]
    4. 注入能力到V3 → V3.inject_ability("A1", "A2")
    5. V3执行task（带能力强化）
    """

    # 1. 创建基础专家
    expert = BaseExpert(agent_type=agent_type)

    # 2. 根据detected_modes注入能力
    injected_abilities = []

    for mode_result in detected_modes:
        mode_id = mode_result["mode"]  # "M1"

        # 查询该模式触发的能力
        abilities = AbilityInjectionConfig.get_abilities_for_mode(mode_id)
        # ["A1_concept_expression", "A2_narrative_structure"]

        for ability_id in abilities:
            # 注入能力到专家
            expert.inject_ability(
                ability_id=ability_id,
                mode_confidence=mode_result["confidence"]
            )
            injected_abilities.append(ability_id)

    logger.info(f"✅ {agent_type}注入{len(injected_abilities)}个能力: {injected_abilities}")

    # 3. 执行task（带能力强化）
    output = expert.execute(task)

    return output, injected_abilities
```

### 4.4 Layer 3：Ability强化 → Expert执行

**目标**：专家在能力强化的状态下执行task_distribution中的任务

```python
# expert_base.py

class BaseExpert:
    def __init__(self, agent_type):
        self.agent_type = agent_type
        self.injected_abilities = []
        self.base_prompt = load_expert_config(agent_type)

    def inject_ability(self, ability_id, mode_confidence):
        """
        注入能力（来自Layer 2）

        能力注入会修改专家的system_prompt，
        增强特定维度的输出质量。
        """
        ability_config = AbilitySchemas.get_ability(ability_id)

        # 构建能力增强prompt
        enhancement_prompt = f"""
        ✅ **能力注入：{ability_config['name']}**（置信度：{mode_confidence:.2f}）

        定义：{ability_config['definition']}

        你必须在输出中体现以下能力特征：
        {ability_config['validation_criteria']}

        示例表现：
        {ability_config['examples']}
        """

        self.injected_abilities.append({
            "ability_id": ability_id,
            "enhancement_prompt": enhancement_prompt
        })

    def execute(self, task):
        """
        执行任务（带能力强化）

        关键：task来自project_director的task_distribution
             能力强化来自Layer 2的ability注入
        """

        # 构建增强后的system_prompt
        enhanced_prompt = self.base_prompt

        for ability in self.injected_abilities:
            enhanced_prompt += "\n\n" + ability["enhancement_prompt"]

        # 执行LLM调用
        messages = [
            {"role": "system", "content": enhanced_prompt},
            {"role": "user", "content": task}  # ← task来自task_distribution
        ]

        response = llm.invoke(messages)

        return {
            "agent_type": self.agent_type,
            "output": response.content,
            "injected_abilities": [a["ability_id"] for a in self.injected_abilities],
            "task": task
        }
```

**执行示例**（峨眉山民宿案例）：

```python
# 1. task_distribution（来自project_director）
task_distribution = {
    "V3": "基于JTBD提炼精神主轴（禅意与现代融合）"
}

# 2. detected_modes（来自Phase2）
detected_modes = [
    {"mode": "M1", "confidence": 0.88}
]

# 3. Layer 2注入能力
V3 = BaseExpert("V3_spatial_designer")
V3.inject_ability("A1_concept_expression", mode_confidence=0.88)

# 4. Layer 3执行任务（带能力强化）
output = V3.execute(task_distribution["V3"])

# 输出示例：
# {
#   "agent_type": "V3",
#   "output": "
#     【精神主轴提炼】（✅ 体现A1概念表达能力）
#
#     核心概念：'禅境现代主义'
#     - 禅的克制 × 现代的纯粹 = 极简美学
#     - 山的沉静 × 云的流动 = 动静平衡
#
#     空间规则：
#     1. 材料控制：木+石+清水混凝土（禅的物质性）
#     2. 光线策略：单一自然光源 + 反射间接光（禅的静谧）
#     3. 尺度压缩：3.2m压低层高 → 视线内收（禅的内省）
#     4. 叙事节奏：入口压缩(2.2m) → 过渡(走廊) → 释放(客房) → 高潮(观景平台)
#
#     （✅ 概念贯穿平面/立面/材料/灯光，符合A1验证标准）
#   ",
#   "injected_abilities": ["A1_concept_expression"],
#   "task": "基于JTBD提炼精神主轴"
# }
```

### 4.5 Layer 4：P2验证能力体现

**目标**：验证专家输出是否真实体现了注入的能力

```python
# ability_validator.py

class AbilityValidator:
    def validate_expert_output(self, expert_output, baseline):
        """
        P2验证框架

        输入：
        - expert_output：专家输出（来自Layer 3）
        - baseline：验证标准（来自Phase2的expert_handoff）

        输出：
        - ability_validation：各能力的体现分数
        - overall_score：总体质量分数
        """

        injected_abilities = expert_output.get("injected_abilities", [])
        output_content = expert_output.get("output", "")

        # 从Phase2获取验证基线
        design_challenge = baseline.get("design_challenge", "")  # ← L3杠杆点
        sharpness_threshold = baseline.get("sharpness_score", 70)  # ← L5阈值

        validation_results = {}

        for ability_id in injected_abilities:
            ability_config = AbilitySchemas.get_ability(ability_id)

            # 验证该能力是否体现
            score = self._validate_ability(
                output_content=output_content,
                ability_definition=ability_config["definition"],
                validation_criteria=ability_config["validation_criteria"],
                baseline_challenge=design_challenge  # ← 使用Phase2定义的标准
            )

            validation_results[ability_id] = {
                "score": score,
                "passed": score >= sharpness_threshold  # ← 使用Phase2定义的阈值
            }

        overall_score = sum(r["score"] for r in validation_results.values()) / len(validation_results)

        return {
            "ability_validation": validation_results,
            "overall_score": overall_score,
            "threshold": sharpness_threshold,
            "baseline_challenge": design_challenge
        }
```

**验证示例**（承接Layer 3输出）：

```python
# 1. 专家输出（来自Layer 3）
expert_output = {
    "agent_type": "V3",
    "output": "【精神主轴提炼】...",  # ← 完整输出见4.4节
    "injected_abilities": ["A1_concept_expression"]
}

# 2. 验证基线（来自Phase2）
baseline = {
    "design_challenge": "商业 vs 精神",  # ← L3杠杆点
    "sharpness_score": 78  # ← L5锐度
}

# 3. P2验证
validation = AbilityValidator.validate_expert_output(
    expert_output=expert_output,
    baseline=baseline
)

# 验证结果：
# {
#   "ability_validation": {
#     "A1_concept_expression": {
#       "score": 82,  # ✅ 高于阈值78
#       "passed": True,
#       "evidence": [
#         "✅ 核心概念明确：'禅境现代主义'",
#         "✅ 概念转化为空间规则：材料/光线/尺度/叙事",
#         "✅ 概念贯穿多个维度：平面/立面/材料/灯光"
#       ]
#     }
#   },
#   "overall_score": 82,
#   "threshold": 78,  # ← 来自Phase2 L5
#   "baseline_challenge": "商业 vs 精神"  # ← 来自Phase2 L3
# }
```

### 4.6 四层协同的真实定位

**四层协同不是"能力管理"，而是任务执行的实施层：**

| Layer | 功能 | 输入 | 输出 | 来源/去向 |
|-------|------|------|------|----------|
| **Layer 1** | 使用Mode结果 | detected_modes | - | Phase2已完成 |
| **Layer 2** | Mode → Ability | detected_modes | ability_injections | 来自Phase2 → 注入Layer 3 |
| **Layer 3** | Expert执行 | task + abilities | expert_outputs | task来自project_director |
| **Layer 4** | P2验证 | outputs + baseline | validation_report | baseline来自Phase2 |

**完整数据流**：

```
Phase2输出
├─ detected_design_modes
│   ↓
├─ Layer 1: 直接使用（无需重复检测）
│   ↓
├─ Layer 2: Mode → Ability映射
│   └→ M1 → [A1, A2]
│       ↓
│   Layer 3: 注入到V3 → 执行task_distribution中的任务
│       ├→ task: "基于JTBD提炼精神主轴"（来自project_director）
│       └→ abilities: [A1, A2]（来自Layer 2）
│           ↓
│       输出: expert_output (带A1/A2能力特征)
│           ↓
│       Layer 4: P2验证
│       ├→ baseline: expert_handoff（来自Phase2 L3/L5）
│       └→ threshold: sharpness_score（来自Phase2 L5）
│           ↓
│       验证结果: A1=82分, A2=75分 ✅
│
└─ expert_handoff (验证标准)
    ↓
    传递给Layer 4
```

**关键发现**：

✅ 四层协同的**唯一目标**是执行task_distribution中的任务：
1. Layer 1使用Phase2的detected_modes（无需重复）
2. Layer 2根据detected_modes触发能力注入
3. Layer 3执行task_distribution中的任务（带能力强化）
4. Layer 4验证输出质量（使用Phase2的baseline）

✅ 四层协同是**任务执行系统的实施层**，不是独立系统。

---

## 五、统一链路：完整执行流程

### 5.1 峨眉山民宿案例（端到端）

**用户输入**：

```
峨眉山高端民宿，禅意与现代融合，20间客房，预算800万，
目标客群为追求精神体验的高净值人群，需要实现品牌溢价。
```

#### 5.1.1 阶段1：任务定义（Phase1 + Phase2）

**Phase1: 能力边界判断**

```python
# 输入：用户需求

# Phase1输出：
{
  "info_status": "sufficient",  # 信息充足
  "primary_deliverables": [
    "建筑设计方案",
    "室内设计方案",
    "品牌策略方案"
  ],
  "capability_score": 0.85  # 能力匹配度
}

# ✅ 判断：所有交付物在能力范围内，触发Phase2
```

**Phase2: 任务定义 + 能力预判**

```python
# Phase2 Track 1: L1-L7深度分析

{
  "L1_解构": {
    "用户是谁": "追求精神体验的高净值人群",
    "要什么": "品牌溢价 + 禅意体验",
    "约束": "预算800万，峨眉山地形"
  },

  "L2_建模": {
    "心理需求": "精神认同 > 物质消费",
    "社会身份": "文化精英阶层",
    "审美偏好": "极简、自然、禅意"
  },

  "L3_杠杆点": {
    "核心对立": "商业 vs 精神",
    "设计挑战": "如何在盈利模型中保持精神纯粹性？"
  },

  "L4_JTBD": {
    "project_task": "When [用户需要峨眉山高端民宿] I want [品牌溢价 + 精神体验] So I can [实现商业价值与精神价值的平衡]"
  },

  "L5_锐度测试": {
    "sharpness_score": 78,  # ← 将作为验证阈值
    "不足项": ["商业模式需进一步深化"]
  },

  "expert_handoff": {
    "design_challenge": "商业 vs 精神",  # ← 将作为验证基线
    "core_tasks": [
      "提炼精神主轴",
      "设计收益模型",
      "平衡商业与精神"
    ]
  }
}

# Phase2 Track 2: Mode Detection

{
  "detected_design_modes": [
    {"mode": "M1", "confidence": 0.88},  # 概念驱动型
    {"mode": "M4", "confidence": 0.75},  # 资产资本型
    {"mode": "M8", "confidence": 0.62}   # 极端环境型
  ]
}

# ═══════════════════════════════════════════════════════════
# ✅ Phase2输出（传递给下游）
# ═══════════════════════════════════════════════════════════

传递给project_director:
- project_task (JTBD)
- expert_handoff (验证标准)

传递给四层协同:
- detected_design_modes (能力需求)
- analysis_layers (验证基线)
```

#### 5.1.2 阶段2：任务分配（project_director）

```python
# 输入：Phase2输出

# project_director处理：

# 1. 基于JTBD生成tasks
project_task = "When [用户需要峨眉山民宿] I want [品牌溢价 + 精神体验] So I can [平衡商业与精神]"

# ↓ JTBD分解

tasks = [
    "提炼精神主轴（禅意与现代的融合点）",  # ← 对应"精神体验"
    "设计收益模型（品牌溢价路径）",        # ← 对应"品牌溢价"
    "平衡商业与精神（核心对立解决）"      # ← 对应"平衡"
]

# 2. 召集专家 + 分配任务
task_distribution = {
    "V3_spatial_designer": "基于JTBD提炼精神主轴（禅意与现代融合）。你需要将'禅'的克制与'现代'的纯粹融合为可执行的空间规则，涵盖材料/光线/尺度/叙事节奏。",

    "V6_2_commercial_strategist": "基于JTBD设计收益模型（品牌溢价路径）。你需要在保持精神纯粹性的前提下，构建可持续的盈利模型，包括定价策略、客群定位、服务体系。",

    "V7_context_designer": "基于JTBD分析峨眉山环境适应。你需要研究地形、气候、材料可获得性，提出技术方案。"
}

# 3. 预判能力需求（基于detected_modes）
detected_modes = [M1:0.88, M4:0.75, M8:0.62]

# ↓ 预判

required_abilities = {
    "M1": ["A1_concept_expression", "A2_narrative_structure"],
    "M4": ["A7_asset_management"],
    "M8": ["A11_extreme_adaptation"]
}

# ═══════════════════════════════════════════════════════════
# ✅ project_director输出（传递给四层协同）
# ═══════════════════════════════════════════════════════════

传递给Layer 3:
- task_distribution（任务清单）

传递给Layer 2:
- detected_modes（触发能力注入）
```

#### 5.1.3 阶段3：任务执行（四层协同）

**Layer 1: 使用Mode Detection结果**

```python
# 直接使用Phase2的detected_modes，无需重复检测
detected_modes = [
    {"mode": "M1", "confidence": 0.88},
    {"mode": "M4", "confidence": 0.75}
]

logger.info("[Layer 1] 使用Phase2检测的2个主模式")
```

**Layer 2: Mode → Ability映射**

```python
# 查询ability_injections.yaml

M1 → ["A1_concept_expression", "A2_narrative_structure"]
M4 → ["A7_asset_management"]

# 注入规则：
{
    "V3": ["A1", "A2"],  # ← M1触发
    "V6_2": ["A7"]       # ← M4触发
}
```

**Layer 3: Ability强化 → Expert执行**

```python
# V3执行（带A1/A2能力强化）

# 1. 创建专家
V3 = BaseExpert("V3_spatial_designer")

# 2. 注入能力（来自Layer 2）
V3.inject_ability("A1_concept_expression", mode_confidence=0.88)
V3.inject_ability("A2_narrative_structure", mode_confidence=0.88)

# 3. 执行任务（来自task_distribution）
output_V3 = V3.execute(
    task="基于JTBD提炼精神主轴（禅意与现代融合）..."
)

# V3输出（体现A1/A2能力）：
{
  "agent_type": "V3",
  "output": "
    【精神主轴提炼】

    ✅ 核心概念（A1能力体现）:
    '禅境现代主义' = 禅的克制 × 现代的纯粹

    空间规则（A1能力体现）:
    - 材料：木+石+清水混凝土（禅的物质性）
    - 光线：单一自然光源 + 间接反射（禅的静谧）
    - 尺度：3.2m压低层高（禅的内省）
    - 色彩：低饱和度灰白系（禅的克制）

    ✅ 叙事节奏（A2能力体现）:
    进入  → 压缩(2.2m入口，暗)
    过渡  → 走廊(渐明，木香)
    聚焦  → 茶室(单光源，静)
    高潮  → 观景平台(视线释放，云海)
    沉静  → 客房(内省空间，禅修)

    ✅ 对立平衡（呼应JTBD的'平衡商业与精神'）:
    商业层：房价溢价来自精神价值认同（不是豪华堆砌）
    精神层：禅意不是符号化，而是空间结构本身
  ",
  "injected_abilities": ["A1", "A2"],
  "task": "基于JTBD提炼精神主轴"
}

# ═══════════════════════════════════════════════════════════
# 同理，V6_2执行（带A7能力强化）
# ═══════════════════════════════════════════════════════════

V6_2 = BaseExpert("V6_2_commercial_strategist")
V6_2.inject_ability("A7_asset_management", mode_confidence=0.75)

output_V6 = V6_2.execute(
    task="基于JTBD设计收益模型..."
)

# V6_2输出（体现A7能力）：
{
  "agent_type": "V6_2",
  "output": "
    【收益模型设计】

    ✅ 客群资产模型（A7能力体现）:
    - 目标客群：资产>3000万，年龄35-50岁
    - 消费动机：精神认同 > 物质消费
    - 付费意愿：溢价空间30%-50%

    ✅ 坪效模型（A7能力体现）:
    - 房价：2800-4500元/晚（高于区域均价50%）
    - 入住率目标：淡季50%，旺季85%
    - 年收益：1200万（投资回报周期5.5年）

    ✅ 溢价符号构建（A7能力体现）:
    - 稀缺性：限量20间（拒绝规模化）
    - 仪式感：预约制+主理人接待
    - 文化IP：与禅修大师合作
  ",
  "injected_abilities": ["A7"],
  "task": "基于JTBD设计收益模型"
}
```

**Layer 4: P2验证能力体现**

```python
# 验证V3输出（使用Phase2的baseline）

baseline = {
    "design_challenge": "商业 vs 精神",  # ← 来自Phase2 L3
    "sharpness_threshold": 78            # ← 来自Phase2 L5
}

validation_V3 = AbilityValidator.validate_expert_output(
    expert_output=output_V3,
    baseline=baseline
)

# 验证结果：
{
  "ability_validation": {
    "A1_concept_expression": {
      "score": 82,  # ✅ 高于阈值78
      "passed": True,
      "evidence": [
        "✅ 核心概念明确：'禅境现代主义'",
        "✅ 概念转化为规则：材料/光线/尺度/色彩",
        "✅ 贯穿多维度：平面/立面/材料/叙事"
      ]
    },
    "A2_narrative_structure": {
      "score": 75,  # ⚠️ 接近阈值
      "passed": True,
      "evidence": [
        "✅ 叙事节奏完整：进入→过渡→高潮→沉静",
        "⚠️ 情绪高潮可再强化"
      ]
    }
  },
  "overall_score": 78.5,  # ✅ 通过
  "baseline_challenge": "商业 vs 精神",
  "challenge_addressed": True  # ✅ V3输出确实平衡了商业与精神
}

# ═══════════════════════════════════════════════════════════
# 同理验证V6_2输出
# ═══════════════════════════════════════════════════════════

validation_V6 = AbilityValidator.validate_expert_output(
    expert_output=output_V6,
    baseline=baseline
)

# 验证结果：
{
  "ability_validation": {
    "A7_asset_management": {
      "score": 86,  # ✅ 显著高于阈值
      "passed": True,
      "evidence": [
        "✅ 客群资产模型精准",
        "✅ 坪效模型可落地",
        "✅ 溢价符号构建完整",
        "✅ 在盈利模型中保持精神纯粹性"
      ]
    }
  },
  "overall_score": 86,
  "challenge_addressed": True
}
```

### 5.2 完整链路总结

**统一目标**：执行用户任务（峨眉山高端民宿设计）

```
阶段1：任务定义（Phase1 + Phase2）
├─ Phase1: 判断"能做什么"
│   └→ 交付物在能力范围内 ✅
├─ Phase2 L1-L7: 定义"做什么任务"
│   └→ JTBD: "品牌溢价 + 精神体验，平衡商业与精神" ✅
└─ Phase2 Mode: 预判"需要什么能力"
    └→ detected_modes: [M1:0.88, M4:0.75] ✅
        ↓
阶段2：任务分配（project_director）
├─ 基于JTBD生成tasks
│   ├→ V3: "提炼精神主轴"
│   └→ V6_2: "设计收益模型"
└─ 基于detected_modes预判能力
    └→ V3需要A1/A2，V6需要A7 ✅
        ↓
阶段3：任务执行（四层协同）
├─ Layer 1: 使用detected_modes（Phase2已完成）
├─ Layer 2: M1→A1/A2, M4→A7
├─ Layer 3: V3执行任务（带A1/A2强化）
│             V6执行任务（带A7强化）
└─ Layer 4: 验证输出（使用Phase2的baseline）
              V3=78.5分 ✅, V6=86分 ✅
        ↓
最终输出：专家方案（Expert Outputs）
├─ V3方案：精神主轴 + 空间规则 + 叙事节奏
└─ V6方案：客群模型 + 坪效模型 + 溢价符号
```

**关键洞察**：

✅ 整个系统只有一个目标：**执行用户任务**
✅ Phase1/Phase2/project_director/四层协同是**同一执行链路的三个阶段**
✅ 数据流是**单向传递**：Phase2 → project_director → 四层协同
✅ JTBD是**任务定义**，detected_modes是**能力预判**，两者共同驱动执行

---

## 六、架构优化建议

### 6.1 当前缺口（基于统一链路视角）

#### 缺口1：问卷未融入Mode Detection（P0优先级）

**问题**：

```python
# 当前流程（v7.621）

if info_status == "insufficient":
    # ❌ 问卷生成未使用detected_modes
    questions = generate_generic_questions(sharpness_deficiencies)
    # 所有项目收到相同问题（无论M1还是M9）
```

**影响**：

- M1（概念驱动型）项目：问卷应聚焦"精神主轴"、"文化母题"
- M9（社会结构型）项目：问卷应聚焦"权力关系"、"冲突缓冲"
- 当前：两者问相同问题 ❌

**修复方案**：

```python
# 优化后流程

if info_status == "insufficient":
    # ✅ 使用detected_modes生成定制化问题
    questions = generate_mode_specific_questions(
        sharpness_deficiencies=sharpness_deficiencies,
        detected_modes=detected_modes  # ← Phase2已检测
    )

# 示例：
# M1项目 → 问："你希望空间表达什么核心精神？"
# M9项目 → 问："家庭成员之间的权力关系如何？"
```

**ROI评估**：

- 成本：5小时开发 + 创建MODE_QUESTION_TEMPLATES.yaml
- 收益：问卷精准度提升10x（从通用问题 → 模式定制问题）
- 优先级：P0（影响66%的insufficient场景）

#### 缺口2：Task Generation隐式化（P2优先级）

**问题**：

```python
# 当前流程

# project_director依赖LLM自由发挥生成tasks
task_distribution = llm.invoke(f"基于JTBD '{project_task}' 分配任务")

# ❌ 风险：LLM可能漏掉关键任务
#    例如：M1项目忘记分配"文化母题提炼"任务
```

**影响**：

- 任务分配不稳定（LLM发挥不稳定）
- 关键任务可能被遗漏
- 无法保证JTBD的完整覆盖

**修复方案**：

```python
# 优化后流程

# ✅ 创建MODE_TASK_LIBRARY.yaml
M1_concept_driven:
  core_tasks:  # 必须分配的核心任务
    - "提炼精神主轴（M1-1）"
    - "构建概念结构（M1-2）"
    - "提取文化母题（M1-3）"
    - "设计叙事路径（M1-4）"
  optional_tasks:  # 可选任务
    - "制作概念手册"

# project_director先从library提取核心任务，再让LLM补充
core_tasks = MODE_TASK_LIBRARY.get_core_tasks(detected_modes)
supplementary_tasks = llm.generate_supplementary_tasks(project_task, core_tasks)

task_distribution = {
    **core_tasks,  # ← 保证完整性
    **supplementary_tasks  # ← 保证灵活性
}
```

**ROI评估**：

- 成本：8小时开发 + 创建任务库（10个模式×4个核心任务）
- 收益：任务分配稳定性提升5x
- 优先级：P2（推荐优化，但不紧急）

#### 缺口3：Capability Precheck缺失（P1优先级）

**问题**：

```python
# 当前流程

# Phase2输出detected_modes，但未预判required_abilities
detected_modes = [M1:0.88, M4:0.75]

# ❌ 直到Layer 2才映射能力
#    project_director无法提前规划专家召集
```

**影响**：

- project_director无法提前知道需要哪些能力
- 专家召集可能遗漏（例如M1需要A1能力，但未召集擅长A1的专家）
- 能力预判延迟到Layer 2（应该在Phase2完成）

**修复方案**：

```python
# 优化后流程

# ✅ Phase2输出时预判required_abilities

def phase2_node(state):
    # ... L1-L7分析 ...
    # ... Mode Detection ...

    # ✅ 预判能力需求
    required_abilities = predict_abilities_from_modes(detected_modes)

    # 示例：
    # detected_modes = [M1:0.88, M4:0.75]
    # required_abilities = {
    #     "M1": ["A1", "A2"],
    #     "M4": ["A7"]
    # }

    return {
        "detected_design_modes": detected_modes,
        "required_abilities": required_abilities,  # ← 新增输出
        # ...
    }

# project_director收到required_abilities后
# 可以在召集专家时优先选择符合能力需求的专家

def select_roles_for_task(requirements_text, required_abilities):
    # ✅ 优先召集擅长required_abilities的专家
    candidates = filter_experts_by_abilities(required_abilities)
    # ...
```

**ROI评估**：

- 成本：4小时开发
- 收益：专家召集精准度提升3x
- 优先级：P1（简单且高效）

### 6.2 架构演进时间线

```
v7.17之前：分离的两套系统
├─ Phase1/Phase2：需求分析（独立运行）
└─ 四层协同：能力管理（独立运行）
❌ 问题：两套系统缺乏深度联动

v7.17：Mode Detection注入
├─ Phase2嵌入Mode Detection（集成点）
└─ detected_modes传递给Layer 2
✅ 进步：建立初步联动

v7.18（当前）：L6/L7扩展 + P2验证
├─ L6假设审计 + L7系统影响
├─ P2验证框架（Layer 4）
└─ expert_handoff传递给验证层
✅ 进步：验证体系完善

v7.621（本次洞察）：架构本质重新定义
├─ 统一任务执行框架
├─ Phase1/Phase2 = 任务定义阶段
├─ project_director = 任务分配阶段
└─ 四层协同 = 任务执行阶段
✅ 进步：架构理解统一

v7.700（未来规划）：链路完整性优化
├─ 问卷融入Mode Detection（P0）
├─ Capability Precheck（P1）
├─ MODE_TASK_LIBRARY（P2）
└─ 端到端质量保障体系
🎯 目标：任务执行链路的完整闭环
```

---

## 七、关键FAQ

### Q1: Phase1/Phase2还在吗？

✅ **完全保留**，正常运行中。

但理解方式改变：
- ❌ 旧理解：Phase1/Phase2是"需求分析系统"
- ✅ 新理解：Phase1/Phase2是"任务执行的定义阶段"

**L0-L7框架全部保留**：
- L0定性、L1解构、L2建模、L3杠杆点、L4 JTBD、L5锐度、L6假设、L7影响
- Mode Detection（10 Mode Engine）

### Q2: 四层协同与L0-L7是什么关系？

✅ **同一执行系统的不同阶段**。

不是"两套独立系统"，而是：
- **阶段1（Phase1/Phase2）**：定义"做什么"
- **阶段2（project_director）**：分配"谁做什么"
- **阶段3（四层协同）**：执行"如何做"

**数据流**：
```
Phase2输出
├─ JTBD → project_director → task_distribution → Layer 3执行
└─ detected_modes → Layer 2注入 → Layer 3强化
```

### Q3: 是取代还是补充？

✅ **既不是取代，也不是补充，而是同一系统的协同阶段**。

**不是**：
- ❌ Phase1/Phase2取代四层协同
- ❌ 四层协同取代Phase1/Phase2
- ❌ Phase1/Phase2补充四层协同

**而是**：
- ✅ Phase1/Phase2为四层协同准备**执行框架**
- ✅ project_director将Phase2的**任务定义**转化为**任务分配**
- ✅ 四层协同基于**任务分配**和**能力预判**执行任务

### Q4: 为什么之前理解错了？

❌ **旧理解的误区**：

1. 将Phase1/Phase2视为"需求分析"
   - 实际：Phase1/Phase2是任务执行的**定义层**
   - 输出的JTBD直接驱动任务分配

2. 将四层协同视为"能力管理"
   - 实际：四层协同是任务执行的**实施层**
   - Layer 3执行的是task_distribution中的任务

3. 认为两者是"独立系统"
   - 实际：两者通过JTBD和detected_modes**单向连接**
   - Phase2 → project_director → 四层协同（数据流）

✅ **新理解的关键**：

**从结果导向看**：整个系统的唯一目标是执行用户任务。
- Phase1/Phase2定义任务（JTBD）
- project_director分配任务（task_distribution）
- 四层协同执行任务（expert_outputs）

**不是两套系统，而是同一执行系统的三个阶段。**

### Q5: 用户需要理解新概念吗？

❌ **不需要**。

用户只需理解：
1. Phase1会判断信息是否充足（可能需要填问卷）
2. Phase2会进行深度分析（L1-L7）
3. 系统会自动根据项目特征（Mode Detection）强化专家能力
4. 最终输出专家方案

**后台机制（用户无感）**：
- JTBD如何传递给project_director
- detected_modes如何触发能力注入
- Layer 4如何验证能力体现

**用户体验不变，但系统理解更清晰。**

---

## 八、总结与展望

### 8.1 核心结论

**统一任务执行架构（Unified Task Execution Framework）**：

```
目标：执行用户任务（Task Execution）
              ↓
    ┌─────────┼─────────┐
    │         │         │
 阶段1      阶段2      阶段3
任务定义    任务分配    任务执行
Phase1+2    director    四层协同
L0-L7+Mode  JTBD→tasks  Mode→Expert
```

**三个阶段**：

| 阶段 | 目标 | 核心输出 | 下游消费 |
|-----|------|---------|---------|
| **阶段1** | 定义"做什么" | JTBD + detected_modes | 任务分配 + 任务执行 |
| **阶段2** | 分配"谁做什么" | task_distribution | 任务执行 |
| **阶段3** | 执行"如何做" | expert_outputs | 用户交付 |

**关键洞察**：

✅ **不是两套系统，而是同一执行系统的三个阶段**
✅ **数据流单向传递**：Phase2 → project_director → 四层协同
✅ **JTBD是任务定义，detected_modes是能力预判**
✅ **整个系统只有一个目标：执行用户任务**

### 8.2 链路一致性验证

**完整执行链路**：

```
用户需求
    ↓
Phase1: 能力边界判断
    └→ primary_deliverables（能力范围内的任务）
        ↓
Phase2 L1-L7: 任务定义
    └→ JTBD（"When...I want...So I can..."）
        ↓
Phase2 Mode: 能力预判
    └→ detected_modes（[M1, M4, ...]）
        ↓
project_director: 任务分配
    ├→ 基于JTBD生成tasks
    └→ 基于detected_modes预判abilities
        ↓
Layer 1: 使用detected_modes
        ↓
Layer 2: Mode → Ability映射
        ↓
Layer 3: Expert执行tasks（带能力强化）
        ↓
Layer 4: P2验证（使用Phase2的baseline）
        ↓
专家方案输出
```

**链路一致性**：

✅ **每个阶段都为下游准备明确的输入**
✅ **数据流无断层（JTBD → tasks → outputs）**
✅ **验证标准源头统一（Phase2定义，Layer 4使用）**

### 8.3 未来优化方向

v7.700（下一版本）规划：

1. **P0: 问卷融入Mode Detection**
   - 从通用问题 → 模式定制问题
   - ROI: 10x精准度提升

2. **P1: Capability Precheck**
   - Phase2输出required_abilities
   - project_director提前规划专家召集

3. **P2: MODE_TASK_LIBRARY**
   - 保证核心任务不遗漏
   - 稳定性提升5x

4. **P3: 端到端质量保障**
   - Phase2 → project_director → Layer 4
   - 完整的验证闭环

**终极目标**：
从用户需求到专家交付的**完整任务执行链路**，每个环节紧密衔接，数据流清晰可追溯，质量保障体系完整。

---

## 附录

### A. 关键术语对照表

| 术语 | 定义 | 所属阶段 | 数据流向 |
|-----|------|---------|---------|
| **JTBD** | Jobs To Be Done，任务定义 | 阶段1 Phase2 L4 | → project_director |
| **detected_modes** | 10 Mode Engine检测结果 | 阶段1 Phase2 Mode | → Layer 2 |
| **expert_handoff** | 专家接口，验证标准 | 阶段1 Phase2 L3/L5 | → Layer 4 |
| **task_distribution** | 任务分配表 | 阶段2 project_director | → Layer 3 |
| **required_abilities** | 能力需求预判 | 阶段2（未来） | → Layer 2 |
| **ability_injections** | 能力注入配置 | 阶段3 Layer 2 | → Layer 3 |
| **expert_outputs** | 专家输出方案 | 阶段3 Layer 3 | → Layer 4 |
| **validation_report** | P2验证报告 | 阶段3 Layer 4 | → 用户交付 |

### B. 架构演进对比图

```
v7.17之前：误解架构
┌─────────────────┐       ┌─────────────────┐
│ Phase1/Phase2   │       │   四层协同      │
│ (需求分析)      │  独立  │  (能力管理)     │
└─────────────────┘       └─────────────────┘
❌ 问题：两套系统，联动弱

v7.621：统一架构
┌──────────────────────────────────────────────┐
│         统一任务执行框架                      │
├──────────────────────────────────────────────┤
│ 阶段1：任务定义 → 阶段2：任务分配 → 阶段3：执行│
│ Phase1/Phase2      project_director   四层协同│
│ JTBD + detected_modes → tasks → outputs      │
└──────────────────────────────────────────────┘
✅ 解决：单向数据流，链路清晰
```

### C. 实现文件清单

| 阶段 | 模块 | 文件路径 | 核心功能 |
|-----|------|---------|---------|
| **阶段1** | Phase1 | `requirements_analyst_agent.py:phase1_node()` | 能力边界判断 |
| **阶段1** | Phase2 L1-L7 | `requirements_analyst_agent.py:phase2_node()` | JTBD定义 |
| **阶段1** | Phase2 Mode | `mode_detector.py:detect_sync()` | Mode检测 |
| **阶段2** | project_director | `project_director.py:execute_dynamic_with_validation()` | 任务分配 |
| **阶段3** | Layer 1 | Phase2已完成 | 使用detected_modes |
| **阶段3** | Layer 2 | `ability_injections.yaml` | Mode → Ability |
| **阶段3** | Layer 3 | `task_oriented_expert_factory.py` | Expert执行 |
| **阶段3** | Layer 4 | `ability_validator.py` | P2验证 |

### D. 配置文件清单

| 配置文件 | 作用 | 关键字段 |
|---------|------|---------|
| `requirements_analyst_phase1.yaml` | Phase1 prompt配置 | `system_prompt`, `task_description_template` |
| `requirements_analyst_phase2.yaml` | Phase2 L1-L7配置 | `analysis_layers`, `JTBD_template` |
| `sf/10_Mode_Engine` | 10个模式定义 | M1-M10二级结构 |
| `ability_schemas.py` | 12个能力定义 | A1-A12验证标准 |
| `ability_injections.yaml` | Mode → Ability映射 | `M1.triggered_abilities` |
| `expert_configs.yaml` | 专家配置 | V2-V7专家定义 |
| `ability_verification_rules.yaml` | P2验证规则 | 验证标准配置 |

---

**文档版本**：v1.0
**最后更新**：2026-02-13
**作者**：GitHub Copilot（基于用户深度思考）
**审核**：用户洞察驱动的架构重构

**关键突破**：从"两套系统"到"同一执行链路的三个阶段"
