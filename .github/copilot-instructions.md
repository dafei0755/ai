# Copilot Instructions for AI Agents

欢迎来到 `intelligent_project_analyzer` 项目！本说明专为 AI 编程助手（如 Copilot、GPT-4.1）设计，帮助你高效理解和贡献代码。

## ⚠️ 重要：开发规范与稳定性保障

**在修改代码前，请务必阅读以下规范文档**：
- **[开发规范](DEVELOPMENT_RULES.md)**：代码复用、数据契约、测试要求、**LLM提示词规范**
- **[变更检查清单](PRE_CHANGE_CHECKLIST.md)**：修改前必须完成的检查项

### 核心规则速查

1. **代码复用**：公共函数放 `lib/`（前端）或 `utils/`（后端），禁止重复实现
2. **专家名称格式化**：统一使用 `lib/formatters.ts` 的 `formatExpertName`
3. **修改前搜索**：`grep -rn "函数名" --include="*.tsx" frontend-nextjs/`
4. **测试覆盖**：公共函数必须有单元测试
5. **🆕 问卷/LLM相关**：修改前必读 `DEVELOPMENT_RULES.md` 第10-11章
6. **🆕 v7.17 Agent架构**：修改需求分析师前必读 `DEVELOPMENT_RULES.md` 第8.22节
7. **🆕 v7.18 问卷Agent**：修改问卷生成前必读 `DEVELOPMENT_RULES.md` 第8.23节
8. **🆕 v7.19 Config优化**：修改配置文件前必读 `DEVELOPMENT_RULES.md` 第8.24节

### v7.19 Config 目录全面优化 🆕

**核心升级** (2025-12-17):
- Prompts 目录: 废弃未使用配置，统一版本管理
- Roles 目录: V2-V6 角色配置添加 v7.19 对齐声明
- 策略配置: `role_selection_strategy.yaml` v7.3 → v7.4

**配置文件版本**:
| 配置 | 版本 | 用途 |
|------|------|------|
| `role_selection_strategy.yaml` | v7.4 | 角色选择策略 |
| `content_safety.yaml` | v1.1 | 内容安全配置 |
| `deliverable_role_constraints.yaml` | v1.1 | 交付物约束 |
| `roles/v2_design_director.yaml` | v2.6 | 设计总监 |
| `roles/v3_narrative_expert.yaml` | v2.6 | 叙事专家 |
| `roles/v4_design_researcher.yaml` | v2.7 | 设计研究员 |
| `roles/v5_scenario_expert.yaml` | v2.8 | 场景专家 |
| `roles/v6_chief_engineer.yaml` | v2.8 | 总工程师 |

### v7.18 问卷生成 StateGraph Agent

**核心升级** (2025-12-17):
- QuestionnaireAgent 集成到主工作流
- 共享函数: `shared_agent_utils.py` 中 3 个问卷相关函数
- 环境变量控制: `USE_V718_QUESTIONNAIRE_AGENT=true`

**关键文件**:
- `agents/questionnaire_agent.py` - StateGraph 实现
- `interaction/nodes/calibration_questionnaire.py` - Agent 分支入口
- `utils/shared_agent_utils.py` - 共享函数

**执行流程**:
```
calibration_questionnaire.py
    ↓
[USE_V718=true?] → QuestionnaireAgent (StateGraph)
    ↓ No
LLMQuestionGenerator (原有逻辑)
```

### v7.17 需求分析师 StateGraph Agent

**核心升级** (2025-12-17):
- 两阶段 LLM 架构: Phase1 快速定性 + Phase2 深度分析
- 程序化能力边界检测: `CapabilityDetector`
- 环境变量控制: `USE_V717_REQUIREMENTS_ANALYST=true`

**关键文件**:
- `agents/requirements_analyst_agent.py` - StateGraph 实现 (~790行)
- `utils/capability_detector.py` - 能力检测 (~350行)
- `config/prompts/requirements_analyst_phase1.yaml` - Phase1 提示词
- `config/prompts/requirements_analyst_phase2.yaml` - Phase2 提示词

**StateGraph 节点**:
```
START → precheck (~1ms) → phase1 (~10s) → [条件] → phase2 (~20s) → output → END
                                              ↓
                                           output (信息不足)
```

### 问卷系统专项规范（易出错区域）

**修改问卷相关代码前必须检查**：
- `llm_generator.py` 的 `_build_analysis_summary` 是否覆盖所有字段
- `questionnaire_generator.yaml` 是否包含禁止/必须规则
- 生成的问题是否引用用户原话关键词

**已知陷阱**：
- ❌ 字段提取不完整 → 问卷变成泛化模板
- ❌ 提示词缺乏强制约束 → LLM 生成通用问题
- ❌ 未验证相关性 → 问题与用户输入脱节

## 项目架构总览
- **模块化设计**：项目分为 agents、core、services、tools、utils、report、review、workflow、interaction、frontend、api 等子模块，每个模块有独立职责。
- **LangGraph 工作流**：核心分析流程由 `workflow/` 下的 MainWorkflow/DynamicWorkflow 组织，支持多智能体协作与动态节点。
- **多智能体协作**：`agents/` 实现需求分析师、项目总监、动态角色工厂等，支持 YAML 配置动态生成 agent。
- **服务层**：`services/` 提供 LLM 工厂、工具工厂、上下文管理，统一模型和工具实例化。
- **人机交互**：`interaction/` 实现关键节点的 interrupt 机制，支持用户输入、审核、确认。
- **前后端分离**：`api/` 用 FastAPI 提供 RESTful 服务，`frontend/` 用 Streamlit 构建 Web UI。
- **报告生成**：`report/` 聚合分析结果，支持文本和 PDF 输出，采用 Pydantic 保证结构化。
- **多轮审核**：`review/` 支持红蓝对抗、评委裁决、甲方审核等多视角流程。

## 关键开发流程
- **依赖管理**：所有依赖见 `requirements.txt`，部分模块有独立 requirements。
- **运行前端**：
  ```cmd
  python intelligent_project_analyzer/frontend/run_frontend.py
  ```
- **启动 API 服务**：
  ```cmd
  python intelligent_project_analyzer/api/server.py
  ```
- **核心工作流入口**：
  - `workflow/main_workflow.py` 组织主流程
  - `workflow/dynamic_workflow.py` 支持动态流程
- **配置文件**：YAML 配置见 `config/roles/` 和 `config/prompts/`，用于 agent/角色/提示词动态加载。

## 项目专有约定
- **interrupt 机制**：交互节点用 `interrupt()` 暂停，等待用户输入，见 `interaction/`。
- **Agent 动态生成**：角色/agent 可通过 YAML 配置动态创建，见 `agents/specialized_agent_factory.py`。
- **多轮分批执行**：工作流支持批次切换（如 V3/V4/V5 → V2/V6），见 `workflow/`。
- **审核流程**：红蓝对抗、评委裁决、甲方审核等见 `review/`，流程图见 CLAUDE.md。
- **报告结构**：所有输出报告采用 Pydantic 数据模型，见 `report/result_aggregator.py`。
- **外部工具集成**：如 Tavily、Arxiv、RAGFlow，见 `tools/`，API key 配置于 .env。

## 重要文件/目录参考
- `agents/base.py`：智能体基类与统一接口
- `agents/requirements_analyst_agent.py`：**🆕 v7.17 需求分析师 StateGraph Agent**
- `core/state.py`：全局状态容器
- `services/llm_factory.py`：模型实例化工厂
- `utils/capability_detector.py`：**🆕 v7.17 程序化能力边界检测**
- `report/result_aggregator.py`：LLM 驱动结果聚合
- `frontend/app.py`：Streamlit 主界面
- `api/server.py`：FastAPI 服务主入口
- `config/roles/`、`config/prompts/`：角色与提示词配置
- **🆕 `interaction/questionnaire/`**：问卷生成核心模块（易出错）

## 代码风格与模式
- **强类型/Pydantic**：数据结构统一用 Pydantic
- **职责分明**：每个模块有独立 CLAUDE.md 说明职责与接口
- **YAML 配置驱动**：角色、提示词、策略均可通过 YAML 动态加载

---
如有不清楚或遗漏的部分，请反馈以便进一步完善说明。
