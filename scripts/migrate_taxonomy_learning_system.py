"""
维度学习系统数据库迁移脚本

创建分类体系学习所需的5个新表，并插入初始示例数据。
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from intelligent_project_analyzer.models.taxonomy_models import (
    Base,
    TaxonomyConceptDiscovery,
    TaxonomyEmergingType,
    TaxonomyExtendedType,
    TaxonomyUserFeedback,
    TaxonomyUserSuggestion,
)


def get_db_path():
    """获取数据库文件路径"""
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "archived_sessions.db"


def check_existing_tables(engine):
    """检查哪些表已经存在"""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    taxonomy_tables = [
        "taxonomy_extended_types",
        "taxonomy_emerging_types",
        "taxonomy_user_feedback",
        "taxonomy_user_suggestions",
        "taxonomy_concept_discoveries",
    ]

    return {table: table in existing_tables for table in taxonomy_tables}


def create_tables(engine):
    """创建所有新表"""
    print("📦 开始创建表...")

    # 检查已存在的表
    existing = check_existing_tables(engine)

    for table_name, exists in existing.items():
        if exists:
            print(f"  ⏭️  {table_name} 已存在，跳过")
        else:
            print(f"  ➕ 创建 {table_name}...")

    # 创建所有表（已存在的会被跳过）
    Base.metadata.create_all(engine, checkfirst=True)

    print("✅ 表创建完成！")


def insert_mock_data(session):
    """插入初始示例数据"""
    print("\n📝 插入示例数据...")

    # 1. 扩展类型示例（已通过验证的晋升标签）
    extended_examples = [
        TaxonomyExtendedType(
            dimension="emotion",
            type_id="song_chi_gan",
            label_zh="松弛感",
            label_en="Relaxed Living",
            keywords=json.dumps(["松弛", "慢生活", "不用力", "躺平", "佛系"], ensure_ascii=False),
            usage_count=25,
            success_count=22,
            promoted_at=datetime.now() - timedelta(days=15),
            last_used_at=datetime.now() - timedelta(hours=2),
        ),
        TaxonomyExtendedType(
            dimension="style",
            type_id="hou_gong_ye_feng",
            label_zh="后工业风",
            label_en="Post-Industrial",
            keywords=json.dumps(["工业遗产", "锈蚀美学", "机械感", "粗粝"], ensure_ascii=False),
            usage_count=18,
            success_count=16,
            promoted_at=datetime.now() - timedelta(days=20),
            last_used_at=datetime.now() - timedelta(days=1),
        ),
    ]

    # 2. 新兴类型示例（待验证的候选标签）
    emerging_examples = [
        TaxonomyEmergingType(
            dimension="emotion",
            type_id="jue_dui_zi_you",
            label_zh="绝对自由",
            label_en="Absolute Freedom",
            keywords=json.dumps(["完全自由", "无束缚", "极致个性"], ensure_ascii=False),
            case_count=4,
            success_count=3,
            source="user_suggest",
            confidence_score=0.75,
            created_at=datetime.now() - timedelta(days=5),
            last_used_at=datetime.now() - timedelta(hours=6),
        ),
        TaxonomyEmergingType(
            dimension="style",
            type_id="sai_bo_peng_ke",
            label_zh="赛博朋克",
            label_en="Cyberpunk",
            keywords=json.dumps(["霓虹", "科技感", "未来", "赛博"], ensure_ascii=False),
            case_count=6,
            success_count=5,
            source="llm_discover",
            confidence_score=0.83,
            created_at=datetime.now() - timedelta(days=3),
            last_used_at=datetime.now() - timedelta(hours=8),
        ),
    ]

    # 3. 用户反馈示例
    feedback_examples = [
        TaxonomyUserFeedback(
            task_id="task_demo_001",
            dimension="emotion",
            type_id="song_chi_gan",
            action="confirm",
            comment="非常准确，正是我想要的感觉",
            created_at=datetime.now() - timedelta(days=2),
        ),
        TaxonomyUserFeedback(
            task_id="task_demo_002",
            dimension="style",
            type_id="sai_bo_peng_ke",
            action="reject",
            comment="偏离主题，不适合住宅设计",
            created_at=datetime.now() - timedelta(days=1),
        ),
    ]

    # 4. 用户建议示例
    suggestion_examples = [
        TaxonomyUserSuggestion(
            task_id="task_demo_003",
            dimension="method",
            suggested_label="模块化设计",
            keywords=json.dumps(["灵活组合", "可变空间", "多功能"], ensure_ascii=False),
            reason="现代小户型常用的设计手法，应该纳入方法维度",
            status="pending",
            submitted_at=datetime.now() - timedelta(hours=12),
        ),
    ]

    # 5. LLM概念发现示例
    discovery_examples = [
        TaxonomyConceptDiscovery(
            concept_cluster="治愈系空间",
            keywords=json.dumps(["治愈", "疗愈", "安静", "放松", "温柔"], ensure_ascii=False),
            sample_inputs=json.dumps(["想要一个能让人放松的空间", "疗愈系的家居环境", "让人感到安静和温柔的设计"], ensure_ascii=False),
            occurrence_count=8,
            confidence=0.72,
            suggested_dimension="emotion",
            suggested_type_id="zhi_yu_xi_kong_jian",
            discovered_at=datetime.now() - timedelta(days=7),
            last_seen_at=datetime.now() - timedelta(hours=4),
        ),
    ]

    # 批量插入
    try:
        session.add_all(extended_examples)
        session.add_all(emerging_examples)
        session.add_all(feedback_examples)
        session.add_all(suggestion_examples)
        session.add_all(discovery_examples)
        session.commit()

        print(f"  ✅ 插入 {len(extended_examples)} 条扩展类型")
        print(f"  ✅ 插入 {len(emerging_examples)} 条新兴类型")
        print(f"  ✅ 插入 {len(feedback_examples)} 条用户反馈")
        print(f"  ✅ 插入 {len(suggestion_examples)} 条用户建议")
        print(f"  ✅ 插入 {len(discovery_examples)} 条概念发现")

    except Exception as e:
        session.rollback()
        print(f"  ❌ 插入数据失败: {e}")
        raise


def verify_migration(session):
    """验证迁移结果"""
    print("\n🔍 验证迁移结果...")

    extended_count = session.query(TaxonomyExtendedType).count()
    emerging_count = session.query(TaxonomyEmergingType).count()
    feedback_count = session.query(TaxonomyUserFeedback).count()
    suggestion_count = session.query(TaxonomyUserSuggestion).count()
    discovery_count = session.query(TaxonomyConceptDiscovery).count()

    print(f"  📊 扩展类型: {extended_count} 条")
    print(f"  📊 新兴类型: {emerging_count} 条")
    print(f"  📊 用户反馈: {feedback_count} 条")
    print(f"  📊 用户建议: {suggestion_count} 条")
    print(f"  📊 概念发现: {discovery_count} 条")

    # 示例查询：显示新兴类型详情
    print("\n📋 新兴类型示例：")
    emerging_types = session.query(TaxonomyEmergingType).all()
    for et in emerging_types:
        success_rate = et.success_count / et.case_count if et.case_count > 0 else 0
        print(
            f"  - {et.label_zh} ({et.dimension}): "
            f"使用{et.case_count}次, 成功率{success_rate:.1%}, "
            f"来源={et.source}, 置信度={et.confidence_score:.2f}"
        )


def main():
    """主迁移流程"""
    print("=" * 70)
    print("🚀 维度学习系统数据库迁移")
    print("=" * 70)

    # 1. 连接数据库
    db_path = get_db_path()
    database_url = f"sqlite:///{db_path}"
    print(f"\n📍 数据库路径: {db_path}")

    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)

    # 2. 检查现有表
    print("\n🔍 检查现有表...")
    existing = check_existing_tables(engine)
    for table_name, exists in existing.items():
        status = "✅ 存在" if exists else "❌ 不存在"
        print(f"  {status} {table_name}")

    # 3. 创建新表
    create_tables(engine)

    # 4. 插入示例数据
    db_session = SessionLocal()
    try:
        insert_mock_data(db_session)

        # 5. 验证迁移
        verify_migration(db_session)

    finally:
        db_session.close()

    print("\n" + "=" * 70)
    print("✅ 迁移完成！")
    print("=" * 70)
    print("\n💡 下一步：")
    print("  1. 重启后端服务")
    print("  2. 访问 http://localhost:3001/admin/dimension-learning")
    print("  3. 查看实时数据统计")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
