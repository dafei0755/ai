# 🧠 思考模式系统 - 多专家机制演进复盘 (v2-v7)

**复盘日期**: 2026-02-12
**代码版本**: v7.122+
**评估维度**: 架构设计、专家定义、思考模式演进、协作机制
**分析方法**: 代码审查 + 配置分析 + 历史追溯 + 架构深度复盘
**文档类型**: 机制复盘

---

## 📋 目录

1. [系统概览](#系统概览)
2. [思考模式演进史](#思考模式演进史)
3. [六大专家类别详解](#六大专家类别详解)
4. [专家协作机制](#专家协作机制)
5. [配置架构分析](#配置架构分析)
6. [核心机制复盘](#核心机制复盘)
7. [性能与质量优化](#性能与质量优化)
8. [未来演进方向](#未来演进方向)

---

## 1. 系统概览

### 1.1 多专家架构全景

```
用户需求
  ↓
V1: RequirementsAnalyst (需求分析)
  ↓
动态专家选择 (DynamicProjectDirector)
  ↓
┌──────────────────────────────────────────────────────┐
│             六层专家金字塔（V2-V7）                   │
├──────────────────────────────────────────────────────┤
│                                                        │
│        V2 - 设计总监 (Design Director)                │
│        统筹规划 | 整合协调 | 决策把关                 │
│        6个子角色 | 1455行配置                         │
│                    ▲                                   │
│         ┌──────────┼──────────┐                       │
│         │          │          │                        │
│    V3 叙事      V4 研究    V5 场景                    │
│    3子角色      2子角色    7子角色                    │
│    486行        409行      1947行                     │
│         │          │          │                        │
│         └──────────┼──────────┘                       │
│                    ▼                                   │
│        V6 - 专业总工程师 (Chief Engineer)             │
│        技术实现 | 工程落地 | 成本控制                 │
│        4个子角色 | 1719行配置                         │
│                                                        │
│    V7 - 情感洞察专家 (Emotional Insight)              │
│    实验性角色 | 心理分析 | 情感设计                   │
│                                                        │
└──────────────────────────────────────────────────────┘
  ↓
批次调度 (BatchScheduler - 拓扑排序)
  ↓
并行执行 + 结果聚合
  ↓
思考模式驱动的概念图生成
  ↓
最终报告 (ResultAggregator)
```

### 1.2 核心统计数据

| 维度 | 数据 | 说明 |
|------|------|------|
| **专家类别** | 6个主类别 (V2-V7) | V7为实验性角色 |
| **细分角色** | 22+ 个子角色 | 覆盖全设计流程 |
| **配置代码量** | 6000+ 行YAML | 包含系统提示词和约束 |
| **核心引擎** | 3100+ 行Python | Director + Factory + Scheduler |
| **思考模式** | 2种模式 | Normal / Deep Thinking |
| **概念图策略** | 动态调整 | 1张(普通) / 3-10张(深度) |
| **执行时长** | 60-180秒 | 取决于专家数量和批次 |
| **并行能力** | 批次内并行 | 通过拓扑排序优化 |

### 1.3 关键文件索引

| 组件 | 文件路径 | 代码量 | 职责 |
|------|---------|--------|------|
| **专家配置** | `config/roles/v2_design_director.yaml` | 1455行 | V2设计总监定义 |
| | `config/roles/v3_narrative_expert.yaml` | 486行 | V3叙事与体验专家 |
| | `config/roles/v4_design_researcher.yaml` | 409行 | V4设计研究员 |
| | `config/roles/v5_scenario_expert.yaml` | 1947行 | V5场景与行业专家 |
| | `config/roles/v6_chief_engineer.yaml` | 1719行 | V6专业总工程师 |
| | `config/roles/v7_emotional_insight_expert.yaml` | 未统计 | V7情感洞察专家(实验) |
| **思考模式** | `config/analysis_mode.yaml` | 64行 | 思考模式配置 |
| **核心引擎** | `agents/dynamic_project_director.py` | 1781行 | 动态角色选择 |
| | `agents/task_oriented_expert_factory.py` | 951行 | 专家执行引擎 |
| | `workflow/batch_scheduler.py` | 385行 | 批次调度器 |

---

## 2. 思考模式演进史

### 2.1 版本演进时间线

```
v7.38 (2025-11-XX)
  └─ 🎨 概念图生成系统初版
     - OpenRouter + Gemini 3 Pro Image
     - 每个专家生成1-2张概念图
     - 基于正则提取的提示词生成

v7.39 (2025-12-XX)
  └─ 🧠 思考模式概念诞生
     - 引入 analysis_mode 参数
     - Normal Mode: 标准分析流程
     - Deep Thinking Mode: 增强可视化
     - 前端增加模式切换UI

v7.50 (2025-12-XX)
  └─ 🔬 LLM语义提取升级
     - 从正则提取升级到LLM语义理解
     - 提示词质量大幅提升
     - 支持多轮对话优化

v7.61-62 (2025-12-XX)
  └─ 👁️ Vision分析 + Inpainting
     - Vision API集成（图像理解）
     - Mask编辑功能（局部修改）
     - 多焦点分析模式

v7.108 (2025-12-30)
  └─ 📦 交付物级概念图系统
     - 从专家级升级到交付物级
     - 交付物ID提前生成机制
     - 约束注入 + 精准生成
     - deliverable_metadata架构

v7.110 (2026-01-XX)
  └─ ⚙️ 声明式配置系统
     - analysis_mode.yaml正式定义
     - 可配置的概念图数量
     - 深度思考: 3张(可调整1-10张)
     - 普通模式: 1张(固定)

v7.350 (2026-01-XX)
  └─ 📎 文件上传模式限制
     - 深度思考模式启用附件上传
     - 普通模式禁用附件上传
     - 模式特性差异化设计

当前 (v7.122+)
  └─ 🎯 成熟的双模式系统
     - Normal: 快速验证，1张概念图
     - Deep Thinking: 详细分析，3-10张概念图
     - 配置驱动，灵活可扩展
```

### 2.2 思考模式核心配置

#### 配置文件: `config/analysis_mode.yaml`

```yaml
modes:
  # 普通思考模式 - 快速验证
  normal:
    name: "普通模式"
    description: "适合快速验证和概念阶段"
    concept_image:
      count: 1              # 每个交付物1张概念图
      editable: false       # 不可调整
      max_count: 1
      min_count: 1
    file_upload:
      enabled: false        # v7.350: 禁用附件上传

  # 深度思考模式 - 详细分析
  deep_thinking:
    name: "深度思考模式"
    description: "适合详细方案设计，多角度可视化"
    concept_image:
      count: 3              # 默认3张概念图
      editable: true        # 允许调整
      max_count: 10         # 最多10张
      min_count: 1
    file_upload:
      enabled: true         # v7.350: 启用附件上传
```

### 2.3 模式差异对比

| 特性 | Normal Mode | Deep Thinking Mode |
|------|------------|-------------------|
| **定位** | 快速验证、概念阶段 | 详细方案、深度分析 |
| **概念图数量** | 1张/交付物（固定） | 3张/交付物（可调1-10） |
| **图像可编辑性** | ❌ 不可调整 | ✅ 用户可调整数量 |
| **文件上传** | ❌ 禁用 (v7.350) | ✅ 启用 |
| **LLM Temperature** | 标准 | 标准（未来可配置） |
| **执行时长** | 60-90秒 | 120-180秒 |
| **Token消耗** | 较少 | 较多（更多概念图生成） |
| **适用场景** | 初期沟通、快速迭代 | 方案深化、客户汇报 |
| **前端标识** | 📝 普通模式 | 💭 深度思考 |

### 2.4 概念图生成策略演进

#### Phase 1: 专家级生成 (v7.38-v7.50)
```python
# 旧模式：每个专家生成1-2张概念图
for expert in experts:
    expert_result = execute_expert(expert)
    images = generate_concept_images(
        expert_summary=expert_result.content[:500],
        num_images=2
    )
    expert_result.concept_images = images
```

**问题**:
- 概念图与具体交付物无关联
- 提示词质量低（正则提取）
- 无法注入交付物约束

#### Phase 2: 交付物级生成 (v7.108+)
```python
# 新模式：为每个交付物生成精准概念图
for deliverable_id in expert.deliverable_ids:
    metadata = deliverable_metadata[deliverable_id]
    image = await generate_deliverable_image(
        deliverable_metadata=metadata,  # 包含keywords, constraints
        expert_analysis=expert_result.content[:500],
        session_id=session_id,
        aspect_ratio="16:9"
    )
    deliverable.concept_images.append(image)
```

**改进**:
- ✅ 概念图精准对应交付物
- ✅ 注入交付物关键词和约束
- ✅ LLM语义提取提示词
- ✅ deliverable_id提前生成机制

---

## 3. 六大专家类别详解

### 3.1 V2 - 设计总监 (Design Director)

**定位**: 项目总设计师 (Project Design Principal)
**配置文件**: `config/roles/v2_design_director.yaml` (1455行)
**版本**: v2.8 (更新于2025-12-17)

#### 专家矩阵

| 角色ID | 名称 | 适用场景 | 核心能力 | LLM参数 |
|-------|------|---------|---------|---------|
| **2-0** | 项目设计总监 | 多业态综合体 | Master Plan、专业协调、总体规划 | temp=0.6 |
| **2-1** | 居住空间设计总监 | 住宅/别墅/公寓 | 户型设计、生活场景、人性化细节 | temp=0.6 |
| **2-2** | 商业零售设计总监 | 购物中心/零售店 | 动线组织、视觉营销、商业氛围 | temp=0.6 |
| **2-3** | 办公空间设计总监 | 企业/联合办公 | 工位布局、协作空间、企业文化 | temp=0.6 |
| **2-4** | 酒店餐饮设计总监 | 酒店/餐厅/民宿 | 服务流线、氛围营造、体验设计 | temp=0.6 |
| **2-5** | 文化公共建筑总监 | 博物馆/图书馆/剧院 | 公共性、文化表达、场所精神 | temp=0.6 |
| **2-6** | 建筑及景观总监 | 建筑/景观规划 | 建筑形态、室外空间、环境整合 | temp=0.6 |

#### 配置特点

```yaml
V2_设计总监:
  description: "负责项目的总体规划和方案整合"
  roles:
    "2-1":
      name: "居住空间设计总监"
      keywords:
        - "住宅"
        - "户型"
        - "生活方式"
        - "家庭"
        - "公寓"
      system_prompt: |
        ### **1. 身份与任务**
        你是一位居住空间设计总监，负责住宅项目的整体设计规划...

        ### **动态本体论框架**
        {dynamic_ontology_injection}

        ### **🆕 输出模式判断协议**
        - Targeted Mode: 针对性问答
        - Comprehensive Mode: 完整分析报告

        ### **2. 输出定义**
        class V2_1_FlexibleOutput(BaseModel):
            output_mode: Literal["targeted", "comprehensive"]
            user_question_focus: str
            confidence: float = Field(ge=0, le=1)
            # ... 标准字段
            targeted_analysis: Optional[Dict[str, Any]] = None
```

#### 工具配置
```python
tools = ["ragflow_kb_tool"]  # 仅内部知识库，理性决策
max_tokens = 8000
temperature = 0.6  # 稳定输出
```

#### V2核心职责

1. **总体规划** (Master Planning)
   - 空间功能分区
   - 动线组织策略
   - 尺度与比例控制

2. **方案整合** (Scheme Integration)
   - 综合V3/V4/V5/V6的专家意见
   - 化解设计冲突
   - 决策把关

3. **决策支持** (Decision Support)
   - 设计方向建议
   - 风险评估
   - 成本与品质平衡

---

### 3.2 V3 - 叙事与体验专家 (Narrative & Experience Expert)

**定位**: 首席共情官 (Chief Empathy Officer)
**配置文件**: `config/roles/v3_narrative_expert.yaml` (486行)
**标识**: `is_creative_narrative=True` (v7.10创意叙事模式)

#### 叙事原点三分法

```
个体 (Person) ────→ V3-1 ────→ 个体叙事与心理洞察
   ↓                           情感、心理、价值观
   ↓
组织 (Brand) ─────→ V3-2 ────→ 品牌叙事与顾客体验
   ↓                           品牌故事、顾客旅程
   ↓
概念 (Idea) ──────→ V3-3 ────→ 文化叙事与符号转译
                                文化解码、符号转译
```

#### 专家矩阵

| 角色ID | 名称 | 叙事原点 | 核心能力 | 工具链 |
|-------|------|---------|---------|--------|
| **3-1** | 个体叙事与心理洞察 | 个体 (Individual) | 人物画像、心理洞察、生活方式 | bocha + tavily + ragflow |
| **3-2** | 品牌叙事与顾客体验 | 组织 (Organization) | 品牌故事、顾客旅程、情感连接 | bocha + tavily + ragflow |
| **3-3** | 文化叙事与符号转译 | 概念 (Concept) | 文化解码、符号转译、理念具象化 | bocha + tavily + ragflow |

#### 配置特点

```yaml
V3_叙事与体验专家:
  roles:
    "3-1":
      name: "个体叙事与心理洞察专家"
      keywords:
        - "人物"
        - "心理"
        - "情感"
        - "生活方式"
      system_prompt: |
        ### **🔧 v7.63.1: 工具使用指南**
        - 🔍 bocha_search: 实时中文搜索（百度+知乎）
        - 🌐 tavily_search: 国际趋势研究
        - 📚 ragflow_kb_tool: 内部知识库检索
```

#### LLM参数
```python
temperature = 0.75  # 高创意度
max_tokens = 10000  # 支持长篇叙事
```

#### V3核心交付物

1. **叙事地图** (Narrative Map)
   - 核心叙事线索
   - 情感触点设计
   - 故事化场景构建

2. **体验蓝图** (Experience Blueprint)
   - 用户旅程地图
   - 关键时刻设计
   - 情感峰值布局

3. **共情洞察** (Empathy Insights)
   - 深层需求挖掘
   - 心理动机分析
   - 价值观映射

---

### 3.3 V4 - 设计研究员 (Design Researcher)

**定位**: 战略智库 (Strategic Think Tank)
**配置文件**: `config/roles/v4_design_researcher.yaml` (409行)

#### 专家矩阵

| 角色ID | 名称 | 研究焦点 | 核心能力 | 工具链 |
|-------|------|---------|---------|--------|
| **4-1** | 设计研究员(案例导向) | 案例研究 | 标杆分析、设计批判、案例萃取 | tavily + arxiv + ragflow |
| **4-2** | 设计研究员(理论导向) | 方法论研究 | 设计理论、创新方法、学术研究 | tavily + arxiv + ragflow |

#### 配置特点

```yaml
V4_设计研究员:
  roles:
    "4-1":
      name: "设计研究员（案例导向）"
      keywords:
        - "案例研究"
        - "标杆分析"
        - "设计批判"
      system_prompt: |
        ### **1. 身份与任务**
        你是一位设计研究员，擅长通过案例研究挖掘设计规律...

        ### **研究方法论**
        - 案例筛选标准（相关性、创新性、可借鉴性）
        - 多维度分析框架（空间、材料、技术、商业）
        - 批判性思维（不盲从，提炼精华）
```

#### LLM参数
```python
temperature = 0.5  # 数据驱动，理性分析
max_tokens = 8000
```

#### V4核心职责

1. **案例研究** (Case Study)
   - 标杆项目分析
   - 设计手法解构
   - 成功要素提取

2. **方法论研究** (Methodology)
   - 设计思维框架
   - 创新方法探索
   - 学术研究综述

3. **趋势洞察** (Trend Insight)
   - 前沿设计趋势
   - 技术创新应用
   - 行业发展动向

---

### 3.4 V5 - 场景与行业专家 (Scenario Expert)

**定位**: 运营架构师 (Operation Architect)
**配置文件**: `config/roles/v5_scenario_expert.yaml` (1947行，最复杂)

#### 专家矩阵（7个子角色，行业覆盖最广）

| 角色ID | 名称 | 行业领域 | 核心能力 | 关键指标 |
|-------|------|---------|---------|---------|
| **5-1** | 家庭生活场景专家 | 居住 | 生活方式、家庭动线、收纳系统 | 居住舒适度、空间利用率 |
| **5-2** | 商业零售运营专家 | 零售 | 坪效优化、动线设计、视觉营销 | 坪效、转化率、客单价 |
| **5-3** | 办公场景与协作专家 | 办公 | 工位布局、协作空间、企业文化 | 工位效率、协作频率 |
| **5-4** | 酒店运营与服务专家 | 酒店 | 服务流程、客户体验、RevPAR | RevPAR、入住率、复购率 |
| **5-5** | 文化教育场景专家 | 文化 | 参观流程、教育模式、公共服务 | 参观人次、教育效果 |
| **5-6** | 餐饮空间运营专家 | 餐饮 | 厨房流程、翻台率、氛围营造 | 翻台率、客座率 |
| **5-7** | 康养空间专家 | 康养 | 康复流程、老幼友好、安全设计 | 康复效果、满意度 |

#### 配置特点

```yaml
V5_场景与行业专家:
  roles:
    "5-1":
      name: "家庭生活场景专家"
      keywords:
        - "家庭"
        - "生活方式"
        - "收纳"
        - "动线"
      system_prompt: |
        ### **1. 身份与任务**
        你是一位家庭生活场景专家，深谙现代家庭的生活模式...

        ### **分析维度**
        - 家庭结构与需求（成员、年龄、职业、爱好）
        - 生活动线（早晨、日间、晚间、周末）
        - 收纳系统（分区、分类、频率、可达性）
        - 居住舒适度（采光、通风、隔音、温湿度）
```

#### LLM参数
```python
temperature = 0.6  # 行业洞察，稳定输出
max_tokens = 9000
```

#### V5核心职责

1. **行业运营策略** (Operation Strategy)
   - 业态定位
   - 运营模式设计
   - KPI指标体系

2. **场景化分析** (Scenario Analysis)
   - 用户使用场景
   - 行为模式研究
   - 触点设计

3. **商业可行性** (Business Feasibility)
   - 投资回报分析
   - 风险评估
   - 运营成本控制

---

### 3.5 V6 - 专业总工程师 (Chief Engineer)

**定位**: 技术实现专家 (Technical Implementation Expert)
**配置文件**: `config/roles/v6_chief_engineer.yaml` (1719行)

#### 专家矩阵

| 角色ID | 名称 | 专业领域 | 核心能力 | 精确度 |
|-------|------|---------|---------|--------|
| **6-1** | 建筑及空间工程师 | 建筑/结构 | 承重分析、尺寸校核、规范审查 | temp=0.4 |
| **6-2** | 机电与智能化工程师 | 机电/智能化 | 设备选型、管线综合、能耗计算 | temp=0.4 |
| **6-3** | 材料与工艺专家 | 材料/施工 | 材料选型、工艺评估、节点设计 | temp=0.4 |
| **6-4** | 成本与价值工程师 | 成本/价值 | 造价估算、价值分析、成本优化 | temp=0.4 |

#### 配置特点

```yaml
V6_专业总工程师:
  roles:
    "6-1":
      name: "建筑及空间工程师"
      keywords:
        - "结构"
        - "承重"
        - "规范"
        - "施工图"
      system_prompt: |
        ### **1. 身份与任务**
        你是一位建筑及空间工程师，负责技术可行性评估...

        ### **技术审查清单**
        1. 承重与结构（梁柱位置、荷载计算、抗震设防）
        2. 尺寸校核（净高、开间、深度、疏散宽度）
        3. 规范符合性（建筑规范、防火规范、无障碍规范）
        4. 可施工性（拆改难度、工期评估、风险预判）
```

#### LLM参数
```python
temperature = 0.4  # 高精确度，技术严谨
max_tokens = 8000
```

#### V6核心职责

1. **技术可行性** (Technical Feasibility)
   - 结构承重分析
   - 规范符合性审查
   - 施工可行性评估

2. **工程实施** (Engineering Implementation)
   - 施工图设计要点
   - 材料选型建议
   - 工艺节点设计

3. **成本控制** (Cost Control)
   - 工程量估算
   - 造价分析
   - 成本优化方案

---

### 3.6 V7 - 情感洞察专家 (Emotional Insight Expert)

**定位**: 心理设计专家 (Psychological Design Expert)
**配置文件**: `config/roles/v7_emotional_insight_expert.yaml`
**状态**: 🧪 实验性角色

#### 角色特点

```yaml
V7_情感洞察专家:
  description: "实验性角色，专注情感设计与心理分析"
  roles:
    "7-1":
      name: "情感洞察专家"
      keywords:
        - "情感设计"
        - "心理学"
        - "情绪价值"
        - "感官体验"
```

#### 核心职责（实验阶段）

1. **情感设计** (Emotional Design)
   - 情绪触发点设计
   - 感官体验优化
   - 情感记忆构建

2. **心理分析** (Psychological Analysis)
   - 用户心理画像
   - 决策心理研究
   - 行为动机分析

3. **感官整合** (Sensory Integration)
   - 五感设计策略
   - 感官协同效应
   - 沉浸式体验设计

**注**: V7作为实验性角色，尚未在生产环境中广泛使用，配置和能力仍在迭代中。

---

## 4. 专家协作机制

### 4.1 批次调度系统

#### 依赖关系定义

**文件**: `workflow/batch_scheduler.py`

```python
class BatchScheduler:
    def __init__(self):
        # 基础依赖关系（类别级别）
        self.base_dependencies = {
            "V4": [],                # 第一批次，无依赖
            "V5": ["V4"],            # 依赖V4完成
            "V3": ["V4", "V5"],      # 依赖V4+V5完成
            "V2": ["V3", "V4", "V5"], # 依赖前3批次完成
            "V6": ["V2"],            # 依赖V2决策
            "V7": ["V3"]             # 实验性，依赖V3
        }
```

#### 执行流程

```
Batch 1: [V4_研究员]
   ↓ (研究基础，案例分析)
   ↓
Batch 2: [V5_场景专家] (并行执行多个V5子角色)
   ↓ (行业洞察，场景分析)
   ↓
Batch 3: [V3_叙事专家] (并行执行多个V3子角色)
   ↓ (情感叙事，体验设计)
   ↓
Batch 4: [V2_设计总监] (方案整合)
   ↓ (总体规划，决策把关)
   ↓
Batch 5: [V6_专业总工程师] (工程落地)
   ↓ (技术实现，成本控制)
   ↓
最终报告聚合
```

### 4.2 批次内并行机制

**理论设计** (v7.17.0):
```python
# BatchScheduler计算出可并行的专家
batch_2 = [
    {"role_id": "5-1", "name": "家庭生活场景专家"},
    {"role_id": "5-2", "name": "商业零售运营专家"}
]
# 理论上应并行执行，节省时间
```

**实际执行** (当前瓶颈):
```python
# 实际仍串行执行（主工作流问题）
for expert in batch_2:
    result = await execute_expert(expert)  # 串行阻塞
```

**改进方向** (Future Optimization):
```python
# 真正并行执行（使用asyncio.gather）
import asyncio
results = await asyncio.gather(
    *[execute_expert(expert) for expert in batch_2]
)
```

### 4.3 专家间信息传递

#### 上下文构建

**文件**: `agents/task_oriented_expert_factory.py`

```python
def _build_context(self, state: ProjectAnalysisState, role_id: str) -> str:
    """为专家构建上下文"""
    context_parts = []

    # 1. 用户原始需求
    context_parts.append(f"## 用户需求\n{state['user_input']}")

    # 2. V1结构化需求
    structured_req = state.get("structured_requirements", {})
    context_parts.append(f"## 结构化需求\n{json.dumps(structured_req, ensure_ascii=False)}")

    # 3. 前置专家的分析结果
    agent_results = state.get("agent_results", {})
    for prev_role_id, prev_result in agent_results.items():
        if self._is_dependency(role_id, prev_role_id):
            context_parts.append(f"## {prev_role_id} 的分析\n{prev_result}")

    return "\n\n".join(context_parts)
```

#### 依赖链示例

```
V4_研究员 (案例研究)
   ↓ 输出: 标杆案例分析、设计手法提取
   ↓
V5_场景专家 (行业分析)
   ↓ 接收: V4的案例研究结果
   ↓ 输出: 行业运营策略、KPI指标
   ↓
V3_叙事专家 (体验设计)
   ↓ 接收: V4的案例研究 + V5的行业洞察
   ↓ 输出: 叙事地图、体验蓝图
   ↓
V2_设计总监 (方案整合)
   ↓ 接收: V3+V4+V5的全部分析
   ↓ 输出: 整合方案、设计决策
   ↓
V6_专业总工程师 (工程落地)
   ↓ 接收: V2的设计决策
   ↓ 输出: 技术方案、成本估算
```

### 4.4 专家挑战机制 (v3.5+)

#### Challenge Protocol

```python
class ExpertOutput(BaseModel):
    # 标准分析字段
    design_rationale: str

    # 🆕 v3.5: 挑战机制
    challenge_flags: Optional[List[Dict[str, str]]] = None

    # 挑战响应
    expert_handoff_response: Optional[Dict[str, Any]] = None
```

#### 挑战类型

1. **Accept** (接受建议)
   - 更新 `expert_driven_insights`
   - 记录接受理由

2. **Synthesize** (综合框架)
   - 构建竞争性框架
   - 保留多元观点

3. **Escalate** (提交裁决)
   - 标记为需要甲方决策
   - 提供决策依据

---

## 5. 配置架构分析

### 5.1 专家配置文件结构

#### 标准YAML模板

```yaml
# ============================================================================
# 文件头部元数据
# ============================================================================
# 版本: v2.x
# 更新日期: YYYY-MM-DD
# 本文件定义了XX类细分专家角色
# ============================================================================

## 🔧 模板变量说明 (Template Variables)
# {user_specific_request} - 用户任务动态注入
# {dynamic_ontology_injection} - 本体论框架注入

## 📌 置信度校准指南 (Confidence Calibration)
# 0.9-1.0: 输入完整，所有字段可充分展开
# 0.7-0.9: 小幅缺失，可基于专业判断
# 0.5-0.7: 关键信息缺失，仅方向性建议
# < 0.5: 任务超出范围或信息极度匮乏

## 📌 版本历史 (Version History)
# v2.8 (2025-12-17):
#   - 新增输出模式判断协议
#   - 优化Few-Shot示例
#   - 增强工具使用指南

# ============================================================================
# 角色定义主体
# ============================================================================
VX_类别名称:
  description: "类别简短描述"
  roles:
    "X-Y":
      name: "角色中文名称"
      description: "角色职责描述"
      keywords: ["关键词1", "关键词2"]
      system_prompt: |
        ### **🔧 v7.63.1: 工具使用指南**
        工具列表及使用策略

        ### **1. 身份与任务**
        角色定位与核心任务

        ### **动态本体论框架**
        {dynamic_ontology_injection}

        ### **🆕 输出模式判断协议**
        - Targeted Mode: 针对性问答
        - Comprehensive Mode: 完整报告

        ### **2. 输出定义 (Pydantic模型)**
        ```python
        class VX_Y_FlexibleOutput(BaseModel):
            output_mode: Literal["targeted", "comprehensive"]
            user_question_focus: str
            confidence: float
            design_rationale: str
            # 标准字段
            targeted_analysis: Optional[Dict[str, Any]]
        ```

        ### **3. Targeted Analysis 模板**
        示例模板（3-4种常见分析类型）

        ### **4. 工作流程**
        执行步骤（5-8步）

        ### **5. 专业准则**
        质量标准与注意事项

        ### **🔥 v3.5 专家主动性协议**
        - expert_driven_insights: 主动洞察
        - challenge_flags: 挑战机制
        - expert_handoff_response: 协作响应
```

### 5.2 核心配置字段

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `name` | string | 角色中文名称 | "居住空间设计总监" |
| `description` | string | 角色职责描述 | "负责住宅项目的整体设计规划" |
| `keywords` | array | 权重计算关键词 | ["住宅", "户型", "生活方式"] |
| `system_prompt` | string | 系统提示词（150-300行） | 包含身份、任务、输出定义、工作流程 |

### 5.3 动态本体论注入机制

#### 概念

根据项目类型动态注入类目体系，指导专家分析维度。

#### 三种项目类型

```python
project_type_ontology = {
    "personal_residential": {
        "name": "个人居住项目",
        "categories": [
            "空间功能", "生活动线", "收纳系统", "采光通风",
            "家庭成员需求", "风格偏好", "预算分配"
        ]
    },
    "hybrid_residential_commercial": {
        "name": "住宅+商业混合",
        "categories": [
            "业态组合", "动线分离", "商业界面", "住宅私密性",
            "停车配比", "物业管理", "消防分区"
        ]
    },
    "commercial_enterprise": {
        "name": "商业/企业项目",
        "categories": [
            "品牌定位", "目标客群", "运营模式", "坪效优化",
            "视觉营销", "服务流程", "KPI指标"
        ]
    }
}
```

#### 注入方式

```python
# 在专家执行前，动态注入类目体系
system_prompt = system_prompt.replace(
    "{dynamic_ontology_injection}",
    ontology_injector.get_categories_for_project_type(project_type)
)
```

---

## 6. 核心机制复盘

### 6.1 关键性能瓶颈

#### 瓶颈1: 批次内串行执行 ⚠️⚠️⚠️ (最严重)

**问题描述**:
- BatchScheduler精心计算的批次内并行专家，实际仍串行执行
- 例如Batch 2有3个可并行的V5专家，却串行等待：3×15秒=45秒
- 理论上只需15秒（真正并行）

**影响**:
- 浪费40-50%的执行时间
- LLM API并发能力未利用（支持10-20个并发请求）
- 用户体验：等待时间过长

**解决方案**:
```python
# 当前（串行）
for expert in batch:
    result = await execute_expert(expert)

# 改进（并行）
import asyncio
results = await asyncio.gather(
    *[execute_expert(expert) for expert in batch],
    return_exceptions=True
)
```

**预期收益**:
- 节省40-50%执行时间
- 5专家项目：从90秒降至50-60秒
- 8专家项目：从180秒降至100-120秒

#### 瓶颈2: Prompt重复构建 ⚠️⚠️ (严重)

**问题描述**:
- 每个专家执行时重复加载配置文件（磁盘IO）
- 静态Prompt部分（如autonomy_protocol）重复拼接
- 5个专家 = 5次配置加载 + 5次Prompt拼接

**解决方案**:
```python
# v7.17.0 优化：Prompt预构建机制
class ExpertPromptTemplate:
    def __init__(self, role_type, base_prompt, autonomy_protocol):
        self.static_sections = self._build_static_sections(autonomy_protocol)

    def build_prompt(self, dynamic_context):
        return f"{self.static_sections}\n\n{dynamic_context}"
```

**实施状态**: ✅ 已在v7.17.0实施

**收益**:
- 减少80%的Prompt构建时间
- 避免重复磁盘IO
- 统一Prompt管理

### 6.2 质量优化机制

#### Few-Shot示例库系统 (P0优化)

**实施状态**: ✅ 66.7%完成 (v2.0/v2.1/v3.1/v4.1/v5.1已完成)

**文件结构**:
```
config/roles/examples/
├── v2_0_examples.yaml  # V2-0 项目设计总监
├── v2_1_examples.yaml  # V2-1 居住空间设计总监
├── v3_1_examples.yaml  # V3-1 个体叙事专家
├── v4_1_examples.yaml  # V4-1 设计研究员（3个示例，14657字符）
├── v5_1_examples.yaml  # V5-1 家庭生活场景专家
└── [待扩展] v6_x_examples.yaml  # V6系列
```

**Few-Shot加载器**:
```python
# utils/few_shot_loader.py (217行)
class FewShotLoader:
    def load_examples(self, role_id: str) -> List[Dict]:
        """加载指定角色的Few-Shot示例"""

    def inject_examples_to_prompt(self, prompt: str, examples: List[Dict]) -> str:
        """将示例注入到系统提示词"""
```

**质量改进**:
- 格式正确率: 60% → 95% (+35%)
- 降级策略触发率: 20% → 2% (-90%)
- 平均质量分: 0.75 → 0.90 (+20%)

#### 输出模式判断协议 (Output Mode Selection)

**引入版本**: v7.63+

**两种模式**:

1. **Targeted Mode** (针对性问答)
   ```python
   {
       "output_mode": "targeted",
       "user_question_focus": "儿童房收纳系统设计",
       "targeted_analysis": {
           "storage_zones": {...},
           "accessibility_design": {...}
       },
       "standard_fields": None  # 标准字段置空
   }
   ```

2. **Comprehensive Mode** (完整报告)
   ```python
   {
       "output_mode": "comprehensive",
       "user_question_focus": "完整的家庭生活场景分析",
       "family_profile": {...},
       "lifecycle_needs": {...},
       "storage_system": {...},
       "targeted_analysis": None
   }
   ```

**判断依据**:
- 疑问词检测（如何、哪些、什么、为什么）
- 明确的分析维度（"收纳需求"、"动线设计"）
- 用户期望（"完整分析" vs "针对性建议"）

**收益**:
- Token节省：30-50%（Targeted模式下）
- 响应速度：提升40%
- 用户满意度：更精准的回答

### 6.3 上下文压缩策略

**引入版本**: v7.502

**三级压缩策略**:

```python
# workflow/context_compressor.py
class ContextCompressor:
    STRATEGIES = {
        "minimal": {  # 最小压缩
            "method": "first_n_chars",
            "params": {"n": 800, "priority_sections": ["核心洞察"]}
        },
        "balanced": {  # 平衡压缩
            "method": "smart_truncate",
            "params": {"max_length": 500, "preserve_structure": True}
        },
        "aggressive": {  # 激进压缩
            "method": "bullet_points_only",
            "params": {"max_bullets": 5}
        }
    }
```

**压缩时机**:
- Batch 1 (V4) → Minimal（完全不压缩）
- Batch 2-3 (V5, V3) → Balanced（前800字符+智能截断）
- Batch 4+ (V2, V6) → Aggressive（清单+示例）

**收益**:
- 标准3批次项目：节省15-25% Token
- 复杂5批次项目：节省40-50% Token
- 质量影响：<2%（通过测试验证）

---

## 7. 性能与质量优化

### 7.1 P0优化（快速见效）

| 优化项 | 状态 | 收益 | 实施版本 |
|-------|------|------|---------|
| **Few-Shot示例库** | ✅ 66.7%完成 | 格式正确率+35% | v7.502 |
| **结构化输出API** | 📋 规划中 | 格式错误-95% | - |
| **提示词精简与分层** | ✅ 已实施 | 核心约束遵守率+25% | v7.17.0 |
| **实时输出监控** | ✅ 已实施 | Token浪费-90% | v7.502 |
| **Prompt预构建机制** | ✅ 已实施 | Prompt构建时间-80% | v7.17.0 |

### 7.2 P1优化（中期提升）

| 优化项 | 状态 | 预期收益 | 计划实施 |
|-------|------|---------|---------|
| **质量评分系统** | 📋 规划中 | 质量可量化跟踪 | Week 3-4 |
| **Peer Review机制** | 📋 规划中 | 互评提升质量20% | Week 3-4 |
| **动态提示词优化** | 📋 规划中 | 自适应调整 | Week 3-4 |
| **批次内真正并行** | 📋 规划中 | 执行时间-40% | Week 3-4 |
| **上下文压缩** | ✅ 已实施 | Token节省15-50% | v7.502 |

### 7.3 P2优化（战略提升）

| 优化项 | 状态 | 预期收益 | 计划实施 |
|-------|------|---------|---------|
| **Few-Shot自动积累** | 📋 规划中 | 持续学习机制 | Month 2-3 |
| **工具效果评估** | 📋 规划中 | 工具使用优化 | Month 2-3 |
| **A/B测试框架** | 📋 规划中 | 数据驱动优化 | Month 2-3 |
| **细粒度依赖图** | 📋 规划中 | 更精准的并行 | Month 2-3 |

### 7.4 综合性能指标

#### 当前性能 (v7.122+)

| 指标 | 数值 | 备注 |
|------|------|------|
| **平均执行时长** | 60-120秒 | 5个专家，典型项目 |
| **格式正确率** | 95% | Few-Shot优化后 |
| **降级策略触发率** | 2% | 从20%降至2% |
| **平均质量分** | 0.90 | 从0.75提升至0.90 |
| **Token消耗** | 15-50% less | 上下文压缩生效 |

#### 优化目标 (v8.0)

| 指标 | 目标值 | 提升幅度 |
|------|-------|---------|
| **平均执行时长** | 40-80秒 | -33% |
| **格式正确率** | 99% | +4% |
| **降级策略触发率** | <1% | -50% |
| **平均质量分** | 0.95 | +5% |
| **Token消耗** | 60% less | 进一步优化 |

---

## 8. 未来演进方向

### 8.1 短期优化 (v7.150 - v7.200)

#### 1. 批次内真正并行执行
```python
# 目标实现
async def execute_batch_parallel(batch: List[Expert]):
    tasks = [execute_expert(expert) for expert in batch]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

**预期收益**:
- 执行时间减少40%
- LLM并发能力充分利用

#### 2. 结构化输出API集成
```python
# OpenAI Structured Outputs
response = await client.chat.completions.create(
    model="gpt-4o-2024-08-06",
    messages=[...],
    response_format={
        "type": "json_schema",
        "json_schema": V2_1_FlexibleOutput.model_json_schema()
    }
)
```

**预期收益**:
- 格式错误率降至<1%
- 无需降级策略

#### 3. 质量评分系统
```python
class QualityScorer:
    def score_expert_output(self, output: Dict) -> float:
        """多维度质量评分"""
        scores = {
            "format_compliance": self._check_format(output),
            "content_depth": self._evaluate_depth(output),
            "constraint_adherence": self._check_constraints(output),
            "creativity": self._evaluate_creativity(output)
        }
        return weighted_average(scores)
```

### 8.2 中期演进 (v7.300 - v7.500)

#### 1. Few-Shot自动积累系统
```python
class FewShotCollector:
    def collect_high_quality_examples(self):
        """自动识别高质量输出并加入示例库"""
        sessions = get_recent_sessions(days=7)
        for session in sessions:
            if session.quality_score > 0.95:
                self.add_to_example_pool(session)
```

#### 2. 动态专家推荐
```python
class ExpertRecommender:
    def recommend_experts(self, project: Dict) -> List[str]:
        """基于项目特征智能推荐专家"""
        # 机器学习模型预测最佳专家组合
        features = extract_project_features(project)
        return ml_model.predict(features)
```

#### 3. 细粒度依赖图
```python
# 从类别级依赖升级到专家级依赖
expert_dependencies = {
    "V3-1": ["V4-1"],  # V3-1只依赖V4-1
    "V3-2": ["V4-1", "V5-2"],  # V3-2依赖V4-1和V5-2
    "V6-1": ["V2-1", "V2-6"]  # V6-1依赖V2-1和V2-6
}
```

### 8.3 长期愿景 (v8.0+)

#### 1. 自适应专家系统
- 专家能力根据历史表现动态调整
- 温度参数、max_tokens自动优化
- 工具使用策略自我学习

#### 2. 多模态专家
- 图像理解能力（Vision API）
- 3D模型分析能力
- 视频内容理解

#### 3. 专家生态系统
- 第三方专家插件机制
- 社区贡献的专家配置
- 专家市场（付费专家）

#### 4. 实时协作模式
- 专家之间实时对话
- 冲突实时调解
- 动态方案演化

---

## 9. 总结与建议

### 9.1 核心优势

1. **配置驱动架构** ✅
   - 6000+行YAML配置，易于扩展
   - 新增专家无需修改代码
   - 灵活的角色定义系统

2. **多专家协作机制** ✅
   - 清晰的依赖关系
   - 批次调度系统
   - 上下文传递机制

3. **思考模式创新** ✅
   - Normal / Deep Thinking双模式
   - 概念图生成系统
   - 交付物级精准可视化

4. **质量保证机制** ✅
   - Few-Shot示例库
   - 输出模式判断协议
   - 挑战与审核机制

### 9.2 待改进点

1. **性能优化** ⚠️
   - ❌ 批次内真正并行执行
   - ❌ LLM批量调用API
   - ⚠️ 细粒度依赖优化

2. **质量提升** ⚠️
   - ⏳ 结构化输出API集成
   - ⏳ 质量评分系统
   - ⏳ Peer Review机制

3. **V7专家完善** ⚠️
   - 🧪 V7仍处于实验阶段
   - 📋 需要更多场景验证
   - 📋 配置和能力待稳定

### 9.3 实施建议

#### 优先级矩阵

| 优化项 | ROI | 复杂度 | 优先级 | 预期时间 |
|-------|-----|--------|--------|---------|
| 批次内并行执行 | ⭐⭐⭐⭐⭐ | ⭐⭐ | P0 | 1周 |
| 结构化输出API | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | P0 | 1-2周 |
| 质量评分系统 | ⭐⭐⭐⭐ | ⭐⭐⭐ | P1 | 2周 |
| Few-Shot自动积累 | ⭐⭐⭐ | ⭐⭐⭐⭐ | P2 | 1个月 |
| 细粒度依赖图 | ⭐⭐⭐ | ⭐⭐⭐⭐ | P2 | 2-3周 |

#### 实施路线图

**Week 1-2: P0优化（快速见效）**
- ✅ 批次内并行执行
- ✅ 结构化输出API集成
- ✅ Prompt进一步精简

**Week 3-4: P1优化（质量提升）**
- ⏳ 质量评分系统
- ⏳ Peer Review机制
- ⏳ 动态提示词优化

**Month 2-3: P2战略优化**
- ⏳ Few-Shot自动积累
- ⏳ 细粒度依赖图
- ⏳ A/B测试框架

### 9.4 关键技术栈

| 技术 | 当前使用 | 未来考虑 |
|------|---------|---------|
| **LLM** | OpenAI GPT-4/Claude | Gemini 2.0, GPT-5 |
| **图像生成** | Gemini 3 Pro Image | DALL-E 3, Midjourney API |
| **配置格式** | YAML | 继续使用，增加验证 |
| **调度策略** | 类别级依赖 | 细粒度专家级依赖 |
| **并行执行** | 串行（待优化） | asyncio.gather |
| **质量监控** | 基础日志 | 完整评分系统 |

---

## 10. 参考文档

### 10.1 核心机制文档

- [动态专家Agent机制复盘](DYNAMIC_EXPERT_MECHANISM_REVIEW.md)
- [专家角色定义系统](EXPERT_ROLE_DEFINITION_SYSTEM.md)
- [专家输出质量优化方案](EXPERT_OUTPUT_QUALITY_OPTIMIZATION.md)
- [智能上下文压缩策略](CONTEXT_COMPRESSION_GUIDE.md)

### 10.2 优化实施报告

- [P0优化实施报告](../../P0_OPTIMIZATION_IMPLEMENTATION_v7.502.md)
- [P0优化验证报告](../../P0_OPTIMIZATION_VERIFICATION_v7.502.md)
- [P1优化计划](../../P1_OPTIMIZATION_PLAN_v7.501.md)
- [P1优化实施报告](../../P1_OPTIMIZATION_IMPLEMENTATION_v7.502.md)

### 10.3 配置文件

- [v2_design_director.yaml](../../config/roles/v2_design_director.yaml)
- [v3_narrative_expert.yaml](../../config/roles/v3_narrative_expert.yaml)
- [v4_design_researcher.yaml](../../config/roles/v4_design_researcher.yaml)
- [v5_scenario_expert.yaml](../../config/roles/v5_scenario_expert.yaml)
- [v6_chief_engineer.yaml](../../config/roles/v6_chief_engineer.yaml)
- [analysis_mode.yaml](../../config/analysis_mode.yaml)

### 10.4 核心代码文件

- [dynamic_project_director.py](../../intelligent_project_analyzer/agents/dynamic_project_director.py)
- [task_oriented_expert_factory.py](../../intelligent_project_analyzer/agents/task_oriented_expert_factory.py)
- [batch_scheduler.py](../../intelligent_project_analyzer/workflow/batch_scheduler.py)
- [context_compressor.py](../../intelligent_project_analyzer/workflow/context_compressor.py)

---

**复盘完成日期**: 2026-02-12
**下次复盘计划**: 2026-03-12 (v7.200+ 优化后)
**维护者**: Architecture Review Team
