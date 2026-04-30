# 空间分类系统梳理文档

> 日期：2026-03-07  
> 适用范围：`intelligent_project_analyzer` 中与“空间分类 / 空间类型 / 项目类型 / 功能分区 / 空间语义框架”相关的历史与现行实现。  
> 文档目的：沉淀系统中“空间分类”相关的组件、方法、文件与调用关系，便于后续重构、追踪与字段归并。

---

## 1. 结论摘要

当前系统中，“空间分类”**不是单一中心模块**，而是由以下三层能力共同承载：

1. **类型分类层**  
   负责判断用户当前描述的是哪一类项目 / 空间类型，核心字段是 `project_type`、`space_type`。

2. **语义本体层**  
   负责定义某一类项目/空间应使用哪些分析维度、关注点与专家增强视角，核心载体是 `ontology.yaml`。

3. **业务消费层**  
   负责在需求分析、问卷交互、执行规划、交付物命名等环节消费分类结果，形成后续流程路由与输出。

换言之，系统以前关于“空间分类”的能力，本质上是：

- `project_type` 驱动的项目分类体系
- `space_type` 驱动的物理/功能空间标签
- `ontology.yaml` 驱动的语义分析框架
- 问卷、工作流与交付层对以上结果的消费链

---

## 2. 总体结构

### 2.1 三层结构

| 层级 | 作用 | 代表字段 / 对象 | 核心文件 |
| --- | --- | --- | --- |
| 类型分类层 | 识别项目或空间属于哪类类型 | `project_type` / `space_type` / `parent_type` / `specialty_tag` | `services/_type_registry.py`、`services/project_type_detector.py` |
| 语义本体层 | 为不同项目类型提供分析维度与专家增强层 | ontology frameworks / expert extensions | `knowledge_base/ontology.yaml`、`utils/ontology_loader.py`、`services/ontology_service.py` |
| 业务消费层 | 在需求分析、问卷、执行与交付环节使用分类结果 | `structured_requirements` / `physical_context` / `project_classification` | `agents/requirements_analyst_agent.py`、`workflow/nodes/*.py`、`interaction/questionnaire/*.py` |

### 2.2 当前最接近“空间分类”的真实落点

系统中与“空间分类”最直接对应的并不是一个单独模块，而是以下几类字段与逻辑：

- `project_type`：最核心的项目/空间类型分类字段
- `space_type`：更贴近物理空间、功能空间、上下文标签的字段
- 问卷中的“空间类型配置”问题：面向用户可见的“空间分类”交互形式
- `ontology.yaml` 中按项目类型分层的框架：面向内部分析的“空间语义分类”形式
- `extracted_spatial_zones`：新主线下逐步显式化的空间区域对象

---

## 3. 组件梳理

### 3.1 类型分类真相源组件

#### `intelligent_project_analyzer/services/_type_registry.py`

这是当前“项目/空间类型分类”的**单一权威注册表**。

主要职责：

- 定义所有项目类型注册表 `PROJECT_TYPE_REGISTRY`
- 提供旧 ID → 新 ID 的兼容映射 `LEGACY_TYPE_ALIASES`
- 定义父分类桶 `PARENT_TYPE_MAP`
- 定义专项细分标签 `SPECIALTY_TAG_MAP`
- 统一提供 ID → 标签 / 英文名 / 列表等公共函数

该文件中的分类覆盖了大量空间或项目类型，例如：

- `personal_residential`
- `commercial_office`
- `commercial_dining`
- `commercial_hospitality`
- `special_function`
- `digital_media_studio`
- `popup_temporary`
- `hybrid_residential_commercial`
- `residential_collective`

从系统角度看，这个文件就是“空间分类字典总表”。

#### `intelligent_project_analyzer/services/project_type_detector.py`

这是读取注册表并执行分类检测的主组件。

主要职责：

- 根据输入文本和任务内容推断 `project_type`
- 计算置信度
- 输出人类可读的命中原因
- 推导 `parent_type`
- 提取 `specialty_tag`
- 输出次候选类型、歧义提示等扩展信息

它本身不是分类定义源，而是分类规则执行器。

---

### 3.2 语义本体组件

#### `intelligent_project_analyzer/knowledge_base/ontology.yaml`

这是“空间/项目语义框架”的核心数据源。

与 `_type_registry.py` 不同，这里不是在回答“这是什么类型”，而是在回答：

- 这类项目应该从哪些维度去理解？
- 不同类型的空间应该关注哪些问题？
- 不同专家在这种类型下应增加哪些分析维度？

主要结构包括：

- `ontology_frameworks`
  - `meta_framework`
  - `personal_residential`
  - `commercial_enterprise`
  - `office_coworking`
  - `hospitality_tourism`
  - `education_research`
  - `healthcare_wellness`
  - `industrial_manufacturing`
  - `transportation_infrastructure`
  - 等等
- `expert_extensions`
  - `requirements_analyst`
  - `spatial_planner`
  - `conceptual_designer`
  - `structural_engineer`
  - `mep_engineer`
  - 等等

它体现的是“按空间/项目类型划分的分析世界观”。

#### `intelligent_project_analyzer/utils/ontology_loader.py`

这是三层注入式本体加载器。

三层结构：

1. 基础层：`meta_framework`
2. 项目类型层：按 `project_type` 加载对应框架
3. 专家强化层：按 `expert_role` 注入附加维度

因此，它是“空间分类 → 分析维度注入”的桥梁。

#### `intelligent_project_analyzer/services/ontology_service.py`

这是本体框架的服务层封装。

主要用于：

- 加载与缓存 `ontology.yaml`
- 查询所有框架
- 获取单个框架详情
- 搜索维度关键词
- 验证 YAML 语法

#### `intelligent_project_analyzer/api/routes/admin_ontology.py`

这是本体相关的后台 API 入口。

说明本体框架不仅用于内部推理，也具备管理与查看能力。

---

### 3.3 主流程消费组件

#### `intelligent_project_analyzer/agents/requirements_analyst_agent.py`

这是需求分析主代理，是分类结果进入主流程的重要入口。

主要职责：

- 解析用户输入
- 生成 `structured_data`
- 推断并写入 `project_type`
- 输出 `physical_context`
- 输出 `project_type_preliminary`
- 为后续流程提供初始结构化结果

#### `intelligent_project_analyzer/workflow/nodes/requirements_nodes.py`

这是工作流中需求分析结果落盘的关键节点。

主要职责：

- 调用 `RequirementsAnalystAgentV2`
- 从 `result.structured_data` 中读取 `project_type`
- 将 `project_type` 写入主状态 `ProjectAnalysisState`
- 同时写入动机路由、雷达路由等后续消费字段

从主链角度看，`project_type` 在这里正式进入工作流状态。

#### `intelligent_project_analyzer/core/state.py`

这是全局状态定义文件。

与空间分类相关的重点字段包括：

- `project_type`
- `project_classification`
- `structured_requirements`
- `detected_design_modes`
- `physical_context`（在具体业务结果中被消费）
- `extracted_spatial_zones`
- `selected_dimensions`
- `radar_dimension_values`

其中 `extracted_spatial_zones` 说明系统新主线已经开始把空间区域对象显式化。

---

### 3.4 问卷与交互消费组件

#### `intelligent_project_analyzer/interaction/questionnaire/generators.py`

这是“空间分类”在用户交互层最直观的体现之一。

已确认的空间相关问卷内容包括：

- 办公场景下的 `office_space_types`
- 问题文案：`以下哪些空间类型是必须的？`
- 说明文案：`空间类型配置决定了功能分区。`

这意味着：

- `project_type` 会影响问卷模板
- “空间类型”被显式暴露给用户作为可配置项
- “功能分区”依赖“空间类型配置”

#### `intelligent_project_analyzer/interaction/questionnaire/context.py`

负责问卷上下文结构，包含 `project_type` 等字段。

#### `intelligent_project_analyzer/interaction/questionnaire/llm_generator.py`

会读取 `project_type` 和 `physical_contexts` 组织问卷生成上下文。

#### `intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py`

渐进式问卷节点会消费 `project_type`，用于组织交互内容。

#### `intelligent_project_analyzer/interaction/nodes/questionnaire_summary.py`

在总结阶段会综合物理环境、约束、雷达结果等，完成更正式的需求洞察整理。

---

### 3.5 执行与交付消费组件

#### `intelligent_project_analyzer/workflow/nodes/deliverable_id_generator_node.py`

这是 `space_type` 被直接消费的关键文件。

主要表现：

- 从 `structured_requirements["physical_context"]` 中提取 `space_type`
- 用于生成交付物名称
- 用于拼接 `project_context`
- 用于输出如：
  - `整体设计方案`
  - `{space_type}整体设计方案`
  - `{space_type}的功能分区`
  - `{space_type}设计研究报告`
  - `{space_type}技术实施方案`

说明 `space_type` 已被用于结果层命名，而不仅是前期分类。

#### `intelligent_project_analyzer/workflow/nodes/execution_nodes.py`

会读取 `project_type` 并通过 `OntologyLoader.get_layered_ontology()` 为后续执行层注入相应本体维度。

---

### 3.6 辅助相关组件

以下文件虽然不是主分类器，但都与“空间分类/空间类型”强相关：

#### `intelligent_project_analyzer/services/change_intent_detector.py`

用途：

- 使用“空间类型关键词”判断用户是否在表达空间变更意图
- 命中后归入 `SPATIAL_ZONE`

#### `intelligent_project_analyzer/services/core_task_decomposer.py`

用途：

- 使用 `space_type_keywords`
- 生成如“某类空间功能规划”“某类空间设计框架”任务

#### `intelligent_project_analyzer/services/few_shot_selector_v2.py`

用途：

- 在 few-shot 示例选择时使用 `space_type` 标签
- 控制示例覆盖与相似度

#### `intelligent_project_analyzer/services/project_type_expansion.py`

用途：

- 对项目类型体系进行扩展
- 新增类型并写入扩展注册表

#### `intelligent_project_analyzer/services/type_alias_normalizer.py`

用途：

- 对用户输入中的类型别名做归一化处理
- 作为项目类型检测前的预处理环节

---

## 4. 核心方法梳理

### 4.1 分类检测方法

#### 位于 `services/project_type_detector.py`

- `ProjectTypeDetector.detect()`  
  输入文本，输出 `(project_type, confidence, reason)`

- `ProjectTypeDetector.detect_with_details()`  
  在基础检测结果上补充：
  - `parent_type`
  - `specialty_tag`
  - `secondary_type`
  - `is_ambiguous`

- `detect_project_type()`  
  便捷入口，无匹配时返回默认类型

- `detect_project_type_with_confidence()`  
  返回类型与置信度

### 4.2 类型注册表公共方法

#### 位于 `services/_type_registry.py`

- `get_type_label()`  
  类型 ID → 中文标签

- `get_type_name_en()`  
  类型 ID → 英文检索上下文

- `get_all_type_ids()`  
  获取全部类型 ID

- `normalize_type_id()`  
  旧别名归一化到新 ID

### 4.3 本体方法

#### 位于 `utils/ontology_loader.py`

- `get_ontology_by_type()`  
  按项目类型读取框架

- `get_meta_framework()`  
  读取通用元框架

- `get_layered_ontology()`  
  按项目类型 + 专家角色合并框架，是最核心的方法

- `format_as_prompt()`  
  将本体框架格式化为提示词文本

#### 位于 `services/ontology_service.py`

- `get_all_frameworks()`  
  返回框架概览

- `get_framework_detail()`  
  返回某类项目的完整维度树

- `search_dimensions()`  
  按关键词搜索维度

- `validate_yaml_syntax()`  
  校验 `ontology.yaml`

### 4.4 需求分析链相关方法

#### 位于 `agents/requirements_analyst_agent.py`

- `_infer_project_type()`  
  使用启发式方式对 `structured_data` 推断 `project_type`

#### 位于 `workflow/nodes/requirements_nodes.py`

- `_requirements_analyst_node()`  
  读取需求分析结果，将 `project_type` 写入主状态

---

## 5. 相关文件清单

### 5.1 定义层

- `d:\11-20\langgraph-design\intelligent_project_analyzer\services\_type_registry.py`
- `d:\11-20\langgraph-design\intelligent_project_analyzer\knowledge_base\ontology.yaml`

### 5.2 检测层

- `d:\11-20\langgraph-design\intelligent_project_analyzer\services\project_type_detector.py`
- `d:\11-20\langgraph-design\intelligent_project_analyzer\agents\requirements_analyst_agent.py`

### 5.3 本体与注入层

- `d:\11-20\langgraph-design\intelligent_project_analyzer\utils\ontology_loader.py`
- `d:\11-20\langgraph-design\intelligent_project_analyzer\services\ontology_service.py`
- `d:\11-20\langgraph-design\intelligent_project_analyzer\api\routes\admin_ontology.py`

### 5.4 主流程消费层

- `d:\11-20\langgraph-design\intelligent_project_analyzer\workflow\nodes\requirements_nodes.py`
- `d:\11-20\langgraph-design\intelligent_project_analyzer\workflow\nodes\execution_nodes.py`
- `d:\11-20\langgraph-design\intelligent_project_analyzer\workflow\nodes\deliverable_id_generator_node.py`
- `d:\11-20\langgraph-design\intelligent_project_analyzer\core\state.py`

### 5.5 交互消费层

- `d:\11-20\langgraph-design\intelligent_project_analyzer\interaction\questionnaire\generators.py`
- `d:\11-20\langgraph-design\intelligent_project_analyzer\interaction\questionnaire\context.py`
- `d:\11-20\langgraph-design\intelligent_project_analyzer\interaction\questionnaire\llm_generator.py`
- `d:\11-20\langgraph-design\intelligent_project_analyzer\interaction\nodes\progressive_questionnaire.py`
- `d:\11-20\langgraph-design\intelligent_project_analyzer\interaction\nodes\questionnaire_summary.py`

### 5.6 辅助相关层

- `d:\11-20\langgraph-design\intelligent_project_analyzer\services\change_intent_detector.py`
- `d:\11-20\langgraph-design\intelligent_project_analyzer\services\core_task_decomposer.py`
- `d:\11-20\langgraph-design\intelligent_project_analyzer\services\few_shot_selector_v2.py`
- `d:\11-20\langgraph-design\intelligent_project_analyzer\services\project_type_expansion.py`
- `d:\11-20\langgraph-design\intelligent_project_analyzer\services\type_alias_normalizer.py`

---

## 6. 数据流与调用关系

### 6.1 主数据流

```text
用户输入
  → project_type_detector / requirements_analyst_agent
  → 得到 project_type / physical_context / space_type
  → requirements_nodes 写入主状态
  → questionnaire / progressive_questionnaire / summary 消费
  → execution_nodes 根据 project_type 注入 ontology
  → deliverable_id_generator_node 根据 physical_context.space_type 生成交付命名
```

### 6.2 分层调用关系

1. **定义层**  
   `_type_registry.py` 定义“有哪些类型”。

2. **检测层**  
   `project_type_detector.py` 根据文本从注册表中识别类型。

3. **分析层**  
   `requirements_analyst_agent.py` / `requirements_nodes.py` 把类型结果放入主状态。

4. **语义注入层**  
   `ontology_loader.py` 根据 `project_type` 和专家角色组合分析维度。

5. **交互层**  
   问卷生成器和渐进式问卷根据 `project_type` 提问“空间类型 / 功能分区”。

6. **执行与结果层**  
   交付生成节点根据 `space_type` 调整交付命名和上下文。

---

## 7. 历史与冻结约束

### 7.1 已废弃内容

根据 `CLAUDE.md`，以下内容必须注意：

- `progressive_step1_core_task` 已废弃
- 不能再把旧 Step1 当作当前“空间分类”的主入口
- `progressive_questionnaire.py` 中已删除 Step1 运行时代码

因此，当前主路径中的空间分类入口应理解为：

- `requirements_analyst`
- `project_type`
- `ontology` 注入
- 问卷与需求洞察的后续消费

而不是旧的 Step1 任务梳理链。

### 7.2 新主线迁移方向

根据 `docs/plans/ANALYSIS_STORM_REFACTOR_IMPLEMENTATION_PLAN.md`，新主线正在向对象协议聚合：

- `TaskFramework`
- `IntentSignal`
- `GapProfile`
- `PreferenceRadarProfile`
- `RadarRoutingDecision`
- `RequirementsInsight`

这意味着：

- 旧的 `project_type` / `space_type` / `physical_context` / 零散状态字段仍然在使用
- 但未来“空间分类”能力将更偏向聚合到正式对象协议中
- 尤其 `extracted_spatial_zones` 这类字段，可能会成为未来结构化空间语义的更直接承载体

---

## 8. 当前理解下的归纳结论

可以将系统中“空间分类”相关能力概括为以下几类核心中心：

### 8.1 分类定义中心

- `services/_type_registry.py`

### 8.2 分类检测中心

- `services/project_type_detector.py`

### 8.3 语义框架中心

- `knowledge_base/ontology.yaml`
- `utils/ontology_loader.py`

### 8.4 工作流入口中心

- `agents/requirements_analyst_agent.py`
- `workflow/nodes/requirements_nodes.py`

### 8.5 交互消费中心

- `interaction/questionnaire/generators.py`
- `interaction/nodes/progressive_questionnaire.py`

### 8.6 结果消费中心

- `workflow/nodes/deliverable_id_generator_node.py`

### 8.7 状态承载中心

- `core/state.py`

因此，“空间分类”在现有系统中不是一个点，而是一条链：

**分类定义 → 类型检测 → 状态写入 → 本体注入 → 问卷消费 → 交付消费**

---

## 9. 后续建议

如果后续继续深入，可按两个方向扩展：

### 9.1 调用链文档化

建议补一份“空间分类数据流图”，重点追踪：

- `project_type_detector`
- `requirements_analyst_agent`
- `requirements_nodes`
- `progressive_questionnaire`
- `questionnaire_summary`
- `deliverable_id_generator_node`

### 9.2 协议映射文档化

建议补一份“旧字段 → 新对象协议”的映射表，重点围绕：

- `project_type`
- `space_type`
- `physical_context`
- `project_classification`
- `extracted_spatial_zones`
- `TaskFramework`
- `RequirementsInsight`

这样更利于后续把“空间分类”从零散字段体系升级为正式对象协议。

---

## 10. 快速关联索引（按“文件 → 代码符号”定位）

> 本节用于快速跳转代码，不替代上文详细梳理。

### 10.1 分类定义与检测

- `intelligent_project_analyzer/services/_type_registry.py`
  - `PROJECT_TYPE_REGISTRY`
  - `LEGACY_TYPE_ALIASES`
  - `PARENT_TYPE_MAP`
  - `SPECIALTY_TAG_MAP`
- `intelligent_project_analyzer/services/project_type_detector.py`
  - `ProjectTypeDetector.detect()`
  - `ProjectTypeDetector.detect_with_details()`

### 10.2 本体语义与加载

- `intelligent_project_analyzer/knowledge_base/ontology.yaml`
  - `ontology_frameworks`
  - `expert_extensions`
- `intelligent_project_analyzer/utils/ontology_loader.py`
  - `get_layered_ontology()`
  - `get_ontology_by_type()`

### 10.3 主链写入与状态承载

- `intelligent_project_analyzer/workflow/nodes/requirements_nodes.py`
  - `_requirements_analyst_node()`（写入 `project_type` / `space_classification` / `project_classification` / `extracted_spatial_zones`）
- `intelligent_project_analyzer/core/state.py`
  - `project_type`
  - `project_classification`
  - `space_classification`
  - `extracted_spatial_zones`

### 10.4 交互消费

- `intelligent_project_analyzer/interaction/questionnaire/generators.py`
  - `office_space_types`
  - “空间类型配置决定了功能分区”相关问题模板
- `intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py`
  - 基于 `project_type` 组织渐进问卷分支

### 10.5 执行与交付消费

- `intelligent_project_analyzer/workflow/nodes/execution_nodes.py`
  - 依据 `project_type` 注入本体层
- `intelligent_project_analyzer/workflow/nodes/deliverable_id_generator_node.py`
  - 读取 `structured_requirements.physical_context.space_type` 生成交付命名

### 10.6 主链契约对齐（防语义漂移）

- `intelligent_project_analyzer/workflow/workflow_contract.py`
  - `NODE_TO_STAGE`
  - `NODE_PROGRESS`
  - `is_deprecated_node()`

该索引用于确保“空间分类”讨论始终锚定项目现状代码，而非停留在历史概念名词。

---

## 11. 空间分类系统清单（SPACE_CLASSIFICATION_SYSTEM_INVENTORY）的功能、价值、可解决问题

- **功能**：建立“空间分类能力全链路清单”（定义层→检测层→状态层→交互层→交付层）。
- **价值**：提供单点入口定位分类相关代码，支持重构、排障与评审对齐。
- **能解决什么问题**：
  1. 不知道空间分类到底在哪些模块生效；
  2. 字段命名多、消费点分散，修改容易漏；
  3. 讨论停留在概念层，缺少可验证的代码定位。
