# 问卷第一步任务梳理优化方案

**创建日期**: 2026-01-02
**问题发现者**: 用户反馈
**影响范围**: 问卷Step 1、Step 3、任务分配、专家协作

---

## 📋 问题描述

用户在问卷第一步"任务梳理"环节发现了两个关键问题：

### 问题1: 任务精准度不足

**用户输入**：
```
上海老弄堂120平米老房翻新，业主想要"杂志级"的重生效果，
但全包预算（含软硬装）被严格限制在50万人民币。
请给出资金分配策略，明确指出哪三个关键节点必须投入重金，
哪三个环节可以极致压缩成本，并说明理...
```

**当前生成的任务**：
```json
{
  "id": "task_1",
  "title": "杂志级室内设计风格与材料预算研究",
  "description": "研究杂志级室内设计的关键风格元素，评估预算范围内的主材选择与效果最大化策略",
  "motivation": "任务聚焦杂志级视觉风格与预算内效果最大化，主要为审美动机，次要体现功能性和商业价值考虑"
}
```

**问题**：
- ❌ 任务描述**过于泛泛**，没有限定在"上海老弄堂120平米老房翻新"这个具体场景
- ❌ 如果不限定场景，后续专家执行时会"离用户问题十万八千里"
- ❌ 缺乏对用户核心需求的精准定位（资金分配策略、重金节点、成本压缩）

**根本原因**：
`CoreTaskDecomposer` 的 prompt 中虽然强调"深度利用结构化数据"，但在**任务标题和描述生成**环节，LLM倾向于抽象化、通用化，**丢失了用户输入中的关键约束条件**（地点、规模、预算、特殊需求）。

---

### 问题2: 数据传递闭环缺失

**当前生成的任务**：
```json
{
  "id": "task_2",
  "title": "上海老弄堂老房结构与改造可能性研究",
  "description": "调研120平米老式改造中的潜在结构问题，评估改造可行性与关键限制条件",
  "motivation": "任务聚焦老房结构问题与改造限制，主要涉及技术分析与工程可行性评估"
}
```

**问题**：
- ❌ 用户在输入时**没有提供完整的老房结构信息**（建造年代、结构类型、承重墙、管线情况等）
- ❌ 但任务梳理时就生成了需要这些信息的任务
- ❌ **Step 3 信息补全**应该识别出这些缺失信息并询问用户
- ❌ 但当前 Step 3 只检查 6 大维度（预算、时间、交付等），**不会针对具体任务的执行需求生成补充问题**

**根本原因**：
1. **Step 1 任务梳理**生成任务时，没有标记"该任务需要哪些必需信息"
2. **Step 3 信息补全**只检查通用维度，不分析具体任务的信息依赖
3. **任务分配给专家**时，专家可能因信息不足无法执行或执行结果偏离

---

## 🔍 当前数据流分析

### 完整数据流路径

```
用户输入
  ↓
【需求分析师】生成 structured_requirements
  ↓
【Step 1: 任务梳理】CoreTaskDecomposer 生成 confirmed_core_tasks
  ↓
【Step 2: 雷达图】生成 dimension_priorities
  ↓
【Step 3: 信息补全】TaskCompletenessAnalyzer 分析 6 大维度 → gap_filling_answers
  ↓
【需求确认】用户确认 structured_requirements + gap_filling_answers
  ↓
【项目总监】基于 structured_requirements 分配任务给专家
  ↓
【专家协作】基于 task_instruction 执行分析
```

### 问题点定位

#### 问题点 A: Step 1 → Step 3 数据传递断层

**当前情况**：
- `CoreTaskDecomposer` 生成的任务存储在 `state["confirmed_core_tasks"]`
- `TaskCompletenessAnalyzer` 虽然接收 `confirmed_tasks` 参数，但**只用于统计任务密度**
- **不分析具体任务的信息依赖**

**代码证据**：
```python
# intelligent_project_analyzer/services/task_completeness_analyzer.py:39
def analyze(
    self,
    confirmed_tasks: List[Dict[str, Any]],  # ✅ 接收了任务
    user_input: str,
    structured_data: Dict[str, Any]
) -> Dict[str, Any]:
    # 1. 合并所有文本信息
    all_text = self._merge_text(confirmed_tasks, user_input, structured_data)

    # 2. 评估每个维度的覆盖度（只检查 6 大维度）
    dimension_scores = {}
    for dim, keywords in self.DIMENSIONS.items():  # ❌ 固定的 6 大维度
        score = self._calculate_dimension_score(all_text, keywords)
        dimension_scores[dim] = score
```

**缺失的逻辑**：
```python
# ❌ 应该有但没有的逻辑
def _analyze_task_specific_requirements(self, confirmed_tasks):
    """分析每个任务的特定信息需求"""
    task_requirements = []
    for task in confirmed_tasks:
        if "老房结构" in task["title"]:
            task_requirements.append({
                "task_id": task["id"],
                "missing_info": ["建造年代", "结构类型", "承重墙位置", "管线情况"],
                "question": "请提供老房的基本结构信息"
            })
    return task_requirements
```

#### 问题点 B: Step 1 → 项目总监 数据传递不完整

**当前情况**：
- `confirmed_core_tasks` 生成后存储在 `state`
- 但**项目总监分配任务时，不直接使用 `confirmed_core_tasks`**
- 而是基于 `structured_requirements` 和角色配置独立生成任务

**代码证据**：
```python
# intelligent_project_analyzer/agents/dynamic_project_director.py:966
def _build_user_prompt(self, requirements: str, roles_info: str) -> str:
    """构建用户提示词"""
    return f"""# 项目需求

{requirements}  # ❌ 只用了 structured_requirements，没有用 confirmed_core_tasks

# 可用角色

{roles_info}

# 任务

请根据上述项目需求,从可用角色中选择3-8个最合适的角色来完成这个项目。
```

**结果**：
- Step 1 用户确认的核心任务 → **没有传递给项目总监**
- 项目总监独立生成新的任务分配 → **可能与用户确认的核心任务不一致**
- 最终专家执行的任务 → **可能偏离用户最初确认的方向**

---

## ✅ 优化方案

### 方案1: 增强任务精准度（解决问题1）

#### 1.1 优化 CoreTaskDecomposer 的 Prompt

**文件**: `intelligent_project_analyzer/config/prompts/core_task_decomposer.yaml`

**当前问题**：
- Prompt 中强调"深度利用结构化数据"，但**没有强制要求任务描述中包含用户场景的关键约束**

**优化建议**：
```yaml
system_prompt: |
  你是一个项目任务拆解专家。你的任务是深度挖掘用户需求，从多层结构化数据中提取洞察，生成精准的、可执行的任务列表。

  # ⚠️ 核心原则：任务必须精准定位到用户场景

  ## 任务标题与描述要求（新增）

  1. **场景锚定**：任务标题和描述中必须包含用户场景的核心约束条件：
     - 地点/区域（如"上海老弄堂"）
     - 规模/面积（如"120平米"）
     - 项目类型（如"老房翻新"）
     - 预算范围（如"50万全包"）
     - 特殊需求（如"杂志级效果"）

  2. **避免泛泛而谈**：
     - ❌ 错误："杂志级室内设计风格与材料预算研究"
     - ✅ 正确："上海老弄堂120平米老房翻新的杂志级效果实现策略（50万预算约束下的资金分配方案）"

  3. **任务描述必须具体化**：
     - 明确指出该任务要解决用户提出的哪个具体问题
     - 包含用户场景的约束条件
     - 指明预期的可交付成果

  ## 示例对比（新增）

  ### 错误示例（过于抽象）
  ```json
  {
    "title": "杂志级室内设计风格研究",
    "description": "研究杂志级室内设计的关键风格元素"
  }
  ```

  ### 正确示例（精准定位）
  ```json
  {
    "title": "上海老弄堂120平米老房翻新的杂志级效果实现策略",
    "description": "在50万预算约束下，研究如何通过资金分配实现杂志级视觉效果：明确三个必须重金投入的关键节点（如主材选择、工艺品质、软装搭配），以及三个可极致压缩成本的环节（如辅材、基础硬装、隐蔽工程），输出具体的资金分配比例建议"
  }
  ```

  # 数据源（按重要性排序）

  你将收到以下两类数据，请**务必全面利用**：

  ### 1. 用户原始输入（最高优先级！）
  - 用户的初步描述，包含项目的**具体场景约束**和**核心问题**
  - ⚠️ 任务标题和描述中必须提取并保留这些关键信息

  ### 2. 结构化需求数据（核心！必须深度利用）
  ...
```

#### 1.2 增强 LLM 输出验证

**文件**: `intelligent_project_analyzer/services/core_task_decomposer.py`

**新增逻辑**：
```python
def _validate_task_specificity(
    self,
    tasks: List[Dict[str, Any]],
    user_input: str,
    structured_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    验证任务的精准度，确保任务描述包含用户场景的关键约束

    Args:
        tasks: LLM 生成的任务列表
        user_input: 用户原始输入
        structured_data: 结构化需求数据

    Returns:
        验证并优化后的任务列表
    """
    # 提取用户场景的关键约束
    key_constraints = self._extract_key_constraints(user_input, structured_data)
    # 示例：["上海老弄堂", "120平米", "老房翻新", "50万预算", "杂志级效果"]

    validated_tasks = []
    for task in tasks:
        title = task.get("title", "")
        description = task.get("description", "")

        # 检查任务描述中是否包含至少 2 个关键约束
        matched_constraints = [c for c in key_constraints if c in title or c in description]

        if len(matched_constraints) < 2:
            # 任务过于抽象，需要补充场景信息
            logger.warning(f"⚠️ 任务过于抽象: {title}，尝试增强精准度")

            # 自动补充场景信息到任务描述
            enhanced_description = self._enhance_task_description(
                task, key_constraints, structured_data
            )
            task["description"] = enhanced_description
            task["specificity_enhanced"] = True

        validated_tasks.append(task)

    return validated_tasks

def _extract_key_constraints(
    self,
    user_input: str,
    structured_data: Dict[str, Any]
) -> List[str]:
    """提取用户场景的关键约束条件"""
    constraints = []

    # 从用户输入中提取
    # 地点/区域
    location_patterns = [r'([北上广深]\w+[区县市])', r'(\w+老弄堂)', r'(\w+小区)']
    for pattern in location_patterns:
        match = re.search(pattern, user_input)
        if match:
            constraints.append(match.group(1))

    # 规模/面积
    area_match = re.search(r'(\d+平[米方])', user_input)
    if area_match:
        constraints.append(area_match.group(1))

    # 预算
    budget_match = re.search(r'(\d+万|预算\w+)', user_input)
    if budget_match:
        constraints.append(budget_match.group(1))

    # 特殊需求关键词
    special_keywords = ['杂志级', '极简', '奢华', '工业风', '现代', '新中式']
    for keyword in special_keywords:
        if keyword in user_input:
            constraints.append(keyword)

    # 从 structured_data 中提取
    physical_context = structured_data.get("physical_context", "")
    if physical_context:
        # 提取地点、规模等信息
        ...

    return constraints
```

---

### 方案2: 建立任务信息依赖检查（解决问题2）

#### 2.1 在任务生成时标记信息依赖

**文件**: `intelligent_project_analyzer/services/core_task_decomposer.py`

**新增字段**：
```python
def decompose_tasks(
    self,
    user_input: str,
    structured_data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    拆解核心任务（增强版）

    Returns:
        任务列表，每个任务包含：
        - id: 任务ID
        - title: 任务标题
        - description: 任务描述
        - type: 任务类型
        - motivation: 动机标签
        - execution_order: 执行顺序
        - dependencies: 依赖的其他任务
        - required_info: 🆕 执行该任务所需的必要信息（新增）
        - info_status: 🆕 信息完整性状态（新增）
    """
    ...

    # LLM 生成任务后，增加信息依赖分析
    tasks = self._parse_llm_output(llm_response)
    tasks = self._analyze_task_info_requirements(tasks, user_input, structured_data)

    return tasks

def _analyze_task_info_requirements(
    self,
    tasks: List[Dict[str, Any]],
    user_input: str,
    structured_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    分析每个任务的信息依赖

    为每个任务标记：
    1. required_info: 执行该任务需要哪些信息
    2. info_status: 这些信息是否已经提供
    """
    # 已有信息集合
    available_info = self._extract_available_info(user_input, structured_data)

    for task in tasks:
        # 根据任务标题和描述推断需要的信息
        required_info = self._infer_required_info(task)

        # 检查信息完整性
        missing_info = [info for info in required_info if info not in available_info]

        task["required_info"] = required_info
        task["missing_info"] = missing_info
        task["info_status"] = "complete" if not missing_info else "incomplete"

    return tasks

def _infer_required_info(self, task: Dict[str, Any]) -> List[str]:
    """根据任务内容推断需要的信息"""
    title = task.get("title", "")
    description = task.get("description", "")
    text = f"{title} {description}"

    required_info = []

    # 规则匹配（可扩展为 LLM 推理）
    info_patterns = {
        "老房结构信息": [r'老房.*结构', r'改造.*可行性', r'承重墙', r'管线'],
        "预算详细分配": [r'预算.*分配', r'资金.*策略', r'成本.*控制'],
        "交付时间节点": [r'时间.*节点', r'工期.*安排', r'交付.*计划'],
        "业主生活习惯": [r'生活.*习惯', r'使用.*场景', r'日常.*动线'],
        "风格偏好细节": [r'风格.*偏好', r'设计.*倾向', r'美学.*要求'],
    }

    for info_type, patterns in info_patterns.items():
        if any(re.search(p, text, re.IGNORECASE) for p in patterns):
            required_info.append(info_type)

    return required_info
```

#### 2.2 在 Step 3 中检查任务信息依赖

**文件**: `intelligent_project_analyzer/services/task_completeness_analyzer.py`

**增强逻辑**：
```python
class TaskCompletenessAnalyzer:
    """任务完整性分析器（增强版）"""

    def analyze(
        self,
        confirmed_tasks: List[Dict[str, Any]],
        user_input: str,
        structured_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分析任务信息完整性（增强版）

        新增功能：
        1. 检查通用 6 大维度（原有功能）
        2. 🆕 检查每个任务的特定信息依赖（新增功能）
        """
        # 原有逻辑：检查通用维度
        all_text = self._merge_text(confirmed_tasks, user_input, structured_data)
        dimension_scores = ...
        covered_dimensions = ...
        missing_dimensions = ...
        critical_gaps = self._identify_critical_gaps(missing_dimensions, all_text)

        # 🆕 新增逻辑：检查任务特定信息依赖
        task_specific_gaps = self._check_task_specific_requirements(confirmed_tasks)

        # 合并通用缺失和任务特定缺失
        all_critical_gaps = critical_gaps + task_specific_gaps

        return {
            "completeness_score": completeness_score,
            "covered_dimensions": covered_dimensions,
            "missing_dimensions": missing_dimensions,
            "critical_gaps": all_critical_gaps,  # 包含通用+任务特定
            "task_specific_gaps": task_specific_gaps,  # 🆕 单独返回任务特定缺失
            "dimension_scores": dimension_scores
        }

    def _check_task_specific_requirements(
        self,
        confirmed_tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        检查每个任务的特定信息依赖

        Returns:
            任务特定缺失点列表，格式：
            [
                {
                    "dimension": "任务T1所需信息",
                    "task_id": "task_1",
                    "task_title": "上海老弄堂老房结构研究",
                    "missing_info": ["建造年代", "结构类型"],
                    "reason": "任务「上海老弄堂老房结构研究」需要老房的建造年代、结构类型等基础信息"
                }
            ]
        """
        task_gaps = []

        for task in confirmed_tasks:
            missing_info = task.get("missing_info", [])
            if missing_info:
                task_gaps.append({
                    "dimension": f"任务 {task.get('id')} 所需信息",
                    "task_id": task.get("id"),
                    "task_title": task.get("title"),
                    "missing_info": missing_info,
                    "reason": f"任务「{task.get('title')}」需要以下信息: {', '.join(missing_info)}"
                })

        return task_gaps

    def generate_gap_questions(
        self,
        missing_dimensions: List[str],
        critical_gaps: List[Dict[str, str]],  # 现在包含任务特定缺失
        confirmed_tasks: List[Dict[str, Any]],
        existing_info_summary: str = "",
        target_count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        生成针对性补充问题（增强版）

        新增功能：
        - 为任务特定的信息缺失生成定制化问题
        """
        questions = []

        # 1. 为通用维度生成问题（原有逻辑）
        for dimension in missing_dimensions:
            question = self._generate_question_for_dimension(dimension, is_required=True)
            if question:
                questions.append(question)

        # 2. 🆕 为任务特定信息缺失生成问题（新增逻辑）
        for gap in critical_gaps:
            if "task_id" in gap:  # 这是任务特定缺失
                task_question = self._generate_task_specific_question(gap)
                if task_question:
                    questions.append(task_question)

        # 3. 按优先级排序和限制数量
        questions.sort(key=lambda q: q.get("priority", 999))
        return questions[:target_count]

    def _generate_task_specific_question(
        self,
        gap: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        为任务特定的信息缺失生成问题

        Args:
            gap: 任务缺失信息，包含 task_id, task_title, missing_info

        Returns:
            问题字典
        """
        task_title = gap.get("task_title", "")
        missing_info = gap.get("missing_info", [])

        # 根据缺失信息类型生成问题
        if "老房结构信息" in missing_info:
            return {
                "id": f"task_{gap['task_id']}_structure",
                "question": f"为了完成「{task_title}」任务，请提供老房的基本结构信息：",
                "type": "multiple_choice",
                "options": [
                    "砖混结构",
                    "框架结构",
                    "木结构",
                    "砖木结构",
                    "不清楚"
                ],
                "sub_questions": [
                    {"field": "build_year", "question": "建造年代大约是？", "type": "open_ended"},
                    {"field": "load_wall", "question": "是否知道承重墙位置？", "type": "single_choice", "options": ["清楚", "不清楚"]},
                    {"field": "pipeline", "question": "管线情况", "type": "open_ended"}
                ],
                "priority": 1,  # 高优先级
                "weight": 10,
                "related_task": gap["task_id"],
                "note": f"此信息用于「{task_title}」任务的执行"
            }

        # 其他信息类型...

        return None
```

---

### 方案3: 打通任务数据到专家协作（解决数据传递断层）

#### 3.1 项目总监融合 Step 1 确认的核心任务

**文件**: `intelligent_project_analyzer/agents/dynamic_project_director.py`

**修改 `_build_user_prompt` 方法**：
```python
def _build_user_prompt(
    self,
    requirements: str,
    roles_info: str,
    confirmed_tasks: Optional[List[Dict[str, Any]]] = None  # 🆕 新增参数
) -> str:
    """
    构建用户提示词（增强版）

    Args:
        requirements: 用户需求（结构化数据）
        roles_info: 角色信息
        confirmed_tasks: 🆕 Step 1 用户确认的核心任务列表
    """
    prompt = f"""# 项目需求

{requirements}
"""

    # 🆕 新增：如果有用户确认的核心任务，作为任务分配的指导
    if confirmed_tasks:
        prompt += f"""

# 用户确认的核心任务（优先级最高！）

用户在问卷环节已经确认了以下核心任务，你在分配专家任务时**必须围绕这些核心任务展开**：

"""
        for i, task in enumerate(confirmed_tasks, 1):
            prompt += f"""
**核心任务 {i}: {task.get('title')}**
- 描述: {task.get('description')}
- 类型: {task.get('type')}
- 动机: {task.get('motivation', '')}
"""
            # 如果任务有信息依赖，也要告知项目总监
            if task.get("missing_info"):
                prompt += f"- ⚠️ 信息缺失: {', '.join(task['missing_info'])} (用户已在问卷中补充)\n"

        prompt += """
⚠️ **重要**：你分配给专家的任务必须与上述核心任务对齐，确保最终输出能回答用户确认的核心问题。
"""

    prompt += f"""

# 可用角色

{roles_info}

# 任务

请根据上述项目需求和用户确认的核心任务，从可用角色中选择3-8个最合适的角色来完成这个项目。

要求:
1. **任务对齐**：分配的任务必须与用户确认的核心任务对齐
2. 选择的角色必须能够覆盖所有核心任务
3. 为每个角色的task_instruction.deliverables分配具体交付物
4. 任务描述要明确说明该角色需要完成什么、如何完成、达到什么目标
...
"""

    return prompt
```

**修改 `execute` 方法**：
```python
def execute(self, state: ProjectAnalysisState) -> Dict[str, Any]:
    """执行项目总监分析（增强版）"""
    # 获取用户确认的核心任务
    confirmed_tasks = state.get("confirmed_core_tasks", [])  # 🆕 从 state 中提取

    # 构建 prompt（传入核心任务）
    user_prompt = self._build_user_prompt(
        requirements=formatted_requirements,
        roles_info=roles_info,
        confirmed_tasks=confirmed_tasks  # 🆕 传入核心任务
    )

    ...
```

#### 3.2 专家执行时能看到核心任务上下文

**文件**: `intelligent_project_analyzer/workflow/main_workflow.py`

**修改 `_build_context_for_expert` 方法**：
```python
def _build_context_for_expert(self, state: ProjectAnalysisState) -> str:
    """
    为任务导向专家构建上下文信息（增强版）
    """
    context_parts = []

    # 添加用户需求
    task_description = state.get("task_description", "")
    if task_description:
        context_parts.append(f"## 用户需求\n{task_description}")

    # 添加结构化需求
    structured_requirements = state.get("structured_requirements", {})
    if structured_requirements:
        context_parts.append("## 结构化需求")
        for key, value in structured_requirements.items():
            if value:
                context_parts.append(f"**{key}**: {value}")

    # 🆕 新增：添加用户确认的核心任务
    confirmed_tasks = state.get("confirmed_core_tasks", [])
    if confirmed_tasks:
        context_parts.append("\n## 用户确认的核心任务\n")
        context_parts.append("以下是用户在问卷环节确认的核心任务，你的分析应该围绕这些任务展开：\n")
        for i, task in enumerate(confirmed_tasks, 1):
            context_parts.append(f"""
**核心任务 {i}: {task.get('title')}**
- 描述: {task.get('description')}
- 类型: {task.get('type')}
""")

    # 🆕 新增：添加用户补充的信息（Step 3 问卷答案）
    gap_filling_answers = state.get("gap_filling_answers", {})
    if gap_filling_answers:
        context_parts.append("\n## 用户补充的关键信息\n")
        for question_id, answer in gap_filling_answers.items():
            context_parts.append(f"- {question_id}: {answer}")

    # 添加前序专家输出（原有逻辑）
    ...

    return "\n\n".join(context_parts)
```

---

## 📊 实施优先级

### P0 - 必须立即实施（解决核心痛点）

1. **✅ 优化 CoreTaskDecomposer 的 Prompt**（方案1.1）
   - 文件：`intelligent_project_analyzer/config/prompts/core_task_decomposer.yaml`
   - 工作量：1小时
   - 影响：直接提升任务精准度

2. **✅ 项目总监融合核心任务**（方案3.1）
   - 文件：`intelligent_project_analyzer/agents/dynamic_project_director.py`
   - 工作量：2小时
   - 影响：打通 Step 1 → 专家协作数据流

### P1 - 近期实施（增强体验）

3. **✅ 增强任务精准度验证**（方案1.2）
   - 文件：`intelligent_project_analyzer/services/core_task_decomposer.py`
   - 工作量：3小时
   - 影响：自动检测和修正过于抽象的任务

4. **✅ 专家上下文包含核心任务**（方案3.2）
   - 文件：`intelligent_project_analyzer/workflow/main_workflow.py`
   - 工作量：1小时
   - 影响：专家能看到用户确认的核心任务和补充信息

### P2 - 后续优化（完善闭环）

5. **✅ 任务信息依赖标记**（方案2.1）
   - 文件：`intelligent_project_analyzer/services/core_task_decomposer.py`
   - 工作量：4小时
   - 影响：为每个任务标记所需信息

6. **✅ Step 3 检查任务信息依赖**（方案2.2）
   - 文件：`intelligent_project_analyzer/services/task_completeness_analyzer.py`
   - 工作量：4小时
   - 影响：生成任务特定的补充问题

---

## 🧪 验证方案

### 测试用例1：上海老弄堂案例

**输入**：
```
上海老弄堂120平米老房翻新，业主想要"杂志级"的重生效果，
但全包预算（含软硬装）被严格限制在50万人民币。
请给出资金分配策略，明确指出哪三个关键节点必须投入重金，
哪三个环节可以极致压缩成本，并说明理由。
```

**期望输出（Step 1 任务梳理）**：
```json
[
  {
    "id": "task_1",
    "title": "上海老弄堂120平米老房翻新的杂志级效果实现策略",
    "description": "在50万全包预算约束下，研究如何通过资金分配实现杂志级视觉效果：明确三个必须重金投入的关键节点（主材选择、工艺品质、软装搭配），以及三个可极致压缩成本的环节（辅材、基础硬装、隐蔽工程），输出具体的资金分配比例建议（如硬装30%、软装40%、家具家电30%）",
    "type": "analysis",
    "required_info": ["预算详细分配", "业主风格偏好"],
    "missing_info": [],  // 预算已明确，风格已明确
    "info_status": "complete"
  },
  {
    "id": "task_2",
    "title": "上海老弄堂120平米老房结构改造可行性研究",
    "description": "调研老式里弄建筑的典型结构问题（承重墙、管线老化、采光不足等），评估120平米空间内的改造可能性与限制条件，提出结构加固和空间优化方案",
    "type": "research",
    "required_info": ["老房结构信息"],
    "missing_info": ["老房结构信息"],  // 用户未提供
    "info_status": "incomplete"
  }
]
```

**期望输出（Step 3 信息补全）**：
```json
{
  "questions": [
    {
      "id": "task_2_structure",
      "question": "为了完成「上海老弄堂120平米老房结构改造可行性研究」任务，请提供老房的基本结构信息：",
      "type": "multiple_choice",
      "options": ["砖混结构", "框架结构", "木结构", "砖木结构", "不清楚"],
      "sub_questions": [
        {"field": "build_year", "question": "建造年代大约是？"},
        {"field": "load_wall", "question": "是否知道承重墙位置？"}
      ],
      "priority": 1,
      "related_task": "task_2"
    }
  ]
}
```

---

## 📝 后续优化建议

### 长期优化方向

1. **LLM 驱动的任务信息依赖分析**
   - 当前方案2.1使用规则匹配推断 `required_info`
   - 可升级为 LLM 推理，更智能地识别任务的信息依赖

2. **任务执行反馈机制**
   - 专家执行任务时，如果发现信息不足，可以向系统反馈
   - 系统自动生成追问并返回给用户

3. **任务拆解质量评分**
   - 引入任务拆解质量评估机制
   - 根据任务的精准度、信息完整性等指标打分
   - 低分任务自动触发重新拆解

---

## 🎯 总结

### 核心问题

1. **任务精准度不足**：LLM 生成任务时倾向于抽象化，丢失用户场景的关键约束
2. **数据传递断层**：Step 1 确认的核心任务未传递给项目总监和专家

### 优化方案

1. **增强任务精准度**：优化 Prompt + 自动验证 + 场景锚定
2. **建立信息依赖检查**：任务生成时标记所需信息 + Step 3 检查并询问
3. **打通数据流**：项目总监和专家都能看到用户确认的核心任务

### 实施路径

- **P0（立即）**：优化 Prompt + 项目总监融合核心任务
- **P1（近期）**：任务精准度验证 + 专家上下文增强
- **P2（后续）**：任务信息依赖标记 + Step 3 检查任务信息

---

**文档状态**: ✅ 待审批
**下一步**: 获得批准后按 P0 → P1 → P2 顺序实施
