"""
数据库迁移脚本 v7.501 - 双轨分类系统

为分类学习系统的表添加 task_type 字段，支持区分用户需求和研究任务。

Changes:
- taxonomy_concept_discoveries 表: 添加 task_type 字段（默认 user_demand）
- taxonomy_emerging_types 表: 添加 task_type 字段（默认 user_demand）

Usage:
    python scripts/migrate_taxonomy_v7.501_dual_track.py
"""

import sqlite3
from pathlib import Path
from datetime import datetime


def migrate_database():
    """执行数据库迁移"""
    data_dir = Path(__file__).parent.parent / "data"
    db_path = data_dir / "archived_sessions.db"

    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    print(f"📁 数据库路径: {db_path}")
    print(f"📏 当前大小: {db_path.stat().st_size / 1024 / 1024:.2f} MB")
    print()

    # 备份数据库
    backup_path = data_dir / f"archived_sessions_backup_v7.501_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    print(f"📦 创建备份: {backup_path.name}")

    import shutil

    shutil.copy2(db_path, backup_path)
    print(f"✅ 备份完成")
    print()

    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("=" * 70)
        print("🚀 开始数据库迁移 v7.501 - 双轨分类系统")
        print("=" * 70)
        print()

        # 1. 检查 taxonomy_concept_discoveries 表是否已有 task_type 字段
        cursor.execute("PRAGMA table_info(taxonomy_concept_discoveries)")
        columns = [col[1] for col in cursor.fetchall()]

        if "task_type" not in columns:
            print("📊 [1/2] 为 taxonomy_concept_discoveries 表添加 task_type 字段...")
            cursor.execute(
                """
                ALTER TABLE taxonomy_concept_discoveries
                ADD COLUMN task_type VARCHAR(20) DEFAULT 'user_demand'
            """
            )
            conn.commit()
            print("   ✅ taxonomy_concept_discoveries.task_type 字段已添加")
        else:
            print("⏭️  [1/2] taxonomy_concept_discoveries 表已有 task_type 字段，跳过")
        print()

        # 2. 检查 taxonomy_emerging_types 表是否已有 task_type 字段
        cursor.execute("PRAGMA table_info(taxonomy_emerging_types)")
        columns = [col[1] for col in cursor.fetchall()]

        if "task_type" not in columns:
            print("📊 [2/2] 为 taxonomy_emerging_types 表添加 task_type 字段...")
            cursor.execute(
                """
                ALTER TABLE taxonomy_emerging_types
                ADD COLUMN task_type VARCHAR(20) DEFAULT 'user_demand'
            """
            )
            conn.commit()
            print("   ✅ taxonomy_emerging_types.task_type 字段已添加")
        else:
            print("⏭️  [2/2] taxonomy_emerging_types 表已有 task_type 字段，跳过")
        print()

        # 3. 验证迁移结果
        print("🔍 验证迁移结果...")

        cursor.execute("PRAGMA table_info(taxonomy_concept_discoveries)")
        concept_columns = [col[1] for col in cursor.fetchall()]

        cursor.execute("PRAGMA table_info(taxonomy_emerging_types)")
        emerging_columns = [col[1] for col in cursor.fetchall()]

        if "task_type" in concept_columns and "task_type" in emerging_columns:
            print("   ✅ 所有表结构验证通过")
        else:
            print("   ❌ 表结构验证失败")
            return False
        print()

        # 4. 显示统计信息
        print("📈 数据统计:")

        cursor.execute("SELECT COUNT(*) FROM taxonomy_concept_discoveries")
        concept_count = cursor.fetchone()[0]
        print(f"   - 概念发现记录: {concept_count}")

        cursor.execute("SELECT COUNT(*) FROM taxonomy_emerging_types")
        emerging_count = cursor.fetchone()[0]
        print(f"   - 新兴标签记录: {emerging_count}")
        print()

        print("=" * 70)
        print("✅ 数据库迁移完成！")
        print("=" * 70)
        print()

        print("📝 迁移摘要:")
        print(f"   - 备份文件: {backup_path.name}")
        print(f"   - 新增字段: task_type (VARCHAR(20), 默认 'user_demand')")
        print(f"   - 影响表数: 2 (taxonomy_concept_discoveries, taxonomy_emerging_types)")
        print()

        print("🎯 下一步:")
        print("   1. 重启后端服务使配置生效")
        print("   2. 运行诊断脚本验证双轨分类系统:")
        print("      python diagnose_dimension_classification.py")
        print()

        return True

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    success = migrate_database()
    exit(0 if success else 1)
