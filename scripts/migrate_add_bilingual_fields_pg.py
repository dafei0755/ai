"""
PostgreSQL 双语字段迁移脚本

为 external_projects 表添加 v2.0 新增的双语和元数据列。
安全地使用 ADD COLUMN IF NOT EXISTS，已存在的列直接跳过。

用法:
    python scripts/migrate_add_bilingual_fields_pg.py
"""

import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from loguru import logger


def get_db_url() -> str:
    return os.getenv(
        "EXTERNAL_DB_URL",
        "postgresql://postgres:password@localhost:5432/external_projects",
    )


# 需要确保存在的列（列名 → DDL 类型定义）
COLUMNS_TO_ADD = {
    # 双语字段
    "title_en": "TEXT",
    "title_zh": "TEXT",
    "description_en": "TEXT",
    "description_zh": "TEXT",
    "lang": "VARCHAR(20)",
    # 翻译元数据
    "translation_engine": "VARCHAR(50)",
    "translation_quality": "REAL",
    "translated_at": "TIMESTAMP",
    "is_human_reviewed": "BOOLEAN DEFAULT FALSE",
    # 内容哈希（防止无意义重写）
    "content_hash": "VARCHAR(64)",
    # catch-all 扩展字段
    "extra_fields": "JSONB",
    # 封面图
    "cover_image_url": "TEXT",
}


def run_migration():
    db_url = get_db_url()
    display_url = db_url.split("@")[-1] if "@" in db_url else db_url
    logger.info(f"🔧 连接数据库: {display_url}")

    engine = create_engine(db_url)

    with engine.connect() as conn:
        # 获取现有列
        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'external_projects'"
            )
        )
        existing_cols = {row[0] for row in result.fetchall()}

        if not existing_cols:
            logger.error("❌ external_projects 表不存在，请先运行 init_external_db.py")
            sys.exit(1)

        logger.info(f"📋 现有列数: {len(existing_cols)}")

        added = []
        for col_name, col_def in COLUMNS_TO_ADD.items():
            if col_name not in existing_cols:
                sql = f"ALTER TABLE external_projects ADD COLUMN IF NOT EXISTS {col_name} {col_def}"
                conn.execute(text(sql))
                added.append(col_name)
                logger.info(f"  ✅ 添加列: {col_name} {col_def}")
            else:
                logger.debug(f"  ⏭️  列已存在: {col_name}")

        # 创建辅助索引（如尚未存在）
        index_sqls = [
            "CREATE INDEX IF NOT EXISTS idx_content_hash ON external_projects(content_hash)",
            "CREATE INDEX IF NOT EXISTS idx_lang ON external_projects(lang)",
            "CREATE INDEX IF NOT EXISTS idx_source_category ON external_projects(source, primary_category)",
        ]
        for sql in index_sqls:
            try:
                conn.execute(text(sql))
            except Exception as e:
                logger.debug(f"索引跳过（可能已存在）: {e}")

        conn.commit()

    if added:
        logger.success(f"✅ 迁移完成: 新增 {len(added)} 列: {added}")
    else:
        logger.info("✅ 所有列均已存在，无需迁移")

    # 验证：对比模型定义
    _verify_columns(engine)


def _verify_columns(engine):
    """验证数据库列与新模型定义一致"""
    try:
        from intelligent_project_analyzer.external_data_system.models.external_projects import ExternalProject

        model_cols = {c.name for c in ExternalProject.__table__.columns}

        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'external_projects'"
                )
            )
            db_cols = {row[0] for row in result.fetchall()}

        missing = model_cols - db_cols
        extra = db_cols - model_cols

        if missing:
            logger.warning(f"⚠️  模型定义但数据库缺少的列: {missing}")
        if extra:
            logger.info(f"ℹ️  数据库多余列（模型中未定义，可忽略）: {extra}")
        if not missing:
            logger.success("✅ 模型定义与数据库列完全一致")
    except Exception as e:
        logger.warning(f"列验证跳过: {e}")


if __name__ == "__main__":
    run_migration()
