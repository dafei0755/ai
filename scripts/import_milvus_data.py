"""
Milvus 知识库数据导入脚本

功能:
1. 创建 Milvus Collection
2. 从文档文件夹导入数据
3. 批量向量化和插入
4. 验证数据完整性

用法:
    python scripts/import_milvus_data.py --source ./data/knowledge_docs --collection design_knowledge_base
"""

import argparse
import json
import os

# 添加项目根目录到路径
import sys
import time
from pathlib import Path
from typing import Dict, List

from loguru import logger
from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility
from sentence_transformers import SentenceTransformer

sys.path.append(str(Path(__file__).parent.parent))

from intelligent_project_analyzer.settings import settings


def create_collection(collection_name: str, embedding_dim: int = 1024) -> Collection:
    """
    创建 Milvus Collection

    Args:
        collection_name: Collection 名称
        embedding_dim: 向量维度

    Returns:
        Collection 实例
    """
    if utility.has_collection(collection_name):
        logger.warning(f"Collection '{collection_name}' 已存在，将删除并重建")
        utility.drop_collection(collection_name)

    # 定义字段 schema
    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
        FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=10000),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=embedding_dim),
        FieldSchema(name="document_type", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="tags", dtype=DataType.ARRAY, element_type=DataType.VARCHAR, max_capacity=20, max_length=50),
        FieldSchema(name="project_type", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="source_file", dtype=DataType.VARCHAR, max_length=500),
        # 🆕 v7.141: 用户隔离字段（支持公共知识库和私有知识库）
        # 🆕 v7.141.2: 团队知识库支持
        FieldSchema(
            name="owner_type", dtype=DataType.VARCHAR, max_length=20, default_value="system"
        ),  # "system" | "user" | "team"
        FieldSchema(
            name="owner_id", dtype=DataType.VARCHAR, max_length=100, default_value="public"
        ),  # "public" | user_id | team_id
        FieldSchema(
            name="visibility", dtype=DataType.VARCHAR, max_length=20, default_value="public"
        ),  # "public" | "private"
        FieldSchema(
            name="team_id", dtype=DataType.VARCHAR, max_length=100, default_value=""
        ),  # 🆕 v7.141.2: 团队ID（用于团队知识库）
        # 🆕 v7.141.3: 配额管理字段
        FieldSchema(name="file_size_bytes", dtype=DataType.INT64, default_value=0),  # 文件大小（字节）
        FieldSchema(name="created_at", dtype=DataType.INT64, default_value=0),  # 创建时间（Unix 时间戳）
        FieldSchema(name="expires_at", dtype=DataType.INT64, default_value=0),  # 过期时间（Unix 时间戳，0表示永不过期）
        FieldSchema(name="is_deleted", dtype=DataType.BOOL, default_value=False),  # 软删除标记
        FieldSchema(name="user_tier", dtype=DataType.VARCHAR, max_length=20, default_value="free"),  # 用户会员等级
    ]

    # 创建 schema
    schema = CollectionSchema(fields=fields, description="设计知识库")

    # 创建 collection
    collection = Collection(name=collection_name, schema=schema)

    # 创建索引 (HNSW 用于向量检索)
    index_params = {
        "index_type": "HNSW",
        "metric_type": "COSINE",
        "params": {"M": 16, "efConstruction": 256},
    }
    collection.create_index(field_name="vector", index_params=index_params)

    logger.info(f"✅ Collection '{collection_name}' 创建成功")
    return collection


def load_documents(source_path: str) -> List[Dict]:
    """
    从文件夹加载文档

    支持格式:
    - .txt
    - .md
    - .json (结构化数据)

    Args:
        source_path: 文档文件夹路径

    Returns:
        文档列表
    """
    documents = []
    source = Path(source_path)

    if not source.exists():
        logger.error(f"源路径不存在: {source_path}")
        return []

    # 遍历文件
    for file_path in source.rglob("*"):
        if file_path.is_file() and file_path.suffix in [".txt", ".md", ".json"]:
            try:
                if file_path.suffix == ".json":
                    # JSON 文件 (结构化数据)
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            documents.extend(data)
                        else:
                            documents.append(data)
                else:
                    # 文本文件
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        documents.append(
                            {
                                "title": file_path.stem,
                                "content": content,
                                "document_type": "文档",
                                "tags": [],
                                "project_type": "",
                                "source_file": str(file_path),
                            }
                        )
                logger.info(f"✅ 加载文件: {file_path.name}")
            except Exception as e:
                logger.error(f"⚠️ 加载失败: {file_path.name}, {e}")

    logger.info(f"共加载 {len(documents)} 个文档")
    return documents


def batch_insert(
    collection: Collection, documents: List[Dict], embedding_model: SentenceTransformer, batch_size: int = 32
):
    """
    批量向量化并插入数据

    Args:
        collection: Milvus Collection
        documents: 文档列表
        embedding_model: Embedding 模型
        batch_size: 批量大小
    """
    total = len(documents)
    inserted = 0

    for i in range(0, total, batch_size):
        batch = documents[i : i + batch_size]

        # 准备数据
        ids = [str(hash(doc.get("title", "") + doc.get("content", "")[:100]))[:100] for doc in batch]
        titles = [doc.get("title", "无标题") for doc in batch]
        contents = [doc.get("content", "") for doc in batch]
        document_types = [doc.get("document_type", "通用") for doc in batch]
        tags = [doc.get("tags", []) for doc in batch]
        project_types = [doc.get("project_type", "") for doc in batch]
        source_files = [doc.get("source_file", "") for doc in batch]

        # 🆕 v7.141: 用户隔离字段（默认为公共知识库）
        # 🆕 v7.141.2: 团队知识库字段
        owner_types = [doc.get("owner_type", "system") for doc in batch]
        owner_ids = [doc.get("owner_id", "public") for doc in batch]
        visibilities = [doc.get("visibility", "public") for doc in batch]
        team_ids = [doc.get("team_id", "") for doc in batch]  # 🆕 v7.141.2

        # 🆕 v7.141.3: 配额管理字段
        import time

        file_size_bytes = [doc.get("file_size_bytes", len(doc.get("content", "").encode("utf-8"))) for doc in batch]
        created_at = [doc.get("created_at", int(time.time())) for doc in batch]
        expires_at = [doc.get("expires_at", 0) for doc in batch]  # 0 表示永不过期
        is_deleted = [doc.get("is_deleted", False) for doc in batch]
        user_tier = [doc.get("user_tier", "free") for doc in batch]

        # 向量化 (批量)
        logger.info(f"正在向量化批次 {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}...")
        vectors = embedding_model.encode(contents, normalize_embeddings=True, show_progress_bar=False).tolist()

        # 插入数据
        entities = [
            ids,
            titles,
            contents,
            vectors,
            document_types,
            tags,
            project_types,
            source_files,
            owner_types,
            owner_ids,
            visibilities,
            team_ids,  # v7.141.2: 团队知识库字段
            file_size_bytes,
            created_at,
            expires_at,
            is_deleted,
            user_tier,  # v7.141.3: 配额管理字段
        ]

        try:
            collection.insert(entities)
            inserted += len(batch)
            logger.info(f"✅ 已插入 {inserted}/{total} 个文档")
        except Exception as e:
            logger.error(f"⚠️ 插入失败: {e}")

    # Flush 数据到磁盘
    collection.flush()
    logger.info(f"✅ 数据导入完成: {inserted}/{total} 个文档")


def verify_data(collection: Collection):
    """验证数据完整性"""
    collection.load()
    num_entities = collection.num_entities
    logger.info(f"✅ Collection 包含 {num_entities} 个实体")

    # 测试搜索
    test_vector = [[0.1] * collection.schema.fields[3].params["dim"]]
    search_params = {"metric_type": "COSINE", "params": {"ef": 64}}

    results = collection.search(
        data=test_vector, anns_field="vector", param=search_params, limit=5, output_fields=["title", "document_type"]
    )

    if results and len(results[0]) > 0:
        logger.info("✅ 搜索测试成功:")
        for hit in results[0]:
            logger.info(f"  - {hit.entity.get('title')} ({hit.entity.get('document_type')}), 相似度: {hit.score:.3f}")
    else:
        logger.warning("⚠️ 搜索测试未返回结果")


def main():
    parser = argparse.ArgumentParser(description="Milvus 知识库数据导入工具")
    parser.add_argument("--source", type=str, required=True, help="文档源文件夹路径")
    parser.add_argument(
        "--collection", type=str, default="design_knowledge_base", help="Collection 名称 (默认: design_knowledge_base)"
    )
    parser.add_argument("--host", type=str, default="localhost", help="Milvus 服务器地址 (默认: localhost)")
    parser.add_argument("--port", type=int, default=19530, help="Milvus 端口 (默认: 19530)")
    parser.add_argument("--embedding-model", type=str, default="BAAI/bge-m3", help="Embedding 模型 (默认: BAAI/bge-m3)")
    parser.add_argument("--embedding-dim", type=int, default=1024, help="向量维度 (默认: 1024)")
    parser.add_argument("--batch-size", type=int, default=32, help="批量插入大小 (默认: 32)")

    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("Milvus 知识库数据导入工具")
    logger.info("=" * 50)

    # 连接 Milvus
    logger.info(f"连接 Milvus: {args.host}:{args.port}")
    connections.connect(host=args.host, port=args.port)

    # 创建 Collection
    logger.info(f"创建 Collection: {args.collection}")
    collection = create_collection(args.collection, args.embedding_dim)

    # 加载文档
    logger.info(f"加载文档: {args.source}")
    documents = load_documents(args.source)

    if not documents:
        logger.error("未找到任何文档，退出")
        return

    # 加载 Embedding 模型
    logger.info(f"加载 Embedding 模型: {args.embedding_model}")
    embedding_model = SentenceTransformer(args.embedding_model)

    # 批量插入
    logger.info("开始批量导入...")
    start_time = time.time()
    batch_insert(collection, documents, embedding_model, args.batch_size)
    elapsed = time.time() - start_time

    logger.info(f"✅ 导入完成，耗时: {elapsed:.2f}s")

    # 验证数据
    logger.info("验证数据完整性...")
    verify_data(collection)

    logger.info("=" * 50)
    logger.info("全部完成！")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
