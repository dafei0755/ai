"""
LLM重试机制工具模块

提供通用的LLM调用重试装饰器和函数，支持：
- 指数退避策略
- 可配置的重试次数和超时时间
- 详细的错误日志
- 只对可重试的错误进行重试（网络错误、超时等）

作者：Design Beyond Team
日期：2026-01-04
版本：v7.131
"""

import asyncio
import functools
from typing import Any, Callable, TypeVar, Union

import httpcore
import openai
from loguru import logger
from tenacity import (
    AsyncRetrying,
    RetryError,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# 定义可重试的异常类型
RETRIABLE_EXCEPTIONS = (
    httpcore.ConnectError,
    httpcore.ConnectTimeout,
    httpcore.ReadTimeout,
    httpcore.WriteTimeout,
    httpcore.PoolTimeout,
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.RateLimitError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
)

# 类型变量
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


class LLMRetryConfig:
    """LLM重试配置"""

    def __init__(
        self,
        max_attempts: int = 3,
        min_wait: float = 1.0,
        max_wait: float = 10.0,
        multiplier: float = 2.0,
        timeout: float | None = 30.0,
    ):
        """
        初始化重试配置

        Args:
            max_attempts: 最大重试次数（包含首次尝试）
            min_wait: 最小等待时间（秒）
            max_wait: 最大等待时间（秒）
            multiplier: 指数退避乘数
            timeout: 单次调用超时时间（秒），None表示不设置超时
        """
        self.max_attempts = max_attempts
        self.min_wait = min_wait
        self.max_wait = max_wait
        self.multiplier = multiplier
        self.timeout = timeout


# 默认配置
DEFAULT_RETRY_CONFIG = LLMRetryConfig()


def _log_retry_attempt(retry_state) -> None:
    """记录重试尝试"""
    attempt_number = retry_state.attempt_number
    if attempt_number > 1:
        exception = retry_state.outcome.exception() if retry_state.outcome else None
        wait_time = retry_state.next_action.sleep if retry_state.next_action else 0
        logger.warning(
            f" [LLM重试] 第 {attempt_number - 1} 次重试 | "
            f"错误: {type(exception).__name__ if exception else 'Unknown'} | "
            f"等待 {wait_time:.1f}s"
        )


def _log_final_failure(retry_state) -> None:
    """记录最终失败"""
    exception = retry_state.outcome.exception() if retry_state.outcome else None
    logger.error(
        f" [LLM重试] 达到最大重试次数 {retry_state.attempt_number} | "
        f"最终错误: {type(exception).__name__ if exception else 'Unknown'}: {exception}"
    )


def invoke_llm_with_retry(
    llm: Any,
    messages: Union[list, str],
    config: LLMRetryConfig | None = None,
    **kwargs,
) -> Any:
    """
    同步调用LLM（带重试机制）

    Args:
        llm: LLM实例
        messages: 消息列表或字符串
        config: 重试配置
        **kwargs: 传递给LLM的额外参数

    Returns:
        LLM响应

    Example:
        >>> from intelligent_project_analyzer.services.llm_factory import LLMFactory
        >>> llm = LLMFactory.create_llm()
        >>> response = invoke_llm_with_retry(llm, "Hello, world!")
    """
    cfg = config or DEFAULT_RETRY_CONFIG

    # 创建重试器
    retryer = Retrying(
        stop=stop_after_attempt(cfg.max_attempts),
        wait=wait_exponential(multiplier=cfg.multiplier, min=cfg.min_wait, max=cfg.max_wait),
        retry=retry_if_exception_type(RETRIABLE_EXCEPTIONS),
        before_sleep=_log_retry_attempt,
        reraise=True,
    )

    try:
        logger.debug(f" [LLM调用] 开始同步调用 | 最大尝试次数: {cfg.max_attempts}")

        for attempt in retryer:
            with attempt:
                if cfg.timeout:
                    # 使用线程池执行器实现超时
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(llm.invoke, messages, **kwargs)
                        try:
                            response = future.result(timeout=cfg.timeout)
                        except concurrent.futures.TimeoutError:
                            raise TimeoutError(f"LLM调用超时 ({cfg.timeout}s)")
                else:
                    response = llm.invoke(messages, **kwargs)

                logger.debug(f" [LLM调用] 成功 | 尝试次数: {attempt.retry_state.attempt_number}")
                return response

    except RetryError as e:
        _log_final_failure(e.last_attempt)
        raise e.last_attempt.exception()
    except Exception as e:
        logger.error(f" [LLM调用] 未预期错误: {type(e).__name__}: {e}")
        raise


async def ainvoke_llm_with_retry(
    llm: Any,
    messages: Union[list, str],
    config: LLMRetryConfig | None = None,
    **kwargs,
) -> Any:
    """
    异步调用LLM（带重试机制）

    Args:
        llm: LLM实例
        messages: 消息列表或字符串
        config: 重试配置
        **kwargs: 传递给LLM的额外参数

    Returns:
        LLM响应

    Example:
        >>> from intelligent_project_analyzer.services.llm_factory import LLMFactory
        >>> llm = LLMFactory.create_llm()
        >>> response = await ainvoke_llm_with_retry(llm, "Hello, world!")
    """
    cfg = config or DEFAULT_RETRY_CONFIG

    # 创建异步重试器
    retryer = AsyncRetrying(
        stop=stop_after_attempt(cfg.max_attempts),
        wait=wait_exponential(multiplier=cfg.multiplier, min=cfg.min_wait, max=cfg.max_wait),
        retry=retry_if_exception_type(RETRIABLE_EXCEPTIONS),
        before_sleep=_log_retry_attempt,
        reraise=True,
    )

    try:
        logger.debug(f" [LLM调用] 开始异步调用 | 最大尝试次数: {cfg.max_attempts}")

        async for attempt in retryer:
            with attempt:
                if cfg.timeout:
                    response = await asyncio.wait_for(llm.ainvoke(messages, **kwargs), timeout=cfg.timeout)
                else:
                    response = await llm.ainvoke(messages, **kwargs)

                logger.debug(f" [LLM调用] 成功 | 尝试次数: {attempt.retry_state.attempt_number}")
                return response

    except RetryError as e:
        _log_final_failure(e.last_attempt)
        raise e.last_attempt.exception()
    except Exception as e:
        logger.error(f" [LLM调用] 未预期错误: {type(e).__name__}: {e}")
        raise


def llm_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    multiplier: float = 2.0,
    timeout: float | None = 30.0,
) -> Callable[[F], F]:
    """
    LLM重试装饰器（同步函数）

    Args:
        max_attempts: 最大重试次数
        min_wait: 最小等待时间（秒）
        max_wait: 最大等待时间（秒）
        multiplier: 指数退避乘数
        timeout: 单次调用超时时间（秒）

    Example:
        >>> @llm_retry(max_attempts=3, timeout=30)
        ... def call_llm():
        ...     return llm.invoke("Hello")
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retryer = Retrying(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait),
                retry=retry_if_exception_type(RETRIABLE_EXCEPTIONS),
                before_sleep=_log_retry_attempt,
                reraise=True,
            )

            try:
                for attempt in retryer:
                    with attempt:
                        if timeout:
                            import concurrent.futures

                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(func, *args, **kwargs)
                                try:
                                    result = future.result(timeout=timeout)
                                except concurrent.futures.TimeoutError:
                                    raise TimeoutError(f"函数调用超时 ({timeout}s)")
                        else:
                            result = func(*args, **kwargs)

                        return result

            except RetryError as e:
                _log_final_failure(e.last_attempt)
                raise e.last_attempt.exception()

        return wrapper  # type: ignore

    return decorator


def async_llm_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    multiplier: float = 2.0,
    timeout: float | None = 30.0,
) -> Callable[[F], F]:
    """
    LLM重试装饰器（异步函数）

    Args:
        max_attempts: 最大重试次数
        min_wait: 最小等待时间（秒）
        max_wait: 最大等待时间（秒）
        multiplier: 指数退避乘数
        timeout: 单次调用超时时间（秒）

    Example:
        >>> @async_llm_retry(max_attempts=3, timeout=30)
        ... async def call_llm():
        ...     return await llm.ainvoke("Hello")
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            retryer = AsyncRetrying(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait),
                retry=retry_if_exception_type(RETRIABLE_EXCEPTIONS),
                before_sleep=_log_retry_attempt,
                reraise=True,
            )

            try:
                async for attempt in retryer:
                    with attempt:
                        if timeout:
                            result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                        else:
                            result = await func(*args, **kwargs)

                        return result

            except RetryError as e:
                _log_final_failure(e.last_attempt)
                raise e.last_attempt.exception()

        return wrapper  # type: ignore

    return decorator


# 导出主要接口
__all__ = [
    "LLMRetryConfig",
    "DEFAULT_RETRY_CONFIG",
    "invoke_llm_with_retry",
    "ainvoke_llm_with_retry",
    "llm_retry",
    "async_llm_retry",
    "RETRIABLE_EXCEPTIONS",
]
