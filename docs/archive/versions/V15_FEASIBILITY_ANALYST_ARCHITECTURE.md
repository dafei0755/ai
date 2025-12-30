# V1.5 项目可行性分析师 - 架构设计文档

**版本**: v1.0
**最后更新**: 2025-12-06
**作者**: AI Project Analyzer Team

---

## 目录

1. [架构概览](#架构概览)
2. [设计动机](#设计动机)
3. [双轨并行范式](#双轨并行范式)
4. [核心组件](#核心组件)
5. [数据流](#数据流)
6. [与V1的关系](#与v1的关系)
7. [技术实现](#技术实现)
8. [扩展性](#扩展性)

---

## 架构概览

V1.5项目可行性分析师（Feasibility Analyst）是对V1需求分析师的**互补增强**，形成"双轨并行"架构：

```
用户输入
    ↓
┌────────────────────────────────────────────────┐
│ V1 需求分析师 (Requirements Analyst)            │
│ 范式: 战略洞察 (Strategic Insight)              │
│ 关注: 人的深层需求、身份认同、价值冲突         │
│ 输出: project_task, design_challenge, ...      │
└────────────────┬───────────────────────────────┘
                 ↓
┌────────────────────────────────────────────────┐
│ V1.5 项目可行性分析师 (Feasibility Analyst)     │  🆕 新增
│ 范式: 项目管理 (Project Management)             │
│ 关注: 资源约束验证、冲突检测、优先级排序       │
│ 输出: feasibility_assessment, priority_matrix  │
└────────────────┬───────────────────────────────┘
                 ↓
           其他专家角色
         (V2, V3, V4, V5, V6)
```

**核心特性**:
- ✅ **互补而非替代** - V1关注"为什么"，V1.5关注"能不能"
- ✅ **量化验证** - 提供预算/时间/空间的数值化可行性分析
- ✅ **风险预警** - 提前识别资源约束冲突，避免项目后期风险
- ✅ **决策支持** - 提供多个可行方案及权衡分析

---

## 设计动机

### 发现的问题

在实际使用中，发现了**范式差异**：

| 对比维度 | V1需求分析师（当前） | 用户实际期望 |
|---------|-------------------|------------|
| **设计哲学** | "深刻>全面" - 关注核心矛盾 | "全面>遗漏" - 关注资源可行性 |
| **输出重点** | 人的深层需求、身份认同 | 功能需求、预算分配、时间计划 |
| **冲突定义** | 心理/社会矛盾（"展示vs私密"） | 资源约束冲突（"预算vs需求"） |
| **优先级逻辑** | 层级结构（精神>社会>物质） | 数值化计算（权重×必要性×紧迫性） |
| **目标用户** | 设计师/创意专业人士 | 项目经理/业主/决策者 |

### 典型用户案例

**案例1**: 智能家居系统

**V1输出**（战略洞察）:
```json
{
  "project_task": "为[追求便捷生活的现代家庭]+打造[全屋智能空间]+雇佣空间完成[设备自动化联动]与[语音便捷控制]",
  "design_challenge": "作为[技术拥抱者]的[智能便捷需求]与[预算灵活性]的不确定对立"
}
```

**用户期望**（项目管理）:
```json
{
  "functional_requirements": {
    "core_features": ["全屋设备联动", "语音控制"],
    "control_interfaces": ["语音", "手机APP", "中控屏"]
  },
  "budget_constraints": {
    "type": "弹性预算",
    "estimated_range": "4-7万元"
  }
}
```

**案例2**: 预算冲突

**用户输入**: "20万预算装修200㎡别墅，要求全进口材料+智能家居+私人影院"

**V1输出**:
- 识别深层需求："展示品味的需求"vs"预算有限的现实"
- 但不会明确告知：实际需要40-50万，预算缺口20-30万

**V1.5输出**:
```json
{
  "conflict_detection": {
    "budget_conflicts": [{
      "type": "预算vs功能冲突",
      "severity": "critical",
      "details": {
        "available_budget": 200000,
        "estimated_cost": 450000,
        "gap": 250000,
        "gap_percentage": 125
      },
      "description": "预算20万，但需求成本45万，缺口25万（超预算125%）"
    }]
  },
  "recommendations": [
    {
      "name": "方案A: 保预算方案",
      "adjustments": ["保留智能家居5万", "削减私人影院改为观影区", "材料降级为国产高端"],
      "adjusted_cost": {"total": 200000, "gap_from_budget": 0}
    },
    {
      "name": "方案B: 分期实施",
      "adjustments": ["一期20万完成基础装修+智能家居", "二期15万实现私人影院"],
      "adjusted_cost": {"phase1": 200000, "phase2": 150000}
    }
  ]
}
```

### 为什么是双轨并行？

**为什么不是"替换V1"？**
- ❌ V1的战略洞察是核心竞争力，不应丢弃
- ❌ 项目管理范式无法提供设计洞察

**为什么不是"V1内部增强"？**
- ❌ 角色职责模糊（既要战略又要执行）
- ❌ 提示词会变得过长和复杂
- ❌ 稀释V1的核心价值

**为什么是"双轨并行"？**
- ✅ 清晰的职责分工（V1=洞察，V1.5=验证）
- ✅ 两者互补而非冲突
- ✅ 用户可根据场景选择关注点
- ✅ 符合专家协作模式

---

## 双轨并行范式

### V1: 战略洞察范式

**核心问题**: "用户真正想要什么？"

**分析方法**:
- Jobs-to-be-Done框架："雇佣空间完成什么任务"
- 身份认同分析："想成为的自己" vs "现实中的自己"
- 价值冲突识别："展示" vs "私密"、"效率" vs "体验"

**输出格式** (9个结构化字段):
1. `project_task` - JTBD公式
2. `character_narrative` - 过去→现在→未来转变弧线
3. `design_challenge` - 核心设计矛盾
4. `physical_context` - 物理环境
5. `resource_constraints` - 资源限制
6. `regulatory_requirements` - 规范要求
7. `inspiration_references` - 灵感参考
8. `experience_behavior` - 场景描述
9. `expert_handoff` - 专家协作接口

**典型用户**: 设计师、创意专业人士、追求深度洞察的业主

---

### V1.5: 项目管理范式

**核心问题**: "项目能不能做？怎么做？"

**分析方法**:
- 资源约束验证：预算/时间/空间可行性计算
- 冲突检测：量化评估资源缺口和严重性
- 优先级排序：stakeholder_weight × necessity_level × time_sensitivity

**输出格式** (4个核心字段):
1. `feasibility_assessment` - 总体可行性评估
2. `conflict_detection` - 冲突检测结果（预算/时间/空间）
3. `priority_matrix` - 优先级矩阵（数值化排序）
4. `recommendations` - 决策建议（3-5个方案+权衡）

**典型用户**: 项目经理、业主/决策者、需要可行性验证的场景

---

### 两者关系

```
V1输出 → V1.5输入
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

V1: project_task
"为[追求便捷生活的现代家庭]+打造[全屋智能空间]+雇佣空间完成[设备自动化联动]与[语音便捷控制]"
    ↓ 提取关键词：智能家居、全屋、联动、语音
    ↓
V1.5: 成本估算
- 匹配行业标准：smart_home.core_system → [40000, 70000]
- 典型成本：55000元

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

V1: resource_constraints
"预算: 20万; 工期: 2个月"
    ↓ 解析约束值
    ↓
V1.5: 冲突检测
- 可用预算：200000元
- 估算成本：340000元（智能家居+私人影院+装修）
- 冲突：critical（超预算70%）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

V1: character_narrative
"从传统手动操作到智能语音控制的转变弧线"
    ↓ 推断需求层次
    ↓
V1.5: 优先级计算
- necessity_type: "social"（舒适需求）
- necessity_level: 0.70
- priority_score: 0.40 × 0.70 × 0.75 = 0.21（高优先级）
```

---

## 核心组件

### 1. 行业标准知识库

**文件**: `intelligent_project_analyzer/knowledge_base/industry_standards.yaml`

**结构**:
```yaml
version: "1.0"

# 成本数据库
residential_costs:
  smart_home:
    core_system: {total_cost: [40000, 70000]}
  home_theater:
    standard: {total_cost: [60000, 120000]}

# 冲突阈值
conflict_thresholds:
  budget:
    critical: 1.5  # 总成本是预算的1.5倍以上（超预算50%+）
    high: 1.25
    medium: 1.1
  timeline:
    critical: 2.0
    high: 1.5
  space:
    critical: 1.5
    high: 1.3

# 利益相关者权重
stakeholder_weights:
  residential:
    owner: 0.40
    family_members: 0.30
    guests: 0.15

# 需求层次权重（马斯洛层次）
necessity_levels:
  survival: {weight: 1.0}   # 生存需求
  safety: {weight: 0.85}     # 安全需求
  social: {weight: 0.70}     # 舒适/社交需求
  esteem: {weight: 0.60}     # 尊重需求
  self_actualization: {weight: 0.50}  # 自我实现

# 时间敏感性
time_sensitivity:
  urgent: {weight: 1.0}
  important: {weight: 0.75}
  normal: {weight: 0.50}
  nice_to_have: {weight: 0.30}
```

**扩展性**:
- 支持添加新行业类型（commercial_costs, educational_costs等）
- 支持地域系数调整（不同城市的成本差异）
- 支持年份更新（市场价格波动）

---

### 2. 成本计算器（CostCalculator）

**职责**: 基于行业标准估算需求成本

**核心方法**:
```python
def estimate_cost(self, requirement_text: str) -> Tuple[int, int, int]:
    """
    估算需求成本

    Args:
        requirement_text: V1的project_task或用户描述

    Returns:
        (min_cost, typical_cost, max_cost)
    """
    # 关键词匹配
    if any(kw in requirement_text for kw in ["智能家居", "全屋智能"]):
        smart_costs = self.standards["residential_costs"]["smart_home"]["core_system"]
        cost_range = smart_costs["total_cost"]  # [40000, 70000]
        total_min += cost_range[0]
        total_max += cost_range[1]
        total_typical += (cost_range[0] + cost_range[1]) // 2

    return (total_min, total_typical, total_max)
```

**示例输出**:
```python
# 输入："全屋智能家居系统和私人影院"
# 输出：(100000, 145000, 190000)
#       智能家居[40k,70k] + 私人影院[60k,120k]
```

---

### 3. 冲突检测器（ConflictDetector）

**职责**: 检测预算/时间/空间约束冲突

**核心方法**:

#### 3.1 预算冲突检测

```python
def detect_budget_conflict(
    self,
    available_budget: Optional[int],
    estimated_cost: int
) -> Dict[str, Any]:
    """
    检测预算冲突

    逻辑：
    - cost_ratio = estimated_cost / available_budget
    - critical: cost_ratio ≥ 1.5 (超预算50%+)
    - high: cost_ratio ≥ 1.25 (超预算25-50%)
    - medium: cost_ratio ≥ 1.1 (超预算10-25%)
    """
    if available_budget is None:
        return {
            "type": "预算未明确",
            "severity": "medium",
            "description": "预算未明确，建议确定预算区间"
        }

    cost_ratio = estimated_cost / available_budget

    if cost_ratio >= self.thresholds["budget"]["critical"]:
        severity = "critical"
    elif cost_ratio >= self.thresholds["budget"]["high"]:
        severity = "high"
    # ...

    return {
        "type": "预算vs功能冲突",
        "severity": severity,
        "detected": gap > 0,
        "details": {
            "available_budget": available_budget,
            "estimated_cost": estimated_cost,
            "gap": gap,
            "gap_percentage": int((cost_ratio - 1) * 100)
        }
    }
```

#### 3.2 时间冲突检测

```python
def detect_timeline_conflict(
    self,
    available_days: Optional[int],
    required_days: int
) -> Dict[str, Any]:
    """
    检测工期冲突

    逻辑：
    - time_ratio = required_days / available_days
    - critical: time_ratio ≥ 2.0 (所需时间超2倍)
    - high: time_ratio ≥ 1.5
    """
    time_ratio = required_days / available_days

    if time_ratio >= self.thresholds["timeline"]["critical"]:
        severity = "critical"
    # ...
```

#### 3.3 空间冲突检测

```python
def detect_space_conflict(
    self,
    available_area: Optional[int],
    required_area: int
) -> Dict[str, Any]:
    """
    检测空间冲突

    示例：
    - 60㎡小户型要4房2厅4独立卫生间
    - required_area = 4×10 + 2×15 + 4×4 = 86㎡
    - area_ratio = 86/60 = 1.43 → "high"冲突
    """
    area_ratio = required_area / available_area

    if area_ratio >= self.thresholds["space"]["critical"]:
        severity = "critical"
    # ...
```

---

### 4. 优先级引擎（PriorityEngine）

**职责**: 计算需求优先级分数

**核心公式**:
```
priority_score = stakeholder_weight × necessity_level × time_sensitivity
```

**维度说明**:

| 维度 | 取值范围 | 说明 |
|-----|---------|------|
| **stakeholder_weight** | 0-1 | 业主0.4, 家庭成员0.3, 访客0.15, 投资0.15 |
| **necessity_level** | 0-1 | 生存1.0, 安全0.85, 社交0.7, 尊重0.6, 自我实现0.5 |
| **time_sensitivity** | 0-1 | urgent 1.0, important 0.75, normal 0.5, nice_to_have 0.3 |

**核心方法**:

```python
def calculate_priority(
    self,
    requirement: str,
    stakeholder_type: str = "owner",
    necessity_type: str = "social",
    sensitivity_type: str = "important"
) -> Tuple[float, Dict[str, float]]:
    """
    计算优先级分数

    Returns:
        (priority_score, breakdown)
    """
    stakeholder_weight = self.stakeholder_weights.get(stakeholder_type, 0.40)
    necessity_level = self.necessity_levels.get(necessity_type, {}).get("weight", 0.60)
    time_weight = self.time_sensitivity.get(sensitivity_type, {}).get("weight", 0.75)

    priority_score = stakeholder_weight * necessity_level * time_weight

    breakdown = {
        "stakeholder_weight": stakeholder_weight,
        "necessity_level": necessity_level,
        "time_sensitivity": time_weight
    }

    return (priority_score, breakdown)

def infer_necessity_type(self, requirement_text: str) -> str:
    """推断需求层次类型"""
    if any(kw in requirement_text for kw in ["消防", "防盗", "隐私", "安全"]):
        return "safety"
    elif any(kw in requirement_text for kw in ["智能", "舒适", "便捷"]):
        return "social"
    elif any(kw in requirement_text for kw in ["品牌", "进口", "奢华", "高端"]):
        return "esteem"
    elif any(kw in requirement_text for kw in ["定制", "艺术", "收藏", "影院"]):
        return "self_actualization"
    else:
        return "social"  # 默认社交需求
```

**示例计算**:

```python
# 智能家居系统
priority_score = 0.40 × 0.70 × 0.75 = 0.21（高优先级）
# - 业主需求（0.40）
# - 舒适需求（0.70）
# - 重要但不紧急（0.75）

# 私人影院
priority_score = 0.40 × 0.50 × 0.50 = 0.10（低优先级）
# - 业主需求（0.40）
# - 自我实现需求（0.50）
# - 一般需求（0.50）
```

---

## 数据流

### 完整流程

```
1. 用户输入
   ↓
2. V1需求分析师
   输出: structured_requirements (9个字段)
   ↓
3. V1.5可行性分析师

   阶段1: 需求拆解与成本估算
   ├─ 提取V1的project_task
   ├─ 关键词匹配（智能家居/私人影院/...）
   ├─ 查询industry_standards.yaml
   └─ 输出: requirements_breakdown + total_estimated_cost

   阶段2: 冲突检测
   ├─ 提取V1的resource_constraints
   ├─ 解析预算/工期/面积
   ├─ 调用ConflictDetector
   └─ 输出: budget_conflicts + timeline_conflicts + space_conflicts

   阶段3: 优先级计算
   ├─ 遍历每个需求
   ├─ 推断necessity_type（基于关键词）
   ├─ 调用PriorityEngine.calculate_priority()
   └─ 输出: priority_matrix（按score降序排列）

   阶段4: 决策建议生成
   ├─ 基于冲突严重性
   ├─ 基于优先级排序
   ├─ 设计3-5个方案（保预算/保品质/分期/降级）
   └─ 输出: recommendations + risk_flags

   ↓
4. 输出JSON结果
   {
     "feasibility_assessment": {...},
     "conflict_detection": {...},
     "priority_matrix": [...],
     "recommendations": [...]
   }
```

### 输入输出示例

**输入**（V1的输出）:
```json
{
  "project_task": "为[追求品质生活的三口之家]+打造[200㎡智能别墅]+雇佣空间完成[全屋智能联动]与[影音娱乐享受]",
  "resource_constraints": "预算: 20万; 工期: 2个月",
  "physical_context": "独栋别墅，200㎡，3层"
}
```

**输出**（V1.5的输出）:
```json
{
  "feasibility_assessment": {
    "overall_feasibility": "low",
    "critical_issues": [
      "预算缺口12-17万（超预算60-85%）",
      "工期紧张（标准工期需3-3.5个月）"
    ],
    "summary": "项目需求明确但资源约束严重。建议采用分期实施方案。"
  },

  "conflict_detection": {
    "budget_conflicts": [{
      "type": "预算vs功能冲突",
      "severity": "critical",
      "detected": true,
      "details": {
        "available_budget": 200000,
        "estimated_cost_typical": 370000,
        "gap_typical": 170000,
        "gap_percentage": 85
      },
      "description": "预算20万，但全屋智能（6万）+私人影院（9万）+200㎡装修（40万）典型总成本37万，缺口17万"
    }],

    "timeline_conflicts": [{
      "type": "时间vs质量冲突",
      "severity": "medium",
      "detected": true,
      "details": {
        "available_days": 60,
        "required_days_standard": 90,
        "gap": 30
      },
      "description": "2个月（60天）完成200㎡装修，标准工期需90天，存在30天缺口"
    }]
  },

  "priority_matrix": [
    {
      "requirement": "全屋智能家居系统",
      "priority_score": 0.216,
      "breakdown": {
        "stakeholder_weight": 0.40,
        "necessity_level": 0.60,
        "time_sensitivity": 0.90
      },
      "rank": 1,
      "estimated_cost": 60000,
      "rationale": "三口之家核心需求（业主+家庭成员），属于舒适需求，工期紧张"
    },
    {
      "requirement": "私人影院",
      "priority_score": 0.080,
      "breakdown": {
        "stakeholder_weight": 0.40,
        "necessity_level": 0.40,
        "time_sensitivity": 0.50
      },
      "rank": 2,
      "estimated_cost": 90000,
      "rationale": "业主个人需求，属于自我实现需求，时间敏感性一般"
    }
  ],

  "recommendations": [
    {
      "name": "方案A: 分期实施（推荐）",
      "strategy": "一期满足核心需求，二期扩展",
      "adjustments": [
        "一期（20万）: 基础装修（1000元/㎡×200㎡=20万，标准档次）",
        "一期（预留接口）: 为智能家居和影院预留强弱电接口",
        "二期（15万）: 全屋智能（6万）+ 标准影院（9万）"
      ],
      "adjusted_cost": {
        "phase1": 200000,
        "phase2": 150000,
        "total": 350000,
        "gap_from_budget_phase1": 0
      },
      "trade_offs": {
        "pros": ["一期预算达标", "分散资金压力", "可先入住体验后优化"],
        "cons": ["二期施工影响居住", "二期总成本可能增加10-15%"]
      },
      "recommended": true
    }
  ],

  "risk_flags": [
    {
      "type": "预算风险",
      "severity": "critical",
      "description": "当前预算与需求成本差距达17万（85%），属于严重资源不匹配",
      "mitigation": "建议选择方案A（分期）或方案B（削减），避免超预算导致项目烂尾"
    }
  ]
}
```

---

## 与V1的关系

### 互补关系表

| 维度 | V1需求分析师 | V1.5可行性分析师 |
|-----|-------------|----------------|
| **关注焦点** | 为什么（why） | 能不能（can/feasible） |
| **分析深度** | 深度洞察（核心矛盾） | 广度覆盖（全面验证） |
| **输出性质** | 定性分析（描述性） | 定量分析（数值化） |
| **决策支持** | 战略方向（做什么） | 执行方案（怎么做） |
| **风险识别** | 价值风险（设计不对） | 资源风险（做不到） |
| **用户价值** | 启发思考、提供洞察 | 验证可行性、辅助决策 |

### 协作模式

```python
def analyze_with_dual_track(user_input: str) -> Dict:
    """双轨并行分析"""

    # Track 1: V1战略洞察
    v1_output = requirements_analyst.analyze(user_input)
    # 输出：project_task, design_challenge, character_narrative, ...

    # Track 2: V1.5可行性验证
    v15_output = feasibility_analyst.analyze(v1_output)
    # 输出：feasibility_assessment, conflict_detection, priority_matrix, ...

    # 整合输出
    return {
        "strategic_insight": v1_output,     # 战略洞察
        "feasibility_check": v15_output,    # 可行性验证
        "integration_notes": {
            "conflicts_alignment": "V1识别的价值冲突与V1.5识别的资源冲突存在映射关系",
            "priority_consistency": "V1的层级结构与V1.5的数值化优先级基本一致"
        }
    }
```

### 何时使用哪个？

**仅使用V1** (战略洞察模式):
- ✅ 项目初期，头脑风暴阶段
- ✅ 用户需要设计灵感和深度洞察
- ✅ 预算/工期尚未确定
- ✅ 目标用户是设计师/创意人员

**V1 + V1.5** (双轨并行模式):
- ✅ 项目规划阶段，需要可行性验证
- ✅ 预算/工期已有初步约束
- ✅ 需要决策支持（保预算还是保品质？）
- ✅ 目标用户是业主/项目经理/决策者

**示例对话**:

```
用户: "我想装修一个200㎡的别墅，预算20万，要智能家居和私人影院"

系统:
【V1战略洞察】
你的需求本质是"为追求品质生活的家庭打造智能娱乐空间"。
核心设计挑战：作为[科技爱好者]的[智能便捷需求]与[影音享受需求]之间，
存在预算约束下的功能优先级选择。

【V1.5可行性验证】
⚠️ 预算冲突（critical）：
- 可用预算：20万
- 估算成本：37万（智能家居6万+影院9万+装修22万）
- 缺口：17万（85%）

💡 建议方案：
方案A（推荐）: 分期实施
- 一期20万：完成基础装修+智能家居（核心功能）
- 二期15万：实现私人影院（提升功能）
- 优势：预算达标，风险可控
```

---

## 技术实现

### 文件结构

```
intelligent_project_analyzer/
├── agents/
│   ├── requirements_analyst.py        # V1需求分析师
│   └── feasibility_analyst.py         # V1.5可行性分析师 🆕
│
├── config/
│   └── prompts/
│       ├── requirements_analyst_lite.yaml   # V1配置
│       └── feasibility_analyst.yaml         # V1.5配置 🆕
│
├── knowledge_base/
│   └── industry_standards.yaml        # 行业标准知识库 🆕
│
└── core/
    ├── state.py                       # 状态管理
    └── types.py                       # 类型定义

tests/
└── test_feasibility_analyst.py        # V1.5测试套件 🆕
```

### 核心类设计

```python
# feasibility_analyst.py

class FeasibilityAnalystAgent(LLMAgent):
    """V1.5 项目可行性分析师智能体"""

    def __init__(self, llm_model, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            agent_type=AgentType.REQUIREMENTS_ANALYST,
            name="项目可行性分析师",
            description="验证资源约束、检测冲突、计算优先级，提供可行性分析",
            llm_model=llm_model,
            config=config
        )

        # 初始化提示词管理器
        self.prompt_manager = PromptManager()

        # 加载行业标准知识库
        self.industry_standards = self._load_industry_standards()

        # 初始化子引擎
        self.cost_calculator = CostCalculator(self.industry_standards)
        self.conflict_detector = ConflictDetector(self.industry_standards)
        self.priority_engine = PriorityEngine(self.industry_standards)

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        prompt_config = self.prompt_manager.get_prompt("feasibility_analyst", return_full_config=True)
        return prompt_config.get("system_prompt", "")

    def get_task_description(self, state: ProjectAnalysisState) -> str:
        """获取具体任务描述"""
        structured_requirements = state.get("structured_requirements", {})

        task_description = f"""
# V1.5 可行性分析任务

## 输入：V1需求分析师的输出

```json
{json.dumps(structured_requirements, ensure_ascii=False, indent=2)}
```

## 你的任务

基于V1的输出，执行以下4个阶段的分析：

1. **需求拆解与成本估算** - 识别关键词，匹配行业标准，计算总成本
2. **冲突检测** - 检查预算/时间/空间可行性，识别缺口
3. **优先级计算** - 为每个需求计算priority_score
4. **决策建议生成** - 生成3-5个可行方案（保预算/保品质/分期/降级）
"""
        return task_description


class CostCalculator:
    """成本计算器 - 基于行业标准估算需求成本"""

    def __init__(self, industry_standards: Dict[str, Any]):
        self.standards = industry_standards

    def estimate_cost(self, requirement_text: str) -> Tuple[int, int, int]:
        """估算需求成本，返回: (min_cost, typical_cost, max_cost)"""
        # 实现详见"核心组件 > 成本计算器"章节


class ConflictDetector:
    """冲突检测器 - 检测资源约束冲突"""

    def __init__(self, industry_standards: Dict[str, Any]):
        self.standards = industry_standards
        self.thresholds = industry_standards.get("conflict_thresholds", {})

    def detect_budget_conflict(self, available_budget: Optional[int], estimated_cost: int):
        """检测预算冲突"""
        # 实现详见"核心组件 > 冲突检测器"章节

    def detect_timeline_conflict(self, available_days: Optional[int], required_days: int):
        """检测工期冲突"""

    def detect_space_conflict(self, available_area: Optional[int], required_area: int):
        """检测空间冲突"""


class PriorityEngine:
    """优先级计算引擎 - 计算需求优先级分数"""

    def __init__(self, industry_standards: Dict[str, Any]):
        self.standards = industry_standards
        self.stakeholder_weights = industry_standards.get("stakeholder_weights", {}).get("residential", {})
        self.necessity_levels = industry_standards.get("necessity_levels", {})
        self.time_sensitivity = industry_standards.get("time_sensitivity", {})

    def calculate_priority(
        self,
        requirement: str,
        stakeholder_type: str = "owner",
        necessity_type: str = "social",
        sensitivity_type: str = "important"
    ) -> Tuple[float, Dict[str, float]]:
        """计算优先级分数"""
        # 实现详见"核心组件 > 优先级引擎"章节

    def infer_necessity_type(self, requirement_text: str) -> str:
        """推断需求层次类型"""
```

---

## 扩展性

### 1. 添加新行业类型

在`industry_standards.yaml`中添加新配置：

```yaml
# 新增：商业空间成本标准
commercial_costs:
  retail_store:
    basic_decoration: {total_cost_per_sqm: [800, 1500]}
    mid_level: {total_cost_per_sqm: [1500, 3000]}
    high_end: {total_cost_per_sqm: [3000, 6000]}

  restaurant:
    fast_food: {total_cost_per_sqm: [2000, 4000]}
    casual_dining: {total_cost_per_sqm: [4000, 8000]}
    fine_dining: {total_cost_per_sqm: [8000, 15000]}

# 新增：商业空间利益相关者权重
stakeholder_weights:
  commercial:
    owner: 0.50      # 业主权重更高
    customers: 0.30  # 顾客体验
    employees: 0.15  # 员工需求
    branding: 0.05   # 品牌形象
```

### 2. 添加地域系数

```yaml
# 新增：地域成本系数
regional_multipliers:
  tier1_cities:  # 一线城市
    beijing: 1.3
    shanghai: 1.35
    shenzhen: 1.25
  tier2_cities:  # 二线城市
    hangzhou: 1.15
    chengdu: 1.10
  tier3_cities:  # 三线城市
    default: 0.85

# 使用方式
def estimate_cost_with_region(self, requirement_text: str, city: str):
    base_cost = self.estimate_cost(requirement_text)
    multiplier = self.standards["regional_multipliers"]["tier1_cities"].get(city, 1.0)
    return base_cost * multiplier
```

### 3. 添加新冲突类型

```python
class ConflictDetector:
    # 新增：技术可行性冲突检测
    def detect_technical_conflict(
        self,
        requirement_text: str,
        physical_context: Dict
    ) -> Dict[str, Any]:
        """
        检测技术可行性冲突

        示例：
        - 老旧建筑安装中央空调（承重不足）
        - 低层高空间实现挑高设计（物理限制）
        """
        conflicts = []

        # 检测承重限制
        if "中央空调" in requirement_text:
            if physical_context.get("building_age", 0) > 30:
                conflicts.append({
                    "type": "承重vs设备冲突",
                    "severity": "high",
                    "description": "老建筑（30年+）承重可能不足，需结构工程师评估"
                })

        return {"technical_conflicts": conflicts}
```

### 4. 自定义优先级算法

```python
class CustomPriorityEngine(PriorityEngine):
    """自定义优先级引擎 - 支持不同计算策略"""

    def __init__(self, industry_standards, strategy="weighted"):
        super().__init__(industry_standards)
        self.strategy = strategy

    def calculate_priority(self, requirement, **kwargs):
        if self.strategy == "weighted":
            # 加权策略（当前默认）
            return super().calculate_priority(requirement, **kwargs)

        elif self.strategy == "ahp":
            # 层次分析法（AHP）
            return self._calculate_priority_ahp(requirement, **kwargs)

        elif self.strategy == "fuzzy":
            # 模糊综合评价法
            return self._calculate_priority_fuzzy(requirement, **kwargs)

    def _calculate_priority_ahp(self, requirement, **kwargs):
        """层次分析法（适用于多目标决策）"""
        # TODO: 实现AHP算法
        pass
```

---

## 总结

V1.5项目可行性分析师的核心价值：

✅ **互补增强**: 保留V1战略洞察，新增可行性验证
✅ **量化决策**: 提供数值化的冲突检测和优先级排序
✅ **风险预警**: 提前识别预算/时间/空间约束问题
✅ **方案对比**: 生成多个可行方案及权衡分析
✅ **可扩展性**: 支持新行业、新地域、新冲突类型

**适用场景**: 项目规划阶段、资源约束明确时、需要决策支持的场景。

**不适用场景**: 纯创意头脑风暴、预算/工期完全未定、仅需设计灵感的场景（此时仅用V1即可）。

---

**版本历史**:
- v1.0 (2025-12-06): 初始版本，实现双轨并行架构

**参考文档**:
- `V15_USER_GUIDE.md` - V1.5用户使用指南
- `intelligent_project_analyzer/config/prompts/feasibility_analyst.yaml` - V1.5配置文件
- `intelligent_project_analyzer/knowledge_base/industry_standards.yaml` - 行业标准知识库
