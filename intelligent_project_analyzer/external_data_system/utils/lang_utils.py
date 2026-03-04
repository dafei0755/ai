"""
语言检测与双语文本处理工具

用于爬虫的语言识别、中英文段落分离等功能
"""

import re
from typing import Dict


def detect_lang(text: str) -> str:
    """检测文本主要语言

    Returns:
        'zh'       - 以中文为主（中文字符占比 > 30%）
        'en'       - 以英文为主
        'mixed'    - 中英混合（双语段落）
    """
    if not text or not text.strip():
        return "en"

    chinese_chars = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", text))
    # 只算有意义的英文单词（排除数字/符号）
    english_words = len(re.findall(r"[a-zA-Z]{2,}", text))
    total = len(text.strip())
    if total == 0:
        return "en"

    zh_ratio = chinese_chars / total

    if zh_ratio > 0.3:
        return "zh"
    elif chinese_chars > 5 and english_words > 5:
        return "mixed"
    else:
        return "en"


def is_chinese_dominant(text: str, threshold: float = 0.15) -> bool:
    """判断文本是否以中文为主

    Args:
        threshold: 中文字符占比阈值（默认0.15，即段落中超过15%是汉字则认为是中文段落）
    """
    if not text:
        return False
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", text))
    total = len(text.strip())
    return total > 0 and (chinese_chars / total) >= threshold


def split_bilingual_paragraphs(text: str) -> Dict[str, str]:
    """拆分双语文本为中文段落和英文段落

    gooood 等网站的正文通常为中英双语交替段落模式：
      - 中文段落：描述设计概念（中字比例高）
      - 英文段落：同等内容的英文版本

    Args:
        text: 合并的原始段落文本（用 两空行 分隔段落）

    Returns:
        {
            'zh': '拼合的中文段落',
            'en': '拼合的英文段落',
        }
    """
    if not text:
        return {"zh": "", "en": ""}

    zh_parts: list[str] = []
    en_parts: list[str] = []

    for para in re.split(r"\n{2,}", text):
        para = para.strip()
        if not para:
            continue
        if is_chinese_dominant(para):
            zh_parts.append(para)
        else:
            en_parts.append(para)

    return {
        "zh": "\n\n".join(zh_parts),
        "en": "\n\n".join(en_parts),
    }


def split_bilingual_title(title: str) -> Dict[str, str]:
    """拆分双语标题

    gooood 标题常见格式：
      "中文标题 / English Title, City / Firm Name"
      "中文标题 / English Title"
      或纯中文。

    策略：
      - 按 " / " 分割每个片段
      - 片段含汉字 → title_zh 组成部分
      - 片段无汉字 → title_en 组成部分

    Returns:
        {'zh': '...', 'en': '...'}
    """
    if not title:
        return {"zh": "", "en": ""}

    parts = [p.strip() for p in re.split(r"\s*/\s*", title) if p.strip()]

    if len(parts) == 1:
        # 无 "/" 分隔符：按整体语言判断
        if re.search(r"[\u4e00-\u9fff]", parts[0]):
            return {"zh": parts[0], "en": ""}
        return {"zh": "", "en": parts[0]}

    zh_parts = []
    en_parts = []
    for part in parts:
        # 只要片段含有任意汉字，即归为中文部分
        if re.search(r"[\u4e00-\u9fff\u3400-\u4dbf]", part):
            zh_parts.append(part)
        else:
            en_parts.append(part)

    return {
        "zh": " / ".join(zh_parts),
        "en": " / ".join(en_parts),
    }
