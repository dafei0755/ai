# 系统测试指南 - v7.143 问卷汇总修复验证

**测试目的**: 验证问卷汇总超时修复是否生效
**测试日期**: 2026-01-06
**修复版本**: v7.143

---

## 🚀 启动服务

```bash
# 启动生产环境服务器
python -B scripts\run_server_production.py
```

**预期输出**:
```
[INFO] 🔄 Loading prompts from directory...
[OK] ✅ Successfully loaded 19 prompt configuration(s)
INFO: Started server process [xxxxx]
INFO: Uvicorn running on http://0.0.0.0:3001
```

---

## ✅ 测试场景 1: 正常流程验证

### 测试步骤

1. **访问前端页面**
   ```
   http://localhost:3001
   ```

2. **输入测试用例**
   ```
   让安藤忠雄为一个离家多年的50岁男士设计一座田园民居，
   四川广元农村、300平米，室内设计师职业。
   ```

3. **完成三步问卷**
   - Step 1: 任务梳理 → 确认任务列表
   - Step 3: 信息补全 → 填写补充问题
   - Step 2: 雷达维度 → 调整维度偏好

### 关键日志检查点

#### ✅ Step 1 完成
```
📋 [v7.80.1] 拆解出 7 个核心任务
✅ [第1步] 确认 7 个核心任务
```

#### ✅ Step 3 开始 - 专家角色预测
```
🔮 [v7.136] 启用专家视角风险预判
⏱️ [超时保护] 专家角色预测30秒超时...
✅ [专家角色] 预测成功: ['V3_叙事专家', 'V4_设计专家', 'V6_内容专家']
```

**或者超时降级**:
```
⏰ [专家角色] 预测超时(30秒)，跳过专家视角分析
```

#### ✅ Step 3 中间 - 完整性分析
```
⏱️ [超时保护] 完整性分析(含专家视角)60秒超时...
✅ [完整性分析] 专家视角分析成功
```

**或者超时降级**:
```
⏰ [完整性分析] 专家视角分析超时(60秒)，降级到基础分析
📊 [完整性分析] 使用基础分析(无专家视角)
```

#### ✅ Step 3 完成
```
✅ [第2步] 完成，路由到 progressive_step2_radar
```

#### ✅ Step 2 完成
```
✅ [第3步] 雷达图完成
🔄 路由到 questionnaire_summary
```

#### ✅ **关键点**: questionnaire_summary 被调用
```
====================================================================================================
📋 [问卷汇总] ✅ ENTERING questionnaire_summary node
====================================================================================================
🔍 [前置数据检查]
   - confirmed_core_tasks: 7个
   - gap_filling_answers: 5个字段
   - selected_dimensions: 9个
================================================================================
📋 [问卷汇总] 开始生成结构化需求文档
================================================================================
```

#### ✅ LLM 重试机制工作
```
🚀 [LLM摘要] 使用重试机制调用LLM (最多3次尝试, 每次15秒超时)
✅ [LLM摘要] 生成成功: 为离家多年的50岁男性打造田园民居...
```

**或者重试失败降级**:
```
🔄 [LLM重试] 第 1 次重试 | 错误: ConnectError | 等待 1.0s
🔄 [LLM重试] 第 2 次重试 | 错误: ConnectError | 等待 2.0s
⚠️ [LLM摘要] 所有重试失败: ..., 使用简单版本
```

#### ✅ questionnaire_summary 完成
```
✅ 问卷汇总完成
📝 项目目标: 为离家多年的50岁男性设计田园民居...
🎯 设计重点: 7个维度
⚠️  风险识别: 2项
📊 洞察评分: 0.85
====================================================================================================
📋 [问卷汇总] ✅ EXITING questionnaire_summary node - SUCCESS
   返回字段: ['restructured_requirements', 'requirements_summary_text', 'structured_requirements', 'questionnaire_summary_completed', 'detail']
====================================================================================================
```

---

## ⚠️ 测试场景 2: 超时降级验证

### 模拟方法

**方法1**: 临时禁用网络访问（模拟LLM连接失败）

**方法2**: 设置环境变量（禁用耗时功能）
```bash
# 测试基础分析降级
set ENABLE_EXPERT_FORESIGHT=false
python -B scripts\run_server_production.py
```

### 预期日志

#### ✅ 跳过专家视角
```
⏩ [v7.136] 跳过专家视角风险预判(环境变量禁用)
📊 [完整性分析] 使用基础分析(无专家视角)
```

#### ✅ 仍然完成流程
```
✅ [第2步] 完成，路由到 progressive_step2_radar
📋 [问卷汇总] ✅ ENTERING questionnaire_summary node  # ← 关键：仍然被调用
✅ 问卷汇总完成
```

---

## 🔍 测试场景 3: 异常恢复验证

### 测试步骤

1. 在Step 3运行过程中，强制断开网络
2. 观察系统是否自动降级并继续

### 预期行为

#### ✅ 超时后自动恢复
```
⏰ [专家角色] 预测超时(30秒)，跳过专家视角分析
📊 [完整性分析] 使用基础分析(无专家视角)
✅ [第2步] 完成，路由到 progressive_step2_radar  # ← 仍然继续
```

#### ✅ 紧急降级（如果整个Step 3失败）
```
❌ [第2步] 严重错误: ...
🔍 [错误堆栈] ...
⚠️ [第2步] 使用降级模式继续流程 → progressive_step2_radar
```

---

## 📊 性能基准测试

### 时间基准

| 阶段 | 正常耗时 | 超时阈值 | 降级耗时 |
|------|----------|----------|----------|
| 专家角色预测 | 5-10秒 | 30秒 | 0秒（跳过） |
| 完整性分析 | 10-30秒 | 60秒 | 5秒（基础分析） |
| LLM摘要生成 | 5-15秒 | 45秒（3×15） | 0秒（模板） |
| **Step 3 总计** | 20-55秒 | 90秒 | 5-10秒 |

### 测试命令

```bash
# 记录完整流程时间
# 从 Step 1 开始 → questionnaire_summary 结束
```

**目标**:
- ✅ Step 3 在 **90秒内**完成（有超时保护）
- ✅ questionnaire_summary **总是被调用**
- ✅ 即使降级，数据质量 > **70%**

---

## ✅ 验证清单

### 必须通过项

- [ ] **服务启动成功** - 无启动错误
- [ ] **Step 1 完成** - 任务拆解成功
- [ ] **Step 3 开始** - 进入信息补全阶段
- [ ] **专家角色预测** - 成功或超时降级
- [ ] **完整性分析** - 成功或超时降级
- [ ] **Step 3 完成** - 返回 Command，路由到 Step 2
- [ ] **Step 2 完成** - 雷达维度收集完成
- [ ] **questionnaire_summary 被调用** - 出现 ENTERING 日志 ⭐
- [ ] **需求文档生成** - restructured_requirements 存在
- [ ] **questionnaire_summary 成功** - 出现 EXITING 日志 ⭐
- [ ] **流程继续** - 进入 requirements_confirmation

### 降级功能验证

- [ ] **专家角色超时** - 30秒后自动跳过
- [ ] **完整性分析超时** - 60秒后降级到基础分析
- [ ] **LLM摘要重试** - 3次重试后降级到模板
- [ ] **Step 3 异常** - 捕获并紧急降级
- [ ] **数据缺失容忍** - gap_filling_answers 为空时仍能继续

---

## 📋 测试报告模板

### 测试环境
- OS: Windows 11
- Python: 3.13
- 分支: 20260104
- 提交: [最新commit hash]

### 测试结果

#### 场景1: 正常流程
- [ ] 通过 ✅
- [ ] 失败 ❌

**日志截图位置**: `logs/test_normal_flow.txt`

**questionnaire_summary 调用**:
- [ ] 是 ✅
- [ ] 否 ❌

**耗时**: Step 3 = ___秒, 总计 = ___秒

#### 场景2: 超时降级
- [ ] 通过 ✅
- [ ] 失败 ❌

**降级次数**: ___次
**最终数据质量**: ___%

#### 场景3: 异常恢复
- [ ] 通过 ✅
- [ ] 失败 ❌

**异常类型**: ___
**恢复成功**:
- [ ] 是 ✅
- [ ] 否 ❌

---

## 🐛 如果测试失败

### 问题诊断

1. **questionnaire_summary 未被调用**
   ```bash
   # 搜索日志
   grep "ENTERING questionnaire_summary" logs/*.log

   # 如果没有，检查 Step 2 路由
   grep "路由到 questionnaire_summary" logs/*.log
   ```

2. **Step 3 仍然卡住**
   ```bash
   # 检查超时保护是否生效
   grep "超时保护" logs/*.log
   grep "降级" logs/*.log
   ```

3. **数据生成失败**
   ```bash
   # 检查 restructured_requirements
   grep "restructured_requirements" logs/*.log
   grep "降级模式" logs/*.log
   ```

### 回滚方案

如果测试失败，可以：
```bash
# 查看修改的文件
git status

# 查看具体修改
git diff

# 如需回滚
git checkout -- intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py
git checkout -- intelligent_project_analyzer/interaction/nodes/questionnaire_summary.py
git checkout -- intelligent_project_analyzer/interaction/nodes/requirements_restructuring.py
```

---

## 📞 支持

**问题反馈**:
- 日志位置: `logs/`
- 配置文件: `intelligent_project_analyzer/settings.py`
- 环境变量: `.env.development.example` / `.env.production.example`

**关键环境变量**:
```bash
# 禁用耗时功能（加速测试）
ENABLE_EXPERT_FORESIGHT=false
USE_LLM_GAP_QUESTIONS=false
USE_DYNAMIC_GENERATION=false
```

---

**测试完成后**: 请更新 [BUGFIX_v7.143_QUESTIONNAIRE_SUMMARY_TIMEOUT_FIX.md](docs/BUGFIX_v7.143_QUESTIONNAIRE_SUMMARY_TIMEOUT_FIX.md) 中的**测试状态**字段。
