"""
博查搜索工具 (v7.105)

✅ 状态: 已修复并完整集成博查Web Search API

博查是中文AI搜索引擎，专注于中文内容搜索
适用场景：中文项目、国内市场调研、中文案例研究

📊 API配置:
- 域名: https://api.bocha.cn
- 端点: /v1/web-search
- 文档: https://bocha-ai.feishu.cn/wiki/HmtOw1z6vik14Fkdu5uc9VaInBb
- 获取密钥: https://open.bocha.cn

✅ 实现状态:
- ✅ 配置系统完整
- ✅ 工具框架就绪
- ✅ Web Search API 集成完成
- ✅ 响应解析适配博查返回格式

修复记录:
- v7.105 (2025-12-30): 修复域名 api.bochaai.com → api.bocha.cn
- v7.105: 修复端点 /chat/completions → /v1/web-search
- v7.105: 修复请求格式为博查Web Search API标准
- v7.105: 修复响应解析（code: 200 vs 0）
"""

import json
from typing import Any, Dict, Optional

from loguru import logger

from intelligent_project_analyzer.core.types import ToolConfig
from intelligent_project_analyzer.settings import settings

# LangChain Tool integration
try:
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, Field

    LANGCHAIN_AVAILABLE = True
except ImportError:
    logger.warning("LangChain not available, tool wrapping disabled")
    LANGCHAIN_AVAILABLE = False


class BochaSearchTool:
    """
    博查搜索工具

    使用博查AI搜索引擎进行中文内容搜索
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.bocha.cn",
        default_count: int = 5,
        timeout: int = 30,
        config: Optional[ToolConfig] = None,
    ):
        """
        初始化博查搜索工具

        Args:
            api_key: 博查API密钥
            base_url: 博查API地址
            default_count: 默认搜索结果数量
            timeout: 请求超时时间(秒)
            config: 工具配置
        """
        self.api_key = api_key
        self.base_url = base_url
        self.default_count = default_count
        self.timeout = timeout
        self.config = config or ToolConfig(name="bocha_search")
        self.name = self.config.name  # LangChain compatibility
        self.__name__ = self.config.name  # 🔧 修复: 添加 __name__ 属性用于工具绑定

    def search(self, query: str, count: Optional[int] = None) -> Dict[str, Any]:
        """
        执行搜索

        Args:
            query: 搜索关键词
            count: 返回结果数量（可选，默认使用default_count）

        Returns:
            搜索结果字典
        """
        try:
            import time

            import httpx

            start_time = time.time()
            result_count = count or self.default_count
            freshness = getattr(settings.bocha, "freshness", "oneYear")

            logger.info(f"🔍 [Bocha] Starting Chinese search")
            logger.info(f"📝 [Bocha] Query: {query}")
            logger.debug(f"⚙️ [Bocha] Result count: {result_count}, Freshness: {freshness}")

            # 构建请求头
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

            # 🔥 v7.105: 调用博查Web Search API（官方文档）
            search_url = f"{self.base_url}/v1/web-search"
            payload = {"query": query, "freshness": "oneYear", "count": result_count, "summary": True}  # 搜索时间范围  # 显示摘要

            logger.debug(f"🌐 [Bocha] API URL: {search_url}")
            logger.debug(f"📦 [Bocha] Request payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")

            api_start = time.time()
            with httpx.Client(timeout=self.timeout) as client:
                logger.debug(f"🌐 [Bocha] Calling Bocha API...")
                response = client.post(search_url, headers=headers, json=payload)
                api_time = time.time() - api_start

                logger.info(f"✅ [Bocha] API call completed in {api_time:.2f}s, status={response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f"📥 [Bocha] Response code: {data.get('code', 'unknown')}")
                    logger.debug(f"📥 [Bocha] Response log_id: {data.get('log_id', 'unknown')}")

                    # 🔥 v7.105: 解析博查Web Search API响应格式
                    logger.debug(f"⚙️ [Bocha] Parsing response...")
                    parse_start = time.time()
                    results = []

                    # 博查API返回格式: {code: 200, log_id, msg, data: {webPages: {value: [...]}}}
                    # 注意：code是HTTP状态码200，不是0
                    if isinstance(data, dict) and data.get("code") == 200:
                        web_data = data.get("data", {})
                        web_pages = web_data.get("webPages", {})
                        page_values = web_pages.get("value", [])

                        logger.debug(f"📊 [Bocha] Found {len(page_values)} web pages in response")

                        for idx, item in enumerate(page_values[:result_count], 1):
                            results.append(
                                {
                                    "title": item.get("name", ""),
                                    "url": item.get("url", ""),
                                    "snippet": item.get("snippet", ""),
                                    "summary": item.get("summary", ""),  # 完整摘要
                                    "siteName": item.get("siteName", ""),
                                    "datePublished": item.get("datePublished", ""),
                                }
                            )
                            logger.debug(f"📄 [Bocha] Result {idx}: {item.get('name', '')[:50]}...")

                    parse_time = time.time() - parse_start
                    logger.debug(f"⚙️ [Bocha] Parsing took {parse_time:.2f}s")

                    total_time = time.time() - start_time
                    logger.info(f"✅ [Bocha] Search completed in {total_time:.2f}s, found {len(results)} results")

                    return {
                        "success": True,
                        "query": query,
                        "results": results,
                        "count": len(results),
                        "execution_time": total_time,
                    }
                else:
                    error_msg = f"API returned error {response.status_code}"
                    logger.error(f"❌ [Bocha] Search failed: {error_msg}")
                    logger.error(f"❌ [Bocha] Response content: {response.text[:300]}")

                    return {
                        "success": False,
                        "message": f"{error_msg}。请检查API配置。",
                        "query": query,
                        "results": [],
                        "execution_time": time.time() - start_time,
                    }

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code}"
            logger.error(f"❌ [Bocha] Search failed: {error_msg}", exc_info=True)
            logger.error(f"❌ [Bocha] Response: {e.response.text[:200]}")
            logger.error(f"❌ [Bocha] Failed query: {query}")
            return {
                "success": False,
                "message": error_msg,
                "query": query,
                "results": [],
                "execution_time": time.time() - start_time if "start_time" in locals() else 0,
            }
        except httpx.RequestError as e:
            error_msg = f"Network request failed: {str(e)}"
            logger.error(f"❌ [Bocha] Search failed: {error_msg}", exc_info=True)
            logger.error(f"❌ [Bocha] Failed query: {query}")
            return {
                "success": False,
                "message": error_msg,
                "query": query,
                "results": [],
                "execution_time": time.time() - start_time if "start_time" in locals() else 0,
            }
        except Exception as e:
            logger.error(f"❌ [Bocha] Search failed: {str(e)}", exc_info=True)
            logger.error(f"❌ [Bocha] Failed query: {query}")
            return {
                "success": False,
                "message": f"搜索失败: {str(e)}",
                "query": query,
                "results": [],
                "execution_time": time.time() - start_time if "start_time" in locals() else 0,
            }

    def __call__(self, query: str) -> str:
        """
        LangChain工具接口

        Args:
            query: 搜索关键词

        Returns:
            搜索结果（字符串格式）
        """
        result = self.search(query)

        if not result["success"]:
            return f"搜索失败: {result['message']}"

        if not result["results"]:
            return "未找到相关结果"

        # 格式化输出
        output = f"博查搜索结果 (关键词: {query}):\n\n"
        for i, item in enumerate(result["results"], 1):
            output += f"{i}. {item.get('title', '无标题')}\n"
            output += f"   摘要: {item.get('snippet', '无摘要')}\n"
            output += f"   链接: {item.get('url', '无链接')}\n\n"

        return output

    def to_langchain_tool(self):
        """
        将 BochaSearchTool 转换为 LangChain StructuredTool

        Returns:
            StructuredTool instance compatible with bind_tools()
        """
        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain not available, returning self")
            return self

        # 定义输入schema
        class BochaSearchInput(BaseModel):
            query: str = Field(description="中文搜索查询关键词")

        def bocha_search_func(query: str) -> str:
            """使用博查AI搜索引擎进行中文内容搜索"""
            return self.__call__(query)

        tool = StructuredTool(
            name=self.name,
            description="博查AI中文搜索引擎，专注于中文内容搜索，适用于中文项目、国内市场调研、中文案例研究",
            func=bocha_search_func,
            args_schema=BochaSearchInput,
        )

        return tool


def create_bocha_search_tool_from_settings() -> Optional[BochaSearchTool]:
    """
    从全局配置创建博查搜索工具

    Returns:
        BochaSearchTool实例，如果配置不完整则返回None
    """
    if not settings.bocha.enabled:
        logger.info("博查搜索未启用")
        return None

    if not settings.bocha.api_key or settings.bocha.api_key == "your_bocha_api_key_here":
        logger.warning("⚠️ 博查API密钥未配置")
        return None

    logger.info(f"✅ 创建博查搜索工具: base_url={settings.bocha.base_url}, count={settings.bocha.default_count}")

    tool_config = ToolConfig(name="bocha_search")

    return BochaSearchTool(
        api_key=settings.bocha.api_key,
        base_url=settings.bocha.base_url,
        default_count=settings.bocha.default_count,
        timeout=settings.bocha.timeout,
        config=tool_config,
    )
