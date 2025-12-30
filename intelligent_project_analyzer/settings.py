"""
统一配置管理 - 基于Pydantic Settings 2.x (2025年标准)

使用Pydantic Settings自动加载环境变量,无需手动调用load_dotenv()
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum
from typing import Optional
from dotenv import load_dotenv

# 确保.env文件被加载到环境变量中
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)


class Environment(str, Enum):
    """环境类型"""
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class LLMConfig(BaseModel):
    """LLM配置 - 单一真实来源"""
    provider: str = "openai"
    # model 从 .env 的 {PROVIDER}_MODEL 读取,此处仅为后备默认值
    model: str = Field(default="gpt-4.1", description="默认LLM模型")
    max_tokens: int = Field(default=4000, description="最大token数", alias="MAX_TOKENS")
    timeout: int = Field(default=60, description="请求超时时间(秒)", alias="LLM_TIMEOUT")
    temperature: float = Field(default=0.7, description="温度参数", alias="TEMPERATURE")
    api_key: str = Field(default="", description="LLM API密钥", alias="OPENAI_API_KEY")
    api_base: Optional[str] = Field(default=None, description="自定义API Base URL")
    # 重试配置
    max_retries: int = Field(default=3, description="LLM调用失败重试次数", alias="MAX_RETRIES")
    retry_delay: int = Field(default=5, description="重试间隔(秒)", alias="RETRY_DELAY")

    model_config = {"populate_by_name": True}  # 允许使用别名


class TavilyConfig(BaseModel):
    """Tavily搜索工具配置"""
    api_key: str = Field(default="", description="Tavily API密钥", alias="TAVILY_API_KEY")
    max_results: int = Field(default=5, description="最大搜索结果数")
    search_depth: str = Field(default="basic", description="搜索深度: basic/advanced")
    timeout: int = Field(default=30, description="请求超时时间(秒)")

    model_config = {"populate_by_name": True}


class RagflowConfig(BaseModel):
    """Ragflow知识库配置"""
    endpoint: str = Field(default="http://localhost:9380", description="Ragflow服务端点", alias="RAGFLOW_ENDPOINT")
    api_key: str = Field(default="", description="Ragflow API密钥", alias="RAGFLOW_API_KEY")
    dataset_id: Optional[str] = Field(default=None, description="数据集ID", alias="RAGFLOW_DATASET_ID")
    timeout: int = Field(default=30, description="请求超时时间(秒)")

    model_config = {"populate_by_name": True}


class ArxivConfig(BaseModel):
    """Arxiv搜索配置"""
    enabled: bool = Field(default=True, description="是否启用Arxiv搜索")
    timeout: int = Field(default=30, description="请求超时时间(秒)")


class BochaConfig(BaseModel):
    """博查搜索配置 (v7.63+)"""
    enabled: bool = Field(default=False, description="是否启用博查搜索", alias="BOCHA_ENABLED")
    api_key: str = Field(default="", description="博查API密钥", alias="BOCHA_API_KEY")
    base_url: str = Field(default="https://api.bocha.cn", description="博查API地址", alias="BOCHA_BASE_URL")
    default_count: int = Field(default=5, description="默认搜索结果数量", alias="BOCHA_DEFAULT_COUNT")
    timeout: int = Field(default=30, description="请求超时时间(秒)", alias="BOCHA_TIMEOUT")
    freshness: str = Field(default="oneYear", description="搜索结果时效性", alias="BOCHA_FRESHNESS")

    model_config = {"populate_by_name": True}


class ImageGenerationConfig(BaseModel):
    """
    AI 图像生成配置 (v7.38+)
    
    通过 OpenRouter 调用 Gemini 3 Pro 图像生成 (Nano Banana Pro)
    价格: $2/M input, $12/M output
    """
    enabled: bool = Field(default=False, description="是否启用 AI 概念图生成", alias="IMAGE_GENERATION_ENABLED")
    model: str = Field(
        default="google/gemini-3-pro-image-preview",
        description="图像生成模型（OpenRouter 格式）",
        alias="IMAGE_GENERATION_MODEL"
    )
    max_images_per_report: int = Field(
        default=2, 
        description="每个专家报告最多生成几张概念图",
        alias="IMAGE_GENERATION_MAX_IMAGES_PER_REPORT"
    )
    timeout: int = Field(
        default=120, 
        description="图像生成超时时间(秒)",
        alias="IMAGE_GENERATION_TIMEOUT"
    )
    
    # 🔥 v7.61: Vision 图像分析配置
    vision_enabled: bool = Field(
        default=False,
        description="是否启用 Vision 模型分析参考图",
        alias="VISION_ANALYSIS_ENABLED"
    )
    vision_provider: str = Field(
        default="openai-openrouter",
        description="Vision 模型提供商 (openai-openrouter|gemini-openrouter|openai)",
        alias="VISION_MODEL_PROVIDER"
    )
    vision_model: str = Field(
        default="openai/gpt-4o",
        description="Vision 模型名称",
        alias="VISION_MODEL"
    )
    vision_timeout: int = Field(
        default=30,
        description="Vision 分析超时时间(秒)",
        alias="VISION_ANALYSIS_TIMEOUT"
    )
    vision_max_tokens: int = Field(
        default=500,
        description="Vision 分析最大 token 数",
        alias="VISION_ANALYSIS_MAX_TOKENS"
    )
    
    # 使用 OpenRouter API Key (复用现有配置)
    # api_key 从 OPENROUTER_API_KEY 读取
    
    model_config = {"populate_by_name": True}


class InpaintingConfig(BaseModel):
    """
    AI 图像编辑（Inpainting）配置 (v7.62+)
    
    通过 OpenAI DALL-E 2 Edit API 实现像素级精确图像编辑
    要求: 原图 + Mask（黑色=保留，透明=编辑） + 提示词
    价格: $0.020 / 图像
    """
    enabled: bool = Field(
        default=False,
        description="是否启用 Inpainting 图像编辑",
        alias="INPAINTING_ENABLED"
    )
    provider: str = Field(
        default="openai",
        description="Inpainting 提供商（当前仅支持 openai）",
        alias="INPAINTING_PROVIDER"
    )
    model: str = Field(
        default="dall-e-2",
        description="Inpainting 模型（DALL-E 2 Edit API）",
        alias="INPAINTING_MODEL"
    )
    timeout: int = Field(
        default=120,
        description="Inpainting 超时时间(秒)",
        alias="INPAINTING_TIMEOUT"
    )
    
    # OpenAI API Key 从 OPENAI_API_KEY 环境变量读取（独立于 OpenRouter）
    
    model_config = {"populate_by_name": True}


class StorageConfig(BaseModel):
    """文件存储配置"""
    upload_dir: str = Field(default="./data/uploads", description="上传目录", alias="UPLOAD_DIR")
    output_dir: str = Field(default="./data/outputs", description="输出目录", alias="OUTPUT_DIR")
    temp_dir: str = Field(default="./data/temp", description="临时目录", alias="TEMP_DIR")
    database_url: str = Field(default="sqlite:///./data/project_analyzer.db", description="数据库URL", alias="DATABASE_URL")

    model_config = {"populate_by_name": True}


class ConcurrencyConfig(BaseModel):
    """并发配置"""
    max_concurrent_agents: int = Field(default=6, description="最大并发智能体数", alias="MAX_CONCURRENT_AGENTS")
    agent_timeout: int = Field(default=300, description="智能体超时时间(秒)", alias="AGENT_TIMEOUT")

    model_config = {"populate_by_name": True}


class Settings(BaseSettings):
    """
    全局配置 - 2025年标准

    使用Pydantic Settings自动从环境变量加载配置
    支持嵌套配置: LLM__MAX_TOKENS=8000
    """

    # 环境配置
    environment: Environment = Field(default=Environment.DEV, description="运行环境")
    debug: bool = Field(default=False, description="调试模式", alias="DEBUG")
    log_level: str = Field(default="INFO", description="日志级别", alias="LOG_LEVEL")

    # 应用配置
    app_name: str = Field(default="Intelligent Project Analyzer", description="应用名称", alias="APP_NAME")
    app_version: str = Field(default="2.0.0", description="应用版本", alias="APP_VERSION")
    post_completion_followup_enabled: bool = Field(
        default=True,
        description="报告生成后是否自动触发追问交互"
    )

    # LLM配置 (嵌套) - ✅ 提供默认值
    llm: LLMConfig = Field(default_factory=LLMConfig)

    # 工具配置 (嵌套) - ✅ 提供默认值
    tavily: TavilyConfig = Field(default_factory=TavilyConfig)
    ragflow: RagflowConfig = Field(default_factory=RagflowConfig)
    arxiv: ArxivConfig = Field(default_factory=ArxivConfig)
    bocha: BochaConfig = Field(default_factory=BochaConfig)  # 🆕 v7.63: 博查搜索
    
    # 🆕 v7.38: AI 图像生成配置
    image_generation: ImageGenerationConfig = Field(default_factory=ImageGenerationConfig)
    
    # 🆕 v7.62: AI 图像编辑（Inpainting）配置
    inpainting: InpaintingConfig = Field(default_factory=InpaintingConfig)

    # 存储配置
    storage: StorageConfig = Field(default_factory=StorageConfig)

    # 并发配置
    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig)

    # 数据库配置
    database_url: str = Field(default="sqlite:///./data/project_analyzer.db", description="数据库URL", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL", alias="REDIS_URL")

    # 前端配置
    api_base_url: str = Field(default="http://localhost:8000", description="API服务地址")
    streamlit_port: int = Field(default=8501, description="Streamlit端口", alias="STREAMLIT_PORT")
    streamlit_host: str = Field(default="localhost", description="Streamlit主机", alias="STREAMLIT_HOST")

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_nested_delimiter='__',  # 支持 LLM__MAX_TOKENS=8000
        case_sensitive=False,
        extra='ignore'  # 忽略未定义的环境变量
    )

    @model_validator(mode='after')
    def load_from_flat_env(self):
        """从扁平环境变量加载配置(兼容旧.env格式)"""
        # 读取LLM配置 - 根据提供商选择正确的API Key
        provider = os.getenv('LLM_PROVIDER', 'openai').lower()

        if provider == 'openrouter':
            # OpenRouter: 优先使用 OPENROUTER_API_KEY
            if not self.llm.api_key and os.getenv('OPENROUTER_API_KEY'):
                self.llm.api_key = os.getenv('OPENROUTER_API_KEY', '')
        elif provider == 'deepseek':
            # DeepSeek
            if not self.llm.api_key and os.getenv('DEEPSEEK_API_KEY'):
                self.llm.api_key = os.getenv('DEEPSEEK_API_KEY', '')
        elif provider == 'qwen':
            # Qwen
            if not self.llm.api_key and os.getenv('QWEN_API_KEY'):
                self.llm.api_key = os.getenv('QWEN_API_KEY', '')
        else:
            # OpenAI (默认)
            if not self.llm.api_key and os.getenv('OPENAI_API_KEY'):
                self.llm.api_key = os.getenv('OPENAI_API_KEY', '')

        # 🔄 兼容旧版 .env 字段 (最后的后备选项)
        if not self.llm.api_key and os.getenv('LLM_API_KEY'):
            self.llm.api_key = os.getenv('LLM_API_KEY', '')

        # 加载模型名称 - 根据提供商选择
        if provider == 'openrouter' and os.getenv('OPENROUTER_MODEL'):
            self.llm.model = os.getenv('OPENROUTER_MODEL', self.llm.model)
        elif provider == 'deepseek' and os.getenv('DEEPSEEK_MODEL'):
            self.llm.model = os.getenv('DEEPSEEK_MODEL', self.llm.model)
        elif provider == 'qwen' and os.getenv('QWEN_MODEL'):
            self.llm.model = os.getenv('QWEN_MODEL', self.llm.model)
        elif os.getenv('OPENAI_MODEL'):
            self.llm.model = os.getenv('OPENAI_MODEL', self.llm.model)
        elif os.getenv('LLM_MODEL_NAME'):
            self.llm.model = os.getenv('LLM_MODEL_NAME', self.llm.model)

        # 加载 Base URL - 根据提供商选择
        if provider == 'openrouter' and os.getenv('OPENROUTER_BASE_URL'):
            self.llm.api_base = os.getenv('OPENROUTER_BASE_URL', self.llm.api_base)
        elif provider == 'deepseek' and os.getenv('DEEPSEEK_BASE_URL'):
            self.llm.api_base = os.getenv('DEEPSEEK_BASE_URL', self.llm.api_base)
        elif provider == 'qwen' and os.getenv('QWEN_BASE_URL'):
            self.llm.api_base = os.getenv('QWEN_BASE_URL', self.llm.api_base)
        elif os.getenv('OPENAI_BASE_URL'):
            self.llm.api_base = os.getenv('OPENAI_BASE_URL', self.llm.api_base)
        elif os.getenv('LLM_BASE_URL'):
            self.llm.api_base = os.getenv('LLM_BASE_URL', self.llm.api_base)
        if os.getenv('MAX_TOKENS'):
            self.llm.max_tokens = int(os.getenv('MAX_TOKENS', self.llm.max_tokens))
        if os.getenv('LLM_TIMEOUT'):
            self.llm.timeout = int(os.getenv('LLM_TIMEOUT', self.llm.timeout))
        if os.getenv('TEMPERATURE'):
            self.llm.temperature = float(os.getenv('TEMPERATURE', self.llm.temperature))
        if os.getenv('MAX_RETRIES'):
            self.llm.max_retries = int(os.getenv('MAX_RETRIES', self.llm.max_retries))
        if os.getenv('RETRY_DELAY'):
            self.llm.retry_delay = int(os.getenv('RETRY_DELAY', self.llm.retry_delay))

        # 🆕 v7.38: 读取图像生成配置
        if os.getenv('IMAGE_GENERATION_ENABLED'):
            self.image_generation.enabled = os.getenv('IMAGE_GENERATION_ENABLED', 'false').lower() in ('true', '1', 'yes')
        if os.getenv('IMAGE_GENERATION_MODEL'):
            self.image_generation.model = os.getenv('IMAGE_GENERATION_MODEL', self.image_generation.model)
        if os.getenv('IMAGE_GENERATION_MAX_IMAGES_PER_REPORT'):
            self.image_generation.max_images_per_report = int(os.getenv('IMAGE_GENERATION_MAX_IMAGES_PER_REPORT', self.image_generation.max_images_per_report))
        if os.getenv('IMAGE_GENERATION_TIMEOUT'):
            self.image_generation.timeout = int(os.getenv('IMAGE_GENERATION_TIMEOUT', self.image_generation.timeout))

        # 🆕 v7.62: 读取 Inpainting 图像编辑配置
        if os.getenv('INPAINTING_ENABLED'):
            self.inpainting.enabled = os.getenv('INPAINTING_ENABLED', 'false').lower() in ('true', '1', 'yes')
        if os.getenv('INPAINTING_PROVIDER'):
            self.inpainting.provider = os.getenv('INPAINTING_PROVIDER', self.inpainting.provider)
        if os.getenv('INPAINTING_MODEL'):
            self.inpainting.model = os.getenv('INPAINTING_MODEL', self.inpainting.model)
        if os.getenv('INPAINTING_TIMEOUT'):
            self.inpainting.timeout = int(os.getenv('INPAINTING_TIMEOUT', self.inpainting.timeout))

        # 读取Tavily配置
        if not self.tavily.api_key and os.getenv('TAVILY_API_KEY'):
            self.tavily.api_key = os.getenv('TAVILY_API_KEY', '')

        # 读取Ragflow配置
        if not self.ragflow.api_key and os.getenv('RAGFLOW_API_KEY'):
            self.ragflow.api_key = os.getenv('RAGFLOW_API_KEY', '')
        if os.getenv('RAGFLOW_ENDPOINT'):
            self.ragflow.endpoint = os.getenv('RAGFLOW_ENDPOINT', self.ragflow.endpoint)
        if os.getenv('RAGFLOW_DATASET_ID'):
            self.ragflow.dataset_id = os.getenv('RAGFLOW_DATASET_ID')

        # 🆕 v7.63: 读取博查配置
        if os.getenv('BOCHA_ENABLED'):
            self.bocha.enabled = os.getenv('BOCHA_ENABLED', 'false').lower() in ('true', '1', 'yes')
        if not self.bocha.api_key and os.getenv('BOCHA_API_KEY'):
            self.bocha.api_key = os.getenv('BOCHA_API_KEY', '')
        if os.getenv('BOCHA_BASE_URL'):
            self.bocha.base_url = os.getenv('BOCHA_BASE_URL', self.bocha.base_url)
        if os.getenv('BOCHA_DEFAULT_COUNT'):
            self.bocha.default_count = int(os.getenv('BOCHA_DEFAULT_COUNT', self.bocha.default_count))

        return self
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == Environment.PROD
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment == Environment.DEV


# 全局配置实例 - 单例模式
settings = Settings()

