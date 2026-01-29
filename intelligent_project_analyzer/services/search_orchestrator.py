"""
多轮搜索编排器 (v7.198)

实现5轮渐进式搜索：
1. 基础概念探索 - 获取定义和框架
2. 维度深化 - 深入各影响维度
3. 学术深度 - 搜索论文和方法论（Arxiv + OpenAlex）
4. 实践案例 - 搜索项目案例
5. 数据支撑 - 搜索统计数据

核心特点：
- 渐进式深化：从概念到维度到学术到案例到数据
- 动态调整：根据前轮结果调整后续搜索
- 多工具协同：智能选择 Tavily/Bocha/Arxiv/OpenAlex
- 结构化输出：分类整合搜索结果

v7.198 更新：
- 集成 OpenAlex 开放学术数据库（2.5亿+ 论文）
- 学术搜索轮次同时查询 Arxiv + OpenAlex
"""

import asyncio
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml
from loguru import logger

# 导入搜索工具
try:
    from ..agents.bocha_search_tool import BochaSearchTool, create_bocha_search_tool_from_settings
    from ..settings import settings
    from ..tools.arxiv_search import ArxivSearchTool
    from ..tools.openalex_search import OpenAlexSearchTool  # v7.198: 新增
    from ..tools.quality_control import SearchQualityControl
    from ..tools.query_builder import DeliverableQueryBuilder
    from ..tools.tavily_search import TavilySearchTool
except ImportError as e:
    logger.warning(f"⚠️ 部分搜索工具导入失败: {e}")
    OpenAlexSearchTool = None  # v7.198: 兼容导入失败


class SearchOrchestrator:
    """
    搜索编排器

    核心流程：
    1. 解析用户查询，提取核心概念
    2. 生成5轮搜索计划
    3. 执行搜索并收集结果
    4. 根据前轮结果动态调整后续搜索
    5. 整合所有结果，结构化输出
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化搜索编排器

        Args:
            config_path: 配置文件路径，默认为 config/search_strategy.yaml
        """
        # 加载配置
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "search_strategy.yaml"

        self.config = self._load_config(config_path)
        self.orchestrator_config = self.config.get("search_orchestrator", {})

        # 初始化搜索工具
        self._init_search_tools()

        # 初始化质量控制
        self.qc = SearchQualityControl() if SearchQualityControl else None

        # 初始化查询构建器
        self.query_builder = DeliverableQueryBuilder() if DeliverableQueryBuilder else None

        logger.info("✅ SearchOrchestrator initialized")

    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            else:
                logger.warning(f"⚠️ 配置文件不存在: {config_path}")
                return {}
        except Exception as e:
            logger.error(f"❌ 加载配置失败: {e}")
            return {}

    def _init_search_tools(self):
        """初始化搜索工具"""
        self.tavily = None
        self.bocha = None
        self.arxiv = None
        self.openalex = None  # v7.198: 新增 OpenAlex

        # 初始化 Tavily
        try:
            tavily_api_key = settings.tavily.api_key
            if tavily_api_key:
                self.tavily = TavilySearchTool(api_key=tavily_api_key)
                logger.info("✅ Tavily search tool initialized")
        except Exception as e:
            logger.warning(f"⚠️ Tavily 初始化失败: {e}")

        # 初始化 Bocha
        try:
            self.bocha = create_bocha_search_tool_from_settings()
            if self.bocha:
                logger.info("✅ Bocha search tool initialized")
        except Exception as e:
            logger.warning(f"⚠️ Bocha 初始化失败: {e}")

        # 初始化 Arxiv
        try:
            self.arxiv = ArxivSearchTool()
            logger.info("✅ Arxiv search tool initialized")
        except Exception as e:
            logger.warning(f"⚠️ Arxiv 初始化失败: {e}")

        # 🆕 v7.198: 初始化 OpenAlex
        try:
            if OpenAlexSearchTool:
                self.openalex = OpenAlexSearchTool()
                logger.info("✅ OpenAlex search tool initialized")
        except Exception as e:
            logger.warning(f"⚠️ OpenAlex 初始化失败: {e}")

    def orchestrate(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        max_rounds: Optional[int] = None,
        state: Optional[Dict[str, Any]] = None,  # 🆕 v7.180: 接受state参数
    ) -> Dict[str, Any]:
        """
        执行5轮渐进式搜索

        🆕 v7.180: 支持从state中提取需求分析结果，增强搜索精准度

        Args:
            query: 用户原始查询
            context: 上下文信息（项目类型、交付物等）
            max_rounds: 最大搜索轮次（默认5轮）
            state: ProjectAnalysisState（可选，用于提取需求分析结果）

        Returns:
            结构化搜索结果
        """
        start_time = time.time()
        max_rounds = max_rounds or self.orchestrator_config.get("max_rounds", 5)

        logger.info(f"🚀 [Orchestrator] Starting {max_rounds}-round progressive search")
        logger.info(f"📝 [Orchestrator] Query: {query}")

        # Step 1: 解析查询，提取核心概念
        concepts = self._extract_concepts(query)
        domain = self._extract_domain(query, context)
        logger.info(f"🔍 [Orchestrator] Extracted concepts: {concepts}")
        logger.info(f"🏷️ [Orchestrator] Domain: {domain}")

        # 🆕 v7.180: 提取需求分析上下文并生成增强查询
        requirements_context = None
        enhanced_queries = []
        if state:
            requirements_context = self._extract_requirements_context(state)
            if requirements_context.get("structured_requirements"):
                enhanced_queries = self._build_enhanced_queries(requirements_context, domain)
                logger.info(f"🔍 [Orchestrator] 已提取需求分析上下文，生成 {len(enhanced_queries)} 个增强查询")

        # Step 2: 执行多轮搜索
        all_results = {
            "query": query,
            "concepts": concepts,
            "domain": domain,
            "rounds": {},
            "all_sources": [],
            "execution_time": 0,
            "enhanced_queries": enhanced_queries,  # 🆕 v7.180
            "requirements_context": requirements_context,  # 🆕 v7.180
        }

        # 第1轮：基础概念探索
        if max_rounds >= 1:
            logger.info("📌 [Orchestrator] Round 1: Concept exploration")
            round1 = self._search_round_1_concepts(concepts, domain, enhanced_queries)
            all_results["rounds"]["concepts"] = round1
            all_results["all_sources"].extend(round1.get("results", []))

        # 第2轮：维度深化（根据第1轮结果提取维度）
        if max_rounds >= 2:
            logger.info("📌 [Orchestrator] Round 2: Dimension exploration")
            dimensions = self._extract_dimensions(all_results["rounds"].get("concepts", {}))
            round2 = self._search_round_2_dimensions(concepts, dimensions, domain)
            all_results["rounds"]["dimensions"] = round2
            all_results["dimensions_found"] = dimensions
            all_results["all_sources"].extend(round2.get("results", []))

        # 第3轮：学术深度
        if max_rounds >= 3:
            logger.info("📌 [Orchestrator] Round 3: Academic depth")
            round3 = self._search_round_3_academic(concepts, domain)
            all_results["rounds"]["academic"] = round3
            all_results["all_sources"].extend(round3.get("results", []))

        # 第4轮：实践案例
        if max_rounds >= 4:
            logger.info("📌 [Orchestrator] Round 4: Case studies")
            round4 = self._search_round_4_cases(concepts, domain)
            all_results["rounds"]["cases"] = round4
            all_results["all_sources"].extend(round4.get("results", []))

        # 第5轮：数据支撑
        if max_rounds >= 5:
            logger.info("📌 [Orchestrator] Round 5: Data support")
            round5 = self._search_round_5_data(concepts, domain)
            all_results["rounds"]["data"] = round5
            all_results["all_sources"].extend(round5.get("results", []))

        # Step 3: 整合结果
        integrated = self._integrate_results(all_results)

        total_time = time.time() - start_time
        integrated["execution_time"] = total_time
        integrated["rounds_completed"] = len(all_results["rounds"])

        logger.info(f"🎉 [Orchestrator] Search completed in {total_time:.2f}s")
        logger.info(f"📊 [Orchestrator] Total sources: {len(all_results['all_sources'])}")

        return integrated

    def _extract_concepts(self, query: str) -> List[str]:
        """
        从查询中提取核心概念

        Args:
            query: 用户查询

        Returns:
            核心概念列表
        """
        concepts = []

        # 使用 jieba 提取关键词
        try:
            import jieba.analyse

            keywords = jieba.analyse.extract_tags(query, topK=5, withWeight=False)
            concepts.extend(keywords)
        except ImportError:
            # 简单分词
            words = re.split(r"[，,。.、\s]+", query)
            concepts = [w for w in words if len(w) >= 2][:5]

        # 去重
        seen = set()
        unique_concepts = []
        for c in concepts:
            if c.lower() not in seen:
                unique_concepts.append(c)
                seen.add(c.lower())

        return unique_concepts

    def _extract_domain(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        提取领域信息

        Args:
            query: 用户查询
            context: 上下文信息

        Returns:
            领域名称
        """
        # 从上下文获取
        if context and context.get("project_type"):
            return context["project_type"]

        # 从查询中识别
        domain_mapping = self.orchestrator_config.get("domain_mapping", {})
        query_lower = query.lower()

        for key, value in domain_mapping.items():
            if value in query or key.replace("_", " ") in query_lower:
                return value

        # 默认领域
        return "设计"

    def _extract_dimensions(self, round1_results: Dict[str, Any]) -> List[str]:
        """
        从第1轮结果中提取关键维度

        Args:
            round1_results: 第1轮搜索结果

        Returns:
            维度列表
        """
        dimension_keywords = self.orchestrator_config.get(
            "dimension_keywords", ["哲学", "空间", "布局", "材料", "装饰", "功能", "风格", "技术", "可持续", "智能"]
        )

        found_dimensions = set()

        # 从搜索结果中提取维度
        for result in round1_results.get("results", []):
            content = result.get("content", "") or result.get("snippet", "")
            title = result.get("title", "")
            text = f"{title} {content}"

            for keyword in dimension_keywords:
                if keyword in text:
                    found_dimensions.add(keyword)

        # 如果没有找到，使用默认维度
        if not found_dimensions:
            found_dimensions = {"空间", "材料", "功能", "风格"}

        return list(found_dimensions)[:5]  # 最多5个维度

    def _search_round_1_concepts(
        self, concepts: List[str], domain: str, enhanced_queries: Optional[List[str]] = None  # 🆕 v7.180
    ) -> Dict[str, Any]:
        """
        第1轮：基础概念探索

        目的：获取概念定义和基本框架

        🆕 v7.180: 支持增强查询（来自需求分析）
        """
        round_config = self._get_round_config("concepts")
        queries = []

        # 🆕 v7.180: 优先使用增强查询
        if enhanced_queries:
            queries.extend(enhanced_queries[:6])  # 最多6个增强查询
            logger.debug(f"📌 Using {len(queries)} enhanced queries from requirements analysis")

        # 生成搜索词
        for concept in concepts[:3]:  # 最多3个核心概念
            patterns = round_config.get("query_patterns", ["{concept} 定义 含义", "{concept} 对 {domain} 影响"])
            for pattern in patterns[:2]:  # 每个概念最多2个模式
                query = pattern.replace("{concept}", concept).replace("{domain}", domain)
                queries.append(query)

        # 执行搜索
        results = self._execute_parallel_search(queries, round_config)

        return {
            "round_name": "concepts",
            "queries": queries,
            "results": results,
            "result_count": len(results),
            "enhanced_query_count": len(enhanced_queries) if enhanced_queries else 0,  # 🆕 v7.180
        }

    def _search_round_2_dimensions(self, concepts: List[str], dimensions: List[str], domain: str) -> Dict[str, Any]:
        """
        第2轮：维度深化

        目的：深入探索各个影响维度
        """
        round_config = self._get_round_config("dimensions")
        queries = []

        # 生成搜索词：概念 × 维度
        for concept in concepts[:2]:  # 最多2个核心概念
            for dimension in dimensions[:3]:  # 最多3个维度
                patterns = round_config.get("query_patterns", ["{concept} {dimension} 影响", "{concept} {dimension} 特点"])
                for pattern in patterns[:1]:  # 每组最多1个模式
                    query = pattern.replace("{concept}", concept).replace("{dimension}", dimension)
                    queries.append(query)

        # 执行搜索
        results = self._execute_parallel_search(queries, round_config)

        return {
            "round_name": "dimensions",
            "dimensions": dimensions,
            "queries": queries,
            "results": results,
            "result_count": len(results),
        }

    def _search_round_3_academic(self, concepts: List[str], domain: str) -> Dict[str, Any]:
        """
        第3轮：学术深度 (v7.198: Arxiv + OpenAlex 双源)

        目的：获取学术研究和方法论
        """
        round_config = self._get_round_config("academic")
        queries = []

        # 生成学术搜索词
        academic_keywords = ["研究", "论文", "方法论", "理论"]
        for concept in concepts[:2]:
            for keyword in academic_keywords[:2]:
                query = f"{concept} {keyword}"
                queries.append(query)

        # v7.198: 同时使用 Arxiv 和 OpenAlex
        results = self._execute_parallel_search(queries, round_config, prefer_academic=True)

        return {"round_name": "academic", "queries": queries, "results": results, "result_count": len(results)}

    def _search_round_4_cases(self, concepts: List[str], domain: str) -> Dict[str, Any]:
        """
        第4轮：实践案例

        目的：获取实际案例和项目
        """
        round_config = self._get_round_config("cases")
        queries = []

        # 生成案例搜索词
        case_keywords = ["案例", "项目", "设计实践", "作品"]
        for concept in concepts[:2]:
            for keyword in case_keywords[:2]:
                query = f"{concept} {keyword}"
                queries.append(query)

        # 执行搜索
        results = self._execute_parallel_search(queries, round_config)

        return {"round_name": "cases", "queries": queries, "results": results, "result_count": len(results)}

    def _search_round_5_data(self, concepts: List[str], domain: str) -> Dict[str, Any]:
        """
        第5轮：数据支撑

        目的：获取统计数据和趋势
        """
        round_config = self._get_round_config("data")
        queries = []

        # 生成数据搜索词
        current_year = datetime.now().year
        data_keywords = ["数据", "统计", "趋势", "市场规模"]

        # 使用领域相关词
        related_fields = [domain, concepts[0] if concepts else "设计"]
        for field in related_fields[:2]:
            for keyword in data_keywords[:2]:
                query = f"{field} {keyword} {current_year}"
                queries.append(query)

        # 执行搜索
        results = self._execute_parallel_search(queries, round_config)

        return {"round_name": "data", "queries": queries, "results": results, "result_count": len(results)}

    def _get_round_config(self, round_name: str) -> Dict[str, Any]:
        """获取指定轮次的配置"""
        rounds = self.orchestrator_config.get("rounds", [])
        for round_config in rounds:
            if round_config.get("name") == round_name:
                return round_config
        return {}

    def _execute_parallel_search(
        self,
        queries: List[str],
        round_config: Dict[str, Any],
        prefer_arxiv: bool = False,
        prefer_academic: bool = False,  # v7.198: 新增学术模式
    ) -> List[Dict[str, Any]]:
        """
        并行执行多个搜索查询

        Args:
            queries: 搜索查询列表
            round_config: 轮次配置
            prefer_arxiv: 是否优先使用 Arxiv（向后兼容）
            prefer_academic: 是否使用学术模式（Arxiv + OpenAlex）

        Returns:
            合并后的搜索结果
        """
        all_results = []
        max_results_per_query = round_config.get("max_results", 5)

        # 使用线程池并行搜索
        with ThreadPoolExecutor(max_workers=4) as executor:  # v7.198: 增加线程数
            futures = []

            for query in queries:
                # v7.198: 学术模式同时使用 Arxiv 和 OpenAlex
                if prefer_academic or prefer_arxiv:
                    if self.arxiv:
                        futures.append(executor.submit(self._search_arxiv, query, max_results_per_query))
                    if prefer_academic and self.openalex:
                        futures.append(executor.submit(self._search_openalex, query, max_results_per_query))

                # 判断是否中文查询
                is_chinese = self._is_chinese_query(query)

                if is_chinese and self.bocha:
                    futures.append(executor.submit(self._search_bocha, query, max_results_per_query))
                elif self.tavily:
                    futures.append(executor.submit(self._search_tavily, query, max_results_per_query))

            # 收集结果
            for future in as_completed(futures):
                try:
                    results = future.result(timeout=30)
                    all_results.extend(results)
                except Exception as e:
                    logger.warning(f"⚠️ 搜索任务失败: {e}")

        # 去重
        unique_results = self._deduplicate_results(all_results)

        # 质量控制
        if self.qc:
            unique_results = self.qc.process_results(unique_results)

        return unique_results[: round_config.get("max_results", 10)]

    def _search_tavily(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """使用 Tavily 搜索"""
        try:
            result = self.tavily.search(query, max_results=max_results)
            if result.get("success"):
                return result.get("results", [])
        except Exception as e:
            logger.warning(f"⚠️ Tavily 搜索失败: {e}")
        return []

    def _search_bocha(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """使用 Bocha 搜索"""
        try:
            result = self.bocha.search(query, count=max_results)
            if result.get("success"):
                return result.get("results", [])
        except Exception as e:
            logger.warning(f"⚠️ Bocha 搜索失败: {e}")
        return []

    def _search_arxiv(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """使用 Arxiv 搜索"""
        try:
            result = self.arxiv.search(query, max_results=max_results)
            if result.get("success"):
                return result.get("results", [])
        except Exception as e:
            logger.warning(f"⚠️ Arxiv 搜索失败: {e}")
        return []

    def _search_openalex(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        使用 OpenAlex 搜索 (v7.198 新增)

        Args:
            query: 搜索查询
            max_results: 最大结果数

        Returns:
            搜索结果列表
        """
        try:
            if not self.openalex:
                return []
            result = self.openalex.search(query, max_results=max_results)
            if result.get("status") == "success":
                return result.get("results", [])
        except Exception as e:
            logger.warning(f"⚠️ OpenAlex 搜索失败: {e}")
        return []

    def _is_chinese_query(self, query: str) -> bool:
        """判断是否为中文查询"""
        chinese_pattern = re.compile(r"[\u4e00-\u9fff]+")
        return bool(chinese_pattern.search(query))

    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重搜索结果"""
        seen_urls = set()
        unique_results = []

        for result in results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)

        return unique_results

    def _integrate_results(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        整合5轮搜索结果，生成结构化输出

        Args:
            all_results: 所有轮次的搜索结果

        Returns:
            结构化输出
        """
        # 🆕 v7.176: 保留 all_sources 用于后续处理
        all_sources = all_results.get("all_sources", [])

        integrated = {
            "success": True,
            "query": all_results.get("query", ""),
            "concepts": all_results.get("concepts", []),
            "domain": all_results.get("domain", ""),
            "all_sources": all_sources,  # 🆕 v7.176: 保留原始结果列表
            "rounds": all_results.get("rounds", {}),  # 🆕 v7.176: 保留轮次信息
            "summary": self._generate_summary(all_results),
            "concept_definitions": self._extract_definitions(all_results),
            "dimensions": self._organize_dimensions(all_results),
            "academic_sources": self._organize_academic(all_results),
            "case_studies": self._organize_cases(all_results),
            "data_points": self._organize_data(all_results),
            "references": self._generate_references(all_results),
            "statistics": {
                "total_sources": len(all_sources),
                "rounds_completed": len(all_results.get("rounds", {})),
                "by_round": {name: data.get("result_count", 0) for name, data in all_results.get("rounds", {}).items()},
            },
        }

        return integrated

    def _generate_summary(self, all_results: Dict[str, Any]) -> str:
        """生成搜索摘要"""
        concepts = all_results.get("concepts", [])
        domain = all_results.get("domain", "")
        total = len(all_results.get("all_sources", []))

        return f"针对「{', '.join(concepts)}」在「{domain}」领域的搜索，共获取 {total} 条结果，涵盖概念定义、维度分析、学术研究、实践案例和数据支撑。"

    def _extract_definitions(self, all_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取概念定义"""
        definitions = []
        concept_results = all_results.get("rounds", {}).get("concepts", {}).get("results", [])

        for result in concept_results[:5]:
            definitions.append(
                {
                    "title": result.get("title", ""),
                    "content": result.get("content", "") or result.get("snippet", ""),
                    "url": result.get("url", ""),
                    "source": result.get("siteName", ""),
                }
            )

        return definitions

    def _organize_dimensions(self, all_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """组织维度分析结果"""
        dimensions_found = all_results.get("dimensions_found", [])
        dimension_results = all_results.get("rounds", {}).get("dimensions", {}).get("results", [])

        organized = []
        for dim in dimensions_found:
            dim_data = {"name": dim, "sources": []}
            for result in dimension_results:
                content = result.get("content", "") or result.get("snippet", "")
                if dim in content or dim in result.get("title", ""):
                    dim_data["sources"].append(
                        {"title": result.get("title", ""), "url": result.get("url", ""), "snippet": content[:200]}
                    )
            if dim_data["sources"]:
                organized.append(dim_data)

        return organized

    def _organize_academic(self, all_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """组织学术来源"""
        academic_results = all_results.get("rounds", {}).get("academic", {}).get("results", [])
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "abstract": r.get("content", "") or r.get("snippet", ""),
                "source": r.get("siteName", ""),
            }
            for r in academic_results[:5]
        ]

    def _organize_cases(self, all_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """组织案例研究"""
        case_results = all_results.get("rounds", {}).get("cases", {}).get("results", [])
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "description": r.get("content", "") or r.get("snippet", ""),
                "source": r.get("siteName", ""),
            }
            for r in case_results[:8]
        ]

    def _organize_data(self, all_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """组织数据点"""
        data_results = all_results.get("rounds", {}).get("data", {}).get("results", [])
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", "") or r.get("snippet", ""),
                "source": r.get("siteName", ""),
            }
            for r in data_results[:5]
        ]

    def _generate_references(self, all_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成参考文献列表"""
        all_sources = all_results.get("all_sources", [])
        references = []
        seen_urls = set()

        for idx, source in enumerate(all_sources, 1):
            url = source.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                references.append(
                    {"id": idx, "title": source.get("title", ""), "url": url, "source": source.get("siteName", "")}
                )

            if len(references) >= 20:  # 最多20条参考文献
                break

        return references

    # ============================================================================
    # 🆕 v7.180: 需求分析上下文提取和增强查询构建
    # ============================================================================

    def _extract_requirements_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        从state中提取需求分析结果

        🆕 v7.180: 用于指导搜索的需求分析上下文

        Args:
            state: ProjectAnalysisState

        Returns:
            需求分析上下文字典
        """
        structured_requirements = state.get("structured_requirements", {})

        # 提取结构化输出
        structured_output = structured_requirements.get("structured_output", {})

        # 提取分析层
        analysis_layers = structured_requirements.get("analysis_layers", {})

        return {
            "structured_requirements": structured_requirements,
            "core_tension": (
                structured_output.get("design_challenge", "") or analysis_layers.get("L3_core_tension", "")
            ),
            "project_task": (structured_output.get("project_task", "") or analysis_layers.get("L4_project_task", "")),
            "emotional_landscape": structured_output.get("emotional_landscape", ""),
            "spiritual_aspirations": structured_output.get("spiritual_aspirations", ""),
            "psychological_safety_needs": structured_output.get("psychological_safety_needs", ""),
            "ritual_behaviors": structured_output.get("ritual_behaviors", ""),
            "memory_anchors": structured_output.get("memory_anchors", ""),
            "user_model": analysis_layers.get("L2_user_model", {}),
            "design_challenge": structured_output.get("design_challenge", ""),
            "project_type": state.get("project_type", ""),
        }

    def _build_enhanced_queries(self, requirements_context: Dict[str, Any], domain: str) -> List[str]:
        """
        基于需求分析上下文构建增强查询

        🆕 v7.180: 使用JTBD和核心矛盾构建精准搜索词

        Args:
            requirements_context: 需求分析上下文
            domain: 领域

        Returns:
            增强查询列表
        """
        try:
            from ..tools.query_builder import JTBDQueryBuilder

            builder = JTBDQueryBuilder()

            # 构建需求分析结果字典
            structured_requirements = {
                "project_task": requirements_context.get("project_task", ""),
                "core_tension": requirements_context.get("core_tension", ""),
                "design_challenge": requirements_context.get("design_challenge", ""),
                "emotional_landscape": requirements_context.get("emotional_landscape", ""),
                "spiritual_aspirations": requirements_context.get("spiritual_aspirations", ""),
                "psychological_safety_needs": requirements_context.get("psychological_safety_needs", ""),
                "ritual_behaviors": requirements_context.get("ritual_behaviors", ""),
                "memory_anchors": requirements_context.get("memory_anchors", ""),
                "analysis_layers": {
                    "L2_user_model": requirements_context.get("user_model", {}),
                    "L3_core_tension": requirements_context.get("core_tension", ""),
                },
            }

            # 使用JTBD查询构建器
            queries_dict = builder.build_from_requirements(structured_requirements, domain)
            return queries_dict.get("all_queries", [])

        except ImportError as e:
            logger.warning(f"⚠️ JTBDQueryBuilder not available: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Failed to build enhanced queries: {e}")
            return []


# 全局单例
_orchestrator: Optional[SearchOrchestrator] = None


def get_search_orchestrator() -> SearchOrchestrator:
    """获取全局搜索编排器实例"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SearchOrchestrator()
    return _orchestrator


# 便捷函数
def orchestrated_search(query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    执行编排搜索（便捷函数）

    Args:
        query: 搜索查询
        context: 上下文信息

    Returns:
        结构化搜索结果
    """
    orchestrator = get_search_orchestrator()
    return orchestrator.orchestrate(query, context)
