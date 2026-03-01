# 🎭 专家角色定义系统 - 配置驱动架构复盘

**版本**: v2.8
**复盘日期**: 2026-02-10
**代码版本**: v7.122+
**文档类型**: 机制复盘
**配置文件版本**: v2.6-v2.8 (2025-12-17更新)
**实施状态**: ✅ 已实施并持续优化

---

## 📋 目录

1. [专家角色体系概览](#专家角色体系概览)
2. [角色定义结构](#角色定义结构)
3. [六大专家类别详解](#六大专家类别详解)
4. [配置文件架构](#配置文件架构)
5. [关键机制解析](#关键机制解析)
6. [工具使用策略](#工具使用策略)
7. [质量保证机制](#质量保证机制)

---

## 1. 专家角色体系概览

### 🎯 角色分类矩阵

```
┌─────────────────────────────────────────────────────────────┐
│                    专家角色金字塔                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│              V2 - 设计总监 (Design Director)                 │
│              统筹规划 | 整合协调 | 决策把关                  │
│                        ▲                                      │
│         ┌──────────────┼──────────────┐                      │
│         │              │              │                       │
│   V3 - 叙事与体验    V4 - 设计研究   V5 - 场景与行业        │
│   情感共鸣官         战略智库         运营架构师             │
│   (3个子角色)        (2个子角色)      (7个子角色)            │
│         │              │              │                       │
│         └──────────────┼──────────────┘                      │
│                        ▼                                      │
│              V6 - 专业总工程师 (Chief Engineer)              │
│              技术实现 | 工程落地 | 成本控制                  │
│                      (4个子角色)                             │
│                                                               │
│         (V7 - 情感洞察专家 - 实验性角色)                     │
└─────────────────────────────────────────────────────────────┘
```

### 📊 角色统计

| 专家类别 | 配置文件 | 子角色数量 | 总代码量 | 核心职责 |
|---------|---------|-----------|---------|---------|
| **V2** 设计总监 | `v2_design_director.yaml` | 6 | 1455行 | 总体规划、方案整合 |
| **V3** 叙事与体验 | `v3_narrative_expert.yaml` | 3 | 486行 | 情感叙事、体验设计 |
| **V4** 设计研究员 | `v4_design_researcher.yaml` | 2 | 409行 | 案例研究、方法论 |
| **V5** 场景与行业 | `v5_scenario_expert.yaml` | 7 | 1947行 | 行业运营、场景策略 |
| **V6** 专业总工程师 | `v6_chief_engineer.yaml` | 4 | 1719行 | 技术实现、工程落地 |
| **V7** 情感洞察 | `v7_emotional_insight_expert.yaml` | ? | ? | 实验性角色 |

**总计**: 22+ 个细分专家角色 | 6000+ 行配置代码

---

## 2. 角色定义结构

### 🏗️ 配置文件架构

每个专家配置文件遵循统一的 YAML 结构：

```yaml
# ============================================================================
# 文件头部元数据
# ============================================================================
# 版本: v2.x
# 更新日期: YYYY-MM-DD
# 本文件定义了XX类细分专家角色...
# ============================================================================

## 🔧 模板变量说明 (Template Variables Documentation)
# {user_specific_request} - 用户任务动态注入

## 📌 置信度校准指南 (Confidence Calibration Guide)
# 0.9-1.0: 输入完整，所有字段可充分展开
# 0.7-0.9: 小幅缺失，可基于专业判断
# 0.5-0.7: 关键信息缺失，仅方向性建议
# < 0.5: 任务超出范围或信息极度匮乏

## 📌 版本历史 (Version History)
# v2.x: 更新说明

# ============================================================================
# 角色定义主体
# ============================================================================
VX_类别名称:
  description: "类别简短描述"
  roles:
    "X-Y":  # 角色ID
      name: "角色中文名称"
      description: "角色职责描述"
      keywords: ["关键词1", "关键词2", ...]  # 用于权重计算
      system_prompt: |
        ### **🔧 v7.63.1: 工具使用指南**
        工具列表及使用策略...

        ### **1. 身份与任务**
        角色定位与核心任务...

        ### **动态本体论框架**
        类目体系注入规则...

        ### **🆕 输出模式判断协议**
        Targeted vs Comprehensive 模式选择...

        ### **2. 输出定义**
        Pydantic模型结构定义...

        ### **3. Targeted Analysis 模板**
        针对性分析模板...

        ### **🔥 专家主动性协议**
        自主决策与灵活性机制...
```

### 🔑 关键配置字段

#### 1. **角色元数据** (Role Metadata)
```yaml
name: "角色中文名称"  # 显示名称
description: "角色职责描述"  # 核心定位
keywords: ["关键词"]  # 用于RoleWeightCalculator权重计算
```

#### 2. **系统提示词** (System Prompt)
- **长度**: 通常 150-300 行
- **结构**: 分为 7-10 个标准章节
- **特点**: 支持模板变量动态注入

#### 3. **输出模型** (Pydantic Schema)
- 嵌入在 `system_prompt` 中
- 定义标准交付物结构
- 支持 `Targeted` 和 `Comprehensive` 两种模式

---

## 3. 六大专家类别详解

### 🎯 V2 - 设计总监 (Design Director)

**核心定位**: "项目总设计师 (Project Design Principal)"

**6个子角色**:

| 角色ID | 名称 | 适用场景 | 关键能力 |
|-------|------|---------|---------|
| **2-0** | 项目设计总监 | 多业态综合体 | 总体规划、专业协调、Master Plan |
| **2-1** | 居住空间设计总监 | 住宅、别墅、公寓 | 户型设计、生活场景、人性化细节 |
| **2-2** | 商业零售设计总监 | 购物中心、零售店 | 动线组织、视觉营销、商业氛围 |
| **2-3** | 办公空间设计总监 | 企业办公、联合办公 | 工位布局、协作空间、企业文化 |
| **2-4** | 酒店餐饮设计总监 | 酒店、餐厅、民宿 | 服务流线、氛围营造、体验设计 |
| **2-5** | 文化公共建筑总监 | 博物馆、图书馆、剧院 | 公共性、文化表达、场所精神 |
| **2-6** | 建筑及景观总监 | 建筑设计、景观规划 | 建筑形态、室外空间、环境整合 |

**配置特点**:
- **LLM参数**: `temperature=0.6, max_tokens=8000` (理性决策)
- **工具**: 仅 `ragflow_kb_tool` (内部知识库)
- **输出**: 支持动态本体论注入
- **灵活性**: 强 - 通过 `custom_analysis` 处理非标需求

---

### 💬 V3 - 叙事与体验专家 (Narrative & Experience Expert)

**核心定位**: "首席共情官 (Chief Empathy Officer)"

**3个子角色**:

| 角色ID | 名称 | 叙事原点 | 关键能力 |
|-------|------|---------|---------|
| **3-1** | 个体叙事与心理洞察 | 个体 (Individual) | 人物画像、心理洞察、生活方式 |
| **3-2** | 品牌叙事与顾客体验 | 组织 (Organization) | 品牌故事、顾客旅程、情感连接 |
| **3-3** | 文化叙事与符号转译 | 概念 (Concept) | 文化解码、符号转译、理念具象化 |

**配置特点**:
- **LLM参数**: `temperature=0.75, max_tokens=10000` (创意叙事)
- **工具**: 3个 - `bocha_search`, `tavily_search`, `ragflow_kb_tool`
- **标识**: `is_creative_narrative=True` (v7.10创意叙事模式)
- **输出**: 叙事地图、体验蓝图

**叙事原点分类**:
```
个体 (Person) → V3-1 → 情感、心理、价值观
   ↓
组织 (Brand) → V3-2 → 品牌、商业、体验
   ↓
概念 (Idea) → V3-3 → 文化、符号、理念
```

---

### 🔍 V4 - 设计研究员 (Design Researcher)

**核心定位**: "首席洞察官 (Chief Insights Officer)" / "战略智库 & 方法论大师"

**2个子角色**:

| 角色ID | 名称 | 研究焦点 | 关键能力 |
|-------|------|---------|---------|
| **4-1** | 案例与对标策略师 | 案例 (Cases) | 竞品分析、对标研究、模式拆解 |
| **4-2** | 体系与方法论架构师 | 体系 (Systems) | 方法论构建、框架设计、系统思维 |

**配置特点**:
- **LLM参数**: `temperature=0.6, max_tokens=8000` (理性研究)
- **工具**: 4个 - `bocha_search`, `tavily_search`, `arxiv_search`, `ragflow_kb_tool`
- **输出**: 研究报告、方法论框架、案例库

**研究方法论**:
```
案例研究 (Case Study)
  ↓
拆解分析 (Deconstruction)
  ↓
模式提炼 (Pattern Extraction)
  ↓
框架构建 (Framework Building)
  ↓
可复用智慧产品 (Reusable Insights)
```

---

### 🏪 V5 - 场景与行业专家 (Scenario & Industry Expert)

**核心定位**: "首席行业运营官 (Chief Industry & Operations Officer)" / "价值实现架构师"

**7个子角色** (行业纵向分类):

| 角色ID | 名称 | 适用行业 | 关键能力 |
|-------|------|---------|---------|
| **5-0** | 通用场景策略师 | 跨行业/未明确 | 第一性原理、通用场景解构 |
| **5-1** | 居住场景与生活方式 | 住宅、社区 | 生活方式、居住模式、户型策略 |
| **5-2** | 商业零售运营专家 | 零售、购物中心 | 零售运营、动线设计、坪效优化 |
| **5-3** | 企业办公策略专家 | 办公、联合办公 | 办公模式、工位策略、效率优化 |
| **5-4** | 酒店餐饮运营专家 | 酒店、餐饮 | 服务流程、空间效率、收益管理 |
| **5-5** | 文化教育场景专家 | 文化、教育、公共 | 公共服务、文化活动、教育模式 |
| **5-6** | 医疗康养场景专家 | 医疗、康养、健康 | 医疗流程、康养服务、健康管理 |

**配置特点**:
- **LLM参数**: `temperature=0.6, max_tokens=8000`
- **工具**: 3个 - `bocha_search`, `tavily_search`, `ragflow_kb_tool`
- **输出**: 运营蓝图、场景需求、KPI指标

**行业知识体系**:
```
行业特识 (Industry Specifics)
  ├─ 用户画像 (User Profiles)
  ├─ 运营模式 (Operation Models)
  ├─ 空间需求 (Space Requirements)
  ├─ 功能配比 (Function Mix)
  └─ KPI指标 (Performance Metrics)
```

---

### ⚙️ V6 - 专业总工程师 (Chief Engineer)

**核心定位**: "首席实现官 (Chief Delivery Officer)" / "价值工程师"

**4个子角色** (工程学科分类):

| 角色ID | 名称 | 工程领域 | 关键能力 |
|-------|------|---------|---------|
| **6-1** | 结构与幕墙工程师 | 结构、外立面 | 结构安全、形态实现、幕墙技术 |
| **6-2** | 机电与智能化工程师 | 机电、智能化 | 系统设计、智能控制、能耗优化 |
| **6-3** | 室内工艺与材料专家 | 室内、材料 | 材料选择、工艺节点、施工落地 |
| **6-4** | 成本与价值工程师 | 成本、价值工程 | 成本控制、价值优化、ROI分析 |

**配置特点**:
- **LLM参数**: `temperature=0.6, max_tokens=8000` (技术精确)
- **工具**: 4个 - `bocha_search`, `tavily_search`, `arxiv_search`, `ragflow_kb_tool`
- **输出**: 技术方案、工程计算、成本估算

**工程决策优先级**:
```
1. 规范符合性 (Code Compliance)
   ↓
2. 结构安全性 (Structural Safety)
   ↓
3. 施工可行性 (Constructability)
   ↓
4. 成本合理性 (Cost Efficiency)
   ↓
5. 维护便利性 (Maintainability)
```

---

### 🌟 V7 - 情感洞察专家 (Emotional Insight Expert)

**状态**: 实验性角色 (Experimental)

**配置文件**: `v7_emotional_insight_expert.yaml`

**说明**: 该角色可能是为特定项目或新功能设计的扩展专家，需进一步分析配置内容。

---

## 4. 配置文件架构

### 📁 文件组织

```
intelligent_project_analyzer/config/roles/
├── v2_design_director.yaml       (1455行)
├── v3_narrative_expert.yaml      (486行)
├── v4_design_researcher.yaml     (409行)
├── v5_scenario_expert.yaml       (1947行)
├── v6_chief_engineer.yaml        (1719行)
├── v7_emotional_insight_expert.yaml
└── KEYWORDS_GUIDELINE.md         (关键词配置指南)
```

### 🔧 配置加载机制

**加载流程**:
```python
# 1. RoleManager 初始化时加载所有配置文件
role_manager = RoleManager()

# 2. 解析 YAML 配置文件
roles_config = load_yaml_config("v2_design_director.yaml")

# 3. 提取角色元数据
role_id = "2-1"
role_config = roles_config["V2_设计总监"]["roles"]["2-1"]

# 4. 构造完整角色ID
full_role_id = f"V2_居住空间设计总监_2-1"

# 5. SpecializedAgentFactory 使用配置创建专家实例
agent = factory.create_agent(full_role_id, role_config)
```

**关键代码路径**:
- `intelligent_project_analyzer/core/role_manager.py` - 角色配置管理
- `intelligent_project_analyzer/agents/specialized_agent_factory.py` - 专家工厂

---

## 5. 关键机制解析

### 🎯 机制1: 模板变量注入

**变量**: `{user_specific_request}`

**注入时机**: 专家执行时由 `SpecializedAgentFactory` 动态替换

**数据来源优先级**:
```python
# 优先级1: 角色专属任务 (由 DynamicProjectDirector 分配)
task = state.get(f"{role_id}_task")

# 优先级2: 通用项目任务描述
task = state.get("task_description")

# 优先级3: 默认 fallback
task = "完成您所擅长领域的专业分析"
```

**示例替换**:
```yaml
# 配置文件原文
system_prompt: |
  你的核心任务是: {user_specific_request}

# 运行时替换后
system_prompt: |
  你的核心任务是: 为这个200㎡的别墅设计现代侘寂风格的居住空间
```

---

### 📊 机制2: 置信度校准体系

**统一标准** (所有角色遵循):

```
┌─────────────┬──────────────────────────────────────────┐
│ 置信度区间   │ 判断标准                                  │
├─────────────┼──────────────────────────────────────────┤
│ 0.9 - 1.0   │ ✅ 输入完整，所有标准字段可充分展开       │
│             │ ✅ 设计方案成熟且可落地                   │
├─────────────┼──────────────────────────────────────────┤
│ 0.7 - 0.9   │ ⚠️ 信息有少量缺失，可基于专业判断         │
│             │ ⚠️ 方案接近最终，需少量补充               │
├─────────────┼──────────────────────────────────────────┤
│ 0.5 - 0.7   │ ⚠️ 关键信息严重缺失（预算/面积/功能）     │
│             │ ⚠️ 仅提供方向性、探索性建议               │
├─────────────┼──────────────────────────────────────────┤
│ < 0.5       │ ❌ 任务超出角色专业范围                   │
│             │ ❌ 信息缺失到无法进行有效设计             │
│             │ 建议在 custom_analysis 中说明            │
└─────────────┴──────────────────────────────────────────┘
```

**作用**:
1. **质量标识**: 向后续专家和用户传递输出质量信号
2. **风险预警**: 识别信息不足或任务不匹配的场景
3. **审核依据**: 人工审核节点优先检查低置信度输出

---

### 🔄 机制3: 双模式输出协议

**输出模式判断** (v7.63.1新增):

```python
class FlexibleOutput(BaseModel):
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str  # 用户问题焦点
    confidence: float

    # Targeted模式: 仅填充此字段
    targeted_analysis: Optional[str] = None

    # Comprehensive模式: 填充以下5个标准字段
    standard_field_1: Optional[...] = None
    standard_field_2: Optional[...] = None
    # ...
```

**判断逻辑**:
```
用户问题类型判断
  ├─ 针对性问答 (Targeted)
  │  └─ 关键词: "如何...", "什么是...", "是否..."
  │  └─ 行为: 仅填充 targeted_analysis
  │
  └─ 完整报告 (Comprehensive)
     └─ 关键词: "完整方案", "系统分析", "全面设计"
     └─ 行为: 填充所有标准字段
```

**优势**:
- ✅ **灵活性**: 避免简单问题生成冗余输出
- ✅ **效率**: 节省30-50% Token（针对性问答）
- ✅ **质量**: 完整报告模式保证输出深度

---

### 🛠️ 机制4: 动态本体论注入

**概念**: 根据用户需求动态注入相关的类目体系

**占位符**: `{{DYNAMIC_ONTOLOGY_INJECTION}}`

**注入内容示例**:
```markdown
### **动态本体论框架 (Dynamic Ontology Framework)**

**本项目的核心设计维度** (从用户需求自动解析):
1. **空间功能**: 客厅、卧室、书房、厨房...
2. **设计风格**: 现代简约、侘寂美学、工业风...
3. **用户群体**: 三口之家、独居青年、多代同堂...
4. **技术要求**: 智能家居、节能环保、无障碍...

你的分析必须覆盖以上维度，确保与项目需求对齐。
```

**实现** (v7.100+):
- 由 `DynamicOntologyService` 根据结构化需求生成
- 在专家执行前注入到 `system_prompt`
- 替代原有的静态类目体系

---

## 6. 工具使用策略

### 🔧 工具分配矩阵

| 专家类别 | 工具1 | 工具2 | 工具3 | 工具4 | 工具使用原则 |
|---------|-------|-------|-------|-------|-------------|
| **V2** 设计总监 | ✅ ragflow | ❌ | ❌ | ❌ | 综合优先，仅用内部案例 |
| **V3** 叙事与体验 | ✅ bocha | ✅ tavily | ✅ ragflow | ❌ | 优先真实故事，文化适配 |
| **V4** 设计研究员 | ✅ bocha | ✅ tavily | ✅ arxiv | ✅ ragflow | 数据优先，学术支撑 |
| **V5** 场景与行业 | ✅ bocha | ✅ tavily | ❌ | ✅ ragflow | 运营数据优先，行业标准 |
| **V6** 专业总工程师 | ✅ bocha | ✅ tavily | ✅ arxiv | ✅ ragflow | 规范优先，技术验证 |

### 🎯 工具使用原则

#### 原则1: 优先级顺序
```
内部知识库 (ragflow_kb_tool)
  ↓ 复用公司经验
中文搜索 (bocha_search)
  ↓ 本土案例、规范
国际搜索 (tavily_search)
  ↓ 全球最佳实践
学术搜索 (arxiv_search)
  ↓ 前沿技术验证
```

#### 原则2: 文化适配
```
中文项目/国内规范 → 优先 bocha_search
国际项目/海外案例 → 优先 tavily_search
```

#### 原则3: 引用来源
所有使用工具获取的信息必须标注来源：
- ✅ "参考茑屋书店2023年案例..."
- ✅ "根据GB 50210-2018规范..."
- ✅ "借鉴Airbnb品牌叙事策略..."

#### 原则4: 克制使用
```
何时使用工具:
✅ 需要外部数据、真实案例、规范标准
✅ 需要验证技术可行性、商业模式
✅ 用户明确要求"参考"、"对标"

何时不使用工具:
❌ 可基于已有信息和专业经验判断
❌ 纯创意性、理论性分析
❌ 信息已由其他专家提供（V2综合模式）
```

---

## 7. 质量保证机制

### ✅ 输入验证机制

**配置位置**: 每个角色的 `system_prompt` 第4章节

**验证内容**:
```python
# 伪代码示例
if not user_specific_request:
    confidence = 0.3
    custom_analysis = "❌ 任务描述缺失，无法生成有效分析"

if "预算" not in requirements and "成本" in user_request:
    confidence = max(confidence, 0.6)
    custom_analysis += "⚠️ 缺少预算信息，方案仅供参考"
```

### 🚫 输出反模式检测

**配置位置**: 每个角色的注释说明

**常见反模式**:
1. **过度泛化**: 输出通用建议而非项目具体方案
2. **跨界越权**: V3专家执行V6的技术计算
3. **信息堆砌**: 大量搜索结果未经消化直接输出
4. **忽略任务**: 未围绕 `{user_specific_request}` 展开

**检测方式**:
- 自动: `custom_analysis` 字段标记异常
- 人工: 审核节点检查低置信度输出

### 📏 输出规范约束

**Pydantic模型强制约束**:
```python
class ExpertOutput(BaseModel):
    output_mode: Literal["targeted", "comprehensive"]  # 必选
    confidence: float = Field(ge=0.0, le=1.0)  # 0-1范围
    user_question_focus: str  # 必填

    # 字段长度约束
    targeted_analysis: Optional[str] = Field(max_length=4000)
    decision_rationale: str = Field(min_length=50, max_length=1000)
```

**LLM参数约束**:
```python
ROLE_LLM_PARAMS = {
    "V2": {"temperature": 0.6, "max_tokens": 8000},
    "V3": {"temperature": 0.75, "max_tokens": 10000},  # 创意叙事
    "V4": {"temperature": 0.6, "max_tokens": 8000},
    "V5": {"temperature": 0.6, "max_tokens": 8000},
    "V6": {"temperature": 0.6, "max_tokens": 8000},
}
```

---

## 8. 配置演进历史

### 📅 版本迭代

```
v2.3 (初始版本)
  └─ 定义基础角色结构，标准输出字段

v2.4
  └─ 优化 custom_analysis 字段，增强灵活性

v2.5
  └─ 添加置信度校准指南，输入验证机制

v2.6 / v2.7 / v2.8 (当前)
  └─ 模板变量说明
  └─ 输出反模式说明
  └─ 与 v7.19 专家工厂对齐
  └─ 工具使用指南 (v7.63.1)
  └─ 双模式输出协议
  └─ 动态本体论注入
```

### 🔄 与系统版本对齐

| 配置版本 | 系统版本 | 关键对齐项 |
|---------|---------|-----------|
| v2.6-v2.8 | v7.19+ | SpecializedAgentFactory 加载机制 |
| v7.63.1 | v7.63.1 | 工具使用指南标准化 |
| v7.100+ | v7.100+ | 动态本体论注入 |

---

## 9. 使用指南

### 🎯 如何选择专家？

**选择流程**:
```
用户需求
  ↓
需求分类 (RequirementsAnalyst)
  ↓
关键词匹配 (RoleWeightCalculator)
  ↓
权重计算 (基于 keywords 字段)
  ↓
动态选择 (DynamicProjectDirector)
  ↓
LLM智能决策 (3-8个专家)
```

**权重计算示例**:
```python
# 用户需求: "设计一个200㎡现代简约风格的三口之家住宅"

# 关键词提取: ["住宅", "居住", "家庭", "生活"]

# 角色匹配:
V2_居住空间设计总监_2-1: 权重 0.95 ✅ (keywords包含"住宅")
V3_个体叙事与心理洞察_3-1: 权重 0.85 ✅ (keywords包含"家庭")
V5_居住场景与生活方式_5-1: 权重 0.90 ✅ (keywords包含"居住")
V6_室内工艺与材料_6-3: 权重 0.60 (通用角色)
```

### 📝 如何修改专家配置？

**修改流程**:
```
1. 编辑对应的 YAML 配置文件
   └─ 路径: intelligent_project_analyzer/config/roles/vX_xxx.yaml

2. 修改关键字段:
   ├─ name: 角色名称
   ├─ keywords: 关键词列表 (影响权重计算)
   └─ system_prompt: 提示词内容

3. 验证配置:
   └─ 运行 validate_yaml.py 检查语法

4. 重启系统:
   └─ RoleManager 会自动重新加载配置
```

**注意事项**:
- ⚠️ 修改 `keywords` 会影响权重计算和角色选择
- ⚠️ 修改 `system_prompt` 需保持模板变量占位符
- ⚠️ Pydantic模型定义必须与代码中的类定义一致

### 🆕 如何添加新专家？

**添加流程**:
```yaml
# 1. 在现有配置文件中添加新角色
"X-Y":  # 新角色ID
  name: "新专家名称"
  description: "职责描述"
  keywords: ["关键词1", "关键词2"]
  system_prompt: |
    # 复制现有角色的提示词模板
    # 修改专业领域描述
    # 调整输出字段定义
```

**注册到系统**:
```python
# RoleManager 会自动发现新角色
# 无需修改代码，配置驱动架构
```

---

## 10. 最佳实践

### ✅ 配置文件维护

1. **版本控制**: 每次修改更新 `version_history`
2. **文档化**: 在注释中说明修改原因和影响范围
3. **测试验证**: 修改后运行测试确保无语法错误
4. **备份**: 修改前创建 `.backup` 备份文件

### 🎯 关键词优化

**好的关键词**:
- ✅ 具体、明确: "住宅", "零售", "办公"
- ✅ 多维度: 包含行业、场景、功能、风格
- ✅ 中英文结合: "综合体", "master plan"

**避免的关键词**:
- ❌ 过于泛化: "设计", "分析"
- ❌ 与其他角色重复度过高
- ❌ 罕见词汇（难以匹配）

### 📏 提示词质量

**优秀提示词特征**:
1. **结构清晰**: 分章节，有标题层级
2. **任务明确**: 突出核心任务占位符
3. **输出规范**: 详细定义Pydantic模型
4. **示例丰富**: 提供正反案例
5. **灵活机制**: 支持Targeted和Comprehensive模式

---

## 11. 故障排查

### ❌ 常见问题

#### Q1: 专家未被选中？
**排查步骤**:
1. 检查 `keywords` 是否包含需求相关词汇
2. 查看权重计算日志 (`RoleWeightCalculator`)
3. 检查 DynamicProjectDirector 是否过滤了该角色

#### Q2: 输出格式错误？
**排查步骤**:
1. 验证 Pydantic 模型定义是否正确
2. 检查 LLM 是否返回了 JSON
3. 查看 `with_structured_output` 的解析日志

#### Q3: 工具调用失败？
**排查步骤**:
1. 确认角色配置中包含该工具
2. 检查工具服务是否正常运行
3. 查看 `tool_callback` 的调用日志

---

## 12. 统计与分析

### 📊 配置规模统计

```
总配置行数: 6000+ 行
├─ V2: 1455行 (24.3%)
├─ V3: 486行 (8.1%)
├─ V4: 409行 (6.8%)
├─ V5: 1947行 (32.5%)
└─ V6: 1719行 (28.7%)

平均每个角色: ~270行配置
最大角色配置: V5-2 商业零售运营专家 (~400行)
```

### 🎯 角色覆盖度分析

**行业垂直覆盖**:
- ✅ 住宅居住 (V2-1, V5-1)
- ✅ 商业零售 (V2-2, V5-2)
- ✅ 办公空间 (V2-3, V5-3)
- ✅ 酒店餐饮 (V2-4, V5-4)
- ✅ 文化教育 (V2-5, V5-5)
- ✅ 医疗康养 (V5-6)
- ✅ 建筑景观 (V2-6)

**功能横向覆盖**:
- ✅ 设计规划 (V2全系)
- ✅ 情感叙事 (V3全系)
- ✅ 战略研究 (V4全系)
- ✅ 运营场景 (V5全系)
- ✅ 工程实现 (V6全系)

**覆盖盲区**:
- ⏳ 软装与艺术品配置
- ⏳ 家具与产品设计
- ⏳ 照明设计专家
- ⏳ 声学与环境控制

---

## 13. 相关文档

### 📚 核心文档

- [动态专家机制复盘](DYNAMIC_EXPERT_MECHANISM_REVIEW.md) - 专家选择与批次调度
- [Agent架构文档](../AGENT_ARCHITECTURE.md) - 完整Agent架构
- [关键词配置指南](../../intelligent_project_analyzer/config/roles/KEYWORDS_GUIDELINE.md) - 关键词维护规范

### 🔗 相关代码

- `intelligent_project_analyzer/core/role_manager.py` - 角色配置管理器
- `intelligent_project_analyzer/agents/specialized_agent_factory.py` - 专家工厂
- `intelligent_project_analyzer/agents/dynamic_project_director.py` - 动态选择器
- `intelligent_project_analyzer/services/role_weight_calculator.py` - 权重计算器

---

## 附录: 配置文件模板

### 📋 新角色配置模板

```yaml
VX_类别名称:
  description: "类别定位"
  roles:
    "X-Y":
      name: "角色名称"
      description: "角色职责"
      keywords: ["关键词1", "关键词2", "关键词3"]
      system_prompt: |
        ### **🔧 v7.63.1: 工具使用指南**
        [工具列表及策略]

        ### **1. 身份与任务**
        你是一位顶级的 **[角色名称]**，核心定位是 **"[英文定位]"**。

        **核心任务**: {user_specific_request}

        ---

        ### **动态本体论框架**
        {{DYNAMIC_ONTOLOGY_INJECTION}}

        ---

        ### **🆕 输出模式判断协议**
        [Targeted vs Comprehensive 判断逻辑]

        ---

        ### **2. 输出定义**
        ```python
        class VX_Y_FlexibleOutput(BaseModel):
            output_mode: Literal["targeted", "comprehensive"]
            confidence: float
            # [其他字段定义]
        ```

        ---

        ### **3. Targeted Analysis 模板**
        [针对性问答模板]

        ---

        ### **🔥 专家主动性协议**
        [灵活性机制]
```

---

**文档维护者**: GitHub Copilot
**最后更新**: 2026-02-10
**版本**: v1.0
