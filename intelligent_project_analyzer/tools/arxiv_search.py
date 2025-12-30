"""
Arxiv学术搜索工具

提供学术论文搜索功能，用于获取相关研究和技术文献
"""

import json
from typing import Dict, List, Optional, Any, Union
import time
from datetime import datetime
from loguru import logger

try:
    import arxiv
except ImportError:
    logger.warning("Arxiv library not installed. Please install with: pip install arxiv")
    arxiv = None

from ..core.types import ToolConfig

# 🆕 v7.64: 导入精准搜索和质量控制模块
try:
    from .query_builder import DeliverableQueryBuilder
    from .quality_control import SearchQualityControl
except ImportError:
    logger.warning("⚠️ v7.64 modules not available. search_for_deliverable() will use fallback mode.")
    DeliverableQueryBuilder = None
    SearchQualityControl = None


class ArxivSearchTool:
    """Arxiv学术搜索工具类"""
    
    def __init__(self, config: Optional[ToolConfig] = None):
        """
        初始化Arxiv搜索工具

        Args:
            config: 工具配置
        """
        if arxiv is None:
            raise ImportError("Arxiv library not installed. Please install with: pip install arxiv")

        self.config = config or ToolConfig(name="arxiv_search")

        # 初始化客户端
        self.client = arxiv.Client(
            page_size=100,  # 每页结果数
            delay_seconds=3.0,  # 请求间延迟
            num_retries=3  # 重试次数
        )

        # 默认搜索参数
        self.default_params = {
            "max_results": 10,
            "sort_by": arxiv.SortCriterion.Relevance,
            "sort_order": arxiv.SortOrder.Descending
        }

        # 🆕 v7.64: 初始化精准搜索和质量控制模块
        self.query_builder = DeliverableQueryBuilder() if DeliverableQueryBuilder else None
        self.qc = SearchQualityControl() if SearchQualityControl else None
    
    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        sort_by: Optional[arxiv.SortCriterion] = None,
        sort_order: Optional[arxiv.SortOrder] = None,
        categories: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行学术论文搜索
        
        Args:
            query: 搜索查询字符串
            max_results: 最大结果数量
            sort_by: 排序方式
            sort_order: 排序顺序
            categories: 论文分类过滤
            **kwargs: 其他搜索参数
            
        Returns:
            搜索结果字典
        """
        try:
            start_time = time.time()
            
            # 准备搜索参数
            search_params = {
                "query": query,
                "max_results": max_results or self.default_params["max_results"],
                "sort_by": sort_by or self.default_params["sort_by"],
                "sort_order": sort_order or self.default_params["sort_order"]
            }
            
            # 如果指定了分类，添加到查询中
            if categories:
                category_filter = " OR ".join([f"cat:{cat}" for cat in categories])
                search_params["query"] = f"({query}) AND ({category_filter})"
            
            logger.info(f"Executing Arxiv search: {query}")
            
            # 创建搜索对象
            search = arxiv.Search(**search_params)
            
            # 执行搜索
            results = list(self.client.results(search))
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # 处理响应
            processed_response = self._process_search_response(results, query, execution_time)
            
            logger.info(f"Arxiv search completed in {execution_time:.2f}s, found {len(results)} results")
            
            return processed_response
            
        except Exception as e:
            logger.error(f"Arxiv search failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results": [],
                "execution_time": 0
            }
    
    def search_by_id(self, paper_ids: List[str]) -> Dict[str, Any]:
        """
        根据论文ID搜索
        
        Args:
            paper_ids: 论文ID列表
            
        Returns:
            搜索结果字典
        """
        try:
            start_time = time.time()
            
            logger.info(f"Searching Arxiv by IDs: {paper_ids}")
            
            # 创建ID搜索
            search = arxiv.Search(id_list=paper_ids)
            results = list(self.client.results(search))
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # 处理响应
            processed_response = self._process_search_response(results, f"IDs: {paper_ids}", execution_time)
            
            logger.info(f"Arxiv ID search completed in {execution_time:.2f}s")
            
            return processed_response
            
        except Exception as e:
            logger.error(f"Arxiv ID search failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": f"IDs: {paper_ids}",
                "results": [],
                "execution_time": 0
            }
    
    def search_recent_papers(
        self,
        query: str,
        days_back: int = 30,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        搜索最近发布的论文
        
        Args:
            query: 搜索查询
            days_back: 回溯天数
            max_results: 最大结果数
            
        Returns:
            搜索结果字典
        """
        return self.search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )
    
    def search_by_author(self, author_name: str, max_results: int = 10) -> Dict[str, Any]:
        """
        根据作者搜索论文
        
        Args:
            author_name: 作者姓名
            max_results: 最大结果数
            
        Returns:
            搜索结果字典
        """
        query = f"au:{author_name}"
        return self.search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )
    
    def search_by_category(
        self,
        categories: List[str],
        query: str = "",
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        根据分类搜索论文
        
        Args:
            categories: 分类列表 (如 ["cs.AI", "cs.LG"])
            query: 额外查询条件
            max_results: 最大结果数
            
        Returns:
            搜索结果字典
        """
        category_query = " OR ".join([f"cat:{cat}" for cat in categories])
        
        if query:
            full_query = f"({query}) AND ({category_query})"
        else:
            full_query = category_query
        
        return self.search(
            query=full_query,
            max_results=max_results
        )
    
    def _process_search_response(
        self,
        results: List[arxiv.Result],
        query: str,
        execution_time: float
    ) -> Dict[str, Any]:
        """
        处理搜索响应，标准化格式
        
        Args:
            results: Arxiv搜索结果列表
            query: 原始查询
            execution_time: 执行时间
            
        Returns:
            处理后的响应
        """
        processed = {
            "success": True,
            "query": query,
            "results": [],
            "execution_time": execution_time,
            "total_results": len(results)
        }
        
        # 处理每个结果
        for result in results:
            processed_result = {
                "title": result.title,
                "authors": [author.name for author in result.authors],
                "summary": result.summary,
                "published": result.published.isoformat() if result.published else None,
                "updated": result.updated.isoformat() if result.updated else None,
                "entry_id": result.entry_id,
                "arxiv_id": result.get_short_id(),
                "categories": result.categories,
                "primary_category": result.primary_category,
                "pdf_url": result.pdf_url,
                "links": [{"href": link.href, "title": link.title} for link in result.links],
                "journal_ref": result.journal_ref,
                "doi": result.doi,
                "comment": result.comment
            }
            processed["results"].append(processed_result)
        
        return processed
    
    def search_for_agent(
        self,
        query: str,
        agent_context: str = "",
        max_results: int = 5,
        focus_recent: bool = True
    ) -> Dict[str, Any]:
        """
        为智能体优化的搜索方法
        
        Args:
            query: 搜索查询
            agent_context: 智能体上下文信息
            max_results: 最大结果数
            focus_recent: 是否关注最新论文
            
        Returns:
            优化后的搜索结果
        """
        # 根据智能体上下文优化查询
        enhanced_query = query
        if agent_context:
            # 可以根据不同智能体类型添加特定的分类过滤
            if "技术" in agent_context or "architecture" in agent_context.lower():
                enhanced_query = f"({query}) AND (cat:cs.SE OR cat:cs.AI OR cat:cs.LG)"
            elif "设计" in agent_context or "design" in agent_context.lower():
                enhanced_query = f"({query}) AND (cat:cs.HC OR cat:cs.AI)"
            elif "商业" in agent_context or "business" in agent_context.lower():
                enhanced_query = f"({query}) AND (cat:econ.* OR cat:cs.CY)"
        
        # 执行搜索
        sort_by = arxiv.SortCriterion.SubmittedDate if focus_recent else arxiv.SortCriterion.Relevance
        
        results = self.search(
            query=enhanced_query,
            max_results=max_results,
            sort_by=sort_by,
            sort_order=arxiv.SortOrder.Descending
        )
        
        # 为智能体优化结果格式
        if results.get("success"):
            # 提取关键信息
            summary = {
                "query": query,
                "key_papers": [],
                "research_trends": [],
                "relevant_authors": set(),
                "categories": set()
            }
            
            for result in results.get("results", []):
                # 关键论文信息
                summary["key_papers"].append({
                    "title": result["title"],
                    "authors": result["authors"][:3],  # 前3个作者
                    "summary": result["summary"][:300] + "..." if len(result["summary"]) > 300 else result["summary"],
                    "published": result["published"],
                    "arxiv_id": result["arxiv_id"],
                    "categories": result["categories"]
                })
                
                # 收集作者和分类信息
                summary["relevant_authors"].update(result["authors"][:2])  # 前2个作者
                summary["categories"].update(result["categories"])
            
            # 转换集合为列表
            summary["relevant_authors"] = list(summary["relevant_authors"])[:10]  # 最多10个作者
            summary["categories"] = list(summary["categories"])
            
            results["agent_summary"] = summary

        return results

    def search_for_deliverable(
        self,
        deliverable: Dict[str, Any],
        project_type: str = "",
        max_results: int = 10,
        enable_qc: bool = True,
        focus_recent: bool = False
    ) -> Dict[str, Any]:
        """
        🆕 v7.64: 针对交付物的精准学术搜索

        核心改进：
        1. 从交付物构建学术化查询（强调方法论术语）
        2. 应用质量控制管道
        3. 自动添加学科分类过滤（基于项目类型）

        Args:
            deliverable: 交付物字典
            project_type: 项目类型
            max_results: 最大返回结果数
            enable_qc: 是否启用质量控制
            focus_recent: 是否关注最新论文

        Returns:
            搜索结果字典
        """
        try:
            start_time = time.time()

            # Step 1: 构建学术化查询
            if self.query_builder:
                # 使用专门的Arxiv查询构建器
                queries = self.query_builder.build_multi_tool_queries(
                    deliverable,
                    project_type
                )
                precise_query = queries.get("arxiv", deliverable.get("name", ""))
                logger.info(f"🔍 [v7.64 Arxiv] Precise query: {precise_query}")
            else:
                precise_query = deliverable.get("name", "")
                logger.warning("⚠️ Query builder not available, using deliverable name")

            # Step 2: 执行搜索
            sort_by = arxiv.SortCriterion.SubmittedDate if focus_recent else arxiv.SortCriterion.Relevance

            search_results = self.search(
                query=precise_query,
                max_results=max_results * 2 if enable_qc else max_results,
                sort_by=sort_by,
                sort_order=arxiv.SortOrder.Descending
            )

            if not search_results.get("success", False):
                return search_results

            # Step 3: 归一化结果格式（Arxiv结果结构不同于Tavily）
            normalized_results = []
            for result in search_results.get("results", []):
                normalized = {
                    "title": result.get("title", ""),
                    "content": result.get("summary", "")[:500],  # 限制摘要长度
                    "snippet": result.get("summary", "")[:300],
                    "url": result.get("pdf_url", ""),
                    "relevance_score": 0.8,  # Arxiv无相关性分数，使用默认值
                    "published_date": result.get("published", ""),
                    "authors": result.get("authors", []),
                    "arxiv_id": result.get("arxiv_id", "")
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
                    f"✅ [v7.64 Arxiv] Quality control: {len(processed_results)} results"
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
            logger.error(f"❌ [v7.64 Arxiv] search_for_deliverable failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "deliverable_name": deliverable.get("name", ""),
                "results": [],
                "execution_time": 0
            }

    def get_paper_details(self, arxiv_id: str) -> Dict[str, Any]:
        """
        获取特定论文的详细信息
        
        Args:
            arxiv_id: Arxiv论文ID
            
        Returns:
            论文详细信息
        """
        return self.search_by_id([arxiv_id])
    
    def is_available(self) -> bool:
        """
        检查工具是否可用
        
        Returns:
            是否可用
        """
        try:
            # 简单测试搜索
            test_search = arxiv.Search(query="test", max_results=1)
            test_results = list(self.client.results(test_search))
            return True
        except Exception as e:
            logger.error(f"Arxiv tool availability check failed: {str(e)}")
            return False
