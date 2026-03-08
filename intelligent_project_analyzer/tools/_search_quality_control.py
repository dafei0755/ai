"""
Search Quality Control (v7.197 + 语义去重 + 动态权重)

搜索结果质量控制管道：黑名单过滤 → 相关性过滤 → 语义去重 → 可信度评估 → 白名单提升 → 排序 → 域名统计

v7.197 新增：
- 语义去重：使用 Embedding 相似度替代前100字符对比
- 动态权重：根据查询类型动态调整时效性/可信度权重
- 查询分类器集成：自动识别 news/academic/case/concept 等类型
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Set
from urllib.parse import urlparse

from loguru import logger

# v7.197: 导入语义去重和查询分类器
_semantic_dedup_module = None
_query_classifier_module = None


def _get_semantic_dedup():
    """延迟加载语义去重模块"""
    global _semantic_dedup_module
    if _semantic_dedup_module is None:
        try:
            from . import semantic_dedup

            _semantic_dedup_module = semantic_dedup
        except Exception as e:
            logger.warning(f"️ 语义去重模块加载失败，使用前缀去重: {e}")
            _semantic_dedup_module = False
    return _semantic_dedup_module if _semantic_dedup_module else None


def _get_query_classifier():
    """延迟加载查询分类器模块"""
    global _query_classifier_module
    if _query_classifier_module is None:
        try:
            from . import query_classifier

            _query_classifier_module = query_classifier
        except Exception as e:
            logger.warning(f"️ 查询分类器模块加载失败，使用默认权重: {e}")
            _query_classifier_module = False
    return _query_classifier_module if _query_classifier_module else None


# 域名质量统计服务（延迟导入以避免循环依赖）
_domain_stats_service = None


def _get_domain_stats_service():
    """获取域名统计服务（延迟加载）"""
    global _domain_stats_service
    if _domain_stats_service is None:
        try:
            from ..services.domain_quality_stats import get_domain_stats_service

            _domain_stats_service = get_domain_stats_service()
        except Exception as e:
            logger.warning(f"️ 域名质量统计服务加载失败: {e}")
            _domain_stats_service = False  # 标记为加载失败，避免重复尝试
    return _domain_stats_service if _domain_stats_service else None


class SearchQualityControl:
    """
    搜索结果质量控制器

    核心功能：
    1. 相关性过滤 - 移除低相关度结果
    2. 内容完整性检查 - 确保内容不是空壳
    3. 去重和聚类 - 移除重复内容
    4. 来源可信度评估 - 评估信息来源可靠性
    5. 综合质量评分 - 计算多维度加权分数
    6. 排序和编号 - 按质量分数排序
    """

    #  可信域名白名单（分级 v7.155扩展, v7.174学术增强）
    TRUSTED_DOMAINS = {
        "high": [
            # 学术机构 (v7.174: 扩展学术域名)
            "arxiv.org",
            ".edu",
            ".ac.uk",
            ".edu.cn",
            ".ac.cn",
            ".edu.hk",
            ".edu.tw",
            #  v7.174: 学术数据库
            "cnki.net",
            "wanfangdata.com.cn",
            "cqvip.com",
            "scholar.google.com",
            "researchgate.net",
            "academia.edu",
            "sciencedirect.com",
            "springer.com",
            "wiley.com",
            "nature.com",
            "science.org",
            "ieee.org",
            "acm.org",
            "jstor.org",
            # 政府/标准组织
            ".gov",
            ".gov.cn",
            "iso.org",
            "w3.org",
            # 知名设计/技术站点
            "nngroup.com",
            "smashingmagazine.com",
            "a11yproject.com",
            "designbetter.co",
            "ideo.com",
            "frogdesign.com",
            #  v7.174 国际设计权威（扩展）
            "archdaily.com",
            "archdaily.cn",
            "dezeen.com",
            "designboom.com",
            "architizer.com",
            "interiordesign.net",
            "gooood.cn",
            "archcollege.com",
            #  v7.174: 百度学术单独加入（区别于百度系其他产品）
            "xueshu.baidu.com",
        ],
        "medium": [
            # 专业社区
            "medium.com",
            "stackoverflow.com",
            "github.com",
            "dribbble.com",
            "behance.net",
            "awwwards.com",
            # 行业媒体
            "designmilk.com",
            "pinterest.com",
            #  v7.174 中文设计媒体（扩展）
            "uisdc.com",
            "zcool.com.cn",
            "ui.cn",
            "站酷.com",
        ],
        "low": [
            # 商业内容平台（可能质量不稳定）
            "zhihu.com",
            "jianshu.com",
            "csdn.net",
            #  v7.174 营销类站点（降级到low）
            "shejiben.com",
            "to8to.com",
        ],
    }

    # ️ 内容完整性阈值
    MIN_CONTENT_LENGTH = 50  # 最小内容长度（字符）
    MIN_RELEVANCE_THRESHOLD = 0.6  # 最小相关性分数（0-1）

    #  占位符URL模式（扩展 v7.155）
    PLACEHOLDER_PATTERNS = [
        "example.com",
        "example2.com",
        "example3.com",
        "placeholder",
        "test.com",
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "dummy",
        "fake",
        "sample",
        "xxx.com",
        "yyy.com",
        "mock",
    ]

    #  无效URL模式（v7.155）
    INVALID_URL_PATTERNS = [
        r"^javascript:",
        r"^data:",
        r"^mailto:",
        r"^tel:",
        r"^#",
    ]

    #  质量评分权重 (v7.197: 支持动态权重)
    # 默认权重 - 会被查询分类器动态覆盖
    SCORE_WEIGHTS = {
        "relevance": 0.35,  # 相关性 35%
        "timeliness": 0.10,  # 时效性 10% (动态：news=30%, academic=5%)
        "credibility": 0.35,  # 可信度 35% (动态：academic=45%)
        "completeness": 0.20,  # 完整性 20%
    }

    #  v7.174: 学术来源额外加分
    ACADEMIC_BOOST = 15.0  # 学术域名额外加15分

    #  v7.197: 语义去重配置
    SEMANTIC_DEDUP_ENABLED = True
    SEMANTIC_DEDUP_THRESHOLD = 0.85  # 相似度阈值

    def __init__(
        self,
        min_relevance: float = 0.6,
        min_content_length: int = 50,
        enable_deduplication: bool = True,
        enable_filters: bool = True,
        query: str | None = None,  # v7.197: 支持传入查询用于动态权重
    ):
        """
        初始化质量控制器

        Args:
            min_relevance: 最小相关性阈值
            min_content_length: 最小内容长度
            enable_deduplication: 是否启用去重
            enable_filters: 是否启用黑白名单过滤
            query: 用户查询（用于动态权重计算）
        """
        self.min_relevance = min_relevance
        self.min_content_length = min_content_length
        self.enable_deduplication = enable_deduplication
        self.enable_filters = enable_filters
        self.query = query  # v7.197: 保存查询用于动态权重

        #  v7.197: 动态权重计算
        self._dynamic_weights = None
        self._init_dynamic_weights(query)

        #  加载黑白名单管理器
        self.filter_manager = None
        if enable_filters:
            try:
                from ..services.search_filter_manager import get_filter_manager

                self.filter_manager = get_filter_manager()
                logger.info(" 搜索黑白名单过滤器已启用")
            except Exception as e:
                logger.warning(f"️ 黑白名单过滤器加载失败: {e}")
                self.filter_manager = None

        logger.info(
            f" SearchQualityControl initialized: "
            f"min_relevance={min_relevance}, "
            f"min_content_length={min_content_length}, "
            f"dedup={enable_deduplication}, "
            f"filters={enable_filters}"
        )

    def _init_dynamic_weights(self, query: str | None) -> None:
        """
        初始化动态权重 (v7.197)

        根据查询类型动态调整权重。
        """
        if not query:
            self._dynamic_weights = dict(self.SCORE_WEIGHTS)
            return

        classifier = _get_query_classifier()
        if not classifier:
            self._dynamic_weights = dict(self.SCORE_WEIGHTS)
            return

        try:
            weights = classifier.get_dynamic_weights(query)
            self._dynamic_weights = weights
            logger.info(
                f" [动态权重] 查询='{query[:30]}...' | "
                f"时效性={weights.get('timeliness', 0.10):.0%} | "
                f"可信度={weights.get('credibility', 0.35):.0%}"
            )
        except Exception as e:
            logger.warning(f"️ 动态权重计算失败: {e}")
            self._dynamic_weights = dict(self.SCORE_WEIGHTS)

    def get_weights(self) -> Dict[str, float]:
        """获取当前权重（动态或默认）"""
        return self._dynamic_weights or dict(self.SCORE_WEIGHTS)

    def process_results(
        self, results: List[Dict[str, Any]], deliverable_context: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        """
        处理搜索结果（完整管道）

        Pipeline: Filter → Deduplicate → Assess → Score → Sort

        Args:
            results: 原始搜索结果列表
            deliverable_context: 交付物上下文（用于相关性判断）

        Returns:
            处理后的结果列表（已排序）
        """
        if not results:
            return []

        logger.info(f" Processing {len(results)} search results")

        # Step 0:  黑名单过滤（优先级最高）
        if self.enable_filters and self.filter_manager:
            filtered = self._apply_blacklist(results)
            logger.debug(f" After blacklist filter: {len(filtered)} results")
        else:
            filtered = results

        # Step 0.5:  v7.155 URL有效性过滤（新增）
        filtered = self._filter_by_url_validity(filtered)
        logger.debug(f" After URL validity filter: {len(filtered)} results")

        # Step 1: 相关性过滤
        filtered = self._filter_by_relevance(filtered)
        logger.debug(f" After relevance filter: {len(filtered)} results")

        # Step 2: 内容完整性过滤
        filtered = self._filter_by_completeness(filtered)
        logger.debug(f" After completeness filter: {len(filtered)} results")

        # Step 3: 去重
        if self.enable_deduplication:
            unique = self._deduplicate(filtered)
            logger.debug(f" After deduplication: {len(unique)} results")
        else:
            unique = filtered

        # Step 4: 可信度评估 + 质量评分
        for result in unique:
            # 评估来源可信度
            result["source_credibility"] = self.assess_credibility(result.get("url", ""))

            # 计算综合质量分数
            result["quality_score"] = self.calculate_composite_score(result)

        # Step 5:  白名单优先级提升
        if self.enable_filters and self.filter_manager:
            self._boost_whitelist(unique)

        # Step 6: 排序（按质量分数降序）
        sorted_results = sorted(unique, key=lambda x: x.get("quality_score", 0), reverse=True)

        # Step 7:  域名质量统计收集（用于自动评估审核）
        self._record_domain_quality_stats(sorted_results)

        logger.info(f" Quality control completed: {len(sorted_results)} high-quality results")

        return sorted_results

    def _record_domain_quality_stats(self, results: List[Dict[str, Any]]) -> None:
        """
        记录域名质量统计（用于自动评估审核队列）

        Args:
            results: 已处理的搜索结果列表
        """
        try:
            stats_service = _get_domain_stats_service()
            if not stats_service:
                return

            for result in results:
                url = result.get("url", "")
                if not url:
                    continue

                quality_score = result.get("quality_score", 0)
                relevance_score = (
                    result.get("relevance_score") or result.get("similarity_score") or result.get("score", 0)
                )
                if isinstance(relevance_score, float) and relevance_score <= 1:
                    relevance_score *= 100

                content = result.get("content", "") or result.get("snippet", "") or ""
                content_length = len(content)

                # 记录到统计服务
                stats_service.record_result(
                    url=url,
                    quality_score=quality_score,
                    relevance_score=relevance_score,
                    content_length=content_length,
                    is_duplicate=False,
                )

        except Exception as e:
            logger.debug(f"️ 域名质量统计记录失败: {e}")

    def _apply_blacklist(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        应用黑名单过滤

        完全移除黑名单中的域名结果

        Args:
            results: 搜索结果列表

        Returns:
            过滤后的结果列表
        """
        if not self.filter_manager:
            return results

        filtered = []
        blocked_count = 0

        for result in results:
            url = result.get("url", "")
            if not url:
                filtered.append(result)
                continue

            # 检查是否在黑名单中
            if self.filter_manager.is_blacklisted(url):
                blocked_count += 1
                logger.debug(f" [黑名单过滤] {url}")
                continue

            filtered.append(result)

        if blocked_count > 0:
            logger.info(f" 黑名单过滤: 移除 {blocked_count} 个结果")

        return filtered

    def _boost_whitelist(self, results: List[Dict[str, Any]]) -> None:
        """
        提升白名单域名的质量分数

        Args:
            results: 搜索结果列表（原地修改）
        """
        if not self.filter_manager:
            return

        boost_score = self.filter_manager.get_boost_score()
        boost_points = boost_score * 100 if boost_score <= 1 else boost_score
        boosted_count = 0

        for result in results:
            url = result.get("url", "")
            if not url:
                continue

            # 检查是否在白名单中
            if self.filter_manager.is_whitelisted(url):
                # 提升质量分数
                original_score = result.get("quality_score", 0)
                result["quality_score"] = min(100.0, original_score + boost_points)
                result["whitelist_boosted"] = True
                boosted_count += 1
                logger.debug(
                    f"⭐ [白名单提升] {url}: {original_score:.2f} → {result['quality_score']:.2f} (+{boost_points:.2f})"
                )

        if boosted_count > 0:
            logger.info(f"⭐ 白名单提升: {boosted_count} 个结果获得优先级")

    def _filter_by_relevance(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        按相关性分数过滤

        Args:
            results: 搜索结果列表

        Returns:
            过滤后的结果列表

        Note:
            v7.176: 如果结果没有任何相关性分数字段，默认让其通过过滤
            （因为此时相关性分数尚未计算，后续会在评分阶段计算）
        """
        filtered = []
        for r in results:
            # 检查是否有任何相关性分数字段
            has_relevance = any(["relevance_score" in r, "similarity_score" in r, "score" in r])

            if not has_relevance:
                # 没有相关性分数，默认通过（后续评分阶段会计算）
                filtered.append(r)
            elif (
                r.get("relevance_score", 0) >= self.min_relevance
                or r.get("similarity_score", 0) >= self.min_relevance
                or r.get("score", 0) >= self.min_relevance
            ):
                # 有相关性分数且满足阈值
                filtered.append(r)

        removed_count = len(results) - len(filtered)
        if removed_count > 0:
            logger.debug(f"️ Filtered out {removed_count} low-relevance results")

        return filtered

    def _filter_by_completeness(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        按内容完整性过滤

        Args:
            results: 搜索结果列表

        Returns:
            过滤后的结果列表
        """
        filtered = []
        for r in results:
            content = r.get("content", "") or r.get("snippet", "") or r.get("summary", "")
            if len(content) >= self.min_content_length:
                r["content_complete"] = True
                filtered.append(r)
            else:
                r["content_complete"] = False
                logger.debug(
                    f"️ Filtered out incomplete result: '{r.get('title', 'N/A')}' " f"(length={len(content)})"
                )

        return filtered

    def _filter_by_url_validity(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
         v7.155: 按URL有效性过滤

        过滤规则:
        1. URL必须以http/https开头
        2. 不能包含占位符域名
        3. 不能是无效协议

        Args:
            results: 搜索结果列表

        Returns:
            过滤后的结果列表
        """
        filtered = []
        blocked_count = 0

        for result in results:
            url = result.get("url", "")

            # 1. 检查URL是否存在
            if not url or not isinstance(url, str):
                blocked_count += 1
                logger.debug(" [URL过滤] 空URL或非字符串")
                continue

            # 2. 检查协议
            if not url.startswith(("http://", "https://")):
                blocked_count += 1
                logger.debug(f" [URL过滤] 无效协议: {url}")
                continue

            # 3. 检查占位符域名
            url_lower = url.lower()
            is_placeholder = any(placeholder in url_lower for placeholder in self.PLACEHOLDER_PATTERNS)
            if is_placeholder:
                blocked_count += 1
                logger.warning(f" [URL过滤] 占位符URL: {url}")
                continue

            # 4. 检查无效URL模式
            is_invalid = any(re.match(pattern, url_lower) for pattern in self.INVALID_URL_PATTERNS)
            if is_invalid:
                blocked_count += 1
                logger.debug(f" [URL过滤] 无效URL模式: {url}")
                continue

            # 通过所有检查
            filtered.append(result)

        if blocked_count > 0:
            logger.info(f" URL有效性过滤: 移除 {blocked_count} 个无效URL")

        return filtered

    def _deduplicate(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        去重和聚类 (v7.197: 支持语义去重)

        策略：
        1. 按URL去重（完全相同）
        2. 按标题相似度去重
        3. 按内容语义去重（使用 Embedding 相似度）

        Args:
            results: 搜索结果列表

        Returns:
            去重后的结果列表
        """
        # v7.197: 尝试使用语义去重
        if self.SEMANTIC_DEDUP_ENABLED:
            semantic_dedup = _get_semantic_dedup()
            if semantic_dedup:
                try:
                    unique_results, removed_count = semantic_dedup.semantic_deduplicate(
                        results,
                        threshold=self.SEMANTIC_DEDUP_THRESHOLD,
                        content_key="content",
                        fallback_key="snippet",
                    )
                    if removed_count > 0:
                        logger.info(f" [语义去重] 移除 {removed_count} 个重复结果")
                    return unique_results
                except Exception as e:
                    logger.warning(f"️ 语义去重失败，回退到前缀去重: {e}")

        # 回退：使用原始前缀去重方法
        return self._deduplicate_by_prefix(results)

    def _deduplicate_by_prefix(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        前缀去重（回退方法）

        Args:
            results: 搜索结果列表

        Returns:
            去重后的结果列表
        """
        unique_results = []
        seen_urls: Set[str] = set()
        seen_titles: Set[str] = set()
        seen_content_prefixes: Set[str] = set()

        for result in results:
            # 1. URL去重
            url = result.get("url", "")
            if url and url in seen_urls:
                logger.debug(f"️ Duplicate URL: {url}")
                continue

            # 2. 标题去重（归一化后对比）
            title = result.get("title", "")
            normalized_title = self._normalize_text(title)
            if normalized_title and normalized_title in seen_titles:
                logger.debug(f"️ Duplicate title: {title}")
                continue

            # 3. 内容前缀去重（简化版相似度检测）
            content = result.get("content", "") or result.get("snippet", "")
            content_prefix = self._normalize_text(content[:100])
            if content_prefix and content_prefix in seen_content_prefixes:
                logger.debug("️ Duplicate content prefix")
                continue

            # 通过所有去重检查，添加到结果
            unique_results.append(result)
            if url:
                seen_urls.add(url)
            if normalized_title:
                seen_titles.add(normalized_title)
            if content_prefix:
                seen_content_prefixes.add(content_prefix)

        removed_count = len(results) - len(unique_results)
        if removed_count > 0:
            logger.debug(f"️ Removed {removed_count} duplicate results")

        return unique_results

    def _normalize_text(self, text: str) -> str:
        """
        归一化文本（用于相似度对比）

        Args:
            text: 输入文本

        Returns:
            归一化后的文本
        """
        if not text:
            return ""

        # 转小写、去除多余空格和标点
        normalized = text.lower().strip()
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = re.sub(r"[^\w\s]", "", normalized)

        return normalized

    def assess_credibility(self, url: str) -> str:
        """
        评估来源可信度

        Args:
            url: 来源URL

        Returns:
            可信度等级: "high" | "medium" | "low" | "unknown"
        """
        if not url:
            return "unknown"

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # 检查高可信度域名
            for trusted_domain in self.TRUSTED_DOMAINS["high"]:
                if domain.endswith(trusted_domain) or trusted_domain in domain:
                    return "high"

            # 检查中等可信度域名
            for medium_domain in self.TRUSTED_DOMAINS["medium"]:
                if domain.endswith(medium_domain) or medium_domain in domain:
                    return "medium"

            # 检查低可信度域名
            for low_domain in self.TRUSTED_DOMAINS["low"]:
                if domain.endswith(low_domain) or low_domain in domain:
                    return "low"

            # 未知域名
            return "unknown"

        except Exception as e:
            logger.warning(f"️ Failed to parse URL '{url}': {e}")
            return "unknown"

    def calculate_composite_score(self, result: Dict[str, Any]) -> float:
        """
        计算综合质量分数 (v7.197: 支持动态权重)

        公式:
        Quality Score = Relevance(35%) + Timeliness(动态) + Credibility(动态) + Completeness(动态)
        + Academic Boost (学术来源额外+15分)

        分数范围: [30, 100]

        Args:
            result: 搜索结果字典

        Returns:
            综合质量分数（0-100）
        """
        # v7.197: 获取动态权重
        weights = self.get_weights()

        # 1. 相关性分数（0-100）
        relevance = (
            result.get("relevance_score") or result.get("similarity_score") or result.get("score") or 0.7  # 默认中等相关
        )
        relevance_score = relevance * 100

        # 2. 时效性分数（0-100）
        timeliness_score = self._calculate_timeliness_score(result)

        # 3. 可信度分数（0-100）- v7.174增强
        credibility = result.get("source_credibility", "unknown")
        credibility_map = {"high": 100, "medium": 70, "low": 50, "unknown": 60}
        credibility_score = credibility_map.get(credibility, 60)

        # 4. 完整性分数（0-100）
        completeness_score = 100 if result.get("content_complete", True) else 50

        # v7.197: 使用动态权重计算
        composite = (
            relevance_score * weights.get("relevance", 0.35)
            + timeliness_score * weights.get("timeliness", 0.10)
            + credibility_score * weights.get("credibility", 0.35)
            + completeness_score * weights.get("completeness", 0.20)
        )

        #  v7.174: 学术来源额外加分
        url = result.get("url", "")
        if self._is_academic_source(url):
            composite += self.ACADEMIC_BOOST
            result["is_academic"] = True
            logger.debug(f" 学术来源加分: {url} (+{self.ACADEMIC_BOOST})")

        # 确保在合理范围内（30-100）
        composite = max(30.0, min(100.0, composite))

        return round(composite, 2)

    def _is_academic_source(self, url: str) -> bool:
        """
        判断URL是否来自学术来源 (v7.174新增)

        Args:
            url: 来源URL

        Returns:
            是否为学术来源
        """
        if not url:
            return False

        url_lower = url.lower()

        # 学术域名关键词
        academic_indicators = [
            # 学术数据库
            "cnki.net",
            "wanfangdata",
            "cqvip.com",
            "scholar.google",
            "researchgate.net",
            "academia.edu",
            "sciencedirect",
            "springer.com",
            "wiley.com",
            "nature.com",
            "science.org",
            "ieee.org",
            "acm.org",
            "jstor.org",
            "arxiv.org",
            "xueshu.baidu.com",
            # 教育机构
            ".edu",
            ".edu.cn",
            ".edu.hk",
            ".edu.tw",
            ".ac.uk",
            ".ac.cn",
            ".ac.jp",
            # 论文/研究相关URL模式
            "/paper/",
            "/article/",
            "/publication/",
            "/thesis/",
            "/journal/",
            "/proceedings/",
            "/research/",
        ]

        for indicator in academic_indicators:
            if indicator in url_lower:
                return True

        return False

    def _calculate_timeliness_score(self, result: Dict[str, Any]) -> float:
        """
        计算时效性分数

        策略：
        - 最近1年: 100分
        - 1-2年: 90分
        - 2-3年: 80分
        - 3-5年: 70分
        - 5-10年: 60分
        -  v7.155 未来日期: 0分（拒绝）
        -  v7.155 10年以上: 50分（过期）
        - 无日期: 70分（中性）

        Args:
            result: 搜索结果字典

        Returns:
            时效性分数（0-100）
        """
        # 尝试从多个字段获取发布日期
        date_str = (
            result.get("published_date")
            or result.get("datePublished")  #  v7.155 Bocha字段
            or result.get("published")
            or result.get("updated")
            or result.get("last_updated")
        )

        if not date_str:
            return 70.0  # 无日期，返回中性分数

        try:
            # 解析日期（支持多种格式）
            pub_date = None
            if isinstance(date_str, str):
                # 尝试多种日期格式
                for fmt in [
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%d",
                    "%Y/%m/%d",
                    "%Y年%m月%d日",
                ]:
                    try:
                        pub_date = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue

                if pub_date is None:
                    # ISO格式（最后尝试）
                    pub_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                pub_date = date_str

            # 计算时间差
            now = datetime.now(pub_date.tzinfo) if pub_date.tzinfo else datetime.now()
            delta = now - pub_date

            #  v7.155: 检查未来日期
            if delta.days < 0:
                logger.warning(f"️ 检测到未来日期: {date_str}，拒绝此结果")
                return 0.0  # 未来日期，返回0分（将被过滤）

            years = delta.days / 365.25

            # 分级评分
            if years < 1:
                return 100.0
            elif years < 2:
                return 90.0
            elif years < 3:
                return 80.0
            elif years < 5:
                return 70.0
            elif years < 10:
                return 60.0
            else:
                #  v7.155: 超过10年的内容降低分数
                logger.debug(f"️ 内容过期: {years:.1f}年前发布")
                return 50.0

        except Exception as e:
            logger.debug(f"️ Failed to parse date '{date_str}': {e}")
            return 70.0  # 解析失败，返回中性分数


# ============================================================================
# 辅助函数：快速使用
# ============================================================================


def quick_quality_control(results: List[Dict[str, Any]], min_relevance: float = 0.6) -> List[Dict[str, Any]]:
    """
    快速质量控制（单例模式）

    Args:
        results: 搜索结果列表
        min_relevance: 最小相关性阈值

    Returns:
        处理后的结果列表
    """
    qc = SearchQualityControl(min_relevance=min_relevance)
    return qc.process_results(results)


# ============================================================================
# v7.170 新增：内容深度评估器
# ============================================================================


