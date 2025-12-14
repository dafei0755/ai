# 🔍 变更前检查清单

> ⚠️ **强制要求**：每次修改代码前，必须完成本检查清单的所有项目。
>
> 📝 **目的**：避免重复犯错，确保每次修改都有文档记录，建立系统化的迭代思维。

---

## 🚨 必读：修改代码前的强制流程

> ⚠️ **最高优先级**：违反此流程将导致操作无效并需要回滚

### 修改代码前必须完成（规则 0.4）

- [ ] ✅ **诊断完成**：确认问题根本原因
- [ ] ✅ **历史记录查阅**：搜索 `DEVELOPMENT_RULES.md`、`BUG_FIX_*.md` 确认是否有类似问题
- [ ] ✅ **方案报告**：向用户详细说明修复方案
- [ ] ✅ **影响评估**：明确修改范围和风险
- [ ] ✅ **等待批准**：收到"可以实施"、"批准"、"同意"等明确指令
- [ ] ✅ **开始修改**：严格按照批准的方案执行

---

### 标准报告模板

使用以下模板向用户报告修复方案：

```markdown
## 问题诊断
**症状**：[用户看到的现象]
**根因**：[技术层面的根本原因]
**历史记录**：[是否在 DEVELOPMENT_RULES.md 中有类似问题]

## 修复方案
**涉及文件**：
- `path/to/file1.ts` - [修改内容]
- `path/to/file2.py` - [修改内容]

**修改步骤**：
1. [具体步骤1]
2. [具体步骤2]

**影响范围**：
- ✅ 仅影响 [模块名称]
- ⚠️ 可能影响 [功能名称]

**风险评估**：
- 低风险 / 中风险 / 高风险
- [风险说明]

**是否涉及已有修复**：
- 是 / 否
- [如果是，说明与哪个修复（如 v7.6）相关]

## 请求批准
以上方案是否可以实施？
```

---

### 快速搜索历史记录命令

```bash
# 搜索相同问题
grep -rn "错误关键词" .github/*.md

# 搜索相同模块的修复
grep -rn "模块名" .github/DEVELOPMENT_RULES.md

# 搜索版本号
grep -rn "v7." .github/DEVELOPMENT_RULES.md
```

---

## 🚨 修改后必做：文档更新（最重要！）

### ⚠️ 强制要求：每次修改必须更新文档

**修改代码后，必须立即更新以下文档：**

1. **[DEVELOPMENT_RULES.md](.github/DEVELOPMENT_RULES.md)**
   - [ ] 在「历史问题追踪」章节添加新的问题记录
   - [ ] 包含：症状、根因、修复方案、涉及文件、防范措施
   - [ ] 更新「更新记录」表格

2. **创建修复文档（如果是重大问题）**
   - [ ] 创建 `BUG_FIX_vX.X.X.md` 或 `QUALITY_FIX_*.md`
   - [ ] 包含详细的问题诊断、修复方案、测试计划

3. **更新相关专题文档**
   - [ ] 如果修改了 API，更新 API 文档
   - [ ] 如果修改了数据模型，更新数据契约文档
   - [ ] 如果修改了工作流，更新 [CLAUDE.md](CLAUDE.md)

**文档更新模板**：
```markdown
#### 问题 X.X.X：问题简短描述

**症状**：
- 用户看到的现象
- 日志中的错误信息

**根因**：
- 问题的根本原因

**修复方案 (vX.X.X)**：
```代码示例```

**涉及文件**：
- `path/to/file.py`

**防范措施**：
- 如何避免再次出现
```

---

## 📋 修改前必读文档

- [ ] 已阅读 [DEVELOPMENT_RULES.md](.github/DEVELOPMENT_RULES.md)
- [ ] 已检查「历史问题追踪」章节，确认类似问题的修复方案
- [ ] 已阅读 [CLAUDE.md](CLAUDE.md) 了解项目架构

---

## 修改公共函数前

- [ ] 搜索所有调用点：`grep -rn "函数名" --include="*.tsx" --include="*.ts" frontend-nextjs/`
- [ ] 列出受影响的文件数量
- [ ] 确认所有调用点兼容新改动
- [ ] 更新相关单元测试

## 修改数据结构前

- [ ] 检查前端 TypeScript 类型定义 (`types/index.ts`)
- [ ] 检查后端 Pydantic 模型
- [ ] 检查 API 响应格式是否变化
- [ ] 更新相关文档

## 新增功能前

- [ ] 检查 `lib/` 目录是否已有类似函数
- [ ] 检查 `utils/` 目录是否已有类似函数
- [ ] 如已存在，直接导入复用
- [ ] 如需新建，添加到公共模块并编写测试

## 修改组件显示前

- [ ] 确认使用统一的格式化函数 (`lib/formatters.ts`)
- [ ] 确认使用统一的颜色映射
- [ ] 确认处理了空值/异常情况

## 🆕 修改问卷/LLM生成相关代码前

- [ ] 阅读 `DEVELOPMENT_RULES.md` 第10章「LLM提示词与数据流规范」
- [ ] 阅读 `DEVELOPMENT_RULES.md` 第11章「问卷系统规范」
- [ ] 检查 `_build_analysis_summary` 是否覆盖所有关键字段
- [ ] 检查提示词是否包含**禁止生成**和**必须包含**的示例
- [ ] 验证生成内容是否引用用户原话关键词

## TypeScript 编码检查

- [ ] `reduce` 函数是否添加类型标注？
- [ ] 空数组是否有类型断言？（`[] as Type[]`）
- [ ] 第三方库类型问题是否用 `as any` 解决？
- [ ] 是否有重复属性定义？（展开运算符冲突）

## JSX 内容检查

- [ ] 中文引号是否转义？（`&ldquo;` `&rdquo;`）
- [ ] 特殊字符是否转义？（`&amp;` `&lt;` `&gt;`）
- [ ] 撇号是否转义？（`&apos;` 或 `&rsquo;`）

## 提交前

- [ ] 运行前端构建：`cd frontend-nextjs && npm run build`
- [ ] 运行后端测试：`python -B tests/test_questionnaire_generation.py`
- [ ] 验证无 TypeScript 错误
- [ ] 代码格式化：`npm run lint`

## 修复问题后

- [ ] 更新 `DEVELOPMENT_RULES.md` 的「历史问题追踪」章节
- [ ] 记录问题症状、根因、修复方案
- [ ] 列出涉及的文件

---

## 快速搜索命令

```bash
# 搜索函数调用
grep -rn "formatExpertName" --include="*.tsx" frontend-nextjs/

# 搜索类型定义
grep -rn "interface.*Expert" --include="*.ts" frontend-nextjs/

# 搜索 Python 函数
grep -rn "def.*format" --include="*.py" intelligent_project_analyzer/

# 搜索重复函数实现
grep -rn "function format" --include="*.tsx" frontend-nextjs/

# 搜索中文引号（需要转义的）
grep -rn "[""'']" --include="*.tsx" frontend-nextjs/

# 🆕 搜索问卷相关代码
grep -rn "_build_analysis_summary\|questionnaire" --include="*.py" intelligent_project_analyzer/
```

## 常见问题快速参考

| 问题 | 检查点 | 解决方案 |
|------|-------|---------|
| 专家名称格式错误 | `lib/formatters.ts` | 使用统一 `formatExpertName` |
| TypeScript reduce 类型错误 | 累加器参数 | 添加 `: Type[]` 标注 |
| JSX 引号 ESLint 错误 | 中文引号 | 替换为 `&ldquo;` `&rdquo;` |
| 对象重复属性 | 展开运算符 | 删除显式定义的重复属性 |
| react-markdown 类型错误 | components prop | 添加 `as any` |
| **问卷问题泛化** 🆕 | `llm_generator.py` | 检查字段提取+提示词约束 |
| **问卷脱离用户输入** 🆕 | `questionnaire_generator.yaml` | 添加禁止/必须示例 |
| **进度显示英文** 🆕 | `NODE_NAME_MAP` | 扩展映射 + `formatNodeName` 增强 |
| **专家报告显示代码** 🆕 | `renderArrayItemObject` | JSON字符串递归解析 |
| **LLM乱码输出** 🆕 | `cleanLLMGarbage` | 添加乱码清洗函数 |
| **问卷生成TypeError** 🆕 | `_build_analysis_summary` | 增强类型判断 list/dict/str |
| LLM服务连接异常 | llm_factory.py/review_agents.py | 捕获APIConnectionError，友好降级 |

## 相关文档

- [完整开发规范](DEVELOPMENT_RULES.md)
- [项目说明](../README.md)
- [Copilot 指令](copilot-instructions.md)
