"""
services/llm — LLM 基础设施子包

收录 LLM 工厂、并发控制、熔断器、缓存、Key 负载均衡等组件。

快捷导入示例：
    from intelligent_project_analyzer.services.llm import LLMFactory, get_breaker
    from intelligent_project_analyzer.services.llm import CircuitBreaker, CircuitState
"""

# ── Circuit Breaker (LT-4) ──────────────────────────────────────────────────
from intelligent_project_analyzer.services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    get_breaker,
)
from intelligent_project_analyzer.services.circuit_breaker import (
    all_stats as circuit_breaker_all_stats,
)
from intelligent_project_analyzer.services.circuit_breaker import (
    reset_registry as reset_circuit_registry,
)

# ── LLM 工厂 ────────────────────────────────────────────────────────────────
from intelligent_project_analyzer.services.llm_factory import LLMFactory

try:
    from intelligent_project_analyzer.services.multi_llm_factory import (
        FallbackLLM,
        MultiLLMFactory,
    )
except Exception:  # pragma: no cover – optional heavy deps
    MultiLLMFactory = None  # type: ignore[assignment,misc]
    FallbackLLM = None  # type: ignore[assignment,misc]

# ── 并发控制（QW-2 Semaphore）────────────────────────────────────────────────
from intelligent_project_analyzer.services.llm_concurrency import (
    get_llm_semaphore,
    get_llm_stats,
    reset_semaphore,
)

# ── 限流 ────────────────────────────────────────────────────────────────────
from intelligent_project_analyzer.services.rate_limiter import (
    rate_limit_manager,
)

try:
    from intelligent_project_analyzer.services.rate_limited_llm import (
        RateLimitedLLM,
        create_rate_limited_llm,
    )
except Exception:  # pragma: no cover
    RateLimitedLLM = None  # type: ignore[assignment,misc]
    create_rate_limited_llm = None  # type: ignore[assignment]

# ── Key 负载均衡 ──────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.key_balancer import (
        APIKeyPool,
        MultiKeyLoadBalancer,
        get_api_key,
    )
except Exception:  # pragma: no cover
    APIKeyPool = None  # type: ignore[assignment,misc]
    MultiKeyLoadBalancer = None  # type: ignore[assignment,misc]
    get_api_key = None  # type: ignore[assignment]

# ── OpenRouter 负载均衡 ───────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.openrouter_load_balancer import (
        LoadBalancerConfig,
        OpenRouterLoadBalancer,
        get_global_balancer,
    )
except Exception:  # pragma: no cover
    LoadBalancerConfig = None  # type: ignore[assignment,misc]
    OpenRouterLoadBalancer = None  # type: ignore[assignment,misc]
    get_global_balancer = None  # type: ignore[assignment]

# ── 语义缓存 ──────────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.semantic_cache import (
        SemanticCache,
        get_semantic_cache,
    )
except Exception:  # pragma: no cover
    SemanticCache = None  # type: ignore[assignment,misc]
    get_semantic_cache = None  # type: ignore[assignment]

# ── LLM 包装器（缓存加速）────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.cached_llm_wrapper import (
        CachedLLMWrapper,
        wrap_llm_with_cache,
    )
except Exception:  # pragma: no cover
    CachedLLMWrapper = None  # type: ignore[assignment,misc]
    wrap_llm_with_cache = None  # type: ignore[assignment]

# ── 高并发 LLM ────────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.high_concurrency_llm import (
        HighConcurrencyLLM,
        get_high_concurrency_llm,
    )
except Exception:  # pragma: no cover
    HighConcurrencyLLM = None  # type: ignore[assignment,misc]
    get_high_concurrency_llm = None  # type: ignore[assignment]

__all__ = [
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "CircuitState",
    "get_breaker",
    "reset_circuit_registry",
    "circuit_breaker_all_stats",
    # 工厂
    "LLMFactory",
    "MultiLLMFactory",
    "FallbackLLM",
    # 并发 & 限流
    "get_llm_semaphore",
    "get_llm_stats",
    "reset_semaphore",
    "rate_limit_manager",
    "RateLimitedLLM",
    "create_rate_limited_llm",
    # Key & 负载均衡
    "APIKeyPool",
    "MultiKeyLoadBalancer",
    "get_api_key",
    "LoadBalancerConfig",
    "OpenRouterLoadBalancer",
    "get_global_balancer",
    # 缓存
    "SemanticCache",
    "get_semantic_cache",
    "CachedLLMWrapper",
    "wrap_llm_with_cache",
    # 高并发
    "HighConcurrencyLLM",
    "get_high_concurrency_llm",
]
