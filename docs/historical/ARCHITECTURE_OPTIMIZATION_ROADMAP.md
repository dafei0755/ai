# 系统架构优化实施路线图（渐进式 P2 方案）

## 总体目标

彻底消除配置文件冗余，建立清晰的信息流和职责边界，同时采用渐进式实施降低风险。

---

## 阶段划分

### 阶段 1：配置文件职责重新划分 ✅（已完成设计）

**目标：** 明确每个配置文件的单一职责

**新的配置文件架构：**

```
intelligent_project_analyzer/config/
├── role_selection_rules.yaml          # 选角规则（原 role_selection_strategy.yaml）
│   ├── adaptive_strategy_engine       # 协同模式决策树
│   ├── same_layer_deduplication       # 去重规则
│   └── collaboration_flow_model       # 依赖模型
│
├── role_gene_pool.yaml                # 角色元数据库（新建）
│   ├── V2-V7 的所有子角色元数据
│   ├── keywords, primary_abilities
│   └── llm_params (temperature, deliverables)
│
├── dynamic_project_director_v2.yaml   # DPD 提示词（保持）
│   ├── output_structure_mandate       # 输出结构
│   ├── dynamic_role_synthesis         # 角色合成协议
│   ├── special_scenarios              # 特殊场景识别
│   └── complexity_scoring             # 复杂度评分
│
├── MODE_TASK_LIBRARY.yaml             # 任务库（修改）
│   └── quality_target 引用 13_Evaluation_Matrix
│
└── roles/                             # 角色完整配置（单一信息源）
    ├── v2_design_director.yaml
    ├── v3_narrative_expert.yaml
    ├── v6_chief_engineer.yaml
    └── ...
```

**职责边界：**
- `role_selection_rules.yaml`: 只管"怎么选角色"（规则和策略）
- `role_gene_pool.yaml`: 只管"有哪些角色可选"（元数据目录）
- `roles/*.yaml`: 只管"角色的完整定义"（system_prompt、abilities、deliverables）
- `MODE_TASK_LIBRARY.yaml`: 只管"模式对应哪些任务"（任务分配）
- `13_Evaluation_Matrix`: 只管"如何评估质量"（评估标准）

---

### 阶段 2：创建 role_gene_pool.yaml（核心简化）

**目标：** 将 2000+ 行的 role_gene_pool 压缩为 300 行的元数据目录

**实施步骤：**

#### 2.1 提取角色元数据
从 `role_selection_strategy.yaml` 的 role_gene_pool 中提取：
- role_id, role_name
- keywords（用于 DPD 匹配）
- primary_abilities（从 roles/*.yaml 读取）
- llm_params（从 dynamic_project_director_v2.yaml 的 role_characteristics 合并）

#### 2.2 显式化 V6 子角色
当前 V6 只有父角色，6 个子角色隐藏在 `roles/v6_*.yaml` 中。需要显式化：

```yaml
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
      config_file: "roles/v6_1_structural_engineer.yaml"
      keywords: ["结构设计", "幕墙系统", "抗震", "基础设计"]
      primary_abilities: [A8]
    "6-2":
      name: "机电与智能化工程师"
      config_file: "roles/v6_2_mep_engineer.yaml"
      keywords: ["暖通", "给排水", "电气", "智能化", "BIM"]
      primary_abilities: [A8]
    "6-3":
      name: "室内工艺与材料工程师"
      config_file: "roles/v6_3_interior_engineer.yaml"
      keywords: ["材料选型", "工艺实施", "施工图", "节点详图"]
      primary_abilities: [A8]
    "6-4":
      name: "成本与造价工程师"
      config_file: "roles/v6_4_cost_engineer.yaml"
      keywords: ["成本控制", "造价估算", "材料询价", "预算管理"]
      primary_abilities: [A8]
    "6-5":
      name: "照明与灯光工程师"
      config_file: "roles/v6_5_lighting_engineer.yaml"
      keywords: ["照明设计", "灯光策略", "光环境", "节能照明"]
      primary_abilities: [A8]
    "6-6":
      name: "可持续与绿建工程师"
      config_file: "roles/v6_6_sustainability_engineer.yaml"
      keywords: ["绿色建筑", "LEED", "被动式设计", "能耗分析"]
      primary_abilities: [A8]
```

#### 2.3 删除冗余的 system_prompt
不再在 role_gene_pool 中存储完整的 system_prompt（每个角色 200+ 行），改为引用 `config_file`。

**简化效果：**
- 从 2000+ 行 → 300 行
- 信息重复从 3 处 → 1 处（roles/*.yaml 为单一信息源）

---

### 阶段 3：重构 role_selection_strategy.yaml → role_selection_rules.yaml

**目标：** 删除 role_gene_pool 部分，只保留选角规则

**保留内容：**
- `adaptive_strategy_engine`: 三种协同模式的决策树
- `same_layer_deduplication`: 同层去重规则
- `collaboration_flow_model`: 上下游依赖模型
- `output_structure_mandate`: 输出结构强制声明
- `dynamic_role_synthesis_protocol`: 动态角色合成协议

**删除内容：**
- `role_gene_pool`: 移到独立文件

**文件大小：** 从 2000+ 行 → 500 行

---

### 阶段 4：完成 MODE_TASK_LIBRARY.yaml 转换

**目标：** 将所有 validation_criteria 转换为 quality_target

**当前进度：** 6/41 已完成

**批量转换策略：**

按模式分组转换，每个模式的任务通常共享相似的评估维度：

| 模式 | 核心评估维度 | 目标等级 |
|------|-------------|---------|
| M1 概念驱动 | concept_integrity, narrative_coherence | L4 |
| M2 功能效率 | spatial_logic, technical_feasibility | L4 |
| M3 情绪体验 | emotional_resonance, sensory_design | L4 |
| M4 资产资本 | commercial_value, cost_control | L4 |
| M5 乡建在地 | contextual_integration, cultural_authenticity | L4 |
| M6 城市更新 | urban_integration, social_impact | L4 |
| M7 技术整合 | technical_innovation, interdisciplinary_integration | L4 |
| M8 极端环境 | environmental_adaptation, technical_feasibility | L4 |
| M9 社会结构 | social_impact, behavioral_design | L4 |
| M10 未来推演 | future_adaptability, innovation_potential | L4 |

**转换模板：**
```yaml
quality_target:
  dimension: "评估维度名称"
  target_level: "L3或L4"
  reference: "13_Evaluation_Matrix.维度名称.等级"
  criteria_mapping:
    - "原验证标准 → 对应的L级描述"
```

---

### 阶段 5：代码适配

**目标：** 修改代码以读取新的配置结构

**需要修改的文件：**

#### 5.1 `dynamic_project_director.py`
```python
# 修改前：从 role_selection_strategy.yaml 读取 role_gene_pool
role_gene_pool = load_yaml("role_selection_strategy.yaml")["role_gene_pool"]

# 修改后：从独立文件读取
role_gene_pool = load_yaml("role_gene_pool.yaml")
```

#### 5.2 `core/strategy_manager.py`
```python
# 修改前：从 role_selection_strategy.yaml 读取规则
selection_rules = load_yaml("role_selection_strategy.yaml")

# 修改后：从 role_selection_rules.yaml 读取
selection_rules = load_yaml("role_selection_rules.yaml")
```

#### 5.3 `project_director.py`
```python
# 新增：任务验证映射器
class TaskValidationMapper:
    def __init__(self):
        self.task_library = load_yaml("MODE_TASK_LIBRARY.yaml")
        self.evaluation_matrix = load_yaml("13_Evaluation_Matrix")

    def validate_task(self, task_id, deliverable):
        """根据 quality_target 验证任务交付物"""
        task = self.task_library[task_id]
        quality_target = task["quality_target"]

        dimension = quality_target["dimension"]
        target_level = quality_target["target_level"]

        # 从评估矩阵获取标准
        criteria = self.evaluation_matrix[dimension][target_level]

        # 验证逻辑...
        return validation_result
```

#### 5.4 `agents/specialized_agent_factory.py`
```python
# 修改前：V6 子角色隐性路由
def create_v6_agent(task_description):
    # 根据任务描述推断需要哪个 V6 子角色
    if "结构" in task_description:
        return load_role("roles/v6_1_structural_engineer.yaml")
    # ...

# 修改后：DPD 直接指定 V6 子角色
def create_agent(role_id):
    # DPD 已经选择了具体的 role_id（如 "6-1"）
    role_config = role_gene_pool[role_id]
    return load_role(role_config["config_file"])
```

---

### 阶段 6：测试验证

**目标：** 确保简化后的系统功能完整

**测试层级：**

#### 6.1 单元测试
- 测试 role_gene_pool.yaml 加载
- 测试 role_selection_rules.yaml 加载
- 测试 MODE_TASK_LIBRARY.yaml 的 quality_target 解析

#### 6.2 集成测试
- 测试 DPD 选角逻辑（包括 V6 子角色）
- 测试任务验证映射器
- 测试角色合成协议

#### 6.3 端到端测试
- 运行完整的项目分析流程
- 验证所有角色都能正确加载
- 验证任务验证能正确引用评估矩阵

**测试用例：**
```python
# 测试 V6 子角色显式选择
def test_v6_explicit_selection():
    dpd = DynamicProjectDirector()
    result = dpd.select_roles("需要结构设计和照明设计")

    assert "6-1" in result.selected_roles  # 结构工程师
    assert "6-5" in result.selected_roles  # 照明工程师
    assert result.roles["6-1"].name == "结构与幕墙工程师"

# 测试任务验证引用评估矩阵
def test_task_validation_mapping():
    mapper = TaskValidationMapper()
    result = mapper.validate_task("M1_T02", deliverable)

    assert result.dimension == "concept_integrity"
    assert result.target_level == "L4"
    assert result.criteria_source == "13_Evaluation_Matrix"
```

---

## 实施时间表（渐进式）

### 第 1 周：配置文件重构
- [ ] Day 1-2: 创建 role_gene_pool.yaml（提取元数据 + 显式化 V6）
- [ ] Day 3-4: 重构 role_selection_strategy.yaml → role_selection_rules.yaml
- [ ] Day 5: 完成 MODE_TASK_LIBRARY.yaml 的剩余转换

### 第 2 周：代码适配
- [ ] Day 1-2: 修改 dynamic_project_director.py 和 strategy_manager.py
- [ ] Day 3-4: 修改 project_director.py，实现任务验证映射器
- [ ] Day 5: 修改 specialized_agent_factory.py，支持 V6 显式选择

### 第 3 周：测试验证
- [ ] Day 1-2: 单元测试
- [ ] Day 3-4: 集成测试
- [ ] Day 5: 端到端测试 + 修复问题

---

## 风险控制

### 回滚机制
- 保留原配置文件为 `*.yaml.backup`
- 使用 Git 分支进行开发（`feature/architecture-optimization`）
- 每个阶段完成后创建 Git tag

### 渐进式部署
- 阶段 2-3 完成后：配置文件可以独立验证（不影响代码）
- 阶段 4 完成后：任务验证可以独立测试
- 阶段 5 完成后：代码适配可以逐个文件验证

### 兼容性保证
- 在代码中保留对旧配置格式的兼容性（临时）
- 使用 feature flag 控制新旧逻辑切换
- 生产环境先用旧逻辑，测试通过后再切换

---

## 预期成果

### 配置文件简化
- `role_selection_strategy.yaml`: 2000+ 行 → 500 行（role_selection_rules.yaml）
- 新增 `role_gene_pool.yaml`: 300 行（元数据目录）
- 总行数减少：2000+ → 800（减少 60%）

### 信息重复消除
- 角色信息：3 处存储 → 1 处存储（roles/*.yaml）
- 验证标准：2 套系统 → 1 套系统（13_Evaluation_Matrix）
- V6 子角色：隐性路由 → 显式选择

### 维护成本降低
- 添加新角色：修改 2 个文件 → 修改 1 个文件（roles/*.yaml）
- 修改验证标准：修改 2 处 → 修改 1 处（13_Evaluation_Matrix）
- 调整选角规则：修改 2 个文件 → 修改 1 个文件（role_selection_rules.yaml）

### 系统可理解性提升
- 配置文件职责清晰，不重叠
- 信息流向明确：roles/*.yaml → role_gene_pool.yaml → DPD → 选角
- 验证闭环：MODE_TASK_LIBRARY → 13_Evaluation_Matrix → 任务验收

---

## 下一步行动

立即开始阶段 2：创建 role_gene_pool.yaml

1. 从 role_selection_strategy.yaml 提取所有角色的元数据
2. 从 roles/*.yaml 读取 primary_abilities
3. 从 dynamic_project_director_v2.yaml 读取 llm_params
4. 显式化 V6 的 6 个子角色
5. 验证新文件可以正确加载
