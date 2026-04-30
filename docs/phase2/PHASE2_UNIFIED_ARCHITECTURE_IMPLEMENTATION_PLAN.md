# Phase 2: 统一所有角色输出架构实施方案
# Phase 2: Unified Role Output Architecture Implementation Plan

**日期**: 2025-12-05
**版本**: v6.4 → v6.5-全角色灵活输出
**状态**: 🔄 Phase 2 进行中

---

## 一、现状分析 (Current State Analysis)

### 1.1 输出架构现状

| 角色类别 | 子角色数量 | 当前架构 | 状态 |
|---------|-----------|---------|------|
| V2 设计总监 | 7个子角色 | v3.6轻量级模式 (`full_analysis` / `focused_task`) | 🟡 需统一命名 |
| V3 叙事专家 | 3个子角色 | 固定字段 + `custom_analysis` | 🔴 需完全重构 |
| V4 设计研究者 | 2个子角色 | 固定字段 + `custom_analysis` | 🔴 需完全重构 |
| V5 场景专家 | 7个子角色 | 固定字段 + "优先级调整"逻辑 | 🔴 需完全重构 |
| V6 总工程师 | 4个子角色 | V6-1已完成双模式，其余3个固定字段 | 🟢 V6-1已完成 |

**总计**: 23个子角色，其中1个已完成，22个待修正

### 1.2 问题诊断

**核心问题**:
1. **架构不统一**: V2使用`full_analysis/focused_task`，V6-1使用`targeted/comprehensive`
2. **命名不一致**: V2的`focused_task_response`vs V6的`targeted_analysis`
3. **验证逻辑缺失**: V3/V4/V5没有自动化验证机制
4. **文档不完整**: 缺少模式判断协议和结构模板指南

---

## 二、统一架构标准 (Unified Architecture Standard)

### 2.1 核心设计原则

**命名约定** (基于V6-1的成功经验):
- ✅ `output_mode`: `"targeted"` | `"comprehensive"`
- ✅ `targeted_analysis`: 针对性问答的灵活内容区
- ✅ `user_question_focus`: 问题核心聚焦点(≤15字)

**为什么不保留V2的命名?**
- `focused_task`语义不如`targeted`清晰
- `full_analysis`不如`comprehensive`专业
- 新架构已在V6-1验证成功，应作为统一标准

### 2.2 通用Pydantic模板结构

```python
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, model_validator

class V{X}_{N}_FlexibleOutput(BaseModel):
    """[角色名称] - 灵活输出模型"""

    # ===== 第一层：元数据（必需） =====
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str  # ≤15字
    confidence: float  # 0.0-1.0
    design_rationale: str  # v3.5必填

    # ===== 第二层：标准字段（Comprehensive模式必需，Targeted模式可选） =====
    # [根据角色特定需求定义，全部Optional]
    field_1: Optional[...] = None
    field_2: Optional[...] = None
    # ...

    # ===== 第三层：灵活内容区（Targeted模式核心输出） =====
    targeted_analysis: Optional[Dict[str, Any]] = None

    # ===== v3.5协议字段 =====
    expert_handoff_response: Optional[Dict[str, Any]] = None
    challenge_flags: Optional[List[Dict[str, str]]] = None

    @model_validator(mode='after')
    def validate_output_consistency(self):
        """验证输出一致性"""
        mode = self.output_mode

        if mode == 'comprehensive':
            # 检查标准字段
            required_fields = [...]  # 根据角色定义
            missing = [f for f in required_fields if not getattr(self, f)]
            if missing:
                raise ValueError(f"⚠️ Comprehensive模式下必需字段缺失: {missing}")

        elif mode == 'targeted':
            # 检查targeted_analysis
            if not self.targeted_analysis:
                raise ValueError("⚠️ Targeted模式下必须填充targeted_analysis字段")

        return self
```

### 2.3 通用System Prompt模板

**必需章节**:
1. **🆕 输出模式判断协议** (与V6-1完全一致)
2. **输出定义** (灵活输出结构蓝图)
3. **Targeted Analysis结构指南** (根据角色定制4-6种模板)
4. **高质量范例** (Targeted + Comprehensive各1个)
5. **工作流程** (Step 0: 输出模式判断)

---

## 三、分角色实施策略 (Role-by-Role Strategy)

### 3.1 V2 设计总监 (7个子角色)

**现状**: 已有v3.6轻量级模式，但命名不统一

**实施策略**: **轻度改造**
- 将`output_mode`的值从`full_analysis/focused_task`改为`targeted/comprehensive`
- 将`focused_task_response`重命名为`targeted_analysis`
- 添加`@model_validator`验证逻辑
- 更新System Prompt的模式判断协议

**工作量估算**: 4-6小时 (每个角色30-50分钟)

**子角色清单**:
- 2-0: 项目设计总监
- 2-1: 住宅设计总监
- 2-2: 商业设计总监
- 2-3: 办公设计总监
- 2-4: 酒店设计总监
- 2-5: 文化教育设计总监
- 2-6: 建筑及景观设计总监

### 3.2 V3 叙事专家 (3个子角色)

**现状**: 固定字段，无灵活性机制

**实施策略**: **中度改造**
- 创建新的`V3_{N}_FlexibleOutput` Pydantic模型
- 将所有标准字段改为Optional
- 添加`targeted_analysis`字段
- 编写完整的System Prompt（包含模式判断协议）

**工作量估算**: 3-4小时 (每个角色1-1.5小时)

**子角色清单**:
- 3-1: 人物角色叙事专家 (Character Archetype Narrative Expert)
- 3-2: 品牌叙事专家 (Brand Narrative Expert)
- 3-3: 情感体验叙事专家 (Emotional Experience Narrative Expert)

**Targeted Analysis典型结构**:
1. **品牌定位类** (`positioning_matrix`, `brand_essence`, `communication_strategy`)
2. **故事构建类** (`narrative_arc`, `key_moments`, `storytelling_framework`)
3. **情感设计类** (`emotion_map`, `touchpoint_analysis`, `experience_peaks`)

### 3.3 V4 设计研究者 (2个子角色)

**现状**: 固定字段，无灵活性机制

**实施策略**: **中度改造**
- 创建`V4_{N}_FlexibleOutput`模型
- 针对研究类任务定制targeted_analysis结构模板

**工作量估算**: 2-3小时 (每个角色1-1.5小时)

**子角色清单**:
- 4-1: 案例对标策略师 (Precedent Research & Benchmarking Strategist)
- 4-2: 方法论架构师 (Methodology Architect)

**Targeted Analysis典型结构**:
1. **案例分析类** (`precedent_matrix`, `best_practices`, `differentiation_strategy`)
2. **方法论类** (`methodology_framework`, `process_steps`, `decision_criteria`)
3. **竞品研究类** (`competitor_analysis`, `market_positioning`, `opportunity_gaps`)

### 3.4 V5 场景专家 (7个子角色)

**现状**: 使用"优先级调整"逻辑，通过custom_analysis处理针对性问题

**实施策略**: **中度改造**
- 创建`V5_{N}_FlexibleOutput`模型
- 删除"优先级调整"步骤，替换为"输出模式判断"
- 为每个行业专家定制targeted_analysis结构模板

**工作量估算**: 7-9小时 (每个角色1-1.5小时)

**子角色清单**:
- 5-0: 通用场景策略师
- 5-1: 居住场景与生活方式专家
- 5-2: 商业零售运营专家
- 5-3: 企业办公策略专家
- 5-4: 酒店餐饮运营专家
- 5-5: 文化教育场景专家
- 5-6: 医疗康养场景专家

**Targeted Analysis典型结构**:
1. **运营优化类** (`operational_diagnosis`, `optimization_proposals`, `implementation_roadmap`)
2. **空间策略类** (`space_allocation`, `layout_principles`, `flow_optimization`)
3. **KPI设计类** (`metric_definition`, `target_setting`, `measurement_framework`)
4. **体验设计类** (`journey_optimization`, `touchpoint_enhancement`, `service_blueprint`)

### 3.5 V6 总工程师 (剩余3个子角色)

**现状**: V6-1已完成，V6-2/V6-3/V6-4待修正

**实施策略**: **简单复制**
- 直接复制V6-1的架构到其他3个子角色
- 仅调整角色特定的标准字段和targeted_analysis模板

**工作量估算**: 2-3小时 (每个角色40-60分钟)

**子角色清单**:
- 6-1: 结构与幕墙工程师 ✅ (已完成)
- 6-2: 机电与智能化工程师
- 6-3: 室内工艺与材料专家
- 6-4: 成本与价值工程师

---

## 四、实施优先级与时间线 (Priority & Timeline)

### Phase 2.1: 高优先级角色 (Week 1)

**目标**: 完成80%高频使用的角色

| 优先级 | 角色 | 原因 | 预计时间 |
|-------|------|------|---------|
| 🔥 P0 | V6-2, V6-3, V6-4 | 与V6-1同类，复制最快 | 2-3小时 |
| 🔥 P1 | V5-1, V5-2 | 高频使用（居住/商业） | 2-3小时 |
| 🔥 P2 | V2-1, V2-2 | 高频使用（住宅/商业设计） | 1-2小时 |

**小计**: 5-8小时

### Phase 2.2: 中优先级角色 (Week 2)

**目标**: 完成剩余的核心角色

| 优先级 | 角色 | 原因 | 预计时间 |
|-------|------|------|---------|
| ⚡ P3 | V3-2 (品牌叙事) | 品牌项目常用 | 1-1.5小时 |
| ⚡ P4 | V4-1 (案例对标) | 研究阶段必用 | 1-1.5小时 |
| ⚡ P5 | V2-0 (项目总监) | 综合体项目 | 1小时 |
| ⚡ P6 | V5-3, V5-4 | 办公/餐饮项目 | 2-3小时 |

**小计**: 5.5-8小时

### Phase 2.3: 低优先级角色 (Week 3)

**目标**: 完成所有剩余角色

| 优先级 | 角色 | 原因 | 预计时间 |
|-------|------|------|---------|
| ⏳ P7 | V3-1, V3-3 | 较少单独使用 | 2-3小时 |
| ⏳ P8 | V4-2 (方法论) | 特定场景使用 | 1-1.5小时 |
| ⏳ P9 | V2-3, V2-4, V2-5, V2-6 | 特定业态项目 | 2-3小时 |
| ⏳ P10 | V5-0, V5-5, V5-6 | 特定行业项目 | 3-4小时 |

**小计**: 8.5-11.5小时

### 总计时间估算

- **最佳情况**: 19小时 (2.5个工作日)
- **预期情况**: 27.5小时 (3.5个工作日)
- **最坏情况**: 37小时 (5个工作日)

---

## 五、批量实施工具与自动化 (Automation Tools)

### 5.1 代码生成脚本

由于手工修改22个角色容易出错且耗时，建议创建自动化工具：

```python
# generate_flexible_output_models.py
"""
自动生成FlexibleOutput模型的脚本

用法:
python generate_flexible_output_models.py --role V2_1 --fields "field1,field2,field3"
"""

import argparse
from pathlib import Path

TEMPLATE = '''
class V{role_id}_FlexibleOutput(BaseModel):
    """[角色名称] - 灵活输出模型"""

    # ===== 第一层：元数据（必需） =====
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    design_rationale: str

    # ===== 第二层：标准字段 =====
{standard_fields}

    # ===== 第三层：灵活内容区 =====
    targeted_analysis: Optional[Dict[str, Any]] = None

    # ===== v3.5协议字段 =====
    expert_handoff_response: Optional[Dict[str, Any]] = None
    challenge_flags: Optional[List[Dict[str, str]]] = None

    @model_validator(mode='after')
    def validate_output_consistency(self):
        if self.output_mode == 'comprehensive':
            required_fields = {required_fields_list}
            missing = [f for f in required_fields if not getattr(self, f)]
            if missing:
                raise ValueError(f"⚠️ Comprehensive模式下必需字段缺失: {{missing}}")
        elif self.output_mode == 'targeted':
            if not self.targeted_analysis:
                raise ValueError("⚠️ Targeted模式下必须填充targeted_analysis字段")
        return self
'''

def generate_model(role_id: str, fields: list[str]) -> str:
    """生成Pydantic模型代码"""
    standard_fields = "\\n".join([
        f"    {field}: Optional[...] = None"
        for field in fields
    ])
    required_fields_list = f"[{', '.join(repr(f) for f in fields)}]"

    return TEMPLATE.format(
        role_id=role_id,
        standard_fields=standard_fields,
        required_fields_list=required_fields_list
    )
```

### 5.2 System Prompt模板引擎

创建Jinja2模板，批量生成System Prompt:

```jinja2
{# system_prompt_template.j2 #}
### **🆕 输出模式判断协议 (Output Mode Selection Protocol)**

⚠️ **CRITICAL**: 在开始分析之前，你必须首先判断用户问题的类型，选择正确的输出模式。

#### **判断依据**

**针对性问答模式 (Targeted Mode)** - 满足以下任一条件：
- 用户问题聚焦于**单一维度**的深度分析
  {% for example in targeted_examples %}
  - 示例：{{ example }}
  {% endfor %}
- 用户明确使用**"如何"、"哪些"、"什么"、"为什么"**等疑问词
- 用户要求**"针对性建议"、"专项分析"、"具体方案"**

**完整报告模式 (Comprehensive Mode)** - 满足以下任一条件：
- 用户要求**"完整的XX分析"、"系统性评估"、"全面分析"**
- 用户未指定具体问题，而是提供**项目背景**并期待全面分析
- 任务描述包含**"制定策略"、"进行设计"、"构建方案"**等宏观词汇

{# ... 更多模板内容 ... #}
```

### 5.3 测试用例生成器

批量生成pytest测试用例:

```python
# generate_test_cases.py
"""
为每个角色生成标准测试用例

生成的测试包括:
- Targeted模式验证 (至少3种问题类型)
- Comprehensive模式验证
- Schema验证
- 模式一致性验证
"""
```

---

## 六、质量保证策略 (Quality Assurance)

### 6.1 自动化验证

**Pydantic模型验证**:
```bash
# 验证所有模型可正常导入
python -c "from intelligent_project_analyzer.models.flexible_output import *"

# 运行所有测试
pytest tests/test_flexible_output_*.py -v
```

**YAML语法验证**:
```bash
# 检查所有YAML文件语法正确
python -c "import yaml; yaml.safe_load(open('intelligent_project_analyzer/config/roles/v2_design_director.yaml'))"
```

### 6.2 人工审查清单

每个角色完成后必须通过以下检查:

- [ ] Pydantic模型定义正确，validator逻辑有效
- [ ] System Prompt包含所有必需章节
- [ ] 提供至少4种targeted_analysis结构模板
- [ ] 提供Targeted和Comprehensive各1个高质量范例
- [ ] 工作流程包含Step 0: 输出模式判断
- [ ] 测试用例覆盖率≥80%
- [ ] 所有测试通过

### 6.3 回归测试

确保旧功能不受影响:

```python
# tests/test_backward_compatibility.py
"""
测试向后兼容性

确保:
1. 旧代码仍能解析新输出（通过custom_analysis降级）
2. Comprehensive模式输出与旧架构完全一致
3. 现有workflow不受影响
"""
```

---

## 七、风险管理 (Risk Management)

### 风险1: 时间估算不准确 ⚠️中

**描述**: 22个角色的改造可能比预期更耗时

**缓解策略**:
1. 先完成P0-P2高优先级角色（覆盖80%使用场景）
2. 使用自动化工具减少重复劳动
3. 并行开发：一人负责Pydantic模型，一人负责System Prompt

### 风险2: 质量下降 ⚠️高

**描述**: 批量改造可能导致质量参差不齐

**缓解策略**:
1. 使用代码生成确保结构一致性
2. 建立人工审查清单
3. 要求每个角色通过完整测试套件
4. Code Review机制

### 风险3: LLM不遵守新协议 ⚠️中

**描述**: 修改后LLM可能不正确选择输出模式

**缓解策略**:
1. 在System Prompt中强化判断标准
2. 提供丰富的正反例
3. 建立监控系统追踪模式选择准确率
4. 准备后处理脚本强制清理冗余字段

---

## 八、成功标准 (Success Criteria)

### 技术指标

- ✅ 22个角色全部完成灵活输出改造
- ✅ 所有Pydantic模型通过验证
- ✅ 所有System Prompt包含必需章节
- ✅ 测试覆盖率≥80%，通过率100%

### 一致性指标

- ✅ 所有角色使用统一命名 (`targeted` / `comprehensive`)
- ✅ 所有角色使用相同的validator逻辑
- ✅ 所有角色提供targeted_analysis结构模板

### 性能指标

- ✅ Targeted模式Token消耗降低50-60%
- ✅ 响应时间降低40-50%
- ✅ 用户满意度提升

---

## 九、下一步行动 (Next Actions)

### 立即执行 (今天)

1. ✅ 创建Phase 2实施策略文档 (本文档)
2. 🔄 开始P0优先级：完成V6-2, V6-3, V6-4
3. 🔄 创建代码生成工具（可选，如时间充裕）

### 本周执行

1. 完成P1-P2优先级角色 (V5-1, V5-2, V2-1, V2-2)
2. 编写端到端测试用例
3. 进行Code Review和质量检查

### 下周执行

1. 完成P3-P10所有剩余角色
2. 全面回归测试
3. 更新文档和使用指南
4. 准备Phase 3（前端适配）

---

**文档版本**: v1.0
**最后更新**: 2025-12-05
**负责人**: Phase 2 Implementation Team
**预计完成**: 2025-12-12
