# 方案C实施快速检查清单

## ✅ 已完成（Phase 1 - 核心价值）

### 1. V7配置升级 - 社会关系+心理洞察专家 ✅
- **文件**: `intelligent_project_analyzer/config/roles/v7_emotional_insight_expert.yaml`
- **状态**: ✅ 部分完成
  - ✅ 版本号升级：v1.0 → v2.0
  - ✅ 名称升级：情感洞察专家 → 社会关系与心理洞察专家
  - ✅ core_expertise扩展：新增6个社会关系建模能力
  - ✅ 工具使用指南更新：增加社会学研究、多代同堂案例搜索
  - ✅ 身份与核心定位：明确双能力体系
  - 🔄 **待完成**: system_prompt的理论框架部分需完整重写（Part A社会关系 + Part B心理洞察）
  - 🔄 **待完成**: 输出字段扩展（增加social_structure_analysis）

### 2. Batch Scheduler正式化 ✅
- **文件**: `intelligent_project_analyzer/workflow/batch_scheduler.py`
- **状态**: ✅ 完全完成
- **修改内容**:
  ```python
  self.base_dependencies = {
      "V4": [],
      "V5": ["V4"],
      "V3": ["V4", "V5"],
      "V7": ["V3", "V5"],          # 🆕 新增
      "V2": ["V3", "V4", "V5", "V7"], # 🆕 V2依赖V7
      "V6": ["V2"]
  }
  ```
- **批次顺序**: V4 → V5 → V3 → **V7** → V2 → V6
- **依赖逻辑**:
  - V7依赖V3：获取人物叙事 → 构建社会关系
  - V7依赖V5：获取场景描述 → 设计社交距离/隐私分级
  - V2依赖V7：获取社会关系洞察 → 融入设计方案

---

## 📋 设计方案（已文档化，等待实施）

### 3. V6-1增强 - 环境适应维度 📋
- **解决方案**: 通过 `ability_injections.yaml` 实现模式注入
- **触发条件**: 检测到M8极端环境模式
- **注入内容**:
  - 结构抗性系统（保留原有）
  - **材料适应系统**（新增）：基于气候数据选材、维护周期
  - **能源与生存系统**（新增）：低能耗、可再生能源、备用系统
  - **生理舒适保障**（新增）：温度/湿度/氧气/气压控制
- **实施方式**:
  - ✅ 在实施总结中已完整定义M8→V6-1注入规则
  - ⏳ 待创建 `ability_injections.yaml` 配置文件
  - ⏳ 待在 `TaskOrientedExpertFactory` 中实现注入逻辑

### 4. V6新增 - 6-5 灯光与视觉系统工程师 📋
- **新增位置**: `intelligent_project_analyzer/config/roles/v6_chief_engineer.yaml`
- **配置结构**: 参考V6-1/2/3/4的模板
- **核心理论**:
  - 灯光层次理论（环境光、任务光、重点光、装饰光）
  - 光线强化策略（概念与光线联动、空间序列节奏）
  - 昼夜节律照明（动态色温2700K-6500K）
  - 视觉舒适度（UGR<19、CRI>80）
  - 情绪照明（高照度=警觉、低照度=放松）
- **与其他专家协同**: V2/V3/V5/V6-1/V6-2/V6-3/V7
- **预估工作量**: ~400行YAML配置
- **实施状态**: ⏳ 待创建配置

### 5. ability_injections配置 - 模式→能力注入系统 📋
- **新增文件**: `intelligent_project_analyzer/config/ability_injections.yaml`
- **覆盖范围**: 10个设计模式 × 对应专家 × 注入规则
- **核心模式注入**:
  - M1概念驱动 → V2/V3（A1概念建构）
  - M2功能效率 → V5/V6（A6功能优化）
  - M3情绪体验 → V3/V7/V6-5（A3叙事+心理+A5灯光）
  - M4资产资本 → V6-4/V5（A7资本策略+A11运营产品化）
  - M5乡建在地 → V4/V6-3（A12文明表达+A4材料智能）
  - M6城市更新 → V2/V5（A12文明+A11运营）
  - M7技术整合 → V6-2（A8技术整合）
  - **M8极端环境 → V6-1（A10环境适应）** ← 重点
  - **M9社会结构 → V7/V5（A9社会关系建模）** ← 重点
  - M10未来推演 → V4/V6-2（未来研究+A8技术）
- **预估工作量**: ~350行YAML配置
- **实施状态**: ✅ 在实施总结中已完整定义规则，⏳ 待创建文件

---

## 🎯 立即可执行的下一步

### Option A: 完成V7 system_prompt重写（高优先级）
**任务**: 补全V7配置的理论框架部分
**文件**: `intelligent_project_analyzer/config/roles/v7_emotional_insight_expert.yaml`
**工作量**: ~2小时
**价值**: 让V7立即可用，填补A9社会关系建模缺口

**具体步骤**:
1. 读取当前V7配置（lines 95-370）
2. 补全 **Part A: 社会关系建模理论框架**（6个子能力详细说明）
3. 保留 **Part B: 心理洞察理论框架**（原有5个能力）
4. 扩展输出模板：增加 `social_structure_analysis` 字段
5. 更新 `must_select_when` 触发条件（增加多代同堂、再婚、合租场景）

### Option B: 创建V6-5配置（中优先级）
**任务**: 新增灯光与视觉系统工程师
**文件**: `intelligent_project_analyzer/config/roles/v6_chief_engineer.yaml`（在现有文件中增加"6-5"配置）
**工作量**: ~3小时
**价值**: 填补A5灯光系统缺口

**具体步骤**:
1. 在V6配置文件中的 `roles:` 下增加 `"6-5":` 配置块
2. 参考V6-1的结构模板（工具使用指南 + 身份与任务 + 输出模式判断 + 输出蓝图）
3. 定义5个核心理论框架（灯光层次、光线强化、昼夜节律、视觉舒适、情绪照明）
4. 定义输出JSON Schema（lighting_hierarchy_design等6个字段）
5. 增加keywords: ["灯光", "照明", "光线", "视觉", "昼夜节律", "情绪照明"]

### Option C: 创建ability_injections.yaml（中优先级）
**任务**: 创建模式→能力注入配置文件
**文件**: `intelligent_project_analyzer/config/ability_injections.yaml`（新建）
**工作量**: ~2小时
**价值**: 实现自动化能力注入，支持10个设计模式

**具体步骤**:
1. 创建YAML文件头部（版本、说明、使用方式）
2. 定义10个模式的注入规则（参考实施总结文档中的完整定义）
3. 重点完成M8→V6-1和M9→V7的注入规则（填补关键缺口）
4. 在 `TaskOrientedExpertFactory` 中实现注入逻辑（~50行代码）

---

## 📊 实施进度总览

| 任务 | 状态 | 完成度 | 价值 | 优先级 |
|------|------|--------|------|--------|
| V7配置升级（头部） | ✅ | 100% | ⭐⭐⭐⭐⭐ | - |
| V7配置升级（prompt） | 🔄 | 40% | ⭐⭐⭐⭐⭐ | 🔥 高 |
| Batch Scheduler正式化 | ✅ | 100% | ⭐⭐⭐⭐⭐ | - |
| V6-1增强（设计） | 📋 | 100%设计 | ⭐⭐⭐⭐ | 🔸 中 |
| V6-5新增（设计） | 📋 | 100%设计 | ⭐⭐⭐⭐⭐ | 🔸 中 |
| ability_injections（设计） | 📋 | 100%设计 | ⭐⭐⭐⭐ | 🔸 中 |

**总体完成度**: Phase 1 核心架构 60%完成

---

## 🚀 建议执行顺序

**立即执行（今天）**:
1. ✅ **已完成**: V7头部配置升级
2. ✅ **已完成**: Batch Scheduler修改
3. ✅ **已完成**: 创建实施总结文档（完整的设计方案）

**短期执行（本周）**:
4. 🔄 **进行中**: 完成V7 system_prompt重写（Option A）→ 让V7立即可用
5. ⏳ **下一步**: 创建ability_injections.yaml（Option C）→ 实现M8/M9注入
6. ⏳ **备选**: 创建V6-5配置（Option B）→ 填补灯光缺口

**中期执行（下周）**:
7. 在CapabilityDetector中增加轻量级模式检测
8. 在TaskOrientedExpertFactory中实现能力注入逻辑
9. 测试：多代同堂、再婚家庭、极端环境项目

---

## 📖 参考文档

### 本次实施创建的文档
1. **[PLAN_C_IMPLEMENTATION_SUMMARY.md](./PLAN_C_IMPLEMENTATION_SUMMARY.md)** - 完整实施方案（15000字）
   - 三个精准缺口详细分析
   - V7升级完整设计
   - V6-1增强方案
   - V6-5新增配置设计
   - ability_injections完整规则
   - 10个模式 × 注入prompt全部定义

2. **[PLAN_C_QUICK_CHECKLIST.md](./PLAN_C_QUICK_CHECKLIST.md)** - 本文档
   - 实施进度跟踪
   - 下一步行动清单
   - 快速执行指南

### 相关理论文档
3. **[sf/10_Mode_Engine](../../sf/10_Mode_Engine)** - 10种设计模式理论
4. **[sf/12_Ability_Core](../../sf/12_Ability_Core)** - 12种能力构成理论
5. **[docs/mechanism-reviews/THINKING_MODE_MULTI_EXPERT_MECHANISM_REVIEW.md](./THINKING_MODE_MULTI_EXPERT_MECHANISM_REVIEW.md)** - V2-V7专家机制复盘

---

## ✅ 验收标准

### V7升级验收
- [ ] V7配置文件version显示v2.0
- [ ] core_expertise包含6个社会关系建模能力
- [ ] system_prompt包含Part A（社会关系）+ Part B（心理洞察）
- [ ] 输出模板包含social_structure_analysis字段
- [ ] must_select_when包含"多代同堂"、"再婚家庭"、"合租"触发条件

### Batch Scheduler验收
- [ ] base_dependencies包含V7: ["V3", "V5"]
- [ ] V2依赖列表包含V7
- [ ] 日志显示批次顺序：V4→V5→V3→V7→V2→V6

### V6-5验收
- [ ] v6_chief_engineer.yaml存在"6-5"配置块
- [ ] keywords包含"灯光"、"照明"等关键词
- [ ] system_prompt包含5个核心理论框架
- [ ] 输出模板包含lighting_hierarchy_design等6个字段

### ability_injections验收
- [ ] ability_injections.yaml文件存在
- [ ] 包含10个模式的注入规则
- [ ] M8→V6-1规则明确定义环境适应4个维度
- [ ] M9→V7规则明确定义社会关系建模6个维度
- [ ] TaskOrientedExpertFactory能正确读取并注入

---

**文档版本**: v1.0
**最后更新**: 2026-02-12
**状态**: Phase 1完成60%，Phase 2设计完成100%
**下一里程碑**: 完成V7 system_prompt重写
