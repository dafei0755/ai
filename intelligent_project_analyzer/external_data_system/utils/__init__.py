"""
工具函数模块

限流、代理、重试等工具。
"""

from .data_processing import AutoTagger, DataCleaner, DataValidator
from .lang_utils import (
    detect_lang,
    is_chinese_dominant,
    split_bilingual_paragraphs,
    split_bilingual_title,
)
from .rate_limiter import (
    CRAWL_PROFILES,
    SOURCE_PROFILE_MAP,
    AntiBlocker,
    CrawlProfile,
    CrawlProfileConfig,
    ProxyPool,
    RateLimiter,
    UserAgentRotator,
    get_profile,
    get_profile_by_name,
    get_rate_limiter,
)
from .search_service import RecommendationEngine, SemanticSearchService

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
