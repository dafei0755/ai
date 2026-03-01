"""
翻译模块

提供项目内容的多语言翻译功能
"""

from .translator import ProjectTranslator, get_translator

__all__ = [
    "ProjectTranslator",
    "get_translator",
]
