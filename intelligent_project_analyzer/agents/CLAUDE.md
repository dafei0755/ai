# Agents 智能体模块

**[根目录](../../CLAUDE.md) > intelligent_project_analyzer > **agents****

---

## 📋 模块职责

智能体实现模块，包含需求分析师、项目总监、动态角色工厂等核心智能体。

### 核心功能
- ✅ **需求分析师**: 解析用户输入，生成结构化需求
- ✅ **项目总监**: 动态选择角色，分派任务
- ✅ **动态角色工厂**: 从 YAML 配置创建专业智能体
- ✅ **搜索策略**: 智能决策是否使用外部搜索

---

## 🗂️ 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `base.py` | ~300 | 智能体基类、工厂类 |
| `requirements_analyst.py` | ~250 | 需求分析师 |
| `project_director.py` | ~738 | 项目总监（Dynamic Mode）|
| `dynamic_project_director.py` | ~400 | 动态角色选择逻辑 |
| `specialized_agent_factory.py` | ~350 | 专业智能体工厂 |
| `search_strategy.py` | ~200 | 搜索策略决策 |
| `__init__.py` | ~30 | 模块导出 |

---

## 🔑 关键接口

### 1. LLMAgent (智能体基类)

所有智能体的基类，提供统一接口和通用功能。

```python
class LLMAgent(ABC):
    def __init__(
        self,
        agent_type: AgentType,
        name: str,
        description: str,
        llm_model,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化智能体

        Args:
            agent_type: 智能体类型枚举
            name: 智能体名称
            description: 智能体描述
            llm_model: LLM 模型实例
            config: 配置参数
        """

    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取系统提示词"""

    @abstractmethod
    def get_task_description(self, state: ProjectAnalysisState) -> str:
        """获取任务描述"""

    @abstractmethod
    def execute(
        self,
        state: ProjectAnalysisState,
        config: RunnableConfig,
        store: Optional[BaseStore] = None
    ) -> AnalysisResult:
        """执行分析任务"""
```

**关键方法**:

- `validate_input`: 验证输入
- `get_dependencies`: 获取依赖的智能体
- `handle_error`: 错误处理
- `_track_execution_time`: 跟踪执行时间

---

### 2. RequirementsAnalystAgent (需求分析师)

**职责**: 解析用户输入，生成结构化需求文档。

**系统提示词**:

```python
def get_system_prompt(self) -> str:
    """
    需求分析师系统提示词

    核心任务:
    1. 深入理解用户需求和项目背景
    2. 提取关键信息和潜在需求
    3. 生成结构化的需求文档
    4. 识别设计重点和限制条件
    """
```

**输出格式**:

```json
{
  "project_overview": "项目概述",
  "core_objectives": ["目标1", "目标2"],
  "functional_requirements": ["需求1", "需求2"],
  "target_users": "目标用户画像",
  "constraints": {
    "budget": "预算限制",
    "timeline": "时间限制",
    "technical": "技术限制"
  },
  "design_priorities": ["优先级1", "优先级2"],
  "special_requirements": ["特殊需求1"]
}
```

**使用示例**:

```python
agent = AgentFactory.create_agent(
    AgentType.REQUIREMENTS_ANALYST,
    llm_model=llm,
    config=config
)

result = agent.execute(state, {}, store)
structured_requirements = result.structured_data
```

---

### 3. ProjectDirectorAgent (项目总监)

**职责**: 制定分析策略，动态选择专业角色，分派任务。

**重要**: 仅支持 **Dynamic Mode**（从 YAML 动态选择角色）。

**系统提示词版本**: v6.0 最终版（客户定制）

**核心流程**:

```
用户需求 → 评估与分解 → 查询类型确定 → 研究计划 → 角色选择 → 任务分派
```

**查询类型**:

1. **深度优先查询**: 同一主题，多个视角深入分析
2. **广度优先查询**: 多个子问题，独立并行研究
3. **直接查询**: 集中定义，单一调查

**输出格式** (v6.0):

```json
{
  "query_type": "深度优先查询/广度优先查询/直接查询",
  "query_type_reasoning": "判定推理过程",
  "assessment": {
    "core_concepts": ["概念1", "概念2"],
    "required_facts": ["事实1", "事实2"],
    "constraints": ["约束1", "约束2"],
    "user_concerns": "用户核心关切",
    "deliverable_format": "交付物形态"
  },
  "research_plan": {
    "perspectives": ["视角1", "视角2"]  // 深度优先
  },
  "task_assignments": {
    "V2": "具体任务描述",
    "V3": "具体任务描述"
  },
  "execution_strategy": "并行/串行",
  "agent_count": 5,
  "agent_count_reasoning": "数量决策依据"
}
```

**Dynamic Mode 执行逻辑**:

```python
def _execute_dynamic_mode(self, state, config, store, start_time) -> Command:
    # 1. 提取需求信息
    requirements = state.get("structured_requirements", {})
    requirements_text = self._format_requirements_for_selection(requirements)

    # 2. 使用动态项目总监选择角色
    selection = self.dynamic_director.select_roles_for_task(requirements_text)

    # 3. 创建并行命令
    parallel_commands = []
    for role_id in selection.selected_roles:
        base_type, rid = self.role_manager.parse_full_role_id(role_id)
        role_config = self.role_manager.get_role_config(base_type, rid)

        parallel_commands.append(
            Send("dynamic_role_executor", {
                "role_id": role_id,
                "role_config": role_config,
                "task": selection.task_distribution[role_id]
            })
        )

    # 4. 返回 Command
    return Command(
        update={
            "strategic_analysis": {...},
            "active_agents": selection.selected_roles
        },
        goto=parallel_commands
    )
```

---

### 4. DynamicProjectDirector (动态角色选择器)

**职责**: 基于需求文本，从角色库中智能选择最合适的专家团队。

**核心方法**:

```python
class DynamicProjectDirector:
    def __init__(self, llm_model, role_manager: RoleManager):
        """初始化动态项目总监"""

    def select_roles_for_task(
        self,
        requirements_text: str,
        strategy_name: str = "balanced"
    ) -> RoleSelection:
        """
        动态选择角色

        Args:
            requirements_text: 需求描述文本
            strategy_name: 策略名称（balanced/quick/comprehensive）

        Returns:
            RoleSelection: 包含选择的角色和任务分派
        """
```

**RoleSelection 数据结构**:

```python
@dataclass
class RoleSelection:
    selected_roles: List[str]  # ["V3_人物及叙事专家_3-1", ...]
    task_distribution: Dict[str, str]  # {role_id: task_description}
    reasoning: str  # 选择推理
    confidence: float  # 置信度
```

**选择策略** (从 `role_selection_strategy.yaml`):

- **balanced**: 平衡策略（默认）
- **quick**: 快速策略（最少角色）
- **comprehensive**: 全面策略（最多角色）
- **technical_focused**: 技术导向
- **design_focused**: 设计导向

---

### 5. SpecializedAgentFactory (专业智能体工厂)

**职责**: 从 YAML 配置动态创建专业智能体节点。

**核心方法**:

```python
class SpecializedAgentFactory:
    @staticmethod
    def create_simple_agent_node(
        role_id: str,
        role_config: Dict[str, Any],
        llm_model
    ) -> Callable:
        """
        创建简单智能体节点

        Args:
            role_id: 完整角色 ID (如 "V3_人物及叙事专家_3-1")
            role_config: 角色配置（从 roles.yaml 加载）
            llm_model: LLM 模型实例

        Returns:
            可调用的节点函数
        """

    @staticmethod
    def create_agent_with_review(
        role_id: str,
        role_config: Dict[str, Any],
        llm_model,
        enable_search: bool = True
    ) -> Callable:
        """
        创建带审核的智能体节点（支持多轮优化）
        """
```

**使用示例**:

```python
# 创建智能体节点
agent_node = SpecializedAgentFactory.create_simple_agent_node(
    role_id="V3_人物及叙事专家_3-1",
    role_config=role_config,
    llm_model=llm
)

# 执行
result = agent_node(state)
```

---

### 6. SearchStrategy (搜索策略)

**职责**: 智能决策是否需要使用外部搜索工具（Tavily、Arxiv）。

**核心方法**:

```python
class SearchStrategy:
    @staticmethod
    def should_use_search(
        task_description: str,
        role_type: str,
        llm_model
    ) -> Dict[str, Any]:
        """
        判断是否需要搜索

        Returns:
            {
                "need_search": bool,
                "search_type": "tavily" | "arxiv" | None,
                "search_queries": List[str],
                "reasoning": str
            }
        """
```

**决策逻辑**:

- 分析任务中是否包含"最新"、"当前"、"趋势"等关键词
- 判断是否需要行业数据、案例研究、技术文献
- 决定使用 Tavily（通用搜索）还是 Arxiv（学术文献）

---

## 📦 关键依赖

### 内部依赖
- `core.state`: 状态定义
- `core.types`: 类型定义
- `core.role_manager`: 角色管理
- `core.strategy_manager`: 策略管理
- `tools.tavily_search`: Tavily 搜索
- `tools.arxiv_search`: Arxiv 搜索

### 外部依赖
- `langchain_core.runnables`: Runnable, RunnableConfig
- `langchain_core.messages`: HumanMessage, AIMessage
- `langgraph.types`: Command, Send
- `langgraph.store.base`: BaseStore

---

## 🧪 测试覆盖

### 测试文件
- `test_llm_connection.py`: LLM 连接测试
- `test_structured_output.py`: 结构化输出测试
- `test_required_fields.py`: 必填字段验证

### 关键测试场景
1. ✅ 需求分析师输出格式
2. ✅ 项目总监角色选择
3. ✅ 动态智能体创建
4. ✅ 搜索策略决策
5. ⚠️ 完整工作流集成（端到端测试）

---

## 🚨 常见问题

### Q1: 如何自定义智能体的系统提示词？

**A**: 继承 `LLMAgent` 并重写 `get_system_prompt`:

```python
class MyAgent(LLMAgent):
    def get_system_prompt(self) -> str:
        return """
        您是一个专业的...
        核心任务:
        1. ...
        2. ...
        """
```

### Q2: 如何添加新的角色到动态系统？

**A**: 在 `config/roles.yaml` 添加配置：

```yaml
V7_新角色:
  - role_id: "7-1"
    name: "新角色名称"
    description: "角色描述"
    expertise:
      - "专业领域1"
      - "专业领域2"
    system_prompt: |
      您是一个专业的...
```

无需修改代码，系统会自动加载。

### Q3: 如何强制使用特定角色？

**A**: 修改 `role_selection_strategy.yaml` 的 `required_categories`:

```yaml
selection_rules:
  required_categories:
    - "V7_新角色"
```

### Q4: 如何禁用外部搜索？

**A**: 在智能体配置中设置：

```python
config = {
    "enable_search": False
}

agent = SpecializedAgentFactory.create_agent_with_review(
    role_id, role_config, llm, enable_search=False
)
```

### Q5: 如何获取智能体的执行时间？

**A**: 查看 `state["agent_results"][agent_type]`:

```python
result = state["agent_results"]["requirements_analyst"]
execution_time = result.get("execution_time_ms")
```

---

## 🛠️ 高级技巧

### 1. 自定义搜索查询

```python
# 在智能体中注入自定义搜索查询
def get_task_description(self, state):
    base_task = super().get_task_description(state)

    search_queries = [
        "室内设计最新趋势 2025",
        "可持续设计案例研究"
    ]

    return f"{base_task}\n\n搜索关键词: {', '.join(search_queries)}"
```

### 2. 条件性启用搜索

```python
def execute(self, state, config, store):
    # 判断是否需要搜索
    requirements = state.get("structured_requirements", {})
    needs_trends = "最新趋势" in requirements.get("design_priorities", [])

    if needs_trends:
        search_strategy = SearchStrategy.should_use_search(...)
        # 使用搜索结果
    else:
        # 直接分析
```

### 3. 多轮优化

```python
def execute(self, state, config, store):
    # 第一轮分析
    result = self._analyze(state)

    # 获取审核反馈
    feedback = state.get("review_feedback", {})
    my_feedback = feedback.get(self.agent_type.value, {})

    if my_feedback.get("issues"):
        # 第二轮优化
        result = self._refine_analysis(result, my_feedback)

    return result
```

---

## 📚 相关文档

- [根级文档](../../CLAUDE.md)
- [Core 模块](../core/CLAUDE.md) - 角色管理、策略管理
- [Workflow 模块](../workflow/CLAUDE.md) - 如何编排智能体
- [Tools 模块](../tools/CLAUDE.md) - 外部搜索工具

---

**最后更新**: 2025-11-16
**维护者**: Agents Team
