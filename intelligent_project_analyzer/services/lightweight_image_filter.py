"""
轻量图片智能过滤器 v7.172

多维度过滤策略，不依赖 Vision API：
1. 尺寸过滤 - 基于 width/height 排除小图
2. URL 特征过滤 - 正则匹配低质量模式（缩略图、图标、广告等）
3. 域名质量评分 - 基于设计类网站白名单分级
4. 标题关键词相关性 - 简单匹配判断与搜索query的相关性

使用方法：
    from intelligent_project_analyzer.services.lightweight_image_filter import ImageFilterService

    filter_service = ImageFilterService()
    filtered_images = filter_service.filter_images(
        images=raw_images,
        query="日式茶室设计",
        max_results=8
    )

作者: AI Assistant
日期: 2026-01-09
"""

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

from loguru import logger


@dataclass
class ImageQualityScore:
    """图片质量评分结果"""

    total_score: float  # 综合分数 (0-100)
    dimension_score: float  # 尺寸分数
    url_quality_score: float  # URL质量分数
    domain_score: float  # 域名分数
    relevance_score: float  # 相关性分数
    should_keep: bool  # 是否保留
    reject_reason: str | None = None  # 拒绝原因


class ImageFilterService:
    """
    轻量图片过滤服务

    零API成本的智能过滤，通过多维度评分筛选高质量相关图片
    """

    # ====== 默认配置 ======
    DEFAULT_MIN_WIDTH = 400
    DEFAULT_MIN_HEIGHT = 300
    DEFAULT_IDEAL_WIDTH = 800
    DEFAULT_IDEAL_HEIGHT = 600
    DEFAULT_PASS_THRESHOLD = 45

    # ====== 域名质量分级（设计类网站优先） ======
    DOMAIN_TIERS = {
        # Tier 1: 权威设计媒体 (100分)
        "tier_1": {
            "domains": [
                "archdaily.com",
                "archdaily.cn",
                "dezeen.com",
                "designboom.com",
                "architizer.com",
                "gooood.cn",
                "interiordesign.net",
                "archcollege.com",
                "archiposition.com",
                "ad110.com",
                "adchina.cn",
            ],
            "score": 100,
        },
        # Tier 2: 设计社区平台 (85分)
        "tier_2": {
            "domains": [
                "dribbble.com",
                "behance.net",
                "awwwards.com",
                "pinterest.com",
                "pinimg.com",  # Pinterest CDN
                "zcool.com.cn",
                "站酷.com",
                "ui.cn",
                "uisdc.com",
                "shejidaren.com",
            ],
            "score": 85,
        },
        # Tier 3: 图库/素材站 (70分)
        "tier_3": {
            "domains": [
                "huaban.com",
                "花瓣.com",  # 花瓣网
                "unsplash.com",
                "pexels.com",
                "pixabay.com",
                "flickr.com",
                "500px.com",
                "istock",
                "shutterstock",
                "gettyimages",
            ],
            "score": 70,
        },
        # Tier 4: 综合平台 (55分)
        "tier_4": {
            "domains": [
                "zhihu.com",
                "xiaohongshu.com",
                "xhscdn.com",
                "weibo.com",
                "sinaimg.cn",
                "douban.com",
                "bilibili.com",
            ],
            "score": 55,
        },
        # Tier 5: 低质量装修平台 (25分)
        "low_quality": {
            "domains": [
                "qijia.com",
                "齐家网",  # 营销为主
                "to8to.com",
                "土巴兔",  # 营销为主
                "shejiben.com",
                "设计本",  # 内容参差不齐
                "jia.com",
                "家居在线",
                "pchouse.com.cn",
                "zhuangyi.com",
                "装一网",
                "jiazhuang.com",
            ],
            "score": 25,
        },
        # 黑名单: 直接拒绝
        "blacklist": {
            "domains": [
                "baidu.com",
                "bdimg.cn",
                "bdstatic.com",  # 百度图片质量差
                "sohu.com",
                "163.com",
                "qq.com",  # 门户站广告多
                "alicdn.com",
                "taobao.com",
                "tmall.com",  # 电商图片
                "jd.com",
                "360buyimg.com",  # 电商图片
            ],
            "score": 0,
        },
    }

    # ====== 低质量 URL 模式（匹配即拒绝或降分） ======
    LOW_QUALITY_PATTERNS = [
        # === 严格拒绝的模式 ===
        # 缩略图
        (re.compile(r"[/_]thumb(nail)?[/_s]?\d*", re.I), "reject", "缩略图"),
        (re.compile(r"[/_](s|small|mini|tiny|micro)\d*\.", re.I), "reject", "小图"),
        (re.compile(r"[?&][wh]=\d{1,2}(&|$)", re.I), "reject", "尺寸参数过小"),  # w=50
        (re.compile(r"_\d{2,3}x\d{2,3}\.", re.I), "reject", "小尺寸后缀"),  # _50x50.jpg
        # 头像/图标
        (re.compile(r"avatar|profile[-_]?pic|user[-_]?icon", re.I), "reject", "头像"),
        (re.compile(r"/icons?/", re.I), "reject", "图标目录"),
        (re.compile(r"favicon|logo[-_]?(small|mini)?\d*\.(png|ico|svg|gif)", re.I), "reject", "favicon/logo"),
        # 广告/营销
        (re.compile(r"/ads?[/_]", re.I), "reject", "广告目录"),
        (re.compile(r"/banner[s]?/", re.I), "reject", "横幅广告"),
        (re.compile(r"affiliate|sponsor[ed]*|tracking|pixel\.(gif|png)", re.I), "reject", "跟踪像素"),
        (re.compile(r"promo(tion)?[-_]", re.I), "reject", "促销图"),
        # 占位符/默认图
        (re.compile(r"placeholder|default[-_]?image|no[-_]?image|blank[-_]?img", re.I), "reject", "占位符"),
        (re.compile(r"(blank|spacer|loading|empty)\.(gif|png|jpg)", re.I), "reject", "空白图"),
        # 表情/贴纸
        (re.compile(r"/emoji[s]?/", re.I), "reject", "表情"),
        (re.compile(r"/sticker[s]?/", re.I), "reject", "贴纸"),
        # === 降分但不拒绝的模式 ===
        # 可能是缩略图但不确定
        (re.compile(r"[-_]preview\.", re.I), "penalize", "预览图"),
        (re.compile(r"[-_]cover\.", re.I), "penalize", "封面图"),
        (re.compile(r"/thumbnail/", re.I), "penalize", "缩略图目录"),
    ]

    # ====== 高质量 URL 模式（匹配加分） ======
    HIGH_QUALITY_PATTERNS = [
        # 高清/原图标识
        (re.compile(r"[/_](large|hd|hires|highres|full|original|raw)[/_.]", re.I), 20, "高清标识"),
        (re.compile(r"[/_](1920|2k|4k|uhd)[/_x]", re.I), 25, "高分辨率"),
        (re.compile(r"[?&]w=\d{4,}", re.I), 15, "大尺寸参数"),  # w=1920
        (re.compile(r"[?&]quality=\d{2}", re.I), 10, "高质量参数"),
        (re.compile(r"_\d{4}x\d{3,4}\.", re.I), 20, "大尺寸后缀"),  # _1920x1080.jpg
        # 作品集/项目图
        (re.compile(r"/(project|work|portfolio|gallery|showcase)[s]?/", re.I), 15, "作品集目录"),
        (re.compile(r"/render[s]?/", re.I), 15, "渲染图"),
        (re.compile(r"/photo[s]?/", re.I), 10, "照片目录"),
        (re.compile(r"/(interior|exterior|design)[-_]?", re.I), 10, "设计相关"),
        # 设计平台高清图CDN模式
        (re.compile(r"dribbble\.com.*/\d{4}", re.I), 15, "Dribbble原图"),
        (re.compile(r"behance\.net.*original", re.I), 15, "Behance原图"),
        (re.compile(r"pinimg\.com.*/originals?/", re.I), 15, "Pinterest原图"),
        (re.compile(r"archdaily\.com.*large", re.I), 15, "ArchDaily大图"),
    ]

    # ====== 权重配置 ======
    WEIGHTS = {
        "dimension": 0.30,  # 尺寸权重 30%
        "url_quality": 0.25,  # URL模式权重 25%
        "domain": 0.30,  # 域名权重 30%
        "relevance": 0.15,  # 相关性权重 15%
    }

    def __init__(
        self,
        min_width: int | None = None,
        min_height: int | None = None,
        pass_threshold: float | None = None,
        enabled: bool = True,
    ):
        """
        初始化图片过滤服务

        Args:
            min_width: 最小宽度，低于此值拒绝
            min_height: 最小高度，低于此值拒绝
            pass_threshold: 通过阈值，低于此分数拒绝
            enabled: 是否启用过滤
        """
        # 从环境变量读取配置，支持覆盖
        self.enabled = enabled and os.getenv("IMAGE_FILTER_ENABLED", "true").lower() == "true"
        self.min_width = min_width or int(os.getenv("IMAGE_FILTER_MIN_WIDTH", str(self.DEFAULT_MIN_WIDTH)))
        self.min_height = min_height or int(os.getenv("IMAGE_FILTER_MIN_HEIGHT", str(self.DEFAULT_MIN_HEIGHT)))
        self.pass_threshold = pass_threshold or float(
            os.getenv("IMAGE_FILTER_MIN_SCORE", str(self.DEFAULT_PASS_THRESHOLD))
        )
        self.ideal_width = int(os.getenv("IMAGE_FILTER_IDEAL_WIDTH", str(self.DEFAULT_IDEAL_WIDTH)))
        self.ideal_height = int(os.getenv("IMAGE_FILTER_IDEAL_HEIGHT", str(self.DEFAULT_IDEAL_HEIGHT)))

        # 日志记录配置
        self.debug_mode = os.getenv("DEBUG", "false").lower() == "true"

        if self.enabled:
            logger.info(f" 图片过滤服务已启用: min_size={self.min_width}x{self.min_height}, threshold={self.pass_threshold}")

    def filter_images(
        self,
        images: List[Any],
        query: str = "",
        max_results: int = 10,
    ) -> List[Any]:
        """
        过滤图片列表

        Args:
            images: 图片列表（支持 ImageResult 对象或字典）
            query: 搜索查询词（用于相关性评分）
            max_results: 最大返回数量

        Returns:
            过滤后的高质量图片列表（按分数排序）
        """
        if not self.enabled:
            return images[:max_results]

        if not images:
            return []

        # 提取关键词用于相关性评分
        keywords = self._extract_keywords(query)

        scored_images = []
        rejected_count = 0

        for img in images:
            # 统一转换为字典格式处理
            img_dict = self._to_dict(img)

            score_result = self.score_image(img_dict, keywords)

            if score_result.should_keep:
                # 将评分信息附加到图片对象
                if hasattr(img, "__dict__"):
                    img.quality_score = score_result.total_score
                scored_images.append((img, score_result.total_score))
            else:
                rejected_count += 1
                if self.debug_mode:
                    logger.debug(f" 过滤图片: {img_dict.get('url', '')[:80]}... 原因: {score_result.reject_reason}")

        # 按分数排序
        scored_images.sort(key=lambda x: x[1], reverse=True)

        result = [img for img, _ in scored_images[:max_results]]

        logger.info(f" 图片过滤完成: {len(images)} -> {len(result)} (过滤 {rejected_count} 张)")

        return result

    def score_image(
        self,
        image: Dict[str, Any],
        keywords: List[str] = None,
    ) -> ImageQualityScore:
        """
        对单张图片评分

        Args:
            image: 图片信息字典
            keywords: 相关性判断用的关键词列表

        Returns:
            ImageQualityScore 评分结果
        """
        url = image.get("url", "")
        source_url = image.get("source_url", "")
        title = image.get("title", "")
        width = image.get("width", 0)
        height = image.get("height", 0)

        # 1. 尺寸评分
        dim_score, dim_reject = self._score_dimension(width, height)
        if dim_reject:
            return ImageQualityScore(
                total_score=0,
                dimension_score=dim_score,
                url_quality_score=0,
                domain_score=0,
                relevance_score=0,
                should_keep=False,
                reject_reason=dim_reject,
            )

        # 2. URL 质量评分
        url_score, url_reject = self._score_url_quality(url)
        if url_reject:
            return ImageQualityScore(
                total_score=0,
                dimension_score=dim_score,
                url_quality_score=url_score,
                domain_score=0,
                relevance_score=0,
                should_keep=False,
                reject_reason=url_reject,
            )

        # 3. 域名评分
        domain_score, domain_reject = self._score_domain(source_url or url)
        if domain_reject:
            return ImageQualityScore(
                total_score=0,
                dimension_score=dim_score,
                url_quality_score=url_score,
                domain_score=domain_score,
                relevance_score=0,
                should_keep=False,
                reject_reason=domain_reject,
            )

        # 4. 相关性评分
        relevance_score = self._score_relevance(title, keywords or [])

        # 综合评分（加权平均）
        total = (
            dim_score * self.WEIGHTS["dimension"]
            + url_score * self.WEIGHTS["url_quality"]
            + domain_score * self.WEIGHTS["domain"]
            + relevance_score * self.WEIGHTS["relevance"]
        )

        should_keep = total >= self.pass_threshold

        return ImageQualityScore(
            total_score=round(total, 2),
            dimension_score=dim_score,
            url_quality_score=url_score,
            domain_score=domain_score,
            relevance_score=relevance_score,
            should_keep=should_keep,
            reject_reason=None if should_keep else f"综合分数 {total:.1f} < {self.pass_threshold}",
        )

    def _score_dimension(self, width: int, height: int) -> Tuple[float, str | None]:
        """尺寸评分"""
        # 无尺寸信息时给中性分，不拒绝
        if width == 0 or height == 0:
            return 50, None

        # 低于最小尺寸直接拒绝
        if width < self.min_width or height < self.min_height:
            return 0, f"尺寸过小: {width}x{height} < {self.min_width}x{self.min_height}"

        # 达到理想尺寸满分
        if width >= self.ideal_width and height >= self.ideal_height:
            return 100, None

        # 线性插值计算分数
        w_ratio = min(1.0, (width - self.min_width) / (self.ideal_width - self.min_width))
        h_ratio = min(1.0, (height - self.min_height) / (self.ideal_height - self.min_height))
        score = 50 + 50 * ((w_ratio + h_ratio) / 2)

        return round(score, 2), None

    def _score_url_quality(self, url: str) -> Tuple[float, str | None]:
        """URL 质量评分"""
        if not url:
            return 0, "URL为空"

        base_score = 60  # 基础分

        # 检查低质量模式
        for pattern, action, reason in self.LOW_QUALITY_PATTERNS:
            if pattern.search(url):
                if action == "reject":
                    return 0, f"URL模式: {reason}"
                elif action == "penalize":
                    base_score -= 15

        # 检查高质量模式（加分）
        for pattern, bonus, reason in self.HIGH_QUALITY_PATTERNS:
            if pattern.search(url):
                base_score += bonus
                if self.debug_mode:
                    logger.debug(f"   URL加分 +{bonus}: {reason}")

        return min(100, max(0, base_score)), None

    def _score_domain(self, url: str) -> Tuple[float, str | None]:
        """域名评分"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # 遍历各级域名配置
            for tier_name, tier_config in self.DOMAIN_TIERS.items():
                for tier_domain in tier_config["domains"]:
                    if tier_domain in domain:
                        score = tier_config["score"]
                        if score == 0:  # 黑名单
                            return 0, f"域名黑名单: {tier_domain}"
                        return score, None

            # 未知域名给中性分
            return 50, None

        except Exception:
            return 50, None

    def _score_relevance(self, title: str, keywords: List[str]) -> float:
        """标题相关性评分"""
        if not keywords or not title:
            return 50  # 无法判断时给中性分

        title_lower = title.lower()
        matches = sum(1 for kw in keywords if kw.lower() in title_lower)

        if matches == 0:
            return 30
        elif matches == 1:
            return 60
        elif matches == 2:
            return 80
        else:
            return 100

    def _extract_keywords(self, query: str) -> List[str]:
        """从查询中提取关键词"""
        if not query:
            return []

        # 简单分词：按空格和常见标点分割
        import re

        words = re.split(r"[\s,，、;；:：.。!！?？]+", query)

        # 过滤太短的词和停用词
        stopwords = {
            "的",
            "了",
            "和",
            "与",
            "或",
            "在",
            "是",
            "有",
            "我",
            "你",
            "他",
            "a",
            "an",
            "the",
            "is",
            "are",
            "of",
            "for",
            "to",
            "in",
            "on",
        }
        keywords = [w for w in words if len(w) >= 2 and w.lower() not in stopwords]

        return keywords[:10]  # 限制关键词数量

    def _to_dict(self, img: Any) -> Dict[str, Any]:
        """将图片对象转换为字典"""
        if isinstance(img, dict):
            return img

        # 支持 dataclass 或普通对象
        if hasattr(img, "__dict__"):
            return {
                "url": getattr(img, "url", ""),
                "thumbnail_url": getattr(img, "thumbnail_url", ""),
                "title": getattr(img, "title", ""),
                "source_url": getattr(img, "source_url", ""),
                "width": getattr(img, "width", 0),
                "height": getattr(img, "height", 0),
            }

        return {}


# ====== 便捷函数 ======

_default_filter_service: ImageFilterService | None = None


def get_image_filter_service() -> ImageFilterService:
    """获取全局图片过滤服务实例"""
    global _default_filter_service
    if _default_filter_service is None:
        _default_filter_service = ImageFilterService()
    return _default_filter_service


def filter_search_images(
    images: List[Any],
    query: str = "",
    max_results: int = 10,
) -> List[Any]:
    """
    快速过滤搜索图片（便捷函数）

    Args:
        images: 原始图片列表
        query: 搜索查询词
        max_results: 最大返回数量

    Returns:
        过滤后的图片列表

    Usage:
        from intelligent_project_analyzer.services.lightweight_image_filter import filter_search_images

        filtered = filter_search_images(
            images=bocha_result.images,
            query="日式茶室设计",
            max_results=8
        )
    """
    return get_image_filter_service().filter_images(images, query, max_results)
