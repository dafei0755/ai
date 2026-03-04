# AI 开发行为规范

> **目标读者**：AI 编程助手（Copilot、Cursor 等）
> **原则**：这里只写 AI 应该怎么做，不写用哪个工具、怎么调用 API。
> **参考**：完整开发规范见 [docs/dev/](../docs/dev/)

---

## 任务执行原则

### 分解后逐一执行

收到复杂需求后，必须先将其拆解为 3-10 个子任务并列出，然后逐一完成：

- 每次只做 1 个任务
- 开始前明确标记"正在进行"
- 完成后立即标记"已完成"，不要批量确认
- 不要跳过任务或同时推进多个任务

**完成报告格式**：1-3 句话说明做了什么结果，然后等待指令。

### "继续"指令

用户说"继续"时，2 秒内开始执行下一个未完成任务。

禁止行为：
- 重新分析整个项目背景
- 重复描述已完成的任务
- 询问"是否需要做 XXX"（直接做）

---

## 修改代码的原则

### 修改前：充分理解上下文

在修改任何代码之前，必须先读懂它：

- 读取目标代码上下文（至少前后 15 行）
- 识别完整的结构边界（函数开始/结束、括号配对、类定义等）
- 确认修改点在上下文中的唯一性（避免匹配到多处）
- 评估修改的影响范围（谁在调用这段代码）

**判断标准**：能用一句话说清楚"这段代码在做什么、被谁调用"，才算理解。

### 修改时：小步可验证

- 单次修改范围尽量小（改得越多，出错越难排查）
- 修改匹配标识应包含足够的前后上下文（纯单行匹配不可靠）
- 匹配失败超过 2 次，停止重试，改用针对该文件的专项子任务处理
- 跨 20 行以上的修改，或涉及缩进重整的修改，拆分为更小的操作

### 修改后：验证结果

每次代码修改完成后立即验证：

- 读取修改后的代码段（至少前后 10 行）
- 检查关键结构是否完整：函数签名、变量声明、括号匹配、return/export
- 向用户说明修改了什么、影响范围是什么

**禁止**：修改完就认为完成，不验证结果。

---

## 标准工作流（四阶段）

### 阶段一：诊断

- 定位问题根因，而不只是症状
- 查阅历史修复记录（`.github/historical_fixes/`）中是否有同类案例
- 理解完整上下文后再形成方案

### 阶段二：方案报告

向用户说明：
- 问题根本原因
- 计划修改哪些文件/哪些位置
- 预期影响范围
- 可能的风险点

等待确认后再执行。

### 阶段三：实现

- 按方案执行，不扩散
- 遵循修改前/中/后的原则（见上）
- 每个子任务完成后确认，再进行下一个

### 阶段四：文档同步

修改了核心逻辑或公共接口后：

- 更新 `CHANGELOG.md`
- 更新相关技术文档
- 在 `.github/historical_fixes/` 记录修复过程（如为重要 bug fix）

---

## 项目特定约束（v8.x 基线）

### 已冻结的 Feature Flag

以下 feature flag 已冻结，禁止引入条件分支，直接内联唯一路径：

| Flag | 冻结值 | 内联方式 |
|------|--------|---------|
| `USE_V716_AGENTS` | False | 直接使用旧版路径 |
| `USE_V717_REQUIREMENTS_ANALYST` | True | 直接使用 `RequirementsAnalystAgentV2` |
| `USE_PROGRESSIVE_QUESTIONNAIRE` | True | 直接使用 `ProgressiveQuestionnaireNode` |
| `USE_V7_FRONTCHAIN_SEMANTICS` | True | 语义分析永久启用 |
| `USE_MULTI_ROUND_QUESTIONNAIRE` | False | 多轮问卷路径已移除 |

发现 `if USE_V716_AGENTS:` 等条件分支，应立即删除并内联唯一路径。

### 禁止的架构反模式

- 写了 router 文件却不挂载到 app
- 在 `server.py` 保留与 router 文件重复的路由
- 硬编码路由字符串，如 `Command(goto="progressive_step2_radar")`（应用常量 `_NODE_STEP2_RADAR`）

### 已稳定的路由架构

禁止回退到硬编码版本：

```
requirements_analyst → _build_motivation_routing_profile() → state["motivation_routing_profile"]
progressive_questionnaire → _build_self_skip_decision() → 动态跳过节点
```

生效条件：环境变量 `ENABLE_SMART_NODE_SELF_SKIP=true`

---

## 分支与提交原则

> 完整规范见 [docs/dev/workflow.md](../docs/dev/workflow.md)

- 任何代码变更必须在独立分支完成，不在 main 直接提交
- 一个分支只做一件事，生命周期不超过 1 周
- 合并前必须通过：`pytest --collect-only -q`（0 errors）+ `pytest tests/unit/ -q`（0 failed）
- 提交信息格式：`<type>(<scope>): <描述>`，type 白名单：`fix / feat / refactor / arch / chore / docs / test`

---

## 参考文档

| 文档 | 内容 |
|------|------|
| [docs/dev/principles.md](../docs/dev/principles.md) | 开发核心原则（为什么） |
| [docs/dev/workflow.md](../docs/dev/workflow.md) | 标准开发流程（做什么） |
| [docs/dev/quality.md](../docs/dev/quality.md) | 代码质量标准 |
| [docs/dev/testing.md](../docs/dev/testing.md) | 测试规范 |
| [historical_fixes/](historical_fixes/) | 历史 bug 修复案例 |

