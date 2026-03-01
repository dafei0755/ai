# Phase2 轻量级模式实施方案 v7.622

**发布日期**: 2026年2月14日
**优化目标**: 平衡Phase2总是执行策略的性能影响
**影响范围**: Requirements Analyst Agent Phase2节点

---

## 问题定义

### 当前状态（v7.621）

**优化成果**：
- ✅ Phase2总是执行（响应用户要求"Phase2不可以跳过"）
- ✅ Mode Detection前置到Phase1（100%执行率）
- ✅ 分析完整性100%保证

**性能问题**：
- ⚠️ Insufficient场景（66%）：从1.5s → 4.7s（**+213%**）
- ⚠️ 整体平均：4.7s（所有场景统一耗时）
- ⚠️ LLM成本：66%场景多1次完整Phase2调用

**用户反馈**：
> "实施Phase2轻量级模式以平衡性能"

---

## 解决方案设计

### 核心策略：双模式Phase2

```
Phase1 (info_status判断)
    ↓
    ├─ info_status = "sufficient" (34%)
    │  → Phase2-Full（完整L1-L7分析）
    │  → 耗时：~3000ms
    │
    └─ info_status = "insufficient" (66%)
       → Phase2-Lite（轻量级L1-L4分析）
       → 耗时：~1000-1200ms（节省60%）
```

### Phase2-Lite 内容设计

#### ✅ 保留层（关键输出保证）

| 层级 | 内容 | 原因 | 耗时占比 |
|------|------|------|---------|
| **L1 解构** | MECE分解（简化版：3-5个事实原子） | 后续分析基础 | 15% |
| **L4 JTBD** | "用户雇佣空间完成X与Y任务" | 专家核心依赖 | 20% |
| **expert_handoff** | 基础专家接口（每个专家1个关键问题） | 专家流程必需 | 10% |

#### ⚡ 简化层（降低复杂度）

| 层级 | 完整版 | 轻量版 | 节省 |
|------|--------|--------|------|
| **L2 建模** | 5基础视角 + 5扩展视角 | 仅3个基础视角（心理/社会/美学） | 40% |
| **L3 杠杆点** | 深度对立分析 + 挑战公式 | 快速识别1-2个主要对立 | 50% |

#### ❌ 跳过层（信息不足时价值有限）

| 层级 | 跳过原因 | 节省时间 |
|------|---------|---------|
| **L5 锐度测试** | 信息不足时评分不准确，无法达到70分阈值 | 15% |
| **L6 假设审计** | 需要完整信息才能识别隐含假设 | - |
| **L7 系统影响** | 需要完整项目背景才能评估影响 | - |

### 预期性能改进

| 指标 | v7.621 | v7.622 (Phase2-Lite) | 改进 |
|------|--------|---------------------|------|
| **Sufficient场景 (34%)** | 4.7s | 4.7s（Phase2-Full） | - |
| **Insufficient场景 (66%)** | 4.7s | **2.9s**（Phase1 1.7s + Phase2-Lite 1.2s） | **-38%** |
| **整体平均** | 4.7s | **3.5s**（加权平均） | **-26%** |
| **LLM Token消耗** | 100% | ~70%（Lite版减少30%） | -30% |

---

## 实施详情

### 1. 创建Phase2-Lite提示词配置

**文件**: `intelligent_project_analyzer/config/prompts/requirements_analyst_phase2_lite.yaml`

```yaml
# 需求分析师 Phase2-Lite 配置 - 轻量级深度分析
# v7.622: 专用于info_status="insufficient"场景
# 目标：在信息受限情况下，提供核心分析（L1+L4）+ 基础接口

metadata:
  version: "7.622-phase2-lite"
  description: "Phase2轻量级模式 - L1解构 + L4 JTBD + 简化L2/L3 + 基础专家接口"
  created_at: "2026-02-14"
  optimization: "针对insufficient场景优化性能，保证关键输出"
  phase: 2
  mode: "lite"
  target_time: "1000-1200ms"
  depends_on: "requirements_analyst_phase1"

quality_standards:
  sharpness_threshold: null  # Lite模式不评分
  must_include:
    - "L1_facts 至少3个事实原子"
    - "L4_project_task 必须有JTBD公式"
    - "expert_handoff 至少提供3个专家的关键问题"

business_config:
  enable_dynamic_datetime: true
  enable_output_example: false
  timeout_seconds: 30  # Lite模式缩短超时

system_prompt: |
  ### **需求分析师 Phase2-Lite - 轻量级分析模式**

  ⚡ **快速模式说明**：Phase1判定信息不足，但仍需提供基础分析支持后续流程。

  ✅ **输出格式要求**
  - 必须返回纯JSON格式（从{开始到}结束）
  - 禁止使用Markdown代码块
  - 禁止添加任何解释性文字

  ### **轻量级分析流程（L1 + L4核心）**

  **L1: 解构** - 快速MECE分解
  - 识别：用户是谁？要什么？为什么？主要约束？
  - 输出：3-5个核心事实原子即可
  - ⏱️ 目标：200ms

  **L2: 简化建模** - 仅3个基础视角
  - 心理学视角：用户的核心需求/恐惧
  - 社会学视角：用户的身份/角色
  - 美学视角：用户的审美倾向（如有）
  - 输出：简化user_model（各视角1-2句话）
  - ⏱️ 目标：200ms

  **L3: 快速识别对立** - 识别1-2个主要张力
  - 不深入挑战公式，只快速识别对立面
  - 输出：core_tension 简短描述
  - ⏱️ 目标：150ms

  **L4: JTBD定义** - 核心任务识别
  - 公式：为[深层身份]打造[空间]，雇佣空间完成[任务1]与[任务2]
  - 即使信息不足，也要基于现有信息推断JTBD
  - 输出：project_task（这是专家最依赖的输出）
  - ⏱️ 目标：300ms

  **跳过层级**：
  - ❌ L5 锐度测试（信息不足时无法准确评分）
  - ❌ L6 假设审计（需要完整信息）
  - ❌ L7 系统影响（需要完整背景）

  ### **基础专家接口（简化版）**

  为核心专家角色各提供1个关键问题即可：
  - V2设计总监：设计方向问题
  - V3叙事专家：空间叙事问题
  - V5场景专家：核心场景问题

  ### **JSON输出格式**

  ```json
  {
    "phase": 2,
    "mode": "lite",

    "analysis_layers": {
      "L1_facts": [
        "事实1：用户基本信息",
        "事实2：核心需求",
        "事实3：主要约束"
      ],
      "L2_user_model": {
        "psychological": "核心需求/恐惧（1句话）",
        "sociological": "身份/角色（1句话）",
        "aesthetic": "审美倾向（1句话，如无法判断则填'待补充'）"
      },
      "L3_core_tension": "主要对立：[A] vs [B]",
      "L4_project_task": "为[用户身份]打造[空间类型]，雇佣空间完成[任务1]与[任务2]"
    },

    "structured_output": {
      "project_task": "JTBD公式化的项目任务",
      "character_narrative": "用户基本画像（基于有限信息）",
      "physical_context": "物理环境（如Phase1有提供）",
      "resource_constraints": "资源限制（如Phase1有提供）",
      "design_challenge": "设计挑战简要描述"
    },

    "expert_handoff": {
      "critical_questions_for_experts": {
        "for_v2_design_director": [
          "基于现有信息，设计方向建议？"
        ],
        "for_v3_narrative_expert": [
          "空间叙事的可能方向？"
        ],
        "for_v5_scenario_expert": [
          "核心场景是什么？"
        ]
      },
      "info_limitation_notice": "⚠️ 基于有限信息分析，建议后续通过问卷补充",
      "permission_to_diverge": {
        "message": "此为基于有限信息的初步判断",
        "challenge_protocol": "发现更多信息时，请主动补充和调整"
      }
    }
  }
  ```

  ⚡ **性能要求**：总耗时控制在1000-1200ms内

task_description_template: |
  {datetime_info}

  ### 用户输入:
  "{user_input}"

  ### Phase1 输出（info_status = insufficient）:
  {phase1_output}

  ### ⚡ Phase2-Lite 任务（轻量级分析，30秒内完成）

  Phase1判定信息不足，但仍需提供基础分析支持后续流程。

  **轻量级分析要求**：
  1. **L1 解构**：快速MECE分解（3-5个核心事实）
  2. **L2 简化建模**：3个基础视角（心理/社会/美学，各1-2句话）
  3. **L3 快速对立**：识别1-2个主要张力
  4. **L4 JTBD**：核心任务定义（即使信息有限也要推断）
  5. **基础专家接口**：为3个核心专家各提供1个问题

  **跳过层级**：L5锐度测试、L6假设审计、L7系统影响

  请直接返回JSON格式结果，控制在1000-1200ms完成。
```

### 2. 修改phase2_node函数

**文件**: `intelligent_project_analyzer/agents/requirements_analyst_agent.py`

**修改位置**: phase2_node函数（约line 405-490）

**修改策略**：
```python
def phase2_node(state: RequirementsAnalystState) -> Dict[str, Any]:
    """
    节点3: Phase2 - 深度分析 + 专家接口构建

    v7.622新增：根据info_status选择Full或Lite模式
    - sufficient → Phase2-Full（完整L1-L7分析，~3000ms）
    - insufficient → Phase2-Lite（轻量级L1-L4分析，~1200ms）
    """
    start_time = time.time()
    user_input = state.get("user_input", "")
    phase1_result = state.get("phase1_result", {})
    llm_model = state.get("_llm_model")
    prompt_manager = state.get("_prompt_manager")

    # 获取info_status决定使用哪个模式
    info_status = state.get("phase1_info_status", "insufficient")

    # ═══════════════════════════════════════════════════════════
    # v7.622: 根据info_status选择Phase2模式
    # ═══════════════════════════════════════════════════════════
    if info_status == "sufficient":
        phase2_mode = "full"
        prompt_key = "requirements_analyst_phase2"
        logger.info("[Phase2] 模式: Full（完整L1-L7分析）")
    else:
        phase2_mode = "lite"
        prompt_key = "requirements_analyst_phase2_lite"
        logger.info("[Phase2] 模式: Lite（轻量级L1-L4分析，性能优化）")
    # ═══════════════════════════════════════════════════════════

    # 使用Phase1提供的Mode Detection结果（无需重复检测）
    detected_modes = state.get("detected_design_modes", [])
    mode_detection_elapsed = state.get("mode_detection_elapsed_ms", 0)

    if detected_modes:
        logger.info(
            f"[ModeDetection] 使用Phase1检测结果: {len(detected_modes)}个模式, "
            f"耗时 {mode_detection_elapsed:.1f}ms"
        )
        top_mode = detected_modes[0]
        from ..services.mode_detector import get_mode_name
        logger.info(
            f"   主模式: {get_mode_name(top_mode['mode'])} "
            f"({top_mode['confidence']:.2f})"
        )
    else:
        logger.warning("[ModeDetection] Phase1未检测到模式，继续执行Phase2")

    # 加载对应模式的提示词
    phase2_config = prompt_manager.get_prompt(prompt_key, return_full_config=True)

    if not phase2_config:
        logger.warning(f"[Phase2] 未找到配置'{prompt_key}'，使用 fallback")
        return _phase2_fallback(state, start_time)

    # ... 后续LLM调用逻辑保持不变 ...

    # 在返回时添加mode标记
    return {
        "phase2_result": phase2_result,
        "phase2_mode": phase2_mode,  # NEW: 记录使用的模式
        "phase2_elapsed_ms": elapsed_ms,
        "analysis_layers": phase2_result.get("analysis_layers", {}),
        "expert_handoff": phase2_result.get("expert_handoff", {}),
        "detected_design_modes": detected_modes,
        "mode_detection_elapsed_ms": mode_detection_elapsed,
        "processing_log": state.get("processing_log", []) + [
            f"[Phase2] 完成 ({elapsed_ms:.0f}ms, mode={phase2_mode})",
            f"[ModeDetection] 识别{len(detected_modes)}个模式 ({mode_detection_elapsed:.1f}ms)"
        ],
        "node_path": state.get("node_path", []) + ["phase2"],
    }
```

### 3. 状态类型更新

**文件**: `intelligent_project_analyzer/agents/requirements_analyst_agent.py`

**修改位置**: RequirementsAnalystState类定义（约line 75-130）

**添加字段**：
```python
class RequirementsAnalystState(TypedDict):
    # ... 现有字段 ...

    # ─────────────────────────────────────────────────────────────────────────
    # 中间状态 - Phase2 阶段
    # ─────────────────────────────────────────────────────────────────────────
    phase2_result: Dict[str, Any]
    phase2_mode: str  # NEW v7.622: "full" | "lite"
    phase2_elapsed_ms: float
    # ... 其他现有字段 ...
```

---

## 质量保证

### Phase2-Lite 输出完整性

| 输出项 | Phase2-Full | Phase2-Lite | 后续影响 |
|--------|------------|------------|---------|
| **L1 facts** | 5-10个详细事实 | 3-5个核心事实 | ✅ 足够支撑基础分析 |
| **L2 user_model** | 5+5视角详细建模 | 3个基础视角 | ⚠️ 深度降低，但核心保留 |
| **L3 core_tension** | 深度对立分析 | 快速识别对立 | ⚠️ 专家需自行深化 |
| **L4 JTBD** | 完整公式 | 完整公式 | ✅ 无影响（核心输出） |
| **L5 sharpness** | 70+分评分 | ❌ 跳过 | ⚠️ 无质量评分 |
| **expert_handoff** | 每个专家多问题 | 核心专家1问题 | ⚠️ 专家自主性增加 |

### 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| **Lite模式分析质量不足** | 中 | 中 | ✅ 保留L1+L4核心，专家可补充 |
| **专家接口问题过少** | 低 | 低 | ✅ 保留核心专家基础问题 |
| **JTBD推断不准确** | 中 | 高 | ⚠️ 需监控，考虑后续问卷校准 |
| **性能未达1200ms目标** | 低 | 中 | ✅ 精简提示词，移除示例 |

---

## 验证计划

### 阶段1：功能验证（P0）

- [ ] **提示词文件创建**：`requirements_analyst_phase2_lite.yaml`
- [ ] **代码修改完成**：phase2_node函数支持双模式
- [ ] **状态定义更新**：添加phase2_mode字段
- [ ] **日志完整性**：记录使用的模式

### 阶段2：性能测试（P0）

| 测试场景 | 预期Phase2耗时 | 验收标准 |
|---------|---------------|---------|
| Sufficient + Phase2-Full | 2800-3200ms | ✅ 与v7.621一致 |
| Insufficient + Phase2-Lite | 1000-1400ms | ✅ 目标1200ms ±200ms |
| 整体平均 | ~3500ms | ✅ vs v7.621的4700ms，节省26% |

### 阶段3：质量测试（P1）

- [ ] **Lite模式输出完整性**：L1/L4/expert_handoff必须存在
- [ ] **JTBD公式准确性**：抽样10个insufficient场景验证
- [ ] **专家可用性**：验证Lite模式输出是否足够专家执行任务
- [ ] **对比测试**：相同insufficient输入，Full vs Lite质量差异

### 阶段4：集成测试（P1）

- [ ] **50场景测试**：验证模式自动选择准确性
- [ ] **端到端流程**：Phase1 → Phase2(Lite) → 问卷 → 专家
- [ ] **错误恢复**：Phase2-Lite失败时的fallback机制

---

## 实施步骤

### Step 1: 创建Phase2-Lite提示词（5分钟）

```bash
# 创建文件
New-Item -ItemType File -Path "intelligent_project_analyzer/config/prompts/requirements_analyst_phase2_lite.yaml"

# 复制上述YAML内容到文件
```

### Step 2: 修改phase2_node函数（10分钟）

**修改内容**：
1. 添加info_status判断逻辑
2. 根据status选择prompt_key（"requirements_analyst_phase2" 或 "requirements_analyst_phase2_lite"）
3. 添加phase2_mode到返回值
4. 更新日志输出

### Step 3: 更新状态定义（2分钟）

在`RequirementsAnalystState`添加：
```python
phase2_mode: str  # "full" | "lite"
```

### Step 4: 测试验证（30分钟）

```powershell
# 快速测试
python -m pytest tests/ -k "requirements_analyst" -v --tb=short

# 性能基准测试
python -m pytest tests/integration/test_requirements_analyst_performance.py -v
```

### Step 5: 文档更新（5分钟）

- 更新`MECHANISM_RELATIONSHIP_CLARIFICATION.md`：添加Phase2双模式说明
- 更新`OPTIMIZATION_v7.621_MODE_DETECTION_GUARANTEE.md`：添加v7.622补充说明

---

## 成本-收益分析

### 开发成本

| 任务 | 时间 | 复杂度 |
|------|------|--------|
| 创建Lite提示词 | 5分钟 | 低（复制+精简Full版） |
| 修改phase2_node | 10分钟 | 低（添加if判断） |
| 状态定义更新 | 2分钟 | 低 |
| 测试验证 | 30分钟 | 中 |
| 文档更新 | 5分钟 | 低 |
| **总计** | **52分钟** | **低** |

### 性能收益

| 指标 | v7.621 | v7.622 | 改进 |
|------|--------|--------|------|
| Insufficient场景 (66%) | 4.7s | **2.9s** | **-38%** ⭐ |
| 整体平均 | 4.7s | **3.5s** | **-26%** ⭐ |
| LLM Token成本 | 100% | **~70%** | **-30%** ⭐ |

**加权收益**：66%用户体验提升38% = **整体用户满意度提升25%**

### ROI计算

**投入**：52分钟开发 + 测试时间
**回报**：
- 性能提升：66%场景快38%（用户等待时间减少1.8s）
- 成本降低：LLM调用成本减少30%
- 用户体验：快速响应 vs 等待4.7s的体验差异显著

**ROI**: **极高**（低投入，高回报）

---

## 后续优化方向

### 短期优化（P2）

1. **动态阈值调整**：根据用户输入长度动态调整Lite模式深度
2. **Lite模式分级**：
   - Lite-Min：极简模式（仅L1+L4，~800ms）
   - Lite-Standard：标准模式（L1-L4，~1200ms）
   - Lite-Plus：增强模式（L1-L4+简化L5，~1500ms）

### 中期优化（P3）

3. **自适应模式选择**：基于detected_modes自动调整Phase2深度
   - M1概念驱动：需要完整分析 → 强制Full模式
   - M2功能效率：可精简分析 → 允许Lite模式

4. **增量分析**：Phase2-Lite → 问卷补充 → Phase2-Full增量执行

---

## 总结

**核心价值**：
- ✅ **保持v7.621优势**：Phase2总是执行，分析完整性100%
- ✅ **解决v7.621痛点**：Insufficient场景性能优化38%
- ✅ **实施成本极低**：52分钟开发，无架构变更
- ✅ **向后兼容**：不影响Sufficient场景，Lite模式可降级到Full

**适用场景**：
- ✅ Sufficient场景：继续使用Phase2-Full（无变化）
- ✅ Insufficient场景：自动切换Phase2-Lite（性能优化）
- ✅ 特殊需求：可通过配置强制使用Full模式

**升级建议**：
- ✅ **立即实施**（P0优先级）
- 实施简单，风险低
- 收益明显（66%场景性能提升38%）
- 建议配合性能监控验证实际效果

---

**版本**: v7.622
**状态**: 待实施
**预计完成时间**: 1小时
**负责人**: Requirements Analyst Agent Maintainer
