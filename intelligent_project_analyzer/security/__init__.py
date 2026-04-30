"""
安全模块 - 内容安全与领域过滤

提供多层防护机制：
1. 输入预检：内容安全 + 领域分类
2. 领域验证：深度检查需求
3. 输出监控：实时拦截LLM输出
4. 报告审核：最终交付前审核
"""

from .content_safety_guard import ContentSafetyGuard
from .domain_classifier import DomainClassifier
from .safe_llm_wrapper import SafeLLMWrapper, create_safe_llm
from .violation_logger import ViolationLogger

# 延迟导入节点（避免循环导入）
def __getattr__(name):
    if name == "InputGuardNode":
        from .input_guard_node import InputGuardNode
        return InputGuardNode
    elif name == "InputRejectedNode":
        from .input_guard_node import InputRejectedNode
        return InputRejectedNode
    elif name == "DomainValidatorNode":
        from .domain_validator_node import DomainValidatorNode
        return DomainValidatorNode
    elif name == "ReportGuardNode":
        from .report_guard_node import ReportGuardNode
        return ReportGuardNode
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "ContentSafetyGuard",
    "DomainClassifier",
    "SafeLLMWrapper",
    "create_safe_llm",
    "ViolationLogger",
    "InputGuardNode",
    "InputRejectedNode",
    "DomainValidatorNode",
    "ReportGuardNode"
]
