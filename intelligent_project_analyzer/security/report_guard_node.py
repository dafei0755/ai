"""
报告审核节点 - 最终输出内容安全检查
"""

from typing import Dict, Any, Optional
from loguru import logger
from langgraph.store.base import BaseStore

from intelligent_project_analyzer.core.state import ProjectAnalysisState
from intelligent_project_analyzer.security.content_safety_guard import ContentSafetyGuard
from intelligent_project_analyzer.security.violation_logger import ViolationLogger


class ReportGuardNode:
    """报告审核节点 - 最后一道防线"""
    
    @staticmethod
    def execute(
        state: ProjectAnalysisState,
        store: Optional[BaseStore] = None,
        llm_model = None
    ) -> Dict[str, Any]:
        """
        执行报告内容安全检查
        
        检查逻辑：
        1. 提取最终报告文本
        2. 内容安全检测
        3. 如有违规，替换/脱敏
        4. 记录审核日志
        
        Args:
            state: 项目分析状态
            store: 存储接口
            llm_model: LLM模型实例
            
        Returns:
            更新后的状态
        """
        logger.info("=" * 100)
        logger.info("🛡️ 报告审核：最终内容安全检查")
        logger.info("=" * 100)
        
        final_report = state.get("final_report", "")
        session_id = state.get("session_id", "")
        
        if not final_report:
            logger.warning("⚠️ 报告内容为空，跳过审核")
            return {}
        
        # 初始化检测器
        safety_guard = ContentSafetyGuard(llm_model=llm_model)
        violation_logger = ViolationLogger()
        
        # 提取文本（如果是字典/对象，先转换）
        report_text = ReportGuardNode._extract_text(final_report)
        
        logger.info(f"📄 报告长度: {len(report_text)} 字符")
        
        # === 内容安全检测 ===
        safety_result = safety_guard.check(report_text, context="report")
        
        if not safety_result["is_safe"]:
            logger.warning(f"⚠️ 报告包含不当内容: {safety_result['violations']}")
            
            # 记录违规
            violation_logger.log({
                "session_id": session_id,
                "violation_type": "report_content_violation",
                "details": safety_result["violations"],
                "report_length": len(report_text),
                "action_taken": safety_result["action"]
            })
            
            # 根据风险级别处理
            if safety_result["risk_level"] == "high":
                logger.error("🚨 高风险内容，替换为安全版本")
                safe_report = ReportGuardNode._generate_error_report(safety_result)
                
                return {
                    "final_report": safe_report,
                    "report_safety_status": "rejected",
                    "report_violations": safety_result["violations"]
                }
            
            elif safety_result["risk_level"] == "medium":
                logger.warning("⚠️ 中风险内容，执行脱敏处理")
                sanitized_text = safety_result.get("sanitized_text", report_text)
                
                # 如果报告是字典，替换对应字段
                if isinstance(final_report, dict):
                    sanitized_report = ReportGuardNode._sanitize_report_dict(
                        final_report, 
                        report_text, 
                        sanitized_text
                    )
                else:
                    sanitized_report = sanitized_text
                
                return {
                    "final_report": sanitized_report,
                    "report_safety_status": "sanitized",
                    "report_violations": safety_result["violations"]
                }
            
            else:  # low risk
                logger.info("ℹ️ 低风险内容，标记但放行")
                return {
                    "report_safety_status": "flagged",
                    "report_violations": safety_result["violations"]
                }
        
        # === 通过检测 ===
        logger.info("✅ 报告内容安全检查通过")
        logger.info("=" * 100)
        return {
            "report_safety_status": "passed",
            "report_safety_check_passed": True
        }
    
    @staticmethod
    def _extract_text(report: Any) -> str:
        """从报告对象中提取文本"""
        if isinstance(report, str):
            return report
        
        if isinstance(report, dict):
            # 尝试常见字段
            for field in ["content", "text", "report_content", "markdown", "summary"]:
                if field in report and isinstance(report[field], str):
                    return report[field]
            
            # 拼接所有字符串值
            texts = []
            for value in report.values():
                if isinstance(value, str):
                    texts.append(value)
                elif isinstance(value, (list, tuple)):
                    for item in value:
                        if isinstance(item, str):
                            texts.append(item)
            return "\n".join(texts)
        
        # 其他类型，转字符串
        return str(report)
    
    @staticmethod
    def _generate_error_report(safety_result: Dict) -> str:
        """生成错误报告（高风险内容替换）"""
        violations = safety_result.get("violations", [])
        violation_types = [v.get("category", "未知") for v in violations]
        
        return f"""# 报告生成失败

很抱歉，由于内容安全原因，无法生成完整报告。

## 问题说明

分析过程中检测到以下内容安全问题：
{chr(10).join(f"- {vtype}" for vtype in violation_types)}

## 建议

1. 请检查输入需求，避免包含敏感信息
2. 如需重新分析，请调整项目描述
3. 如有疑问，请联系管理员

---
*本报告由内容安全系统自动生成*
"""
    
    @staticmethod
    def _sanitize_report_dict(
        original_report: Dict,
        original_text: str,
        sanitized_text: str
    ) -> Dict:
        """脱敏处理报告字典"""
        # 简单实现：找到包含原始文本的字段并替换
        sanitized_report = original_report.copy()
        
        for key, value in original_report.items():
            if isinstance(value, str) and value in original_text:
                # 找到对应的脱敏位置
                start_pos = original_text.find(value)
                if start_pos >= 0:
                    end_pos = start_pos + len(value)
                    sanitized_report[key] = sanitized_text[start_pos:end_pos]
        
        return sanitized_report
