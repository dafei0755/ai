# 🧠 维度学习系统技术文档

> **版本**: v7.105
> **日期**: 2025-12-31
> **状态**: ✅ MVP 已实现（混合策略）

---

## 📋 系统概述

维度学习系统是对雷达图维度选择器的智能化升级，实现从硬编码维度池到数据驱动的自适应推荐引擎。系统采用**混合策略（80% 规则引擎 + 20% 学习优化）**解决冷启动问题，随历史数据累积逐步提高学习权重（10%→20%→40%→70%），最终达到智能化、自主学习的维度生成能力。

### 核心特性

1. **混合策略架构** - 规则引擎兜底 + 学习优化增强
2. **动态学习权重** - 根据历史数据量自动调整
3. **多维度评分** - 使用频率 + 用户评分 + Gap跟进 + 完成率
4. **渐进式反馈收集** - 非侵入式抽样评分（20%用户）
5. **向后兼容** - 无数据时自动降级到规则引擎

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                  用户会话流程（V7.105）                  │
└─────────────────────────────────────────────────────────┘

1. 用户输入 → Step 1（任务拆解）→ Step 2（维度选择）
                                      │
                                      ▼
                          ┌───────────────────────┐
                          │ AdaptiveDimensionGen  │  🆕
                          │  ┌──────────────────┐ │
                          │  │ 规则引擎（80%）  │ │
                          │  │ - Required维度   │ │
                          │  │ - Recommended    │ │
                          │  │ - 关键词匹配     │ │
                          │  │ - 场景注入       │ │
                          │  └──────────────────┘ │
                          │  ┌──────────────────┐ │
                          │  │ 学习优化（20%）  │ │ 🆕
                          │  │ - 计算维度得分   │ │
                          │  │ - 替换低效维度   │ │
                          │  │ - 选择高价值维度 │ │
                          │  └──────────────────┘ │
                          └───────────────────────┘
                                      │
                                      ▼
2. 用户填写雷达图 → Gap 分析 → Step 3（补充问题）
                                      │
                                      ▼
3. 报告生成 → 反馈收集（20%抽样）🆕
      │                      │
      │                      ▼
      │            ┌──────────────────┐
      │            │ DimensionTracker  │ 🆕
      │            │  - track_selection│
      │            │  - track_feedback │
      │            │  - track_gap_analysis│
      │            └──────────────────┘
      │                      │
      │                      ▼
      │            ┌──────────────────┐
      │            │ DimensionEvaluator│ 🆕
      │            │  - calculate_score│
      │            │  - identify_redundant│
      │            │  - identify_high_value│
      │            └──────────────────┘
      │                      │
      └──────────────────────┘
                  ▲
                  │
          （循环学习优化）
```

---

## 📦 核心模块

### 1. DimensionUsageTracker（数据收集）

**文件**: `intelligent_project_analyzer/services/dimension_usage_tracker.py`

**功能**:
- 记录维度选择过程（来源、策略分布）
- 记录用户反馈（星级评分、文本评论）
- 记录Gap分析效果（是否触发后续补充）

**数据结构**:
```python
dimension_usage_metadata = {
    "selection": {
        "dimension_ids": ["cultural_axis", "tech_visibility", ...],
        "dimension_sources": {
            "cultural_axis": "rule_engine",
            "spiritual_atmosphere": "learning_optimized"  # 学习替换的
        },
        "selection_strategy": {
            "required": 3,
            "recommended": 5,
            "keyword": 2,
            "scene": 1
        }
    },
    "feedback": {
        "dimension_ratings": {
            "cultural_axis": 5,
            "tech_visibility": 4,
            "privacy_level": 2
        },
        "avg_rating": 3.67,
        "useful_dimensions": ["cultural_axis", "tech_visibility"],
        "ineffective_dimensions": ["privacy_level"]
    },
    "gap_analysis": {
        "gap_dimension_ids": ["privacy_level"],
        "user_provided_followup": true,
        "gap_effective": true
    }
}
```

**关键方法**:
- `track_selection()` - 在Step 2选择后立即调用
- `track_user_feedback()` - 前端提交评分时调用
- `track_gap_analysis()` - Gap分析完成后调用
- `build_session_metadata()` - 构建完整元数据保存到session_data

---

### 2. DimensionEvaluator（效果评估）

**文件**: `intelligent_project_analyzer/services/dimension_evaluator.py`

**功能**:
- 计算维度综合得分（0-100分）
- 识别冗余维度（得分<30）
- 识别高价值维度（得分>75）
- 统计维度详细信息

**评分算法**:
```python
score = 0.25 * usage_frequency      # 使用频率（归一化到0-100）
      + 0.35 * avg_user_rating      # 平均评分（1-5 → 0-100）
      + 0.25 * gap_follow_rate      # Gap后续行动率（0-100）
      + 0.15 * report_completion    # 报告完成率（0-100）
```

**示例**:
```python
evaluator = DimensionEvaluator()

# 计算单个维度得分
score = evaluator.calculate_dimension_score(
    dimension_id="cultural_axis",
    historical_data=sessions  # 历史会话列表
)
# 输出: 82.5（高价值维度）

# 批量计算
scores = evaluator.batch_calculate_scores(
    dimension_ids=all_dimension_ids,
    historical_data=sessions
)
# 输出: {"cultural_axis": 82.5, "privacy_level": 28.3, ...}

# 识别冗余维度
redundant = evaluator.identify_redundant_dimensions(
    dimension_scores=scores,
    threshold=30.0
)
# 输出: [("privacy_level", 28.3), ("cost_sensitivity", 25.1)]
```

---

### 3. AdaptiveDimensionGenerator（自适应生成）

**文件**: `intelligent_project_analyzer/services/adaptive_dimension_generator.py`

**功能**:
- 混合策略选择（规则引擎 + 学习优化）
- 学习权重动态调整（基于历史数据量）
- 替换低效维度为高价值维度
- 策略摘要统计

**学习权重配置**:
```python
learning_weight_thresholds = {
    "minimal": (0, 50, 0.10),      # 0-50会话: 10%学习权重
    "low": (50, 200, 0.20),         # 50-200会话: 20%学习权重
    "medium": (200, 500, 0.40),     # 200-500会话: 40%学习权重
    "high": (500, float('inf'), 0.70)  # 500+会话: 70%学习权重
}
```

**核心流程**:
```python
# 1. 基础选择（规则引擎）
base_dimensions = base_selector.select_for_project(
    project_type=project_type,
    user_input=user_input,
    special_scenes=special_scenes
)  # 9-12个维度

# 2. 学习优化（如果启用）
if learning_enabled and historical_data:
    # 计算所有维度得分
    dimension_scores = evaluator.batch_calculate_scores(
        dimension_ids=all_dimension_ids,
        historical_data=historical_data
    )

    # 识别低效维度
    low_score_dims = [d for d in base_dimensions if scores[d.id] < 40]

    # 计算替换数量（基于学习权重）
    learning_weight, stage = get_learning_weight(len(historical_data))
    replacements = int(len(low_score_dims) * learning_weight)

    # 替换为高价值维度
    for i in range(replacements):
        remove low_score_dims[i]
        add high_value_candidates[i]
```

**环境变量**:
```env
# 启用学习系统（默认禁用）
ENABLE_DIMENSION_LEARNING=true
```

---

### 4. 前端反馈组件

**文件**: `frontend-nextjs/components/DimensionFeedbackModal.tsx`

**功能**:
- 延迟弹出（Step 2提交后3秒）
- 抽样展示（20%用户）
- 星级评分（1-5星）
- 可选文本反馈

**调用示例**:
```typescript
// 在 UnifiedQuestionnaireModal.tsx 中集成

import { DimensionFeedbackModal } from '@/components/DimensionFeedbackModal';

// Step 2 提交后
const handleStep2Submit = async (dimensionValues) => {
  // 1. 正常流程
  await submitStep2(dimensionValues);

  // 2. 延迟弹出反馈（抽样20%）
  setTimeout(() => {
    if (Math.random() < 0.2) {  // 20%概率
      setShowFeedbackModal(true);
    }
  }, 3000);  // 延迟3秒
};

// 渲染
<DimensionFeedbackModal
  isOpen={showFeedbackModal}
  onClose={() => setShowFeedbackModal(false)}
  dimensions={selectedDimensions}
  sessionId={sessionId}
/>
```

---

### 5. API端点

**文件**: `intelligent_project_analyzer/api/routes/dimension_feedback.py`

**端点**:

#### POST /api/v1/dimensions/feedback
提交维度反馈

**请求**:
```json
{
  "session_id": "abc-123",
  "dimension_ratings": {
    "cultural_axis": 5,
    "tech_visibility": 4,
    "privacy_level": 2
  },
  "feedback_text": "文化维度很有用，但隐私维度对我的项目不太适用",
  "completion_time": 45.3
}
```

**响应**:
```json
{
  "success": true,
  "message": "反馈提交成功，感谢您的宝贵意见！",
  "feedback_id": "abc-123_feedback",
  "avg_rating": 3.67
}
```

#### GET /api/v1/dimensions/feedback/{session_id}
获取会话的反馈数据

**响应**:
```json
{
  "has_feedback": true,
  "feedback": {
    "dimension_ratings": {...},
    "avg_rating": 3.67,
    "useful_dimensions": ["cultural_axis", "tech_visibility"],
    "ineffective_dimensions": ["privacy_level"]
  }
}
```

---

## 🔄 数据流详解

### 完整会话流程

```
1. 用户输入 → Step 1（任务拆解）
   ├─ 特殊场景检测（8种场景）
   └─ 确认任务列表

2. Step 2（维度选择）
   ├─ AdaptiveDimensionGenerator.select_for_project()
   │   ├─ 基础选择（DimensionSelector）
   │   │   ├─ required 维度（3-5个）
   │   │   ├─ recommended 维度（3-5个）
   │   │   ├─ 关键词匹配（1-3个）
   │   │   └─ 场景注入（0-2个）
   │   └─ 学习优化（如果启用）
   │       ├─ 加载历史数据（从Redis/归档）
   │       ├─ 计算所有维度得分
   │       ├─ 识别低效维度（<40分）
   │       ├─ 计算学习权重（10%-70%）
   │       ├─ 确定替换数量
   │       └─ 用高价值维度替换
   ├─ DimensionUsageTracker.track_selection()
   │   └─ 保存选择元数据到 session_data
   └─ 用户填写雷达图

3. Gap 分析
   ├─ 识别短板维度（值<25 或 >75）
   ├─ DimensionUsageTracker.track_gap_analysis()
   └─ 可选：生成补充问题

4. Step 3（任务完整性）
   └─ 补充信息收集

5. 报告生成
   └─ 完成会话

6. 反馈收集（20%抽样）
   ├─ 延迟3秒弹出 DimensionFeedbackModal
   ├─ 用户评分（1-5星）
   ├─ POST /api/v1/dimensions/feedback
   ├─ DimensionUsageTracker.track_user_feedback()
   └─ 更新 session_data.dimension_usage_metadata.feedback

7. 后续会话
   ├─ 加载历史数据
   ├─ DimensionEvaluator.batch_calculate_scores()
   └─ AdaptiveDimensionGenerator 应用学习结果
```

---

## 📊 性能指标（KPI）

### 系统指标

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| **维度准确率** | >85% | 用户评分 ≥4 的比例 |
| **Gap 召回率** | >90% | Gap识别后用户补充信息的比例 |
| **报告完成率** | >95% | 使用优化维度后的完成率 |
| **平均维度数** | 9-11 | 动态生成的平均维度数 |
| **学习收敛速度** | 200会话 | 达到40%学习权重所需数据量 |

### 维度得分示例

```python
# 高价值维度（>75分）
"cultural_axis": 82.5
- 使用频率: 85/100（85%会话使用）
- 平均评分: 90/100（4.6星）
- Gap跟进率: 75/100（75%触发后有跟进）
- 完成率: 95/100（95%完成报告）

# 低效维度（<30分）
"privacy_level": 28.3
- 使用频率: 40/100（40%会话使用）
- 平均评分: 30/100（2.2星）
- Gap跟进率: 20/100（20%跟进）
- 完成率: 85/100（85%完成）
```

---

## 🧪 测试与验证

### 单元测试

```bash
# 测试数据收集
pytest tests/services/test_dimension_usage_tracker.py

# 测试效果评估
pytest tests/services/test_dimension_evaluator.py

# 测试自适应生成
pytest tests/services/test_adaptive_dimension_generator.py

# 测试API端点
pytest tests/api/test_dimension_feedback_routes.py
```

### 集成测试

```bash
# 完整流程测试（含学习循环）
pytest tests/integration/test_dimension_learning_flow.py
```

### A/B测试设计

```python
# 分流策略
def get_strategy(session_id: str) -> str:
    if hash(session_id) % 100 < 20:  # 20%实验组
        return "learning_optimized"
    else:
        return "baseline"

# 对比指标
metrics = {
    "baseline": {
        "avg_rating": 3.8,
        "gap_follow_rate": 0.75,
        "completion_rate": 0.92
    },
    "learning_optimized": {
        "avg_rating": 4.2,  # 提升 10.5%
        "gap_follow_rate": 0.85,  # 提升 13.3%
        "completion_rate": 0.96   # 提升 4.3%
    }
}
```

---

## 🚀 部署与配置

### 环境变量

```env
# 维度学习系统开关（默认禁用）
ENABLE_DIMENSION_LEARNING=true

# 学习权重配置（可选，覆盖默认值）
DIMENSION_LEARNING_WEIGHT_MINIMAL=0.10  # 0-50会话
DIMENSION_LEARNING_WEIGHT_LOW=0.20      # 50-200会话
DIMENSION_LEARNING_WEIGHT_MEDIUM=0.40   # 200-500会话
DIMENSION_LEARNING_WEIGHT_HIGH=0.70     # 500+会话

# 反馈抽样率（默认20%）
DIMENSION_FEEDBACK_SAMPLE_RATE=0.20

# 评分阈值
DIMENSION_LOW_SCORE_THRESHOLD=40.0      # 低效维度阈值
DIMENSION_HIGH_SCORE_THRESHOLD=75.0     # 高价值维度阈值
```

### 启动顺序

```bash
# 1. 确保Redis运行
docker run -d -p 6379:6379 redis:alpine

# 2. 启动后端（启用学习）
export ENABLE_DIMENSION_LEARNING=true
python -B run_server_production.py

# 3. 启动前端
cd frontend-nextjs
npm run dev
```

### 灰度发布

```python
# 方案1: 环境变量控制（推荐）
if os.getenv("ENABLE_DIMENSION_LEARNING", "false").lower() == "true":
    use_adaptive_generator()
else:
    use_legacy_selector()

# 方案2: 用户级分流
if user_id % 100 < 20:  # 20%用户
    use_adaptive_generator()

# 方案3: 会话级分流
if session_id.hash() % 100 < 20:  # 20%会话
    use_adaptive_generator()
```

---

## 📈 监控与告警

### 关键监控指标

```python
# 1. 学习系统使用率
learning_usage_rate = sessions_with_learning / total_sessions

# 2. 替换维度数量
avg_replacements_per_session = sum(replacements) / len(sessions)

# 3. 用户反馈参与率
feedback_participation_rate = sessions_with_feedback / total_sessions

# 4. 学习权重分布
weight_distribution = {
    "minimal (10%)": count_0_50,
    "low (20%)": count_50_200,
    "medium (40%)": count_200_500,
    "high (70%)": count_500_plus
}
```

### 日志示例

```log
[AdaptiveDimGen] 学习优化开始 - 历史数据:125条, 学习权重:20%, 阶段:low
[AdaptiveDimGen] 发现3个低效维度, 计划替换1个
[AdaptiveDimGen] 替换维度 - 移除:privacy_level(得分:28.3) → 添加:spiritual_atmosphere(得分:78.5)
[AdaptiveDimGen] 学习优化完成 - 替换数量:1, 最终维度数:10

[DimensionTracker] 记录维度选择 - 会话:abc-123, 维度数:10, 策略:{"required":3, "recommended":5, "keyword":1, "learning":1}
[DimensionTracker] 记录用户反馈 - 会话:abc-123, 平均评分:4.20, 有用维度:8, 低效维度:1

[DimensionEval] 维度评分 - cultural_axis: 总分=82.5, 使用率=85.0, 评分=90.0, Gap跟进=75.0, 完成率=95.0
```

---

## 🔧 常见问题（FAQ）

### Q1: 为什么选择混合策略而不是完全LLM生成？

**A**: 混合策略的优势：
1. **冷启动友好** - 无历史数据时规则引擎兜底
2. **成本可控** - 避免频繁LLM调用
3. **稳定性高** - 规则引擎保证基础质量
4. **渐进式优化** - 随数据累积逐步智能化

### Q2: 学习权重如何调整？

**A**: 权重阶梯设计考虑：
- **0-50会话（10%）** - 数据太少，仅做小规模试探
- **50-200会话（20%）** - 初步积累，适度优化
- **200-500会话（40%）** - 数据可信，加大学习比重
- **500+会话（70%）** - 充分学习，主导策略

可根据实际效果调整环境变量 `DIMENSION_LEARNING_WEIGHT_*`。

### Q3: 如何处理反馈偏差？

**A**: 缓解措施：
1. **隐式反馈** - 报告完成=正向信号（无需主动评分）
2. **抽样策略** - 仅向20%用户展示评分弹窗
3. **默认中性** - 无评分时默认3分（中性）
4. **多指标融合** - 结合使用频率、Gap跟进等客观指标

### Q4: 维度池会无限膨胀吗？

**A**: 控制机制：
1. **学习替换而非新增** - 替换低效维度，总数不变
2. **最大容量限制** - 维度池上限50个
3. **定期清理** - 得分<30且使用<3次的维度归档
4. **人工审核** - 标记"黄金维度"永久保留

### Q5: 如何回滚到旧版本？

**A**: 简单！
```env
# 禁用学习系统，恢复纯规则引擎
ENABLE_DIMENSION_LEARNING=false
```

重启服务器即可，无需修改代码。

---

## 📚 参考资料

### 相关文件

- [维度配置](../config/prompts/radar_dimensions.yaml)
- [原始维度选择器](../services/dimension_selector.py)
- [会话归档管理器](../services/session_archive_manager.py)
- [Redis会话管理器](../services/redis_session_manager.py)

### 设计文档

- [V7.105问卷升级报告](../../V7105_QUESTIONNAIRE_UPGRADE_REPORT.md)
- [问卷统一体验文档](../../QUESTIONNAIRE_UI_UNIFIED_v7.109.md)
- [专家工厂架构文档](../../docs/EXPERT_FACTORY_ARCHITECTURE.md)

### 历史修复

- [问卷系统重构](../../.github/historical_fixes/questionnaire_system_refactor.md)
- [雷达图性能优化](../../.github/historical_fixes/radar_chart_performance.md)

---

## 🎯 未来规划

### Phase 2（2-3个月）

- [ ] LLM辅助新维度建议
- [ ] 维度模板化生成引擎
- [ ] 多模态输入支持（图片→维度）
- [ ] 用户画像系统（历史偏好预填）

### Phase 3（6个月）

- [ ] 深度学习模型（Transformer编码器）
- [ ] 实时个性化推荐
- [ ] 跨项目迁移学习
- [ ] 维度自动扩展机制

---

## 👥 贡献者

- **dafei0755** - 系统设计与实现
- **AI Assistant** - 代码审查与文档编写

---

## 📄 许可证

MIT License - 详见 [LICENSE](../../LICENSE)

---

<div align="center">

**版本**: v7.105 | **最后更新**: 2025-12-31

🧠 维度学习系统 - 让雷达图更懂你的需求

Made with ❤️ by LangGraph Design Team

</div>
