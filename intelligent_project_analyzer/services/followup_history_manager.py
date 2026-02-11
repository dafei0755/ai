"""
追问历史管理器

负责追问对话历史的存储、检索和智能上下文构建
支持动态轮次调整和"记忆全部"模式
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
from .redis_session_manager import RedisSessionManager


class FollowupHistoryManager:
    """
    追问历史管理器

    功能：
    1. 追问历史的CRUD操作
    2. 智能上下文构建（动态轮次调整）
    3. "记忆全部"模式（使用摘要技术）
    4. Redis持久化
    """

    # 配置常量
    HISTORY_KEY_SUFFIX = ":followup_history"
    MAX_STORED_TURNS = 50  # Redis最多存储50轮（防止无限增长）

    # Token估算配置
    CHARS_PER_TOKEN = 4  # 估算：4个字符约等于1个token
    MAX_CONTEXT_TOKENS = 8000  # 最大上下文限制
    QUESTION_RESERVED_TOKENS = 500  # 为当前问题预留

    def __init__(self, session_manager: RedisSessionManager):
        """
        初始化追问历史管理器

        Args:
            session_manager: Redis会话管理器实例
        """
        self.session_manager = session_manager
        logger.info(" FollowupHistoryManager 已初始化")

    async def add_turn(
        self,
        session_id: str,
        question: str,
        answer: str,
        intent: str = "general",
        referenced_sections: Optional[List[str]] = None,
        attachments: Optional[List[dict]] = None
    ) -> Dict[str, Any]:
        """
        添加一轮追问对话

        Args:
            session_id: 会话ID
            question: 用户问题
            answer: 系统回答
            intent: 意图类型
            referenced_sections: 引用的报告章节
            attachments: 附件列表（图片等），格式：[{"type": "image", "url": "...", ...}]

        Returns:
            新增的对话轮次数据
        """
        # 获取现有历史
        history = await self.get_history(session_id, limit=None)  # 获取全部

        # 构建新轮次
        turn_data = {
            "turn_id": len(history) + 1,
            "question": question,
            "answer": answer,
            "intent": intent,
            "referenced_sections": referenced_sections or [],
            "attachments": attachments or [],
            "timestamp": datetime.now().isoformat()
        }

        history.append(turn_data)

        # 限制存储长度（只保留最近N轮）
        if len(history) > self.MAX_STORED_TURNS:
            history = history[-self.MAX_STORED_TURNS:]
            logger.warning(f"️ 追问历史超过{self.MAX_STORED_TURNS}轮，已截断")

        # 保存到Redis
        await self._save_history(session_id, history)

        logger.info(f" 添加追问轮次 #{turn_data['turn_id']}: {question[:50]}...")
        return turn_data

    async def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取追问历史

        Args:
            session_id: 会话ID
            limit: 返回最近N轮（None表示全部）

        Returns:
            追问历史列表
        """
        key = f"{session_id}{self.HISTORY_KEY_SUFFIX}"

        # 从Redis获取
        if self.session_manager._memory_mode:
            history = self.session_manager._memory_sessions.get(key, [])
        else:
            try:
                data = await self.session_manager.redis_client.get(
                    f"{self.session_manager.SESSION_PREFIX}{key}"
                )
                history = json.loads(data) if data else []
            except Exception as e:
                logger.error(f" 获取追问历史失败: {e}")
                history = []

        # 限制返回数量
        if limit and len(history) > limit:
            return history[-limit:]

        return history

    async def _save_history(
        self,
        session_id: str,
        history: List[Dict[str, Any]]
    ):
        """
        保存追问历史到Redis

        Args:
            session_id: 会话ID
            history: 完整历史列表
        """
        key = f"{session_id}{self.HISTORY_KEY_SUFFIX}"

        if self.session_manager._memory_mode:
            self.session_manager._memory_sessions[key] = history
        else:
            try:
                await self.session_manager.redis_client.setex(
                    f"{self.session_manager.SESSION_PREFIX}{key}",
                    self.session_manager.SESSION_TTL,
                    json.dumps(history, ensure_ascii=False)
                )
            except Exception as e:
                logger.error(f" 保存追问历史失败: {e}")

    def _estimate_tokens(self, text: str) -> int:
        """
        估算文本的Token数量

        Args:
            text: 文本内容

        Returns:
            估算的token数量
        """
        return len(text) // self.CHARS_PER_TOKEN

    def build_context_for_llm(
        self,
        history: List[Dict[str, Any]],
        report_summary: str,
        current_question: str,
        enable_memory_all: bool = True
    ) -> Dict[str, Any]:
        """
        构建LLM上下文（智能版本）

        Args:
            history: 完整对话历史
            report_summary: 报告摘要内容
            current_question: 当前问题
            enable_memory_all: 是否启用"记忆全部"模式

        Returns:
            {
                "context_str": str,  # 格式化的上下文字符串
                "metadata": {
                    "total_turns": int,
                    "included_turns": int,
                    "report_tokens": int,
                    "history_tokens": int,
                    "total_tokens": int,
                    "truncated": bool
                }
            }
        """
        # 1. 估算各部分Token数
        question_tokens = self._estimate_tokens(current_question)
        report_tokens = self._estimate_tokens(report_summary)

        # 2. 计算历史可用Token
        available_for_history = (
            self.MAX_CONTEXT_TOKENS
            - self.QUESTION_RESERVED_TOKENS
            - report_tokens
        )

        if available_for_history < 0:
            logger.warning(f"️ 报告过长({report_tokens} tokens)，历史空间不足")
            available_for_history = 500  # 最少保留500 tokens给历史

        # 3. 选择历史处理策略
        if enable_memory_all and len(history) > 0:
            # "记忆全部"模式：使用摘要压缩
            history_str, included_turns, history_tokens, truncated = self._build_history_with_summary(
                history, available_for_history
            )
        else:
            # 标准模式：只保留最近N轮
            history_str, included_turns, history_tokens, truncated = self._build_history_recent_only(
                history, available_for_history
            )

        # 4. 组合完整上下文
        context_str = f"""【报告相关内容】
{report_summary}

【对话历史】
{history_str}

【当前问题】
{current_question}
"""

        total_tokens = report_tokens + history_tokens + question_tokens

        metadata = {
            "total_turns": len(history),
            "included_turns": included_turns,
            "report_tokens": report_tokens,
            "history_tokens": history_tokens,
            "question_tokens": question_tokens,
            "total_tokens": total_tokens,
            "truncated": truncated,
            "mode": "memory_all" if enable_memory_all else "recent_only"
        }

        logger.info(f" 上下文构建: {metadata}")

        return {
            "context_str": context_str,
            "metadata": metadata
        }

    def _build_history_recent_only(
        self,
        history: List[Dict[str, Any]],
        max_tokens: int
    ) -> tuple[str, int, int, bool]:
        """
        标准模式：只保留最近N轮对话

        Returns:
            (history_str, included_turns, actual_tokens, truncated)
        """
        if not history:
            return "（首次对话）", 0, 0, False

        # 从最新往前选取
        selected = []
        current_tokens = 0

        for turn in reversed(history):
            #  v7.108: 添加图片引用（如果有）
            turn_text = f"第{turn['turn_id']}轮：\nQ: {turn['question']}\n"

            # 处理附件（图片）
            if turn.get('attachments'):
                for att in turn['attachments']:
                    if att.get('type') == 'image':
                        vision_analysis = att.get('vision_analysis', '')
                        if vision_analysis:
                            turn_text += f"[图片: {att.get('original_filename', '未命名')}]\n"
                            turn_text += f"AI分析: {vision_analysis}\n"

            turn_text += f"A: {turn['answer']}\n"
            turn_tokens = self._estimate_tokens(turn_text)

            if current_tokens + turn_tokens > max_tokens:
                break

            selected.insert(0, turn_text)
            current_tokens += turn_tokens

        if not selected:
            # 至少保留最近1轮（截断回答）
            last_turn = history[-1]
            max_answer_chars = max_tokens * self.CHARS_PER_TOKEN - 100
            truncated_answer = last_turn['answer'][:max_answer_chars] + "..."
            selected = [f"第{last_turn['turn_id']}轮：\nQ: {last_turn['question']}\nA: {truncated_answer}\n"]
            current_tokens = self._estimate_tokens(selected[0])

        history_str = "\n".join(selected)
        truncated = len(selected) < len(history)

        return history_str, len(selected), current_tokens, truncated

    def _build_history_with_summary(
        self,
        history: List[Dict[str, Any]],
        max_tokens: int
    ) -> tuple[str, int, int, bool]:
        """
        "记忆全部"模式：早期轮次使用摘要，最近轮次保留完整

        策略：
        - 最近3轮：保留完整内容
        - 更早轮次：生成简短摘要（问题+关键回答）

        Returns:
            (history_str, included_turns, actual_tokens, truncated)
        """
        if not history:
            return "（首次对话）", 0, 0, False

        # 1. 优先保证最近3轮完整
        recent_turns = history[-3:] if len(history) >= 3 else history
        recent_str_parts = []
        recent_tokens = 0

        for turn in recent_turns:
            #  v7.108: 添加图片引用（如果有）
            turn_text = f"第{turn['turn_id']}轮：\nQ: {turn['question']}\n"

            # 处理附件（图片）
            if turn.get('attachments'):
                for att in turn['attachments']:
                    if att.get('type') == 'image':
                        vision_analysis = att.get('vision_analysis', '')
                        if vision_analysis:
                            turn_text += f"[图片: {att.get('original_filename', '未命名')}]\n"
                            turn_text += f"AI分析: {vision_analysis}\n"

            turn_text += f"A: {turn['answer']}\n"
            recent_str_parts.append(turn_text)
            recent_tokens += self._estimate_tokens(turn_text)

        # 2. 如果token充足，为早期轮次生成摘要
        early_turns = history[:-3] if len(history) > 3 else []
        available_for_early = max_tokens - recent_tokens

        if early_turns and available_for_early > 200:  # 至少200 tokens才值得添加摘要
            early_summary_parts = []
            early_tokens = 0

            for turn in early_turns:
                # 生成简短摘要：问题 + 回答前100字
                summary = f"第{turn['turn_id']}轮摘要: {turn['question']} → {turn['answer'][:100]}..."
                summary_tokens = self._estimate_tokens(summary)

                if early_tokens + summary_tokens > available_for_early:
                    break

                early_summary_parts.append(summary)
                early_tokens += summary_tokens

            # 组合：早期摘要 + 最近完整
            if early_summary_parts:
                history_str = f"""【早期对话摘要（共{len(early_summary_parts)}轮）】
{chr(10).join(early_summary_parts)}

【最近对话（完整）】
{''.join(recent_str_parts)}"""
                total_tokens = early_tokens + recent_tokens
                included_turns = len(early_summary_parts) + len(recent_turns)
            else:
                history_str = ''.join(recent_str_parts)
                total_tokens = recent_tokens
                included_turns = len(recent_turns)
        else:
            # Token不足，只保留最近轮次
            history_str = ''.join(recent_str_parts)
            total_tokens = recent_tokens
            included_turns = len(recent_turns)

        truncated = included_turns < len(history)

        return history_str, included_turns, total_tokens, truncated

    async def clear_history(self, session_id: str):
        """
        清空追问历史（用于测试或用户主动清空）

        Args:
            session_id: 会话ID
        """
        await self._save_history(session_id, [])
        logger.info(f"️ 已清空会话 {session_id} 的追问历史")
