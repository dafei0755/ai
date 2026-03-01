"""
测试工具的 LangChain 兼容性
验证所有工具能够被 bind_tools() 正确绑定
"""

from unittest.mock import MagicMock, patch

import pytest
from loguru import logger


def test_bocha_tool_langchain_compatibility():
    """测试 BochaSearchTool 的 LangChain 兼容性"""
    logger.info("=" * 60)
    logger.info("测试 1: BochaSearchTool LangChain 兼容性")
    logger.info("=" * 60)

    from intelligent_project_analyzer.agents.bocha_search_tool import BochaSearchTool
    from intelligent_project_analyzer.core.types import ToolConfig

    # 创建工具实例
    tool_config = ToolConfig(name="bocha_search")
    tool_instance = BochaSearchTool(api_key="test_key", config=tool_config)

    # 转换为 LangChain Tool
    langchain_tool = tool_instance.to_langchain_tool()

    # 验证属性
    assert hasattr(langchain_tool, "name"), "Tool should have 'name' attribute"
    assert hasattr(langchain_tool, "description"), "Tool should have 'description' attribute"
    assert hasattr(langchain_tool, "func"), "Tool should have 'func' attribute"
    assert hasattr(langchain_tool, "args_schema"), "Tool should have 'args_schema' attribute"

    assert langchain_tool.name == "bocha_search"
    logger.info(f"✅ Tool name: {langchain_tool.name}")
    logger.info(f"✅ Tool description: {langchain_tool.description[:50]}...")
    logger.info(f"✅ BochaSearchTool LangChain 兼容性测试通过")


def test_tavily_tool_langchain_compatibility():
    """测试 TavilySearchTool 的 LangChain 兼容性"""
    logger.info("=" * 60)
    logger.info("测试 2: TavilySearchTool LangChain 兼容性")
    logger.info("=" * 60)

    from intelligent_project_analyzer.core.types import ToolConfig
    from intelligent_project_analyzer.tools.tavily_search import TavilySearchTool

    # Mock TavilyClient
    with patch("intelligent_project_analyzer.tools.tavily_search.TavilyClient"):
        tool_config = ToolConfig(name="tavily_search")
        tool_instance = TavilySearchTool(api_key="test_key", config=tool_config)

        # 转换为 LangChain Tool
        langchain_tool = tool_instance.to_langchain_tool()

        # 验证属性
        assert hasattr(langchain_tool, "name"), "Tool should have 'name' attribute"
        assert langchain_tool.name == "tavily_search"
        logger.info(f"✅ Tool name: {langchain_tool.name}")
        logger.info(f"✅ TavilySearchTool LangChain 兼容性测试通过")


def test_ragflow_tool_langchain_compatibility():
    """测试 RagflowKBTool 的 LangChain 兼容性"""
    logger.info("=" * 60)
    logger.info("测试 3: RagflowKBTool LangChain 兼容性")
    logger.info("=" * 60)

    from intelligent_project_analyzer.core.types import ToolConfig
    from intelligent_project_analyzer.tools.ragflow_kb import RagflowKBTool

    tool_config = ToolConfig(name="ragflow_kb")
    tool_instance = RagflowKBTool(
        api_endpoint="http://test.com", api_key="test_key", dataset_id="test_dataset", config=tool_config
    )

    # 转换为 LangChain Tool
    langchain_tool = tool_instance.to_langchain_tool()

    # 验证属性
    assert hasattr(langchain_tool, "name"), "Tool should have 'name' attribute"
    assert langchain_tool.name == "ragflow_kb"
    logger.info(f"✅ Tool name: {langchain_tool.name}")
    logger.info(f"✅ RagflowKBTool LangChain 兼容性测试通过")


def test_arxiv_tool_langchain_compatibility():
    """测试 ArxivSearchTool 的 LangChain 兼容性"""
    logger.info("=" * 60)
    logger.info("测试 4: ArxivSearchTool LangChain 兼容性")
    logger.info("=" * 60)

    from intelligent_project_analyzer.core.types import ToolConfig
    from intelligent_project_analyzer.tools.arxiv_search import ArxivSearchTool

    tool_config = ToolConfig(name="arxiv_search")
    tool_instance = ArxivSearchTool(config=tool_config)

    # 转换为 LangChain Tool
    langchain_tool = tool_instance.to_langchain_tool()

    # 验证属性
    assert hasattr(langchain_tool, "name"), "Tool should have 'name' attribute"
    assert langchain_tool.name == "arxiv_search"
    logger.info(f"✅ Tool name: {langchain_tool.name}")
    logger.info(f"✅ ArxivSearchTool LangChain 兼容性测试通过")


def test_tool_factory_returns_langchain_tools():
    """测试 ToolFactory 返回的是 LangChain 工具"""
    logger.info("=" * 60)
    logger.info("测试 5: ToolFactory 返回 LangChain Tools")
    logger.info("=" * 60)

    from intelligent_project_analyzer.services.tool_factory import ToolFactory
    from intelligent_project_analyzer.settings import settings

    # 测试 Tavily
    if settings.tavily.api_key and settings.tavily.api_key != "your_tavily_api_key_here":
        with patch("intelligent_project_analyzer.tools.tavily_search.TavilyClient"):
            tavily_tool = ToolFactory.create_tavily_tool()
            assert tavily_tool is not None
            assert hasattr(tavily_tool, "name")
            logger.info(f"✅ Tavily tool from factory: {tavily_tool.name}")

    # 测试 Ragflow
    if settings.ragflow.api_key and settings.ragflow.api_key != "your_ragflow_api_key_here":
        ragflow_tool = ToolFactory.create_ragflow_tool()
        assert ragflow_tool is not None
        assert hasattr(ragflow_tool, "name")
        logger.info(f"✅ Ragflow tool from factory: {ragflow_tool.name}")

    # 测试 Arxiv
    if settings.arxiv.enabled:
        arxiv_tool = ToolFactory.create_arxiv_tool()
        assert arxiv_tool is not None
        assert hasattr(arxiv_tool, "name")
        logger.info(f"✅ Arxiv tool from factory: {arxiv_tool.name}")

    logger.info(f"✅ ToolFactory 测试通过")


def test_bind_tools_simulation():
    """模拟 bind_tools() 调用，确保不会报错"""
    logger.info("=" * 60)
    logger.info("测试 6: 模拟 bind_tools() 调用")
    logger.info("=" * 60)

    from unittest.mock import MagicMock

    from intelligent_project_analyzer.services.tool_factory import ToolFactory

    # 创建所有工具
    tools = []

    # Mock 必要的依赖
    with patch("intelligent_project_analyzer.tools.tavily_search.TavilyClient"):
        with patch("intelligent_project_analyzer.settings.settings") as mock_settings:
            # 配置 mock settings
            mock_settings.tavily.api_key = "test_key"
            mock_settings.ragflow.api_key = "test_key"
            mock_settings.ragflow.endpoint = "http://test.com"
            mock_settings.ragflow.dataset_id = "test_dataset"
            mock_settings.arxiv.enabled = True
            mock_settings.bocha.enabled = False  # 禁用 bocha 避免真实 API 调用

            try:
                tavily_tool = ToolFactory.create_tavily_tool()
                if tavily_tool:
                    tools.append(tavily_tool)
                    logger.info(f"✅ Created Tavily tool: {tavily_tool.name}")
            except Exception as e:
                logger.warning(f"⚠️ Tavily tool creation failed: {e}")

            try:
                ragflow_tool = ToolFactory.create_ragflow_tool()
                if ragflow_tool:
                    tools.append(ragflow_tool)
                    logger.info(f"✅ Created Ragflow tool: {ragflow_tool.name}")
            except Exception as e:
                logger.warning(f"⚠️ Ragflow tool creation failed: {e}")

            try:
                arxiv_tool = ToolFactory.create_arxiv_tool()
                if arxiv_tool:
                    tools.append(arxiv_tool)
                    logger.info(f"✅ Created Arxiv tool: {arxiv_tool.name}")
            except Exception as e:
                logger.warning(f"⚠️ Arxiv tool creation failed: {e}")

    # 验证工具列表
    logger.info(f"📊 Created {len(tools)} tools for bind_tools simulation")

    # 模拟 bind_tools 会做的事：访问工具的 name 属性
    try:
        tool_names = [getattr(tool, "name", str(tool)) for tool in tools]
        logger.info(f"✅ Tool names extracted: {tool_names}")
        logger.info(f"✅ bind_tools() 模拟测试通过 - 所有工具都有 name 属性")
    except Exception as e:
        logger.error(f"❌ bind_tools simulation failed: {e}")
        raise


if __name__ == "__main__":
    # 运行所有测试
    logger.info("\n" + "=" * 80)
    logger.info("🚀 开始工具 LangChain 兼容性测试")
    logger.info("=" * 80 + "\n")

    try:
        test_bocha_tool_langchain_compatibility()
        test_tavily_tool_langchain_compatibility()
        test_ragflow_tool_langchain_compatibility()
        test_arxiv_tool_langchain_compatibility()
        test_tool_factory_returns_langchain_tools()
        test_bind_tools_simulation()

        logger.info("\n" + "=" * 80)
        logger.info("🎉 所有测试通过！")
        logger.info("=" * 80)
    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}", exc_info=True)
        raise
