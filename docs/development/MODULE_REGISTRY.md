# 模块注册表

版本：v1.0
日期：2026-06-20
状态：active registry

本文件记录项目核心模块的权威边界。它不是目录清单，而是开发治理入口：任何核心能力修改，必须先找到对应 `module_id`，确认版本、边界、依赖、守护测试和回退目标。

规则来源：

```text
docs/development/MODULAR_ARCHITECTURE_AND_COMPONENT_GOVERNANCE_PLAN.md
docs/development/FEATURE_VERSION_CHAIN_PROTOCOL.md
docs/development/FEATURE_VERSION_LEDGER.md
```

## 状态说明

```text
implemented: 已有权威版本和守护测试。
governed: 已登记模块边界，但版本链或测试仍需补齐。
candidate: 已识别为模块化候选，等待边界确认。
deprecated: 不再作为新开发入口。
```

## 1. demand-reconstruction

```text
module_id: demand-reconstruction
name: 方案高参需求重构
status: implemented
current_version: v1.4-llm-first-typed-unavailability
feature_ledger: docs/development/FEATURE_VERSION_LEDGER.md#1-demand-reconstruction
```

### owned_paths

```text
intelligent_project_analyzer/services/demand_reconstruction_service.py  # compatibility import path
intelligent_project_analyzer/services/demand_reconstruction_context_adapter.py
intelligent_project_analyzer/services/demand_reconstruction_output_planner.py
intelligent_project_analyzer/services/demand_reconstruction_boundary_guard.py
intelligent_project_analyzer/services/demand_reconstruction_insight_quality.py
intelligent_project_analyzer/services/demand_reconstruction_latent_model.py
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
intelligent_project_analyzer/api/dual_mode_routes.py
docs/mechanism-reviews/DEMAND_RECONSTRUCTION_LLM_FIRST_ARCHITECTURE.md
docs/development/方案高参需求重构运行时开发纲领.md
```

### public_contracts

```text
用户输入必须先进入需求重构入口。
当 DEMAND_RECONSTRUCTION_USE_LLM=1 时，采用 LLM-first。
DemandReconstructionUnavailable 是 typed unavailability 的权威异常类型。
UNDERSTANDING_UNAVAILABLE -> HTTP 503。
SYNTHESIS_UNAVAILABLE -> HTTP 503。
不得静默退回旧规则蓝图。
```

### entrypoints

```text
intelligent_project_analyzer.modules.demand_reconstruction.service.DemandReconstructionService
intelligent_project_analyzer.services.demand_reconstruction_service.DemandReconstructionService  # compatibility import path
intelligent_project_analyzer.api.dual_mode_routes.post_conversation_message
```

### dependencies

```text
llm-runtime
project-type-detection
knowledge-governance
scheme-advisor-entry
```

### guard_tests

```text
tests/unit/test_demand_reconstruction_llm_first_contract_guard.py
tests/services/test_demand_reconstruction_service.py
tests/api/test_scheme_advisor_entry_route.py
```

### next_refactor_target

```text
service.py 已提取为需求重构 canonical service 入口。
contracts.py 已提取为模块合同入口。
semantic_router.py 已提取为 Stage 1 LLM 语义理解入口。
synthesis.py 已提取为 Stage 5 LLM Final Synthesis 入口。
governance.py 已提取为治理知识资产注入与治理信号持久化入口。
alignment_gate.py 已提取为语义一致性 shadow/hard gate 与 fallback rebuild 入口。
compatibility.py 已提取为旧 DemandReconstructionService 私有兼容方法实现入口。
insight_quality_gate.py 已提取为洞察质量评估与质量治理信号入口。
response_builder.py 已提取为 reply/card/context/result 构建入口。
runtime_factory.py 已提取为需求重构运行时依赖装配入口。
semantic_context_applier.py 已提取为 LLM semantic package 到 adapter_context 的应用入口。
semantic_targets.py 已提取为 LLM semantic target alias 配置入口。
blueprint_coordinator.py 已提取为规则计划、LLM synthesis 与 required-LLM 失败契约的编排入口。
conversation_handler.py 已提取为 pending guidance card、handoff 与 continue 会话入口处理。
entry_classifier.py 已提取为需求重构入口判断、正式任务书请求识别与 follow-up 识别入口。
pipeline.py 已提取为需求重构运行时主流程入口。
下一步继续减少 canonical service 中旧私有兼容方法数量。
旧 services/demand_reconstruction_service.py 已收敛为兼容导出 facade。
```

## 2. project-type-detection

```text
module_id: project-type-detection
name: 项目类型检测与空间分类
status: governed
current_version: v0.1-governed-contract
```

### owned_paths

```text
intelligent_project_analyzer/modules/project_type/contracts.py
intelligent_project_analyzer/modules/project_type/registry_audit.py
intelligent_project_analyzer/services/project_type_detector.py
intelligent_project_analyzer/utils/ontology_loader.py
intelligent_project_analyzer/config/registries/
```

### public_contracts

```text
负责识别 project_type、space_type、subdomain、ontology focus。
不得直接生成最终方案建议。
不得绕过需求重构入口成为新对话第一响应主线。
分类结果应作为上下文，不应替代 LLM-first 需求洞察。
在需求重构 required-LLM 链路中，ProjectTypeDetector 不得通过构造期副作用早于 LLM Semantic Router 初始化或执行；只能在 adapter context build 阶段作为辅助证据。
```

### entrypoints

```text
ProjectTypeDetector
ontology_loader.get_layered_ontology
modules.project_type.contracts.project_type_detection_contract
modules.project_type.registry_audit.audit_project_type_registries
```

### dependencies

```text
knowledge-governance
llm-runtime
```

### guard_tests

```text
tests/unit/test_project_type_module_contract_guard.py
tests/api/test_scheme_advisor_entry_route.py::test_required_llm_route_invokes_semantic_router_before_project_type_detector
项目类型检测不应抢占 LLM-first 新对话入口。
strict registry audit 中 registry 缺失或 YAML 解析失败必须显式报错，不得在治理验证中静默退化。
```

### next_refactor_target

```text
登记 FEATURE_VERSION_LEDGER 版本链。
contracts.py 已建立为项目类型检测模块合同入口。
修正不存在的 config/project_type_registry_meta.yaml 权威路径，当前以 PROJECT_TYPE_REGISTRY 与 registries 目录为真实权威。
route-level guard 已补，证明 required LLM 入口先调用 LLM Semantic Router，再初始化 ProjectTypeDetector。
strict registry audit 已补，运行时容错和 CI/治理显式失败分层处理。
```

## 3. scheme-advisor-entry

```text
module_id: scheme-advisor-entry
name: 方案高参正式入口与任务书追问
status: governed
current_version: v0.1-demand-reconstruction-handoff-contract
```

### owned_paths

```text
intelligent_project_analyzer/modules/scheme_advisor/contracts.py
intelligent_project_analyzer/services/scheme_advisor_entry_service.py
intelligent_project_analyzer/config/scheme_advisor_version_tiers.yaml
intelligent_project_analyzer/config/scheme_advisor_entry_copy.yaml
intelligent_project_analyzer/interaction/
```

### public_contracts

```text
正式任务书追问必须发生在需求重构之后。
round 1 / round 2 问题卡不得替代需求洞察。
版本选择卡只负责任务书档位选择，不负责改写需求重构结论。
公共 /conversation/message 路由进入正式 intake 必须先经过 DemandReconstructionService；正式 handoff 由 demand_reconstruction_context.handoff_requested 触发。
直接调用 SchemeAdvisorEntryService 的 fresh start 只作为内部兼容面，不代表公共产品入口可以绕过需求重构。
```

### entrypoints

```text
SchemeAdvisorEntryService
modules.scheme_advisor.contracts.scheme_advisor_entry_contract
```

### dependencies

```text
demand-reconstruction
project-type-detection
knowledge-governance
conversation-analysis-ui
```

### guard_tests

```text
tests/api/test_scheme_advisor_entry_route.py
tests/unit/test_scheme_advisor_entry_module_contract_guard.py
需求重构完成前不得进入正式 intake。
```

### next_refactor_target

```text
contracts.py 已建立，明确 Demand Reconstruction Handoff 输入结构。
FEATURE_VERSION_LEDGER 已登记 v0.1-demand-reconstruction-handoff-contract。
```

## 4. knowledge-governance

```text
module_id: knowledge-governance
name: 知识资产治理、候选、审核、批准与审计
status: governed
current_version: v0.1-governed-contract
```

### owned_paths

```text
intelligent_project_analyzer/modules/knowledge_governance/contracts.py
intelligent_project_analyzer/services/knowledge_governance_store.py
intelligent_project_analyzer/services/knowledge_asset_draft_generation.py
intelligent_project_analyzer/services/approved_knowledge_card_service.py
intelligent_project_analyzer/api/routes/advisor_knowledge_asset_drafts.py
```

### public_contracts

```text
上传或生成的知识资产不得直接改写 classification 或 ontology。
资产进入知识库前，应生成候选、审核、批准、审计。
治理模块不得承担运行时卡片排序和召回结果组装。
治理队列必须保留 tenant/workspace/user 边界。
```

### entrypoints

```text
KnowledgeGovernanceStore
modules.knowledge_governance.contracts.knowledge_governance_contract
advisor_knowledge_asset_drafts routes
```

### dependencies

```text
project-type-detection
scheme-advisor-entry
llm-runtime
```

### guard_tests

```text
tests/services/test_knowledge_asset_draft_generation.py
tests/api/test_advisor_knowledge_asset_draft_routes.py
tests/unit/test_knowledge_module_contract_guard.py
资产不得直接改 classification / ontology 的 contract guard。
```

### next_refactor_target

```text
contracts.py 已建立为知识治理模块合同入口。
拆分 store.py、review_queue.py、audit.py。
FEATURE_VERSION_LEDGER 已登记 v0.1-governed-contract。
```

## 5. knowledge-recall

```text
module_id: knowledge-recall
name: 知识资产运行时召回
status: governed
current_version: v0.1-readonly-runtime-contract
```

### owned_paths

```text
intelligent_project_analyzer/modules/knowledge_recall/contracts.py
intelligent_project_analyzer/services/knowledge_asset_runtime.py
intelligent_project_analyzer/services/knowledge_asset_registry.py
intelligent_project_analyzer/services/governed_knowledge_retrieval.py
intelligent_project_analyzer/services/knowledge_package_registry.py
intelligent_project_analyzer/knowledge_base/
```

### public_contracts

```text
只读取 approved knowledge cards 与 package/dimension indexes。
运行时召回可以过滤 allowed_use、not_allowed_use、evidence_level，并返回 retrieval_trace。
不得创建草稿、发布 approved card、写审核队列、改 classification 或 ontology。
```

### entrypoints

```text
resolve_governed_knowledge_cards
GovernedKnowledgeRetrievalService
KnowledgePackageRegistry.build_search_context
modules.knowledge_recall.contracts.knowledge_recall_contract
```

### dependencies

```text
knowledge-governance
project-type-detection
ontology
```

### guard_tests

```text
tests/unit/test_knowledge_module_contract_guard.py
tests/unit/test_demand_reconstruction_governed_knowledge_matching.py
```

### next_refactor_target

```text
建立 retrieval policy 类型。
补 approved-card index 严格审计。
将 file-backed registry 与 DB-backed approved card 来源统一到只读 repository 接口。
```

## 6. llm-runtime

```text
module_id: llm-runtime
name: LLM provider、fallback、diagnostics 与可用性合同
status: governed
current_version: v0.1-provider-fallback-contract
```

### owned_paths

```text
intelligent_project_analyzer/modules/llm_runtime/contracts.py
intelligent_project_analyzer/services/llm_factory.py
intelligent_project_analyzer/services/multi_llm_factory.py
intelligent_project_analyzer/services/demand_reconstruction_llm.py
scripts/smoke_demand_reconstruction_llm.py
```

### public_contracts

```text
provider 可达不等于输出可用。
llm_partial 不能在 required 模式下被当成最终成功。
fallback 必须记录 llm_status、llm_error、llm_rejection_reason。
required LLM 失败必须交给上层 typed_unavailability_http_503 合同处理，不得静默转规则结果。
```

### entrypoints

```text
LLMFactory
FallbackLLM / multi provider factory
create_demand_reconstruction_llm
describe_demand_reconstruction_llm_config
modules.llm_runtime.contracts.llm_runtime_contract
```

### dependencies

```text
无上层依赖；被 demand-reconstruction、project-type-detection、knowledge-governance、knowledge-recall 调用。
```

### guard_tests

```text
tests/unit/test_llm_fallback_priority.py
tests/unit/services/test_multi_llm_fallback_auth_policy.py
tests/unit/test_demand_reconstruction_llm.py
tests/unit/test_llm_runtime_module_contract_guard.py
```

### next_refactor_target

```text
contracts.py 已建立为 LLM runtime 模块合同入口。
把 provider diagnostics 统一为结构化类型。
登记 FEATURE_VERSION_LEDGER 版本链。
```

## 7. conversation-analysis-ui

```text
module_id: conversation-analysis-ui
name: 分析页对话 UI 与引导卡交互
status: governed
current_version: v0.1-feature-boundary-contract
```

### owned_paths

```text
frontend-nextjs/features/conversation/contracts.ts
frontend-nextjs/app/analysis/[sessionId]/page.tsx
frontend-nextjs/components/ConversationMode/ConversationChat.tsx
frontend-nextjs/components/ConversationMode/GuidanceCard.tsx
frontend-nextjs/lib/api.ts
frontend-nextjs/types/
```

### public_contracts

```text
页面只负责 session 加载、布局和 feature 组合。
ConversationChat 不应无限膨胀为所有卡片类型的唯一实现。
引导卡、候选卡、版本选择卡需要可独立测试。
前端展示不得泄露内部机制术语。
后端内部信号必须翻译为用户可理解的前端标签。
```

### entrypoints

```text
frontend-nextjs/app/analysis/[sessionId]/page.tsx
ConversationChat
GuidanceCardWidget
```

### dependencies

```text
demand-reconstruction
scheme-advisor-entry
frontend api client
```

### guard_tests

```text
frontend-nextjs/features/conversation/contracts.test.ts
frontend-nextjs/components/ConversationMode/ConversationChat.test.tsx
frontend-nextjs/components/ConversationMode/GuidanceCard.test.tsx
```

### next_refactor_target

```text
contracts.ts 已建立为 conversation-analysis-ui 模块合同入口。
提取 features/conversation/types.ts。
提取 card renderer 子组件。
提取 conversation hooks。
ConversationChat 保留为组合容器。
```

## 8. 新模块登记模板

```text
module_id:
name:
status: candidate
authoritative_version:
feature_ledger:
owned_paths:
public_contracts:
entrypoints:
dependencies:
guard_tests:
rollback_target:
next_refactor_target:
```
