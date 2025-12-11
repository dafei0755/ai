"""
基础智能体框架

定义可扩展的智能体基类和通用功能
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from loguru import logger

from ..core.state import ProjectAnalysisState, AgentType
from ..core.types import AnalysisResult, SystemError, ErrorType


class NullLLM:
    """占位LLM，当未配置真实模型时提供友好提示。"""

    def __init__(self, owner: str):
        self.owner = owner

    def _raise(self, method: str) -> None:
        raise RuntimeError(
            f"{self.owner} 需要配置 llm_model 才能调用 {method}。"
            " 请在运行完整工作流前提供有效的 LLM 实例。"
        )

    def invoke(self, *args, **kwargs):
        self._raise("invoke")

    def with_structured_output(self, *args, **kwargs):
        self._raise("with_structured_output")

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        return f"NullLLM(owner={self.owner!r})"


class BaseAgent(ABC):
    """智能体基类"""
    
    def __init__(
        self,
        agent_type: AgentType,
        name: str,
        description: str,
        llm_model: Optional[Any] = None,
        tools: Optional[List[Any]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.agent_type = agent_type
        self.name = name
        self.description = description
        self.llm_model = llm_model
        self.tools = tools or []
        self.config = config or {}
        
        # 性能监控
        self.execution_count = 0
        self.total_execution_time = 0.0
        self.last_execution_time = None
        
        logger.info(f"Initialized agent: {self.name} ({self.agent_type.value})")
    
    @abstractmethod
    def execute(
        self,
        state: ProjectAnalysisState,
        config: RunnableConfig,
        store: Optional[BaseStore] = None
    ) -> AnalysisResult:
        """执行智能体任务"""
        pass
    
    @abstractmethod
    def validate_input(self, state: ProjectAnalysisState) -> bool:
        """验证输入是否有效"""
        pass
    
    def get_dependencies(self) -> List[AgentType]:
        """获取依赖的智能体（默认无依赖）"""
        return []
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return f"""你是{self.name}，专门负责{self.description}。
        
请根据提供的项目需求进行专业分析，并提供详细、可操作的建议。

分析要求：
1. 深入理解项目需求和背景
2. 提供专业、准确的分析结果
3. 给出具体、可执行的建议
4. 考虑实际可行性和成本效益
5. 结构化输出，便于后续处理

请确保分析结果的专业性和实用性。"""
    
    def prepare_context(self, state: ProjectAnalysisState) -> str:
        """准备上下文信息"""
        context_parts = []
        
        # 用户需求
        if state.get("user_input"):
            context_parts.append(f"用户原始需求：\n{state['user_input']}")
        
        # 结构化需求
        if state.get("structured_requirements"):
            context_parts.append(f"结构化需求：\n{state['structured_requirements']}")
        
        # 战略分析
        if state.get("strategic_analysis"):
            context_parts.append(f"战略分析：\n{state['strategic_analysis']}")
        
        # 其他智能体的结果（如果有依赖）
        dependencies = self.get_dependencies()
        for dep in dependencies:
            result_key = f"{dep.value.lower()}_result"
            if state.get(result_key):
                context_parts.append(f"{dep.value}分析结果：\n{state[result_key]}")
        
        return "\n\n".join(context_parts)
    
    def get_review_feedback_for_agent(self, state: ProjectAnalysisState) -> Optional[Dict[str, Any]]:
        """
        🆕 获取针对当前专家的审核反馈
        
        Args:
            state: 项目状态
            
        Returns:
            针对当前专家的反馈，如果没有则返回None
        """
        review_feedback = state.get("review_feedback")
        if not review_feedback:
            return None
        
        feedback_by_agent = review_feedback.get("feedback_by_agent", {})
        agent_feedback = feedback_by_agent.get(self.agent_type.value)
        
        return agent_feedback
    
    def build_retry_prompt_suffix(self, review_feedback: Dict[str, Any], retry_round: int) -> str:
        """
        🆕 构建重试时的prompt后缀
        
        Args:
            review_feedback: 审核反馈
            retry_round: 重试轮次
            
        Returns:
            追加的prompt内容
        """
        if not review_feedback:
            return ""
        
        issues = review_feedback.get("issues", [])
        suggestions = review_feedback.get("suggestions", [])
        current_conf = review_feedback.get("current_confidence", 0)
        target_conf = review_feedback.get("target_confidence", 0.8)
        
        suffix = f"""

==========================================
⚠️ 这是第 {retry_round} 次分析
==========================================

📋 上一轮分析存在以下问题：
"""
        for i, issue in enumerate(issues, 1):
            suffix += f"\n{i}. {issue}"
        
        suffix += f"""

💡 改进建议：
"""
        for i, suggestion in enumerate(suggestions, 1):
            suffix += f"\n{i}. {suggestion}"
        
        suffix += f"""

📊 质量目标：
- 当前置信度: {current_conf:.0%}
- 目标置信度: {target_conf:.0%}
- 需要提升: {(target_conf - current_conf):.0%}

🎯 本次分析要求：
1. **重点针对上述问题逐一解决**
2. **补充缺失的分析内容和数据支持**
3. **提供更详细、更专业的分析**
4. **确保分析质量显著提升**

请根据以上反馈进行深度改进，提供更高质量的分析结果。
"""
        
        return suffix
    
    def create_analysis_result(
        self,
        content: str,
        structured_data: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        sources: Optional[List[str]] = None
    ) -> AnalysisResult:
        """创建分析结果"""
        result = AnalysisResult(
            agent_type=self.agent_type,
            content=content,
            structured_data=structured_data,
            confidence=confidence,
            sources=sources,
            metadata={
                "agent_name": self.name,
                "execution_time": self.last_execution_time,
                "timestamp": datetime.now().isoformat()
            }
        )
        result.timestamp = datetime.now().isoformat()
        return result
    
    def handle_error(self, error: Exception, context: str = "") -> Exception:
        """
        处理错误

        记录错误信息并返回一个可以被 raise 的异常对象
        """
        error_message = f"{self.name} execution failed: {str(error)}"
        if context:
            error_message += f" Context: {context}"

        logger.error(error_message)

        # 创建 SystemError dataclass 用于记录（但不用于 raise）
        system_error = SystemError(
            error_type=ErrorType.AGENT_ERROR,
            message=error_message,
            details={
                "agent_type": self.agent_type.value,
                "agent_name": self.name,
                "exception_type": type(error).__name__,
                "context": context
            },
            agent_type=self.agent_type,
            recoverable=True
        )

        # 返回原始异常（可以被 raise）
        # 如果需要，可以创建一个新的 RuntimeError 包装原始异常
        if isinstance(error, Exception):
            return error
        else:
            return RuntimeError(error_message)
    
    def _track_execution_time(self, start_time: float, end_time: float):
        """跟踪执行时间"""
        execution_time = end_time - start_time
        self.execution_count += 1
        self.total_execution_time += execution_time
        self.last_execution_time = execution_time
        
        logger.info(
            f"{self.name} execution completed in {execution_time:.2f}s "
            f"(avg: {self.total_execution_time/self.execution_count:.2f}s)"
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            "agent_name": self.name,
            "agent_type": self.agent_type.value,
            "execution_count": self.execution_count,
            "total_execution_time": self.total_execution_time,
            "average_execution_time": (
                self.total_execution_time / self.execution_count 
                if self.execution_count > 0 else 0
            ),
            "last_execution_time": self.last_execution_time
        }


class LLMAgent(BaseAgent):
    """基于LLM的智能体基类"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if not self.llm_model:
            # 使用占位LLM，允许在测试中构造无模型的代理
            self.llm_model = NullLLM(self.name)
            self.config.setdefault("llm_placeholder", True)
    
    def invoke_llm(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> AIMessage:
        """
        调用LLM，带参数验证、重试机制和详细错误日志

        Args:
            messages: 消息列表
            **kwargs: 额外的LLM参数

        Returns:
            AIMessage: LLM响应

        Raises:
            Exception: LLM调用失败时抛出异常
        """
        import json
        import time

        try:
            # 合并配置 - 只提取invoke()方法支持的参数
            # 不要传递api_key, base_url等初始化参数
            llm_config = self.config.get("llm", {})
            llm_kwargs = {
                "max_tokens": llm_config.get("max_tokens", 4000),
                "temperature": llm_config.get("temperature", 0.7),
                **kwargs  # 允许调用者覆盖
            }

            # ✅ 参数验证: 确保 max_tokens >= 16 (GPT-4.1 要求)
            max_tokens = llm_kwargs.get("max_tokens", 4000)
            if max_tokens < 16:
                logger.warning(
                    f"[{self.name}] max_tokens ({max_tokens}) 小于 GPT-4.1 最小值 16, "
                    f"自动调整为 100"
                )
                llm_kwargs["max_tokens"] = 100

            # ✅ 重试机制: 最多重试 3 次
            max_retries = 3
            last_error = None

            for attempt in range(max_retries):
                try:
                    # 调用LLM
                    logger.debug(f"[{self.name}] LLM 调用 (尝试 {attempt + 1}/{max_retries})")
                    response = self.llm_model.invoke(messages, **llm_kwargs)

                    if not isinstance(response, AIMessage):
                        response = AIMessage(content=str(response))

                    logger.debug(f"[{self.name}] LLM 调用成功")
                    return response

                except json.JSONDecodeError as e:
                    # ✅ 详细错误日志: JSON 解析错误
                    last_error = e
                    logger.error(f"[{self.name}] JSON 解析错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                    logger.error(f"[{self.name}] OpenRouter 可能返回了 HTML 错误页面而非 JSON")
                    logger.error(f"[{self.name}] 常见原因:")
                    logger.error(f"[{self.name}]   1. max_tokens 参数小于 16 (GPT-4.1 要求)")
                    logger.error(f"[{self.name}]   2. 其他参数不符合模型要求")
                    logger.error(f"[{self.name}]   3. 模型暂时不可用或速率限制")

                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # 指数退避: 1s, 2s, 4s
                        logger.info(f"[{self.name}] 等待 {wait_time} 秒后重试...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"[{self.name}] 已达到最大重试次数，放弃")
                        raise

                except Exception as e:
                    # ✅ 详细错误日志: 其他错误
                    last_error = e
                    logger.error(f"[{self.name}] LLM 调用失败 (尝试 {attempt + 1}/{max_retries}): {type(e).__name__}: {e}")

                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.info(f"[{self.name}] 等待 {wait_time} 秒后重试...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"[{self.name}] 已达到最大重试次数，放弃")
                        raise

            # 如果所有重试都失败，抛出最后一个错误
            if last_error:
                raise last_error

        except Exception as e:
            logger.error(f"[{self.name}] LLM invocation failed: {str(e)}")
            raise
    
    def prepare_messages(
        self,
        state: ProjectAnalysisState,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> List[BaseMessage]:
        """
        准备LLM消息

        Args:
            state: 项目分析状态
            additional_context: 可选的额外上下文信息(如工具结果)

        Returns:
            消息列表
        """
        messages = []

        # 系统提示
        system_prompt = self.get_system_prompt()
        messages.append(HumanMessage(content=f"System: {system_prompt}"))

        # 上下文信息
        context = self.prepare_context(state)
        if context:
            messages.append(HumanMessage(content=f"Context: {context}"))

        # 额外上下文信息(如工具结果)
        if additional_context:
            context_str = self._format_additional_context(additional_context)
            if context_str:
                messages.append(HumanMessage(content=f"Additional Context: {context_str}"))

        # 具体任务
        task_description = self.get_task_description(state)
        messages.append(HumanMessage(content=f"Task: {task_description}"))

        return messages

    def _format_additional_context(self, context: Dict[str, Any]) -> str:
        """
        格式化额外上下文信息

        Args:
            context: 额外上下文字典

        Returns:
            格式化后的字符串
        """
        if not context:
            return ""

        formatted_parts = []
        for key, value in context.items():
            if isinstance(value, (list, dict)):
                import json
                value_str = json.dumps(value, ensure_ascii=False, indent=2)
            else:
                value_str = str(value)
            formatted_parts.append(f"{key}:\n{value_str}")

        return "\n\n".join(formatted_parts)
    
    @abstractmethod
    def get_task_description(self, state: ProjectAnalysisState) -> str:
        """获取具体任务描述"""
        pass


class ToolAgent(BaseAgent):
    """基于工具的智能体基类"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 不在这里检查工具，因为子类可能在super().__init__()之后才初始化工具
        # 工具检查应该在子类的__init__完成后进行
    
    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """执行工具"""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found in {self.name}")
        
        try:
            return tool.invoke(**kwargs)
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {str(e)}")
            raise
    
    def get_tool(self, tool_name: str) -> Optional[Any]:
        """获取工具"""
        for tool in self.tools:
            if hasattr(tool, 'name') and tool.name == tool_name:
                return tool
            elif hasattr(tool, '__name__') and tool.__name__ == tool_name:
                return tool
        return None
    
    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        tool_names = []
        for tool in self.tools:
            if hasattr(tool, 'name'):
                tool_names.append(tool.name)
            elif hasattr(tool, '__name__'):
                tool_names.append(tool.__name__)
        return tool_names


class HybridAgent(LLMAgent, ToolAgent):
    """混合智能体（同时使用LLM和工具）"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 验证LLM已配置
        if not self.llm_model:
            raise ValueError(f"LLM model is required for hybrid agent {self.name}")

        # 不在这里检查工具，因为子类可能在super().__init__()之后才初始化工具
        # 工具检查应该在子类的__init__完成后进行


class AgentFactory:
    """智能体工厂"""
    
    _agent_classes = {}
    
    @classmethod
    def register_agent(cls, agent_type: AgentType, agent_class: type):
        """注册智能体类"""
        cls._agent_classes[agent_type] = agent_class
    
    @classmethod
    def create_agent(
        cls,
        agent_type: AgentType,
        llm_model: Optional[Any] = None,
        tools: Optional[List[Any]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseAgent:
        """创建智能体实例"""
        if agent_type not in cls._agent_classes:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        agent_class = cls._agent_classes[agent_type]

        # 检查构造函数参数
        import inspect
        sig = inspect.signature(agent_class.__init__)
        params = list(sig.parameters.keys())

        # 构建参数字典
        kwargs = {}
        if 'llm_model' in params:
            kwargs['llm_model'] = llm_model
        if 'tools' in params:
            kwargs['tools'] = tools
        if 'config' in params:
            kwargs['config'] = config
        if 'agent_config' in params:
            kwargs['agent_config'] = config

        return agent_class(**kwargs)
    
    @classmethod
    def get_registered_agents(cls) -> List[AgentType]:
        """获取已注册的智能体类型"""
        return list(cls._agent_classes.keys())
