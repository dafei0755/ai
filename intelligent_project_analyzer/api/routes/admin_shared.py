"""共享工具函数与缓存 — admin路由共用"""

import re
from typing import List, Set

from cachetools import TTLCache
from loguru import logger

# API响应缓存（5秒TTL，避免频繁计算）
metrics_cache = TTLCache(maxsize=10, ttl=5)

# 中文停用词列表（扩展版）
CHINESE_STOPWORDS: Set[str] = {
    # 代词
    "的",
    "了",
    "是",
    "在",
    "我",
    "有",
    "和",
    "就",
    "不",
    "人",
    "都",
    "一",
    "一个",
    "上",
    "也",
    "很",
    "到",
    "说",
    "要",
    "去",
    "你",
    "会",
    "着",
    "没有",
    "看",
    "好",
    "自己",
    "这",
    "那",
    "他",
    "她",
    "它",
    "我们",
    "你们",
    "他们",
    "她们",
    "它们",
    "咱们",
    "自己的",
    "其他",
    "另外",
    # 介词/连词
    "为",
    "以",
    "从",
    "对",
    "与",
    "及",
    "等",
    "或",
    "及其",
    "以及",
    "而且",
    "并且",
    "但是",
    "然后",
    "因为",
    "所以",
    "如果",
    "虽然",
    "那么",
    "因此",
    "由于",
    "关于",
    "按照",
    "根据",
    "基于",
    "通过",
    "经过",
    "为了",
    "除了",
    # 助词/语气词
    "啊",
    "呀",
    "吗",
    "呢",
    "吧",
    "哦",
    "哈",
    "嗯",
    "哎",
    "唉",
    "啦",
    "嘛",
    # 量词
    "个",
    "只",
    "件",
    "条",
    "座",
    "栋",
    "套",
    "间",
    "层",
    "张",
    "块",
    "片",
    "辆",
    "台",
    "把",
    "支",
    # 时间词
    "年",
    "月",
    "日",
    "时",
    "分",
    "秒",
    "天",
    "周",
    "季",
    "度",
    # 数字
    "二",
    "三",
    "四",
    "五",
    "六",
    "七",
    "八",
    "九",
    "十",
    "百",
    "千",
    "万",
    "亿",
    # 动词（常见无意义）
    "是的",
    "可以",
    "需要",
    "进行",
    "实现",
    "完成",
    "达到",
    "得到",
    "出来",
    "起来",
    "过来",
    "下去",
    "上去",
    "看好",
    "包含",
    "拥有",
    # 常见无意义短语
    "他唯一的",
    "要求是",
    "让建筑和",
    "建造一座",
    "小型的私",
    "移位匿名",
    "此直面自",
    "已的内心",
    "和宇宙",
    "某于",
    "对于别墅",
    # 设计项目常见停用词
    "设计一个",
    "我想",
    "我需要",
    "希望能",
    "最好是",
    "应该是",
    "比如说",
    "例如",
    "大概",
    "希望",
    "注重",
    # 常见动词（设计相关但过于宽泛）
    "设计",
    "装修",
    "建造",
    "建筑",
    "打造",
    "制作",
    "要求",
    # 度量相关
    "平米",
    "面积",
    "预算",
    # 位置词
    "里面",
    "外面",
    "上面",
    "下面",
    "前面",
    "后面",
    "左边",
    "右边",
    "中间",
    "旁边",
}


def extract_meaningful_keywords(text: str, min_word_len: int = 2, max_word_len: int = 6) -> List[str]:
    """
    从文本中提取有意义的关键词

    参数:
        text: 输入文本
        min_word_len: 最小词长（默认2）
        max_word_len: 最大词长（默认6）

    返回:
        关键词列表
    """
    if not text or not text.strip():
        return []

    keywords = []

    # 尝试使用 jieba 分词
    try:
        import jieba

        # 分词并过滤
        words = jieba.cut(text, cut_all=False)
        for word in words:
            word = word.strip()
            # 过滤条件：
            # 1. 长度符合要求
            # 2. 不在停用词中
            # 3. 包含中文字符
            # 4. 不是纯数字或标点
            if (
                min_word_len <= len(word) <= max_word_len
                and word not in CHINESE_STOPWORDS
                and re.search(r"[\u4e00-\u9fff]", word)  # 包含中文
                and not re.match(r"^[0-9\W]+$", word)  # 不是纯数字或标点
            ):
                keywords.append(word)

    except ImportError:
        # 如果jieba不可用，使用简单规则提取
        logger.warning("jieba未安装，使用简单分词规则")

        # 提取中文词汇（2-6字）
        words = re.findall(r"[\u4e00-\u9fff]{2,6}", text)
        for word in words:
            if word not in CHINESE_STOPWORDS and len(word) >= min_word_len:
                keywords.append(word)

    return keywords
