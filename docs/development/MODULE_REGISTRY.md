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
intelligent_project_analyzer/services/demand_reconstruction_service.py
intelligent_project_analyzer/services/demand_reconstruction_context_adapter.py
intelligent_project_analyzer/services/demand_reconstruction_output_planner.py
intelligent_project_analyzer/services/demand_reconstruction_boundary_guard.py
intelligent_project_analyzer/services/demand_reconstruction_insight_quality.py
intelligent_project_analyzer/services/demand_reconstruction_latent_model.py
intelligent_project_analyzer/api/dual_mode_routes.py
docs/mechanism-reviews/DEMAND_RECONSTRUCTION_LLM_FIRST_ARCHITECTURE.md
docs/development/方案高参需求重构运行时开发纲领.md
```

### public_contracts

```text
用户输入必须先进入需求重构入口。
当 DEMAND_RECONSTRUCTION_USE_LLM=1 时，采用 LLM-first。
UNDERSTANDING_UNAVAILABLE -> HTTP 503。
SYNTHESIS_UNAVAILABLE -> HTTP 503。
不得静默退回旧规则蓝图。
```

### entrypoints

```text
intelligent_project_analyzer.services.demand_reconstruction_service.DemandReconstructionService
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
提取 intelligent_project_analyzer/modules/demand_reconstruction/contracts.py。
提取 semantic_router.py 和 synthesis.py。
旧 services/demand_reconstruction_service.py 保留兼容 facade。
```

## 2. project-type-detection

```text
module_id: project-type-detection
name: 项目类型检测与空间分类
status: governed
current_version: unregistered
```

### owned_paths

```text
intelligent_project_analyzer/services/project_type_detector.py
intelligent_project_analyzer/utils/ontology_loader.py
intelligent_project_analyzer/config/registries/
config/project_type_registry_meta.yaml
```

### public_contracts

```text
负责识别 project_type、space_type、subdomain、ontology focus。
不得直接生成最终方案建议。
不得绕过需求重构入口成为新对话第一响应主线。
分类结果应作为上下文，不应替代 LLM-first 需求洞察。
```

### entrypoints

```text
ProjectTypeDetector
ontology_loader.get_layered_ontology
```

### dependencies

```text
knowledge-governance
llm-runtime
```

### guard_tests

```text
待补齐：项目类型检测不应抢占 LLM-first 新对话入口。
待补齐：registry 解析失败必须显式报错，不得静默退化为错误类型。
```

### next_refactor_target

```text
登记 FEATURE_VERSION_LEDGER 版本链。
建立 contracts.py，明确 classification package 字段。
补 route-level guard，证明新对话入口不会先产出项目类型检测器响应。
```

## 3. scheme-advisor-entry

```text
module_id: scheme-advisor-entry
name: 方案高参正式入口与任务书追问
status: governed
current_version: unregistered
```

### owned_paths

```text
intelligent_project_analyzer/services/scheme_advisor_entry_service.py
intelligent_project_analyzer/services/scheme_version_selection.py
intelligent_project_analyzer/interaction/
```

### public_contracts

```text
正式任务书追问必须发生在需求重构之后。
round 1 / round 2 问题卡不得替代需求洞察。
版本选择卡只负责任务书档位选择，不负责改写需求重构结论。
```

### entrypoints

```text
SchemeAdvisorEntryService
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
待补齐：需求重构完成前不得进入正式 intake。
```

### next_refactor_target

```text
补 contracts.py，明确 Demand Reconstruction Handoff 输入结构。
登记 FEATURE_VERSION_LEDGER 版本链。
```

## 4. knowledge-governance

```text
module_id: knowledge-governance
name: 知识资产治理、候选、审核与运行时召回
status: governed
current_version: unregistered
```

### owned_paths

```text
intelligent_project_analyzer/services/knowledge_governance_store.py
intelligent_project_analyzer/services/knowledge_asset_draft_generation.py
intelligent_project_analyzer/api/routes/advisor_knowledge_asset_drafts.py
intelligent_project_analyzer/knowledge_base/
```

### public_contracts

```text
上传或生成的知识资产不得直接改写 classification 或 ontology。
资产进入知识库后，应生成候选、审核、批准、审计，再进入运行时召回。
治理队列必须保留 tenant/workspace/user 边界。
```

### entrypoints

```text
KnowledgeGovernanceStore
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
待补齐：资产不得直接改 classification / ontology 的 contract guard。
```

### next_refactor_target

```text
拆分 store.py、review_queue.py、audit.py。
登记 FEATURE_VERSION_LEDGER 版本链。
```

## 5. llm-runtime

```text
module_id: llm-runtime
name: LLM provider、fallback、diagnostics 与可用性合同
status: governed
current_version: unregistered
```

### owned_paths

```text
intelligent_project_analyzer/services/llm_factory.py
intelligent_project_analyzer/services/multi_llm_factory.py
scripts/smoke_llm_channels.py
scripts/smoke_demand_reconstruction_llm.py
```

### public_contracts

```text
provider 可达不等于输出可用。
llm_partial 不能在 required 模式下被当成最终成功。
fallback 必须记录 llm_status、llm_error、llm_rejection_reason。
```

### entrypoints

```text
LLMFactory
FallbackLLM / multi provider factory
```

### dependencies

```text
无上层依赖；被 demand-reconstruction、project-type-detection、knowledge-governance 调用。
```

### guard_tests

```text
tests/unit/test_llm_fallback_priority.py
tests/unit/services/test_multi_llm_fallback_auth_policy.py
tests/unit/test_demand_reconstruction_llm.py
```

### next_refactor_target

```text
建立 modules/llm_runtime/contracts.py。
把 provider diagnostics 统一为结构化类型。
登记 FEATURE_VERSION_LEDGER 版本链。
```

## 6. conversation-analysis-ui

```text
module_id: conversation-analysis-ui
name: 分析页对话 UI 与引导卡交互
status: governed
current_version: unregistered
```

### owned_paths

```text
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
```

### entrypoints

```text
frontend-nextjs/app/analysis/[sessionId]/page.tsx
ConversationChat
```

### dependencies

```text
demand-reconstruction
scheme-advisor-entry
frontend api client
```

### guard_tests

```text
待补齐：ConversationChat 主交互路径测试。
待补齐：版本选择卡、GuidanceCard structured response 测试。
```

### next_refactor_target

```text
提取 features/conversation/types.ts。
提取 card renderer 子组件。
ConversationChat 保留为组合容器。
```

## 7. 新模块登记模板

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