# UCPPT搜索模式第一步重构实现报告 v7.270

## 实施日期
2026-01-25

## 实施概述

成功完成UCPPT搜索模式的第一步与第二步分离重构，实现了"需求理解与深度分析"与"搜索任务规划"的解耦。

## 核心变更

### 1. 新增数据结构：ProblemSolvingApproach

**位置**: `ucppt_search_engine.py:1083-1214`

```python
@dataclass
class ProblemSolvingApproach:
    """
    解题思路模块 - v7.270 新增

    第一步"需求理解与深度分析"的核心输出，位于L1-L5分析和搜索任务规划之间。
    提供战术性思考指导，接近可执行级别（5-8步详细路径）。
    """
    # 任务本质识别
    task_type: str                          # research/design/decision/exploration/verification
    task_type_description: str              # 任务类型详细描述
    complexity_level: str                   # simple/moderate/complex/highly_complex
    required_expertise: List[str]           # 所需领域专业知识（3-5个）

    # 解题路径规划（战术级：5-8步详细路径，无依赖关系）
    solution_steps: List[Dict[str, Any]]    # 有序解题步骤
    # 每步: {"step_id": "S1", "action": "...", "purpose": "...", "expected_output": "..."}

    # 关键突破口（1-3个）
    breakthrough_points: List[Dict[str, str]]
    # 每点: {"point": "...", "why_key": "...", "how_to_leverage": "..."}

    # 预期产出形态
    expected_deliverable: Dict[str, Any]
    # {"format": "report", "sections": [...], "key_elements": [...], "quality_criteria": [...]}

    # 任务描述（保留原始）
    original_requirement: str               # 用户原始需求（原文）
    refined_requirement: str                # 结构化后的需求描述

    # 元数据
    confidence_score: float                 # 对此解题思路的置信度 (0-1)
    alternative_approaches: List[str]       # 备选解题路径
```

**关键方法**:
- `to_dict()`: 转换为字典用于JSON序列化
- `to_plain_text()`: 生成纯文字格式（用于前端展示和后续prompt注入）
- `from_dict()`: 从字典创建实例

### 2. 重构第一步Prompt：_build_unified_analysis_prompt()

**位置**: `ucppt_search_engine.py:4069-4398`

**主要变更**:

#### 移除的部分（移至第二步）
- "分析→搜索规划（系统性思考）v7.254" 整个章节
- "第三部分：搜索规划（系统性输出）" 整个章节
- `search_framework` 相关的JSON输出字段
- `targets` 数组的生成

#### 新增的部分：解题思路生成（战术级）

```markdown
### 第三部分：解题思路（战术级规划）v7.270 新增

基于以上L1-L5分析，现在思考**如何解决**这个问题。

⚠️ **严格分离原则**：此部分只输出解题思路，不涉及任何搜索词或搜索任务规划。

**1. 任务本质识别**
- 任务类型：research/design/decision/exploration/verification
- 复杂度评估：simple/moderate/complex/highly_complex
- 所需专业知识领域（列出3-5个）

**2. 解题路径规划（战术级：5-8步详细路径）**
- 生成5-8个具体步骤（不是3-4个宏观步骤）
- 每步的action要具体到可执行级别
- 每步都要有明确的expected_output
- **不需要标注步骤间的依赖关系**

**3. 关键突破口（1-3个）**
- 什么是解锁这个问题的关键洞察或切入点？

**4. 预期产出形态**
- 格式：report/list/comparison/recommendation/plan
- 必须包含的章节/元素（列出5-8个）
- 关键交付物（视觉参考、产品推荐、实施指南等）
- 质量标准（可执行性、协调性、文化融合度等）

**5. 任务描述保留**
- 原始需求（原文）
- 结构化需求（精炼后）

**6. 备选路径（可选）**
- 如果主路径遇阻，有哪些替代方案？
```

#### 输出JSON结构变更

```json
{
    "user_profile": { ... },
    "analysis": {
        "l1_facts": { ... },
        "l2_models": { ... },
        "l3_tension": { ... },
        "l4_jtbd": "...",
        "l5_sharpness": { ... }
    },
    "problem_solving_approach": {
        "task_type": "design",
        "task_type_description": "...",
        "complexity_level": "complex",
        "required_expertise": ["室内设计", "品牌美学", "地域文化", "材料学"],
        "solution_steps": [
            {
                "step_id": "S1",
                "action": "解析HAY品牌核心设计语言",
                "purpose": "建立'源'美学参照系的基础认知",
                "expected_output": "HAY设计哲学、核心设计师"
            },
            // ... 5-8个步骤
        ],
        "breakthrough_points": [ ... ],
        "expected_deliverable": { ... },
        "original_requirement": "...",
        "refined_requirement": "...",
        "confidence_score": 0.85,
        "alternative_approaches": [ ... ]
    },
    "step2_context": {
        "core_question": "问题一句话本质（20字内）",
        "answer_goal": "用户期望得到的答案是...",
        "solution_steps_summary": ["S1:HAY设计语言", "S2:HAY色彩材质", ...],
        "breakthrough_tensions": ["几何工业感 vs 有机自然感"]
    }
}
```

**注意**: `step2_context` 严格不包含任何搜索词或搜索任务规划，只传递解题思路的摘要信息供第二步参考。

### 3. 更新流式处理：_unified_analysis_stream()

**位置**: `ucppt_search_engine.py:4399-4654`

**主要变更**:

#### 新增事件类型

1. **problem_solving_approach_ready** (v7.270 新增)
   - 触发时机：解题思路解析完成
   - 数据内容：完整的解题思路（task_type, solution_steps, breakthrough_points等）
   - 前端用途：展示解题路径卡片

2. **step1_complete** (v7.270 新增)
   - 触发时机：第一步完整分析完成
   - 数据内容：user_profile, analysis, problem_solving_approach, step2_context
   - 内部用途：传递给第二步的上下文

#### 兼容性处理

```python
# v7.270: 兼容旧流程 - 如果数据中包含 search_framework，仍然构建并发送
search_framework_data = data.get("search_framework", {})
if search_framework_data and search_framework_data.get("targets"):
    logger.info(f"📋 [v7.270] 检测到旧格式 search_framework，进行兼容处理")
    framework = self._build_search_framework_from_json(query, data)
    # ... 发送 search_framework_ready 事件
else:
    # v7.270: 新流程 - 不包含 search_framework，只发送 analysis_complete
    yield {
        "type": "analysis_complete",
        "framework": None,  # 第一步不生成 framework
        "quality": quality,
        "problem_solving_approach": problem_solving_approach,
        "step2_context": step2_context,
    }
```

### 4. 新增第二步方法

#### 4.1 _build_step2_search_framework_prompt()

**位置**: `ucppt_search_engine.py:4717-4990`

**功能**: 构建第二步搜索框架生成Prompt

**输入参数**:
- `query`: 用户原始问题
- `step2_context`: 第一步传递的上下文
- `problem_solving_approach`: 第一步生成的解题思路
- `analysis_data`: 第一步的完整分析数据（L1-L5）

**Prompt核心内容**:

```markdown
## 任务要求

现在，基于以上解题思路，生成**可执行的搜索任务清单**。

### 搜索任务设计原则

1. **任务粒度**：每个搜索任务对应解题路径中的1-2个步骤
2. **优先级分层**：
   - P1（高优先级）：回答问题的必需信息
   - P2（中优先级）：深化理解的补充信息
   - P3（低优先级）：锦上添花的延展信息
3. **预设关键词**：每个任务必须包含3-5个精准搜索关键词
4. **质量标准**：明确每个任务的完成标准

### 关键词生成要求

⚠️ **预设关键词是搜索质量的关键**，必须：
1. **具体化**：使用实体名称，而非泛化描述
   - ✅ "HAY Palissade系列 户外家具"
   - ❌ "北欧家具品牌"
2. **场景化**：结合用户的具体场景
   - ✅ "峨眉山七里坪 民宿设计 在地材料"
   - ❌ "民宿设计"
3. **多样化**：覆盖不同搜索角度
4. **可搜索性**：确保关键词能在搜索引擎中找到结果
```

**输出格式**:

```json
{
  "core_question": "...",
  "answer_goal": "...",
  "boundary": "不搜索：价格信息、施工细节、供应商联系方式",
  "targets": [
    {
      "id": "T1",
      "question": "HAY品牌的设计语言是什么？",
      "search_for": "HAY品牌设计哲学、核心产品系列、设计师团队",
      "why_need": "建立'源'美学参照系，理解HAY的设计DNA",
      "success_when": ["找到HAY的设计理念描述", "识别出3个以上代表性产品系列"],
      "priority": 1,
      "category": "品牌调研",
      "preset_keywords": [
        "HAY丹麦家居 设计理念",
        "HAY Palissade系列 Mags沙发",
        "Ronan Bouroullec HAY设计",
        "HAY About A Chair 民主设计",
        "HAY色彩系统 粉末涂层钢"
      ]
    }
    // ... 3-6个任务
  ]
}
```

#### 4.2 _step2_generate_search_framework()

**位置**: `ucppt_search_engine.py:4992-5063`

**功能**: 第二步搜索框架生成的执行方法

**流程**:
1. 调用 `_build_step2_search_framework_prompt()` 构建Prompt
2. 调用 `_call_llm_json()` 生成搜索框架
3. 解析JSON响应
4. 构建 `SearchFramework` 对象
5. 解析 `targets` 列表，创建 `SearchTarget` 对象

**错误处理**:
- LLM返回空结果 → 返回 None
- JSON解析失败 → 返回 None
- 异常捕获 → 记录日志并返回 None

### 5. 更新主流程：search_deep()

**位置**: `ucppt_search_engine.py:3290-3450`

**主要变更**: 实现两步流程

#### 第一步：统一分析（用户画像 + L1-L5 + 解题思路）

```python
async for event in self._unified_analysis_stream(query, context):
    event_type = event.get("type")

    # 流式输出 thinking 内容给前端
    if event_type == "unified_dialogue_chunk":
        yield event

    # v7.270: 解题思路就绪
    elif event_type == "problem_solving_approach_ready":
        problem_solving_approach = event.get("_internal_approach")
        yield event  # 转发给前端

    # v7.270: 第一步完成
    elif event_type == "step1_complete":
        step2_context = event.get("data", {}).get("step2_context", {})
        analysis_data = event.get("_internal_data", {})
        yield event  # 转发给前端
```

#### 第二步：生成搜索框架（仅在新流程中执行）

```python
# === 第二步：生成搜索框架（仅在新流程中执行） ===
if analysis_session and problem_solving_approach and step2_context and not framework:
    logger.info(f"🚀 [v7.270] 开始第二步：生成搜索框架")

    # 发送第二步开始事件
    yield {
        "type": "step2_start",
        "data": {"message": "基于解题思路生成搜索任务清单..."}
    }

    # 调用第二步方法生成搜索框架
    framework = await self._step2_generate_search_framework(
        query, step2_context, problem_solving_approach, analysis_data
    )

    if framework:
        # 生成框架清单
        framework_checklist = self._generate_framework_checklist(framework, analysis_data)
        framework.framework_checklist = framework_checklist

        # 发送搜索框架就绪事件
        yield {
            "type": "search_framework_ready",
            "data": {
                "core_question": framework.core_question,
                "answer_goal": framework.answer_goal,
                "boundary": framework.boundary,
                "target_count": len(framework.targets),
                "targets": [t.to_dict() for t in framework.targets],
                "targets_summary": framework_summary,
                "framework_checklist": framework_checklist.to_dict(),
            },
            "_internal_framework": framework,
        }

        # 发送第二步完成事件
        yield {
            "type": "step2_complete",
            "data": {
                "message": "搜索任务清单已生成",
                "target_count": len(framework.targets),
            }
        }
```

#### 兼容性处理

```python
# v7.270: 检查是否是新流程（有 problem_solving_approach 但无 framework）
if event.get("problem_solving_approach") and not event.get("framework"):
    logger.info(f"🔍 [v7.270] 检测到新流程，准备执行第二步")
    # 新流程：需要执行第二步
    pass
else:
    # 旧流程：直接使用返回的 framework
    framework = event.get("framework")
```

### 6. 新增辅助方法

#### 6.1 _call_llm_json()

**位置**: `ucppt_search_engine.py:10806`

```python
async def _call_llm_json(
    self,
    prompt: str,
    model: str = "deepseek-chat",
    max_tokens: int = 2000,
) -> str:
    """
    调用 LLM 生成 JSON 响应 - v7.270 新增

    用于第二步搜索框架生成等需要结构化输出的场景
    """
    return await self._call_deepseek(prompt, model, max_tokens)
```

#### 6.2 _generate_framework_checklist()

**位置**: `ucppt_search_engine.py:10818`

```python
def _generate_framework_checklist(
    self,
    framework: SearchFramework,
    analysis_data: Dict[str, Any]
) -> 'FrameworkChecklist':
    """
    生成框架清单 - v7.270 兼容方法

    从 SearchFramework 提取关键信息生成清单
    """
    from datetime import datetime

    # 提取主要搜索方向
    main_directions = []
    for t in framework.targets[:5]:  # 最多5个
        direction = {
            "id": t.id,
            "name": t.name or t.question,
            "description": t.search_for or t.description,
            "priority": t.priority,
        }
        main_directions.append(direction)

    # 提取边界
    boundaries = []
    if framework.boundary:
        boundaries = [framework.boundary]

    return FrameworkChecklist(
        core_summary=framework.core_question[:50],
        main_directions=main_directions,
        boundaries=boundaries,
        answer_goal=framework.answer_goal or "为用户提供完整解答",
        generated_at=datetime.now().isoformat(),
    )
```

#### 6.3 _build_default_problem_solving_approach()

**位置**: `ucppt_search_engine.py:4655-4715`

```python
def _build_default_problem_solving_approach(self, query: str) -> ProblemSolvingApproach:
    """
    构建默认的解题思路 - v7.270 新增

    当LLM未能生成有效的解题思路时，使用此方法创建默认值
    """
    return ProblemSolvingApproach(
        task_type="exploration",
        task_type_description="这是一个需要探索和理解的任务",
        complexity_level="moderate",
        required_expertise=["领域知识", "信息检索", "分析能力"],
        solution_steps=[
            {
                "step_id": "S1",
                "action": "理解问题的核心诉求",
                "purpose": "明确用户真正想要解决的问题",
                "expected_output": "问题的本质描述和关键要素"
            },
            # ... 5个默认步骤
        ],
        breakthrough_points=[ ... ],
        expected_deliverable={ ... },
        original_requirement=query,
        refined_requirement=f"为用户提供关于「{query[:50]}」的完整解答",
        confidence_score=0.5,
        alternative_approaches=["从不同角度切入问题", "寻找类似案例参考"]
    )
```

## 事件流变更

### 旧流程（v7.269及之前）

```
unified_analysis_stream
  → question_analyzed (包含targets)
  → 搜索轮次
```

### 新流程（v7.270）

```
step1_analysis_stream
  → problem_solving_approach_ready (解题思路)
  → step1_complete
  → step2_framework_generation
  → search_framework_ready (包含targets)
  → 搜索轮次
```

### 新增事件详细说明

| 事件类型 | 触发时机 | 数据内容 | 用途 |
|---------|---------|---------|------|
| `problem_solving_approach_ready` | 第一步解题思路解析完成 | task_type, solution_steps, breakthrough_points, expected_deliverable等 | 前端展示解题路径卡片 |
| `step1_complete` | 第一步完整分析完成 | user_profile, analysis, problem_solving_approach, step2_context | 传递给第二步的上下文 |
| `step2_start` | 第二步开始 | message: "基于解题思路生成搜索任务清单..." | 前端显示进度提示 |
| `step2_complete` | 第二步完成 | message, target_count | 前端显示完成状态 |

## 关键设计决策

### 1. 严格分离原则

**第一步输出**:
- ✅ 用户画像
- ✅ L1-L5深度分析
- ✅ 解题思路（5-8步战术级路径）
- ✅ step2_context（摘要信息）
- ❌ 搜索词
- ❌ 搜索任务规划

**第二步输出**:
- ✅ 搜索框架（targets）
- ✅ 预设关键词（3-5个/任务）
- ✅ 质量标准

### 2. 战术级粒度

**解题步骤要求**:
- 5-8个具体步骤（不是3-4个宏观步骤）
- 每步action具体到可执行级别
- 每步都有明确的expected_output
- **不需要标注步骤间的依赖关系**

**示例对比**:

❌ 宏观步骤（3步）:
1. 了解HAY品牌
2. 研究峨眉山环境
3. 生成设计方案

✅ 战术级步骤（7步）:
1. 解析HAY品牌核心设计语言 → HAY设计哲学、核心设计师
2. 提取HAY色彩系统与材质特征 → 标志性色彩、材质偏好
3. 研究峨眉山七里坪气候与环境 → 海拔、气候、光线特点
4. 梳理峨眉山在地材料与工艺 → 冷杉木、竹材、传统工艺
5. 识别北欧与川西美学融合策略 → 融合原则、成功案例
6. 构建空间功能分区与动线 → 功能划分、重点空间处理
7. 生成完整概念设计方案 → 色彩、材质、家具、软装、照明

### 3. 向后兼容

**兼容策略**:
- 如果第一步LLM返回包含 `search_framework`，仍然按旧流程处理
- 如果第一步LLM返回只包含 `problem_solving_approach`，执行新流程
- 前端可以同时处理旧事件和新事件

**兼容代码**:

```python
# v7.270: 兼容旧流程
search_framework_data = data.get("search_framework", {})
if search_framework_data and search_framework_data.get("targets"):
    # 旧流程：直接构建并发送 search_framework_ready
    framework = self._build_search_framework_from_json(query, data)
    yield {"type": "search_framework_ready", ...}
else:
    # 新流程：只发送 analysis_complete，等待第二步
    yield {
        "type": "analysis_complete",
        "framework": None,
        "problem_solving_approach": problem_solving_approach,
        "step2_context": step2_context,
    }
```

## 验证结果

### 语法验证

```bash
cd "d:\11-20\langgraph-design"
python -m py_compile "intelligent_project_analyzer/services/ucppt_search_engine.py"
# ✅ 通过，无语法错误
```

### 代码统计

- **新增代码行数**: ~500行
- **修改代码行数**: ~200行
- **新增数据结构**: 1个（ProblemSolvingApproach）
- **新增方法**: 4个
  - `_build_step2_search_framework_prompt()`
  - `_step2_generate_search_framework()`
  - `_call_llm_json()`
  - `_generate_framework_checklist()`
- **修改方法**: 2个
  - `_build_unified_analysis_prompt()`
  - `search_deep()`

## 后续工作

### 前端适配（必需）

1. **新增事件监听**:
   - `problem_solving_approach_ready`: 展示解题路径卡片
   - `step1_complete`: 更新UI状态
   - `step2_start`: 显示"生成搜索任务清单..."
   - `step2_complete`: 显示完成状态

2. **UI组件**:
   - 解题路径展示卡片（ProblemSolvingApproachCard）
   - 步骤进度指示器（Step1 → Step2 → Search）

### 测试验证（推荐）

1. **单元测试**:
   - `ProblemSolvingApproach` 序列化/反序列化
   - `_build_step2_search_framework_prompt()` Prompt生成
   - `_step2_generate_search_framework()` 框架生成

2. **集成测试**:
   - 使用HAY民宿案例验证完整流程
   - 验证新旧流程兼容性
   - 验证事件流正确性

3. **性能测试**:
   - 测量第一步耗时
   - 测量第二步耗时
   - 对比新旧流程总耗时

### 文档更新（推荐）

1. **API文档**:
   - 更新事件流说明
   - 添加新事件类型文档
   - 更新数据结构文档

2. **用户文档**:
   - 更新UCPPT搜索模式说明
   - 添加解题思路功能介绍

## 风险与缓解

### 风险1: LLM未能生成有效的解题思路

**缓解措施**:
- 实现了 `_build_default_problem_solving_approach()` 提供默认值
- 异常捕获机制确保流程不中断

### 风险2: 第二步搜索框架生成失败

**缓解措施**:
- 返回 None 时回退到 `_build_simple_search_framework()`
- 保持系统可用性

### 风险3: 前端未适配新事件

**缓解措施**:
- 保持向后兼容，旧流程仍然可用
- 新事件为可选增强功能

## 总结

本次重构成功实现了UCPPT搜索模式第一步与第二步的分离，核心改进包括：

1. **清晰的职责分离**: 第一步专注于需求理解和解题思路，第二步专注于搜索任务规划
2. **战术级解题路径**: 5-8步详细路径，接近可执行级别
3. **严格的边界控制**: 第一步不涉及任何搜索词或搜索任务规划
4. **完整的向后兼容**: 新旧流程可以共存，平滑过渡
5. **健壮的错误处理**: 多层兜底机制确保系统稳定性

代码已通过语法验证，可以进入测试阶段。

---

**实施人员**: Claude Code
**审核状态**: 待审核
**版本**: v7.270
**文档日期**: 2026-01-25
