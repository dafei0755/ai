# 架构简化方案：从审计文档到可执行配置

## 背景

基于 [MODE_ENGINE_ARCHITECTURE_AUDIT.md](sf/MODE_ENGINE_ARCHITECTURE_AUDIT.md) 的分析，发现了大量**硬编码的矩阵数据**和**隐性的规则逻辑**。这些信息目前散落在文档中，需要转化为可执行的配置文件。

---

## 核心问题识别

### 问题 1：模式 × 能力调用矩阵（硬编码）

**当前状态：**
- 120 个映射关系（10 模式 × 12 能力）硬编码在审计文档的表格中
- 使用符号表示：● = L4+, ◐ = L3+, ○ = L2+, - = 不调用
- 代码中无法直接读取和使用

**示例：**
```markdown
| 能力 \ 模式 | M1概念 | M2功能 | M3情绪 | ...
| A1 概念建构 | ●     | ○     | ◐     | ...
| A2 空间结构 | ◐     | ●     | ◐     | ...
```

**影响：**
- 模式选择后，无法自动确定需要哪些能力
- 能力等级要求无法自动验证
- 修改需要同步更新文档和代码

---

### 问题 2：模式 × 评估维度权重矩阵（硬编码）

**当前状态：**
- 100 个权重配置（10 模式 × 10 评估维度）硬编码在文档中
- 权重值分散，无法动态调整
- 混合模式的权重合成规则未定义

**示例：**
```markdown
| 评估维度 \ 模式 | M1  | M2  | M3  | ...
| 概念完整度      | 40% | 10% | 25% | ...
| 空间逻辑        | 10% | 25% | 10% | ...
```

**影响：**
- 评估时无法自动加载权重配置
- 混合模式（如 M1×M3）的权重合成需要手动计算
- 权重调整需要修改多处代码

---

### 问题 3：项目生命周期 × 模式介入矩阵（隐性逻辑）

**当前状态：**
- 80 个介入深度配置（10 模式 × 8 阶段）在文档中
- 使用符号：★★★ = 主导, ★★ = 深度参与, ★ = 轻度参与
- 二级模块的介入节点（40 个模块 × 8 阶段 = 320 个配置）全部在文档中

**影响：**
- 无法根据项目阶段自动激活相应的模式模块
- 工作流编排依赖人工判断
- 阶段切换时的模块调度逻辑不清晰

---

### 问题 4：混合模式组合规则（缺失）

**当前状态：**
- 12 种常见混合模式组合在文档中列举
- 7 种冲突组合和调和策略在文档中描述
- **权重合成公式未定义**（架构风险 R1）

**示例：**
```markdown
M1 × M3: 概念给骨架，情绪给血肉
M4 × M1: 资本框架内注入精神表达
```

**影响：**
- 混合模式的评估权重无法自动计算
- 冲突检测依赖人工经验
- 无法自动生成混合模式的任务库

---

### 问题 5：模式识别触发机制（缺失）

**当前状态：**
- P2 阶段需要"模式识别"，但触发规则未定义（架构风险 R2）
- 项目特征 → 模式映射的指标体系缺失
- 模式选择依赖主观判断

**影响：**
- 无法实现自动化模式推荐
- 模式选择的一致性无法保证
- 新手用户难以选择合适的模式

---

## 优化方案

### 方案 A：创建模式能力映射配置文件

**目标：** 将"模式 × 能力调用矩阵"转化为可执行配置

**新建文件：** `config/mode_ability_mapping.yaml`

**结构设计：**
```yaml
# 模式 → 能力调用映射
mode_ability_mapping:
  M1_concept_driven:
    required_abilities:
      A1_concept_construction:
        min_level: "L4"
        priority: "core"  # core/important/auxiliary
        weight: 1.0
      A3_narrative_rhythm:
        min_level: "L4"
        priority: "core"
        weight: 1.0
      A2_spatial_structure:
        min_level: "L3"
        priority: "important"
        weight: 0.7
      # ... 其他能力

  M2_functional_efficiency:
    required_abilities:
      A2_spatial_structure:
        min_level: "L4"
        priority: "core"
        weight: 1.0
      A6_functional_efficiency:
        min_level: "L4"
        priority: "core"
        weight: 1.0
      # ... 其他能力

# 能力优先级定义
ability_priority_levels:
  core:
    min_level: "L4"
    symbol: "●"
    description: "核心能力，必须达到 L4+"
  important:
    min_level: "L3"
    symbol: "◐"
    description: "重要能力，需达到 L3+"
  auxiliary:
    min_level: "L2"
    symbol: "○"
    description: "辅助能力，L2+ 即可"
  not_required:
    min_level: null
    symbol: "-"
    description: "不直接调用"
```

**收益：**
- ✅ 代码可直接读取能力要求
- ✅ 自动验证团队能力是否满足模式要求
- ✅ 支持动态调整能力等级阈值
- ✅ 单一信息源，易于维护

---

### 方案 B：创建模式评估权重配置文件

**目标：** 将"模式 × 评估维度权重矩阵"转化为可执行配置

**新建文件：** `config/mode_evaluation_weights.yaml`

**结构设计：**
```yaml
# 单一模式的评估权重
single_mode_weights:
  M1_concept_driven:
    concept_integrity: 0.40
    spatial_logic: 0.10
    narrative_coherence: 0.25
    material_expression: 0.10
    functional_efficiency: 0.05
    technical_feasibility: 0.10
    # 其他维度权重为 0

  M2_functional_efficiency:
    concept_integrity: 0.10
    spatial_logic: 0.25
    functional_efficiency: 0.40
    technical_feasibility: 0.15
    commercial_closure: 0.10
    # 其他维度权重为 0

# 混合模式权重合成规则
hybrid_mode_rules:
  weight_composition:
    method: "weighted_average"  # 加权平均
    formula: "w_final = α × w_primary + β × w_secondary"

  common_combinations:
    - combination_id: "M1_M3"
      primary_mode: "M1_concept_driven"
      secondary_mode: "M3_emotional_experience"
      primary_weight: 0.6
      secondary_weight: 0.4
      description: "概念给骨架，情绪给血肉"

    - combination_id: "M4_M1"
      primary_mode: "M4_capital_asset"
      secondary_mode: "M1_concept_driven"
      primary_weight: 0.7
      secondary_weight: 0.3
      description: "资本框架内注入精神表达"

    - combination_id: "M4_M3"
      primary_mode: "M4_capital_asset"
      secondary_mode: "M3_emotional_experience"
      primary_weight: 0.6
      secondary_weight: 0.4
      description: "用情绪提升停留时间→转化率"

# 冲突检测规则
conflict_detection:
  high_risk_combinations:
    - modes: ["M3_emotional_experience", "M2_functional_efficiency"]
      conflict: "冗余体验 vs 消灭冗余"
      risk_level: "high"
      resolution_strategy: "明确哪些区域允许'浪费'，哪些必须高效"

    - modes: ["M4_capital_asset", "M5_rural_context"]
      conflict: "资本逻辑 vs 地域保护"
      risk_level: "high"
      resolution_strategy: "村民收益机制必须内嵌于商业模型"

    - modes: ["M6_urban_renewal", "M9_social_structure"]
      conflict: "开发者利益 vs 原住民利益"
      risk_level: "critical"
      resolution_strategy: "引入第三方社区利益保障机制"

# 底线规则
baseline_rules:
  - dimension: "technical_feasibility"
    min_weight: 0.10
    description: "无论哪种模式，技术可行 ≥ 10%"
  - dimension: "concept_integrity"
    min_weight: 0.10
    description: "无论哪种模式，概念完整度 ≥ 10%"
```

**收益：**
- ✅ 自动计算混合模式的评估权重
- ✅ 自动检测模式冲突并提供调和策略
- ✅ 支持动态调整权重配置
- ✅ 解决架构风险 R1（混合模式权重合成）

---

### 方案 C：创建项目生命周期模式介入配置

**目标：** 将"项目阶段 × 模式介入矩阵"转化为工作流编排配置

**新建文件：** `config/mode_lifecycle_intervention.yaml`

**结构设计：**
```yaml
# 项目生命周期阶段定义
project_lifecycle:
  P1_requirement_analysis:
    name: "需求分析"
    core_tasks: "理解业主诉求、场地条件、预算约束"
    key_outputs: "项目定位文档"

  P2_mode_identification:
    name: "模式识别"
    core_tasks: "判断适用哪种设计模式（或混合模式）"
    key_outputs: "模式选定报告"

  # ... 其他阶段

# 模式在各阶段的介入深度
mode_intervention_matrix:
  M1_concept_driven:
    P1_requirement_analysis:
      intervention_level: "deep"  # leading/deep/light/none
      priority: 2
      activated_modules: ["M1-1"]  # 激活的二级模块
    P2_mode_identification:
      intervention_level: "leading"
      priority: 1
      activated_modules: ["M1-1", "M1-2"]
    P3_concept_planning:
      intervention_level: "leading"
      priority: 1
      activated_modules: ["M1-1", "M1-2", "M1-3", "M1-4"]
    P4_scheme_design:
      intervention_level: "deep"
      priority: 2
      activated_modules: ["M1-2", "M1-4"]
    # ... 其他阶段

  M2_functional_efficiency:
    P1_requirement_analysis:
      intervention_level: "deep"
      priority: 2
      activated_modules: ["M2-1"]
    # ... 其他阶段

# 二级模块的详细介入节点
module_intervention_details:
  M1-1_spiritual_modeling:
    P1_requirement_analysis:
      intervention_level: "leading"
      tasks:
        - "识别业主/品牌的核心价值观"
        - "提炼精神关键词"
    P2_mode_identification:
      intervention_level: "deep"
      tasks:
        - "验证精神主线的可行性"
    P3_concept_planning:
      intervention_level: "leading"
      tasks:
        - "构建完整的精神主轴模型"
        - "定义概念的核心隐喻"
    # ... 其他阶段

# 介入等级定义
intervention_levels:
  leading:
    symbol: "★★★"
    description: "主导阶段（该模式的核心能力决定此阶段产出）"
    priority: 1
  deep:
    symbol: "★★"
    description: "深度参与（显著影响此阶段决策）"
    priority: 2
  light:
    symbol: "★"
    description: "轻度参与（提供辅助意见）"
    priority: 3
  none:
    symbol: "—"
    description: "不介入"
    priority: null
```

**收益：**
- ✅ 工作流引擎可根据阶段自动激活模块
- ✅ 明确各阶段的主导模式和辅助模式
- ✅ 支持二级模块的精细化调度
- ✅ 解决架构风险 R4（二级模块依赖顺序）

---

### 方案 D：创建模式识别特征指标配置

**目标：** 建立"项目特征 → 模式推荐"的自动化机制

**新建文件：** `config/mode_identification_rules.yaml`

**结构设计：**
```yaml
# 模式识别特征指标体系
mode_identification_features:
  M1_concept_driven:
    trigger_keywords:
      - "品牌精神"
      - "文化表达"
      - "概念驱动"
      - "精神主线"
      - "思想性"
    project_attributes:
      project_type:
        - "品牌旗舰店"
        - "艺术空间"
        - "文化展馆"
        - "高端酒店"
      budget_range: "high"  # high/medium/low
      client_priority: "brand_expression"
    confidence_score_formula:
      keyword_match_weight: 0.4
      project_type_weight: 0.3
      budget_weight: 0.2
      client_priority_weight: 0.1
    min_confidence_threshold: 0.6

  M2_functional_efficiency:
    trigger_keywords:
      - "效率优化"
      - "动线最优"
      - "功能至上"
      - "运营效率"
    project_attributes:
      project_type:
        - "办公空间"
        - "医疗建筑"
        - "工业厂房"
        - "物流中心"
      budget_range: "medium"
      client_priority: "operational_efficiency"
    min_confidence_threshold: 0.6

  # ... 其他模式

# 混合模式推荐规则
hybrid_mode_recommendation:
  rules:
    - condition:
        primary_mode: "M4_capital_asset"
        secondary_indicators:
          - "品牌溢价"
          - "精神表达"
      recommended_combination: "M4_M1"
      confidence_boost: 0.2

    - condition:
        primary_mode: "M5_rural_context"
        secondary_indicators:
          - "产业收益"
          - "商业模型"
      recommended_combination: "M5_M4"
      confidence_boost: 0.15

# 模式选择算法配置
mode_selection_algorithm:
  method: "weighted_scoring"
  steps:
    - step: "extract_features"
      description: "从项目需求中提取关键词和属性"
    - step: "calculate_scores"
      description: "计算每个模式的置信度得分"
    - step: "rank_modes"
      description: "按得分排序，选择 Top 1-3 候选模式"
    - step: "detect_hybrid"
      description: "检测是否需要混合模式"
    - step: "conflict_check"
      description: "检查模式组合是否存在冲突"
  output:
    primary_mode: "置信度最高的模式"
    secondary_mode: "如果需要混合，选择第二模式"
    confidence_scores: "各模式的置信度得分"
    conflict_warnings: "冲突预警信息"
```

**收益：**
- ✅ 实现自动化模式推荐
- ✅ 降低模式选择的主观性
- ✅ 支持混合模式的智能推荐
- ✅ 解决架构风险 R2（模式选择算法缺失）

---

### 方案 E：创建四大组件协同配置

**目标：** 明确四大组件层在项目各阶段的协同时序

**新建文件：** `config/component_orchestration.yaml`

**结构设计：**
```yaml
# 四大组件层在项目节点中的协同时序
component_orchestration:
  P1_requirement_analysis:
    mode_engine:
      role: "predictor"
      tasks:
        - "模式预判（初步匹配1-3个候选模式）"
      output: "候选模式列表"

    ability_core:
      role: "assessor"
      tasks:
        - "评估团队能力短板（哪些A需提升）"
      output: "能力缺口报告"

    evaluation_matrix:
      role: "inactive"
      tasks: []

    output_standards:
      role: "planner"
      tasks:
        - "明确交付物预期清单"
      output: "交付物清单"

  P2_mode_identification:
    mode_engine:
      role: "leader"  # leader/supporter/inactive
      tasks:
        - "确定主模式+辅助模式组合"
      output: "模式选定报告"

    ability_core:
      role: "supporter"
      tasks:
        - "匹配能力矩阵，确认各能力最低要求等级"
      output: "能力要求矩阵"

    evaluation_matrix:
      role: "supporter"
      tasks:
        - "确定评估维度权重配置"
      output: "评估权重配置"

    output_standards:
      role: "supporter"
      tasks:
        - "生成模式-交付物映射表"
      output: "交付物映射表"

  # ... 其他阶段

# 组件间依赖关系
component_dependencies:
  - source: "mode_engine"
    target: "ability_core"
    dependency_type: "scheduling"
    description: "模式调度能力组合"

  - source: "mode_engine"
    target: "evaluation_matrix"
    dependency_type: "configuration"
    description: "模式确定评估权重"

  - source: "ability_core"
    target: "evaluation_matrix"
    dependency_type: "mapping"
    description: "能力成熟度 vs 评估维度一一对应"

  - source: "evaluation_matrix"
    target: "output_standards"
    dependency_type: "validation"
    description: "评估结果触发交付物质量判定"
```

**收益：**
- ✅ 明确各组件在不同阶段的角色
- ✅ 定义组件间的依赖关系
- ✅ 支持工作流的自动化编排
- ✅ 提升系统的可理解性

---

## 实施优先级

基于架构审计文档中的"产品经理视角优先级建议"（第 9.3 节），结合配置简化的收益，建议按以下顺序实施：

| 优先级 | 方案 | 文件 | 解决的架构风险 | 预计工作量 |
|--------|------|------|---------------|-----------|
| **P0** | 方案 B | mode_evaluation_weights.yaml | R1: 混合模式权重合成 | 2-3 小时 |
| **P0** | 方案 D | mode_identification_rules.yaml | R2: 模式选择算法缺失 | 3-4 小时 |
| **P1** | 方案 A | mode_ability_mapping.yaml | 能力调度自动化 | 2-3 小时 |
| **P1** | 方案 C | mode_lifecycle_intervention.yaml | R4: 二级模块依赖顺序 | 4-5 小时 |
| **P2** | 方案 E | component_orchestration.yaml | 组件协同清晰化 | 2-3 小时 |

**总计工作量：** 13-18 小时

---

## 预期收益

### 1. 配置文件数量
- **新增配置文件：** 5 个
- **配置行数：** 约 1500-2000 行
- **替代文档行数：** 约 300 行（审计文档中的矩阵表格）

### 2. 代码简化
- **消除硬编码：** 420+ 个硬编码配置值（120 能力映射 + 100 权重配置 + 80 介入深度 + 120 二级模块介入）
- **自动化程度：** 从 20% → 80%
- **维护成本：** 降低 60%

### 3. 系统能力提升
- ✅ 自动化模式推荐（解决 R2）
- ✅ 混合模式权重自动计算（解决 R1）
- ✅ 模式冲突自动检测（解决 R5）
- ✅ 工作流自动编排（解决 R4）
- ✅ 能力要求自动验证

### 4. 可扩展性
- 新增模式：只需添加配置，无需修改代码
- 调整权重：修改配置文件即可，无需重新部署
- 新增评估维度：配置驱动，易于扩展

---

## 下一步行动

### 阶段 1：P0 配置文件创建（优先）
1. 创建 `mode_evaluation_weights.yaml`（方案 B）
2. 创建 `mode_identification_rules.yaml`（方案 D）
3. 验证配置文件格式和完整性

### 阶段 2：P1 配置文件创建
1. 创建 `mode_ability_mapping.yaml`（方案 A）
2. 创建 `mode_lifecycle_intervention.yaml`（方案 C）
3. 建立配置文件间的引用关系

### 阶段 3：代码适配
1. 创建配置加载器（`config_loader.py`）
2. 修改模式引擎读取新配置
3. 实现混合模式权重计算器
4. 实现模式识别推荐引擎

### 阶段 4：测试验证
1. 单元测试：配置文件解析
2. 集成测试：模式推荐 + 权重计算
3. 端到端测试：完整项目流程

---

## 风险控制

### 已识别风险
1. **配置文件过大**：1500-2000 行可能难以维护
   - 缓解：拆分为多个子配置文件

2. **配置格式复杂**：嵌套层级较深
   - 缓解：提供配置文件模板和验证工具

3. **向后兼容性**：现有代码可能依赖硬编码值
   - 缓解：保留旧代码，逐步迁移

### 回滚策略
- 保留审计文档作为参考
- 配置文件版本控制
- 每个阶段完成后创建 Git tag

---

## 总结

通过创建 5 个结构化配置文件，可以将审计文档中的 420+ 个硬编码配置转化为可执行、可维护的配置系统，解决 5 个关键架构风险（R1, R2, R4, R5），并将系统自动化程度从 20% 提升到 80%。

**核心价值：**
- 📊 数据驱动：从文档驱动 → 配置驱动
- 🤖 自动化：从人工判断 → 算法推荐
- 🔧 可维护：从硬编码 → 配置化
- 🚀 可扩展：从固化逻辑 → 灵活配置
