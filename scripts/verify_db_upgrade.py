"""
数据库升级后一键验证脚本

检查所有数据库的 schema 完整性，确保升级后系统可正常运行。
退出码: 0 = 全部通过，1 = 有关键检查失败。

用法:
    python scripts/verify_db_upgrade.py
"""

import os
import sys
import sqlite3
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="<level>{message}</level>", level="DEBUG")

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "
INFO = "ℹ️ "

_results = {"pass": 0, "fail": 0, "warn": 0}


def check(name: str, ok: bool, detail: str = ""):
    if ok:
        _results["pass"] += 1
        logger.info(f"{PASS} {name}" + (f"  —  {detail}" if detail else ""))
    else:
        _results["fail"] += 1
        logger.error(f"{FAIL} {name}" + (f"  —  {detail}" if detail else ""))


def warn(name: str, detail: str = ""):
    _results["warn"] += 1
    logger.warning(f"{WARN}{name}" + (f"  —  {detail}" if detail else ""))


def section(title: str):
    logger.info(f"\n{'=' * 60}")
    logger.info(f"  {title}")
    logger.info(f"{'=' * 60}")


# ============================================================
# 1. 导入一致性检查
# ============================================================
def check_import_consistency():
    section("1. 导入路径一致性")

    # 旧模型文件应发出 DeprecationWarning 并重定向
    try:
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from intelligent_project_analyzer.models import external_projects as _old  # noqa

            got_warning = any(issubclass(x.category, DeprecationWarning) for x in w)
        check("旧模型文件发出 DeprecationWarning", got_warning, "已重定向到新路径" if got_warning else "缺少废弃警告，请检查旧文件")
    except ImportError:
        check("旧模型文件已删除（可接受）", True)
    except Exception as e:
        warn(f"旧模型导入检查异常: {e}")

    # 新模型可正常导入
    try:
        from intelligent_project_analyzer.external_data_system.models.external_projects import (
            ExternalProject,
            ProjectDiscovery,
            get_external_db,
        )

        check("新模型路径导入正常", True)
    except ImportError as e:
        check("新模型路径导入正常", False, str(e))

    # Celery tasks 不再使用旧路径
    tasks_path = project_root / "intelligent_project_analyzer" / "tasks" / "external_data_tasks.py"
    if tasks_path.exists():
        content = tasks_path.read_text(encoding="utf-8")
        uses_old = "from intelligent_project_analyzer.models.external_projects import" in content
        check("Celery tasks 不再直接使用旧模型路径", not uses_old, "仍有直接旧路径导入！" if uses_old else "已全部切换到新路径")
    else:
        warn("external_data_tasks.py 不存在")


# ============================================================
# 2. SQLite archived_sessions.db 检查
# ============================================================
def check_archived_sessions_db():
    section("2. SQLite: archived_sessions.db")

    db_path = project_root / "data" / "archived_sessions.db"
    if not db_path.exists():
        warn("archived_sessions.db 不存在（首次启动后会自动创建）")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # archived_sessions 表
    cursor.execute("PRAGMA table_info(archived_sessions)")
    cols = {row[1] for row in cursor.fetchall()}
    required_sessions = {
        "session_id",
        "user_id",
        "user_input",
        "status",
        "mode",
        "analysis_mode",
        "display_name",
        "pinned",
        "tags",
        "created_at",
        "archived_at",
    }
    missing = required_sessions - cols
    check("archived_sessions 列完整", not missing, f"缺少: {missing}" if missing else f"共 {len(cols)} 列")

    # archived_search_sessions 表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='archived_search_sessions'")
    if cursor.fetchone():
        cursor.execute("PRAGMA table_info(archived_search_sessions)")
        search_cols = {row[1] for row in cursor.fetchall()}
        v7_required = {
            "is_deep_mode",
            "thinking_content",
            "answer_content",
            "search_plan",
            "rounds",
            "total_rounds",
            "l0_content",
            "problem_solving_thinking",
            "structured_info",
            "search_framework",
            "search_master_line",
            "current_round",
            "overall_completeness",
            "deep_analysis_result",
            "four_missions_result",
            "quality_assessment",
            "answer_thinking_content",
        }
        missing_v7 = v7_required - search_cols
        check(
            "archived_search_sessions v7.x 列完整",
            not missing_v7,
            f"缺少 {len(missing_v7)} 列: {missing_v7}" if missing_v7 else f"共 {len(search_cols)} 列",
        )
    else:
        warn("archived_search_sessions 表不存在（首次使用搜索功能后会自动创建）")

    # taxonomy 表
    for tbl in [
        "taxonomy_extended_types",
        "taxonomy_emerging_types",
        "taxonomy_user_feedback",
        "taxonomy_user_suggestions",
        "taxonomy_concept_discoveries",
    ]:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tbl}'")
        check(f"taxonomy 表 {tbl} 存在", cursor.fetchone() is not None)

    # taxonomy task_type 列
    for tbl in ("taxonomy_concept_discoveries", "taxonomy_emerging_types"):
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tbl}'")
        if cursor.fetchone():
            cursor.execute(f"PRAGMA table_info({tbl})")
            tcols = {row[1] for row in cursor.fetchall()}
            check(f"{tbl}.task_type 列存在", "task_type" in tcols)

    conn.close()


# ============================================================
# 3. SQLite ontology_learning.db 检查
# ============================================================
def check_ontology_db():
    section("3. SQLite: ontology_learning.db")

    db_path = project_root / "data" / "ontology_learning.db"
    if not db_path.exists():
        warn("ontology_learning.db 不存在")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    for tbl in [
        "dimensions",
        "dimension_relations",
        "project_types",
        "learning_sessions",
        "dimension_candidates",
        "dimension_usage_log",
        "optimization_suggestions",
        "project_type_candidates",
        "system_config",
    ]:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tbl}'")
        check(f"ontology 表 {tbl}", cursor.fetchone() is not None)

    try:
        cursor.execute("SELECT value FROM system_config WHERE key='schema_version'")
        row = cursor.fetchone()
        check(f"ontology schema_version = {row[0] if row else '(缺失)'}", row is not None)
    except Exception:
        warn("system_config 查询失败")

    conn.close()


# ============================================================
# 4. SQLite workflow.db 检查
# ============================================================
def check_workflow_db():
    section("4. SQLite: workflow.db (LangGraph Checkpoint)")

    db_path = project_root / "data" / "checkpoints" / "workflow.db"
    if not db_path.exists():
        warn("workflow.db 不存在（首次启动服务后会自动创建）")
        return

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        check(f"workflow.db 可打开", len(tables) >= 0, f"包含 {len(tables)} 张表: {tables}")
        conn.close()
    except Exception as e:
        check("workflow.db 可打开", False, f"可能损坏或版本不兼容: {e}（服务启动时会自动重建）")


# ============================================================
# 5. PostgreSQL 检查
# ============================================================
def check_postgresql():
    section("5. PostgreSQL: external_projects")

    db_url = os.getenv(
        "EXTERNAL_DB_URL",
        "postgresql://postgres:password@localhost:5432/external_projects",
    )

    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(db_url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='external_projects' "
                    "ORDER BY ordinal_position"
                )
            )
            db_cols = {row[0] for row in result.fetchall()}

            if not db_cols:
                warn("external_projects 表不存在（需运行 init_external_db.py 初始化）")
                return

            # 对比新模型
            try:
                from intelligent_project_analyzer.external_data_system.models.external_projects import ExternalProject

                model_cols = {c.name for c in ExternalProject.__table__.columns}
                missing = model_cols - db_cols
                extra = db_cols - model_cols
                check(
                    "PostgreSQL 列完整性（对比新模型）",
                    not missing,
                    f"缺少 {len(missing)} 列: {missing}  →  运行 migrate_add_bilingual_fields_pg.py"
                    if missing
                    else f"共 {len(db_cols)} 列，与模型一致",
                )
                if extra:
                    logger.info(f"{INFO}数据库多余列（可忽略）: {extra}")
            except Exception as e:
                warn(f"模型导入失败，跳过列对比: {e}")

            # project_discovery 表
            result = conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='project_discovery'"
                )
            )
            disc_cols = {row[0] for row in result.fetchall()}
            check("project_discovery 表存在", len(disc_cols) > 0, f"共 {len(disc_cols)} 列" if disc_cols else "表不存在")

            # PostgreSQL 扩展
            for ext in ["pg_trgm", "btree_gin"]:
                result = conn.execute(text(f"SELECT 1 FROM pg_extension WHERE extname = '{ext}'"))
                check(
                    f"PostgreSQL 扩展 {ext}",
                    result.fetchone() is not None,
                    "已安装" if result else "未安装（运行 setup_database_indexes.py）",
                )

    except ImportError:
        warn("sqlalchemy 未安装，跳过 PostgreSQL 检查")
    except Exception as e:
        warn(f"PostgreSQL 连接失败（爬虫功能不可用）: {e}")


# ============================================================
# 6. LangGraph 版本检查
# ============================================================
def check_langgraph_version():
    section("6. 关键依赖版本检查")

    try:
        import langgraph

        version = getattr(langgraph, "__version__", "未知")
        check(f"langgraph 已安装 (v{version})", True)
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver  # noqa

            check("langgraph.checkpoint.sqlite.SqliteSaver 可导入", True)
        except ImportError as e:
            check("langgraph.checkpoint.sqlite.SqliteSaver 可导入", False, str(e))
    except ImportError as e:
        check("langgraph 已安装", False, str(e))

    for pkg in ("aiosqlite", "redis", "pymilvus"):
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "已安装")
            check(f"{pkg} 已安装 ({ver})", True)
        except ImportError:
            warn(f"{pkg} 未安装（部分功能降级）")


# ============================================================
# 7. Redis 连通性
# ============================================================
def check_redis():
    section("7. Redis 连通性")

    try:
        import redis as redis_pkg

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis_pkg.from_url(redis_url, socket_timeout=3)
        r.ping()
        check("Redis 连接正常", True, redis_url)
    except ImportError:
        warn("redis 包未安装（会话将使用内存模式）")
    except Exception as e:
        warn(f"Redis 不可连接: {e}（会话将自动回退到内存模式）")


# ============================================================
# 汇总
# ============================================================
def main():
    logger.info("🔍 数据库升级后全面验证")
    logger.info(f"项目根目录: {project_root}\n")

    check_import_consistency()
    check_archived_sessions_db()
    check_ontology_db()
    check_workflow_db()
    check_postgresql()
    check_langgraph_version()
    check_redis()

    section("验证汇总")
    logger.info(f"  {PASS} 通过: {_results['pass']}")
    if _results["fail"]:
        logger.error(f"  {FAIL} 失败: {_results['fail']}")
    if _results["warn"]:
        logger.warning(f"  {WARN}警告: {_results['warn']}")
    logger.info(f"  总计: {_results['pass'] + _results['fail'] + _results['warn']} 项检查")

    if _results["fail"] == 0:
        logger.info("\n🎉 所有关键检查通过，系统可安全启动。")
    else:
        logger.error(f"\n⛔ 有 {_results['fail']} 项关键检查失败，请先修复再启动服务。")
        sys.exit(1)


if __name__ == "__main__":
    main()
