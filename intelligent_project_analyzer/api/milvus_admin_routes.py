"""
Milvus 知识库管理 API 路由 (v7.141+)

功能:
- Collection 状态查询
- 数据导入（文件上传 + 批量导入）
- 搜索测试
- 统计信息
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel

from ..settings import settings

router = APIRouter(prefix="/api/admin/milvus", tags=["admin", "milvus"])


# ============================================================================
# Pydantic 模型
# ============================================================================


class SearchTestRequest(BaseModel):
    """搜索测试请求"""

    query: str
    max_results: int = 10
    similarity_threshold: float | None = None
    user_id: str | None = None  #  v7.141: 用户ID（用于过滤私有知识库）
    team_id: str | None = None  #  v7.141.2: 团队ID（用于团队知识库）
    search_scope: str = "all"  #  v7.141: "all" | "system" | "user" | "team"


class CollectionStatsResponse(BaseModel):
    """Collection 统计信息"""

    status: str
    collection_name: str
    num_entities: int
    embedding_dim: int
    index_type: str
    metric_type: str
    is_loaded: bool


class ImportProgressResponse(BaseModel):
    """导入进度响应"""

    task_id: str
    status: str  # pending/processing/completed/failed
    progress: float  # 0-100
    total_documents: int
    processed_documents: int
    error_message: str | None = None


# ============================================================================
# Collection 状态管理
# ============================================================================


@router.get("/status")
async def get_milvus_status():
    """
    获取 Milvus 服务状态

    Returns:
        {
            "status": "healthy|degraded|unavailable",
            "enabled": bool,
            "host": str,
            "port": int,
            "collection_name": str
        }
    """
    try:
        from ..core.types import ToolConfig
        from ..tools.milvus_kb import MilvusKBTool

        # 创建工具实例
        tool = MilvusKBTool(
            host=settings.milvus.host,
            port=settings.milvus.port,
            collection_name=settings.milvus.collection_name,
            embedding_model_name=settings.milvus.embedding_model,
            reranker_model_name=settings.milvus.reranker_model,
            config=ToolConfig(name="milvus_admin"),
        )

        # 健康检查
        health = tool.health_check()

        return {
            "status": health.get("status", "unknown"),
            "enabled": settings.milvus.enabled,
            "host": settings.milvus.host,
            "port": settings.milvus.port,
            "collection_name": settings.milvus.collection_name,
            "health_details": health,
        }

    except Exception as e:
        logger.error(f"Milvus 状态检查失败: {e}")
        return {
            "status": "unavailable",
            "enabled": settings.milvus.enabled,
            "error": str(e),
        }


@router.get("/collection/stats")
async def get_collection_stats() -> CollectionStatsResponse:
    """
    获取 Collection 统计信息

    Returns:
        Collection 详细统计
    """
    try:
        from pymilvus import Collection, connections

        # 连接 Milvus
        connections.connect(host=settings.milvus.host, port=settings.milvus.port)

        # 获取 Collection
        collection = Collection(settings.milvus.collection_name)
        collection.load()

        # 获取统计信息
        num_entities = collection.num_entities

        # 获取 schema 信息
        schema = collection.schema
        vector_field = [f for f in schema.fields if f.dtype.name == "FLOAT_VECTOR"][0]
        embedding_dim = vector_field.params.get("dim", 0)

        # 获取索引信息
        indexes = collection.indexes
        index_info = indexes[0].params if indexes else {}

        return CollectionStatsResponse(
            status="healthy",
            collection_name=settings.milvus.collection_name,
            num_entities=num_entities,
            embedding_dim=embedding_dim,
            index_type=index_info.get("index_type", "HNSW"),
            metric_type=index_info.get("metric_type", "COSINE"),
            is_loaded=True,
        )

    except Exception as e:
        logger.error(f"获取 Collection 统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 数据导入
# ============================================================================


@router.post("/import/file")
async def import_file(
    file: UploadFile = File(...),
    document_type: str = Form("文档"),
    project_type: str = Form(""),
    owner_type: str = Form("system"),  #  v7.141: "system" | "user" | "team"
    owner_id: str = Form("public"),  #  v7.141: "public" | user_id | team_id
    visibility: str = Form("public"),  #  v7.141: "public" | "private"
    team_id: str = Form(""),  #  v7.141.2: 团队ID（用于团队知识库）
    user_tier: str = Form("free"),  #  v7.141.3: 用户会员等级（用于配额检查）
):
    """
    上传文件并导入到 Milvus

    支持格式: .txt, .md, .json

    Args:
        file: 上传的文件
        document_type: 文档类型 (设计规范/案例库/技术知识)
        project_type: 项目类型 (residential/commercial等)
        owner_type: 所有者类型 ("system"=公共知识库 | "user"=私有知识库 | "team"=团队知识库)
        owner_id: 所有者ID ("public" | user_id | team_id)
        visibility: 可见性 ("public" | "private")
        team_id: 团队ID（用于团队知识库） v7.141.2
        user_tier: 用户会员等级（free/basic/professional/enterprise） v7.141.3

    Returns:
        导入结果
    """
    try:
        from pymilvus import Collection, connections
        from sentence_transformers import SentenceTransformer

        from ..services.quota_manager import QuotaManager  #  v7.141.3

        # 读取文件内容
        content = await file.read()
        filename = file.filename

        #  v7.141.3: 配额检查（仅对用户知识库和团队知识库进行检查）
        if owner_type in ["user", "team"]:
            # 步骤 1: 检查文件大小
            file_size_bytes = len(content)
            quota_mgr_temp = QuotaManager()  # 临时实例，用于文件大小检查

            file_size_check = quota_mgr_temp.check_file_size(file_size_bytes, user_tier)
            if not file_size_check["allowed"]:
                logger.warning(f" [配额检查] 文件大小超限: {file_size_check['error']}")
                raise HTTPException(
                    status_code=413,  # 413 Payload Too Large
                    detail={
                        "error": "file_size_exceeded",
                        "message": file_size_check.get("error", "文件大小超过限制"),
                        "file_size_mb": file_size_check["file_size_mb"],
                        "max_file_size_mb": file_size_check["max_file_size_mb"],
                        "user_tier": user_tier,
                    },
                )

            logger.info(f" [配额检查] 文件大小检查通过: {file_size_check['file_size_mb']} MB")

            # 步骤 2: 检查配额是否超限（连接 Milvus 获取实时数据）
            try:
                connections.connect(host=settings.milvus.host, port=settings.milvus.port)
                collection = Collection(settings.milvus.collection_name)
                collection.load()

                quota_mgr = QuotaManager(collection=collection)
                quota_check = quota_mgr.check_quota(owner_id, user_tier)

                if not quota_check["allowed"]:
                    logger.warning(f" [配额检查] 配额超限: {quota_check['errors']}")
                    raise HTTPException(
                        status_code=403,  # 403 Forbidden
                        detail={
                            "error": "quota_exceeded",
                            "message": "配额已满，无法上传新文档",
                            "errors": quota_check["errors"],
                            "current_usage": quota_check["current_usage"],
                            "quota_limit": quota_check["quota_limit"],
                            "user_tier": user_tier,
                            "suggestions": [
                                "删除不需要的文档以释放空间",
                                "升级会员等级以提升配额",
                            ],
                        },
                    )

                # 配额警告（不阻止上传，仅记录日志）
                if quota_check["warnings"]:
                    logger.warning(f"️ [配额警告] {quota_check['warnings']}")

                logger.info(f" [配额检查] 配额检查通过: {quota_check['current_usage']}")

            except HTTPException:
                raise  # 重新抛出 HTTP 异常
            except Exception as e:
                logger.error(f"️ [配额检查] 配额检查失败（继续上传）: {e}")
                # 配额检查失败时不阻止上传，但记录警告
        else:
            # 系统知识库不受配额限制
            logger.info(" [配额检查] 系统知识库，跳过配额检查")

        # 解析文件
        if filename.endswith(".json"):
            documents = json.loads(content.decode("utf-8"))
            if not isinstance(documents, list):
                documents = [documents]
        elif filename.endswith((".txt", ".md")):
            text_content = content.decode("utf-8")
            documents = [
                {
                    "title": Path(filename).stem,
                    "content": text_content,
                    "document_type": document_type,
                    "tags": [],
                    "project_type": project_type,
                    "source_file": filename,
                }
            ]
        else:
            raise HTTPException(status_code=400, detail="不支持的文件格式，仅支持 .txt, .md, .json")

        # 连接 Milvus（如果之前未连接）
        if owner_type == "system":
            connections.connect(host=settings.milvus.host, port=settings.milvus.port)
        collection = Collection(settings.milvus.collection_name)

        # 加载 Embedding 模型
        embedding_model = SentenceTransformer(settings.milvus.embedding_model)

        #  v7.141.3: 计算文档过期时间
        from ..services.quota_manager import QuotaManager

        quota_mgr_expiry = QuotaManager()
        expiry_timestamp = (
            quota_mgr_expiry.calculate_expiry_timestamp(user_tier) if owner_type in ["user", "team"] else 0
        )

        # 向量化并插入
        ids = []
        titles = []
        contents = []
        document_types = []
        tags_list = []
        project_types = []
        source_files = []
        owner_types = []  #  v7.141
        owner_ids = []  #  v7.141
        visibilities = []  #  v7.141
        team_ids = []  #  v7.141.2
        file_sizes = []  #  v7.141.3
        created_ats = []  #  v7.141.3
        expires_ats = []  #  v7.141.3
        is_deleteds = []  #  v7.141.3
        user_tiers = []  #  v7.141.3

        current_timestamp = int(time.time())

        for doc in documents:
            doc_id = str(hash(doc.get("title", "") + doc.get("content", "")[:100]))[:100]
            ids.append(doc_id)
            titles.append(doc.get("title", "无标题"))
            content_text = doc.get("content", "")
            contents.append(content_text)
            document_types.append(doc.get("document_type", document_type))
            tags_list.append(doc.get("tags", []))
            project_types.append(doc.get("project_type", project_type))
            source_files.append(doc.get("source_file", filename))

            #  v7.141: 添加用户隔离字段
            #  v7.141.2: 添加团队知识库字段
            owner_types.append(doc.get("owner_type", owner_type))
            owner_ids.append(doc.get("owner_id", owner_id))
            visibilities.append(doc.get("visibility", visibility))
            team_ids.append(doc.get("team_id", team_id))

            #  v7.141.3: 添加配额管理字段
            file_sizes.append(len(content_text.encode("utf-8")))  # 估算文件大小
            created_ats.append(current_timestamp)
            expires_ats.append(expiry_timestamp)
            is_deleteds.append(False)
            user_tiers.append(user_tier)

        # 批量向量化
        logger.info(f"正在向量化 {len(documents)} 个文档...")
        vectors = embedding_model.encode(contents, normalize_embeddings=True, show_progress_bar=False).tolist()

        # 插入数据（完整的 v7.141.4 Schema）
        entities = [
            ids,
            titles,
            contents,
            vectors,
            document_types,
            tags_list,
            project_types,
            source_files,
            owner_types,
            owner_ids,  # v7.141
            visibilities,
            team_ids,  # v7.141.2
            file_sizes,
            created_ats,
            expires_ats,
            is_deleteds,
            user_tiers,  # v7.141.3
        ]
        collection.insert(entities)
        collection.flush()

        logger.info(f" 成功导入 {len(documents)} 个文档")

        return {
            "success": True,
            "message": f"成功导入 {len(documents)} 个文档",
            "total_documents": len(documents),
            "filename": filename,
        }

    except Exception as e:
        logger.error(f"文件导入失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/batch")
async def import_batch_documents(documents: List[Dict[str, Any]]):
    """
    批量导入文档（JSON 格式）

    Args:
        documents: 文档列表，每个文档包含 title, content, document_type, tags, project_type

    Returns:
        导入结果
    """
    try:
        from pymilvus import Collection, connections
        from sentence_transformers import SentenceTransformer

        # 连接 Milvus
        connections.connect(host=settings.milvus.host, port=settings.milvus.port)
        collection = Collection(settings.milvus.collection_name)

        # 加载 Embedding 模型
        embedding_model = SentenceTransformer(settings.milvus.embedding_model)

        # 准备数据
        ids = []
        titles = []
        contents = []
        document_types = []
        tags_list = []
        project_types = []
        source_files = []
        owner_types = []  #  v7.141
        owner_ids = []  #  v7.141
        visibilities = []  #  v7.141
        team_ids = []  #  v7.141.2

        for doc in documents:
            doc_id = str(hash(doc.get("title", "") + doc.get("content", "")[:100]))[:100]
            ids.append(doc_id)
            titles.append(doc.get("title", "无标题"))
            contents.append(doc.get("content", ""))
            document_types.append(doc.get("document_type", "文档"))
            tags_list.append(doc.get("tags", []))
            project_types.append(doc.get("project_type", ""))
            source_files.append(doc.get("source_file", "api_upload"))

            #  v7.141: 添加用户隔离字段（默认为公共知识库）
            #  v7.141.2: 添加团队知识库字段
            owner_types.append(doc.get("owner_type", "system"))
            owner_ids.append(doc.get("owner_id", "public"))
            visibilities.append(doc.get("visibility", "public"))
            team_ids.append(doc.get("team_id", ""))  #  v7.141.2

        # 批量向量化
        logger.info(f"正在向量化 {len(documents)} 个文档...")
        vectors = embedding_model.encode(contents, normalize_embeddings=True, show_progress_bar=False).tolist()

        # 插入数据
        entities = [
            ids,
            titles,
            contents,
            vectors,
            document_types,
            tags_list,
            project_types,
            source_files,
            owner_types,
            owner_ids,
            visibilities,
            team_ids,
        ]  #  v7.141.2
        collection.insert(entities)
        collection.flush()

        logger.info(f" 成功批量导入 {len(documents)} 个文档")

        return {
            "success": True,
            "message": f"成功导入 {len(documents)} 个文档",
            "total_documents": len(documents),
        }

    except Exception as e:
        logger.error(f"批量导入失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 搜索测试
# ============================================================================


@router.post("/search/test")
async def test_search(request: SearchTestRequest):
    """
    测试搜索功能

    Args:
        request: 搜索测试请求

    Returns:
        搜索结果 + Pipeline 指标
    """
    try:
        from ..core.types import ToolConfig
        from ..tools.milvus_kb import MilvusKBTool

        # 创建工具实例
        tool = MilvusKBTool(
            host=settings.milvus.host,
            port=settings.milvus.port,
            collection_name=settings.milvus.collection_name,
            embedding_model_name=settings.milvus.embedding_model,
            reranker_model_name=settings.milvus.reranker_model,
            config=ToolConfig(name="milvus_test"),
        )

        # 执行搜索
        result = tool.search_knowledge(
            query=request.query,
            max_results=request.max_results,
            similarity_threshold=request.similarity_threshold,
            user_id=request.user_id,  #  v7.141: 传递用户ID
            team_id=request.team_id,  #  v7.141.2: 传递团队ID
            search_scope=request.search_scope,  #  v7.141: 传递搜索范围
        )

        return result

    except Exception as e:
        logger.error(f"搜索测试失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 数据管理
# ============================================================================


@router.delete("/collection/clear")
async def clear_collection():
    """
    清空 Collection（危险操作）

    Returns:
        操作结果
    """
    try:
        from pymilvus import connections, utility

        # 连接 Milvus
        connections.connect(host=settings.milvus.host, port=settings.milvus.port)

        # 删除并重建 Collection
        if utility.has_collection(settings.milvus.collection_name):
            utility.drop_collection(settings.milvus.collection_name)
            logger.warning(f"️ Collection '{settings.milvus.collection_name}' 已被清空")

        return {
            "success": True,
            "message": f"Collection '{settings.milvus.collection_name}' 已清空",
        }

    except Exception as e:
        logger.error(f"清空 Collection 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/sample")
async def get_sample_documents(limit: int = 10):
    """
    获取示例文档（用于预览）

    Args:
        limit: 返回文档数量

    Returns:
        示例文档列表
    """
    try:
        from pymilvus import Collection, connections

        # 连接 Milvus
        connections.connect(host=settings.milvus.host, port=settings.milvus.port)
        collection = Collection(settings.milvus.collection_name)
        collection.load()

        # 查询示例文档
        results = collection.query(
            expr="",  # 空表达式，返回所有
            output_fields=[
                "title",
                "content",
                "document_type",
                "tags",
                "project_type",
                "source_file",
                "owner_type",
                "owner_id",
                "visibility",
                "team_id",
            ],  #  v7.141/v7.141.2: 包含用户隔离和团队字段
            limit=limit,
        )

        return {
            "success": True,
            "total": len(results),
            "documents": results,
        }

    except Exception as e:
        logger.error(f"获取示例文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 配额检查 API（ v7.141.3 - P1-1: 前端上传前检查）
# ============================================================================


@router.get("/quota/check")
async def check_quota_before_upload(
    user_id: str,
    user_tier: str = "free",
    file_size_bytes: int | None = None,
):
    """
    上传前配额检查（前端调用）

    Args:
        user_id: 用户 ID
        user_tier: 用户会员等级 (free/basic/professional/enterprise)
        file_size_bytes: 文件大小（字节），可选

    Returns:
        {
            "allowed": bool,
            "quota_status": {
                "current_usage": {"document_count": int, "storage_mb": float},
                "quota_limit": {"max_documents": int, "max_storage_mb": int, "max_file_size_mb": int},
                "usage_percentage": {"documents": float, "storage": float}
            },
            "file_size_check": {
                "allowed": bool,
                "file_size_mb": float,
                "max_file_size_mb": int
            } | null,
            "warnings": List[str],
            "errors": List[str],
            "suggestions": List[str]
        }
    """
    try:
        from pymilvus import Collection, connections

        from ..services.quota_manager import QuotaManager

        # 连接 Milvus
        connections.connect(host=settings.milvus.host, port=settings.milvus.port)
        collection = Collection(settings.milvus.collection_name)
        collection.load()

        # 创建配额管理器
        quota_mgr = QuotaManager(collection=collection)

        # 步骤 1: 检查配额状态
        quota_check = quota_mgr.check_quota(user_id, user_tier)

        # 步骤 2: 检查文件大小（如果提供）
        file_size_check = None
        if file_size_bytes is not None:
            file_size_check = quota_mgr.check_file_size(file_size_bytes, user_tier)

        # 计算使用率百分比
        current_usage = quota_check["current_usage"]
        quota_limit = quota_check["quota_limit"]

        usage_percentage = {
            "documents": (current_usage["document_count"] / quota_limit["max_documents"] * 100)
            if quota_limit["max_documents"] > 0
            else 0,
            "storage": (current_usage["storage_mb"] / quota_limit["max_storage_mb"] * 100)
            if quota_limit["max_storage_mb"] > 0
            else 0,
        }

        # 综合判断是否允许上传
        allowed = quota_check["allowed"]
        if file_size_check is not None:
            allowed = allowed and file_size_check["allowed"]

        # 收集错误和警告
        errors = quota_check.get("errors", [])
        if file_size_check is not None and not file_size_check["allowed"]:
            errors.append(file_size_check.get("error", "文件大小超限"))

        warnings = quota_check.get("warnings", [])

        # 生成建议
        suggestions = []
        if not allowed:
            suggestions.extend(
                [
                    "删除不需要的文档以释放空间",
                    "升级会员等级以提升配额",
                ]
            )
        elif warnings:
            suggestions.append("配额使用率较高，建议及时清理文档或升级会员")

        logger.info(
            f" [配额检查] user_id={user_id}, tier={user_tier}, "
            f"allowed={allowed}, "
            f"usage={current_usage['document_count']}/{quota_limit['max_documents']} docs, "
            f"{current_usage['storage_mb']:.2f}/{quota_limit['max_storage_mb']} MB"
        )

        return {
            "allowed": allowed,
            "quota_status": {
                "current_usage": current_usage,
                "quota_limit": quota_limit,
                "usage_percentage": usage_percentage,
            },
            "file_size_check": file_size_check,
            "warnings": warnings,
            "errors": errors,
            "suggestions": suggestions,
        }

    except Exception as e:
        logger.error(f"配额检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
