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

## 🎯 任务执行规则（新增 v2.1）

### 📝 任务列表化原则

**所有复杂工作必须先创建任务列表，然后逐一执行：**

1. **接收需求后**：
   - ✅ 立即使用 `manage_todo_list` 创建任务列表
   - ✅ 将复杂任务拆解为 3-10 个子任务
   - ✅ 标记优先级和依赖关系

2. **执行任务时**：
   - ✅ 每次只执行 1 个任务
   - ✅ 开始前标记为 `in-progress`
   - ✅ 完成后立即标记为 `completed`
   - ✅ 不要跳跃式执行多个任务

3. **任务完成后**：
   - ✅ 简要报告完成内容（1-3句话）
   - ✅ 等待用户"继续"指令
   - ✅ 不要主动执行下一个任务

### ⚡ "继续"指令处理规则

**当用户说"继续"时，立即执行下一个任务，无需冗长思考：**

```
用户输入："继续"

AI 行动：
1. 标记下一个未完成任务为 in-progress（2秒内）
2. 直接开始执行（不要重复分析背景）
3. 完成后标记 completed
4. 简要报告结果（不要撰写长篇总结）
```

**禁止事项：**
- ❌ 看到"继续"后重新分析整个项目背景
- ❌ 重复已完成任务的详细说明
- ❌ 询问"是否需要做XXX"（直接做）
- ❌ 等待超过 10 秒才开始操作

**正确示例：**
```
用户："继续"

AI（2秒内）:
[标记任务4为in-progress]
[开始执行：创建v3_1_examples.yaml...]
[10-30秒后完成]
✅ V3_1示例库已完成（3个示例，8500字符），测试通过。
```

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

## 🛠️ 工具使用最佳实践

### `read_file` 使用规范

```typescript
// ❌ 错误：范围太小
read_file(filePath, startLine: 100, endLine: 105)

// ✅ 正确：包含足够上下文
read_file(filePath, startLine: 85, endLine: 120)
```

---

### `replace_string_in_file` 使用规范

```typescript
// ❌ 错误：锚点不足
oldString = `
const value = dimensionValues[dimId] || 50;
`

// ✅ 正确：充足锚点
oldString = `
      {/* 右侧：可滚动滑块列表 */}
      <div className="space-y-4 md:overflow-y-auto">
        {dimensions.map((dim: any, index: number) => {
          const dimId = dim.id || dim.dimension_id;
          const value = dimensionValues[dimId] || 50;

          return (
            <div key={dimId}>
`
```

---

### `runSubagent` 使用规范

```typescript
// ✅ 明确的任务描述
runSubagent({
  description: "修复双滚动条问题",
  prompt: `
    文件：UnifiedProgressiveQuestionnaireModal.tsx
    位置：第 770-820 行

    当前问题：
    - 外层容器有 overflow-y-auto
    - 右侧滑块也有 overflow-y-auto
    - 导致双滚动条

    修改要求：
    1. 读取第 750-850 行完整代码
    2. 移除右侧滑块的 md:max-h-[500px] md:overflow-y-auto
    3. 保持 .map() 函数和所有变量声明完整
    4. 验证括号配对正确
    5. 返回修改后的第 770-820 行代码

    重要：确保不删除任何函数定义或变量声明
  `
});
```

---

## 📊 修改复杂度评估表

| 修改类型 | 复杂度 | 推荐工具 | 锚点行数 |
|---------|--------|---------|---------|
| 单行文本修改 | 低 | replace_string | 5 行 |
| 5-10 行修改 | 中 | replace_string | 10 行 |
| 10-20 行修改 | 中高 | replace_string | 15 行 |
| 20+ 行修改 | 高 | runSubagent | - |
| 缩进调整 | 高 | runSubagent | - |
| 结构重构 | 高 | runSubagent | - |
| 匹配失败 2+ 次 | 高 | runSubagent | - |

---

## ✅ 自检清单（每次修改前）

```
[ ] 1. 已读取目标行 ±15 行上下文
[ ] 2. 理解了完整的代码结构
[ ] 3. oldString 包含至少 5 行锚点
[ ] 4. oldString 包含完整的结构性代码
[ ] 5. 预估了修改的影响范围
[ ] 6. 准备好修改后的验证方案
[ ] 7. 复杂修改已考虑使用 runSubagent
```

---

## 📝 历史教训记录

### 2026-01-01: 双滚动条修复事故

**问题：** 移除 `md:overflow-y-auto` 时误删了 `.map()` 函数定义

**根本原因：**
1. oldString 只包含 2 行，锚点不足
2. 未读取足够的上下文
3. 修改后未验证代码结构

**改进措施：**
- ✅ 强制 oldString 包含至少 5 行锚点
- ✅ 修改前强制读取 ±15 行
- ✅ 修改后强制验证结构完整性

**预防机制：**
```typescript
// 新增规则：匹配失败 2 次 → 立即改用 runSubagent
if (replaceAttempts >= 2) {
  use_runSubagent_instead();
}
```

---

## 🎓 进阶技巧

### 1. 使用 grep_search 预览修改影响

```typescript
// 修改前先搜索
grep_search({
  query: "setShowProgressiveStep1",
  isRegexp: false
});

// 确认影响范围后再修改
```

### 2. 多文件修改使用 multi_replace_string_in_file

```typescript
// 确保每个替换独立且安全
multi_replace_string_in_file({
  explanation: "统一修改三个状态处理",
  replacements: [
    { filePath, oldString: "...", newString: "...", explanation: "..." },
    { filePath, oldString: "...", newString: "...", explanation: "..." }
  ]
});
```

### 3. 利用 get_errors 实时验证

```typescript
// 修改后立即检查编译错误
get_errors({ filePaths: [modifiedFile] });
```

---

---

## 📋 领域特定最佳实践

### 正则表达式设计原则

**案例**: [v7.107.1 预算识别修复](historical_fixes/step3_llm_context_awareness_fix_v7107.1.md)

```python
# ❌ 不充分：只考虑常见格式
budget_pattern = r'\d+万|\d+元'

# ✅ 全面：覆盖总价和单位价格
budget_pattern = r'\d+万|\d+元|\d+元[/每]平米?|\d+[kK]/[㎡m²平米]|预算|成本|费用'
```

**强制检查清单**：
- [ ] 收集真实用户输入的多样化表达方式
- [ ] 覆盖数值型（总价、单位价格）和关键词型
- [ ] 支持中英文、简写、特殊符号
- [ ] 编写测试用例验证所有格式
- [ ] 记录已知的不支持边缘情况

---

### 动态优先级设计原则

**案例**: [v7.107.1 上下文感知修复](historical_fixes/step3_llm_context_awareness_fix_v7107.1.md)

```python
# ❌ 硬编码：缺乏灵活性
if dimension == "时间节点":
    return "critical_gap"

# ✅ 上下文感知：根据用户意图动态调整
if dimension == "时间节点":
    design_keywords = ["如何", "设计手法", "体面感", ...]
    if any(kw in user_input for kw in design_keywords):
        return None  # 降级为非必填
    return "critical_gap"
```

**设计原则**：
- 🎯 **意图优先**：根据用户关注点动态调整
- 🔄 **可扩展**：支持添加更多上下文规则
- 📊 **可配置**：关键词列表可外部维护
- 📝 **可追溯**：在日志中记录决策理由

---

### 异常处理日志规范

**案例**: [v7.107.1 日志增强](historical_fixes/step3_llm_context_awareness_fix_v7107.1.md)

```python
# ❌ 不充分：缺少上下文
except Exception as e:
    logger.error(f"失败: {e}")

# ✅ 诊断友好：完整上下文 + 堆栈
import traceback

try:
    logger.info(f"📋 [输入] {user_input[:100]}...")
    logger.info(f"📊 [状态] missing={missing}, critical={critical}")
    result = llm_function(...)
    logger.info(f"✅ [成功] 生成{len(result)}个")

except Exception as e:
    logger.error(f"❌ [异常] {type(e).__name__}: {str(e)}")
    logger.error(f"🔍 [堆栈]\n{traceback.format_exc()}")
```

**日志分级标准**：
- 🔵 **INFO**: 正常流程节点、关键决策、输入输出摘要
- 🟡 **WARNING**: 降级处理、异常分支、性能瓶颈
- 🔴 **ERROR**: 错误详情、完整堆栈、输入上下文

---

## 🔗 相关文档

- 📚 [完整开发规范](DEVELOPMENT_RULES.md) - 详细指南
- ✅ [变更检查清单](PRE_CHANGE_CHECKLIST.md) - 修改前必查
- 📖 [历史修复记录](historical_fixes/) - 过往案例
  - [v7.107.1 上下文感知修复](historical_fixes/step3_llm_context_awareness_fix_v7107.1.md) ⭐ 新增

---

## 📮 反馈与改进

如果发现本规范未能防止某类错误，请：
1. 在 `.github/historical_fixes/` 记录案例（参考v7.107.1模板）
2. 更新本规范添加新的防范措施
3. 在核心规范中添加领域特定最佳实践
4. 通知所有 AI 助手更新规则

---

**最后更新**: 2026-03-04
**维护者**: AI Development Team
**状态**: ✅ 生效中


---

## 🌿 Git 分支规范（v4.0 — 2026-03）

### 核心原则：任何代码改动必须在独立分支完成，绝不在 main 直接修改

### 分支命名规则

| 改动类型 | 前缀 | 示例 |
|---------|------|------|
| 缺陷修复 | `fix/` | `fix/settings-import-safety` |
| 重构优化 | `refactor/` | `refactor/remove-server-proxy` |
| 新功能 | `feature/` | `feature/event-bus` |
| 清理工作 | `chore/` | `chore/cleanup-dead-code` |
| 架构整改 | `arch/` | `arch/server-slim-p1` |

### 强制分支策略

1. **每个独立子系统/阶段建一个短生命周期分支**（目标：不超过 1 周）
2. **跨子系统改动必须拆为多个分支，按依赖顺序合并**
3. **禁止在 main 直接 commit 代码修改**（版本号 bump、纯文档除外）

#### 架构稳定性收口分支顺序（2026-03 基线）

```
fix/settings-import-safety        ← 最优先合并（测试基础设施前提）
    ↓ 合并后
refactor/remove-server-proxy      ← 依赖 settings 修复完成
fix/test-collection-stability     ← 可与 refactor/remove-server-proxy 并行
    ↓ 两者合并后
chore/cleanup-dead-code           ← 版本统一 + 死代码清理
    ↓
arch/server-slim-p1               ← server.py 瘦身 + 路由冲突修复
```

### 合并前验收门槛（强制执行）

每个分支合并 main 前必须通过：

```bash
# 底线：收集零错误
pytest --collect-only -q        # 期望：0 errors

# 单元测试绿色
pytest tests/unit/ -q           # 期望：无 FAILED

# 分支特定验证
# fix/settings-import-safety  →  DEBUG=release python -c "from intelligent_project_analyzer import settings"
#                                 应输出诊断提示，而非 traceback
# refactor/remove-server-proxy →  grep -rn "_ServerProxy" intelligent_project_analyzer/ → 0 结果
# arch/server-slim-p1         →  wc -l intelligent_project_analyzer/api/server.py → < 500
```

### 提交信息规范（Conventional Commits）

```
<type>(<scope>): <描述（中文可）>

type: fix | feat | refactor | chore | docs | test | arch
scope: settings | api | workflow | state | tests | deps | server

示例：
fix(settings): 添加 DEBUG 字段 bool 容错 validator，防止导入期崩溃
refactor(api): 消除 7 个文件的 _ServerProxy 反向依赖模式
chore(dead-code): 删除 5 个冻结 feature flag 和 12 个备份文件
arch(server): 将 31 个 Pydantic 模型迁移至 api/models.py
```

### 禁止事项

- ❌ 禁止一个分支承载互不依赖的多个子系统改动
- ❌ 禁止跳过收集验证直接合并
- ❌ 禁止 `git commit -m "fix"` 等无信息提交
- ❌ 禁止长生命周期大分支（>1 周未合并须拆分）

版本: v4.0 | 更新时间: 2026-03-04 | 原因: 架构稳定性收口专项治理


---

## 架构冻结规则（v3.0 — 2026-02）

背景痛点：AI 助手反复自动回到旧代码，将已清理的死分支重新引入。以下规则建立后，任何违反即视为 BUG 应立即回滚。

### 已冻结的 Feature Flag（禁止条件分支）

| Flag 名称 | 冻结值 | 替代做法 |
|-----------|--------|---------|
| USE_V716_AGENTS | False | 直接内联旧版路径 |
| USE_V717_REQUIREMENTS_ANALYST | True | 直接使用 RequirementsAnalystAgentV2 |
| USE_PROGRESSIVE_QUESTIONNAIRE | True | 直接使用 ProgressiveQuestionnaireNode |
| USE_V7_FRONTCHAIN_SEMANTICS | True | 语义分析永久启用 |
| USE_MULTI_ROUND_QUESTIONNAIRE | False | 多轮问卷路径已移除 |

若源码出现 `if USE_V716_AGENTS:` 等，应立即删除并内联唯一路径。

### 禁止创建临时兼容层

- 禁止：写了 router 文件却不挂载
- 禁止：在 server.py 保留与 router 文件重复的 @app.xxx 路由
- 禁止：硬编码 goto 字符串如 `Command(goto="progressive_step2_radar")`
- 正确：使用常量 `Command(goto=_NODE_STEP2_RADAR)`

### 双动机驱动路由架构约定

已实现链路（禁止回退到硬编码版本）：

```
requirements_analyst 节点
  -> _build_motivation_routing_profile() -> state["motivation_routing_profile"]

progressive_questionnaire 节点
  -> _build_self_skip_decision() 读取 skip_candidates -> 动态跳过 gap_filling/radar
```

代码位置：
- 组装器：`intelligent_project_analyzer/workflow/nodes/requirements_nodes.py`
- 决策器：`intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py`
- 路由常量：`_NODE_STEP1`, `_NODE_STEP2_RADAR`, `_NODE_STEP3_GAP`, `_NODE_SUMMARY`, `_NODE_DIRECTOR`

生效需设置环境变量 `ENABLE_SMART_NODE_SELF_SKIP=true`。

### 提交前快捷检测

```bash
# 检查冻结 flag 的条件分支 (期望：无输出)
grep -rn "if USE_V716_AGENTS" intelligent_project_analyzer/ --include="*.py"
grep -rn "if USE_V717_REQUIREMENTS_ANALYST" intelligent_project_analyzer/ --include="*.py"

# 检查硬编码 goto 字符串 (期望：无输出)
grep -rn 'Command(goto="progressive_step' intelligent_project_analyzer/ --include="*.py"
```

版本: v3.0 | 更新时间: 2026-02 | 原因: P1 架构手术后冻结稳定状态
