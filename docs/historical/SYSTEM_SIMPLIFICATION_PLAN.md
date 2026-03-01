# 系统简化方案

## 一、当前问题诊断

### 1. 配置文件职责重叠

**当前状态：**
- `role_selection_strategy.yaml`（158行起）：包含 role_gene_pool、adaptive_strategy_engine、same_layer_deduplication
- `dynamic_project_director_v2.yaml`（111行起）：包含 special_scenarios、role_characteristics、complexity_scoring

**重叠内容：**
- 两个文件都在定义"如何选角色"的规则
- `role_characteristics` 与 `role_gene_pool` 描述同一批角色
- `special_scenarios` 与 `adaptive_strategy_engine` 都在定义场景匹配规则

### 2. 角色信息三重存储

**当前状态：**
```
role_selection_strategy.yaml 的 role_gene_pool:
  V2_设计总监:
    description: "设计总监 & 设计负责人"
    roles:
      "2-1":
        keywords: ["居住空间设计", "住宅空间设计", ...]
        description: "作为V2设计负责人，扮演住宅空间专家..."
        system_prompt: |
          ### 角色身份：V2 设计总监 (居住空间专家)
          你是一位 V2_设计总监...

roles/v2_design_director.yaml:
  sub_roles:
    "2-1":
      name: "居住空间设计总监"
      core_abilities: [A1, A2, A7]
      expertise: "高端私宅与别墅的空间规划..."

dynamic_project_director_v2.yaml:
  role_characteristics:
    V2_设计总监:
      temperature: 0.6
      strength: "整合协调、最终决策、方案统筹"
```

**问题：** 同一个角色的信息分散在三个地方，维护成本高，容易不一致。

### 3. V6 子角色的隐性路由

**当前状态：**
- `role_gene_pool` 只有 `V6_专业总工程师` 父角色
- V6 的 6 个子角色（结构/机电/材料/成本/灯光/可持续）只存在于 `roles/v6_*.yaml`
- DPD 选择"V6"后，由 `SpecializedAgentFactory` 在运行时根据任务内容隐性路由到具体子角色

**问题：** DPD 的 LLM 不知道 V6 有哪些子角色，无法精确选择。

### 4. 任务验证标准的双轨系统

**当前状态：**
```
MODE_TASK_LIBRARY.yaml:
  M1_T02:
    validation_criteria:
      - "概念是否从PPT层落地为结构逻辑？"
      - "每个设计决策是否能回溯到概念？"

13_Evaluation_Matrix:
  concept_integrity:
    L4: "概念贯通：概念贯穿宏观到微观，每个设计决策可回溯"
```

**问题：** 两套系统描述同一件事，但独立运行，没有闭环。

---

## 二、简化方案

### 方案 A：明确配置文件分工（推荐）

**不合并文件，而是明确职责边界：**

#### `role_selection_strategy.yaml` → 重命名为 `role_selection_rules.yaml`
**职责：** 选角规则和策略
**保留内容：**
- `adaptive_strategy_engine`（协同模式决策树）
- `same_layer_deduplication`（去重规则）
- `collaboration_flow_model`（依赖模型）

**删除内容：**
- `role_gene_pool`（移到独立文件）

#### `dynamic_project_director_v2.yaml`
**职责：** DPD 的 LLM 提示词和输出结构
**保留内容：**
- `output_structure_mandate`（输出结构）
- `dynamic_role_synthesis_protocol`（角色合成协议）
- `special_scenarios`（特殊场景识别）
- `complexity_scoring`（复杂度评分）

**删除内容：**
- `role_characteristics`（合并到 role_gene_pool）

#### 新建 `role_gene_pool.yaml`（独立文件）
**职责：** 角色元数据库（DPD 的选角手册）
**内容结构：**
```yaml
V2_设计总监:
  config_file: "roles/v2_design_director.yaml"  # 引用完整配置
  primary_abilities: [A1, A2, A7]  # 从配置文件提取
  llm_params:
    temperature: 0.6
    min_deliverables: 4
    max_deliverables: 6
  sub_roles:
    "2-0":
      name: "项目设计总监"
      keywords: ["综合体", "总体规划", "整合"]
      primary_abilities: [A1, A2, A7]
    "2-1":
      name: "居住空间设计总监"
      keywords: ["居住空间设计", "住宅空间设计", "私宅设计"]
      primary_abilities: [A1, A2, A7]
    "2-2":
      name: "商业零售设计总监"
      keywords: ["商业空间设计", "零售店铺设计"]
      primary_abilities: [A1, A6, A7]

V6_专业总工程师:
  config_file: "roles/v6_chief_engineer.yaml"
  primary_abilities: [A8]
  llm_params:
    temperature: 0.4
    min_deliverables: 1
    max_deliverables: 2
  sub_roles:
    "6-1":
      name: "结构与幕墙工程师"
      keywords: ["结构设计", "幕墙系统", "抗震"]
      primary_abilities: [A8]
    "6-2":
      name: "机电与智能化工程师"
      keywords: ["暖通", "给排水", "电气", "智能化"]
      primary_abilities: [A8]
    "6-3":
      name: "室内工艺与材料工程师"
      keywords: ["材料选型", "工艺实施", "施工图"]
      primary_abilities: [A8]
    # ... 其他 V6 子角色
```

**优势：**
- 删除 `system_prompt` 的完整存储（太长，从 roles/*.yaml 读取）
- 只保留 DPD 选角需要的元数据（keywords、abilities、llm_params）
- V6 子角色显式化，DPD 可以精确选择

---

### 方案 B：任务验证标准统一引用

#### 修改 `MODE_TASK_LIBRARY.yaml`

**当前：**
```yaml
M1_T02:
  validation_criteria:
    - "概念是否从PPT层落地为结构逻辑？"
    - "每个设计决策是否能回溯到概念？"
```

**修改为：**
```yaml
M1_T02:
  quality_target:
    dimension: "concept_integrity"
    target_level: "L4"
    reference: "13_Evaluation_Matrix.concept_integrity.L4"
  validation_method: "check_if_deliverable_meets_L4_criteria"
```

**优势：**
- 删除重复的验证标准文本
- 任务验收直接对应评估矩阵的 L 级
- 建立任务执行 → 评估的闭环

---

## 三、实施步骤

### 阶段 1：配置文件重构（不影响代码）

1. 创建 `role_gene_pool.yaml`，从 `role_selection_strategy.yaml` 提取并简化
2. 从 `role_selection_strategy.yaml` 删除 `role_gene_pool` 部分
3. 从 `dynamic_project_director_v2.yaml` 删除 `role_characteristics` 部分
4. 在 `role_gene_pool.yaml` 中显式化 V6 的 6 个子角色

### 阶段 2：任务库标准统一

5. 修改 `MODE_TASK_LIBRARY.yaml`，`validation_criteria` 改为 `quality_target` 引用
6. 创建 `task_validation_mapper.py`，实现任务验收 → 评估矩阵的映射

### 阶段 3：代码适配

7. 修改 `dynamic_project_director.py`，读取新的 `role_gene_pool.yaml`
8. 修改 `core/strategy_manager.py`，适配新的配置结构
9. 修改 `project_director.py`，使用新的任务验证映射

### 阶段 4：测试验证

10. 单元测试：验证配置文件加载
11. 集成测试：验证 DPD 选角逻辑
12. 端到端测试：验证完整工作流

---

## 四、预期效果

### 简化前
- 配置文件：5 个（role_selection_strategy + dynamic_project_director_v2 + roles/*.yaml + MODE_TASK_LIBRARY + 13_Evaluation_Matrix）
- 信息重复：3 处（角色描述在 3 个地方）
- 隐性逻辑：1 处（V6 子角色隐性路由）
- 验证标准：2 套（任务验证 + 评估矩阵独立）

### 简化后
- 配置文件：6 个（role_selection_rules + dynamic_project_director_v2 + role_gene_pool + roles/*.yaml + MODE_TASK_LIBRARY + 13_Evaluation_Matrix）
- 信息重复：0 处（角色信息单一来源）
- 隐性逻辑：0 处（V6 子角色显式化）
- 验证标准：1 套（任务验证引用评估矩阵）

### 维护成本
- 添加新角色：只需修改 `roles/*.yaml` 和 `role_gene_pool.yaml`（2 处 → 1 处，因为 gene_pool 只存元数据）
- 修改验证标准：只需修改 `13_Evaluation_Matrix`（2 处 → 1 处）
- 调整选角规则：只需修改 `role_selection_rules.yaml`（2 处 → 1 处）

---

## 五、风险评估

### 低风险
- 配置文件重构：不影响代码逻辑，只是重新组织
- V6 子角色显式化：增强而非削弱功能

### 中风险
- 任务验证标准统一：需要新增映射逻辑，但不影响现有功能

### 缓解措施
- 保留旧配置文件作为备份
- 分阶段实施，每个阶段独立测试
- 先在开发环境验证，再部署到生产环境
