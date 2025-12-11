"""
智能体模块

包含所有智能体的实现：需求分析师、项目总监、专业分析智能体等
"""

from .base import BaseAgent, LLMAgent, ToolAgent, HybridAgent, AgentFactory

__all__ = [
    "BaseAgent",
    "LLMAgent",
    "ToolAgent",
    "HybridAgent",
    "AgentFactory",
    "RequirementsAnalystAgent",
    "ProjectDirectorAgent"
]


def __getattr__(name):
    if name == "RequirementsAnalystAgent":
        from .requirements_analyst import RequirementsAnalystAgent
        return RequirementsAnalystAgent
    if name == "ProjectDirectorAgent":
        from .project_director import ProjectDirectorAgent
        return ProjectDirectorAgent
    raise AttributeError(f"module 'intelligent_project_analyzer.agents' has no attribute {name!r}")
