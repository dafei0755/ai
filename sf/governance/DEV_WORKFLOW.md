# 稳定开发工作流规范

**适用版本**：v8.0.0+
**目标**：稳定开发、逐步迭代、每个重要节点有记录可锁定能回滚、方便扩展、职责界面清晰

---

## 一、开发迭代原则（4 条）

### 原则 1：小步提交，单一职责

每个 commit 只改一件事。commit 信息格式：

```
<type>(<scope>): <what>

[可选] 更详细说明

[可选] Refs: ADR-001, #issue-id
```

type 取值：`fix`（bug 修复）、`feat`（新功能）、`refactor`（重构，无功能变化）、`chore`（清理/配置）、`test`（测试）、`docs`（仅文档）

scope 取值：`workflow`、`api`、`services`、`agents`、`state`、`security`、`frontend` 等

**反例**（禁止）：
```
# 禁止
git commit -m "fix stuff"
git commit -m "lots of changes"
git commit -m "WIP v8.1"
```

### 原则 2：测试前置

每次改动 `main_workflow.py` 或 `state.py` 之前，必须：
1. 确认已有对应单元测试
2. 如果没有，先补测试，再改代码

每次废弃一个节点，必须执行[节点废弃 5 步清单](#节点废弃-5-步清单)。

### 原则 3：无破坏性改动优先合并

清理类工作（脚本归类、lint 修复、注释删除）不等待功能开发完成，随时可以独立合并。这类工作不需要新功能的测试覆盖，只需要现有测试通过。

### 原则 4：新功能用特性开关

新功能上线时，用环境变量控制（取代 hardcode）。规则：
- 开关默认值：`false`（新功能默认关闭，手动启用）
- 开关命名：`FEATURE_<功能名全大写>_ENABLED`（不再用 `USE_V7XX_` 的旧风格）
- 开关生命周期：合并后**不超过 2 个 MINOR 版本**必须移除开关，将功能内联为唯一路径
- 禁止：开关默认值为 `false` 且长期不清理（这正是 `USE_V716_AGENTS` 的错误模式）

---

## 二、版本节点管理（锁定与回滚）

### 2.1 版本号规则

- **格式**：`MAJOR.MINOR.PATCH`（SemVer）
- **唯一来源**（SSOT）：根目录 `VERSION` 文件
- **含义**：
  - `PATCH`（x.x.**N**）：Bug 修复、文档更新、小清理，不改 API
  - `MINOR`（x.**N**.0）：新功能、重构、性能优化，向后兼容
  - `MAJOR`（**N**.0.0）：破坏性变更（State 字段删除、API 签名变更等）

### 2.2 打 Tag（锁定版本节点）

每个 MINOR 版本发布时打 git tag：

```bash
# 1. 更新 VERSION 文件
echo "8.1.0" > VERSION

# 2. 更新 CHANGELOG.md（将 [Unreleased] 改为 [8.1.0] 并填日期）
# 手动编辑 CHANGELOG.md

# 3. Commit
git add VERSION CHANGELOG.md
git commit -m "chore(release): v8.1.0"

# 4. 打 Tag
git tag -a v8.1.0 -m "Release v8.1.0: <一句话说明主要变更>"
git push origin main --tags
```

> PATCH 版本也打 tag，但不需要额外的 release commit，直接在最后一个 commit 上打 tag 即可。

### 2.3 回滚方式

**方式 A：回滚到某个版本的文件内容（不改 git 历史）**
```bash
git checkout v8.0.0 -- .   # 将所有文件内容还原到 v8.0.0
git status                  # 确认变化范围
git commit -m "revert: roll back to v8.0.0 state"
```

**方式 B：回滚最近 N 个 commit（保留历史，生成反向 commit）**
```bash
git revert HEAD~3..HEAD   # 回滚最近 3 个 commit
```

**方式 C：强制回到某个 Tag（仅本地开发时使用，不推送）**
```bash
git reset --hard v8.0.0   # 危险：会丢失本地未提交的修改
```

### 2.4 版本自动更新脚本（`scripts/bump_version.py`）

> 该脚本待建，功能描述如下：

```
用法：python scripts/bump_version.py [patch|minor|major]

功能：
1. 读取 VERSION 文件，计算新版本号
2. 更新 VERSION 文件
3. 在 CHANGELOG.md 中将 [Unreleased] 替换为 [x.y.z] (YYYY-MM-DD)
4. 插入新的空 [Unreleased] 节
5. 输出待执行的 git 命令（不自动执行，需人工确认）
```

---

## 三、版本发布检查清单

**每次发布 MINOR 版本前，逐项确认**：

```
□ make check 全绿（ruff lint + mypy + pytest）
□ 无新增 DEPRECATED 状态字段
□ 无新增 v7.xxx 风格标记（CI 门禁应自动拦截）
□ CHANGELOG.md [Unreleased] 节已填写本次变更
□ 若有废弃节点：已执行节点废弃 5 步清单
□ 若有破坏性变更：VERSION MAJOR 号已递增
□ VERSION 文件已更新
□ git tag vX.Y.Z 已打
□ 冒烟测试通过（python _smoke_v14.py 或等效）
```

---

## 四、节点废弃 5 步清单

**废弃 LangGraph 工作流中的任意节点时，必须按顺序完成**：

1. **注释注册行**：注释掉 `workflow.add_node("node_name", self._node_method)`
2. **清理路由返回值**：在所有路由函数中，找到并删除/替换 `return "node_name"` 分支（绝不留着）
3. **删除孤立路由函数**：删除 `_route_after_node_name(...)` 函数（如果存在）
4. **标记状态字段**：将该节点独有的状态字段标记 `# [DEPRECATED vX.Y.Z] 废弃原因`
5. **记录 CHANGELOG**：在 `CHANGELOG.md` [Unreleased] 节记录废弃，引用对应 ADR 编号（若无 ADR 则新建）

> **教训来源**：ADR-001 废弃了 `analysis_review` 节点，但步骤 2-3 未执行，导致 P0 死代码路由存活至 v8.0.0

---

## 五、扩展新功能规范（方便扩展）

### 新增 Agent

1. 在 `intelligent_project_analyzer/agents/` 创建新文件，如 `new_expert_agent.py`
2. 在 Agent 类中实现 `execute(state: ProjectAnalysisState) -> Dict`
3. 在 `agents/registry.py`（或等效的注册机制）中注册
4. 在 `workflow/main_workflow.py` 中用 `workflow.add_node()` 注册节点
5. 在适当的路由函数中添加路由分支
6. 补充单元测试（`tests/agents/test_new_expert_agent.py`）

**禁止**：直接修改 `main_workflow.py` 中其他已稳定 Agent 的逻辑来适配新 Agent

### 新增 API 路由

1. 在 `intelligent_project_analyzer/api/routes/` 创建新路由文件，如 `new_feature_routes.py`
2. 定义 `router = APIRouter(prefix="/api/new-feature", tags=["new-feature"])`
3. 在 `api/server.py` 的 `include_router` 处注册
4. 补充集成测试

**禁止**：直接在 `server.py` 中添加路由函数（继续扩大单文件）

### 新增 Service

1. 确定所属子包：`session/`、`search/`、`llm/`、`dimension/`、`integration/`（或根据职责新建子包）
2. 在对应子包目录创建新文件
3. 在子包 `__init__.py` 中导出公开 API
4. 通过依赖注入（构造函数参数）而非全局 import 依赖其他 Service

### 新增配置项

- **系统级配置**（DB 地址、Redis 地址、API Key 规范）→ `config/SYSTEM_CONFIG.yaml`
- **服务运行策略**（prompt 模板、维度权重、分析参数）→ `intelligent_project_analyzer/services/config/`
- **环境变量**（敏感信息、可覆盖参数）→ `.env` 文件（不提交）+ 说明加入 `config/SYSTEM_CONFIG.example.yaml`

---

## 六、职责界面清晰规范

### 各层职责边界

| 层级 | 只负责 | 绝对不允许 |
|------|--------|------------|
| `api/` | HTTP 路由、入参校验、响应格式、WebSocket 生命周期 | 直接调用 agents；直接操作 DB；包含业务逻辑 |
| `workflow/` | 图结构定义（add_node/add_edge）、节点编排、状态路由 | 业务逻辑；直接 LLM 调用；直接操作 DB |
| `agents/` | 单一 Agent 的 prompt 构建 + LLM 调用 + 结果解析 | 直接操作 DB；直接修改 State；调用其他 Agent |
| `services/` | 可复用业务逻辑（优先无状态） | 直接依赖其他 Service（通过构造函数 DI）；包含路由逻辑 |
| `tools/` | 外部 API 封装（Tavily/Bocha/ArXiv/RAGFlow） | 业务判断逻辑；直接操作 State |
| `core/` | State 定义、基础模型、公共常量 | 导入上层模块（api/agents/services 等） |
| `security/` | 输入安全校验、输出安全校验、认证 | 业务逻辑 |

### 依赖方向（单向，禁止反向）

```
api → workflow → agents → services → tools
               ↘           ↘
                core         core
```

`core/` 不依赖任何其他层。`services/` 内部子包之间通过接口（抽象基类）而非直接 import 通信。

### 状态（State）操作规范

- **只有 agents 和 workflow 节点函数**可以修改 State
- `services/` 返回数据给节点函数，**不直接写入 State**
- State 字段的增/删必须在 CHANGELOG 中记录，删除字段前至少保留 1 个 MINOR 版本的 DEPRECATED 标记

---

## 七、CI/CD 检查清单（本地 pre-push）

运行 `make check` 等效于执行以下步骤：

```bash
# 1. 代码风格
ruff check intelligent_project_analyzer/ tests/

# 2. 类型检查
mypy intelligent_project_analyzer/agents intelligent_project_analyzer/workflow intelligent_project_analyzer/services

# 3. 快速测试（排除 slow/llm 标记）
pytest tests/ -m "not slow and not llm" -q --tb=short

# 4. 禁止规则检查（手动执行）
# 禁止新增 v7.xxx 风格标记
git diff HEAD --name-only | xargs grep -l "v7\." 2>/dev/null && echo "警告：发现 v7.xxx 标记，请确认是否为遗留标记"
```

> **目标**：`make check` 全绿才能 push 到主分支
