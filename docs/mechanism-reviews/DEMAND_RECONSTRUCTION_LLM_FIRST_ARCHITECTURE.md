# 需求重构 LLM-first 智能架构专题

版本：v1.35  
日期：2026-06-19  
定位：方案高参需求重构阶段的下一代主架构设计  
范围：讨论 LLM 先行语义理解、规则蓝图扫描、未命中诚实分流、最终 LLM 综合输出的协同机制  
Revision: v1.25 completes the default public_cultural_experience primary blueprint fragment: it now has full task_reframe / viability / primary_risk / sections / slots, and the default public-cultural path uses registry:primary_archetypes.public_cultural_experience before older generic fallback.
Revision: v1.26 completes the default life_identity primary blueprint fragment: it now has full task_reframe / viability / primary_risk / key_forks / unknowns / sections / slots, and the default life-identity path uses registry:primary_archetypes.life_identity instead of treating residential_life_order as the fallback default.
Revision: v1.27 completes the default media_production primary blueprint fragment: it now has full task_reframe / viability / primary_risk / key_forks / unknowns / sections / slots, and the default media-production path uses registry:primary_archetypes.media_production instead of treating live_commerce_studio as the fallback default.
Revision: v1.28 completes the default hard_constraint primary blueprint fragment: it now has full task_reframe / viability / primary_risk / key_forks / unknowns / sections / slots, and the default hard-constraint path uses registry:primary_archetypes.hard_constraint instead of treating generic_constraint as the fallback default.
Revision: v1.29 moves Stage 2 forward: the LLM Semantic Router prompt now exposes the controlled scan target ids and explicitly requires recommended_scan_targets to use those ids, so Stage 1 understanding can drive Stage 2 asset scanning without invented labels.
Revision: v1.30 implements the Evidence & Confidence Check in scan grading: LLM semantic scan results now expose confidence_band / max_confidence, and medium-confidence known targets become partial_match instead of strong_match.
Revision: v1.31 connects partial_match to Path Selection: partial_specialist coverage now softens the user-facing commitment as neighbor-transfer judgment and explicitly forbids treating nearby rules as complete specialist conclusions.
Revision: v1.32 improves Final Synthesis input fidelity: the prompt context now preserves LLM Semantic Router candidate/tension evidence and confidence instead of flattening them into plain strings.
Revision: v1.33 verifies the hard-failure entry contract: the production route uses DEMAND_RECONSTRUCTION_USE_LLM=1 by default and maps DemandReconstructionUnavailable to HTTP 503 instead of silently falling back to the rule blueprint.
Revision: v1.34 completes Stage 3 asset-scan observability: llm_semantic_scan now records rule fragments, semantic axes, main tensions, coverage, and approved knowledge assets, and Final Synthesis preserves that asset_scan instead of flattening it away.
Revision: v1.35 tightens Stage 2 fragment retrieval: default specialty fragments such as residential_life_order and generic_exhibition only outrank primary defaults when registry trigger terms or semantic-axis evidence support them, preserving evidence-based asset scanning instead of unconditional template capture.

---

## 0. 核心结论

需求重构阶段不应继续以规则蓝图作为理解入口。

规则蓝图再完善，也仍然是有限枚举、有限碎片、有限经验资产。面对无边无际的真实项目问题，如果系统先按规则蓝图做判断，就必然出现三类问题：

1. 命中样板题时表现好，但遇到长尾项目时容易错分。
2. 规则没有覆盖时，会退回通用模板或硬套邻近模板。
3. LLM 被放在后面时，只能补写、润色或修补，无法充分发挥开放语义理解能力。

更合理的主架构应改为：

```text
LLM 先理解
    ↓
扫描规则蓝图、语义轴、算法资产和知识包
    ↓
命中则调用稳定规则，未命中则诚实转入探索路径
    ↓
LLM 再综合为唯一用户可见结果
```

这不是取消规则蓝图，而是重新定义规则蓝图的位置：

> 规则蓝图不是入口，不是默认答案，而是 LLM 理解之后可以调用的稳定能力库。

---

## 1. 重新理解用户意图

用户真正指出的问题不是“当前规则蓝图还不够多”，而是：

> 只要系统从规则蓝图开始，它就天然受限于枚举边界。

规则、模板、碎片库、关键词、语义轴和主矛盾算法都很有价值，但它们不应承担第一理解责任。第一理解责任应交给 LLM，因为 LLM 更擅长处理：

- 未见过的空间类型；
- 复合型项目；
- 模糊而长的自然语言；
- 多目标冲突；
- 隐含任务意图；
- 用户没有按系统分类体系描述的问题。

因此，新的目标不是：

```text
规则蓝图 + LLM 增强
```

而是：

```text
LLM 语义识别 + 规则资产匹配 + LLM 受控综合
```

---

## 2. 为什么“规则优先”仍然不够

### 2.1 规则蓝图的价值

规则蓝图仍然有不可替代的作用：

1. 稳定，不依赖模型状态。
2. 可审计，输出结构可控。
3. 能沉淀高频行业经验。
4. 能提供边界和兜底。
5. 能把已验证知识资产变成可复用能力。

这些价值应该保留。

### 2.2 规则蓝图的天花板

但规则蓝图不适合做第一入口：

1. 它只能覆盖已知类型。
2. 它容易被关键词污染。
3. 它对复合项目的主次关系不敏感。
4. 它无法自然理解用户语言里的隐含任务。
5. 它容易在未命中时输出“看似合理但其实泛化”的模板。

当问题规模从几十个样板扩展到上百、上千、上万种真实项目时，继续扩大规则枚举会变成维护负担，而不是智能能力。

### 2.3 当前阶段的根本转向

规则蓝图应该从：

```text
前台判断器
```

转为：

```text
后台可调用资产库
```

LLM 应该从：

```text
后置润色器
```

转为：

```text
第一语义理解器 + 最终综合表达器
```

---

## 3. 推荐主架构：LLM-first Semantic Routing

建议将需求重构主链路拆为五层。

```text
用户原始输入
    ↓
1. LLM Semantic Router
    ↓
2. Evidence & Confidence Check
    ↓
3. Rule / Algorithm / Knowledge Scanner
    ↓
4. Path Selection
    ↓
5. LLM Final Synthesis
    ↓
唯一用户可见需求重构结果
```

### 3.1 参考意见交叉校验与冲突处理

本节把两份参考意见逐项校验，区分“采纳”“修正采纳”“不采纳但保留原因”，避免把观点拼盘式叠加。

1. **关于主架构：`LLM → 规则蓝图 → LLM`**
   - 参考意见一致认为，规则蓝图不应再作为第一入口，LLM 应先承担开放语义理解。
   - 采纳。主架构确定为 LLM 先生成结构化理解包，中间确定性扫描规则/算法/知识资产，最后由 LLM 综合成唯一用户可见版本。

2. **关于规则蓝图角色：默认作者还是稳定资产**
   - 两份参考意见都主张规则蓝图从“分类器 + 输出主体”退到“可检索稳定资产 + 硬约束”。
   - 采纳。规则蓝图不再负责抢先回答用户，而是向第二轮 LLM 提供领域碎片、边界条款、handoff slots 和覆盖等级。

3. **关于 LLM 是否必须可用**
   - 参考意见 1 保留“故障兜底”表达；参考意见 2 进一步记录了最新决策：LLM 必须可用，多 API 梯度全部失败时直接明确报错，不静默退回规则蓝图。
   - 修正采纳参考意见 2。下一代主链路不再以 `semantic_fallback` 作为用户默认体验；全链失败应返回类型化错误，并给用户明确提示“智能识别暂不可用，请重试”。现有规则路径可保留为诊断、迁移和后台对照工具，但不是产品默认兜底。

4. **关于两次 LLM 调用还是一次合并**
   - 参考意见 1 提到可合并以降低延迟；参考意见 2 明确锁定 ① 理解器与 ③ 综合器为两次独立调用。
   - 采纳两次独立调用。理由是第一阶段要产出可审计理解包，第三阶段要在检索碎片和硬约束后综合输出，二者职责不同。后续可以通过缓存、流式、模型路由优化延迟，但不在第一版合并。

5. **关于多供应商梯度**
   - 参考意见 2 与当前代码基础一致：系统已有 `qwen → deepseek → openrouter` 的 fallback provider order。
   - 采纳。两轮 LLM 都独立跑同一梯度链；每段每 provider 允许一次结构修复或质量修复，仍失败则换下一家。整条链耗尽才判定不可用。

6. **关于“碎片化 registry”是否从零开始**
   - 参考意见都强调要把模板拆成碎片库；但当前工作树已经存在 `_demand_reconstruction_blueprint_fragments()`、`_primary_blueprint_fragment()`、`_specialized_blueprint_fragment()` 和 `_fragment_plan()` 等半成品机制。
   - 修正采纳。执行重点不是从零新建碎片系统，而是完成迁移：补全现有碎片字段、拆出独立 YAML、把仍在 Python builder 里的整段文案和 `if` 分支迁入可检索碎片。

7. **关于“没有命中规则蓝图就完全不使用规则”**
   - 参考意见强调“未命中如实走另一条路”，不能硬套最近模板。
   - 修正采纳。未命中时不调用专科规则碎片，但仍可调用通用第一性推理框架、输出边界、handoff slots 和知识缺口治理信号。也就是说，不套错专业模板，但保留通用结构护栏。

8. **关于入口分诊的归属**
   - 参考意见建议复用 `scheme_advisor_entry_service._classify_input` 并扩展六分法。
   - 修正采纳。下一代主链路中，第一责任应由 LLM Semantic Router 承担；既有入口分诊算法可作为受控词表、交叉校验和诊断依据，而不是继续作为主入口硬分类器。

9. **关于防幻觉机制**
   - 两份参考意见都要求 LLM 不能完全自由发挥。
   - 采纳。第一轮 LLM 受 schema、registry 词表、证据字段约束；第二轮 LLM 受命中碎片、边界条款、语义对齐门、质量门约束。LLM 是主干，不是无约束作者。

10. **关于测试契约和破坏性变化**
    - 当前代码和测试仍有 `semantic_fallback` 断言，代表旧契约“LLM 失败不阻断入口”。
    - 明确为迁移影响。实施 LLM-first 后，相关测试应从“失败回规则蓝图”改为“梯度耗尽返回类型化错误”；否则测试会保护旧架构，阻碍新架构落地。

---

## 4. 第一层：LLM Semantic Router

第一轮 LLM 不直接回答用户，而是生成内部语义识别包。

### 4.1 职责

LLM Semantic Router 负责判断：

1. 用户到底是在提具体项目，还是方法论、案例、命名、资料或出域问题。
2. 项目对象是什么。
3. 空间类型可能有哪些。
4. 是否存在复合类型。
5. 用户真正要解决的矛盾是什么。
6. 有哪些硬约束、软目标和未知条件。
7. 哪些判断有原文证据，哪些只是推断。
8. 当前问题是否属于系统已知范围。

### 4.2 内部输出结构

建议输出为结构化语义包：

```json
{
  "intent_type": "specific_project_reconstruction",
  "project_anchor": true,
  "project_object": "汽车品牌体验店",
  "space_candidates": [
    {
      "label": "品牌体验空间",
      "confidence": 0.82,
      "evidence": ["汽车品牌体验店", "品牌空间"]
    },
    {
      "label": "历史街区商业更新",
      "confidence": 0.71,
      "evidence": ["成都历史街区", "城市记忆"]
    }
  ],
  "core_tensions": [
    {
      "title": "城市记忆转译与品牌商业识别之间的张力",
      "evidence": ["城市记忆转译", "品牌空间"],
      "confidence": 0.78
    }
  ],
  "missing_slots": [
    "品牌体验店的运营目标",
    "街区保护和改造边界",
    "访客路径与商业转化优先级"
  ],
  "novelty_level": "partial_unknown",
  "recommended_scan_targets": [
    "brand_experience",
    "urban_renewal",
    "cultural_translation",
    "commercial_operation"
  ]
}
```

### 4.3 关键约束

第一轮 LLM 必须带证据输出。任何判断如果没有原文证据，只能标记为 hypothesis，不能进入强规则匹配。

---

## 5. 第二层：Evidence & Confidence Check

LLM 先行不等于 LLM 自由发挥。第一轮语义包必须经过证据和置信度检查。

### 5.1 检查对象

1. `intent_type` 是否与原文一致。
2. `project_anchor` 是否有明确项目证据。
3. `space_candidates` 是否有原文支撑。
4. `core_tensions` 是否不是模型脑补。
5. `missing_slots` 是否与后续任务有关。
6. `novelty_level` 是否过度自信或过度保守。

### 5.2 处理方式

| 情况 | 处理 |
|---|---|
| 高置信 + 有证据 | 进入规则/知识扫描 |
| 中置信 + 有部分证据 | 进入弱命中扫描，并保留探索路径 |
| 低置信 | 不调用强规则，只做探索型重构 |
| 与原文冲突 | 丢弃该字段或重跑 LLM 识别 |

---

## 6. 第三层：Rule / Algorithm / Knowledge Scanner

这一层不是重新理解用户，而是拿第一轮 LLM 语义包去扫描系统已有资产。

### 6.1 扫描对象

1. 规则蓝图碎片库。
2. 语义轴 registry。
3. 主矛盾排序算法。
4. 空间分类器。
5. 知识覆盖等级。
6. 已审核知识资产。
7. 历史治理样本。

### 6.2 扫描结果分级

扫描结果不应该只有“命中 / 不命中”，而应分为三档：

| 扫描结果 | 含义 | 后续处理 |
|---|---|---|
| strong_match | 有稳定规则和知识资产支撑 | 调用对应规则蓝图碎片 |
| partial_match | 有邻近碎片，但不能完整覆盖 | 调用部分碎片，同时保留探索说明 |
| no_match | 无可靠规则支撑 | 不硬套规则，进入探索型需求重构 |

### 6.3 重要原则

规则蓝图只能响应被 LLM 语义包明确提出、且有证据支撑的部分。

不能因为规则库里有某个模板，就把用户没有表达的行业、场景、运营方式写进去。

---

## 7. 第四层：Path Selection

系统应根据扫描结果选择不同路径。

### 7.1 强命中路径

适用情况：

- LLM 识别明确；
- 规则蓝图有高匹配碎片；
- 知识覆盖等级足够；
- 原文证据充分。

处理方式：

```text
LLM 语义包
    +
强命中规则碎片
    +
主矛盾算法
    +
覆盖等级
→ LLM 最终综合
```

用户侧看到的是深度、具体、定制化的需求重构。

### 7.2 弱命中路径

适用情况：

- 有部分规则碎片；
- 但项目是复合或长尾；
- 知识覆盖不完整；
- 需要保留假设边界。

处理方式：

```text
部分规则碎片
    +
探索型追问
    +
覆盖边界说明
→ LLM 综合为谨慎版本
```

用户侧应看到：

- 哪些判断可以先成立；
- 哪些只是待验证假设；
- 下一步最该确认什么。

### 7.3 未命中路径

适用情况：

- 规则蓝图无可靠匹配；
- 空间类型或任务类型很新；
- 只有 LLM 能做初步理解；
- 系统不应伪装成已有专科能力。

处理方式：

```text
LLM 语义理解
    +
通用需求重构框架
    +
知识缺口治理信号
→ 探索型需求重构
```

用户侧表达应是：

> 当前不能直接按现有空间类型套模板。更合理的是先确认项目成立逻辑、核心冲突、约束边界和下一步信息缺口。

后台应生成：

- `knowledge_gap_ticket`
- `space_registry_review`
- `new_fragment_candidate`

---

## 8. 第五层：LLM Final Synthesis

最终输出必须由 LLM 综合生成，而不是把规则结果、算法结果和诊断字段拼接给用户。

### 8.1 输入

最终 LLM 应接收：

1. 用户原文；
2. 第一轮 LLM 语义包；
3. 证据校验结果；
4. 规则/知识扫描结果；
5. 命中的蓝图碎片；
6. 未命中的缺口；
7. 覆盖等级；
8. 输出边界。

### 8.2 输出

用户只看到一个综合版本：

```text
需求重构

这不是单纯把城市记忆做成品牌装饰的问题，而是判断历史街区的地方记忆、汽车品牌的商业识别、访客体验路径和街区公共性，能否形成一个不互相抵消的空间秩序。

真正的风险是：用文化转译包装品牌空间，但没有先确认街区保护边界、品牌转化目标和访客停留机制。

我建议先确认一个关键点：这个体验店首先承担品牌展示、城市记忆表达，还是销售转化？
```

### 8.3 禁止输出

最终用户侧不能出现：

- `LLM Semantic Router`
- `semantic_candidate_set`
- `fragment`
- `registry`
- `llm_status`
- `coverage_gap`
- `knowledge_gap_ticket`
- “规则蓝图命中”
- “模型判断”

这些都应留在后台诊断和治理系统。

---

## 9. 新旧架构对比

| 维度 | 旧规则优先架构 | 新 LLM-first 架构 |
|---|---|---|
| 第一理解责任 | 规则/算法 | LLM |
| 规则蓝图角色 | 前台答案或主骨架 | 后台可调用资产库 |
| 长尾问题处理 | 容易兜底套话 | 探索型重构 + 知识缺口 |
| LLM 作用 | 后置增强/润色 | 先理解 + 后综合 |
| 风险 | 枚举过拟合、错域注入 | 需要证据门和置信度门 |
| 用户体验 | 可能像模板 | 更像真实理解 |
| 治理方式 | 补规则分支 | 沉淀新资产和缺口队列 |

---

## 10. 风险与护栏

LLM-first 架构更智能，但必须有护栏。

### 10.1 证据护栏

LLM 识别出的关键判断必须有原文证据。

没有证据的内容只能进入 hypothesis，不能驱动强规则命中。

### 10.2 置信度护栏

低置信语义识别不能调用高确定性规则蓝图。

低置信时应输出探索型重构，而不是强判断。

### 10.3 规则护栏

规则蓝图只能补充已命中的稳定部分，不能覆盖 LLM 对用户原文的理解。

### 10.4 覆盖护栏

没有专科知识时，必须降级：

```text
专科深答
    ↓
邻近迁移
    ↓
通用框架
    ↓
知识缺口说明
```

### 10.5 输出护栏

最终输出必须是用户语言，不暴露内部机制。

### 10.6 可用性护栏：多供应商梯度与硬失败

LLM-first 主链路不再把规则蓝图作为静默兜底。可用性由多供应商梯度保证，而不是由规则模板假装成功。

建议错误契约：

| 阶段 | 梯度 | 修复预算 | 全链失败错误 |
|---|---|---|---|
| LLM Semantic Router | `qwen → deepseek → openrouter` | 每 provider 1 次 schema repair | `UNDERSTANDING_UNAVAILABLE` |
| LLM Final Synthesis | `qwen → deepseek → openrouter` | 每 provider 1 次 quality/alignment repair | `SYNTHESIS_UNAVAILABLE` |

用户侧不显示内部错误码，只显示清晰提示：

```text
智能识别暂不可用，请重试。
```

后台应记录每个 provider 的失败原因、耗时、修复次数和最终错误类型，用于判断是供应商故障、鉴权问题、限流问题，还是输出质量始终不过门。

---

## 11. 建议实施路线

### 阶段零：冻结现状与迁移边界

先明确当前系统仍存在两类旧契约：

1. `semantic_fallback` 静默兜底；
2. Python builder 仍承担大量硬编码模板和二次分支。

这两类不是立即删除对象，而是迁移边界。先记录现状快照，防止迁移中把旧问题误判为新问题。

### 阶段一：完成规则蓝图碎片化迁移

碎片化已经有半成品机制，第一阶段不是从零开发，而是完成迁移：

1. 将 `demand_reconstruction_blueprint_fragments` 从综合语义轴 YAML 中拆成独立 registry；
2. 补全已存在但字段不完整的 primary fragments；
3. 把仍在 Python builder 里的整段文案迁入碎片；
4. 把 Python `if` 分支迁为带 `trigger_terms` / `fragment_id` 的子碎片；
5. 保留 `_fragment_plan()` 一类通用渲染器，减少服务代码里的领域补丁。

完成后，规则蓝图应成为“可检索知识资产”，而不是“入口模板工厂”。

### 阶段二：LLM Semantic Router

- `intent_type`
- `project_anchor`
- `project_object`
- `space_candidates`
- `core_tensions`
- `missing_slots`
- `novelty_level`
- `evidence`

新增第一轮 LLM 语义识别，不直接面向用户输出。它必须使用受控 schema、registry 词表、证据绑定和置信度字段。

该阶段先影子运行，与现有关键词/算法分诊做对照，验证 LLM 路由是否真正减少错域和 general 套话。

### 阶段三：规则/知识扫描器

把规则蓝图从“入口 builder”改成“资产扫描器”：

- 强命中调用；
- 弱命中部分调用；
- 未命中不调用。

扫描器只接受第一轮 LLM 理解包和证据字段，不再自行用宽关键词抢主类型。

### 阶段四：探索型需求重构路径

新增 no_match / partial_match 的正式路径，替代空泛 general_project。

探索型路径必须包含：

- 当前高置信判断；
- 当前不确定判断；
- 下一步最关键追问；
- 知识缺口治理信号。

### 阶段五：LLM Final Synthesis

最终 LLM 基于完整内部语义包生成唯一用户版。

第二轮 LLM 独立调用多供应商梯度，消费：

1. 用户原文；
2. 第一轮理解包；
3. 规则/知识扫描结果；
4. 命中碎片或未命中信号；
5. 覆盖等级；
6. 输出边界和禁止项。

生成后必须过质量门和语义对齐门；失败按 provider 修复一次，再切换下一 provider。

### 阶段六：替换旧 fallback 契约

实施新主链路后，现有“LLM 失败回规则蓝图”的测试与产品契约需要改写：

```text
旧：LLM 失败 → semantic_fallback → 用户看到规则蓝图
新：梯度耗尽 → 类型化错误 → 用户看到“智能识别暂不可用，请重试”
```

这一步是破坏性变化，必须明确纳入实施计划，否则系统会被旧测试长期锁回规则优先。

### 阶段七：治理闭环

把未命中、低覆盖、错域拒绝、用户纠偏沉淀为治理队列。

---

## 12. 验收标准

### 12.1 具体项目建议类输入

输入：

```text
成都历史街区里的一家汽车品牌体验店，需要将城市记忆转译为品牌空间，给出建议。
```

期望：

1. LLM Semantic Router 判断为具体项目；
2. 识别品牌体验、历史街区、城市记忆转译；
3. 扫描到部分规则资产；
4. 不进入 deep research；
5. 不硬套公共文化、商业翻台、文化研究模板；
6. 最终输出一个综合需求重构结果。

### 12.2 纯方法论输入

输入：

```text
社区文化空间应该怎么研究在地性、公共性和运营模式，请给出分析框架和判断方法。
```

期望：

1. LLM Semantic Router 判断为方法论咨询；
2. 不进入需求重构；
3. 不调用规则蓝图；
4. 返回方法论型回答或进入方法论路径。

### 12.3 未覆盖长尾项目

输入：

```text
一个面向虚拟偶像线下粉丝共创的混合空间，希望兼顾沉浸互动、线下聚会、内容生产和商业转化。
```

期望：

1. 系统不硬套已有蓝图；
2. 输出探索型需求重构；
3. 标注高置信判断和待验证假设；
4. 后台生成知识缺口或新碎片候选。

### 12.4 用户侧体验

用户只看到：

- 需求重构判断；
- 核心风险；
- 关键分叉；
- 待补信息；
- 下一步追问。

用户不看到：

- LLM 状态；
- 规则命中状态；
- registry；
- fragment；
- governance queue；
- 内部字段名。

---

## 13. 与既有 v1.28 文档的关系

`DEMAND_RECONSTRUCTION_ALGORITHM_OPTIMIZATION.md` v1.28 已经完成了大量规则蓝图、算法资产、同步融合和治理闭环的阶段性实施。

本专题不是否定 v1.28，而是提出下一阶段主架构升级：

| 文档 | 角色 |
|---|---|
| v1.28 算法优化专题 | 规则蓝图算法化、碎片化、同步融合的当前实施总结 |
| 本专题 | 下一代 LLM-first 需求重构主架构 |

可以理解为：

```text
v1.28 解决“规则蓝图怎样不模板化”
本专题解决“需求重构为什么不应从规则蓝图开始”
```

---

## 14. v1.25 阶段性实施状态

截至 2026-06-19，本专题已进入第一批代码落地，但尚未完成全部架构闭环。

### 14.1 已落地

1. **LLM 必需错误契约**
   - 需求重构服务新增显式不可用异常。
   - 当主链路要求 LLM 且 LLM 未配置、调用失败或结构化理解失败时，不再静默退回规则蓝图。
   - 对外错误文案固定为：`智能识别暂不可用，请重试。`

2. **Stage 1 LLM Semantic Router**
   - 在规则蓝图构建前，先调用 LLM 输出内部语义理解包。
   - 理解包要求包含意图、项目锚点、项目对象、候选空间、核心张力、缺失槽位、覆盖/新颖度判断等字段。
   - 候选和张力必须携带 evidence；不满足结构契约时先做一次修复，再进入下一个 provider 或最终失败。

3. **Stage 3 最终综合接收理解包**
   - 第一轮 LLM 理解包已注入 `adapter_context`。
   - 最终综合 prompt 明确要求把“LLM 语义理解包”作为优先语义依据，再结合规则蓝图边界与碎片。
   - 用户侧仍只看到一个综合版本，不显示两轮 LLM 的内部过程。

4. **入口路由显式失败**
   - `/api/v2/conversation/message` 在 `DEMAND_RECONSTRUCTION_USE_LLM=1` 时启用 `require_llm`。
   - 当 LLM-first 主链路不可用时，返回 HTTP 503，detail 中包含错误码与用户文案。
   - 旧的异步补丁开关不再改变主链路输出形态。

5. **回归测试**
   - 服务层新增必需 LLM 失败、未配置、两段调用顺序等测试。
   - API 层新增 503 显式失败测试，并将同步融合路径更新为两次 LLM 调用预期。

6. **Stage 1 驱动 Stage 2 的第一批规则扫描**
   - 第一轮 LLM 理解包中的 `space_candidates` 已可转为规则蓝图候选。
   - 候选必须带 evidence，低置信或无法映射到受控目标的候选不会进入强规则匹配。
   - LLM 候选与原有关键词/算法候选合并时，LLM 有证据的候选优先。
   - 典型效果：当文本包含“咖啡店”等会触发商业模板的词，但第一轮 LLM 有证据判断它首先是“社区公共客厅/公共文化体验”时，规则蓝图选型可转向 `public_cultural_experience`，而不是被关键词劫持到 `commercial_operation`。
   - 公开上下文增加 `llm_semantic_scan`，记录 `strong_match / partial_match / no_match` 的初步扫描状态。

7. **no_match 防模板劫持**
   - 当 Stage 1 判断 `novelty_level=unknown`，且候选无法映射到受控规则目标时，Stage 2 生成 `general_project` 探索候选。
   - 该候选来源标记为 `llm_semantic_router_no_match`。
   - 原有关键词/规则候选可作为次级诊断保留，但不得再作为主蓝图作者。
   - 典型效果：文本里即使包含“咖啡店”，只要 LLM 有证据判断项目实为未覆盖的“虚拟偶像线下粉丝共创空间”，系统也不会硬套 `commercial_operation` 的门店/外带/补货模板。

8. **no_match / partial_match 治理信号**
   - no_match/partial_match 会向 `classification` 注入后台治理上下文。
   - no_match 生成 `knowledge_gap_ticket`，进入 `knowledge_asset_review`。
   - no_match 生成 `new_fragment_candidate`，进入 `blueprint_fragment_review`。
   - partial_match 生成 `knowledge_gap_ticket`，但不生成新碎片候选；它表示“已有邻近碎片可迁移，但不能冒充完整专科覆盖”。
   - 治理信号保留在后台 `demand_reconstruction_context.blueprint.governance_signals`。
   - `GuidanceCard.summary` 会过滤 `governance_signals / semantic_alignment_shadow / alignment_gate / llm_semantic_scan`，避免把内部 code 泄漏到用户侧卡片。

9. **partial_match 谨慎覆盖路径**
   - 当 Stage 1 判断 `novelty_level=partial_unknown` 且至少命中一个受控规则目标时，系统会主动写入 `knowledge_coverage_ceiling`。
   - 覆盖等级固定为 `partial_specialist`，并标记 `must_not_claim_specialist_coverage=true`。
   - 规则蓝图据此生成 `knowledge_coverage_watch` 后台信号，进入 `coverage_watch_pool`。
   - Stage 3 最终综合 prompt 现在显式包含 `llm_semantic_scan`，第二轮 LLM 不再只看到“理解包”和“规则蓝图”，而能知道当前是 `strong_match / partial_match / no_match` 哪条路径。
   - 典型含义：公共图书馆儿童阅读区若叠加特殊儿童友好使用，系统可以调用公共文化邻近碎片，但必须提示覆盖边界，不能把公共文化经验伪装成特殊儿童友好专科结论。

10. **治理信号持久化入队**
   - `KnowledgeGovernanceStore` 新增公开 `enqueue_review_item(...)`，可把运行时治理信号写入 `governance_review_items`。
   - `DemandReconstructionService` 可选接收 `governance_store`，在最终蓝图确定后，把 `governance_signals` 逐条写入审核队列。
   - 入队记录统一标记 `module=demand_reconstruction`、`object_type=governance_signal`，metadata 保留原始 signal、review_queue 和 source_message_digest。
   - `/api/v2/conversation/message` 增加 `DEMAND_RECONSTRUCTION_GOVERNANCE_PERSIST` 显式开关；未开启时不连接治理库，开启时懒加载 `KnowledgeGovernanceStore` 并传入需求重构服务。
   - 持久化结果只写入后台 `blueprint.governance_persistence`，并从 `GuidanceCard.summary` 过滤，避免向用户暴露内部队列状态。

11. **规则蓝图碎片 registry 独立化**
   - `demand_reconstruction_blueprint_fragments` 已从 `scheme_advisor_semantic_axes.yaml` 拆入独立 `demand_reconstruction_blueprints.yaml`。
   - `DemandReconstructionOutputPlanner` 的蓝图片段加载器优先读取独立 registry；旧语义轴 registry 位置仅作为兼容回退。
   - 这一步不改变蓝图文案和行为，只完成资产边界拆分：通用语义轴继续负责识别框架，需求重构蓝图片段独立成为可被 Stage 2 检索的稳定资产库。

12. **Stage 1 直接驱动具体蓝图片段**
   - Stage 1 LLM Semantic Router 的 schema 增加 `recommended_fragment_targets`。
   - 每个目标必须包含 `group_id / fragment_id / confidence / evidence`；低置信或无证据目标不会进入 adapter context。
   - `DemandReconstructionOutputPlanner` 在 `life_identity / commercial / media / public_cultural / style / technical` 等 specialty group 扫描前，优先尝试 LLM 指定的 fragment。
   - 命中后在 `brief_handoff_slots` 记录 `fragment_match_source=llm_semantic_router` 与 `fragment_match_evidence`，便于后台诊断。
   - 典型效果：用户没有命中“社区文化中心”原有 trigger_terms，但第一轮 LLM 有证据判断应使用 `public_cultural_specialties.community_culture_center` 时，Stage 2 可以直接调用该碎片，而不是退回泛公共文化或关键词候选。

13. **治理审核队列最小人工处理闭环**
   - `KnowledgeGovernanceStore` 新增 `update_review_item_status(...)`，可把 `governance_review_items` 从 `pending` 更新为 `approved / rejected / ignored / pending`。
   - 状态更新会写入审计事件 `update_governance_review_item_status`，metadata 中保留 `reviewer_note` 与 `reviewed_by`。
   - 管理员接口新增 `GET /api/admin/governance-review-queue`，支持按 `tenant_id / workspace_id / review_status / review_queue` 列出治理审核项。
   - 管理员接口新增 `POST /api/admin/governance-review-queue/{item_id}/status`，支持人工处理单条治理审核项。
   - 这使 no_match / partial_match 产生的知识缺口、新碎片候选、覆盖观察等信号不再只是“写入库”，而能进入最小人工处理流程。

14. **审核通过后的反哺候选草案**
   - 当 `new_fragment_candidate` 审核项被更新为 `approved` 时，`KnowledgeGovernanceStore` 会在 metadata 中生成 `governance_followup`。
   - followup 类型为 `blueprint_fragment_candidate_draft`，包含 `fragment_id / project_object / summary / evidence / scan_result`，下一步动作为 `review_blueprint_fragment_draft`。
   - 当 `knowledge_gap_ticket` 审核项被更新为 `approved` 时，followup 类型为 `knowledge_asset_candidate_draft`，包含 `project_type / gap_type / summary / evidence / matched_targets`，下一步动作为 `review_knowledge_asset_draft`。
   - 这一步不会直接写入正式 registry 或 approved knowledge pack，只形成可追踪、可复核的半自动候选草案，避免人工批准动作直接污染稳定资产。

15. **知识缺口批准后进入知识资产 draft 表**
   - 当 `knowledge_gap_ticket` 审核项被更新为 `approved` 时，系统会基于 followup 草案创建 pending `knowledge_asset_drafts` 记录。
   - draft id 采用 `demand_gap_<hash>` 的确定性格式，并写回 `governance_followup.asset_draft_id`。
   - draft payload 记录 `title / project_type / source_gap_type / summary / evidence / matched_targets / allowed_use / not_allowed_use / evidence_level`。
   - draft source_ref 记录 `review_item_id / review_queue / reviewed_by`，形成从需求重构治理项到知识资产候选的可追踪链路。
   - 该 draft 仍需走现有知识资产审核流程，未审核通过前不会进入 approved knowledge card 或运行时召回。

16. **新碎片候选批准后进入蓝图片段 draft 表**
   - 当 `new_fragment_candidate` 审核项被更新为 `approved` 时，系统会基于 followup 草案创建 pending `blueprint_fragment_drafts` 记录。
   - draft id 采用 `blueprint_fragment_<hash>` 的确定性格式，并写回 `governance_followup.blueprint_fragment_draft_id`。
   - draft payload 记录 `fragment_id / project_object / summary / evidence / scan_result / allowed_use / not_allowed_use`。
   - draft source_ref 记录 `review_item_id / review_queue / reviewed_by`，形成从需求重构治理项到蓝图片段候选的可追踪链路。
   - 该 draft 仍需人工审核并迁入 `demand_reconstruction_blueprints.yaml` 或后续 registry patch 机制，未审核前不会进入 Stage 2 稳定规则检索。

17. **蓝图片段 draft 审核生成 registry patch 候选**
   - `KnowledgeGovernanceStore` 新增 `approve_blueprint_fragment_draft(...)`。
   - pending `blueprint_fragment_drafts` 被批准后，draft 状态更新为 `approved`，payload 写入 `registry_patch`。
   - registry patch 明确 `registry_file=intelligent_project_analyzer/config/registries/demand_reconstruction_blueprints.yaml`、`target_root=demand_reconstruction_blueprint_fragments`、`operation=manual_merge_required`。
   - patch 中保留 `fragment_id / project_object / task_reframe / primary_risk / evidence / source_summary`，供后续人工补全 sections/key_forks/unknowns 后迁入稳定 registry。
   - 管理员接口新增 `POST /api/admin/governance-review-queue/blueprint-fragment-drafts/{draft_id}/approve`，可触发蓝图片段 draft 审核并返回 registry patch 候选。
   - 该步骤仍不自动写入 YAML，避免未经完整人工编辑的候选片段污染稳定规则资产。

18. **知识资产 draft 后台审批入口**
   - 管理员接口新增 `POST /api/admin/governance-review-queue/knowledge-asset-drafts/{draft_id}/approve`。
   - 该接口复用 `KnowledgeGovernanceStore.approve_asset_draft(...)`，将 pending `knowledge_asset_drafts` 批准为 approved knowledge card。
   - 这使 `knowledge_gap_ticket -> pending knowledge_asset_drafts -> approved knowledge card` 的人工审核路径具备后台入口。
   - 审核通过后才可进入现有 approved knowledge card / runtime recall 路径，保持“候选不直接运行时可用”的治理边界。

19. **approved knowledge card 回流需求重构 Stage 2/3**
   - `DemandReconstructionService` 在构建蓝图前会扫描治理库中的 approved knowledge cards。
   - 扫描使用当前 session 的 `tenant_id / workspace_id / user_id`，只读取对当前用户可见且 `review_status=approved` 的知识卡。
   - 匹配依据来自 Stage 1 LLM Semantic Router 的 `project_object / space_candidates / core_tensions / recommended_scan_targets`，以及用户原文和规则候选。
   - 命中后注入 `adapter_context.governed_knowledge_assets`，并在 `context_source.governed_knowledge_assets=true` 标记来源。
   - 召回门控已升级为结构化匹配：文本相关性只是必要条件，仍需命中 `package_ids`、`ontology_dimension_ids`，或具备 `expert_review / approved_review / e2_research / e3_case / validated_asset` 等强证据等级之一，避免弱文本卡误入 Stage 3。
   - Stage 1 semantic package, knowledge_gap_ticket, pending knowledge_asset_drafts, and approved knowledge card approval now preserve `package_ids / ontology_dimension_ids`, so governed assets can be consumed by structural recall gating.
   - 注入内容保留 `package_ids / ontology_dimension_ids / match_metadata`，Stage 3 prompt 可看到命中来源、结构锚点与证据强度，而不只看到卡片标题摘要。
   - `DemandReconstructionInsightProtocol` 会把治理知识资产压缩进 Stage 3 prompt，使最终综合能看到 `title / summary / evidence / allowed_use / not_allowed_use / evidence_level / package_ids / ontology_dimension_ids / match_metadata`。
   - 这一步只消费 approved knowledge card，不扫描 pending draft 或 review item，保持候选不进入运行时的治理边界。

20. **蓝图片段 registry patch 导出入口**
   - `KnowledgeGovernanceStore` 新增 `get_blueprint_fragment_registry_patch(...)`。
   - `KnowledgeGovernanceStore.get_blueprint_fragment_registry_patch(...)` 现在同时返回 `registry_patch` 与 `registry_patch_yaml`，使 CLI、后台接口和后续人工合并工具可以复用同一导出格式。
   - 已批准且带 `registry_patch` 的 `blueprint_fragment_drafts` 可被重新读取，未批准或没有 patch 的 draft 会被拒绝导出。
   - 管理员接口新增 `GET /api/admin/governance-review-queue/blueprint-fragment-drafts/{draft_id}/registry-patch`。
   - 接口返回结构化 `registry_patch` 与 `registry_patch_yaml`，便于人工复制、审查、补全 sections/key_forks/unknowns 后合并到 `demand_reconstruction_blueprints.yaml`。
   - 该导出仍保持 `manual_merge_required`，不自动写入稳定 YAML。

21. **前端 503 智能识别不可用提示**
   - 前端新增 `buildConversationErrorMessage(...)`，识别后端 503 detail `智能识别暂不可用，请重试`。
   - 普通对话发送与引导卡响应失败时，不再只写 `console.error`，而会追加 assistant 消息。
   - 用户可见文案明确说明“没有使用规则蓝图降级生成”，与后端 LLM-first 硬失败契约保持一致。
   - 该行为已通过 `conversationErrorMessage.test.ts` 覆盖，避免回退成泛化“服务维护中”或静默失败。

### 14.2 尚未完成

1. **Stage 2 规则蓝图扫描仍未完全由 Stage 1 理解包驱动**
   - 当前已完成有证据候选对 archetype/候选集的提权。
   - 当前已完成有证据 `recommended_fragment_targets` 对 specialty fragment 的直接提权。
   - 当前已完成 approved knowledge cards 对 Stage 1 理解包与原文的相关性扫描，并注入 Stage 3 综合上下文。
   - 当前已完成包/维度/证据强度共同参与的 approved card 召回门控，弱文本相关卡不会直接进入 Stage 3。
   - Completed propagation of `package_ids / ontology_dimension_ids` from Stage 1 semantic packages into `knowledge_gap_ticket`, pending `knowledge_asset_drafts`, and approved knowledge cards.
   - 但治理样本扫描、全部子变体的长期治理闭环、包/维度 taxonomy 的补全，以及跨空间类型的召回阈值治理仍未完成。

2. **规则蓝图碎片库仍需继续迁移**
   - 现有代码已经具备碎片优先机制。
   - 独立 registry 文件已建立，综合语义轴 YAML 不再混放 `demand_reconstruction_blueprint_fragments`。
   - 但部分 builder、子变体、硬编码分支仍需要继续迁入统一碎片资产，并由 Stage 1 输出驱动检索。

3. **未覆盖长尾项目的诚实路径仍需继续产品化**
   - 当前已实现 no_match 阻断关键词模板劫持，并转入 `general_project` 探索蓝图。
   - 当前已生成 `knowledge_gap_ticket` 与 `new_fragment_candidate` 后台信号。
   - 当前已实现 partial_match 的 `partial_specialist` 覆盖天花板与 `knowledge_coverage_watch` 观察信号。
   - 当前已支持将这些信号写入 `governance_review_items` 审核队列。
   - 当前已支持后台列表和最小人工状态处理。
   - 当前已支持 `new_fragment_candidate / knowledge_gap_ticket` 在审核通过后生成半自动候选草案。
   - 当前已支持 `knowledge_gap_ticket` 审核通过后进入 pending `knowledge_asset_drafts`。
   - 当前已支持 `new_fragment_candidate` 审核通过后进入 pending `blueprint_fragment_drafts`。
   - 当前已支持蓝图片段 draft 审核后生成 registry patch 候选。
   - 当前已支持已批准蓝图片段 draft 的 registry patch 重新导出为结构化数据与 YAML 文本。
   - 当前已支持知识资产 draft 通过后台接口批准进入 approved knowledge card。
   - 当前已支持 approved knowledge card 被需求重构 Stage 2 扫描，并注入 Stage 3 LLM 综合上下文。
   - 当前已支持 approved knowledge card 以文本命中 + 包/维度结构锚点或强证据等级作为召回门控，并向 Stage 3 保留 match metadata。
   - Knowledge-gap approval now preserves `package_ids / ontology_dimension_ids`: governance signals enter knowledge asset drafts, and approved cards retain the structural anchors after review.
   - 当前已支持审核后的蓝图片段 registry patch 通过管理员显式 apply 动作写入 `demand_reconstruction_blueprints.yaml` 的 `governed_candidates`，并把 patch 状态更新为 `applied`。
   - 当前已支持治理复核中心对已批准的蓝图片段 draft 显示“应用到蓝图 registry”按钮，调用后端 apply endpoint 完成显式迁入。
   - 但 approved knowledge card 的包/维度 taxonomy 仍需要持续治理，后续还需补充跨空间类型召回阈值、批量迁移治理和更完整的前端状态展示。

4. **前端错误体验已完成桌面浏览器链路核验**
   - 后端已返回 503 与明确文案。
   - 前端已将该错误追加为 assistant 气泡，明确提示智能识别不可用且未降级生成。
   - 已在真实浏览器中打开 `/analysis/demo`，拦截 `/api/v2/conversation/message` 为 503，确认右侧“方案高参”对话流可见 `智能识别暂不可用，请重试` 与 `没有使用规则蓝图降级生成`。
   - 后续仍需补充移动端窄屏布局和更多真实后端错误分支的视觉回归。

### 14.3 v1.25 结论

v1.25 completes the first implementation batch for the LLM-first chain, including semantic routing, explicit LLM failure, Stage 1 driven Stage 2 selection, no_match/partial_match governance, review queues, draft creation, registry patch export/apply, approved knowledge card Stage 2/3 recall, structured approved-card recall gating, knowledge-gap taxonomy propagation, default public-cultural primary fragment migration, and standalone blueprint fragment registry.
default public_cultural_experience now renders from `registry:primary_archetypes.public_cultural_experience` instead of the older generic exhibition fallback when no more specific specialty is proven;

```text
规则蓝图不再是启用 LLM 时的默认首屏作者；
LLM 先行理解已经进入主链路；
有证据的 LLM 语义候选已经可以驱动规则蓝图候选排序；
有证据的 LLM fragment target 已经可以直接驱动 Stage 2 调用具体 registry 碎片；
未知长尾项目不会再被关键词模板强行接管；
未知长尾项目会产生后台知识缺口与新碎片候选信号；
部分命中的项目会进入 partial_specialist 覆盖天花板；
第二轮 LLM 能显式看到 llm_semantic_scan，并据此控制承诺深度；
治理信号不再只能停留在运行时上下文，可进入治理审核队列；
治理审核队列不再只是入库，可被管理员列出、过滤和人工更新状态；
被批准的新碎片候选和知识缺口可以生成可追踪的 followup 草案；
被批准的知识缺口可以进入 pending knowledge_asset_drafts，继续走现有知识资产审核流；
被批准的新碎片候选可以进入 pending blueprint_fragment_drafts，继续走蓝图片段人工审核/迁移流；
被批准的蓝图片段 draft 可以生成 manual_merge_required registry patch 候选；
已批准的 registry patch 可以通过管理员显式 apply 动作写入独立蓝图 registry 的 governed_candidates；
治理复核中心已经提供“应用到蓝图 registry”的前端操作入口，管理员不再只能通过后端接口触发迁入；
已批准的蓝图片段 draft 可以导出结构化 registry patch 与 YAML 文本，供人工合并；
store 层与 API 层共享同一份 registry_patch_yaml 导出结果；
前端遇到需求重构 LLM-first 503 硬失败时，会追加用户可见的 assistant 错误气泡；
被批准的知识资产 draft 可以通过后台入口进入 approved knowledge card 流；
approved knowledge card 可以被需求重构 Stage 2 扫描，并以文本相关 + 包/维度/强证据门控进入 Stage 3 LLM 综合 prompt；
规则蓝图片段已经从通用语义轴 registry 中拆出，成为独立资产库；
LLM 全链不可用时系统明确失败，不再用规则蓝图假装智能识别成功。
```

但完整目标仍是下一步：

```text
Stage 1 理解包真正驱动 Stage 2 规则/碎片/知识资产扫描；
未覆盖问题进入诚实探索路径；
最终再由 Stage 3 LLM 受控综合。
```

---

## 15. 最终判断

需求重构要成为真正智能的第一环节，不能把规则蓝图放在入口位置。

最优架构应是：

```text
LLM 先做开放语义理解；
规则蓝图只承接系统已经稳定掌握的部分；
未覆盖问题走探索型重构和知识治理；
最终再由 LLM 生成用户唯一可见结果。
```

v1.19 的进一步结论是：

```text
LLM-first 主链路必须真实依赖 LLM。
多供应商梯度可以提高可用性；
但梯度全挂时，应明确失败，而不是用规则蓝图假装智能识别成功。
规则蓝图应作为独立稳定资产被检索，而不是继续混在通用语义轴配置里。
Stage 1 不只负责选择大类，也应能用证据把 Stage 2 导向具体稳定碎片。
治理闭环至少需要“信号入队 -> 后台列表 -> 人工状态处理”三步，当前已经形成第一版可操作链路。
```

这样系统才不会停留在“规则枚举系统”，而会变成：

> LLM 驱动的语义理解系统 + 稳定规则资产库 + 可进化知识治理闭环。




