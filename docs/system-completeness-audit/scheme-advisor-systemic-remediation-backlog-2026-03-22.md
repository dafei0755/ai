# 方案高参系统性整改清单

- 生成时间：`2026-06-15T19:30:19`
- 压测样本：190
- 需人工复核：126
- 系统性整改项：8
- 禁止个案硬编码：True

## 原则

- 不把单个案例写成固定规则；只沉淀跨样本成立的机制。
- 先识别空间主轴、项目阶段、核心矛盾，再决定输出深度。
- 专科知识和激活包不能全覆盖时，先走基础空间推理框架；只有专业覆盖不足会影响判断可靠性时才封顶。
- 模型推断只能进入候选和复核，不得自动进入正式 Registry 或知识库。
- 前端只展示人话标签，不暴露内部英文枚举和字段名。

## 基线差异

- 处理策略：`report_only_never_auto_sync`
- 需要人工复核：True

| 字段 | Golden 批注 | 最新压测 |
|---|---:|---:|
| warning_counts.coverage_gap | 110 | 0 |
| warning_counts.knowledge_gap_ticket | 110 | 0 |
| warning_counts.low_classification_confidence | 20 | 0 |
| governance_signal_counts.activation_pack_candidate | 183 | 131 |
| governance_signal_counts.coverage_gap | 0 | 102 |
| governance_signal_counts.knowledge_coverage_watch | 0 | 51 |
| governance_signal_counts.knowledge_gap_ticket | 0 | 102 |

## 治理信号路由

| 信号 | 数量 | 候选类型 | 治理队列 | 允许动作 | 晋级规则 | 验证门槛 |
|---|---:|---|---|---|---|---|
| activation_pack_candidate | 131 | activation_pack_candidate | activation_pack_review | 进入激活包候选池，按频次、商业价值和知识成熟度排期。 | 高频聚类 + 范围定义 + 人工批准 | 正式上线前必须定义适用/不适用边界、最小知识卡和回归样本。 |
| coverage_gap | 102 | registry_boundary_candidate | space_registry_review | 生成空间分类、别名或边界规则候选，不得直接改正式 Registry。 | 候选聚合 + 人工复核 + 190 条回归通过 | 批准前只能影响候选池；批准后必须确认没有挤压既有空间主轴。 |
| knowledge_coverage_watch | 51 | coverage_watch_signal | coverage_watch_pool | 只进入观察池，累计样本和风险，不直接立项建设专科包。 | 达到频次、风险或商业价值阈值后再转候选 | 观察阶段只能影响报告和建设优先级，不得改变运行时事实。 |
| knowledge_gap_ticket | 102 | knowledge_card_candidate | knowledge_asset_review | 生成候选知识卡或知识包缺口，不得进入 runtime recall。 | 证据链完整 + 适用边界明确 + 人工审核批准 | 审核通过前不得被消费链召回；通过后必须登记来源、边界和成熟度。 |

## 整改项

| 优先级 | 模块 | 治理方式 | 风险 | 机制 | 验证方式 | 守门规则 | 证据量 |
|---|---|---|---|---|---|---|---:|
| P0 | SpaceClassificationService | algorithmic_rule | 空间主轴识别偏移会把用户问题导向错误专题。 | 建立空间主轴判定算法：空间载体、使用者身份、经营/家庭/公共目标、阶段和约束分层打分，再输出主类、次类和不确定原因。 | 用 190 条 golden baseline 回归，住宅身份、复合空间、非空间入口不得误入无关类型；低置信必须进入人工复核。 |  | 73 |
| P0 | SchemeAdvisorEntryService | algorithmic_rule | 第一轮响应没有抓住主矛盾，会导致后续追问和方案方向答非所问。 | 先抽取核心矛盾：身份表达、家庭关系、商业效率、文化转译、阶段不确定、硬约束冲突；再生成首轮回应和追问。 | 190 条回归中 core_tension 必须优先反映用户真实目标，不得只按类型模板套话。 |  | 79 |
| P0 | OutputCeilingPolicy | algorithmic_rule | 信息不足或题目不是空间方案时，系统仍可能输出过深、过确定的方案。 | 按信息完整度、空间尺度、项目阶段、知识覆盖和风险约束计算输出封顶等级：完整方案、条件方案、策略框架、决策论证、风险提示。 | 190 条回归中缺面积/图纸/阶段/专业覆盖的样本必须降级输出，不得承诺施工级或确定性方案。 |  | 41 |
| P0 | FrontendHumanLanguageMapping | ui_mapping | 英文内部字段和工程术语暴露给终端用户，降低可信度和理解效率。 | 建立内部枚举到人话标签的映射层：追问标题、选项、风险、空间类型、输出深度都用中文业务语言展示。 | 前端截图和 DOM 文本检查不得出现 heritage value、preservation grade、core_tension 等内部英文字段。 | fail_review: heritage value、preservation grade、structural condition、adaptive reuse program | 190 |
| P1 | ProjectTypeRegistry | registry_governed | 空间分类相对稳定，但新增别名、子类和复合类型不能靠代码里临时补词。 | 把类型别名、父桶、复合规则和反例样本纳入 Registry 候选池；人工审核后才进入正式分类源。 | 新增类型候选只能改变候选池；批准前 190 条回归不得读取未审核 Registry 事实。 |  | 54 |
| P1 | KnowledgeCoverageAndRecall | review_workflow | 知识包无法覆盖所有空间时，系统可能把通用推断当专业结论。 | 按空间主类、核心矛盾和输出深度先走基础空间推理框架；缺专业知识时输出通用方法论、边界声明和候选知识缺口。 | 专业覆盖不足会影响判断可靠性时才给出封顶原因；不得引用未批准卡片，也不得把通用推断包装成专科结论。 |  | 110 |
| P1 | ContextPacketLensActivation | algorithmic_rule | 激活包不能全覆盖所有空间，错误激活会把问题推向错误专业路径。 | 用空间主轴、项目阶段、核心矛盾、硬约束和知识覆盖计算 lens 激活分档，而不是按空间名称硬匹配。 | 复合空间样本必须产生多 lens context_packet；低覆盖样本必须 active_light 或 dormant，不得强行专科化。 |  | 183 |
| P1 | GoldenReviewWorkflow | review_workflow | 模型建议若直接写入 gold，会把低置信推断固化成系统事实。 | 保留 suggested_* 与 gold_expected_* 双轨：机器只给建议，人工确认后 verifier 才能写入 golden 副本。 | suggestions 中 needs_human_decision 必须保留为空 gold；apply 工具不得覆盖原始 golden 基线。 |  | 26 |

## 方法论字段

| 模块 | 通用输入 | 泛化方法 | 反硬编码策略 | 算法验证 |
|---|---|---|---|---|
| SpaceClassificationService | 空间载体；使用者身份；经营/家庭/公共目标；项目阶段；硬约束；知识覆盖等级 | 对输入先做空间主轴分层评分，再输出主类、次类、置信度和不确定原因；新样本只能影响权重和候选池，不能形成单题分支。 | 样本编号只作为证据，不得作为运行时分支条件。 | 190 条模拟问题回归中，空间主轴、复合空间和低置信降级必须稳定；新增候选批准前不得改变正式分类事实。 |
| SchemeAdvisorEntryService | 用户真实目标；身份叙事；经营闭环；家庭关系；文化表达；约束冲突 | 先抽取核心矛盾，再按目标、约束、场景和情绪权重组织首轮回应；追问围绕当前矛盾，而不是固定套用四个标签。 | 样本编号只作为证据，不得作为运行时分支条件。 | golden baseline 中首轮回应必须覆盖真实目标和主矛盾；不得把商业、住宅、文化项目统一套成模板话术。 |
| OutputCeilingPolicy | 信息完整度；空间尺度；项目阶段；知识覆盖等级；风险约束 | 按可判断程度计算输出封顶等级，缺面积、图纸、阶段或专业覆盖时只给条件方案或策略框架。 | 样本编号只作为证据，不得作为运行时分支条件。 | 缺关键参数的样本不得输出施工级结论；风险冲突样本必须先声明前提和边界。 |
| FrontendHumanLanguageMapping | 内部字段名；终端用户界面位置；业务语义；管理后台可见范围 | 建立内部枚举到人话标签的统一映射层，终端界面只显示中文业务语义，技术字段只允许在管理后台详情中出现。 | 样本编号只作为证据，不得作为运行时分支条件。 | 用户可见文本守卫脚本必须阻断英文内部字段和工程术语；新增字段必须先登记中文标签。 |
| ProjectTypeRegistry | 类型别名；父类；复合类型线索；反例样本；审核状态 | 把空间分类作为相对稳定 Registry 治理对象，别名和边界进入候选池，经人工复核后才进入正式分类源。 | 样本编号只作为证据，不得作为运行时分支条件。 | 未审核候选不得参与运行时分类；批准新增类型后必须跑 190 条回归，确认没有挤压既有类型。 |
| KnowledgeCoverageAndRecall | 空间主类；核心矛盾；知识覆盖等级；输出深度；已批准知识卡成熟度 | 知识覆盖不足时先走基础空间推理框架，只输出通用方法论、边界声明和候选缺口；不得把通用推理包装成专科结论。 | 样本编号只作为证据，不得作为运行时分支条件。 | 没有 approved card 或专科包时不得召回未审知识；覆盖不足必须生成知识缺口候选或观察信号。 |
| ContextPacketLensActivation | 空间主轴；项目阶段；核心矛盾；硬约束；知识覆盖等级；可用卡片成熟度 | 按输入特征计算 lens 激活分档，复合空间允许多 lens 协同，低覆盖场景降为 active_light 或 dormant。 | 样本编号只作为证据，不得作为运行时分支条件。 | 复合空间样本必须产生多 lens context_packet；低覆盖样本不得强行专科化。 |
| GoldenReviewWorkflow | 模型建议；golden 原值；置信度；人工裁决状态；漂移差异 | 保持 suggested 与 gold 双轨，模型只生成建议；人工批准后才写入 golden 副本和后续回归基线。 | 样本编号只作为证据，不得作为运行时分支条件。 | apply 工具不得覆盖原始 golden；baseline drift 只报告差异，不自动同步。 |
