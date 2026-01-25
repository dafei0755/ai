# 能力边界机制优化复盘报告

**版本**: v7.130
**日期**: 2026-01-04
**问题**: 信息补全环节出现超出能力边界的交付物（施工图、效果图、软装清单）
**影响**: 用户期望与系统能力不符，导致后续执行环节无法满足需求

---

## 📋 问题复盘

### 问题背景

系统定位为**策略规划工具**，不提供需要专业工具的深度设计工作：

**✅ 支持的交付物**:
- 设计策略文档
- 空间概念描述
- 材料选择指导
- 预算框架
- 分析报告

**❌ 不支持的交付物**:
- CAD施工图（需要AutoCAD等专业工具）
- 3D效果图（需要3ds Max、SketchUp等建模渲染）
- 精确材料清单（需要现场测量和精确计算）
- 精确预算清单（需要实时市场报价）
- BOM清单（需要供应商对接）

### 问题表现

用户在**信息补全问卷**（第2步）中选择"效果图、施工图、软装清单、预算清单"等选项后：
- ❌ 这些超出能力边界的交付物**直接进入系统**
- ❌ 没有经过能力边界检查和转化
- ❌ 用户期望与系统能力产生巨大落差

**相似问题历史**:
- 前几天已有类似讨论
- 今天再次出现，说明根本问题未解决

---

## 🔍 根因分析

### 根因1: 能力边界检查配置错误 ⚠️

**问题配置**:
```yaml
# config/capability_boundary_config.yaml
progressive_step3_gap_filling:
  enabled: true
  check_type: "info"  # ❌ 仅检查信息充足性
```

**问题**: `check_type: "info"` 表示只检查信息是否充足，**不检查交付物能力边界**。

**修复**:
```yaml
progressive_step3_gap_filling:
  enabled: true
  check_type: "full"  # ✅ 完整检查（交付物+信息）
```

### 根因2: 硬编码问题模板包含超出能力选项 ❌

**问题代码**:
```python
# intelligent_project_analyzer/services/task_completeness_analyzer.py
"options": ["设计方案", "效果图", "施工图", "软装清单", "预算清单", "其他"]
```

**问题**: 直接提供了"效果图、施工图、软装清单、预算清单"等超出能力的选项。

**修复**:
```python
"options": [
    "设计策略文档",
    "空间概念描述",
    "材料选择指导",
    "预算框架",
    "分析报告",
    "其他"
],
"context": "系统提供策略性指导，不提供需要专业工具的CAD图纸、3D效果图或精确清单"
```

### 根因3: LLM提示词缺乏能力边界约束 📝

**问题**: `gap_question_generator.yaml` 配置文件中：
- ❌ 没有提及系统能力边界约束
- ❌ 没有说明哪些交付物不支持
- ❌ 没有指导转化规则

**修复**: 添加完整的能力边界约束章节：
```yaml
## ⚠️ 系统能力边界约束

**系统支持的交付物类型**（仅限策略性指导）：
  - ✅ 设计策略文档
  - ✅ 空间概念描述
  - ✅ 材料选择指导
  - ✅ 预算框架
  - ✅ 分析报告

**系统不支持的交付物类型**：
  - ❌ CAD施工图
  - ❌ 3D效果图
  - ❌ 精确材料清单
  - ❌ 精确预算清单
  - ❌ BOM清单

**重要**：询问"交付要求"时必须：
1. 仅提供系统支持的选项
2. 添加说明："系统提供策略性指导，不提供CAD图纸、3D效果图或精确清单"
3. 引导用户期望
```

### 根因4: 代码层面缺少能力边界检查 💻

**问题**: `progressive_questionnaire.py` 的 `step3_gap_filling()` 函数中：
- ❌ 收集用户答案后，没有调用 `CapabilityBoundaryService.check_questionnaire_answers()`
- ❌ 答案直接存入 `gap_filling_answers` 字段
- ❌ 后续节点直接使用，未经转化

**修复**: 添加能力边界检查和转化逻辑：
```python
# 🆕 v7.130: 能力边界检查和转化
if answers and answers.get("deliverables"):
    try:
        from ...services.capability_boundary_service import CapabilityBoundaryService

        check_result = CapabilityBoundaryService.check_questionnaire_answers(
            answers,
            context={"node": "progressive_step3_gap_filling", ...}
        )

        if check_result.get("transformations"):
            # 应用转化规则
            answers = check_result["transformed_answers"]
            logger.info(f"✅ [能力边界] 交付物已转化为系统支持的类型")
    except Exception as e:
        logger.error(f"❌ [能力边界] 检查失败: {e}")
```

---

## ✅ 实施方案

### 1. 修正能力边界检查配置 ✓

**文件**: `config/capability_boundary_config.yaml`

**修改**:
```diff
  progressive_step3_gap_filling:
    enabled: true
-   check_type: "info"
+   check_type: "full"
    auto_transform: true
-   notes: "补充信息时，检查是否提供了足够的细节"
+   notes: "补充信息时，检查交付物能力边界并提供足够的细节"
```

### 2. 清理硬编码问题模板 ✓

**文件**: `intelligent_project_analyzer/services/task_completeness_analyzer.py`

**修改**:
```diff
  "交付要求": {
    "id": "deliverables",
    "question": "您期望的交付物包括哪些？（可多选）",
    "type": "multiple_choice",
-   "options": ["设计方案", "效果图", "施工图", "软装清单", "预算清单", "其他"],
+   "options": [
+       "设计策略文档",
+       "空间概念描述",
+       "材料选择指导",
+       "预算框架",
+       "分析报告",
+       "其他"
+   ],
+   "context": "系统提供策略性指导，不提供需要专业工具的CAD图纸、3D效果图或精确清单",
    "priority": 3,
    "weight": 8,
  }
```

### 3. 强化LLM提示词约束 ✓

**文件**: `intelligent_project_analyzer/config/prompts/gap_question_generator.yaml`

**新增章节**: "⚠️ 系统能力边界约束"（约40行）
- 明确列出支持/不支持的交付物
- 提供转化规则指导
- 强制要求LLM遵循能力边界

### 4. 添加答案转化逻辑 ✓

**文件**: `intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py`

**新增代码**: 在 `step3_gap_filling()` 收集答案后：
```python
# 🆕 v7.130: 能力边界检查和转化（40行）
if answers and answers.get("deliverables"):
    check_result = CapabilityBoundaryService.check_questionnaire_answers(...)
    if check_result.get("transformations"):
        answers = check_result["transformed_answers"]
```

### 5. 添加管理后台监控页面 ✓

**新增文件**: `frontend-nextjs/app/admin/capability-boundary/page.tsx`

**功能**:
- **节点统计**: 各节点违规率、常见转化模式
- **违规记录**: 详细的转化记录列表
- **转化模式**: 支持/不支持的交付物清单，转化规则

**新增API**: `intelligent_project_analyzer/api/admin_routes.py`
- `GET /api/admin/capability-boundary/stats` - 统计数据
- `GET /api/admin/capability-boundary/violations` - 违规记录

---

## 📊 效果预期

### 用户侧

**修复前**:
1. 用户在问卷中选择"效果图、施工图"
2. 系统默默接受
3. 后续无法交付，用户失望 ❌

**修复后**:
1. 用户在问卷中看到"空间概念描述、设计策略文档"等选项
2. 如果通过其他途径输入超出能力的交付物，系统自动转化
3. 日志明确记录转化过程
4. 用户期望与系统能力匹配 ✅

### 系统侧

**新增监控能力**:
- 📊 实时统计各节点的能力边界检查情况
- 📋 记录所有转化操作（原始 → 转化后）
- 📈 趋势分析，识别高风险节点
- ⚠️ 违规率≥30%为高风险，自动告警

**持续优化**:
- 通过监控数据发现用户常见需求误区
- 优化前端引导和说明文字
- 调整能力边界转化规则

---

## 🔄 长期建议

### 1. 前端优化（未实施）

**建议**: 在问卷选项旁添加能力边界提示
```tsx
<option value="设计策略文档">
  设计策略文档 ✅
</option>
<option value="施工图" disabled>
  施工图 ❌ (系统不支持)
</option>
```

**原因**: 本次优化已通过清理选项解决，暂不需要前端提示

### 2. 历史数据迁移

**建议**: 编写脚本对已有会话的 `gap_filling_answers` 进行能力边界转化

**示例**:
```python
# scripts/migrate_capability_boundary.py
for session in get_all_sessions():
    answers = session.get("gap_filling_answers", {})
    if answers.get("deliverables"):
        transformed = apply_capability_transformations(answers)
        update_session(session.id, {"gap_filling_answers": transformed})
```

### 3. 能力边界自适应

**建议**: 根据用户反馈和技术发展，动态调整能力边界

**示例**:
- 如果未来引入自动CAD生成能力 → 调整配置支持"施工图"
- 如果与3D渲染服务集成 → 支持"效果图"

---

## 📝 知识沉淀

### 核心原则

1. **能力边界必须前置声明**: 不能等用户选择后再拒绝
2. **配置驱动检查**: 通过 `capability_boundary_config.yaml` 统一管理
3. **多层防御**: 配置 + 提示词 + 代码检查
4. **监控先行**: 先监控问题，再优化策略

### 最佳实践

1. **问卷设计**:
   - 选项必须符合系统能力
   - 添加说明文字引导用户
   - 避免引发不切实际的期望

2. **能力边界检查**:
   - `check_type: "full"` 用于涉及交付物的节点
   - `check_type: "info"` 仅用于纯信息收集节点
   - `auto_transform: true` 启用自动转化

3. **转化规则**:
   - 施工图 → 设计策略文档
   - 效果图 → 空间概念描述
   - 精确清单 → 指导性框架

---

## 🎯 验收标准

- [x] 配置文件修正（`check_type: "full"`）
- [x] 硬编码问题模板清理
- [x] LLM提示词强化
- [x] 代码层能力边界检查
- [x] 管理后台监控页面
- [ ] 测试覆盖（建议添加单元测试）
- [ ] 文档更新（建议在用户文档中说明系统定位）

---

## 📚 相关文档

- [能力边界配置](../config/capability_boundary_config.yaml)
- [能力边界检测器](../intelligent_project_analyzer/utils/capability_detector.py)
- [能力边界服务](../intelligent_project_analyzer/services/capability_boundary_service.py)
- [需求分析师能力边界声明](../intelligent_project_analyzer/agents/requirements_analyst.py)
- [管理后台监控页面](../frontend-nextjs/app/admin/capability-boundary/page.tsx)

---

**修复人员**: GitHub Copilot
**审核人员**: [待填写]
**上线时间**: [待填写]
**版本标签**: v7.130
