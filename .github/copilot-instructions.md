# Copilot Instructions for AI Agents

欢迎来到 `intelligent_project_analyzer` 项目！本说明专为 AI 编程助手（如 Copilot、GPT-4.1）设计，帮助你高效理解和贡献代码。

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
- `core/state.py`：全局状态容器
- `services/llm_factory.py`：模型实例化工厂
- `report/result_aggregator.py`：LLM 驱动结果聚合
- `frontend/app.py`：Streamlit 主界面
- `api/server.py`：FastAPI 服务主入口
- `config/roles/`、`config/prompts/`：角色与提示词配置

## 代码风格与模式
- **强类型/Pydantic**：数据结构统一用 Pydantic
- **职责分明**：每个模块有独立 CLAUDE.md 说明职责与接口
- **YAML 配置驱动**：角色、提示词、策略均可通过 YAML 动态加载

---
如有不清楚或遗漏的部分，请反馈以便进一步完善说明。
