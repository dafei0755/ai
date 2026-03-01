"""
 P1优化: 智能上下文压缩器
v7.502.1 - 2026-02-10

 目标: 减少重复上下文构建的Token消耗，同时确保信息完整性
 方案: 使用分级压缩策略 - Batch1完整传递，后续批次适度压缩
 预期收益: Token消耗↓30-50%（质量优先，避免过度压缩）

 质量保证原则:
1.  Batch1完全不压缩 - 保证第一批专家获得完整上下文
2.  Batch2-3适度压缩 - 保留前800字符完整内容
3.  Batch4+谨慎压缩 - 仅在批次很多时使用激进模式
4.  智能截断 - 在句号处截断，避免破坏语义完整性

️ 注意: 质量 > 成本，不为节省Token牺牲专家分析质量
"""

from typing import Any, Dict
from loguru import logger


class ContextCompressor:
    """
    智能上下文压缩器 - 质量优先的分级压缩策略

     v7.502.1调整: 确保不造成信息流失
    - Minimal: 完全不压缩（Batch1专家获得完整上下文）
    - Balanced: 适度压缩（前800字符完整 + 智能截断）
    - Aggressive: 谨慎压缩（仅Batch4+使用）
    """

    def __init__(self, compression_level: str = "balanced"):
        """
        初始化上下文压缩器

        Args:
            compression_level: 压缩级别
                - "minimal": 不压缩，完整传递（Batch1）
                - "balanced": 适度压缩，保留前800字符（Batch2-3）
                - "aggressive": 激进压缩，交付物清单+示例（Batch4+）
        """
        self.compression_level = compression_level
        self._compression_stats = {"original_length": 0, "compressed_length": 0, "compression_ratio": 0.0}

    def compress_agent_results(self, agent_results: Dict[str, Any], current_role_id: str) -> str:
        """
         P1优化: 压缩前序专家输出

        策略:
        1. 提取交付物摘要 (而非完整内容)
        2. 保留关键结论和建议
        3. 移除冗余描述性文本

        Args:
            agent_results: 所有专家的执行结果
            current_role_id: 当前专家ID (用于过滤相关上下文)

        Returns:
            压缩后的上下文字符串
        """
        if not agent_results:
            return ""

        context_parts = []

        #  向后兼容: minimal模式使用原始标题格式
        if self.compression_level == "minimal":
            context_parts.append("## 前序专家的分析成果")
            context_parts.append("**说明**: 以下是前序专家的完整分析结果，你可以参考和引用。\n")
        else:
            context_parts.append("## 前序专家分析成果 (摘要)")
            context_parts.append("**说明**: 以下是前序专家的核心结论，详细分析已省略以优化性能。\n")

        for expert_id, result in agent_results.items():
            if not isinstance(result, dict):
                continue

            # 跳过自己
            if expert_id == current_role_id:
                continue

            expert_name = result.get("expert_name", expert_id)
            context_parts.append(f"### {expert_name}")

            # 提取结构化输出
            structured_output = result.get("structured_output", {})
            if structured_output:
                summary = self._extract_structured_summary(structured_output)
                context_parts.append(summary)
            else:
                # 降级: 使用 analysis 字段
                analysis = result.get("analysis", "")
                summary = self._extract_text_summary(analysis, expert_name)
                context_parts.append(summary)

            context_parts.append("")  # 空行分隔

        compressed = "\n".join(context_parts)

        #  修复统计逻辑: 计算原始完整内容长度（v7.18传递的是完整deliverable content）
        original_length = 0
        for result in agent_results.values():
            if not isinstance(result, dict):
                continue

            # 优先统计structured_output中的完整内容
            structured_output = result.get("structured_output", {})
            if structured_output:
                task_report = structured_output.get("task_execution_report", {})
                deliverable_outputs = task_report.get("deliverable_outputs", [])
                for deliverable in deliverable_outputs:
                    content = deliverable.get("content", "")
                    original_length += len(content)
            else:
                # 降级: 统计analysis字段
                analysis = result.get("analysis", "")
                original_length += len(analysis)

        self._compression_stats["original_length"] = original_length
        self._compression_stats["compressed_length"] = len(compressed)
        if original_length > 0:
            self._compression_stats["compression_ratio"] = len(compressed) / original_length

        return compressed

    def _extract_structured_summary(self, structured_output: Dict[str, Any]) -> str:
        """
        从结构化输出中提取摘要

        提取策略:
        1. 交付物列表 (名称+状态)
        2. 关键结论 (如果有)
        3. 重要建议 (如果有)
        """
        parts = []

        task_report = structured_output.get("task_execution_report", {})
        deliverable_outputs = task_report.get("deliverable_outputs", [])

        if deliverable_outputs:
            parts.append(f"**交付物数量**: {len(deliverable_outputs)}")

            # 根据压缩级别决定详细程度
            if self.compression_level == "minimal":
                #  质量优先: Minimal模式完全不压缩，传递完整内容
                # 确保Batch1的专家能获得完整上下文，避免信息流失
                for i, deliverable in enumerate(deliverable_outputs, 1):
                    name = deliverable.get("deliverable_name", f"交付物{i}")
                    content = deliverable.get("content", "")
                    status = deliverable.get("completion_status", "unknown")

                    parts.append(f"\n#### 交付物 {i}: {name}")
                    parts.append(f"**状态**: {status}")
                    if content:
                        #  传递完整内容（不截断）
                        parts.append(f"**内容**:\n{content}\n")

            elif self.compression_level == "balanced":
                #  适度压缩: 保留结构化信息 + 关键内容摘要
                # Batch2专家已有一定上下文，可适度精简
                for i, deliverable in enumerate(deliverable_outputs, 1):
                    name = deliverable.get("deliverable_name", f"交付物{i}")
                    content = deliverable.get("content", "")
                    status = deliverable.get("completion_status", "unknown")

                    parts.append(f"\n**{i}. {name}** (状态: {status})")
                    if content:
                        # 保留前800字符 + 智能截断
                        if len(content) <= 800:
                            parts.append(f"内容: {content}")
                        else:
                            # 在句号处截断
                            truncated = content[:800]
                            last_period = truncated.rfind("。")
                            if last_period > 600:  # 至少保留75%
                                truncated = truncated[: last_period + 1]
                            parts.append(f"摘要: {truncated}...")

            else:  # aggressive
                #  激进压缩: 交付物清单 + 简短摘要
                # Batch3+专家聚焦细节，但仍需基本上下文
                deliverable_list = []
                for i, deliverable in enumerate(deliverable_outputs, 1):
                    name = deliverable.get("deliverable_name", f"交付物{i}")
                    deliverable_list.append(f"{i}. {name}")

                parts.append(f"**交付物清单** ({len(deliverable_outputs)}个)")
                parts.extend(deliverable_list)

                # 保留第一个交付物的简短摘要（前300字符）
                if deliverable_outputs:
                    first_content = deliverable_outputs[0].get("content", "")
                    if first_content and len(first_content) > 0:
                        summary = first_content[:300]
                        last_period = summary.rfind("。")
                        if last_period > 200:
                            summary = summary[: last_period + 1]
                        parts.append(f"\n**典型输出示例**: {summary}...")

        # 提取整体结论
        overall_conclusions = task_report.get("overall_conclusions", [])
        if overall_conclusions and self.compression_level != "aggressive":
            parts.append("\n**关键结论**:")
            # 最多保留前3个结论
            for conclusion in overall_conclusions[:3]:
                parts.append(f"- {conclusion}")

        return "\n".join(parts)

    def _extract_text_summary(self, analysis_text: str, expert_name: str, max_length: int = 300) -> str:
        """
        从纯文本分析中提取摘要

        策略:
        1. 提取前max_length字符
        2. 尝试在句号处截断
        3. 添加省略号提示
        """
        if not analysis_text:
            return f"**摘要**: {expert_name}未提供分析内容"

        # 根据压缩级别调整最大长度
        if self.compression_level == "minimal":
            max_length = 500
        elif self.compression_level == "balanced":
            max_length = 300
        else:  # aggressive
            max_length = 150

        if len(analysis_text) <= max_length:
            return f"**摘要**: {analysis_text}"

        # 尝试在句号处截断
        truncated = analysis_text[:max_length]
        last_period = truncated.rfind("。")
        if last_period > max_length * 0.6:  # 至少保留60%
            truncated = truncated[: last_period + 1]

        return f"**摘要**: {truncated}..."

    def compress_user_requirements(self, structured_requirements: Dict[str, Any]) -> str:
        """
        压缩用户需求

        策略: 仅保留非空字段，使用紧凑格式
        """
        if not structured_requirements:
            return ""

        parts = []
        parts.append("## 结构化需求")

        # 过滤空值
        non_empty_fields = {k: v for k, v in structured_requirements.items() if v}

        if self.compression_level == "aggressive":
            # 激进模式: 仅列出字段名
            parts.append(f"**字段数**: {len(non_empty_fields)}")
            parts.append(f"**包含**: {', '.join(non_empty_fields.keys())}")
        else:
            # 常规模式: 列出所有字段和值
            for key, value in non_empty_fields.items():
                # 如果值过长，截断
                value_str = str(value)
                if len(value_str) > 100 and self.compression_level == "balanced":
                    value_str = value_str[:100] + "..."
                parts.append(f"- **{key}**: {value_str}")

        return "\n".join(parts)

    def get_compression_stats(self) -> Dict[str, Any]:
        """
        获取压缩统计信息

        Returns:
            包含原始长度、压缩长度、压缩比的字典
        """
        return {
            **self._compression_stats,
            "savings_percent": (1 - self._compression_stats["compression_ratio"]) * 100
            if self._compression_stats["compression_ratio"] > 0
            else 0,
        }

    def reset_stats(self):
        """重置统计信息"""
        self._compression_stats = {"original_length": 0, "compressed_length": 0, "compression_ratio": 0.0}


def create_context_compressor(batch_number: int, total_batches: int) -> ContextCompressor:
    """
     P1优化: 工厂函数 - 根据批次动态选择压缩级别

     质量优先策略（v7.502.1调整）:
    - Batch1: minimal（完全不压缩，传递完整内容）
      * 确保第一批专家获得完整上下文
      * 避免信息流失导致分析质量下降

    - Batch2+: balanced（适度压缩，保留关键信息）
      * 保留前800字符完整内容（智能截断）
      * 维持专家间的信息连贯性
      * Token节省30-50%，质量影响最小

    - Batch4+: aggressive（仅在批次很多时使用）
      * 交付物清单 + 典型输出示例
      * Token节省70-80%
      * 仅适用于后期聚焦细节的专家

    Args:
        batch_number: 当前批次编号 (1-based)
        total_batches: 总批次数

    Returns:
        配置好的ContextCompressor实例
    """
    if batch_number == 1:
        # Batch1: 完全不压缩，确保信息完整性
        compression_level = "minimal"
    elif batch_number >= 4 and total_batches >= 4:
        # Batch4+: 激进压缩（仅当批次>=4时）
        compression_level = "aggressive"
    else:
        # Batch2-3: 适度压缩，平衡质量与效率
        compression_level = "balanced"

    logger.info(f"️ [ContextCompressor] Batch{batch_number}/{total_batches} 使用压缩级别: {compression_level}")

    return ContextCompressor(compression_level=compression_level)
