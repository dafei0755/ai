"""
LangGraph运行时上下文 - 2025年Runtime Context模式

提供动态配置支持,无需全局状态
"""

from typing_extensions import TypedDict
from typing import Optional, Dict, Any
from loguru import logger

from intelligent_project_analyzer.settings import settings


class GraphContext(TypedDict):
    """
    LangGraph运行时上下文 - 2025年模式
    
    用于在graph运行时传递配置,支持:
    - 动态配置
    - 多租户场景
    - A/B测试
    - 无全局状态污染
    """
    # LLM配置
    llm_model: str
    max_tokens: int
    temperature: float
    timeout: int
    
    # 运行时配置
    debug: bool
    session_id: str
    
    # 可选的用户配置
    user_id: Optional[str]
    metadata: Optional[Dict[str, Any]]


def get_default_context(
    session_id: str,
    user_id: Optional[str] = None,
    **overrides
) -> GraphContext:
    """
    获取默认运行时上下文
    
    Args:
        session_id: 会话ID
        user_id: 用户ID (可选)
        **overrides: 覆盖默认配置的参数
        
    Returns:
        GraphContext字典
        
    Example:
        # 使用默认配置
        context = get_default_context(session_id="abc123")
        
        # 覆盖特定参数
        context = get_default_context(
            session_id="abc123",
            llm_model="gpt-4",
            max_tokens=8000
        )
    """
    context: GraphContext = {
        # 从全局settings读取默认值
        "llm_model": settings.llm.model,
        "max_tokens": settings.llm.max_tokens,
        "temperature": settings.llm.temperature,
        "timeout": settings.llm.timeout,
        
        # 运行时配置
        "debug": settings.debug,
        "session_id": session_id,
        
        # 可选配置
        "user_id": user_id,
        "metadata": {}
    }
    
    # 应用覆盖参数
    context.update(overrides)
    
    logger.info(f"创建Graph上下文: session={session_id}, model={context['llm_model']}")
    
    return context


def create_context_for_testing(
    session_id: str = "test-session",
    **overrides
) -> GraphContext:
    """
    创建测试用的上下文
    
    Args:
        session_id: 测试会话ID
        **overrides: 覆盖参数
        
    Returns:
        测试用的GraphContext
    """
    test_context = get_default_context(
        session_id=session_id,
        debug=True,
        **overrides
    )
    
    logger.info(f"创建测试上下文: {session_id}")
    
    return test_context


def create_context_for_user(
    user_id: str,
    session_id: str,
    preferences: Optional[Dict[str, Any]] = None
) -> GraphContext:
    """
    为特定用户创建上下文
    
    Args:
        user_id: 用户ID
        session_id: 会话ID
        preferences: 用户偏好设置
        
    Returns:
        用户专属的GraphContext
        
    Example:
        context = create_context_for_user(
            user_id="user123",
            session_id="session456",
            preferences={
                "llm_model": "gpt-4",
                "max_tokens": 8000
            }
        )
    """
    overrides = preferences or {}
    
    context = get_default_context(
        session_id=session_id,
        user_id=user_id,
        **overrides
    )
    
    # 添加用户元数据
    context["metadata"] = {
        "user_id": user_id,
        "preferences": preferences
    }
    
    logger.info(f"创建用户上下文: user={user_id}, session={session_id}")
    
    return context


def validate_context(context: GraphContext) -> bool:
    """
    验证上下文配置
    
    Args:
        context: 要验证的上下文
        
    Returns:
        上下文是否有效
    """
    required_fields = ["llm_model", "max_tokens", "session_id"]
    
    for field in required_fields:
        if field not in context:
            logger.error(f"上下文缺少必需字段: {field}")
            return False
    
    if context["max_tokens"] < 100:
        logger.warning(f"max_tokens过小: {context['max_tokens']}")
    
    logger.info("上下文验证通过")
    return True

