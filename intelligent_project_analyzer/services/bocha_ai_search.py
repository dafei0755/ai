"""
博查 AI Search 服务 (v7.160, v7.171: TikHub社交媒体集成, v7.173: Arxiv学术搜索集成, v7.275: OpenAI推理)

基于博查 AI Search API 的高质量搜索服务，支持：
- AI Search API（LLM优化的结构化回答）
- 图片搜索
- 流式输出
- 黑白名单过滤
- OpenAI 推理增强（v7.275 切换自 DeepSeek-R1）
-  v7.171: TikHub社交媒体搜索（小红书/抖音/微博/知乎）
-  v7.173: Arxiv学术论文搜索集成

API文档: https://open.bochaai.com/
TikHub文档: https://docs.tikhub.io/
Arxiv API: https://arxiv.org/help/api
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from loguru import logger

from intelligent_project_analyzer.settings import settings

#  v7.171: 导入TikHub SDK
try:
    from tikhub import Client as TikHubClient

    TIKHUB_AVAILABLE = True
except ImportError:
    logger.info(" TikHub SDK not installed, social media search disabled. Install with: pip install tikhub")
    TikHubClient = None
    TIKHUB_AVAILABLE = False

#  v7.173: 导入Arxiv学术搜索工具
try:
    from intelligent_project_analyzer.tools.arxiv_search import ArxivSearchTool

    ARXIV_AVAILABLE = True
except ImportError:
    logger.info(" Arxiv library not installed, academic search disabled. Install with: pip install arxiv")
    ArxivSearchTool = None
    ARXIV_AVAILABLE = False

#  v7.167: 导入搜索结果ID生成器
try:
    from intelligent_project_analyzer.utils.search_id_generator import generate_stable_search_id
except ImportError:
    logger.warning("️ v7.167 search_id_generator not available")
    generate_stable_search_id = None

#  v7.172: 导入轻量图片过滤服务
try:
    from intelligent_project_analyzer.services.lightweight_image_filter import filter_search_images

    IMAGE_FILTER_AVAILABLE = True
except ImportError:
    logger.warning("️ v7.172 lightweight_image_filter not available")
    filter_search_images = None
    IMAGE_FILTER_AVAILABLE = False
    logger.warning("️ v7.167 search_id_generator not available")
    generate_stable_search_id = None


@dataclass
class SourceCard:
    """搜索来源卡片"""

    title: str
    url: str
    site_name: str
    site_icon: str
    snippet: str
    summary: str = ""
    date_published: str = ""
    reference_number: int = 0
    is_whitelisted: bool = False
    quality_score: float = 0.0
    id: str = ""  #  v7.167: 唯一标识符，格式: "{source}_{hash}"


@dataclass
class ImageResult:
    """图片搜索结果"""

    url: str
    thumbnail_url: str
    title: str
    source_url: str
    width: int = 0
    height: int = 0


@dataclass
class AISearchResult:
    """AI搜索结果"""

    query: str
    sources: List[SourceCard] = field(default_factory=list)
    images: List[ImageResult] = field(default_factory=list)
    ai_summary: str = ""
    reasoning_content: str = ""  # 推理过程（保留兼容性）
    execution_time: float = 0.0
    total_matches: int = 0


class BochaAISearchService:
    """
    博查 AI Search 服务

    集成功能：
    1. AI Search API - 获取LLM优化的结构化回答
    2. Web Search API - 获取网页搜索结果
    3. Image Search - 获取图片结果
    4. 黑白名单过滤 - 连通管理后台配置
    5. OpenAI 推理 - 结构化深度分析（v7.275）
    """

    #  使用官方最新API域名
    BASE_URL = "https://api.bochaai.com"

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 60,
        enable_filters: bool = True,
    ):
        """
        初始化博查AI搜索服务

        Args:
            api_key: 博查API密钥，默认从环境变量读取
            timeout: 请求超时时间
            enable_filters: 是否启用黑白名单过滤
        """
        #  v7.235: 修复 settings 属性未初始化的 bug
        self.settings = settings.bocha
        self.api_key = api_key or getattr(self.settings, "api_key", "")
        self.timeout = timeout
        self.enable_filters = enable_filters

        # 加载黑白名单管理器
        self.filter_manager = None
        if enable_filters:
            try:
                from intelligent_project_analyzer.services.search_filter_manager import get_filter_manager

                self.filter_manager = get_filter_manager()
                logger.info(" 搜索黑白名单过滤器已加载")
            except Exception as e:
                logger.warning(f"️ 黑白名单过滤器加载失败: {e}")

        # 质量控制模块
        self.qc = None
        try:
            from intelligent_project_analyzer.tools.quality_control import SearchQualityControl

            self.qc = SearchQualityControl(enable_filters=enable_filters)
        except Exception as e:
            logger.warning(f"️ 质量控制模块加载失败: {e}")

        #  v7.171: 初始化TikHub客户端（社交媒体搜索）
        self.tikhub_enabled = False
        self.tikhub_client = None
        self.tikhub_platforms = []
        self.tikhub_count = 5

        if (
            TIKHUB_AVAILABLE
            and getattr(settings.bocha, "tikhub_enabled", False)
            and getattr(settings.bocha, "tikhub_api_key", "")
        ):
            try:
                self.tikhub_client = TikHubClient(
                    api_key=settings.bocha.tikhub_api_key, base_url=settings.bocha.tikhub_base_url, timeout=timeout
                )
                self.tikhub_platforms = [p.strip() for p in settings.bocha.tikhub_platforms.split(",") if p.strip()]
                self.tikhub_count = getattr(settings.bocha, "tikhub_count", 5)
                self.tikhub_enabled = True
                logger.info(f" [BochaAI] TikHub社交媒体搜索已启用, 平台: {self.tikhub_platforms}")
            except Exception as e:
                logger.warning(f"️ [BochaAI] TikHub初始化失败: {e}")

        #  v7.173: 初始化Arxiv学术搜索工具
        self.arxiv_tool = None
        self.arxiv_enabled = False
        if ARXIV_AVAILABLE and getattr(settings, "arxiv", None) and getattr(settings.arxiv, "enabled", True):
            try:
                self.arxiv_tool = ArxivSearchTool()
                self.arxiv_enabled = True
                logger.info(" [BochaAI] Arxiv学术搜索已启用")
            except Exception as e:
                logger.warning(f"️ [BochaAI] Arxiv初始化失败: {e}")

    async def search(
        self,
        query: str,
        count: int = 10,
        freshness: str = "oneYear",
        include_images: bool = False,  # v7.234: 默认禁用图片搜索
        image_count: int = 8,
    ) -> AISearchResult:
        """
        执行AI搜索（非流式）

        Args:
            query: 搜索查询
            count: 网页结果数量
            freshness: 时效性（oneDay, oneWeek, oneMonth, oneYear）
            include_images: 是否包含图片搜索
            image_count: 图片结果数量

        Returns:
            AISearchResult 搜索结果
        """
        start_time = time.time()
        result = AISearchResult(query=query)

        #  v7.234: 强制禁用图片搜索（全局策略）
        # 无论调用者传入什么值，都强制禁用图片搜索
        if not self.settings.image_search_enabled:
            include_images = False

        try:
            #  v7.176: 优化图片搜索策略
            # 博查独立图片搜索端点 (/v1/image-search) 返回 404
            # 改为优先从 Web Search 响应的 images 字段提取图片

            # 执行网页搜索
            web_data = await self._web_search(query, count, freshness)

            if web_data:
                result.sources = self._parse_web_results(web_data)
                result.total_matches = web_data.get("webPages", {}).get("totalEstimatedMatches", 0)
                result.ai_summary = self._extract_ai_summary(web_data)

                # v7.233: 图片搜索逻辑简化
                # 只有明确启用图片搜索时才执行，Ucppt模式默认禁用
                if include_images:
                    result.images = self._extract_images_from_web_search(web_data, max_count=image_count)
                    if result.images:
                        logger.info(f" 从 Web Search 提取了 {len(result.images)} 张图片")
                    elif self.settings.image_search_enabled:  # 只有设置启用时才尝试独立端点
                        # 备选：尝试独立图片搜索端点
                        logger.info(" Web Search 无图片，尝试独立图片搜索端点...")
                        image_data = await self._image_search(query, image_count)
                        if image_data:
                            result.images = self._parse_image_results(image_data)
            else:
                logger.error(" 网页搜索失败")

            #  v7.172: 应用轻量图片过滤（尺寸、URL模式、域名质量、相关性）
            if result.images and IMAGE_FILTER_AVAILABLE:
                original_count = len(result.images)
                result.images = filter_search_images(images=result.images, query=query, max_results=image_count)
                if len(result.images) < original_count:
                    logger.info(f" 图片智能过滤: {original_count} -> {len(result.images)}")

            #  v7.171: 添加TikHub社交媒体搜索结果
            if self.tikhub_enabled:
                try:
                    tikhub_sources = await self._search_tikhub(query)
                    if tikhub_sources:
                        result.sources.extend(tikhub_sources)
                        logger.info(f" [TikHub] 添加了 {len(tikhub_sources)} 个社交媒体来源")
                except Exception as e:
                    logger.warning(f"️ [TikHub] 社交媒体搜索失败: {e}")

            result.execution_time = time.time() - start_time
            logger.info(
                f" AI搜索完成 | query={query[:30]}... | "
                f"sources={len(result.sources)} | images={len(result.images)} | "
                f"time={result.execution_time:.2f}s"
            )

        except Exception as e:
            logger.error(f" AI搜索失败: {e}")
            result.execution_time = time.time() - start_time

        return result

    async def search_stream(
        self,
        query: str,
        count: int = 10,
        freshness: str = "oneYear",
        include_images: bool = False,  # v7.234: 默认禁用图片搜索
        image_count: int = 8,
        use_deepseek_r1: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式AI搜索

        事件类型：
        - thinking: 搜索状态更新
        - sources: 来源卡片列表
        - images: 图片结果列表
        - reasoning: DeepSeek-R1推理过程（流式）
        - content: 最终回答内容（流式）
        - done: 搜索完成
        - error: 错误信息

        Args:
            query: 搜索查询
            count: 网页结果数量
            freshness: 时效性
            include_images: 是否包含图片
            image_count: 图片数量
            use_deepseek_r1: 是否使用DeepSeek-R1推理

        Yields:
            事件字典 {type, data}
        """
        start_time = time.time()

        try:
            # 阶段1: 开始搜索
            yield {"type": "thinking", "data": {"status": "searching", "message": "正在搜索相关资料..."}}

            # 阶段2: 执行搜索
            search_result = await self.search(
                query=query,
                count=count,
                freshness=freshness,
                include_images=include_images,
                image_count=image_count,
            )

            # 阶段3: 返回来源
            if search_result.sources:
                yield {
                    "type": "thinking",
                    "data": {"status": "sources_found", "message": f"找到 {len(search_result.sources)} 个相关来源"},
                }
                yield {"type": "sources", "data": [self._source_to_dict(s) for s in search_result.sources]}

            # 阶段4: 返回图片
            if search_result.images:
                yield {"type": "images", "data": [self._image_to_dict(img) for img in search_result.images]}

            # 阶段5: DeepSeek-R1 推理生成
            if use_deepseek_r1 and search_result.sources:
                yield {"type": "thinking", "data": {"status": "reasoning", "message": "DeepSeek-R1 正在深度分析..."}}

                async for event in self._generate_with_deepseek_r1(query, search_result):
                    yield event
            else:
                # 直接返回博查AI摘要
                if search_result.ai_summary:
                    yield {"type": "content", "data": search_result.ai_summary}

            # 阶段6: 完成
            execution_time = time.time() - start_time
            yield {
                "type": "done",
                "data": {
                    "execution_time": execution_time,
                    "total_sources": len(search_result.sources),
                    "total_images": len(search_result.images),
                },
            }

        except Exception as e:
            logger.error(f" 流式搜索失败: {e}")
            yield {"type": "error", "data": {"message": str(e)}}

    async def _web_search(
        self,
        query: str,
        count: int,
        freshness: str,
    ) -> Dict[str, Any]:
        """执行网页搜索"""
        url = f"{self.BASE_URL}/v1/web-search"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "query": query,
            "count": count,
            "freshness": freshness,
            "summary": True,  # 请求AI摘要
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 200:
                return data.get("data", {})
            else:
                raise Exception(f"API返回错误: {data.get('msg', 'Unknown error')}")

    async def _image_search(
        self,
        query: str,
        count: int,
    ) -> Dict[str, Any]:
        """
        执行图片搜索

        优先尝试独立的 /v1/image-search 端点，
        如果失败（404或其他错误），则返回空结果。
        图片也可能从 Web Search 响应的 images 字段中提取。
        """
        url = f"{self.BASE_URL}/v1/image-search"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "query": query,
            "count": count,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)

                # 如果端点不存在，静默降级
                if response.status_code == 404:
                    logger.info(" 图片搜索端点不可用 (404)，将从Web Search提取图片")
                    return {}

                response.raise_for_status()
                data = response.json()

                if data.get("code") == 200:
                    logger.info(" 图片搜索成功")
                    return data.get("data", {})
                else:
                    logger.warning(f"图片搜索API返回: {data.get('msg', 'Unknown')}")
                    return {}
        except httpx.HTTPStatusError as e:
            logger.warning(f"图片搜索HTTP错误: {e.response.status_code}")
            return {}
        except Exception as e:
            logger.warning(f"图片搜索失败: {e}")
            return {}

    def _parse_web_results(self, data: Dict[str, Any]) -> List[SourceCard]:
        """解析网页搜索结果"""
        sources = []
        web_pages = data.get("webPages", {}).get("value", [])

        blacklisted_count = 0
        whitelisted_count = 0

        for idx, item in enumerate(web_pages, 1):
            url = item.get("url", "")

            # 黑名单过滤
            if self.filter_manager and self.filter_manager.is_blacklisted(url):
                logger.info(f" 黑名单过滤: {url}")
                blacklisted_count += 1
                continue

            # 检查白名单状态
            is_whitelisted = False
            if self.filter_manager:
                is_whitelisted = self.filter_manager.is_whitelisted(url)
                if is_whitelisted:
                    whitelisted_count += 1

            #  v7.167: 生成唯一ID
            source_id = ""
            if generate_stable_search_id:
                source_id = generate_stable_search_id("bocha", url, item.get("name", ""))

            source = SourceCard(
                title=item.get("name", ""),
                url=url,
                site_name=item.get("siteName", ""),
                site_icon=item.get("siteIcon", ""),
                snippet=item.get("snippet", ""),
                summary=item.get("summary", ""),
                date_published=item.get("datePublished", ""),
                reference_number=idx,
                is_whitelisted=is_whitelisted,
                id=source_id,
            )
            sources.append(source)

        #  添加过滤统计日志
        if blacklisted_count > 0 or whitelisted_count > 0:
            logger.info(f" 黑白名单过滤统计: 黑名单过滤={blacklisted_count}, 白名单命中={whitelisted_count}, 保留来源={len(sources)}")

        #  v7.162: 增强质量排序 - 多维度评分
        def calculate_quality_score(source: SourceCard) -> tuple:
            """
            计算来源质量分数
            返回元组用于排序（值越小排越前）
            """
            score = 0
            url_lower = source.url.lower()

            # 0.  ucppt.com 官网最高优先级（置顶）
            if "ucppt.com" in url_lower:
                score -= 10000

            # 1. 白名单优先（权重最高）
            if source.is_whitelisted:
                score -= 1000

            # 2. 内容丰富度（有摘要的优先）
            if source.snippet and len(source.snippet) > 100:
                score -= 50
            if source.summary and len(source.summary) > 50:
                score -= 30

            # 3. 权威域名加分
            authority_domains = [
                ".edu",
                ".gov",
                ".org",
                ".ac.",  # 教育/政府/组织
                "wikipedia",
                "zhihu.com",
                "baidu.com",
                "csdn.net",  # 知名平台
                "github.com",
                "stackoverflow.com",
                "microsoft.com",
                "arxiv.org",
                "nature.com",
                "science.org",  # 学术
            ]
            for domain in authority_domains:
                if domain in url_lower:
                    score -= 100
                    break

            # 4. 时效性（有日期的优先）
            if source.date_published:
                score -= 20

            # 5. 原始排名（保持搜索引擎的相关性判断）
            score += source.reference_number * 2

            return (score, source.reference_number)

        sources.sort(key=calculate_quality_score)

        # 重新编号
        for idx, source in enumerate(sources, 1):
            source.reference_number = idx

        return sources

    def _parse_image_results(self, data: Dict[str, Any]) -> List[ImageResult]:
        """
        解析图片搜索结果

        支持多种数据源：
        1. 独立图片搜索API返回的数据
        2. Web Search 响应中的 images 字段（dict 或 list）

         v7.176: 优化字段解析，处理 name=None 的情况
        """
        images = []

        #  处理 images 字段（可能是 dict 或 list）
        image_values = []

        # 情况1: data 本身包含 images 字段
        images_field = data.get("images")
        if images_field:
            if isinstance(images_field, dict):
                # images: { value: [...] }
                image_values = images_field.get("value", [])
            elif isinstance(images_field, list):
                # images: [...]
                image_values = images_field

        # 情况2: data 本身就是图片列表
        if not image_values and isinstance(data, list):
            image_values = data

        # 情况3: data.value 直接是列表（独立图片搜索API）
        if not image_values and isinstance(data.get("value"), list):
            image_values = data.get("value", [])

        for item in image_values:
            if not isinstance(item, dict):
                continue

            # 获取图片 URL（兼容多种字段名）
            url = item.get("contentUrl") or item.get("url") or ""
            if not url:
                continue  # 跳过无效图片

            # 获取缩略图 URL
            thumbnail_url = item.get("thumbnailUrl") or item.get("thumbnail") or url

            # 获取标题（处理 None 值，从 URL 提取备用标题）
            title = item.get("name") or item.get("title") or ""
            if not title and url:
                # 从 URL 提取文件名作为标题
                from urllib.parse import unquote, urlparse

                path = urlparse(url).path
                filename = path.split("/")[-1] if path else ""
                title = unquote(filename.split(".")[0]) if filename else "图片"

            # 获取来源页面 URL
            source_url = item.get("hostPageUrl") or item.get("sourceUrl") or item.get("hostPageDisplayUrl") or ""

            image = ImageResult(
                url=url,
                thumbnail_url=thumbnail_url,
                title=title,
                source_url=source_url,
                width=item.get("width") or 0,
                height=item.get("height") or 0,
            )
            images.append(image)

        logger.debug(f" 解析图片结果: {len(images)} 张")
        return images

    def _extract_images_from_web_search(self, web_data: Dict[str, Any], max_count: int = 12) -> List[ImageResult]:
        """
        从 Web Search 响应中提取图片

         v7.176: 优化提取逻辑
        - 优先从顶层 images 字段提取（高质量）
        - 备选从网页结果的 thumbnailUrl 提取

        Args:
            web_data: Web Search API 响应数据
            max_count: 最大返回数量

        Returns:
            ImageResult 列表
        """
        images = []

        # 1. 优先从顶层 images 字段提取（这是博查返回的高质量图片）
        if "images" in web_data:
            images = self._parse_image_results(web_data)
            if images:
                logger.info(f" 从 Web Search images 字段提取: {len(images)} 张图片")

        # 2. 如果没有足够的图片，从网页结果中补充
        if len(images) < max_count:
            web_pages = web_data.get("webPages", {}).get("value", [])
            for page in web_pages:
                if len(images) >= max_count:
                    break

                # 检查网页结果中的图片字段
                thumb_url = page.get("thumbnailUrl") or page.get("imageUrl") or ""
                if thumb_url:
                    # 避免重复
                    existing_urls = {img.url for img in images}
                    if thumb_url not in existing_urls:
                        image = ImageResult(
                            url=thumb_url,
                            thumbnail_url=thumb_url,
                            title=page.get("name", "")[:100] if page.get("name") else "图片",
                            source_url=page.get("url", ""),
                        )
                        images.append(image)

        return images[:max_count]

    def _extract_ai_summary(self, data: Dict[str, Any]) -> str:
        """提取AI生成的摘要"""
        # 博查API可能在不同字段返回摘要
        if "aiSummary" in data:
            return data["aiSummary"]

        # 从第一个结果的summary字段获取
        web_pages = data.get("webPages", {}).get("value", [])
        if web_pages and web_pages[0].get("summary"):
            return web_pages[0]["summary"]

        return ""

    async def _generate_with_deepseek_r1(
        self,
        query: str,
        search_result: AISearchResult,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        使用 OpenAI 进行推理生成（v7.275 切换自 DeepSeek-R1）

        流式返回推理过程和最终回答

        OpenAI API 特点：
        - 模型名: gpt-4o（可通过环境变量配置）
        - 支持 system 消息
        - 流式输出 content 字段
        """
        try:
            import os

            import httpx

            # 获取 OpenAI API 配置
            api_key = os.getenv("OPENAI_API_KEY", "")

            # 检查是否为有效的 API Key（排除占位符值）
            placeholder_values = ["your_openai_api_key", "your_openai_api_key_here", "sk-xxx", ""]
            if not api_key or api_key in placeholder_values:
                logger.warning("️ OPENAI_API_KEY 未配置或无效，使用博查摘要作为回答。" "请访问 https://platform.openai.com/ 获取有效的 API Key")
                if search_result.ai_summary:
                    yield {"type": "content", "data": search_result.ai_summary}
                return

            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
            model = os.getenv("BOCHA_AI_SEARCH_MODEL", "gpt-4o")  # 可配置模型

            # 构建上下文
            context = self._build_context_for_llm(search_result)

            # 系统提示词
            system_prompt = """你是一个资深的信息分析专家，擅长综合多源信息进行深度分析。请基于搜索结果，对用户问题进行全面、专业的分析。

## 任务要求

1. **深度分析**：不要简单罗列信息，要进行深入的分析和洞察
2. **结构化回答**：使用清晰的标题、分点论述，便于阅读
3. **引用来源**：使用 [1]、[2] 等标注信息来源，确保可溯源
4. **多角度分析**：从不同维度分析问题，呈现完整视角
5. **实用建议**：在分析基础上给出实际可行的建议或结论

## 输出格式

请使用 Markdown 格式，包含：
- 开篇概述（1-2段，回答问题核心）
- 详细分析（多个小节，每节有标题）
- 关键要点（列表形式，突出重点）
- 总结建议（结尾总结）"""

            # 用户消息
            user_prompt = f"""## 用户问题

{query}

## 搜索结果

{context}

---

请基于以上信息，撰写一篇专业、深入、结构清晰的分析回答。使用中文，语言专业但易于理解。"""

            # 使用 httpx 直接调用 OpenAI API（支持流式）
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": model,
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                "stream": True,
                "max_tokens": 8192,
            }

            content_buffer = ""

            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data.get("choices", [{}])[0].get("delta", {})

                                # OpenAI 内容在 content 字段
                                if "content" in delta and delta["content"]:
                                    content_buffer += delta["content"]
                                    if len(content_buffer) > 20:
                                        yield {"type": "content_chunk", "data": content_buffer}
                                        content_buffer = ""

                            except json.JSONDecodeError:
                                continue

            # 发送剩余的正文内容
            if content_buffer:
                yield {"type": "content_chunk", "data": content_buffer}

        except Exception as e:
            logger.error(f" OpenAI 生成失败: {e}")
            # 降级到博查摘要
            if search_result.ai_summary:
                yield {"type": "content", "data": search_result.ai_summary}
            else:
                yield {"type": "error", "data": {"message": f"推理生成失败: {e}"}}

    def _build_context_for_llm(self, search_result: AISearchResult) -> str:
        """构建LLM上下文 - 增强版"""
        context_parts = []

        for source in search_result.sources[:10]:  # 最多使用10个来源
            # 构建丰富的来源信息
            whitelist_marker = "⭐ [权威来源]" if source.is_whitelisted else ""
            date_info = f"发布时间：{source.date_published}" if source.date_published else ""

            part = f"""### 【来源 {source.reference_number}】{source.title} {whitelist_marker}
- 网站：{source.site_name}
- 链接：{source.url}
{f"- {date_info}" if date_info else ""}

**内容摘要：**
{source.snippet}

{f"**详细内容：**\n{source.summary}" if source.summary and len(source.summary) > len(source.snippet) else ""}
"""
            context_parts.append(part)

        # 添加来源统计
        whitelist_count = sum(1 for s in search_result.sources if s.is_whitelisted)
        header = f"""**共 {len(search_result.sources)} 个信息来源，其中 {whitelist_count} 个来自权威网站**

---

"""
        return header + "\n---\n".join(context_parts)

    def _source_to_dict(self, source: SourceCard) -> Dict[str, Any]:
        """SourceCard 转字典"""
        return {
            "title": source.title,
            "url": source.url,
            "siteName": source.site_name,
            "siteIcon": source.site_icon,
            "snippet": source.snippet,
            "summary": source.summary,
            "datePublished": source.date_published,
            "referenceNumber": source.reference_number,
            "isWhitelisted": source.is_whitelisted,
        }

    def _image_to_dict(self, image: ImageResult) -> Dict[str, Any]:
        """ImageResult 转字典"""
        return {
            "url": image.url,
            "thumbnailUrl": image.thumbnail_url,
            "title": image.title,
            "sourceUrl": image.source_url,
            "width": image.width,
            "height": image.height,
        }

    # ==================== v7.173: Arxiv 学术搜索 ====================

    async def _arxiv_search(self, query: str, max_results: int = 5) -> List[SourceCard]:
        """
         v7.173: 执行 Arxiv 学术论文搜索

        Args:
            query: 搜索关键词
            max_results: 最大返回结果数

        Returns:
            SourceCard 列表（学术论文来源）
        """
        if not self.arxiv_tool or not self.arxiv_enabled:
            return []

        try:
            # 在线程池中执行同步搜索（arxiv库是同步的）
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: self.arxiv_tool.search(query, max_results=max_results))

            if not result.get("success", False):
                logger.warning(f"️ [Arxiv] 搜索失败: {result.get('error', 'Unknown error')}")
                return []

            sources = []
            for paper in result.get("results", []):
                # 生成唯一ID
                source_id = ""
                if generate_stable_search_id:
                    source_id = generate_stable_search_id(
                        "arxiv", paper.get("pdf_url", paper.get("entry_id", "")), paper.get("title", "")
                    )

                # 格式化作者列表
                authors = paper.get("authors", [])
                authors_str = ", ".join(authors[:3])
                if len(authors) > 3:
                    authors_str += f" 等 {len(authors)} 位作者"

                # 格式化发布日期
                published = paper.get("published", "")
                if published:
                    try:
                        # ISO格式转换为更友好的格式
                        from datetime import datetime

                        dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                        published = dt.strftime("%Y-%m-%d")
                    except Exception:
                        pass

                source = SourceCard(
                    title=f"[学术] {paper.get('title', '')}",
                    url=paper.get("pdf_url", paper.get("entry_id", "")),
                    site_name="arXiv",
                    site_icon="https://arxiv.org/favicon.ico",
                    snippet=f"作者: {authors_str}\n{paper.get('summary', '')[:250]}...",
                    summary=paper.get("summary", ""),
                    date_published=published,
                    is_whitelisted=True,  # 学术来源默认高质量
                    quality_score=0.9,
                    id=source_id,
                )
                sources.append(source)

            logger.info(f" [Arxiv] 找到 {len(sources)} 篇学术论文")
            return sources

        except Exception as e:
            logger.warning(f"️ [Arxiv] 搜索异常: {e}")
            return []

    # ==================== v7.171: TikHub 社交媒体搜索 ====================

    async def _search_tikhub(self, query: str) -> List[SourceCard]:
        """
         v7.171: 搜索 TikHub 社交媒体平台

        支持平台:
        - xiaohongshu: 小红书笔记搜索
        - douyin: 抖音视频搜索
        - weibo: 微博Web搜索
        - zhihu: 知乎文章搜索V3

        Args:
            query: 搜索关键词

        Returns:
            SourceCard 列表
        """
        if not self.tikhub_client:
            return []

        results = []

        for platform in self.tikhub_platforms:
            try:
                platform_results = await self._search_tikhub_platform(platform, query)
                results.extend(platform_results)
                if platform_results:
                    logger.info(f" [TikHub/{platform}] Found {len(platform_results)} results")
            except Exception as e:
                logger.warning(f"️ [TikHub/{platform}] Search failed: {e}")
                continue

        return results

    async def _search_tikhub_platform(self, platform: str, query: str) -> List[SourceCard]:
        """
        搜索单个 TikHub 平台

        Args:
            platform: 平台名称 (xiaohongshu, douyin, weibo, zhihu)
            query: 搜索关键词

        Returns:
            SourceCard 列表
        """
        results = []
        tikhub_base = settings.bocha.tikhub_base_url
        headers = {"Authorization": f"Bearer {settings.bocha.tikhub_api_key}", "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                if platform == "xiaohongshu":
                    # 小红书笔记搜索 - 使用 SDK
                    try:
                        response = await self.tikhub_client.XiaohongshuWeb.search_notes(
                            keyword=query, page=1, sort="general"
                        )
                        if response and response.get("data"):
                            inner_data = response.get("data", {}).get("data", {})
                            items = inner_data.get("items", [])
                            for item in items[: self.tikhub_count]:
                                source = self._normalize_xiaohongshu_result(item)
                                if source:
                                    results.append(source)
                    except Exception as e:
                        logger.debug(f"[TikHub/xiaohongshu] SDK call failed: {e}")

                elif platform == "douyin":
                    # 抖音视频搜索 - HTTP API
                    url = f"{tikhub_base}/api/v1/douyin/search/fetch_video_search_v1"
                    payload = {
                        "keyword": query,
                        "offset": 0,
                        "count": self.tikhub_count,
                        "sort_type": "0",
                        "publish_time": "0",
                        "filter_duration": "0",
                    }
                    response = await client.post(url, headers=headers, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("data"):
                            items = data["data"].get("data", []) or data["data"].get("aweme_list", [])
                            for item in items[: self.tikhub_count]:
                                source = self._normalize_douyin_result(item)
                                if source:
                                    results.append(source)

                elif platform == "weibo":
                    # 微博Web搜索 - HTTP API
                    url = f"{tikhub_base}/api/v1/weibo/web/fetch_search"
                    params = {"keyword": query, "page": "1"}
                    response = await client.get(url, headers=headers, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("data"):
                            inner_data = data["data"].get("data", {})
                            items = inner_data.get("cards", []) if isinstance(inner_data, dict) else []
                            if isinstance(items, list):
                                for item in items[: self.tikhub_count]:
                                    source = self._normalize_weibo_result(item)
                                    if source:
                                        results.append(source)

                elif platform == "zhihu":
                    # 知乎文章搜索V3 - HTTP API
                    url = f"{tikhub_base}/api/v1/zhihu/web/fetch_article_search_v3"
                    params = {"keyword": query, "page": "1"}
                    response = await client.get(url, headers=headers, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("data"):
                            items = data["data"].get("data", []) or data["data"].get("items", [])
                            if isinstance(items, list):
                                for item in items[: self.tikhub_count]:
                                    source = self._normalize_zhihu_result(item)
                                    if source:
                                        results.append(source)

        except Exception as e:
            logger.warning(f"️ [TikHub/{platform}] API call failed: {e}")

        return results

    def _normalize_xiaohongshu_result(self, item: Dict[str, Any]) -> Optional[SourceCard]:
        """标准化小红书搜索结果"""
        try:
            note = item.get("note", item)
            note.get("user", {})

            note_id = note.get("id", "") or note.get("note_id", "")
            title = note.get("title", "") or note.get("display_title", "")
            desc = note.get("desc", "")
            display_title = title if title else (desc[:50] if desc else "小红书笔记")
            url = f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else ""

            #  v7.167: 生成唯一ID
            source_id = ""
            if generate_stable_search_id:
                source_id = generate_stable_search_id("xiaohongshu", url, display_title)

            return SourceCard(
                title=f"[小红书] {display_title}",
                url=url,
                site_name="小红书",
                site_icon="",
                snippet=desc[:200] if desc else title,
                summary=desc,
                is_whitelisted=False,
                id=source_id,
            )
        except Exception as e:
            logger.debug(f"Failed to normalize xiaohongshu result: {e}")
            return None

    def _normalize_douyin_result(self, item: Dict[str, Any]) -> Optional[SourceCard]:
        """标准化抖音搜索结果"""
        try:
            aweme_info = item.get("aweme_info", item)
            aweme_info.get("author", {})

            aweme_id = aweme_info.get("aweme_id", "")
            desc = aweme_info.get("desc", "")
            url = f"https://www.douyin.com/video/{aweme_id}" if aweme_id else ""
            title = f"[抖音] {desc[:50] if desc else '抖音视频'}"

            #  v7.167: 生成唯一ID
            source_id = ""
            if generate_stable_search_id:
                source_id = generate_stable_search_id("douyin", url, title)

            return SourceCard(
                title=title,
                url=url,
                site_name="抖音",
                site_icon="",
                snippet=desc[:200] if desc else "",
                summary=desc,
                is_whitelisted=False,
                id=source_id,
            )
        except Exception as e:
            logger.debug(f"Failed to normalize douyin result: {e}")
            return None

    def _normalize_weibo_result(self, item: Dict[str, Any]) -> Optional[SourceCard]:
        """标准化微博搜索结果"""
        try:
            mblog = item.get("mblog", item)
            mblog.get("user", {})

            # 优先使用 bid（短链接ID），如果没有则使用 mid
            bid = mblog.get("bid", "")
            mid = mblog.get("mid", "") or mblog.get("id", "")
            text = mblog.get("text", "") or mblog.get("text_raw", "")
            # 移除HTML标签
            import re

            clean_text = re.sub(r"<[^>]+>", "", text)

            # 使用移动端 URL（无需登录）
            if bid:
                url = f"https://m.weibo.cn/detail/{bid}"
            elif mid:
                url = f"https://m.weibo.cn/detail/{mid}"
            else:
                url = ""

            title = f"[微博] {clean_text[:50] if clean_text else '微博内容'}"

            #  v7.167: 生成唯一ID
            source_id = ""
            if generate_stable_search_id:
                source_id = generate_stable_search_id("weibo", url, title)

            return SourceCard(
                title=title,
                url=url,
                site_name="微博",
                site_icon="",
                snippet=clean_text[:200] if clean_text else "",
                summary=clean_text,
                is_whitelisted=False,
                id=source_id,
            )
        except Exception as e:
            logger.debug(f"Failed to normalize weibo result: {e}")
            return None

    def _normalize_zhihu_result(self, item: Dict[str, Any]) -> Optional[SourceCard]:
        """标准化知乎搜索结果"""
        import re

        def clean_html(text: str) -> str:
            """清理HTML标签"""
            if not text:
                return ""
            # 移除所有HTML标签
            return re.sub(r"<[^>]+>", "", text)

        try:
            # 知乎文章结构
            raw_title = item.get("title", "") or item.get("question", {}).get("title", "")
            raw_content = item.get("excerpt", "") or item.get("content", "")
            url = item.get("url", "")
            obj_type = item.get("type", "")  # article, answer 等

            # 清理HTML标签
            title = clean_html(raw_title)
            content = clean_html(raw_content)

            # 处理 API URL（形如 https://api.zhihu.com/articles/xxx）
            if url and "api.zhihu.com" in url:
                # 从API URL提取ID
                if "/articles/" in url:
                    article_id = url.split("/articles/")[-1].split("?")[0]
                    url = f"https://zhuanlan.zhihu.com/p/{article_id}"
                elif "/answers/" in url:
                    answer_id = url.split("/answers/")[-1].split("?")[0]
                    question_id = item.get("question", {}).get("id", "")
                    if question_id:
                        url = f"https://www.zhihu.com/question/{question_id}/answer/{answer_id}"
                    else:
                        url = f"https://www.zhihu.com/answer/{answer_id}"

            # 如果没有完整URL，根据类型构建
            if not url:
                item_id = item.get("id", "")
                if item_id:
                    if obj_type == "article":
                        url = f"https://zhuanlan.zhihu.com/p/{item_id}"
                    elif obj_type == "answer":
                        question_id = item.get("question", {}).get("id", "")
                        if question_id:
                            url = f"https://www.zhihu.com/question/{question_id}/answer/{item_id}"
                        else:
                            url = f"https://www.zhihu.com/answer/{item_id}"
                    else:
                        # 默认当作文章处理
                        url = f"https://zhuanlan.zhihu.com/p/{item_id}"

            display_title = f"[知乎] {title[:50] if title else '知乎文章'}"

            #  v7.167: 生成唯一ID
            source_id = ""
            if generate_stable_search_id:
                source_id = generate_stable_search_id("zhihu", url, display_title)

            return SourceCard(
                title=display_title,
                url=url,
                site_name="知乎",
                site_icon="",
                snippet=content[:200] if content else "",
                summary=content,
                is_whitelisted=False,
                id=source_id,
            )
        except Exception as e:
            logger.debug(f"Failed to normalize zhihu result: {e}")
            return None


# 单例实例
_ai_search_service: Optional[BochaAISearchService] = None


def get_ai_search_service() -> BochaAISearchService:
    """获取博查AI搜索服务单例"""
    global _ai_search_service
    if _ai_search_service is None:
        _ai_search_service = BochaAISearchService()
    return _ai_search_service
