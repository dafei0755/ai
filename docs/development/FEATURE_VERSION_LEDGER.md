# 功能版本账本

版本：v1.0
日期：2026-06-20
状态：active index

本账本记录核心功能的当前权威版本链。它用于回答一个问题：某个机制现在到底以哪个版本、哪个分支、哪个提交为准。

规则详见：

```text
docs/development/FEATURE_VERSION_CHAIN_PROTOCOL.md
```

## 1. Demand Reconstruction

```text
feature_id: demand-reconstruction
name: 方案高参需求重构
status: implemented
current_authoritative_version: v1.4-llm-first-typed-unavailability
authoritative_branch: fix/scheme-advisor-question-root-cause-20260616
authoritative_commit: 1da451d
previous_authoritative_commit: be51dbd
rollback_target: be51dbd
last_promotion: 2026-06-20
```

### 版本链

```text
v1.0: 规则蓝图机制
v1.1: 强制需求重构入口
v1.2: LLM 参与洞察
v1.3: LLM-first 理解层恢复到当前权威分支
v1.4: typed 503 不可用合同与防回退守护测试
```

### 当前合同

```text
用户输入
-> DemandReconstructionService
-> LLM Semantic Router
-> asset/rule scan
-> LLM Final Synthesis
-> quality/alignment gates
```

当 `DEMAND_RECONSTRUCTION_USE_LLM=1` 时：

```text
DemandReconstructionUnavailable -> typed unavailability exception
UNDERSTANDING_UNAVAILABLE -> HTTP 503
SYNTHESIS_UNAVAILABLE -> HTTP 503
```

不得静默退回旧规则蓝图。规则蓝图只允许作为显式资产扫描、非 required 模式或 LLM 关闭时的受控路径。

`DEMAND_RECONSTRUCTION_USE_LLM=1` 时，项目类型检测不得在需求重构构造期抢占链路；ProjectTypeDetector / SpaceClassification 只能在 LLM Semantic Router 之后作为 adapter context 证据进入。

### 权威文件

```text
intelligent_project_analyzer/modules/demand_reconstruction/contracts.py
intelligent_project_analyzer/modules/demand_reconstruction/service.py
intelligent_project_analyzer/modules/demand_reconstruction/semantic_router.py
intelligent_project_analyzer/modules/demand_reconstruction/synthesis.py
intelligent_project_analyzer/modules/demand_reconstruction/governance.py
intelligent_project_analyzer/modules/demand_reconstruction/alignment_gate.py
intelligent_project_analyzer/modules/demand_reconstruction/compatibility.py
intelligent_project_analyzer/modules/demand_reconstruction/insight_quality_gate.py
intelligent_project_analyzer/modules/demand_reconstruction/response_builder.py
intelligent_project_analyzer/modules/demand_reconstruction/runtime_factory.py
intelligent_project_analyzer/modules/demand_reconstruction/semantic_context_applier.py
intelligent_project_analyzer/modules/demand_reconstruction/semantic_targets.py
intelligent_project_analyzer/modules/demand_reconstruction/blueprint_coordinator.py
intelligent_project_analyzer/modules/demand_reconstruction/conversation_handler.py
intelligent_project_analyzer/modules/demand_reconstruction/entry_classifier.py
intelligent_project_analyzer/modules/demand_reconstruction/pipeline.py
intelligent_project_analyzer/services/demand_reconstruction_service.py  # compatibility import path
intelligent_project_analyzer/api/dual_mode_routes.py
docs/mechanism-reviews/DEMAND_RECONSTRUCTION_LLM_FIRST_ARCHITECTURE.md
docs/development/方案高参需求重构运行时开发纲领.md
```

### 守护测试

```text
tests/unit/test_demand_reconstruction_llm_first_contract_guard.py
tests/services/test_demand_reconstruction_service.py
tests/api/test_scheme_advisor_entry_route.py
```

推荐验证：

```powershell
.\.conda\python.exe -m pytest tests/services/test_demand_reconstruction_service.py tests/api/test_scheme_advisor_entry_route.py tests/unit/test_demand_reconstruction_llm_first_contract_guard.py -q
```

### 风险备注

```text
backup/* 分支中存在过 LLM-first 快照，但 backup 分支不代表已实施。
需求重构相关修改必须更新本账本，否则不能宣称形成新版本。
```

## 2. Project Type Detection

```text
feature_id: project-type-detection
name: 项目类型检测与空间分类
status: governed
current_authoritative_version: v0.1-governed-contract
authoritative_branch: fix/scheme-advisor-question-root-cause-20260616
authoritative_commit: current-branch-head-after-checkpoint
previous_authoritative_commit: unregistered
rollback_target: branch head before v0.1-governed-contract checkpoint
last_promotion: 2026-06-20
```

### 版本链

```text
v0.1: 建立模块合同，明确 ProjectTypeDetector 是分类上下文服务，不是新对话第一响应主线。
```

### 当前合同

```text
用户输入
-> DemandReconstructionService
-> LLM Semantic Router
-> adapter context build
-> ProjectTypeDetector / SpaceClassificationService 作为上下文证据
```

项目类型检测负责识别 `project_type`、`space_type`、`subdomain`、`ontology focus`，不得直接生成最终方案建议，不得绕过需求重构入口成为新对话第一响应主线。

当前可验证权威源：

```text
intelligent_project_analyzer/modules/project_type/contracts.py
intelligent_project_analyzer/modules/project_type/registry_audit.py
intelligent_project_analyzer/services/project_type_detector.py
intelligent_project_analyzer/config/registries/
intelligent_project_analyzer/utils/ontology_loader.py
```

### 守护测试

```text
tests/unit/test_project_type_module_contract_guard.py
tests/api/test_scheme_advisor_entry_route.py::test_required_llm_route_invokes_semantic_router_before_project_type_detector
```

推荐验证：

```powershell
.\.conda\python.exe -m pytest tests/unit/test_project_type_module_contract_guard.py tests/services/test_space_classification_registry_externalization.py tests/api/test_scheme_advisor_entry_route.py -q
```

## 3. Knowledge Governance

```text
feature_id: knowledge-governance
name: 知识资产治理、候选、审核、批准与审计
status: governed
current_authoritative_version: v0.1-governed-contract
authoritative_branch: fix/scheme-advisor-question-root-cause-20260616
authoritative_commit: current-branch-head-after-checkpoint
previous_authoritative_commit: unregistered
rollback_target: branch head before v0.1-governed-contract checkpoint
last_promotion: 2026-06-20
```

### 当前合同

```text
knowledge asset input
-> draft / learning candidate
-> review queue
-> approved card publication
-> audit event
```

治理模块不得直接改写 classification、ontology，也不得承担运行时卡片排序和召回结果组装。

### 权威文件

```text
intelligent_project_analyzer/modules/knowledge_governance/contracts.py
intelligent_project_analyzer/services/knowledge_governance_store.py
intelligent_project_analyzer/services/knowledge_asset_draft_generation.py
intelligent_project_analyzer/services/approved_knowledge_card_service.py
intelligent_project_analyzer/api/routes/advisor_knowledge_asset_drafts.py
```

### 守护测试

```text
tests/unit/test_knowledge_module_contract_guard.py
tests/unit/services/test_knowledge_governance_store_review_items.py
tests/unit/services/test_knowledge_asset_review_service.py
```

## 4. Knowledge Recall

```text
feature_id: knowledge-recall
name: 知识资产运行时召回
status: governed
current_authoritative_version: v0.1-readonly-runtime-contract
authoritative_branch: fix/scheme-advisor-question-root-cause-20260616
authoritative_commit: current-branch-head-after-checkpoint
previous_authoritative_commit: unregistered
rollback_target: branch head before v0.1-readonly-runtime-contract checkpoint
last_promotion: 2026-06-20
```

### 当前合同

```text
runtime context / package ids / ontology dimension ids
-> approved-card lookup
-> allowed_use / not_allowed_use / evidence filtering
-> cards + graph_context + retrieval_trace + policy
```

召回模块只能读取 approved knowledge cards，不得创建草稿、发布 approved card、写审核队列、改 classification 或 ontology。

### 权威文件

```text
intelligent_project_analyzer/modules/knowledge_recall/contracts.py
intelligent_project_analyzer/services/knowledge_asset_runtime.py
intelligent_project_analyzer/services/knowledge_asset_registry.py
intelligent_project_analyzer/services/governed_knowledge_retrieval.py
intelligent_project_analyzer/services/knowledge_package_registry.py
intelligent_project_analyzer/knowledge_base/
```

### 守护测试

```text
tests/unit/test_knowledge_module_contract_guard.py
tests/unit/test_demand_reconstruction_governed_knowledge_matching.py
```

推荐验证：

```powershell
.\.conda\python.exe -m pytest tests/unit/test_knowledge_module_contract_guard.py tests/unit/test_demand_reconstruction_governed_knowledge_matching.py tests/unit/services/test_knowledge_governance_store_review_items.py tests/unit/services/test_knowledge_asset_review_service.py -q
```

## 5. LLM Runtime

```text
feature_id: llm-runtime
name: LLM provider、fallback、diagnostics 与可用性合同
status: governed
current_authoritative_version: v0.1-provider-fallback-contract
authoritative_branch: fix/scheme-advisor-question-root-cause-20260616
authoritative_commit: current-branch-head-after-checkpoint
previous_authoritative_commit: unregistered
rollback_target: branch head before v0.1-provider-fallback-contract checkpoint
last_promotion: 2026-06-20
```

### 当前合同

```text
provider config / fallback chain
-> provider invocation
-> diagnostics
-> success response OR typed required-mode failure
```

`provider ready` 不等于业务输出成功。`llm_partial`、`semantic_fallback`、`llm_failed` 不得在 required LLM 模式下被当成最终成功；required 模式失败必须由需求重构合同映射到 typed HTTP 503。

### 权威文件

```text
intelligent_project_analyzer/modules/llm_runtime/contracts.py
intelligent_project_analyzer/services/llm_factory.py
intelligent_project_analyzer/services/multi_llm_factory.py
intelligent_project_analyzer/services/demand_reconstruction_llm.py
scripts/smoke_demand_reconstruction_llm.py
```

### 守护测试

```text
tests/unit/test_llm_runtime_module_contract_guard.py
tests/unit/test_llm_fallback_priority.py
tests/unit/services/test_multi_llm_fallback_auth_policy.py
tests/unit/test_demand_reconstruction_llm.py
```

推荐验证：

```powershell
.\.conda\python.exe -m pytest tests/unit/test_llm_runtime_module_contract_guard.py tests/unit/test_llm_fallback_priority.py tests/unit/services/test_multi_llm_fallback_auth_policy.py tests/unit/test_demand_reconstruction_llm.py -q
```

## 6. Scheme Advisor Entry

```text
feature_id: scheme-advisor-entry
name: 方案高参正式入口与任务书追问
status: governed
current_authoritative_version: v0.1-demand-reconstruction-handoff-contract
authoritative_branch: fix/scheme-advisor-question-root-cause-20260616
authoritative_commit: current-branch-head-after-checkpoint
previous_authoritative_commit: unregistered
rollback_target: branch head before v0.1-demand-reconstruction-handoff-contract checkpoint
last_promotion: 2026-06-20
```

### 当前合同

```text
public conversation message
-> DemandReconstructionService
-> demand_reconstruction_context.handoff_requested
-> SchemeAdvisorEntryService
-> round_1 / round_2 / stage conclusion / version selection
```

正式任务书追问必须发生在需求重构之后。round 1 / round 2 问题卡不得替代需求洞察；版本选择卡只负责任务书档位选择，不负责改写需求重构结论。

### 权威文件

```text
intelligent_project_analyzer/modules/scheme_advisor/contracts.py
intelligent_project_analyzer/services/scheme_advisor_entry_service.py
intelligent_project_analyzer/config/scheme_advisor_version_tiers.yaml
intelligent_project_analyzer/config/scheme_advisor_entry_copy.yaml
intelligent_project_analyzer/api/dual_mode_routes.py
```

### 守护测试

```text
tests/unit/test_scheme_advisor_entry_module_contract_guard.py
tests/api/test_scheme_advisor_entry_route.py
tests/services/test_scheme_advisor_entry_v2_restore.py
```

推荐验证：

```powershell
.\.conda\python.exe -m pytest tests/unit/test_scheme_advisor_entry_module_contract_guard.py tests/api/test_scheme_advisor_entry_route.py tests/services/test_scheme_advisor_entry_v2_restore.py -q
```

## 7. Conversation Analysis UI

```text
feature_id: conversation-analysis-ui
name: 分析页对话 UI 与引导卡交互
status: governed
current_authoritative_version: v0.2-conversation-types-extracted
authoritative_branch: fix/scheme-advisor-question-root-cause-20260616
authoritative_commit: current-branch-head-after-checkpoint
previous_authoritative_commit: unregistered
rollback_target: branch head before v0.2-conversation-types-extracted checkpoint
last_promotion: 2026-06-20
```

### 版本链

```text
v0.1: 前端模块边界合同与守护测试
v0.2: conversation types 从 ConversationChat 抽取到 feature 层，并保留兼容导出
```

### 当前合同

```text
analysis session page
-> ConversationChat composition shell
-> GuidanceCard / CandidateCard / scheme version card
-> user-facing response callback
```

分析页负责 session 加载、布局和 feature 组合；ConversationChat 保留为对话组合容器；引导卡、候选卡和版本选择卡必须保持可独立测试。后端内部字段和机制信号必须在前端翻译为用户可理解的标签。

### 权威文件

```text
frontend-nextjs/features/conversation/contracts.ts
frontend-nextjs/features/conversation/types.ts
frontend-nextjs/app/analysis/[sessionId]/page.tsx
frontend-nextjs/components/ConversationMode/ConversationChat.tsx
frontend-nextjs/components/ConversationMode/GuidanceCard.tsx
frontend-nextjs/lib/api.ts
frontend-nextjs/types/
```

### 守护测试

```text
frontend-nextjs/features/conversation/contracts.test.ts
frontend-nextjs/components/ConversationMode/ConversationChat.test.tsx
frontend-nextjs/components/ConversationMode/GuidanceCard.test.tsx
```

推荐验证：

```powershell
cd frontend-nextjs
npm test -- ConversationChat.test.tsx GuidanceCard.test.tsx features/conversation/contracts.test.ts
```
