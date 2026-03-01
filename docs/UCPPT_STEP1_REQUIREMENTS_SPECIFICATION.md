# UCPPT搜索模式第一步需求理解与深度分析 - 用户需求规格说明书

> **文档版本**: v7.310
> **创建日期**: 2026-02-04
> **最后更新**: 2026-02-04
> **关联版本**: v7.270 ~ v7.310

---

## 📋 目录

1. [概述](#1-概述)
2. [系统架构](#2-系统架构)
3. [核心功能规格](#3-核心功能规格)
4. [L0-L5 深度分析框架](#4-l0-l5-深度分析框架)
5. [12维动机分析模型](#5-12维动机分析模型)
6. [人性维度分析](#6-人性维度分析)
7. [解题思路生成](#7-解题思路生成)
8. [核心数据结构](#8-核心数据结构)
9. [API规格与SSE事件流](#9-api规格与sse事件流)
10. [前端交互流程](#10-前端交互流程)
11. [Prompt模板原文](#11-prompt模板原文)
12. [与Step 2-4的衔接](#12-与step-2-4的衔接)
13. [配置参数](#13-配置参数)

---

## 1. 概述

### 1.1 功能定位

UCPPT搜索模式第一步"需求理解与深度分析"是整个搜索流程的基础阶段，负责：

1. **深度理解用户问题**：通过L0-L5五层分析框架解构用户需求
2. **识别用户动机**：从12个动机维度分析用户的真实意图
3. **生成解题思路**：输出5-8步可执行的搜索清单（ProblemSolvingApproach）
4. **构建搜索框架**：为后续Step 2-4提供结构化输入

### 1.2 在4步流程中的位置

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Step 1: 需求理解与深度分析 ← 本文档                    │
│  用户问题 → L0对话式理解 → L1-L5深度分析 → 解题思路生成                    │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    Step 2: 搜索任务分解                                  │
│  生成具体搜索查询清单 → 用户可编辑 → 确认后执行                           │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    Step 3: 迭代式搜索（最多30轮）                         │
│  搜索执行 → 信息收集 → 反思评估 → 动态增补                                │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    Step 4: 总结生成                                      │
│  整合搜索结果 → 按框架生成最终报告                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.3 设计原则

| 原则 | 说明 |
|------|------|
| **智能开放** | LLM根据问题动态生成框架，不预设固定模板 |
| **高度具体化** | 输出必须包含用户关键特征，禁止泛化描述 |
| **可操作性** | 每步都有明确的action、purpose、expected_output |
| **MECE覆盖** | 通过coverage_check确保分析完整性 |
| **流式输出** | 实时推送分析进度，提升用户体验 |

---

## 2. 系统架构

### 2.1 核心文件结构

| 层级 | 文件路径 | 功能描述 |
|------|----------|----------|
| **核心引擎** | `intelligent_project_analyzer/services/ucppt_search_engine.py` | UCPPT深度迭代搜索引擎核心实现（约14,500行） |
| **API路由** | `intelligent_project_analyzer/api/routes/search_routes.py` | 提供 `/api/search/ucppt/stream` 等API端点 |
| **Prompt配置** | `intelligent_project_analyzer/config/prompts/search_question_analysis.yaml` | 第一步分析的Prompt模板配置（v7.310版本） |
| **前端页面** | `frontend-nextjs/app/search/[session_id]/page.tsx` | 搜索页面主组件（约4,500行） |
| **分析展示组件** | `frontend-nextjs/components/search/L0DialogueCard.tsx` | 第一步分析结果展示组件 |

### 2.2 调用流程

```
用户输入问题
       ↓
前端调用 /api/search/ucppt/stream (SSE)
       ↓
后端 UcpptSearchEngine.search_stream()
       ↓
_unified_analysis_stream() [两次LLM调用]
       │
       ├──→ 第一次调用：生成对话式分析（流式输出给用户）
       │         使用 dialogue_prompt_template
       │         输出：自然语言分析（问题解构、动机分析、解题思路）
       │
       └──→ 第二次调用：生成结构化JSON（系统内部使用）
                 使用 _build_unified_analysis_prompt
                 输出：SearchFramework + ProblemSolvingApproach
       ↓
SSE事件推送 → 前端渲染
```

---

## 3. 核心功能规格

### 3.1 输入规格

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | ✅ | 用户搜索查询（1-2000字） |
| `session_id` | string | ❌ | 会话ID（用于状态追踪） |
| `context` | object | ❌ | 上下文信息（历史对话等） |
| `phase_mode` | string | ❌ | 执行模式：`full`/`step1_only`/`step2_only` |

### 3.2 输出规格

第一步分析完成后，输出以下核心数据结构：

| 输出项 | 数据结构 | 说明 |
|--------|----------|------|
| **用户画像** | `StructuredUserInfo` | L0分析结果，包含用户身份、偏好、隐性需求 |
| **深度分析** | `L1-L5 Analysis` | 事实解构、多视角建模、核心张力、JTBD、锐度评估 |
| **解题思路** | `ProblemSolvingApproach` | 5-8步可执行搜索清单 |
| **搜索框架** | `SearchFramework` | 搜索目标列表、完成度追踪 |
| **框架清单** | `FrameworkChecklist` | 用于前端展示的结构化清单 |

### 3.3 v7.310 两板块输出结构

最新版本(v7.310)将输出优化为2个主要板块：

#### 板块1：问题分析（自然叙述）
- 问题解构（L1）
- 动机分析（L2）- 12维动机得分与理由
- 核心张力（L3）
- 人性维度洞察（如适用）
- 综合理解

#### 板块2：解题思路（维度框架）
- 输出结果框架
- 搜索执行框架
- 维度优先级与依赖关系
- 成功标准

---

## 4. L0-L5 深度分析框架

### 4.1 L0: 对话式理解

**目标**：从用户问题中提取结构化用户信息

**输出字段**：

```python
@dataclass
class StructuredUserInfo:
    # 用户基础画像
    demographics: Dict[str, str]  # 地点、年龄、职业、教育等
    identity_tags: List[str]      # 身份标签（3-5个）
    lifestyle: Dict[str, Any]     # 生活方式

    # 项目/场景信息
    project_context: Dict[str, Any]  # 类型、规模、约束、预算、时间

    # 偏好与参照
    preferences: Dict[str, List[str]]  # 风格参照、色彩偏好、材质偏好

    # 核心诉求
    core_request: Dict[str, Any]  # 显性需求 + 隐性需求列表

    # 地点特殊考量
    location_considerations: Dict[str, str]  # 气候、建筑、生活方式

    # 信息完整度评估
    completeness: Dict[str, Any]  # 已提供维度、缺失维度、置信度
```

### 4.2 L1: 问题解构

**目标**：将问题分解为第一性原理事实原子（MECE原则）

**分析维度**：
- 用户是谁？（身份、角色、背景）
- 要什么？（显性需求）
- 为什么？（隐性动机）
- 约束是什么？（时间、资源、能力）

**输出结构**：

```json
{
  "l1_facts": {
    "brand_entities": [
      {"name": "HAY", "product_lines": ["Palissade", "Mags"], "designers": ["Bouroullec兄弟"]}
    ],
    "location_entities": [
      {"name": "峨眉山七里坪", "climate": "湿润多雾", "altitude": "1300m"}
    ],
    "style_entities": ["北欧极简", "山地自然"],
    "person_entities": [{"name": "设计师", "role": "民宿主", "works": []}]
  }
}
```

### 4.3 L2: 多视角建模

**目标**：从多个学科视角构建用户系统模型

**视角池**（动态选择3-5个）：
- 心理学视角：用户的内在需求/恐惧/渴望
- 社会学视角：用户的身份/角色/关系网络
- 美学视角：用户的审美偏好/风格倾向
- 经济学视角：成本收益分析
- 技术可行性视角：实现难度评估
- 生态视角：环境可持续性
- 人类学视角：文化背景影响
- 符号学视角：符号意义解读

**选择原则**：
| 问题类型 | 优先视角 |
|----------|----------|
| 创造型问题 | 美学+心理学+符号学 |
| 决策型问题 | 经济学+技术可行性+风险评估 |
| 探索型问题 | 人类学+社会学+趋势分析 |

### 4.4 L3: 核心张力识别

**目标**：寻找问题中最尖锐的对立面

**常见对立模式**：
- 展示 vs 私密
- 效率 vs 体验
- 功能 vs 情感
- 专业 vs 通俗
- 几何秩序 vs 自然生长

**输出格式**：

```json
{
  "l3_tension": {
    "formula": "HAY几何工业感 vs 峨眉山有机自然感",
    "description": "北欧工业设计的精确几何与川西山地的有机自然形态存在视觉语言冲突",
    "resolution_strategy": "用HAY的几何框架作为'骨架'，用峨眉山的自然材料作为'肌肤'"
  }
}
```

### 4.5 L4: 用户任务定义（JTBD）

**目标**：明确"用户雇佣搜索完成什么任务"

**公式**：`当...时，我想要...，以便...`

**任务类型**：
| 任务类型 | 定义 | 示例 |
|----------|------|------|
| 功能任务 | 完成具体功能 | 获得设计方案 |
| 情感任务 | 获得情感满足 | 感受专业被理解 |
| 社会任务 | 满足社会期望 | 向客人展示品味 |

**输出示例**：
```
"当我需要为峨眉山民宿做空间设计时，我想要获得融合HAY北欧风格与在地文化的概念方案，以便在保持设计品质的同时创造独特的地域体验。"
```

### 4.6 L5: 锐度测试

**目标**：验证分析质量是否达标

**三问测试**：

| 维度 | 问题 | 及格标准 |
|------|------|----------|
| 专一性 | 此分析只适用于本问题吗？ | 分析结果不能套用于其他问题 |
| 可操作性 | 能直接指导下一步行动吗？ | 有明确的行动指引 |
| 深度 | 触及了用户未明说的深层诉求吗？ | 识别出隐性需求 |

**输出结构**：

```json
{
  "l5_sharpness": {
    "score": 85,
    "specificity": "此分析专门针对HAY+峨眉山的融合问题，不适用于其他品牌或地点",
    "actionability": "可直接指导搜索HAY产品线、峨眉山在地材料、融合案例",
    "depth": "识别出用户对'精致自然'的深层追求，超越表面的风格需求"
  }
}
```

---

## 5. 12维动机分析模型

### 5.1 动机类型定义

| 类型ID | 中文名 | 典型特征 | 识别关键词 |
|--------|--------|----------|------------|
| `cultural` | 文化认同 | 传统文化、地域特色、民族符号、精神传承 | 传统、文化、历史、传承 |
| `commercial` | 商业价值 | ROI、坪效、运营效率、竞争策略 | 营收、成本、效率、盈利 |
| `wellness` | 健康疗愈 | 物理健康、心理疗愈、医疗标准 | 健康、疗愈、养生、医疗 |
| `technical` | 技术创新 | 智能化、工程技术、系统集成 | 智能、技术、系统、创新 |
| `sustainable` | 可持续价值 | 环保、社会责任、绿色低碳 | 环保、绿色、可持续、节能 |
| `professional` | 专业职能 | 行业标准、专业设备、工作流程 | 专业、标准、规范、认证 |
| `inclusive` | 包容性 | 无障碍设计、特殊人群、尊严平等 | 无障碍、特殊人群、平等 |
| `functional` | 功能性 | 空间功能、实用性、动线布局 | 功能、实用、动线、收纳 |
| `emotional` | 情感性 | 情感体验、氛围营造、心理感受 | 感受、氛围、温馨、舒适 |
| `aesthetic` | 审美 | 视觉美感、艺术表达、风格呈现 | 美感、风格、艺术、设计 |
| `social` | 社交 | 人际互动、社群关系、交流空间 | 社交、聚会、交流、展示 |
| `mixed` | 综合 | 多种动机混合，无明显主导 | 综合、平衡、兼顾 |

### 5.2 动机分析输出格式

```markdown
**主导动机**（驱动整个项目）：
- **审美追求(aesthetic)** [5/5]：用户明确提及HAY品牌，追求北欧极简美学
- **文化认同(cultural)** [4/5]：强调峨眉山在地特色，希望融合川西文化

**次要动机**（需要兼顾）：
- **功能性(functional)** [3/5]：作为民宿需满足基本居住功能
- **商业价值(commercial)** [3/5]：民宿定位暗示需考虑运营效率
```

### 5.3 动机张力识别

系统会自动识别主导动机之间的对立或融合关系：

```
核心张力：审美追求(aesthetic) vs 文化认同(cultural)
- 北欧极简的几何理性 与 川西自然的有机感性 存在视觉语言冲突
- 解决策略：寻找两者的共同价值——"对自然材料的尊重"
```

---

## 6. 人性维度分析

### 6.1 触发条件

当用户问题涉及以下关键词时，自动启用人性维度分析：

```yaml
human_dimension_triggers:
  - "设计"
  - "装修"
  - "空间"
  - "生活"
  - "家"
  - "居住"
  - "体验"
  - "感受"
  - "氛围"
  - "风格"
  - "冥想"
  - "休息"
  - "舒适"
  - "温馨"
  - "私密"
  - "放松"
```

### 6.2 五大人性维度

| 维度 | 定义 | 分析要点 |
|------|------|----------|
| **情绪地图** (emotional_landscape) | 用户情绪转化路径 | 当前情绪状态 → 期望转化 → 通过答案获得的情绪价值 |
| **精神追求** (spiritual_aspirations) | 穿透功能需求的精神层面渴望 | 超越物质层面，用户真正追求的精神价值是什么 |
| **心理安全需求** (psychological_safety_needs) | 用户在对抗什么恐惧或不确定性 | 隐藏的焦虑、担忧、不安全感 |
| **仪式行为** (ritual_behaviors) | 问题背后涉及的日常仪式或习惯 | 晨起、入睡、用餐、工作等场景需求 |
| **记忆锚点** (memory_anchors) | 影响用户期望的情感记忆 | 童年记忆、重要经历、情感联结 |

### 6.3 输出示例

```markdown
### 人性维度洞察

1. **情绪地图**：从城市疲惫 → 自然疗愈 → 精神归属 → 内在平静
2. **精神追求**：在快节奏都市生活中寻找"有根"的归属感，民宿是精神家园的投射
3. **心理安全需求**：担心设计过于"网红化"而失去真实性，对抗"千篇一律"的焦虑
4. **仪式行为**：清晨看云海、午后品茶、夜间观星——需要为这些仪式预留空间
5. **记忆锚点**：可能有童年山村生活记忆，"木屋"、"炊烟"是情感触发点
```

---

## 7. 解题思路生成

### 7.1 ProblemSolvingApproach 数据结构

```python
@dataclass
class ProblemSolvingApproach:
    # === 任务本质识别 ===
    task_type: str  # research/design/decision/exploration/verification
    task_type_description: str
    complexity_level: str  # simple/moderate/complex/highly_complex
    required_expertise: List[str]  # 3-5个专业领域

    # === 搜索清单（v7.290 核心） ===
    solution_steps: List[Dict[str, Any]]
    # 每步结构:
    # {
    #   "step_id": "S1",
    #   "action": "搜索HAY品牌核心设计语言",
    #   "purpose": "建立源美学参照系",
    #   "expected_output": "HAY设计哲学、核心设计师",
    #   "search_keywords": ["HAY design", "HAY 设计语言"],
    #   "expected_sources": ["HAY官网", "Dezeen"],
    #   "success_criteria": "找到3个代表作品",
    #   "priority": "high",
    #   "task_type": "research"
    # }

    # === 关键突破口（1-3个） ===
    breakthrough_points: List[Dict[str, str]]
    # {"point": "...", "why_key": "...", "how_to_leverage": "..."}

    # === 预期产出形态 ===
    expected_deliverable: Dict[str, Any]
    # {
    #   "format": "report",
    #   "sections": ["设计理念", "色彩方案", "材质选择", ...],
    #   "key_elements": ["视觉参考", "产品推荐"],
    #   "quality_criteria": ["可执行性强", "视觉协调"]
    # }

    # === v7.290: MECE覆盖校验 ===
    coverage_check: Dict[str, Any]
    # {
    #   "covered_points": ["HAY品牌", "峨眉山环境"],
    #   "potentially_missing": ["预算约束", "施工可行性"],
    #   "user_entities": ["HAY", "峨眉山", "民宿"],
    #   "entity_coverage": {"HAY": "S1,S2", "峨眉山": "S3,S4"}
    # }

    # === v7.300: 创作指令和交付物 ===
    creation_command: str  # 一句话创作指令
    deliverables: List[str]  # 交付物清单（10-15项）
    final_output_format: str  # 最终输出格式说明
```

### 7.2 solution_steps 生成规范

每个步骤必须包含：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `step_id` | string | 步骤编号 | "S1" |
| `action` | string | 具体行动（包含搜索引导词） | "搜索HAY品牌核心设计语言" |
| `purpose` | string | 为什么需要这一步 | "建立源美学参照系" |
| `expected_output` | string | 预期产出 | "HAY设计哲学、核心设计师" |
| `search_keywords` | List[str] | 搜索关键词（2-5个，中英文混合） | ["HAY design", "HAY 设计语言"] |
| `expected_sources` | List[str] | 期望信息来源 | ["HAY官网", "Dezeen"] |
| `success_criteria` | string | 成功标准 | "找到3个代表作品" |
| `priority` | string | 优先级：high/medium/low | "high" |
| `task_type` | string | 任务类型：research/analysis/design/output | "research" |

### 7.3 生成示例

```json
{
  "solution_steps": [
    {
      "step_id": "S1",
      "action": "搜索HAY品牌核心设计语言",
      "purpose": "建立'源'美学参照系的基础认知",
      "expected_output": "HAY设计哲学（民主设计、功能美学）、核心设计师（Bouroullec兄弟等）",
      "search_keywords": ["HAY design philosophy", "HAY 设计语言", "HAY brand identity"],
      "expected_sources": ["HAY官网", "Dezeen", "设计媒体"],
      "success_criteria": "找到HAY官方设计理念描述和3个代表作品",
      "priority": "high",
      "task_type": "research"
    },
    {
      "step_id": "S2",
      "action": "查找HAY色彩系统与材质特征",
      "purpose": "获取可直接应用的视觉元素",
      "expected_output": "HAY标志性色彩（柔和灰、暖黄、雾蓝）、材质偏好（粉末涂层钢、实木、织物）",
      "search_keywords": ["HAY color palette", "HAY 色彩系统", "HAY materials"],
      "expected_sources": ["HAY官网", "Pinterest", "设计案例库"],
      "success_criteria": "提取出HAY的5种标志性色彩和3种核心材质",
      "priority": "high",
      "task_type": "research"
    },
    {
      "step_id": "S3",
      "action": "调研峨眉山七里坪气候与环境特征",
      "purpose": "理解设计的物理约束条件",
      "expected_output": "海拔1300m、湿润多雾气候、温差大、自然光线特点",
      "search_keywords": ["峨眉山七里坪气候", "峨眉山海拔", "四川山地气候"],
      "expected_sources": ["气象网站", "旅游攻略", "地理资料"],
      "success_criteria": "获取七里坪的年均温度、湿度、光照时长数据",
      "priority": "high",
      "task_type": "research"
    }
  ]
}
```

---

## 8. 核心数据结构

### 8.1 SearchFramework

搜索框架是Step 1的核心输出，贯穿整个搜索流程：

```python
@dataclass
class SearchFramework:
    # === 问题锚点 ===
    original_query: str      # 原始用户问题
    core_question: str       # 问题一句话本质（20字内）
    answer_goal: str         # 回答目标
    boundary: str            # 搜索边界（不搜什么）

    # === 搜索目标列表 ===
    targets: List[SearchTarget]  # 每个目标对应一个搜索维度

    # === 深度分析结果 ===
    l1_facts: List[str]          # L1 事实解构
    l2_models: Dict[str, str]    # L2 多视角建模
    l3_tension: str              # L3 核心张力
    l4_jtbd: str                 # L4 用户任务
    l5_sharpness: Dict[str, Any] # L5 锐度评估

    # === 用户画像 ===
    user_profile: Dict[str, Any]

    # === 进度追踪 ===
    overall_completeness: float  # 整体完成度 0-1
    completed_count: int         # 已完成目标数

    # === v7.300: 交付物 ===
    deliverables: List[str]      # 交付物清单（10-15项）
    final_output_format: str     # 最终输出格式说明
```

### 8.2 SearchTarget

统一的搜索目标单元：

```python
@dataclass
class SearchTarget:
    # === 基础信息 ===
    id: str                      # 目标ID (T1, T2, ...)

    # === v7.236: 语义明确字段 ===
    question: str                # 这个任务要回答什么问题？（问句形式）
    search_for: str              # 具体搜索什么内容
    why_need: str                # 找到后对回答有什么帮助
    success_when: List[str]      # 什么情况算搜索成功

    # === 分类与优先级 ===
    priority: int                # 优先级 1(高) / 2(中) / 3(低)
    category: str                # 类别: 品牌调研 / 案例参考 / 方案验证 / 背景知识

    # === 状态追踪 ===
    status: str                  # pending / searching / complete
    completion_score: float      # 完成度 0-1

    # === v7.232: 预设搜索关键词 ===
    preset_keywords: List[str]   # 预设的精准搜索关键词

    # === v7.260: 并行支持 ===
    dependencies: List[str]      # 依赖的任务ID
    can_parallel: bool           # 是否可并行
```

### 8.3 FrameworkChecklist

用于前端展示的框架清单：

```python
@dataclass
class FrameworkChecklist:
    # === 核心摘要 ===
    core_summary: str            # 问题一句话本质

    # === 搜索主线 ===
    main_directions: List[Dict]  # 主要搜索方向
    # 每个方向: {direction, purpose, targets, motivation_id}

    # === 边界 ===
    boundaries: List[str]        # 不涉及的内容

    # === 回答目标 ===
    answer_goal: str

    # === v7.300: 交付物 ===
    deliverables: List[str]
    final_output_format: str
    creation_command: str
```

---

## 9. API规格与SSE事件流

### 9.1 API端点

**端点**: `POST /api/search/ucppt/stream`

**请求体**:

```typescript
interface UcpptSearchRequest {
  query: string;                    // 搜索查询（1-2000字）
  max_rounds?: number;              // 最大搜索轮数，默认30
  confidence_threshold?: number;    // 信息充分度阈值，默认0.8
  session_id?: string;              // 会话ID
  phase_mode?: 'full' | 'step1_only' | 'step2_only';  // 执行模式
  framework_data?: object;          // step2_only时必填，用户编辑后的框架
}
```

**响应**: SSE (Server-Sent Events) 流

### 9.2 Step 1 相关的SSE事件类型

| 事件类型 | 数据结构 | 说明 | 触发时机 |
|----------|----------|------|----------|
| `phase` | `{phase, phase_name, message}` | 阶段开始 | 进入Step 1时 |
| `two_sections_stream` | `{content, current_section}` | v7.310 2板块流式输出 | 第一次LLM调用期间 |
| `two_sections_stream_complete` | `{section_contents}` | 2板块流式完成 | 第一次LLM调用完成 |
| `structured_info_ready` | `StructuredUserInfo` | 用户画像就绪 | JSON解析完成 |
| `problem_solving_approach_ready` | `ProblemSolvingApproach` | 解题思路就绪 | 解题思路生成完成 |
| `search_framework_ready` | `SearchFramework` | 搜索框架就绪 | 框架构建完成 |
| `step1_complete` | `{framework, approach, checklist}` | 第一步完成 | Step 1结束 |

### 9.3 事件数据示例

#### two_sections_stream 事件

```json
{
  "type": "two_sections_stream",
  "data": {
    "content": "这是一个有趣的设计融合挑战——**HAY的几何工业美学**与**峨眉山的有机自然气质**...",
    "current_section": 1
  }
}
```

#### step1_complete 事件

```json
{
  "type": "step1_complete",
  "data": {
    "framework": {
      "core_question": "HAY北欧风格与峨眉山在地文化的融合设计方案",
      "targets": [...],
      "deliverables": [...]
    },
    "approach": {
      "task_type": "design",
      "solution_steps": [...],
      "breakthrough_points": [...]
    },
    "checklist": {
      "core_summary": "...",
      "main_directions": [...]
    }
  }
}
```

---

## 10. 前端交互流程

### 10.1 页面组件结构

```
SearchPage (page.tsx)
├── 搜索输入区
├── 分析结果展示区
│   ├── L0DialogueCard           # 第一步分析结果
│   │   ├── 问题解构 (L1)
│   │   ├── 动机分析 (L2)
│   │   ├── 核心张力 (L3)
│   │   ├── 人性维度洞察
│   │   └── 综合理解
│   ├── FrameworkChecklistCard   # 框架清单
│   └── SearchTaskListCard       # 搜索任务列表
├── 搜索进度展示区
│   └── UcpptSearchProgress
└── 结果展示区
```

### 10.2 状态管理

```typescript
interface SearchState {
  status: 'idle' | 'analyzing' | 'searching' | 'synthesizing' | 'done' | 'error';
  currentPhase: 'analysis' | 'search' | 'synthesis';

  // Step 1 相关状态
  l0Content: string;              // 流式分析内容
  structuredInfo: StructuredUserInfo | null;
  problemSolvingApproach: ProblemSolvingApproach | null;
  searchFramework: SearchFramework | null;
  frameworkChecklist: FrameworkChecklist | null;

  // 进度信息
  statusMessage: string;
}
```

### 10.3 事件处理

```typescript
// 处理 SSE 事件
function handleSSEEvent(event: SSEEvent) {
  switch (event.type) {
    case 'two_sections_stream':
      const { content, current_section } = event.data;
      setSearchState(prev => ({
        ...prev,
        status: 'analyzing',
        currentPhase: 'analysis',
        l0Content: (prev.l0Content || '') + content,
        statusMessage: current_section === 1
          ? '正在分析问题...'
          : '正在制定解题思路...',
      }));
      break;

    case 'step1_complete':
      setSearchState(prev => ({
        ...prev,
        searchFramework: event.data.framework,
        problemSolvingApproach: event.data.approach,
        frameworkChecklist: event.data.checklist,
        statusMessage: '分析完成，准备开始搜索...',
      }));
      break;

    // ... 其他事件处理
  }
}
```

---

## 11. Prompt模板原文

### 11.1 dialogue_prompt_template (v7.310)

以下是 `search_question_analysis.yaml` 中的完整Prompt模板：

```yaml
dialogue_prompt_template: |
  {datetime_info}

  ## 用户搜索问题
  "{user_input}"

  ## 你的任务

  作为资深设计顾问，请对用户的需求进行深度分析，并提供解决问题的维度框架。

  **重要**：解题思路部分只给出"需要研究的维度"，不给出具体答案。具体答案将在Step 2搜索后产出。

  ## 分析流程（内部思考，不暴露给用户）

  ### 第一步：深度理解（L1-L5分析）
  - L1 问题解构：用户是谁？要什么？为什么？约束是什么？
  - L2 动机建模：从12个动机维度分析
  - L3 核心张力：识别主导动机之间的对立或融合关系
  - L4 用户任务：用户雇佣我们完成什么任务？
  - L5 锐度测试：这个分析是否专一、可操作、有深度？

  ### 第二步：人性维度分析（如适用）
  如果问题涉及设计/装修/空间/生活/家/居住/体验等关键词，分析：
  - 情绪地图、精神追求、心理安全需求、仪式行为、记忆锚点

  ### 第三步：问题类型识别
  识别问题类型（设计/创意/策略/技术/研究），并根据类型调整输出侧重点。

  ## 维度设计要求（关键）

  ### 1. 维度名称必须高度具体化

  **包含用户关键特征**：
  - ❌ 错误："空间布局与功能分区"（过于宽泛，适用于任何空间设计）
  - ✅ 正确："38岁独立女性的200平米大平层功能分区策略（社交区vs私密区平衡）"

  **包含核心主题**：
  - ❌ 错误："色彩体系研究"（过于通用）
  - ✅ 正确："Audrey Hepburn经典黑白灰色彩体系在现代大平层中的应用研究"

  [... 更多维度设计要求详见配置文件 ...]

  ## 输出格式（2个板块）

  ---

  **【使命1：我的理解】**

  ### 问题解构（L1）

  （用自然语言展示L1的分析结果，2-3句话，包含：用户身份、显性需求、隐性动机、关键约束）

  ### 动机分析（L2）

  从12个动机维度分析，我识别出：

  **主导动机**（驱动整个项目）：
  - **[动机名称(类型)]** [得分X/5]：[具体理由]
  - **[动机名称(类型)]** [得分X/5]：[具体理由]

  **次要动机**（需要兼顾）：
  - **[动机名称(类型)]** [得分X/5]：[具体理由]

  ### 核心张力（L3）

  [具体的张力描述，使用动机类型表达]

  ### 人性维度洞察（如适用）

  1. **情绪地图**：[具体的情绪转化路径]
  2. **精神追求**：[具体的精神层面渴望]
  3. **心理安全需求**：[具体的恐惧或不确定性]
  4. **仪式行为**：[具体的日常仪式]
  5. **记忆锚点**：[具体的情感记忆推断]

  ### 综合理解

  （基于以上L1-L4分析的综合描述）

  ---

  ## 解题思路

  **核心目标：**[一句话描述设计目标]

  ---

  ### 第一部分：输出结果框架

  **最终交付物类型：**[具体类型]

  **输出结构（3-5个主要板块）：**
  [... 具体板块内容 ...]

  ---

  ### 第二部分：搜索执行框架

  **维度1：[具体到用户情境的维度名称]**
  **服务于输出板块**：板块1、板块2

  **需要深入研究的方向**：
  - [研究方向1 - 包含用户关键特征]
  - [研究方向2]

  **关键问题**：
  - [问题1 - 针对用户具体情境]

  **预期产出**：
  - [具体的搜索结果类型和数量]

  [... 继续5-8个维度 ...]

  ---

  **维度优先级与依赖关系**
  **第一优先级**（基础研究，必须先完成）：
  **第二优先级**（依赖第一优先级）：
  **第三优先级**（依赖前两个优先级）：

  ---

  **成功标准**（5-8项）
  1. [标准1 - 可量化]

  ---

  **设计师洞察**：
  [2-3段自然语言说明核心价值]
```

### 11.2 统一分析Prompt (_build_unified_analysis_prompt)

用于第二次LLM调用，生成结构化JSON：

```python
def _build_unified_analysis_prompt(self, query: str, context: Optional[Dict] = None) -> str:
    """
    v7.270 重构：生成结构化分析JSON

    输出包含：
    - user_profile: 用户画像
    - analysis: L1-L5深度分析
    - problem_solving_approach: 解题思路
    - step2_context: 供Step 2使用的上下文
    """
    return f"""你是顶级战略顾问。用**庖丁解牛**的方式分析问题。

## 用户问题
{query}

## 输出规范

⛔ **绝对禁止**：
1. 元认知叙述：不描述你要怎么思考
2. 过程解释：不解释为什么要分析某个维度
3. 口语化词汇："好的"、"嗯"、"我想"

✅ **正确做法**：直接输出分析结果

## 分析要求

### 第一部分：理解用户
1. 用户画像（身份、标签）
2. 实体提取（6类实体：品牌/地点/风格/场景/竞品/人物）
3. 隐性需求推断
4. 动机类型识别（12维）

### 第二部分：深度分析
5. L1 事实解构（结构化实体清单）
6. L2 多视角建模（3-5个视角）
7. L3 核心张力（张力公式 + 解决策略）
8. L4 JTBD（当...时，我想要...，以便...）
9. L5 锐度自检（三问测试）

### 第三部分：解题思路
1. 任务本质识别
2. 搜索清单规划（5-8步，每步包含search_keywords）
3. 关键突破口（1-3个）
4. 预期产出形态
5. MECE覆盖校验

## 输出JSON

```json
{{
    "user_profile": {...},
    "analysis": {...},
    "problem_solving_approach": {...},
    "step2_context": {...}
}}
```
"""
```

---

## 12. 与Step 2-4的衔接

### 12.1 Step 1 → Step 2 数据传递

Step 1 完成后，向 Step 2 传递以下关键数据：

| 数据项 | 用途 |
|--------|------|
| `SearchFramework` | 作为搜索任务生成的基础 |
| `ProblemSolvingApproach.solution_steps` | 转换为具体的 `SearchTarget` 列表 |
| `step2_context` | 包含 core_question、answer_goal、breakthrough_tensions |
| `FrameworkChecklist` | 用于前端展示和用户编辑 |

### 12.2 Step 2: 搜索任务分解

**输入**: Step 1 的 `SearchFramework` + `ProblemSolvingApproach`

**处理**:
1. 将 `solution_steps` 转换为 `SearchTarget` 列表
2. 生成预设搜索关键词（`preset_keywords`）
3. 计算任务依赖关系
4. 用户可编辑任务列表

**输出**: 确认后的 `SearchTarget[]`

### 12.3 Step 3: 迭代式搜索

**输入**: Step 2 确认的 `SearchTarget[]`

**处理**:
1. 按优先级和依赖关系调度搜索任务
2. 每轮搜索后进行反思评估
3. 动态增补延展任务
4. 完成度追踪和停止判断

**关键参数**:
- `MAX_SEARCH_ROUNDS = 30` 最大搜索轮数
- `MIN_SEARCH_ROUNDS = 4` 最小搜索轮数
- `COMPLETENESS_THRESHOLD = 0.88` 回答完整度阈值

### 12.4 Step 4: 总结生成

**输入**: 所有轮次收集的 `sources` + `SearchFramework`

**处理**:
1. 按 `expected_deliverable.sections` 组织内容
2. 引用来源生成标注（[1]、[2]...）
3. 生成符合 `final_output_format` 的最终报告

**输出**: 结构化的最终答案

### 12.5 数据流图

```
Step 1: 需求理解与深度分析
├── 输入: query (用户问题)
├── 处理: L0-L5分析 + 12维动机 + 解题思路
└── 输出: SearchFramework + ProblemSolvingApproach
            ↓
Step 2: 搜索任务分解
├── 输入: SearchFramework
├── 处理: solution_steps → SearchTarget[]
└── 输出: 用户确认的 SearchTarget[]
            ↓
Step 3: 迭代式搜索
├── 输入: SearchTarget[]
├── 处理: 搜索 → 反思 → 增补（最多30轮）
└── 输出: all_sources[] + round_insights[]
            ↓
Step 4: 总结生成
├── 输入: all_sources + SearchFramework
├── 处理: 按 deliverables 结构生成
└── 输出: 最终报告
```

---

## 13. 配置参数

### 13.1 模型配置

```python
# 环境变量配置
UCPPT_THINKING_MODEL = os.getenv("UCPPT_THINKING_MODEL", "openai/gpt-4o")
UCPPT_EVAL_MODEL = os.getenv("UCPPT_EVAL_MODEL", "openai/gpt-4o")
SYNTHESIS_MODEL = "openai/gpt-4o"
```

### 13.2 搜索参数

```python
MAX_SEARCH_ROUNDS = 30              # 最大搜索轮数
MIN_SEARCH_ROUNDS = 4               # 最小搜索轮数
COMPLETENESS_THRESHOLD = 0.88       # 回答完整度阈值
MAX_PARALLEL_MAINLINES = 4          # 最大并行主线数
MAX_EXTENSION_ROUNDS = 3            # 最大延展轮次
```

### 13.3 质量阈值

```python
# 质量门控
QUALITY_GATE_THRESHOLD = 0.75       # 阶段质量及格线
L5_SHARPNESS_MIN_SCORE = 70         # L5锐度最低分
SEMANTIC_DEDUP_THRESHOLD = 0.85     # 语义去重阈值
```

### 13.4 YAML配置位置

```
intelligent_project_analyzer/config/prompts/search_question_analysis.yaml
```

主要配置项：
- `metadata.version`: 配置版本号
- `human_dimension_triggers`: 人性维度分析触发关键词
- `business_config.timeout_seconds`: 分析超时时间
- `system_prompt`: 系统提示词
- `dialogue_prompt_template`: 对话式分析Prompt模板

---

## 附录A：版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v7.270 | 2026-01-28 | 切换到OpenAI GPT-4o，两次LLM调用架构 |
| v7.290 | 2026-01-29 | solution_steps增强为可执行搜索清单 |
| v7.300 | 2026-01-29 | 4步工作流数据模型，新增deliverables |
| v7.302 | 2026-01-30 | 修复dialogue_prompt_template加载 |
| v7.303 | 2026-01-30 | 12维动机分析可见化，L1-L5完整输出 |
| v7.310 | 2026-01-31 | 2板块优化，维度高度具体化要求 |

---

## 附录B：相关文档

- [4-STEP-FLOW-README.md](../4-STEP-FLOW-README.md) - 4步骤流程概述
- [FRAMEWORK_CHECKLIST_DATA_FLOW_ANALYSIS.md](../FRAMEWORK_CHECKLIST_DATA_FLOW_ANALYSIS.md) - 框架清单数据流分析
- [UCPPT_STEP_SEPARATION_IMPLEMENTATION_v7.270.md](../UCPPT_STEP_SEPARATION_IMPLEMENTATION_v7.270.md) - Step分离实现文档
- [docs/v7.303-final-summary.md](v7.303-final-summary.md) - v7.303版本总结

---

*文档结束*
