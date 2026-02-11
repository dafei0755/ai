"""
博查搜索工具 (v7.163)

 状态: 已修复并完整集成博查Web Search API + TikHub社交媒体搜索

博查是中文AI搜索引擎，专注于中文内容搜索
适用场景：中文项目、国内市场调研、中文案例研究

 API配置:
- 博查域名: https://api.bochaai.com (官方最新域名)
- 博查端点: /v1/web-search
- 博查文档: https://open.bochaai.com/
- TikHub域名: https://api.tikhub.io (海外) / https://api.tikhub.dev (中国大陆)
- TikHub文档: https://docs.tikhub.io/

 实现状态:
-  配置系统完整
-  工具框架就绪
-  Web Search API 集成完成
-  响应解析适配博查返回格式
-  质量控制管道集成
-  TikHub社交媒体搜索集成（抖音/小红书/微博/知乎）

修复记录:
- v7.163 (2026-01-09): 新增微博Web搜索、知乎V3文章搜索
- v7.162 (2026-01-09): 集成TikHub社交媒体搜索（抖音/小红书/视频号）
- v7.161 (2026-01-08): 统一域名为官方最新 api.bochaai.com
- v7.155: 集成质量控制管道
- v7.105 (2025-12-30): 修复端点和响应解析
"""

import json
import time
from typing import Any, Dict, List, Optional

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

#  v7.155: 导入质量控制模块（与Tavily/Serper对齐）
try:
    from ..tools.quality_control import SearchQualityControl
    from ..tools.query_builder import DeliverableQueryBuilder
except ImportError:
    logger.warning("️ Quality control modules not available")
    DeliverableQueryBuilder = None
    SearchQualityControl = None

#  v7.164: 导入搜索结果ID生成器
try:
    from ..utils.search_id_generator import add_ids_to_search_results
except ImportError:
    logger.warning("️ v7.164 search_id_generator not available")
    add_ids_to_search_results = None

#  v7.174: 导入搜索结果缓存服务
try:
    from ..services.search_cache import get_search_cache

    SEARCH_CACHE_AVAILABLE = True
except ImportError:
    logger.warning("️ v7.174 search_cache not available")
    get_search_cache = None
    SEARCH_CACHE_AVAILABLE = False

#  v7.162: 导入TikHub SDK（社交媒体搜索）
try:
    from tikhub import Client as TikHubClient

    TIKHUB_AVAILABLE = True
except ImportError:
    logger.info(" TikHub SDK not installed, social media search disabled. Install with: pip install tikhub")
    TikHubClient = None
    TIKHUB_AVAILABLE = False


class BochaSearchTool:
    """
    博查搜索工具 (v7.162: 集成TikHub社交媒体搜索)

    使用博查AI搜索引擎进行中文内容搜索
    可选：启用TikHub搜索抖音/小红书/视频号内容
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.bochaai.com",
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
        self.__name__ = self.config.name  #  修复: 添加 __name__ 属性用于工具绑定

        #  v7.155: 初始化质量控制模块
        self.query_builder = DeliverableQueryBuilder() if DeliverableQueryBuilder else None
        self.qc = SearchQualityControl() if SearchQualityControl else None

        #  v7.162: 初始化TikHub客户端（社交媒体搜索）
        self.tikhub_enabled = False
        self.tikhub_client = None
        self.tikhub_platforms = []
        self.tikhub_count = 5

        if TIKHUB_AVAILABLE and settings.bocha.tikhub_enabled and settings.bocha.tikhub_api_key:
            try:
                self.tikhub_client = TikHubClient(
                    api_key=settings.bocha.tikhub_api_key, base_url=settings.bocha.tikhub_base_url, timeout=timeout
                )
                self.tikhub_platforms = [p.strip() for p in settings.bocha.tikhub_platforms.split(",") if p.strip()]
                self.tikhub_count = settings.bocha.tikhub_count
                self.tikhub_enabled = True
                logger.info(f" [Bocha] TikHub社交媒体搜索已启用, 平台: {self.tikhub_platforms}")
            except Exception as e:
                logger.warning(f"️ [Bocha] TikHub初始化失败: {e}")
                self.tikhub_enabled = False

    def search(self, query: str, count: Optional[int] = None) -> Dict[str, Any]:
        """
        执行搜索 (v7.174: 支持缓存)

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

            #  v7.174: 尝试从缓存获取
            if SEARCH_CACHE_AVAILABLE:
                cache = get_search_cache()
                cached_result = cache.get(query, "bocha", count=result_count)
                if cached_result is not None:
                    logger.info(f" [Bocha] 缓存命中，跳过API调用")
                    cached_result["from_cache"] = True
                    return cached_result

            logger.info(f" [Bocha] Starting Chinese search")
            logger.info(f" [Bocha] Query: {query}")
            logger.debug(f"️ [Bocha] Result count: {result_count}, Freshness: {freshness}")

            # 构建请求头
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

            #  v7.105: 调用博查Web Search API（官方文档）
            search_url = f"{self.base_url}/v1/web-search"
            payload = {"query": query, "freshness": "oneYear", "count": result_count, "summary": True}  # 搜索时间范围  # 显示摘要

            logger.debug(f" [Bocha] API URL: {search_url}")
            logger.debug(f" [Bocha] Request payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")

            api_start = time.time()
            with httpx.Client(timeout=self.timeout) as client:
                logger.debug(f" [Bocha] Calling Bocha API...")
                response = client.post(search_url, headers=headers, json=payload)
                api_time = time.time() - api_start

                logger.info(f" [Bocha] API call completed in {api_time:.2f}s, status={response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f" [Bocha] Response code: {data.get('code', 'unknown')}")
                    logger.debug(f" [Bocha] Response log_id: {data.get('log_id', 'unknown')}")

                    #  v7.105: 解析博查Web Search API响应格式
                    logger.debug(f"️ [Bocha] Parsing response...")
                    parse_start = time.time()
                    results = []

                    # 博查API返回格式: {code: 200, log_id, msg, data: {webPages: {value: [...]}}}
                    # 注意：code是HTTP状态码200，不是0
                    if isinstance(data, dict) and data.get("code") == 200:
                        web_data = data.get("data", {})
                        web_pages = web_data.get("webPages", {})
                        page_values = web_pages.get("value", [])

                        logger.debug(f" [Bocha] Found {len(page_values)} web pages in response")

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
                            logger.debug(f" [Bocha] Result {idx}: {item.get('name', '')[:50]}...")

                    parse_time = time.time() - parse_start
                    logger.debug(f"️ [Bocha] Parsing took {parse_time:.2f}s")

                    total_time = time.time() - start_time
                    logger.info(f" [Bocha] Search completed in {total_time:.2f}s, found {len(results)} results")

                    #  v7.162: 添加TikHub社交媒体搜索结果
                    if self.tikhub_enabled:
                        tikhub_results = self._search_tikhub(query)
                        if tikhub_results:
                            results.extend(tikhub_results)
                            logger.info(f" [Bocha] Added {len(tikhub_results)} TikHub social media results")

                    result = {
                        "success": True,
                        "query": query,
                        "results": results,
                        "count": len(results),
                        "execution_time": total_time,
                        "sources": ["bocha_web"] + (["tikhub"] if self.tikhub_enabled else []),
                    }

                    #  v7.155: 应用质量控制管道（与Tavily/Serper对齐）
                    if self.qc and result["success"] and result["results"]:
                        logger.debug(f" [Bocha] Applying quality control to {len(result['results'])} results")
                        qc_start = time.time()

                        # 处理结果：过滤 → 去重 → 评分 → 排序
                        processed_results = self.qc.process_results(
                            result["results"], deliverable_context=None  # 可在后续版本增强
                        )

                        qc_time = time.time() - qc_start
                        logger.info(
                            f" [Bocha] QC completed in {qc_time:.2f}s: "
                            f"{len(result['results'])} → {len(processed_results)} results"
                        )

                        result["results"] = processed_results
                        result["quality_controlled"] = True
                    else:
                        result["quality_controlled"] = False

                    #  v7.164: 为搜索结果添加唯一ID
                    if add_ids_to_search_results and result["results"]:
                        result["results"] = add_ids_to_search_results(result["results"], source_tool="bocha")

                    #  v7.174: 缓存搜索结果
                    if SEARCH_CACHE_AVAILABLE and result["success"]:
                        cache = get_search_cache()
                        cache.set(query, "bocha", result, count=result_count)
                        logger.debug(f" [Bocha] 结果已缓存")

                    return result
                else:
                    error_msg = f"API returned error {response.status_code}"
                    logger.error(f" [Bocha] Search failed: {error_msg}")
                    logger.error(f" [Bocha] Response content: {response.text[:300]}")

                    return {
                        "success": False,
                        "message": f"{error_msg}。请检查API配置。",
                        "query": query,
                        "results": [],
                        "execution_time": time.time() - start_time,
                    }

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code}"
            logger.error(f" [Bocha] Search failed: {error_msg}", exc_info=True)
            logger.error(f" [Bocha] Response: {e.response.text[:200]}")
            logger.error(f" [Bocha] Failed query: {query}")
            return {
                "success": False,
                "message": error_msg,
                "query": query,
                "results": [],
                "execution_time": time.time() - start_time if "start_time" in locals() else 0,
            }
        except httpx.RequestError as e:
            error_msg = f"Network request failed: {str(e)}"
            logger.error(f" [Bocha] Search failed: {error_msg}", exc_info=True)
            logger.error(f" [Bocha] Failed query: {query}")
            return {
                "success": False,
                "message": error_msg,
                "query": query,
                "results": [],
                "execution_time": time.time() - start_time if "start_time" in locals() else 0,
            }
        except Exception as e:
            logger.error(f" [Bocha] Search failed: {str(e)}", exc_info=True)
            logger.error(f" [Bocha] Failed query: {query}")
            return {
                "success": False,
                "message": f"搜索失败: {str(e)}",
                "query": query,
                "results": [],
                "execution_time": time.time() - start_time if "start_time" in locals() else 0,
            }

    def search_for_deliverable(
        self,
        deliverable: Dict[str, Any],
        project_type: str = "",
        max_results: int = 10,
        enable_qc: bool = True,
    ) -> Dict[str, Any]:
        """
         v7.155: 针对交付物的精准搜索（与Tavily/Serper对齐）

        Pipeline:
        1. 从交付物提取中文关键词构建精准查询
        2. 执行搜索（获取2倍结果用于质量过滤）
        3. 应用质量控制管道
        4. 限制到max_results并添加编号

        Args:
            deliverable: 交付物字典（name, description, format）
            project_type: 项目类型（用于上下文优化）
            max_results: 最大返回结果数
            enable_qc: 是否启用质量控制

        Returns:
            搜索结果字典，包含排序后的高质量结果
        """
        try:
            import time

            start_time = time.time()
            deliverable_name = deliverable.get("name", "Unknown")

            logger.info(f" [Bocha Deliverable] Starting search for: {deliverable_name}")

            # Step 1: 构建精准查询（中文优化）
            if self.query_builder:
                query_start = time.time()
                # 使用中文关键词（不添加英文术语）
                precise_query = self._build_chinese_query(deliverable, project_type)
                query_time = time.time() - query_start
                logger.info(f" [Bocha Deliverable] Query built in {query_time:.2f}s: {precise_query}")
            else:
                precise_query = deliverable.get("name", "")
                logger.warning(f"️ [Bocha Deliverable] Query builder not available, using name")

            # Step 2: 执行搜索（获取2倍结果用于质量过滤）
            search_count = max_results * 2 if enable_qc else max_results
            logger.debug(f" [Bocha Deliverable] Executing search (requesting {search_count} results)")

            search_results = self.search(query=precise_query, count=search_count)

            if not search_results.get("success", False):
                logger.error(f" [Bocha Deliverable] Search failed: {search_results.get('message')}")
                return search_results

            # Step 3: 限制到max_results（QC已在search()中应用）
            processed_results = search_results.get("results", [])[:max_results]
            search_results["results"] = processed_results

            # Step 4: 添加编号
            for idx, result in enumerate(processed_results, start=1):
                result["reference_number"] = idx

            total_time = time.time() - start_time
            search_results["execution_time"] = total_time
            search_results["deliverable_name"] = deliverable_name
            search_results["precise_query"] = precise_query

            logger.info(f" [Bocha Deliverable] Completed in {total_time:.2f}s, {len(processed_results)} results")

            return search_results

        except Exception as e:
            logger.error(f" [Bocha Deliverable] Failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": str(e),
                "deliverable_name": deliverable.get("name", ""),
                "results": [],
                "execution_time": 0,
            }

    def _build_chinese_query(self, deliverable: Dict[str, Any], project_type: str) -> str:
        """构建中文优化的查询（不添加英文术语）"""
        if not self.query_builder:
            return deliverable.get("name", "")

        # 提取中文关键词
        name = deliverable.get("name", "")
        description = deliverable.get("description", "")

        # 使用jieba提取关键词（如果可用）
        try:
            import jieba.analyse

            combined_text = f"{name} {description}"
            keywords = jieba.analyse.extract_tags(combined_text, topK=5, withWeight=False)
            query_parts = keywords
        except:
            query_parts = [name]

        # 添加项目类型（中文）
        if project_type:
            project_type_cn_map = {
                "commercial_space": "商业空间设计",
                "residential": "住宅设计",
                "retail": "零售空间设计",
                "hospitality": "酒店民宿设计",
                "office": "办公空间设计",
            }
            project_type_cn = project_type_cn_map.get(project_type, project_type)
            query_parts.append(project_type_cn)

        return " ".join(query_parts)

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
            output += f"   链接: {item.get('url', '无链接')}\n"
            # 显示社交媒体来源信息
            if item.get("source_type") == "social":
                output += f"   来源: {item.get('platform', '社交媒体')}\n"
            output += "\n"

        return output

    def _search_tikhub(self, query: str) -> List[Dict[str, Any]]:
        """
         v7.163: 搜索 TikHub 社交媒体平台

        支持平台:
        - xiaohongshu: 小红书笔记搜索
        - douyin: 抖音视频搜索
        - weibo: 微博Web搜索
        - zhihu: 知乎文章搜索V3

        Args:
            query: 搜索关键词

        Returns:
            标准化的搜索结果列表
        """
        if not self.tikhub_client:
            return []

        results = []

        for platform in self.tikhub_platforms:
            try:
                platform_results = self._search_tikhub_platform(platform, query)
                results.extend(platform_results)
                logger.info(f" [TikHub/{platform}] Found {len(platform_results)} results")
            except Exception as e:
                logger.warning(f"️ [TikHub/{platform}] Search failed: {e}")
                continue

        return results

    def _search_tikhub_platform(self, platform: str, query: str) -> List[Dict[str, Any]]:
        """
        搜索单个 TikHub 平台

        Args:
            platform: 平台名称 (xiaohongshu, douyin, weibo, zhihu)
            query: 搜索关键词

        Returns:
            标准化的搜索结果列表
        """
        import asyncio

        import httpx

        results = []
        tikhub_base = settings.bocha.tikhub_base_url
        headers = {"Authorization": f"Bearer {settings.bocha.tikhub_api_key}", "Content-Type": "application/json"}

        try:
            if platform == "xiaohongshu":
                # 小红书笔记搜索 - 使用 SDK: XiaohongshuWeb.search_notes
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    response = loop.run_until_complete(
                        self.tikhub_client.XiaohongshuWeb.search_notes(keyword=query, page=1, sort="general")
                    )
                finally:
                    loop.close()

                if response and response.get("data"):
                    # 数据结构: response['data']['data']['items']
                    inner_data = response.get("data", {}).get("data", {})
                    items = inner_data.get("items", [])
                    for item in items[: self.tikhub_count]:
                        normalized = self._normalize_xiaohongshu_result(item)
                        if normalized:
                            results.append(normalized)

            elif platform == "douyin":
                # 抖音视频搜索 - 使用 HTTP: Douyin-Search-API (最新版本)
                # POST /api/v1/douyin/search/fetch_video_search_v1
                tikhub_base = settings.bocha.tikhub_base_url
                url = f"{tikhub_base}/api/v1/douyin/search/fetch_video_search_v1"
                headers = {
                    "Authorization": f"Bearer {settings.bocha.tikhub_api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "keyword": query,
                    "offset": 0,
                    "count": self.tikhub_count,
                    "sort_type": "0",  # 字符串! 0=综合排序
                    "publish_time": "0",  # 字符串! 0=不限时间
                    "filter_duration": "0",  # 字符串! 0=不限时长
                }

                with httpx.Client(timeout=30) as client:
                    response = client.post(url, headers=headers, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("data"):
                            items = data["data"].get("data", []) or data["data"].get("aweme_list", [])
                            for item in items[: self.tikhub_count]:
                                normalized = self._normalize_douyin_result(item)
                                if normalized:
                                    results.append(normalized)
                    else:
                        logger.warning(f"️ [TikHub/douyin] HTTP {response.status_code}")

            elif platform == "wechat_channels":
                # 微信视频号: TikHub API需要额外权限或Cookie，暂不支持
                logger.debug(f"[TikHub] wechat_channels API requires special permissions, skipped")
                pass

            elif platform == "weibo":
                #  v7.163: 微博Web搜索
                # GET /api/v1/weibo/web/fetch_search
                url = f"{tikhub_base}/api/v1/weibo/web/fetch_search"
                params = {"keyword": query, "page": "1"}

                with httpx.Client(timeout=30) as client:
                    response = client.get(url, headers=headers, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("data"):
                            # 微博数据结构: data.data.cards (嵌套结构)
                            inner_data = data["data"].get("data", {})
                            items = inner_data.get("cards", []) if isinstance(inner_data, dict) else []
                            if isinstance(items, list):
                                for item in items[: self.tikhub_count]:
                                    normalized = self._normalize_weibo_result(item)
                                    if normalized:
                                        results.append(normalized)
                    else:
                        logger.warning(f"️ [TikHub/weibo] HTTP {response.status_code}")

            elif platform == "zhihu":
                #  v7.163: 知乎文章搜索V3
                # GET /api/v1/zhihu/web/fetch_article_search_v3
                url = f"{tikhub_base}/api/v1/zhihu/web/fetch_article_search_v3"
                params = {"keyword": query, "page": "1"}

                with httpx.Client(timeout=30) as client:
                    response = client.get(url, headers=headers, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("data"):
                            items = data["data"].get("data", []) or data["data"].get("items", [])
                            if isinstance(items, list):
                                for item in items[: self.tikhub_count]:
                                    normalized = self._normalize_zhihu_result(item)
                                    if normalized:
                                        results.append(normalized)
                    else:
                        logger.warning(f"️ [TikHub/zhihu] HTTP {response.status_code}")

        except Exception as e:
            logger.warning(f"️ [TikHub/{platform}] API call failed: {e}")

        return results

    def _normalize_xiaohongshu_result(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """标准化小红书搜索结果

        数据结构: item = {"model_type": "note", "note": {...}}

        URL格式说明：
        - 旧格式: https://www.xiaohongshu.com/explore/{note_id} (需要登录)
        - 新格式: https://www.xiaohongshu.com/discovery/item/{note_id} (分享链接，免登录)
        """
        try:
            # 从 item['note'] 获取笔记信息
            note = item.get("note", item)
            user = note.get("user", {})

            note_id = note.get("id", "") or note.get("note_id", "")
            title = note.get("title", "") or note.get("display_title", "")
            desc = note.get("desc", "")

            # 如果没有标题，使用描述的前50字符
            display_title = title if title else (desc[:50] if desc else "小红书笔记")

            # 使用分享链接格式，免登录可查看
            # 备选格式: https://xhslink.com/a/{note_id} 或 https://www.xiaohongshu.com/discovery/item/{note_id}
            url = f"https://www.xiaohongshu.com/discovery/item/{note_id}" if note_id else ""

            return {
                "title": f"[小红书] {display_title}",
                "url": url,
                "snippet": desc[:200] if desc else title,
                "summary": desc,
                "siteName": "小红书",
                "author": user.get("nickname", "") or user.get("nick_name", ""),
                "source_type": "social",
                "platform": "xiaohongshu",
                "content_type": note.get("type", "normal"),
                "liked_count": note.get("nice_count", 0) or note.get("liked_count", 0),
            }
        except Exception as e:
            logger.debug(f"Failed to normalize xiaohongshu result: {e}")
            return None

    def _normalize_douyin_result(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """标准化抖音搜索结果"""
        try:
            aweme_info = item.get("aweme_info", item)
            author = aweme_info.get("author", {})

            aweme_id = aweme_info.get("aweme_id", "")
            desc = aweme_info.get("desc", "")

            return {
                "title": f"[抖音] {desc[:50]}" if desc else "[抖音视频]",
                "url": f"https://www.douyin.com/video/{aweme_id}" if aweme_id else "",
                "snippet": desc[:200] if desc else "",
                "summary": desc,
                "siteName": "抖音",
                "author": author.get("nickname", ""),
                "source_type": "social",
                "platform": "douyin",
                "digg_count": aweme_info.get("statistics", {}).get("digg_count", 0),
                "comment_count": aweme_info.get("statistics", {}).get("comment_count", 0),
            }
        except Exception as e:
            logger.debug(f"Failed to normalize douyin result: {e}")
            return None

    def _normalize_wechat_channels_result(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """标准化微信视频号搜索结果"""
        try:
            object_desc = item.get("objectDesc", {})
            media = object_desc.get("media", [{}])[0] if object_desc.get("media") else {}

            feed_id = item.get("id", "")
            desc = object_desc.get("description", "")
            nickname = item.get("nickname", "")

            return {
                "title": f"[视频号] {desc[:50]}" if desc else f"[视频号] {nickname}",
                "url": f"https://channels.weixin.qq.com/platform/post/{feed_id}" if feed_id else "",
                "snippet": desc[:200] if desc else "",
                "summary": desc,
                "siteName": "微信视频号",
                "author": nickname,
                "source_type": "social",
                "platform": "wechat_channels",
            }
        except Exception as e:
            logger.debug(f"Failed to normalize wechat_channels result: {e}")
            return None

    def _normalize_weibo_result(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """ v7.163: 标准化微博搜索结果

        URL格式说明：
        - 旧格式: https://weibo.com/{uid}/{mid} (需要登录)
        - 新格式: https://m.weibo.cn/detail/{mid} (移动端，免登录)

        数据说明：
        - text: 带HTML标签的内容
        - text_raw: 纯文本（有时为空）
        - mid/id/bid: 微博ID
        """
        try:
            # 微博返回格式可能是 card 或直接微博对象
            mblog = item.get("mblog", item)
            user = mblog.get("user", {}) or {}

            # 获取ID，优先使用bid（短链接格式）
            mid = str(mblog.get("bid", "") or mblog.get("mid", "") or mblog.get("id", ""))

            # 获取文本内容，优先text，然后text_raw
            text = mblog.get("text", "") or mblog.get("text_raw", "") or ""

            # 移除HTML标签
            import re

            text_clean = re.sub(r"<[^>]+>", "", text)
            # 移除多余空白
            text_clean = re.sub(r"\s+", " ", text_clean).strip()

            screen_name = user.get("screen_name", "") or user.get("name", "") or ""

            # 使用移动端URL格式，免登录可查看
            url = f"https://m.weibo.cn/detail/{mid}" if mid else ""

            # 生成标题
            if text_clean:
                title = f"[微博] {text_clean[:50]}..." if len(text_clean) > 50 else f"[微博] {text_clean}"
            else:
                title = f"[微博] @{screen_name}" if screen_name else "[微博]"

            return {
                "title": title,
                "url": url,
                "snippet": text_clean[:200] if text_clean else f"来自 @{screen_name} 的微博",
                "summary": text_clean[:500] if text_clean else "",
                "siteName": "微博",
                "author": screen_name,
                "source_type": "social",
                "platform": "weibo",
                "reposts_count": mblog.get("reposts_count", 0),
                "comments_count": mblog.get("comments_count", 0),
                "attitudes_count": mblog.get("attitudes_count", 0),
            }
        except Exception as e:
            logger.debug(f"Failed to normalize weibo result: {e}")
            return None

    def _normalize_zhihu_result(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """ v7.163: 标准化知乎文章搜索结果

        URL格式说明：
        - 专栏文章(article): https://zhuanlan.zhihu.com/p/{id}
        - 问答(answer): https://www.zhihu.com/question/{qid}/answer/{aid}
        - API URL需要转换
        """
        try:
            import re

            # 知乎返回格式可能是 object 或直接文章对象
            obj = item.get("object", item)
            author = obj.get("author", {}) or {}

            article_id = str(obj.get("id", ""))
            title_raw = obj.get("title", "") or ""
            excerpt_raw = obj.get("excerpt", "") or ""
            content_raw = obj.get("content", "") or ""

            # 清理HTML标签（包括<em>高亮标签）
            def clean_html(text):
                if not text:
                    return ""
                text = re.sub(r"<[^>]+>", "", text)
                text = re.sub(r"\s+", " ", text).strip()
                return text

            title = clean_html(title_raw)
            excerpt = clean_html(excerpt_raw)
            content = clean_html(content_raw[:500]) if content_raw else ""

            # 优先使用excerpt，其次content
            text_clean = excerpt if excerpt else content

            author_name = author.get("name", "") or author.get("headline", "") or ""
            url_token = obj.get("url", "") or ""
            obj_type = obj.get("type", "article")
            question = obj.get("question", {}) or {}
            question_id = str(question.get("id", "")) if question else ""
            question_title = clean_html(question.get("title", "")) if question else ""

            # 构建URL - 根据类型
            url = ""
            if obj_type == "article":
                # 专栏文章
                url = f"https://zhuanlan.zhihu.com/p/{article_id}"
            elif obj_type == "answer":
                # 问答
                if question_id:
                    url = f"https://www.zhihu.com/question/{question_id}/answer/{article_id}"
                else:
                    url = f"https://www.zhihu.com/answer/{article_id}"
            elif "api.zhihu.com/articles" in url_token:
                url = f"https://zhuanlan.zhihu.com/p/{article_id}"
            elif "api.zhihu.com/answers" in url_token:
                url = f"https://www.zhihu.com/answer/{article_id}"
            elif url_token.startswith("http") and "api.zhihu.com" not in url_token:
                url = url_token
            elif article_id:
                url = f"https://zhuanlan.zhihu.com/p/{article_id}"

            # 显示标题：优先文章标题，其次问题标题
            display_title = title if title else question_title

            return {
                "title": f"[知乎] {display_title}" if display_title else "[知乎]",
                "url": url,
                "snippet": text_clean[:200] if text_clean else display_title,
                "summary": text_clean[:500] if text_clean else "",
                "siteName": "知乎",
                "author": author_name,
                "source_type": "social",
                "platform": "zhihu",
                "voteup_count": obj.get("voteup_count", 0),
                "comment_count": obj.get("comment_count", 0),
            }
        except Exception as e:
            logger.debug(f"Failed to normalize zhihu result: {e}")
            return None

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
            description="""博查AI中文搜索引擎 - 专注中文本土内容

 核心定位:
- 中文网站深度覆盖（国内主流平台、论坛、博客）
- 中文语义理解优化
- 国内市场专属数据

 适用场景:
- 中文本土案例（国内品牌、中国设计师作品）
- 国内市场调研（政策、报告、行业动态）
- 中文关键词查询
- 国内设计趋势

️ 不适用场景:
- 英文查询（使用Tavily）
- 国际案例（使用Tavily）
- 海外市场分析（使用Tavily）
- 学术论文（使用arxiv）

查询示例: "中国商业空间设计趋势 2024", "国内零售品牌店铺设计"
""",
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
        logger.warning("️ 博查API密钥未配置")
        return None

    logger.info(f" 创建博查搜索工具: base_url={settings.bocha.base_url}, count={settings.bocha.default_count}")

    #  v7.162: TikHub 配置会在 BochaSearchTool.__init__ 中自动从 settings 读取

    tool_config = ToolConfig(name="bocha_search")

    return BochaSearchTool(
        api_key=settings.bocha.api_key,
        base_url=settings.bocha.base_url,
        default_count=settings.bocha.default_count,
        timeout=settings.bocha.timeout,
        config=tool_config,
    )
