# 需求重构阶段算法优化专题

版本：v1.28  
日期：2026-06-19  
定位：方案高参需求重构阶段的算法机制评估与优化思路  
范围：讨论机制、算法链路、LLM 介入方式、质量治理，并记录首轮实施与验收结果  
修订说明：v1.28 在 v1.27 基础上，补齐具体项目锚点优先级：品牌体验店、品牌空间、历史街区这类具体项目不会被“转译 / 给出建议”泛词误挡在需求重构之外。

---

## 0. 核心结论

需求重构阶段当前的问题，不是“没有算法”，也不是“LLM 完全没有介入”，而是：

> 已有算法主要在前半段生成上下文，但最终面向用户的需求重构输出仍被压缩成单一规则蓝图或单一 archetype 模板，导致多轴语义判断、候选解释、知识覆盖边界和 LLM 综合判断没有形成同一个输出面。

因此，最优方向不是继续补单题规则，也不是让 LLM 完全接管流程，而是把需求重构阶段重构为“融合优先”的单产物链路：

```text
入口分诊算法
↓
项目语义理解器
↓
候选解释与主矛盾排序
↓
受控 LLM 综合生成或语义兜底
↓
分级质量门
↓
语义一致性质检
↓
用户可见的唯一综合版本
```

前台不应先展示规则蓝图，再等待 LLM 补充判断。规则、算法、LLM 应在后台合成，最终只给用户一个综合后的需求重构版本。LLM 不可用或超时时，兜底也应来自语义算法包摘要，而不是退回旧模板首屏。

---

## 1. 问题背景

在需求重构阶段，用户输入往往不是一个清晰的设计任务，而是一组混合线索：

- 空间载体：访客中心、厨房、实验室、民居、店铺、展厅等。
- 功能组合：展示、教育、餐饮、拍摄、办公、居住、社交等。
- 隐含目标：回本、品牌表达、公共教育、家族传承、文化转译、运营效率等。
- 约束条件：面积、预算、设备、消防、排水、声学、电力、材料、工期等。
- 输出意图：完整方案、概念框架、方法论、竞标策略、命名、技术专项、改造诊断等。

如果系统只靠固定规则蓝图，会出现两个典型问题：

1. **单关键词误判**  
   例如“访客中心 + 咖啡区”被“咖啡”拉向商业餐饮逻辑，错误强调翻台、外带、堂食、出杯效率。

2. **LLM 与规则割裂**  
   如果规则蓝图先出现在前台，LLM 后续判断就只能变成补充或修正，用户体感会变成“先错再改”，而不是“系统一开始就读懂”。

需求重构的产品目标是让用户产生：

> “它把我没说清楚的真实问题说清楚了。”

所以需求重构阶段必须从模板整理升级为算法支撑的语义综合。

---

## 2. 已有算法资产

当前系统已经具备若干与需求重构相关的算法资产，不应另起一套孤立逻辑。

### 2.1 入口分诊算法

相关位置：

- `intelligent_project_analyzer/services/scheme_advisor_entry_service.py`

已有能力：

- 判断用户输入是具体项目、方法论讨论、自由咨询、案例借鉴、资料整理或出域问题。
- 识别具体项目锚点，避免真实项目被“方法论、流程、转译”等泛词误导。
- 基于空间线索、项目意图、数值锚点、业务锚点、媒体空间锚点等判断是否进入方案高参链路。

优化方向：

入口分诊应成为需求重构阶段的第一道权威路由，而不是让需求重构服务再次用一组 `_SPACE_TERMS` 与 `_PROJECT_INTENT_TERMS` 重复判断。

### 2.2 项目语义轴算法

相关位置：

- `intelligent_project_analyzer/services/scheme_advisor_semantic_axes.py`
- `intelligent_project_analyzer/config/registries/scheme_advisor_semantic_axes.yaml`

已有能力：

- `derive_semantic_axes()`：从用户输入提取语义轴。
- `rank_main_tensions()`：对主矛盾进行排序。
- `evaluate_semantic_alignment()`：检查输出是否出现错域、模板泄漏、英文 key 外露等问题。

当前 registry 已覆盖：

- `space_domains`：住宅、酒店、商业、公共市场、办公、文化展陈、医疗康养、教育公共、城市更新、技术专项等。
- `input_intents`：完整设计框架、方法论、命名、竞标策略、技术解决方案等。
- `problem_modes`：方法论讨论、类比转译、价值论证等。
- `subject_profiles`：创始人业主、家庭多代、儿童、老人、专业使用者、公众访客等。
- `founding_drivers`：身份表达、家族传承、商业回报、品牌差异化、文化转译、民生实用、公共展示、疗愈支持、运营效率等。
- `spatial_design_drivers`：社交与独处、记忆物件整合、艺术与生活、材料可持续、家庭隐私边界、极端韧性、灵活场景切换等。
- `site_resources`：滨水、山地自然、历史场地、交通节点等。
- `critical_constraints`：预算、消防结构、声学、无障碍、机电气候、卫生排水、冷链后勤、隐私安防等。

优化方向：

这些语义轴不应只用于辅助生成追问，而应成为需求重构蓝图的核心事实源。

### 2.3 项目语义理解器

相关位置：

- `intelligent_project_analyzer/services/scheme_advisor_context_intelligence.py`

已有能力：

- 生成 `advisor_packet`。
- 汇总空间分类、上下文向量、本体焦点、知识上下文、能力计划、成熟度、问题计划、版本评分和追踪信息。
- 构造 `question_plan`，优先使用语义轴动态生成追问。
- 提供 `intelligence_trace`，记录分类置信度、覆盖缺口、激活包、知识包、缺失槽位、版本评分原因等。

优化方向：

该模块应被视为“项目语义理解器”的主入口。需求重构不应重新发明一套简化分类器，而应消费它输出的上下文包，并在此基础上生成候选解释和前台表达。

### 2.4 空间上下文包

相关位置：

- `intelligent_project_analyzer/services/space_context_packet_service.py`

已有能力：

- 生成 `context_packet.v3.3`。
- 包含分类、上下文向量、主体轴、元语境驱动、输出模式、专业切换、缺失槽位、本体绑定、知识绑定、激活包协调等。
- 判断知识覆盖上限。
- 支持治理候选、二级激活包、检索计划和受治理知识召回。

优化方向：

需求重构阶段应使用知识覆盖上限约束输出深度。没有专科知识包时，系统可以给 L0/L1 框架，但不能冒充专科判断。

### 2.5 受控 LLM 洞察协议

相关位置：

- `intelligent_project_analyzer/services/demand_reconstruction_insight_protocol.py`

已有能力：

- 把结构化上下文和规则蓝图交给 LLM。
- 要求 LLM 输出 `insight_packet`、真实需求重构、项目成立判断、头号风险、关键分叉、未知边界和一个关键追问。
- 具备 JSON 解析、字段合并、质量门、套话过滤、禁止越界内容等机制。

优化方向：

LLM 不应在规则蓝图之后作为补写层，而应在最终用户输出之前参与综合生成。规则蓝图是约束与兜底，不是前台初稿。

---

## 3. 当前机制断点

### 3.1 丰富语义被压缩成单一 archetype

相关位置：

- `intelligent_project_analyzer/services/demand_reconstruction_context_adapter.py`

当前适配器会调用：

- `SchemeAdvisorContextIntelligence().build(text)`
- `derive_semantic_axes(text)`
- `rank_main_tensions(text)`

但后续又通过 `_derive_archetype()` 把多轴结果压缩成一个主类型：

- `cultural_research`
- `hard_constraint`
- `style_semantics`
- `media_production`
- `public_cultural_experience`
- `commercial_operation`
- `life_identity`
- `general_project`

这一步是主要信息损耗点。

问题不在有 archetype，而在 archetype 被当成了前台蓝图主控。它无法表达：

- 主候选与次候选的关系。
- 某个功能是主空间还是附属功能。
- 关键词之间的冲突。
- 分类置信度与知识覆盖上限。
- LLM 可反驳规则蓝图的依据。
- 当前输出为什么不应套用某个模板。

### 3.2 规则蓝图过早变成用户可见结果

需求重构的用户可见结果应是综合后的判断，而不是后台中间态。

如果系统先展示规则蓝图，再异步等待 LLM：

```text
规则蓝图先输出
↓
用户已看到方向
↓
LLM 后续补充
↓
用户体感：系统先按模板答了，再试图修正
```

正确机制应是：

```text
规则 / 语义 / 知识 / LLM 在后台融合
↓
质量门检查
↓
只展示一个综合版本
```

### 3.3 语义一致性质检没有成为渲染前门禁

`evaluate_semantic_alignment()` 已经能发现：

- 非商业题出现商业模板话术。
- 用户侧出现固定内部步骤名。
- 用户侧出现英文或蛇形命名字段。
- 输出引用了不相关的城市更新或历史建筑语境。
- 没有回应关键主体画像或成立原因。

但需求重构阶段如果不把它作为渲染前门禁，仍然可能出现“分类包正确，前台话术错误”的情况。

### 3.4 知识覆盖上限没有充分约束需求重构深度

`SpaceContextPacketService` 已经能形成知识覆盖判断，但前台输出如果不消费这个字段，就会出现：

- 没有专科包，却输出专科结论。
- 只有邻近知识，却像完整覆盖一样表达。
- 已有知识缺口，但没有进入治理队列。
- 用户看不到系统判断的可信边界。

需求重构阶段不应追求“说得满”，而应追求“说得准、说得有边界”。

### 3.5 参考意见交叉校验结论

本次交叉校验吸收两类参考意见：一类强调“异步替换导致体验割裂，应改为同步熔合”；另一类强调“现有算法资产算而不用，应让语义算法驱动蓝图”。二者主方向一致，但存在若干需要修正的细节。

1. **“规则先出、LLM 后补”的判断在历史机制中成立，当前应作为已消除风险持续防回归。**  
   旧异步链路会让主请求先以 `llm=None` 生成规则版需求重构，再后台排队执行 LLM 增强。用户看到“瞬间回答，没有 LLM 介入”的体感是机制上可解释的。当前实现不再保留用户侧异步替换入口，需求重构首屏必须走同步融合或语义兜底。

2. **“系统没有同步融合能力”不成立。**  
   `DemandReconstructionService` 可以在请求内调用 LLM，并把 LLM 字段与规则蓝图合并。整改后的正确状态是：同步融合成为唯一用户路径；LLM 不可用、失败或质量门拒绝时，直接返回语义兜底版本，而不是再派发后台替换。

3. **“异步偷换卡片”成立，且不应保留为用户体验路径。**  
   旧机制曾依赖后端广播同一条 assistant message 的更新事件、前端按 `guidance_card_id` 替换卡片，并显示“模型洞察中 / 模型洞察已介入”。整改方向不是修补替换链，而是删除这条链路，让首屏就是融合后的唯一版本。

4. **“算法资产算而不用”基本成立，是最关键断点。**  
   需求重构适配器已经调用项目语义理解器、语义轴和主矛盾排序，但输出规划仍主要由 `archetype.primary` 选择整片模板。`rank_main_tensions`、`missing_slots`、`knowledge_coverage_ceiling` 没有成为 `key_forks`、`unknowns`、`next_question` 和承诺深度的主控来源。

5. **“质量门一票否决”需要精确修正。**  
   现有质量门不是完全一票否决，它会逐字段合并；但当有意义字段不足、蓝图字段少于最低阈值时，仍会整体拒绝并进入修复或回退。合理表述应是：字段级合并已经存在，但整体准入门槛偏硬，套话、偏短、泛化类问题不应导致整份 LLM 结果被丢弃。

6. **“默认 8 秒超时”不能作为当前代码事实。**  
   当前需求重构 LLM 超时默认值是 45 秒，最大重试默认值是 0。短超时可以作为部署配置风险写入，但不能作为当前机制事实。

7. **`insight_packet` 的用户价值没有充分释放。**  
   LLM 可以生成 `insight_packet`，后端也会保存，但前端主要渲染 `sections`、`prompt_text`、`options` 和模型状态。后续不应直接展示内部字段名，而应把其中的观察事实、当前假设、反证风险转译成用户侧的“判断依据 / 当前理解 / 会推翻判断的条件”。

8. **“动态购买 UI 组件”是中期方向，不宜作为第一阶段强依赖。**  
   `InsightPanel`、`ConflictSlider`、`DataChecklist` 这类组件化表达能提升体验，但会扩大前后端改造面。第一阶段应先让后端输出 `interaction_module` 或 `component_intent`，仍映射到现有 GuidanceCard；第二阶段再升级为真正组件化 UI。

9. **“删除黑名单”不宜直接采纳。**  
   越界类禁词仍应硬拦，例如完整方案、施工图、报价、材料清单。套话类、偏短类、泛化类应改为字段级修补或降权评分，而不是整份废弃。

10. **“同步阻塞”应修正为“融合优先 + 可流式 + 可降级”。**  
    第一阶段目标不是无限等待 LLM，而是在合理时间内优先产出融合版；LLM 失败或超时时，输出算法语义兜底版。后续再通过骨架屏、流式片段或组件化卡片降低等待体感。

---

## 4. 优化目标

需求重构阶段的算法优化目标可以概括为四句话：

```text
空间分类要稳定。
主矛盾要动态。
知识覆盖要诚实。
追问要人话。
```

进一步拆解为：

1. **稳定底座**  
   空间分类、别名归一、语义轴、知识覆盖等级、风险约束库必须稳定，不靠 LLM 临场猜。

2. **动态判断**  
   用户每个问题的真正重点由多轴语义、主矛盾排序和候选解释决定，不由固定模板决定。

3. **LLM 融合**  
   LLM 基于算法包生成最终表达，不独立改路由，不绕过边界，不在前台输出内部字段。

4. **质量门守护**  
   输出前必须检查错域泄漏、模板泄漏、英文 key 外露、固定步骤名外露、知识越界和套话。

5. **治理闭环**  
   新类型、新误判、新知识缺口进入候选池与复核队列，而不是直接写成服务代码里的散点分支。

---

## 5. 推荐目标链路

### 5.1 总链路

```text
用户输入
↓
入口分诊算法
↓
项目语义理解器
↓
多候选解释包
↓
知识覆盖与风险边界
↓
受控 LLM 综合生成
↓
分级质量门
↓
语义一致性质检
↓
需求重构用户版
↓
是否进入设计任务书
```

这条链路的关键不是“同步阻塞”，而是“融合优先”：请求内优先产出综合版；如果 LLM 不可用、超时或质量门失败，则降级为算法语义兜底版。规则版不再是默认首屏，只保留为故障兜底。

### 5.2 入口分诊层

责任：

- 判断是否进入需求重构。
- 判断是否是具体项目、方法论讨论、案例借鉴、资料整理或出域问题。
- 判断是否直接进入正式任务书链路。

不负责：

- 写前台蓝图。
- 判断最终主矛盾。
- 替代 LLM 做综合表达。

### 5.3 项目语义理解层

责任：

- 生成结构化语义包。
- 提取语义轴。
- 识别空间域、输入意图、问题模式、主体画像、成立动因、场地资源、生命周期、硬约束。
- 输出主矛盾排序。
- 输出缺失槽位。
- 输出知识覆盖上限。

不负责：

- 直接生成用户可见长文本。
- 把所有问题压成一个固定模板。

### 5.4 多候选解释层

这是当前最需要补齐的一层。

它不应只输出一个 `primary archetype`，而应输出候选解释包：

```text
候选 A：主解释
支持证据
反证风险
适用边界

候选 B：次解释
支持证据
为什么不是主解释

候选 C：被降权解释
为什么容易误判
为什么当前不应主导
```

例如：

```text
输入：
崇明岛市民农场访客中心，包含农产品展示、亲子厨房、科普教育与咖啡区。

主候选：
公共文化 / 农业教育型访客中心。

次候选：
农文旅体验与社区教育空间。

附属功能：
轻餐饮 / 咖啡休憩。

降权候选：
纯商业餐饮店。

降权原因：
咖啡区只是支撑停留与社交的功能，不是项目成立的主目标。
```

### 5.5 LLM 综合生成层

LLM 的输入不应只是原始用户问题，也不应只是规则蓝图，而应包含：

- 原始用户输入。
- 入口分诊结果。
- 语义轴。
- 主矛盾排序。
- 候选解释包。
- 知识覆盖上限。
- 缺失槽位。
- 规则蓝图。
- 禁止输出边界。

LLM 的责任：

- 在候选解释中选择最合理主线。
- 说明为什么其他候选不应主导。
- 把结构化判断转成用户语言。
- 生成唯一的需求重构用户版。
- 只提出一个最关键追问。

LLM 不负责：

- 改写入口路由。
- 编造知识覆盖。
- 输出完整方案、完整任务书、施工级建议、报价或材料清单。
- 直接展示内部字段、英文 key、schema 名称。

LLM 成功时，用户看到的是单一综合版本；LLM 失败时，用户也只看到算法语义兜底版。前台不应出现“规则版”和“LLM 版”两个并列答案。

### 5.6 渲染前质量门

用户可见输出前，应至少经过以下检查：

| 检查项 | 目标 |
|---|---|
| 商业模板泄漏 | 非商业/非餐饮题不能出现翻台、外带、出杯等模板化表达 |
| 错域引用 | 不把文化教育题说成商业运营题，不把居住题说成城市更新题 |
| 固定步骤名泄漏 | 用户侧不出现内部流程名、固定卡片名、英文字段 |
| 主体缺失 | 输出必须回应题目里的关键主体，如访客、儿童、业主、运营方 |
| 驱动力缺失 | 输出必须回应项目成立原因，如公共服务、文化转译、品牌表达、回本 |
| 知识越界 | 没有专科覆盖时降级为通用框架或邻近迁移 |
| 套话检查 | 避免温馨舒适、动线合理、满足需求等泛化表述 |

质量门失败时，不应把低质内容直接给用户，而应：

1. 要求 LLM 修复。
2. 或降级到语义包摘要。
3. 或返回诚实边界与关键追问。

质量门应分成三层，而不是把所有问题都做成整份拒绝：

| 层级 | 问题类型 | 处理方式 |
|---|---|---|
| 硬边界 | 完整方案、施工图、报价、材料清单、伪造证据 | 阻断或强制修复，不允许进入前台 |
| 语义一致性 | 错域、商业模板泄漏、内部 key 外露、固定步骤名外露 | 渲染前阻断，要求重写或降级 |
| 表达质量 | 套话、偏短、泛化、缺少锋利判断 | 字段级修补或降权，不应整份废弃 |

这意味着质量门不是取消，而是从“偏硬的整体验收”改为“硬边界守住、软质量修字段、语义错误不放行”。

### 5.7 规则模板的重新定位

现有 8 类规则模板仍有价值，但不应再作为整片输出模板。它们应降级为“知识碎片库”：

- `life_identity` 中关于人生结构、乡土语境、作品化风险的判断，可以作为居住身份类碎片。
- `commercial_operation` 中关于峰值、外带、出品效率的判断，可以作为商业运营类碎片。
- `public_cultural_experience` 中关于亲子、科普、后勤、材料维护的判断，可以作为公共体验类碎片。
- `media_production` 中关于机位、灯光、油烟、收音的判断，可以作为内容生产类碎片。

碎片的选择应由语义轴、主矛盾、候选解释和知识覆盖共同决定。复合项目可以组合多个碎片，但最终由 LLM 或语义兜底层统一成一份用户语言，而不是让用户看到多个模板拼接痕迹。

---

## 6. 规则蓝图与 LLM 的正确配合

### 6.1 不合理方式

```text
规则蓝图生成
↓
前台立即展示
↓
LLM 异步补充
↓
前台替换或追加 LLM 判断
```

问题：

- 用户先看到的可能是错误模板。
- LLM 即使正确，也是在修补第一印象。
- 规则和 LLM 容易出现前后不一致。
- 前端需要处理两个不同来源的答案。
- 用户可能已阅读或点击首屏卡片，后续替换容易造成状态和认知错位。

### 6.2 合理方式

```text
入口分诊与语义算法生成内部结构
↓
规则蓝图提供边界、承接槽位和兜底片段
↓
LLM 基于完整上下文综合生成单一用户版
↓
分级质量门检查
↓
前台展示唯一版本；失败时展示语义兜底版
```

分工：

| 层 | 负责 | 不负责 |
|---|---|---|
| 规则蓝图 | 稳定结构、边界、兜底、任务书承接槽位 | 直接作为最终用户答案 |
| 语义算法 | 多轴识别、候选解释、主矛盾排序、覆盖上限 | 写成自然语言洞察 |
| LLM | 综合判断、用户语言、表达锋利度、关键追问 | 改路由、越界生成完整方案 |
| 质量门 | 拦截错域、套话、越界、内部字段外露 | 增加内容深度 |

异步增强不再作为用户侧过渡或诊断路径保留。默认且唯一的用户体验应是“融合优先”：用户第一次看到的就是综合判断；失败时也只看到一次语义兜底，而不是等待后台把第一版替换掉。

### 6.3 UI 组件化的阶段边界

参考意见提出的 `InsightPanel`、`ConflictSlider`、`DataChecklist` 方向有价值，但不宜在第一阶段直接强行改造为 LLM 动态购买组件。合理分期如下：

| 阶段 | 目标 | 前端影响 |
|---|---|---|
| 第一阶段 | 后端输出 `interaction_module` 或 `component_intent`，仍映射到现有 GuidanceCard | 小改，主要改善内容和状态一致性 |
| 第二阶段 | 引入洞察、取舍、清单等专用组件 | 中改，需要前端组件协议 |
| 第三阶段 | 支持流式片段渲染和骨架屏 | 大改，需要接口、状态和体验联动 |

第一阶段的优先级仍是：消除“规则首屏 + LLM 替换”的割裂，而不是立刻追求复杂组件。

---

## 7. 候选解释与冲突矩阵

需求重构阶段需要从“单类型判断”升级到“候选解释 + 冲突矩阵”。

### 7.1 为什么需要候选解释

真实项目常常是复合空间：

- 访客中心里有咖啡区。
- 美食实验室里有拍摄棚。
- 私宅里有艺术展示。
- 社区店里同时服务熟客与路过客。
- 农贸市场里有民生、商业、公共形象和卫生后勤。

如果系统只选择一个类型，就会丢失主次关系。

### 7.2 冲突矩阵示例

| 复合信号 | 容易误判 | 正确判断方式 |
|---|---|---|
| 访客中心 + 咖啡区 | 纯餐饮商业 | 先判访客中心的公共服务/展示教育目标，咖啡只是停留支撑 |
| 美食实验室 + 拍摄 | 普通厨房 | 先判内容生产和镜头动线，再看厨房操作 |
| 私宅 + 展示 | 样板房或展厅 | 先判居住生活与身份表达，再看展示强度 |
| 农贸市场 + 打卡 | 商业街区 | 先判民生、卫生、摊贩与采购效率，再看形象升级 |
| 儿童空间 + 医疗信号 | 普通教育空间 | 先判安全、感官、照护与专业边界 |

### 7.3 输出原则

冲突出现时，不应强行给一个类型，而应：

1. 列出候选。
2. 标注主候选。
3. 标注次候选。
4. 标注被降权候选。
5. 说明证据和反证。
6. 把最能改变判断的问题交给用户。

---

## 8. 知识覆盖与诚实封顶

需求重构不是越具体越好，而是越准确越好。

建议将知识覆盖分为四级：

| 等级 | 含义 | 输出深度 |
|---|---|---|
| L2 专科覆盖 | 有细分空间知识包、案例或方法资产 | 可以给较具体的判断框架和关键风险 |
| L1 邻近迁移 | 有相近类型知识，可部分迁移 | 必须说明迁移边界 |
| L0 通用框架 | 只有通用空间方法论 | 给功能、动线、边界、风险、体验、生命周期框架 |
| L-1 覆盖不足 | 细分领域陌生或证据不足 | 明确不足，只给判断路径和下一步验证 |

前台表达示例：

```text
我会先把它按“公共农业教育型访客中心”来理解，而不是按普通咖啡店来理解。
咖啡区在这里更像停留和社交的支撑功能。除非你的目标是靠咖啡收入回本，否则翻台和外带不应成为第一判断。
```

这类表达比内部说“coverage_gap=true”更适合用户侧。

---

## 9. 分阶段优化路线

### 9.1 短期：融合优先与算法兜底

目标：

- 不让规则蓝图作为默认首屏直接露出。
- 把默认体验从“规则首屏 + 异步替换”调整为“融合优先 + 语义兜底”。
- 让已有语义轴和主矛盾进入 LLM prompt 的核心位置。
- 输出前增加语义一致性质检。
- LLM 不可用时，兜底为语义包摘要，而不是旧模板。

重点：

- 前台只展示一个综合版本。
- `archetype` 从主控降级为兼容字段。
- 规则蓝图只作为内部结构和兜底。
- `rank_main_tensions` 驱动 `key_forks` 和 `next_question`。
- `missing_slots` 驱动 `unknowns`。
- `knowledge_coverage_ceiling` 或覆盖缺口驱动输出深度。

### 9.2 中期：替换单一 archetype 为候选评分器与碎片库

目标：

- 把 `_derive_archetype()` 从单一路由分支升级为候选评分器。
- 候选评分器输出主候选、次候选、被降权候选、证据、反证和置信度。
- 冲突矩阵进入候选评分逻辑。
- 现有模板拆为可组合知识碎片库，而不是整片套用。

重点：

- 不能再靠“咖啡”“店”“翻台”等单词一票决定商业运营。
- 复合空间必须保留主次关系。
- 候选解释要能被 LLM 使用，也要能被后台审计。
- 质量门改为硬边界、语义一致性、表达质量三层。

### 9.3 中期扩展：组件化 UI 与流式体验

目标：

- 在不破坏现有 GuidanceCard 的前提下，先输出 `interaction_module` 或 `component_intent`。
- 将洞察、取舍、清单三类交互意图映射到稳定前端组件。
- 在后端融合耗时较长时，用骨架屏或流式片段降低等待体感。

重点：

- 组件化是表达层升级，不替代语义算法。
- LLM 只能选择组件意图和填充用户语言，不能绕过分诊、覆盖和质量门。
- 第一阶段不把组件化作为算法优化的前置依赖。

### 9.4 长期：治理闭环

目标：

- 高频误判进入治理队列。
- 新空间类型、新语义轴、新冲突关系、新知识缺口进入 registry 或管理后台复核。
- 不把一次性修复散落在服务代码里。

重点：

- 语义轴 registry 是稳定识别框架。
- 服务代码只做编排，不长期承载业务补丁。
- 测试样本逐条可追溯。

---

## 10. 测试与验收清单

### 10.1 单样本验收

对每条测试输入，至少检查：

| 检查项 | 通过标准 |
|---|---|
| 入口分诊 | 进入正确流程，不把具体项目误判为方法论闲聊 |
| 主空间判断 | 主空间类型正确，附属功能不反客为主 |
| 复合关系 | 能识别主候选、次候选、被降权候选 |
| 主矛盾 | 输出抓住真正张力，不套通用设计话术 |
| 知识覆盖 | 有边界说明，不冒充专科 |
| LLM 融合 | 用户首屏只看到综合版本，不看到规则版 + LLM 版割裂 |
| 质检 | 无错域模板、无英文 key、无内部字段、无固定步骤名 |
| 追问 | 只问最关键的 1 个问题，且能改变后续判断 |
| 语义兜底 | LLM 失败时输出语义包摘要，而不是旧模板 |
| 组件意图 | 若输出交互模块，必须能回落到现有 GuidanceCard |

### 10.2 压力测试样本类型

建议优先覆盖：

1. 公共访客中心 + 轻餐饮。
2. 美食实验室 + 拍摄/直播。
3. 私宅 + 艺术收藏/展示。
4. 社区农贸市场 + 城市形象升级。
5. 茶饮/咖啡/轻食相互邻近迁移。
6. 方法论讨论但带有真实项目锚点。
7. 技术专项问题，如声学、给排水、排烟、电力。
8. 知识覆盖不足的新型空间。

### 10.3 失败分级

| 等级 | 失败表现 | 处理方式 |
|---|---|---|
| P0 | 错域严重，输出完全跑偏 | 阻断输出，进入修复或兜底 |
| P1 | 主次关系错误，但仍部分相关 | 降级输出，要求补关键问题 |
| P2 | 表达泛化、套话、缺乏洞察 | LLM 修复或改写 |
| P3 | 缺少次要字段或追踪信息 | 记录观察，不阻断 |

### 10.4 机制验收

| 机制 | 通过标准 |
|---|---|
| 融合优先 | 默认路径不再先返回规则版再异步替换 |
| 主矛盾接通 | 修改输入主矛盾后，`key_forks` 和 `next_question` 明显变化 |
| 缺失槽接通 | `missing_slots` 能进入 `unknowns` 或追问候选 |
| 覆盖封顶 | 无专科包时自动降级为 L0/L1 表达 |
| LLM 可观测 | 后台记录 `insight_source`、`llm_status`、质量报告，用户侧不暴露内部字段 |
| 异步替换移除 | 不再广播需求重构卡片替换事件，不再展示 pending 洞察状态，不再轮询等待后台增强 |

---

## 10.5 v1.2 首轮实施记录

本轮实施只处理后端主链路和测试验收，不展开中期组件化 UI。

### 10.5.1 已落地机制

1. **融合优先默认路径**  
   默认请求路径优先在请求内完成 LLM 融合；LLM 不可用或失败时直接返回语义兜底版本。

2. **语义候选集替代单关键词原型树**  
   `DemandReconstructionContextAdapter` 输出 `semantic_candidate_set`，区分 `primary`、`secondary`、`downweighted`，并保留证据与反证信息。  
   例如市民农场访客中心中，`public_cultural_experience` 为主解释，`commercial_operation` 因咖啡区属于配套停留节点而被降权。

3. **主矛盾、缺失槽和覆盖封顶进入蓝图**  
   `DemandReconstructionOutputPlanner` 使用 `main_tensions` 进入 `key_forks` / `next_question`，使用 `missing_slots` 进入 `unknowns`，使用 `knowledge_coverage_ceiling` 生成知识覆盖边界段落。

4. **语义兜底替代纯规则兜底**  
   LLM 未配置、调用失败或质量门拒绝时，`insight_source` 统一为 `semantic_fallback`，表示用户看到的是算法语义包 + 规则护栏后的兜底版本，而不是旧规则模板首屏。

5. **公共文化模板碎片化的第一步**  
   公共文化不再只有市民农场/亲子厨房片段。昆曲老宅、教学故居、练声、展陈类项目会切到“动静分区 / 保护边界 / 文化转译”碎片，避免把亲子厨房、咖啡和材料循环误带入。

6. **未证实主矛盾过滤**  
   对 `rank_main_tensions` 输出增加轻量相关性过滤，避免把原文没有出现的“摊贩 / 居民”等市场型张力强行插入市民农场访客中心首位。

7. **LLM 提示上下文补齐算法脚手架**  
   LLM prompt 中增加 `semantic_candidate_set` 和 `knowledge_coverage_ceiling`，让模型不再只面对原始消息和规则蓝图。

### 10.5.2 验收样本

| 样本 | 主解释 | 关键验证 |
|---|---|---|
| 崇明岛市民农场访客中心 | `public_cultural_experience` | 商业解释被降权；前台无翻台、坪效、外带、摊贩泄漏；保留公共体验、材料循环、教育互动 |
| 美食作家 KOL 美食实验室 | `media_production` | 进入场景切换、专业使用者习惯、污染与画面边界；无住宅旧模板泄漏 |
| 50 岁设计师返乡民居 | `life_identity` | 进入真实需求重构、四个结构轴、路径分流；LLM 未配置时为 `semantic_fallback` |
| 苏州昆曲老宅教学故居 | `public_cultural_experience` | 进入动静分区、保护边界、文化转译；无亲子厨房、咖啡、材料循环误带入 |
| 小型茶饮店冷藏柜尺寸 | `hard_constraint` | 硬约束优先于商业运营模板；追问前场展示冷藏还是后场储藏冷藏 |

### 10.5.3 已跑验证

```text
pytest tests\services\test_demand_reconstruction_service.py -q
结果：24 passed

pytest tests\api\test_scheme_advisor_entry_route.py -q
结果：11 passed

pytest tests\unit\test_demand_reconstruction_llm.py -q
结果：8 passed

pytest tests\services\test_demand_reconstruction_service.py tests\api\test_scheme_advisor_entry_route.py tests\unit\test_demand_reconstruction_llm.py -q
结果：43 passed
```

### 10.5.4 剩余边界

1. 组件化 UI 已完成第一阶段：`component_intent` 会携带主矛盾、缺失槽和追问 payload，并映射到现有 GuidanceCard 模块；真正独立的 `InsightPanel` / `ConflictSlider` / `DataChecklist` 专用组件仍后置。
2. 真实线上 LLM 是否可用仍依赖 provider 配置；已提供同步首屏 smoke 验证脚本，但最终通过需要在实际后端与密钥环境中运行。

---

## 10.6 v1.3 异步替换链路移除记录

本轮收口的是用户最直接感知到的割裂问题：需求重构不再允许“先规则蓝图首屏，再后台 LLM 替换同一卡片”。

### 10.6.1 机制调整

1. **后端入口只走同步融合或语义兜底**  
   需求重构路由不再读取 `DEMAND_RECONSTRUCTION_LLM_ASYNC` 决定是否异步增强。请求内能拿到 LLM 时，直接生成融合蓝图；拿不到或失败时，直接返回语义兜底蓝图。

2. **后台替换事件退出需求重构链路**  
   旧的需求重构增强任务、同卡片替换逻辑和 `conversation_message_updated` 用户侧事件不再参与需求重构。前端不会再等待后台把第一版 assistant message 改写成第二版。

3. **前端 pending 状态清理**  
   需求重构卡片不再展示“模型洞察中”。会话页也不再因为 `semantic_pending_llm` / `scheduled` 状态启动定时刷新。

4. **兼容口径**  
   历史会话中若仍存在旧的 pending 标记，前端只按普通兜底卡片处理，不再触发轮询或显示“正在增强”的状态。

### 10.6.2 防回归标准

| 项 | 标准 |
|---|---|
| 首屏输出 | 一次请求只返回一个需求重构版本 |
| LLM 参与 | `insight_source=llm` 时首屏 reply 已包含 LLM 融合内容 |
| 兜底路径 | LLM 不可用时返回 `semantic_fallback`，不排队替换 |
| 前端状态 | 不出现“模型洞察中”状态，不轮询等待增强 |
| WebSocket | 不依赖 `conversation_message_updated` 更新需求重构卡片 |

---

## 10.7 v1.4 语义一致性门禁默认启用记录

本轮收口的是质量治理问题：`evaluate_semantic_alignment()` 不再只是 shadow 观察，而是进入需求重构渲染前门禁。

### 10.7.1 机制调整

1. **默认阻断 blocking 级错域输出**  
   需求重构生成 reply/card 后，会先运行语义一致性质检。若检测到 blocking 级问题，并且当前蓝图来自 LLM 融合结果，则丢弃该 LLM 蓝图，回退到 registry 驱动的语义兜底蓝图。

2. **保留诊断关闭入口**  
   `DEMAND_RECONSTRUCTION_ALIGNMENT_GATE=0/false/off/no` 可关闭硬阻断，进入 shadow-only 诊断模式。该模式只用于观察和调试，不应作为默认用户体验。

3. **可观测性保留**  
   无论是否阻断，`semantic_alignment_shadow` 都会记录 issue 数量、blocking 数量、warning 数量和问题代码。发生阻断时，蓝图额外记录 `alignment_gate.action=llm_rejected` 与阻断代码，便于排查。

### 10.7.2 防回归标准

| 项 | 标准 |
|---|---|
| 默认门禁 | 未设置环境变量时，blocking 级 LLM 错域输出会回退到 `semantic_fallback` |
| 诊断关闭 | 显式设置 `DEMAND_RECONSTRUCTION_ALIGNMENT_GATE=0` 时，错域输出仅记录 shadow，不改变输出 |
| 用户可见内容 | 被门禁拒绝的 LLM 具体措辞不进入 reply |
| 追踪字段 | `semantic_alignment_shadow` 始终记录质检结果 |

---

## 10.8 v1.5 入口判断共享化记录

本轮收口的是入口分诊口径分叉问题：需求重构不再在 `DemandReconstructionService.should_handle()` 内维护独立判断词表，而是调用语义轴模块中的共享纯函数。

### 10.8.1 机制调整

1. **共享入口门禁函数**  
   `scheme_advisor_semantic_axes.should_enter_demand_reconstruction()` 集中处理需求重构入口判断，包括空输入、竞标策略、纯命名文案、参考资料请求、具体项目锚点、显式需求重构、多轴项目描述、研究建议型空间问题。

2. **service 降为编排层**  
   `DemandReconstructionService.should_handle()` 只调用共享函数，不再复制入口分诊词表。后续要调整需求重构入口策略，应优先改共享语义函数和 registry，而不是改 service 编排层。

3. **行为保持**  
   已有关键路径保持不变：具体项目进入需求重构；方法论闲聊、竞标策略、纯命名文案、参考资料请求不被需求重构误吞。

### 10.8.2 防回归标准

| 项 | 标准 |
|---|---|
| 具体项目 | 新行业真实项目仍进入需求重构 |
| 方法论 | 纯方法论问题不被需求重构误吞 |
| 竞标策略 | 竞标/投标汇报策略不进入需求重构 |
| 命名文案 | 纯命名/文案请求不进入需求重构 |
| 参考资料 | 只要案例/资料/参考图的请求不进入需求重构 |

---

## 10.9 v1.6 组件意图 payload 可见化记录

本轮收口的是组件化第一阶段不足：`component_intent` 不再只是后台诊断字段，而是携带可直接渲染的用户可见内容。

### 10.9.1 机制调整

1. **后端 payload 补齐**  
   `conflict_check` 会携带主矛盾条目和关键追问；`data_checklist` 会携带缺失槽的用户可见说明；`insight_panel` 会携带默认重构提示。

2. **前端可见模块**  
   GuidanceCard 会把 `component_intent.items` 和 `component_intent.prompt` 渲染出来，不再只显示“关键取舍 / 条件清单 / 洞察面板”的静态标签。

3. **协议边界**  
   这仍属于第一阶段组件化：不新增独立复杂组件协议，不引入流式状态，只把后端算法意图更清楚地呈现在现有 GuidanceCard 内。

### 10.9.2 防回归标准

| 项 | 标准 |
|---|---|
| 关键取舍 | `conflict_check.items` 显示主矛盾条目 |
| 关键追问 | `conflict_check.prompt` 可见 |
| 条件清单 | `data_checklist.items` 显示缺失槽说明 |
| 洞察面板 | `insight_panel.items` 可见 |
| 前端兼容 | 无 payload 的历史 `component_intent` 仍能显示静态模块 |

---

## 10.10 v1.7 真实 LLM 介入 smoke 同步化记录

本轮收口的是生产验证口径问题：旧 smoke 脚本仍按“首屏规则版 + 后台替换”的异步机制轮询 session，这会掩盖当前同步融合机制的真实状态。

### 10.10.1 机制调整

1. **首屏即验收**  
   `scripts/smoke_demand_reconstruction_llm.py` 现在优先检查 `/api/v2/conversation/message` 的首次响应。如果首屏已经是 `insight_source=llm` 且 `llm_status=used`，立即验证蓝图有效性并通过。

2. **fallback 明确失败**  
   如果首屏返回 `semantic_fallback`、`not_configured` 或其它终态失败状态，脚本直接失败，并打印 `llm_error_type` / `llm_error`。这能直接暴露 provider 未配置、网络失败、质量门拒绝等问题。

3. **兼容轮询降级**  
   轮询逻辑只保留为过渡兼容，不再作为正常成功路径。当前机制的目标是首屏同步融合，而不是等待后台增强。

### 10.10.2 使用方式

```bash
.conda\python.exe -B scripts\smoke_demand_reconstruction_llm.py --base-url http://127.0.0.1:8001
```

### 10.10.3 防回归标准

| 项 | 标准 |
|---|---|
| 首屏 LLM | 首次响应为 `llm/used` 时不再 GET 会话轮询 |
| 未配置 | 首次响应为 `semantic_fallback/not_configured` 时 smoke 失败 |
| 蓝图有效性 | `task_reframe`、`primary_risk`、`key_forks`、`unknowns`、`sections` 等字段达到最低有效性 |

---

## 10.11 v1.8 旧异步运行态诊断记录

本轮运行真实本机 smoke 时，当前 8001 后端返回：

```text
initial source=rule_pending_llm, status=scheduled
```

这说明运行中的后端仍是旧异步路径进程，而不是当前 worktree 的同步融合实现。当前代码扫描中，生产代码不再生成 `rule_pending_llm` / `semantic_pending_llm`，因此该结果应按“后端进程未重启 / 运行态过期”处理。

### 10.11.1 机制调整

1. **smoke 快速失败**  
   若首屏返回 `rule_pending_llm`、`semantic_pending_llm` 或 `llm_status=scheduled`，`scripts/smoke_demand_reconstruction_llm.py` 会立即失败，并提示重启后端。

2. **不再误轮询**  
   旧脚本会持续轮询等待后台替换，容易让排查误以为只是 LLM 慢。现在该状态被识别为旧机制残留，不再等待。

3. **验证顺序**  
   需要先重启后端加载当前 worktree，再运行：

```bash
.conda\python.exe -B scripts\smoke_demand_reconstruction_llm.py --base-url http://127.0.0.1:8001 --case return-home-house
```

### 10.11.2 防回归标准

| 项 | 标准 |
|---|---|
| 旧 pending | `rule_pending_llm` / `semantic_pending_llm` / `scheduled` 直接判失败 |
| 错误提示 | 明确提示“legacy async demand reconstruction path”和重启后端 |
| 当前代码 | 生产代码不再生成旧 pending 状态 |

---

## 10.12 v1.9 规则蓝图候选前置与 registry 消费修补

本轮继续推进“规则蓝图退到后台骨架、算法与 registry 驱动输出”的实施，重点不是增加新模板，而是减少 planner 内部特例抢路由，让高频空间缺口进入统一候选集合和可审计输出。

### 10.12.1 机制调整

1. **高频缺口进入统一 candidate set**  
   `DemandReconstructionContextAdapter` 现在会把城市更新、收藏展陈、办公总部、医疗照护等高频项目作为语义候选输出，而不是只依赖 `DemandReconstructionOutputPlanner` 后置判断。这样 `archetype.secondary`、复合关系、诊断字段和后续 LLM prompt 都能看到这些类型。

2. **planner builder 映射补齐**  
   `DemandReconstructionOutputPlanner.build_plan()` 已补齐 `workplace_headquarters`、`urban_renewal`、`collection_museum` 的 builder 映射，避免候选已经识别但输出仍回落到 `general_project`。

3. **registry trigger 合并但控制泛词抢路由**  
   planner 侧合并专科碎片 trigger 与 override trigger，避免 registry 细分词与覆盖词互相遮蔽；同时收紧办公分支，`员工`、`办公` 这类泛词不能单独把品牌展厅或商业接待题改写成“总部办公”主线。

4. **追加碎片同样走占位符格式化**  
   primary/secondary 追加 sections 现在也通过 `_format_fragment_text()` 格式化，避免 registry 碎片里的 `{space_label}`、`{owner_profile}`、`{target_space}` 等占位符在非主 fragment 路径中泄漏。

5. **碎片评分消费语义轴**  
   `_fragment_trigger_score()` 不再只统计字面 trigger，也会把 `semantic_axis_matches` 纳入分值，减少“算法已经识别但碎片没被选中”的落差。

### 10.12.2 防回归标准

| 项 | 标准 |
|---|---|
| 高频缺口 | 城市更新、收藏展陈、办公总部、医疗照护能进入候选集合和对应 planner |
| 泛词控制 | 品牌展厅含“员工活动”时不能被改写成总部办公主线 |
| 占位符 | 追加的 primary/secondary registry sections 不泄漏 `{...}` 占位符 |
| 语义轴 | 配置了 `semantic_axis_matches` 的碎片可被语义轴命中推动 |

### 10.12.3 本轮验证

```bash
.conda\python.exe -B -m py_compile intelligent_project_analyzer\services\demand_reconstruction_output_planner.py intelligent_project_analyzer\services\demand_reconstruction_context_adapter.py
.conda\python.exe -B -m pytest tests\services\test_demand_reconstruction_service.py::test_family_enterprise_brand_exhibition_is_not_treated_as_headquarters_office -q
.conda\python.exe -B -m pytest tests\services\test_demand_reconstruction_service.py -q
```

验证结果：`tests\services\test_demand_reconstruction_service.py` 全量通过，`148 passed`。

---

## 10.13 v1.10 高频候选主次排序与组件化回归验证

本轮补的是 v1.9 后继续审计发现的排序细节：部分高频空间类型已经进入统一 candidate set，但当题面同时包含“恒温恒湿、消防、结构”等硬约束词时，`hard_constraint` 可能凭固定分值压过真实项目主线。典型样本是“球鞋博物馆 + 限量藏品展示 + 恒温恒湿保护”：正确输出应以收藏展陈为主线，硬约束作为次候选进入复合关系，而不是把项目主线改写成硬约束题。

### 10.13.1 机制调整

1. **项目主线优先于技术条件**  
   城市更新、收藏展陈这类明确项目对象候选的分值上调，使其在包含硬约束词时仍能保持 primary。技术条件继续作为 secondary 进入复合关系，保留其约束价值。

2. **候选集合测试固定化**  
   新增回归断言：城市更新、收藏展陈必须进入 `semantic_candidate_set`，并成为对应样本的 primary archetype。收藏展陈样本中的 `hard_constraint` 必须作为 secondary 保留。

3. **registry 占位符防泄漏**  
   针对城市更新和收藏展陈样本新增渲染断言，确保追加的 registry fragments 不会把 `{space_label}`、`{target_space}` 等占位符暴露给用户。

4. **前端组件意图回归**  
   继续保留现有 GuidanceCard 承载方式，但验证 `component_intent` 已作为用户可见模块展示，并且旧 `semantic_pending_llm` / `rule_pending_llm` 不再显示“模型洞察中”的运行态。

### 10.13.2 本轮验证

```bash
.conda\python.exe -B -m pytest tests\services\test_demand_reconstruction_service.py -q
npm test -- ConversationChat.test.tsx GuidanceCard.test.tsx --runInBand
```

验证结果：

| 验证项 | 结果 |
|---|---|
| 需求重构服务全量测试 | `156 passed` |
| GuidanceCard / ConversationChat 前端聚焦测试 | `12 passed` |

---

## 10.14 v1.11 registry 可见文案治理

本轮处理的是规则蓝图从“代码硬模板”迁到 registry 后的新风险：registry 本身可能把内部工程术语写进用户可见文案。此前 `style_semantics` 的“表达禁区”段落中出现了 `registry 主线碎片`，这类词不应该出现在需求重构前台。

### 10.14.1 机制调整

1. **用户可见文案去内部术语**  
   将 `registry 主线碎片会明确...` 改为 `需求重构会明确...`，同时同步修改 planner 内置 fallback，避免 registry 读取失败时仍泄漏内部词。

2. **新增 registry 可见字段治理测试**  
   新增测试扫描 `demand_reconstruction_blueprint_fragments` 中会进入前台的字段：
   `task_reframe`、`viability`、`primary_risk`、`key_forks`、`unknowns`、`next_question`、`title`、`body`、`items`。

3. **禁止泄漏的内部词**  
   当前治理测试禁止用户可见文案包含：
   `registry`、`fragment`、`archetype`、`candidate_set`、`component_intent`、`axis_id`、`ontology`、`LLM`、`llm`。

### 10.14.2 本轮验证

```bash
.conda\python.exe -B -m pytest tests\services\test_demand_reconstruction_service.py::test_demand_reconstruction_registry_visible_text_does_not_leak_internal_terms tests\services\test_demand_reconstruction_service.py::test_default_blueprint_fragments_are_marked_in_registry_not_skipped_by_name tests\services\test_demand_reconstruction_service.py::test_style_and_hard_constraint_prompts_select_different_module_sets -q
.conda\python.exe -B -m pytest tests\services\test_demand_reconstruction_service.py -q
```

验证结果：

| 验证项 | 结果 |
|---|---|
| registry 可见文案治理聚焦测试 | `3 passed` |
| 需求重构服务全量测试 | `157 passed` |

---

## 10.15 v1.12 LLM 运行态诊断与 smoke 失败分类

本轮处理的是实施后继续排查中的剩余盲点：即使代码已经取消旧异步替换路径，用户现场仍可能看到“瞬间回答、没有 LLM 介入”。这种现象至少可能来自四类不同原因：

1. 后端进程仍是旧代码，首屏返回 `rule_pending_llm` / `semantic_pending_llm` / `scheduled`。
2. 当前运行环境没有配置需求重构 LLM key，服务直接走 `semantic_fallback / not_configured`。
3. LLM 已配置但调用失败，例如网络、代理、provider、模型名或超时问题。
4. LLM 有响应但被 JSON/质量门/语义一致性门拒绝。

如果没有运行态诊断，这四类都会被用户感知为“LLM 没介入”，但对应处理完全不同。

### 10.15.1 机制调整

1. **新增无密钥泄漏的本地配置快照**  
   `demand_reconstruction_llm.describe_demand_reconstruction_llm_config()` 现在可以输出需求重构 LLM 的红acted配置状态：

   - `DEMAND_RECONSTRUCTION_USE_LLM` 是否启用。
   - direct adapter 是否启用。
   - fallback 链是否启用。
   - provider chain。
   - 每个 provider 是否有 API key。
   - 模型、base_url、proxy 来源状态。
   - 当前配置是否具备 ready 条件。
   - blocked reasons。

   该函数只返回 key 是否存在和 key 来源环境变量名，不返回任何密钥值。

2. **smoke 脚本启动即打印本地诊断**  
   `scripts/smoke_demand_reconstruction_llm.py` 默认会加载本地 `.env`（不覆盖当前环境变量），并打印一行配置快照：

   ```text
   local LLM config: ready=True, use_llm=True, direct=True, auto_fallback=False, providers=[qwen(key=yes, model=..., proxy=...)], blocked=[none]
   ```

   如果只想验证 HTTP 行为，可使用 `--no-local-llm-diagnosis` 关闭该输出。

3. **语义兜底失败信息携带配置提示**  
   当首屏返回 `semantic_fallback` 或 terminal failure status 时，smoke 错误会同时输出：

   - 后端返回的 `insight_source` / `llm_status`。
   - `llm_error_type` / `llm_error`。
   - 本地红acted配置快照。

   这样可以快速区分“代码没加载”“key 没配”“调用失败”“质量门拒绝”。

### 10.15.2 防回归标准

| 项 | 标准 |
|---|---|
| 配置诊断 | 不打印任何 API key 值，只打印是否配置与来源变量名 |
| 未配置 | direct provider 无 key 时 `ready=False` 且给出 blocked reason |
| fallback 链 | 能显示 demand-specific provider chain 中各 provider 的 key/model/proxy 状态 |
| smoke 输出 | 默认打印本地 LLM config；失败时把 config hint 带入错误信息 |

### 10.15.3 本轮验证

```bash
.conda\python.exe -B -m pytest tests\unit\test_demand_reconstruction_llm.py tests\unit\test_smoke_demand_reconstruction_llm_script.py -q
.conda\python.exe -B -m py_compile intelligent_project_analyzer\services\demand_reconstruction_llm.py scripts\smoke_demand_reconstruction_llm.py
```

验证结果：

| 验证项 | 结果 |
|---|---|
| LLM adapter + smoke 诊断聚焦测试 | `14 passed` |
| 诊断相关 Python 文件编译 | 通过 |

---

## 10.16 v1.13 知识缺口治理信号进入蓝图 metadata

本轮补的是“误判与知识缺口进入治理队列”的主计划闭环。此前压力测试系统已经能把 `coverage_gap`、`knowledge_gap_ticket` 聚合到治理报告，但需求重构蓝图本身没有把这些信号结构化透传出来。结果是：用户侧能看到“知识覆盖边界”，但后台很难从单次需求重构结果直接追踪“这个空间类型应该补 registry 还是补知识资产”。

### 10.16.1 机制调整

1. **coverage gap 进入空间 registry 治理队列**  
   当 `classification.coverage_gap=True` 时，蓝图追加：

   ```json
   {
     "code": "coverage_gap",
     "track": "space_registry",
     "review_queue": "space_registry_review",
     "severity": "P1",
     "user_visible": false
   }
   ```

   含义是：分类或语义覆盖存在缺口，应进入空间类型、别名、边界样本或 registry 覆盖治理。

2. **knowledge gap ticket 进入知识资产审核队列**  
   当 `classification.knowledge_gap_ticket` 存在时，蓝图追加：

   ```json
   {
     "code": "knowledge_gap_ticket",
     "track": "knowledge_asset_pipeline",
     "review_queue": "knowledge_asset_review",
     "severity": "P2",
     "user_visible": false
   }
   ```

   ticket 中只保留 `gap_type`、`project_type`、`summary` 这类治理摘要，作为后续候选知识卡或知识包沉淀的入口。

3. **部分覆盖进入观察池**  
   当覆盖等级为 `partial_specialist` / `l1` / `neighbor_transfer` 时，蓝图追加 `knowledge_coverage_watch`，进入 `coverage_watch_pool`。这类信号不一定马上生产知识资产，但应观察是否逐渐成为高频缺口。

4. **治理信号不进入用户文案**  
   `governance_signals` 是后台 metadata，不参与 `_render_reply()`，也不进入用户侧自然语言。用户只看到“知识覆盖边界”的解释，不看到 `coverage_gap`、`knowledge_gap_ticket`、`space_registry_review`、`knowledge_asset_review` 等内部治理术语。

### 10.16.2 防回归标准

| 项 | 标准 |
|---|---|
| coverage_gap | 蓝图含 `governance_signals[].code=coverage_gap`，review_queue 为 `space_registry_review` |
| knowledge_gap_ticket | 蓝图含 `governance_signals[].code=knowledge_gap_ticket`，review_queue 为 `knowledge_asset_review` |
| 用户文案 | `_render_reply()` 不包含 `coverage_gap`、`knowledge_gap_ticket`、`space_registry_review`、`knowledge_asset_review` |
| 覆盖观察 | L1/partial 覆盖可进入 `coverage_watch_pool` |

### 10.16.3 本轮验证

```bash
.conda\python.exe -B -m pytest tests\services\test_demand_reconstruction_service.py::test_low_coverage_level_downgrades_user_visible_commitment_depth tests\services\test_demand_reconstruction_service.py::test_demand_reconstruction_blueprint_surfaces_knowledge_gap_governance_signals_without_user_leakage tests\services\test_demand_reconstruction_service.py::test_output_planner_uses_main_tensions_missing_slots_and_coverage_before_template_defaults tests\unit\test_demand_reconstruction_llm.py tests\unit\test_smoke_demand_reconstruction_llm_script.py -q
.conda\python.exe -B -m py_compile intelligent_project_analyzer\services\demand_reconstruction_output_planner.py intelligent_project_analyzer\services\demand_reconstruction_llm.py scripts\smoke_demand_reconstruction_llm.py
```

验证结果：

| 验证项 | 结果 |
|---|---|
| 需求重构覆盖/治理 + LLM 诊断聚焦测试 | `17 passed` |
| 相关 Python 文件编译 | 通过 |

---

## 10.17 v1.14 前端覆盖边界枚举对齐

本轮处理的是后端与前端的枚举口径不一致。后端 `_apply_coverage_commitment()` 已经把以下覆盖等级都视为低覆盖降级：

- `general_method_only`
- `methodology_framework`
- `low`
- `l0`
- `limited`

但前端 `GuidanceCard` 原先只对 `general_method_only` 展示“通用方法论”覆盖边界。这会造成一类隐蔽问题：后端已经降级了 `task_reframe` / `project_viability_judgment` / `primary_risk`，但卡片上没有显示“覆盖边界”模块，用户只能从正文语气里推断系统正在诚实封顶。

### 10.17.1 机制调整

1. **低覆盖枚举归一显示**  
   `GuidanceCard` 现在会把 `methodology_framework`、`l0`、`low`、`limited` 与 `general_method_only` 统一展示为：

   - 标签：`通用方法论`
   - 描述：`当前只能先按通用方法论重构，不应伪装成专科判断。`

2. **保持前端不暴露内部枚举**  
   用户看到的是自然语言覆盖边界，不会看到 `l0`、`methodology_framework`、`limited` 等内部状态值。

3. **与后端承诺深度保持一致**  
   后端低覆盖降级和前端覆盖模块现在使用同一组语义等级，避免“后端已降级、前端未提示”的断裂。

### 10.17.2 防回归标准

| 项 | 标准 |
|---|---|
| `general_method_only` | 显示覆盖边界模块 |
| `methodology_framework` | 显示覆盖边界模块 |
| `l0` / `low` / `limited` | 显示覆盖边界模块 |
| 前端文案 | 只显示“通用方法论”等用户语言，不显示内部枚举说明 |

### 10.17.3 本轮验证

```bash
npm test -- GuidanceCard.test.tsx --runInBand
npm test -- ConversationChat.test.tsx GuidanceCard.test.tsx --runInBand
```

验证结果：

| 验证项 | 结果 |
|---|---|
| GuidanceCard 覆盖边界聚焦测试 | `10 passed` |
| ConversationChat + GuidanceCard 聚焦测试 | `16 passed` |

---

## 10.18 v1.15 smoke 首屏最终态验收

本轮处理的是真实 LLM smoke 自身的旧机制惯性。虽然生产路由已经取消异步替换，但 smoke 脚本仍保留“首屏不是最终态时继续轮询 session”的逻辑。这样会让排查重新滑回旧假设：似乎首屏可以先返回临时状态，再等待后台增强。

需求重构新架构的验收口径应更严格：

> 第一响应必须已经是最终需求重构结果。要么 `llm/used`，要么 `llm_partial/partial`，要么明确语义兜底失败原因；不能等待异步替换。

### 10.18.1 机制调整

1. **未知首屏状态直接失败**  
   若首屏不是 LLM used/partial，也不是明确 terminal failure 或 semantic fallback，smoke 直接报错：

   ```text
   first response was not a final fused demand reconstruction result
   ```

2. **不再读取 session 等后台替换**  
   smoke 不再通过 `/api/sessions/{session_id}` 轮询等待 LLM 接管。隐藏保留 `--poll-seconds` / `--timeout-seconds` 仅用于命令兼容，不再作为需求重构 smoke 行为依据。

3. **旧 pending 仍然快速失败**  
   `rule_pending_llm` / `semantic_pending_llm` / `scheduled` 仍按旧异步路径残留处理，直接提示重启后端或检查运行态是否加载当前 worktree。

### 10.18.2 防回归标准

| 项 | 标准 |
|---|---|
| LLM 成功 | 首屏 `llm/used` 或 `llm_partial/partial` 直接通过 |
| 旧 pending | 直接失败，不轮询 |
| 未知处理中状态 | 直接失败，不轮询 |
| 语义兜底 | 直接失败，并输出配置/错误诊断 |

### 10.18.3 本轮验证

```bash
.conda\python.exe -B -m pytest tests\unit\test_smoke_demand_reconstruction_llm_script.py -q
.conda\python.exe -B -m py_compile scripts\smoke_demand_reconstruction_llm.py
```

验证结果：

| 验证项 | 结果 |
|---|---|
| smoke 首屏最终态聚焦测试 | `5 passed` |
| smoke 脚本编译 | 通过 |

---

## 10.19 v1.16 LLM 诊断字段后台化

本轮处理的是用户侧仍残留的 LLM 诊断文案。需求重构主架构要求：规则、算法、LLM 在后台融合，前台只展示一个综合后的需求重构版本。因此 `insight_source`、`llm_status` 这类字段应服务后台排查和 smoke 验收，不应变成用户侧状态徽标。

此前前端会在 LLM 成功时显示：

```text
模型洞察已介入
```

并把 `insight_packet` 模块标题显示为：

```text
模型洞察
```

这虽然能帮助调试，但会把“模型是否介入”变成用户体验的一部分，重新制造“规则版 / LLM 版”的心理分裂。

### 10.19.1 机制调整

1. **移除模型参与状态徽标**  
   需求重构卡片不再根据 `llm_status` / `insight_source` 显示：

   - `模型洞察已介入`
   - `模型洞察失败`
   - `模型洞察未采纳`

   这些状态仍保留在后台 summary / smoke / 日志中，用于排查，不进入用户界面。

2. **`insight_packet` 改为用户语言**  
   前端仍展示 `chosen_hypothesis`、`core_tension`、`hypotheses` 等有用判断，但模块标题从 `模型洞察` 改为 `判断依据`。

3. **保留综合判断，不暴露生成来源**  
   用户看到的是系统当前的判断依据、覆盖边界、关键取舍和条件清单，而不是“这段由 LLM 生成”。

### 10.19.2 防回归标准

| 项 | 标准 |
|---|---|
| LLM 成功 | 不显示 `模型洞察已介入` |
| LLM 失败/未采纳 | 不显示 `模型洞察失败` / `模型洞察未采纳` |
| insight packet | 以 `判断依据` 呈现，不显示 `模型洞察` |
| 后台诊断 | `llm_status` / `insight_source` 仍可供 smoke 与日志排查 |

### 10.19.3 本轮验证

```bash
npm test -- ConversationChat.test.tsx GuidanceCard.test.tsx --runInBand
```

验证结果：

| 验证项 | 结果 |
|---|---|
| ConversationChat + GuidanceCard 前端聚焦测试 | `16 passed` |

---

## 10.20 v1.17 LLM Prompt 语义契约透传

本轮处理的是“算法已经进入蓝图，但 LLM 是否拿到完整算法脚手架”的闭环问题。需求重构的主架构要求 LLM 不是自由写作，也不是只看规则蓝图补文案，而是在项目语义理解器输出的结构化契约上做受控综合。

### 10.20.1 问题

此前 prompt 已经包含：

1. 用户原文。
2. `semantic_axes`。
3. `main_tensions`。
4. `missing_slots`。
5. `knowledge_coverage_ceiling`。
6. `semantic_candidate_set`。
7. `archetype`。
8. 当前规则蓝图。

但仍缺两个关键输入：

1. **`classification`**  
   包含项目类型、置信度、覆盖缺口、知识缺口票据等判断，是项目语义理解器的分类结果。

2. **`context_vector`**  
   包含主体画像、驱动类型、关系/运营语义等向量，是把“项目语义理解器”从词表判断提升到语境判断的关键材料。

如果 LLM 缺少这两块，它仍能看到规则蓝图和主矛盾，但对“为什么这个项目被判为某类”“置信度是否足够”“主体画像与运营驱动是什么”的理解会不完整。

### 10.20.2 调整

`DemandReconstructionInsightProtocol.build_prompt()` 的结构化上下文现在补入：

```json
{
  "classification": "...",
  "context_vector": "...",
  "context_source": "..."
}
```

同时补充 prompt 约束：

```text
治理信号只作为后台覆盖边界，不要把 coverage_gap、knowledge_gap_ticket、review_queue 等内部 code 写给用户。
```

这样 LLM 可以利用治理信号调整语气和承诺深度，但不会把内部治理字段暴露为用户文案。

### 10.20.3 防回归标准

| 项 | 标准 |
|---|---|
| 分类结果 | prompt 包含 `classification` 与置信度 |
| 语义向量 | prompt 包含 `context_vector` 与主体/驱动信号 |
| 主矛盾 | prompt 包含排序后的 tension title/prompt |
| 缺失槽 | prompt 包含 user-visible missing slot note |
| 治理信号 | prompt 可读到后台治理 signal，但明确禁止写给用户 |

### 10.20.4 本轮验证

```bash
.conda\python.exe -B -m pytest tests\services\test_demand_reconstruction_service.py::test_insight_prompt_receives_full_project_semantic_contract tests\services\test_demand_reconstruction_service.py::test_insight_prompt_demotes_rule_blueprint_to_constraints_and_requires_hypotheses tests\services\test_demand_reconstruction_service.py::test_llm_insight_layer_rewrites_the_rule_blueprint_when_available tests\services\test_demand_reconstruction_service.py::test_llm_partial_insight_is_salvaged_instead_of_full_rule_fallback -q
```

验证结果：

| 验证项 | 结果 |
|---|---|
| LLM prompt 语义契约与相邻融合行为 | `4 passed` |

---

## 10.21 v1.18 前端结构化洞察展示

本轮处理的是“LLM 已按结构化协议输出，但前端是否能完整承接”的问题。后端 prompt 要求 `insight_packet.core_tension` 使用结构化对象：

```json
{
  "a": "张力一端",
  "b": "张力另一端",
  "why_it_matters": "为什么会改变判断"
}
```

此前前端只识别字符串型 `core_tension`。如果 LLM 按协议输出对象，用户侧“判断依据”模块会显示 `chosen_hypothesis` 与 `hypotheses`，但核心矛盾本身会被静默跳过。这会削弱“综合版本”的可解释性。

### 10.21.1 调整

`GuidanceCard` 现在同时支持两种形态：

1. 字符串型：

```json
"core_tension": "作品冲动与长期生活之间的冲突"
```

2. 对象型：

```json
"core_tension": {
  "a": "复健训练",
  "b": "家庭日常",
  "why_it_matters": "两者会决定通道尺度、器械停放和照护动线。"
}
```

对象型会被转译为用户语言：

```text
核心矛盾：复健训练与家庭日常：两者会决定通道尺度、器械停放和照护动线。
```

### 10.21.2 防回归标准

| 项 | 标准 |
|---|---|
| 结构化 core_tension | `{a,b,why_it_matters}` 能显示为“核心矛盾”文本 |
| 字符串 core_tension | 仍保持原有显示 |
| 诊断字段 | `insight_source`、`llm_status`、`quality_report`、`governance_signals` 不显示给用户 |
| 用户语言 | 模块标题仍为“判断依据”，不出现“模型洞察” |

### 10.21.3 本轮验证

```bash
npm test -- GuidanceCard.test.tsx --runInBand --testNamePattern="structured core tension"
npm test -- GuidanceCard.test.tsx --runInBand
```

验证结果：

| 验证项 | 结果 |
|---|---|
| 结构化 core_tension 聚焦测试 | `1 passed` |
| GuidanceCard 全文件测试 | `11 passed` |

---

## 10.22 v1.19 Smoke 首屏最终融合口径

本轮处理的是 smoke 脚本的验收表述一致性。当前架构允许两类首屏合格状态：

1. `insight_source=llm` 且 `llm_status=used`
2. `insight_source=llm_partial` 且 `llm_status=partial`

第二种不是旧异步补丁，也不是失败状态，而是字段级质量门修补后的首屏融合结果：可用字段来自 LLM，不合格字段由规则蓝图补洞。它符合“单次首屏综合产物”的架构目标。

此前 `scripts/smoke_demand_reconstruction_llm.py` 的行为已允许 `llm_partial/partial` 通过，但最终汇总仍写成：

```text
reached LLM used
```

这会误导运行态验收，让人以为只有 `llm/used` 才算通过。

### 10.22.1 调整

smoke 汇总文案改为：

```text
reached final fused first response
```

含义是：

1. 首屏已经是最终态，不等待异步替换。
2. `llm/used` 与 `llm_partial/partial` 均为有效融合。
3. `semantic_fallback`、`invoke_failed`、`quality_rejected`、`invalid_json`、`empty_response` 仍按 LLM 未成功介入处理。
4. `rule_pending_llm`、`semantic_pending_llm`、`scheduled` 仍按旧异步路径残留直接失败。

### 10.22.2 防回归标准

| 项 | 标准 |
|---|---|
| LLM used | 首屏通过 |
| LLM partial | 首屏通过，汇总称为 final fused first response |
| semantic fallback | smoke 失败，并输出本地 LLM 配置诊断 |
| legacy pending | smoke 失败，并提示后端仍是旧异步路径 |
| 汇总文案 | 不再写 `reached LLM used` |

### 10.22.3 本轮验证

```bash
.conda\python.exe -B -m pytest tests\unit\test_smoke_demand_reconstruction_llm_script.py::test_demand_reconstruction_smoke_summary_accepts_partial_fused_result -q
.conda\python.exe -B -m pytest tests\unit\test_smoke_demand_reconstruction_llm_script.py -q
.conda\python.exe -B -m py_compile scripts\smoke_demand_reconstruction_llm.py
```

验证结果：

| 验证项 | 结果 |
|---|---|
| partial 首屏融合汇总口径测试 | `1 passed` |
| smoke 脚本单测 | `6 passed` |
| smoke 脚本编译 | 通过 |

---

## 10.23 v1.20 隔离后端真实 smoke 验收与 timeout 修正

本轮处理的是真实运行态验收中的工具缺口。`scripts/smoke_demand_reconstruction_llm.py` 已暴露 `--timeout-seconds` 参数，默认值为 120 秒，但实际首屏 POST 仍写死 `timeout=30`。在当前同步融合架构下，需求重构 LLM 可能需要等待 provider fallback 链路或较长首包生成，30 秒会把真实可成功的首屏融合误判为请求超时。

### 10.23.1 调整

smoke 脚本的首屏请求超时改为使用命令行传入的 `timeout_seconds`：

```text
http.post(..., timeout=timeout_seconds)
```

含义是：

1. smoke 验收超时由调用方显式控制。
2. 默认 120 秒可以覆盖常规同步融合等待。
3. 需要验证完整 fallback 链路时，可通过 `--timeout-seconds 180` 放宽。
4. 该参数不恢复旧轮询语义；首屏仍必须直接返回最终融合或明确兜底。

### 10.23.2 隔离运行态证据

为了避免误连 8001 上的旧后端进程，本轮使用独立端口 `8011` 启动当前工作树后端，并只运行代表性用例 `return-home-house`。

运行方式：

```powershell
# 后端隔离端口
$env:BACKEND_HOST='127.0.0.1'
$env:BACKEND_PORT='8011'
$env:BACKEND_PORT_CONFLICT_POLICY='adopt'
.\.conda\python.exe -B scripts\run_server_production.py

# smoke 验收
.\.conda\python.exe -B scripts\smoke_demand_reconstruction_llm.py --base-url http://127.0.0.1:8011 --case return-home-house --timeout-seconds 180
```

关键输出：

```text
health_status=200
[1/1] return-home-house
  initial source=llm, status=used
PASS return-home-house: session=conv-20260619071622-a83c9bb7, elapsed=77.8s, source=llm, status=used
ALL PASSED: 1/1 demand-reconstruction cases reached final fused first response.
```

后端日志同时显示：

```text
[DemandReconstructionLLM] direct call succeeded: model=qwen/qwen3.7-max, elapsed_ms=75892
[DemandReconstruction] semantic alignment shadow: clean
[dual_mode] DemandReconstruction handled: source=llm, llm_status=used
```

结论：

1. 当前工作树后端已不再返回 `rule_pending_llm / scheduled`。
2. 需求重构首屏可以直接得到 `llm/used` 的最终融合结果。
3. LLM 实际介入链路可观测，且语义一致性门结果为 clean。
4. 该用例首屏耗时约 77.8 秒，说明同步融合方向成立，但性能体验仍需要后续单独优化。

### 10.23.3 本轮验证

```bash
.conda\python.exe -B -m pytest tests\unit\test_smoke_demand_reconstruction_llm_script.py::test_demand_reconstruction_smoke_uses_configured_request_timeout -q
.conda\python.exe -B -m pytest tests\unit\test_smoke_demand_reconstruction_llm_script.py -q
.conda\python.exe -B -m py_compile scripts\smoke_demand_reconstruction_llm.py
```

验证结果：

| 验证项 | 结果 |
|---|---|
| timeout 参数生效聚焦测试 | `1 passed` |
| smoke 脚本单测 | `8 passed` |
| smoke 脚本编译 | 通过 |
| 隔离后端真实 smoke | `return-home-house` 通过，首屏 `llm/used` |

---

## 10.24 v1.21 Prompt 压缩与固定步骤标题前置质量门

v1.20 的真实 smoke 已证明同步融合链路成立，但也暴露出两个后续问题：

1. prompt 过长。`return-home-house` 样本在未压缩前真实请求约 `prompt_chars=12939`，单次 LLM 调用耗时约 `75.9s`。
2. LLM 偶发输出固定内部步骤标题，例如 `成立路径`，会被语义一致性门以 `generic_step_title_visible` 拦截，导致原本有价值的 LLM 内容被整份打回 `semantic_fallback`。

### 10.24.1 Prompt 压缩

`DemandReconstructionInsightProtocol.build_prompt()` 不再把 `classification`、`context_vector`、`semantic_axes`、`semantic_candidate_set` 和完整 `rule_plan` 原样 JSON 化给 LLM，而是构造 LLM 专用摘要包：

| 输入 | 保留 | 压缩掉 |
|---|---|---|
| classification | 项目类型、置信度、覆盖缺口、澄清问题 | 完整 routing、space_axis 展开、内部 profile 细节 |
| context_vector | 非空语义向量 | Unknown 占位 |
| semantic_axes | 非空轴命中 | 空轴 |
| main_tensions | title / prompt / score / related_options | 过长原始对象 |
| missing_slots | user_visible_note / note / label | 内部冗余字段 |
| semantic_candidate_set | id / score / role / evidence / counter_evidence | 长尾候选 |
| rule_plan | 核心判断、分叉、未知项、少量 sections、组件意图 | 完整后台 routing 与冗余结构 |

压缩目标不是减少算法信息，而是把算法信息变成 LLM 能直接消费的“项目语义契约”。

本轮新增预算测试要求真实返乡民居样本 prompt 低于 `8000` 字符，同时仍包含：

- `classification`
- `context_vector`
- `semantic_candidate_set`
- `task_reframe`
- 规则蓝图约束说明

实测同一类样本压缩后本地 prompt 长度约 `4443` 字符；真实后端日志显示 `prompt_chars=5834`。

### 10.24.2 固定步骤标题前置质量门

此前 `generic_step_title_visible` 只在最终语义一致性门中触发，属于“最后一票否决”。这样会产生不合理结果：LLM 的核心判断、风险、追问都可用，但因为一个 section 标题写成 `成立路径`，整份 LLM 蓝图被打回。

v1.21 将这类问题前移到 LLM 协议质量门：

```text
sections.title 禁止使用：
选择判断路径 / 成立路径 / 硬约束 / 取舍边界
```

如果 LLM 命中这些固定内部步骤标题：

1. 只拒绝 `sections` 字段。
2. 其它合格字段继续采纳。
3. 结果进入 `llm_partial/partial` 或在其它字段均合格时继续保持融合路径。
4. 避免 alignment gate 最后整份打回。

### 10.24.3 压缩后真实 smoke 复验

使用独立端口 `8013` 启动当前工作树后端，并运行：

```powershell
.\.conda\python.exe -B scripts\smoke_demand_reconstruction_llm.py --base-url http://127.0.0.1:8013 --case return-home-house --timeout-seconds 180
```

关键输出：

```text
[1/1] return-home-house
  initial source=llm, status=used
PASS return-home-house: session=conv-20260619073144-09c90fcb, elapsed=68.1s, source=llm, status=used
ALL PASSED: 1/1 demand-reconstruction cases reached final fused first response.
```

后端日志：

```text
[DemandReconstructionLLM] direct call succeeded: model=qwen/qwen3.7-max, prompt_chars=5834, content_chars=2905, elapsed_ms=66174
[DemandReconstruction] semantic alignment shadow: clean
[dual_mode] DemandReconstruction handled: source=llm, llm_status=used
```

结论：

1. prompt 体量已明显下降。
2. 首屏仍然是 `llm/used` 的融合结果。
3. alignment gate 为 clean。
4. 首屏耗时从上一轮 `77.8s` 降到本轮 `68.1s`，但仍偏慢；后续应继续治理模型选择、max_tokens、输出结构和流式体验。

### 10.24.4 本轮验证

```bash
.conda\python.exe -B -m pytest tests\services\test_demand_reconstruction_service.py::test_insight_prompt_compacts_runtime_context_without_losing_semantic_contract -q
.conda\python.exe -B -m pytest tests\services\test_demand_reconstruction_service.py::test_llm_sections_with_generic_internal_step_titles_are_salvaged_by_quality_gate -q
.conda\python.exe -B -m pytest tests\services\test_demand_reconstruction_service.py -q
.conda\python.exe -B -m pytest tests\unit\test_smoke_demand_reconstruction_llm_script.py -q
.conda\python.exe -B -m py_compile intelligent_project_analyzer\services\demand_reconstruction_insight_protocol.py scripts\smoke_demand_reconstruction_llm.py
```

验证结果：

| 验证项 | 结果 |
|---|---|
| prompt 压缩预算测试 | `1 passed` |
| 固定步骤标题前置质量门测试 | `1 passed` |
| 需求重构服务全量测试 | `161 passed` |
| smoke 脚本单测 | `8 passed` |
| py_compile | 通过 |
| 隔离后端真实 smoke | `return-home-house` 通过，首屏 `llm/used`，`prompt_chars=5834` |

---

## 10.25 v1.22 输出预算治理与真实耗时复验

v1.21 已将 prompt 体量压缩到可控范围，但真实运行仍有约 `68.1s` 首屏等待。日志显示主要耗时仍在单次 LLM 生成阶段，而非后端编排：

```text
prompt_chars=5834, content_chars=2905, elapsed_ms=66174
```

这说明只压缩输入还不够，输出预算也必须收紧。

### 10.25.1 调整

本轮做两类收敛：

1. **默认输出 token 预算收紧**

   `DEMAND_RECONSTRUCTION_LLM_MAX_TOKENS` 默认值从 `1800` 调整为 `1200`。环境变量仍可覆盖，适合不同部署按模型能力调节。

2. **本地运行配置同步**

   当前 `.env` 中需求重构专用配置同步为：

   ```text
   DEMAND_RECONSTRUCTION_LLM_MAX_TOKENS=1200
   ```

3. **Prompt 明确短输出约束**

   LLM 协议加入首屏预算要求：

   ```text
   输出要短，服务首屏判断，不写长报告；总输出控制在 1200 中文字以内。
   sections 最多 2 段，items 每段最多 2 条；每个字段只保留最关键判断。
   ```

### 10.25.2 真实 smoke 复验

使用独立端口 `8015` 启动当前工作树后端，并运行：

```powershell
.\.conda\python.exe -B scripts\smoke_demand_reconstruction_llm.py --base-url http://127.0.0.1:8015 --case return-home-house --timeout-seconds 180
```

关键输出：

```text
[1/1] return-home-house
  initial source=llm, status=used
PASS return-home-house: session=conv-20260619074101-3a39ab8b, elapsed=50.6s, source=llm, status=used
ALL PASSED: 1/1 demand-reconstruction cases reached final fused first response.
```

后端日志确认：

```text
[DemandReconstructionLLM] using direct compatible adapter: provider=openrouter, ..., max_tokens=1200
[DemandReconstructionLLM] direct call succeeded: model=qwen/qwen3.7-max, prompt_chars=5920, content_chars=2213, elapsed_ms=48770
[DemandReconstruction] semantic alignment shadow: clean
[dual_mode] DemandReconstruction handled: source=llm, llm_status=used
```

对比：

| 阶段 | prompt_chars | content_chars | smoke elapsed | 结果 |
|---|---:|---:|---:|---|
| v1.20 未压缩 | 12939 | 3371 | 77.8s | `llm/used` |
| v1.21 prompt 压缩 | 5834 | 2905 | 68.1s | `llm/used` |
| v1.22 输出预算收紧 | 5920 | 2213 | 50.6s | `llm/used` |

结论：

1. 输出预算收紧没有导致 JSON 截断。
2. 首屏仍保持 `llm/used`，alignment clean。
3. 真实耗时继续下降，但 `50s+` 仍不满足理想交互体验。
4. 后续性能优化不应再主要靠压 prompt，而应进入模型路由、流式首屏、轻量模型/轻量 schema、后台补全等产品级体验设计。

### 10.25.3 本轮验证

```bash
.conda\python.exe -B -m pytest tests\unit\test_demand_reconstruction_llm.py -q
.conda\python.exe -B -m pytest tests\unit\test_smoke_demand_reconstruction_llm_script.py -q
.conda\python.exe -B -m pytest tests\services\test_demand_reconstruction_service.py -q
.conda\python.exe -B -m py_compile intelligent_project_analyzer\services\demand_reconstruction_llm.py intelligent_project_analyzer\services\demand_reconstruction_insight_protocol.py scripts\smoke_demand_reconstruction_llm.py
```

验证结果：

| 验证项 | 结果 |
|---|---|
| 需求重构 LLM 配置测试 | `11 passed` |
| smoke 脚本单测 | `8 passed` |
| 需求重构服务全量测试 | `162 passed` |
| py_compile | 通过 |
| 隔离后端真实 smoke | `return-home-house` 通过，首屏 `llm/used`，`max_tokens=1200` |

---

## 10.26 v1.23 入口分诊纯方法论窄门

v1.22 之后，规则蓝图主体已经由 registry 碎片、主矛盾、缺失槽位和覆盖边界共同驱动。但入口层仍有一个细分风险：

```text
社区文化空间应该怎么研究在地性、公共性和运营模式，请给出分析框架和判断方法。
```

这类输入有空间语义，也有“研究/怎么看”语义，但没有具体项目锚点。如果直接进入需求重构，会把纯方法论讨论误包装为项目行动蓝图，违背“入口分诊前置”的主架构。

### 10.26.1 调整

共享入口函数 `should_enter_demand_reconstruction()` 增加纯方法论窄门：

1. 命中“方法论 / 分析框架 / 判断方法 / 研究方法 / 如何研究 / 怎么研究”等表达；
2. 且没有明确“重构需求 / 帮我重构 / 梳理需求 / 请提出完整设计”等项目重构意图；
3. 则不进入需求重构，交给入口流或方法论响应处理。

该窄门不屏蔽 cultural_research 蓝图。类似“研究某文化对象对某空间的启发”仍可进入研究路径，因为它是研究任务蓝图，不是泛方法论问答。

### 10.26.2 定向验证

```bash
.conda\python.exe -B -m pytest tests/services/test_demand_reconstruction_service.py::test_spatial_research_method_prompt_without_project_anchor_is_not_taken_by_demand_reconstruction tests/services/test_demand_reconstruction_service.py::test_methodology_only_prompt_is_not_taken_by_demand_reconstruction tests/services/test_demand_reconstruction_service.py::test_deep_research_prompt_is_routed_without_pretending_to_complete_evidence tests/services/test_demand_reconstruction_service.py::test_cultural_research_prompt_does_not_inject_yaji_club_context_for_other_topics tests/services/test_demand_reconstruction_service.py::test_citizen_farm_visitor_center_uses_public_cultural_experience_plan tests/services/test_demand_reconstruction_service.py::test_kunqu_old_house_uses_performance_heritage_fragments_not_farm_fragments -q
```

结果：

| 验证项 | 结果 |
|---|---|
| 纯空间研究方法问题 | 不进入需求重构 |
| 通用方法论问题 | 不进入需求重构 |
| cultural_research 研究蓝图 | 保持进入深度研究路径 |
| 市民农场 / 昆曲老宅具体项目 | 保持进入需求重构 |
| 定向测试 | `6 passed` |

---

## 10.27 v1.24 smoke 输出预算可观测性

v1.22 将需求重构 LLM 输出预算收紧为 `max_tokens=1200`，但真实 smoke 输出中只能从后端日志确认该值。为了让排查链路更直接，smoke 脚本的本地 LLM 配置摘要补充输出 `max_tokens`。

### 10.27.1 调整

`scripts/smoke_demand_reconstruction_llm.py` 的本地诊断输出由：

```text
local LLM config: ready=True, use_llm=True, direct=True, auto_fallback=False, providers=[...], blocked=[none]
```

扩展为：

```text
local LLM config: ready=True, use_llm=True, direct=True, auto_fallback=False, max_tokens=1200, providers=[...], blocked=[none]
```

该信息来自 `describe_demand_reconstruction_llm_config()` 的红线脱敏配置快照，不展示 API key。

### 10.27.2 验证

```bash
.conda\python.exe -B -m pytest tests/unit/test_smoke_demand_reconstruction_llm_script.py -q
```

结果：`8 passed`。

---

## 10.28 v1.25 Entry 承接纯方法论分诊

v1.23 已在需求重构入口增加纯方法论窄门，但完整入口链路还需要后续 `SchemeAdvisorEntryService` 使用同一判断。否则会出现：

```text
DemandReconstructionService.should_handle(...) = False
SchemeAdvisorEntryService.handle_message(...) = project intake
```

也就是需求重构已经让出，但 Entry 又把同一条“空间研究方法/分析框架”输入当作具体项目启动。

### 10.28.1 调整

`SchemeAdvisorEntryService._classify_input()` 接入共享函数 `is_methodology_discussion_request()`：

1. 纯“方法论 / 分析框架 / 判断方法 / 研究方法 / 怎么研究”类输入进入 methodology profile；
2. 带有明确项目重构意图的输入保留项目入口，例如“请先帮我重构需求，并说明后续分析框架”；
3. 竞标策略、纯命名文案、参考资料请求原有分流保持不变。

### 10.28.2 定向验证

```bash
.conda\python.exe -B -m pytest tests/services/test_scheme_advisor_entry_v2_restore.py::test_spatial_research_method_prompt_enters_methodology_path_not_project_intake tests/services/test_scheme_advisor_entry_v2_restore.py::test_concrete_project_with_method_frame_still_enters_project_intake tests/services/test_scheme_advisor_entry_v2_restore.py::test_formal_milk_tea_prompt_enters_design_taskbook_entry_flow tests/services/test_scheme_advisor_entry_v2_restore.py::test_competition_strategy_prompt_enters_methodology_path_not_project_intake -q
.conda\python.exe -B -m py_compile intelligent_project_analyzer\services\scheme_advisor_entry_service.py intelligent_project_analyzer\services\scheme_advisor_semantic_axes.py
```

结果：

| 验证项 | 结果 |
|---|---|
| 纯空间研究方法输入 | Entry 进入 methodology profile |
| 带“重构需求”的具体项目 | Entry 保持 project intake |
| 正式项目入口 | 保持进入设计任务书入口 |
| 竞标策略 | 保持 methodology path |
| 定向测试 | `4 passed` |
| py_compile | 通过 |

---

## 10.29 v1.26 前端首屏等待态

同步融合后，首屏质量提高，但真实 LLM 调用仍可能达到几十秒。前端不能继续只显示三个点，否则用户无法判断系统是在卡住、还是正在做需求重构。

### 10.29.1 调整

`ConversationChat` 的 loading 状态增加用户可理解的等待文案：

1. 最近一条用户消息像需求重构/项目简报时，显示：

   ```text
   正在重构需求
   正在融合项目语义、关键约束和下一步判断。
   ```

2. 普通追问 loading 显示中性文案：

   ```text
   正在整理回应
   正在根据上下文组织下一步回应。
   ```

3. 等待态不出现 `LLM`、`模型`、`规则蓝图`、`semantic`、`llm_status` 等内部状态词。

### 10.29.2 验证

```bash
npm test -- ConversationChat.test.tsx GuidanceCard.test.tsx --runInBand
```

结果：

| 验证项 | 结果 |
|---|---|
| 需求重构 loading 文案 | 通过 |
| 普通追问 loading 中性文案 | 通过 |
| 需求重构卡内部状态隐藏 | 通过 |
| GuidanceCard 组件回归 | 通过 |
| 前端聚焦测试 | `19 passed` |

---

## 10.30 v1.27 错域输出治理信号

此前 `coverage_gap` 和 `knowledge_gap_ticket` 已进入治理信号，但 alignment hard gate 拦下的错域输出只会回退到 semantic fallback，没有进入治理队列。这样虽然保护了用户首屏，但后台无法从单次需求重构结果追踪“哪个输出曾被错域门禁拦截”。

### 10.30.1 调整

当 LLM 融合蓝图被语义一致性硬门拒绝时，最终 fallback 蓝图会追加后台治理信号：

```json
{
  "code": "semantic_alignment_rejection",
  "track": "semantic_alignment",
  "review_queue": "wrong_domain_output_review",
  "severity": "P0",
  "source_codes": ["wrong_domain_reference"],
  "user_visible": false
}
```

该信号用于后台错域输出治理，不参与用户侧回复，也不显示在 `GuidanceCard`。

### 10.30.2 验证

```bash
.conda\python.exe -B -m pytest tests/services/test_demand_reconstruction_service.py::test_alignment_hard_gate_rejects_blocking_llm_blueprint_by_default tests/services/test_demand_reconstruction_service.py::test_demand_reconstruction_blueprint_surfaces_knowledge_gap_governance_signals_without_user_leakage -q
npm test -- ConversationChat.test.tsx GuidanceCard.test.tsx --runInBand
.conda\python.exe -B -m py_compile intelligent_project_analyzer\services\demand_reconstruction_service.py
```

结果：

| 验证项 | 结果 |
|---|---|
| alignment hard gate 错域治理信号 | 通过 |
| coverage/knowledge gap 治理信号回归 | 通过 |
| 前端不泄漏内部治理 code | 通过 |
| 前端聚焦测试 | `19 passed` |
| py_compile | 通过 |

---

## 10.31 v1.28 具体项目锚点优先级修正

聚焦验收时发现一个与主架构直接相关的入口缺口：

```text
成都历史街区里的一家汽车品牌体验店，需要将城市记忆转译为品牌空间，给出建议。
```

这条输入是明确具体项目，但同时包含“转译 / 给出建议”这类泛研究或建议词。旧判定中，语义轴能识别到 `brand_differentiation`、`heritage_context` 和 `analogy_translation`，但空间域与输入意图不足；具体项目锚点词表又没有覆盖“体验店 / 品牌空间 / 历史街区”，导致它被 `problem_mode` 拦截，未进入需求重构。

### 10.31.1 调整

`has_concrete_project_anchor()` 补充具体项目锚点：

1. `体验店`；
2. `品牌空间`；
3. `历史街区`。

该调整不是新增蓝图模板，也不是放宽所有建议型问题，而是把“具体空间对象 + 场地语境 + 品牌空间任务”的项目锚点补入入口分诊。纯方法论输入仍然被拦截。

### 10.31.2 验证

```bash
.conda\python.exe -B -m pytest tests/services/test_demand_reconstruction_service.py::test_concrete_brand_experience_advice_is_not_routed_to_deep_research tests/services/test_demand_reconstruction_service.py::test_concrete_brand_experience_reconstruction_is_not_routed_to_deep_research tests/services/test_demand_reconstruction_service.py::test_spatial_research_method_prompt_without_project_anchor_is_not_taken_by_demand_reconstruction tests/services/test_scheme_advisor_entry_v2_restore.py::test_spatial_research_method_prompt_enters_methodology_path_not_project_intake tests/services/test_scheme_advisor_entry_v2_restore.py::test_concrete_project_with_method_frame_still_enters_project_intake -q
.conda\python.exe -B -m pytest tests/services/test_demand_reconstruction_service.py tests/services/test_scheme_advisor_entry_v2_restore.py tests/api/test_scheme_advisor_entry_route.py tests/unit/test_demand_reconstruction_llm.py tests/unit/test_smoke_demand_reconstruction_llm_script.py -q
npm test -- ConversationChat.test.tsx GuidanceCard.test.tsx --runInBand
.conda\python.exe -B -m py_compile intelligent_project_analyzer\services\demand_reconstruction_service.py intelligent_project_analyzer\services\scheme_advisor_entry_service.py intelligent_project_analyzer\services\scheme_advisor_semantic_axes.py intelligent_project_analyzer\services\demand_reconstruction_llm.py intelligent_project_analyzer\services\demand_reconstruction_insight_protocol.py intelligent_project_analyzer\services\demand_reconstruction_output_planner.py intelligent_project_analyzer\services\demand_reconstruction_context_adapter.py scripts\smoke_demand_reconstruction_llm.py
```

结果：

| 验证项 | 结果 |
|---|---|
| 具体品牌体验项目建议输入 | 进入需求重构，不进入 deep research |
| 纯空间研究方法输入 | 仍不进入需求重构 |
| 入口分诊相邻回归 | `5 passed` |
| 后端聚焦套件 | `226 passed` |
| 前端聚焦测试 | `19 passed` |
| py_compile | 通过 |

---

## 11. 与专题 H 的关系

专题 H 已定义：

> 需求重构是设计任务书正式问诊前的理解力证明阶段。

本专题补充的是：

> 需求重构如何通过算法机制稳定地产生“理解力证明”。

二者关系如下：

| 文档 | 关注点 |
|---|---|
| 专题 H：需求重构到设计任务书升级机制 | 产品定位、阶段责任、用户体验、任务书承接 |
| 本专题：需求重构阶段算法优化 | 算法链路、规则与 LLM 配合、候选解释、质量门、治理闭环 |

专题 H 解决“需求重构是什么”；本专题解决“需求重构怎样不跑偏、不模板化、可泛化”。

---

## 12. 最终建议

需求重构阶段的最优架构不是规则优先，也不是 LLM 优先，而是：

```text
规则负责稳定性。
算法负责理解结构。
LLM 负责综合表达。
质检负责边界。
治理负责进化。
```

更具体地说：

1. 入口分诊决定是否进入需求重构。
2. 项目语义理解器生成上下文事实包。
3. 语义轴算法生成主矛盾和候选解释。
4. 知识覆盖算法决定输出深度。
5. 规则蓝图只做内部结构和兜底。
6. LLM 基于完整算法包生成唯一用户版。
7. 质量门分成硬边界、语义一致性和表达质量三层。
8. 旧模板拆成可组合知识碎片库。
9. 组件化 UI 作为中期表达层升级，不作为第一阶段算法优化前置条件。
10. 误判与知识缺口进入治理队列。

如果只继续增加规则分支，系统会越来越像枚举表；如果只依赖 LLM，系统会失去稳定边界。真正合理的方向，是把已有算法资产接入需求重构主链路，让规则蓝图从“前台答案”退回“后台骨架”，让 LLM 从“事后补写”变成“受控综合生成”，并在 LLM 不可用时用算法语义包兜底。

最终目标：

> 需求重构不再是快速整理用户输入，而是一次可追溯、可治理、可泛化的项目语义理解。
