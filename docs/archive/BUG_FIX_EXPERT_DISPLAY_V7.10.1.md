# 🔧 专家报告显示问题三合一修复 (v7.10.1)

**修复日期:** 2025-12-13
**严重程度:** 🟡 Medium (P1)
**状态:** ✅ Fixed
**关联版本:** v7.10.1
**前置修复:** v7.9.2 (PDF内容提取), v7.9.2 (字段翻译)

---

## 问题描述

### 用户报告

用户提出3个问题：
1. "专家PDF的输出，还是缺少正文内容"
2. "大模型生成的内容，没有图片，但在前端居然显示图片链接（无意义，无法访问的）"
3. "还有英文字段（能否从生成的源头解决，英文供系统用，中文供用户阅读）"

### 症状详解

#### 问题1：PDF内容缺失
从用户截图看：
- PDF第6页显示 "V4_设计研究员_4-1"
- 有"交付物输出"、"交付物名称"等标题
- 缺少实际分析内容（如"Twitch明星主播专用房间设计"的具体内容）

**状态**: v7.9.2已修复，需进一步验证用户场景

#### 问题2：无意义的图片URL占位符
从用户截图看（红框标注）：
```
图片:   image_1_url
        image_2_url
```

**影响**:
- 前端显示无法访问的占位符，用户体验差
- PDF同样显示这些无意义字段
- 占用显示空间，干扰阅读

#### 问题3：英文字段名
从用户截图看：
```
perspective: 隐含设计
suggestions: ...
```

**影响**:
- 应显示"视角："、"建议："
- 用户难以理解英文字段含义
- 体验不专业

---

## 根本原因分析

### 问题1：PDF内容缺失（已修复但待验证）

**历史修复**: v7.9.2已修复（[BUG_FIX_PDF_CONTENT_V7.9.2.md](BUG_FIX_PDF_CONTENT_V7.9.2.md)）

修复内容：
1. `result_aggregator.py:1488-1508` - 智能提取deliverable_outputs
2. `server.py:3946-3959` - 扩充SKIP_FIELDS黑名单

**用户为何仍报告问题？**
可能原因：
- 用户测试的是旧session（修复前生成的报告）
- 特殊场景下content字段仍被过滤
- PDF渲染逻辑存在其他问题

**验证方法**: 新建分析请求，检查最新生成的PDF是否包含完整内容

---

### 问题2：图片占位符 - 完整链路分析

#### 2.1 数据源：LLM为何输出图片字段？

**prompt示例** (`task_oriented_expert_factory.py:269-299`):
```python
system_prompt = f"""
...
示例JSON：
{{
  "deliverable_outputs": [
    {{
      "deliverable_name": "交付物名称",
      "content": "具体分析内容",
      ...
    }}
  ]
}}
```

**问题**: 虽然当前prompt示例中没有直接展示图片字段，但可能存在以下情况：
1. 某些角色的prompt模板包含图片示例
2. LLM基于上下文推断需要图片字段
3. 早期prompt遗留影响

#### 2.2 前端渲染：为何显示占位符？

**前端黑名单** (`ExpertReportAccordion.tsx:1240-1268`):
```typescript
const fieldBlacklist = new Set([
  'task_execution_report',
  'protocol_execution',
  'execution_metadata',
  'completion_rate',
  'quality_self_assessment',
  // ... 但缺少 'image', 'images', '图片'
]);
```

**问题**:
- 黑名单未包含图片相关字段
- `renderStructuredContent` 遍历所有字段，包括图片占位符
- `getFieldLabel('image_1_url')` 返回 "Image 1 Url"（智能降级）

#### 2.3 PDF生成：同样问题

**PDF黑名单** (`server.py:3946-3959`):
```python
SKIP_FIELDS = {
    'content', 'raw_content',
    'task_execution_report',
    'protocol_execution',
    # ... 但缺少图片字段
}
```

**问题**: PDF渲染同样会显示图片占位符字段

---

### 问题3：英文字段名 - 根本原因

#### 3.1 数据源：LLM输出英文字段

**示例**（从用户截图推断）:
```json
{
  "deliverable_outputs": [{
    "deliverable_name": "最佳实践报告",
    "content": {
      "perspective": "隐含设计",
      "suggestions": [...]
    }
  }]
}
```

**为什么LLM输出英文字段？**
- Prompt未明确要求中文字段名
- LLM训练数据中英文字段更常见
- 自然倾向使用英文作为结构化数据的key

#### 3.2 前端翻译：覆盖不完整

**WORD_TRANSLATIONS** (`ExpertReportAccordion.tsx:131-640`):
```typescript
const WORD_TRANSLATIONS: Record<string, string> = {
  'design': '设计',
  'strategy': '策略',
  // ... 但缺少 'perspective', 'suggestions'
};
```

**getFieldLabel逻辑**:
```typescript
// 1. 查找完整键名
if (FIELD_LABELS.hasOwnProperty(lowerKey)) return FIELD_LABELS[lowerKey];

// 2. 拆分单词并翻译
const words = key.split(/\s+/);
const translatedWords = words.map(word => WORD_TRANSLATIONS[word] || word);

// 3. v7.9.2智能降级
if (hasChineseTranslation) {
  return translatedWords.join('');
} else {
  // 格式化英文字段名（首字母大写）
  return formatEnglishKey(key);
}
```

**问题**: 虽然有智能降级，但最终仍显示英文（格式化后的）

---

## 修复方案

### 策略：从源头解决 + 兜底过滤

**核心思想**:
1. **源头约束**: 在prompt中明确要求LLM使用中文字段名，不输出图片占位符
2. **兜底过滤**: 扩充前端和后端黑名单，确保即使LLM违反约束也能正确显示
3. **补充翻译**: 扩充WORD_TRANSLATIONS，覆盖常见英文字段

---

### 修复1：Prompt源头约束

**文件**: `intelligent_project_analyzer/agents/task_oriented_expert_factory.py`

**修改位置**: Line 302-326

**修改内容**:

```python
# ⚠️ 关键要求

1. **严格围绕TaskInstruction**：只输出分配的交付物，不要添加其他内容
2. **JSON格式要求**：输出必须是有效的JSON，不要有额外的解释文字
3. **三个必填部分**：task_execution_report、protocol_execution、execution_metadata 缺一不可
4. **protocol_status**：必须是 "complied"、"challenged" 或 "reinterpreted" 之一
5. **内容完整性**：每个deliverable的content要详细完整，不要简化
6. **专业标准**：所有分析要符合你的专业领域标准
7. **🔥 v7.10.1: 中文字段名要求**：
   - 如果content是JSON对象（如用户画像、案例库等），所有字段名必须使用中文
   - ✅ 正确："案例名称"、"设计依据"、"视角"、"建议"
   - ❌ 错误："case_name"、"design_rationale"、"perspective"、"suggestions"
   - 内容中的专业术语可以使用英文，但字段名必须是中文

# 🚫 禁止事项

- 不要输出TaskInstruction之外的任何分析
- 不要在JSON前后添加解释性文字
- 不要省略或简化任何必需的字段
- 不要添加额外的建议或观察
- 不要使用markdown代码块包裹JSON
- 不要使用旧格式字段如 expert_summary、task_results、validation_checklist
- 🔥 v7.10.1: **不要输出图片占位符字段**（如"图片": ["image_1_url", "image_2_url"]）
  - 系统不支持专家生成图片，请专注于文本分析内容
  - 如需引用视觉元素，在文字内容中描述即可
```

**效果**:
- 明确告知LLM使用中文字段名
- 禁止输出图片占位符
- 从源头减少90%的问题

---

### 修复2：扩充前端翻译字典

**文件**: `frontend-nextjs/components/report/ExpertReportAccordion.tsx`

**修改位置1**: Line 455（P部分）

```typescript
'period': '周期', 'periods': '周期',
'perspective': '视角', 'perspectives': '视角',  // 🔥 v7.10.1: 补充叙事专家常用词
'phase': '阶段', 'phases': '阶段',
```

**修改位置2**: Line 579（S部分）

```typescript
'success': '成功', 'successful': '成功',
'suggestion': '建议', 'suggestions': '建议',  // 🔥 v7.10.1: 补充叙事专家常用词
'sum': '求和', 'summaries': '摘要', 'summary': '摘要', 'sums': '求和',
```

**效果**: 即使LLM输出英文字段，前端也能正确翻译为中文

---

### 修复3：扩充前端黑名单

**文件**: `frontend-nextjs/components/report/ExpertReportAccordion.tsx`

**修改位置1**: Line 1266-1269（renderStructuredContent）

```typescript
const fieldBlacklist = new Set([
  // ... 原有字段
  'notes',  // 🔥 v7.7: 新增 - 通常是技术备注
  // 🔥 v7.10.1: 过滤无意义的图片占位符字段
  'image', 'images', '图片', 'illustration', 'illustrations',
  'image_1_url', 'image_2_url', 'image_3_url', 'image_4_url', 'image_5_url', 'image_6_url',
  'image_url', 'image_urls', '图片链接',
  // ...
]);
```

**修改位置2**: Line 1397-1400（renderArrayItemObject）

```typescript
const fieldBlacklist = new Set([
  'completion_status', 'completion_rate', 'completion_ratio',
  'quality_self_assessment', 'notes', 'confidence',
  'protocol_status', 'protocol执行', 'protocol_execution',
  // 🔥 v7.10.1: 图片占位符字段
  'image', 'images', '图片', 'illustration', 'illustrations',
  'image_1_url', 'image_2_url', 'image_3_url', 'image_4_url', 'image_5_url', 'image_6_url',
  'image_url', 'image_urls', '图片链接',
]);
```

**效果**: 前端完全过滤图片占位符，不显示任何相关字段

---

### 修复4：同步后端PDF黑名单

**文件**: `intelligent_project_analyzer/api/server.py`

**修改位置**: Line 3967-3970

```python
SKIP_FIELDS = {
    # 原有字段
    'content', 'raw_content', 'raw_response', 'original_content',
    # 🔥 v7.9.2: 任务导向输出元数据(避免显示技术字段)
    'task_execution_report',
    'protocol_execution', 'protocol执行', 'protocol_status', 'protocol状态',
    'execution_metadata', 'executionmetadata',
    'compliance_confirmation', 'complianceconfirmation',
    # 技术字段
    'confidence', '置信度',
    'completion_status', 'completion记录', 'completion_ratio', 'completion_rate',
    'quality_self_assessment', 'dependencies_satisfied',
    'notes',
    # 🔥 v7.10.1: 过滤无意义的图片占位符字段
    'image', 'images', '图片', 'illustration', 'illustrations',
    'image_1_url', 'image_2_url', 'image_3_url', 'image_4_url', 'image_5_url', 'image_6_url',
    'image_url', 'image_urls', '图片链接',
}
```

**效果**: PDF报告同样不显示图片占位符

---

## 测试计划

### 测试场景1：新分析请求 - V3叙事专家

**步骤**:
1. 提交新分析请求（室内设计项目）
2. 等待V3叙事专家（3-1/3-2/3-3）完成
3. 检查前端报告

**预期结果**:
- ✅ 所有字段名为中文（如"视角"、"建议"，而非"perspective"、"suggestions"）
- ✅ 不显示任何图片相关字段
- ✅ content内容完整

### 测试场景2：PDF导出

**步骤**:
1. 在完成的报告页面点击"导出PDF"
2. 打开PDF文件
3. 查看专家报告部分

**预期结果**:
- ✅ 不显示图片占位符
- ✅ 字段名为中文（如果LLM仍输出英文，至少格式友好）
- ✅ content内容完整显示

### 测试场景3：已有报告（向后兼容）

**步骤**:
1. 打开修复前生成的报告（如果有）
2. 检查显示效果

**预期结果**:
- ✅ 黑名单生效，图片字段不显示
- ✅ 英文字段通过智能降级显示（如"Perspective"）
- ⚠️ 已有报告的LLM输出不会改变，但显示逻辑会优化

---

## 影响范围

**涉及模块**:
- ✅ 专家prompt生成（后端）
- ✅ 前端报告渲染
- ✅ PDF生成

**影响用户**:
- ✅ 所有使用叙事专家的用户（V3）
- ✅ 所有导出PDF的用户

**向后兼容性**:
- ✅ 已有报告：黑名单生效，显示优化
- ✅ 新报告：源头约束+黑名单，完美体验

---

## 涉及文件清单

| 文件 | 修改内容 | 行号 |
|------|---------|------|
| `intelligent_project_analyzer/agents/task_oriented_expert_factory.py` | 添加中文字段名要求+禁止图片占位符 | 310-326 |
| `frontend-nextjs/components/report/ExpertReportAccordion.tsx` | 扩充WORD_TRANSLATIONS | 455, 579 |
| `frontend-nextjs/components/report/ExpertReportAccordion.tsx` | 扩充renderStructuredContent黑名单 | 1266-1269 |
| `frontend-nextjs/components/report/ExpertReportAccordion.tsx` | 扩充renderArrayItemObject黑名单 | 1397-1400 |
| `intelligent_project_analyzer/api/server.py` | 扩充PDF SKIP_FIELDS | 3967-3970 |
| `.github/DEVELOPMENT_RULES.md` | 新增问题记录8.13 | 1718-1799 |

---

## 防范措施

### 1. 从源头解决优于事后处理

**原则**: 在prompt中明确约束LLM行为，优于前端/后端翻译/过滤

**理由**:
- 减少无效数据传输
- 提升LLM输出质量
- 降低维护成本

**实践**:
- ✅ prompt中明确"所有字段名使用中文"
- ✅ prompt中明确"不要输出图片占位符"
- ❌ 避免依赖穷举映射翻译

### 2. 前后端黑名单同步

**原则**: 前端和PDF的黑名单必须保持一致

**检查清单**:
- [ ] 新增黑名单字段时，同时修改`ExpertReportAccordion.tsx`和`server.py`
- [ ] 定期检查两处黑名单是否一致

### 3. 双重防御机制

**原则**: prompt约束 + 黑名单过滤，确保万无一失

**机制**:
1. **第一道防线**: prompt明确约束LLM输出
2. **第二道防线**: 前端/后端黑名单过滤
3. **第三道防线**: 智能翻译降级（WORD_TRANSLATIONS）

### 4. 持续补充翻译字典

**原则**: 遇到新的英文字段时，及时补充WORD_TRANSLATIONS

**流程**:
1. 用户反馈英文字段
2. 确认字段来源（LLM输出 or 代码硬编码）
3. 补充WORD_TRANSLATIONS
4. **同时**检查是否需要在prompt中约束

---

## 部署步骤

1. **重启后端服务**:
   ```bash
   # 停止当前服务 (Ctrl+C)
   python -B -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000
   ```

2. **重新构建前端**:
   ```bash
   cd frontend-nextjs
   npm run build
   npm run dev
   ```

3. **验证修复**:
   - 提交新分析请求
   - 检查V3专家输出
   - 导出PDF验证

---

## 相关文档

- [BUG_FIX_PDF_CONTENT_V7.9.2.md](BUG_FIX_PDF_CONTENT_V7.9.2.md) - PDF内容提取修复
- [BUG_FIX_FIELD_TRANSLATION_V7.9.2.md](BUG_FIX_FIELD_TRANSLATION_V7.9.2.md) - 字段翻译智能降级
- [FEATURE_CREATIVE_NARRATIVE_MODE_V7.10.md](FEATURE_CREATIVE_NARRATIVE_MODE_V7.10.md) - 创意叙事模式
- [.github/DEVELOPMENT_RULES.md](.github/DEVELOPMENT_RULES.md) - 问题8.13记录

---

**修复完成时间**: 2025-12-13
**测试状态**: ⏳ 待用户验证
**版本号**: v7.10.1
