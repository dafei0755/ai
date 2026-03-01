"""
Serper搜索工具 (v7.130+)

基于Google搜索的API服务，提供稳定的实时网络搜索功能。
相比Tavily，Serper基于Google搜索引擎，质量更稳定。

 API配置:
- 域名: https://google.serper.dev
- 文档: https://serper.dev/api-docs
- 获取密钥: https://serper.dev/
- 免费额度: 2500次/月
- 付费价格: $0.5/1000次

适用场景：
- 实时网络搜索（国际内容）
- 最新行业信息、设计案例、技术趋势
- 需要高质量稳定搜索结果的场景
"""

import json
import time
from typing import Any, Dict, Optional

from loguru import logger

try:
    import httpx
except ImportError:
    logger.warning("httpx library not installed. Please install with: pip install httpx")
    httpx = None

from ..core.types import ToolConfig

# LangChain Tool integration
try:
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, Field

    LANGCHAIN_AVAILABLE = True
except ImportError:
    logger.warning("LangChain not available, tool wrapping disabled")
    LANGCHAIN_AVAILABLE = False

#  v7.64: 导入精准搜索和质量控制模块
try:
    from .quality_control import SearchQualityControl
    from .query_builder import DeliverableQueryBuilder
except ImportError:
    logger.warning("️ v7.64 modules not available. search_for_deliverable() will use fallback mode.")
    DeliverableQueryBuilder = None
    SearchQualityControl = None

#  v7.164: 导入搜索结果ID生成器
try:
    from ..utils.search_id_generator import add_ids_to_search_results
except ImportError:
    logger.warning("️ v7.164 search_id_generator not available")
    add_ids_to_search_results = None


class SerperSearchTool:
    """Serper搜索工具类 - 基于Google搜索"""

    def __init__(self, api_key: str, config: Optional[ToolConfig] = None):
        """
        初始化Serper搜索工具

        Args:
            api_key: Serper API密钥
            config: 工具配置
        """
        if httpx is None:
            raise ImportError("httpx library not installed. Please install with: pip install httpx")

        self.api_key = api_key
        self.base_url = "https://google.serper.dev"
        self.config = config or ToolConfig(name="serper_search")
        self.name = self.config.name  # LangChain compatibility

        # 默认搜索参数
        self.default_params = {
            "num": 10,  # 返回结果数量
            "gl": "us",  # 地理位置 (us=美国, cn=中国)
            "hl": "en",  # 语言 (en=英语, zh-cn=简体中文)
            "type": "search",  # 搜索类型: search, images, news
        }

        #  v7.64: 初始化精准搜索和质量控制模块
        self.query_builder = DeliverableQueryBuilder() if DeliverableQueryBuilder else None
        self.qc = SearchQualityControl() if SearchQualityControl else None

    def search(
        self,
        query: str,
        num_results: Optional[int] = None,
        gl: str = "us",
        hl: str = "en",
        search_type: str = "search",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        执行搜索查询

        Args:
            query: 搜索查询字符串
            num_results: 最大结果数量
            gl: 地理位置代码 (us, cn, uk等)
            hl: 语言代码 (en, zh-cn等)
            search_type: 搜索类型 (search, images, news)
            **kwargs: 其他搜索参数

        Returns:
            搜索结果字典
            {
                "success": True,
                "query": "...",
                "answer": "...",  # 知识图谱摘要(如有)
                "results": [
                    {
                        "title": "...",
                        "url": "...",
                        "content": "...",
                        "snippet": "...",
                        "position": 1,
                        "score": 0.95
                    }
                ],
                "execution_time": 0.5
            }
        """
        try:
            start_time = time.time()

            # 准备搜索参数
            payload = {
                "q": query,
                "num": num_results or self.default_params["num"],
                "gl": gl,
                "hl": hl,
                "type": search_type,
            }

            # 添加其他可选参数
            if "autocorrect" in kwargs:
                payload["autocorrect"] = kwargs["autocorrect"]
            if "page" in kwargs:
                payload["page"] = kwargs["page"]

            logger.info(" [Serper] Starting Google search")
            logger.info(f" [Serper] Query: {query}")
            logger.debug(f"️ [Serper] Search params: {json.dumps(payload, ensure_ascii=False, indent=2)}")

            # 执行搜索
            logger.debug(" [Serper] Calling Serper API...")
            api_start = time.time()
            response = self._make_api_request("/search", payload)
            api_time = time.time() - api_start

            logger.info(f" [Serper] API call completed in {api_time:.2f}s")
            logger.debug(f" [Serper] Raw response keys: {list(response.keys())}")

            # 处理响应
            logger.debug("️ [Serper] Processing response...")
            process_start = time.time()
            processed_response = self._process_search_response(response, time.time() - start_time, query)
            process_time = time.time() - process_start

            logger.debug(f"️ [Serper] Response processing took {process_time:.2f}s")
            logger.info(
                f" [Serper] Search completed in {processed_response['execution_time']:.2f}s, found {len(processed_response.get('results', []))} results"
            )

            return processed_response

        except Exception as e:
            logger.error(f" [Serper] Search failed: {str(e)}", exc_info=True)
            logger.error(f" [Serper] Failed query: {query}")
            logger.error(
                f" [Serper] Failed params: {json.dumps(payload if 'payload' in locals() else {}, ensure_ascii=False)}"
            )
            return {"success": False, "error": str(e), "query": query, "results": [], "execution_time": 0}

    def search_for_deliverable(
        self,
        deliverable: Dict[str, Any],
        project_type: str = "",
        max_results: int = 10,
        enable_qc: bool = True,
        gl: str = "us",
        hl: str = "en",
    ) -> Dict[str, Any]:
        """
         v7.64: 针对交付物的精准搜索

        核心改进：
        1. 从交付物的name + description提取关键词构建精准查询
        2. 应用质量控制管道（过滤 → 去重 → 评分 → 排序）
        3. 按质量分数编号排序

        Args:
            deliverable: 交付物字典，包含name, description, format等
            project_type: 项目类型（用于上下文优化）
            max_results: 最大返回结果数
            enable_qc: 是否启用质量控制
            gl: 地理位置代码
            hl: 语言代码

        Returns:
            搜索结果字典，包含排序后的高质量结果
        """
        try:
            start_time = time.time()
            deliverable_name = deliverable.get("name", "Unknown")

            logger.info(f" [Serper Deliverable] Starting search for deliverable: {deliverable_name}")
            logger.debug(
                f" [Serper Deliverable] Deliverable details: {json.dumps(deliverable, ensure_ascii=False, indent=2)}"
            )
            logger.debug(f"️ [Serper Deliverable] Project type: {project_type}")
            logger.debug(f"️ [Serper Deliverable] Max results: {max_results}, QC enabled: {enable_qc}")

            # Step 1: 构建精准查询
            logger.debug(" [Serper Deliverable] Step 1: Building precise query...")
            if self.query_builder:
                query_start = time.time()
                precise_query = self.query_builder.build_query(deliverable, project_type)
                query_time = time.time() - query_start
                logger.info(f" [Serper Deliverable] Precise query built in {query_time:.2f}s: {precise_query}")
            else:
                # Fallback: 使用交付物名称
                precise_query = deliverable.get("name", "")
                logger.warning(
                    f"️ [Serper Deliverable] Query builder not available, using deliverable name: {precise_query}"
                )

            # Step 2: 执行搜索（获取2倍结果用于质量过滤）
            search_count = max_results * 2 if enable_qc else max_results
            logger.debug(f" [Serper Deliverable] Step 2: Executing search (requesting {search_count} results)...")
            search_start = time.time()
            search_results = self.search(query=precise_query, num_results=search_count, gl=gl, hl=hl)
            search_time = time.time() - search_start
            logger.info(
                f" [Serper Deliverable] Search completed in {search_time:.2f}s, success={search_results.get('success', False)}"
            )

            if not search_results.get("success", False):
                logger.error(f" [Serper Deliverable] Search failed: {search_results.get('error', 'Unknown error')}")
                return search_results

            initial_count = len(search_results.get("results", []))
            logger.debug(f" [Serper Deliverable] Initial results count: {initial_count}")

            # Step 3: 质量控制
            if enable_qc and self.qc:
                logger.debug(" [Serper Deliverable] Step 3: Running quality control...")
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
                    f" [Serper Deliverable] QC completed in {qc_time:.2f}s: {initial_count} → {before_limit} → {after_limit} results"
                )
            else:
                search_results["quality_controlled"] = False
                logger.debug(
                    f"️ [Serper Deliverable] Quality control skipped (enable_qc={enable_qc}, qc_available={self.qc is not None})"
                )

            # Step 4: 添加编号（按质量分数排序）
            logger.debug(" [Serper Deliverable] Step 4: Adding reference numbers...")
            for idx, result in enumerate(search_results.get("results", []), start=1):
                result["reference_number"] = idx

            end_time = time.time()
            total_time = end_time - start_time
            search_results["execution_time"] = total_time
            search_results["deliverable_name"] = deliverable_name
            search_results["precise_query"] = precise_query

            logger.info(f" [Serper Deliverable] Search for deliverable completed in {total_time:.2f}s")
            logger.info(
                f" [Serper Deliverable] Final results: {len(search_results.get('results', []))} items, QC={search_results.get('quality_controlled', False)}"
            )

            return search_results

        except Exception as e:
            logger.error(f" [Serper Deliverable] search_for_deliverable failed: {str(e)}", exc_info=True)
            logger.error(f" [Serper Deliverable] Failed deliverable: {deliverable.get('name', 'Unknown')}")
            return {
                "success": False,
                "error": str(e),
                "deliverable_name": deliverable.get("name", ""),
                "results": [],
                "execution_time": 0,
            }

    def _make_api_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Serper API请求

        Args:
            endpoint: API端点路径
            payload: 请求数据

        Returns:
            API响应

        Raises:
            Exception: API请求失败
        """
        url = f"{self.base_url}{endpoint}"
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f" [Serper] HTTP error {e.response.status_code}: {e.response.text[:200]}")
            raise Exception(f"Serper API HTTP error {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f" [Serper] Request error: {str(e)}")
            raise Exception(f"Serper API request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f" [Serper] JSON decode error: {str(e)}")
            raise Exception("Invalid JSON response from Serper API")

    def _process_search_response(self, response: Dict[str, Any], execution_time: float, query: str) -> Dict[str, Any]:
        """
        处理搜索响应，标准化格式

        Args:
            response: 原始API响应
            execution_time: 执行时间
            query: 查询字符串

        Returns:
            处理后的响应
        """
        processed = {
            "success": True,
            "query": query,
            "answer": "",  # 知识图谱摘要
            "results": [],
            "execution_time": execution_time,
            "total_results": 0,
        }

        # 提取知识图谱答案（如有）
        if "knowledgeGraph" in response:
            kg = response["knowledgeGraph"]
            processed["answer"] = kg.get("description", "")

        # 提取答案框（如有）
        if "answerBox" in response:
            answer_box = response["answerBox"]
            if "answer" in answer_box:
                processed["answer"] = answer_box["answer"]
            elif "snippet" in answer_box:
                processed["answer"] = answer_box["snippet"]

        # 处理有机搜索结果
        organic_results = response.get("organic", [])
        processed["total_results"] = len(organic_results)

        for idx, result in enumerate(organic_results, start=1):
            processed_result = {
                "title": result.get("title", ""),
                "url": result.get("link", ""),
                "content": result.get("snippet", ""),
                "snippet": result.get("snippet", ""),
                "position": result.get("position", idx),
                "score": 1.0 - (idx * 0.05),  # 位置权重分数
                "published_date": result.get("date", ""),
            }
            processed["results"].append(processed_result)

        #  v7.164: 为搜索结果添加唯一ID
        if add_ids_to_search_results and processed["results"]:
            processed["results"] = add_ids_to_search_results(processed["results"], source_tool="serper")

        return processed

    def is_available(self) -> bool:
        """
        检查工具是否可用

        Returns:
            是否可用
        """
        try:
            # 简单测试搜索
            test_response = self.search(query="test", num_results=1)
            return test_response.get("success", False)
        except Exception as e:
            logger.error(f"Serper tool availability check failed: {str(e)}")
            return False

    def to_langchain_tool(self):
        """
        将 SerperSearchTool 转换为 LangChain StructuredTool

        Returns:
            StructuredTool instance compatible with bind_tools()
        """
        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain not available, returning self")
            return self

        # 定义输入schema
        class SerperSearchInput(BaseModel):
            query: str = Field(description="搜索查询字符串")

        def serper_search_func(query: str) -> str:
            """使用Serper (Google搜索) 进行实时网络搜索"""
            result = self.search(query)
            if not result.get("success", False):
                return f"搜索失败: {result.get('error', 'Unknown error')}"

            results = result.get("results", [])
            if not results:
                return "未找到相关结果"

            # 格式化输出
            output = f"Serper搜索结果 (基于Google, 关键词: {query}):\n\n"
            if result.get("answer"):
                output += f"摘要答案: {result['answer']}\n\n"

            for i, item in enumerate(results, 1):
                output += f"{i}. {item.get('title', '无标题')}\n"
                output += f"   内容: {item.get('content', '无内容')[:200]}...\n"
                output += f"   链接: {item.get('url', '无链接')}\n\n"

            return output

        # 根据role_type提供简化版/完整版描述
        role_type = getattr(self, "_current_role_type", None)

        if role_type in ["V4", "V6"]:  # 研究型角色使用完整描述
            description = """Serper实时网络搜索 (基于Google) - 获取最新行业信息、设计案例、技术趋势

适用场景:
- 需要2023年后的最新设计趋势、案例
- 国际化项目需要海外案例参考
- 商业空间、零售、餐饮等行业最新动态
- 新兴技术在设计领域的应用
- 需要高质量稳定搜索结果

不适用场景:
- 学术论文查询（使用arxiv）
- 纯中文本土案例（使用bocha）
- 内部组织知识（使用milvus）

查询示例: "2024 commercial space design trends sustainable"
"""
        else:  # 其他角色使用简化描述
            description = "Serper实时网络搜索 (基于Google) - 提供最新行业信息、国际设计案例、技术趋势（高质量稳定）"

        tool = StructuredTool(
            name=self.name, description=description, func=serper_search_func, args_schema=SerperSearchInput
        )

        return tool
