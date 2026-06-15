"""
Milvus 知识库管理 API 路由 (v7.141+)

功能:
- Collection 状态查询
- 数据导入（文件上传 + 批量导入）
- 搜索测试
- 统计信息
"""

import json
import ast
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel

from ..settings import settings
from ..services.knowledge_package_registry import KnowledgePackageRegistry
from ..services.approved_knowledge_card_service import ApprovedKnowledgeCardService

router = APIRouter(prefix="/api/admin/milvus", tags=["admin", "milvus"])

_SAMPLE_DATA_PATHS = [
    Path(__file__).resolve().parent.parent / "resources" / "knowledge_base_sample_documents.json",
    Path(__file__).resolve().parent.parent / "data" / "knowledge_base_sample_documents.json",
    Path(__file__).resolve().parent.parent.parent / "data" / "knowledge_base_sample_documents.json",
]


# ============================================================================
# Pydantic 模型
# ============================================================================


class SearchTestRequest(BaseModel):
    """搜索测试请求"""

    query: str
    max_results: int = 10
    similarity_threshold: Optional[float] = None
    user_id: Optional[str] = None  #  v7.141: 用户ID（用于过滤私有知识库）
    team_id: Optional[str] = None  #  v7.141.2: 团队ID（用于团队知识库）
    search_scope: str = "all"  #  v7.141: "all" | "system" | "user" | "team"
    knowledge_packages: Optional[List[str]] = None
    search_tags: Optional[List[str]] = None
    project_type: Optional[str] = None


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
    error_message: Optional[str] = None


def _stable_doc_id(doc: Dict[str, Any]) -> str:
    import hashlib

    raw = "{}|{}|{}".format(doc.get("package_id", ""), doc.get("title", ""), doc.get("content", "")[:300])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _connect_milvus():
    from pymilvus import connections

    connections.connect(host=settings.milvus.host, port=settings.milvus.port)


def _ensure_collection():
    """Return a loaded collection, creating the v7.142+ schema when absent."""
    from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, utility

    _connect_milvus()
    if utility.has_collection(settings.milvus.collection_name):
        collection = Collection(settings.milvus.collection_name)
        collection.load()
        return collection

    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=128),
        FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=settings.milvus.embedding_dim),
        FieldSchema(name="document_type", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="tags", dtype=DataType.ARRAY, element_type=DataType.VARCHAR, max_capacity=64, max_length=128),
        FieldSchema(name="project_type", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="package_id", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="source_file", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="source_type", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="review_status", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="knowledge_status", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="owner_type", dtype=DataType.VARCHAR, max_length=32),
        FieldSchema(name="owner_id", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="visibility", dtype=DataType.VARCHAR, max_length=32),
        FieldSchema(name="team_id", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="file_size_bytes", dtype=DataType.INT64),
        FieldSchema(name="created_at", dtype=DataType.INT64),
        FieldSchema(name="expires_at", dtype=DataType.INT64),
        FieldSchema(name="is_deleted", dtype=DataType.BOOL),
        FieldSchema(name="user_tier", dtype=DataType.VARCHAR, max_length=32),
    ]
    schema = CollectionSchema(fields=fields, description="Design knowledge base with logical package routing")
    collection = Collection(settings.milvus.collection_name, schema=schema)
    collection.create_index(
        field_name="vector",
        index_params={"metric_type": "COSINE", "index_type": "HNSW", "params": {"M": 16, "efConstruction": 200}},
    )
    collection.load()
    logger.info(f"Created Milvus collection '{settings.milvus.collection_name}' with knowledge package schema")
    return collection


def _collection_field_names(collection) -> List[str]:
    return [field.name for field in collection.schema.fields]


def _safe_output_fields(collection, requested: List[str]) -> List[str]:
    names = set(_collection_field_names(collection))
    return [field for field in requested if field in names]


def _plain_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {str(key): _plain_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_plain_json_value(item) for item in value]
    if hasattr(value, "item"):
        try:
            return _plain_json_value(value.item())
        except Exception:
            pass
    return str(value)


def _plain_result_row(row: Any, fields: List[str]) -> Dict[str, Any]:
    plain: Dict[str, Any] = {}
    for field in fields:
        value = row.get(field) if hasattr(row, "get") else getattr(row, field, None)
        if value is not None:
            plain_value = _plain_json_value(value)
            plain[field] = _plain_tags_value(plain_value) if field == "tags" else plain_value
    return plain


def _plain_tags_value(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed if item]
        except Exception:
            pass
        return [item.strip().strip("'\"") for item in value.strip("[]").split(",") if item.strip()]
    return [str(value)] if value else []


def _document_output_fields(collection) -> List[str]:
    return _safe_output_fields(
        collection,
        [
            "id",
            "title",
            "content",
            "document_type",
            "tags",
            "project_type",
            "package_id",
            "source_file",
            "source_type",
            "review_status",
            "knowledge_status",
            "owner_type",
            "owner_id",
            "visibility",
            "team_id",
        ],
    )


def _build_document_expr(
    package_id: str = "",
    document_type: str = "",
    project_type: str = "",
    unbound: bool = False,
) -> str:
    exprs = []
    if unbound:
        exprs.append('package_id == ""')
    elif package_id:
        exprs.append(f'package_id == "{package_id}"')
    if document_type:
        exprs.append(f'document_type == "{document_type}"')
    if project_type:
        exprs.append(f'project_type == "{project_type}"')
    return " and ".join(exprs)


def _query_documents(
    collection,
    *,
    limit: int = 50,
    package_id: str = "",
    document_type: str = "",
    project_type: str = "",
    unbound: bool = False,
) -> List[Dict[str, Any]]:
    output_fields = _document_output_fields(collection)
    results = collection.query(
        expr=_build_document_expr(
            package_id=package_id,
            document_type=document_type,
            project_type=project_type,
            unbound=unbound,
        ),
        output_fields=output_fields,
        limit=max(1, min(limit, 1000)),
    )
    return [_plain_result_row(row, output_fields) for row in results]


def _normalise_document(
    doc: Dict[str, Any],
    *,
    document_type: str = "文档",
    project_type: str = "",
    source_file: str = "api_upload",
    owner_type: str = "system",
    owner_id: str = "public",
    visibility: str = "public",
    team_id: str = "",
    user_tier: str = "free",
    expiry_timestamp: int = 0,
    created_at: Optional[int] = None,
) -> Dict[str, Any]:
    now = int(created_at or time.time())
    content = str(doc.get("content", "") or "")
    tags = doc.get("tags", []) or []
    if isinstance(tags, str):
        tags = [item.strip() for item in tags.split(",") if item.strip()]
    package_id = str(doc.get("package_id", "") or "")
    if package_id and package_id not in tags:
        tags = [*tags, package_id]
    normalised = {
        "id": str(doc.get("id") or _stable_doc_id(doc)),
        "title": str(doc.get("title", "无标题") or "无标题")[:512],
        "content": content[:8192],
        "document_type": str(doc.get("document_type", document_type) or document_type)[:128],
        "tags": [str(tag)[:128] for tag in tags[:64] if tag],
        "project_type": str(doc.get("project_type", project_type) or project_type)[:128],
        "package_id": package_id[:128],
        "source_file": str(doc.get("source_file", source_file) or source_file)[:512],
        "source_type": "uploaded_knowledge_document",
        "review_status": "unreviewed",
        "knowledge_status": "raw_imported_document",
        "owner_type": str(doc.get("owner_type", owner_type) or owner_type)[:32],
        "owner_id": str(doc.get("owner_id", owner_id) or owner_id)[:128],
        "visibility": str(doc.get("visibility", visibility) or visibility)[:32],
        "team_id": str(doc.get("team_id", team_id) or team_id)[:128],
        "file_size_bytes": int(doc.get("file_size_bytes") or len(content.encode("utf-8"))),
        "created_at": int(doc.get("created_at") or now),
        "expires_at": int(doc.get("expires_at") or expiry_timestamp or 0),
        "is_deleted": bool(doc.get("is_deleted", False)),
        "user_tier": str(doc.get("user_tier", user_tier) or user_tier)[:32],
    }
    return normalised


def _load_sample_documents() -> tuple[List[Dict[str, Any]], Path]:
    for sample_path in _SAMPLE_DATA_PATHS:
        if sample_path.exists():
            return json.loads(sample_path.read_text(encoding="utf-8")), sample_path
    raise HTTPException(
        status_code=404,
        detail=f"示范数据不存在: {', '.join(str(path) for path in _SAMPLE_DATA_PATHS)}",
    )


def _import_documents_to_milvus(
    documents: List[Dict[str, Any]],
    *,
    document_type: str = "文档",
    project_type: str = "",
    source_file: str = "api_upload",
    owner_type: str = "system",
    owner_id: str = "public",
    visibility: str = "public",
    team_id: str = "",
    user_tier: str = "free",
) -> Dict[str, Any]:
    from ..services.embedding_provider import load_embedding_model

    collection = _ensure_collection()
    embedding_model = load_embedding_model(settings.milvus.embedding_model, dim=settings.milvus.embedding_dim)
    # 旧会员等级配额已退役；知识资产有效期由后续独立用户/权限系统接管。
    expiry_timestamp = 0

    normalised = [
        _normalise_document(
            doc,
            document_type=document_type,
            project_type=project_type,
            source_file=source_file,
            owner_type=owner_type,
            owner_id=owner_id,
            visibility=visibility,
            team_id=team_id,
            user_tier=user_tier,
            expiry_timestamp=expiry_timestamp,
        )
        for doc in documents
    ]
    normalised = _filter_existing_documents(collection, normalised)
    if not normalised:
        return {"success": True, "total_documents": 0, "package_ids": []}
    contents = [doc["content"] for doc in normalised]
    encoded = embedding_model.encode(contents, normalize_embeddings=True, show_progress_bar=False)
    vectors = encoded.tolist() if hasattr(encoded, "tolist") else encoded

    field_names = _collection_field_names(collection)
    values_by_field: Dict[str, List[Any]] = {name: [] for name in field_names}
    for doc, vector in zip(normalised, vectors):
        doc_with_vector = {**doc, "vector": vector}
        for field_name in field_names:
            if field_name in doc_with_vector:
                values_by_field[field_name].append(doc_with_vector[field_name])
    entities = [values_by_field[name] for name in field_names if name in values_by_field and values_by_field[name]]
    collection.insert(entities)
    collection.flush()
    return {
        "success": True,
        "total_documents": len(normalised),
        "package_ids": sorted({doc.get("package_id", "") for doc in normalised if doc.get("package_id")}),
    }


def _filter_existing_documents(collection, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ids = [doc["id"] for doc in documents if doc.get("id")]
    if not ids or "id" not in _collection_field_names(collection):
        return documents
    existing: set[str] = set()
    chunk_size = 128
    for index in range(0, len(ids), chunk_size):
        chunk = ids[index : index + chunk_size]
        expr = "id in [" + ",".join(json.dumps(item, ensure_ascii=False) for item in chunk) + "]"
        try:
            rows = collection.query(expr=expr, output_fields=["id"], limit=len(chunk))
            existing.update(str(row.get("id")) for row in rows if hasattr(row, "get") and row.get("id"))
        except Exception as exc:
            logger.warning(f"检查既有示范文档失败，将继续导入: {exc}")
            return documents
    return [doc for doc in documents if doc.get("id") not in existing]


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
        # 获取或初始化 Collection
        collection = _ensure_collection()

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
    package_id: str = Form(""),
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
        # 读取文件内容
        content = await file.read()
        filename = file.filename

        logger.info(
            "[知识库导入] 旧会员配额检查已退役，按内部知识资产治理流程继续导入: "
            f"owner_type={owner_type}, owner_id={owner_id}"
        )

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
                    "package_id": package_id,
                    "source_file": filename,
                }
            ]
        else:
            raise HTTPException(status_code=400, detail="不支持的文件格式，仅支持 .txt, .md, .json")

        if package_id:
            for doc in documents:
                doc.setdefault("package_id", package_id)

        import_result = _import_documents_to_milvus(
            documents,
            document_type=document_type,
            project_type=project_type,
            source_file=filename or "upload",
            owner_type=owner_type,
            owner_id=owner_id,
            visibility=visibility,
            team_id=team_id,
            user_tier=user_tier,
        )

        logger.info(f" 成功导入 {len(documents)} 个文档")

        return {
            "success": True,
            "message": f"成功导入 {len(documents)} 个文档",
            "total_documents": len(documents),
            "filename": filename,
            "package_ids": import_result.get("package_ids", []),
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
        import_result = _import_documents_to_milvus(documents)

        logger.info(f" 成功批量导入 {len(documents)} 个文档")

        return {
            "success": True,
            "message": f"成功导入 {len(documents)} 个文档",
            "total_documents": len(documents),
            "package_ids": import_result.get("package_ids", []),
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
            context={
                "knowledge_packages": request.knowledge_packages or [],
                "search_tags": request.search_tags or [],
                "project_type": request.project_type or "",
            },
        )

        return _plain_json_value(result)

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
async def get_sample_documents(
    limit: int = 10,
    package_id: str = "",
    document_type: str = "",
    project_type: str = "",
    unbound: bool = False,
):
    """
    获取示例文档（用于预览）

    Args:
        limit: 返回文档数量

    Returns:
        示例文档列表
    """
    try:
        collection = _ensure_collection()

        documents = _query_documents(
            collection,
            limit=limit,
            package_id=package_id,
            document_type=document_type,
            project_type=project_type,
            unbound=unbound,
        )

        return {
            "success": True,
            "total": len(documents),
            "documents": documents,
            "filters": {
                "package_id": package_id,
                "document_type": document_type,
                "project_type": project_type,
                "unbound": unbound,
            },
        }

    except Exception as e:
        logger.error(f"获取示例文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document-types")
async def list_document_types(package_id: str = "", unbound: bool = False):
    """List document_type categories with counts, optionally scoped to one knowledge package."""
    try:
        collection = _ensure_collection()
        docs = _query_documents(collection, limit=1000, package_id=package_id, unbound=unbound)
        counts: Dict[str, int] = {}
        for doc in docs:
            doc_type = str(doc.get("document_type") or "未分类")
            counts[doc_type] = counts.get(doc_type, 0) + 1
        categories = [
            {"document_type": doc_type, "document_count": count}
            for doc_type, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ]
        return {
            "success": True,
            "total": len(categories),
            "package_id": package_id,
            "unbound": unbound,
            "document_types": categories,
        }
    except Exception as e:
        logger.error(f"获取文档类型统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collection/ensure")
async def ensure_collection():
    """Create the Milvus collection when it does not yet exist."""
    try:
        collection = _ensure_collection()
        return {
            "success": True,
            "collection_name": collection.name,
            "fields": _collection_field_names(collection),
            "num_entities": collection.num_entities,
        }
    except Exception as e:
        logger.error(f"初始化 Collection 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-packages")
async def list_knowledge_packages():
    """List logical kp.xxx packages and current Milvus document counts."""
    try:
        registry = KnowledgePackageRegistry()
        packages = registry.list_packages()
        coverage_report = registry.build_coverage_report()
        coverage_by_package = {
            item["package_id"]: item for item in coverage_report.get("packages", [])
        }
        counts: Dict[str, int] = {}
        unbound_document_count = 0
        counts_available = True
        count_error_message = ""
        try:
            collection = _ensure_collection()
            if "package_id" in _collection_field_names(collection):
                for package in packages:
                    package_id = package["package_id"]
                    rows = collection.query(expr=f'package_id == "{package_id}"', output_fields=["id"], limit=16384)
                    counts[package_id] = len(rows)
                unbound_rows = collection.query(expr='package_id == ""', output_fields=["id"], limit=16384)
                unbound_document_count = len(unbound_rows)
        except Exception as count_error:
            counts_available = False
            count_error_message = str(count_error)
            logger.warning(f"知识包计数失败: {count_error}")

        for package in packages:
            package["document_count"] = counts.get(package["package_id"], 0)
            coverage = coverage_by_package.get(package["package_id"], {})
            package["approved_card_ids"] = coverage.get("approved_card_ids", [])
            package["approved_card_count"] = coverage.get("approved_card_count", 0)
            package["activation_pack_ids"] = coverage.get("activation_pack_ids", [])
            package["activation_pack_ref_count"] = coverage.get("activation_pack_ref_count", 0)
            package["coverage_status"] = coverage.get("coverage_status", "registered_only")
        return {
            "success": True,
            "total": len(packages),
            "collection_name": settings.milvus.collection_name,
            "counts_available": counts_available,
            "count_error": count_error_message,
            "unbound_document_count": unbound_document_count,
            "coverage_summary": {
                "approved_card_count": coverage_report.get("approved_card_count", 0),
                "package_with_approved_cards_count": coverage_report.get("package_with_approved_cards_count", 0),
                "activation_referenced_package_count": coverage_report.get("activation_referenced_package_count", 0),
                "missing_approved_cards_for_referenced_packages": coverage_report.get(
                    "missing_approved_cards_for_referenced_packages", []
                ),
            },
            "packages": packages,
        }
    except Exception as e:
        logger.error(f"获取知识包列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-packages/coverage")
async def knowledge_package_coverage():
    """List approved-card coverage and activation-pack references for kp.xxx packages."""
    try:
        registry = KnowledgePackageRegistry()
        return {"success": True, **registry.build_coverage_report()}
    except Exception as e:
        logger.error(f"获取知识包覆盖率失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/approved-knowledge-cards")
async def list_approved_knowledge_cards():
    """List governed approved knowledge cards used by runtime recall."""
    try:
        service = ApprovedKnowledgeCardService()
        return {"success": True, **service.list_cards()}
    except Exception as e:
        logger.error(f"获取已审核知识卡失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/approved-knowledge-cards/health")
async def approved_knowledge_cards_health():
    """Return governance health for approved knowledge cards."""
    try:
        service = ApprovedKnowledgeCardService()
        return {"success": True, **service.health()}
    except Exception as e:
        logger.error(f"获取已审核知识卡健康度失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-packages/import-samples")
async def import_sample_knowledge_documents(package_ids: Optional[List[str]] = Body(default=None)):
    """Import bundled demonstration documents for package-based retrieval."""
    try:
        documents, sample_path = _load_sample_documents()
        if package_ids:
            requested = set(package_ids)
            documents = [doc for doc in documents if doc.get("package_id") in requested]
        if not documents:
            return {"success": True, "message": "没有需要导入的示范文档", "total_documents": 0}

        result = _import_documents_to_milvus(
            documents,
            document_type="示范知识",
            source_file=sample_path.name,
            owner_type="system",
            owner_id="public",
            visibility="public",
            user_tier="enterprise",
        )
        return {
            "success": True,
            "message": f"成功导入 {result['total_documents']} 条知识库示范数据",
            **result,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导入知识库示范数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 配额检查 API（ v7.141.3 - P1-1: 前端上传前检查）
# ============================================================================


@router.get("/quota/check")
async def check_quota_before_upload(
    user_id: str,
    user_tier: str = "free",
    file_size_bytes: Optional[int] = None,
):
    """旧会员配额检查兼容端点。

    旧 free/basic/professional 会员配额已经退役。端点暂时保留为兼容层，
    避免旧前端缓存或人工访问导致 500；真实限制由后续独立用户/权限系统接管。
    """
    file_size_mb = round(file_size_bytes / 1024 / 1024, 2) if file_size_bytes else 0
    return {
        "allowed": True,
        "quota_status": {
            "current_usage": {"document_count": 0, "storage_mb": 0},
            "quota_limit": {
                "max_documents": -1,
                "max_storage_mb": -1,
                "max_file_size_mb": -1,
            },
            "usage_percentage": {"documents": 0, "storage": 0},
        },
        "file_size_check": {
            "allowed": True,
            "file_size_mb": file_size_mb,
            "max_file_size_mb": -1,
        }
        if file_size_bytes is not None
        else None,
        "warnings": ["旧会员配额已停用"],
        "errors": [],
        "suggestions": ["当前按内部知识资产治理流程放行"],
    }
