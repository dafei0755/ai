"""
数据处理工具集

提供数据清洗、标准化、去重等工具函数
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Set


class DataCleaner:
    """数据清洗工具"""

    @staticmethod
    def clean_text(text: str | None) -> str | None:
        """
        清洗文本内容

        - 移除HTML标签
        - 规范化空白字符
        - 移除控制字符
        """
        if not text:
            return None

        # 移除HTML标签
        text = re.sub(r"<[^>]+>", "", text)

        # 规范化空白字符
        text = re.sub(r"\s+", " ", text)

        # 移除控制字符
        text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)

        # 去除首尾空格
        text = text.strip()

        return text if text else None

    @staticmethod
    def normalize_url(url: str) -> str:
        """规范化URL"""
        # 统一协议为https
        url = url.replace("http://", "https://")

        # 移除尾部斜杠
        url = url.rstrip("/")

        # 移除查询参数和锚点
        url = re.sub(r"[?#].*$", "", url)

        return url

    @staticmethod
    def extract_year(text: str) -> int | None:
        """从文本中提取年份"""
        # 匹配4位数字年份（1900-2099）
        matches = re.findall(r"\b(19\d{2}|20\d{2})\b", text)
        if matches:
            years = [int(y) for y in matches]
            # 返回最近的年份
            current_year = datetime.now().year
            valid_years = [y for y in years if 1990 <= y <= current_year + 5]
            return max(valid_years) if valid_years else None
        return None

    @staticmethod
    def extract_area(text: str) -> float | None:
        """
        从文本中提取面积（平方米）

        支持格式：
        - 1000 m²
        - 1,000 sqm
        - 1000 square meters
        """
        # 移除逗号
        text = text.replace(",", "")

        patterns = [
            r"(\d+(?:\.\d+)?)\s*(?:m²|m2|sqm|square\s*meters?)",
            r"(\d+(?:\.\d+)?)\s*(?:平方米|㎡)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except Exception:
                    continue

        return None

    @staticmethod
    def deduplicate_images(images: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """图片去重（基于URL）"""
        seen_urls: Set[str] = set()
        unique_images = []

        for img in images:
            url = img.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_images.append(img)

        return unique_images

    @staticmethod
    def standardize_location(location: Dict[str, Any] | None) -> Dict[str, Any] | None:
        """标准化位置信息"""
        if not location:
            return None

        standardized = {}

        # 标准化国家名称
        country = location.get("country", "").strip()
        if country:
            # TODO: 添加国家名称映射表
            standardized["country"] = country

        # 标准化城市名称
        city = location.get("city", "").strip()
        if city:
            standardized["city"] = city

        # 保留坐标
        if "lat" in location and "lng" in location:
            try:
                standardized["lat"] = float(location["lat"])
                standardized["lng"] = float(location["lng"])
            except Exception:
                pass

        return standardized if standardized else None


class DataValidator:
    """数据验证工具"""

    @staticmethod
    def validate_project(data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        验证项目数据完整性

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        # 必需字段检查
        required_fields = ["source", "source_id", "url", "title"]
        for field in required_fields:
            if not data.get(field):
                errors.append(f"缺少必需字段: {field}")

        # URL格式检查
        url = data.get("url", "")
        if url and not url.startswith("http"):
            errors.append(f"无效的URL: {url}")

        # 年份范围检查
        year = data.get("year")
        if year:
            current_year = datetime.now().year
            if not (1900 <= year <= current_year + 5):
                errors.append(f"无效的年份: {year}")

        # 面积范围检查
        area = data.get(" area_sqm")
        if area:
            if not (1 <= area <= 1000000):  # 1平米 - 100万平米
                errors.append(f"无效的面积: {area}")

        # 描述长度检查
        desc = data.get("description", "")
        if desc and len(desc) > 50000:
            errors.append(f"描述过长: {len(desc)}字符")

        return (len(errors) == 0, errors)

    @staticmethod
    def calculate_completeness(data: Dict[str, Any]) -> float:
        """
        计算数据完整度（0-1）

        评估维度：
        - 基础信息（40%）：title, description, url
        - 元数据（30%）：architects, location, year, area
        - 丰富内容（30%）：images, tags, categories
        """
        score = 0.0

        # 基础信息（40%）
        if data.get("title"):
            score += 0.15
        if data.get("description") and len(data.get("description", "")) > 100:
            score += 0.20
        if data.get("url"):
            score += 0.05

        # 元数据（30%）
        if data.get("architects"):
            score += 0.10
        if data.get("location"):
            score += 0.08
        if data.get("year"):
            score += 0.06
        if data.get("area_sqm"):
            score += 0.06

        # 丰富内容（30%）
        images = data.get("images", [])
        if images and len(images) >= 5:
            score += 0.15
        elif images:
            score += 0.10

        tags = data.get("tags", [])
        if tags and len(tags) >= 5:
            score += 0.10
        elif tags:
            score += 0.05

        categories = data.get("sub_categories", [])
        if categories:
            score += 0.05

        return min(score, 1.0)


class AutoTagger:
    """自动标注系统"""

    # 关键词映射
    STYLE_KEYWORDS = {
        "modern": ["现代", "contemporary", "minimalist", "简约"],
        "traditional": ["传统", "classical", "古典", "heritage"],
        "industrial": ["工业", "loft", "厂房改造"],
        "parametric": ["参数化", "computational", "算法"],
        "sustainable": ["可持续", "green", "eco", "生态"],
        "brutalist": ["粗野主义", "brutalism", "混凝土"],
    }

    MATERIAL_KEYWORDS = {
        "concrete": ["混凝土", "concrete", "清水混凝土"],
        "wood": ["木材", "timber", "木质", "木结构"],
        "steel": ["钢", "steel", "金属", "metal"],
        "glass": ["玻璃", "glass", "透明"],
        "brick": ["砖", "brick", "砌体"],
        "stone": ["石材", "stone", "大理石", "marble"],
    }

    @classmethod
    def extract_tags(cls, text: str, existing_tags: List[str] = None) -> List[str]:
        """
        从文本中提取标签

        Args:
            text: 项目描述文本
            existing_tags: 已有标签（不重复添加）

        Returns:
            新标签列表
        """
        if not text:
            return []

        text_lower = text.lower()
        new_tags = []
        existing_set = set(existing_tags or [])

        # 提取风格标签
        for tag, keywords in cls.STYLE_KEYWORDS.items():
            if tag not in existing_set:
                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        new_tags.append(tag)
                        break

        # 提取材料标签
        for tag, keywords in cls.MATERIAL_KEYWORDS.items():
            if tag not in existing_set:
                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        new_tags.append(tag)
                        break

        return new_tags

    @classmethod
    def auto_categorize(cls, title: str, description: str) -> str | None:
        """
        自动分类项目类型

        Returns:
            主分类名称
        """
        text = f"{title} {description}".lower()

        category_keywords = {
            "residential": ["住宅", "house", "apartment", "villa", "residence"],
            "commercial": ["商业", "shopping", "retail", "store", "mall"],
            "cultural": ["文化", "museum", "library", "gallery", "theater"],
            "educational": ["教育", "school", "university", "campus", "kindergarten"],
            "office": ["办公", "office", "headquarters", "workplace"],
            "hospitality": ["酒店", "hotel", "resort", "restaurant", "cafe"],
            "healthcare": ["医疗", "hospital", "clinic", "healthcare"],
            "sports": ["体育", "stadium", "gym", "sports center"],
        }

        # 计算每个分类的匹配分数
        scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[category] = score

        # 返回得分最高的分类
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]

        return None


__all__ = [
    "DataCleaner",
    "DataValidator",
    "AutoTagger",
]
