"""
工具工厂模块 - 2025年工厂模式

提供统一的工具实例创建接口,支持配置注入
"""

from typing import Optional

from loguru import logger

from intelligent_project_analyzer.settings import BochaConfig, MilvusConfig, SerperConfig, TavilyConfig, settings

# Note: RagflowConfig 已废弃 (v7.141)


class ToolFactory:
    """
    工具工厂 - 2025年配置注入模式

    优势:
    - 统一的工具创建接口
    - 配置外部化
    - 易于测试
    - 避免硬编码
    """

    @staticmethod
    def create_tavily_tool(config: Optional[TavilyConfig] = None):
        """
        创建Tavily搜索工具

        Args:
            config: Tavily配置,如果为None则使用全局settings

        Returns:
            LangChain StructuredTool实例
        """
        from intelligent_project_analyzer.core.types import ToolConfig
        from intelligent_project_analyzer.tools.tavily_search import TavilySearchTool

        cfg = config or settings.tavily

        logger.info(f"创建Tavily工具: max_results={cfg.max_results}, depth={cfg.search_depth}")

        #  v7.63.1: TavilySearchTool只接受api_key和config参数
        tool_config = ToolConfig(name="tavily_search")

        tool_instance = TavilySearchTool(api_key=cfg.api_key, config=tool_config)

        #  v7.120: 包装为 LangChain Tool 以兼容 bind_tools()
        langchain_tool = tool_instance.to_langchain_tool()
        logger.info(f" Tavily工具已包装为 LangChain Tool: {langchain_tool.name}")
        return langchain_tool

    @staticmethod
    def create_serper_tool(config: Optional[SerperConfig] = None):
        """
        创建Serper搜索工具 (v7.130+)

        Args:
            config: Serper配置,如果为None则使用全局settings

        Returns:
            LangChain StructuredTool实例
        """
        from intelligent_project_analyzer.core.types import ToolConfig
        from intelligent_project_analyzer.tools.serper_search import SerperSearchTool

        cfg = config or settings.serper

        if not cfg.enabled:
            logger.warning("️ Serper搜索未启用")
            return None

        if not cfg.api_key or cfg.api_key == "":
            logger.warning("️ Serper API密钥未配置")
            return None

        logger.info(f"创建Serper工具: num={cfg.default_num}, gl={cfg.default_gl}, hl={cfg.default_hl}")

        tool_config = ToolConfig(name="serper_search")
        tool_instance = SerperSearchTool(api_key=cfg.api_key, config=tool_config)

        # 包装为 LangChain Tool 以兼容 bind_tools()
        langchain_tool = tool_instance.to_langchain_tool()
        logger.info(f" Serper工具已包装为 LangChain Tool: {langchain_tool.name}")
        return langchain_tool

    # ==================== RAGFlow 已废弃 (v7.141) ====================
    # @staticmethod
    # def create_ragflow_tool(config: Optional[RagflowConfig] = None):
    #     """创建Ragflow知识库工具 (已废弃，请使用 create_milvus_tool)"""
    #     logger.error(" RAGFlow 已废弃，请使用 Milvus 向量数据库")
    #     raise NotImplementedError("RAGFlow 已被 Milvus 替代，请使用 create_milvus_tool()")

    @staticmethod
    def create_milvus_tool(config: Optional["MilvusConfig"] = None):
        """
        创建 Milvus 向量数据库知识库工具 (v7.141+)

        Args:
            config: Milvus 配置，如果为 None 则使用全局 settings

        Returns:
            LangChain StructuredTool 实例
        """
        from intelligent_project_analyzer.core.types import ToolConfig
        from intelligent_project_analyzer.tools.milvus_kb import MilvusKBTool

        cfg = config or settings.milvus

        if not cfg.enabled:
            logger.warning("️ Milvus 知识库未启用")
            # 注意：不再后备到 RAGFlow，直接返回 None 或抛出异常
            raise RuntimeError("Milvus 知识库未启用，且 RAGFlow 已废弃。请启用 Milvus 或检查配置。")

        logger.info(f"创建 Milvus 工具: host={cfg.host}, port={cfg.port}, collection={cfg.collection_name}")

        tool_config = ToolConfig(name="milvus_kb")

        tool_instance = MilvusKBTool(
            host=cfg.host,
            port=cfg.port,
            collection_name=cfg.collection_name,
            embedding_model_name=cfg.embedding_model,
            reranker_model_name=cfg.reranker_model,
            config=tool_config,
        )

        # 包装为 LangChain Tool
        langchain_tool = tool_instance.to_langchain_tool()
        logger.info(f" Milvus 工具已包装为 LangChain Tool: {langchain_tool.name}")
        return langchain_tool

    @staticmethod
    def create_bocha_tool(config: Optional[BochaConfig] = None):
        """
        创建博查搜索工具

        Args:
            config: 博查配置，如果为None则使用全局settings

        Returns:
            LangChain StructuredTool实例（而非原始BochaSearchTool）
        """
        from intelligent_project_analyzer.agents.bocha_search_tool import create_bocha_search_tool_from_settings

        cfg = config or settings.bocha

        if not cfg.enabled:
            logger.warning("️ 博查搜索未启用")
            return None

        if not cfg.api_key or cfg.api_key == "your_bocha_api_key_here":
            logger.warning("️ 博查API密钥未配置")
            return None

        logger.info(f" 创建博查搜索工具: count={cfg.default_count}")

        tool_instance = create_bocha_search_tool_from_settings()
        if tool_instance:
            #  v7.120: 包装为 LangChain Tool 以兼容 bind_tools()
            langchain_tool = tool_instance.to_langchain_tool()
            logger.info(f" 博查工具已包装为 LangChain Tool: {langchain_tool.name}")
            return langchain_tool
        return None

    @staticmethod
    def create_arxiv_tool():
        """
        创建Arxiv搜索工具

        Returns:
            LangChain StructuredTool实例
        """
        from intelligent_project_analyzer.core.types import ToolConfig
        from intelligent_project_analyzer.tools.arxiv_search import ArxivSearchTool

        logger.info("创建Arxiv工具")

        #  v7.63.1: ArxivSearchTool只接受config参数(不接受timeout)
        tool_config = ToolConfig(name="arxiv_search")

        tool_instance = ArxivSearchTool(config=tool_config)

        #  v7.120: 包装为 LangChain Tool 以兼容 bind_tools()
        langchain_tool = tool_instance.to_langchain_tool()
        logger.info(f" Arxiv工具已包装为 LangChain Tool: {langchain_tool.name}")
        return langchain_tool

    @staticmethod
    def create_all_tools():
        """
        创建所有可用的工具

        Returns:
            工具字典 {tool_name: tool_instance}
        """
        tools = {}

        #  v7.63: 添加博查搜索
        try:
            if settings.bocha.enabled:
                bocha_tool = ToolFactory.create_bocha_tool()
                if bocha_tool:
                    tools["bocha"] = bocha_tool
                    logger.info(" 博查搜索工具已启用")
                else:
                    logger.error(" 博查工具创建返回None（API密钥无效或配置错误）")
                    logger.error(f"   请检查: BOCHA_API_KEY={settings.bocha.api_key[:10]}...")
            else:
                logger.info("ℹ️ 博查搜索已禁用（BOCHA_ENABLED=false）")
        except Exception as e:
            logger.error(f" 博查工具创建失败: {e}", exc_info=True)
            logger.error("   请检查: 1) API密钥是否有效 2) 网络连接是否正常 3) api.bochaai.com是否可访问")

        #  v7.130+: Serper搜索
        try:
            if settings.serper.enabled and settings.serper.api_key:
                serper_tool = ToolFactory.create_serper_tool()
                if serper_tool:
                    tools["serper"] = serper_tool
                    logger.info(" Serper搜索工具已启用")
        except Exception as e:
            logger.warning(f"️ Serper工具创建失败: {e}")

        # Tavily搜索
        try:
            if settings.tavily.api_key:
                tools["tavily"] = ToolFactory.create_tavily_tool()
                logger.info(" Tavily工具已启用")
        except Exception as e:
            logger.warning(f"️ Tavily工具创建失败: {e}")

        #  v7.141: Ragflow知识库已废弃，已被 Milvus 替代
        # try:
        #     if settings.ragflow.api_key:
        #         tools["ragflow"] = ToolFactory.create_ragflow_tool()
        #         logger.info(" Ragflow工具已启用 (备选方案)")
        # except Exception as e:
        #     logger.warning(f"️ Ragflow工具创建失败: {e}")

        #  v7.141: Milvus向量数据库知识库 (替代 RAGFlow)
        try:
            if settings.milvus.enabled:
                tools["milvus"] = ToolFactory.create_milvus_tool()
                logger.info(" Milvus知识库工具已启用 (6-Stage Deep Pipeline)")
        except Exception as e:
            logger.warning(f"️ Milvus工具创建失败: {e}")

        # Arxiv搜索
        try:
            if settings.arxiv.enabled:
                tools["arxiv"] = ToolFactory.create_arxiv_tool()
                logger.info(" Arxiv工具已启用")
        except Exception as e:
            logger.warning(f"️ Arxiv工具创建失败: {e}")

        logger.info(f"工具初始化完成: {len(tools)}个工具可用")
        return tools

    @staticmethod
    def validate_tool_config(tool_name: str) -> bool:
        """
        验证工具配置

        Args:
            tool_name: 工具名称 (tavily/milvus/arxiv/bocha/serper)

        Returns:
            配置是否有效
        """
        if tool_name == "tavily":
            if not settings.tavily.api_key:
                logger.error("Tavily配置无效: 缺少API Key")
                return False
            return True

        elif tool_name == "ragflow":
            logger.error(" RAGFlow 已废弃 (v7.141)，请使用 'milvus'")
            return False

        elif tool_name == "milvus":
            if not settings.milvus.enabled:
                logger.error("Milvus配置无效: 未启用")
                return False
            return True

        elif tool_name == "arxiv":
            return settings.arxiv.enabled

        else:
            logger.error(f"未知的工具名称: {tool_name}")
            return False
