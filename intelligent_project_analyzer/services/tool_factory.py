"""
工具工厂模块 - 2025年工厂模式

提供统一的工具实例创建接口,支持配置注入
"""

from typing import Optional
from loguru import logger

from intelligent_project_analyzer.settings import settings, TavilyConfig, RagflowConfig


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
            TavilySearchTool实例
            
        Example:
            # 使用默认配置
            tool = ToolFactory.create_tavily_tool()
            
            # 使用自定义配置
            custom_config = TavilyConfig(
                api_key="...",
                max_results=10,
                search_depth="advanced"
            )
            tool = ToolFactory.create_tavily_tool(config=custom_config)
        """
        from intelligent_project_analyzer.tools.tavily_search import TavilySearchTool
        
        cfg = config or settings.tavily
        
        logger.info(f"创建Tavily工具: max_results={cfg.max_results}, depth={cfg.search_depth}")
        
        return TavilySearchTool(
            api_key=cfg.api_key,
            max_results=cfg.max_results,
            search_depth=cfg.search_depth,
            timeout=cfg.timeout
        )
    
    @staticmethod
    def create_ragflow_tool(config: Optional[RagflowConfig] = None):
        """
        创建Ragflow知识库工具
        
        Args:
            config: Ragflow配置,如果为None则使用全局settings
            
        Returns:
            RagflowKBTool实例
        """
        from intelligent_project_analyzer.tools.ragflow_kb import RagflowKBTool
        
        cfg = config or settings.ragflow
        
        logger.info(f"创建Ragflow工具: endpoint={cfg.endpoint}")
        
        return RagflowKBTool(
            api_key=cfg.api_key,
            endpoint=cfg.endpoint,
            dataset_id=cfg.dataset_id,
            timeout=cfg.timeout
        )
    
    @staticmethod
    def create_arxiv_tool():
        """
        创建Arxiv搜索工具
        
        Returns:
            ArxivSearchTool实例
        """
        from intelligent_project_analyzer.tools.arxiv_search import ArxivSearchTool
        
        logger.info("创建Arxiv工具")
        
        return ArxivSearchTool(
            timeout=settings.arxiv.timeout
        )
    
    @staticmethod
    def create_all_tools():
        """
        创建所有可用的工具
        
        Returns:
            工具字典 {tool_name: tool_instance}
        """
        tools = {}
        
        # Tavily搜索
        try:
            if settings.tavily.api_key:
                tools["tavily"] = ToolFactory.create_tavily_tool()
                logger.info("✅ Tavily工具已启用")
        except Exception as e:
            logger.warning(f"⚠️ Tavily工具创建失败: {e}")
        
        # Ragflow知识库
        try:
            if settings.ragflow.api_key:
                tools["ragflow"] = ToolFactory.create_ragflow_tool()
                logger.info("✅ Ragflow工具已启用")
        except Exception as e:
            logger.warning(f"⚠️ Ragflow工具创建失败: {e}")
        
        # Arxiv搜索
        try:
            if settings.arxiv.enabled:
                tools["arxiv"] = ToolFactory.create_arxiv_tool()
                logger.info("✅ Arxiv工具已启用")
        except Exception as e:
            logger.warning(f"⚠️ Arxiv工具创建失败: {e}")
        
        logger.info(f"工具初始化完成: {len(tools)}个工具可用")
        return tools
    
    @staticmethod
    def validate_tool_config(tool_name: str) -> bool:
        """
        验证工具配置
        
        Args:
            tool_name: 工具名称 (tavily/ragflow/arxiv)
            
        Returns:
            配置是否有效
        """
        if tool_name == "tavily":
            if not settings.tavily.api_key:
                logger.error("Tavily配置无效: 缺少API Key")
                return False
            return True
        
        elif tool_name == "ragflow":
            if not settings.ragflow.api_key:
                logger.error("Ragflow配置无效: 缺少API Key")
                return False
            if not settings.ragflow.endpoint:
                logger.error("Ragflow配置无效: 缺少Endpoint")
                return False
            return True
        
        elif tool_name == "arxiv":
            return settings.arxiv.enabled
        
        else:
            logger.error(f"未知的工具名称: {tool_name}")
            return False

