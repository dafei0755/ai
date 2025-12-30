"""
Search Quality Control (v7.64)

搜索结果质量控制管道：过滤 → 去重 → 可信度评估 → 质量评分 → 排序
"""

from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
import re
from loguru import logger
from urllib.parse import urlparse


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

    # 🔒 可信域名白名单（分级）
    TRUSTED_DOMAINS = {
        "high": [
            # 学术机构
            "arxiv.org", ".edu", ".ac.uk", ".edu.cn",
            # 政府/标准组织
            ".gov", ".gov.cn", "iso.org", "w3.org",
            # 知名设计/技术站点
            "nngroup.com", "smashingmagazine.com", "a11yproject.com",
            "designbetter.co", "ideo.com", "frogdesign.com"
        ],
        "medium": [
            # 专业社区
            "medium.com", "stackoverflow.com", "github.com",
            "dribbble.com", "behance.net", "awwwards.com",
            # 行业媒体
            "designmilk.com", "dezeen.com", "archdaily.com",
            "interiordesign.net", "architizer.com"
        ],
        "low": [
            # 商业内容平台（可能质量不稳定）
            "zhihu.com", "jianshu.com", "csdn.net"
        ]
    }

    # ⚠️ 内容完整性阈值
    MIN_CONTENT_LENGTH = 50  # 最小内容长度（字符）
    MIN_RELEVANCE_THRESHOLD = 0.6  # 最小相关性分数（0-1）

    # 📊 质量评分权重
    SCORE_WEIGHTS = {
        "relevance": 0.4,      # 相关性 40%
        "timeliness": 0.2,     # 时效性 20%
        "credibility": 0.2,    # 可信度 20%
        "completeness": 0.2    # 完整性 20%
    }

    def __init__(
        self,
        min_relevance: float = 0.6,
        min_content_length: int = 50,
        enable_deduplication: bool = True
    ):
        """
        初始化质量控制器

        Args:
            min_relevance: 最小相关性阈值
            min_content_length: 最小内容长度
            enable_deduplication: 是否启用去重
        """
        self.min_relevance = min_relevance
        self.min_content_length = min_content_length
        self.enable_deduplication = enable_deduplication

        logger.info(
            f"✅ SearchQualityControl initialized: "
            f"min_relevance={min_relevance}, "
            f"min_content_length={min_content_length}, "
            f"dedup={enable_deduplication}"
        )

    def process_results(
        self,
        results: List[Dict[str, Any]],
        deliverable_context: Optional[Dict[str, Any]] = None
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

        logger.info(f"🔧 Processing {len(results)} search results")

        # Step 1: 相关性过滤
        filtered = self._filter_by_relevance(results)
        logger.debug(f"📌 After relevance filter: {len(filtered)} results")

        # Step 2: 内容完整性过滤
        filtered = self._filter_by_completeness(filtered)
        logger.debug(f"📌 After completeness filter: {len(filtered)} results")

        # Step 3: 去重
        if self.enable_deduplication:
            unique = self._deduplicate(filtered)
            logger.debug(f"📌 After deduplication: {len(unique)} results")
        else:
            unique = filtered

        # Step 4: 可信度评估 + 质量评分
        for result in unique:
            # 评估来源可信度
            result["source_credibility"] = self.assess_credibility(
                result.get("url", "")
            )

            # 计算综合质量分数
            result["quality_score"] = self.calculate_composite_score(result)

        # Step 5: 排序（按质量分数降序）
        sorted_results = sorted(
            unique,
            key=lambda x: x.get("quality_score", 0),
            reverse=True
        )

        logger.info(
            f"✅ Quality control completed: {len(sorted_results)} high-quality results"
        )

        return sorted_results

    def _filter_by_relevance(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        按相关性分数过滤

        Args:
            results: 搜索结果列表

        Returns:
            过滤后的结果列表
        """
        filtered = [
            r for r in results
            if r.get("relevance_score", 0) >= self.min_relevance or
               r.get("similarity_score", 0) >= self.min_relevance or
               r.get("score", 0) >= self.min_relevance
        ]

        removed_count = len(results) - len(filtered)
        if removed_count > 0:
            logger.debug(f"⚠️ Filtered out {removed_count} low-relevance results")

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
                    f"⚠️ Filtered out incomplete result: '{r.get('title', 'N/A')}' "
                    f"(length={len(content)})"
                )

        return filtered

    def _deduplicate(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        去重和聚类

        策略：
        1. 按URL去重（完全相同）
        2. 按标题相似度去重（编辑距离）
        3. 按内容相似度去重（简化版：前100字符对比）

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
                logger.debug(f"⚠️ Duplicate URL: {url}")
                continue

            # 2. 标题去重（归一化后对比）
            title = result.get("title", "")
            normalized_title = self._normalize_text(title)
            if normalized_title and normalized_title in seen_titles:
                logger.debug(f"⚠️ Duplicate title: {title}")
                continue

            # 3. 内容前缀去重（简化版相似度检测）
            content = result.get("content", "") or result.get("snippet", "")
            content_prefix = self._normalize_text(content[:100])
            if content_prefix and content_prefix in seen_content_prefixes:
                logger.debug(f"⚠️ Duplicate content prefix")
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
            logger.debug(f"⚠️ Removed {removed_count} duplicate results")

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
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[^\w\s]', '', normalized)

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
            logger.warning(f"⚠️ Failed to parse URL '{url}': {e}")
            return "unknown"

    def calculate_composite_score(self, result: Dict[str, Any]) -> float:
        """
        计算综合质量分数

        公式:
        Quality Score = Relevance(40%) + Timeliness(20%) + Credibility(20%) + Completeness(20%)

        分数范围: [30, 100]

        Args:
            result: 搜索结果字典

        Returns:
            综合质量分数（0-100）
        """
        # 1. 相关性分数（0-100）
        relevance = (
            result.get("relevance_score") or
            result.get("similarity_score") or
            result.get("score") or
            0.7  # 默认中等相关
        )
        relevance_score = relevance * 100

        # 2. 时效性分数（0-100）
        timeliness_score = self._calculate_timeliness_score(result)

        # 3. 可信度分数（0-100）
        credibility = result.get("source_credibility", "unknown")
        credibility_map = {"high": 100, "medium": 70, "low": 50, "unknown": 60}
        credibility_score = credibility_map.get(credibility, 60)

        # 4. 完整性分数（0-100）
        completeness_score = 100 if result.get("content_complete", True) else 50

        # 加权计算
        composite = (
            relevance_score * self.SCORE_WEIGHTS["relevance"] +
            timeliness_score * self.SCORE_WEIGHTS["timeliness"] +
            credibility_score * self.SCORE_WEIGHTS["credibility"] +
            completeness_score * self.SCORE_WEIGHTS["completeness"]
        )

        # 确保在合理范围内（30-100）
        composite = max(30.0, min(100.0, composite))

        return round(composite, 2)

    def _calculate_timeliness_score(self, result: Dict[str, Any]) -> float:
        """
        计算时效性分数

        策略：
        - 最近1年: 100分
        - 1-2年: 90分
        - 2-3年: 80分
        - 3-5年: 70分
        - 5年以上: 60分
        - 无日期: 70分（中性）

        Args:
            result: 搜索结果字典

        Returns:
            时效性分数（0-100）
        """
        # 尝试从多个字段获取发布日期
        date_str = (
            result.get("published_date") or
            result.get("published") or
            result.get("updated") or
            result.get("last_updated")
        )

        if not date_str:
            return 70.0  # 无日期，返回中性分数

        try:
            # 解析日期（支持多种格式）
            if isinstance(date_str, str):
                # ISO格式
                pub_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                pub_date = date_str

            # 计算时间差
            now = datetime.now(pub_date.tzinfo) if pub_date.tzinfo else datetime.now()
            delta = now - pub_date
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
            else:
                return 60.0

        except Exception as e:
            logger.debug(f"⚠️ Failed to parse date '{date_str}': {e}")
            return 70.0  # 解析失败，返回中性分数


# ============================================================================
# 辅助函数：快速使用
# ============================================================================

def quick_quality_control(
    results: List[Dict[str, Any]],
    min_relevance: float = 0.6
) -> List[Dict[str, Any]]:
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
