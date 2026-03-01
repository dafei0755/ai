# 动态专家合成机制专题复盘 v8.1

> **复盘日期**: 2026-02-20
> **版本升级**: v7.3 → v8.1
> **核心目标**: 提升合成质量，解决角色与子角色覆盖有限时的未知问题处理能力

---

## 一、现状诊断：8个关键瓶颈

### 问题全景

| # | 瓶颈 | 严重度 | 状态 |
|---|------|--------|------|
| P1 | 合成协议仅在Prompt中声明，无代码强制执行 | **严重** | ✅ 已修复 |
| P2 | 合成角色ID格式(`2-1+5-1`)无代码路由支持 | **严重** | ✅ 已修复 |
| P3 | 权重计算纯关键词匹配，缺乏语义理解 | 中等 | 🔜 计划中 |
| P4 | 测试套件使用Mock数据，未真正调用LLM | 低 | 📌 待定 |
| P5 | ChallengeDetector的`synthesize`决策无LLM支持 | 中等 | 🔜 计划中 |
| P6 | 合成质量评估仅在离线测试，无在线监控 | **严重** | ✅ 已修复 |
| P7 | DPD中存在重复的`select_roles_for_task`方法 | 低 | 📌 技术债 |
| P8 | 合成Prompt示例不足，融合深度指导缺失 | **严重** | ✅ 已修复 |

---

## 二、架构分析：合成机制工作流

```
用户需求输入
    ↓
[RequirementsAnalyst] 解析需求 → 结构化需求
    ↓
[RoleWeightCalculator] jieba分词 → 标签匹配 → 角色权重
    ↓
[DynamicProjectDirector.select_roles_for_task()]
    ├── 解析 project_scope
    ├── 按权重排序可用角色
    ├── 构建 system_prompt + user_prompt
    ├── LLM调用 → RoleSelection (Pydantic验证)
    │
    │   ┌─────────────────────────────────────────┐
    │   │ 自适应协同策略引擎 决策树                 │
    │   │  优先级1: 单一专家深潜 (匹配度>0.9)      │
    │   │  优先级2: 多专家并行 (多子角色明确匹配)   │
    │   │  优先级3: ★动态角色合成★ (跨界+新颖)     │
    │   └─────────────────────────────────────────┘
    │
    ├── [NEW v8.1] 合成角色ID路由 (SYNTHESIZED_2-1+5-1)
    ├── [NEW v8.1] 合成质量在线验证 (5维度评分)
    ├── Pydantic验证 + 重试3次 + 降级兜底
    └── 返回 RoleSelection
    ↓
[TaskOrientedExpertFactory.execute_expert()]
    ├── [NEW v8.1] 合成角色 → 动态融合Prompt生成
    ├── 搜索阶段 → 报告阶段 (两阶段执行)
    └── 乱码检测 + 质量验证
    ↓
[ChallengeDetector] 挑战检测与闭环
    ↓
[ResultAggregator] 结果聚合 → 最终报告
```

---

## 三、v8.1 优化详情

### 3.1 合成角色ID全链路路由支持 (P1+P2)

**问题**: 合成协议定义了 `"2-1+5-1"` 这样的复合ID，但整个代码链路（`_construct_full_role_id` → `RoleManager.get_role_config` → `_get_role_config_filename` → `_extract_base_type`）都不支持这种格式，导致合成角色在下游代码中找不到配置。

**修复**:

| 组件 | 文件 | 改动 |
|------|------|------|
| `_construct_full_role_id` | `dynamic_project_director.py` | 检测`+`号 → 生成`SYNTHESIZED_`前缀 |
| `RoleManager.get_role_config` | `role_manager.py` | 检测复合ID → 调用`_get_synthesized_role_config`动态融合 |
| `RoleManager._get_synthesized_role_config` | `role_manager.py` | **新增** 智能融合多个父角色的配置 |
| `_get_role_config_filename` | `task_oriented_expert_factory.py` | 合成角色 → 取主导父角色配置文件 |
| `_extract_base_type` | `task_oriented_expert_factory.py` | 合成角色 → 取主导父角色的V层级 |

**融合策略**:
- **system_prompt**: 主导父角色框架 + 其他父角色核心能力注入
- **keywords**: 合并去重所有父角色关键词
- **描述**: `合成角色[2-1(居住设计)+5-1(场景运营)]: 融合XXX的跨界能力`

### 3.2 合成质量在线验证器 (P6)

**问题**: `SynthesisQualityScorer` 只存在于测试文件中，未集成到在线流程。LLM生成的合成角色无法在运行时得到质量保障。

**修复**: 创建 `services/synthesis_quality_validator.py`，5维度加权评分：

| 维度 | 权重 | 验证内容 | 合格线 |
|------|------|----------|--------|
| 跨战略层 | 25% | 父角色是否来自不同V层级 | ≥8 (硬性) |
| 融合深度 | 30% | 任务是否使用融合性动词，是否有堆叠信号 | ≥6 |
| 命名质量 | 15% | dynamic_role_name是否体现融合特征 | ≥7 |
| 关键词融合 | 15% | keywords去重率和多样性 | ≥7 |
| 依赖最小化 | 15% | 是否依赖了已被合成的父角色 | ≥8 |

**集成点**: `DynamicProjectDirector.select_roles_for_task()` 返回前自动调用 `_validate_synthesized_roles()`

**评分系统**:
- **A+ (≥9.0)**: 优秀合成，跨界融合深度高
- **A (≥8.0)**: 良好，可直接执行
- **B (≥7.0)**: 合格，建议观察
- **C (≥6.0)**: 待改进，输出日志警告
- **D (<6.0)**: 不合格，建议降级为多专家并行

### 3.3 合成Prompt增强与融合深度指导 (P8)

**问题**: 合成协议原本只有1个示例、3个约束，LLM缺乏足够的"融合"范式指导，容易生成任务堆叠而非真正的融合。

**修复**:

#### 新增 `fusion_depth_requirements`:
```yaml
fusion_patterns:    # 正确的融合模式
  - "X逻辑驱动Y决策"
  - "在X视角下重构Y方案"
  - "平衡X需求与Y目标"
  - "将X洞察嵌入Y过程"

anti_patterns:      # 需要避免的堆叠模式
  - "先做X分析，再做Y设计"
  - "X负责A任务，Y负责B任务"
  - "分别从X和Y角度分析"
```

#### 新增 `synthesis_triggers`:
精细化合成触发条件，避免过度合成或遗漏必要合成：
- **应合成**: 核心意图深度依赖两个V层专业能力 / 存在明确的"X驱动Y"关系 / 关键词无法通过任务分工解耦
- **不应合成**: 两角色可通过dependencies解耦 / 需求是多个独立子任务 / 3+父角色融合过于复杂

#### 扩展合成约束 (3→5):
- 约束4: `dynamic_role_name`必须体现融合特征，格式为 `{项目特征}+{融合专业}+{职责}`
- 约束5: 每个task至少包含一个融合性关键动词（驱动/整合/协同/平衡/贯穿/嵌入）

#### 扩展合成示例 (1→4):
| 场景 | 父角色组合 | 融合模式 |
|------|-----------|----------|
| 三代同堂居住空间 | V2-1 + V5-1 | 运营逻辑驱动设计决策 |
| 文化疗愈康养空间 | V3-2 + V7-1 | 文化转译嵌入心理疗愈 |
| 自闭症儿童家庭住宅 | V2-1 + V7-1 | 感官需求驱动空间规划 |
| 电竞主题商业空间 | V3-3 + V5-2 | 品牌IP驱动坪效优化 |

### 3.4 动态Prompt融合引擎

**问题**: 即使DPD正确生成了合成角色，专家工厂执行时只能加载单个父角色的system_prompt，丢失了跨界融合的能力。

**修复**: 在 `TaskOrientedExpertFactory` 中新增：

- `_build_synthesized_expert_prompt()`: 动态构建融合Prompt
  - 以主导父角色为框架
  - 从次要父角色提取核心专业领域段落
  - 注入"跨界融合身份声明"，锚定合成身份
  - 添加融合原则指令

- `_extract_core_capability_section()`: 从system_prompt中智能提取核心能力段落
  - 启发式匹配"核心专业领域"/"工具箱"等段落标题
  - 回退到取前300字概要

---

## 四、验证结果

```
Test 1 (合法跨层合成 V2+V5): Score=9.85/10 A+ ✅
Test 2 (同层违规 V2-1+V2-2): Score=4.35/10 D ❌ 正确拦截
Test 3 (非合成角色):         跳过验证 ✅
Test 4 (批量验证含合成角色): Score=9.40/10 A+ ✅
Test 5 (RoleManager融合配置): 成功生成融合配置 (17个关键词) ✅
```

既有测试套件(`test_role_synthesis.py` 6个测试用例)全部通过。

---

## 五、影响范围与兼容性

| 影响范围 | 兼容性 |
|----------|--------|
| `dynamic_project_director.py` | ✅ 向后兼容，新增方法不影响现有流程 |
| `role_manager.py` | ✅ 向后兼容，原有`get_role_config`对非合成ID行为不变 |
| `task_oriented_expert_factory.py` | ✅ 向后兼容，合成Prompt生成只在检测到`+`时激活 |
| `role_selection_strategy.yaml` | ✅ 新增配置节，不影响现有配置解析 |
| `role_gene_pool.yaml` | 无改动 |
| 新增模块 | `services/synthesis_quality_validator.py` (独立模块) |

---

## 六、待改进项（后续迭代）

| 优先级 | 待改进项 | 估计工作量 |
|--------|---------|-----------|
| P1 | 权重计算器引入embedding语义匹配，解决"老人"≠"养老"问题 | 8h |
| P1 | ChallengeDetector的`synthesize`决策接入LLM智能综合 | 6h |
| P2 | 清理DPD中重复的`select_roles_for_task`方法 | 2h |
| P2 | FastTrack模式代码实现（配置中已定义但无代码） | 4h |
| P3 | 合成角色的A/B测试框架（对比合成vs多专家并行质量） | 12h |
| P3 | 合成质量评分数据持久化与趋势分析 | 6h |

---

## 七、结论

v8.1 通过**4个核心改进**从根本上打通了动态专家合成的全链路：

1. **ID路由**: 合成角色ID现在可以在整个系统中正确流转
2. **质量验证**: 5维度在线评分器确保合成质量可度量、可监控
3. **Prompt增强**: 4个示例+融合/反融合模式+精细化触发条件引导LLM生成高质量合成
4. **执行融合**: 专家工厂动态构建融合Prompt，确保合成角色真正继承多个父角色的能力

这些改进使系统在面对预定义角色无法覆盖的跨界需求时，具备了更强的自适应能力。
