"""
Milvus Collection 迁移脚本 - v7.141.2-v7.141.4

用途: 重建 Milvus Collection 以支持新增的配额管理字段
新增字段:
  - visibility (VARCHAR) - 文档可见性
  - team_id (VARCHAR) - 团队ID
  - file_size_bytes (INT64) - 文件大小
  - created_at (INT64) - 创建时间
  - expires_at (INT64) - 过期时间
  - is_deleted (BOOL) - 软删除标记
  - user_tier (VARCHAR) - 用户会员等级

运行方式:
  python scripts/migrate_milvus_v7141.py [--backup] [--drop-old]

参数说明:
  --backup: 导出现有数据到备份文件
  --drop-old: 删除旧的 Collection（如果存在）
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

from intelligent_project_analyzer.settings import settings

# Get Milvus settings
MILVUS_HOST = settings.milvus.host
MILVUS_PORT = settings.milvus.port
MILVUS_COLLECTION_NAME = settings.milvus.collection_name
MILVUS_EMBEDDING_MODEL = settings.milvus.embedding_model
MILVUS_DIMENSION = settings.milvus.embedding_dim

# 备份目录
BACKUP_DIR = project_root / "data" / "milvus_backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def backup_existing_collection(collection_name: str) -> str:
    """
    备份现有 Collection 的数据

    Returns:
        str: 备份文件路径
    """
    print(f"\n📦 开始备份 Collection: {collection_name}")

    try:
        if not utility.has_collection(collection_name):
            print(f"⚠️  Collection '{collection_name}' 不存在，跳过备份")
            return None

        collection = Collection(collection_name)
        collection.load()

        # 查询所有数据
        print("🔍 查询现有数据...")
        results = collection.query(expr="id >= 0", output_fields=["*"], limit=16384)  # Milvus 单次查询上限

        if not results:
            print("⚠️  Collection 为空，跳过备份")
            return None

        # 创建备份文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"backup_{collection_name}_{timestamp}.json"

        # 保存数据
        print(f"💾 保存数据到: {backup_file}")
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "collection_name": collection_name,
                    "backup_time": timestamp,
                    "document_count": len(results),
                    "schema_version": "v7.141 (before migration)",
                    "data": results,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        print(f"✅ 备份完成: {len(results)} 个文档")
        print(f"   备份文件: {backup_file}")
        return str(backup_file)

    except Exception as e:
        print(f"❌ 备份失败: {e}")
        return None


def create_new_collection(collection_name: str) -> Collection:
    """
    创建新的 Collection（包含所有v7.141字段）

    Returns:
        Collection: 新创建的 Collection 实例
    """
    print(f"\n🔨 创建新 Collection: {collection_name}")

    # 定义字段 Schema（完整版本）
    fields = [
        # 基础字段
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=MILVUS_DIMENSION),
        # 分类字段
        FieldSchema(name="document_type", dtype=DataType.VARCHAR, max_length=100, default_value="general"),
        FieldSchema(name="tags", dtype=DataType.VARCHAR, max_length=500, default_value=""),
        FieldSchema(name="project_type", dtype=DataType.VARCHAR, max_length=100, default_value="unknown"),
        FieldSchema(name="source_file", dtype=DataType.VARCHAR, max_length=500, default_value=""),
        # 🆕 v7.141: 用户隔离字段（支持公共知识库和私有知识库）
        FieldSchema(name="owner_type", dtype=DataType.VARCHAR, max_length=20, default_value="system"),
        FieldSchema(name="owner_id", dtype=DataType.VARCHAR, max_length=100, default_value="public"),
        # 🆕 v7.141.2: 文档共享和团队知识库
        FieldSchema(name="visibility", dtype=DataType.VARCHAR, max_length=20, default_value="public"),
        FieldSchema(name="team_id", dtype=DataType.VARCHAR, max_length=100, default_value=""),
        # 🆕 v7.141.3: 配额管理字段
        FieldSchema(name="file_size_bytes", dtype=DataType.INT64, default_value=0),
        FieldSchema(name="created_at", dtype=DataType.INT64, default_value=0),
        FieldSchema(name="expires_at", dtype=DataType.INT64, default_value=0),
        FieldSchema(name="is_deleted", dtype=DataType.BOOL, default_value=False),
        FieldSchema(name="user_tier", dtype=DataType.VARCHAR, max_length=20, default_value="free"),
    ]

    # 创建 Collection Schema
    schema = CollectionSchema(
        fields=fields,
        description=f"Design Knowledge Base (v7.141.4 - with quota management)",
        enable_dynamic_field=True,
    )

    # 创建 Collection
    collection = Collection(name=collection_name, schema=schema, using="default", shards_num=2)

    print(f"✅ Collection 创建成功")
    print(f"   字段数量: {len(fields)}")
    print(f"   Schema 版本: v7.141.4")

    # 创建索引
    print("\n📊 创建向量索引...")
    index_params = {"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
    collection.create_index(field_name="vector", index_params=index_params)
    print("✅ 索引创建成功")

    return collection


def restore_data_from_backup(collection: Collection, backup_file: str):
    """
    从备份文件恢复数据到新 Collection

    Args:
        collection: 新 Collection 实例
        backup_file: 备份文件路径
    """
    print(f"\n📥 从备份恢复数据: {backup_file}")

    try:
        with open(backup_file, "r", encoding="utf-8") as f:
            backup_data = json.load(f)

        old_data = backup_data["data"]
        print(f"📋 备份文件包含 {len(old_data)} 个文档")

        if not old_data:
            print("⚠️  备份为空，跳过恢复")
            return

        # 数据转换：添加新字段的默认值
        print("🔄 转换数据格式...")
        current_time = int(time.time())

        transformed_data = []
        for doc in old_data:
            # 保留旧字段
            new_doc = {k: v for k, v in doc.items() if k != "id"}  # 排除 auto_id 字段

            # 🆕 v7.141.2: 添加缺失的共享和团队字段
            if "visibility" not in new_doc:
                new_doc["visibility"] = "public"
            if "team_id" not in new_doc:
                new_doc["team_id"] = ""

            # 🆕 v7.141.3: 添加缺失的配额管理字段
            if "file_size_bytes" not in new_doc:
                # 通过内容长度估算文件大小
                content_size = len(new_doc.get("content", "").encode("utf-8"))
                new_doc["file_size_bytes"] = content_size

            if "created_at" not in new_doc:
                new_doc["created_at"] = current_time

            if "expires_at" not in new_doc:
                new_doc["expires_at"] = 0  # 0 表示永不过期

            if "is_deleted" not in new_doc:
                new_doc["is_deleted"] = False

            if "user_tier" not in new_doc:
                # 根据 owner_type 推断会员等级
                if new_doc.get("owner_type") == "system":
                    new_doc["user_tier"] = "enterprise"  # 系统文档视为企业级
                else:
                    new_doc["user_tier"] = "free"

            transformed_data.append(new_doc)

        # 批量插入（分批处理，避免单次插入过多）
        batch_size = 100
        total_inserted = 0

        print(f"💾 批量插入数据（批次大小: {batch_size}）...")
        for i in range(0, len(transformed_data), batch_size):
            batch = transformed_data[i : i + batch_size]

            # 准备批次数据
            batch_dict = {field: [] for field in collection.schema.fields if field.name != "id"}
            for doc in batch:
                for field in collection.schema.fields:
                    if field.name == "id":
                        continue
                    batch_dict[field.name].append(doc.get(field.name, field.default_value))

            # 插入数据
            collection.insert(list(batch_dict.values()))
            total_inserted += len(batch)
            print(f"   进度: {total_inserted}/{len(transformed_data)} ({total_inserted/len(transformed_data)*100:.1f}%)")

        collection.flush()
        print(f"✅ 数据恢复完成: {total_inserted} 个文档")

    except Exception as e:
        print(f"❌ 数据恢复失败: {e}")
        raise


def verify_migration(collection: Collection):
    """
    验证迁移结果

    Args:
        collection: Collection 实例
    """
    print("\n🔍 验证迁移结果...")

    try:
        # 加载 Collection
        collection.load()

        # 检查字段
        expected_fields = [
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
            "visibility",
            "team_id",  # v7.141.2
            "file_size_bytes",
            "created_at",
            "expires_at",
            "is_deleted",
            "user_tier",  # v7.141.3
        ]

        actual_fields = [field.name for field in collection.schema.fields]

        print(f"\n📋 Schema 验证:")
        print(f"   期望字段数: {len(expected_fields)}")
        print(f"   实际字段数: {len(actual_fields)}")

        missing_fields = set(expected_fields) - set(actual_fields)
        if missing_fields:
            print(f"   ❌ 缺失字段: {missing_fields}")
            return False

        extra_fields = set(actual_fields) - set(expected_fields)
        if extra_fields:
            print(f"   ℹ️  额外字段: {extra_fields}")

        # 检查数据量
        num_entities = collection.num_entities
        print(f"\n📊 数据量验证:")
        print(f"   文档总数: {num_entities}")

        # 抽样检查新字段
        if num_entities > 0:
            print("\n🎯 抽样检查新字段...")
            sample = collection.query(
                expr="id >= 0",
                output_fields=[
                    "id",
                    "title",
                    "visibility",
                    "team_id",
                    "file_size_bytes",
                    "created_at",
                    "expires_at",
                    "is_deleted",
                    "user_tier",
                ],
                limit=3,
            )

            for i, doc in enumerate(sample, 1):
                print(f"\n   样本 {i}:")
                print(f"     ID: {doc.get('id')}")
                print(f"     标题: {doc.get('title', 'N/A')[:50]}")
                print(f"     可见性: {doc.get('visibility')}")
                print(f"     团队ID: {doc.get('team_id') or '(无)'}")
                print(f"     文件大小: {doc.get('file_size_bytes')} bytes")
                print(f"     创建时间: {doc.get('created_at')}")
                print(f"     过期时间: {doc.get('expires_at')} {'(永不过期)' if doc.get('expires_at') == 0 else ''}")
                print(f"     已删除: {doc.get('is_deleted')}")
                print(f"     会员等级: {doc.get('user_tier')}")

        print("\n✅ 迁移验证通过！")
        return True

    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Milvus Collection 迁移工具 (v7.141)")
    parser.add_argument("--backup", action="store_true", help="导出现有数据到备份文件")
    parser.add_argument("--drop-old", action="store_true", help="删除旧的 Collection")
    parser.add_argument("--restore", type=str, help="从指定备份文件恢复数据")
    args = parser.parse_args()

    print("=" * 70)
    print("Milvus Collection 迁移工具 - v7.141.2-v7.141.4")
    print("=" * 70)

    # 连接到 Milvus
    print(f"\n🔌 连接到 Milvus: {MILVUS_HOST}:{MILVUS_PORT}")
    connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
    print("✅ 连接成功")

    collection_name = MILVUS_COLLECTION_NAME
    backup_file = None

    # 步骤 1: 备份现有数据
    if args.backup:
        backup_file = backup_existing_collection(collection_name)
        if not backup_file:
            print("\n⚠️  无数据可备份")

    # 步骤 2: 删除旧 Collection（可选）
    if args.drop_old:
        if utility.has_collection(collection_name):
            print(f"\n🗑️  删除旧 Collection: {collection_name}")
            utility.drop_collection(collection_name)
            print("✅ 删除成功")
        else:
            print(f"\n⚠️  Collection '{collection_name}' 不存在，跳过删除")

    # 步骤 3: 创建新 Collection
    if not utility.has_collection(collection_name):
        collection = create_new_collection(collection_name)
    else:
        print(f"\n⚠️  Collection '{collection_name}' 已存在，使用现有 Collection")
        collection = Collection(collection_name)

    # 步骤 4: 恢复数据
    restore_file = args.restore or backup_file
    if restore_file and os.path.exists(restore_file):
        restore_data_from_backup(collection, restore_file)
    elif restore_file:
        print(f"\n⚠️  备份文件不存在: {restore_file}")

    # 步骤 5: 验证迁移
    success = verify_migration(collection)

    # 总结
    print("\n" + "=" * 70)
    if success:
        print("✅ 迁移完成！")
        print("\n下一步:")
        print("  1. 启动后端服务: python -B scripts\\run_server_production.py")
        print("  2. 导入文档: python scripts/import_milvus_data.py --source ./data/knowledge_docs")
        print("  3. 测试配额管理功能: 访问 http://localhost:3000/user/dashboard")
    else:
        print("❌ 迁移失败，请检查错误日志")
    print("=" * 70)


if __name__ == "__main__":
    main()
