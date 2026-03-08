"""
OpenAlex 学术搜索工具 (v7.198)

提供开放学术数据搜索功能，支持论文、作者、机构检索。

特点：
- 完全免费，无需认证
- 每日 100,000 次请求/用户
- 2.5亿+ 学术论文数据库
- CC0 开放数据许可

API 文档: https://docs.openalex.org/

作者: AI Assistant
日期: 2026-01-10
"""

import os
from typing import Any, Dict, List

import httpx
from loguru import logger

from ..core.types import ToolConfig

# 配置
OPENALEX_ENABLED = os.getenv("OPENALEX_ENABLED", "true").lower() == "true"
OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL", "")  # 可选，用于 polite pool
OPENALEX_BASE_URL = "https://api.openalex.org"
OPENALEX_TIMEOUT = int(os.getenv("OPENALEX_TIMEOUT", "30"))

# LangChain Tool integration
try:
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, Field

    LANGCHAIN_AVAILABLE = True
except ImportError:
    logger.warning("LangChain not available, tool wrapping disabled")
    LANGCHAIN_AVAILABLE = False

# 导入质量控制模块
try:
    from .quality_control import SearchQualityControl
except ImportError:
    logger.warning("️ quality_control not available")
    SearchQualityControl = None

# 导入搜索结果ID生成器
try:
    from ..utils.search_id_generator import add_ids_to_search_results
except ImportError:
    logger.warning("️ search_id_generator not available")
    add_ids_to_search_results = None


class OpenAlexSearchTool:
    """OpenAlex 学术搜索工具类"""

    def __init__(self, config: ToolConfig | None = None):
        """
        初始化 OpenAlex 搜索工具

        Args:
            config: 工具配置
        """
        self.config = config or ToolConfig(name="openalex_search")
        self.name = self.config.name

        # HTTP 客户端
        self.client = httpx.Client(timeout=OPENALEX_TIMEOUT)

        # 默认搜索参数
        self.default_params = {
            "max_results": 10,
        }

        # 质量控制
        self.qc = SearchQualityControl() if SearchQualityControl else None

        # 构建基础 headers（polite pool）
        self.headers = {"Accept": "application/json"}
        if OPENALEX_EMAIL:
            self.headers["User-Agent"] = f"mailto:{OPENALEX_EMAIL}"

        logger.info(f" OpenAlex 搜索工具初始化完成 (polite_pool={'yes' if OPENALEX_EMAIL else 'no'})")

    def search(
        self,
        query: str,
        max_results: int | None = None,
        from_year: int | None = None,
        to_year: int | None = None,
        open_access_only: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        搜索学术论文

        Args:
            query: 搜索关键词
            max_results: 最大结果数量（默认10）
            from_year: 起始年份
            to_year: 结束年份
            open_access_only: 仅开放获取论文
            **kwargs: 其他参数

        Returns:
            搜索结果字典
        """
        if not OPENALEX_ENABLED:
            return {
                "status": "disabled",
                "message": "OpenAlex 搜索已禁用",
                "results": [],
            }

        if not query:
            return {
                "status": "error",
                "message": "查询不能为空",
                "results": [],
            }

        max_results = max_results or self.default_params["max_results"]

        try:
            # 构建 API 请求
            url = f"{OPENALEX_BASE_URL}/works"
            params = {
                "search": query,
                "per_page": min(max_results, 50),  # API 限制每页最多200
            }

            # 添加过滤器
            filters = []
            if from_year:
                filters.append(f"from_publication_date:{from_year}-01-01")
            if to_year:
                filters.append(f"to_publication_date:{to_year}-12-31")
            if open_access_only:
                filters.append("is_oa:true")

            if filters:
                params["filter"] = ",".join(filters)

            # polite pool
            if OPENALEX_EMAIL:
                params["mailto"] = OPENALEX_EMAIL

            logger.info(f" [OpenAlex] 搜索: '{query[:50]}...' | 限制={max_results}")

            # 执行请求
            response = self.client.get(url, params=params, headers=self.headers)
            response.raise_for_status()

            data = response.json()

            # 解析结果
            results = []
            for work in data.get("results", [])[:max_results]:
                result = self._parse_work(work)
                results.append(result)

            # 添加搜索结果 ID
            if add_ids_to_search_results:
                results = add_ids_to_search_results(results, "openalex")

            logger.info(f" [OpenAlex] 找到 {len(results)} 篇论文")

            return {
                "status": "success",
                "query": query,
                "total_count": data.get("meta", {}).get("count", 0),
                "returned_count": len(results),
                "results": results,
            }

        except httpx.TimeoutException:
            logger.error(f" [OpenAlex] 请求超时: {query}")
            return {
                "status": "error",
                "message": "请求超时",
                "results": [],
            }
        except httpx.HTTPStatusError as e:
            logger.error(f" [OpenAlex] HTTP 错误: {e.response.status_code}")
            return {
                "status": "error",
                "message": f"HTTP 错误: {e.response.status_code}",
                "results": [],
            }
        except Exception as e:
            logger.error(f" [OpenAlex] 搜索失败: {e}")
            return {
                "status": "error",
                "message": str(e),
                "results": [],
            }

    def _parse_work(self, work: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析单篇论文数据

        Args:
            work: OpenAlex 论文数据

        Returns:
            标准化的论文结果
        """
        # 提取标题（优先英文）
        title = work.get("title", "")

        # 提取摘要
        abstract = ""
        if work.get("abstract_inverted_index"):
            # OpenAlex 使用倒排索引存储摘要，需要重建
            abstract = self._rebuild_abstract(work["abstract_inverted_index"])

        # 提取作者
        authors = []
        for authorship in work.get("authorships", [])[:5]:  # 最多5个作者
            author = authorship.get("author", {})
            author_name = author.get("display_name", "")
            if author_name:
                authors.append(author_name)

        # 提取发布日期
        pub_date = work.get("publication_date", "")
        pub_year = work.get("publication_year")

        # 提取 DOI 和 URL
        doi = work.get("doi", "")
        url = doi if doi else work.get("id", "")

        # 提取期刊/会议
        source = work.get("primary_location", {}).get("source", {})
        journal = source.get("display_name", "") if source else ""

        # 提取引用数
        cited_by_count = work.get("cited_by_count", 0)

        # 开放获取状态
        is_oa = work.get("open_access", {}).get("is_oa", False)
        oa_url = work.get("open_access", {}).get("oa_url", "")

        # 主题/概念
        concepts = []
        for concept in work.get("concepts", [])[:5]:
            concept_name = concept.get("display_name", "")
            if concept_name:
                concepts.append(concept_name)

        return {
            "title": title,
            "url": url,
            "doi": doi,
            "abstract": abstract[:500] if abstract else "",  # 限制摘要长度
            "snippet": abstract[:200] if abstract else title,
            "content": abstract,
            "authors": authors,
            "authors_str": ", ".join(authors),
            "publication_date": pub_date,
            "publication_year": pub_year,
            "journal": journal,
            "cited_by_count": cited_by_count,
            "is_open_access": is_oa,
            "open_access_url": oa_url,
            "concepts": concepts,
            "source": "openalex",
            "source_credibility": "high",  # 学术来源
        }

    def _rebuild_abstract(self, inverted_index: Dict[str, List[int]]) -> str:
        """
        从倒排索引重建摘要文本

        OpenAlex 使用倒排索引格式存储摘要以节省空间

        Args:
            inverted_index: 倒排索引 {"word": [position1, position2, ...]}

        Returns:
            重建的摘要文本
        """
        if not inverted_index:
            return ""

        # 构建位置到词的映射
        position_to_word = {}
        for word, positions in inverted_index.items():
            for pos in positions:
                position_to_word[pos] = word

        # 按位置排序并重建文本
        max_position = max(position_to_word.keys()) if position_to_word else 0
        words = [position_to_word.get(i, "") for i in range(max_position + 1)]

        return " ".join(words)

    def search_by_author(
        self,
        author_name: str,
        max_results: int | None = None,
    ) -> Dict[str, Any]:
        """
        按作者搜索论文

        Args:
            author_name: 作者姓名
            max_results: 最大结果数量

        Returns:
            搜索结果字典
        """
        return self.search(
            query=author_name,
            max_results=max_results,
        )

    def search_by_concept(
        self,
        concept: str,
        max_results: int | None = None,
        min_citations: int = 0,
    ) -> Dict[str, Any]:
        """
        按研究概念/领域搜索

        Args:
            concept: 研究概念/领域
            max_results: 最大结果数量
            min_citations: 最小引用数

        Returns:
            搜索结果字典
        """
        result = self.search(query=concept, max_results=max_results)

        if result.get("status") == "success" and min_citations > 0:
            # 过滤低引用论文
            result["results"] = [r for r in result["results"] if r.get("cited_by_count", 0) >= min_citations]
            result["returned_count"] = len(result["results"])

        return result

    def get_work_details(self, openalex_id: str) -> Dict[str, Any]:
        """
        获取单篇论文详情

        Args:
            openalex_id: OpenAlex ID (如 W2741809807)

        Returns:
            论文详情
        """
        try:
            url = f"{OPENALEX_BASE_URL}/works/{openalex_id}"
            params = {}
            if OPENALEX_EMAIL:
                params["mailto"] = OPENALEX_EMAIL

            response = self.client.get(url, params=params, headers=self.headers)
            response.raise_for_status()

            work = response.json()
            return {
                "status": "success",
                "work": self._parse_work(work),
            }

        except Exception as e:
            logger.error(f" [OpenAlex] 获取论文详情失败: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    def __del__(self):
        """清理资源"""
        if hasattr(self, "client"):
            self.client.close()


# ============ LangChain Tool 包装 ============

if LANGCHAIN_AVAILABLE:

    class OpenAlexSearchInput(BaseModel):
        """OpenAlex 搜索输入模式"""

        query: str = Field(description="搜索关键词，如论文标题、作者、研究主题等")
        max_results: int = Field(default=10, description="返回结果数量（1-50）")
        from_year: int | None = Field(default=None, description="起始年份，如 2020")
        to_year: int | None = Field(default=None, description="结束年份，如 2024")
        open_access_only: bool = Field(default=False, description="是否仅返回开放获取论文")

    def create_openalex_tool() -> StructuredTool:
        """创建 LangChain 工具"""
        tool = OpenAlexSearchTool()

        def run_search(
            query: str,
            max_results: int = 10,
            from_year: int | None = None,
            to_year: int | None = None,
            open_access_only: bool = False,
        ) -> str:
            """执行搜索并返回结果"""
            result = tool.search(
                query=query,
                max_results=max_results,
                from_year=from_year,
                to_year=to_year,
                open_access_only=open_access_only,
            )

            if result.get("status") != "success":
                return f"搜索失败: {result.get('message', '未知错误')}"

            papers = result.get("results", [])
            if not papers:
                return f"未找到与 '{query}' 相关的学术论文"

            output = [f"找到 {result.get('total_count', 0)} 篇相关论文，返回 {len(papers)} 篇：\n"]

            for i, paper in enumerate(papers, 1):
                title = paper.get("title", "无标题")
                authors = paper.get("authors_str", "未知作者")
                year = paper.get("publication_year", "")
                journal = paper.get("journal", "")
                citations = paper.get("cited_by_count", 0)
                url = paper.get("url", "")
                abstract = paper.get("abstract", "")[:200]

                output.append(f"{i}. {title}")
                output.append(f"   作者: {authors}")
                if year:
                    output.append(f"   发表: {year} | {journal}")
                if citations:
                    output.append(f"   引用: {citations} 次")
                if abstract:
                    output.append(f"   摘要: {abstract}...")
                if url:
                    output.append(f"   链接: {url}")
                output.append("")

            return "\n".join(output)

        return StructuredTool(
            name="openalex_academic_search",
            description=("搜索 OpenAlex 学术数据库，获取学术论文、研究文献。" "适用于需要学术背景、研究依据、理论支持的场景。" "数据库包含 2.5 亿+ 学术论文，完全免费。"),
            func=run_search,
            args_schema=OpenAlexSearchInput,
        )


# ============ 工具实例创建 ============

_tool_instance: OpenAlexSearchTool | None = None


def get_openalex_tool() -> OpenAlexSearchTool:
    """获取 OpenAlex 工具单例"""
    global _tool_instance
    if _tool_instance is None:
        _tool_instance = OpenAlexSearchTool()
    return _tool_instance
