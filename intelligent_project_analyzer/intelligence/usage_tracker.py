"""
使用数据跟踪器 - Phase 1 Intelligence Evolution

记录 Few-Shot 示例的使用情况、用户反馈和质量信号，
支持 SQLite（推荐）和 JSONL（轻量级）两种后端。

Author: AI Architecture Team
Version: v1.0.0
Date: 2026-03-04
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class UsageTracker:
    """
    Few-Shot 示例使用数据跟踪器

    支持：
    - SQLite 后端（默认，支持复杂查询）
    - JSONL 文件后端（轻量级，每日一文件）
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        use_sqlite: bool = True,
    ) -> None:
        """
        初始化跟踪器

        Args:
            data_dir: 数据存储目录
            use_sqlite: True=SQLite后端，False=JSONL文件后端
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data" / "intelligence" / "usage_logs"

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.use_sqlite = use_sqlite

        if use_sqlite:
            self.db_path = self.data_dir / "usage.db"
            self._init_sqlite()
        else:
            self.db_path = self.data_dir / "usage.db"  # 保持属性存在但不使用

        logger.info(f"[UsageTracker] 初始化完成 backend={'sqlite' if use_sqlite else 'jsonl'} dir={self.data_dir}")

    # ──────────────────────────────────────────────────────────────
    # SQLite 初始化
    # ──────────────────────────────────────────────────────────────

    def _init_sqlite(self) -> None:
        """创建 SQLite 数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id              TEXT PRIMARY KEY,
                    timestamp       TEXT NOT NULL,
                    role_id         TEXT NOT NULL,
                    user_request    TEXT,
                    selected_examples TEXT,
                    output_tokens   INTEGER DEFAULT 0,
                    response_time   REAL DEFAULT 0.0,
                    user_feedback   TEXT,
                    session_id      TEXT,
                    metadata        TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_role_id ON usage_logs (role_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_timestamp ON usage_logs (timestamp)"
            )
            conn.commit()

    # ──────────────────────────────────────────────────────────────
    # 日志记录
    # ──────────────────────────────────────────────────────────────

    def log_expert_usage(
        self,
        role_id: str,
        user_request: str,
        selected_examples: List[str],
        output_tokens: int = 0,
        response_time: float = 0.0,
        user_feedback: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        记录一次 Few-Shot 示例使用事件

        Args:
            role_id: 专家角色 ID
            user_request: 用户请求文本
            selected_examples: 被选中的示例 ID 列表
            output_tokens: 输出 token 数
            response_time: 响应时间（秒）
            user_feedback: 用户反馈字典，如 {"liked": True, "rating": 5}
            session_id: 会话 ID
            metadata: 额外元数据

        Returns:
            记录 ID
        """
        record_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        if self.use_sqlite:
            self._log_sqlite(
                record_id=record_id,
                timestamp=timestamp,
                role_id=role_id,
                user_request=user_request,
                selected_examples=selected_examples,
                output_tokens=output_tokens,
                response_time=response_time,
                user_feedback=user_feedback,
                session_id=session_id,
                metadata=metadata,
            )
        else:
            self._log_jsonl(
                record_id=record_id,
                timestamp=timestamp,
                role_id=role_id,
                user_request=user_request,
                selected_examples=selected_examples,
                output_tokens=output_tokens,
                response_time=response_time,
                user_feedback=user_feedback,
                session_id=session_id,
                metadata=metadata,
            )

        return record_id

    def _log_sqlite(self, **kwargs: Any) -> None:
        """写入 SQLite"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO usage_logs
                        (id, timestamp, role_id, user_request, selected_examples,
                         output_tokens, response_time, user_feedback, session_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        kwargs["record_id"],
                        kwargs["timestamp"],
                        kwargs["role_id"],
                        kwargs.get("user_request", ""),
                        json.dumps(kwargs.get("selected_examples", []), ensure_ascii=False),
                        kwargs.get("output_tokens", 0),
                        kwargs.get("response_time", 0.0),
                        json.dumps(kwargs.get("user_feedback"), ensure_ascii=False),
                        kwargs.get("session_id"),
                        json.dumps(kwargs.get("metadata"), ensure_ascii=False),
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"[UsageTracker] SQLite 写入失败: {e}")

    def _log_jsonl(self, **kwargs: Any) -> None:
        """写入 JSONL 文件（每日一文件）"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = self.data_dir / f"usage_{today}.jsonl"
            record = {
                "id": kwargs["record_id"],
                "timestamp": kwargs["timestamp"],
                "role_id": kwargs["role_id"],
                "user_request": kwargs.get("user_request", ""),
                "selected_examples": kwargs.get("selected_examples", []),
                "output_tokens": kwargs.get("output_tokens", 0),
                "response_time": kwargs.get("response_time", 0.0),
                "user_feedback": kwargs.get("user_feedback"),
                "session_id": kwargs.get("session_id"),
                "metadata": kwargs.get("metadata"),
            }
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"[UsageTracker] JSONL 写入失败: {e}")

    # ──────────────────────────────────────────────────────────────
    # 查询接口
    # ──────────────────────────────────────────────────────────────

    def get_logs(
        self,
        limit: int = 100,
        role_id: Optional[str] = None,
        since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        查询使用记录

        Args:
            limit: 返回上限
            role_id: 按角色过滤
            since: 起始时间（ISO 格式）

        Returns:
            记录列表
        """
        if self.use_sqlite:
            return self._get_logs_sqlite(limit=limit, role_id=role_id, since=since)
        else:
            return self._get_logs_jsonl(limit=limit, role_id=role_id)

    def _get_logs_sqlite(
        self,
        limit: int,
        role_id: Optional[str],
        since: Optional[str],
    ) -> List[Dict[str, Any]]:
        """从 SQLite 查询"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                conditions: List[str] = []
                params: List[Any] = []

                if role_id:
                    conditions.append("role_id = ?")
                    params.append(role_id)
                if since:
                    conditions.append("timestamp >= ?")
                    params.append(since)

                where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
                params.append(limit)

                rows = conn.execute(
                    f"SELECT * FROM usage_logs {where} ORDER BY timestamp DESC LIMIT ?",
                    params,
                ).fetchall()

                result = []
                for row in rows:
                    rec = dict(row)
                    for field in ("selected_examples", "user_feedback", "metadata"):
                        if rec.get(field):
                            try:
                                rec[field] = json.loads(rec[field])
                            except Exception:
                                pass
                    result.append(rec)
                return result
        except Exception as e:
            logger.error(f"[UsageTracker] SQLite 查询失败: {e}")
            return []

    def _get_logs_jsonl(
        self,
        limit: int,
        role_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        """从 JSONL 文件查询（仅当日）"""
        results: List[Dict[str, Any]] = []
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = self.data_dir / f"usage_{today}.jsonl"
            if not log_file.exists():
                return []
            with open(log_file, encoding="utf-8") as f:
                for line in f:
                    rec = json.loads(line.strip())
                    if role_id and rec.get("role_id") != role_id:
                        continue
                    results.append(rec)
                    if len(results) >= limit:
                        break
        except Exception as e:
            logger.error(f"[UsageTracker] JSONL 查询失败: {e}")
        return results

    def get_example_stats(
        self,
        role_id: str,
        example_id: str,
    ) -> Dict[str, Any]:
        """
        汇总某个示例的使用统计

        Returns:
            {"total_uses": int, "positive_feedback": int, "negative_feedback": int, ...}
        """
        logs = self.get_logs(limit=10000, role_id=role_id)
        total = 0
        positive = 0
        negative = 0
        total_rating = 0.0
        rating_count = 0

        for log in logs:
            examples = log.get("selected_examples") or []
            if example_id not in examples:
                continue
            total += 1
            fb = log.get("user_feedback") or {}
            if isinstance(fb, dict):
                if fb.get("liked") is True:
                    positive += 1
                if fb.get("edited") is True or fb.get("liked") is False:
                    negative += 1
                if "rating" in fb:
                    total_rating += float(fb["rating"])
                    rating_count += 1

        return {
            "example_id": example_id,
            "role_id": role_id,
            "total_uses": total,
            "positive_feedback": positive,
            "negative_feedback": negative,
            "avg_rating": round(total_rating / rating_count, 2) if rating_count else None,
        }
