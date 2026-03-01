"""
工具函数模块

限流、代理、重试等工具。
"""

from .data_processing import DataCleaner, DataValidator, AutoTagger
from .search_service import SemanticSearchService, RecommendationEngine
from .rate_limiter import (
    RateLimiter,
    UserAgentRotator,
    ProxyPool,
    AntiBlocker,
    CrawlProfile,
    CrawlProfileConfig,
    CRAWL_PROFILES,
    SOURCE_PROFILE_MAP,
    get_rate_limiter,
    get_profile,
    get_profile_by_name,
)
from .lang_utils import (
    detect_lang,
    is_chinese_dominant,
    split_bilingual_paragraphs,
    split_bilingual_title,
)

__all__ = [
    "DataCleaner",
    "DataValidator",
    "AutoTagger",
    "SemanticSearchService",
    "RecommendationEngine",
    "RateLimiter",
    "UserAgentRotator",
    "ProxyPool",
    "AntiBlocker",
    "CrawlProfile",
    "CrawlProfileConfig",
    "CRAWL_PROFILES",
    "SOURCE_PROFILE_MAP",
    "get_rate_limiter",
    "get_profile",
    "get_profile_by_name",
    # 语言工具
    "detect_lang",
    "is_chinese_dominant",
    "split_bilingual_paragraphs",
    "split_bilingual_title",
]
