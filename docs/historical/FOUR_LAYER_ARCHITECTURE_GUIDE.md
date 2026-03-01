# 四层协同架构完整指南
## 从需求分析到最终输出的全流程解析

**版本**: v1.0
**创建日期**: 2026-02-13
**作者**: Architecture Analysis Team

---

## 🎯 执行摘要

四层协同架构是本系统的核心设计理念，贯穿从**需求分析 → 问卷交互 → 任务分配 → 专家执行 → 输出验证**的完整流程。

**四层定义**:
1. **Layer 1 - 设计模式层** (10 Mode Engine): 识别项目主导逻辑
2. **Layer 2 - 能力层** (12 Ability Core): 定义能力需求映射
3. **Layer 3 - 专家层** (V2-V7 Expert System): 携带能力执行任务
4. **Layer 4 - 验证层** (P2 Validation Framework): 验证能力体现

---

## 📊 流程概览：各环节如何体现四层协同

```
┌─────────────────────────────────────────────────────────────┐
│ 环节1: 需求分析 (Requirements Analysis)                      │
├─────────────────────────────────────────────────────────────┤
│ Layer 1 体现: Mode Detection（10 Mode Engine检测）           │
│   - 分析用户输入，识别设计模式倾向                             │
│   - 输出: detected_design_modes (M1-M10检测置信度)           │
│                                                              │
│ Layer 2 体现: Capability Precheck（能力预检查）              │
│   - 根据模式，预判需要哪些能力                                │
│   - 输出: required_abilities (A1-A12需求清单)                │
│                                                              │
│ Layer 3 体现: Expert Pool Analysis（专家池分析）             │
│   - 评估当前专家池是否覆盖所需能力                             │
│   - 输出: expert_coverage_report                             │
│                                                              │
│ Layer 4 体现: Quality Metadata（质量元数据）                 │
│   - 标注信息充足性、置信度级别                                │
│   - 输出: info_quality_metadata                              │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│ 环节2: 问卷交互 (Three-Step Questionnaire)                   │
├─────────────────────────────────────────────────────────────┤
│ Layer 1 体现: Mode-Specific Questions（模式专用问题）        │
│   - M1概念型: 问"精神主轴"、"文化母题"                       │
│   - M2功能型: 问"动线优化"、"效率指标"                       │
│   - M4资产型: 问"坪效"、"ROI预期"                           │
│                                                              │
│ Layer 2 体现: Ability Gap Identification（能力缺口识别）     │
│   - Step 3: 针对缺失能力的专项提问                           │
│   - 示例: 缺A9社会关系 → 问"家庭结构"、"隐私需求"            │
│                                                              │
│ Layer 3 体现: Expert Readiness Check（专家就绪检查）         │
│   - 问卷结果补充后，重新评估专家匹配度                        │
│   - 输出: expert_readiness_score                             │
│                                                              │
│ Layer 4 体现: Validation Rules Pre-loading（验证规则预加载）  │
│   - 根据问卷结果，预判验证要点                                │
│   - 输出: expected_validation_points                         │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│ 环节3: 任务分配 (Task Allocation)                            │
├─────────────────────────────────────────────────────────────┤
│ Layer 1 体现: Mode-Driven Task Generation（模式驱动任务生成） │
│   - M1模式 → 生成"概念主轴提炼"、"母题转译"任务              │
│   - M7模式 → 生成"系统隐形化"、"数据反馈"任务                │
│                                                              │
│ Layer 2 体现: Ability-Task Mapping（能力-任务映射）          │
│   - A1能力 → 分配"概念建构"、"空间叙事"任务                  │
│   - A9能力 → 分配"权力建模"、"隐私分级"任务                  │
│                                                              │
│ Layer 3 体现: Expert Selection & Synergy（专家选择与协同）   │
│   - 匹配原则:                                                │
│     1. primary_ability优先匹配                              │
│     2. maturity_level满足要求（L3+）                        │
│     3. 输出格式适配（concept_images/reports）                │
│   - 协同设计:                                                │
│     V2(A1) + V3(A3) → M1概念型项目                          │
│     V7(A9) + V6-1(A6) → M9社会结构型项目                    │
│                                                              │
│ Layer 4 体现: Validation Strategy Planning（验证策略规划）   │
│   - 为每个任务预设验证规则                                    │
│   - 示例: "概念主轴提炼"任务 → A1验证规则                    │
│     required_fields: [conceptual_foundation]                │
│     required_keywords: [精神主轴, 思想, 理念]                │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│ 环节4: 任务执行 (Task Execution)                             │
├─────────────────────────────────────────────────────────────┤
│ Layer 1 体现: Mode Injection（模式注入）                     │
│   - ability_injections.yaml提供模式专用prompt                │
│   - M1场景注入:                                              │
│     "在M1概念驱动型项目中，空间必须围绕核心精神主线展开..."   │
│                                                              │
│ Layer 2 体现: Capability Injection（能力注入）               │
│   - 动态注入能力专用prompt（v7.620能力注入系统）              │
│   - A9能力注入示例:                                          │
│     system_prompt += """                                     │
│     你必须展示A9社会关系建模能力：                            │
│     - 权力距离分析（who dominates）                          │
│     - 隐私层级设计（4级隐私模型）                             │
│     - 冲突缓冲机制（回避路径设计）                            │
│     """                                                      │
│                                                              │
│ Layer 3 体现: Expert Execution（专家执行）                   │
│   - 专家配置加载:                                            │
│     core_abilities: {primary: [A9], secondary: [A3]}        │
│   - 专家输出结构:                                            │
│     TaskOrientedExpertOutput {                              │
│       deliverable_id: str                                   │
│       analysis_content: str                                 │
│       structured_output: dict  # A9相关字段                 │
│       concept_images: List[...]  # 可选                     │
│     }                                                        │
│   - 能力体现标记:                                            │
│     _ability_manifestation: {                               │
│       A9: {keywords: [...], depth: 0.85}                    │
│     }                                                        │
│                                                              │
│ Layer 4 体现: Runtime Validation（运行时验证）               │
│   - 实时验证专家输出（P2 Framework集成）                      │
│   - 验证流程:                                                │
│     1. 提取declared_abilities (从配置文件)                   │
│     2. 加载ability_verification_rules.yaml                  │
│     3. 执行AbilityValidator.validate_expert_output()        │
│     4. 生成ExpertValidationReport                           │
│   - 验证结果嵌入输出:                                        │
│     result["ability_validation"] = {                        │
│       overall_passed: bool                                  │
│       overall_score: 0.627                                  │
│       abilities_validated: [                                │
│         {ability_id: "A9", passed: true, score: 0.85},      │
│         {ability_id: "A3", passed: false, score: 0.54}      │
│       ]                                                      │
│     }                                                        │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│ 环节5: 输出聚合与验证 (Output Aggregation & Validation)      │
├─────────────────────────────────────────────────────────────┤
│ Layer 1 体现: Mode Consistency Check（模式一致性检查）       │
│   - 验证最终输出是否符合检测到的设计模式                       │
│   - M1模式检查: 是否有"精神主轴"、"母题系统"                  │
│   - M4模式检查: 是否有"坪效分析"、"ROI预测"                  │
│                                                              │
│ Layer 2 体现: Ability Coverage Report（能力覆盖报告）        │
│   - 统计各能力的体现情况:                                    │
│     A1: 3/5专家体现（60%）                                   │
│     A9: 1/1专家体现（100%）                                  │
│   - 识别能力缺口:                                            │
│     缺失A10环境适应 → 建议补充可持续设计专家                  │
│                                                              │
│ Layer 3 体现: Expert Performance Analysis（专家表现分析）    │
│   - 专家级评分:                                              │
│     v7_emotional_insight_expert:                            │
│       ability_score: {A9: 85%, A3: 54%}                     │
│       quality_level: "good" (0.628)                         │
│   - 协同效果评估:                                            │
│     V2+V3协同 → 覆盖A1+A3（M1模式）                          │
│                                                              │
│ Layer 4 体现: Final Validation Report（最终验证报告）        │
│   - 整体通过率: 56.2% (45%-80%各模式)                       │
│   - 失败模式分析:                                            │
│     高频缺失字段: narrative_design (44次)                    │
│     高频缺失关键词: 精神主轴 (68次)                          │
│   - 优化建议:                                                │
│     1. [高优] 整体质量提升（低于70%目标）                    │
│     2. [中优] A1/A7能力增强                                 │
│     3. [中优] 验证规则调整                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 详细解析：各环节的四层实现

### 1️⃣ 需求分析环节

#### Layer 1: Mode Detection实现

**文件**: `intelligent_project_analyzer/agents/requirements_analyst_agent.py`

```python
# Line 321-370: 10 Mode Engine检测
detected_modes = []

# M1 概念驱动型检测
if any(kw in user_input for kw in ["精神", "概念", "哲学", "思想"]):
    detected_modes.append({
        "mode_id": "M1",
        "mode_name": "概念驱动型设计",
        "confidence": calculate_confidence(keywords),
        "trigger_abilities": ["A1", "A3"],
        "recommended_experts": ["v2_design_director", "v3_narrative_expert"]
    })

# M9 社会结构型检测
if any(kw in user_input for kw in ["家庭", "代际", "隐私", "冲突"]):
    detected_modes.append({
        "mode_id": "M9",
        "mode_name": "社会结构型设计",
        "confidence": calculate_confidence(keywords),
        "trigger_abilities": ["A9"],
        "recommended_experts": ["v7_emotional_insight_expert"]
    })

return detected_modes
```

**输出结构**:
```json
{
  "detected_design_modes": [
    {
      "mode_id": "M1",
      "mode_name": "概念驱动型设计",
      "confidence": 0.85,
      "trigger_abilities": ["A1", "A3"],
      "recommended_experts": ["v2_design_director", "v3_narrative_expert"],
      "sub_modes": ["M1-1 人物精神建模", "M1-2 概念结构化"],
      "evidence_keywords": ["精神主轴", "文化母题", "空间思想"]
    }
  ]
}
```

#### Layer 2: Capability Precheck实现

**逻辑**:
```python
def precheck_required_abilities(detected_modes: List[Dict]) -> Dict:
    """根据检测到的模式，预判需要的能力"""
    required_abilities = set()

    # 10 Mode Engine → 12 Ability Core映射
    MODE_ABILITY_MAP = {
        "M1": {"primary": ["A1"], "secondary": ["A3"]},
        "M2": {"primary": ["A6"], "secondary": ["A2"]},
        "M3": {"primary": ["A3"], "secondary": ["A5"]},
        "M4": {"primary": ["A7"], "secondary": ["A11"]},
        "M5": {"primary": ["A4"], "secondary": ["A10"]},
        "M6": {"primary": ["A11"], "secondary": ["A12"]},
        "M7": {"primary": ["A8"], "secondary": ["A6"]},
        "M8": {"primary": ["A10"], "secondary": []},
        "M9": {"primary": ["A9"], "secondary": []},
        "M10": {"primary": ["A12"], "secondary": ["A8"]}
    }

    for mode in detected_modes:
        mode_id = mode["mode_id"]
        required_abilities.update(MODE_ABILITY_MAP[mode_id]["primary"])
        required_abilities.update(MODE_ABILITY_MAP[mode_id]["secondary"])

    return {
        "required_abilities": list(required_abilities),
        "mode_coverage": len(detected_modes),
        "ability_count": len(required_abilities)
    }
```

#### Layer 3: Expert Pool Analysis实现

**文件**: `intelligent_project_analyzer/utils/ability_query.py`

```python
def analyze_expert_coverage(required_abilities: List[str]) -> Dict:
    """分析专家池对所需能力的覆盖情况"""
    tool = AbilityQueryTool()
    coverage_report = {}

    for ability_id in required_abilities:
        experts = tool.find_experts_by_ability(
            ability_id=ability_id,
            min_level="L3",  # 至少L3高级整合
            include_secondary=True
        )

        coverage_report[ability_id] = {
            "primary_experts": experts["primary"],
            "secondary_experts": experts["secondary"],
            "total_coverage": len(experts["primary"]) + len(experts["secondary"]),
            "coverage_status": "sufficient" if len(experts["primary"]) > 0 else "weak"
        }

    return coverage_report
```

**输出示例**:
```json
{
  "A1": {
    "primary_experts": ["v2_design_director"],
    "secondary_experts": ["v3_narrative_expert", "v4_design_researcher"],
    "total_coverage": 3,
    "coverage_status": "sufficient"
  },
  "A9": {
    "primary_experts": ["v7_emotional_insight_expert"],
    "secondary_experts": [],
    "total_coverage": 1,
    "coverage_status": "weak"  // ⚠️ 单点故障风险
  }
}
```

#### Layer 4: Quality Metadata生成

**逻辑** (v7.900架构优化):
```python
def generate_quality_metadata(capability_precheck: Dict) -> Dict:
    """生成信息质量元数据，不决定是否执行，而是影响如何执行"""
    score = capability_precheck['info_sufficiency']['score']

    confidence_level = (
        "high" if score >= 0.75 else
        "medium" if score >= 0.50 else
        "low"
    )

    return {
        "score": score,
        "confidence_level": confidence_level,
        "present_dimensions": capability_precheck['info_sufficiency']['present_elements'],
        "missing_dimensions": capability_precheck['info_sufficiency']['missing_elements'],
        "needs_questionnaire_focus": capability_precheck['info_sufficiency']['missing_elements'],
        "validation_strategy": "strict" if confidence_level == "high" else "flexible"
    }
```

---

### 2️⃣ 问卷交互环节

#### Layer 1: Mode-Specific Questions生成

**文件**: `intelligent_project_analyzer/interaction/questionnaire_generator.py`

```python
def generate_step3_gap_questions(
    phase2_result: Dict,
    detected_modes: List[Dict]
) -> List[Dict]:
    """根据模式生成专项问题"""
    questions = []

    for mode in detected_modes:
        if mode["mode_id"] == "M1":  # 概念驱动型
            questions.append({
                "question_id": "M1_spiritual_axis",
                "question_text": "请描述这个项目的核心精神主轴是什么？",
                "related_ability": "A1",
                "required_for_mode": "M1",
                "validation_impact": "high"  # 影响A1能力验证
            })
            questions.append({
                "question_id": "M1_cultural_motif",
                "question_text": "项目需要表达的文化母题是什么？",
                "related_ability": "A1",
                "required_for_mode": "M1"
            })

        elif mode["mode_id"] == "M4":  # 资产资本型
            questions.append({
                "question_id": "M4_target_roi",
                "question_text": "项目的预期ROI目标是多少？",
                "related_ability": "A7",
                "required_for_mode": "M4"
            })

    return questions
```

#### Layer 2: Ability Gap Identification

**Step 3问卷逻辑**:
```python
def identify_ability_gaps(
    expert_coverage: Dict,
    phase2_uncertainty_map: Dict
) -> List[str]:
    """识别能力缺口，生成针对性问题"""
    gaps = []

    # 检查能力覆盖不足
    for ability_id, coverage in expert_coverage.items():
        if coverage["coverage_status"] == "weak":
            gaps.append({
                "ability_id": ability_id,
                "reason": "专家覆盖不足",
                "questions": ABILITY_GAP_QUESTIONS[ability_id]
            })

    # 检查信息缺失
    for ability_id, uncertainty in phase2_uncertainty_map.items():
        if uncertainty["level"] == "high":
            gaps.append({
                "ability_id": ability_id,
                "reason": "信息不确定性高",
                "questions": ABILITY_DETAIL_QUESTIONS[ability_id]
            })

    return gaps
```

**能力缺口问题库**:
```python
ABILITY_GAP_QUESTIONS = {
    "A9": [
        "家庭成员关系结构？（权力距离分析）",
        "隐私需求分级？（公共/半公共/半私密/完全私密）",
        "潜在冲突场景？（需要缓冲机制的地方）",
        "关系演化预期？（5-10年变化）"
    ],
    "A10": [
        "当地气候数据？（温度/湿度/降雨/日照）",
        "能源获取限制？（电力/燃气/水源）",
        "舒适性要求？（温度/湿度/空气质量标准）"
    ]
}
```

#### Layer 3: Expert Readiness Check

**问卷结果影响专家选择**:
```python
def recheck_expert_readiness(
    questionnaire_results: Dict,
    initial_expert_selection: List[str]
) -> Dict:
    """问卷结果可能改变专家选择"""
    adjustments = {}

    # 示例：问卷揭示强烈M9社会结构需求
    if questionnaire_results.get("family_structure_complexity") == "high":
        # 确保V7必须参与
        if "v7_emotional_insight_expert" not in initial_expert_selection:
            adjustments["add"] = ["v7_emotional_insight_expert"]
            adjustments["reason"] = "问卷揭示复杂家庭结构（A9能力必需）"

    return adjustments
```

---

### 3️⃣ 任务分配环节

#### Layer 1: Mode-Driven Task Generation

**文件**: `intelligent_project_analyzer/agents/dynamic_project_director.py`

```python
def generate_mode_specific_tasks(detected_modes: List[Dict]) -> List[Dict]:
    """根据模式生成专用任务"""
    tasks = []

    # M1概念驱动型专用任务
    if any(m["mode_id"] == "M1" for m in detected_modes):
        tasks.extend([
            {
                "task_id": "T_M1_01",
                "task_name": "核心精神主轴提炼",
                "required_ability": "A1",
                "required_maturity": "L4",
                "output_type": "conceptual_foundation",
                "deliverable_fields": ["spiritual_axis", "core_tension"]
            },
            {
                "task_id": "T_M1_02",
                "task_name": "文化母题转译为空间逻辑",
                "required_ability": "A1",
                "required_maturity": "L4",
                "output_type": "spatial_logic"
            }
        ])

    # M9社会结构型专用任务
    if any(m["mode_id"] == "M9" for m in detected_modes):
        tasks.extend([
            {
                "task_id": "T_M9_01",
                "task_name": "家庭权力结构建模",
                "required_ability": "A9",
                "required_maturity": "L3",
                "sub_abilities": ["A9-1_power_distance"],
                "output_type": "social_analysis"
            },
            {
                "task_id": "T_M9_02",
                "task_name": "四级隐私分层设计",
                "required_ability": "A9",
                "required_maturity": "L3",
                "sub_abilities": ["A9-2_privacy_hierarchy"]
            }
        ])

    return tasks
```

#### Layer 2: Ability-Task Mapping矩阵

```python
ABILITY_TASK_MAP = {
    "A1": {
        "核心任务": ["概念主轴提炼", "母题转译", "空间叙事结构"],
        "输出字段": ["conceptual_foundation", "narrative_design"],
        "验证关键词": ["精神主轴", "思想", "理念", "哲学"],
        "maturity_requirement": "L4"
    },
    "A9": {
        "核心任务": ["权力建模", "隐私分级", "冲突缓冲设计", "关系演化规划"],
        "输出字段": ["social_structure_analysis", "privacy_design"],
        "验证关键词": ["权力距离", "隐私层级", "代际关系", "冲突机制"],
        "maturity_requirement": "L3"
    },
    # ... 其他能力映射
}
```

#### Layer 3: Expert Selection策略

**专家选择算法**:
```python
def select_experts_for_tasks(
    tasks: List[Dict],
    expert_pool: Dict[str, ExpertAbilityProfile]
) -> Dict[str, List[str]]:
    """为任务选择最佳专家"""
    allocation = {}

    for task in tasks:
        required_ability = task["required_ability"]
        required_maturity = task["required_maturity"]

        # 筛选候选专家
        candidates = []
        for expert_id, profile in expert_pool.items():
            # 优先匹配primary ability
            for ability in profile.primary:
                if (ability.id == required_ability and
                    maturity_level_to_numeric(ability.maturity_level) >=
                    maturity_level_to_numeric(required_maturity)):
                    candidates.append({
                        "expert_id": expert_id,
                        "score": ability.confidence * 1.5,  # primary权重高
                        "maturity": ability.maturity_level
                    })

            # 次选secondary ability
            for ability in profile.secondary:
                if ability.id == required_ability:
                    candidates.append({
                        "expert_id": expert_id,
                        "score": ability.confidence,  # secondary权重低
                        "maturity": ability.maturity_level
                    })

        # 选择得分最高的专家
        if candidates:
            best_expert = max(candidates, key=lambda x: x["score"])
            allocation[task["task_id"]] = best_expert["expert_id"]
        else:
            # ⚠️ 无合适专家，记录缺口
            allocation[task["task_id"]] = None
            log_capability_gap(required_ability, required_maturity)

    return allocation
```

**协同设计示例**:
```python
# M1概念驱动型项目的专家协同
M1_SYNERGY = {
    "primary_expert": "v2_design_director",  # A1能力L5
    "supporting_experts": [
        "v3_narrative_expert",  # A3能力L4（叙事支撑）
        "v4_design_researcher"  # A12能力L4（文明表达）
    ],
    "task_distribution": {
        "T_M1_01_精神主轴": "v2_design_director",
        "T_M1_02_母题转译": "v2_design_director",
        "T_M1_03_空间叙事": "v3_narrative_expert",  # A3协同
        "T_M1_04_文明背景": "v4_design_researcher"  # A12补充
    }
}
```

#### Layer 4: Validation Strategy Planning

**为每个任务预设验证规则**:
```python
def plan_validation_strategy(tasks: List[Dict]) -> Dict:
    """为任务规划验证策略"""
    validation_plan = {}

    for task in tasks:
        ability_id = task["required_ability"]

        # 加载能力验证规则
        rules = load_ability_verification_rules(ability_id)

        validation_plan[task["task_id"]] = {
            "ability_id": ability_id,
            "required_fields": rules["required_fields"],
            "required_keywords": rules["required_keywords"],
            "failed_checks": rules["failed_checks"],
            "threshold_score": rules.get("threshold_score", 0.70),
            "validation_mode": "strict" if task["required_maturity"] >= "L4" else "flexible"
        }

    return validation_plan
```

**验证规则加载** (从`ability_verification_rules.yaml`):
```yaml
A1_concept_architecture:
  required_fields:
    - conceptual_foundation
    - narrative_design

  required_keywords:
    - weight: 0.3
      keywords: [精神主轴, 思想, 理念, 哲学]
    - weight: 0.2
      keywords: [母题, 隐喻, 象征, 文化]

  failed_checks:
    - check_id: "A1:depth_score"
      description: "概念深度不足"
      threshold: 0.7
      weight: 0.3
```

---

### 4️⃣ 任务执行环节

#### Layer 1: Mode Injection实现

**文件**: `intelligent_project_analyzer/config/ability_injections.yaml`

```yaml
# M1概念驱动型场景注入
M1_concept_driven:
  description: "M1概念驱动型设计模式专用prompt"
  applicable_modes: ["M1"]
  trigger_abilities: ["A1", "A3"]

  injection_content: |
    【设计模式识别】
    本项目被识别为 **M1 概念驱动型设计**，核心原则：

    1. **精神优先**：空间围绕核心精神主线展开，而非风格或功能
    2. **结构秩序**：概念必须转化为可执行的空间规则
    3. **母题系统**：从文化/哲学中提炼统一母题，避免符号堆砌
    4. **叙事节奏**：空间必须有高潮与沉静的节奏控制

    【能力要求】
    你的输出必须体现：
    - A1 概念建构能力（L4+）
    - A3 叙事节奏能力（L3+）

    【输出强制要求】
    必须包含以下结构化字段：
    - conceptual_foundation: 概念基础（精神主轴、核心张力）
    - narrative_design: 叙事路径（进入→过渡→高潮→沉静）

    【验证关键词】
    输出中必须出现：精神主轴、思想、理念、母题、象征

# M9社会结构型场景注入
M9_social_structure:
  description: "M9社会结构型设计模式专用prompt"
  applicable_modes: ["M9"]
  trigger_abilities: ["A9"]

  injection_content: |
    【设计模式识别】
    本项目被识别为 **M9 社会结构型设计**，核心原则：

    1. **权力平衡**：空间反映并调节权力关系
    2. **隐私分级**：必须建立4级隐私模型
    3. **冲突缓冲**：设计情绪缓冲带和回避路径
    4. **关系演化**：空间可适配10年内的关系变化

    【能力要求】
    你的输出必须体现：
    - A9 社会关系建模能力（L3+）

    【输出强制要求】
    必须包含以下分析：
    - 权力距离建模（谁主导空间？谁有视线控制权？）
    - 四级隐私设计（公共区/半公共/半私密/完全私密）
    - 冲突缓冲机制（灰空间、独立通道、多入口）
    - 关系演化适配（可拆分、可转换、独立套间）
```

**注入执行**:
```python
def inject_mode_specific_prompts(
    detected_modes: List[Dict],
    base_system_prompt: str
) -> str:
    """将模式专用prompt注入到system_prompt"""
    injections = load_ability_injections()
    augmented_prompt = base_system_prompt

    for mode in detected_modes:
        mode_id = mode["mode_id"]
        if mode_id in injections:
            augmented_prompt += "\n\n" + injections[mode_id]["injection_content"]

    return augmented_prompt
```

#### Layer 2: Capability Injection实现

**文件**: `intelligent_project_analyzer/agents/task_oriented_expert_factory.py`

```python
# Line 1370-1500: v7.620能力注入系统
def inject_ability_specific_prompts(
    expert_id: str,
    task: Dict,
    detected_modes: List[Dict]
) -> str:
    """动态注入能力专用prompt"""

    required_ability = task["required_ability"]

    # 加载能力注入内容
    ability_injections = {
        "A1": """
【A1 概念建构能力强化】
你必须展示L4+的概念建构能力：

1. **概念主轴提炼**（而非风格表达）
   - 从人物/品牌中提炼精神张力（内在冲突、欲望、权力感）
   - 形成可指导空间的抽象主线

2. **概念结构化转译**
   - 将抽象词转化为空间规则
   - 示例："克制" → 材料控制+体量压缩+光线单一来源

3. **文化母题提炼**
   - 从文化/哲学中提取母题（而非符号堆砌）
   - 形成材料象征、光线强化、结构呼应

4. **空间叙事路径**
   - 设计节奏：进入→过渡→聚焦→高潮→沉静→收束
   - 通过尺度/光线/材料变化控制节奏
""",
        "A9": """
【A9 社会关系建模能力强化】
你必须展示L3+的社会关系建模能力：

1. **权力距离建模**（A9-1）
   - 识别谁主导空间、谁有视线控制权、谁拥有核心区域
   - 空间结构选择：中轴对称（权威型）/分散式（平权型）/环绕式（家族型）

2. **四级隐私设计**（A9-2）
   - 公共区 → 半公共区 → 半私密区 → 完全私密区
   - 物理隔离 + 视觉隔离 + 声学隔离 + 心理隔离

3. **冲突缓冲机制**（A9-3）
   - 灰空间设计（过渡带）
   - 独立通道系统（回避路径）
   - 多入口配置（错峰使用）

4. **关系演化适配**（A9-4）
   - 可拆分房间、可转换功能、独立套间系统
   - 适配10年内的孩子长大、父母老去、婚姻变化
""",
        # ... 其他能力注入内容
    }

    # 构建注入prompt
    injected_prompt = ""
    if required_ability in ability_injections:
        injected_prompt = ability_injections[required_ability]

    # 模式相关的额外强化
    for mode in detected_modes:
        if mode["mode_id"] == "M1" and required_ability == "A1":
            injected_prompt += "\n\n【M1模式额外要求】\n"
            injected_prompt += "在概念驱动型项目中，A1能力是核心支柱，必须达到L4+水平。"

    return injected_prompt
```

**实际注入到LLM调用**:
```python
# task_oriented_expert_factory.py: Line 1550
final_system_prompt = (
    base_system_prompt +  # 专家基础prompt
    mode_injection +       # Layer 1: 模式注入
    capability_injection   # Layer 2: 能力注入
)

response = client.chat.completions.create(
    model=model_name,
    messages=[
        {"role": "system", "content": final_system_prompt},
        {"role": "user", "content": task_instruction}
    ],
    temperature=0.7
)
```

#### Layer 3: Expert Execution详解

**专家配置加载**:
```python
# 从YAML配置加载专家能力声明
expert_config = load_yaml(f"config/roles/{expert_id}.yaml")

# 示例：v7_emotional_insight_expert.yaml
V7_社会关系与心理洞察专家:
  description: "专注家庭结构、代际关系、隐私规划的社会心理学专家"

  core_abilities:
    primary:
      - id: "A9"
        name: "Social Structure Modeling"
        maturity_level: "L4"
        sub_abilities:
          - "A9-1_power_distance"
          - "A9-2_privacy_hierarchy"
          - "A9-3_conflict_buffer"
          - "A9-4_evolution_adaptability"
        confidence: 0.90
        focus: "多代同堂住宅、复杂家庭关系"

    secondary:
      - id: "A3"
        name: "Narrative Orchestration"
        maturity_level: "L3"
        confidence: 0.75
        focus: "家庭叙事、情感节奏"

  roles:
    "7-1":
      name: "家庭结构分析师"
      system_prompt: |
        你是家庭结构分析专家，精通权力距离理论和隐私调节...
      tools:
        - bocha_search_tool
        - tavily_search_tool
```

**专家输出结构**:
```python
class TaskOrientedExpertOutput(BaseModel):
    """专家输出结构（Layer 3体现）"""
    deliverable_id: str
    deliverable_name: str
    analysis_content: str  # 主要分析内容

    # 结构化字段（Layer 2能力体现）
    structured_output: Dict[str, Any]
    # 示例：A9能力输出
    # {
    #   "social_structure_analysis": {
    #     "power_distance": "中轴对称结构，父母主导核心区域",
    #     "privacy_hierarchy": {
    #       "level_1_public": "客厅、餐厅",
    #       "level_2_semi_public": "书房、茶室",
    #       "level_3_semi_private": "儿童房间",
    #       "level_4_private": "主卧套间"
    #     },
    #     "conflict_buffer": "独立茶室作为情绪缓冲区"
    #   }
    # }

    concept_images: Optional[List[ImageMetadata]] = None

    # Layer 4验证相关（内部标记）
    _ability_manifestation: Optional[Dict] = None
    # {
    #   "A9": {
    #     "keywords_found": ["权力距离", "隐私层级", "冲突缓冲"],
    #     "depth_score": 0.85,
    #     "sub_abilities_covered": ["A9-1", "A9-2", "A9-3"]
    #   }
    # }
```

#### Layer 4: Runtime Validation集成

**文件**: `intelligent_project_analyzer/agents/task_oriented_expert_factory.py` (Line 660-710)

```python
# P2 能力验证框架集成
if AbilityValidator and AbilityQueryTool:
    try:
        logger.info(f"🎯 [P2验证] 开始验证 {role_id} 的能力体现...")

        # 1. 获取该专家声明的能力
        ability_tool = AbilityQueryTool()
        expert_profile = ability_tool.get_expert_abilities(role_id)

        if expert_profile:
            # 2. 将ExpertAbilityProfile转换为验证器期望的格式
            declared_abilities = []
            if expert_profile.primary:
                for ability in expert_profile.primary:
                    declared_abilities.append({
                        "id": ability.id,
                        "maturity_level": ability.maturity_level,
                        "confidence": ability.confidence
                    })
            if expert_profile.secondary:
                for ability in expert_profile.secondary:
                    declared_abilities.append({
                        "id": ability.id,
                        "maturity_level": ability.maturity_level,
                        "confidence": ability.confidence
                    })

            logger.info(f"   声明能力: {[a['id'] for a in declared_abilities]}")

            # 3. 执行能力验证
            validator = AbilityValidator()
            validation_report = validator.validate_expert_output(
                expert_id=role_id,
                output=structured_output,  # 专家输出的结构化数据
                declared_abilities=declared_abilities
            )

            # 4. 将验证结果添加到返回结果中
            result["ability_validation"] = {
                "overall_passed": validation_report.overall_passed,
                "overall_score": validation_report.overall_score,
                "timestamp": validation_report.timestamp,
                "summary": validation_report.summary,
                "abilities_validated": [
                    {
                        "ability_id": av.ability_id,
                        "passed": av.passed,
                        "score": av.overall_score,
                        "missing_fields": av.missing_fields[:3],
                        "missing_keywords": av.missing_keywords[:3]
                    }
                    for av in validation_report.abilities_validated
                ]
            }

            # 5. 记录验证结果
            status_icon = "✅" if validation_report.overall_passed else "⚠️"
            logger.info(
                f"   {status_icon} 能力验证评分: {validation_report.overall_score:.1%} "
                f"({validation_report.summary['abilities_passed']}/"
                f"{validation_report.summary['total_abilities_checked']}通过)"
            )

            # 6. 如果验证失败且低于阈值，记录警告
            if not validation_report.overall_passed:
                logger.warning(f"⚠️  [P2验证] {role_id} 能力验证未通过")
                for ability_result in validation_report.abilities_validated:
                    if not ability_result.passed:
                        logger.warning(
                            f"   - {ability_result.ability_id}: {ability_result.overall_score:.1%} "
                            f"(缺失字段: {ability_result.missing_fields[:2]})"
                        )

    except Exception as e:
        logger.error(f"❌ [P2验证] 验证过程出错: {e}")
```

**验证器工作原理**:
```python
# intelligent_project_analyzer/services/ability_validator.py
class AbilityValidator:
    def validate_expert_output(
        self,
        expert_id: str,
        output: Dict[str, Any],
        declared_abilities: List[Dict[str, Any]]
    ) -> ExpertValidationReport:
        """验证专家输出是否体现声明的能力"""

        report = ExpertValidationReport(
            expert_id=expert_id,
            overall_passed=True,
            overall_score=0.0
        )

        for ability_decl in declared_abilities:
            ability_id = ability_decl["id"]

            # 加载验证规则
            rules = self.rules.get(f"{ability_id}_*")

            # 执行验证
            ability_result = self._validate_ability(
                ability_id=ability_id,
                output=output,
                rules=rules
            )

            report.abilities_validated.append(ability_result)

        return report

    def _validate_ability(
        self,
        ability_id: str,
        output: Dict,
        rules: Dict
    ) -> AbilityValidationResult:
        """验证单个能力"""

        # 1. 检查必需字段
        missing_fields = []
        for field in rules["required_fields"]:
            if field not in output:
                missing_fields.append(field)

        # 2. 检查关键词密度
        missing_keywords = []
        text_content = json.dumps(output, ensure_ascii=False)
        for kw_group in rules["required_keywords"]:
            found = any(kw in text_content for kw in kw_group["keywords"])
            if not found:
                missing_keywords.extend(kw_group["keywords"])

        # 3. 执行失败检查
        failed_checks = []
        for check in rules["failed_checks"]:
            check_result = self._execute_check(check, output)
            if not check_result:
                failed_checks.append(check["check_id"])

        # 4. 计算得分
        score = self._calculate_score(
            missing_fields=missing_fields,
            missing_keywords=missing_keywords,
            failed_checks=failed_checks,
            rules=rules
        )

        return AbilityValidationResult(
            ability_id=ability_id,
            passed=score >= rules.get("threshold_score", 0.70),
            overall_score=score,
            missing_fields=missing_fields,
            missing_keywords=missing_keywords,
            failed_checks=failed_checks
        )
```

---

### 5️⃣ 输出聚合与验证环节

#### Layer 1: Mode Consistency Check

**文件**: `intelligent_project_analyzer/report/result_aggregator.py`

```python
def check_mode_consistency(
    detected_modes: List[Dict],
    expert_outputs: List[Dict]
) -> Dict:
    """检查最终输出是否符合检测到的设计模式"""

    consistency_report = {}

    for mode in detected_modes:
        mode_id = mode["mode_id"]

        # M1概念驱动型检查
        if mode_id == "M1":
            has_spiritual_axis = any(
                "精神主轴" in output.get("analysis_content", "")
                for output in expert_outputs
            )
            has_motif_system = any(
                "母题" in output.get("analysis_content", "")
                for output in expert_outputs
            )
            has_conceptual_foundation = any(
                "conceptual_foundation" in output.get("structured_output", {})
                for output in expert_outputs
            )

            consistency_report["M1"] = {
                "mode_name": "概念驱动型",
                "consistency_score": (
                    (0.4 if has_spiritual_axis else 0) +
                    (0.3 if has_motif_system else 0) +
                    (0.3 if has_conceptual_foundation else 0)
                ),
                "missing_elements": [
                    elem for elem, present in [
                        ("精神主轴", has_spiritual_axis),
                        ("母题系统", has_motif_system),
                        ("概念基础字段", has_conceptual_foundation)
                    ] if not present
                ],
                "status": "consistent" if all([
                    has_spiritual_axis, has_motif_system, has_conceptual_foundation
                ]) else "inconsistent"
            }

        # M4资产资本型检查
        elif mode_id == "M4":
            has_roi_analysis = any(
                "ROI" in output.get("analysis_content", "") or
                "坪效" in output.get("analysis_content", "")
                for output in expert_outputs
            )
            has_capital_analysis = any(
                "capital_analysis" in output.get("structured_output", {})
                for output in expert_outputs
            )

            consistency_report["M4"] = {
                "mode_name": "资产资本型",
                "consistency_score": (
                    (0.5 if has_roi_analysis else 0) +
                    (0.5 if has_capital_analysis else 0)
                ),
                "status": "consistent" if all([
                    has_roi_analysis, has_capital_analysis
                ]) else "inconsistent"
            }

    return consistency_report
```

#### Layer 2: Ability Coverage Report生成

**统计各能力的体现情况**:
```python
def generate_ability_coverage_report(
    expert_outputs: List[Dict]
) -> Dict:
    """生成能力覆盖报告"""

    ability_stats = {f"A{i}": {"experts": [], "manifestations": 0} for i in range(1, 13)}

    for output in expert_outputs:
        expert_id = output["role_id"]

        # 从ability_validation中提取能力体现
        if "ability_validation" in output:
            for ability_result in output["ability_validation"]["abilities_validated"]:
                ability_id = ability_result["ability_id"]

                if ability_result["passed"]:
                    ability_stats[ability_id]["experts"].append(expert_id)
                    ability_stats[ability_id]["manifestations"] += 1

    # 计算覆盖率
    coverage_report = {}
    for ability_id, stats in ability_stats.items():
        total_expected = get_expected_expert_count(ability_id)
        coverage_rate = len(stats["experts"]) / total_expected if total_expected > 0 else 0

        coverage_report[ability_id] = {
            "ability_name": ABILITY_NAMES[ability_id],
            "expert_count": len(stats["experts"]),
            "expected_count": total_expected,
            "coverage_rate": coverage_rate,
            "status": (
                "sufficient" if coverage_rate >= 0.80 else
                "weak" if coverage_rate >= 0.50 else
                "critical"
            ),
            "participating_experts": stats["experts"]
        }

    return coverage_report
```

**输出示例**:
```json
{
  "A1": {
    "ability_name": "Concept Architecture",
    "expert_count": 3,
    "expected_count": 5,
    "coverage_rate": 0.60,
    "status": "weak",
    "participating_experts": [
      "v2_design_director",
      "v3_narrative_expert",
      "v4_design_researcher"
    ]
  },
  "A9": {
    "ability_name": "Social Structure Modeling",
    "expert_count": 1,
    "expected_count": 1,
    "coverage_rate": 1.00,
    "status": "sufficient",
    "participating_experts": ["v7_emotional_insight_expert"]
  }
}
```

#### Layer 3: Expert Performance Analysis

**专家级评分**:
```python
def analyze_expert_performance(
    expert_outputs: List[Dict]
) -> Dict[str, Dict]:
    """分析专家表现"""

    performance_report = {}

    for output in expert_outputs:
        expert_id = output["role_id"]

        if "ability_validation" in output:
            validation = output["ability_validation"]

            # 计算能力级评分
            ability_scores = {}
            for ability_result in validation["abilities_validated"]:
                ability_scores[ability_result["ability_id"]] = {
                    "score": ability_result["score"],
                    "passed": ability_result["passed"]
                }

            # 质量等级评估
            overall_score = validation["overall_score"]
            quality_level = (
                "excellent" if overall_score >= 0.85 else
                "good" if overall_score >= 0.70 else
                "fair" if overall_score >= 0.55 else
                "poor"
            )

            performance_report[expert_id] = {
                "overall_score": overall_score,
                "quality_level": quality_level,
                "ability_scores": ability_scores,
                "passed_abilities": validation["summary"]["abilities_passed"],
                "total_abilities": validation["summary"]["total_abilities_checked"],
                "pass_rate": validation["summary"]["abilities_passed"] /
                             validation["summary"]["total_abilities_checked"]
            }

    return performance_report
```

**协同效果评估**:
```python
def evaluate_expert_synergy(
    detected_modes: List[Dict],
    expert_outputs: List[Dict]
) -> Dict:
    """评估专家协同效果"""

    synergy_report = {}

    # M1模式协同评估
    if any(m["mode_id"] == "M1" for m in detected_modes):
        v2_output = next((o for o in expert_outputs if o["role_id"] == "v2_design_director"), None)
        v3_output = next((o for o in expert_outputs if o["role_id"] == "v3_narrative_expert"), None)

        if v2_output and v3_output:
            # 检查A1+A3协同
            v2_has_a1 = any(
                a["ability_id"] == "A1" and a["passed"]
                for a in v2_output.get("ability_validation", {}).get("abilities_validated", [])
            )
            v3_has_a3 = any(
                a["ability_id"] == "A3" and a["passed"]
                for a in v3_output.get("ability_validation", {}).get("abilities_validated", [])
            )

            synergy_report["M1_V2_V3"] = {
                "mode": "M1 概念驱动型",
                "experts": ["v2_design_director", "v3_narrative_expert"],
                "target_abilities": ["A1", "A3"],
                "synergy_achieved": v2_has_a1 and v3_has_a3,
                "coverage": "A1+A3" if (v2_has_a1 and v3_has_a3) else "部分覆盖"
            }

    return synergy_report
```

#### Layer 4: Final Validation Report

**P3数据收集输出示例** (完整验证报告):
```markdown
================================================================================
🎉 P3数据收集与分析完成！
   结果目录: D:\11-20\langgraph-design\tests\results\p3_validation_data
================================================================================

整体统计:
  总验证数: 280 (28专家 × 10场景 × 1质量)
  整体通过率: 56.2%
  平均分数: 0.562

模式分析:
  M1 (概念驱动): 60.0% (avg: 59.8%)
  M2 (功能效率): 51.4% (avg: 47.8%)
  M3 (情绪体验): 57.0% (avg: 57.0%)
  M4 (资产资本): 51.3% (avg: 47.7%)
  M5 (乡建在地): 66.8% (avg: 61.8%)
  M6 (城市更新): 43.5% (avg: 43.5%)
  M7 (技术整合): 57.5% (avg: 57.5%)
  M8 (极端环境): 80.2% (avg: 72.5%)  ✅ 最高
  M9 (社会结构): 62.9% (avg: 58.1%)
  M10 (未来推演): 45.0% (avg: 45.0%)

能力分析:
  A1 (概念建构): 58.0% (avg, n=52)
  A3 (叙事节奏): 58.8% (avg, n=40)
  A4 (材料系统): 50.1% (avg, n=32)
  A8 (技术整合): 68.3% (avg, n=40)  ✅ 最高
  A9 (社会关系): 54.0% (avg, n=40)

失败模式分析:
  高频缺失字段 (Top 5):
    narrative_design: 44次
    conceptual_foundation: 40次
    tech_integration: 40次
    spatial_analysis: 36次
    capital_analysis: 28次

  高频缺失关键词 (Top 5):
    精神主轴: 68次
    思想: 68次
    理念: 68次
    叙事: 44次
    母题: 40次

  高频失败检查 (Top 5):
    A1:depth_score: 68次  ← 概念深度不足
    A1:required_fields: 47次
    A3:required_fields: 44次
    A3:keyword_density: 44次

优化建议:
  1. [高优] 整体质量: 整体通过率56.2%，低于70%目标
     → 建议全面检查专家system_prompt，确保明确要求输出能力相关内容

  2. [中优] 能力质量: A1/A7能力平均分<70%
     → 建议优化这些能力对应专家的输出结构，增强相关字段和关键词

  3. [中优] 验证规则: A1:depth_score失败率70%，超过50%
     → 建议降低该检查项阈值或优化专家输出指导
```

---

## 🎓 四层协同的核心价值

### 1. **理论与实践的桥梁**

```
理论层 (Layer 1+2)        实践层 (Layer 3+4)
     │                          │
10 Mode Engine ────┬──────→ 专家选择策略
     │             │             │
12 Ability Core ───┴──────→ 能力验证框架
```

### 2. **质量的可量化追踪**

```
需求分析 → 预判能力需求 (Layer 2)
    ↓
任务分配 → 匹配能力专家 (Layer 3)
    ↓
任务执行 → 注入能力prompt (Layer 2)
    ↓
输出验证 → 验证能力体现 (Layer 4)
    ↓
覆盖报告 → 统计能力分布 (Layer 2)
```

### 3. **系统的自我进化能力**

```
P3数据收集 → 发现能力缺口 (Layer 2)
    ↓
P1能力补充 → 新增专家配置 (Layer 3)
    ↓
P2验证框架 → 持续质量监控 (Layer 4)
    ↓
能力注入优化 → prompt迭代升级 (Layer 2)
```

---

## 📊 四层协同效果实证

### 当前系统状态 (2026-02-13)

| 指标 | 数值 | 目标 | 状态 |
|------|------|------|------|
| **Layer 1 覆盖** | 10/10模式 | 10/10 | ✅ 100% |
| **Layer 2 覆盖** | 12/12能力 | 12/12 | ✅ 100% |
| **Layer 3 覆盖** | 14专家 | 14+ | ✅ 达标 |
| **Layer 4 验证率** | 56.2% | 70% | ⚠️ 待提升 |

### 关键成果

1. **Layer 1-2映射完整** ✅
   - 10 Mode Engine → 12 Ability Core映射100%覆盖
   - 每个模式都有明确的主能力和辅助能力定义

2. **Layer 2-3匹配改善** ✅
   - P1补充前：58.3%能力有专家 → P1补充后：100.0%
   - 关键缺口填补：A4材料、A6功能、A7资本、A8技术、A11运营

3. **Layer 3-4验证集成** ✅
   - P2验证框架已集成到workflow（v7.900+）
   - 实时验证专家输出能力体现
   - 生成详细的验证报告和优化建议

4. **全链路可观测** ✅
   - 需求分析：Mode Detection输出
   - 任务分配：Ability-Task映射记录
   - 任务执行：Ability Injection日志
   - 输出验证：Validation Report完整追踪

---

## 🔮 未来优化方向

### Short-term (1-2周)

1. **提升验证通过率** (当前56.2% → 目标70%+)
   - 优化专家system_prompt，强化能力输出要求
   - 调整验证规则阈值（尤其A1:depth_score）
   - 增强能力注入prompt的具体性

2. **完善能力缺口填补**
   - A10环境适应：考虑新增"可持续设计专家"(v6_6补充)
   - A12文明表达：明确V4研究专家定位

### Mid-term (1-2月)

3. **能力成长机制**
   - 从历史项目中学习（expert_knowledge_base）
   - 基于验证结果自动优化prompt
   - 建立能力成熟度进化路径

4. **协同效果量化**
   - 专家协同评分系统
   - 最优协同模式库
   - 自动推荐协同配置

### Long-term (3-6月)

5. **能力可视化系统**
   - 能力热力图（12 Ability Core分布）
   - 专家能力雷达图
   - 项目能力需求vs实际覆盖对比

6. **智能任务分配**
   - 基于历史表现的专家推荐
   - 能力-任务最优匹配算法
   - 动态专家池管理

---

## 📚 参考文档

1. **理论基础**
   - [10_Mode_Engine](./sf/10_Mode_Engine) - 设计模式完整定义
   - [12_Ability_Core](./sf/12_Ability_Core) - 能力体系完整定义
   - [ABILITY_CORE_DEEP_ANALYSIS.md](./ABILITY_CORE_DEEP_ANALYSIS.md) - 88页深度分析

2. **实施报告**
   - [P1_SUPPLEMENT_COMPLETION_REPORT.md](./P1_SUPPLEMENT_COMPLETION_REPORT.md) - Layer 3专家补充
   - [P2_IMPLEMENTATION_SUMMARY.md](./P2_IMPLEMENTATION_SUMMARY.md) - Layer 4验证框架
   - [P3_IMPLEMENTATION_REPORT.md](./P3_IMPLEMENTATION_REPORT.md) - 数据收集与分析

3. **架构文档**
   - [ARCHITECTURE_OPTIMIZATION_v7.900.md](./ARCHITECTURE_OPTIMIZATION_v7.900.md) - 强制执行Phase2+问卷
   - [docs/AGENT_ARCHITECTURE.md](./docs/AGENT_ARCHITECTURE.md) - Agent层次结构

---

**文档维护**: 本文档随系统演进持续更新
**最后更新**: 2026-02-13
**贡献者**: Architecture Analysis Team
