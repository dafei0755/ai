"""
Tavily搜索工具

提供实时网络搜索功能，用于获取最新的行业信息、技术趋势等
"""

import json
import time
from typing import Any, Dict, List, Optional, Union

from loguru import logger

try:
    from tavily import TavilyClient
except ImportError:
    logger.warning("Tavily library not installed. Please install with: pip install tavily-python")
    TavilyClient = None

from ..core.types import ToolConfig

# LangChain Tool integration
try:
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, Field

    LANGCHAIN_AVAILABLE = True
except ImportError:
    logger.warning("LangChain not available, tool wrapping disabled")
    LANGCHAIN_AVAILABLE = False

# 🆕 v7.64: 导入精准搜索和质量控制模块
try:
    from .quality_control import SearchQualityControl
    from .query_builder import DeliverableQueryBuilder
except ImportError:
    logger.warning("⚠️ v7.64 modules not available. search_for_deliverable() will use fallback mode.")
    DeliverableQueryBuilder = None
    SearchQualityControl = None


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
        self.name = self.config.name  # LangChain compatibility

        # 默认搜索参数
        self.default_params = {
            "max_results": 10,
            "search_depth": "advanced",
            "include_answer": True,
            "include_raw_content": False,
            "include_images": False,
        }

        # 🆕 v7.64: 初始化精准搜索和质量控制模块
        self.query_builder = DeliverableQueryBuilder() if DeliverableQueryBuilder else None
        self.qc = SearchQualityControl() if SearchQualityControl else None

    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        search_depth: str = "advanced",
        include_answer: bool = True,
        include_raw_content: bool = False,
        include_images: bool = False,
        **kwargs,
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
                **kwargs,
            }

            logger.info(f"🔍 [Tavily] Starting search")
            logger.info(f"📝 [Tavily] Query: {query}")
            logger.debug(f"⚙️ [Tavily] Search params: {json.dumps(search_params, ensure_ascii=False, indent=2)}")

            # 执行搜索
            logger.debug(f"🌐 [Tavily] Calling Tavily API...")
            api_start = time.time()
            response = self.client.search(**search_params)
            api_time = time.time() - api_start

            logger.info(f"✅ [Tavily] API call completed in {api_time:.2f}s")
            logger.debug(f"📥 [Tavily] Raw response keys: {list(response.keys())}")
            logger.debug(
                f"📊 [Tavily] Response summary: {len(response.get('results', []))} results, has_answer={bool(response.get('answer'))}"
            )

            # 处理响应
            logger.debug(f"⚙️ [Tavily] Processing response...")
            process_start = time.time()
            processed_response = self._process_search_response(response, time.time() - start_time)
            process_time = time.time() - process_start

            logger.debug(f"⚙️ [Tavily] Response processing took {process_time:.2f}s")
            logger.info(
                f"✅ [Tavily] Search completed in {processed_response['execution_time']:.2f}s, found {len(processed_response.get('results', []))} results"
            )

            return processed_response

        except Exception as e:
            logger.error(f"❌ [Tavily] Search failed: {str(e)}", exc_info=True)
            logger.error(f"❌ [Tavily] Failed query: {query}")
            logger.error(
                f"❌ [Tavily] Failed params: {json.dumps(search_params if 'search_params' in locals() else {}, ensure_ascii=False)}"
            )
            return {"success": False, "error": str(e), "query": query, "results": [], "execution_time": 0}

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

            context = self.client.get_search_context(query=query, max_tokens=max_tokens)

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

            response = self.client.extract(urls=urls, include_images=include_images)

            logger.info(f"Content extraction completed, {len(response.get('results', []))} successful")
            return response

        except Exception as e:
            logger.error(f"Content extraction failed: {str(e)}")
            return {"success": False, "error": str(e), "results": [], "failed_results": urls}

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
            "total_results": len(response.get("results", [])),
        }

        # 处理搜索结果
        for result in response.get("results", []):
            processed_result = {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
                "score": result.get("score", 0),
                "published_date": result.get("published_date", ""),
                "raw_content": result.get("raw_content", "") if result.get("raw_content") else None,
            }
            processed["results"].append(processed_result)

        return processed

    def search_for_agent(self, query: str, agent_context: str = "", max_results: int = 5) -> Dict[str, Any]:
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
            include_raw_content=False,
        )

        # 为智能体优化结果格式
        if results.get("success"):
            # 提取关键信息
            summary = {"query": query, "answer": results.get("answer", ""), "key_findings": [], "sources": []}

            for result in results.get("results", []):
                summary["key_findings"].append(
                    {
                        "title": result["title"],
                        "content": result["content"][:200] + "..."
                        if len(result["content"]) > 200
                        else result["content"],
                        "relevance_score": result.get("score", 0),
                    }
                )

                summary["sources"].append(
                    {"title": result["title"], "url": result["url"], "published_date": result.get("published_date", "")}
                )

            results["agent_summary"] = summary

        return results

    def search_for_deliverable(
        self,
        deliverable: Dict[str, Any],
        project_type: str = "",
        max_results: int = 10,
        enable_qc: bool = True,
        similarity_threshold: float = 0.6,
    ) -> Dict[str, Any]:
        """
        🆕 v7.64: 针对交付物的精准搜索

        核心改进：
        1. 从交付物的name + description提取关键词构建精准查询
        2. 应用质量控制管道（过滤 → 去重 → 评分 → 排序）
        3. 按质量分数编号排序

        Args:
            deliverable: 交付物字典，包含name, description, format等
            project_type: 项目类型（用于上下文优化）
            max_results: 最大返回结果数
            enable_qc: 是否启用质量控制
            similarity_threshold: 相关性阈值（0-1）

        Returns:
            搜索结果字典，包含排序后的高质量结果

        Example:
            >>> deliverable = {
            ...     "name": "用户画像",
            ...     "description": "构建目标用户的详细画像，包括需求、行为、痛点",
            ...     "format": "persona"
            ... }
            >>> results = tool.search_for_deliverable(deliverable, "commercial_space")
            >>> # 返回按质量分数排序的结果，每个结果包含quality_score
        """
        try:
            start_time = time.time()
            deliverable_name = deliverable.get("name", "Unknown")

            logger.info(f"🎯 [Tavily Deliverable] Starting search for deliverable: {deliverable_name}")
            logger.debug(
                f"📋 [Tavily Deliverable] Deliverable details: {json.dumps(deliverable, ensure_ascii=False, indent=2)}"
            )
            logger.debug(f"🏷️ [Tavily Deliverable] Project type: {project_type}")
            logger.debug(f"⚙️ [Tavily Deliverable] Max results: {max_results}, QC enabled: {enable_qc}")

            # Step 1: 构建精准查询
            logger.debug(f"📝 [Tavily Deliverable] Step 1: Building precise query...")
            if self.query_builder:
                query_start = time.time()
                precise_query = self.query_builder.build_query(deliverable, project_type)
                query_time = time.time() - query_start
                logger.info(f"🔍 [Tavily Deliverable] Precise query built in {query_time:.2f}s: {precise_query}")
            else:
                # Fallback: 使用交付物名称
                precise_query = deliverable.get("name", "")
                logger.warning(
                    f"⚠️ [Tavily Deliverable] Query builder not available, using deliverable name: {precise_query}"
                )

            # Step 2: 执行搜索（获取2倍结果用于质量过滤）
            search_count = max_results * 2 if enable_qc else max_results
            logger.debug(f"🔎 [Tavily Deliverable] Step 2: Executing search (requesting {search_count} results)...")
            search_start = time.time()
            search_results = self.search(
                query=precise_query, max_results=search_count, search_depth="advanced", include_answer=True
            )
            search_time = time.time() - search_start
            logger.info(
                f"✅ [Tavily Deliverable] Search completed in {search_time:.2f}s, success={search_results.get('success', False)}"
            )

            if not search_results.get("success", False):
                logger.error(f"❌ [Tavily Deliverable] Search failed: {search_results.get('error', 'Unknown error')}")
                return search_results

            initial_count = len(search_results.get("results", []))
            logger.debug(f"📊 [Tavily Deliverable] Initial results count: {initial_count}")

            # Step 3: 质量控制
            if enable_qc and self.qc:
                logger.debug(f"🔬 [Tavily Deliverable] Step 3: Running quality control...")
                qc_start = time.time()
                processed_results = self.qc.process_results(
                    search_results.get("results", []), deliverable_context=deliverable
                )
                qc_time = time.time() - qc_start

                # 限制到max_results
                before_limit = len(processed_results)
                processed_results = processed_results[:max_results]
                after_limit = len(processed_results)

                search_results["results"] = processed_results
                search_results["quality_controlled"] = True
                logger.info(
                    f"✅ [Tavily Deliverable] QC completed in {qc_time:.2f}s: {initial_count} → {before_limit} → {after_limit} results"
                )
                logger.debug(
                    f"📉 [Tavily Deliverable] QC pipeline: initial={initial_count}, after_qc={before_limit}, after_limit={after_limit}"
                )
            else:
                search_results["quality_controlled"] = False
                logger.debug(
                    f"⏭️ [Tavily Deliverable] Quality control skipped (enable_qc={enable_qc}, qc_available={self.qc is not None})"
                )

            # Step 4: 添加编号（按质量分数排序）
            logger.debug(f"🔢 [Tavily Deliverable] Step 4: Adding reference numbers...")
            for idx, result in enumerate(search_results.get("results", []), start=1):
                result["reference_number"] = idx
            logger.debug(f"✅ [Tavily Deliverable] Reference numbers added (1-{len(search_results.get('results', []))})")

            end_time = time.time()
            total_time = end_time - start_time
            search_results["execution_time"] = total_time
            search_results["deliverable_name"] = deliverable_name
            search_results["precise_query"] = precise_query

            logger.info(f"🎉 [Tavily Deliverable] Search for deliverable completed in {total_time:.2f}s")
            logger.info(
                f"📊 [Tavily Deliverable] Final results: {len(search_results.get('results', []))} items, QC={search_results.get('quality_controlled', False)}"
            )

            return search_results

        except Exception as e:
            logger.error(f"❌ [Tavily Deliverable] search_for_deliverable failed: {str(e)}", exc_info=True)
            logger.error(f"❌ [Tavily Deliverable] Failed deliverable: {deliverable.get('name', 'Unknown')}")
            logger.error(f"❌ [Tavily Deliverable] Full deliverable data: {json.dumps(deliverable, ensure_ascii=False)}")
            return {
                "success": False,
                "error": str(e),
                "deliverable_name": deliverable.get("name", ""),
                "results": [],
                "execution_time": 0,
            }

    def is_available(self) -> bool:
        """
        检查工具是否可用

        Returns:
            是否可用
        """
        try:
            # 简单测试搜索
            test_response = self.client.search(query="test", max_results=1, search_depth="basic")
            return True
        except Exception as e:
            logger.error(f"Tavily tool availability check failed: {str(e)}")
            return False

    def to_langchain_tool(self):
        """
        将 TavilySearchTool 转换为 LangChain StructuredTool

        Returns:
            StructuredTool instance compatible with bind_tools()
        """
        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain not available, returning self")
            return self

        # 定义输入schema
        class TavilySearchInput(BaseModel):
            query: str = Field(description="搜索查询字符串")

        def tavily_search_func(query: str) -> str:
            """使用Tavily搜索引擎进行实时网络搜索"""
            result = self.search(query)
            if not result.get("success", False):
                return f"搜索失败: {result.get('error', 'Unknown error')}"

            results = result.get("results", [])
            if not results:
                return "未找到相关结果"

            # 格式化输出
            output = f"Tavily搜索结果 (关键词: {query}):\n\n"
            if result.get("answer"):
                output += f"摘要答案: {result['answer']}\n\n"

            for i, item in enumerate(results, 1):
                output += f"{i}. {item.get('title', '无标题')}\n"
                output += f"   内容: {item.get('content', '无内容')[:200]}...\n"
                output += f"   链接: {item.get('url', '无链接')}\n\n"

            return output

        # 🆕 v7.65: 根据role_type提供简化版/完整版描述
        role_type = getattr(self, "_current_role_type", None)

        if role_type in ["V4", "V6"]:  # 研究型角色使用完整描述
            description = """Tavily实时网络搜索 - 获取最新行业信息、设计案例、技术趋势

适用场景:
- 需要2023年后的最新设计趋势、案例
- 国际化项目需要海外案例参考
- 商业空间、零售、餐饮等行业最新动态
- 新兴技术在设计领域的应用

不适用场景:
- 学术论文查询（使用arxiv）
- 纯中文本土案例（使用bocha）
- 内部组织知识（使用ragflow）

查询示例: "2024 commercial space design trends sustainable"""
        else:  # 其他角色使用简化描述
            description = "Tavily实时网络搜索 - 提供最新行业信息、国际设计案例、技术趋势（适合需要2023+数据的场景）"

        tool = StructuredTool(
            name=self.name, description=description, func=tavily_search_func, args_schema=TavilySearchInput
        )

        return tool
