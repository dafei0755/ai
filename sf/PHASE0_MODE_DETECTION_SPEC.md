# 阶段 0：模式检测（Mode Detection）— 详细说明

> 模式检测是整个方法论流水线的**第一道结构性决策**。
> 它决定了后续所有组件（能力注入、任务分解、评估权重、输出标准）的调度方向。

---

## 一、定位与职责

### 1.1 在流水线中的位置

```
用户输入
  │
  ▼
┌─────────────────────────────────────────┐
│  P0 ─ 模式检测（本文档）                    │
│  节点: requirements_analyst (Phase 1)      │
│  执行: HybridModeDetector.detect_sync()    │
└────────────────┬────────────────────────┘
                 │ detected_design_modes
                 │ project_classification
                 ▼
┌────────────────────────────────────────────────┐
│  P1 ─ 需求分析 & 信息质量判定                      │
│  · 模式感知信息质量调整 (mode_info_adjuster)        │
│  · 加权投票 (_weighted_info_status_vote)          │
└────────────────┬───────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────┐
│  P2 ─ 三步递进式问卷                              │
│  · progressive_step1 → step2 → step3           │
└────────────────┬───────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────┐
│  P3 ─ 项目总监（project_director）                │
│  · 读取 project_classification                  │
│  · 选择分析框架（ability_core / multi_scale …）   │
│  · 注入模式特定任务                               │
└────────────────┬───────────────────────────────┘
                 │
                 ▼
        batch_executor → experts → aggregator → report
```

### 1.2 核心职责

| 职责 | 说明 |
|------|------|
| **识别主模式** | 从 10 种设计模式中确定 primary_mode |
| **识别辅助模式** | 检出 secondary_modes（最多 2 个） |
| **输出置信度** | 每个模式附带 0–1 的 confidence 分数 |
| **驱动下游调度** | 所有后续节点通过 `project_classification` 统一读取模式结果 |

### 1.3 设计原则

> **"模式（Mode）是策略方向——决定'用什么方式做这个项目'。**
> **能力（Ability）是执行技能——决定'设计师需要什么本事'。**
> **模式调度能力，而非等于能力。"**
> — sf/10_Mode_Engine

---

## 二、检测架构：三层类体系

```
┌──────────────────────────────────────────────┐
│  HybridModeDetector            [入口层]       │
│  ├─ detect_sync()   → 同步：仅关键词          │
│  └─ detect()        → 异步：关键词 + LLM      │
├──────────────────────────────────────────────┤
│  DesignModeDetector            [关键词层]      │
│  └─ detect()                                  │
│     · MODE_SIGNATURES（10个模式特征字典）        │
│     · 关键词/场景匹配 → 评分 → 归一化 → 过滤    │
├──────────────────────────────────────────────┤
│  AdvancedModeDetector          [LLM精判层]     │
│  └─ detect_with_llm()                         │
│     · gpt-4o-mini, temperature=0.3            │
│     · 接受关键词层 Top 5 候选 → JSON 输出       │
└──────────────────────────────────────────────┘
```

**当前主路径**（requirements_analyst Phase 1）使用的是 `detect_sync()`，即**纯关键词检测**，不依赖 LLM，确保速度和确定性。

---

## 三、10 个模式的特征签名

### 3.1 MODE_SIGNATURES 数据结构

每个模式在 `DesignModeDetector.MODE_SIGNATURES` 中定义四个字段：

```python
{
    "M1_concept_driven": {
        "name": "概念驱动型设计",
        "keywords": [...],          # 正向关键词（30+个）
        "scenarios": [...],         # 场景短语（15-20个）
        "anti_keywords": [...],     # 反向关键词（惩罚项）
        "weight": 1.2               # 模式权重系数
    },
    ...
}
```

### 3.2 各模式权重与定位

| 模式 ID | 中文名 | weight | 设计意图 |
|---------|--------|--------|----------|
| `M1_concept_driven` | 概念驱动型 | **1.2** | 精神表达类项目信号明确时给予加权 |
| `M2_function_efficiency` | 功能效率型 | 1.0 | 基准模式，也是**无法识别时的默认回退** |
| `M3_emotional_experience` | 情绪体验型 | **1.1** | 体验类项目微弱加权 |
| `M4_capital_asset` | 资产资本型 | 1.0 | 商业项目无额外加权 |
| `M5_rural_context` | 乡建在地型 | **1.3** | 乡建信号通常更稀疏、需要提升灵敏度 |
| `M6_urban_regeneration` | 城市更新型 | **1.2** | 城更类信号加权 |
| `M7_tech_integration` | 技术整合型 | **1.1** | 智能化信号微弱加权 |
| `M8_extreme_condition` | 极端环境型 | **1.5** | 极端环境项目最高加权——生存安全不可漏判 |
| `M9_social_structure` | 社会结构型 | **1.3** | 关系类信号通常隐含、需高灵敏度 |
| `M10_future_speculation` | 未来推演型 | 1.0 | 基准权重 |

> **设计逻辑**：`weight > 1.0` 意味着"宁可误报，不可漏报"——极端环境（1.5）和社会结构（1.3）如果被漏判，后果最严重。

### 3.3 关键词示例（M1 概念驱动型）

```python
"keywords": [
    "概念", "精神", "品牌", "文化母题", "表达", "哲学", "身份",
    "艺术", "旗舰", "灵魂", "思想", "价值观", "内在冲突", "自我认同",
    "内涵", "底层逻辑", "本质", "信仰", "理念", "精神内核",
    "文化传承", "符号系统", "意象", "隐喻", "诗意", "意境",
    "禅意", "东方美学", "西方哲学", "叙事", "故事", "主题",
    "象征", "仪式感", "归属感", "认同", "根", "乡愁"
],
"anti_keywords": [
    "效率", "成本", "回报", "坪效", "翻台率", "客单价",
    "投资回报", "盈利模式", "商业模式", "ROI", "成本控制"
]
```

### 3.4 正/反关键词的博弈

反向关键词机制确保模式之间的**互斥性**：
- M1（概念驱动）的 anti_keywords 包含 M4（资本型）的核心词
- M4 的 anti_keywords 包含 M1 的精神类词汇
- 当两组词同时大量出现，双方分数互相压制 → 置信度差缩小 → 触发**混合模式**判定

---

## 四、核心评分算法

### 4.1 `DesignModeDetector.detect()` 完整逻辑

```
对用户输入文本（+可选的 structured_requirements 扩展文本）：

FOR 每个模式 M:
    score = 0
    matched = []

    ① 关键词匹配
       对 M.keywords 中的每个词：
         - 长度 > 3字 → 命中得 1.5 分（词组更具辨识度）
         - 长度 ≤ 3字 → 命中得 1.0 分（短词可能歧义）

    ② 场景匹配
       对 M.scenarios 中的每个短语：
         - 命中得 2.5 分（场景比单词更精确）

    ③ 反向惩罚
       对 M.anti_keywords 中的每个词：
         - 命中扣 1.0 分
       score = max(0, score - anti_penalty)

    ④ 模式权重
       weighted_score = score × M.weight

    ⑤ 归一化
       confidence = min(weighted_score / 6.0, 1.0)
       （6 分为满分阈值：约等于匹配 2-3 个关键词 + 1 个场景）

    ⑥ 过滤
       confidence ≥ 0.30 才保留
       （v7.623 从 0.25 提升到 0.30，减少噪声）

SORT by confidence DESC
RETURN Top N
```

### 4.2 评分公式图示

```
                关键词得分           场景得分           反向惩罚
                ┌────────┐         ┌────────┐         ┌────────┐
                │ Σ 1.0  │         │ Σ 2.5  │         │ Σ -1.0 │
                │ 或 1.5  │         │ /match │         │ /match │
                └───┬────┘         └───┬────┘         └───┬────┘
                    │                   │                   │
                    └───────────┬───────┘                   │
                                │                           │
                          raw_score = Σ(kw + sc)            │
                                │                           │
                          score = max(0, raw - anti_penalty)│
                                │   ◄───────────────────────┘
                                │
                          × weight (1.0 ~ 1.5)
                                │
                          ÷ 6.0 (归一化)
                                │
                          min(result, 1.0)
                                │
                          confidence ≥ 0.30 ?
                          ├── YES → 保留
                          └── NO  → 丢弃
```

### 4.3 上下文扩展机制

如果提供了 `structured_requirements`，会将以下字段拼接到分析文本：
```python
extended_text = user_input
if structured_requirements:
    project_type = structured_requirements.get("project_type", {})
    extended_text += " " + project_type.get("primary", "")
    extended_text += " " + project_type.get("secondary", "")
```

这使得 Phase 1 LLM 解析出的项目类型也能参与模式匹配。

---

## 五、混合模式检测与冲突解决

### 5.1 触发条件

从 `config/MODE_HYBRID_PATTERNS.yaml`：

```yaml
detection_thresholds:
  min_confidence: 0.45         # 单模式最低置信度（低于此不参与混合）
  max_confidence_gap: 0.25     # 双模式置信度差（差 < 0.25 → 视为混合模式）
  multi_mode_std_threshold: 0.15  # ≥3 模式的置信度标准差阈值
```

**判定逻辑**：
```
IF Top1.confidence - Top2.confidence < 0.25
AND Top2.confidence >= 0.45
THEN → 混合模式（Top1 为主，Top2 为辅）

IF 三模式的 std(confidences) < 0.15
AND all >= 0.45
THEN → 多模式混合
```

### 5.2 四种冲突解决策略

| 策略 | 适用场景 | 机制 |
|------|----------|------|
| **priority_based** | 存在不可妥协维度时 | 冲突维度由指定模式主导 |
| **balanced** | 冲突可调和时 | 取冲突维度的中间值 |
| **zoned** | 空间可分区时 | 不同区域由不同模式主导 |
| **phased** | 时间可分段时 | 不同阶段由不同模式主导 |

### 5.3 混合模式冲突示例

**M1 × M4（概念驱动 × 资本导向）** — 冲突级别：高

| 冲突维度 | 严重度 | 主导方 | 约束条件 |
|----------|--------|--------|----------|
| 成本控制 | 高 | M4 | 总成本不得超过资产模型预算 15% |
| 精神表达 | 高 | M1 | 概念核心区域占比不低于 30% |
| 材料选择 | 高 | balanced | 高端材料面积占比 ≤ 40% |
| 品牌溢价 | 低 | synergy | 溢价需可被客群资产模型验证 |

**M1 × M3（概念 × 情绪）** — 解决策略：synergy（协同）
> "概念提供骨架，情绪提供血肉"

**M2 × M8（效率 × 极端环境）** — 解决策略：priority_based
> "生存系统不可妥协，效率在安全基础上优化"

---

## 六、模式检测后的三级决策链

模式检测结果不直接决定最终 `info_status`，而是进入一个**三级决策链**：

```
┌──────────────────────────────────────────────┐
│ 第一级：Precheck（预检查）                      │
│ · 快速检查用户输入的基础充分性                    │
│ · 输出: is_sufficient (bool)                   │
│ · 权重: 0.4                                   │
├──────────────────────────────────────────────┤
│ 第二级：Phase 1 LLM（需求分析）                 │
│ · LLM 结构化解析项目类型/交付物/信息状态          │
│ · 输出: info_status (sufficient/insufficient)  │
│ · 权重: 0.4                                   │
├──────────────────────────────────────────────┤
│ 第三级：Mode 感知调整                           │
│ · 基于检出模式的关键信息覆盖率                    │
│ · 覆盖率 < 30% → 扣除惩罚分                    │
│ · 输出: adjusted_status                       │
│ · 权重: 0.2                                   │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
         ┌─────────────────┐
         │ 加权投票          │
         │ final_score =    │
         │   0.4×precheck   │
         │ + 0.4×phase1     │
         │ + 0.2×mode       │
         │                  │
         │ ≥ 0.5 → sufficient│
         │ < 0.5 → insufficient│
         └─────────────────┘
```

### 6.1 模式感知信息质量调整

`ModeAwareInfoQualityAdjuster` 的工作方式：

1. 将原始 status 转为基础分：`sufficient → 0.85` / `partial → 0.55` / `insufficient → 0.25`
2. 对每个高置信度模式（confidence ≥ 0.3），检查用户输入的关键词覆盖率
3. 覆盖率 < 30% → 施加惩罚分 = `missing_penalty × confidence`
4. 最终分数 → 回转为 status

**各模式的惩罚力度**：

| 模式 | quality_weight | missing_penalty | 设计意图 |
|------|---------------|----------------|----------|
| M8 极端环境 | 1.5 | **0.25** | 缺失关键环境信息=高危，强制降级 |
| M4 资本型 | 1.3 | **0.20** | 缺失财务信息=无法做资产分析 |
| M1 概念型 | 1.2 | 0.15 | 缺失精神建模信息→降级 |
| M9 社会结构 | 1.2 | 0.15 | 缺失关系信息→降级 |
| M6 城市更新 | 1.2 | 0.15 | 缺失区域信息→降级 |
| M2 功能效率 | 1.0 | 0.10 | 基准惩罚（最轻） |

### 6.2 加权投票决策规则

| 投票组合 | final_score | 结果 | 说明 |
|----------|-------------|------|------|
| Precheck✓ + Phase1✓ + Mode✓ | 1.0 | sufficient | 三方一致 |
| Precheck✓ + Phase1✓ + Mode✗ | 0.8 | sufficient | 双方强支持 |
| Precheck✓ + Phase1✗ + Mode✓ | 0.6 | sufficient | 预检+模式支持 |
| Precheck✗ + Phase1✓ + Mode✓ | 0.6 | sufficient | 分析+模式支持 |
| Precheck✓ + Phase1✗ + Mode✗ | 0.4 | **insufficient** | 仅预检通过不够 |
| Precheck✗ + Phase1✓ + Mode✗ | 0.4 | **insufficient** | 仅分析通过不够 |
| Precheck✗ + Phase1✗ + Mode✓ | 0.2 | insufficient | 仅模式调整不够 |
| Precheck✗ + Phase1✗ + Mode✗ | 0.0 | insufficient | 三方一致不足 |

> **关键设计**：至少需要**两个投票方同意**才能判定信息充足（阈值 ≥ 0.5）。

---

## 七、State 输出结构

### 7.1 `detected_design_modes`

```python
# 写入 State 的顶层 key
detected_design_modes: List[Dict] = [
    {
        "mode": "M1_concept_driven",       # 模式 ID
        "confidence": 0.85,                # 置信度 0-1
        "reason": "精神, 概念, 品牌旗舰店", # 命中的关键词/场景
        "detected_by": "keyword"           # 检测方式
    },
    {
        "mode": "M3_emotional_experience",
        "confidence": 0.62,
        "reason": "情绪, 记忆, 展示空间",
        "detected_by": "keyword"
    }
]
```

### 7.2 `project_classification`（统一分类出口）

```python
project_classification: Dict = {
    "project_type": "酒店设计",                    # LLM 解析的项目类型
    "primary_mode": "M1_concept_driven",           # 主模式 ID
    "secondary_modes": ["M3_emotional_experience"], # 次要模式（最多2个）
    "mode_confidence": 0.85,                       # 主模式置信度
    "motivation_type": "expression",               # 动机类型
    "detected_design_modes": [...]                 # 完整原始数据
}
```

**下游组件统一读取 `project_classification`**，不直接读 `detected_design_modes`。

---

## 八、下游消费：模式如何驱动整个系统

### 8.1 Mode → Ability 激活（mode_ability_activation.yaml）

```
project_classification.primary_mode = "M1_concept_driven"
               │
               ▼
  ┌─────────────────────────────┐
  │ primary_abilities:           │
  │   A1 概念建构 → 目标 L4      │
  │   A3 叙事节奏 → 目标 L4      │
  │ secondary_abilities:         │
  │   A12 文明表达 → 目标 L3     │
  │   A2 空间结构 → 目标 L3      │
  └──────────────┬──────────────┘
                 │
                 ▼
          注入 expert prompt
          └─ "核心能力要求：A1(L4) + A3(L4)"
```

**消费规则**：
- `primary_abilities` 数量 × 1.5 ≈ 最小任务数
- primary 能力必须包含 L4 判断标准
- secondary 能力作为扩展信号，专家自主决定是否深化

### 8.2 Mode → 评估权重（13_Evaluation_Matrix）

```
primary_mode = "M1_concept_driven"
               │
               ▼
  ┌─────────────────────────────┐
  │ 概念完整度  40%   ← 最高权重  │
  │ 叙事连贯度  25%              │
  │ 空间逻辑    10%              │
  │ 材料适配    10%              │
  │ 技术可行    10%   ← 底线     │
  │ 功能效率     5%              │
  └─────────────────────────────┘
```

**底线规则**：无论何种模式，技术可行 ≥ 10%，概念完整度 ≥ 10%。

### 8.3 Mode → 框架选择（analysis_frameworks.yaml）

```
primary_mode = "M1_concept_driven"
               │
               ▼
  frameworks.ability_core.trigger_modes 包含 M1
               │
               ▼
  project_director 选择 ability_core 框架
               │
               ▼
  激活 ability_core_5layer 纵深模型
  ├─ L1 表象层（200字）
  ├─ L2 策略层（250字）
  ├─ L3 机制层（300字）
  ├─ L4 批判层
  └─ L5 演化层
```

### 8.4 Mode → 交付物（14_Output_Standards）

模式决定交付物类型和验收标准：
- M1 概念型 → T2 方案型（至少 2 个可行方案 + 优劣分析）
- M4 资本型 → T3 策略型（含 ROI 模型）
- M2 功能型 → T1 信息型（准确、有出处）

---

## 九、默认回退与边界处理

### 9.1 无法识别时

当所有模式的 confidence 都 < 0.30：
```python
# 回退到默认模式
return [{
    "mode": "M2_function_efficiency",
    "confidence": 0.5,
    "reason": "默认模式（未检出明确模式信号）",
    "detected_by": "default"
}]
```

**选择 M2 作为默认的理由**：功能效率是最通用、最低风险的设计策略方向。

### 9.2 LLM 失败时

`AdvancedModeDetector` 如果 LLM 调用失败：
- 自动 fallback 到关键词检测结果
- 不中断流程

### 9.3 `detect_sync()` vs `detect()` 选择

| 方法 | 类型 | 策略 | 使用场景 |
|------|------|------|----------|
| `detect_sync()` | 同步 | 仅关键词 | **当前主路径**—Phase 1 使用 |
| `detect()` | 异步 | 关键词 + LLM | 候选 ≥ 2 时启用 LLM 精判 |

当前架构选择 `detect_sync()` 是为了：
1. **速度**：关键词检测 < 10ms
2. **确定性**：不依赖外部 LLM 调用
3. **可预测性**：结果完全由输入文本决定

---

## 十、12 Ability Core 与模式检测的关系

模式检测的输出直接决定了 12 种能力中哪些被激活以及达到什么深度：

| 模式 | primary（必须 L4+） | secondary（建议 L3+） | 最小任务数 |
|------|---------------------|----------------------|-----------|
| M1 概念驱动 | A1, A3 | A12, A2 | 3 |
| M2 功能效率 | A2, A6 | A8, A11 | 3 |
| M3 情绪体验 | A3, A5 | A1, A9 | 3 |
| M4 资本资产 | A7, A11 | A6, A4 | 3 |
| M5 乡建在地 | A1, A4, A9, A12 | A2, A3, A5, A6, A10, A11 | **6** |
| M6 城市更新 | A2, A7 | A6, A9, A11, A12 | 3 |
| M7 技术整合 | A8 | A6, A2, A5 | 2 |
| M8 极端环境 | A10, A8, A4 | A2, A6, A5 | 5 |
| M9 社会结构 | A9 | A1, A2, A3 | 2 |
| M10 未来推演 | A8, A12 | A1, A10, A11 | 3 |

> M5（乡建在地）和 M8（极端环境）是调用能力最多的模式——它们的项目复杂度天然更高。

---

## 十一、代码入口索引

| 组件 | 文件 | 关键行号 |
|------|------|---------|
| 特征字典 | `services/mode_detector.py` | MODE_SIGNATURES 定义 |
| 关键词评分 | `services/mode_detector.py` | `DesignModeDetector.detect()` |
| LLM 精判 | `services/mode_detector.py` | `AdvancedModeDetector.detect_with_llm()` |
| 混合入口 | `services/mode_detector.py` | `HybridModeDetector.detect_sync()` |
| 便捷函数 | `services/mode_detector.py` | `detect_design_modes()` |
| Phase 1 调用 | `agents/requirements_analyst_agent.py` | L296–L430 |
| 信息质量调整 | `services/mode_info_adjuster.py` | `adjust_info_status_by_mode()` |
| 加权投票 | `agents/requirements_analyst_agent.py` | `_weighted_info_status_vote()` L654 |
| State 构建 | `workflow/main_workflow.py` | L544–L622 |
| 混合冲突配置 | `config/MODE_HYBRID_PATTERNS.yaml` | detection_thresholds |
| 能力激活矩阵 | `config/mode_ability_activation.yaml` | 全文 |
| 框架注册表 | `config/analysis_frameworks.yaml` | frameworks.ability_core |

---

## 十二、设计决策记录

| 决策 | 理由 | 版本 |
|------|------|------|
| 过滤阈值从 0.25 → 0.30 | 减少低信噪比干扰 | v7.623 |
| M8 权重设为 1.5（最高） | 极端环境漏判的安全风险最大 | v7.5 |
| 默认回退到 M2 | 功能效率是最通用策略 | v7.0 |
| 加权投票阈值 0.5 | 需至少两方同意，防止单一来源误判 | v7.623 |
| 关键词层不调 LLM | 速度 + 确定性优先 | v7.5 |
| Phase 1 而非 Phase 2 执行检测 | 确保模式总是执行，不被跳过 | v7.750 |
| 场景得分 2.5 > 关键词 1.0/1.5 | 场景短语更精确、歧义更低 | v7.0 |
| anti_keywords 每词扣 1.0 | 适度压制，不过度消除 | v7.0 |
