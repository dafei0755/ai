"""
数据库管理器 (Database Manager)

管理本体论学习系统的SQLite数据库连接和操作。

核心功能:
- 初始化数据库Schema
- 执行数据库迁移
- 提供基础CRUD操作
- 管理连接池

版本: v3.0
创建日期: 2026-02-10
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from loguru import logger
from contextlib import contextmanager


class DatabaseManager:
    """
    本体论学习数据库管理器

    负责数据库的创建、迁移、查询等操作
    """

    def __init__(self, db_path: str = "data/ontology_learning.db"):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.schema_file = Path(__file__).parent / "database_schema.sql"

        # 确保数据目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f" 初始化数据库管理器: {self.db_path}")

    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # 允许通过列名访问
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f" 数据库操作失败: {e}")
            raise
        finally:
            conn.close()

    def initialize(self) -> bool:
        """
        初始化数据库（创建所有表）

        Returns:
            是否成功初始化
        """
        try:
            logger.info(" 开始初始化数据库...")

            # 读取SQL脚本
            with open(self.schema_file, "r", encoding="utf-8") as f:
                schema_sql = f.read()

            # 执行Schema创建
            with self.get_connection() as conn:
                # 分割成多个语句执行
                statements = [s.strip() for s in schema_sql.split(";") if s.strip()]
                for stmt in statements:
                    if stmt:
                        conn.execute(stmt)

            logger.info(" 数据库初始化完成")
            return True

        except Exception as e:
            logger.error(f" 数据库初始化失败: {e}")
            return False

    def check_exists(self) -> bool:
        """检查数据库是否已存在"""
        return self.db_path.exists()

    def get_schema_version(self) -> str:
        """获取当前Schema版本"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT value FROM system_config WHERE key = 'schema_version'")
                result = cursor.fetchone()
                return result[0] if result else "unknown"
        except Exception:
            return "unknown"

    # ============================================================
    # 维度 (Dimensions) 操作
    # ============================================================

    def insert_dimension(
        self, name: str, category: str, project_type: str, description: str, ask_yourself: str, examples: str, **kwargs
    ) -> Optional[int]:
        """
        插入新维度

        Returns:
            维度ID，失败返回None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO dimensions (
                        name, category, project_type, description,
                        ask_yourself, examples, created_by, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        category,
                        project_type,
                        description,
                        ask_yourself,
                        examples,
                        kwargs.get("created_by", "system"),
                        kwargs.get("source", "manual"),
                    ),
                )
                dim_id = cursor.lastrowid
                logger.info(f" 插入维度: {name} (ID: {dim_id})")
                return dim_id
        except sqlite3.IntegrityError as e:
            logger.warning(f"️ 维度已存在: {name}")
            return None
        except Exception as e:
            logger.error(f" 插入维度失败: {e}")
            return None

    def get_dimension(self, dimension_id: int) -> Optional[Dict[str, Any]]:
        """获取维度详情"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM dimensions WHERE id = ?", (dimension_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f" 获取维度失败: {e}")
            return None

    def update_dimension_usage(self, dimension_id: int):
        """更新维度使用计数"""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """
                    UPDATE dimensions
                    SET usage_count = usage_count + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (dimension_id,),
                )
        except Exception as e:
            logger.error(f" 更新使用计数失败: {e}")

    def get_dimensions_by_project_type(self, project_type: str, status: str = "active") -> List[Dict[str, Any]]:
        """获取指定项目类型的所有维度"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM dimensions
                    WHERE project_type = ? AND status = ?
                    ORDER BY usage_count DESC
                    """,
                    (project_type, status),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f" 查询维度失败: {e}")
            return []

    # ============================================================
    # 学习会话 (Learning Sessions) 操作
    # ============================================================

    def log_learning_session(
        self,
        session_id: str,
        project_type: str,
        expert_roles: List[str],
        extracted_dimensions: List[Dict[str, Any]],
        quality_metrics: Dict[str, Any],
    ) -> bool:
        """记录学习会话"""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO learning_sessions (
                        session_id, project_type, expert_roles,
                        extracted_dimensions, quality_metrics
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        project_type,
                        json.dumps(expert_roles),
                        json.dumps(extracted_dimensions),
                        json.dumps(quality_metrics),
                    ),
                )
                logger.info(f" 记录学习会话: {session_id}")
                return True
        except Exception as e:
            logger.error(f" 记录学习会话失败: {e}")
            return False

    # ============================================================
    # 候选维度 (Dimension Candidates) 操作
    # ============================================================

    def add_candidate(
        self, dimension_data: Dict[str, Any], confidence_score: float, source_session_id: str = None
    ) -> Optional[int]:
        """添加候选维度"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO dimension_candidates (
                        dimension_data, confidence_score, source_session_id
                    ) VALUES (?, ?, ?)
                    """,
                    (json.dumps(dimension_data), confidence_score, source_session_id),
                )
                candidate_id = cursor.lastrowid
                logger.info(f" 添加候选维度 (ID: {candidate_id})")
                return candidate_id
        except Exception as e:
            logger.error(f" 添加候选维度失败: {e}")
            return None

    def get_pending_candidates(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取待审核的候选维度"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM v_pending_candidates
                    LIMIT ?
                    """,
                    (limit,),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f" 获取候选维度失败: {e}")
            return []

    def approve_candidate(self, candidate_id: int, reviewer_id: str = "system") -> bool:
        """批准候选维度"""
        try:
            # 1. 获取候选数据
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT dimension_data FROM dimension_candidates WHERE id = ?", (candidate_id,))
                row = cursor.fetchone()
                if not row:
                    return False

                dim_data = json.loads(row[0])

            # 2. 插入到维度表
            dim_id = self.insert_dimension(
                name=dim_data["name"],
                category=dim_data["category"],
                project_type=dim_data["project_type"],
                description=dim_data["description"],
                ask_yourself=dim_data["ask_yourself"],
                examples=dim_data["examples"],
                created_by="ai_approved",
                source=f"candidate_{candidate_id}",
            )

            if not dim_id:
                return False

            # 3. 更新候选状态
            with self.get_connection() as conn:
                conn.execute(
                    """
                    UPDATE dimension_candidates
                    SET review_status = 'approved',
                        reviewer_id = ?,
                        reviewed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (reviewer_id, candidate_id),
                )

            logger.info(f" 批准候选维度: {dim_data['name']}")
            return True

        except Exception as e:
            logger.error(f" 批准候选维度失败: {e}")
            return False

    def reject_candidate(self, candidate_id: int, reviewer_id: str = "system", reason: str = None) -> bool:
        """
        拒绝候选维度

        Args:
            candidate_id: 候选ID
            reviewer_id: 审核人ID
            reason: 拒绝原因（可选）
        """
        try:
            with self.get_connection() as conn:
                # 检查候选是否存在
                cursor = conn.execute("SELECT id FROM dimension_candidates WHERE id = ?", (candidate_id,))
                if not cursor.fetchone():
                    logger.warning(f"️ 候选维度不存在: {candidate_id}")
                    return False

                # 更新状态为 rejected
                conn.execute(
                    """
                    UPDATE dimension_candidates
                    SET review_status = 'rejected',
                        reviewer_id = ?,
                        reviewed_at = CURRENT_TIMESTAMP,
                        dimension_data = json_set(dimension_data, '$.reject_reason', ?)
                    WHERE id = ?
                    """,
                    (reviewer_id, reason or "未提供原因", candidate_id),
                )

                logger.info(f" 拒绝候选维度 {candidate_id}: {reason}")
                return True

        except Exception as e:
            logger.error(f" 拒绝候选维度失败: {e}")
            return False

    def get_candidate_statistics(self) -> Dict[str, Any]:
        """
        获取候选维度统计信息

        Returns:
            {
                "pending": 10,
                "approved": 25,
                "rejected": 5,
                "total": 40,
                "high_confidence": 8  # confidence > 0.8
            }
        """
        try:
            with self.get_connection() as conn:
                stats = {}

                # 按状态统计
                cursor = conn.execute(
                    """
                    SELECT review_status, COUNT(*) as count
                    FROM dimension_candidates
                    GROUP BY review_status
                """
                )
                for row in cursor.fetchall():
                    stats[row[0]] = row[1]

                # 总数
                cursor = conn.execute("SELECT COUNT(*) FROM dimension_candidates")
                stats["total"] = cursor.fetchone()[0]

                # 高置信度候选（confidence > 0.8）
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM dimension_candidates
                    WHERE confidence_score > 0.8 AND review_status = 'pending'
                """
                )
                stats["high_confidence"] = cursor.fetchone()[0]

                return stats

        except Exception as e:
            logger.error(f" 获取候选统计失败: {e}")
            return {}

    def batch_approve_candidates(self, candidate_ids: List[int], reviewer_id: str = "system") -> Dict[str, Any]:
        """
        批量批准候选维度

        Args:
            candidate_ids: 候选ID列表
            reviewer_id: 审核人ID

        Returns:
            {
                "success": [1, 3, 5],
                "failed": [2, 4],
                "total": 5
            }
        """
        success = []
        failed = []

        for cid in candidate_ids:
            if self.approve_candidate(cid, reviewer_id):
                success.append(cid)
            else:
                failed.append(cid)

        logger.info(f" 批量批准结果: 成功 {len(success)}, 失败 {len(failed)}")

        return {"success": success, "failed": failed, "total": len(candidate_ids)}

    # ============================================================
    # 项目类型候选 (Project Type Candidates) 操作
    # ============================================================

    def add_type_candidate(self, candidate: Dict[str, Any]) -> Optional[int]:
        """
        新增项目类型候选。

        Args:
            candidate: 候选数据字典（需含 type_id_suggestion, name_zh, source）

        Returns:
            候选ID，失败返回 None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO project_type_candidates (
                        type_id_suggestion, name_zh, name_en, description,
                        source, source_session_id,
                        sample_inputs, occurrence_count,
                        suggested_keywords, suggested_secondary_keywords,
                        confidence_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        candidate.get("type_id_suggestion", ""),
                        candidate.get("name_zh", ""),
                        candidate.get("name_en", ""),
                        candidate.get("description", ""),
                        candidate.get("source", "user_input"),
                        candidate.get("source_session_id"),
                        json.dumps(candidate.get("sample_inputs", []), ensure_ascii=False),
                        candidate.get("occurrence_count", 1),
                        json.dumps(candidate.get("suggested_keywords", []), ensure_ascii=False),
                        json.dumps(candidate.get("suggested_secondary_keywords", []), ensure_ascii=False),
                        candidate.get("confidence_score", 0.5),
                    ),
                )
                cid = cursor.lastrowid
                logger.info(f" 添加类型候选 {candidate.get('type_id_suggestion')} (ID: {cid})")
                return cid
        except Exception as e:
            logger.error(f" 添加类型候选失败: {e}")
            return None

    def get_pending_type_candidates(
        self,
        limit: int = 50,
        status: str = "pending",
    ) -> List[Dict[str, Any]]:
        """获取待审核的项目类型候选列表，按置信度×出现次数降序。"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM project_type_candidates
                    WHERE review_status = ?
                    ORDER BY (confidence_score * occurrence_count) DESC, created_at ASC
                    LIMIT ?
                    """,
                    (status, limit),
                )
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    d = dict(row)
                    # 反序列化 JSON 字段
                    for field in ("sample_inputs", "suggested_keywords", "suggested_secondary_keywords"):
                        try:
                            d[field] = json.loads(d.get(field) or "[]")
                        except Exception:
                            d[field] = []
                    results.append(d)
                return results
        except Exception as e:
            logger.error(f" 获取类型候选失败: {e}")
            return []

    def get_type_candidate_by_id(self, candidate_id: int) -> Optional[Dict[str, Any]]:
        """获取单条类型候选记录。"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM project_type_candidates WHERE id = ?", (candidate_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                d = dict(row)
                for field in ("sample_inputs", "suggested_keywords", "suggested_secondary_keywords"):
                    try:
                        d[field] = json.loads(d.get(field) or "[]")
                    except Exception:
                        d[field] = []
                return d
        except Exception as e:
            logger.error(f" 获取类型候选失败: {e}")
            return None

    def get_type_candidate_by_suggestion(self, type_id_suggestion: str) -> Optional[Dict[str, Any]]:
        """按建议ID查找已有候选（用于去重）。"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM project_type_candidates
                    WHERE type_id_suggestion = ? AND review_status = 'pending'
                    LIMIT 1
                    """,
                    (type_id_suggestion,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f" 查找候选失败: {e}")
            return None

    def increment_type_candidate_count(self, candidate_id: int) -> bool:
        """将候选的出现次数 +1（同一输入模式重复出现时）。"""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """
                    UPDATE project_type_candidates
                    SET occurrence_count = occurrence_count + 1,
                        confidence_score = MIN(0.95, confidence_score + 0.05)
                    WHERE id = ?
                    """,
                    (candidate_id,),
                )
            return True
        except Exception as e:
            logger.error(f" 更新候选次数失败: {e}")
            return False

    def approve_type_candidate(
        self,
        candidate_id: int,
        reviewer_id: str,
        approved_data: Dict[str, Any],
    ) -> bool:
        """
        审批通过类型候选，持久化审批参数。
        （写入扩展 JSON 由 API 层调用 ProjectTypeRegistryWriter 完成）

        Args:
            candidate_id  : 候选ID
            reviewer_id   : 审核人
            approved_data : 审批后的参数（type_id, keywords, priority 等）
        """
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """
                    UPDATE project_type_candidates SET
                        review_status                = 'approved',
                        reviewer_id                  = ?,
                        reviewer_note                = ?,
                        approved_type_id             = ?,
                        approved_keywords            = ?,
                        approved_secondary_keywords  = ?,
                        approved_priority            = ?,
                        approved_min_secondary_hits  = ?,
                        reviewed_at                  = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        reviewer_id,
                        approved_data.get("reviewer_note", ""),
                        approved_data.get("type_id"),
                        json.dumps(approved_data.get("keywords", []), ensure_ascii=False),
                        json.dumps(approved_data.get("secondary_keywords", []), ensure_ascii=False),
                        int(approved_data.get("priority", 6)),
                        int(approved_data.get("min_secondary_hits", 0)),
                        candidate_id,
                    ),
                )
            logger.info(f" 审批通过类型候选 {candidate_id}: {approved_data.get('type_id')}")
            return True
        except Exception as e:
            logger.error(f" 审批类型候选失败: {e}")
            return False

    def reject_type_candidate(
        self,
        candidate_id: int,
        reviewer_id: str,
        reason: str = "",
    ) -> bool:
        """拒绝类型候选。"""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """
                    UPDATE project_type_candidates SET
                        review_status = 'rejected',
                        reviewer_id   = ?,
                        reviewer_note = ?,
                        reviewed_at   = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (reviewer_id, reason, candidate_id),
                )
            logger.info(f" 拒绝类型候选 {candidate_id}: {reason}")
            return True
        except Exception as e:
            logger.error(f" 拒绝类型候选失败: {e}")
            return False

    def get_type_candidate_statistics(self) -> Dict[str, Any]:
        """统计类型候选各状态数量。"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT review_status, COUNT(*) as cnt,
                           AVG(confidence_score) as avg_conf
                    FROM project_type_candidates
                    GROUP BY review_status
                    """
                )
                stats: Dict[str, Any] = {}
                for row in cursor.fetchall():
                    stats[row[0]] = {"count": row[1], "avg_confidence": round(row[2] or 0, 3)}

                cursor = conn.execute("SELECT COUNT(*) FROM project_type_candidates")
                stats["total"] = cursor.fetchone()[0]

                # 高频候选（出现≥3次）
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM project_type_candidates "
                    "WHERE occurrence_count >= 3 AND review_status = 'pending'"
                )
                stats["high_frequency"] = cursor.fetchone()[0]

                return stats
        except Exception as e:
            logger.error(f" 统计类型候选失败: {e}")
            return {}

    # ============================================================
    # 统计和分析
    # ============================================================

    def get_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            with self.get_connection() as conn:
                # 维度统计
                cursor = conn.execute("SELECT COUNT(*) FROM dimensions WHERE status = 'active'")
                active_dimensions = cursor.fetchone()[0]

                # 候选统计
                cursor = conn.execute("SELECT COUNT(*) FROM dimension_candidates WHERE review_status = 'pending'")
                pending_candidates = cursor.fetchone()[0]

                # 会话统计
                cursor = conn.execute("SELECT COUNT(*) FROM learning_sessions")
                total_sessions = cursor.fetchone()[0]

                return {
                    "active_dimensions": active_dimensions,
                    "pending_candidates": pending_candidates,
                    "total_learning_sessions": total_sessions,
                    "schema_version": self.get_schema_version(),
                    "db_size_mb": self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0,
                }
        except Exception as e:
            logger.error(f" 获取统计信息失败: {e}")
            return {}


# ============================================================
# 全局数据库实例
# ============================================================

_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """获取全局数据库管理器实例（首次调用时自动初始化 schema）"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        # 数据库文件不存在或为空时，自动执行 schema 初始化
        db_path = _db_manager.db_path
        if not db_path.exists() or db_path.stat().st_size == 0:
            logger.info(" 数据库为空，自动执行 schema 初始化...")
            _db_manager.initialize()
        else:
            # 文件存在但可能缺少视图（如 v_pending_candidates），做增量补全
            try:
                with _db_manager.get_connection() as conn:
                    conn.execute("SELECT 1 FROM v_pending_candidates LIMIT 1")
            except Exception:
                logger.warning(" 检测到数据库 schema 不完整，重新执行初始化...")
                _db_manager.initialize()
    return _db_manager


def init_database(db_path: str = None) -> bool:
    """初始化数据库（便捷函数）"""
    if db_path:
        db = DatabaseManager(db_path)
    else:
        db = get_db_manager()

    return db.initialize()
