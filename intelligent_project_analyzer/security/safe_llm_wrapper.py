"""
安全LLM包装器 - 监控所有LLM输出
"""

from typing import Any
from loguru import logger
from .content_safety_guard import ContentSafetyGuard
from .violation_logger import ViolationLogger


class SafeLLMWrapper:
    """安全LLM包装器 - 拦截并检测所有LLM输出"""
    
    def __init__(self, base_llm, safety_guard: ContentSafetyGuard = None):
        """
        初始化安全LLM包装器
        
        Args:
            base_llm: 基础LLM实例
            safety_guard: 内容安全守卫实例
        """
        self.base_llm = base_llm
        self.safety_guard = safety_guard or ContentSafetyGuard()
        self.violation_logger = ViolationLogger()
    
    def invoke(self, messages, **kwargs):
        """
        包装invoke方法，添加安全检测
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            LLM响应（可能已脱敏或替换）
        """
        try:
            # 调用原始LLM
            response = self.base_llm.invoke(messages, **kwargs)
            
            # 提取文本内容
            if hasattr(response, 'content'):
                text = response.content
            else:
                text = str(response)
            
            # 安全检测
            safety_result = self.safety_guard.check(text, context="output")
            
            if not safety_result["is_safe"]:
                logger.error(f"🚨 LLM输出违规: {safety_result['violations']}")
                
                # 记录违规
                self.violation_logger.log({
                    "violation_type": "llm_output_violation",
                    "details": safety_result["violations"],
                    "prompt": str(messages)[:200] if isinstance(messages, list) else str(messages)[:200],
                    "response": text[:200]
                })
                
                # 根据严重性决定处理方式
                if safety_result["risk_level"] == "high":
                    # 高风险：替换为安全内容
                    safe_response = self._generate_safe_fallback_response()
                    if hasattr(response, 'content'):
                        response.content = safe_response
                    else:
                        response = safe_response
                    logger.warning("⚠️ 已替换为安全内容")
                else:
                    # 中低风险：尝试脱敏
                    if "sanitized_text" in safety_result:
                        if hasattr(response, 'content'):
                            response.content = safety_result["sanitized_text"]
                        else:
                            response = safety_result["sanitized_text"]
                        logger.info("✅ 已完成内容脱敏")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ SafeLLMWrapper异常: {e}")
            # 出错时返回原始响应，避免阻断流程
            return self.base_llm.invoke(messages, **kwargs)
    
    def _generate_safe_fallback_response(self) -> str:
        """生成安全的兜底响应"""
        return """抱歉，我在生成回答时遇到了一些问题。让我重新为您分析这个空间设计项目。

作为空间设计专家，我建议我们专注于以下几个方面：

1. **空间功能布局优化**
   - 分析空间使用需求
   - 规划功能分区
   - 优化动线设计

2. **用户体验设计**
   - 提升空间舒适度
   - 营造良好氛围
   - 考虑人性化细节

3. **材料与色彩搭配**
   - 选择合适的材质
   - 协调色彩方案
   - 统一设计风格

4. **照明与氛围营造**
   - 合理的照明设计
   - 营造空间氛围
   - 节能环保考虑

请问您希望我重点分析哪个方面？或者您可以补充更多项目信息，我将为您提供更专业的设计建议。"""
    
    # 转发其他方法到base_llm
    def __getattr__(self, name):
        """转发未定义的方法到base_llm"""
        return getattr(self.base_llm, name)


def create_safe_llm(base_llm, safety_guard: ContentSafetyGuard = None):
    """
    工厂方法：创建安全LLM实例
    
    Args:
        base_llm: 基础LLM实例
        safety_guard: 内容安全守卫（可选）
        
    Returns:
        SafeLLMWrapper实例
    """
    return SafeLLMWrapper(base_llm, safety_guard)
