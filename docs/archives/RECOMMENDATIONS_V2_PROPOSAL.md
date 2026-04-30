# 建议提醒生成逻辑优化方案 V2

**创建日期**: 2025-12-10
**核心思路**: 基于用户反馈，使用"重点/难点/易忽略/有风险/理想"等维度分类
**优先级**: P0 (立即实施)

---

## 核心洞察

### 用户真正关心的维度

❌ **不关心**: "2-4周"、"3-6个月"这种抽象时间
✅ **真正关心**:
- **重点**: 哪些是必须做的核心工作
- **难点**: 哪些是技术难度高、容易卡壳的
- **易忽略**: 哪些是容易被遗漏但很重要的
- **有风险**: 哪些是不做会出问题的
- **理想**: 哪些是锦上添花、有余力再做的

---

## 优化方案

### 数据模型

```python
# intelligent_project_analyzer/report/result_aggregator.py

class RecommendationItem(BaseModel):
    """单条建议"""
    model_config = ConfigDict(extra='forbid')

    content: str = Field(description="建议内容（50-150字）")

    # 🆕 核心分类维度
    dimension: Literal[
        "critical",      # 重点：核心工作，必须完成
        "difficult",     # 难点：技术难度高，需要重点攻克
        "overlooked",    # 易忽略：容易被遗漏但很重要
        "risky",         # 有风险：不做会出问题
        "ideal"          # 理想：锦上添花，有余力再做
    ] = Field(description="建议维度分类")

    # 🆕 辅助属性
    reasoning: str = Field(
        description="为什么属于这个维度（1-2句话）"
    )

    source_expert: str = Field(
        description="建议来源专家（如 V2_设计总监_2-2）"
    )

    estimated_effort: Optional[str] = Field(
        default=None,
        description="预估工作量（如'2-3天'、'1周'、'需专业团队'）"
    )

    dependencies: List[str] = Field(
        default=[],
        description="依赖的其他建议内容（用于排序）"
    )


class RecommendationsSection(BaseModel):
    """建议提醒区块"""
    model_config = ConfigDict(extra='forbid')

    recommendations: List[RecommendationItem] = Field(
        description="所有建议列表（按维度分类）"
    )

    summary: str = Field(
        description="建议总览（2-3句话概括核心要点）"
    )
```

---

## LLM提示词设计

```yaml
# config/prompts/result_aggregator.yaml

system_prompt: |
  ...

  ## 📋 建议生成规则（五维度分类法）

  将所有专家的建议整合后，按以下5个维度分类：

  ### 1. 🎯 重点（critical）
  **定义**: 项目的核心工作，必须完成，是项目成功的基石

  **判断标准**:
  - 是否在项目关键路径上
  - 是否直接影响项目核心目标
  - 是否是其他工作的前置依赖

  **示例**:
  - ✅ "确定空间分区与动线布局，完成平面图初稿"
  - ✅ "选定并下单定制家具（吧台、座椅、展示柜）"
  - ✅ "完成消防审批和营业执照办理"

  **数量**: 3-5项（不超过7项）

  ---

  ### 2. 🔥 难点（difficult）
  **定义**: 技术难度高、实施复杂、容易卡壳的工作

  **判断标准**:
  - 是否需要专业技能或特殊资源
  - 是否涉及多方协调或复杂流程
  - 是否有技术不确定性

  **示例**:
  - ✅ "在30㎡极小空间内实现吧台、座位、外摆三区功能，需精密计算动线"
  - ✅ "协调消防、城管、物业三方审批，确保外摆合规"
  - ✅ "在有限预算内实现高品质材料选择，需供应商深度谈判"

  **数量**: 2-4项

  ---

  ### 3. 👁️ 易忽略（overlooked）
  **定义**: 容易被遗漏但很重要的细节，不注意会留下隐患

  **判断标准**:
  - 是否是非显性需求（用户没明确提但很重要）
  - 是否是后期难以补救的工作
  - 是否是跨专业的边界问题

  **示例**:
  - ✅ "预留足够的电源插座和网络接口，避免后期明线改造"
  - ✅ "确保吧台高度符合人体工学，避免员工长期疲劳"
  - ✅ "设计时考虑设备维修通道，避免后期拆装困难"
  - ✅ "提前确认邻里噪音承受度，避免运营后投诉"

  **数量**: 3-5项

  ---

  ### 4. ⚠️ 有风险（risky）
  **定义**: 不做或做不好会导致严重后果的工作

  **判断标准**:
  - 是否涉及安全隐患
  - 是否涉及法律合规
  - 是否影响项目可持续性

  **示例**:
  - ✅ "严格执行消防规范，确保疏散通道畅通（违规将被强制停业）"
  - ✅ "确保食品安全许可齐全，避免卫生部门处罚"
  - ✅ "控制装修成本在预算内，避免资金链断裂"
  - ✅ "提前锁定关键供应商，避免工期延误导致租金损失"

  **数量**: 2-4项

  ---

  ### 5. ✨ 理想（ideal）
  **定义**: 锦上添花的优化项，有余力再做，不做也不影响基本功能

  **判断标准**:
  - 是否是增值服务或体验优化
  - 是否需要额外预算或资源
  - 是否可以后期迭代

  **示例**:
  - ✅ "引入智能硬件优化数据分析，自动调整运营策略"
  - ✅ "设计品牌IP形象，增强门店辨识度"
  - ✅ "增加艺术装置或互动体验区，提升社交传播性"
  - ✅ "开发会员系统和小程序，提升客户粘性"

  **数量**: 2-4项

  ---

  ## 📊 输出格式

  ```json
  {
    "recommendations": [
      {
        "content": "确定空间分区与动线布局，完成平面图初稿",
        "dimension": "critical",
        "reasoning": "这是所有后续工作的基础，不确定平面图无法进行家具定制和施工",
        "source_expert": "V2_设计总监_2-2",
        "estimated_effort": "2-3天",
        "dependencies": []
      },
      {
        "content": "在30㎡极小空间内实现吧台、座位、外摆三区功能，需精密计算动线",
        "dimension": "difficult",
        "reasoning": "空间极小，需要毫米级精度设计，稍有不慎就会导致拥堵或功能缺失",
        "source_expert": "V2_设计总监_2-2",
        "estimated_effort": "需专业设计师，3-5天反复推敲",
        "dependencies": []
      },
      {
        "content": "预留足够的电源插座和网络接口，避免后期明线改造",
        "dimension": "overlooked",
        "reasoning": "用户往往只关注美观，忽略实用性，后期改造成本高且影响美观",
        "source_expert": "V6_专业总工程师_6-3",
        "estimated_effort": "设计阶段提前规划，无额外成本",
        "dependencies": ["确定空间分区与动线布局"]
      },
      {
        "content": "严格执行消防规范，确保疏散通道畅通",
        "dimension": "risky",
        "reasoning": "违反消防规范将被强制停业，且涉及人身安全，绝不能妥协",
        "source_expert": "V6_专业总工程师_6-3",
        "estimated_effort": "设计阶段必须考虑，施工阶段严格执行",
        "dependencies": []
      },
      {
        "content": "引入智能硬件优化数据分析，自动调整运营策略",
        "dimension": "ideal",
        "reasoning": "可以提升运营效率，但不是开业必需，可以后期迭代",
        "source_expert": "V5_场景与行业专家_5-2",
        "estimated_effort": "2-3周，需额外预算2-3万",
        "dependencies": []
      }
    ],
    "summary": "本项目的核心是在28天内完成30㎡精品咖啡店的设计与施工。重点是空间分区和家具定制，难点是极小空间的动线优化，易忽略的是电源网络等隐蔽工程，风险点是消防合规和成本控制，理想优化是智能化运营系统。"
  }
  ```

  ## ⚠️ 重要规则

  ### 分类原则
  1. **互斥性**: 每条建议只能属于一个维度
  2. **完整性**: 所有重要建议都要覆盖
  3. **平衡性**: 避免某个维度过多或过少
  4. **实用性**: 建议必须具体可执行，避免空话套话

  ### 数量控制
  - 重点：3-5项（最多7项）
  - 难点：2-4项
  - 易忽略：3-5项
  - 有风险：2-4项
  - 理想：2-4项
  - **总计**: 12-22项

  ### 内容要求
  - 每条建议50-150字
  - 必须具体可执行
  - 必须标注来源专家
  - 必须说明为什么属于这个维度
```

---

## 前端UI设计

```typescript
// frontend-nextjs/components/report/RecommendationsSection.tsx

import React from 'react';
import {
  Target,        // 🎯 重点
  Flame,         // 🔥 难点
  Eye,           // 👁️ 易忽略
  AlertTriangle, // ⚠️ 有风险
  Sparkles       // ✨ 理想
} from 'lucide-react';

interface RecommendationItem {
  content: string;
  dimension: 'critical' | 'difficult' | 'overlooked' | 'risky' | 'ideal';
  reasoning: string;
  source_expert: string;
  estimated_effort?: string;
  dependencies: string[];
}

interface RecommendationsSectionProps {
  recommendations: {
    recommendations: RecommendationItem[];
    summary: string;
  };
}

const DIMENSION_CONFIG = {
  critical: {
    title: '🎯 重点',
    subtitle: '项目核心工作，必须完成',
    icon: Target,
    color: 'red',
    bgColor: 'bg-red-500/20',
    borderColor: 'border-red-500/30',
    textColor: 'text-red-400'
  },
  difficult: {
    title: '🔥 难点',
    subtitle: '技术难度高，需要重点攻克',
    icon: Flame,
    color: 'orange',
    bgColor: 'bg-orange-500/20',
    borderColor: 'border-orange-500/30',
    textColor: 'text-orange-400'
  },
  overlooked: {
    title: '👁️ 易忽略',
    subtitle: '容易被遗漏但很重要',
    icon: Eye,
    color: 'blue',
    bgColor: 'bg-blue-500/20',
    borderColor: 'border-blue-500/30',
    textColor: 'text-blue-400'
  },
  risky: {
    title: '⚠️ 有风险',
    subtitle: '不做会出问题',
    icon: AlertTriangle,
    color: 'amber',
    bgColor: 'bg-amber-500/20',
    borderColor: 'border-amber-500/30',
    textColor: 'text-amber-400'
  },
  ideal: {
    title: '✨ 理想',
    subtitle: '锦上添花，有余力再做',
    icon: Sparkles,
    color: 'purple',
    bgColor: 'bg-purple-500/20',
    borderColor: 'border-purple-500/30',
    textColor: 'text-purple-400'
  }
};

export default function RecommendationsSection({ recommendations }: RecommendationsSectionProps) {
  if (!recommendations || !recommendations.recommendations) {
    return null;
  }

  // 按维度分组
  const groupedRecommendations = recommendations.recommendations.reduce((acc, item) => {
    if (!acc[item.dimension]) {
      acc[item.dimension] = [];
    }
    acc[item.dimension].push(item);
    return acc;
  }, {} as Record<string, RecommendationItem[]>);

  // 维度顺序
  const dimensionOrder: Array<keyof typeof DIMENSION_CONFIG> = [
    'critical',
    'difficult',
    'overlooked',
    'risky',
    'ideal'
  ];

  return (
    <div id="recommendations" className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-2xl p-6">
      {/* 标题 */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
          <CheckCircle className="w-5 h-5 text-green-400" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-white">建议提醒</h2>
          <p className="text-sm text-gray-400 mt-1">{recommendations.summary}</p>
        </div>
      </div>

      {/* 建议列表 */}
      <div className="space-y-5">
        {dimensionOrder.map(dimension => {
          const items = groupedRecommendations[dimension];
          if (!items || items.length === 0) return null;

          const config = DIMENSION_CONFIG[dimension];
          const Icon = config.icon;

          return (
            <div key={dimension} className="bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg p-5">
              {/* 维度标题 */}
              <div className="flex items-center gap-2 mb-4">
                <div className={`w-8 h-8 rounded-full ${config.bgColor} flex items-center justify-center`}>
                  <Icon className={`w-4 h-4 ${config.textColor}`} />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-white">{config.title}</h3>
                  <p className="text-xs text-gray-400">{config.subtitle}</p>
                </div>
              </div>

              {/* 建议列表 */}
              <ul className="space-y-3">
                {items.map((item, index) => (
                  <li key={index} className={`border ${config.borderColor} rounded-lg p-3`}>
                    {/* 建议内容 */}
                    <div className="flex items-start gap-3">
                      <span className={`flex-shrink-0 w-6 h-6 rounded-full ${config.bgColor} ${config.textColor} text-xs flex items-center justify-center font-semibold mt-0.5`}>
                        {index + 1}
                      </span>
                      <div className="flex-1">
                        <p className="text-sm text-gray-200 leading-relaxed">{item.content}</p>

                        {/* 元信息 */}
                        <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-gray-400">
                          {/* 理由 */}
                          <div className="flex items-center gap-1">
                            <span className="text-gray-500">💡</span>
                            <span>{item.reasoning}</span>
                          </div>

                          {/* 工作量 */}
                          {item.estimated_effort && (
                            <div className="flex items-center gap-1">
                              <span className="text-gray-500">⏱️</span>
                              <span>{item.estimated_effort}</span>
                            </div>
                          )}

                          {/* 来源专家 */}
                          <div className="flex items-center gap-1">
                            <span className="text-gray-500">👤</span>
                            <span>{formatExpertName(item.source_expert)}</span>
                          </div>

                          {/* 依赖 */}
                          {item.dependencies.length > 0 && (
                            <div className="flex items-center gap-1">
                              <span className="text-gray-500">🔗</span>
                              <span>依赖 {item.dependencies.length} 项</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>

      {/* 提示信息 */}
      <div className="mt-6 bg-gradient-to-r from-green-500/5 to-blue-500/5 border border-green-500/20 rounded-lg p-4">
        <p className="text-xs text-gray-400 text-center">
          💡 建议按"重点-难点-易忽略-有风险-理想"五个维度组织，帮助您全面把控项目
        </p>
      </div>
    </div>
  );
}

// 辅助函数：格式化专家名称
function formatExpertName(expertId: string): string {
  // V2_设计总监_2-2 → 设计总监
  const parts = expertId.split('_');
  return parts.length >= 2 ? parts[1] : expertId;
}
```

---

## 视觉效果示例

```
┌─────────────────────────────────────────────────────────────┐
│ 🎯 重点                                                      │
│ 项目核心工作，必须完成                                        │
├─────────────────────────────────────────────────────────────┤
│ 1️⃣ 确定空间分区与动线布局，完成平面图初稿                    │
│    💡 这是所有后续工作的基础                                  │
│    ⏱️ 2-3天 | 👤 设计总监                                    │
│                                                              │
│ 2️⃣ 选定并下单定制家具（吧台、座椅、展示柜）                  │
│    💡 工厂加工需7-10天，必须提前锁定                          │
│    ⏱️ 7-10天 | 👤 成本工程师 | 🔗 依赖 1 项                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 🔥 难点                                                      │
│ 技术难度高，需要重点攻克                                      │
├─────────────────────────────────────────────────────────────┤
│ 1️⃣ 在30㎡极小空间内实现吧台、座位、外摆三区功能              │
│    💡 需要毫米级精度设计，稍有不慎就会拥堵                    │
│    ⏱️ 需专业设计师，3-5天反复推敲 | 👤 设计总监              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 👁️ 易忽略                                                   │
│ 容易被遗漏但很重要                                            │
├─────────────────────────────────────────────────────────────┤
│ 1️⃣ 预留足够的电源插座和网络接口                              │
│    💡 后期改造成本高且影响美观                                │
│    ⏱️ 设计阶段提前规划 | 👤 工程师 | 🔗 依赖 1 项            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ ⚠️ 有风险                                                    │
│ 不做会出问题                                                  │
├─────────────────────────────────────────────────────────────┤
│ 1️⃣ 严格执行消防规范，确保疏散通道畅通                        │
│    💡 违规将被强制停业，涉及人身安全                          │
│    ⏱️ 设计+施工全程 | 👤 工程师                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ ✨ 理想                                                      │
│ 锦上添花，有余力再做                                          │
├─────────────────────────────────────────────────────────────┤
│ 1️⃣ 引入智能硬件优化数据分析                                  │
│    💡 可提升运营效率，但不是开业必需                          │
│    ⏱️ 2-3周，需额外2-3万 | 👤 运营专家                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 实施计划

### Phase 1: 后端模型升级（1小时）
1. ✅ 修改 `RecommendationItem` 模型
2. ✅ 修改 `RecommendationsSection` 模型
3. ✅ 更新类型定义

### Phase 2: 提示词优化（1小时）
1. ✅ 更新 `result_aggregator.yaml`
2. ✅ 添加详细的分类规则和示例
3. ✅ 测试LLM生成质量

### Phase 3: 前端UI重构（2小时）
1. ✅ 实现新的 `RecommendationsSection` 组件
2. ✅ 添加维度配置和图标
3. ✅ 优化卡片布局和样式

### Phase 4: 测试与优化（1小时）
1. ✅ 测试不同项目类型
2. ✅ 调整分类逻辑
3. ✅ 优化UI细节

**总计**: 5小时

---

## 优势对比

| 维度 | 当前方案 | V2方案 |
|------|---------|--------|
| **用户理解成本** | 🔴 高（需理解时间概念） | 🟢 低（直观易懂） |
| **实用性** | 🟡 中（时间标签不准确） | 🟢 高（真正关心的维度） |
| **LLM生成难度** | 🟢 低 | 🟡 中（需理解维度含义） |
| **扩展性** | 🔴 差（固定4个分类） | 🟢 好（可灵活调整） |
| **专业性** | 🟡 中 | 🟢 高（体现专业判断） |

---

## 后续优化方向

### 1. 依赖关系可视化
```
重点1 → 重点2 → 难点1
  ↓
易忽略1
```

### 2. 风险等级标注
```
⚠️ 有风险 1: 严格执行消防规范
   风险等级: 🔴 极高（违规将被强制停业）
```

### 3. 完成度追踪
```
✅ 已完成: 3/5
⏳ 进行中: 1/5
⭕ 未开始: 1/5
```

---

**提案人**: Claude Code
**审核状态**: 待评审
**预计收益**: 显著提升建议的实用性和用户满意度
