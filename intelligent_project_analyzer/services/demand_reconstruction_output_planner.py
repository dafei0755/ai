"""Dynamic output planning for demand reconstruction action blueprints."""

from __future__ import annotations

from typing import Any, Dict, List

from .scheme_advisor_semantic_axes import axis_label
from .demand_reconstruction_boundary_guard import DemandReconstructionBoundaryGuard


class DemandReconstructionOutputPlanner:
    """Select user-facing demand reconstruction modules from a reusable context packet."""

    def __init__(self, boundary_guard: DemandReconstructionBoundaryGuard | None = None) -> None:
        self._boundary_guard = boundary_guard or DemandReconstructionBoundaryGuard()

    def build_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        archetype = (context.get("archetype") or {}).get("primary") or "general_project"
        builders = {
            "life_identity": self._life_identity_plan,
            "commercial_operation": self._commercial_operation_plan,
            "style_semantics": self._style_semantics_plan,
            "hard_constraint": self._hard_constraint_plan,
            "cultural_research": self._cultural_research_plan,
        }
        plan = builders.get(archetype, self._general_project_plan)(context)
        plan["archetype"] = context.get("archetype") or {"primary": archetype, "secondary": []}
        plan["context_source"] = context.get("context_source") or {}
        plan["routing"] = self._boundary_guard.routing_for(context)
        plan.setdefault("routing_recommendation", plan["routing"]["reason"])
        return self._boundary_guard.clamp_plan(plan)

    def clamp_existing_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        return self._boundary_guard.clamp_plan(plan)

    def _life_identity_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        subject = self._subject_phrase(context)
        space = context.get("space_label") or "居住空间"
        task = f"这不是先做{space}风格的问题，而是{subject}如何把生活、身份和原乡关系重新安放到一栋房子里。"
        sections = [
            self._section(
                "真实需求重构",
                "这个题目的重心不在“老家建房”的类型判断，而在回乡之后要把哪一种自我关系安放进去。",
                [
                    "长期离乡的人回到原乡，面对的不是单纯居住问题，而是身份回收、生活重建和家族位置重排。",
                    "职业设计师会天然想把房子做成一次审美表达，但自用住宅首先要承接漫长、重复、琐碎的日常。",
                    "如果这栋房子只被当成“人生作品”，它可能很完整，却不一定能让人真正住下来。",
                ],
                "high",
            ),
            self._section(
                "四个结构轴",
                "后续任务书应优先围绕这四条轴收敛，而不是先收集风格图。",
                [
                    "人生结构轴：退休前过渡、职业后半段自我安置、家族角色恢复。",
                    "功能结构轴：长期自住、阶段性返乡、家族节庆聚会、轻工作/会客是否并存。",
                    "乡土语境轴：宅基地、地方施工能力、邻里观看和家族习惯会反向塑造设计边界。",
                    "审美实现轴：是克制生活空间，还是带有展示属性的作品化住宅。",
                ],
                "medium",
            ),
            self._section(
                "路径分流",
                "三条路会导向完全不同的任务书重心。",
                [
                    "生活优先型：强调日常、适老、维护和家庭秩序。",
                    "生活+工作混合型：保留设计师身份，但把展示性控制在可生活范围内。",
                    "作品化住宅型：表达最强，但维护、家庭使用和乡土关系风险最高。",
                ],
                "medium",
            ),
        ]
        return self._common_plan(
            context,
            task_reframe=task,
            viability="项目能否成立，取决于它是否先回答“我要如何回来生活”，再回答“我要如何表达设计”。",
            primary_risk="头号风险是作品化住宅压过真实生活，导致房子成为专业表达而不是可长期居住的家。",
            key_forks=[
                "长期自住、阶段性返乡，还是精神据点？",
                "亲友和家族关系是被纳入日常，还是只被纳入节庆接待？",
                "设计表达是克制地服务生活，还是成为这栋房子的主角？",
            ],
            unknowns=[
                "真实居住频率会改变空间的日常强度。",
                "家庭成员结构会改变公共区、卧室和接待边界。",
                "宅基地环境和当地施工能力会改变设计语言可实现的程度。",
                "是否保留工作/会客功能会改变动线和私密层级。",
            ],
            sections=sections,
            slots={
                "project_object": context.get("space_label") or "自建住宅",
                "owner_profile": subject,
                "core_tension": "专业表达与长期真实生活之间的张力",
                "recommended_brief_focus": "先冻结生活方式、家庭关系和作品化边界",
            },
            next_question="这栋民居更像长期居所、阶段性返乡居所，还是带有工作室/接待属性的精神据点",
        )

    def _commercial_operation_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        task = "这不是单纯布置店面的效率题，而是客流、出品、停留和外带路径能否在小空间里同时成立的问题。"
        sections = [
            self._section(
                "经营变量",
                "商业空间需求重构要先抓经营机制，不先做风格建议。",
                [
                    "翻台取决于座席停留时长、点单等待、取餐回流和清台效率。",
                    "外带效率取决于点单、等候、取餐是否与堂食路径互不打架。",
                    "小面积店铺的命门通常不是座位多，而是高峰期是否堵在吧台前。",
                ],
                "high",
            ),
            self._section(
                "隐藏开关",
                "这些选择会让后续平面和面积判断完全不同。",
                [
                    "堂食优先还是外带优先，会改变吧台长度和座席密度。",
                    "现制饮品复杂度越高，后场和等候区压力越大。",
                    "社区熟客店与路过型快取店，视觉表达和入口组织不同。",
                ],
                "medium",
            ),
        ]
        return self._common_plan(
            context,
            task_reframe=task,
            viability="项目成立先看高峰期路径是否顺畅，再看氛围和风格能否加分。",
            primary_risk="头号风险是把面积花在好看的座位或展示上，反而牺牲出品和取餐效率。",
            key_forks=[
                "堂食翻台优先，还是外带快取优先？",
                "高峰期订单集中在几分钟内，还是全天均匀？",
                "吧台承担展示、点单、出品、取餐中的哪几项？",
            ],
            unknowns=[
                "峰值订单量会改变吧台与等候区判断。",
                "菜单复杂度会改变设备和后场需求。",
                "外带占比会改变入口、排队和取餐组织。",
            ],
            sections=sections,
            slots={
                "project_object": context.get("space_label") or "商业空间",
                "core_tension": "坪效、出品效率与停留体验之间的张力",
                "recommended_brief_focus": "优先冻结经营模型、峰值动线和外带/堂食比例",
            },
        )

    def _style_semantics_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        task = "这不是寻找风格标签的问题，而是把模糊审美词拆成可控制的空间语义边界。"
        sections = [
            self._section(
                "语义边界",
                "风格需求重构要先防止词语滑向符号堆叠。",
                [
                    "“东方感”需要拆成比例、光线、材质、留白或仪式感中的具体来源。",
                    "“不老气”通常不是去掉传统元素，而是控制符号密度和材料年代感。",
                    "茶空间还要判断是社交、独处、展示，还是生活方式消费。",
                ],
                "high",
            ),
            self._section(
                "误区风险",
                "过早给图像答案会让问题变成风格拼贴。",
                [
                    "直接使用中式符号，容易让东方感变成仿古感。",
                    "只追求极简，可能丢掉茶空间应有的停留层次。",
                ],
                "medium",
            ),
        ]
        return self._common_plan(
            context,
            task_reframe=task,
            viability="项目成立先看语义边界能否收住，再看具体材料和形式。",
            primary_risk="头号风险是用风格词替代空间判断，最后得到一套看似统一但不可使用的氛围包装。",
            key_forks=[
                "东方感来自文化母题、空间比例，还是材料触感？",
                "不老气是减少符号，还是提升构造和光线的现代性？",
                "茶空间主要服务独处、社交、零售展示还是接待？",
            ],
            unknowns=[
                "目标客群会改变表达强度。",
                "茶空间使用方式会改变停留机制。",
                "已有品牌或场地条件会改变可用语义。",
            ],
            sections=sections,
            slots={
                "core_tension": "文化语义与现代使用之间的张力",
                "recommended_brief_focus": "优先冻结风格边界、使用场景和符号禁区",
            },
        )

    def _hard_constraint_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        task = "这不是直接报一个尺寸的问题，而是先找出会让参数翻倍或失效的隐藏开关。"
        sections = [
            self._section(
                "隐藏开关",
                "硬约束题必须先问会改变答案的变量。",
                [
                    "设备尺寸受产品结构、补货频率、后场面积和用电条件共同影响。",
                    "如果涉及鲜果、奶制品或预制品，冷藏需求会完全不同。",
                    "前场展示冷藏与后场储藏冷藏不是同一个问题。",
                ],
                "high",
            ),
            self._section(
                "待确认参数",
                "这些参数不清，需求重构只能给判断路径，不能给施工级结论。",
                [
                    "日销量和峰值备货量。",
                    "SKU 数量与需要冷藏的原料类型。",
                    "前场展示、后场储藏和操作台下冷藏的分工。",
                ],
                "medium",
            ),
        ]
        return self._common_plan(
            context,
            task_reframe=task,
            viability="当前能判断问题路径，但不能直接冻结尺寸。",
            primary_risk="头号风险是用经验尺寸替代设备逻辑，后期造成补货、动线或用电冲突。",
            key_forks=[
                "前场展示冷藏，还是后场储藏冷藏？",
                "鲜果奶制品为主，还是瓶装/预制品为主？",
                "按日补货，还是需要多日储备？",
            ],
            unknowns=[
                "菜单结构会改变冷藏容量。",
                "补货频率会改变储藏量。",
                "设备布置和电力条件会改变可选型号。",
            ],
            sections=sections,
            slots={
                "core_tension": "设备参数与运营模型之间的张力",
                "recommended_brief_focus": "优先冻结菜单、补货和设备分工",
            },
        )

    def _cultural_research_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        task = "这不是可以直接给空间灵感的题，而是需要先建立文化、行为和场景证据的研究任务。"
        sections = [
            self._section(
                "研究边界",
                "需求重构只能定义研究路径，不能把未经验证的文化想象当结论。",
                [
                    "需要确认历史语境中的人物、活动、空间和礼仪结构。",
                    "需要区分可转译的行为机制和不可直接借用的文化符号。",
                    "没有证据时，最多提出假设，不能输出确定设计依据。",
                ],
                "high",
            ),
            self._section(
                "证据缺口",
                "这些缺口决定是否应进入深度研究。",
                [
                    "原始文本或可靠二手研究来源。",
                    "雅集活动的行为结构与空间组织证据。",
                    "当代会所目标客群与使用场景。",
                ],
                "medium",
            ),
        ]
        return self._common_plan(
            context,
            task_reframe=task,
            viability="当前适合生成研究计划，不适合直接生成空间结论。",
            primary_risk="头号风险是把文化主题直接装饰化，导致空间看似有典故但没有行为依据。",
            key_forks=[
                "研究目标是文化解释、空间转译，还是汇报论证？",
                "使用证据来自文献、案例、图像，还是当代行为观察？",
                "会所更重社交礼序、精神性，还是商业接待？",
            ],
            unknowns=[
                "证据来源会改变结论可靠性。",
                "当代会所使用方式会改变可转译变量。",
                "输出用途会决定研究深度。",
            ],
            sections=sections,
            slots={
                "core_tension": "文化证据与当代空间转译之间的张力",
                "recommended_brief_focus": "先进入深度研究，再决定是否回填任务书",
            },
        )

    def _general_project_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        labels = self._axis_labels(context)
        focus_items = labels or ["使用者是谁", "项目为什么成立", "哪些条件会改变判断"]
        sections = [
            self._section(
                "先抓变量",
                "当前还不能直接进入方案，应先把影响判断的变量排出来。",
                [f"{item}会影响后续任务书的目录重心。" for item in focus_items[:3]],
                "medium",
            )
        ]
        return self._common_plan(
            context,
            task_reframe="这个问题还处在前结构化阶段，关键是先把真实目标、使用者和约束条件分清。",
            viability="当前已有项目苗头，但还不足以直接冻结设计任务书。",
            primary_risk="头号风险是过早给方案，掩盖真正决定项目方向的未知条件。",
            key_forks=["目标优先级", "使用者结构", "场地与资源边界"],
            unknowns=["空间对象", "使用方式", "预算与落地条件"],
            sections=sections,
            slots={
                "core_tension": "模糊目标与可执行项目定义之间的张力",
                "recommended_brief_focus": "先补齐项目对象、目标和约束",
            },
        )

    def _common_plan(
        self,
        context: Dict[str, Any],
        *,
        task_reframe: str,
        viability: str,
        primary_risk: str,
        key_forks: List[str],
        unknowns: List[str],
        sections: List[Dict[str, Any]],
        slots: Dict[str, Any],
        next_question: str | None = None,
    ) -> Dict[str, Any]:
        merged_slots = {
            "project_object": context.get("space_label") or context.get("project_type_name") or "空间项目",
            "project_type": context.get("project_type"),
            "project_type_name": context.get("project_type_name"),
            **slots,
        }
        return {
            "reconstruction_type": "demand_reconstruction",
            "artifact_name": "action_blueprint",
            "display_title": "需求重构",
            "display_artifact_name": "行动蓝图",
            "task_reframe": task_reframe,
            "project_viability_judgment": viability,
            "primary_risk": primary_risk,
            "key_forks": key_forks,
            "unknowns": unknowns,
            "sections": sections,
            "next_question": next_question or (key_forks[0] if key_forks else "哪个变量最先改变后续判断"),
            "routing_recommendation": "可以继续需求重构；若要形成可交付文件，再整理成设计任务书草稿。",
            "brief_handoff_slots": merged_slots,
        }

    @staticmethod
    def _section(title: str, body: str, items: List[str], emphasis: str) -> Dict[str, Any]:
        return {
            "title": title,
            "body": body,
            "items": items,
            "emphasis": emphasis,
        }

    @staticmethod
    def _subject_phrase(context: Dict[str, Any]) -> str:
        text = str(context.get("source_message") or "")
        if "设计师" in text:
            if "50" in text or "50岁" in text:
                return "50岁专业设计师"
            return "专业设计师"
        if "业主" in text:
            return "业主"
        return "使用者"

    @staticmethod
    def _axis_labels(context: Dict[str, Any]) -> List[str]:
        labels: List[str] = []
        for values in (context.get("semantic_axes") or {}).values():
            for axis_id in values or []:
                label = axis_label(axis_id)
                if label and label not in labels:
                    labels.append(label)
        return labels
