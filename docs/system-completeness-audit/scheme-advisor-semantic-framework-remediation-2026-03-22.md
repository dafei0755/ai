# 方案高参语义底座压力测试与整改清单

生成日期：2026-06-14

最近更新：2026-06-15

来源问题集：`sf/2026.3.22/模拟问题集合.txt`

## 本轮结论

本轮不是按单题补丁处理，而是把问题归纳为“入口语义底座是否能防止模板外溢”。核心判断如下：

- 激活包、知识包无法覆盖所有空间类型，不能作为系统正确性的唯一前提。
- 空间分类、语义轴、追问生成必须先保证“不跑偏、不套错模板、不暴露内部术语”。
- 专科知识只负责增强深度；没有专科知识时，应降级到通用空间方法论和诚实封顶。

## 当前验证结果

| 指标 | 修复前 | 修复后 |
|---|---:|---:|
| 问题总数 | 190 | 190 |
| 通过 | 184 | 190 |
| 阻断失败 | 6 | 0 |
| 警告项问题 | 162 | 186 |

阻断失败已经归零。警告项上升，是因为评测更严格地识别出“知识覆盖、激活包、低置信分类”缺口；这些属于后续治理清单，不代表入口流程跑偏。

### 最新压力回归（2026-06-15）

本轮继续坚持“系统性修复，不按单题硬编码”。针对低置信样本中“住宅内部家庭关系/隐私边界被儿童或公共服务弱词误吸”的问题，新增可复用的家庭隐私与共居边界语义轴，并把该类问题路由到住宅共居冲突主轴。

| 指标 | 修复前一轮 | 最新结果 |
|---|---:|---:|
| 问题总数 | 190 | 190 |
| 通过 | 190 | 190 |
| 阻断失败 | 0 | 0 |
| 带警告问题 | 182 | 182 |
| `low_classification_confidence` | 19 | 18 |
| `coverage_gap` | 108 | 107 |
| `knowledge_gap_ticket` | 108 | 107 |
| `activation_pack_candidate` | 181 | 181 |

本轮变化不追求指标“好看”，而是修正一类真实系统误差：含有“孩子/安全”的住宅家庭问题，不应自动进入儿童公共服务或医疗康养路径；只有公共机构、学校、托育、社区中心等明确公共服务语境，才进入公共服务轴。

## 已修复的机制问题

### 1. 茶饮模板外溢

问题表现：

- 山地住宅区会所、国际贸易会客中心、艺术驻留中心、美丽乡村示范村等非茶饮问题，被入口层误套“茶饮小店 / 出杯 / 门头菜单 / 高周转”模板。

根因：

- 检测器本身部分题目能识别为非茶饮，但入口服务里的茶饮适用性判断过宽。
- “座位”等通用词被当成茶饮运营词；“一座位于”也会误触发“座位”。

修复方向：

- 收紧茶饮入口触发条件。
- 弱关键词不能单独触发茶饮增强链。
- 只有明确茶饮词、饮品门店强信号或强运营组合，才进入茶饮包。

### 2. 咖啡近邻被茶饮话术吞掉

问题表现：

- 精品咖啡店被识别为 `coffee_shop`，但用户侧回复仍显示“茶饮小店”和“成立路径”。

根因：

- 茶饮和咖啡共用 beverage 入口兜底，但文案写死为茶饮。

修复方向：

- 增加咖啡 profile 判断。
- 咖啡入口使用“精品咖啡店、短停留、克制停留、品牌质感、高租金坪效”等语言。
- 饮品通用兜底改为“饮品小店”，不默认写成茶饮。

### 3. 固定内部步骤名暴露

问题表现：

- 用户侧出现“成立路径、硬约束、取舍边界”等内部流程名。

修复方向：

- 入口可继续保留内部判断结构，但用户侧追问要改成人话问题。
- 评测器把这些固定词列为阻断项。

### 4. 语义轴规则双源漂移

问题表现：

- 压力测试评测器和运行时入口各维护一套语义轴规则，后续容易漂移。

修复方向：

- 新增共享语义轴模块。
- 压力测试器保留兼容函数名，但实际调用共享模块。

追加整改（2026-06-14）：

- 已新增 `intelligent_project_analyzer/config/registries/scheme_advisor_semantic_axes.yaml`，把空间领域、输入意图、主体画像、成立动因、场地资源、生命周期、关键约束和 guardrails 外部化。
- `scheme_advisor_semantic_axes.py` 只保留 registry 加载、归一化、匹配和评测逻辑，不再维护 `AXIS_RULES` / `AXIS_LABELS` 这类代码内大表。
- `scheme_advisor_pressure_runner.py` 已移除残留的内联语义轴大表，避免压测器和运行时出现第二真相源。
- 已新增 fixture 测试，证明语义轴可以从外部治理文件加载。

### 5. 住宅家庭关系被儿童/公共服务弱词误吸

问题表现：

- 再婚家庭、青春期子女、无血缘同住、绝对隐私、心理安全边界等住宅内部关系题，被“孩子/安全”等弱词拉向 `children_family` 或 `public_service_inclusive_reuse`。
- 这类问题的主轴不是儿童公共服务，而是居住关系、隐私边界、公共交流和冲突缓冲。

根因：

- 项目类型检测器中“孩子/安全”是儿童相关弱信号，但缺少更高层的家庭关系边界语义轴来纠偏。
- 空间主轴中 `residential_conflict_lifestyle_balance` 只覆盖“共居/夫妻/公寓 + 动静分区/隔音”等窄场景，不能覆盖再婚家庭、青春期、无血缘、心理安全边界等真实住宅关系冲突。
- 住宅身份/传承轴优先级过高时，会抢走更具体的家庭冲突边界题。

修复方向：

- 新增 `family_privacy_boundary` 语义轴，覆盖再婚家庭、无血缘、青春期、公共交流区、绝对隐私、独立性、冲突缓冲、心理安全边界等跨题型信号。
- 扩展 `residential_conflict_lifestyle_balance` 的 decision focus，把它从“动静分区”升级为“隐私边界、动静分区与日常共处”。
- 在低置信且被儿童/康养/公共服务弱词误吸时，若同时满足住宅场域、家庭关系、隐私边界三类信号，保守回落到 `personal_residential`。
- 该规则不把“家庭”作为大范围硬关键词写入项目类型 Registry，避免把所有家庭词都误判成住宅。

验证结果：

- 再婚家庭/青春期隐私边界样本从 `children_family + public_service_inclusive_reuse + 0.32` 修正为 `personal_residential + residential_conflict_lifestyle_balance + 0.62`。
- 深圳湾一代创业者海景别墅样本仍保持 `personal_residential + private_residential_identity_legacy + 0.9`，未被家庭冲突规则误伤。
- 相关回归通过；完整 190 条压力测试仍为 190/190 通过。

### 最终压力回归与算法约束（2026-06-15 14:11）

本轮新增验证重点不是“多补几个案例”，而是确认入口链路已经具备更广泛适用的判断框架：

- 运行时不允许用样本编号、单个项目名称或单个空间词形成个案分支。
- 空间分类先判断稳定空间主轴，再叠加使用者身份、经营目标、家庭关系、场地资源、生命周期和硬约束。
- 激活包和知识包只提供专业增强；没有覆盖时，系统必须使用基础空间方法论，并触发知识覆盖封顶。
- “动线”是通用空间词，不能单独推导为商业运营效率；只有同时出现商业载体、投资回收、租金压力、交通节点、客流或成交转化等信号，才进入商业效率轴。
- 前端和终端回复不得暴露英文枚举、蛇形字段、ontology、context packet、activation pack 等内部工程词。
- 用户可见标签必须统一走 `scheme_advisor_public_labels.yaml` 和 `public_label()`；入口服务、上下文服务、语义轴服务不得各自维护本地翻译表，避免第二真相源。
- 终端用户文案配置也必须过同一条守卫线。`scheme_advisor_intelligence.yaml`、`scheme_advisor_entry_copy.yaml`、`scheme_advisor_version_tiers.yaml` 不得保留“成立路径 / 硬约束 / 取舍边界 / 选择判断路径”等固定流程词，避免 fallback 或旧茶饮文案重新暴露内部话术。
- 饮品类专科入口的首答、首轮卡片、二轮卡片、阶段收束和版本引导均已改为配置规则选择。服务代码只解释 `entry_scene_tags`、profile 条件、信号词和默认规则，不再固定把所有饮品问题压到同一套追问或收束话术。
- 非饮品通用项目的首答、首轮追问、阶段收束和版本引导已开始接入语义轴配置规则。服务代码只解释 `space_axis_id`、`project_type`、profile 条件、卡片路径和模板变量；住宅身份、商业运营、公共更新、办公协同、文化叙事等稳定主轴由 `scheme_advisor_entry_copy.yaml` 的 `generic_project.*_selection_rules` 选择，不再只能退回同一套通用项目收束或固定追问话术。

最新服务层压力测试结果：

| 指标 | 结果 |
|---|---:|
| 问题总数 | 190 |
| 通过 | 190 |
| 阻断失败 | 0 |
| 用户文案警告 | 0 |
| 治理信号样本 | 183 |
| `coverage_gap` | 102 |
| `knowledge_gap_ticket` | 102 |
| `knowledge_coverage_watch` | 51 |
| `activation_pack_candidate` | 131 |

这组结果的含义：

- 190 题不是运行时硬编码依据，而是持续回归基准。
- 治理信号不是失败，而是知识建设队列：哪些空间需要补 Registry，哪些需要补知识包，哪些只进入观察池。
- 当前系统可以在知识不全时给出条件级设计框架，但不能把通用判断伪装成专科结论。
- 后续任何新增空间分类、语义轴、激活包、知识卡，都必须先进入候选和人工复核，再通过 190 题回归后进入正式运行链。

## 当前仍需整改的系统清单

### P0 已完成第一步：空间分类主干稳定化

目标：

- 把相对稳定的空间分类 Registry 固定下来，避免入口靠临时关键词误判。

已完成：

- 建立并校验以下可治理 Registry：
  - `config/registries/founding_type_registry.yaml`
  - `config/registries/subdomain_registry.yaml`
  - `config/registries/spatial_extent_registry.yaml`
  - `config/registries/lifecycle_registry.yaml`
  - `config/registries/spatial_layer_registry.yaml`
- 新增 Registry 外部化测试，要求上述稳定分类骨架必须存在于 YAML，而不是只藏在 Python 兜底表里。
- 当前审计结果显示 founding type、subdomain、spatial extent、lifecycle、spatial layer 均已与运行时内置口径保持一致。

仍需后续治理：

- 将空间主类、大类、近邻类、复合类型、未知类型拆清楚。
- 对“会所、体验馆、展厅、品牌中心、会客中心、社区、乡村、康养、商业”等高歧义词建立边界规则。
- 分类输出必须包含主类型、辅助类型、置信度、为什么不能进入某些专科包。
- Registry 只解决“稳定分类骨架”，不等于知识包、激活包已经覆盖所有空间；未知或弱覆盖空间仍必须触发知识覆盖封顶。

### P1 已完成：语义轴从代码规则迁移到可治理 Registry

目标：

- 语义轴具备算法框架，但词表、标签、说明和 guardrails 必须由 YAML/Registry 治理，而不是长期写死在服务代码里。

已完成：

- 建立 `config/registries/scheme_advisor_semantic_axes.yaml`。
- 语义轴包括：空间领域、输入意图、用户身份、项目驱动力、场地资源、生命周期、硬约束。
- guardrails 包括：茶饮/商业模板外溢、固定内部步骤名、英文蛇形字段、错误领域引用、核心主体与核心驱动力缺失。
- 服务层新增 `load_semantic_axis_registry()`，可从默认 registry 或测试 fixture 加载。

仍需后续接入：

- 管理后台只展示可治理项，不展示内部推断细节。
- 语义轴新增、停用、合并、别名补充应进入审核队列，不能直接由运行时自动写入。

### P1 已完成第一步：知识覆盖封顶机制

目标：

- 没有专科激活包时，不应错误套用已有专科；应诚实降级。

已完成：

- 区分三种封顶：
  - 信息缺口封顶：用户资料不足。
  - 知识覆盖封顶：没有对应专科知识包。
  - 卡片成熟度封顶：有知识但证据强度不足。
- `context_packet.knowledge_binding.coverage_ceiling` 已声明知识覆盖等级：
  - `specialist_covered`：可进入专科级判断。
  - `partial_specialist`：只能给条件级判断。
  - `general_method_only`：只能给通用空间方法论和策略级判断。
- `CapabilityPlanService` 已读取 coverage ceiling；当没有可用专科知识时，整体能力状态降级为 `degraded`，成熟度封顶为 `strategy_framework`。
- 输出约束已写入 `allowed_outputs` / `forbidden_outputs`，明确不能给精确施工尺寸、确定设备型号、保证性经营结论，也不能冒充专科知识包结论。
- 通用项目入口首答模板已接入 `coverage_note`。服务层从 `context_packet.knowledge_binding.coverage_ceiling.user_visible_note` 读取用户可见提示；当知识覆盖不足时，首答会说明“只能先给通用方法论和策略级判断 / 条件级判断”，但不会暴露 `coverage_ceiling`、`general_method_only` 等内部字段。

仍需后续治理：

- 卡片成熟度封顶还需要和 Approved Knowledge Cards 的 evidence/maturity 字段进一步打通。
- 前端应把 coverage ceiling 翻译为用户能理解的话，不展示内部字段名。

### P1：追问卡片语义化

目标：

- 追问不是固定四步，而是由语义轴生成。

待做：

- 住宅问家庭关系、私密边界、主人画像。
- 会所问会员关系、社交节奏、情绪支持。
- 展陈问叙事线、参观路径、信息层级。
- 商业问成交理由、停留节奏、投入优先级。
- 康养问安全边界、照护关系、情绪修复。

已完成第一步：

- 第一轮追问页已按主语义张力生成，不再展示“成立路径 / 硬约束 / 取舍边界 / 选择判断路径”等固定内部标题。
- 第二轮追问标题已从统一“最后确认优先级”改为按当前主轴命名，例如“身份与精神表达”“商业成立与回报”等，不同问题不再共用同一标题。
- 新增回归测试要求深圳湾创业者住宅和地铁小铺的第二轮追问必须呈现不同主轴，避免用通用模板伪装为智能判断。
- 压力测试 runner 已从只检查第一轮扩展为推进到第二轮，逐条结果会记录“第二轮追问”摘要，用于发现固定模板复发、内部术语泄漏和第二轮语义跑偏。
- 老码头、城市公共客厅、城市记忆、滨水界面重构等词已纳入更新再生语境识别，避免把合理的城市更新判断误报为跑偏。
- 新增“多场景切换”语义轴，用于覆盖居住、拍摄、派对、展示、可移动家具、模块化灯光等可变空间问题，避免媒体/生活复合空间退回“当前项目主轴”兜底。
- 追问选项生成已区分“空间大类”和“真实判断边界”：住宅、住宿、办公、展陈、技术专项等大类只作为兜底，不在已有身份、运营、景观、隐私等具体张力时直接作为用户选项。
- 住宿度假类追问标题已改为“住客、公共空间和运营”这类用户能理解的真实问题，避免抽象空间分类词替代入口判断。
- 压力测试 summary 已新增 `round_2_generic_fallback_count`，Markdown 报告顶部会显示“第二轮通用兜底残留”。命令行退出码也已接入该门槛：即使阻断失败为 0，只要第二轮仍退回“当前项目主轴 / 最后确认优先级 / 最不能跑偏”等模板兜底，压测命令也会失败。
- 已清理“深圳湾 / 第一代创业者”样本级入口补丁：服务层不再保留 `private_founder_residential_entry`、`_build_private_founder_residence_first_confidence` 等专项模板，创始人住宅类问题统一走语义轴、Registry 和通用追问生成。
- 已清理新项目重启识别中的旧茶饮样本词密度：不再依赖“深圳 / 地铁 / 35平 / 茶”等旧测试词，而是使用设计任务书意图、通用空间载体、数值锚点和语义轴密度判断是否另起新项目。
- 已清理方法论入口的服务内私有正则：不再用“马斯克 / 哲学 / 思维方式”等零散词判断自由讨论，而是统一读取 `scheme_advisor_semantic_axes.yaml` 中的 `problem_modes`，并用“无具体项目锚点”防止真实项目被误降级为方法论闲聊。
- 已清理入口总门控的服务内项目词表：不再用“设计 / 项目 / 店 / 餐厅 / 空间”等大表决定是否进入方案高参入口，而是统一使用具体项目锚点、语义轴密度和输入意图。Registry 已能识别的公共教育、图书馆、学习路径等问题不会因缺少旧词表命中而被挡在入口外。
- 已把问题模式、输入意图和语义轴密度收敛到 `scheme_advisor_semantic_axes.py` 共享函数，入口服务不再维护 `methodology_modes` / `actionable_intents` / `project_intents` 这类语义 ID 白名单。
- 新项目重启判断和具体项目锚点判断也已改用共享 `semantic_axis_density()`，入口服务不再手动枚举 `space_domains`、`founding_drivers`、`site_resources` 等语义轴名称计算密度，避免新增语义轴时局部入口判断漂移。
- 创始人私宅、商业回本/交通节点、公共学习等“共现推断”已从 Python 词表迁入 `scheme_advisor_semantic_axes.yaml` 的 `inference_rules`。代码只解释 `all / any / any_terms / all_terms` 这类通用条件，不再把具体业务信号写死在共享语义轴模块里。
- 用户可见标签已从入口服务本地 `labels = {}` 迁入 `scheme_advisor_public_labels.yaml`。`SchemeAdvisorEntryService` 只调用统一 `public_label()`，知识模块名、空间对象、风险选项等不再各自维护翻译表。
- 终端用户文案配置已完成固定流程词清理：旧 fallback 配置中的“成立路径 / 硬约束 / 取舍边界”改为“先看项目靠什么成立 / 先看哪些条件不能含糊 / 先看最不能牺牲什么”；茶饮入口配置中的“回本成立路径”改为“回本支撑逻辑 / 先看回本靠什么撑住”；版本档位中的“硬约束”改为“关键边界 / 不能含糊的条件”。
- 终端用户文案守卫已继续扩展到运行时回复：`风险阈值 / 预算押注 / 决策级变量` 不再允许出现在首答、第二轮回复、卡片标题或页面标题中。服务 fallback、配置文案和压力测试 `_INTERNAL_TERMS` 已同步纳入该门禁，避免“服务层 JSON 通过但用户看到内部流程词”。
- 标准茶饮/奶茶入口的第一轮、第二轮追问卡片已改为读取 `scheme_advisor_entry_copy.yaml`，服务层通过 `_configured_card()` 装配并标记 `source = entry_copy.configured`。旧的服务内标准茶饮卡片文案块已移除，避免“先看能不能回本 / 这家店最像哪种打法 / 最不能接受哪种失败 / 这份建议需要做到多深”等旧话术绕过配置治理。
- 饮品入口的硬条件卡、运营诊断卡、上下文化第一轮卡也已迁入 `scheme_advisor_entry_copy.yaml`。服务层只负责根据 `entry_scene_tags` 和咖啡/饮品类型选择配置节点：`hard_boundary_card`、`operational_diagnostic_card`、`contextual_round_1_cards.coffee/default`，不再保留整块用户可见追问卡片正文。
- 饮品入口的第一信心回复也已迁入 `scheme_advisor_entry_copy.yaml` 的 `tea_retail_space.first_confidence_variants`。服务层只负责选择变体键：`coffee`、`hard_boundary`、`operational_diagnostic`、`transit_payback`、`community`、`office`、`campus`、`tourism`、`competition`、`payback`、`transit`、`default`，不再保留整块用户可见首轮判断正文。
- 饮品入口“标签到第一信心回复变体”的优先级也已迁入 `scheme_advisor_entry_copy.yaml` 的 `tea_retail_space.first_confidence_variant_rules`。服务层只解释 `tags_all`、`tags_any`、`profile_contains`、`profile_contains_any`、`profile_equals` 和 `default` 这类通用条件，不再维护 `coffee / hard_boundary / transit_payback / payback` 等业务顺序分支。
- 饮品入口“标签到第一轮追问卡片类型”的选择规则也已迁入 `scheme_advisor_entry_copy.yaml` 的 `tea_retail_space.round_1_card_selection_rules`。服务层只解释 `card_path`、`tags_all`、`tags_any`、`profile_contains`、`profile_contains_any`、`profile_equals` 和 `default` 这类通用条件，不再维护硬条件卡、运营诊断卡、咖啡上下文卡、交通回本卡的业务优先级分支。
- 饮品入口的阶段收束和版本引导也已迁入 `scheme_advisor_entry_copy.yaml`。服务层通过 `stage_conclusion_selection_rules`、`version_intro_selection_rules`、`signals` 和 `directory_focus` 解释配置规则，不再在 Python 中维护硬条件、运营诊断、咖啡等业务顺序分支。
- 通用项目入口的首答、首轮追问、阶段收束和版本引导也已接入 `scheme_advisor_entry_copy.yaml`。服务层通过 `generic_project.first_confidence_selection_rules`、`generic_project.round_1_card_selection_rules`、`generic_project.stage_conclusion_selection_rules`、`generic_project.version_intro_selection_rules` 和 `space_axis_id` 匹配稳定空间主轴；住宅身份、商业运营、公共更新、办公协同、文化叙事等由配置模板和配置卡片承接，代码只提供通用模板/卡片解释器与变量。首答模板可通过 `{coverage_note}` 引用知识覆盖封顶的人话提示，确保“知识不全时不装懂”的原则进入用户首屏。
- 压力测试输出中的空间主轴已接入注册表门禁：`space_axis_counts` 里出现的每个 `space_axis_id` 必须存在于 `space_axis_registry.yaml`，且必须能通过 `scheme_advisor_public_labels.yaml` / `public_label()` 转成用户可见中文。新增 `methodology_not_project` 作为稳定的方法论讨论主轴，避免方法论问题被当成未知空间，也避免报告和前端暴露机器 key。

当前验收：

- `tests/services/test_scheme_advisor_pressure_semantic_axes.py` 覆盖第二轮追问摘要、Markdown 报告展示、老码头公共再生语境，以及压力测试空间主轴的注册表覆盖和中文标签门禁。
- `sf/2026.3.22/模拟问题集合.txt` 190 条压力测试在推进到第二轮后为 190/190 通过，0 失败、0 警告，第二轮“当前项目主轴”兜底残留为 0。
- 运行时用户文案新增抽样守卫：深圳湾创始人海景别墅、方法论类问题的首答、第二轮回复和卡片标题均不得出现“风险阈值 / 预算押注 / 决策级变量”。
- 本轮回归覆盖 `tests/services/test_scheme_advisor_pressure_semantic_axes.py`、`tests/services/test_scheme_advisor_systemic_remediation_backlog.py`、`tests/services/test_scheme_advisor_p0_intelligence_guardrails.py`，合计 90 个相关服务测试通过。
- `scripts/check_terminal_user_copy_guardrails.py` 用户可见文案守卫通过，当前禁词 19 个，违规数为 0。

### P2：治理信号转化为建设队列

当前治理信号：

- `coverage_gap`
- `knowledge_gap_ticket`
- `knowledge_coverage_watch`
- `activation_pack_candidate`

治理边界：

- 不把这些当阻断失败，也不把它们直接写成运行时事实。
- 按出现频率、商业价值、空间稳定性和知识成熟度聚合成知识包、激活包、Registry、边界样本的建设优先级。
- `activation_pack_candidate` 只代表“值得进入候选池”，不代表已经有正式激活包。
- `knowledge_coverage_watch` 代表“基础框架可服务，但暂不适合直接建设专科包”，需要继续观察样本密度。

已完成：

- 系统性整改清单已新增 `governance_signal_routing`，把最新压测信号从“统计数字”升级为治理路由：
  - `coverage_gap` → `space_registry_review`，生成空间分类、别名或边界规则候选，不能直接改正式 Registry。
  - `knowledge_gap_ticket` → `knowledge_asset_review`，生成候选知识卡或知识包缺口，审核通过前不得进入 runtime recall。
  - `activation_pack_candidate` → `activation_pack_review`，进入激活包候选池，必须按频次、商业价值、知识成熟度和人工复核排期。
  - `knowledge_coverage_watch` → `coverage_watch_pool`，只进入观察池，累计样本和风险，不直接立项建设专科包。
- `governance_signal_routing` 的每个路由都显式带有 `must_not_auto_promote = true`、候选类型、审核队列、允许动作、晋级规则和验证门槛。
- 新增/刷新压测优化待办清单：
  - `docs/system-completeness-audit/scheme-advisor-pressure-optimization-backlog-2026-03-22.md`
  - `docs/system-completeness-audit/scheme-advisor-pressure-optimization-backlog-2026-03-22.json`
- 新增/刷新系统性整改清单：
  - `docs/system-completeness-audit/scheme-advisor-systemic-remediation-backlog-2026-03-22.md`
  - `docs/system-completeness-audit/scheme-advisor-systemic-remediation-backlog-2026-03-22.json`
  - `docs/system-completeness-audit/scheme-advisor-systemic-remediation-backlog-2026-03-22.csv`
- 最新服务层聚合结果：190 题中 183 题带治理信号，其中 `coverage_gap` 102、`knowledge_gap_ticket` 102、`knowledge_coverage_watch` 51、`activation_pack_candidate` 131。四类信号均已有治理队列，不会自动写入正式 Registry、知识库或激活包。

## 回归要求

以后入口、空间分类、激活包、知识包、context packet 任一链路改动后，必须至少跑：

```powershell
pytest tests/services/test_scheme_advisor_pressure_semantic_axes.py -q
python -m intelligent_project_analyzer.services.scheme_advisor_pressure_runner --input "sf\2026.3.22\模拟问题集合.txt" --output "docs\system-completeness-audit\scheme-advisor-pressure-test-2026-03-22.md" --json-output "docs\system-completeness-audit\scheme-advisor-pressure-test-2026-03-22.json"
```

验收标准：

- 阻断失败必须为 0。
- 第二轮通用兜底残留必须为 0。
- 非茶饮空间不得出现茶饮模板。
- 咖啡不得显示成茶饮。
- 用户侧不得出现英文蛇形字段或内部步骤名。
- 警告项必须进入整改队列，不得悄悄忽略。
