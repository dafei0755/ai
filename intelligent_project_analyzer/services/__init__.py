"""
服务层模块 - 2025年Service Layer Architecture

提供工厂模式和依赖注入支持

注意：LLMFactory / ToolFactory 不在此处预导入，避免 import 链触发
langchain_openai（Python 3.14 下耗时 5+ 秒）拖慢服务器启动。
需要时请在使用处直接 from .llm_factory import LLMFactory 导入。
"""

__all__ = ["LLMFactory", "ToolFactory"]

