"""
Tavily搜索工具

提供实时网络搜索功能，用于获取最新的行业信息、技术趋势等
"""

import json
from typing import Dict, List, Optional, Any, Union
import time
from loguru import logger

try:
    from tavily import TavilyClient
except ImportError:
    logger.warning("Tavily library not installed. Please install with: pip install tavily-python")
    TavilyClient = None

from ..core.types import ToolConfig


class TavilySearchTool:
    """Tavily搜索工具类"""
    
    def __init__(self, api_key: str, config: Optional[ToolConfig] = None):
        """
        初始化Tavily搜索工具

        Args:
            api_key: Tavily API密钥
            config: 工具配置
        """
        if TavilyClient is None:
            raise ImportError("Tavily library not installed. Please install with: pip install tavily-python")

        self.api_key = api_key
        self.client = TavilyClient(api_key=api_key)
        self.config = config or ToolConfig(name="tavily_search")
        
        # 默认搜索参数
        self.default_params = {
            "max_results": 10,
            "search_depth": "advanced",
            "include_answer": True,
            "include_raw_content": False,
            "include_images": False
        }
    
    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        search_depth: str = "advanced",
        include_answer: bool = True,
        include_raw_content: bool = False,
        include_images: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行搜索查询
        
        Args:
            query: 搜索查询字符串
            max_results: 最大结果数量
            search_depth: 搜索深度 ("basic" 或 "advanced")
            include_answer: 是否包含答案摘要
            include_raw_content: 是否包含原始内容
            include_images: 是否包含图片
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
                "search_depth": search_depth,
                "include_answer": include_answer,
                "include_raw_content": include_raw_content,
                "include_images": include_images,
                **kwargs
            }
            
            logger.info(f"Executing Tavily search: {query}")
            
            # 执行搜索
            response = self.client.search(**search_params)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # 处理响应
            processed_response = self._process_search_response(response, execution_time)
            
            logger.info(f"Tavily search completed in {execution_time:.2f}s, found {len(processed_response.get('results', []))} results")
            
            return processed_response
            
        except Exception as e:
            logger.error(f"Tavily search failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results": [],
                "execution_time": 0
            }
    
    def qna_search(self, query: str) -> str:
        """
        执行问答搜索，返回简洁答案
        
        Args:
            query: 问题查询
            
        Returns:
            答案字符串
        """
        try:
            logger.info(f"Executing Tavily Q&A search: {query}")
            
            answer = self.client.qna_search(query=query)
            
            logger.info("Tavily Q&A search completed")
            return answer
            
        except Exception as e:
            logger.error(f"Tavily Q&A search failed: {str(e)}")
            return f"搜索失败: {str(e)}"
    
    def get_search_context(self, query: str, max_tokens: int = 4000) -> str:
        """
        获取搜索上下文，用于RAG应用
        
        Args:
            query: 搜索查询
            max_tokens: 最大token数量
            
        Returns:
            上下文字符串
        """
        try:
            logger.info(f"Getting Tavily search context: {query}")
            
            context = self.client.get_search_context(
                query=query,
                max_tokens=max_tokens
            )
            
            logger.info("Tavily search context retrieved")
            return context
            
        except Exception as e:
            logger.error(f"Tavily search context failed: {str(e)}")
            return f"获取上下文失败: {str(e)}"
    
    def extract_content(self, urls: List[str], include_images: bool = False) -> Dict[str, Any]:
        """
        从URL列表提取内容
        
        Args:
            urls: URL列表（最多20个）
            include_images: 是否包含图片
            
        Returns:
            提取结果字典
        """
        try:
            logger.info(f"Extracting content from {len(urls)} URLs")
            
            response = self.client.extract(
                urls=urls,
                include_images=include_images
            )
            
            logger.info(f"Content extraction completed, {len(response.get('results', []))} successful")
            return response
            
        except Exception as e:
            logger.error(f"Content extraction failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "failed_results": urls
            }
    
    def _process_search_response(self, response: Dict[str, Any], execution_time: float) -> Dict[str, Any]:
        """
        处理搜索响应，标准化格式
        
        Args:
            response: 原始响应
            execution_time: 执行时间
            
        Returns:
            处理后的响应
        """
        processed = {
            "success": True,
            "query": response.get("query", ""),
            "answer": response.get("answer", ""),
            "results": [],
            "execution_time": execution_time,
            "total_results": len(response.get("results", []))
        }
        
        # 处理搜索结果
        for result in response.get("results", []):
            processed_result = {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
                "score": result.get("score", 0),
                "published_date": result.get("published_date", ""),
                "raw_content": result.get("raw_content", "") if result.get("raw_content") else None
            }
            processed["results"].append(processed_result)
        
        return processed
    
    def search_for_agent(
        self,
        query: str,
        agent_context: str = "",
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        为智能体优化的搜索方法
        
        Args:
            query: 搜索查询
            agent_context: 智能体上下文信息
            max_results: 最大结果数
            
        Returns:
            优化后的搜索结果
        """
        # 如果有智能体上下文，优化查询
        if agent_context:
            enhanced_query = f"{query} {agent_context}"
        else:
            enhanced_query = query
        
        # 执行搜索
        results = self.search(
            query=enhanced_query,
            max_results=max_results,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=False
        )
        
        # 为智能体优化结果格式
        if results.get("success"):
            # 提取关键信息
            summary = {
                "query": query,
                "answer": results.get("answer", ""),
                "key_findings": [],
                "sources": []
            }
            
            for result in results.get("results", []):
                summary["key_findings"].append({
                    "title": result["title"],
                    "content": result["content"][:200] + "..." if len(result["content"]) > 200 else result["content"],
                    "relevance_score": result.get("score", 0)
                })
                
                summary["sources"].append({
                    "title": result["title"],
                    "url": result["url"],
                    "published_date": result.get("published_date", "")
                })
            
            results["agent_summary"] = summary
        
        return results
    
    def is_available(self) -> bool:
        """
        检查工具是否可用
        
        Returns:
            是否可用
        """
        try:
            # 简单测试搜索
            test_response = self.client.search(
                query="test",
                max_results=1,
                search_depth="basic"
            )
            return True
        except Exception as e:
            logger.error(f"Tavily tool availability check failed: {str(e)}")
            return False
