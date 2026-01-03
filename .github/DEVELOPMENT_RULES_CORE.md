# 🔥 核心开发规范 (AI 优先加载版)

> **版本**: v2.0 | **更新时间**: 2026-01-01
> **目标读者**: AI 助手、开发者
> **核心原则**: 防止意外删除、确保代码质量、提高修改可靠性

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

**最后更新**: 2026-01-02
**维护者**: AI Development Team
**状态**: ✅ 生效中
