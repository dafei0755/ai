"""
报告生成模块

实现PDF报告生成、结果聚合等功能
"""

__all__ = [
    "ResultAggregatorAgent",
    "PDFGeneratorAgent"
]


def __getattr__(name):
    if name == "ResultAggregatorAgent":
        from .result_aggregator import ResultAggregatorAgent  # 延迟导入避免循环依赖
        return ResultAggregatorAgent
    if name == "PDFGeneratorAgent":
        from .pdf_generator import PDFGeneratorAgent  # 延迟导入避免循环依赖
        return PDFGeneratorAgent
    raise AttributeError(f"module 'intelligent_project_analyzer.report' has no attribute {name!r}")
