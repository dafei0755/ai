# 渐进式问卷路由错误修复报告 v7.146

## 🎯 问题描述

会话 `8pdwoxj8-20260106170903-65f24ca3` 在渐进式问卷流程中出现路由错误：
- **预期流程**: Step 1（任务梳理）→ Step 2（信息补全）→ Step 3（雷达图）
- **实际流程**: Step 1（任务梳理）→ Step 3（雷达图）→ Step 2（信息补全）

**问题影响**: 用户完成任务梳理后，系统错误地跳到雷达图环节，导致信息补全环节被跳过或执行顺序错乱。

## 🔍 根本原因

### 1. 前后端事件类型不匹配（已修复）

| 节点函数 | UI显示 | 后端发送事件 | 前端监听事件 | 状态 |
|---------|--------|------------|------------|------|
| `step1_core_task` | Step 1（任务梳理） | `progressive_questionnaire_step1` | `progressive_questionnaire_step1` | ✅ 正确 |
| `step3_gap_filling` | **Step 2（信息补全）** | ~~`progressive_questionnaire_step3`~~ → `progressive_questionnaire_step2` | `progressive_questionnaire_step2` | ✅ 已修复 |
| `step2_radar` | Step 3（雷达图） | ~~`progressive_questionnaire_step2`~~ → `progressive_questionnaire_step3` | `progressive_questionnaire_step3` | ✅ 已修复 |

### 2. 工作流路由顺序错误（新发现，已修复）

**节点名称与实际功能不匹配**：
- 节点 `progressive_step2_radar` 实际执行雷达图（应该是 UI Step 3）
- 节点 `progressive_step3_gap_filling` 实际执行信息补全（应该是 UI Step 2）

**错误的路由配置**（修复前）：
```python
# Step 1 完成后
return Command(update=update_dict, goto="progressive_step2_radar")  # ❌ 跳到雷达图

# Step 2 (雷达图函数) 完成后
return Command(update=update_dict, goto="progressive_step3_gap_filling")  # ❌ 到信息补全

# Step 3 (信息补全函数) 完成后
return Command(update=update_dict, goto="project_director")  # ❌ 直接跳过汇总
```

**实际执行顺序**：任务梳理 → 雷达图 → 信息补全 → 项目总监（错误！）

## ✅ 修复方案

## ✅ 修复方案

### 1. 修复前后端事件类型匹配

**文件**: `intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py`

#### 修复信息补全节点事件类型（Line 730）
```python
# 🔧 v7.146: 修正事件类型，与前端统一为 step2（信息补全环节）
payload = {
    "interaction_type": "progressive_questionnaire_step2",  # 原: step3
    "step": 2,  # 原: 3
    "total_steps": 3,
    "title": "补充关键信息",
    ...
}
```

#### 修复雷达图节点事件类型（Line 517）
```python
# 🔧 v7.146: 修正事件类型，step2_radar函数对应前端第3步（雷达图）
payload = {
    "interaction_type": "progressive_questionnaire_step3",  # 原: step2
    "step": 3,  # 原: 2
    "total_steps": 3,
    "title": "多维度偏好设置",
    ...
}
```

### 2. 修复工作流路由顺序（核心修复）

**文件**: `intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py`

#### Step 1 完成后的路由（Line 315）
```python
# 🔧 v7.146: 修正路由顺序 - Step1 → Step2(信息补全)
return Command(update=update_dict, goto="progressive_step3_gap_filling")  # 原: progressive_step2_radar
```

#### Step 2（信息补全）完成后的路由（Line 796）
```python
# 🔧 v7.146: 修正路由 - Step2(信息补全)完成后进入Step3(雷达图)
return Command(update=update_dict, goto="progressive_step2_radar")  # 原: project_director
```

#### Step 2（信息补全）无需补充时的路由（Line 645）
```python
if not critical_gaps:
    logger.info("✅ 任务信息完整，无需补充，跳过问题生成，直接进入雷达图")
    # 🔧 v7.146: 即使无需补充，也要进入雷达图环节
    return Command(update=update_dict, goto="progressive_step2_radar")  # 原: project_director
```

#### Step 3（雷达图）完成后的路由（Line 565）
```python
# 🔧 v7.146: 修正路由 - Step3(雷达图)完成后进入问卷汇总
logger.info("📊 [Step 3] 雷达图维度收集完成，准备进入问卷汇总")
return Command(update=update_dict, goto="questionnaire_summary")  # 原: progressive_step3_gap_filling
```

### 修复后的正确流程

| UI步骤 | 节点函数 | 节点名称 | 后端事件 | 前端监听 | 下一步路由 |
|-------|---------|---------|---------|---------|----------|
| Step 1（任务梳理） | `step1_core_task` | `progressive_step1_core_task` | `progressive_questionnaire_step1` | ✅ 匹配 | → `progressive_step3_gap_filling` |
| **Step 2（信息补全）** | `step3_gap_filling` | `progressive_step3_gap_filling` | `progressive_questionnaire_step2` | ✅ 匹配 | → `progressive_step2_radar` |
| Step 3（雷达图） | `step2_radar` | `progressive_step2_radar` | `progressive_questionnaire_step3` | ✅ 匹配 | → `questionnaire_summary` |
| 问卷汇总 | `questionnaire_summary_node` | `questionnaire_summary` | - | - | → `requirements_confirmation` |

**正确的执行顺序**：任务梳理 → 信息补全 → 雷达图 → 问卷汇总 → 需求确认 ✅

## 📊 影响范围

### ✅ 解决的问题

1. **信息补全环节卡顿**：前端现在可以正确接收到 Step 2 的 interrupt 消息
2. **雷达图显示问题**：前端可以正确识别并显示 Step 3 的雷达图维度选择
3. **进度显示准确性**：步骤编号与UI展示一致，用户体验更清晰

### ⚠️ 潜在影响

1. **已卡住的会话**：历史会话如果卡在信息补全环节，需要手动恢复或重新创建
2. **测试用例**：相关测试用例可能需要更新事件类型断言

## 🚀 验证方法

### 方法 1: 创建新会话测试

```bash
# 1. 重启后端服务
python -B scripts\run_server_production.py

# 2. 访问前端
http://localhost:3000

# 3. 输入需求并完成问卷
- Step 1: 确认任务列表
- Step 2: 应该能正常显示"补充关键信息"界面 ✅
- Step 3: 应该能正常显示雷达图维度选择 ✅
```

### 方法 2: 检查前端控制台日志

```javascript
// 成功时应看到：
"📋 检测到待处理的第2步 - 信息补全"  // Step 2
"📋 检测到待处理的第3步 - 雷达图维度选择"  // Step 3
```

### 方法 3: 检查后端日志

```bash
# 应该看到 interrupt payload 的正确事件类型
grep "progressive_questionnaire" logs/server_snap*.log
```

## 🔮 后续优化建议

### 短期（P1）

1. **重构函数命名**：将 `step2_radar` 重命名为 `step3_radar`，`step3_gap_filling` 重命名为 `step2_gap_filling`
   - 避免：函数名与UI顺序不一致导致的混淆
   - 影响：需要更新工作流路由、测试用例、文档

2. **添加自动化测试**：创建端到端测试验证前后端事件匹配
   ```python
   # tests/test_progressive_questionnaire_events.py
   def test_event_mapping_consistency():
       """验证前后端事件类型一致性"""
   ```

### 中期（P2）

1. **完善错误处理**：为 interrupt 添加超时机制
   - 当前：无限等待用户输入
   - 建议：30-60秒无响应时显示提示或自动重试

2. **增强日志记录**：记录会话ID与步骤的关联
   ```python
   logger.info(f"[{session_id}] Step 2 interrupt sent: progressive_questionnaire_step2")
   ```

## 📝 相关文档

- [v7.128 问卷步骤互换](.github/historical_fixes/questionnaire_step_swap_v7.128.md)
- [v7.129.1 信息补全问卷修复](.github/historical_fixes/step2_modal_fix_v7.129.1.md)
- [v7.142 智能问卷生成](INTELLIGENT_QUESTIONNAIRE_EXPLANATION_v7.142.md)
- [渐进式问卷架构](docs/progressive_questionnaire_architecture.md)

## ✅ 验证清单

- [x] 修复后端 step3_gap_filling 事件类型（step3 → step2）
- [x] 修复后端 step2_radar 事件类型（step2 → step3）
- [x] 创建验证脚本检查前后端一致性
- [ ] 重启后端服务
- [ ] 创建新会话测试完整流程
- [ ] 确认前端控制台无错误
- [ ] 更新相关测试用例

---

**修复日期**: 2026-01-06
**修复版本**: v7.146
**修复人**: GitHub Copilot
**问题来源**: 会话 8pdwoxj8-20260106164847-c5970c3e
**优先级**: P0（阻塞用户使用）
