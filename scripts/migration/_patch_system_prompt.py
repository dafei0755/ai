import sys

filepath = r"d:\11-20\langgraph-design\intelligent_project_analyzer\config\prompts\requirements_analyst_phase2.yaml"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

start_marker = "  ### **[v10] A/B/C 三阶段分析流程（占位符，待全量替换）**"
end_marker = "  4. **adversarial_question** - 如果你是这个分析的批评者，你会对这个层的分析提出最尖锐的质难是什么？（避免温和，质难就是质难）"

s = content.find(start_marker)
e = content.find(end_marker) + len(end_marker)

if s == -1 or e == len(end_marker) - 1:
    print("ERROR: markers not found", s, e)
    sys.exit(1)

new_block = """\
  ## Phase A：现实画像（全量强制，回答 WHO + WHAT）

  本阶段所有组件必须执行。不得跳过。

  **A1：事实原子化（MECE解构）**
  将输入分解为不可再分的事实筐子。不进行任何推断，只提取确认的事实。
  - 识别：用户是谁？要什么？为什么？约束是什么？
  - 输出：A1_facts 列表

  **A2：利益相关者系统（前置，决定后续分析视角）**
  ⚠️ 神经：利益相关者系统直接影响后续所有层的分析视角，必须先识别。
  - 识别：投资人/业主、终端消费者、运营者（至少3类）
  - 分析：各方关注点差异（时间视角/风险偏好/价值排序/审美取向）
  - 识别：冲突/协同/权力动态/隐性利益相关者
  - 输出：A2_stakeholders（包含冲突、协同、决策层级）

  **A3a：用户深度建模**（知道利益相关者后再建模）
  - 基础视角（必选）：心理学 / 社会学 / 美学 / 情感 / 仪式
  - 扩展视角（条件激活）：商业/技术/生态/文化/政治
  - 输出：A3_user_model 对象
  - 人性维度（贯穿全程）：emotional_landscape / spiritual_aspirations / psychological_safety_needs / ritual_behaviors / memory_anchors

  **A3b：品牌DNA深层解码**（当提及品牌/风格标签时触发）
  - 品牌基因层：起源故事 + 设计哲学 + 文化根基
  - 审美基调层：色彩系统 + 形态语言 + 情绪基调
  - 空间转译层：品牌元素→空间表达转译规则 + 品牌禁忌的空间模式
  - 输出：A3_brand_dna（只在触发时输出）

  **A4：约束地图（新增——PM视角必填层）**
  识别不可改变的外部局限，后续所有分析必须在此边界内岩行。
  - 预算 / 工期 / 法规规范 / 物理现实（户型/面积/结构）
  - 关键识别哪些约束是确定的 vs 可谈判的
  - 输出：A4_constraints（包含确定项/弹性项/未知项）

  ✅ Phase A 门控：A1-A4 全部完成且无空字段 → 进入 Phase B

  ---

  ## Phase B：需求挖掘（深度挑战，回答 WHY）

  B1/B2/B3强制。B4条件激活（需B3深度铺垫）。B5必须执行。

  **B1：核心张力识别（最尖锐对立面）**
  利益相关者和需求之间最核心的张力是什么？
  - 展示 vs 私密 / 效率 vs 体验 / 功能 vs 情感 / 在地 vs 国际
  - 输出：B1_core_tension 公式

  **B2：JTBD 任务定义（空间被雇佣完成什么？）**
  - 公式：为[深层身份]打造[空间]，雇佣空间完成[任务1]与[任务2]
  - 任务必须靠近身份认同层，不能停在功能层
  - 输出：B2_project_task

  **B3：五层为什么深度追问（必须到达L4情感层）**
  ⚠️ 神经：必须追问到情感层（L4）或身份层（L5），停在功能层即为失败。
  - L1 What：用户原话引用
  - L2 Why表层：直接可见的原因
  - L3 Why行为：行为模式是什么
  - L4 Why情感：对抗什么恐惧？渴望什么满足？（必达）
  - L5 Why身份：渴望成为什么样的人？（理想到达）
  - 输出：B3_five_whys_analysis 对象

  **B4：第一性原理裸需求【条件触发：B3已达 L4+ 土壤足够】**
  为什么B3后才做：B3臭问到情感层后才知道哪些是"惯例期待"，哪些是"真实需求"。
  - 四层剔除：风格标签 → 行业惯例 → 参考案例 → 社交驱动
  - 剔除后达到：用户对[光/距离/控制感/触觉/自主性]的基本需要
  - 输出：B4_first_principles（naked_requirement + stripped_conventions + confidence_note）

  **B5：假设审计【在挖掘末尾锁定假设边界，而非事后回顾】**
  ⚠️ 神经：其他层的推断已加入了假设。在B阶段结束时锁定假设边界，替代在C阶段之后才发现。
  - 识别隐含假设：A2/A3/B3中有哪些未经验证的前提？
  - 生成反向假设：如果相反的情况为真会怎样？
  - 评估假设影响：如果假设错误，对设计的影响有多大？
  - 探索替代路径：有哪些被忽视的替代方案？
  - 深度与项目复杂度正相关：简单项目≥1个，中等≥3个，复杂≥5个
  - 输出：B5_assumption_audit（每个假设必含：assumption + counter + challenge_question + impact_if_wrong + alternative_approach）

  ✅ Phase B 门控：B3已达 L4+，B5已按项目复杂度完成足够假设数量 → 进入 Phase C

  ---

  ## Phase C：验证攻击（机械检验，回答 HOW VALID）

  C1/C5强制。C2/C3/C4/C6条件激活（见 component_activation_config）。

  **C1：锐度评分（门控，必需≥70）**
  对 Phase A+B 的分析质量打分：
  - 专一性：是否只适用于此用户？（禁止套话）
  - 可操作性：能否直接指导设计？（必须具体到可执行）
  - 深度：是否触及情感/身份层？
  - 矛盾性：是否揭示核心张力？
  - 证据性：是否有用户原话支撑？
  - 输出：C1_sharpness_score（0-100）

  🛑 C1 门控处：得分 < 70 → 返回 Phase B 重挖，不进行 C2-C6

  **C2：奥卡姆剃刀逆向检验【条件：C1≥70 或 B3追问链超过4跳】**
  1. 堆层检验：是否在用复杂理论解释一个本质简单的问题？（更简洁的解释胜出）
  2. 替代假设检验：是否存在更简洁且同等有效的解释？（记录保留复杂性的理由）
  - 输出：C2_razor_check（is_overcomplicated / simpler_alternative / reason_for_keeping_complexity）

  **C3：思想实验层【条件：complexity≥medium 或需求权重不明确】**
  为什么在C阶段：思想实验=验证工具而非发现工具。它测试 A+B 已经挖掘出的需求假设是否准确。
  - 如果预算无限：哪些需求会消失或改变？ → 区分真实偏好 vs 预算内妥协
  - 如果只能保留一个：选什么？ → 需求优先级的真实排序（逼迫选择）
  - 10年后最后悔：最后悔哪个决策？ → 时间维度的需求验证
  - 每个实验必须提供：假设前判断 + 假设后判断 + 设计启示
  - 输出：C3_thought_experiments

  **C4：系统性影响【商业/酒店/文化项目必选，纯私宅可选】**
  - 短期/中期/长期 × 社会/环境/经济/文化
  - 必识别至少2个非预期后果，并提供应对策略
  - 输出：C4_systemic_impact

  **C5：反套路化自检（强制，输出前必过）**
  禁用词出现即重写：
  - 情感套话："温馨舒适"、"有归属感"、"品质生活"、"家的感觉"
  - 功能套话："功能齐全"、"动线合理"、"空间利用率高"
  - 美学套话："简约大气"、"时尚现代"、"低调奢华"
  - 输出：C5_anti_cliche_check（包含替换记录）

  **C6：多视角对抗合成【条件：complexity≥medium 且 C1≥80】**
  B5假设审计是内部自检，C6是引入不同角色的外部攻击——两者不重复。
  - 竞争对手分析师：哪些需求并不特殊？你会如何利用此分析的弱点差异化攻击？
  - 恶魔代言人：最易被推翻的假设是哪个？提出更尖锐的替代性分析框架。
  - 10年后的用户：哪些决策10年后会后悔？那些是短期流行 vs 长期核心？
  - 局外人专家：行为经济学家/神经科学家会如何重新解读此需求？
  - 收敛盲点洞察：4个视角汇聚出单视角无法发现的核心盲点
  - 输出：C6_multi_perspective_synthesis

  ✅ Phase C 门控 + expert_handoff构建条件：
  C1≥70 ✔ C5通过 ✔ → 可构建 expert_handoff

  ---

  ## 专家接口构建

  上述三阶段都通过后，为每个专家角色提供：
  1. **critical_questions** — 需要此专家回答的关键问题
  2. **design_challenge_spectrum** — 设计挑战的可能立场谱
  3. **permission_to_diverge** — 授权专家挑战需求分析师判断
  4. **adversarial_question** — 如果你是这个分析的批评者，你会提出的最尖锐质难是什么？（避免温和，质难就是质难）"""

new_content = content[:s] + new_block + content[e:]

# Verify no surrogates
bad = [i for i, c in enumerate(new_content) if 0xD800 <= ord(c) <= 0xDFFF]
if bad:
    print(f"ERROR: {len(bad)} surrogate chars found")
    sys.exit(1)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"Done. File length: {len(new_content)} chars")
print(f"Replaced block: {e-s} chars -> {len(new_block)} chars")
