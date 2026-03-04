"""
项目类型别名标准化器 (Type Alias Normalizer)
v1.0

功能：
1. 将用户输入中的别名/缩写/行业俚语规范化，提升 detect_project_type() 命中率
2. 维护 NORMALIZATION_MAP：(原始词 → 规范写法) 的替换规则
3. 提供 normalize_input() 便捷函数，供检测器预处理阶段调用
4. 支持从数据库学习到的新别名（运行时动态追加）

接入方式：
    from intelligent_project_analyzer.services.type_alias_normalizer import normalize_input
    cleaned = normalize_input(user_input)          # 预处理
    project_type, conf, reason = detector.detect(cleaned)

版本历史：
    v1.0  2026-02-25  首次创建（Step 6 of 智能化升级计划）
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from loguru import logger

# =============================================================================
# 静态规范化词典
# 格式: "用户可能输入的别名/缩写" → "对应的标准关键词（PROJECT_TYPE_REGISTRY 中的词）"
#
# 分区说明：
#   §A  住宅类别名
#   §B  商业餐饮类别名
#   §C  酒店/民宿类别名
#   §D  教育/亲子类别名
#   §E  休闲娱乐类别名
#   §F  办公/新兴媒体类别名
#   §G  美容/汽车/快闪类别名
#   §H  医疗/康养类别名
#   §I  文化/体育/展览类别名
#   §J  乡建/公共类别名
#   §K  误写/繁简/全半角
# =============================================================================

NORMALIZATION_MAP: Dict[str, str] = {
    # ── §A 住宅 ──────────────────────────────────────────────────────────────
    "公寓设计": "住宅",  # → personal_residential
    "家装": "住宅",
    "家庭改造": "住宅",
    "精装房": "住宅",
    "毛坯改造": "旧房改造",
    "老宅": "老房改造",
    "旧房": "老房改造",  # → residential_renovation
    "二手房": "老房改造",
    "改善型住宅": "改善住宅",
    "改善型": "改善住宅",
    # ── §B 餐饮 ──────────────────────────────────────────────────────────────
    "饭店设计": "餐厅",  # → commercial_dining
    "饭馆": "餐厅",
    "饭庄": "餐厅",
    "酒楼": "餐厅",
    "中式餐厅": "餐厅",
    "西式餐厅": "餐厅",
    "网红餐厅": "餐厅",
    "旋转寿司": "餐厅",
    "拉面馆": "餐厅",
    "甜品店": "咖啡馆",
    "蛋糕店": "咖啡馆",
    "brunch": "咖啡馆",
    "Brunch": "咖啡馆",
    "自助餐厅": "自助餐",  # → commercial_dining secondary
    "buffet": "自助餐",
    "Buffet": "自助餐",
    # ── §C 酒店/民宿 ─────────────────────────────────────────────────────────
    "精品酒店": "精品",  # → commercial_hospitality
    "B&B": "民宿",
    "b&b": "民宿",
    "bed and breakfast": "民宿",
    "Bed and Breakfast": "民宿",
    "airbnb房": "民宿",
    "Airbnb": "民宿",
    "度假屋": "民宿",
    "山居": "度假酒店",
    "海景房": "度假酒店",
    "康养酒店": "康养",  # → commercial_hospitality + healthcare_wellness
    "温浴中心": "泡汤",
    "泡汤馆": "泡汤",
    "汤泉": "泡汤",
    "温泉设计": "温泉",
    # ── §D 教育/亲子 ─────────────────────────────────────────────────────────
    "幼儿园": "亲子乐园",  # → children_family
    "托班": "早教",
    "托育所": "早教",
    "育儿中心": "早教",
    "儿童馆": "亲子乐园",
    "儿童主题": "亲子乐园",
    "乐高": "亲子乐园",
    "儿童体验": "亲子乐园",
    "艺术教育": "培训",  # → educational_facility
    "培训学校": "培训",
    "辅导班": "培训",
    "考研机构": "培训",
    "职业培训": "培训",
    "图书馆设计": "图书馆",  # → public_cultural
    # ── §E 休闲娱乐 ──────────────────────────────────────────────────────────
    "水疗": "水会",  # → leisure_entertainment
    "SPA中心": "spa",
    "会所设计": "会所",
    "洗浴中心": "洗浴",
    "澡堂": "洗浴",
    "沐浴中心": "洗浴",
    "棋牌室设计": "棋牌",
    "麻将馆": "棋牌",
    "电玩城": "游戏厅",
    "游艺厅": "游戏厅",
    "桌游": "游戏厅",
    "密室设计": "密室",
    "沉浸式体验": "密室",
    # ── §F 办公/新兴媒体 ─────────────────────────────────────────────────────
    "写字楼改造": "办公",  # → commercial_office
    "联合办公": "共享办公",
    "工位": "共享办公",
    "众创": "孵化器",
    "创业空间": "孵化器",
    "录播间": "直播间",  # → digital_media_studio
    "直播工作室": "直播间",
    "网红拍摄": "直播间",
    "短视频": "直播间",
    "pod cast": "直播间",
    "podcast": "直播间",
    "Podcast": "直播间",
    "音频室": "录音棚",  # → special_function
    "收音室": "录音棚",
    # ── §G 美容/汽车/快闪 ────────────────────────────────────────────────────
    "发廊": "美发",  # → beauty_personal_care
    "理发店": "美发",
    "修甲": "美甲",
    "睫毛": "美甲",
    "半永久": "美甲",
    "纹绣": "美甲",
    "微整形": "医美",  # → healthcare_wellness
    "皮肤管理": "医美",
    "轻医美": "医美",
    "汽车4S": "4s店",  # → automotive_showroom
    "4S店": "4s店",
    "汽车展示": "汽车展厅",
    "新能源车展": "汽车展厅",
    "快闪店": "快闪",  # → popup_temporary
    "pop-up store": "快闪",
    "pop up": "快闪",
    "Pop-Up": "快闪",
    # ── §H 医疗/康养 ─────────────────────────────────────────────────────────
    "养老室": "养老",  # → healthcare_wellness
    "护理院": "养老",
    "老年公寓": "养老",
    "银发": "适老化",
    "老龄化": "适老化",
    "中医诊所": "中医馆",
    "中药房": "中医馆",
    "口腔诊所": "牙科",
    "牙科诊所": "牙科",
    "牙医诊室": "牙科",
    # ── §I 文化/体育 ─────────────────────────────────────────────────────────
    "博物馆设计": "博物馆",  # → public_cultural
    "多功能厅": "博物馆",
    "剧场设计": "剧场",
    "礼堂设计": "礼堂",
    "艺术展": "美术馆",
    "展示空间": "展览",  # → commercial_retail / public_cultural
    "品牌展厅": "品牌展厅",  # → automotive_showroom
    "健身设计": "健身房",  # → sports_entertainment_arts
    # ── §J 乡建/公共 ─────────────────────────────────────────────────────────
    "农家乐": "乡村民宿",  # → rural_construction
    "乡愁": "乡村振兴",
    "古村": "乡村改造",
    "古民居": "乡村改造",
    "集体用地": "乡村建设",
    "社区中心设计": "社区中心",  # → community_public
    "邻里中心": "社区中心",
    "长者食堂设计": "长者食堂",
    # ── §K 误写/繁简/全半角 ──────────────────────────────────────────────────
    "設計": "设计",
    "裝修": "装修",
    "餐廳": "餐厅",
    "辦公室": "办公室",
    "辦公": "办公",
    "醫院": "医院",
    "醫療": "医疗",
    "住宅設計": "住宅",
    "kTV": "ktv",
    "Ktv": "ktv",
    "KTV": "ktv",
    "K歌": "ktv",
    "ok厅": "ktv",
    "量贩KTV": "ktv",
}

# =============================================================================
# 运行时动态别名（由 alias_learning_service 学习后追加，重启前有效）
# =============================================================================
_DYNAMIC_ALIASES: Dict[str, str] = {}


def add_dynamic_alias(alias: str, canonical: str) -> None:
    """运行时追加别名（由 alias_learning_service 调用）"""
    _DYNAMIC_ALIASES[alias.strip()] = canonical.strip()
    logger.debug(f"[AliasNorm] 动态别名已注册: {alias!r} → {canonical!r}")


def get_all_aliases() -> Dict[str, str]:
    """返回静态 + 动态合并后的全部别名映射（用于管理员查看）"""
    return {**NORMALIZATION_MAP, **_DYNAMIC_ALIASES}


# =============================================================================
# 否定词规则
# 用于 negation_handling（Steps 13）：检测否定上下文，避免误命中
# =============================================================================

NEGATION_PATTERNS: List[str] = [
    r"不(要|做|是|想|需要|改|建|含|包括|属于)",
    r"非(?!常|凡|常的)",  # "非常" 不是否定
    r"无需",
    r"排除",
    r"避免",
    r"没有",
    r"不是",
]

# 编译后的否定正则（供 extract_negated_spans() 使用）
_NEGATION_RE = re.compile("|".join(NEGATION_PATTERNS), re.IGNORECASE)

# 否定词影响范围（字符数）—— 否定词后 N 个字符内的关键词被视为否定对象
NEGATION_REACH = 8


def extract_negated_spans(text: str) -> List[Tuple[int, int]]:
    """
    返回文本中属于"否定语境"的字符区间列表 [(start, end), ...]。

    用法示例：
        spans = extract_negated_spans("我不要做KTV，想要做咖啡馆")
        # spans = [(3, 11)]   →  "做KTV，想要做" 区间被排除
    """
    spans: List[Tuple[int, int]] = []
    for m in _NEGATION_RE.finditer(text):
        start = m.end()  # 否定词结束位置
        end = min(len(text), start + NEGATION_REACH)
        spans.append((start, end))
    return spans


def is_negated(keyword: str, text: str, negated_spans: List[Tuple[int, int]] | None = None) -> bool:
    """
    判断 keyword 在 text 中是否位于否定语境内。

    Args:
        keyword: 要检查的关键词
        text: 完整文本（已 lower()）
        negated_spans: 预计算的否定区间列表，None 则自动计算

    Returns:
        True = 该关键词处于否定语境，不应计入命中
    """
    if negated_spans is None:
        negated_spans = extract_negated_spans(text)
    if not negated_spans:
        return False

    pos = text.find(keyword)
    if pos < 0:
        return False

    kw_end = pos + len(keyword)
    for span_start, span_end in negated_spans:
        # 关键词与否定区间有重叠
        if pos < span_end and kw_end > span_start:
            return True
    return False


# =============================================================================
# 主函数
# =============================================================================


def normalize_input(text: str) -> str:
    """
    标准化用户输入：
    1. 替换已知别名/俚语 → 规范写法
    2. 繁简转换（通过词典映射，不依赖 opencc）
    3. 全角→半角数字/字母

    Args:
        text: 用户原始输入（不做 lower()，保留大小写供下游处理）

    Returns:
        标准化后的文本（别名已替换，不修改原词序）
    """
    merged_map = {**NORMALIZATION_MAP, **_DYNAMIC_ALIASES}

    # 按别名长度降序排列，优先替换更长的匹配（避免子串替换冲突）
    sorted_aliases = sorted(merged_map.items(), key=lambda x: len(x[0]), reverse=True)

    result = text
    for alias, canonical in sorted_aliases:
        if alias in result:
            result = result.replace(alias, canonical)

    # 全角→半角
    result = _fullwidth_to_halfwidth(result)

    if result != text:
        logger.debug(f"[AliasNorm] 别名替换: {text!r} → {result!r}")

    return result


def _fullwidth_to_halfwidth(text: str) -> str:
    """全角 ASCII 字符转半角（数字、字母、常用符号）"""
    result = []
    for ch in text:
        code = ord(ch)
        if 0xFF01 <= code <= 0xFF5E:
            result.append(chr(code - 0xFEE0))
        elif ch == "\u3000":  # 全角空格 → 普通空格
            result.append(" ")
        else:
            result.append(ch)
    return "".join(result)
