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
UNDERSTANDING_UNAVAILABLE -> HTTP 503
SYNTHESIS_UNAVAILABLE -> HTTP 503
```

不得静默退回旧规则蓝图。规则蓝图只允许作为显式资产扫描、非 required 模式或 LLM 关闭时的受控路径。

### 权威文件

```text
intelligent_project_analyzer/modules/demand_reconstruction/contracts.py
intelligent_project_analyzer/modules/demand_reconstruction/semantic_router.py
intelligent_project_analyzer/modules/demand_reconstruction/synthesis.py
intelligent_project_analyzer/modules/demand_reconstruction/governance.py
intelligent_project_analyzer/services/demand_reconstruction_service.py
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
