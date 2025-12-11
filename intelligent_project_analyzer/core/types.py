"""
核心类型定义

定义系统中使用的数据类型和接口
"""

from typing import Dict, List, Optional, Any, Protocol, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore

from .state import ProjectAnalysisState, AgentType


class AnalysisResult:
    """分析结果基类"""
    
    def __init__(
        self,
        agent_type: AgentType,
        content: str,
        structured_data: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        sources: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.agent_type = agent_type
        self.content = content
        self.structured_data = structured_data or {}
        self.confidence = confidence
        self.sources = sources or []
        self.metadata = metadata or {}
        self.timestamp = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "agent_type": self.agent_type.value,
            "content": self.content,
            "structured_data": self.structured_data,
            "confidence": self.confidence,
            "sources": self.sources,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


@dataclass
class TaskAssignment:
    """任务分派"""
    agent_type: AgentType
    task_description: str
    priority: int = 1
    dependencies: List[AgentType] = None
    estimated_duration: Optional[int] = None  # 预估时间（秒）
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class ToolConfig:
    """工具配置"""
    name: str
    enabled: bool = True
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}


class AgentInterface(Protocol):
    """智能体接口"""
    
    def execute(
        self,
        state: ProjectAnalysisState,
        config: RunnableConfig,
        store: Optional[BaseStore] = None
    ) -> AnalysisResult:
        """执行智能体任务"""
        ...
    
    def validate_input(self, state: ProjectAnalysisState) -> bool:
        """验证输入是否有效"""
        ...
    
    def get_dependencies(self) -> List[AgentType]:
        """获取依赖的智能体"""
        ...


class ToolInterface(Protocol):
    """工具接口"""
    
    def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """搜索功能"""
        ...
    
    def is_available(self) -> bool:
        """检查工具是否可用"""
        ...


class InteractionType(Enum):
    """交互类型"""
    CONFIRMATION = "confirmation"
    REVIEW = "review"
    CLARIFICATION = "clarification"
    APPROVAL = "approval"
    FEEDBACK = "feedback"
    FINAL_REVIEW = "final_review"  # 最终报告审核
    QUESTION = "question"  # 用户提问


@dataclass
class InteractionRequest:
    """交互请求"""
    interaction_type: InteractionType
    message: str
    data: Dict[str, Any]
    timeout: Optional[int] = None
    required: bool = True


@dataclass
class InteractionResponse:
    """交互响应"""
    approved: bool
    feedback: Optional[str] = None
    modifications: Optional[Dict[str, Any]] = None
    action: Optional[str] = None


class ReportSection(Enum):
    """报告章节"""
    EXECUTIVE_SUMMARY = "executive_summary"
    REQUIREMENTS_ANALYSIS = "requirements_analysis"
    DESIGN_RESEARCH = "design_research"
    TECHNICAL_ARCHITECTURE = "technical_architecture"
    UX_DESIGN = "ux_design"
    BUSINESS_MODEL = "business_model"
    IMPLEMENTATION_PLAN = "implementation_plan"
    CONCLUSIONS = "conclusions"
    APPENDICES = "appendices"


@dataclass
class ReportContent:
    """报告内容"""
    section: ReportSection
    title: str
    content: str
    charts: Optional[List[Dict[str, Any]]] = None
    tables: Optional[List[Dict[str, Any]]] = None
    images: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.charts is None:
            self.charts = []
        if self.tables is None:
            self.tables = []
        if self.images is None:
            self.images = []


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dict: Dict[str, Any]):
        self._config = config_dict
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_llm_config(self) -> Dict[str, Any]:
        """获取LLM配置"""
        return {
            "model": self.get("llm.model", "gpt-4o-mini"),
            "temperature": self.get("llm.temperature", 0.7),
            "max_tokens": self.get("llm.max_tokens", 4000),
            "timeout": self.get("llm.timeout", 60)
        }
    
    def get_tool_config(self, tool_name: str) -> ToolConfig:
        """获取工具配置"""
        tool_config = self.get(f"tools.{tool_name}", {})
        return ToolConfig(
            name=tool_name,
            enabled=tool_config.get("enabled", True),
            api_key=tool_config.get("api_key"),
            endpoint=tool_config.get("endpoint"),
            timeout=tool_config.get("timeout", 30),
            max_retries=tool_config.get("max_retries", 3),
            config=tool_config.get("config", {})
        )


class ErrorType(Enum):
    """错误类型"""
    VALIDATION_ERROR = "validation_error"
    API_ERROR = "api_error"
    TIMEOUT_ERROR = "timeout_error"
    CONFIGURATION_ERROR = "configuration_error"
    AGENT_ERROR = "agent_error"
    TOOL_ERROR = "tool_error"
    SYSTEM_ERROR = "system_error"


@dataclass
class SystemError:
    """系统错误"""
    error_type: ErrorType
    message: str
    details: Optional[Dict[str, Any]] = None
    agent_type: Optional[AgentType] = None
    recoverable: bool = True
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


# ==================== 显示格式化工具函数 ====================

def format_role_display_name(full_role_id: str, dynamic_name: str = None) -> str:
    """
    将完整角色ID转换为简洁显示格式
    
    Args:
        full_role_id: 完整角色ID，如 "V4_设计研究员_4-1"
        dynamic_name: 动态角色名称（可选），如 "家庭生活方式研究员"
    
    Returns:
        简洁显示格式，如 "4-1 家庭生活方式研究员" 或 "4-1 设计研究员"
    
    Examples:
        >>> format_role_display_name("V4_设计研究员_4-1")
        "4-1 设计研究员"
        >>> format_role_display_name("V4_设计研究员_4-1", "家庭生活方式研究员")
        "4-1 家庭生活方式研究员"
        >>> format_role_display_name("V3_叙事与体验专家_3-1", "别墅居住体验设计师")
        "3-1 别墅居住体验设计师"
    """
    if not full_role_id:
        return full_role_id
    
    parts = full_role_id.split('_')
    if len(parts) >= 3:
        suffix = parts[-1]  # "4-1"
        static_name = parts[1]  # "设计研究员"
        display_name = dynamic_name or static_name
        return f"{suffix} {display_name}"
    elif len(parts) == 2:
        # 格式如 "V4_4-1"
        suffix = parts[-1]
        return suffix
    
    return full_role_id
