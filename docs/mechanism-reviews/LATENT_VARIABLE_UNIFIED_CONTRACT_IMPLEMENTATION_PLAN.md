# 潜变量统一数据契约实施计划（专题）

版本：v1.1
日期：2026-06-20
修订定位：结合三份参考意见完成交叉校验，补齐人本潜变量、证据化情感判断、历史算法沉淀回收与实施路线修正。

> 面向开放问题的需求重构机制升级方案（非硬编码）

---

## 1. 背景与问题定义

当前系统已具备以下能力：

- 语义轴识别（`semantic_axes`）
- 主张力排序（`main_tensions`）
- 洞察包结构（`insight_packet`）
- 规则蓝图生成与边界约束

但潜变量仍分散在多个对象，导致：

1. 入口分诊、需求重构、追问生成、质量门禁之间复用成本高。
2. 方法论型/高抽象问题容易被门控跳过，无法稳定进入“深刻重构”路径。
3. 证据链与置信度未形成统一契约，治理和回归成本较高。

本专题目标是把分散字段统一为 `latent_model.v1`，形成可演进的数据中台层。

---

## 2. 目标与非目标

### 2.1 目标

1. 建立统一潜变量契约 `latent_model.v1`。
2. 将项目型与方法论型输入纳入同一分诊与重构框架。
3. 建立“潜变量-证据-置信度-决策边界”闭环。
4. 用 190 条压力集作为回归门禁，持续验证泛化能力。

### 2.2 非目标

1. 本阶段不重写全部重构文案模板。
2. 本阶段不替换现有知识资产审核流程。
3. 本阶段不引入新外部依赖服务。

---

## 3. 统一契约（字段级）

### 3.1 顶层结构

```json
{
  "schema_version": "latent_model.v1",
  "mode": "project_reconstruction|methodology_reconstruction",
  "input_frame": {},
  "latent_variables": {},
  "tensions": [],
  "hypotheses": [],
  "uncertainty_ledger": [],
  "decision_frontier": {},
  "evidence_index": [],
  "quality_gate": {},
  "provenance": {}
}
```

### 3.2 MVP 必填最小集

1. `mode`
2. `input_frame.intent_strength`
3. `latent_variables.identity_drivers`（至少 1 条）
4. `tensions`（至少 1 条）
5. `hypotheses`（至少 2 条）
6. `uncertainty_ledger`（至少 2 条）
7. `decision_frontier.first_decision`
8. `evidence_index`（至少 3 条）
9. `quality_gate.pass`

### 3.3 核心字段约束

1. 任意 `inferred/speculative` 项必须有 `evidence_refs`。
2. `tensions` 为空或全部低强度时，`quality_gate.pass=false`。
3. `mode=methodology_reconstruction` 时允许 `project_anchor_strength` 较低，但 `semantic_density` 不得为空。

---

## 4. 现有系统映射

| 现有来源 | 目标字段 | 说明 |
|---|---|---|
| `semantic_axes` | `latent_variables.*` | 主体、驱动、场景、约束映射 |
| `main_tensions` | `tensions` | 张力候选标准化 |
| `insight_packet.inferred_intents` | `latent_variables.identity_drivers` | 隐含意图沉淀 |
| `missing_slots` | `uncertainty_ledger` | 未知数账本 |
| `routing_recommendation` | `decision_frontier.routing_recommendation` | 路由决策依据 |

---

## 5. 分阶段实施计划

## 5.1 Phase P0：契约落地与旁路接入（1 周）

### 目标

在不破坏现网行为的前提下，引入 `latent_model.v1` 旁路生成。

### 任务

1. 新增契约模型（Pydantic）：`latent_model.py`。
2. 新增适配器：将 `context_adapter + insight_packet` 转换为 `latent_model`。
3. 在 `demand_reconstruction_service` 中增加旁路构建开关（默认只记录，不影响输出）。
4. 增加结构校验与降级保护：无效结构不阻断主链。

### 交付物

1. 数据模型代码
2. 适配器代码
3. 单测（契约校验、映射校验）

### 验收

1. 现有测试集通过率无回退。
2. 至少 95% 输入可生成合法 `latent_model`。

## 5.2 Phase P1：入口分诊升级为多轨路由（1-2 周）

### 目标

从“是否进入需求重构”升级为“多轨语义路由”。

### 任务

1. 将 `should_enter_demand_reconstruction` 从 bool 语义升级为路由枚举：
   - `project_reconstruction`
   - `methodology_reconstruction`
   - `naming_copy`
   - `reference_material`
   - `competition_strategy`
2. 对 `methodology_reconstruction` 输出“问题空间蓝图”，不再 gate_skip。
3. 对 `formal_bypass` 场景增加“短版重构前置层”。

### 交付物

1. 路由器改造代码
2. 路由单测与回归集

### 验收

1. 190 条压力集 `gate_skip + formal_bypass` 数量下降 60% 以上。
2. 方法论问题进入可解释路径（非空输出率 > 95%）。

## 5.3 Phase P2：张力-假设-未知数闭环（1 周）

### 目标

把潜变量从“标签层”升级到“推理层”。

### 任务

1. 新增 `hypotheses` 生成器（至少 2 条候选 + 可证伪条件）。
2. 新增 `uncertainty_ledger` 优先级排序。
3. 新增 `decision_frontier`（先决判断/延后判断）。
4. 输出层绑定：重构文案必须引用至少一条高强度张力。

### 验收

1. 结构完整率（`tensions+hypotheses+uncertainty_ledger`）> 90%。
2. 浅层重构（无关键张力）比例下降 50% 以上。

## 5.4 Phase P3：质量门禁与治理闭环（1 周）

### 目标

将潜变量质量纳入系统门禁与治理流水线。

### 任务

1. 新增 `quality_gate` 评分器：结构、证据覆盖、张力锐度、反套话。
2. 将 `quality_gate.pass=false` 的样本写入治理队列。
3. 新增周报：漏检类型、张力弱化类型、证据不足类型。

### 验收

1. 回归运行可稳定输出质量报告。
2. 治理队列可追踪到具体字段与证据项。

---

## 6. 代码改造清单（建议）

### 6.1 新增文件

1. `intelligent_project_analyzer/core/latent_model.py`
2. `intelligent_project_analyzer/services/latent_model_adapter.py`
3. `tests/unit/test_latent_model_contract.py`
4. `tests/services/test_latent_model_adapter.py`

### 6.2 修改文件

1. `intelligent_project_analyzer/services/demand_reconstruction_service.py`
2. `intelligent_project_analyzer/services/scheme_advisor_semantic_axes.py`
3. `intelligent_project_analyzer/services/demand_reconstruction_insight_protocol.py`
4. `intelligent_project_analyzer/services/demand_reconstruction_context_adapter.py`

---

## 7. 回归与验证方案

### 7.1 数据集

1. `sf/2026.3.22/模拟问题集合.txt`（190 条）
2. 线上抽样会话（匿名）

### 7.2 指标

1. 结构合法率：`latent_model` 校验通过占比
2. 路由覆盖率：多轨路由命中分布
3. 漏检率：被跳过但应进入重构的问题比例
4. 张力锐度：高强度张力占比
5. 证据覆盖率：推断字段带证据引用占比

### 7.3 门禁阈值（初版）

1. 结构合法率 >= 95%
2. 漏检率 <= 5%
3. 证据覆盖率 >= 90%

---

## 8. 风险与回滚策略

### 风险

1. 新增契约导致推理耗时上升。
2. 路由改造引发旧行为漂移。
3. 证据约束过严导致输出空洞。

### 回滚

1. 所有新路径加特性开关：`LATENT_MODEL_ENABLED`、`LATENT_ROUTER_ENABLED`。
2. 保留旧路径并支持按会话级灰度回退。
3. 关键异常时自动降级到现有重构流程。

---

## 9. 里程碑与负责人建议

1. M1（P0 完成）：契约模型与旁路适配上线（负责人：后端）
2. M2（P1 完成）：多轨路由上线并通过 190 条回归（负责人：后端 + 算法）
3. M3（P2 完成）：张力-假设-未知数闭环接入输出（负责人：算法）
4. M4（P3 完成）：质量门禁与治理报表上线（负责人：平台 + 治理）

---

## 10. 立即可执行的首周任务

1. 建立 `latent_model.v1` Pydantic 模型与字段校验。
2. 实现 `latent_model_adapter`，先做旁路产物，不影响现网响应。
3. 增加 190 条批测脚本输出 `latent_model` 结构统计。
4. 完成 P0 评审：确认字段定义、证据规则、降级策略。

---

## 11. 预期效果

1. 需求重构从“规则枚举驱动”转向“潜变量推理驱动”。
2. 对开放问题保持稳定解释力，不依赖单案例硬编码。
3. 形成可持续治理闭环：可测、可追踪、可迭代。
---

## 12. v1.1 交叉校验结论

本节用于回应三份参考意见，不做拼盘式采纳。每条意见都按“采纳 / 修正采纳 / 不采纳但保留风险”的方式处理。

### 12.1 参考1：从“项目+施工风险”转向“人+人生叙事”

**判断：修正采纳。**

参考1指出的根因成立：当前 LLM Semantic Router 更偏向 `project_object`、`space_candidates`、`core_tensions`、`recommended_scan_targets`，对“50岁、背井离乡、室内设计师、老家民居”这类人的生命阶段、职业身份和返乡意义，没有稳定的一等字段承接。

但不能简单理解为“增加共情”。系统之前设置反套话门，是为了避免空洞暖词、情感按摩和不推进判断。真正要改的是：

```text
禁止无证据的情感套话；
允许并鼓励有原文证据、能改变后续判断的情感/身份/人生阶段判断。
```

因此 v1.1 不把“温暖表达”作为目标，而把“证据化的人本判断”作为目标。

### 12.2 参考2：190 题逐条测试与机制级优化

**判断：采纳其测试方向，修正其实施侧重点。**

参考2的价值在于把问题从单案例扩展到 190 条开放题，并指出 `gate_skip`、`formal_bypass`、方法论/命名/城市策略类输入被门控跳过的问题。这与本专题的多轨路由目标一致。

但参考2偏重入口覆盖与结构完整度，仍不足以解决“进入了但不深刻”的问题。因此本计划把它并入两层门：

1. 路由门：解决能不能进入、多轨怎么走。
2. 洞察门：解决进入后是否抓住真实命题。

### 12.3 参考3：潜变量统一契约

**判断：作为主实施底座采纳，但必须补人本字段与反套话修正。**

参考3提供了 `latent_model.v1` 的字段级骨架，适合作为跨入口、需求重构、追问生成、质量门的统一数据契约。但原草案对“人”的表达仍偏泛化，需要补充更明确的人本潜变量层：

- `person_profile`
- `life_stage_signals`
- `professional_identity`
- `returning_home_signals`
- `belonging_and_memory_drivers`
- `evidence_bound_affect`
- `forbidden_capture_paths`

这些字段不是为了给用户贴标签，而是为了防止人的线索在规则扫描阶段被空间类型、技术约束或风格模板吞掉。

---

## 13. 冲突排查与处理决定

### 13.1 冲突一：加人本洞察 vs 防止空洞共情

**冲突描述：** 参考1要求系统读懂人的人生叙事；现有反套话门会压制“归属感、家的感觉、温暖”等表达。

**处理决定：** 反套话门不删除，但升级为“证据化反套话门”。

实施要求：

1. 如果情感词没有 evidence_ref，仍然判为套话。
2. 如果情感判断能回指原文，如“50岁”“长期离家”“老家”“乡土复杂情感”，则不得被 `_CLICHE_TERMS` 一刀切误杀。
3. `quality_gate` 增加 `evidence_bound_affect_score`，区分空洞暖词与有证据的人本判断。

### 13.2 冲突二：规则蓝图稳定性 vs LLM-first 开放理解

**冲突描述：** 规则蓝图稳定可审计，但会把长尾问题压成邻近模板；LLM 开放理解更强，但有幻觉风险。

**处理决定：** 保持 LLM-first，但让 latent model 成为中间证据层。

实施要求：

1. 第一轮 LLM 不直接写答案，只生成 `latent_model` 候选。
2. 规则、语义轴、知识包只扫描和校正 `latent_model`。
3. Final Synthesis 必须引用 `evidence_index` 与 `tensions`，不能自由发挥。

### 13.3 冲突三：方法论/命名/城市策略是否进入需求重构

**冲突描述：** 旧入口倾向具体项目；190 题里有方法论、命名、城市轴线、行为经济学体验馆等高抽象输入。

**处理决定：** 不再用 bool 判断“进/不进”，改为多轨路由。

实施要求：

```text
project_reconstruction
methodology_reconstruction
naming_copy_reconstruction
competition_strategy_reconstruction
urban_strategy_reconstruction
research_case_reconstruction
```

这些轨道都允许生成 `latent_model`，但输出深度和交付边界不同。

### 13.4 冲突四：空间被雇佣是功能任务还是存在意义

**冲突描述：** 历史方法里“空间被雇佣”容易被读成功能任务，导致“回乡民居”被转成使用频率、维护成本和施工容错。

**处理决定：** 保留“空间被雇佣”，但拆成两层。

```text
functional_job：空间承担什么行为/运营/技术任务。
existential_job：空间承担什么人生/关系/身份/记忆任务。
```

Q16 这类输入必须优先判断 `existential_job`，再判断 `functional_job`。

---

## 14. 历史沉淀回收清单

本专题不得从零发明潜变量层。系统中已有大量历史方法、算法与模块，应按以下方式回收。

### 14.1 现行运行时能力

1. `scheme_advisor_semantic_axes.yaml`
   - 可回收：`subject_profiles`、`founding_drivers`、`problem_modes`、`input_intents`。
   - 映射：进入 `latent_variables.subject_profile`、`identity_drivers`、`input_frame`。

2. `scheme_advisor_semantic_axes.py`
   - 可回收：`derive_semantic_axes()`、`rank_main_tensions()`。
   - 映射：进入 `latent_variables` 与 `tensions`。

3. `demand_reconstruction_context_adapter.py`
   - 可回收：现有 `semantic_axes`、`main_tensions`、`semantic_candidate_set` 构建路径。
   - 映射：作为 `latent_model_adapter` 的第一输入源。

4. `demand_reconstruction_insight_protocol.py`
   - 可回收：字面事实、隐含意图、核心张力、第一性剥离、空间被雇佣、未知边界、锐度自检。
   - 修正：补 `person_profile`、`existential_job`、`evidence_bound_affect`，并升级反套话门。

### 14.2 历史深度分析能力

1. `intelligent_project_analyzer/core/four_step_flow_types.py`
   - 可回收：`implicit_motivations`、`L3CoreTension`、`L5SharpnessTest`。
   - 映射：`hypotheses`、`tensions`、`quality_gate.tension_sharpness_score`。

2. `intelligent_project_analyzer/utils/insight_methodology.py`
   - 可回收：`HUMAN_DIMENSIONS`、`TENSION_PATTERNS`、`parse_core_tension()`、`extract_human_dimensions()`。
   - 映射：`person_profile`、`evidence_bound_affect`、`tensions.pole_a/pole_b`。

3. `docs/requirements/STEP1_DEEP_ANALYSIS_REQUIREMENTS_v1.0.md`
   - 可回收：L1 隐性动机、L3 核心张力、L5 锐度测试的字段约束。
   - 映射：`latent_variables`、`tensions`、`quality_gate`。

4. `docs/historical/SIMULATED_FRONTEND_OUTPUT_HAY_EMEISHAN.md`
   - 可回收：`L4_underlying_motivations`、`L5_latent_expectations`。
   - 映射：`hypotheses` 与 `uncertainty_ledger`。

5. `docs/historical/COMPLETE_L1_L5_SIMULATION_HAY_EMEISHAN.md`
   - 可回收：完整 L1-L5 示例链路。
   - 映射：作为 `latent_model.v1` 金标准样例，不直接进线上 prompt。

### 14.3 不应回收的部分

1. 不回收“长篇深度分析”的前台展示形态。
2. 不回收内部术语，如 L1-L5、JTBD、锐度测试、核心张力的用户可见表达。
3. 不回收无证据的情感形容词堆叠。
4. 不回收会导致首屏过长的完整方案生成流程。

---

## 15. v1.1 契约修正

在 v1.0 字段基础上，补充以下字段。

### 15.1 `person_profile`

```json
{
  "person_profile": [
    {
      "id": "middle_age_returning_designer",
      "label": "职业后半场的返乡设计师",
      "life_stage": "mid_life",
      "professional_identity": "interior_designer",
      "relationship_to_place": "returning_home",
      "confidence": 0.86,
      "evidence_refs": ["ev_age_50", "ev_designer", "ev_long_left_home"],
      "status": "observed"
    }
  ]
}
```

### 15.2 `existential_job`

```json
{
  "existential_job": {
    "statement": "这栋民居被拿来安放职业后半场、故乡关系和家族记忆，而不只是解决居住功能。",
    "confidence": 0.82,
    "evidence_refs": ["ev_age_50", "ev_hometown", "ev_rural_emotion"],
    "decision_impact": "决定首屏应先讨论回归与身份，而不是先问面积、预算、宅基地。"
  }
}
```

### 15.3 `evidence_bound_affect`

```json
{
  "evidence_bound_affect": [
    {
      "affect_id": "returning_home_belonging",
      "claim": "用户的问题包含返乡与身心安放诉求。",
      "allowed_terms": ["回归", "故乡", "身心安放"],
      "evidence_refs": ["ev_long_left_home", "ev_hometown"],
      "cliche_risk": "low"
    }
  ]
}
```

### 15.4 `forbidden_capture_paths`

```json
{
  "forbidden_capture_paths": [
    {
      "path": "style_semantics_first",
      "reason": "原文中的安藤忠雄只是表达假设，不应压过返乡和职业身份命题。",
      "evidence_refs": ["ev_ando", "ev_long_left_home"]
    },
    {
      "path": "hard_constraint_first",
      "reason": "当前问题不是施工容错优先，而是人生阶段与故乡关系优先。",
      "evidence_refs": ["ev_age_50", "ev_hometown"]
    }
  ]
}
```

---

## 16. 修正后的实施路线

### P0：历史资产回收与契约补强

1. 从 `InsightMethodology` 回收人性维度和张力解析函数。
2. 从 `four_step_flow_types` 回收 L1 隐性动机、L3 张力、L5 锐度结构。
3. 从历史 L1-L5 文档抽 10 个金标准样例，作为测试夹具。
4. 将 v1.0 契约升级为 v1.1，新增 `person_profile`、`existential_job`、`evidence_bound_affect`、`forbidden_capture_paths`。

### P1：LLM Semantic Router schema 升级

1. 在 Semantic Router 输出中新增 `person_profile`。
2. 每条 person/profile/affect 判断必须带 `evidence`。
3. `project_object` 不再是唯一主锚点；当 person/profile 置信度高于空间类型时，首屏以人的命题为先。

### P2：反套话门升级

1. 将 `_CLICHE_TERMS` 从“一刀切禁止词”改为“无证据禁止词”。
2. 如果命中归属、家的感觉、温暖、身心安放等词，但有 evidence_ref 且改变后续判断，则允许。
3. 如果没有 evidence_ref，则仍然进入 cliche rejection。

### P3：多轨路由与 190 题回归

1. bool 路由升级为多轨路由。
2. 方法论、命名、竞标、城市策略都必须进入对应 reconstruction mode。
3. 190 题回归报告新增三项：`person_signal_loss_count`、`wrong_capture_count`、`evidence_bound_affect_pass_rate`。

---

## 17. v1.1 验收补充

1. Q16 输出必须优先命中“职业后半场 / 故乡关系 / 身心安放 / 家族记忆”中的至少 3 项。
2. 如果输出使用“归属感、回归、温暖、身心安放”等词，必须能在 `evidence_index` 中找到对应原文证据。
3. `style_semantics_first` 和 `hard_constraint_first` 对 Q16 必须进入 `forbidden_capture_paths`。
4. Q2、Q8、Q34、Q59、Q181、Q187、Q190 必须各自有至少 1 条 person、symbolic、cognitive、ethical 或 relationship 潜变量。
5. 用户可见输出不得出现 L1-L5、latent_model、JTBD、核心张力、锐度测试等内部术语。
6. 190 题回归不只统计 handled，还必须统计 `trust_pass` 与 `evidence_bound_affect_pass_rate`。

