"""
项目类型自动检测器 — 单一权威注册表 (Single Source of Truth)
v7.200: 统一分类定义、中文标签映射、关键词推断、LLM Prompt 类型列表
v1.8 改造: 候选生成器化（不再做完整分类装配）

╔══════════════════════════════════════════════════════════════════════════╗
║  ⭐⭐⭐  本文件改动 → 必须同步检查的文件清单（人话备注）  ⭐⭐⭐         ║
║                                                                          ║
║  这个文件是空间分类系统的"事实源"。改这里的任何东西，都可能要同步      ║
║  改下面 10 个文件。请按"改了什么"对应"必须检查哪些文件"逐条核对。      ║
║                                                                          ║
║  ─────────────────────────────────────────────────────────────────────  ║
║  【场景 1】新增 / 删除 / 重命名 project_type_id (大类型)                ║
║  ─────────────────────────────────────────────────────────────────────  ║
║  必须同步检查:                                                          ║
║    ① config/registries/project_type_registry_meta.yaml                  ║
║         → 是 PROJECT_TYPE_REGISTRY 的 meta overlay，必须补 status/owner ║
║    ② config/registries/classification_master_index.yaml                 ║
║         → axis_mappings.project_type_to_framework 内的映射要补          ║
║    ③ config/type_operating_profiles.yaml                                ║
║         → 新类型如果要进方法论/知识召回/下游 profile，必须补类型画像    ║
║         → 否则 detector 能识别，但下游没有方法论支撑                    ║
║    ④ knowledge_base/ontology.yaml                                       ║
║         → 如果需要专属本体框架或专家扩展，补 ontology 绑定              ║
║    ⑤ utils/ontology_loader.py::DETECTOR_TO_ONTOLOGY                     ║
║         → 检查 detector 到 ontology 的近邻归并映射是否覆盖              ║
║    ⑥ PARENT_TYPE_MAP (本文件内)                                         ║
║         → 新类型的"父桶"归属 (residential/hospitality/...)              ║
║                                                                          ║
║  ─────────────────────────────────────────────────────────────────────  ║
║  【场景 2】detector 输出结构变了 (新增 / 删除字段)                      ║
║  ─────────────────────────────────────────────────────────────────────  ║
║  必须同步检查:                                                          ║
║    ⑦ services/space_classification_service.py                           ║
║         → 它直接消费 detect_with_details() 输出, 字段变了它必须改       ║
║    ⑧ services/dimension_selector.py                                     ║
║         → 它读 result["confidence"]、result["project_type"] 等          ║
║    ⑨ 14 个其他直接消费 detector 的文件 (见下方完整清单)                 ║
║                                                                          ║
║  ─────────────────────────────────────────────────────────────────────  ║
║  【场景 3】只是加 / 删 / 改关键词（不动 type_id 也不动输出结构）         ║
║  ─────────────────────────────────────────────────────────────────────  ║
║  最低限度: 跑 190 题回归测试, 看零回归                                  ║
║  推荐补充: 加新词前判断它是哪一层 (见场景 5)                            ║
║                                                                          ║
║  ─────────────────────────────────────────────────────────────────────  ║
║  【场景 4】新增容易歧义的关键词 (跨多个 type 都可能命中)                ║
║  ─────────────────────────────────────────────────────────────────────  ║
║  正确做法: 不要硬塞 keywords / secondary_keywords，要补                 ║
║    ⑩ config/space_classification/boundary_cases.yaml                    ║
║         → 给歧义词建一个 boundary_case, 让 detector 触发"协议判断"     ║
║         → 不要靠 priority 硬压                                          ║
║                                                                          ║
║  ─────────────────────────────────────────────────────────────────────  ║
║  【场景 5】新增的"关键词"其实是别的层级 (重要 ⚡⚡⚡)                    ║
║  ─────────────────────────────────────────────────────────────────────  ║
║  分情况处理 (不要往 project_type 里乱塞):                                ║
║                                                                          ║
║   ▸ 是"业态细分"(茶饮店/咖啡馆/民宿集群/牙科诊所)                       ║
║       → 不增大类型, 加到 SUBDOMAIN_REGISTRY (本文件) 或                 ║
║         config/registries/subdomain_registry.yaml                       ║
║       → 必须挂在 parent_project_type_id 下                              ║
║                                                                          ║
║   ▸ 是"项目动因/成立方式"(乡村振兴/资产盘活/品牌旗舰/家庭传承)         ║
║       → 不污染 project_type, 加到 config/registries/                    ║
║         founding_type_registry.yaml                                     ║
║                                                                          ║
║   ▸ 是"项目阶段/条件"(新品牌/限时/高翻台/外带优先)                      ║
║       → 加到 config/registries/project_condition_registry.yaml          ║
║                                                                          ║
║   ▸ 是"空间尺度/生命周期"(室内装修/建筑改造/快闪)                       ║
║       → 加到 spatial_extent_registry.yaml / lifecycle_registry.yaml     ║
║                                                                          ║
║  ─────────────────────────────────────────────────────────────────────  ║
║  【场景 6】检查 space_type_dimension_map.yaml (旧兼容链路)              ║
║  ─────────────────────────────────────────────────────────────────────  ║
║    ⑪ config/space_type_dimension_map.yaml (deprecated_compat)           ║
║         → 这是旧兼容链路。新逻辑不应主要维护它,                          ║
║           但如果旧下游 (task_completeness_analyzer 等) 还读它,           ║
║           新增类型要确认是否会断                                         ║
║                                                                          ║
║  ─────────────────────────────────────────────────────────────────────  ║
║  【硬性规则】                                                            ║
║  ─────────────────────────────────────────────────────────────────────  ║
║   1. 改 PROJECT_TYPE_REGISTRY: 必须跑 registry 一致性校验               ║
║       python -c "from intelligent_project_analyzer.services.            ║
║                  project_type_detector import                            ║
║                  validate_registries_against_yaml; print(               ║
║                  validate_registries_against_yaml())"                   ║
║   2. 新增 project_type_id: 必须同步 meta、profile、ontology 映射         ║
║   3. 新增关键词: 必须先判断是强词 / 弱词 / 边界词, 不能只往 keywords 堆 ║
║   4. 新增细分业态: 优先放 subdomain_registry, 不要轻易增大类型           ║
║   5. 新增项目动因: 放 founding_type_registry.yaml, 不要污染 project_type║
║   6. 出现高歧义词: 补 boundary_cases, 不要靠 priority 硬压               ║
║   7. 改完必跑 190 题回归 (sf/2026.3.22/模拟问题集合.txt) 验证零回归     ║
║                                                                          ║
║  ─────────────────────────────────────────────────────────────────────  ║
║  【完整直接消费 detector 的 14 个文件】(改输出结构必须全部检查)          ║
║  ─────────────────────────────────────────────────────────────────────  ║
║    services/space_classification_service.py    ⭐ 主消费方              ║
║    services/dimension_selector.py              ⭐ 读 confidence float    ║
║    services/core_task_decomposer.py                                     ║
║    services/llm_gap_question_generator.py                               ║
║    services/project_type_expansion.py                                   ║
║    services/task_completeness_analyzer.py      (旧 space_type 路径)     ║
║    services/taxonomy_learning_collector.py                              ║
║    services/type_alias_normalizer.py           (词归一)                 ║
║    agents/questionnaire_agent.py                                        ║
║    agents/requirements_analyst.py                                       ║
║    agents/requirements_analyst_agent.py                                 ║
║    api/admin_routes.py                                                  ║
║    tools/query_builder.py                                               ║
║    utils/capability_detector.py / shared_agent_utils.py                 ║
║                                                                          ║
║  全局事实源全图:                                                         ║
║    config/registries/classification_master_index.yaml                   ║
║      (读它就能看到完整 9 张分类表 + 1 张本体维度表的关系)               ║
╚══════════════════════════════════════════════════════════════════════════╝

定位（对照 空间类型及本体论_v1.8.codex.md §2、§8）:
  本文件是 ClassificationCandidateSet 的"项目分类轴"贡献者:
    + 项目类型候选生成器 (ProjectTypeCandidateGenerator)
    + 成立方式候选生成器 (FoundingTypeCandidateGenerator)
    + 子域信号输出器 (SubdomainSignalEmitter)
    + 尺度线索输出器 (SpatialExtent / Lifecycle Signal Emitter)
    + 局部置信度评估器 (LocalConfidenceEvaluator)
    + 歧义信号源 (AmbiguitySignalSource)
    + 证据输出器 (EvidenceEmitter)

  本文件不做:
    - classification_output 完整组装 (由 SpaceClassificationService 负责)
    - project_scale 最终合成 (由 SpaceClassificationService 笛卡尔积)
    - discipline_scope / spatial_layer_ids / knowledge_scope_ids 推导
    - ClarificationRequest 构造 / freeze_state 决策
    - ontology / knowledge 推导

注册表与别名的三层职责 (避免合并成一个 mega-dict):
  1. type_alias_normalizer.normalize_input(): 输入文本归一 (如 "五菱宏光" → "汽车")
     位置: services/type_alias_normalizer.py
  2. LEGACY_TYPE_ALIASES: 旧 type_id 历史迁移 (旧 ID → 新 ID)
     位置: 本文件
  3. registry_item.aliases (Phase B 新增): 类型语义别名 / 词条层别名
     位置: 本文件 PROJECT_TYPE_REGISTRY 各 item 内

所有与项目类型相关的设置，只在此文件中维护：
  - PROJECT_TYPE_REGISTRY      : 类型定义（ID、标签、优先级、关键词、status）
  - FOUNDING_TYPE_REGISTRY     : 成立方式注册表 (v1.8 §4 第 0 段路由起点)
  - SUBDOMAIN_REGISTRY         : 子域注册表 (v1.8 §6.1 受控枚举)
  - LEGACY_TYPE_ALIASES        : 旧 ID → 新 ID 向后兼容映射
  - get_type_label()           : ID → 中文标签（全局唯一出处）
  - get_all_type_ids()         : 返回全部类型 ID 列表（供 YAML/Prompt 注入）

规则：
  - 新增/修改分类 → 只改本文件 PROJECT_TYPE_REGISTRY
  - 下游代码 shared_agent_utils / query_builder / requirements_analyst
    等均从本模块读取，禁止自行维护字典
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

# 扩展类型文件路径（管理员审批后由 project_type_expansion.py 写入）
_EXTENSIONS_FILE = Path(__file__).parent.parent.parent / "data" / "project_type_extensions.json"


def _has_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _build_vertical_mixed_use_candidate(combined_text: str) -> Optional[Dict[str, Any]]:
    floor_tokens = set(re.findall(r"(?:\d+|[一二三四五六七八九十]+)\s*(?:楼|层)", combined_text))
    floor_count = len(floor_tokens)
    if floor_count < 3:
        return None

    has_residential = _has_any(
        combined_text,
        ["住宅", "家庭住宅", "别墅", "私宅", "家宅", "自住", "佛堂"],
    )
    if not has_residential:
        return None

    function_groups = {
        "cultural_display": ["艺术展厅", "美术馆厅", "展厅", "画廊", "展览"],
        "office_business": ["办公室", "办公", "公司", "总部", "工作室"],
        "club_leisure": ["会所", "ktv", "健身房", "高尔夫", "露台会所"],
        "wellness": ["中医理疗", "理疗", "康养", "疗愈"],
        "real_estate_conversion": ["售楼处改造", "销售中心改造", "展示中心改造"],
    }
    matched_groups = [
        group for group, keywords in function_groups.items() if _has_any(combined_text, keywords)
    ]
    if len(matched_groups) < 2:
        return None

    config = PROJECT_TYPE_REGISTRY["hybrid_residential_commercial"]
    score = 7.5 + min(2.0, (floor_count - 3) * 0.5) + min(2.0, (len(matched_groups) - 2) * 0.5)
    return {
        "type_id": "hybrid_residential_commercial",
        "score": round(score, 3),
        "weighted_score": round(score * config["priority"], 3),
        "priority": config["priority"],
        "primary_hits": 1,
        "secondary_hits": len(matched_groups),
        "matched_keywords": {
            "primary": ["多楼层住商复合"],
            "secondary": matched_groups,
        },
        "negated_hits": [],
        "name": config["name"],
        "name_en": config.get("name_en", ""),
    }


def _demote_enterprise_function_inside_residential_carrier(
    candidates: List[Dict[str, Any]],
    combined_text: str,
) -> None:
    """Keep an explicit residence as the carrier when enterprise terms are only functions."""

    residential_carrier_terms = [
        "私人住宅",
        "住宅中",
        "住宅内",
        "住宅里",
        "家中",
        "家里",
        "自宅",
        "私宅",
        "别墅",
        "家宅",
        "自住",
    ]
    enterprise_carrier_terms = [
        "企业总部",
        "企业展厅",
        "总部展厅",
        "企业展示",
        "企业品牌馆",
        "企业文化馆",
        "公司总部",
        "办公总部",
        "接待中心",
        "客户接待中心",
        "投资人接待中心",
        "总部",
        "办公室",
        "办公",
        "公司",
        "企业",
    ]
    enterprise_function_terms = {
        "数据安全指挥中心",
        "战略指挥室",
        "决策室",
        "决策中心",
        "指挥中心",
        "指挥室",
        "战略",
        "决策",
    }

    if not _has_any(combined_text, residential_carrier_terms):
        return
    if _has_any(combined_text, enterprise_carrier_terms):
        return

    residential_candidate = next(
        (
            candidate
            for candidate in candidates
            if candidate.get("type_id") == "personal_residential"
            and candidate.get("primary_hits", 0) > 0
        ),
        None,
    )
    if not residential_candidate:
        return

    for candidate in candidates:
        if candidate.get("type_id") != "commercial_enterprise":
            continue
        matched = set(candidate.get("matched_keywords", {}).get("primary") or [])
        matched.update(candidate.get("matched_keywords", {}).get("secondary") or [])
        if matched and matched.issubset(enterprise_function_terms):
            candidate["weighted_score"] = round(candidate["weighted_score"] * 0.45, 3)
            candidate["object_anchor_penalty"] = "residential_carrier_enterprise_function_demoted"


def _load_extension_registry() -> Dict[str, Any]:
    """
    功能 0.1 — 扩展类型加载。
    人话: 管"后台审批过的新类型怎么临时并入核心注册表"。
    """
    if not _EXTENSIONS_FILE.exists():
        return {}
    try:
        import json
        with open(_EXTENSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("types", {})
    except Exception as e:
        logger.warning(f"[TypeRegistry] 加载扩展类型失败，忽略: {e}")
        return {}

# =============================================================================
# 项目类型权威注册表  ⭐ 改这里 = 改"事实源", 必须看下面 checklist
# =============================================================================
# 功能层级 1 — 项目类型行为注册表
# 人话: 管"这个项目是什么空间"。例如住宅、餐饮、酒店、办公、零售、
# 展厅、城市更新、乡村建设。这里的 keywords / secondary_keywords /
# priority 会直接参与打分，是 project_type 轴的行为事实源。
#
# ⚠️ 改动 checklist (详见本文件最顶部的"必须同步检查的文件清单"):
#   ✅ 新增 type_id   → 同步 project_type_registry_meta.yaml + master_index + ontology
#   ✅ 改输出结构    → 同步 14 个直接消费 detector 的文件
#   ✅ 加歧义词      → 不要硬塞这里, 补 boundary_cases.yaml
#   ✅ 加细分业态    → 不要硬塞这里, 用 subdomain_registry
#   ✅ 加项目动因    → 不要硬塞这里, 用 founding_type_registry
#   ✅ 改完必跑      → 190 题回归验证
#
# 字段说明：
#   name        : 中文显示标签（唯一出处，其他文件不得另建映射）
#   name_en     : 英文检索上下文（供 query_builder 使用）
#   keywords    : 主关键词，命中权重 ×2
#   secondary_keywords: 次要关键词，命中权重 ×1
#   priority    : 类型区分优先级（越高越优先），范围 1-15
#   min_secondary_hits: 当 primary hits=0 时，次要命中需达到此阈值才触发（0=不限制）
#   include_in_prompt : True → 写入 LLM prompt 的可用类型列表
#
# v1.8 §6.4 Registry Contract 可选元数据字段 (向后兼容, 缺省时 _registry_meta 补默认):
#   status        : active_mvp | active_light | reserved_light | reserved | deprecated_compat
#   aliases       : 类型语义别名 (与 LEGACY_TYPE_ALIASES 不同, 这里是词条层别名)
#   owner         : 维护责任人
#   review_status : draft | approved | deprecated
# =============================================================================
PROJECT_TYPE_REGISTRY: Dict[str, Dict[str, Any]] = {

    # ══════════════════════════════════════════════════════════════════════════
    # 优先级 15 — 乡建/新农村（强优先，防止被住宅/酒店关键词稀释）
    # ══════════════════════════════════════════════════════════════════════════
    "rural_construction": {
        "name": "乡建/新农村建设",
        "name_en": "rural construction village regeneration agricultural tourism",
        "keywords": [
            "新农村", "乡村振兴", "乡建", "农文旅", "村建", "村落改造",
            "乡村建设", "农村建设", "乡居", "村庄改造", "美丽乡村",
            "农村民居", "乡村民居", "返乡民居",
        ],
        "secondary_keywords": [
            "民宿集群", "在地农耕", "农耕文化", "乡村经济", "村子", "村庄",
            "村民", "农村", "乡村", "田园", "山村", "聚落", "振兴",
        ],
        "priority": 15,
        "min_secondary_hits": 3,
        "include_in_prompt": True,
    },

    # ══════════════════════════════════════════════════════════════════════════
    # 优先级 10 — 城市更新
    # ══════════════════════════════════════════════════════════════════════════
    "urban_renewal_market": {
        "name": "城市更新/公共市场",
        "name_en": "urban renewal public market regeneration",
        "keywords": [
            "城市更新", "菜市场", "农贸市场", "市场改造", "活化", "再生",
            "旧改", "老旧改造",
        ],
        "secondary_keywords": ["标杆", "示范", "渔村", "老街", "历史街区", "公共市场", "集市"],
        "priority": 10,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "urban_renewal_heritage": {
        "name": "城市更新/历史建筑活化",
        "name_en": "urban renewal heritage conservation adaptive reuse renovation restoration addition",
        "keywords": [
            "历史街区", "老建筑", "文物保护", "历史保护", "古建筑", "老城区",
            "遗址保护", "遗产保护",
            "适应性改造", "适应性利用", "加建改造", "建筑修复",
            # v1.9 补强 (190 题反推: 四合院/小洋楼/老弄堂/百年建筑/防空洞/废弃工厂)
            "四合院", "四合院改造", "传统四合院",
            "民国建筑", "民国小洋楼", "小洋楼", "百年洋楼",
            "老弄堂", "弄堂老房", "石库门", "石库门老房",
            "百年药铺", "百年老店", "百年建筑",
            "老厂房", "废弃工厂", "废弃车间", "工业遗存",
            "工业厂区", "工业遗址", "工业遗产",
            "废弃陶瓷工厂", "景德镇废弃工厂", "景德镇陶瓷",
            "废弃粮仓", "粮仓改造", "废弃码头", "老码头",
            "防空洞", "废弃防空洞", "山城防空洞",
            "重庆山城步道", "山城步道",
            "废弃核电厂", "核电厂改造",
            "故居改造", "故居更新", "名人故居",
            "古镇", "古镇改造", "历史古镇",
        ],
        "secondary_keywords": [
            # v1.9 清洗: 删除 "修复 / 保护 / 传承" 三个泛词
            #   原因: 这些词频繁出现在私宅家族传承、婚姻修复主卧、文化保护等
            #         非历史建筑活化的场景, 会拉飞分类。
            #   保留更精准的同义词: 修缮 / 非遗 / 加建 / 立面改造 / 历史风貌
            "修缮", "非遗", "传统建筑",
            "加建", "扩建", "立面改造", "历史风貌",
            "保留", "活化", "再生", "记忆", "原真性",
            "新旧对撞", "新旧融合", "结构加固", "防潮防水",
            "工业美学", "锈迹", "锯齿屋顶", "梁架结构",
        ],
        "priority": 10,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },

    # ══════════════════════════════════════════════════════════════════════════
    # 优先级 9 — 高辨识度专项类型
    # ══════════════════════════════════════════════════════════════════════════
    "real_estate_showcase": {
        "name": "地产样板房/售楼展示",
        "name_en": "real estate model room showflat sales center developer",
        "keywords": ["样板房", "样板间", "售楼处", "展示中心", "地产营销", "销售中心"],
        "secondary_keywords": ["楼盘", "开发商", "竞标", "开盘", "地产项目", "地标建筑", "超高层"],
        "priority": 9,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "industrial_conversion": {
        "name": "工业/生产设施/厂房改造",
        "name_en": "industrial conversion factory warehouse winery barn brewery adaptive reuse",
        "keywords": [
            # v1.9 冲突清理: "工业遗存 / 工业遗址" 与 urban_renewal_heritage 冲突
            #   industrial_conversion 主关键词聚焦"工业生产 / 物流 / 仓储 / 厂区办公"
            #   urban_renewal_heritage 主关键词聚焦"老建筑活化 / 文化记忆保护"
            #   两边可以共存但要靠上下文区分: industrial 更偏生产+办公转换,
            #   heritage 更偏文化+展览转换
            "厂房", "工厂", "仓库", "工业建筑", "粮仓", "车间",
            "工厂改造办公", "工厂改造产业园", "厂区改造创意园",
            "工业用地转型", "酒庄", "酿酒厂", "啤酒厂", "谷仓",
        ],
        "secondary_keywords": [
            "改造", "旧厂区", "工业风", "loft", "创意园区",
            "马厩", "温室", "能源工厂", "库房", "物流仓储",
        ],
        "priority": 9,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "educational_facility": {
        "name": "教育建筑/校园",
        "name_en": "educational school campus university kindergarten library research daycare",
        "keywords": [
            "学校", "校园", "幼儿园", "小学", "中学", "高中", "大学", "高校",
            "教学楼", "图书馆", "科研楼", "实验楼", "书院", "学院",
            "日托中心", "研究所", "学生大厅",
        ],
        "secondary_keywords": [
            "教育", "教室", "课室", "培训", "研究院", "科研中心",
            "学生宿舍", "学生公寓", "食堂", "操场", "研学",
            "青少年", "职业学校", "培训学校", "研学基地",
        ],
        "priority": 9,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "religious_spiritual": {
        "name": "宗教/仪式/殡葬空间",
        "name_en": "religious spiritual church temple mosque shrine chapel memorial cemetery",
        "keywords": [
            "教堂", "寺庙", "清真寺", "礼拜堂", "祠堂", "庙宇", "佛堂",
            "寺院", "道观", "神殿", "宗教建筑",
            "修道院", "大教堂", "小教堂", "祈告室", "犹太教堂",
        ],
        "secondary_keywords": [
            # v1.9 清洗: 删除 "精神 / 冥想 / 禅" 三个泛词
            #   原因: 苏东坡式文人精神住宅 / 高净值精神性私宅 /
            #         健康焦虑正念空间 等都会被误带到宗教类。
            #   保留更精准的: 礼拜 / 信仰 / 纪念堂 / 神圣 / 殡葬等
            "礼拜", "信仰", "纪念堂", "坛庙",
            "圣地", "庄严", "神圣",
            # 殡葬建筑（纪念中心/火葬场/公墓/陵墓）
            "火葬场", "公墓", "陵墓", "殡仪馆", "墓园", "纪念馆",
        ],
        "priority": 9,
        "min_secondary_hits": 1,
        "include_in_prompt": True,
    },

    # ══════════════════════════════════════════════════════════════════════════
    # 优先级 8 — 主流场所类型
    # ══════════════════════════════════════════════════════════════════════════
    "commercial_hospitality": {
        "name": "酒店民宿/度假",
        "name_en": "hospitality hotel boutique inn resort spa hostel holiday cabin glamping treehouse container hotspring serviced_apartment",
        "keywords": [
            "酒店", "民宿", "度假村", "客栈", "旅馆", "会所",
            "度假小屋", "青年旅舍", "精品酒店",
            # 新型度假场所
            "泡汤", "日归温泉", "汤屋", "山顶营地",
            "树屋民宿", "露营基地", "集装箱民宿",
            "帐篷酒店", "荠野形", "帐篷度假",
            # v1.9 补强: 服务式公寓 / 公寓酒店
            #   原因: §1 雅诗阁项目当前误判为 commercial_office, 因为题面有
            #         "总部大楼"。服务式公寓本质上是 hospitality 业态,
            #         需要明确独立信号词锁定
            "公寓酒店", "服务式公寓", "品牌公寓",
            "酒店式公寓", "高级公寓品牌",
            "雅诗阁", "辉盛阁", "馨乐庭",
            "长租公寓", "短租公寓",
            "全套房客房", "高级套房",
        ],
        "secondary_keywords": [
            "resort", "住宿", "客房", "大堂吧", "度假", "宾馆",
            "旅游景点", "主题公园", "度假区", "旅游配套",
            "野外", "自然", "山里", "乡村住宿",
        ],
        "priority": 8,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "commercial_dining": {
        "name": "餐饮/夜生活空间",
        "name_en": "restaurant dining cafe food beverage bar tea nightclub buffet hotpot barbecue",
        "keywords": [
            "餐厅", "餐饮", "咖啡馆", "茶饮店", "茶室", "酒吧", "食堂",
            "快餐店", "夜店", "夜总会",
            # 新茶饮 / 咖啡子域信号 (v1.8 茶饮 MVP)
            "奶茶店", "新茶饮", "茶饮", "咖啡店", "精品咖啡",
            # 特色餐饮形式
            "自助餐", "自助火锅", "无限畅吃",
            "烧烤店", "火锅店", "火锅", "串串",
            "居酒屋", "大排档改造",
            # v1.9 补强 (190 题反推)
            "中餐厅", "中餐厅包房", "中餐厅设计", "高端中餐",
            "日料店", "高端日料", "怀石料理", "寿司店",
            "西餐厅", "法餐厅", "意餐厅",
            "酒馆", "小酒馆", "清吧", "鸡尾酒吧", "lounge酒吧",
            "全日餐厅", "大堂吧", "下午茶餐厅",
            # v1.9 冲突清理 (美食实验室):
            #   commercial_dining 限定为"餐厅创新厨房 / 创意菜实验"语境
            #   digital_media_studio 限定为"博主拍摄 / 视频内容"语境
            "餐厅创新厨房", "创意菜实验",
            "美食拍摄厨房",
            "茶道空间", "茶道大师空间", "极致茶室", "私人茶室",
            "茶文化空间", "茶艺空间",
            "非标咖啡", "非标小酒馆", "非标咖啡集群", "咖啡小酒馆集群",
            "海边餐厅", "全木结构餐厅", "海景餐厅", "山地餐厅",
            # v1.9 冲突清理: "亲子餐厅" 移到 children_family 独占 (孩子主导是关键)
            # v1.9 冲突清理: "婚宴酒楼" 移到 wedding_banquet 独占 (婚宴主导)
            "夜间餐饮", "夜宵餐厅", "深夜食堂",
        ],
        "secondary_keywords": [
            # v1.9 冲突清理: "小酒馆 / 清吧" 已是 keywords 主词, 删 secondary 重复
            "茶馆", "酒楼", "美食", "用餐",
            "中餐", "西餐", "日料", "包房",
            "lounge", "娱乐餐饮", "夜宵", "外带",
            # v1.9 清洗: 动因词从 keywords (×2) 降到 secondary (×1)
            #   原因: "翻台 / 坪效 / 出杯" 等是 founding_type.operating_business
            #         的核心信号词, project_type 应聚焦"是什么空间"
            #         (茶饮店 / 火锅店 / 中餐厅), 不重复 founding_type 信号
            "出杯", "翻台", "翻台率", "坪效", "客单价",
            "厨房", "前厅", "后厨",
            "用餐体验", "用餐节奏", "用餐场景",
            "包间", "包房", "宴请", "聚餐",
            "灯光氛围", "声学氛围", "材料防火",
        ],
        "priority": 8,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "performing_arts": {
        "name": "演艺/剧场空间",
        "name_en": "performing arts theater concert hall opera auditorium stage cinema ballroom",
        "keywords": [
            "剧院", "剧场", "音乐厅", "演艺中心", "歌剧院", "音乐会场",
            "露天剧场", "礼堂", "演出中心", "大剧院",
            "电影院", "舞厅", "音乐俱乐部",
        ],
        "secondary_keywords": [
            "舞台", "演出", "表演", "观演", "戏剧", "排演",
            "影院", "多厅影城", "放映厅",
        ],
        "priority": 8,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "public_cultural": {
        "name": "文化展陈/科教场馆",
        "name_en": "cultural museum exhibition gallery art center science visitor aquarium zoo planetarium",
        "keywords": [
            # 展陈建筑
            # v1.9 冲突清理 (展厅): public_cultural 限定为"博物馆 / 美术馆 / 公共"语境
            "博物馆", "美术馆", "展览馆", "展览中心", "展馆",
            "博物馆展厅", "美术馆展厅", "公共展厅", "展厅",  # "展厅"通用词保留兜底
            "文化中心", "艺术馆", "艺术中心", "视觉艺术中心",
            "图书馆",
            # 科教建筑
            "科学中心", "游客中心", "动物园", "水族馆", "天文馆",
            "解说中心", "青年活动中心",
            # v1.9 补强 (190 题反推: 主题博物馆 / 跨域文化机构)
            "私人博物馆", "私人画廊", "私人展厅",
            # v1.9 冲突清理: "城市记忆馆" public_cultural 独占 (community_public 已移除)
            "城市记忆馆", "工业记忆馆", "工业遗产展", "城市形象展示中心",
            "未来学习中心", "数字课堂中心", "数字课堂",
            "数据遗产博物馆", "数据安全博物馆", "数据可视化馆",
            "电竞文化博物馆", "电竞博物馆",
            "行为经济学体验馆", "行为科学体验馆",
            # v1.9 冲突清理: "氢能未来展示馆 / 氢能展示馆" 移到 commercial_enterprise 独占
            # (这是企业品牌技术展示, 不是公共文化展陈)
            "能源教育博物馆",
            "太空旅游体验中心", "太空展示中心", "宇航体验中心",
            "人类迁徙博物馆", "迁徙博物馆", "身份认同研究中心",
            "语言保护中心", "方言保护馆", "民族语言馆",
            "文明档案库", "文明记忆馆", "文明博物馆",
            "AI伦理研究中心", "后人类伦理实验室",
            # v1.9 冲突清理: "意识研究住宅" 移到 personal_residential 独占
            # (这是住宅形态, 不是科教场馆)
            "神经科学实验空间", "意识研究空间",
            "传播学实验零售空间", "传播学实验馆",
            "宗教研究机构", "跨信仰对话空间", "宗教对话中心",
            "极端灾害模拟训练中心", "灾害模拟训练中心",
            "城市应急避难空间示范中心", "应急避难展示中心",
            "宇宙观测", "天文展示", "海洋展示",
        ],
        "secondary_keywords": [
            "展览", "展示", "画廊", "书屋", "艺术空间",
            "文物", "文化遗址", "传统建筑展",
            # 展陈装置/临时装置
            "展陈装置", "临时装置", "装置艺术",
            # 瞭望塔/自然博物馆（科教建筑周边）
            "瞭望塔", "自然博物馆", "昆曲",
            # v1.9 补强
            "策展", "展陈", "馆藏", "公教", "非营利", "教育", "普及",
            "沉浸式", "多媒体", "互动装置", "数字可视化",
            "叙事路径", "观展体验", "公众教育", "科普",
            "文化记忆", "文化传播", "学术交流",
        ],
        "priority": 8,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "landscape_outdoor": {
        "name": "景观/公共户外空间",
        "name_en": "landscape architecture outdoor public space park plaza waterfront urban garden",
        "keywords": [
            "景观设计", "城市公园", "公共广场", "滨水景观", "花园设计", "公共绿地",
            "景观装置", "口袋公园", "屋顶花园", "庭院设计",
        ],
        "secondary_keywords": [
            "景观", "园林", "户外", "广场", "公园", "步道", "滨水",
            "绿化", "植被", "水景", "铺装", "人行道", "林荫", "生态",
        ],
        "priority": 8,
        "min_secondary_hits": 1,
        "include_in_prompt": True,
    },
    "community_public": {
        "name": "社区/公共服务空间",
        "name_en": "community public service center civic shared space neighborhood memorial senior station elderly",
        "keywords": [
            "社区活动中心", "公共服务中心", "市民中心", "社区图书馆", "社区书屋",
            "社区服务中心", "居委会", "邻里中心", "社区食堂", "社区公园",
            "社区中心",
            # 城市新型社区设施
            "长者食堂", "银发驿站", "老年活动室", "共享洗衣房",
            "社区健身角", "无障碍改造社区",
            # v1.9 补强 (190 题反推)
            "社区共享厨房", "社区共享厨房网络", "共享厨房网络",
            # v1.9 冲突清理: 银发服务类 community 独占 (社区服务主导, 非医疗照护)
            "银发再就业中心", "银发再就业", "银发驿站",
            "社区银发服务站", "社区便民驿站", "便民驿站",
            "青少年心理干预中心", "青少年心理中心",
            # v1.9 冲突清理: 应急避难空间 / 城市记忆馆 归位
            #   "城市应急避难空间示范中心" 移除 (与 public_cultural 冲突,
            #     由 community_public 独占, public_cultural 已同步移除)
            #   "城市记忆馆 / 城市记忆中心" 移除 (这是文化展陈, 归 public_cultural)
            "应急避难空间", "应急避难中心", "城市应急避难空间", "城市应急避难空间示范中心",
            "平灾两态社区中心", "平时灾时社区中心",
            "城市文化综合体", "文化综合体",
            "数字游民社区服务中心", "数字难民社区服务中心", "数字游民社区",
            "战后社区恢复中心", "社区恢复中心",
            "难民社区服务中心", "难民营服务中心",
            "韧性社区样板住宅", "韧性社区",
            "保障房示范项目", "高品质保障房示范项目", "保障性住房示范",
            "气候迁徙过渡型居住社区", "过渡型居住社区",
            # v1.9 冲突清理: 养老社区 3 词 由 healthcare 独占 (医疗 + 居家照护混合)
            # "银发驿站" 留 community (社区服务主导)
            # "AI陪伴养老社区"/"高端养老社区"/"养老社区" 已从此处移除
            "国际NGO医疗支援培训中心", "医疗支援培训中心",
            "全球员工心理恢复中心", "员工心理恢复",
            "乡村数字课堂中心", "乡村公共书屋网络",
            "夜间文化市集", "城市公共客厅",
        ],
        "secondary_keywords": [
            "社区", "公益空间", "共享厨房", "避难所", "公共客厅",
            "社会服务", "社区改造", "留守儿童", "社区图书角", "公共活动",
            "纪念碑", "纪念广场", "城市纪念",
            "银发服务", "居家养老", "互助养老",
            # v1.9 补强
            "民生", "公益", "福利", "公共属性",
            "韧性", "防灾", "灾时", "应急转换", "平灾两态",
            "代际交流", "代际融合", "弱势群体", "尊严感",
            "无障碍底线", "通用设计", "公共财政",
        ],
        "priority": 8,
        "min_secondary_hits": 1,
        "include_in_prompt": True,
    },

    # ══════════════════════════════════════════════════════════════════════════
    # 优先级 7 — 商业/办公/专业类
    # ══════════════════════════════════════════════════════════════════════════
    "commercial_retail": {
        "name": "商业零售/综合体",
        "name_en": "retail commercial shop brand store mall shopping complex",
        "keywords": [
            "商场", "综合体", "购物中心", "专卖店", "买手店", "百货",
            # v1.9 补强 (190 题反推: 商业改造、夜经济、生活方式中心)
            "商业街区", "商业街", "百货商场", "购物广场", "商业综合体",
            "生活方式中心", "夜经济街区", "夜经济示范街区",
            "设计师集合店", "买手商业街区", "商业升级",
            "无人花店", "无人商店", "自助零售", "24小时营业",
            "交换商店", "二手商店", "闲置交换", "社区商业",
            "社区型商业综合体", "便利商店", "标杆商业",
        ],
        "secondary_keywords": [
            # v1.9 冲突清理: "商业街区 / 旗舰店" 已是 keywords 主词, 删 secondary 重复
            "零售", "店铺", "品牌", "门店", "购物",
            "招商", "租户组合", "客流", "坪效", "动线",
            "夜间", "打卡", "标杆", "业态", "首店", "销售场景",
        ],
        "priority": 7,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "brand_experience": {
        "name": "品牌旗舰/体验店",
        "name_en": "brand flagship experience store showroom concept store immersive",
        "keywords": [
            "旗舰店", "品牌体验店", "概念店", "体验店", "品牌展示馆",
            # v1.9 补强 (190 题反推: 沉浸体验、香薰、汽车体验、奢侈品 VIP)
            "沉浸式体验店", "沉浸式体验中心", "品牌沉浸",
            "香薰品牌旗舰店", "化妆品旗舰店", "美妆体验店",
            # v1.9 冲突清理: "汽车体验中心" 移到 automotive_showroom 独占
            "NIO House", "蔚来空间", "新能源体验店",
            "奢侈品旗舰店", "爱马仕", "Tiffany", "Louis Vuitton",
            "买手店升级", "限量发布店", "新品首发店", "品牌秀场",
            "工艺体验实验室", "工艺体验中心", "工艺体验店",
            "智能体验店", "AI 体验店", "数字孪生体验店",
        ],
        "secondary_keywords": [
            "品牌旗舰", "香薰品牌", "生活方式品牌", "展示空间", "品牌叙事",
            "限定", "VIP", "稀有", "高定", "尊享", "品牌精神",
            "首发", "互动装置", "气味分子", "材料透明度", "互动体验",
        ],
        "priority": 7,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "commercial_office": {
        "name": "办公/联合办公",
        "name_en": "office coworking workspace studio research center corporate incubator makerspace accelerator creator",
        "keywords": [
            "办公室", "写字楼", "联合办公", "工作室", "研发中心", "总部大楼",
            # 新型工作场所
            "孵化器", "加速器", "众创空间", "创客空间", "makerspace",
            "电商仓储办公", "直播办公（办公性质）",
            # v1.9 补强 (190 题反推 + 对接 founding_type.organizational_efficiency)
            "甲级写字楼", "总部办公室", "全球总部", "亚太总部",
            "集团总部办公", "顶层行政会所", "高管层办公",
            "研发中心办公室", "工程师中心", "技术中心办公室",
            "律师事务所办公室", "律所办公室", "投行办公室",
            "金融科技公司办公室", "证券公司办公室",
            "AI算法独角兽研发中心", "AI算法公司办公", "AI研发空间",
            "数字孪生办公", "数据驱动办公", "可迭代办公",
            "全沉浸式虚拟现实办公空间", "VR办公空间", "VR办公",
            "元宇宙办公室", "元宇宙公司办公",
            "AI生成内容公司办公", "AI内容公司",
            "注意力经济公司办公", "数字游民办公中心",
            "24小时无人自助办公中心", "无人办公空间",
            "高端健身俱乐部办公", "灵感工作场",
            "意识研究实验室办公", "哲学家工作室",
            "南昌4层复合总部建筑", "总部建筑办公部分",
            "甲方办公楼", "甲级写字楼升级",
        ],
        "secondary_keywords": [
            "办公", "会议室", "工位", "共享办公",
            "创意园", "产业园", "数据中心",
            "创业团队", "起步世界", "创立者社区",
            # v1.9 补强
            "员工", "工程师", "设计师", "团队协作",
            "可移动家具", "可分可合办公", "弹性办公",
            "热力图", "组织文化", "工程师文化", "员工心理",
            "AI伦理", "数字孪生", "数据驱动",
            "可成长", "可迭代", "可重组",
            "VR设备", "碰撞预防", "虚拟与现实",
        ],
        "priority": 7,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "commercial_enterprise": {
        "name": "企业空间/品牌展厅",
        "name_en": "corporate enterprise brand showroom experience center headquarters",
        "keywords": [
            # v1.9 冲突清理 (展厅): commercial_enterprise 限定为"企业 / 接待"语境
            # ("展厅"通用词保留, 由上下文区分; public_cultural 主"博物馆/美术馆展厅")
            "企业总部", "企业展厅", "总部展厅", "接待展厅",
            "接待中心", "企业展示", "体验中心",
            # v1.9 补强 (190 题反推: 企业俱乐部、行政会所、跨国总部、研发中心展示)
            "企业俱乐部", "企业家俱乐部", "行政会所", "总裁俱乐部",
            "跨国企业总部", "跨国公司中国区总部", "中国区总部",
            # v1.9 冲突清理: "全球总部 / 亚太总部" 移到 commercial_office
            # (办公功能主导, enterprise 仅做品牌展示侧)
            "区域总部",
            "未来实验室展示中心", "AI伦理研究中心展示",
            "氢能未来展示馆", "新能源展示馆",
            "企业历史馆", "企业文化馆", "企业品牌馆",
            "数据安全指挥中心", "战略指挥室", "决策室", "决策中心",
            "客户接待中心", "投资人接待中心", "高净值客户会客厅",
        ],
        "secondary_keywords": [
            "企业文化", "员工空间", "运营", "商业模式", "坪效", "俱乐部",
            "跨界连接", "高净值会客", "私密性", "权力感", "圈层",
            "接待动线", "VIP区域", "战略", "决策", "全球视野",
            "本土扎根", "国际化",
        ],
        "priority": 7,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "healthcare_wellness": {
        "name": "医疗/康养/养老",
        "name_en": "healthcare wellness senior living medical clinic spa rehabilitation veterinary TCM elderly adaptive",
        "keywords": [
            "医院", "诊所", "养老院", "康养中心", "月子中心", "体检中心",
            "保健中心", "牙科诊所", "水疗中心", "温泉", "桑拿",
            # 适老化
            "适老化改造", "适老化", "无障碍设计", "老人房",
            # v1.9 冲突清理: "银发驿站" 移到 community_public 独占
            "老年住宅改造", "针对老人的设计",
            # 中医馆/心理
            # v1.9 冲突清理: "正念空间 / 冥想室" 仅在后面 (576) 保留, 此处删重复
            "中医馆", "针灸推拿", "心理咨询室",
            # 医美（与 beauty_personal_care 共用，主词赋予正规医疗语境）
            "医疗美容", "整形外科", "整形诊所",
            # v1.9 补强 (190 题反推 + 对接 founding_type.special_needs_care / healing_repair)
            "高端私立医院", "私立医院", "私立牙科诊所", "高端牙科",
            "宁静病房", "临终关怀病房", "临终关怀中心",
            "私立月子中心", "高端月子中心", "VIP月子中心",
            # v1.9 冲突清理 (重审): "AI陪伴养老社区 / 高端养老社区 / 养老社区"
            # 决定: healthcare 独占 (这是医疗 + 居家照护混合, 医疗主导)
            "AI陪伴养老社区", "高端养老社区", "养老社区",
            "AI伦理养老社区", "智能养老社区",
            "宠物医院", "宠物医疗", "宠物社交体验中心",
            "高端生物安全实验室", "生物安全实验室", "P3实验室", "P4实验室",
            "生物科技未来实验室", "生物实验室",
            "正念空间", "冥想室", "冥想中心", "私人冥想中心", "冥想住宅",
            "正念住宅", "瑜伽冥想空间", "瑜伽冥想房",
            # v1.9 冲突清理 (感统训练室): healthcare 限定为"康复 / 治疗" 语境
            "感统康复训练室", "自闭症医疗训练室", "医疗级感统训练",
            "感统训练室", "自闭症训练室", "感统训练空间",  # 保留(因为也可能是临床)
            "过敏儿童卧室", "无敏卧室", "医疗级新风住宅",
            # v1.9 冲突清理: "无障碍住宅 / 全屋无障碍" 移到 personal_residential 独占
            # (这是住宅形态, healthcare 只负责医疗 / 康养机构)
            "残障人士住宅",
            "失眠康复空间", "焦虑康复空间", "睡眠康复",
            "婚姻修复主卧室", "婚姻修复空间", "夫妻关系修复",
        ],
        "secondary_keywords": [
            # v1.9 冲突清理: "宁静病房" 已是 keywords 主词, 删 secondary 重复
            "护理", "康复", "老年", "养生", "医疗", "康养", "健康",
            "临终关怀", "心理干预",
            "水疗", "spa", "澡堂", "汗蒸", "药浴",
            "兽医", "动物医院", "医学实验室", "药疗设施",
            # 适老化次要
            "老人", "老年人", "扶手", "坡道", "轮椅", "踏板",
            # v1.9 补强
            "尊严感", "陪护", "陪伴", "家属", "病人",
            "焦虑感", "恐惧感", "抗焦虑", "正念", "情绪修复",
            "感统", "自闭", "过敏", "低敏", "医疗级新风", "空气净化",
            "无障碍底线", "适老化底线", "无菌等级",
            "心理安全", "心理舒适", "心理疗愈",
        ],
        "priority": 7,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "sports_entertainment_arts": {
        "name": "体育/健身/运动场馆",
        "name_en": "sports fitness arena stadium aquatics gymnasium track field skating frisbee paddle surf climbing trampoline",
        "keywords": [
            "体育馆", "体育场", "运动场", "游泳馆", "游泳池", "健身房",
            "球场", "足球场", "篮球场", "檪榄球场", "跡马场",
            "健身俱乐部", "滑板公园", "滑雪中心", "冰场",
            # 新兴运动项目
            "电竞馆", "电竞中心", "污遢环", "飞爹卢环", "攀岩馆", "屋内攀岩",
            "蹦寭公园", "蹦寭场", "室内滑雪", "高尔夫练习场",
            "台球应允容", "刑棒馆", "膙弓馆",
        ],
        "secondary_keywords": [
            "运动", "健身", "竞技", "训练", "马术", "射击", "攀岩",
            "游乐设施", "娱乐", "活动课", "星期训练",
        ],
        "priority": 7,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "transportation_civic": {
        "name": "交通/市政/公共行政",
        "name_en": "transportation civic infrastructure airport metro station government courthouse embassy",
        "keywords": [
            # 交通建筑
            "交通枢纽", "地铁站", "机场", "火车站", "高铁站", "港口", "码头",
            "停车场", "公交站", "交通中心", "游船码头", "船坞",
            # 行政/公共建筑
            "市政厅", "市政建筑", "政府大楼", "行政中心", "法院", "大使馆",
            # 安保建筑
            "消防站", "警察局", "紧急服务",
        ],
        "secondary_keywords": [
            "交通", "枢纽", "公共交通", "基础设施", "桥梁", "人行桥", "公路桥",
            "能源站", "变电站", "水务", "物流中心",
            "部门建筑", "行政楼", "办事处", "司法",
        ],
        "priority": 7,
        "min_secondary_hits": 1,
        "include_in_prompt": True,
    },

    # ══════════════════════════════════════════════════════════════════════════
    # 优先级 8 补充 — 休闲娱乐/婚宴庆典/亲子早教/存量住宅改造（v8.0 新增）
    # ══════════════════════════════════════════════════════════════════════════
    "leisure_entertainment": {
        "name": "休闲娱乐/水会棋牌KTV",
        "name_en": "leisure entertainment KTV karaoke spa bathhouse billiards escape room board game mahjong",
        "keywords": [
            "ktv", "量贩ktv", "一声ktv", "棋牌室", "麻将馆", "棋牌",
            "水会", "洗浴中心", "澡堂子", "男宾女宾", "洗浴",
            "密室逃脱", "剧本杀", "密室", "沉浸式密室",
            "桌游馆", "轰趴馆", "轰趴", "真人cs", "激光枪战",
            "电玩城", "游戏厅", "娱乐城",
        ],
        "secondary_keywords": [
            "包厢", "娱乐", "会员卡", "大厅", "休闲", "台球厅",
            "棋牌文化", "休闲服务", "娱乐空间", "消费场所",
        ],
        "priority": 8,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "wedding_banquet": {
        "name": "婚庆宴会/庆典空间",
        "name_en": "wedding banquet ceremony hall celebration event venue bridal",
        "keywords": [
            "婚宴", "婚礼堂", "婚礼会所", "婚礼场地", "婚庆公司",
            "宴会厅", "宴请厅", "宴会中心", "宴请空间",
            "庆典会所", "答谢宴", "颁奖典礼场地", "婚宴酒楼",
            "宴会楼", "满月宴", "升学宴", "寿宴厅",
        ],
        "secondary_keywords": [
            # v1.9 清洗: 删除 "仪式感" (泛词, 婚纱店 / 茶道空间 / 高端零售
            #          / 高端私宅 都谈仪式感, 不应被婚宴独占)
            "婚礼", "庆典", "酒席", "席面", "摆席",
            "宴席", "堂食大厅", "主题婚礼", "婚礼策划",
        ],
        "priority": 8,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "children_family": {
        "name": "亲子/早教/儿童空间",
        "name_en": "children family early education daycare toddler playground parenting center baby gym",
        "keywords": [
            "早教中心", "早教", "亲子乐园", "儿童乐园", "儿童游乐场",
            "绘本馆", "亲子餐厅", "宝宝", "托育", "托育中心",
            "蒙台梭利", "baby gym",
            "亲子主题", "儿童主题", "儿童活动中心",
            # v1.9 冲突清理 (感统训练室): children_family 限定为"早教 / 亲子" 语境
            "早教感统训练", "亲子感统训练", "感统训练室",  # 保留通用词作兜底
            "感统",
        ],
        "secondary_keywords": [
            "儿童", "小朋友", "幼儿", "亲子", "家长", "育儿",
            "安全", "圆角", "低甲醛", "无毒", "启蒙", "启智",
        ],
        "priority": 8,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "residential_renovation": {
        "name": "存量住宅改造/二手房翻新",
        "name_en": "renovation existing residential second-hand house renovation remodel old apartment makeover",
        "keywords": [
            "二手房", "二手房改造", "旧房翻新", "老房改造", "老旧住宅",
            "重新装修", "格局改造", "格局重整", "老破小", "回迁房",
            "翻新改造", "老宅改造", "原有户型", "房龄",
        ],
        "secondary_keywords": [
            "翻新", "改造", "重装", "拆改", "承重", "原来", "之前",
            "住了多年", "原房东", "原有格局", "局部改造",
        ],
        "priority": 8,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },

    # ══════════════════════════════════════════════════════════════════════════
    # 优先级 7 补充 — 美容美发/汽车展厅/直播媒体/快闪临时（v8.0 新增）
    # ══════════════════════════════════════════════════════════════════════════
    "beauty_personal_care": {
        "name": "美容美发/生活美学门店",
        "name_en": "beauty salon hair studio nail spa lash brow tattoo aesthetic clinic personal care",
        "keywords": [
            "美发沙龙", "发型工作室", "美发店", "理发店", "剪发",
            "美容院", "美容工作室", "美甲店", "美睫", "纹身馆",
            "轻医美", "医美诊所", "皮肤管理", "无创美容",
            "造型工作室", "整体形象", "香薰spa工作室",
        ],
        "secondary_keywords": [
            "美容", "美发", "护肤", "发色", "烫发", "染发",
            "造型", "顾客", "师傅", "操作台", "洗剪吹",
        ],
        "priority": 7,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "automotive_showroom": {
        "name": "汽车展厅/4S店/改装",
        "name_en": "automotive showroom 4S car dealership EV experience center auto modification supercar club",
        "keywords": [
            "4s店", "4s店展厅", "汽车展厅", "汽车展示中心", "新能源汽车体验店",
            "汽车体验中心", "汽车改装店", "改装车", "试驾中心",
            "超跑俱乐部", "汽车美容", "洗车房", "汽车主题",
        ],
        "secondary_keywords": [
            "汽车", "车", "售车", "购车", "看车", "品牌店",
            "展车", "试驾", "交车区", "维修区",
        ],
        "priority": 8,
        "min_secondary_hits": 1,
        "include_in_prompt": True,
    },
    "digital_media_studio": {
        "name": "直播/拍摄/媒体基地",
        "name_en": "live streaming studio MCN filming base media production creator photography commercial shoot",
        "keywords": [
            "直播基地", "直播间", "直播间设计", "拍摄基地", "拍摄场地",
            "mcn机构", "影棚", "商业摄影棚", "摄影基地",
            "短视频基地", "内容创作基地", "录播室",
            # v1.9 补强 (190 题反推)
            "跨境电商直播基地", "电商直播基地", "选品仓储直播",
            "B站UP主工作室", "UP主工作室", "动漫UP主", "二次元工作室",
            "B站直播工作室", "抖音直播间", "微信视频号直播间",
            "电竞选手直播间", "电竞主播工作室", "电竞直播",
            "电影混音工作室", "杜比全景声工作室", "家庭影院工作室",
            "电影录音棚", "电影声学工作室", "声学工作室",
            # v1.9 冲突清理 (美食实验室): digital_media_studio 限定为"博主 / 拍摄"语境
            "美食博主工作室", "美食博主拍摄基地", "美食视频工作室",
            "美食工作室", "美食实验室",  # 保留通用词, 由上下文区分
            "时尚博主工作室", "KOL工作室", "网红工作室",
            "私人影音室", "家庭影院", "私人录音棚",
            "短视频影棚", "短视频工作室",
        ],
        "secondary_keywords": [
            "直播", "带货", "主播", "博主", "kol", "up主",
            "内容创作", "摄影", "拍摄", "录制", "布景",
            # v1.9 补强
            "灯光控制", "声学", "隔音", "吸音", "扩散",
            "可替换背景", "模块化背景", "背景墙",
            "视觉品牌", "镜头逻辑", "拍摄角度",
            "7×24小时", "选品", "数据监控",
        ],
        "priority": 7,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "popup_temporary": {
        "name": "快闪/临时装置空间",
        "name_en": "pop-up temporary installation flash store limited event space immersive experience",
        "keywords": [
            "快闪店", "快闪", "pop-up", "popup", "限时体验店",
            "快闪餐厅", "限时店", "期间限定", "快闪空间",
            "发布空间", "新品发布场地",
            # v1.9 补强 (190 题反推)
            "户外音乐节VIP休息区", "音乐节VIP", "音乐节临时VIP",
            "户外音乐节", "三个月户外音乐节", "限期音乐节",
            "国际艺术双年展临时城市展馆", "临时城市展馆",
            "双年展展馆", "艺术节临时展馆", "可回收展馆",
            "国际品牌沉浸式体验中心", "沉浸式快闪",
            "30小时换装", "夜间换装",
            "可拆装结构", "可循环装置", "可拆装VIP",
            "VR沉浸式临时空间", "短期沉浸式装置",
        ],
        "secondary_keywords": [
            "临时", "限时", "短期", "拆除", "可拆卸", "快速搭建",
            "模块化", "装置", "互动体验",
            # v1.9 补强
            "三个月", "VIP休息", "现场拼装", "预制化装配",
            "材料环保可回收", "循环材料", "拆装",
            "夜间施工", "不闭店", "周期短",
        ],
        "priority": 7,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },

    # ══════════════════════════════════════════════════════════════════════════
    # 优先级 6 — 细分/兜底类型
    # ══════════════════════════════════════════════════════════════════════════
    "special_function": {
        "name": "专项功能空间",
        "name_en": "specialty functional space home theater studio piano wine cellar cigar meditation yoga recording lab",
        "keywords": [
            "影音室", "家庭影院", "茶室", "书房", "衣帽间", "收藏室",
            # 新增专项空间类型
            "钢琴室", "乐器房", "红酒窖", "雪茄室", "私人图书室",
            "冥想室", "瑜伽房", "家用瑜伽", "第二书房",
            # v1.9 补强 (190 题反推: 私人专项空间)
            "私人衣帽间展厅", "爱马仕衣帽间", "VIP衣帽间", "高定衣帽间",
            "球鞋收藏墙", "球鞋收藏室", "手办展示墙", "手办收藏室",
            "限量收藏展示墙", "私人画廊", "白盒子画廊",
            "诗人书房", "哲学书房", "学者书房",
            "私人冥想中心", "宇宙冥想中心", "极致冥想空间",
            "茶道空间", "茶道大师茶室", "极致茶室", "私人茶道空间",
            "电竞选手训练空间", "电竞训练房", "顶级电竞空间",
            "求婚场景", "求婚布置", "浪漫装置空间",
            "数字时代的浪漫花园", "互动求婚空间",
            "诗意空间", "意象空间", "意境空间",
            "代码空间", "光影装置空间",
            "杜比全景声家庭影院", "Dolby Atmos家庭影院",
            "私人健身房", "私人CrossFit", "高强度训练空间",
            "气味实验室", "香薰实验室", "香气可视化空间",
            "私人录音棚", "私人混音室",
            "感统训练室住宅", "家庭感统训练",
        ],
        "secondary_keywords": [
            "隔音", "声学", "冥想空间", "实验室", "工坊", "训练室",
            "拍摄间", "录音室", "专业灯光",
            # v1.9 补强
            "限量", "收藏品", "恒温恒湿", "展示灯光", "防氧化",
            "意象", "意境", "诗意", "象征", "叙事",
            "声学构造", "散热", "杜比", "Dolby",
            "代码", "光影", "装置",
        ],
        "priority": 6,
        "min_secondary_hits": 2,
        "include_in_prompt": True,
    },
    "residential_collective": {
        "name": "集合住宅/公共住房",
        "name_en": "collective housing affordable apartment complex social housing co-living loft",
        "keywords": [
            "公租房", "保障房", "集合住宅", "住宅楼", "公寓楼", "居住综合体",
            "住宅小区", "人才公寓", "廉租房",
            "社会住房", "共享生活", "共居公寓",
        ],
        "secondary_keywords": [
            "集合", "多层", "高层住宅", "居住区", "住宅区", "宿舍楼",
            "学生公寓", "员工宿舍", "共居",
            "loft公寓", "阁楼公寓", "联排住宅",
        ],
        "priority": 6,
        "min_secondary_hits": 1,
        "include_in_prompt": True,
    },
    # ───────────────────────────────────────────────────────────────────────
    # 住商混合 (project_type 层) — v1.9 修复真 bug:
    #   原 keywords / secondary_keywords 均为空数组 (v1.5 残留兼容空壳)
    #   导致此 type 永远无法被命中, 复合住宅项目被错误压到 personal_residential
    #   兜底或 commercial_office。
    #
    # 与 hybrid_composite (founding_type 层) 的边界:
    #   - hybrid_residential_commercial = 空间形态层面的复合 (一栋楼/一片区里
    #     同时含住+商+办+展等不同业态的物理混合)
    #   - hybrid_composite = 项目动因层面的复合 (公益+经营 / 自用+招待 等)
    #   二者可共存: 一个项目既是空间复合(此 type), 也可能是动因复合(founding)
    # ───────────────────────────────────────────────────────────────────────
    "hybrid_residential_commercial": {
        "name": "住商混合 / 复合业态空间",
        "name_en": "hybrid residential commercial mixed use vertical composition",
        "keywords": [
            # 经典住商混合形态
            "前店后宅", "前店后厂", "下店上居", "上居下店",
            "底商住宅", "底商公寓", "商住两用", "商住一体",
            # 复合塔楼
            "复合型总部", "复合型大楼", "复合塔楼",
            "一楼商业二楼住宅", "底层商业上部住宅",
            # v1.9 冲突清理: "酒店式公寓 / 公寓酒店 / 服务式公寓"
            # 已移除 (与 commercial_hospitality 冲突, 后者作为独占主词)
            # 工作生活复合
            "居住兼工作室", "住宅加工作室", "工作室住宅",
            "前场茶席后场研发", "前场展览后场办公",
            # 复合空间
            "民宿自营", "前店后院民宿", "自住兼经营",
            "公益结合商业", "展览加住宿", "办公加住宅",
            "商业加办公加住宅", "多用途综合楼",
            # 一体化混合开发
            "混合用途开发", "混合社区", "复合社区",
            "多功能塔楼", "垂直综合体",
        ],
        "secondary_keywords": [
            "复合", "兼营", "兼做", "兼用", "混合",
            "多功能", "一体化", "垂直分层",
            "动静分区", "公共与私密分层",
            "权属分隔", "业态叠加", "分时复用",
            "互不干扰", "界面转换", "二楼住宅一楼商业",
        ],
        "priority": 7,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },

    # ══════════════════════════════════════════════════════════════════════════
    # 优先级 5 — 个人住宅（默认兜底）
    # ══════════════════════════════════════════════════════════════════════════
    "personal_residential": {
        "name": "个人住宅",
        "name_en": "residential apartment villa home interior private house villa duplex penthouse loft studio flat",
        "keywords": [
            "住宅", "公寓", "别墅", "房子", "新房", "私宅", "住房", "自住",
            "民居", "新家", "家中", "家里", "日常居住",
            # 户型规格
            "三房", "两房", "四房", "三居室", "两居室", "一居室", "五居室",
            "大平层", "小平层", "平层",
            # 楼型/产品形态
            "独栋别墅", "独栋", "联排别墅", "联排", "叠拼别墅", "叠拼",
            "洋房", "花园洋房", "豪宅", "豪宅公寓",
            "复式", "跃层", "顶层复式", "顶层", "loft户型", "阁楼",
            # 小户型
            "小户型", "迎为公寓", "微户型", "单间",
            # 持有/病态
            "婚房", "首套房", "改善型住宅", "度假屋", "度假宅", "自建房",
            # v1.9 补强 (190 题反推: 海景宅、高净值定制、特殊客群)
            "海景别墅", "山地别墅", "海景宅", "山地住宅", "山顶住宅",
            "私人住宅", "海景大平层", "高净值住宅",
            "宇宙记忆住宅", "人机共居住宅", "意识研究住宅",
            "重力适应住宅", "极地生活住宅", "极端环境住宅",
            "数字时代住宅", "未来住宅", "全屋智能住宅", "未来样板住宅",
            "韧性社区住宅", "应对气候迁徙住宅", "零碳住宅",
            "宠物优先住宅", "宠物友好住宅", "无障碍住宅",
            "出租屋", "出租单间", "城中村单间", "极小户型",
            "依维柯卡车房车", "房车", "微型住宅",
            "跨国家庭住宅", "跨文化住宅", "中美双国籍住宅",
        ],
        "secondary_keywords": [
            "卧室", "客厅", "厨房", "卫生间", "装修", "家装", "家居", "户型",
            # 延伸（次要）
            "主卧", "次卧", "儿童房", "玄关", "过道", "阳台",
            # v1.9 冲突清理: "餐厅" 与 commercial_dining 主词冲突, 删除
            # (户型内的"餐厅"由"客餐一体 / 开放式厨房 / 餐厨一体"间接表达)
            "书房", "客餐一体", "开放式厨房", "餐厨一体",
            # v1.9 补强
            "业主", "家庭结构", "生活方式", "起居", "归家", "锁上门",
            "杂志级", "豪宅感", "体面感", "成就象征", "家族传承",
            "宠物动线", "宠物舒适", "残疾人之家", "无障碍",
        ],
        "priority": 5,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
}

# =============================================================================
# 向后兼容别名 — 旧 ID → 新 ID
# 功能层级 2 — 旧 ID 兼容层
# 人话: 管"旧系统叫法怎么迁到新 type_id"。它不新增新分类，只负责把历史
# 数据库 / 状态 / 旧 ontology 里的 ID 规范化到当前 PROJECT_TYPE_REGISTRY。
# 已有数据库/状态中存储了旧 ID 的，可通过此表规范化到当前 ID
# =============================================================================
LEGACY_TYPE_ALIASES: Dict[str, str] = {
    # 旧 ontology 体系 ID → 新 detector 体系 ID
    "cultural_educational": "public_cultural",        # v3.0 → v3.2
    "office_coworking": "commercial_office",
    "hospitality_tourism": "commercial_hospitality",
    "commercial_enterprise": "commercial_enterprise",  # 保持，部分含义不同但沿用
    "urban_renewal": "urban_renewal_market",
    "heritage_conservation": "urban_renewal_heritage",
    # v3.2 新增：ontology.yaml 框架重命名产生的旧别名
    "industrial_manufacturing": "industrial_conversion",
    "education_research": "educational_facility",
    "transportation_infrastructure": "transportation_civic",
    # v8.0 新增：8 个新分类的备用别名（预留向前兼容）
    "entertainment_leisure": "leisure_entertainment",
    "bathhouse_ktv": "leisure_entertainment",
    "wedding_hall": "wedding_banquet",
    "banquet_hall": "wedding_banquet",
    "early_education": "children_family",
    "kids_space": "children_family",
    "house_renovation": "residential_renovation",
    "old_house_renovation": "residential_renovation",
    "hair_salon": "beauty_personal_care",
    "beauty_salon": "beauty_personal_care",
    "car_showroom": "automotive_showroom",
    "live_streaming": "digital_media_studio",
    "flash_store": "popup_temporary",
}


# =============================================================================
# FOUNDING_TYPE_REGISTRY  (v1.9 §4 第 0 段路由 — 战略总闸口)
# 功能层级 3 — 项目成立方式 / 终局类型注册表
# 人话: 管"这个项目为什么成立"。例如商业经营、自用改善、资产盘活、
# 品牌旗舰、城市更新、乡村振兴、公共服务。它和 project_type 正交，
# 用来避免系统只按"室内画图"理解项目。
# 成立方式 / 终局类型注册表 — 与 PROJECT_TYPE_REGISTRY 平行注册
#
# v1.9 关键变更 (基于五份参考意见交叉校验):
#   1. 删除 new_brand / brand_renovation → 迁移到 project_condition_registry
#   2. 新增 organizational_efficiency (组织效能型办公)
#   3. 新增 urban_renewal / rural_revitalization
#   4. 私宅细分为 personal_use / family_legacy / identity_expression /
#      healing_repair / special_needs_care
#   5. 新增 flagship_demonstration / commercial_renewal / asset_value_upgrade
#   6. 新增 negative_co_occurrence 字段防止误判
#   运行时事实源: config/registries/founding_type_registry.yaml (v1.9)
#   下方内联表仅作为 YAML 缺失/损坏时的兜底。
#
# 字段说明:
#   name             : 中文显示标签
#   name_en          : 英文检索上下文
#   keywords         : 主关键词，命中权重 ×2
#   secondary_keywords: 次要关键词，命中权重 ×1
#   priority         : 优先级，与 PROJECT_TYPE_REGISTRY 同语义
#   status           : active_mvp / active_light / reserved_light / reserved
#   group            : 分组标识 (commercial/personal/urban/rural/institutional/hybrid)
#   negative_co_occurrence: 共现降权 (与某些 founding_type 共现时 score 降低)
# =============================================================================
FOUNDING_TYPE_REGISTRY: Dict[str, Dict[str, Any]] = {
    # ──── 一、商业经营组 ────
    "operating_business": {
        "name": "经营性项目",
        "name_en": "operating business commercial revenue",
        "group": "commercial",
        "keywords": [
            "开店", "外带", "翻台", "坪效", "试营业", "营业", "经营",
            "出杯", "客单价", "毛利", "翻桌率", "营收", "盈利",
            "开业", "门店运营", "招商", "营业额", "销售转化", "复购",
            "客流提升", "商业闭环", "留存率", "获客成本",
        ],
        "secondary_keywords": [
            "商业", "客户", "顾客", "消费者", "回头客", "客流",
            "销售", "转化率", "到店", "留存", "下单", "营业时间",
            "高峰", "现金流",
        ],
        "negative_co_occurrence": ["public_service", "rural_revitalization", "urban_renewal"],
        "priority": 9,
        "status": "active_mvp",
    },
    "flagship_demonstration": {
        "name": "旗舰示范 / 标杆样板",
        "name_en": "flagship demonstration benchmark prototype",
        "group": "commercial",
        "keywords": [
            "旗舰店", "标杆店", "示范店", "形象店", "体验中心",
            "样板房", "样板项目", "示范中心", "标杆项目", "行业示范",
            "全新旗舰", "首个样板", "可复制模型", "产品线样板",
            "品牌展示馆", "品牌体验馆", "全球总部", "中国旗舰",
            "标志性项目",
        ],
        "secondary_keywords": [
            "示范", "样板", "标杆", "复制", "形象", "引领", "展示",
            "原型", "起步形象", "模型项目", "行业突破", "战略形象",
            "试点",
        ],
        "negative_co_occurrence": ["personal_use", "healing_repair"],
        "priority": 8,
        "status": "active_mvp",
    },
    "commercial_renewal": {
        "name": "商业更新 / 存量商业改造",
        "name_en": "commercial renewal retail repositioning",
        "group": "commercial",
        "keywords": [
            "商业更新", "商场改造", "商业街区升级", "商业空间升级",
            "客流下降", "商业综合体改造", "百货升级", "生活方式中心",
            "夜经济", "主力店", "次主力", "租户组合", "动线优化",
            "招商调整", "商业活化", "业态重组", "客流回升",
            "不闭店改造", "商业再定位",
        ],
        "secondary_keywords": [
            "客流", "租金", "坪效", "品牌组合", "业态", "打卡点",
            "社交场景", "夜间", "消费场景", "商业地产", "换装", "翻新",
        ],
        "priority": 8,
        "status": "active_mvp",
    },
    "asset_value_upgrade": {
        "name": "资产价值提升 / 存量资产盘活",
        "name_en": "asset value upgrade property appreciation",
        "group": "commercial",
        "keywords": [
            "资产增值", "物业增值", "存量资产", "资产盘活", "物业改造",
            "租金提升", "空置率", "入住率", "资产运营", "地产溢价",
            "土地价值", "物业价值", "商业地产升级", "公共空间升级",
            "不大规模结构改造", "招商提振", "持有型资产", "重资产",
            # v1.9 补强 (避免 §76 香格里拉客房升级 误判为 urban_renewal)
            "客房升级", "酒店升级", "酒店改造", "客房改造",
            "客房翻新", "保持原有结构", "保持结构不变", "提振入住率",
            "重建信心", "重新建立信心", "品牌吸引力",
        ],
        "secondary_keywords": [
            "租户", "招租", "回报率", "收益", "运营收益", "现金流",
            "投资回收", "持有", "空置", "出租率", "投资人",
            "客房", "入住", "客群重定位",
        ],
        "priority": 8,
        "status": "active_mvp",
    },

    # ──── 二、私人生活组 ────
    "personal_use": {
        "name": "自用 / 私人生活项目",
        "name_en": "personal use private residence self-occupied",
        "group": "personal",
        "keywords": [
            "自住", "私宅", "私人住宅", "自用", "我家", "我们家",
            "自家", "家里", "新房装修", "改善型住宅", "婚房", "大平层",
            "别墅", "别墅装修", "公寓装修", "住宅翻新", "私人书房",
            "卧室改造", "居家", "自家装修", "入住", "家居", "居住",
            # v1.9 补强 (避免 §12 麓山别墅 None 命中)
            "豪宅", "洋房", "独栋", "联排", "复式", "跃层", "顶层",
            "三居", "四居", "三室", "四室",
        ],
        "secondary_keywords": [
            "家人", "起居", "日常", "家庭", "收纳", "卧室", "客厅",
            "厨房", "卫生间", "玄关", "阳台", "户型", "生活方式",
        ],
        "negative_co_occurrence": ["operating_business", "flagship_demonstration", "public_service"],
        "priority": 9,
        "status": "active_mvp",
    },
    "family_legacy": {
        "name": "家族传承 / 家庭秩序重建",
        "name_en": "family legacy generational continuity",
        "group": "personal",
        "keywords": [
            "家族传承", "多代同堂", "家族精神", "家庭传承", "家庭秩序",
            "家族会客", "家族聚会", "祖孙", "家族宅", "老宅更新", "传家",
            "家族记忆", "三代人", "家族议事", "家族客厅", "长辈短住",
            "外公外婆", "父母同住",
        ],
        "secondary_keywords": [
            "长辈", "子代", "亲情", "家庭关系", "代际", "家庭结构",
            "家族仪式", "亲属", "多代", "兄弟姐妹", "家庭重组", "再婚家庭",
        ],
        "priority": 8,
        "status": "active_light",
    },
    "identity_expression": {
        "name": "身份表达 / 精神画像项目",
        "name_en": "identity expression personal symbolic",
        "group": "personal",
        "keywords": [
            "身份表达", "精神结构", "成就象征", "个人气质", "生活态度",
            "自我认同", "精神表达", "审美人格", "企业家精神", "女性独立精神",
            "文人精神", "生活美学", "权力感", "体面感", "圈层认同",
            "高净值", "收藏家", "主理人精神", "跨文化身份", "不婚主义",
            "一代创业者",
        ],
        "secondary_keywords": [
            "气场", "象征", "叙事", "品味", "圈层", "自律", "优雅",
            "厚度", "克制", "尊严", "财富", "成就", "独立", "桀骜",
        ],
        "negative_co_occurrence": ["operating_business", "public_service"],
        "priority": 8,
        "status": "active_light",
    },
    "healing_repair": {
        "name": "疗愈修复 / 情绪与关系支持",
        "name_en": "healing repair emotional relational support",
        "group": "personal",
        "keywords": [
            "疗愈", "情绪修复", "心理安全", "焦虑", "失眠", "正念",
            "冥想", "重新开始", "婚姻修复", "情绪缓冲", "心理恢复",
            "临终关怀", "创伤修复", "安静陪伴", "抗焦虑",
            # v1.9: "复合" 改为更明确的语义 (避免和 hybrid_composite 的"复合用途"冲突)
            "婚姻复合", "夫妻复合", "感情复合",
            "重建关系", "内观", "静修", "心境", "修复关系",
        ],
        "secondary_keywords": [
            "温暖", "私密", "放松", "安全感", "平静", "慢下来", "呼吸",
            "光线节律", "声环境", "触感", "沉静", "修复", "恢复", "仪式",
        ],
        "priority": 8,
        "status": "active_light",
    },
    "special_needs_care": {
        "name": "特殊需求照护 / 无障碍 / 医疗适配",
        "name_en": "special needs care accessibility medical adaptation",
        "group": "personal",
        "keywords": [
            "自闭症", "感统训练", "无障碍", "轮椅", "过敏", "低敏",
            "医疗级新风", "空气净化", "护理动线", "新生儿", "产妇",
            "老年照护", "失能", "行动不便", "康复", "适老化", "适老化改造",
            "残障", "心理干预", "创伤敏感", "医疗适配", "全屋无障碍",
        ],
        "secondary_keywords": [
            "安全", "照护", "辅助", "适老", "防滑", "隔音", "净化",
            "材料安全", "尺度", "情绪稳定", "特殊需求", "陪护",
        ],
        "priority": 8,
        "status": "active_light",
    },

    # ──── 三、城市与乡村组 ────
    "urban_renewal": {
        "name": "城市更新 / 街区微更新",
        "name_en": "urban renewal micro regeneration adaptive reuse",
        "group": "urban",
        "keywords": [
            "城市更新", "微更新", "老城区", "老街区", "历史街区",
            "城中村改造", "街巷界面", "底商改造", "公共节点", "片区更新",
            "社区更新", "城市公共客厅", "滨水界面", "夜间文化市集",
            "街区活化", "工业厂区改造", "废弃工厂改造", "旧厂房改造",
            "历史建筑活化", "工业遗存", "老码头", "防空洞改造",
            "菜市场更新", "百货商场改造", "街区焕新", "城市记忆",
            "地下空间活化",
        ],
        "secondary_keywords": [
            "街道", "巷道", "界面", "存量", "活力", "公共空间",
            "社区参与", "肌理", "保留", "非标店铺", "灯光升级", "改造",
            "旧改", "活化", "再生", "适应性改造", "文物保护", "历史保护",
        ],
        "priority": 9,
        "status": "active_mvp",
    },
    "rural_revitalization": {
        "name": "乡村振兴 / 农文旅激活",
        "name_en": "rural revitalization agro cultural tourism",
        "group": "rural",
        "keywords": [
            "乡村振兴", "新农村建设", "美丽乡村", "示范村", "乡村旅游",
            "农文旅", "农文旅融合", "民宿集群", "乡村公共空间", "村庄更新",
            "农产品销售", "乡村经济", "村民参与", "留守儿童", "乡村书屋",
            "非遗工坊", "生态研学", "乡建", "村庄改造", "自建房",
            "农村民居", "田园民居", "返乡住宅", "乡村振兴示范", "村集体",
            "在地农耕", "乡村人才回流",
        ],
        "secondary_keywords": [
            "农耕文化", "在地材料", "村民", "返乡", "农田", "乡土建筑",
            "农产品", "产业结构", "公共会客厅", "农村", "村庄", "田园",
            "古村", "乡土", "在地", "非遗",
        ],
        "priority": 9,
        "status": "active_mvp",
    },

    # ──── 四、机构与组织组 ────
    "organizational_efficiency": {
        "name": "组织效能 / 高精办公空间",
        "name_en": "organizational efficiency productivity workspace",
        "group": "institutional",
        "keywords": [
            "集团总部", "研发中心", "企业办公室", "创客空间", "联合办公",
            "直播基地", "智能实验室", "数据安全指挥中心", "算力中心",
            "生产车间", "工作室", "联合工作室", "共享办公", "律师事务所",
            "律所", "写字楼", "总部大楼", "行政会所", "工程师文化",
            "AI研发", "协同办公", "跨境电商直播基地", "实验室办公",
            "创作工作室", "制片工作室", "元宇宙办公", "VR办公",
            "注意力经济公司", "AI生成内容",
        ],
        "secondary_keywords": [
            "生产力提振", "组织文化物化", "协作动线", "设备散热负荷",
            "声学隔离系统", "电力冗余", "数字孪生集成度", "行为热力图",
            "可迭代弹性模块", "员工", "工位", "会议", "协作", "创新",
            "研发", "工程师", "团队", "灵感",
        ],
        "priority": 8,
        "status": "active_mvp",
    },
    "public_service": {
        "name": "公共服务 / 民生与社区效益",
        "name_en": "public service civic community welfare resilience",
        "group": "institutional",
        "keywords": [
            "公共服务", "社区服务", "政府项目", "村民", "市民中心",
            "公益项目", "公益空间", "便民服务", "社区共享厨房",
            "应急避难空间", "青少年心理干预中心", "银发再就业中心",
            "保障性住房", "保障房", "社区中心", "城市记忆馆",
            "难民社区服务中心", "战后社区恢复中心", "韧性社区",
            "灾害模拟训练中心", "公共应急", "公共图书馆", "社区活动中心",
            "留守儿童服务", "老人活动中心", "数字游民服务中心", "文明档案库",
        ],
        "secondary_keywords": [
            "政府", "财政", "公共", "公益", "社区", "村集体",
            "社会包容性", "弱势群体", "通用设计", "无障碍底线",
            "尊严感表达", "灾时快速转换", "社会效益", "韧性", "防灾",
            "难民", "灾后", "民生",
        ],
        "priority": 8,
        "status": "active_mvp",
    },

    # ──── 五、文化与机构组 ────
    "cultural_institution": {
        "name": "文化机构 / 公共文化与展示",
        "name_en": "cultural institution heritage public culture exhibition",
        "group": "institutional",
        "keywords": [
            "美术馆", "博物馆", "文化机构", "公共文化", "艺术机构",
            "文化驿站", "城市书房", "私人博物馆", "文化综合体", "展示馆",
            "体验馆", "体验中心", "科普教育", "展示中心", "品牌展示",
            "科技展示", "数据可视化", "互动装置", "沉浸式体验",
            "能源教育博物馆", "行为经济学体验馆", "氢能展示馆",
            "太空旅游体验中心", "数据遗产博物馆", "电竞文化博物馆",
            "历史展厅", "城市形象展示中心", "国际学校图书馆", "学校",
            "大学", "研学基地", "教育中心", "培训中心", "数字课堂",
        ],
        "secondary_keywords": [
            "策展", "馆藏", "公教", "非营利", "文物", "叙事轴线",
            "观展人流", "展陈路径", "沉浸式", "符号学", "教育", "普及",
            "参观", "多媒体", "文化地标", "文化记忆", "学习", "研究",
        ],
        "priority": 8,
        "status": "active_mvp",
    },

    # ──── 六、复合 ────
    "hybrid_composite": {
        "name": "复合性质项目",
        "name_en": "hybrid composite mixed purpose",
        "group": "hybrid",
        "keywords": [
            "前店后宅", "自住兼经营", "民宿自营", "公益结合商业",
            "复合用途", "混合大楼", "多功能厅", "分时复用", "酒店式公寓",
            "会所住宅复合", "社区复合空间", "商业加办公", "办公加住宅",
            "展览加住宿", "工作室加住宅", "农业加艺术加居住", "生活加研究",
            "住宅加工作室", "平灾两态", "平时灾时切换",
        ],
        "secondary_keywords": [
            "兼", "兼营", "混合", "复合", "多功能", "一体化", "跨界",
            "组合", "弹性切换", "双态", "同时承担", "既...又",
        ],
        "priority": 6,
        "status": "active_mvp",
    },
}


# =============================================================================
# SUBDOMAIN_REGISTRY  (v1.8 §6.1 子域受控枚举)
# 功能层级 4 — 子域 / 细分业态注册表
# 人话: 管"大类型下面的细分业态"。例如 commercial_dining 下面的
# tea_drink_store。茶饮店、咖啡馆、眼镜店、律师事务所这类细分，不要
# 默认膨胀成一级 project_type，优先作为 subdomain / industry_domain 承接。
# 子域必须挂在 parent_project_type_id 下；activation_pack_id 对应激活包
# 字段说明:
#   name              : 中文显示标签
#   parent_project_type_id: 父项目类型 ID
#   activation_pack_id    : 关联激活包 ID
#   signal_keywords       : 用于识别本子域的"信号关键词"
#                           (来自 SPECIALTY_TAG_MAP 升级，仅为信号源，
#                            最终 subdomain_id 由 SpaceClassificationService 冻结)
#   status                : active_mvp / reserved_light / reserved
# =============================================================================
SUBDOMAIN_REGISTRY: Dict[str, Dict[str, Any]] = {
    "tea_drink_store": {
        "name": "茶饮店",
        "parent_project_type_id": "commercial_dining",
        "activation_pack_id": "tea_drink_store_pack",
        "signal_keywords": [
            "茶饮店", "茶饮", "奶茶店", "奶茶", "新茶饮",
            "茶饮品牌", "果茶", "鲜果茶",
        ],
        "status": "active_mvp",
    },
    "coffee_shop": {
        "name": "咖啡馆",
        "parent_project_type_id": "commercial_dining",
        "activation_pack_id": "coffee_shop_pack",
        "signal_keywords": [
            "咖啡馆", "咖啡店", "精品咖啡", "咖啡品牌",
        ],
        "status": "reserved_light",
    },
}


# =============================================================================
# INDUSTRY_DOMAIN_REGISTRY  (v1.10 新增)
# 功能层级 5 — 行业属性 / 职业产业语境注册表
# 人话: 管"这个空间服务哪个行业"。例如法律服务、科技 AI、汽车、眼镜视光。
# 它不替代 project_type，而是与 project_type 组合：律师事务所 =
# commercial_office + legal_service，眼镜店 = commercial_retail + eyewear_optical。
# 行业语境受控枚举 — 与 project_type / founding_type 正交
#
# 设计原则:
#   - project_type 回答"这是什么空间机制"
#   - industry_domain 回答"服务于哪个行业语境"
#   - 未命中行业时允许 unspecified/unknown, 不阻断主分类
#
# 字段说明:
#   name                  : 中文显示标签
#   keywords              : 主关键词，命中权重 ×2
#   secondary_keywords    : 次关键词，命中权重 ×1
#   preferred_project_types: 与哪些 project_type 常共现（仅小幅加权）
#   priority              : 行业区分优先级（1-15）
#   maturity_level        : L1_tagged / L2_profiled / L3_packed
# =============================================================================
INDUSTRY_DOMAIN_REGISTRY: Dict[str, Dict[str, Any]] = {
    "legal_service": {
        "name": "法律服务",
        "keywords": ["律师事务所", "律所", "律师", "法律咨询", "合规", "法务", "仲裁"],
        "secondary_keywords": ["卷宗", "案卷", "签约室", "会客保密", "证据", "尽调"],
        "preferred_project_types": ["commercial_office"],
        "priority": 9,
        "maturity_level": "L2_profiled",
        "status": "active_light",
    },
    "technology_ai": {
        "name": "科技/AI/互联网",
        "keywords": ["AI", "人工智能", "算法", "互联网", "SaaS", "数据平台", "研发中心"],
        "secondary_keywords": ["工程师", "算力", "数据安全", "产品研发", "敏捷", "协作"],
        "preferred_project_types": ["commercial_office", "commercial_enterprise"],
        "priority": 9,
        "maturity_level": "L2_profiled",
        "status": "active_light",
    },
    "financial_service": {
        "name": "金融服务",
        "keywords": ["投行", "证券", "基金", "私募", "财富管理", "银行", "金融科技"],
        "secondary_keywords": ["风控", "审计", "合规审查", "高净值", "路演", "交易"],
        "preferred_project_types": ["commercial_office", "commercial_enterprise"],
        "priority": 8,
        "maturity_level": "L1_tagged",
        "status": "active_light",
    },
    "healthcare_medical": {
        "name": "医疗健康",
        "keywords": ["医院", "诊所", "牙科", "医疗", "体检", "康复", "月子中心"],
        "secondary_keywords": ["护理", "医生", "治疗", "诊疗", "无菌", "隐私"],
        "preferred_project_types": ["healthcare_wellness", "community_public"],
        "priority": 9,
        "maturity_level": "L2_profiled",
        "status": "active_mvp",
    },
    "education_training": {
        "name": "教育培训",
        "keywords": ["学校", "教育", "培训", "研学", "课堂", "教学", "托育"],
        "secondary_keywords": ["教研", "课程", "师生", "学习路径", "公教"],
        "preferred_project_types": ["educational_facility", "public_cultural"],
        "priority": 8,
        "maturity_level": "L1_tagged",
        "status": "active_light",
    },
    "culture_art": {
        "name": "文化艺术",
        "keywords": ["博物馆", "美术馆", "艺术", "策展", "画廊", "非遗", "文化机构"],
        "secondary_keywords": ["馆藏", "展陈", "公教活动", "文化记忆", "叙事"],
        "preferred_project_types": ["public_cultural", "urban_renewal_heritage"],
        "priority": 8,
        "maturity_level": "L1_tagged",
        "status": "active_light",
    },
    "automotive": {
        "name": "汽车行业",
        "keywords": ["汽车", "4S", "试驾", "新能源车", "车展", "改装"],
        "secondary_keywords": ["交车", "展车", "售后", "车主", "品牌体验"],
        "preferred_project_types": ["automotive_showroom", "brand_experience", "commercial_retail"],
        "priority": 7,
        "maturity_level": "L1_tagged",
        "status": "active_light",
    },
    "retail_apparel_luxury": {
        "name": "时尚/奢侈品零售",
        "keywords": ["奢侈品", "精品店", "时尚", "服饰", "珠宝", "高定", "买手"],
        "secondary_keywords": ["试戴", "VIP", "陈列", "品牌叙事", "限量"],
        "preferred_project_types": ["commercial_retail", "brand_experience"],
        "priority": 7,
        "maturity_level": "L1_tagged",
        "status": "active_light",
    },
    "eyewear_optical": {
        "name": "眼镜视光",
        "keywords": ["眼镜店", "视光", "验光", "镜架", "镜片", "配镜"],
        "secondary_keywords": ["试戴", "视力检查", "验配", "咨询", "镜面"],
        "preferred_project_types": ["commercial_retail", "healthcare_wellness", "brand_experience"],
        "priority": 8,
        "maturity_level": "L1_tagged",
        "status": "active_light",
    },
    "pet_service": {
        "name": "宠物服务",
        "keywords": ["宠物", "宠物医院", "宠物店", "宠物护理", "宠物殡葬", "宠物纪念"],
        "secondary_keywords": ["告别", "宠物家属", "寄养", "洗护", "纪念"],
        "preferred_project_types": ["healthcare_wellness", "special_function", "community_public"],
        "priority": 6,
        "maturity_level": "L1_tagged",
        "status": "reserved_light",
    },
}


# =============================================================================
# Boundary Cases 加载器  (v1.9 新增, schema v2.0 配套)
# 功能层级 6 — 高风险边界案例加载器
# 人话: 管"哪些词一出现就容易误判"。例如民宿集群、展厅、养老社区、
# 工业遗存。boundary 只输出 case_id 给下游二次判断，不直接给 project_type 加分。
# -----------------------------------------------------------------------------
# 事实源: config/space_classification/boundary_cases.yaml (21 个 case)
# 消费时机: detect_with_details() 命中 boundary_keyword 时, 把对应 case_id
#           写入输出的 boundary_case_ids 字段
#
# 设计原则:
#   - boundary_keyword 命中**不直接加分**, 不影响 _build_candidate_set 的 scoring
#   - 只生成 case_ids 信号给 SpaceClassificationService 用于二次判断
#   - yaml 缺失/损坏时返回空集合, 不影响 detector 运行 (零运行时风险)
# =============================================================================
_BOUNDARY_CASES_PATH = (
    Path(__file__).resolve().parent.parent
    / "config" / "space_classification" / "boundary_cases.yaml"
)

_boundary_cases_cache: Optional[Dict[str, Any]] = None


def _load_boundary_cases() -> Dict[str, Any]:
    """加载 boundary_cases.yaml (带进程级缓存)"""
    global _boundary_cases_cache
    if _boundary_cases_cache is not None:
        return _boundary_cases_cache
    if not _BOUNDARY_CASES_PATH.exists():
        logger.debug("[BoundaryCases] boundary_cases.yaml 不存在, boundary 检测禁用")
        _boundary_cases_cache = {}
        return _boundary_cases_cache
    try:
        import yaml  # type: ignore
        with open(_BOUNDARY_CASES_PATH, "r", encoding="utf-8") as f:
            _boundary_cases_cache = yaml.safe_load(f) or {}
        cases_count = len(_boundary_cases_cache.get("cases") or {})
        logger.info(f"[BoundaryCases] 加载 {cases_count} 个 boundary cases")
    except Exception as exc:
        logger.warning(f"[BoundaryCases] 解析失败, boundary 检测禁用: {exc}")
        _boundary_cases_cache = {}
    return _boundary_cases_cache


def reload_boundary_cases() -> None:
    """清空 boundary_cases 缓存 (admin / 测试用)"""
    global _boundary_cases_cache
    _boundary_cases_cache = None


def _build_boundary_keyword_index() -> Dict[str, List[str]]:
    """
    构建反向索引: keyword → [case_id1, case_id2, ...]
    用于 detect_with_details() 快速查找命中了哪些 boundary cases

    Returns:
        {keyword: [case_id, ...], ...}
    """
    bc = _load_boundary_cases()
    cases = bc.get("cases") or {}
    index: Dict[str, List[str]] = {}
    for case_id, case_def in cases.items():
        for kw in (case_def.get("boundary_keywords") or []):
            index.setdefault(kw, []).append(case_id)
    return index


# 进程级缓存反向索引
_boundary_keyword_index_cache: Optional[Dict[str, List[str]]] = None


def _get_boundary_keyword_index() -> Dict[str, List[str]]:
    """获取反向索引 (带缓存)"""
    global _boundary_keyword_index_cache
    if _boundary_keyword_index_cache is None:
        _boundary_keyword_index_cache = _build_boundary_keyword_index()
    return _boundary_keyword_index_cache


# =============================================================================
# SPATIAL_EXTENT_KEYWORDS  (v1.8 §7.1 空间范围关键词)
# 功能层级 7 — 空间范围线索
# 人话: 管"项目发生在多大空间范围"。例如室内、建筑、场地、园区、街区、
# 区域。这里只出线索，不直接合成最终 project_scale。
# 仅作为 detector 输出"线索"，不合成最终 project_scale
# =============================================================================
SPATIAL_EXTENT_KEYWORDS: Dict[str, List[str]] = {
    "interior": [
        "室内", "店面", "店铺", "门店", "装修", "户型",
        "硬装", "软装", "局部改造", "室内空间",
    ],
    "building": [
        "建筑", "整栋", "整楼", "立面", "外立面",
        "屋顶", "幕墙", "结构改造", "建筑改造",
        "单体建筑",
    ],
    "site": [
        "场地", "用地", "地块", "庭院", "园区景观",
        "景观设计", "总图",
    ],
    "cluster": [
        "建筑群", "园区", "校区", "营地", "民宿集群",
        "组团", "建筑组合",
    ],
    "district": [
        "街区", "城市更新", "片区", "老旧小区改造",
        "历史街区", "街道",
    ],
    "regional": [
        "区域", "全域", "市域", "县域", "文旅规划",
        "产业园规划", "片区规划",
    ],
}


# =============================================================================
# LIFECYCLE_KEYWORDS  (v1.8 §7.2 生命周期关键词)
# 功能层级 8 — 生命周期线索
# 人话: 管"项目处在什么阶段"。例如装修、改造、活化、新建、临时。它和
# 空间范围一起交给 SpaceClassificationService 合成 project_scale。
# 仅作为线索；与 runtime_modifiers.lifecycle 协同 (装配在 SpaceClassificationService)
# =============================================================================
LIFECYCLE_KEYWORDS: Dict[str, List[str]] = {
    "fitout": [
        "装修", "开店", "新店", "首店", "硬装", "软装",
        "精装", "整装",
    ],
    "renovation": [
        "改造", "翻新", "重装", "拆改", "格局改造",
        "二次装修", "二手房改造",
    ],
    "adaptive_reuse": [
        "活化", "再生", "适应性改造", "老建筑改造",
        "工业遗存", "历史建筑活化",
    ],
    "newbuild": [
        "新建", "新建建筑", "拿地", "从零开始建",
        "新楼盘",
    ],
    "temporary": [
        "快闪", "临时", "短期", "限时", "拆除",
        "可拆卸", "模块化搭建",
    ],
}


# =============================================================================
# 公用工具函数 — 全局唯一出处，下游直接 import 使用
# 功能层级 9 — 公用读取函数
# 人话: 管"下游怎么拿中文名、英文名、全部类型、旧 ID 规范化结果"。
# 下游不要自己维护 type_id 到中文名的字典，统一从这里读。
# =============================================================================

def get_type_label(type_id: str, fallback: str = "") -> str:
    """
    功能 9.1 — 读取项目类型中文名。
    人话: 给下游统一返回 type_id 的中文显示名，避免各处重复写映射表。

    根据项目类型 ID 返回中文显示标签。

    这是全局唯一的 ID→标签 映射出处，所有模块必须调用此函数，
    禁止在其他文件中自行维护字典。

    Args:
        type_id: 项目类型 ID（支持旧别名自动转换）
        fallback: 找不到时的默认值，默认返回 type_id 本身

    Returns:
        中文标签字符串
    """
    # 合并注册表：静态 + 扩展
    merged = {**PROJECT_TYPE_REGISTRY, **_load_extension_registry()}
    canonical_id = LEGACY_TYPE_ALIASES.get(type_id, type_id)
    entry = merged.get(canonical_id)
    if entry:
        return entry["name"]
    return fallback if fallback is not None else type_id


def get_type_name_en(type_id: str) -> str:
    """
    功能 9.2 — 读取项目类型英文检索上下文。
    人话: 给 query_builder / few-shot 用，不让下游自己拼英文语义。
    """
    merged = {**PROJECT_TYPE_REGISTRY, **_load_extension_registry()}
    canonical_id = LEGACY_TYPE_ALIASES.get(type_id, type_id)
    entry = merged.get(canonical_id)
    if entry:
        return entry.get("name_en", type_id)
    return type_id


def get_all_type_ids(include_in_prompt_only: bool = False) -> List[str]:
    """
    功能 9.3 — 读取全部项目类型 ID。
    人话: 给 prompt、校验、后台列表使用；是否进入 prompt 由 include_in_prompt 控制。

    返回全部项目类型 ID 列表（静态注册表 + 已审批扩展）。

    Args:
        include_in_prompt_only: True → 仅返回 include_in_prompt=True 的类型
    """
    merged = {**PROJECT_TYPE_REGISTRY, **_load_extension_registry()}
    if include_in_prompt_only:
        return [tid for tid, cfg in merged.items() if cfg.get("include_in_prompt", True)]
    return list(merged.keys())


def normalize_type_id(type_id: str) -> str:
    """
    功能 9.4 — 规范化旧 type_id。
    人话: 旧系统传来的名字先在这里转成当前标准 ID。
    """
    return LEGACY_TYPE_ALIASES.get(type_id, type_id)


# =============================================================================
# Registry meta (v1.8 §6.4 Registry Contract)
# 功能层级 10 — project_type 元数据覆盖层读取
# 人话: 管"PROJECT_TYPE_REGISTRY 这些类型在治理层是什么状态"。例如 status、
# aliases、owner、review_status。行为事实源仍是 .py，YAML 只做 meta overlay。
# 默认值兜底: 已注册类型若未显式声明 status/owner/review_status,
# 在访问时按以下默认值返回, 避免一次性批量修改 30+ 条目。
# =============================================================================
_REGISTRY_DEFAULT_META: Dict[str, Any] = {
    "status": "active_mvp",
    "aliases": [],
    "owner": "core_team",
    "review_status": "approved",
}


def get_type_meta(type_id: str) -> Dict[str, Any]:
    """
    功能 10.1 — 读取项目类型治理元数据。
    人话: 把 .py 里的行为事实源和 YAML 里的 status / aliases / owner 合起来返回。

    返回类型的 v1.8 §6.4 meta 字段 (status/aliases/owner/review_status)。
    project_type_registry_meta.yaml 是 meta overlay; 未显式声明的字段返回 defaults。
    """
    merged = {**PROJECT_TYPE_REGISTRY, **_load_extension_registry()}
    canonical_id = LEGACY_TYPE_ALIASES.get(type_id, type_id)
    entry = merged.get(canonical_id, {})
    meta_yaml = load_project_type_registry_meta_yaml() if "load_project_type_registry_meta_yaml" in globals() else None
    yaml_defaults = (meta_yaml or {}).get("defaults") or {}
    defaults = {**_REGISTRY_DEFAULT_META, **yaml_defaults}
    overlay = ((meta_yaml or {}).get("items") or {}).get(canonical_id, {})
    meta = {
        "type_id": canonical_id,
        "display_name": overlay.get("display_name") or entry.get("name", canonical_id),
        "status": overlay.get("status", entry.get("status", defaults["status"])),
        "aliases": overlay.get("aliases", entry.get("aliases", defaults["aliases"])),
        "owner": overlay.get("owner", entry.get("owner", defaults["owner"])),
        "review_status": overlay.get("review_status", entry.get("review_status", defaults["review_status"])),
        "meta_source": "project_type_registry_meta.yaml" if meta_yaml else "inline_defaults",
        "canonical_type_source": "project_type_detector.py::PROJECT_TYPE_REGISTRY",
    }
    return meta


def get_founding_type_label(founding_type_id: str) -> str:
    """
    功能 10.2 — 读取成立方式中文名。
    人话: 把 operating_business 这类 ID 转成人能读的中文标签。
    """
    entry = FOUNDING_TYPE_REGISTRY.get(founding_type_id, {})
    return entry.get("name", founding_type_id)


def get_subdomain_meta(subdomain_id: str) -> Optional[Dict[str, Any]]:
    """
    功能 10.3 — 读取子域元数据。
    人话: 查某个子域挂在哪个大类型下、绑定哪个 activation_pack。
    """
    return SUBDOMAIN_REGISTRY.get(subdomain_id)


# =============================================================================
# 业态父分类映射（Steps 9-12 两阶段检测）
# 功能层级 11 — 父桶聚合兼容层
# 人话: 管"把 32 个 project_type 粗略归到住宅、酒店、办公、零售等父桶"。
# 这是旧下游和统计聚合用的兼容层，不是新分类主协议。
# type_id → parent_type（宽泛业态桶，供两阶段检测的第一阶段使用）
#
# ⚠️ v1.8 标记: deprecated_compat / aggregation_only
#   v1.8 §4 字段规则: parent_type 只可用于兼容聚合，不进入主协议
#   新逻辑不得依赖 parent_type 推导:
#     project_type_id / subdomain_id / project_scale /
#     discipline_scope / spatial_layer_ids
#   保留用于: 旧下游 / 统计聚合 / 兜底问卷
# =============================================================================
PARENT_TYPE_MAP: Dict[str, str] = {
    # 住宅
    "personal_residential":    "residential",
    "residential_renovation":  "residential",
    # 商业餐饮/酒店
    "commercial_dining":       "hospitality",
    "commercial_hospitality":  "hospitality",
    "wedding_banquet":         "hospitality",
    # 办公
    "commercial_office":       "office",
    "digital_media_studio":    "office",
    # 零售
    "commercial_retail":       "retail",
    "beauty_personal_care":    "retail",
    "automotive_showroom":     "retail",
    "popup_temporary":         "retail",
    # 休闲娱乐
    "leisure_entertainment":   "leisure",
    "sports_entertainment_arts": "leisure",
    "performing_arts":         "leisure",
    # 教育/亲子
    "children_family":         "education",
    "educational_facility":    "education",
    # 医疗/康养
    "healthcare_wellness":     "healthcare",
    # 公共/社区
    "community_public":        "public",
    "public_cultural":         "public",
    "transportation_civic":    "public",
    "rural_construction":      "public",
    # 工业更新
    "industrial_conversion":   "industrial",
    "urban_renewal_market":    "urban_renewal",
    "urban_renewal_heritage":  "urban_renewal",
    # 品牌/展示
    "brand_experience":        "retail",
    "commercial_enterprise":   "office",
    "real_estate_showcase":    "retail",
    # 特殊
    "landscape_outdoor":       "outdoor",
    "religious_spiritual":     "special",
    "special_function":        "special",
}

# =============================================================================
# 专项标签映射（Steps 9-12）
# 功能层级 12 — specialty 辅助标签层
# 人话: 管"火锅、loft、牙科、茶饮、海景别墅这类细碎信号"。它是开放标签，
# 只做辅助证据；真正受控的细分应升级到 SUBDOMAIN_REGISTRY。
# (触发关键词, specialty_tag) — 按精确度降序（长词优先）
#
# ⚠️ v1.8 标记: 辅助证据角色 (aux signal)
#   v1.8 §4 字段规则: specialty_tag 是开放词集（hotpot/loft/...）,
#   不直接进入 classification_output 主协议;
#   subdomain_signals 才是受 SUBDOMAIN_REGISTRY 约束的封闭枚举。
#   specialty_tag 仅作为 subdomain_signals 匹配的辅助证据。
# =============================================================================
SPECIALTY_TAG_MAP: List[Tuple[str, str]] = [
    # 餐饮细分
    ("自助餐",      "buffet"),
    ("烧烤",        "bbq"),
    ("火锅",        "hotpot"),
    ("咖啡馆",      "cafe"),
    ("茶饮店",      "tea_bar"),
    ("奶茶店",      "tea_bar"),
    ("新茶饮",      "tea_bar"),
    ("精品咖啡",    "specialty_coffee"),
    ("中餐厅",      "chinese_restaurant"),
    ("日料",        "japanese_restaurant"),
    ("茶道空间",    "tea_ceremony"),
    ("茶道大师",    "tea_ceremony"),
    # 住宅细分
    ("大平层",      "flat_luxury"),
    ("海景大平层",  "flat_seaview"),
    ("海景别墅",    "villa_seaview"),
    ("山地别墅",    "villa_mountain"),
    ("独栋别墅",    "detached_villa"),
    ("叠拼",        "stacked_mansion"),
    ("loft",        "loft"),
    ("跃层",        "duplex"),
    ("复式",        "duplex"),
    ("别墅",        "villa"),
    ("公寓",        "apartment"),
    ("自建房",      "self_built_house"),
    ("农村民居",    "rural_residence"),
    ("四合院",      "courtyard_house"),
    ("民国小洋楼",  "republican_villa"),
    ("老弄堂",      "shanghai_lane"),
    # 酒店细分
    ("精品酒店",    "boutique_hotel"),
    ("树屋民宿",    "treehouse"),
    ("胶囊酒店",    "capsule_hotel"),
    ("民宿集群",    "homestay_cluster"),
    ("山地民宿",    "mountain_homestay"),
    ("民宿",        "b_and_b"),
    ("文华东方",    "luxury_hotel_brand"),
    ("雅诗阁",      "serviced_apartment_brand"),
    ("香格里拉",    "luxury_hotel_brand"),
    # 办公细分
    ("共享办公",    "co_working"),
    ("孵化器",      "incubator"),
    ("makerspace",  "makerspace"),
    ("总部大楼",    "headquarters"),
    ("研发中心",    "rnd_center"),
    ("律师事务所",  "law_firm"),
    ("律所",        "law_firm"),
    ("元宇宙办公",  "metaverse_workspace"),
    ("VR办公",      "vr_workspace"),
    ("AI算法",      "ai_lab"),
    # 娱乐细分
    ("ktv",         "ktv"),
    ("密室",        "escape_room"),
    ("棋牌",        "mahjong_room"),
    ("水会",        "spa_club"),
    # 医疗细分
    ("牙科",        "dental"),
    ("中医",        "tcm"),
    ("适老",        "age_friendly"),
    ("养老",        "elderly_care"),
    ("医美",        "aesthetic_medicine"),
    ("月子中心",    "postpartum_center"),
    ("临终关怀",    "hospice_care"),
    ("正念",        "mindfulness"),
    ("冥想",        "meditation"),
    ("自闭症",      "autism_friendly"),
    ("感统训练",    "sensory_integration"),
    ("无障碍",      "barrier_free"),
    ("过敏",        "allergy_sensitive"),
    # 教育细分
    ("幼儿园",      "kindergarten"),
    ("早教",        "early_childhood"),
    ("国际学校",    "international_school"),
    ("研学基地",    "study_tour_base"),
    # 汽车细分
    ("4s店展厅",    "auto_4s_showroom"),
    ("汽车展厅",    "auto_showroom"),
    ("NIO House",   "nio_house"),
    ("蔚来",        "nio_house"),
    # 直播细分
    ("直播间",      "live_studio"),
    ("mcn",         "mcn_studio"),
    ("跨境电商直播", "cross_border_livestream"),
    ("B站UP主",     "bilibili_upload"),
    ("UP主",        "creator_studio"),
    # 快闪
    ("快闪",        "popup"),
    ("音乐节",      "music_festival"),
    ("双年展",      "biennale"),
    # 婚宴细分
    ("婚宴",        "wedding_banquet_hall"),
    ("宴会厅",      "banquet_hall"),
    # 收藏 / 私人展厅
    ("球鞋收藏",    "sneaker_display"),
    ("手办收藏",    "figurine_display"),
    ("私人画廊",    "private_gallery"),
    ("白盒子画廊",  "white_cube_gallery"),
    # 未来 / 极端项目
    ("火星模拟",    "mars_simulation"),
    ("地下居住",    "underground_habitat"),
    ("极地",        "polar_habitat"),
    ("零碳",        "zero_carbon"),
    ("后碳",        "post_carbon"),
    ("文明档案库",  "civilization_archive"),
    ("文明重启",    "civilization_restart"),
    # 商业品牌细分
    ("旗舰店",      "flagship_store"),
    ("品牌体验店",  "brand_experience_store"),
    ("买手店",      "select_shop"),
    ("生活方式中心","lifestyle_center"),
    # 公共服务细分
    ("社区共享厨房","community_kitchen"),
    ("应急避难",    "emergency_shelter"),
    ("韧性社区",    "resilient_community"),
    ("数字游民",    "digital_nomad"),
    ("保障房",      "affordable_housing"),
    # 文化 / 研究细分
    ("行为经济学",  "behavioral_economics_lab"),
    ("AI伦理",      "ai_ethics_lab"),
    ("意识研究",    "consciousness_research"),
    ("电竞文化",    "esports_culture"),
    ("数据遗产",    "data_heritage"),
    ("语言保护",    "language_preservation"),
]


def _build_exclusivity_weights(registry: Dict[str, Any]) -> Dict[str, float]:
    """
    功能层级 13 — 关键词排他性权重。
    人话: 管"一个词越独占，命中越可靠"。比如只出现在一个类型里的词
    比到处都能出现的泛词更可信。

    计算关键词排他性权重（Step 14）。

    - 仅出现在 1 个类型中 → 1.5（独占关键词，命中更可靠）
    - 出现在 2 个类型中   → 1.2（稀有词，小幅加成）
    - 出现在 3+ 个类型中  → 1.0（通用词，不加成）
    """
    keyword_freq: Dict[str, int] = {}
    for cfg in registry.values():
        for kw in cfg.get("keywords", []) + cfg.get("secondary_keywords", []):
            keyword_freq[kw] = keyword_freq.get(kw, 0) + 1
    weights: Dict[str, float] = {}
    for kw, freq in keyword_freq.items():
        if freq == 1:
            weights[kw] = 1.5
        elif freq == 2:
            weights[kw] = 1.2
        else:
            weights[kw] = 1.0
    return weights


LOW_INFORMATION_SECONDARY_KEYWORDS = {
    # 角色/甲乙方身份，不是空间类型
    "业主",
    "设计师",
    "员工",
    "团队",
    # 设计动作/流程词，几乎所有空间都会出现
    "动线",
    "接待动线",
    "协作动线",
    "护理动线",
    "动线优化",
    "模块化",
    "可移动家具",
    # 成立动因/展示诉求，不是空间对象
    "品牌",
    "示范",
    "标杆",
    "运营",
    "成本控制",
}


# 保持向后兼容 — 旧代码直接引用 PROJECT_TYPE_KEYWORDS 的地方仍可访问
PROJECT_TYPE_KEYWORDS = PROJECT_TYPE_REGISTRY


# =============================================================================
# v1.8 YAML Registry Loader  (可选)
# 功能层级 14 — YAML registry 加载与一致性审计
# 人话: 管".py 行为事实源与 YAML 总索引 / meta overlay 有没有脱节"。用于巡检、
# CI 和后台治理，不影响 detector 日常运行。
# -----------------------------------------------------------------------------
# 设计原则:
#   1. FOUNDING_TYPE_REGISTRY 运行时由 founding_type_registry.yaml 构建。
#   2. FOUNDING_TYPE_REGISTRY / SUBDOMAIN_REGISTRY /
#      SPATIAL_EXTENT_REGISTRY / LIFECYCLE_REGISTRY 运行时由 YAML 构建。
#   3. yaml 缺失或损坏时回退到内联兜底表。
#   4. 通过 validate_registries_against_yaml() 做一致性审计 (CI / 巡检使用)
#   5. 关键词表保留为向后兼容派生视图, 不是治理事实源。
# =============================================================================

_REGISTRIES_DIR = Path(__file__).resolve().parent.parent / "config" / "registries"


def _load_yaml_safe(filename: str) -> Optional[Dict[str, Any]]:
    """
    功能 14.1 — 安全加载 registry YAML。
    人话: YAML 坏了也不让 detector 崩，最多返回 None 给审计层处理。
    """
    path = _REGISTRIES_DIR / filename
    if not path.exists():
        return None
    try:
        import yaml  # type: ignore
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as exc:
        logger.warning(f"[RegistryLoader] {filename} 解析失败, 回退到内联常量: {exc}")
        return None


def load_classification_master_index() -> Optional[Dict[str, Any]]:
    """
    功能 14.2 — 加载分类总索引。
    人话: 读取 9 张分类表 + 本体维度表的总目录。
    """
    return _load_yaml_safe("classification_master_index.yaml")


def load_project_type_registry_meta_yaml() -> Optional[Dict[str, Any]]:
    """
    功能 14.3 — 加载 project_type meta overlay。
    人话: 读取 PROJECT_TYPE_REGISTRY 的治理元数据补充层。
    """
    return _load_yaml_safe("project_type_registry_meta.yaml")


def load_founding_type_registry_yaml() -> Optional[Dict[str, Any]]:
    """
    功能 14.4 — 加载成立方式 YAML 注册表。
    人话: Founding Type 的运行时事实源。
    """
    return _load_yaml_safe("founding_type_registry.yaml")


_EMBEDDED_FOUNDING_TYPE_REGISTRY = FOUNDING_TYPE_REGISTRY


def _build_founding_type_registry_from_yaml() -> Dict[str, Dict[str, Any]]:
    """
    功能 14.4.1 — 从 YAML 构建 Founding Type 运行时注册表。

    YAML 使用治理字段 name_cn/name_en; detector 历史代码消费 name。
    这里做一次轻量适配，避免维护两份关键词表。
    """
    yaml_data = load_founding_type_registry_yaml()
    items = (yaml_data or {}).get("items") or {}
    if not items:
        logger.warning("[RegistryLoader] founding_type_registry.yaml 缺失或为空, 回退到内联兜底表")
        return _EMBEDDED_FOUNDING_TYPE_REGISTRY

    registry: Dict[str, Dict[str, Any]] = {}
    for founding_type_id, item in items.items():
        if not isinstance(item, dict):
            continue
        runtime_item = dict(item)
        runtime_item["name"] = item.get("name") or item.get("name_cn") or founding_type_id
        runtime_item["name_en"] = item.get("name_en") or ""
        runtime_item["keywords"] = list(item.get("keywords") or [])
        runtime_item["secondary_keywords"] = list(item.get("secondary_keywords") or [])
        runtime_item["negative_co_occurrence"] = list(item.get("negative_co_occurrence") or [])
        runtime_item["priority"] = int(item.get("priority") or 1)
        runtime_item["status"] = item.get("status") or "reserved"
        registry[founding_type_id] = runtime_item
    return registry


FOUNDING_TYPE_REGISTRY = _build_founding_type_registry_from_yaml()


def load_subdomain_registry_yaml() -> Optional[Dict[str, Any]]:
    """
    功能 14.5 — 加载子域 YAML 注册表。
    人话: Subdomain 的运行时事实源。
    """
    return _load_yaml_safe("subdomain_registry.yaml")


_EMBEDDED_SUBDOMAIN_REGISTRY = SUBDOMAIN_REGISTRY


def _build_subdomain_registry_from_yaml() -> Dict[str, Dict[str, Any]]:
    """
    功能 14.5.1 — 从 YAML 构建 Subdomain 运行时注册表。

    YAML 使用 name_cn/name_en 等治理字段; detector 历史代码消费 name。
    这里保持向后兼容，同时带出完整治理字段供管理后台和审计使用。
    """
    yaml_data = load_subdomain_registry_yaml()
    items = (yaml_data or {}).get("items") or {}
    if not items:
        logger.warning("[RegistryLoader] subdomain_registry.yaml 缺失或为空, 回退到内联兜底表")
        return _EMBEDDED_SUBDOMAIN_REGISTRY

    registry: Dict[str, Dict[str, Any]] = {}
    for subdomain_id, item in items.items():
        if not isinstance(item, dict):
            continue
        runtime_item = dict(item)
        runtime_item["name"] = item.get("name") or item.get("name_cn") or subdomain_id
        runtime_item["name_en"] = item.get("name_en") or ""
        runtime_item["parent_project_type_id"] = item.get("parent_project_type_id")
        runtime_item["activation_pack_id"] = item.get("activation_pack_id")
        runtime_item["signal_keywords"] = list(item.get("signal_keywords") or [])
        runtime_item["specialty_tag_assist"] = list(item.get("specialty_tag_assist") or [])
        runtime_item["aliases"] = list(item.get("aliases") or [])
        runtime_item["status"] = item.get("status") or "reserved"
        registry[subdomain_id] = runtime_item
    return registry


SUBDOMAIN_REGISTRY = _build_subdomain_registry_from_yaml()


def load_industry_registry_yaml() -> Optional[Dict[str, Any]]:
    """
    功能 14.6 — 加载行业属性 YAML 镜像。
    人话: Industry Domain 的运行时事实源。
    """
    return _load_yaml_safe("industry_registry.yaml")


_EMBEDDED_INDUSTRY_DOMAIN_REGISTRY = INDUSTRY_DOMAIN_REGISTRY


def _build_industry_domain_registry_from_yaml() -> Dict[str, Dict[str, Any]]:
    """
    功能 14.6.1 — 从 YAML 构建 Industry Domain 运行时注册表。

    YAML 使用 name_cn / defaults / review_status 等治理字段; detector 历史代码消费
    name / keywords / secondary_keywords。这里同时满足检测和后台治理。
    """
    yaml_data = load_industry_registry_yaml()
    items = (yaml_data or {}).get("items") or {}
    if not items:
        logger.warning("[RegistryLoader] industry_registry.yaml 缺失或为空, 回退到内联兜底表")
        return _EMBEDDED_INDUSTRY_DOMAIN_REGISTRY

    defaults = (yaml_data or {}).get("defaults") or {}
    registry: Dict[str, Dict[str, Any]] = {}
    for industry_id, item in items.items():
        if not isinstance(item, dict):
            continue
        runtime_item = dict(item)
        runtime_item["name"] = item.get("name") or item.get("name_cn") or industry_id
        runtime_item["keywords"] = list(item.get("keywords") or [])
        runtime_item["secondary_keywords"] = list(item.get("secondary_keywords") or [])
        runtime_item["preferred_project_types"] = list(item.get("preferred_project_types") or [])
        runtime_item["priority"] = item.get("priority", 6)
        runtime_item["maturity_level"] = item.get(
            "maturity_level",
            defaults.get("maturity_level", "L1_tagged"),
        )
        runtime_item["status"] = item.get("status", defaults.get("status", "active_light"))
        runtime_item["review_status"] = item.get("review_status") or (yaml_data or {}).get("review_status")
        runtime_item["owner"] = item.get("owner") or (yaml_data or {}).get("owner")
        runtime_item["schema_version"] = (yaml_data or {}).get("schema_version")
        registry[industry_id] = runtime_item
    return registry


INDUSTRY_DOMAIN_REGISTRY = _build_industry_domain_registry_from_yaml()


def load_spatial_extent_registry_yaml() -> Optional[Dict[str, Any]]:
    """
    功能 14.7 — 加载空间范围 YAML 注册表。
    人话: Project Scale 的空间范围线索运行时事实源。
    """
    return _load_yaml_safe("spatial_extent_registry.yaml")


def load_lifecycle_registry_yaml() -> Optional[Dict[str, Any]]:
    """
    功能 14.8 — 加载生命周期 YAML 注册表。
    人话: Project Scale 的生命周期线索运行时事实源。
    """
    return _load_yaml_safe("lifecycle_registry.yaml")


def load_spatial_layer_registry_yaml() -> Optional[Dict[str, Any]]:
    """
    功能 14.8.1 — 加载空间层 YAML 注册表。
    人话: Spatial Layer 的运行时事实源。
    """
    return _load_yaml_safe("spatial_layer_registry.yaml")


_EMBEDDED_SPATIAL_EXTENT_KEYWORDS = SPATIAL_EXTENT_KEYWORDS
_EMBEDDED_LIFECYCLE_KEYWORDS = LIFECYCLE_KEYWORDS


def _build_keyword_signal_registry_from_yaml(
    filename: str,
    fallback_keywords: Dict[str, List[str]],
    registry_label: str,
) -> Dict[str, Dict[str, Any]]:
    """
    功能 14.9 — 从 YAML 构建关键词线索类注册表。

    spatial_extent / lifecycle 历史上只有关键词表。这里补齐治理字段,
    并保留 keywords 视图给现有 detector 逻辑直接消费。
    """
    yaml_data = _load_yaml_safe(filename)
    items = (yaml_data or {}).get("items") or {}
    if not items:
        logger.warning(f"[RegistryLoader] {filename} 缺失或为空, 回退到内联 {registry_label} 兜底表")
        return {
            item_id: {
                "name": item_id,
                "name_en": "",
                "status": "reserved",
                "keywords": list(keywords),
            }
            for item_id, keywords in fallback_keywords.items()
        }

    registry: Dict[str, Dict[str, Any]] = {}
    for item_id, item in items.items():
        if not isinstance(item, dict):
            continue
        runtime_item = dict(item)
        runtime_item["name"] = item.get("name") or item.get("name_cn") or item_id
        runtime_item["name_en"] = item.get("name_en") or ""
        runtime_item["keywords"] = list(item.get("keywords") or [])
        runtime_item["status"] = item.get("status") or "reserved"
        registry[item_id] = runtime_item
    return registry


SPATIAL_EXTENT_REGISTRY = _build_keyword_signal_registry_from_yaml(
    "spatial_extent_registry.yaml",
    _EMBEDDED_SPATIAL_EXTENT_KEYWORDS,
    "spatial_extent",
)
LIFECYCLE_REGISTRY = _build_keyword_signal_registry_from_yaml(
    "lifecycle_registry.yaml",
    _EMBEDDED_LIFECYCLE_KEYWORDS,
    "lifecycle",
)

# 向后兼容: detector 仍读取关键词表, 但关键词表由 YAML runtime registry 派生。
SPATIAL_EXTENT_KEYWORDS = {
    item_id: list(item.get("keywords") or [])
    for item_id, item in SPATIAL_EXTENT_REGISTRY.items()
}
LIFECYCLE_KEYWORDS = {
    item_id: list(item.get("keywords") or [])
    for item_id, item in LIFECYCLE_REGISTRY.items()
}


def _build_spatial_layer_registry_from_yaml() -> Dict[str, Dict[str, Any]]:
    """
    功能 14.9.1 — 从 YAML 构建 Spatial Layer 运行时注册表。

    空间层不是关键词检测轴, 但它是 project_scale 到 ontology dimensions 的关键中继。
    运行时注册表用于治理、后台展示和跨文件一致性审计。
    """
    yaml_data = load_spatial_layer_registry_yaml()
    items = (yaml_data or {}).get("items") or {}
    if not items:
        logger.warning("[RegistryLoader] spatial_layer_registry.yaml 缺失或为空, 空间层运行时注册表为空")
        return {}

    registry: Dict[str, Dict[str, Any]] = {}
    for layer_id, item in items.items():
        if not isinstance(item, dict):
            continue
        runtime_item = dict(item)
        runtime_item["name"] = item.get("name") or item.get("name_cn") or layer_id
        runtime_item["name_en"] = item.get("name_en") or ""
        runtime_item["typical_objects"] = list(item.get("typical_objects") or [])
        runtime_item["related_disciplines"] = list(item.get("related_disciplines") or [])
        runtime_item["status"] = item.get("status") or "reserved"
        runtime_item["review_status"] = item.get("review_status") or (yaml_data or {}).get("review_status")
        runtime_item["owner"] = item.get("owner") or (yaml_data or {}).get("owner")
        runtime_item["schema_version"] = (yaml_data or {}).get("schema_version")
        registry[layer_id] = runtime_item
    return registry


SPATIAL_LAYER_REGISTRY = _build_spatial_layer_registry_from_yaml()


def validate_registries_against_yaml() -> Dict[str, Any]:
    """
    功能 14.10 — 注册表一致性审计。
    人话: 一次性检查 .py 行为事实源和 YAML 总索引 / meta overlay 有没有漂移。

    一致性审计: 比较运行时注册表与 yaml / meta overlay 内容, 列出差异。
    用于 CI / 定期巡检, 不影响运行时行为。

    Returns:
        {
            "project_type": {"meta_unknown_type_ids": [...], "master_link_ok": bool, ...},
            "founding_type": {"in_py_only": [...], "in_yaml_only": [...], "consistent": bool},
            "subdomain": {...},
            "spatial_extent": {...},
            "lifecycle": {...},
        }
    """
    report: Dict[str, Any] = {}

    # project_type: PROJECT_TYPE_REGISTRY 是行为事实源, project_type_registry_meta.yaml 是 meta overlay
    yaml_data = load_project_type_registry_meta_yaml()
    master_index = load_classification_master_index()
    if yaml_data:
        meta_items = set((yaml_data.get("items") or {}).keys())
        py_ids = set(PROJECT_TYPE_REGISTRY.keys())
        source_declared = yaml_data.get("canonical_type_source") or yaml_data.get("keywords_source")
        source_ok = source_declared == "intelligent_project_analyzer/services/project_type_detector.py::PROJECT_TYPE_REGISTRY"

        axis_source = (
            ((master_index or {}).get("classification_axes") or {})
            .get("project_type", {})
            .get("source", {})
        )
        master_source_ok = axis_source.get("canonical_type_source") == "../../services/project_type_detector.py::PROJECT_TYPE_REGISTRY"
        master_behavior_ok = axis_source.get("behavior_registry") == "../../services/project_type_detector.py::ProjectTypeDetector"
        master_meta_ok = axis_source.get("meta_overlay") == "project_type_registry_meta.yaml"

        report["project_type"] = {
            "canonical_source": "PROJECT_TYPE_REGISTRY",
            "meta_overlay": "project_type_registry_meta.yaml",
            "py_type_count": len(py_ids),
            "explicit_meta_count": len(meta_items),
            "meta_unknown_type_ids": sorted(meta_items - py_ids),
            "py_ids_without_explicit_meta": sorted(py_ids - meta_items),
            "defaults_cover_missing_meta": bool(yaml_data.get("defaults")),
            "meta_source_declared_ok": source_ok,
            "master_link_ok": master_source_ok and master_behavior_ok and master_meta_ok,
            "consistent": (
                not (meta_items - py_ids)
                and bool(yaml_data.get("defaults"))
                and source_ok
                and master_source_ok
                and master_behavior_ok
                and master_meta_ok
            ),
        }
    else:
        report["project_type"] = {"yaml_missing": True}

    # founding_type
    yaml_data = load_founding_type_registry_yaml()
    if yaml_data:
        yaml_ids = set((yaml_data.get("items") or {}).keys())
        py_ids = set(FOUNDING_TYPE_REGISTRY.keys())
        report["founding_type"] = {
            "in_py_only": sorted(py_ids - yaml_ids),
            "in_yaml_only": sorted(yaml_ids - py_ids),
            "consistent": py_ids == yaml_ids,
        }
    else:
        report["founding_type"] = {"yaml_missing": True}

    # subdomain
    yaml_data = load_subdomain_registry_yaml()
    if yaml_data:
        yaml_ids = set((yaml_data.get("items") or {}).keys())
        py_ids = set(SUBDOMAIN_REGISTRY.keys())
        report["subdomain"] = {
            "in_py_only": sorted(py_ids - yaml_ids),
            "in_yaml_only": sorted(yaml_ids - py_ids),
            "consistent": py_ids == yaml_ids,
        }
    else:
        report["subdomain"] = {"yaml_missing": True}

    # industry_domain
    yaml_data = load_industry_registry_yaml()
    if yaml_data:
        yaml_ids = set((yaml_data.get("items") or {}).keys())
        py_ids = set(INDUSTRY_DOMAIN_REGISTRY.keys())
        report["industry_domain"] = {
            "in_py_only": sorted(py_ids - yaml_ids),
            "in_yaml_only": sorted(yaml_ids - py_ids),
            "consistent": py_ids == yaml_ids,
        }
    else:
        report["industry_domain"] = {"yaml_missing": True}

    # spatial_extent
    yaml_data = load_spatial_extent_registry_yaml()
    if yaml_data:
        yaml_ids = set((yaml_data.get("items") or {}).keys())
        py_ids = set(SPATIAL_EXTENT_REGISTRY.keys())
        report["spatial_extent"] = {
            "in_py_only": sorted(py_ids - yaml_ids),
            "in_yaml_only": sorted(yaml_ids - py_ids),
            "consistent": py_ids == yaml_ids,
        }
    else:
        report["spatial_extent"] = {"yaml_missing": True}

    # lifecycle
    yaml_data = load_lifecycle_registry_yaml()
    if yaml_data:
        yaml_ids = set((yaml_data.get("items") or {}).keys())
        py_ids = set(LIFECYCLE_REGISTRY.keys())
        report["lifecycle"] = {
            "in_py_only": sorted(py_ids - yaml_ids),
            "in_yaml_only": sorted(yaml_ids - py_ids),
            "consistent": py_ids == yaml_ids,
        }
    else:
        report["lifecycle"] = {"yaml_missing": True}

    # spatial_layer
    yaml_data = load_spatial_layer_registry_yaml()
    if yaml_data:
        yaml_ids = set((yaml_data.get("items") or {}).keys())
        py_ids = set(SPATIAL_LAYER_REGISTRY.keys())
        report["spatial_layer"] = {
            "in_py_only": sorted(py_ids - yaml_ids),
            "in_yaml_only": sorted(yaml_ids - py_ids),
            "consistent": py_ids == yaml_ids,
        }
    else:
        report["spatial_layer"] = {"yaml_missing": True}

    return report


class ProjectTypeDetector:
    """
    功能层级 15 — 项目类型候选检测器。
    人话: 管"怎么从用户输入里算出一组候选"。它读取上面的注册表，
    做文本归一、关键词命中、否定词处理、强弱词计分、priority 加权、
    候选排序。它不是最终空间分类器。

    项目类型自动检测器 — 所有关键词逻辑从 PROJECT_TYPE_REGISTRY 读取。

    v7.200: 统一注册表驱动，消除重复逻辑
    v7.210: 支持扩展类型热重载（data/project_type_extensions.json）
    """

    # 类级别合并注册表（静态 + 扩展）
    _merged_registry: Optional[Dict[str, Any]] = None

    def __init__(self):
        # 功能 15.0 — 初始化检测器。
        # 人话: 合并核心类型和扩展类型，并提前算好关键词排他性权重。
        self.registry = self._get_registry()
        # Step 14: 预计算排他性权重（基于合并注册表）
        self._excl_weights = _build_exclusivity_weights(self.registry)
        logger.info("[v8.1] 项目类型检测器初始化，共 {} 种类型（含 {} 个扩展）".format(
            len(self.registry),
            len(self.registry) - len(PROJECT_TYPE_REGISTRY)
        ))

    @classmethod
    def _get_registry(cls) -> Dict[str, Any]:
        """
        功能 15.0.1 — 获取合并后的项目类型注册表。
        人话: 把内置 PROJECT_TYPE_REGISTRY 和后台审批扩展类型合成一张表。
        """
        if cls._merged_registry is None:
            cls._merged_registry = {**PROJECT_TYPE_REGISTRY, **_load_extension_registry()}
        return cls._merged_registry

    @classmethod
    def reload_extensions(cls) -> int:
        """
        功能 15.0.2 — 热重载扩展类型。
        人话: 后台审批新增类型后，不重启也能刷新 detector 的合并注册表。

        热重载扩展类型（管理员审批新类型后调用）。

        Returns:
            当前扩展类型数量
        """
        extensions = _load_extension_registry()
        cls._merged_registry = {**PROJECT_TYPE_REGISTRY, **extensions}
        logger.info(f"[TypeRegistry] 热重载完成，共 {len(cls._merged_registry)} 种类型，{len(extensions)} 个扩展")
        return len(extensions)

    @staticmethod
    def _get_specialty_tag(combined_text: str) -> Optional[str]:
        """
        功能 12.1 — 提取 specialty 辅助标签。
        人话: 从文本里抓火锅、loft、茶饮、牙科这类细碎信号，只作辅助证据。
        """
        for trigger, tag in SPECIALTY_TAG_MAP:
            if trigger in combined_text:
                return tag
        return None

    @staticmethod
    def _get_parent_type(type_id: str) -> Optional[str]:
        """
        功能 11.1 — 读取父桶类型。
        人话: 把具体 project_type 粗略归到住宅、办公、零售等旧父类。
        """
        return PARENT_TYPE_MAP.get(type_id)

    # =========================================================================
    # 内部核心: 结构化候选集生成
    # 功能层级 15.1 — project_type 候选集生成
    # 人话: 管"所有项目类型候选怎么被算出来"。detect() 和
    # detect_with_details() 都从这里取结果；这里不装配最终 classification_output。
    # detect() 与 detect_with_details() 都从这里取数据
    # =========================================================================
    def _build_candidate_set(
        self,
        user_input: str,
        confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        功能 15.1.1 — 生成 project_type 候选集。
        人话: 从用户文本里找项目类型关键词，算分、加权、排序，并输出候选列表。

        生成完整的 ClassificationCandidateSet (v1.8 内部协议)。

        Returns:
            {
                "input_fingerprint": str,
                "combined_text": str,
                "negated_spans": list,
                "project_type_candidates": [{type_id, score, weighted_score,
                                             confidence, primary_hits, secondary_hits,
                                             matched_keywords, negated_hits, priority,
                                             name, name_en}],
                "no_match_reason": str | None,
            }
        """
        # ── Step 6: 别名预处理 ─────────────────────────────────────────────
        try:
            from .type_alias_normalizer import normalize_input_with_trace
            normalization_trace = normalize_input_with_trace(user_input)
            preprocessed = normalization_trace["normalized_text"]
        except Exception:
            normalization_trace = {
                "schema_version": "type_alias_normalization_trace.v1",
                "original_text": user_input,
                "normalized_text": user_input,
                "changed": False,
                "fullwidth_converted": False,
                "replacement_count": 0,
                "replacements": [],
                "error": "normalization_failed",
            }
            preprocessed = user_input

        combined_text = preprocessed.lower()
        if confirmed_tasks:
            for task in confirmed_tasks:
                combined_text += " " + task.get("title", "").lower()
                combined_text += " " + task.get("description", "").lower()

        # 输入指纹 (供下游缓存)
        import hashlib
        input_fingerprint = hashlib.md5(combined_text.encode("utf-8")).hexdigest()[:16]

        # ── Step 13: 预计算否定区间 ───────────────────────────────────────────
        try:
            from .type_alias_normalizer import extract_negated_spans, is_negated
            negated_spans = extract_negated_spans(combined_text)
        except Exception:
            negated_spans = []
            is_negated = lambda kw, txt, spans: False  # noqa: E731

        candidates: List[Dict[str, Any]] = []

        for type_id, config in self.registry.items():
            if not config.get("keywords"):
                continue  # 兼容: 关键词为空的 type 跳过 (v1.9 已修复 hybrid_residential_commercial)

            def _hits_with_negation(keywords: List[str]) -> Tuple[int, float, List[str], List[str]]:
                """返回 (命中数, 加权分, 有效命中词列表, 被否定命中词列表)"""
                count = 0
                weighted = 0.0
                matched: List[str] = []
                negated_hits: List[str] = []
                for kw in keywords:
                    if kw not in combined_text:
                        continue
                    if negated_spans and is_negated(kw, combined_text, negated_spans):
                        negated_hits.append(kw)  # v1.8 改造: 记录而非静默
                        continue
                    w = self._excl_weights.get(kw, 1.0)
                    count += 1
                    weighted += w
                    matched.append(kw)
                return count, weighted, matched, negated_hits

            primary_count, primary_weighted, primary_matched, primary_negated = _hits_with_negation(
                config["keywords"]
            )
            secondary_count, secondary_weighted, secondary_matched, secondary_negated = _hits_with_negation(
                config.get("secondary_keywords", [])
            )

            # 低信息次级词只能补充已有空间对象证据，不能单独决定 project_type。
            # 例如"动线/示范/品牌/设计师/业主"是几乎所有空间都会出现的
            # 任务语境词；如果没有 primary keyword，它们应当交给后续
            # input_intent / founding_type / context_packet 处理，而不是抢空间分类。
            if primary_count == 0 and secondary_matched:
                low_info_hits = [
                    kw for kw in secondary_matched if kw in LOW_INFORMATION_SECONDARY_KEYWORDS
                ]
                if low_info_hits:
                    low_info_set = set(low_info_hits)
                    secondary_matched = [
                        kw for kw in secondary_matched if kw not in low_info_set
                    ]
                    secondary_count = len(secondary_matched)
                    secondary_weighted = sum(
                        self._excl_weights.get(kw, 1.0) for kw in secondary_matched
                    )

            min_sec = config.get("min_secondary_hits", 0)
            if primary_count == 0:
                if min_sec > 0 and secondary_count < min_sec:
                    continue
                elif min_sec == 0 and secondary_count == 0:
                    continue

            score = primary_weighted * 2 + secondary_weighted
            weighted_score = score * config["priority"]

            candidates.append({
                "type_id": type_id,
                "score": round(score, 3),
                "weighted_score": round(weighted_score, 3),
                "priority": config["priority"],
                "primary_hits": primary_count,
                "secondary_hits": secondary_count,
                "matched_keywords": {
                    "primary": primary_matched,
                    "secondary": secondary_matched,
                },
                "negated_hits": primary_negated + secondary_negated,
                "name": config["name"],
                "name_en": config.get("name_en", ""),
            })

        vertical_mixed_use_candidate = _build_vertical_mixed_use_candidate(combined_text)
        if vertical_mixed_use_candidate:
            candidates = [
                candidate
                for candidate in candidates
                if candidate["type_id"] != vertical_mixed_use_candidate["type_id"]
            ]
            candidates.append(vertical_mixed_use_candidate)

        _demote_enterprise_function_inside_residential_carrier(candidates, combined_text)

        # 主空间对象优先于主题/叙事/风格词。
        # 如果任一候选命中了 primary keyword，说明输入里已经有明确空间对象；
        # 仅靠 secondary keyword 命中的候选只能作为语义补充，不能抢主类型。
        if any(candidate.get("primary_hits", 0) > 0 for candidate in candidates):
            for candidate in candidates:
                if candidate.get("primary_hits", 0) == 0:
                    candidate["weighted_score"] = round(candidate["weighted_score"] * 0.45, 3)
                    candidate["object_anchor_penalty"] = "secondary_only_demoted"

        # 按 weighted_score 降序
        candidates.sort(key=lambda x: x["weighted_score"], reverse=True)

        # 计算候选自身的局部 confidence (v1.8 §9.1 三档语义)
        # 重做后的公式:
        #   base = min(0.85, 0.30 + score * 0.08)              # 绝对强度，上限收紧
        #   top1/top2 margin penalty: 接近时扣分
        #   negation penalty: 否定区间命中比例越高扣越多
        if candidates:
            top1 = candidates[0]
            top2 = candidates[1] if len(candidates) >= 2 else None

            for idx, cand in enumerate(candidates):
                base = min(0.85, 0.30 + cand["score"] * 0.08)

                # top2 接近度惩罚 (仅作用于 top1)
                margin_penalty = 0.0
                if idx == 0 and top2 is not None:
                    top1_w = max(top1["weighted_score"], 0.001)
                    margin = (top1["weighted_score"] - top2["weighted_score"]) / top1_w
                    # margin < 0.30 触发惩罚, < 0.10 重罚
                    if margin < 0.10:
                        margin_penalty = -0.20
                    elif margin < 0.30:
                        margin_penalty = -0.10

                # 否定命中惩罚
                total_hits = cand["primary_hits"] + cand["secondary_hits"]
                total_neg = len(cand["negated_hits"])
                neg_ratio = total_neg / max(total_hits + total_neg, 1)
                neg_penalty = -0.15 * neg_ratio if neg_ratio > 0.30 else 0.0

                # 排他性加成 (主关键词全是独占词 → 加成)
                excl_bonus = 0.0
                primary_words = cand["matched_keywords"]["primary"]
                if primary_words:
                    excl_avg = sum(self._excl_weights.get(w, 1.0) for w in primary_words) / len(primary_words)
                    if excl_avg >= 1.4:
                        excl_bonus = 0.05

                final_score = max(0.0, min(0.95, base + margin_penalty + neg_penalty + excl_bonus))

                # 三档 level (v1.8 §9.1)
                if final_score >= 0.80:
                    level = "high"
                elif final_score >= 0.60:
                    level = "medium"
                else:
                    level = "low"

                cand["confidence"] = round(final_score, 3)
                cand["confidence_level"] = level
                cand["debug_breakdown"] = {
                    "base": round(base, 3),
                    "margin_penalty": round(margin_penalty, 3),
                    "negation_penalty": round(neg_penalty, 3),
                    "exclusivity_bonus": round(excl_bonus, 3),
                }

        # no_match_reason (v1.8 改造: 替代隐式 None)
        no_match_reason: Optional[str] = None
        if not candidates:
            if not combined_text.strip():
                no_match_reason = "empty_input"
            else:
                no_match_reason = "insufficient_evidence"

        # ── v1.9 新增: boundary_keywords 命中检测 ────────────────────────────
        # 命中 boundary_keyword **不影响 candidates 的 scoring** (已经在上面算完),
        # 仅作为信号输出, 由下游 SpaceClassificationService 据此查 boundary_cases.yaml
        # 做二次判断 / 生成 ClarificationRequest
        boundary_keyword_hits: List[str] = []
        boundary_case_ids: List[str] = []
        try:
            boundary_index = _get_boundary_keyword_index()
            seen_case_ids: set = set()
            for kw, case_ids in boundary_index.items():
                if kw.lower() in combined_text:
                    boundary_keyword_hits.append(kw)
                    for cid in case_ids:
                        if cid not in seen_case_ids:
                            boundary_case_ids.append(cid)
                            seen_case_ids.add(cid)
        except Exception as exc:
            logger.debug(f"[BoundaryCases] 检测失败, 跳过 (不影响主流程): {exc}")

        return {
            "input_fingerprint": input_fingerprint,
            "combined_text": combined_text,
            "negated_spans": negated_spans,
            "normalization_trace": normalization_trace,
            "project_type_candidates": candidates,
            "no_match_reason": no_match_reason,
            # v1.9 新增: boundary 信号
            "boundary_keyword_hits": boundary_keyword_hits,
            "boundary_case_ids": boundary_case_ids,
        }

    def detect(
        self,
        user_input: str,
        confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Optional[str], float, str]:
        """
        功能 17.0 — 旧式三元组检测接口。
        人话: 给旧代码返回一个最简单的 (project_type, confidence, reason)。

        检测项目类型 (旧三元组接口，向后兼容)。

        Args:
            user_input: 用户原始输入（或预处理后的合并文本）
            confirmed_tasks: 确认的任务列表（可选）

        Returns:
            (project_type, confidence, reason)
            - project_type : 类型 ID；若完全无匹配，返回 None（触发通用框架）
            - confidence   : 0.0–1.0
            - reason       : 人类可读的匹配说明
        """
        cset = self._build_candidate_set(user_input, confirmed_tasks)
        candidates = cset["project_type_candidates"]

        if not candidates:
            reason = f"无关键词命中 (no_match_reason={cset['no_match_reason']})"
            logger.info(f"[v1.8] 项目类型未匹配 ({cset['no_match_reason']})，建议触发通用框架")
            return None, 0.0, reason

        top1 = candidates[0]
        confidence = top1["confidence"]
        primary_matched = top1["matched_keywords"]["primary"]
        secondary_matched = top1["matched_keywords"]["secondary"]
        matched_preview = (primary_matched + secondary_matched)[:4]
        reason = "匹配关键词: " + ", ".join(matched_preview)

        # top-2 融合提示 (保留旧字符串协议供回归兼容; 新代码请用 detect_with_details)
        if len(candidates) >= 2:
            top2 = candidates[1]
            t1w = max(top1["weighted_score"], 0.001)
            if top2["weighted_score"] / t1w >= 0.8:
                reason += f" | 次选: {top2['name']} ({top2['type_id']})"

        logger.info(
            f"[v1.8] 检测结果: {top1['name']} ({top1['type_id']}), "
            f"置信度: {confidence:.0%} ({top1['confidence_level']}), {reason}"
        )
        return top1["type_id"], confidence, reason

    # =========================================================================
    # FoundingType / SubdomainSignal / ScaleSignal 检测 (v1.8 新增)
    # 功能层级 15.2 — 多轴候选信号生成
    # 人话: 管"除了 project_type 之外的其他信号"。包括成立方式、子域、
    # 行业属性、空间尺度线索。它们只是候选信号，最终冻结由下游服务完成。
    # =========================================================================
    def _detect_founding_type_candidates(
        self, combined_text: str, negated_spans: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        功能 15.2.1 — 生成成立方式候选。
        人话: 判断项目是为了经营、自用、资产盘活、乡村振兴还是公共服务等。
        """
        try:
            from .type_alias_normalizer import is_negated
        except Exception:
            is_negated = lambda kw, txt, spans: False  # noqa: E731

        candidates: List[Dict[str, Any]] = []
        for ft_id, config in FOUNDING_TYPE_REGISTRY.items():
            primary_matched: List[str] = []
            secondary_matched: List[str] = []
            negated_hits: List[str] = []

            for kw in config.get("keywords", []):
                if kw not in combined_text:
                    continue
                if negated_spans and is_negated(kw, combined_text, negated_spans):
                    negated_hits.append(kw)
                    continue
                primary_matched.append(kw)

            for kw in config.get("secondary_keywords", []):
                if kw not in combined_text:
                    continue
                if negated_spans and is_negated(kw, combined_text, negated_spans):
                    negated_hits.append(kw)
                    continue
                secondary_matched.append(kw)

            if not primary_matched and not secondary_matched:
                continue

            score = len(primary_matched) * 2.0 + len(secondary_matched) * 1.0
            weighted_score = score * config["priority"]
            # founding_type 置信度公式 (比 project_type 更保守, 因为词集小、噪音大)
            base_conf = min(0.80, 0.25 + score * 0.10)

            candidates.append({
                "founding_type_id": ft_id,
                "score": round(score, 3),
                "weighted_score": round(weighted_score, 3),
                "confidence": round(base_conf, 3),
                "matched_keywords": {
                    "primary": primary_matched,
                    "secondary": secondary_matched,
                },
                "negated_hits": negated_hits,
                "name": config["name"],
                "status": config.get("status", "active_mvp"),
            })

        candidates.sort(key=lambda x: x["weighted_score"], reverse=True)
        return candidates

    def _detect_subdomain_signals(
        self,
        combined_text: str,
        project_type_candidates: List[Dict[str, Any]],
        specialty_tag: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        功能 15.2.2 — 生成子域候选信号。
        人话: 判断大类型下面有没有茶饮店、咖啡馆这类受控细分业态。

        生成 subdomain 信号数组 (v1.8 §6.1)。

        注意:
          - 仅引用 SUBDOMAIN_REGISTRY 中已注册条目
          - 禁止凭关键词凭空提议新 subdomain_id
          - specialty_tag 作为辅助证据加分, 不直接当 subdomain_id
        """
        signals: List[Dict[str, Any]] = []
        top_type_id = project_type_candidates[0]["type_id"] if project_type_candidates else None

        # specialty_tag → subdomain 的辅助映射 (仅对已注册子域)
        SPECIALTY_TO_SUBDOMAIN: Dict[str, str] = {
            "tea_bar": "tea_drink_store",
            "cafe": "coffee_shop",
        }

        for sub_id, config in SUBDOMAIN_REGISTRY.items():
            matched_kw: List[str] = []
            for kw in config.get("signal_keywords", []):
                if kw in combined_text:
                    matched_kw.append(kw)

            # specialty_tag 辅助加分
            specialty_match = False
            if specialty_tag and SPECIALTY_TO_SUBDOMAIN.get(specialty_tag) == sub_id:
                specialty_match = True

            if not matched_kw and not specialty_match:
                continue

            # 父类型一致性校验: 若顶级 project_type 与 parent_project_type_id 不符, 降低置信度
            parent_match = (
                top_type_id is None
                or top_type_id == config.get("parent_project_type_id")
            )

            base = 0.35 + len(matched_kw) * 0.15
            if specialty_match:
                base += 0.10
            if not parent_match:
                base -= 0.20  # 父类型不一致降权
            confidence = max(0.0, min(0.90, base))

            signals.append({
                "signal_id": sub_id,
                "suggested_subdomain_id": sub_id,
                "parent_project_type_id": config["parent_project_type_id"],
                "activation_pack_id": config["activation_pack_id"],
                "confidence": round(confidence, 3),
                "matched_keywords": matched_kw,
                "specialty_tag_assist": specialty_tag if specialty_match else None,
                "parent_type_match": parent_match,
                "status": config.get("status", "reserved"),
                "subdomain_registration_status": "registered",
            })

        signals.sort(key=lambda x: x["confidence"], reverse=True)
        return signals

    def _detect_industry_candidates(
        self,
        combined_text: str,
        negated_spans: List[Any],
        project_type_candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        功能 15.2.3 — 生成行业属性候选。
        人话: 判断空间服务哪个行业，例如法律、科技、汽车、眼镜视光；未命中不阻断主分类。
        """
        try:
            from .type_alias_normalizer import is_negated
        except Exception:
            is_negated = lambda kw, txt, spans: False  # noqa: E731

        top_project_type = (
            project_type_candidates[0]["type_id"] if project_type_candidates else None
        )
        candidates: List[Dict[str, Any]] = []

        for industry_id, config in INDUSTRY_DOMAIN_REGISTRY.items():
            primary_matched: List[str] = []
            secondary_matched: List[str] = []
            negated_hits: List[str] = []

            for kw in config.get("keywords", []):
                if kw not in combined_text:
                    continue
                if negated_spans and is_negated(kw, combined_text, negated_spans):
                    negated_hits.append(kw)
                    continue
                primary_matched.append(kw)

            for kw in config.get("secondary_keywords", []):
                if kw not in combined_text:
                    continue
                if negated_spans and is_negated(kw, combined_text, negated_spans):
                    negated_hits.append(kw)
                    continue
                secondary_matched.append(kw)

            if not primary_matched and not secondary_matched:
                continue

            base_score = len(primary_matched) * 2.0 + len(secondary_matched) * 1.0
            type_fit_bonus = 0.0
            if top_project_type and top_project_type in config.get("preferred_project_types", []):
                type_fit_bonus = 0.6

            score = base_score + type_fit_bonus
            weighted_score = score * float(config.get("priority", 6))
            confidence = min(0.90, 0.25 + score * 0.10)
            confidence_level = "high" if confidence >= 0.8 else ("medium" if confidence >= 0.6 else "low")

            candidates.append({
                "industry_id": industry_id,
                "name": config["name"],
                "score": round(score, 3),
                "weighted_score": round(weighted_score, 3),
                "confidence": round(confidence, 3),
                "confidence_level": confidence_level,
                "matched_keywords": {
                    "primary": primary_matched,
                    "secondary": secondary_matched,
                },
                "negated_hits": negated_hits,
                "preferred_project_types": config.get("preferred_project_types", []),
                "maturity_level": config.get("maturity_level", "L1_tagged"),
                "status": config.get("status", "active_light"),
            })

        candidates.sort(key=lambda x: x["weighted_score"], reverse=True)
        return candidates

    @staticmethod
    def _detect_scale_signals(combined_text: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        功能 15.2.4 — 生成尺度与生命周期线索。
        人话: 只判断室内/建筑/园区/街区以及装修/改造/活化/临时这些线索。

        生成 spatial_extent / lifecycle 候选线索 (v1.8 §7)。

        注意: detector 不合成最终 project_scale, 仅输出线索。
              SpaceClassificationService 负责笛卡尔积合成。
        """
        def _match(
            kw_map: Dict[str, List[str]],
            priority_map: Optional[Dict[str, int]] = None,
        ) -> List[Dict[str, Any]]:
            results = []
            for axis_id, kws in kw_map.items():
                matched = [kw for kw in kws if kw in combined_text]
                if not matched:
                    continue
                results.append({
                    "id": axis_id,
                    "matched_keywords": matched,
                    "hit_count": len(matched),
                })
            results.sort(
                key=lambda x: (
                    x["hit_count"],
                    (priority_map or {}).get(str(x["id"]), 0),
                ),
                reverse=True,
            )
            return results

        return {
            "spatial_extent_candidates": _match(SPATIAL_EXTENT_KEYWORDS),
            "lifecycle_candidates": _match(
                LIFECYCLE_KEYWORDS,
                {
                    "adaptive_reuse": 5,
                    "temporary": 4,
                    "newbuild": 3,
                    "renovation": 2,
                    "fitout": 1,
                },
            ),
        }

    def detect_with_details(
        self,
        user_input: str,
        confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        功能层级 16 — 结构化详细输出接口。
        功能 16.1 — 输出完整候选信号包。
        人话: 管"把所有候选信号打包给下游"。输出 project_type_candidates、
        founding_type_candidates、subdomain_signals、industry_candidates、
        scale_signals、boundary_case_ids、confidence、ambiguity、evidence。
        它仍然不是最终分类器，最终由 SpaceClassificationService 组装。

        检测项目类型 — 输出 v1.8 ClassificationCandidateSet。

        本方法是 SpaceClassificationService 的主消费入口。
        detector 只输出候选与证据，最终 classification_output 由
        SpaceClassificationService 装配 (v1.8 §2.2: 不新建并行 Classifier)。

        新协议字段 (v1.8):
          input_fingerprint        : 归一化文本指纹，供下游缓存
          project_type_candidates  : 多候选数组 (替代 secondary_type 字符串解析)
          founding_type_candidates : 成立方式候选 (v1.8 §4 第 0 段)
          subdomain_signals        : 子域信号 (v1.8 §6.1)
          scale_signals            : spatial_extent / lifecycle 线索 (v1.8 §7)
          confidence               : {score, level: high|medium|low, debug_breakdown}
          ambiguity                : {is_ambiguous, margin, competing_candidates}
          evidence                 : {negated_hits, unmatched_input_fragments}
          no_match_reason          : 无主匹配时的原因码

                新增字段 (v1.10):
                    industry_candidates      : 行业候选数组 (独立维度)
                    industry_profile         : 当前行业识别摘要与成熟度
                    needs_industry_clarification: 行业维度是否需要追问

        兼容字段 (v1.5 旧协议，保留以避免下游震荡):
          project_type / project_type_name / confidence (=confidence.score)
          reason / parent_type (deprecated_compat) / specialty_tag (aux)
          secondary_type / secondary_type_name (由结构化候选派生，不再 split reason)
          is_ambiguous / all_matches
        """
        cset = self._build_candidate_set(user_input, confirmed_tasks)
        candidates = cset["project_type_candidates"]
        combined_text = cset["combined_text"]
        negated_spans = cset["negated_spans"]

        # ── specialty_tag (aux signal, 不入主协议) ────────────────────────────
        specialty_tag = self._get_specialty_tag(combined_text)

        # ── v1.8 新增: founding_type / subdomain / scale 信号 ──────────────────
        founding_type_candidates = self._detect_founding_type_candidates(
            combined_text, negated_spans
        )
        subdomain_signals = self._detect_subdomain_signals(
            combined_text, candidates, specialty_tag
        )
        industry_candidates = self._detect_industry_candidates(
            combined_text, negated_spans, candidates
        )
        scale_signals = self._detect_scale_signals(combined_text)

        top_industry = industry_candidates[0] if industry_candidates else None
        industry_domain = top_industry["industry_id"] if top_industry else None
        industry_domain_name = top_industry["name"] if top_industry else None
        industry_confidence = top_industry["confidence"] if top_industry else 0.0
        industry_profile_status = top_industry["maturity_level"] if top_industry else "unspecified"
        needs_industry_clarification = (
            not top_industry or top_industry["confidence"] < 0.55
        )

        # ── 主候选与 ambiguity 结构化 ─────────────────────────────────────────
        top1 = candidates[0] if candidates else None
        top2 = candidates[1] if len(candidates) >= 2 else None

        # ambiguity: margin = (top1_w - top2_w) / top1_w
        is_ambiguous = False
        margin = 1.0
        competing_candidates: List[Dict[str, Any]] = []
        if top1 and top2:
            t1w = max(top1["weighted_score"], 0.001)
            margin = (top1["weighted_score"] - top2["weighted_score"]) / t1w
            if margin < 0.20:  # 第二名得分 ≥80% 第一名 → ambiguous
                is_ambiguous = True
                competing_candidates = [
                    {
                        "type_id": c["type_id"],
                        "name": c["name"],
                        "weighted_score": c["weighted_score"],
                        "confidence": c["confidence"],
                    }
                    for c in candidates[:3]
                ]

        # ── all_matches: 完整候选数组 (v1.8 改造: 不再固定空数组) ─────────────
        all_matches = [
            {
                "type_id": c["type_id"],
                "name": c["name"],
                "score": c["score"],
                "weighted_score": c["weighted_score"],
                "priority": c["priority"],
                "primary_hits": c["primary_hits"],
                "secondary_hits": c["secondary_hits"],
                "matched_keywords": c["matched_keywords"],
                "negated_hits": c["negated_hits"],
                "confidence": c["confidence"],
                "confidence_level": c["confidence_level"],
            }
            for c in candidates
        ]

        # ── 兼容字段 (v1.5 旧协议) ────────────────────────────────────────────
        project_type = top1["type_id"] if top1 else None
        project_type_name = top1["name"] if top1 else "未识别"
        confidence_score = top1["confidence"] if top1 else 0.0
        confidence_level = top1["confidence_level"] if top1 else "low"

        # reason 字符串保留 (但不再被下游 split 解析; 仅供日志/调试)
        if top1:
            matched_preview = (
                top1["matched_keywords"]["primary"] + top1["matched_keywords"]["secondary"]
            )[:4]
            reason = "匹配关键词: " + ", ".join(matched_preview)
            if top2 and is_ambiguous:
                reason += f" | 次选: {top2['name']} ({top2['type_id']})"
        else:
            reason = f"无关键词命中 (no_match_reason={cset['no_match_reason']})"

        # secondary_type 从结构化候选派生 (不再 split reason)
        secondary_type = top2["type_id"] if (top2 and is_ambiguous) else None
        secondary_type_name = top2["name"] if (top2 and is_ambiguous) else None

        # parent_type (deprecated_compat)
        parent_type = self._get_parent_type(project_type) if project_type else None

        # ── v1.9 新增: boundary 信号 + secondary_type_candidates ──────────────
        boundary_keyword_hits = cset.get("boundary_keyword_hits", [])
        boundary_case_ids = cset.get("boundary_case_ids", [])

        # secondary_type_candidates: 比 secondary_type 更结构化的次候选数组
        # 触发条件:
        #   (a) top2 候选与 top1 weighted_score margin < 30% (ambiguous 信号)
        #   (b) 命中 boundary_case_ids (即使分数差距大也提供 secondary)
        secondary_type_candidates: List[Dict[str, Any]] = []
        if candidates and len(candidates) >= 2:
            for cand in candidates[1:3]:  # 最多取 top2-top3
                cand_score = cand.get("confidence", 0.0)
                top1_score = top1["confidence"] if top1 else 0.0
                rel_score = cand_score / max(top1_score, 0.001)
                # 收录条件: 相对分数 >= 0.50 或 有 boundary case
                include = rel_score >= 0.50 or bool(boundary_case_ids)
                if include and cand_score >= 0.40:
                    secondary_type_candidates.append({
                        "type_id": cand["type_id"],
                        "name": cand["name"],
                        "confidence": cand_score,
                        "weighted_score": cand["weighted_score"],
                        "score_ratio_to_primary": round(rel_score, 3),
                        "matched_keywords": cand["matched_keywords"],
                        "trigger_source": (
                            "boundary_case" if boundary_case_ids else "score_proximity"
                        ),
                    })

        # needs_clarification: 主候选信号弱 + boundary 命中, 强烈建议澄清
        # 触发条件 (任一):
        #   (a) ambiguous + boundary_case_ids 非空
        #   (b) top1 confidence_level == "low" + boundary_case_ids 非空
        #   (c) top1 primary_hits == 0 (只命中次词) + secondary_type_candidates 非空
        needs_clarification = False
        if boundary_case_ids:
            if is_ambiguous or (top1 and top1.get("confidence_level") == "low"):
                needs_clarification = True
        if top1 and top1.get("primary_hits", 0) == 0 and secondary_type_candidates:
            needs_clarification = True

        result: Dict[str, Any] = {
            # ── v1.8 新协议 ─────────────────────────────────────────────────
            "schema_version": "candidate_set.v1.10",
            "input_fingerprint": cset["input_fingerprint"],
            "project_type_candidates": [
                {
                    "type_id": c["type_id"],
                    "name": c["name"],
                    "score": c["score"],
                    "weighted_score": c["weighted_score"],
                    "confidence": c["confidence"],
                    "confidence_level": c["confidence_level"],
                    "matched_keywords": c["matched_keywords"],
                    "priority": c["priority"],
                }
                for c in candidates[:5]  # top-5
            ],
            "founding_type_candidates": founding_type_candidates,
            "subdomain_signals": subdomain_signals,
            "industry_candidates": industry_candidates[:5],
            "industry_profile": {
                "industry_domain": industry_domain,
                "industry_name": industry_domain_name,
                "confidence": industry_confidence,
                "profile_status": industry_profile_status,
            },
            "needs_industry_clarification": needs_industry_clarification,
            "scale_signals": scale_signals,
            # 新协议: confidence_detail (dict 形态; v1.8 §9.1 三档)
            # 注: 保留兼容字段 confidence (浮点) 避免打穿下游
            #     (dimension_selector / space_classification_service 等)
            "confidence_detail": {
                "score": confidence_score,
                "level": confidence_level,
                "debug_breakdown": top1["debug_breakdown"] if top1 else None,
            },
            "ambiguity": {
                "is_ambiguous": is_ambiguous,
                "margin": round(margin, 3) if candidates else None,
                "competing_candidates": competing_candidates,
            },
            "evidence": {
                "negated_hits": top1["negated_hits"] if top1 else [],
                "specialty_tag_assist": specialty_tag,
                "normalization_trace": cset.get("normalization_trace") or {},
            },
            "normalization_trace": cset.get("normalization_trace") or {},
            "no_match_reason": cset["no_match_reason"],

            # ── v1.9 新增字段: boundary + secondary_type_candidates ──────────
            # boundary_keyword_hits: 命中的 boundary_keywords (供调试 / 审计)
            # boundary_case_ids: 命中的 boundary_cases.yaml 内 case_id
            #   (供 SpaceClassificationService 查 case 内 primary_preference_rules
            #    与 clarification_questions)
            # secondary_type_candidates: 结构化次候选数组 (比旧 secondary_type 单字符串更丰富)
            # needs_clarification: 强烈建议向用户发起 ClarificationRequest 的信号
            "boundary_keyword_hits": boundary_keyword_hits,
            "boundary_case_ids": boundary_case_ids,
            "secondary_type_candidates": secondary_type_candidates,
            "needs_clarification": needs_clarification,

            # ── 兼容字段 (v1.5 旧协议; 双跑期保留, 由 SpaceClassificationService
            #    切换到 confidence_detail 后回收) ─────────────────────────────
            "project_type": project_type,
            "project_type_name": project_type_name if project_type else "未识别",
            "confidence": confidence_score,  # 保持 float, 不能改 dict (下游硬依赖)
            "confidence_level": confidence_level,  # 新增辅助字段, 不破坏兼容
            "reason": reason,
            "parent_type": parent_type,  # deprecated_compat
            "specialty_tag": specialty_tag,  # aux signal
            "secondary_type": secondary_type,
            "secondary_type_name": secondary_type_name,
            "industry_domain": industry_domain,
            "industry_domain_name": industry_domain_name,
            "industry_confidence": industry_confidence,
            "industry_profile_status": industry_profile_status,
            "is_ambiguous": is_ambiguous,
            "all_matches": all_matches,
        }
        return result




# =============================================================================
# 便捷函数
# 功能层级 17 — 旧式便捷入口
# 人话: 管"给旧代码一个简单函数直接拿 project_type / confidence"。新主流程
# 应优先使用 ProjectTypeDetector.detect_with_details()，因为它包含多轴候选信号。
# =============================================================================

def detect_project_type(
    user_input: str,
    confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
    default: Optional[str] = None,
) -> Optional[str]:
    """
    功能 17.1 — 旧式便捷 project_type 入口。
    人话: 只想拿一个 project_type 时用；新主流程不建议只用这个。

    便捷函数：检测项目类型，无匹配时返回 default。

    v1.8 改造:
      默认值由 "personal_residential" 改为 None。
      旧默认值会将未知项目误导到住宅链路 (v1.8 §19 验收用例风险)。
      调用方应改为接收 None 后:
        - 由 SpaceClassificationService 决定 needs_clarification
        - 或主动走 general fallback

    Args:
        user_input: 用户原始输入
        confirmed_tasks: 确认的任务列表（可选）
        default: 无匹配时的默认类型 ID; 默认 None (v1.8 推荐)。
                 仅在调用方明确知道自己语境下"住宅兜底"安全时才显式传入。

    Returns:
        项目类型 ID 或 None
    """
    detector = ProjectTypeDetector()
    project_type, _, _ = detector.detect(user_input, confirmed_tasks)
    return project_type if project_type is not None else default


def detect_project_type_with_confidence(
    user_input: str,
    confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Optional[str], float]:
    """
    功能 17.2 — 旧式便捷 project_type + confidence 入口。
    人话: 给旧代码快速拿类型和置信度，不包含边界、行业、子域等新信号。

    便捷函数：检测项目类型（带置信度）。

    Returns:
        (项目类型ID或None, 置信度)
    """
    detector = ProjectTypeDetector()
    project_type, confidence, _ = detector.detect(user_input, confirmed_tasks)
    return project_type, confidence

