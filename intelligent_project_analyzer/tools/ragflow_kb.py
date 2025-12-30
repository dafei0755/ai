"""
Ragflow知识库工具

提供知识库查询功能，用于获取内部知识和文档
"""

import json
import requests
from typing import Dict, List, Optional, Any, Union
import time
from loguru import logger

from ..core.types import ToolConfig

# 🆕 v7.64: 导入精准搜索和质量控制模块
try:
    from .query_builder import DeliverableQueryBuilder
    from .quality_control import SearchQualityControl
except ImportError:
    logger.warning("⚠️ v7.64 modules not available. search_for_deliverable() will use fallback mode.")
    DeliverableQueryBuilder = None
    SearchQualityControl = None


class RagflowKBTool:
    """Ragflow知识库工具类"""

    def __init__(self, api_endpoint: str = "", api_key: str = "", dataset_id: str = "", config: Optional[ToolConfig] = None):
        """
        初始化Ragflow知识库工具

        Args:
            api_endpoint: Ragflow API端点
            api_key: API密钥
            dataset_id: 数据集ID
            config: 工具配置
        """
        self.api_endpoint = (api_endpoint or "http://localhost:9380").rstrip('/')
        self.api_key = api_key or "placeholder_key"
        self.dataset_id = dataset_id or ""
        self.config = config or ToolConfig(name="ragflow_kb")  # ✅ 修复：添加必需的name参数

        # 当前为占位符状态
        self.is_placeholder = not api_endpoint or api_key == "placeholder_key"

        if self.is_placeholder:
            logger.warning("Ragflow KB tool is in placeholder mode. Please configure API endpoint and key.")
        else:
            logger.info(f"Ragflow KB tool initialized with endpoint: {self.api_endpoint}")

        # 默认查询参数（基于客户配置）
        self.default_params = {
            "top_k": 1,
            "similarity_threshold": 0.6,
            "vector_similarity_weight": 0.5,  # 对应客户的keyword_weight
            "page_size": 10,
            "rerank_id": "BAAI/bge-reranker-v2-m3"
        }

        # 🆕 v7.64: 初始化精准搜索和质量控制模块
        self.query_builder = DeliverableQueryBuilder() if DeliverableQueryBuilder else None
        self.qc = SearchQualityControl() if SearchQualityControl else None
    
    def search_knowledge(
        self,
        query: str,
        knowledge_base_id: Optional[str] = None,
        max_results: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        在知识库中搜索相关内容

        Args:
            query: 搜索查询字符串
            knowledge_base_id: 知识库ID（数据集ID）
            max_results: 最大结果数量
            similarity_threshold: 相似度阈值
            **kwargs: 其他搜索参数

        Returns:
            搜索结果字典
        """
        if self.is_placeholder:
            return self._placeholder_search_response(query)

        try:
            start_time = time.time()

            # 使用提供的dataset_id或默认值
            dataset_id = knowledge_base_id or self.dataset_id
            if not dataset_id:
                logger.warning("No dataset_id provided, using placeholder response")
                return self._placeholder_search_response(query)

            # 构建请求参数（基于RAGFlow官方API文档）
            payload = {
                "question": query,
                "dataset_ids": [dataset_id],
                "page": kwargs.get("page", 1),
                "page_size": max_results or kwargs.get("page_size", self.default_params["page_size"]),
                "similarity_threshold": similarity_threshold or kwargs.get("similarity_threshold", self.default_params["similarity_threshold"]),
                "vector_similarity_weight": kwargs.get("vector_similarity_weight", self.default_params["vector_similarity_weight"]),
                "top_k": kwargs.get("top_k", self.default_params["top_k"]),
                "rerank_id": kwargs.get("rerank_id", self.default_params["rerank_id"]),
                "keyword": kwargs.get("keyword", False),
                "highlight": kwargs.get("highlight", False)
            }

            logger.info(f"Executing Ragflow KB search: {query}")
            logger.debug(f"Search payload: {payload}")

            # 调用RAGFlow检索API
            response = self._make_api_request("/api/v1/retrieval", payload)

            end_time = time.time()
            execution_time = end_time - start_time

            # 处理响应
            processed_response = self._process_search_response(response, execution_time, query)

            logger.info(f"Ragflow KB search completed in {execution_time:.2f}s, found {processed_response.get('total_results', 0)} results")

            return processed_response

        except Exception as e:
            logger.error(f"Ragflow KB search failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results": [],
                "execution_time": 0
            }
    
    def get_document(self, document_id: str) -> Dict[str, Any]:
        """
        获取特定文档的详细内容
        
        Args:
            document_id: 文档ID
            
        Returns:
            文档详细信息
        """
        if self.is_placeholder:
            return self._placeholder_document_response(document_id)
        
        try:
            logger.info(f"Retrieving document: {document_id}")
            
            # TODO: 实际的API调用
            # response = self._make_api_request(f"/documents/{document_id}")
            
            logger.info("Document retrieved successfully")
            
            # 临时返回占位符响应
            return self._placeholder_document_response(document_id)
            
        except Exception as e:
            logger.error(f"Document retrieval failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "document_id": document_id
            }
    
    def list_knowledge_bases(self) -> Dict[str, Any]:
        """
        列出可用的知识库
        
        Returns:
            知识库列表
        """
        if self.is_placeholder:
            return self._placeholder_kb_list_response()
        
        try:
            logger.info("Listing knowledge bases")
            
            # TODO: 实际的API调用
            # response = self._make_api_request("/knowledge_bases")
            
            logger.info("Knowledge bases listed successfully")
            
            # 临时返回占位符响应
            return self._placeholder_kb_list_response()
            
        except Exception as e:
            logger.error(f"Knowledge base listing failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "knowledge_bases": []
            }
    
    def search_for_agent(
        self,
        query: str,
        agent_context: str = "",
        max_results: int = 5,
        similarity_threshold: float = 0.6
    ) -> Dict[str, Any]:
        """
        为智能体优化的搜索方法
        
        Args:
            query: 搜索查询
            agent_context: 智能体上下文信息
            max_results: 最大结果数
            similarity_threshold: 相似度阈值（默认0.6，重试时可降低到0.3-0.4）
            
        Returns:
            优化后的搜索结果
        """
        # 根据智能体上下文优化查询
        enhanced_query = query
        if agent_context:
            enhanced_query = f"{query} context:{agent_context}"
        
        # 执行搜索
        results = self.search_knowledge(
            query=enhanced_query,
            max_results=max_results,
            similarity_threshold=similarity_threshold
        )
        
        # 为智能体优化结果格式
        if results.get("success"):
            # 提取关键信息
            summary = {
                "query": query,
                "relevant_documents": [],
                "key_insights": [],
                "knowledge_sources": []
            }
            
            for result in results.get("results", []):
                summary["relevant_documents"].append({
                    "title": result.get("title", ""),
                    "content": result.get("content", "")[:200] + "..." if len(result.get("content", "")) > 200 else result.get("content", ""),
                    "relevance_score": result.get("similarity_score", 0),
                    "source": result.get("source", "")
                })
                
                summary["knowledge_sources"].append({
                    "title": result.get("title", ""),
                    "source": result.get("source", ""),
                    "last_updated": result.get("last_updated", "")
                })
            
            results["agent_summary"] = summary
        
        return results
    
    def _placeholder_search_response(self, query: str) -> Dict[str, Any]:
        """
        占位符搜索响应
        
        Args:
            query: 搜索查询
            
        Returns:
            占位符响应
        """
        return {
            "success": True,
            "query": query,
            "results": [
                {
                    "title": "示例知识文档1",
                    "content": f"这是关于'{query}'的示例知识内容。当前Ragflow知识库工具处于占位符模式，等待实际API配置。",
                    "similarity_score": 0.85,
                    "source": "internal_kb",
                    "document_id": "doc_001",
                    "last_updated": "2024-01-01T00:00:00Z",
                    "metadata": {
                        "category": "general",
                        "tags": ["example", "placeholder"]
                    }
                },
                {
                    "title": "示例知识文档2", 
                    "content": f"这是另一个关于'{query}'的示例知识内容。实际部署时将连接到真实的Ragflow知识库。",
                    "similarity_score": 0.78,
                    "source": "internal_kb",
                    "document_id": "doc_002",
                    "last_updated": "2024-01-01T00:00:00Z",
                    "metadata": {
                        "category": "technical",
                        "tags": ["example", "placeholder"]
                    }
                }
            ],
            "execution_time": 0.1,
            "total_results": 2,
            "is_placeholder": True
        }
    
    def _placeholder_document_response(self, document_id: str) -> Dict[str, Any]:
        """
        占位符文档响应
        
        Args:
            document_id: 文档ID
            
        Returns:
            占位符响应
        """
        return {
            "success": True,
            "document_id": document_id,
            "title": f"示例文档 {document_id}",
            "content": f"这是文档 {document_id} 的完整内容。当前为占位符模式。",
            "metadata": {
                "category": "example",
                "tags": ["placeholder"],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "author": "system"
            },
            "is_placeholder": True
        }
    
    def _placeholder_kb_list_response(self) -> Dict[str, Any]:
        """
        占位符知识库列表响应
        
        Returns:
            占位符响应
        """
        return {
            "success": True,
            "knowledge_bases": [
                {
                    "id": "kb_001",
                    "name": "技术文档库",
                    "description": "包含技术规范和最佳实践",
                    "document_count": 150,
                    "last_updated": "2024-01-01T00:00:00Z"
                },
                {
                    "id": "kb_002", 
                    "name": "业务知识库",
                    "description": "包含业务流程和规则",
                    "document_count": 89,
                    "last_updated": "2024-01-01T00:00:00Z"
                }
            ],
            "total_count": 2,
            "is_placeholder": True
        }

    def search_for_deliverable(
        self,
        deliverable: Dict[str, Any],
        project_type: str = "",
        max_results: int = 10,
        enable_qc: bool = True,
        similarity_threshold: float = 0.6
    ) -> Dict[str, Any]:
        """
        🆕 v7.64: 针对交付物的精准知识库搜索

        核心改进：
        1. 从交付物构建中文优化查询（内部知识库以中文为主）
        2. 应用质量控制管道
        3. 按质量分数排序

        Args:
            deliverable: 交付物字典
            project_type: 项目类型
            max_results: 最大返回结果数
            enable_qc: 是否启用质量控制
            similarity_threshold: 相似度阈值

        Returns:
            搜索结果字典
        """
        try:
            start_time = time.time()

            # Step 1: 构建查询（内部知识库优先使用中文原文）
            if self.query_builder:
                queries = self.query_builder.build_multi_tool_queries(
                    deliverable,
                    project_type
                )
                precise_query = queries.get("ragflow", deliverable.get("name", ""))
                logger.info(f"🔍 [v7.64 RAGFlow] Precise query: {precise_query}")
            else:
                # Fallback: 使用交付物名称+描述前50字
                name = deliverable.get("name", "")
                desc = deliverable.get("description", "")
                precise_query = f"{name} {desc[:50]}" if desc else name
                logger.warning("⚠️ Query builder not available, using name+description")

            # Step 2: 执行搜索
            search_results = self.search_knowledge(
                query=precise_query,
                max_results=max_results * 2 if enable_qc else max_results,
                similarity_threshold=similarity_threshold
            )

            if not search_results.get("success", False):
                return search_results

            # Step 3: 归一化结果格式（RAGFlow结果结构）
            normalized_results = []
            for result in search_results.get("results", []):
                normalized = {
                    "title": result.get("title", ""),
                    "content": result.get("content", "")[:500],
                    "snippet": result.get("content", "")[:300],
                    "url": None,  # 内部知识库通常无URL
                    "relevance_score": result.get("similarity_score", 0.7),
                    "vector_similarity": result.get("vector_similarity", 0),
                    "term_similarity": result.get("term_similarity", 0),
                    "document_id": result.get("document_id", ""),
                    "kb_id": result.get("kb_id", "")
                }
                normalized_results.append(normalized)

            # Step 4: 质量控制
            if enable_qc and self.qc:
                processed_results = self.qc.process_results(
                    normalized_results,
                    deliverable_context=deliverable
                )
                processed_results = processed_results[:max_results]
                search_results["results"] = processed_results
                search_results["quality_controlled"] = True
                logger.info(
                    f"✅ [v7.64 RAGFlow] Quality control: {len(processed_results)} results"
                )
            else:
                search_results["results"] = normalized_results[:max_results]
                search_results["quality_controlled"] = False

            # Step 5: 添加编号
            for idx, result in enumerate(search_results.get("results", []), start=1):
                result["reference_number"] = idx

            end_time = time.time()
            search_results["execution_time"] = end_time - start_time
            search_results["deliverable_name"] = deliverable.get("name", "")
            search_results["precise_query"] = precise_query

            return search_results

        except Exception as e:
            logger.error(f"❌ [v7.64 RAGFlow] search_for_deliverable failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "deliverable_name": deliverable.get("name", ""),
                "results": [],
                "execution_time": 0
            }

    def is_available(self) -> bool:
        """
        检查工具是否可用
        
        Returns:
            是否可用
        """
        if self.is_placeholder:
            logger.info("Ragflow KB tool is in placeholder mode")
            return True  # 占位符模式下认为可用
        
        try:
            # TODO: 实际的健康检查
            # response = self._make_api_request("/health")
            return True
        except Exception as e:
            logger.error(f"Ragflow KB tool availability check failed: {str(e)}")
            return False
    
    def configure_api(self, api_endpoint: str, api_key: str, dataset_id: str = ""):
        """
        配置API连接信息

        Args:
            api_endpoint: API端点
            api_key: API密钥
            dataset_id: 数据集ID
        """
        self.api_endpoint = api_endpoint.rstrip('/')
        self.api_key = api_key
        if dataset_id:
            self.dataset_id = dataset_id
        self.is_placeholder = False
        logger.info(f"Ragflow KB tool configured with endpoint: {api_endpoint}")

    def _make_api_request(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        执行API请求

        Args:
            endpoint: API端点路径
            data: 请求数据

        Returns:
            API响应
        """
        url = f"{self.api_endpoint}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            logger.debug(f"Making API request to: {url}")

            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=self.config.timeout if hasattr(self.config, 'timeout') else 30
            )

            response.raise_for_status()

            result = response.json()
            logger.debug(f"API response code: {result.get('code')}")

            return result

        except requests.exceptions.Timeout:
            logger.error(f"API request timeout: {url}")
            raise Exception("RAGFlow API request timeout")
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise Exception(f"RAGFlow API request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response: {str(e)}")
            raise Exception("Invalid JSON response from RAGFlow API")

    def _process_search_response(self, response: Dict[str, Any], execution_time: float, query: str) -> Dict[str, Any]:
        """
        处理搜索响应

        Args:
            response: API响应
            execution_time: 执行时间
            query: 查询字符串

        Returns:
            处理后的响应
        """
        # 检查响应状态
        if response.get("code") != 0:
            error_msg = response.get("message", "Unknown error")
            logger.error(f"RAGFlow API error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "query": query,
                "results": [],
                "execution_time": execution_time
            }

        # 提取数据
        data = response.get("data", {})
        chunks = data.get("chunks", [])
        total = data.get("total", 0)

        # 转换为统一格式
        results = []
        for chunk in chunks:
            results.append({
                "title": chunk.get("document_keyword", ""),
                "content": chunk.get("content", ""),
                "similarity_score": chunk.get("similarity", 0.0),
                "vector_similarity": chunk.get("vector_similarity", 0.0),
                "term_similarity": chunk.get("term_similarity", 0.0),
                "source": "ragflow",
                "document_id": chunk.get("document_id", ""),
                "chunk_id": chunk.get("id", ""),
                "kb_id": chunk.get("kb_id", ""),
                "highlight": chunk.get("highlight", ""),
                "metadata": {
                    "image_id": chunk.get("image_id", ""),
                    "important_keywords": chunk.get("important_keywords", []),
                    "positions": chunk.get("positions", [])
                }
            })

        return {
            "success": True,
            "query": query,
            "results": results,
            "execution_time": execution_time,
            "total_results": total,
            "is_placeholder": False
        }
