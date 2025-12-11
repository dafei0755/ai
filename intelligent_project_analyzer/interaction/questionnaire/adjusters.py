"""
问卷调整器模块

提供问卷问题数量的动态调整逻辑。
"""

from typing import Dict, Any, List, Tuple
from loguru import logger


class QuestionAdjuster:
    """
    问题数量动态调整器
    
    根据问卷总长度动态调整：避免问卷过长导致用户疲劳。
    根据冲突严重性动态调整：critical冲突时优先保留冲突问题。
    
    原始位置: calibration_questionnaire.py L534-709
    """
    
    @staticmethod
    def adjust(
        philosophy_questions: List[Dict[str, Any]],
        conflict_questions: List[Dict[str, Any]],
        original_question_count: int,
        feasibility_data: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        动态调整问题数量（🆕 P2进阶功能）

        核心策略：
        1. 根据问卷总长度动态调整：避免问卷过长导致用户疲劳
        2. 根据冲突严重性动态调整：critical冲突时优先保留冲突问题
        3. 优先级排序：确保保留最有价值的问题

        调整规则：
        - 问卷总长度 <= 7: 保留全部问题
        - 问卷总长度 8-10: 轻度裁剪（保留80%）
        - 问卷总长度 11-13: 中度裁剪（保留60%）
        - 问卷总长度 >= 14: 重度裁剪（保留40%）

        优先级排序（从高到低）：
        1. critical冲突问题 > 理念选择问题
        2. high冲突问题 > 方案倾向问题
        3. 目标理念问题 > medium冲突问题
        4. 开放探索问题（可选）

        Args:
            philosophy_questions: 理念探索问题列表
            conflict_questions: 资源冲突问题列表
            original_question_count: 原始问卷问题数量
            feasibility_data: V1.5可行性分析数据（用于判断冲突严重性）

        Returns:
            调整后的(philosophy_questions, conflict_questions)
        """
        total_injected = len(philosophy_questions) + len(conflict_questions)

        # 如果没有问题需要注入，直接返回
        if total_injected == 0:
            return [], []

        # 计算问卷总长度（原始问题 + 注入问题）
        total_length = original_question_count + total_injected

        # 根据总长度决定保留比例
        if total_length <= 7:
            # 短问卷：保留全部
            keep_ratio = 1.0
            logger.info(f"📊 动态调整: 问卷总长度{total_length}≤7, 保留全部问题")
        elif total_length <= 10:
            # 中等问卷：轻度裁剪
            keep_ratio = 0.8
            logger.info(f"📊 动态调整: 问卷总长度{total_length}在8-10, 轻度裁剪（保留80%）")
        elif total_length <= 13:
            # 较长问卷：中度裁剪
            keep_ratio = 0.6
            logger.info(f"📊 动态调整: 问卷总长度{total_length}在11-13, 中度裁剪（保留60%）")
        else:
            # 超长问卷：重度裁剪
            keep_ratio = 0.4
            logger.info(f"📊 动态调整: 问卷总长度{total_length}≥14, 重度裁剪（保留40%）")

        # 如果不需要裁剪，直接返回
        if keep_ratio >= 1.0:
            return philosophy_questions, conflict_questions

        # 计算目标保留数量
        target_count = max(1, int(total_injected * keep_ratio))

        # 提取冲突严重性（用于优先级判断）
        conflict_severity = QuestionAdjuster._get_max_conflict_severity(feasibility_data)

        # 为每个问题分配优先级分数
        scored_questions = []

        # 评分：冲突问题
        for cq in conflict_questions:
            severity = cq.get("severity", "unknown")
            if severity == "critical":
                score = 100
            elif severity == "high":
                score = 80
            elif severity == "medium":
                score = 60
            else:
                score = 40
            scored_questions.append({
                "question": cq,
                "score": score,
                "type": "conflict",
                "label": f"冲突问题({severity})"
            })

        # 评分：理念问题
        for pq in philosophy_questions:
            dimension = pq.get("dimension", "unknown")
            q_id = pq.get("id", "")

            # 根据dimension和冲突严重性动态调整分数
            if dimension == "philosophy":
                # 理念选择问题：如果有critical冲突，降低优先级；否则最高优先级
                score = 70 if conflict_severity == "critical" else 90
                label = "理念选择问题"
            elif dimension == "approach":
                # 方案倾向问题：始终高优先级
                score = 75
                label = "方案倾向问题"
            elif dimension == "goal":
                # 目标理念问题：中等优先级
                score = 65
                label = "目标理念问题"
            elif dimension == "exploration":
                # 开放探索问题：如果问卷很长，可裁剪；否则保留
                score = 50 if total_length >= 13 else 70
                label = "开放探索问题"
            else:
                score = 50
                label = "其他问题"

            scored_questions.append({
                "question": pq,
                "score": score,
                "type": "philosophy",
                "label": label
            })

        # 按分数排序（从高到低）
        scored_questions.sort(key=lambda x: x["score"], reverse=True)

        # 保留前target_count个问题
        kept_questions = scored_questions[:target_count]

        # 分离理念问题和冲突问题
        adjusted_philosophy = [q["question"] for q in kept_questions if q["type"] == "philosophy"]
        adjusted_conflict = [q["question"] for q in kept_questions if q["type"] == "conflict"]

        # 记录裁剪详情
        if len(kept_questions) < len(scored_questions):
            dropped = scored_questions[target_count:]
            dropped_labels = [q["label"] for q in dropped]
            logger.info(f"📊 动态裁剪: 移除 {len(dropped)} 个低优先级问题: {', '.join(dropped_labels)}")
            kept_labels = [q["label"] for q in kept_questions]
            logger.info(f"📊 保留问题: {', '.join(kept_labels)}")

        return adjusted_philosophy, adjusted_conflict

    @staticmethod
    def _get_max_conflict_severity(feasibility_data: Dict[str, Any]) -> str:
        """
        获取最高冲突严重性等级

        Args:
            feasibility_data: V1.5可行性分析数据

        Returns:
            最高严重性等级: "critical" | "high" | "medium" | "low" | "none"
        """
        if not feasibility_data:
            return "none"

        conflicts = feasibility_data.get("conflict_detection", {})
        if not conflicts:
            return "none"

        max_severity = "none"
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}

        # 检查所有冲突类型
        for conflict_type in ["budget_conflicts", "timeline_conflicts", "space_conflicts"]:
            conflict_list = conflicts.get(conflict_type, [])
            if conflict_list and conflict_list[0].get("detected"):
                severity = conflict_list[0].get("severity", "none")
                if severity_order.get(severity, 0) > severity_order.get(max_severity, 0):
                    max_severity = severity

        return max_severity
