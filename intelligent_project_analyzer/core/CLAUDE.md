# Core 核心模块

**[根目录](../../CLAUDE.md) > intelligent_project_analyzer > **core****

---

## 📋 模块职责

核心状态管理模块，负责系统的核心数据结构、状态管理、角色管理和策略管理。

### 核心功能
- ✅ **状态定义**: `ProjectAnalysisState` 全局状态容器
- ✅ **状态管理**: `StateManager` 状态操作工具类
- ✅ **类型定义**: `AgentType`, `AnalysisStage` 等枚举
- ✅ **角色管理**: `RoleManager` 动态角色加载与查询
- ✅ **策略管理**: `StrategyManager` 角色选择策略

---

## 🗂️ 文件清单

### 核心文件

| 文件 | 行数 | 职责 |
|------|------|------|
| `state.py` | ~350 | 状态定义、StateManager |
| `types.py` | ~200 | 类型定义、数据模型 |
| `role_manager.py` | ~300 | 角色配置管理 |
| `strategy_manager.py` | ~250 | 策略管理 |
| `__init__.py` | ~20 | 模块导出 |

---

## 🔑 关键接口

### 1. ProjectAnalysisState (状态容器)

**核心字段**：

```python
class ProjectAnalysisState(TypedDict):
    # === 基础信息 ===
    session_id: str
    user_id: Optional[str]
    created_at: str
    updated_at: str

    # === 用户输入 ===
    user_input: str
    structured_requirements: Optional[Dict[str, Any]]

    # === 分析策略 ===
    strategic_analysis: Annotated[Optional[Dict[str, Any]], merge_agent_results]
    subagents: Annotated[Optional[Dict[str, str]], merge_agent_results]
    agent_results: Annotated[Optional[Dict[str, Any]], merge_agent_results]  # ⚠️ 使用 reducer

    # === 结果聚合 ===
    aggregated_results: Optional[Dict[str, Any]]
    final_report: Optional[str]
    pdf_file_path: Optional[str]

    # === 流程控制 ===
    current_stage: str  # AnalysisStage
    active_agents: Annotated[List[str], merge_lists]  # ⚠️ 使用 reducer
    completed_agents: Annotated[List[str], merge_lists]
    failed_agents: Annotated[List[str], merge_lists]

    # === 任务依赖 ===
    execution_batch: Optional[str]  # "first" / "second"
    dependency_summary: Optional[Dict[str, Any]]

    # === 第二批策略 ===
    second_batch_approved: Optional[bool]
    second_batch_strategies: Optional[Dict[str, Any]]

    # === 🆕 多轮审核控制 ===
    review_round: int  # 当前审核轮次（从 0 开始）
    review_history: Annotated[List[Dict[str, Any]], merge_lists]
    best_result: Optional[Dict[str, Any]]  # 历史最佳结果
    best_score: float  # 历史最佳评分
    review_feedback: Optional[Dict[str, Any]]  # 传递给专家的反馈

    # === 错误处理 ===
    errors: List[Dict[str, Any]]
    retry_count: int

    # === 元数据 ===
    metadata: Dict[str, Any]
```

**⚠️ 重要提示**:
- 带 `Annotated[..., merge_*]` 的字段使用 **reducer 函数**，支持并发更新
- `agent_results` 是核心结果存储，键是 `role_id`（如 `"V3_人物及叙事专家_3-1"`）
- 节点只需返回 **部分更新**，不要返回完整 state

### 2. StateManager (状态管理器)

**核心方法**：

```python
class StateManager:
    @staticmethod
    def create_initial_state(
        user_input: str,
        session_id: str,
        user_id: Optional[str] = None
    ) -> ProjectAnalysisState:
        """创建初始状态"""

    @staticmethod
    def update_state(
        state: ProjectAnalysisState,
        updates: Dict[str, Any]
    ) -> ProjectAnalysisState:
        """更新状态（返回新状态）"""

    @staticmethod
    def update_stage(
        state: ProjectAnalysisState,
        new_stage: AnalysisStage
    ) -> Dict[str, Any]:
        """更新分析阶段（返回部分更新）"""

    @staticmethod
    def is_analysis_complete(state: ProjectAnalysisState) -> bool:
        """检查分析是否完成（基于动态分派的智能体）"""

    @staticmethod
    def get_analysis_progress(state: ProjectAnalysisState) -> Dict[str, Any]:
        """获取分析进度"""
```

### 3. AnalysisStage (分析阶段)

```python
class AnalysisStage(Enum):
    INIT = "init"
    REQUIREMENT_COLLECTION = "requirement_collection"
    REQUIREMENT_CONFIRMATION = "requirement_confirmation"
    STRATEGIC_ANALYSIS = "strategic_analysis"
    PARALLEL_ANALYSIS = "parallel_analysis"
    ANALYSIS_REVIEW = "analysis_review"  # 分析结果审核
    RESULT_AGGREGATION = "result_aggregation"
    PDF_GENERATION = "pdf_generation"
    COMPLETED = "completed"
    ERROR = "error"
```

### 4. AgentType (智能体类型)

```python
class AgentType(Enum):
    """仅保留核心智能体（V2-V6 已移除，使用动态角色）"""
    REQUIREMENTS_ANALYST = "requirements_analyst"
    PROJECT_DIRECTOR = "project_director"
    RESULT_AGGREGATOR = "result_aggregator"
    PDF_GENERATOR = "pdf_generator"
```

**⚠️ 注意**: V2-V6 专家已迁移到动态角色系统，不再使用固定枚举。

---

## 🔄 Reducer 函数

### merge_agent_results

用于合并并发节点的 `agent_results` 更新：

```python
def merge_agent_results(
    left: Optional[Dict[str, Any]],
    right: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """合并智能体结果字典"""
    if left is None:
        return right or {}
    if right is None:
        return left
    # 右侧覆盖左侧同名键
    return {**left, **right}
```

**使用场景**: 多个专家并行执行时，它们各自更新 `agent_results[role_id]`，LangGraph 自动合并。

### merge_lists

用于合并列表字段（如 `active_agents`, `completed_agents`）：

```python
def merge_lists(
    left: Optional[List[Any]],
    right: Optional[List[Any]]
) -> List[Any]:
    """合并列表（去重）"""
    if left is None:
        return right or []
    if right is None:
        return left

    result = left.copy()
    for item in right:
        if item not in result:
            result.append(item)
    return result
```

---

## 📦 关键依赖

### 内部依赖
- 无（这是最底层模块）

### 外部依赖
- `langgraph.graph.add_messages`: 用于 `conversation_history`
- `langchain_core.messages.BaseMessage`: 消息基类
- `pydantic`: 类型验证（间接依赖）

---

## 🧪 测试覆盖

### 测试文件
- `test_config_loading.py`: 状态初始化测试
- `test_structured_output.py`: 状态字段验证

### 关键测试场景
1. ✅ 初始状态创建
2. ✅ 状态更新与合并
3. ✅ 并发更新（reducer 函数）
4. ✅ 分析进度计算
5. ✅ 完成状态判断

---

## 🚨 常见问题

### Q1: 为什么节点返回后状态未更新？

**A**: 检查是否返回了完整 state 而非部分更新。正确做法：

```python
# ❌ 错误：返回完整 state
def my_node(state: ProjectAnalysisState) -> ProjectAnalysisState:
    state["field"] = "value"
    return state

# ✅ 正确：返回部分更新
def my_node(state: ProjectAnalysisState) -> Dict[str, Any]:
    return {"field": "value"}
```

### Q2: 并发节点如何更新同一个字段？

**A**: 使用 `Annotated` 标注 reducer 函数：

```python
# 在 TypedDict 定义中
agent_results: Annotated[Optional[Dict[str, Any]], merge_agent_results]
```

LangGraph 会自动调用 `merge_agent_results` 合并多个并发更新。

### Q3: 如何获取当前轮次的审核结果？

**A**:

```python
review_round = state.get("review_round", 0)
review_history = state.get("review_history", [])
if review_history:
    current_review = review_history[-1]
    score = current_review["final_decision"]["overall_score"]
```

### Q4: 如何判断是否需要重新执行？

**A**: 查看最新审核的决策：

```python
review_history = state.get("review_history", [])
if review_history:
    latest = review_history[-1]
    decision = latest["final_decision"]["decision"]
    agents_to_rerun = latest["final_decision"].get("agents_to_rerun", [])
```

---

## 🛠️ 数据模型

### RoleManager (角色管理器)

**职责**: 从 `roles.yaml` 加载角色配置，提供查询和验证功能。

**核心方法**:

```python
class RoleManager:
    def __init__(self, config_path: Optional[str] = None):
        """初始化角色管理器，加载 YAML 配置"""

    def get_role_config(self, category: str, role_id: str) -> Dict[str, Any]:
        """获取角色配置"""

    def parse_full_role_id(self, full_id: str) -> Tuple[str, str]:
        """解析完整角色 ID (如 "V3_人物及叙事专家_3-1" → ("V3", "3-1"))"""

    def get_all_role_ids(self) -> List[str]:
        """获取所有可用角色 ID"""

    def validate_role_selection(self, selected_ids: List[str]) -> bool:
        """验证角色选择是否有效"""
```

### StrategyManager (策略管理器)

**职责**: 管理角色选择策略（从 `role_selection_strategy.yaml` 加载）。

**核心方法**:

```python
class StrategyManager:
    def __init__(self, strategy_path: Optional[str] = None):
        """初始化策略管理器"""

    def get_strategy(self, name: str = "balanced") -> Dict[str, Any]:
        """获取选择策略"""

    def validate_selection(
        self,
        selected_roles: List[str],
        strategy_name: str = "balanced"
    ) -> Tuple[bool, List[str]]:
        """验证选择是否符合策略"""
```

---

## 📚 相关文档

- [根级文档](../../CLAUDE.md)
- [Workflow 模块](../workflow/CLAUDE.md) - 使用 state 编排流程
- [Agents 模块](../agents/CLAUDE.md) - 智能体如何更新 state
- [Review 模块](../review/CLAUDE.md) - 审核系统如何使用 review_history

---

**最后更新**: 2025-11-16
**维护者**: Core Team
