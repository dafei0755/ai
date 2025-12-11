"""
实时质量监控 - 专家执行过程中的质量控制

在agent_executor中嵌入质量检查，实现执行前约束注入和执行后快速验证
"""

from typing import Dict, List, Any, Optional
from loguru import logger


class QualityMonitor:
    """质量监控器 - 前置预防第2层"""
    
    @staticmethod
    def inject_quality_constraints(
        original_prompt: str,
        quality_checklist: Dict[str, Any]
    ) -> str:
        """
        在专家执行前注入质量约束
        
        将质量检查清单添加到system prompt中，让专家"带着约束"工作
        
        Args:
            original_prompt: 原始的专家prompt
            quality_checklist: 质量检查清单
            
        Returns:
            增强后的prompt
        """
        if not quality_checklist:
            return original_prompt
        
        # 提取关键信息
        risk_level = quality_checklist.get("risk_level", "medium")
        risk_points = quality_checklist.get("risk_points", [])
        checklist_items = quality_checklist.get("quality_checklist", [])
        
        # 构建质量约束部分
        quality_section = "\n\n" + "="*60 + "\n"
        quality_section += "⚠️ **质量控制要求**（请务必遵守）\n"
        quality_section += "="*60 + "\n\n"
        
        # 风险提示
        if risk_level == "high":
            quality_section += "🔴 **本任务为高风险任务，请格外注意以下风险点**：\n"
        elif risk_level == "medium":
            quality_section += "🟡 **本任务为中等风险任务，请注意以下风险点**：\n"
        else:
            quality_section += "🟢 **本任务风险可控，但仍需注意**：\n"
        
        for i, risk in enumerate(risk_points, 1):
            quality_section += f"{i}. {risk}\n"
        
        quality_section += "\n"
        
        # 质量检查清单
        quality_section += "📋 **输出前必须完成的自查清单**：\n"
        for i, item in enumerate(checklist_items, 1):
            quality_section += f"[ ] {i}. {item}\n"
        
        quality_section += "\n"
        
        # 自我审查指令
        quality_section += "🔍 **自我审查流程**：\n"
        quality_section += "1. 完成初步分析后，先不要输出\n"
        quality_section += "2. 对照上述清单逐项检查\n"
        quality_section += "3. 发现问题立即修正\n"
        quality_section += "4. 确认无误后再输出最终结果\n"
        quality_section += "\n"
        quality_section += "="*60 + "\n"
        
        # 将质量约束插入到prompt中（在主要任务描述之后，例子之前）
        enhanced_prompt = original_prompt + quality_section
        
        logger.debug(f"✅ 已注入质量约束（风险等级: {risk_level}）")
        
        return enhanced_prompt
    
    @staticmethod
    def quick_validation(
        agent_output: str,
        quality_checklist: Dict[str, Any],
        role_id: str
    ) -> Dict[str, Any]:
        """
        专家输出后的快速验证
        
        不依赖LLM，使用规则引擎快速检查常见问题
        
        Args:
            agent_output: 专家的输出内容
            quality_checklist: 质量检查清单
            role_id: 专家角色ID
            
        Returns:
            验证结果：
            {
                "passed": True/False,
                "warnings": ["警告1", "警告2"],
                "errors": ["错误1"],
                "suggestions": ["建议1"],
                "quality_score": 85  # 0-100
            }
        """
        warnings = []
        errors = []
        suggestions = []
        
        # 1. 输出长度检查
        output_length = len(agent_output)
        if output_length < 500:
            errors.append(f"输出过短({output_length}字符)，可能分析不充分")
        elif output_length < 1000:
            warnings.append(f"输出较短({output_length}字符)，建议增加分析深度")
        elif output_length > 10000:
            warnings.append(f"输出过长({output_length}字符)，建议精简")
        
        # 2. 结构完整性检查（检查是否包含关键章节）
        required_sections = ["分析", "建议", "总结"]
        missing_sections = [s for s in required_sections if s not in agent_output]
        if missing_sections:
            warnings.append(f"缺少关键章节: {', '.join(missing_sections)}")
        
        # 3. 数据支撑检查（是否包含数据、案例、引用）
        has_data = any(keyword in agent_output for keyword in [
            "数据", "案例", "研究", "调研", "报告", "根据", "来源", "参考"
        ])
        if not has_data:
            warnings.append("缺乏数据或案例支撑，可能过于主观")
        
        # 4. 空洞表达检查（过多泛泛而谈）
        vague_phrases = ["可能", "也许", "大概", "一般来说", "通常", "基本上"]
        vague_count = sum(agent_output.count(phrase) for phrase in vague_phrases)
        if vague_count > 10:
            warnings.append(f"包含过多模糊表达({vague_count}处)，建议更具体")
        
        # 5. 风险点覆盖检查（是否关注了预判的风险）
        risk_points = quality_checklist.get("risk_points", [])
        uncovered_risks = []
        for risk in risk_points:
            # 提取风险关键词
            risk_keywords = [w for w in risk.split() if len(w) > 2]
            if not any(keyword in agent_output for keyword in risk_keywords):
                uncovered_risks.append(risk)
        
        if uncovered_risks:
            warnings.append(f"未充分关注预判的风险点: {', '.join(uncovered_risks[:2])}")
        
        # 6. 质量清单覆盖检查
        checklist_items = quality_checklist.get("quality_checklist", [])
        unchecked_items = []
        for item in checklist_items:
            item_keywords = [w for w in item.split() if len(w) > 2]
            if not any(keyword in agent_output for keyword in item_keywords):
                unchecked_items.append(item)
        
        if len(unchecked_items) > len(checklist_items) / 2:
            errors.append(f"质量清单完成度不足({len(unchecked_items)}/{len(checklist_items)}项未覆盖)")
        
        # 计算质量评分
        quality_score = 100
        quality_score -= len(errors) * 20  # 每个错误-20分
        quality_score -= len(warnings) * 5  # 每个警告-5分
        quality_score = max(0, min(100, quality_score))
        
        # 判断是否通过
        passed = len(errors) == 0 and quality_score >= 60
        
        # 生成改进建议
        if not passed:
            suggestions.append("建议重新分析，重点关注上述错误和警告")
        if quality_score < 80:
            suggestions.append("增加数据支撑和具体案例")
            suggestions.append("对照质量检查清单逐项完善")
        
        result = {
            "passed": passed,
            "warnings": warnings,
            "errors": errors,
            "suggestions": suggestions,
            "quality_score": quality_score,
            "role_id": role_id
        }
        
        # 记录日志
        status = "✅ 通过" if passed else "❌ 未通过"
        logger.info(f"{status} 快速验证 [{role_id}]: 评分={quality_score}, 错误={len(errors)}, 警告={len(warnings)}")
        
        return result
    
    @staticmethod
    def should_retry(validation_result: Dict[str, Any]) -> bool:
        """
        判断是否应该给专家一次重试机会
        
        策略:
        - 如果有严重错误（如输出过短）→ 重试
        - 如果质量评分<60 → 重试
        - 已经重试过 → 不再重试（避免无限循环）
        """
        if not validation_result.get("passed", True):
            errors = validation_result.get("errors", [])
            quality_score = validation_result.get("quality_score", 100)
            
            # 检查是否有严重错误
            has_critical_error = any(
                "过短" in error or "清单完成度不足" in error
                for error in errors
            )
            
            if has_critical_error or quality_score < 60:
                logger.warning("⚠️ 检测到质量问题，建议重试")
                return True
        
        return False
    
    @staticmethod
    def generate_retry_prompt(
        original_prompt: str,
        validation_result: Dict[str, Any]
    ) -> str:
        """
        生成重试prompt，包含第一次的问题反馈
        
        让专家知道哪里做得不好，针对性改进
        """
        errors = validation_result.get("errors", [])
        warnings = validation_result.get("warnings", [])
        suggestions = validation_result.get("suggestions", [])
        quality_score = validation_result.get("quality_score", 0)
        
        retry_section = "\n\n" + "🔄 " + "="*60 + "\n"
        retry_section += "**重要提示：第一次分析存在以下问题，请改进**\n"
        retry_section += "="*60 + "\n\n"
        
        retry_section += f"**质量评分**: {quality_score}/100 ⚠️\n\n"
        
        if errors:
            retry_section += "❌ **必须修复的错误**：\n"
            for i, error in enumerate(errors, 1):
                retry_section += f"{i}. {error}\n"
            retry_section += "\n"
        
        if warnings:
            retry_section += "⚠️ **需要改进的警告**：\n"
            for i, warning in enumerate(warnings, 1):
                retry_section += f"{i}. {warning}\n"
            retry_section += "\n"
        
        if suggestions:
            retry_section += "💡 **改进建议**：\n"
            for i, suggestion in enumerate(suggestions, 1):
                retry_section += f"{i}. {suggestion}\n"
            retry_section += "\n"
        
        retry_section += "🎯 **请针对上述问题重新分析，确保质量达标**\n"
        retry_section += "="*60 + "\n\n"
        
        enhanced_prompt = retry_section + original_prompt
        
        logger.info("📝 已生成重试prompt")
        
        return enhanced_prompt
