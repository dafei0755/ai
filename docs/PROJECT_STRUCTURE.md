# 项目结构说明

本目录为 LangGraph 多智能体项目分析系统的主目录。

## 📁 目录结构

```
langgraph-design/
├── intelligent_project_analyzer/   # 核心代码包
│   ├── agents/                    # 智能体实现
│   ├── api/                       # FastAPI 后端服务
│   ├── config/                    # 配置文件（YAML、角色、提示词）
│   ├── core/                      # 核心状态管理、类型定义
│   ├── frontend/                  # Streamlit 前端界面（原型版本）
│   ├── interaction/               # 人机交互节点
│   ├── knowledge_base/            # 外部知识库（本体论框架）
│   ├── report/                    # 报告生成器
│   ├── review/                    # 审核流程
│   ├── security/                  # 内容安全与领域过滤
│   ├── services/                  # LLM 工厂、工具工厂、能力边界检查 🆕
│   │   ├── demand_reconstruction_service.py         # 需求重构入口编排
│   │   ├── demand_reconstruction_context_adapter.py # 复用语义理解/分类/主矛盾生成上下文
│   │   ├── demand_reconstruction_output_planner.py  # 动态行动蓝图规划
│   │   ├── demand_reconstruction_boundary_guard.py  # 防止滑入完整任务书或伪研究
│   │   ├── scheme_advisor_entry_service.py          # 正式设计任务书一二轮追问入口
│   │   ├── capability_boundary_service.py  # 统一能力边界检查服务 (v7.117)
│   │   ├── dimension_selector.py           # 维度选择器
│   │   ├── core_task_decomposer.py         # 任务拆解器
│   │   └── ...                             # 其他服务
│   ├── tools/                     # 外部工具集成
│   ├── utils/                     # 工具函数
│   │   ├── mode_config.py         # 分析模式配置管理器 v7.110 🆕
│   │   └── ...                    # 其他工具函数
│   └── workflow/                  # LangGraph 工作流编排
│
├── config/                        # 全局配置文件 🆕
│   ├── analysis_mode.yaml         # 分析模式配置（normal/deep_thinking）v7.110 🆕
│   ├── capability_boundary_config.yaml  # 能力边界检查配置 (v7.117)
│   ├── notify.example.json
│   └── redis.conf
│
├── frontend-nextjs/               # Next.js 前端（生产版本）
│   ├── app/                       # Next.js App Router
│   ├── components/                # React 组件
│   ├── lib/                       # 工具库
│   └── types/                     # TypeScript 类型定义
│
├── tests/                         # 测试文件（集中管理）
├── scripts/                       # 独立脚本（工具、修复脚本）
├── docs/                          # 文档
│   ├── development/方案高参需求重构运行时开发纲领.md  # 当前方案高参入口开发基线
│   ├── implementation/            # 实现文档、修复记录、版本报告
│   └── guides/                    # 用户指南
├── logs/                          # 日志文件
├── reports/                       # 生成的分析报告
│
├── .env                           # 环境变量配置
├── requirements.txt               # Python 依赖
├── README.md                      # 项目说明
└── start_services.bat             # 快速启动脚本
```

## 🚀 快速开始

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

2. 配置环境变量（`.env`）：
   - `OPENAI_API_KEY` 或其他 LLM API 密钥
   - Tavily、RAGFlow 等外部工具 API 密钥

3. 启动前端：
   ```bash
   python intelligent_project_analyzer/frontend/run_frontend.py
   ```

4. 启动 API 服务：
   ```bash
   python intelligent_project_analyzer/api/server.py
   ```

5. 或使用快速启动脚本（Windows）：
   ```cmd
   start_services.bat
   ```

## 📖 核心特性

- **多智能体协作**：需求分析师、项目总监、设计总监、技术架构师、用户体验设计师、商业分析师、实施规划师
- **LangGraph 工作流**：支持动态批次执行、审核反馈循环、挑战检测
- **动态角色生成**：YAML 配置驱动的 agent 动态创建
- **人机交互**：interrupt 机制支持校准问卷、需求确认、审核反馈
- **方案高参需求重构**：模糊输入先生成行动蓝图，再无损衔接正式一二轮追问和设计任务书 2.0
- **报告生成**：文本/PDF 双格式输出，支持多轮迭代
- **内容安全**：输入/输出双重安全检查，领域适配性验证

## 📚 文档导航

- **实现文档**：`docs/implementation/`（修复记录、版本报告、技术设计）
- **方案高参入口基线**：`docs/development/方案高参需求重构运行时开发纲领.md`
- **模块化治理**：`docs/development/MODULAR_ARCHITECTURE_AND_COMPONENT_GOVERNANCE_PLAN.md`
- **模块注册表**：`docs/development/MODULE_REGISTRY.md`
- **功能版本账本**：`docs/development/FEATURE_VERSION_LEDGER.md`
- **用户指南**：`docs/guides/`（使用手册、快速入门）
- **模块说明**：各子模块的 `CLAUDE.md` 文件

## 🔧 开发说明

- **测试**：所有测试文件位于 `tests/` 目录
- **脚本**：工具脚本位于 `scripts/` 目录
- **配置**：角色配置见 `intelligent_project_analyzer/config/roles/`，提示词见 `config/prompts/`
- **知识库**：本体论框架已外部化至 `knowledge_base/ontology.yaml`，支持动态注入

## 📝 版本历史

- **v3.5**：专家协作接口、跨学科知识工具箱、锐度升级
- **v3.4**：跨学科集成、8 大项目类型全域覆盖
- **v3.3**：元框架系统、反套路思维协议
- **v3.2**：核心协议恢复、高质量示例
- **v3.0-3.1**：初始多智能体架构

---
更多详情请查看各子目录的 `CLAUDE.md` 或 `docs/implementation/` 下的实现文档。
