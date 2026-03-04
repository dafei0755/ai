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
---

## 🚨 强制执行规则（违反即停止）

### 1️⃣ 代码修改前置检查（MANDATORY）

**每次使用 `replace_string_in_file` 前必须执行：**

```
✅ 步骤 1: read_file 读取目标行 ±15 行上下文
✅ 步骤 2: 理解完整代码结构（函数、类、块）
✅ 步骤 3: 在 oldString 中包含至少 5 行不变代码作为锚点
✅ 步骤 4: 确认 oldString 包含完整的结构性代码（{, }, map, return 等）
```

**禁止事项：**
- ❌ 不读取上下文直接修改
- ❌ oldString 只有 1-2 行
- ❌ 匹配失败 2 次以上仍继续尝试

---

### 2️⃣ 修改后强制验证（MANDATORY）

**每次 `replace_string_in_file` 成功后立即执行：**

```
✅ 步骤 1: read_file 读取修改后的代码段（±10 行）
✅ 步骤 2: 检查关键结构完整性（函数定义、括号匹配、变量声明）
✅ 步骤 3: 向用户明确说明修改的具体范围和影响
```

**验证检查点：**
- ✓ 函数/方法签名完整
- ✓ 变量声明存在
- ✓ 括号/大括号配对正确
- ✓ 关键语句（return、export、import）未被误删

---

### 3️⃣ 复杂修改使用 runSubagent（MANDATORY）

**以下情况必须使用 `runSubagent` 而非直接 `replace_string_in_file`：**

1. **跨越超过 20 行的修改**
2. **需要调整缩进的修改**（tab ↔ space 转换）
3. **涉及多个代码块的重构**
4. **匹配失败 2 次以上**

**runSubagent 调用示例：**
```typescript
runSubagent({
  description: "修复雷达图滚动条问题",
  prompt: `请修复 file.tsx 第 770-820 行的代码：

  问题：右侧滑块列表有独立滚动条，与外层容器产生双滚动

  要求：
  1. 读取第 750-850 行完整上下文
  2. 移除第 773 行的 md:max-h-[500px] md:overflow-y-auto
  3. 保持 .map() 函数完整性
  4. 验证修改后代码结构
  5. 返回修改后的完整代码段（第 750-850 行）`
});
```

---

## 📋 标准工作流程

### 阶段 1: 诊断问题

```
1. 理解用户报告的问题
2. 使用 grep_search / semantic_search 定位相关代码
3. read_file 读取完整上下文（±20 行）
4. 查阅历史修复记录（.github/historical_fixes/）
5. 形成修改方案
```

### 阶段 2: 报告方案

```
向用户说明：
- 问题根本原因
- 修改计划（具体文件和行号）
- 预期影响范围
- 可能的风险点
```

### 阶段 3: 执行修改

**选择修改方式：**

| 条件 | 工具选择 |
|------|---------|
| 简单单行修改 | `replace_string_in_file` + 10 行锚点 |
| 5-20 行修改 | `replace_string_in_file` + 15 行锚点 |
| 20+ 行修改 | `runSubagent` |
| 涉及缩进调整 | `runSubagent` |
| 匹配失败 2+ 次 | `runSubagent` |

**执行步骤：**
```
1. read_file 读取目标 ±15 行
2. 准备 oldString（包含 5-10 行锚点）
3. 准备 newString（完整替换内容）
4. 调用 replace_string_in_file
5. read_file 验证修改结果
6. 向用户确认修改完成
```

### 阶段 4: 更新文档

```
如果修改了核心逻辑或配置：
1. 更新 CHANGELOG.md
2. 更新相关技术文档
3. 在 .github/historical_fixes/ 记录修复过程
```

---

## 🎯 典型错误案例与防范

### ❌ 案例 1: 意外删除函数定义

**错误代码：**
```typescript
// 目标：删除 overflow-y-auto
oldString = `
<div className="space-y-4 md:overflow-y-auto">
`;
```

**问题：**
- 缺少锚点代码
- 可能匹配到多个位置
- 未检查上下文

**正确做法：**
```typescript
// read_file 读取第 760-780 行后
oldString = `
      </div>

      {/* 右侧：可滚动滑块列表 */}
      <div className="space-y-4 md:max-h-[500px] md:overflow-y-auto md:pr-2">
        {dimensions.map((dim: any, index: number) => {
          const dimId = dim.id || dim.dimension_id;
`;

newString = `
      </div>

      {/* 右侧：滑块列表 */}
      <div className="space-y-4">
        {dimensions.map((dim: any, index: number) => {
          const dimId = dim.id || dim.dimension_id;
`;
```

---

### ❌ 案例 2: Tab/Space 混用导致匹配失败

**错误做法：**
```typescript
// 尝试 1: 失败（tab）
// 尝试 2: 失败（2 spaces）
// 尝试 3: 失败（4 spaces）
// ... 继续尝试
```

**正确做法：**
```typescript
// 失败 2 次后立即停止
runSubagent({
  description: "修复缩进问题",
  prompt: "请读取完整代码段，统一缩进后返回"
});
```

---

### ❌ 案例 3: 破坏代码结构

**错误操作：**
```
修改时删除了：
- 函数签名: .map((dim, index) => {
- 变量声明: const dimId = ...
- 返回语句: return (
```

**防范措施：**
```
1. oldString 必须包含完整的结构边界
2. 修改后立即 read_file 验证
3. 检查关键词：function, const, let, return, export
```

---
