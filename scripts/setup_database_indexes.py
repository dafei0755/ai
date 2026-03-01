"""
数据库索引配置脚本

创建PostgreSQL + pgvector的高性能索引
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from sqlalchemy import text


def create_vector_index(db):
    """创建向量索引（IVFFlat）"""
    logger.info("=" * 60)
    logger.info("创建向量索引")
    logger.info("=" * 60)

    try:
        with db.engine.connect() as conn:
            # 1. 创建pgvector扩展
            logger.info("📦 创建pgvector扩展...")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            logger.success("✅ pgvector扩展已创建")

            # 2. 创建IVFFlat索引（向量相似度搜索）
            logger.info("📊 创建IVFFlat向量索引...")
            conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_description_vector_ivfflat
                ON external_projects
                USING ivfflat (description_vector vector_cosine_ops)
                WITH (lists = 100)
            """
                )
            )
            conn.commit()
            logger.success("✅ IVFFlat向量索引已创建")

            return True

    except Exception as e:
        logger.error(f"❌ 创建向量索引失败: {e}")
        logger.info("💡 可能原因：")
        logger.info("   1. PostgreSQL未安装pgvector扩展")
        logger.info("   2. 数据库连接失败")
        logger.info("   3. 权限不足")
        return False


def create_full_text_index(db):
    """创建全文搜索索引"""
    logger.info("\n" + "=" * 60)
    logger.info("创建全文搜索索引")
    logger.info("=" * 60)

    try:
        with db.engine.connect() as conn:
            # 1. 添加tsvector列（如果不存在）
            logger.info("📝 添加全文搜索列...")
            conn.execute(
                text(
                    """
                ALTER TABLE external_projects
                ADD COLUMN IF NOT EXISTS search_vector tsvector
            """
                )
            )
            conn.commit()

            # 2. 创建触发器更新search_vector
            logger.info("🔧 创建更新触发器...")
            conn.execute(
                text(
                    """
                CREATE OR REPLACE FUNCTION update_search_vector()
                RETURNS trigger AS $$
                BEGIN
                    NEW.search_vector :=
                        setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
                        setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B');
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql
            """
                )
            )
            conn.commit()

            conn.execute(
                text(
                    """
                DROP TRIGGER IF EXISTS tsvector_update ON external_projects
            """
                )
            )
            conn.execute(
                text(
                    """
                CREATE TRIGGER tsvector_update
                BEFORE INSERT OR UPDATE ON external_projects
                FOR EACH ROW EXECUTE FUNCTION update_search_vector()
            """
                )
            )
            conn.commit()
            logger.success("✅ 触发器已创建")

            # 3. 创建GIN索引
            logger.info("📊 创建GIN全文索引...")
            conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_search_vector_gin
                ON external_projects
                USING gin(search_vector)
            """
                )
            )
            conn.commit()
            logger.success("✅ GIN全文索引已创建")

            return True

    except Exception as e:
        logger.error(f"❌ 创建全文索引失败: {e}")
        return False


def create_performance_indexes(db):
    """创建性能优化索引"""
    logger.info("\n" + "=" * 60)
    logger.info("创建性能优化索引")
    logger.info("=" * 60)

    indexes = [
        # 复合索引：来源 + 质量分数
        (
            "idx_source_quality",
            "CREATE INDEX IF NOT EXISTS idx_source_quality ON external_projects(source, quality_score DESC)",
        ),
        # 复合索引：分类 + 年份
        (
            "idx_category_year",
            "CREATE INDEX IF NOT EXISTS idx_category_year ON external_projects(primary_category, year DESC)",
        ),
        # 复合索引：质量分数 + 浏览量
        (
            "idx_quality_views",
            "CREATE INDEX IF NOT EXISTS idx_quality_views ON external_projects(quality_score DESC, views DESC)",
        ),
        # 时间索引：爬取时间
        ("idx_crawled_at", "CREATE INDEX IF NOT EXISTS idx_crawled_at ON external_projects(crawled_at DESC)"),
        # JSONB索引：位置信息
        ("idx_location_gin", "CREATE INDEX IF NOT EXISTS idx_location_gin ON external_projects USING gin(location)"),
        # JSONB索引：建筑师信息
        (
            "idx_architects_gin",
            "CREATE INDEX IF NOT EXISTS idx_architects_gin ON external_projects USING gin(architects)",
        ),
    ]

    success_count = 0
    for idx_name, sql in indexes:
        try:
            logger.info(f"📊 创建索引: {idx_name}...")
            with db.engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
            logger.success(f"✅ {idx_name} 已创建")
            success_count += 1
        except Exception as e:
            logger.error(f"❌ {idx_name} 创建失败: {e}")

    logger.info(f"\n✅ 成功创建 {success_count}/{len(indexes)} 个索引")
    return success_count == len(indexes)


def analyze_tables(db):
    """分析表统计信息（优化查询计划）"""
    logger.info("\n" + "=" * 60)
    logger.info("分析表统计信息")
    logger.info("=" * 60)

    try:
        with db.engine.connect() as conn:
            logger.info("📊 运行ANALYZE命令...")
            conn.execute(text("ANALYZE external_projects"))
            conn.execute(text("ANALYZE external_project_images"))
            conn.execute(text("ANALYZE sync_history"))
            conn.execute(text("ANALYZE quality_issues"))
            conn.commit()
            logger.success("✅ 表统计信息已更新")
            return True
    except Exception as e:
        logger.error(f"❌ 分析表失败: {e}")
        return False


def show_index_stats(db):
    """显示索引统计信息"""
    logger.info("\n" + "=" * 60)
    logger.info("索引统计信息")
    logger.info("=" * 60)

    try:
        with db.engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                FROM pg_catalog.pg_stat_user_indexes
                WHERE schemaname = 'public'
                AND tablename LIKE 'external%'
                ORDER BY pg_relation_size(indexrelid) DESC
            """
                )
            )

            indexes = result.fetchall()
            if indexes:
                logger.info(f"📊 找到 {len(indexes)} 个索引:")
                for idx in indexes:
                    logger.info(f"  - {idx.tablename}.{idx.indexname}: {idx.index_size}")
            else:
                logger.warning("⚠️ 未找到任何索引")

            return True
    except Exception as e:
        logger.warning(f"⚠️ 获取索引统计失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("🚀 开始配置数据库索引")

    # 导入数据库
    try:
        from intelligent_project_analyzer.external_data_system import get_external_db
    except ImportError as e:
        logger.error(f"❌ 导入失败: {e}")
        logger.info("💡 请确保已完成重构：external_data_system模块")
        return 1

    # 获取数据库实例
    db = get_external_db()

    # 检查数据库类型
    if "sqlite" in db.database_url.lower():
        logger.warning("⚠️ 当前使用SQLite数据库")
        logger.info("💡 向量搜索和全文索引需要PostgreSQL + pgvector")
        logger.info("💡 跳过高级索引创建...")
        return 0

    # 执行索引创建
    results = {
        "向量索引": create_vector_index(db),
        "全文索引": create_full_text_index(db),
        "性能索引": create_performance_indexes(db),
        "表分析": analyze_tables(db),
    }

    # 显示统计
    show_index_stats(db)

    # 汇总结果
    logger.info("\n" + "=" * 60)
    logger.info("配置结果汇总")
    logger.info("=" * 60)

    for name, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        logger.info(f"{name}: {status}")

    success_count = sum(1 for v in results.values() if v)
    total = len(results)

    if success_count == total:
        logger.success(f"\n🎉 所有索引配置完成！({success_count}/{total})")
        return 0
    else:
        logger.warning(f"\n⚠️ 部分索引配置失败 ({success_count}/{total})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
