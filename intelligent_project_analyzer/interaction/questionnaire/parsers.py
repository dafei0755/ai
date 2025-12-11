"""
答案解析器模块

提供问卷答案的提取、解析和归一化逻辑。
"""

import json
from typing import Dict, Any, List, Tuple, Optional
from loguru import logger


class AnswerParser:
    """
    答案解析器
    
    从用户响应中提取问卷答案原始结构，将原始答案与问卷元数据合并为结构化摘要。
    
    原始位置: calibration_questionnaire.py L864-1014
    """
    
    @staticmethod
    def extract_raw_answers(user_response: Any) -> Tuple[Optional[Any], str]:
        """从用户响应中提取问卷答案原始结构和补充说明."""
        if user_response is None:
            return None, ""

        additional_notes = ""
        raw_answers: Optional[Any] = None

        if isinstance(user_response, dict):
            additional_notes = str(user_response.get("additional_info") or user_response.get("notes") or "").strip()
            raw_answers = (
                user_response.get("answers")
                or user_response.get("entries")
                or user_response.get("responses")
            )
        elif isinstance(user_response, list):
            raw_answers = user_response
        elif isinstance(user_response, str):
            stripped = user_response.strip()
            if not stripped:
                return None, ""
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return None, ""
            if isinstance(parsed, dict):
                additional_notes = str(parsed.get("additional_info") or parsed.get("notes") or "").strip()
                raw_answers = parsed.get("answers") or parsed.get("entries") or parsed
            elif isinstance(parsed, list):
                raw_answers = parsed

        return raw_answers, additional_notes

    @staticmethod
    def build_answer_entries(
        questionnaire: Dict[str, Any],
        raw_answers: Optional[Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """将原始答案与问卷元数据合并为结构化摘要."""
        if not raw_answers:
            return [], {}

        answer_lookup: Dict[str, Any] = {}

        if isinstance(raw_answers, dict):
            answer_lookup = {str(key): value for key, value in raw_answers.items()}
        elif isinstance(raw_answers, list):
            for idx, item in enumerate(raw_answers, 1):
                if not isinstance(item, dict):
                    continue
                q_id = item.get("question_id") or item.get("id") or f"Q{idx}"
                answer_value = (
                    item.get("answer")
                    or item.get("value")
                    or item.get("response")
                    or item.get("selected")
                    or item.get("answers")
                )
                if answer_value is None:
                    continue
                key = str(q_id)
                answer_lookup[key] = answer_value
                question_label = item.get("question")
                if question_label:
                    answer_lookup[str(question_label)] = answer_value
        else:
            return [], {}

        questions = questionnaire.get("questions", []) if questionnaire else []
        entries: List[Dict[str, Any]] = []
        compact_answers: Dict[str, Any] = {}

        for idx, question in enumerate(questions, 1):
            q_id = question.get("id") or f"Q{idx}"
            potential_keys = [
                str(q_id),
                f"q{idx}",
                question.get("question"),
                str(idx)
            ]

            answer_value = None
            for key in potential_keys:
                if key is None:
                    continue
                key_str = str(key)
                if key_str in answer_lookup:
                    answer_value = answer_lookup[key_str]
                    break
                if key in answer_lookup:  # 兼容原始键
                    answer_value = answer_lookup[key]
                    break

            if answer_value is None:
                continue

            normalized_value = AnswerParser._normalize_answer_value(question, answer_value)
            if normalized_value is None:
                continue

            entry = {
                "id": q_id,
                "question": question.get("question", ""),
                "value": normalized_value,
                "type": question.get("type"),
                "context": question.get("context", "")
            }
            entries.append(entry)
            compact_answers[q_id] = normalized_value

        return entries, compact_answers

    @staticmethod
    def _normalize_answer_value(question: Dict[str, Any], answer: Any) -> Optional[Any]:
        """根据题型对答案进行归一化，便于后续处理."""
        if answer is None:
            return None

        q_type = (question.get("type") or "open_ended").lower()

        if q_type == "multiple_choice":
            if isinstance(answer, str):
                values = [item.strip() for item in answer.split(",") if item.strip()]
                return values or None
            if isinstance(answer, (list, tuple, set)):
                values = [str(item).strip() for item in answer if str(item).strip()]
                return values or None
            coerced = str(answer).strip()
            return [coerced] if coerced else None

        if q_type == "single_choice":
            if isinstance(answer, (list, tuple, set)):
                for item in answer:
                    candidate = str(item).strip()
                    if candidate:
                        return candidate
                return None
            return str(answer).strip() or None

        if isinstance(answer, (list, tuple, set)):
            values = [str(item).strip() for item in answer if str(item).strip()]
            return "、".join(values) if values else None

        if isinstance(answer, dict):
            try:
                serialized = json.dumps(answer, ensure_ascii=False)
            except (TypeError, ValueError):
                serialized = str(answer)
            return serialized.strip() or None

        return str(answer).strip() or None
