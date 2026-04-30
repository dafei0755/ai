# UCPPT 搜索模式 Step 1：需求理解与深度分析

## 文档信息

| 属性 | 值 |
|------|-----|
| **文档版本** | v1.0 |
| **创建日期** | 2026-02-04 |
| **最后更新** | 2026-02-04 |
| **状态** | 已发布 |
| **作者** | AI Assistant |

---

## 1. 概述

### 1.1 功能定位

Step 1 "需求理解与深度分析" 是 UCPPT 4步骤搜索流程的第一步，负责深入理解用户需求并生成结构化的输出框架。该步骤是整个搜索流程的基础，直接影响后续搜索任务的质量和最终报告的价值。

### 1.2 核心目标

1. **深度理解用户需求** - 通过 L1-L5 分析框架，从多个维度解构用户问题
2. **识别显性与隐性需求** - 不仅理解用户明确表达的需求，还要挖掘潜在动机
3. **生成搜索导向的输出框架** - 为后续搜索任务提供清晰的方向和结构
4. **提供用户友好的反馈** - 以对话式语言向用户展示分析结果

### 1.3 设计原则

| 原则 | 说明 |
|------|------|
| **搜索导向** | 所有输出都应指向"可搜索"的信息需求，而非实施方案 |
| **用户友好** | 完全避免专业术语，使用对话式语言 |
| **结构化** | 强制使用标准化的分析框架，确保输出一致性 |
| **价值前置** | 先展示用户将获得什么，再解释分析过程 |

---

## 2. 功能需求

### 2.1 三阶段执行架构

Step 1 采用三阶段架构，确保分析深度和输出质量：

```
┌─────────────────────────────────────────────────────────────┐
│                    Stage 1: 内部分析                         │
│  输入: 用户原始输入                                          │
│  处理: L1-L5 结构化分析                                      │
│  输出: JSON 格式的分析结果                                   │
│  温度: 0.3 (低随机性)                                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Stage 2: 用户输出                         │
│  输入: Stage 1 的 JSON 结果                                  │
│  处理: 转化为对话式内容                                      │
│  输出: 3 个部分的用户友好文本                                │
│  温度: 0.7 (允许创意表达)                                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Stage 3: 验证与提取                       │
│  输入: Stage 1 + Stage 2 结果                                │
│  处理: 验证合规性，提取结构化数据                            │
│  输出: 完整的 DeepAnalysisResult                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 L1-L5 分析框架

#### 2.2.1 L1 问题解构 (Problem Deconstruction)

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `user_identity` | string | 用户身份描述 | "50岁室内设计师，计划回乡建房" |
| `explicit_needs` | string | 显性需求 | "需要300平米田园民居的设计参考" |
| `implicit_motivations` | string | 隐性动机 | "寻求职业转型，渴望归属感" |
| `key_constraints` | string | 关键约束 | "预算有限，需要考虑当地气候" |
| `analysis_perspective` | string | 分析视角 | "功利视角 + 情感视角" |

#### 2.2.2 L2 动机维度分析 (Motivation Dimensions)

**强制使用 12 个标准维度**（不可自创）：

| 类型 | 维度 | 说明 |
|------|------|------|
| **功能型** | 效率 | 追求更高的工作/生活效率 |
| **功能型** | 控制 | 希望掌控局面和结果 |
| **功能型** | 安全 | 规避风险，寻求稳定 |
| **情感型** | 归属 | 渴望被接纳和认同 |
| **情感型** | 认同 | 寻求自我价值确认 |
| **情感型** | 愉悦 | 追求快乐和满足感 |
| **社会型** | 地位 | 提升社会地位和声望 |
| **社会型** | 影响 | 希望影响他人和环境 |
| **社会型** | 连接 | 建立和维护人际关系 |
| **精神型** | 意义 | 寻找人生意义和目的 |
| **精神型** | 成长 | 追求个人成长和进步 |
| **精神型** | 超越 | 超越自我，追求更高境界 |

每个维度需包含：
- `score`: 1-5 分评分
- `reason`: 至少 30 字的评分理由
- `evidence`: 支持证据列表
- `scenario_expression`: 场景化表达（v3.1 新增）

#### 2.2.3 L3 核心张力 (Core Tension)

| 字段 | 类型 | 说明 |
|------|------|------|
| `primary_motivation` | string | 主导动机 |
| `secondary_motivation` | string | 次要动机 |
| `tension_formula` | string | 张力公式（"X vs Y" 或 "X + Y"） |
| `resolution_strategy` | string | 解决策略 |
| `hidden_insights` | list | 隐性需求洞察列表 |

#### 2.2.4 L4 JTBD 定义 (Jobs To Be Done)

**模板格式**：
```
为【用户身份】提供【信息类型】，帮助完成【任务1】与【任务2】
```

要求：
- `full_statement` 至少 50 字
- 必须明确用户身份、信息类型、具体任务

#### 2.2.5 L5 锐度测试 (Sharpness Test)

| 维度 | 评分范围 | 说明 |
|------|----------|------|
| `specificity_score` | 1-10 | 专一性：需求是否足够具体 |
| `actionability_score` | 1-10 | 可操作性：是否可转化为行动 |
| `depth_score` | 1-10 | 深度：分析是否足够深入 |
| `overall_quality` | 枚举 | 优秀/良好/合格/不合格 |

### 2.3 输出框架 (Output Framework)

#### 2.3.1 框架结构

```python
OutputFramework:
  - core_objective: str        # 核心目标（一句话）
  - deliverable_type: str      # 最终交付物类型
  - blocks: List[Block]        # 2-7 个输出板块
```

#### 2.3.2 板块结构

```python
Block:
  - id: str                    # 板块 ID（如 "block_1"）
  - name: str                  # 板块名称（>=15 字）
  - estimated_length: str      # 预计字数/页数
  - sub_items: List[str]       # 子板块列表
  - user_characteristics: str  # 用户特征关键词
  - search_focus: str          # 核心搜索焦点
  - indicative_queries: List   # 示范性搜索查询
```

#### 2.3.3 板块命名规范

**禁止使用**（实施导向）：
- ❌ "场地限制下的项目规划"
- ❌ "实施流程和时间节点把控"
- ❌ "成本控制与预算管理"
- ❌ "施工方案与工艺选择"

**推荐使用**（搜索导向）：
- ✅ "安藤忠雄清水混凝土与光影诗学在田园建筑中的应用研究"
- ✅ "50岁室内设计师的归乡住宅需求与案例分析"
- ✅ "四川广元地域特色与建筑文化探索"
- ✅ "300平米田园民居的空间布局案例参考"

### 2.4 用户输出格式

Stage 2 生成的用户友好输出必须包含以下三个部分：

#### 2.4.1 【我们如何理解您的需求】

- 以对话式语言描述对用户需求的理解
- 体现 L1-L5 分析的核心洞察
- 避免使用任何专业术语

#### 2.4.2 【您将获得什么】

- 清晰列出输出框架的各个板块
- 每个板块包含子项说明
- 使用编号结构（1.1, 1.2 等）

#### 2.4.3 【接下来的搜索计划】

- 简要说明后续搜索方向
- 让用户了解系统将如何工作

---

## 3. 非功能需求

### 3.1 性能要求

| 指标 | 要求 |
|------|------|
| Stage 1 执行时间 | < 15 秒 |
| Stage 2 执行时间 | < 20 秒 |
| Stage 3 执行时间 | < 5 秒 |
| 总执行时间 | < 40 秒 |
| Token 消耗 | ~11,000 tokens |

### 3.2 质量要求

| 指标 | 要求 |
|------|------|
| L2 维度覆盖率 | 100%（必须分析全部 12 个维度） |
| 板块名称长度 | >= 15 字 |
| JTBD 语句长度 | >= 50 字 |
| 锐度测试完整性 | 3 个维度全部评分 |

### 3.3 验证规则

#### Stage 1 验证

- [ ] L2 动机名称必须是 12 个标准维度之一
- [ ] L4 JTBD 必须包含所有必填字段
- [ ] L5 锐度测试必须有 3 个维度的评分和理由

#### Stage 2 验证

- [ ] 必须包含【我们如何理解您的需求】部分
- [ ] 必须包含【您将获得什么】部分
- [ ] 禁止包含术语：L1-L5、动机维度、核心张力、JTBD、锐度测试
- [ ] 必须包含子板块结构（如 1.1, 1.2 等编号）

---

## 4. 数据结构定义

### 4.1 DeepAnalysisResult

```python
@dataclass
class DeepAnalysisResult:
    """Step 1 深度分析结果"""

    # L1-L5 分析结果
    l1_problem_deconstruction: L1ProblemDeconstruction
    l2_motivation_dimensions: List[L2MotivationDimension]
    l3_core_tension: L3CoreTension
    l4_jtbd_definition: L4JTBDDefinition
    l5_sharpness_test: L5SharpnessTest

    # 输出框架
    output_framework: OutputFramework

    # 人性维度分析
    human_dimensions: HumanDimensions

    # 用户友好输出
    dialogue_content: str

    # 验证报告
    validation_report: ValidationReport
```

### 4.2 HumanDimensions

```python
@dataclass
class HumanDimensions:
    """人性维度分析"""

    emotional_landscape: str      # 情绪地图
    spiritual_aspirations: str    # 精神追求
    psychological_safety_needs: str  # 心理安全需求
    ritual_behaviors: str         # 仪式行为
    memory_anchors: str           # 记忆锚点
```

---

## 5. 接口定义

### 5.1 执行器接口

```python
class Step1DeepAnalysisExecutor:
    """Step 1 深度分析执行器"""

    async def execute(
        self,
        user_input: str,
        stream: bool = True
    ) -> DeepAnalysisResult:
        """
        执行深度分析

        Args:
            user_input: 用户原始输入
            stream: 是否启用流式输出

        Returns:
            DeepAnalysisResult: 完整的分析结果
        """
        pass
```

### 5.2 API 接口

```
POST /api/search/four-step/stream
Content-Type: application/json

Request:
{
    "user_input": "用户的问题或需求描述",
    "session_id": "可选的会话ID"
}

Response (SSE):
event: step1_dialogue_chunk
data: {"content": "对话内容片段"}

event: step1_extracting_structure
data: {"message": "正在提取结构..."}

event: step1_completed
data: {
    "deep_analysis_result": {...},
    "output_framework": {...},
    "validation_report": {...}
}
```

### 5.3 SSE 事件类型

| 事件类型 | 说明 | 数据结构 |
|----------|------|----------|
| `step1_dialogue_chunk` | 对话内容（流式） | `{content: string}` |
| `step1_extracting_structure` | 正在提取结构 | `{message: string}` |
| `step1_completed` | 完成 | `{deep_analysis_result, output_framework, validation_report}` |
| `step1_validation_warnings` | 验证警告 | `{warnings: string[]}` |
| `step1_error` | 执行错误 | `{error: string, details: string}` |

---

## 6. 配置参数

### 6.1 环境变量

```bash
# 4-Step Flow 配置
ENABLE_4STEP_FLOW=true              # 启用 4 步骤流程

# Step 1 配置
STEP1_STAGE1_TEMPERATURE=0.3        # Stage 1 温度
STEP1_STAGE1_MAX_TOKENS=3000        # Stage 1 最大 Token
STEP1_STAGE2_TEMPERATURE=0.7        # Stage 2 温度
STEP1_STAGE2_MAX_TOKENS=4000        # Stage 2 最大 Token
```

### 6.2 Prompt 配置文件

位置：`intelligent_project_analyzer/config/prompts/step1_deep_analysis_v3.yaml`

---

## 7. 使用示例

### 7.1 用户输入示例

```
我是一名50岁的室内设计师，计划回四川广元老家建一栋300平米的田园民居。
我希望这个房子既能体现我的专业审美，又能融入当地的建筑文化。
预算大概在80-100万之间。
```

### 7.2 期望输出示例

#### 【您将获得什么】

我们将为您提供一份**田园民居设计参考研究报告**，包含以下内容：

**1. 50岁室内设计师的归乡住宅需求与案例分析**
   - 1.1 设计师自建房的独特需求特征
   - 1.2 国内外设计师自宅案例精选
   - 1.3 职业转型期的空间需求演变

**2. 四川广元地域特色与建筑文化探索**
   - 2.1 广元传统民居建筑特征
   - 2.2 当地气候与建筑适应性
   - 2.3 地域材料与工艺传承

**3. 300平米田园民居的空间布局案例参考**
   - 3.1 功能分区与动线设计
   - 3.2 室内外空间过渡处理
   - 3.3 多代同堂的空间考量

**4. 80-100万预算区间的建造策略研究**
   - 4.1 成本控制与品质平衡案例
   - 4.2 分期建设的可行性分析
   - 4.3 性价比材料与工艺选择

#### 【我们如何理解您的需求】

您不仅仅是在建一栋房子，更是在为人生的下一个阶段创造一个承载梦想的空间...

#### 【接下来的搜索计划】

我们将围绕以上4个板块，进行针对性的信息搜索...

---

## 8. 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.0 | 2026-02-04 | 初始版本，完整定义 Step 1 需求 |

---

## 9. 相关文档

- [4步骤搜索流程概述](./FOUR_STEP_FLOW_OVERVIEW.md)
- [Step 2 搜索任务分解需求文档](./STEP2_SEARCH_DECOMPOSITION_REQUIREMENTS.md)
- [Step 3 智能搜索执行需求文档](./STEP3_INTELLIGENT_SEARCH_REQUIREMENTS.md)
- [Step 4 总结生成需求文档](./STEP4_SUMMARY_GENERATION_REQUIREMENTS.md)

---

## 10. 附录

### 10.1 关键文件路径

| 功能 | 文件路径 |
|------|---------|
| 数据结构定义 | `intelligent_project_analyzer/core/four_step_flow_types.py` |
| Step 1 执行器 | `intelligent_project_analyzer/services/four_step_flow_orchestrator.py` |
| Prompt 配置 | `intelligent_project_analyzer/config/prompts/step1_deep_analysis_v3.yaml` |
| API 路由 | `intelligent_project_analyzer/api/four_step_flow_routes.py` |

### 10.2 术语表

| 术语 | 说明 |
|------|------|
| UCPPT | 用户中心的项目规划工具 (User-Centric Project Planning Tool) |
| JTBD | Jobs To Be Done，待完成的工作 |
| L1-L5 | 五层分析框架 |
| SSE | Server-Sent Events，服务器推送事件 |
