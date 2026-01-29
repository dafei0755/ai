"""
Milvus Schema 检查脚本

用途: 检查当前 Collection 是否需要迁移到 v7.141.4
运行: python scripts/check_milvus_schema.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pymilvus import Collection, connections, utility

from intelligent_project_analyzer.settings import settings

# Get Milvus settings
MILVUS_HOST = settings.milvus.host
MILVUS_PORT = settings.milvus.port
MILVUS_COLLECTION_NAME = settings.milvus.collection_name


def check_schema():
    """检查 Collection Schema 是否包含所有 v7.141.4 字段"""

    print("=" * 70)
    print("Milvus Schema 检查工具 - v7.141.4")
    print("=" * 70)

    # 期望的字段列表（v7.141.4）
    expected_fields = {
        # v7.141.1: 基础字段
        "id",
        "title",
        "content",
        "vector",
        "document_type",
        "tags",
        "project_type",
        "source_file",
        "owner_type",
        "owner_id",
        # v7.141.2: 文档共享和团队知识库
        "visibility",
        "team_id",
        # v7.141.3: 配额管理字段
        "file_size_bytes",
        "created_at",
        "expires_at",
        "is_deleted",
        "user_tier",
    }

    try:
        # 连接 Milvus
        print(f"\n🔌 连接到 Milvus: {MILVUS_HOST}:{MILVUS_PORT}")
        connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
        print("✅ 连接成功")

        # 检查 Collection 是否存在
        if not utility.has_collection(MILVUS_COLLECTION_NAME):
            print(f"\n⚠️  Collection '{MILVUS_COLLECTION_NAME}' 不存在")
            print("📝 需要创建新 Collection")
            print("\n建议操作:")
            print("  python scripts/migrate_milvus_v7141.py")
            return False

        # 获取 Collection
        collection = Collection(MILVUS_COLLECTION_NAME)

        # 获取当前字段
        current_fields = {field.name for field in collection.schema.fields}

        print(f"\n📊 当前 Collection: {MILVUS_COLLECTION_NAME}")
        print(f"   字段数量: {len(current_fields)}")

        # 检查缺失字段
        missing_fields = expected_fields - current_fields
        extra_fields = current_fields - expected_fields

        if not missing_fields:
            print("\n✅ Schema 检查通过！")
            print("   所有 v7.141.4 字段都已存在")

            # 显示字段列表
            print("\n📋 当前字段列表:")
            for field in collection.schema.fields:
                print(f"   - {field.name} ({field.dtype.name})")

            # 显示数据量
            collection.load()
            print(f"\n📊 数据统计:")
            print(f"   文档总数: {collection.num_entities}")

            return True
        else:
            print("\n❌ Schema 不匹配！")
            print("\n缺失字段:")
            for field in sorted(missing_fields):
                print(f"   ❌ {field}")

            if extra_fields:
                print("\n额外字段:")
                for field in sorted(extra_fields):
                    print(f"   ℹ️  {field}")

            print("\n📝 需要迁移到 v7.141.4")
            print("\n建议操作:")
            print("  1. 备份现有数据:")
            print("     python scripts/migrate_milvus_v7141.py --backup")
            print("\n  2. 执行完整迁移:")
            print("     python scripts/migrate_milvus_v7141.py --backup --drop-old")
            print("\n⚠️  警告: 迁移会删除并重建 Collection，请先备份数据！")

            return False

    except Exception as e:
        print(f"\n❌ 检查失败: {e}")
        print("\n可能的原因:")
        print("  1. Milvus 服务未启动")
        print("  2. 连接配置错误")
        print("  3. Collection 不存在或损坏")
        return False

    finally:
        print("\n" + "=" * 70)


if __name__ == "__main__":
    success = check_schema()
    sys.exit(0 if success else 1)
