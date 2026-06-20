# 需求重构洞察质量提升实施计划

版本：v1.0  
日期：2026-06-20  
定位：在 LLM-first 需求重构架构之上，补齐“深刻洞察”质量门与 190 题验收机制  
范围：面向 `sf/2026.3.22/模拟问题集合.txt` 暴露出的开放问题，不做单题硬编码，建立可实现、可测试、可迭代的机制级实施计划

---

## 0. 核心结论

当前需求重构机制已经解决了一部分“能不能进来、能不能分流、能不能给框架”的问题，但还没有稳定解决“用户是否觉得系统真的懂他”的问题。

190 题审计显示：

- 已有压力测试产物 `.tmp/pressure-current/scheme-advisor-pressure-test-current.json` 中，`190/190` 为 pass。
- 其中 `183` 条为 project，`7` 条为 methodology。
- 但 `183/190` 都是 `partial_specialist`。
- `102` 条有 `coverage_gap`，`102` 条有 `knowledge_gap_ticket`，`131` 条需要 activation pack candidate。

这说明当前 pass 更偏向“链路通过”，不是“洞察通过”。下一步不能继续补规则，而要把“深刻”变成可检查的机制。

目标不是为“50岁男性室内设计师返乡建民居”写一条特例，而是建立一种通用能力：

```text
用户输入
  ↓
高价值语义保真
  ↓
主命题竞争
  ↓
规则 / 知识 / 算法资产扫描
  ↓
反捕获质量门
  ↓
LLM 受控综合
  ↓
用户可见的可信需求重构
```

---

## 1. 本轮要解决的问题

### 1.1 不是覆盖率问题，而是洞察质量问题

当前机制可以把多数问题放进空间类型、语义轴、知识覆盖和二轮追问里，但很多输出仍然停留在项目类型、技术约束、风格语义、商业运营或通用下一步追问。这些判断不一定错，但常常没有抓住“为什么这个用户会这样问”。

### 1.2 典型失败形态

| 样本 | 应抓住的命题 | 容易误捕获为 |
|---|---|---|
| Q2 第一代创业者深圳湾别墅 | 成就象征、家族传承、内心回归 | 硬约束或普通豪宅 |
| Q8 自闭症儿童三代之家 | 感统支持、照护秩序、家庭长期共居 | 声学 / 技术专项 |
| Q16 返乡设计师民居 | 职业后半场、故乡关系、精神安放 | 风格标签 / 乡建模板 |
| Q26 文华东方竞标 | 弱势团队如何赢竞标 | 酒店大堂运营 |
| Q34 诗人书房 | 意象到空间语言转译 | 技术性能 / 文化泛谈 |
| Q59 哲学教授住宅 | 存在、虚无、自我对话 | 普通家庭秩序 |
| Q126 地下未来居住 | 地下高密度生活原型 | 极寒生命支持 |
| Q181 行为经济学体验馆 | 抽象认知概念如何空间化 | 普通展陈 |
| Q187 注意力经济办公室 | 认知负荷、专注力、信息过载 | 普通办公效率 |
| Q190 后人类伦理实验室 | 技术伦理与空间边界 | 普通技术空间 |

---

## 2. 设计原则

1. 不硬编码单题。所有能力都必须抽象为语义保真、主命题竞争、反捕获、质量门或知识资产沉淀。
2. LLM 先理解，但不能裸奔。LLM 负责开放语义理解；规则、registry、知识包负责边界、证据和稳定性。
3. 规则是后台资产，不是首屏作者。规则可以被调用，但不能压过用户输入里的年龄、职业、故乡、关系、隐喻、经营压力等高价值信息。
4. 通过分层。`pass` 不再只有一个含义，至少拆成 routing pass、semantic pass、insight pass、trust pass。
5. 先评估，再扩写。不先增加长答案，而是先确保第一屏真实问题重写足够准确。

---

## 3. 目标状态

### 3.1 新增四级质量状态

```text
routing_pass
  能识别这是项目、方法论、命名、竞赛、城市策略或其他可处理输入。

semantic_pass
  保留了关键事实、主体、约束、隐喻和目标。

insight_pass
  重写出了真实问题，并指出真正卡点。

trust_pass
  首屏表达能建立用户信心，让用户觉得“它懂我”。
```

### 3.2 需求重构首屏必须完成三件事

1. 真实问题重写：用户表面在问什么，实际在解决什么。
2. 关键判断：这个项目真正卡在哪里，或者最值得抓住的命门是什么。
3. 下一步追问：只问一个最能改变判断的问题。

### 3.3 高价值信息不可丢失

以下信息一旦出现在用户输入中，就必须被纳入判断链：年龄 / 人生阶段、职业身份、返乡 / 故乡 / 离乡、家庭结构、情感修复、文化隐喻、哲学 / 伦理 / 精神命题、经营压力 / 竞标策略、技术硬约束、城市 / 社区 / 公共价值。

---

## 4. 文件级实施计划

### Task 1：新增洞察质量评估器

新增文件：

- `intelligent_project_analyzer/services/demand_reconstruction_insight_quality.py`
- `tests/unit/test_demand_reconstruction_insight_quality.py`

职责：

- 从原始输入中识别高价值语义信号；
- 检查这些信号是否进入 `task_reframe`、`primary_risk`、`visible_reply`；
- 判断是否发生技术、风格、运营模板的过度捕获；
- 输出 `insight_quality` 结构。

建议输出结构：

```python
{
    "level": "semantic_pass",
    "preserved_signals": ["life_stage", "professional_identity"],
    "missing_high_value_signals": ["returning_home"],
    "dominant_proposition": "life_identity_reconciliation",
    "anti_capture_checks": {
        "technical_over_capture": "pass",
        "style_over_capture": "fail",
        "operation_over_capture": "pass",
    },
    "blocking_issues": [],
    "warning_issues": [
        {
            "code": "high_value_signal_loss",
            "message": "用户输入中的高价值语义没有进入需求重构首屏。",
        }
    ],
}
```

首批单测必须覆盖 Q16、Q34、Q181、Q187。

验收命令：

```bash
.\.conda\python.exe -m pytest tests/unit/test_demand_reconstruction_insight_quality.py -q
```

---

### Task 2：接入 `DemandReconstructionService`

修改文件：

- `intelligent_project_analyzer/services/demand_reconstruction_service.py`
- `tests/services/test_demand_reconstruction_insight_quality_gate.py`

接入点：

```python
reply = self._render_reply(blueprint)
quality = self._insight_quality.evaluate(
    source_message=message,
    semantic_package=adapter_context.get("llm_semantic_understanding") or {},
    blueprint=blueprint,
    visible_reply=reply,
)
blueprint["insight_quality"] = quality
```

治理信号：

```python
{
    "code": "insight_quality_watch",
    "track": "demand_reconstruction_quality",
    "review_queue": "demand_reconstruction_insight_quality",
    "severity": "P1",
    "meaning": "需求重构已通过基础路由，但高价值语义可能没有进入首屏洞察。",
}
```

第一版只做 warning，不直接阻断线上。只有明显错域、内部词泄露、任务书越界时才 blocking。

---

### Task 3：升级 LLM Semantic Router 与 Final Synthesis prompt

修改文件：

- `intelligent_project_analyzer/services/demand_reconstruction_insight_protocol.py`
- `tests/unit/test_demand_reconstruction_insight_protocol.py`

Semantic Router 必须输出：

- `high_value_signals`
- `core_proposition_candidates`
- `must_preserve_evidence`
- `forbidden_capture_paths`
- `recommended_scan_targets`
- `confidence_band`

Final Synthesis 必须遵守：

```text
先重写真实问题：用户表面在问什么，实际在解决什么。
不要先索取面积、预算、CAD、现场照片。
不要把风格、技术、运营模板放在人的命题之前。
如果只是 partial_specialist，要诚实说明是邻近迁移判断。
```

验收点：prompt 文本包含“高价值信息不可丢失”“表面在问什么，实际在解决什么”，并明确禁止先问 CAD / 面积 / 预算。

---

### Task 4：Planner 增加反捕获机制

修改文件：

- `intelligent_project_analyzer/services/demand_reconstruction_output_planner.py`
- `tests/unit/test_demand_reconstruction_output_planner_fragments.py`

新增机制：

```text
如果输入中出现人生阶段、职业身份、返乡、家庭关系、情感修复、文化隐喻，
则 hard_constraint / style_semantics / technical_performance_environment
不能仅凭关键词成为主导路径。
```

不是禁止技术和风格，而是调整优先级：技术约束可以作为成立边界，风格可以作为表达方式，但主命题必须先由更高价值的用户语义决定。

代表断言：

```python
assert "故乡" in plan["task_reframe"] or "乡土" in plan["task_reframe"] or "身份" in plan["task_reframe"]
assert "风格标签" not in plan["task_reframe"]
```

---

### Task 5：建立 190 题洞察审计脚本

新增文件：

- `scripts/audit_demand_reconstruction_insight_quality.py`
- `tests/unit/test_audit_demand_reconstruction_insight_quality_script.py`

脚本职责：

- 读取 `sf/2026.3.22/模拟问题集合.txt`；
- 兼容 `1. ...` 编号格式；
- 批量调用需求重构服务；
- 输出每题的 `project_type`、`task_reframe`、`insight_quality`、`governance_codes`；
- 生成 `.tmp/demand-reconstruction-insight-quality-audit.json`。

验收命令：

```bash
.\.conda\python.exe scripts/audit_demand_reconstruction_insight_quality.py --source "sf/2026.3.22/模拟问题集合.txt" --output ".tmp/demand-reconstruction-insight-quality-audit.json"
```

基础预期：

```json
{"total": 190, "handled": 190, "unhandled": 0}
```

如果短期做不到 `handled=190`，必须列出未处理题号，不允许隐藏。

---

### Task 6：建立阈值化验收门

验收阈值：

```text
handled_ratio >= 0.98
trust_or_insight_ratio >= 0.70
high_value_signal_loss_ratio <= 0.20
wrong_capture_count <= 10
internal_term_leak_count == 0
```

含义：

- `handled_ratio` 验证开放问题入口覆盖；
- `trust_or_insight_ratio` 验证输出是否真正进入洞察层；
- `high_value_signal_loss_ratio` 验证用户关键线索是否丢失；
- `wrong_capture_count` 验证是否仍被技术/风格/运营模板抢主导；
- `internal_term_leak_count` 验证前台不暴露内部机制词。

---

## 5. 推荐实施顺序

```text
1. 洞察质量 evaluator
2. service 接入 insight_quality
3. LLM prompt 增加语义保真契约
4. planner 增加反捕获排序
5. 190 题 audit 脚本
6. 阈值化验收门
7. 人工金标准扩展到 20 题，再扩展到 190 题
```

不要先改 registry。registry 是稳定资产库，不是修补浅洞察的入口。

---

## 6. 首批金标准样本

| ID | 类型 | 必须保留 | 禁止路径 |
|---:|---|---|---|
| 2 | 创业者别墅 | 成就、家族、回归 | 硬约束优先 |
| 8 | 自闭症儿童家庭 | 感统、照护、三代共居 | 声学优先 |
| 16 | 返乡设计师民居 | 年龄、职业、故乡、精神安放 | 风格标签优先 |
| 26 | 酒店竞标 | 竞标策略、弱势团队破局 | 酒店大堂运营优先 |
| 34 | 诗人书房 | 意象、诗性、空间转译 | 技术性能优先 |
| 59 | 哲学教授住宅 | 存在、虚无、自我对话 | 普通家庭秩序 |
| 126 | 地下未来居住 | 地下生存、高密度、未来原型 | 极寒生命支持 |
| 181 | 行为经济学体验馆 | 决策偏差、损失厌恶、路径实验 | 普通展陈 |
| 187 | 注意力经济办公 | 认知负荷、专注力、信息过载 | 普通办公效率 |
| 190 | 后人类伦理实验室 | 技术伦理、边界、后人类关系 | 普通技术空间 |

---

## 7. 完成定义

本专题完成的判据不是“增加了更多规则”，而是：

1. 需求重构输出包含 `insight_quality`。
2. Q16 这类题首屏能命中“故乡 / 职业身份 / 人生阶段 / 精神安放”。
3. Q34、Q59、Q181、Q190 这类抽象题能进入意象、哲学、伦理或认知转译路径。
4. 190 题审计脚本可以稳定运行并输出阈值报告。
5. 质量门能区分 routing pass 和 trust pass。
6. `partial_specialist` 不再被当作万能通过，而是触发诚实边界和知识资产沉淀。

最终目标：

> 用户不是看到一个分类器，而是看到一个能把他没说清楚的真实问题说清楚的顾问。
