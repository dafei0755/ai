# 模块化架构与组件治理实施计划

版本：v1.0
日期：2026-06-20
状态：active plan

## 1. 目标

本计划把项目从“按文件和临时任务推进”升级为“按模块、合同、版本链推进”。目标不是一次性大搬家，而是让每个核心能力都具备：

```text
模块边界 -> 公共合同 -> 权威入口 -> 依赖关系 -> 守护测试 -> 版本链 -> 回退路径
```

本计划与以下规则共同生效：

```text
docs/development/FEATURE_VERSION_CHAIN_PROTOCOL.md
docs/development/FEATURE_VERSION_LEDGER.md
docs/development/CHANGE_SAFETY_AND_ROLLBACK_PROTOCOL.md
docs/development/MODULE_REGISTRY.md
```

## 2. 分层模型

项目按五层治理。目录可以逐步迁移，但任何新设计必须先归入以下层次：

```text
L0 产品能力层
  面向用户可感知能力：方案高参、需求重构、空间分类、知识资产、对话分析、管理后台。

L1 模块合同层
  每个能力的输入、输出、错误码、状态机、版本、权威文件、守护测试。

L2 应用编排层
  API route、service orchestration、workflow、conversation session。

L3 领域能力层
  semantic understanding、project type、ontology、governance、quality gate、asset recall。

L4 基础设施层
  LLM provider、DB、YAML registry、cache、日志、外部 API、脚本。
```

开发判断规则：

```text
API route 只做协议转换和错误映射。
Service 只做流程编排和状态衔接。
Domain 只做业务判断和合同执行。
Adapter 只做外部系统、LLM、DB、YAML、HTTP 的隔离。
```

如果一个文件同时承担三层以上职责，它就是后续拆分候选。

## 3. 目标后端结构

中期目标结构如下，先作为方向，不要求立即搬迁全部代码：

```text
intelligent_project_analyzer/
  modules/
    demand_reconstruction/
      contracts.py
      service.py
      semantic_router.py
      synthesis.py
      governance.py
      alignment_gate.py
      compatibility.py
      insight_quality_gate.py
      response_builder.py
      runtime_factory.py
      semantic_context_applier.py
      semantic_targets.py
      blueprint_coordinator.py
      conversation_handler.py
      entry_classifier.py
      pipeline.py
      quality_gate.py
      adapters.py
      version.py
      README.md

    project_type/
      contracts.py
      detector.py
      ontology.py
      registry.py
      version.py
      README.md

    scheme_advisor/
      contracts.py
      entry_service.py
      formal_intake.py
      version.py
      README.md

    knowledge_governance/
      contracts.py
      store.py
      review_queue.py
      audit.py
      version.py
      README.md

    llm_runtime/
      contracts.py
      providers.py
      fallback.py
      diagnostics.py
      version.py
      README.md

  api/
    routes/
      conversation.py
      analysis.py
      governance.py

  infrastructure/
    llm/
    db/
    yaml_registry/
    logging/
```

迁移原则：

```text
先登记模块 -> 再固化合同 -> 再补守护测试 -> 再新建 facade -> 最后迁移实现。
```

不得用“整文件覆盖”完成迁移。旧路径应先保留兼容入口，让测试和运行时逐步证明新模块有效。

## 4. 目标前端结构

前端按 feature 分层，而不是把所有业务组件放在全局 components 下：

```text
frontend-nextjs/
  features/
    analysis/
      components/
      hooks/
      api.ts
      types.ts
      version.ts

    conversation/
      components/
      hooks/
      api.ts
      types.ts
      version.ts

    governance/
      components/
      hooks/
      api.ts
      types.ts
      version.ts

  components/
    ui/
    layout/

  lib/
    api-client.ts
    runtime-config.ts

  types/
    shared.ts
```

规则：

```text
page 只做路由和组合。
feature 管理自己的业务状态、API、类型和局部组件。
components/ui 不知道业务语义。
lib 只放跨 feature 的基础能力。
```

## 5. 实施阶段

### Phase 0：建立模块治理层

交付物：

```text
docs/development/MODULAR_ARCHITECTURE_AND_COMPONENT_GOVERNANCE_PLAN.md
docs/development/MODULE_REGISTRY.md
docs/development/templates/MODULE_CONTRACT_TEMPLATE.md
```

验收标准：

```text
核心模块已经登记。
每个模块有 owned_paths、entrypoints、dependencies、guard_tests。
后续任何核心功能修改都能先找到 module_id。
```

### Phase 1：核心模块合同固化

优先模块：

```text
demand-reconstruction
project-type-detection
scheme-advisor-entry
knowledge-governance
llm-runtime
conversation-analysis-ui
```

交付物：

```text
每个模块补一份 README 或 contracts 文件。
每个模块在 FEATURE_VERSION_LEDGER.md 中有版本链。
每个模块至少一个 contract guard test 或明确的验收命令。
```

验收标准：

```text
修改模块前能知道输入、输出、错误码、守护测试和回退点。
```

### Phase 2：需求重构模块 facade

目标：把 `DemandReconstructionService` 的职责拆成可理解的子能力，但不立即破坏旧 import。

建议顺序：

```text
1. 新建 intelligent_project_analyzer/modules/demand_reconstruction/contracts.py
2. 提取 typed unavailability、状态码、核心合同常量。
3. 新建 semantic_router.py，迁移 LLM Semantic Router 的 prompt/parse/invoke 逻辑。（已完成）
4. 新建 synthesis.py，迁移 Final Synthesis 逻辑。（已完成）
5. 新建 governance.py，迁移治理知识资产注入与治理信号持久化逻辑。（已完成）
6. 新建 alignment_gate.py，迁移语义一致性 shadow/hard gate 与 fallback rebuild 逻辑。（已完成）
7. 新建 insight_quality_gate.py，迁移洞察质量评估与质量治理信号逻辑。（已完成）
8. 新建 response_builder.py，迁移 reply/card/context/result 构建逻辑。（已完成）
9. 新建 runtime_factory.py，迁移需求重构运行时依赖装配逻辑。（已完成）
10. 新建 semantic_context_applier.py，迁移 LLM semantic package 到 adapter_context 的应用逻辑。（已完成）
11. 新建 semantic_targets.py，迁移 LLM semantic target alias 配置。（已完成）
12. 新建 blueprint_coordinator.py，迁移规则计划、LLM synthesis 与 required-LLM 失败契约编排。（已完成）
13. 新建 conversation_handler.py，迁移 pending guidance card、handoff 与 continue 会话入口处理。（已完成）
14. 新建 entry_classifier.py，迁移需求重构入口判断、正式任务书请求识别与 follow-up 识别。（已完成）
15. 新建 pipeline.py，迁移需求重构运行时主流程编排。（已完成）
16. 新建 compatibility.py，迁移旧私有兼容方法实现，service.py 保留方法名薄转发。（已完成）
17. 新建 modules/demand_reconstruction/service.py 作为 canonical service，旧 services/demand_reconstruction_service.py 作为兼容 facade。（已完成）
```

验收命令：

```powershell
.\.conda\python.exe -m pytest tests/services/test_demand_reconstruction_service.py tests/api/test_scheme_advisor_entry_route.py tests/unit/test_demand_reconstruction_llm_first_contract_guard.py -q
```

### Phase 3：项目类型检测与知识资产解耦

目标：让项目类型检测、ontology、activation pack、knowledge asset recall 各自有合同，避免互相隐式写入。

原则：

```text
project_type_detection 负责识别和路由。
ontology 负责稳定提问框架。
knowledge_governance 负责候选、审核、批准、审计。
knowledge_recall 负责运行时引用，不直接改分类或本体。
```

第一步实施：

```text
1. 新建 modules/project_type/contracts.py，登记 project-type-detection 合同。
2. FEATURE_VERSION_LEDGER 登记 v0.1-governed-contract。
3. MODULE_REGISTRY 修正当前真实权威路径，移除不存在的 project_type_registry_meta.yaml 作为已实施权威。
4. 补 tests/unit/test_project_type_module_contract_guard.py，守住“分类只能作为 LLM-first 后置上下文证据”的边界。
5. 补 API 入口顺序测试，证明 required LLM 入口先调用 LLM Semantic Router，再初始化 ProjectTypeDetector。
6. 新建 modules/project_type/registry_audit.py，让 registry 缺失或 YAML 解析失败在治理验证中显式报错。
7. 新建 modules/knowledge_governance/contracts.py 与 modules/knowledge_recall/contracts.py，把候选/审核/批准/审计和只读运行时召回拆成两个模块合同。
8. 新建 modules/llm_runtime/contracts.py，明确 provider/fallback/diagnostics 与 required-mode typed failure 的合同边界。
9. 新建 modules/scheme_advisor/contracts.py，明确正式 intake 必须由需求重构 handoff 触发，round 卡不得替代需求洞察。
10. 新建 frontend-nextjs/features/conversation/contracts.ts，明确 conversation-analysis-ui 前端模块边界和守护测试。
```

### Phase 4：前端 feature 化

优先处理：

```text
frontend-nextjs/components/ConversationMode/ConversationChat.tsx
frontend-nextjs/app/analysis/[sessionId]/page.tsx
```

建议顺序：

```text
1. 先建立 conversation-analysis-ui 合同和守护测试。（已完成）
2. 提取 conversation types。（已完成）
3. 提取 card rendering 子组件。（已完成）
4. 提取 conversation composer hook。（已完成）
5. 提取 layout/context panel state。（已完成）
6. 提取 visual brief/context panel components。（已完成）
7. 提取 expert controls and summon menu。（已完成）
8. 提取 composer shell。（已完成）
9. 提取 message list shell。（已完成）
10. 提取 upgrade banner。（已完成）
11. 移除 disabled legacy advisor context block，并审计 ConversationChat 是否已满足组合容器目标。（已完成）
12. 提取 advisor context derivation。（已完成）
13. 审计 ConversationChat 是否已满足最终组合容器目标。（已完成）
14. 提取 conversation history adapter。（已完成）
15. 提取 analysis page conversation mode session bootstrap。（已完成）
16. 提取 analysis page conversation send/card-response handlers。（已完成）
17. 提取 advisor conversation local persistence。（已完成）
18. 提取 advisor history local persistence。（已完成）
19. 提取 advisor history record derivation。（已完成）
20. 提取 advisor history grouping。（已完成）
21. 提取 active advisor conversation accessors。
22. 页面只保留 session 加载、布局和 feature 组合。
```

验收：

```text
现有页面可运行。
对话消息、引导卡、候选卡、三档版本选择卡行为不变。
新增前端测试覆盖至少一个主交互路径，并由合同测试防止被移除。
```

## 6. 每次模块修改的启动模板

```text
module_id:
current_version:
target_version:
base_branch:
base_commit:
work_branch:
owned_paths:
shared_paths:
contract_change:
expected_runtime_behavior:
guard_tests:
rollback_target:
```

没有这份启动信息，不应修改核心模块。

## 7. 每次模块修改的完成模板

```text
module_id:
feature_version:
base_commit:
head_commit:
changed_paths:
contract_changed: yes/no
ledger_updated: yes/no
module_registry_updated: yes/no
verification:
rollback_target:
residual_risks:
```

## 8. 第一批实施建议

第一批不做大规模代码迁移，只做治理固化：

```text
1. 建立 MODULE_REGISTRY.md。
2. 将 demand-reconstruction 作为第一个完整模块样例。
3. 将 project-type-detection、scheme-advisor-entry、knowledge-governance、llm-runtime、conversation-analysis-ui 登记为受控模块。
4. 后续任何对这些模块的修改必须更新注册表和版本账本。
```

完成 Phase 0 后，再进入单模块 facade 迁移。
