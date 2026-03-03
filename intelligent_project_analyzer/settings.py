"""
统一配置管理 - 基于Pydantic Settings 2.x (2025年标准)

使用Pydantic Settings自动加载环境变量,无需手动调用load_dotenv()

多环境配置支持 (v8.1+):
    - 通过 APP_ENV 环境变量指定环境 (development/test/production)
    - 优先级: 环境变量 > .env.{APP_ENV} > .env > 默认值
    - 示例: APP_ENV=test python run.py
"""

import os
from enum import Enum
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 多环境配置加载 (v8.1+)
# 1. 首先加载 .env（基础配置）
# 2. 然后根据 APP_ENV 加载环境特定配置（会覆盖同名变量）
# 3. 最后环境变量拥有最高优先级
root_path = Path(__file__).parent.parent
base_env_path = root_path / ".env"
if base_env_path.exists():
    load_dotenv(base_env_path)

# 根据 APP_ENV 加载环境特定配置
app_env = os.getenv("APP_ENV", "development").lower()
env_specific_path = root_path / f".env.{app_env}"
if env_specific_path.exists():
    # override=True: 环境特定配置覆盖基础配置
    load_dotenv(env_specific_path, override=True)


class Environment(str, Enum):
    """环境类型"""

    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"

    @classmethod
    def _missing_(cls, value):
        """支持常见别名"""
        aliases = {
            "development": cls.DEV,
            "develop": cls.DEV,
            "test": cls.STAGING,
            "testing": cls.STAGING,
            "production": cls.PROD,
        }
        return aliases.get(str(value).lower())


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


class SerperConfig(BaseModel):
    """Serper搜索工具配置 (v7.130+)"""

    enabled: bool = Field(default=False, description="是否启用Serper搜索（中国网络环境SSL不稳定，默认禁用）", alias="SERPER_ENABLED")
    api_key: str = Field(default="", description="Serper API密钥", alias="SERPER_API_KEY")
    default_num: int = Field(default=10, description="默认搜索结果数量")
    default_gl: str = Field(default="us", description="默认地理位置 (us/cn/uk等)")
    default_hl: str = Field(default="en", description="默认语言 (en/zh-cn等)")
    timeout: int = Field(default=30, description="请求超时时间(秒)")

    model_config = {"populate_by_name": True}


# ==================== RAGFlow 已废弃 (v7.141) ====================
# RAGFlow 知识库已被 Milvus 替代，相关代码已移至 archive
# class RagflowConfig(BaseModel):
#     """Ragflow知识库配置 (已废弃)"""
#     endpoint: str = Field(default="http://localhost:9380", description="Ragflow服务端点", alias="RAGFLOW_ENDPOINT")
#     api_key: str = Field(default="", description="Ragflow API密钥", alias="RAGFLOW_API_KEY")
#     dataset_id: Optional[str] = Field(default=None, description="数据集ID", alias="RAGFLOW_DATASET_ID")
#     timeout: int = Field(default=30, description="请求超时时间(秒)")
#     model_config = {"populate_by_name": True}


class MilvusConfig(BaseModel):
    """Milvus向量数据库配置 (v7.141+)"""

    enabled: bool = Field(default=True, description="是否启用Milvus知识库", alias="MILVUS_ENABLED")
    host: str = Field(default="localhost", description="Milvus服务器地址", alias="MILVUS_HOST")
    port: int = Field(default=19530, description="Milvus服务端口", alias="MILVUS_PORT")
    collection_name: str = Field(
        default="design_knowledge_base", description="Collection名称", alias="MILVUS_COLLECTION_NAME"
    )

    # Embedding配置
    embedding_model: str = Field(
        default="BAAI/bge-m3", description="Embedding模型（支持中英文）", alias="MILVUS_EMBEDDING_MODEL"
    )
    embedding_dim: int = Field(default=1024, description="向量维度（BGE-M3默认1024）", alias="MILVUS_EMBEDDING_DIM")

    # 检索配置
    similarity_threshold: float = Field(default=0.6, description="粗排相似度阈值", alias="MILVUS_SIMILARITY_THRESHOLD")
    candidate_multiplier: int = Field(default=5, description="候选集扩大倍数（top_k×倍数）", alias="MILVUS_CANDIDATE_MULTIPLIER")

    # Reranker配置
    reranker_model: str = Field(default="BAAI/bge-reranker-v2-m3", description="重排序模型", alias="MILVUS_RERANKER_MODEL")
    rerank_enabled: bool = Field(default=True, description="是否启用重排序", alias="MILVUS_RERANK_ENABLED")
    rerank_weight: float = Field(default=0.7, description="重排序分数权重（0-1）", alias="MILVUS_RERANK_WEIGHT")

    # 去重配置
    dedup_threshold: float = Field(default=0.95, description="去重相似度阈值", alias="MILVUS_DEDUP_THRESHOLD")

    # 性能配置
    timeout: int = Field(default=30, description="请求超时时间(秒)", alias="MILVUS_TIMEOUT")
    batch_size: int = Field(default=32, description="批量插入/查询大小", alias="MILVUS_BATCH_SIZE")

    model_config = {"populate_by_name": True}


class ArxivConfig(BaseModel):
    """Arxiv搜索配置"""

    enabled: bool = Field(default=True, description="是否启用Arxiv搜索")
    timeout: int = Field(default=30, description="请求超时时间(秒)")


class BochaConfig(BaseModel):
    """博查搜索配置 (v7.63+, v7.160: AI Search增强, v7.162: TikHub社交媒体集成)"""

    enabled: bool = Field(default=False, description="是否启用博查搜索", alias="BOCHA_ENABLED")
    api_key: str = Field(default="", description="博查API密钥", alias="BOCHA_API_KEY")
    base_url: str = Field(
        default="https://api.bochaai.com", description="博查API地址（v7.160更新为官方最新域名）", alias="BOCHA_BASE_URL"
    )
    default_count: int = Field(default=5, description="默认搜索结果数量", alias="BOCHA_DEFAULT_COUNT")
    timeout: int = Field(default=30, description="请求超时时间(秒)", alias="BOCHA_TIMEOUT")
    freshness: str = Field(default="oneYear", description="搜索结果时效性", alias="BOCHA_FRESHNESS")
    #  v7.160: AI Search 模式配置
    ai_search_enabled: bool = Field(default=True, description="是否启用AI Search API", alias="BOCHA_AI_SEARCH_ENABLED")
    image_search_enabled: bool = Field(
        default=False, description="是否启用图片搜索（Ucppt模式强制禁用）", alias="BOCHA_IMAGE_SEARCH_ENABLED"
    )
    use_deepseek_r1: bool = Field(default=True, description="搜索模式是否使用DeepSeek-R1推理", alias="BOCHA_USE_DEEPSEEK_R1")
    #  v7.162: TikHub 社交媒体数据源配置（抖音/小红书/微博/知乎）
    tikhub_enabled: bool = Field(default=False, description="是否启用TikHub社交媒体搜索", alias="BOCHA_TIKHUB_ENABLED")
    tikhub_api_key: str = Field(default="", description="TikHub API密钥", alias="BOCHA_TIKHUB_API_KEY")
    tikhub_base_url: str = Field(
        default="https://api.tikhub.io", description="TikHub API地址（中国大陆用api.tikhub.dev）", alias="BOCHA_TIKHUB_BASE_URL"
    )
    tikhub_platforms: str = Field(
        default="xiaohongshu,douyin,weibo,zhihu",
        description="启用的平台(逗号分隔): xiaohongshu,douyin,weibo,zhihu",
        alias="BOCHA_TIKHUB_PLATFORMS",
    )
    tikhub_count: int = Field(default=5, description="每个平台返回的结果数量", alias="BOCHA_TIKHUB_COUNT")

    model_config = {"populate_by_name": True}


class SearchQualityConfig(BaseModel):
    """
    搜索质量优化配置 (v7.212 + v7.237)

    包含专业搜索模式配置和质量筛选配置，
    通过规则评分 + LLM二次过滤确保搜索结果质量。
    """

    # v7.237: 专业搜索模式配置
    design_professional_mode: bool = Field(
        default=False, description="启用专业设计搜索模式", alias="ENABLE_DESIGN_PROFESSIONAL_MODE"
    )
    min_search_relevance: float = Field(default=0.6, description="最小搜索相关性阈值", alias="MIN_SEARCH_RELEVANCE")
    prioritize_case_studies: bool = Field(default=False, description="优先返回案例研究类内容", alias="PRIORITIZE_CASE_STUDIES")
    enhance_scenario_keywords: bool = Field(default=False, description="增强场景化关键词生成", alias="ENHANCE_SCENARIO_KEYWORDS")
    filter_commercial_content: bool = Field(default=False, description="过滤纯商业推广内容", alias="FILTER_COMMERCIAL_CONTENT")

    # v7.212: 质量评分阈值配置
    quality_threshold: float = Field(
        default=0.3, description="质量评分阈值（0.2宽松/0.3平衡/0.5严格）", alias="SEARCH_QUALITY_THRESHOLD"
    )

    # LLM二次过滤开关
    llm_filter_enabled: bool = Field(
        default=True, description="是否启用LLM二次过滤（反思阶段判断相关性）", alias="SEARCH_QUALITY_LLM_FILTER"
    )

    # 每轮最少需要的高质量来源数
    min_quality_sources: int = Field(default=3, description="每轮搜索最少需要的高质量来源数", alias="SEARCH_MIN_QUALITY_SOURCES")

    # 补充搜索最大次数
    supplement_max_retries: int = Field(
        default=3, description="补充搜索最大次数（防止无限循环）", alias="SEARCH_SUPPLEMENT_MAX_RETRIES"
    )

    model_config = {"populate_by_name": True}


class ImageGenerationConfig(BaseModel):
    """
    AI 图像生成配置 (v7.38+)

    通过 OpenRouter 调用 Gemini 3 Pro 图像生成 (Nano Banana Pro)
    价格: $2/M input, $12/M output
    """

    enabled: bool = Field(default=False, description="是否启用 AI 概念图生成", alias="IMAGE_GENERATION_ENABLED")
    model: str = Field(
        default="google/gemini-3-pro-image-preview", description="图像生成模型（OpenRouter 格式）", alias="IMAGE_GENERATION_MODEL"
    )
    max_images_per_report: int = Field(
        default=2, description="每个专家报告最多生成几张概念图", alias="IMAGE_GENERATION_MAX_IMAGES_PER_REPORT"
    )
    timeout: int = Field(default=120, description="图像生成超时时间(秒)", alias="IMAGE_GENERATION_TIMEOUT")

    #  v7.61: Vision 图像分析配置
    vision_enabled: bool = Field(default=False, description="是否启用 Vision 模型分析参考图", alias="VISION_ANALYSIS_ENABLED")
    vision_provider: str = Field(
        default="openai-openrouter",
        description="Vision 模型提供商 (openai-openrouter|gemini-openrouter|openai)",
        alias="VISION_MODEL_PROVIDER",
    )
    vision_model: str = Field(default="openai/gpt-4o", description="Vision 模型名称", alias="VISION_MODEL")
    vision_timeout: int = Field(default=30, description="Vision 分析超时时间(秒)", alias="VISION_ANALYSIS_TIMEOUT")
    vision_max_tokens: int = Field(default=500, description="Vision 分析最大 token 数", alias="VISION_ANALYSIS_MAX_TOKENS")

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

    enabled: bool = Field(default=False, description="是否启用 Inpainting 图像编辑", alias="INPAINTING_ENABLED")
    provider: str = Field(default="openai", description="Inpainting 提供商（当前仅支持 openai）", alias="INPAINTING_PROVIDER")
    model: str = Field(default="dall-e-2", description="Inpainting 模型（DALL-E 2 Edit API）", alias="INPAINTING_MODEL")
    timeout: int = Field(default=120, description="Inpainting 超时时间(秒)", alias="INPAINTING_TIMEOUT")

    # OpenAI API Key 从 OPENAI_API_KEY 环境变量读取（独立于 OpenRouter）

    model_config = {"populate_by_name": True}


class StorageConfig(BaseModel):
    """文件存储配置"""

    upload_dir: str = Field(default="./data/uploads", description="上传目录", alias="UPLOAD_DIR")
    output_dir: str = Field(default="./data/outputs", description="输出目录", alias="OUTPUT_DIR")
    temp_dir: str = Field(default="./data/temp", description="临时目录", alias="TEMP_DIR")
    database_url: str = Field(
        default="sqlite:///./data/archived_sessions.db", description="数据库URL", alias="DATABASE_URL"
    )

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
    多环境配置: 通过 APP_ENV 环境变量指定环境
    """

    # 环境配置
    app_env: str = Field(default="development", description="应用环境 (development/test/production)", alias="APP_ENV")
    environment: Environment = Field(default=Environment.DEV, description="运行环境 (向后兼容)")
    debug: bool = Field(default=False, description="调试模式", alias="DEBUG")
    log_level: str = Field(default="INFO", description="日志级别", alias="LOG_LEVEL")

    # 端口配置 (v8.1+): 支持多环境并行运行
    api_port: int = Field(default=8000, description="后端API端口", alias="API_PORT")
    frontend_port: int = Field(default=3001, description="前端端口", alias="FRONTEND_PORT")

    # 日志配置 (v8.1+): 支持环境隔离
    structured_logging: bool = Field(default=False, description="是否使用结构化日志(JSON)", alias="STRUCTURED_LOGGING")
    enable_detailed_logging: bool = Field(default=False, description="是否启用详细日志", alias="ENABLE_DETAILED_LOGGING")
    log_sample_rate: float = Field(default=1.0, description="日志采样率(0.0-1.0)", alias="LOG_SAMPLE_RATE")
    log_file_path: str = Field(default="logs/server.log", description="日志文件路径", alias="LOG_FILE_PATH")

    # 应用配置
    app_name: str = Field(default="Intelligent Project Analyzer", description="应用名称", alias="APP_NAME")
    app_version: str = Field(default="2.0.0", description="应用版本", alias="APP_VERSION")
    post_completion_followup_enabled: bool = Field(default=True, description="报告生成后是否自动触发追问交互")

    # LLM配置 (嵌套) -  提供默认值
    llm: LLMConfig = Field(default_factory=LLMConfig)

    # 工具配置 (嵌套) -  提供默认值
    tavily: TavilyConfig = Field(default_factory=TavilyConfig)
    serper: SerperConfig = Field(default_factory=SerperConfig)  #  v7.130+: Serper搜索
    # ragflow: RagflowConfig = Field(default_factory=RagflowConfig)  #  v7.141: 已废弃，使用 Milvus
    milvus: MilvusConfig = Field(default_factory=MilvusConfig)  #  v7.141: Milvus向量数据库
    arxiv: ArxivConfig = Field(default_factory=ArxivConfig)
    bocha: BochaConfig = Field(default_factory=BochaConfig)  #  v7.63: 博查搜索
    search_quality: SearchQualityConfig = Field(default_factory=SearchQualityConfig)  #  v7.212: 搜索质量筛选

    #  v7.38: AI 图像生成配置
    image_generation: ImageGenerationConfig = Field(default_factory=ImageGenerationConfig)

    #  v7.62: AI 图像编辑（Inpainting）配置
    inpainting: InpaintingConfig = Field(default_factory=InpaintingConfig)

    # 存储配置
    storage: StorageConfig = Field(default_factory=StorageConfig)

    # 并发配置
    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig)

    # 数据库配置
    database_url: str = Field(
        default="sqlite:///./data/archived_sessions.db", description="数据库URL", alias="DATABASE_URL"
    )
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL", alias="REDIS_URL")

    # 前端配置
    api_base_url: str = Field(default="http://localhost:8000", description="API服务地址")
    streamlit_port: int = Field(default=8501, description="Streamlit端口", alias="STREAMLIT_PORT")
    streamlit_host: str = Field(default="localhost", description="Streamlit主机", alias="STREAMLIT_HOST")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # 支持 LLM__MAX_TOKENS=8000
        case_sensitive=False,
        extra="ignore",  # 忽略未定义的环境变量
    )

    @model_validator(mode="after")
    def load_from_flat_env(self):
        """从扁平环境变量加载配置(兼容旧.env格式)"""
        # 读取LLM配置 - 根据提供商选择正确的API Key
        provider = os.getenv("LLM_PROVIDER", "openai").lower()

        if provider == "openrouter":
            # OpenRouter: 优先使用 OPENROUTER_API_KEY
            if not self.llm.api_key and os.getenv("OPENROUTER_API_KEY"):
                self.llm.api_key = os.getenv("OPENROUTER_API_KEY", "")
        elif provider == "deepseek":
            # DeepSeek
            if not self.llm.api_key and os.getenv("DEEPSEEK_API_KEY"):
                self.llm.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        elif provider == "qwen":
            # Qwen
            if not self.llm.api_key and os.getenv("QWEN_API_KEY"):
                self.llm.api_key = os.getenv("QWEN_API_KEY", "")
        else:
            # OpenAI (默认)
            if not self.llm.api_key and os.getenv("OPENAI_API_KEY"):
                self.llm.api_key = os.getenv("OPENAI_API_KEY", "")

        #  兼容旧版 .env 字段 (最后的后备选项)
        if not self.llm.api_key and os.getenv("LLM_API_KEY"):
            self.llm.api_key = os.getenv("LLM_API_KEY", "")

        # 加载模型名称 - 根据提供商选择
        if provider == "openrouter" and os.getenv("OPENROUTER_MODEL"):
            self.llm.model = os.getenv("OPENROUTER_MODEL", self.llm.model)
        elif provider == "deepseek" and os.getenv("DEEPSEEK_MODEL"):
            self.llm.model = os.getenv("DEEPSEEK_MODEL", self.llm.model)
        elif provider == "qwen" and os.getenv("QWEN_MODEL"):
            self.llm.model = os.getenv("QWEN_MODEL", self.llm.model)
        elif os.getenv("OPENAI_MODEL"):
            self.llm.model = os.getenv("OPENAI_MODEL", self.llm.model)
        elif os.getenv("LLM_MODEL_NAME"):
            self.llm.model = os.getenv("LLM_MODEL_NAME", self.llm.model)

        # 加载 Base URL - 根据提供商选择
        if provider == "openrouter" and os.getenv("OPENROUTER_BASE_URL"):
            self.llm.api_base = os.getenv("OPENROUTER_BASE_URL", self.llm.api_base)
        elif provider == "deepseek" and os.getenv("DEEPSEEK_BASE_URL"):
            self.llm.api_base = os.getenv("DEEPSEEK_BASE_URL", self.llm.api_base)
        elif provider == "qwen" and os.getenv("QWEN_BASE_URL"):
            self.llm.api_base = os.getenv("QWEN_BASE_URL", self.llm.api_base)
        elif os.getenv("OPENAI_BASE_URL"):
            self.llm.api_base = os.getenv("OPENAI_BASE_URL", self.llm.api_base)
        elif os.getenv("LLM_BASE_URL"):
            self.llm.api_base = os.getenv("LLM_BASE_URL", self.llm.api_base)
        if os.getenv("MAX_TOKENS"):
            self.llm.max_tokens = int(os.getenv("MAX_TOKENS", self.llm.max_tokens))
        if os.getenv("LLM_TIMEOUT"):
            self.llm.timeout = int(os.getenv("LLM_TIMEOUT", self.llm.timeout))
        if os.getenv("TEMPERATURE"):
            self.llm.temperature = float(os.getenv("TEMPERATURE", self.llm.temperature))
        if os.getenv("MAX_RETRIES"):
            self.llm.max_retries = int(os.getenv("MAX_RETRIES", self.llm.max_retries))
        if os.getenv("RETRY_DELAY"):
            self.llm.retry_delay = int(os.getenv("RETRY_DELAY", self.llm.retry_delay))

        #  v7.38: 读取图像生成配置
        if os.getenv("IMAGE_GENERATION_ENABLED"):
            self.image_generation.enabled = os.getenv("IMAGE_GENERATION_ENABLED", "false").lower() in (
                "true",
                "1",
                "yes",
            )
        if os.getenv("IMAGE_GENERATION_MODEL"):
            self.image_generation.model = os.getenv("IMAGE_GENERATION_MODEL", self.image_generation.model)
        if os.getenv("IMAGE_GENERATION_MAX_IMAGES_PER_REPORT"):
            self.image_generation.max_images_per_report = int(
                os.getenv("IMAGE_GENERATION_MAX_IMAGES_PER_REPORT", self.image_generation.max_images_per_report)
            )
        if os.getenv("IMAGE_GENERATION_TIMEOUT"):
            self.image_generation.timeout = int(os.getenv("IMAGE_GENERATION_TIMEOUT", self.image_generation.timeout))

        #  v7.62: 读取 Inpainting 图像编辑配置
        if os.getenv("INPAINTING_ENABLED"):
            self.inpainting.enabled = os.getenv("INPAINTING_ENABLED", "false").lower() in ("true", "1", "yes")
        if os.getenv("INPAINTING_PROVIDER"):
            self.inpainting.provider = os.getenv("INPAINTING_PROVIDER", self.inpainting.provider)
        if os.getenv("INPAINTING_MODEL"):
            self.inpainting.model = os.getenv("INPAINTING_MODEL", self.inpainting.model)
        if os.getenv("INPAINTING_TIMEOUT"):
            self.inpainting.timeout = int(os.getenv("INPAINTING_TIMEOUT", self.inpainting.timeout))

        # 读取Tavily配置
        if not self.tavily.api_key and os.getenv("TAVILY_API_KEY"):
            self.tavily.api_key = os.getenv("TAVILY_API_KEY", "")

        # 读取Ragflow配置（已禁用）
        # if not self.ragflow.api_key and os.getenv("RAGFLOW_API_KEY"):
        #     self.ragflow.api_key = os.getenv("RAGFLOW_API_KEY", "")
        # if os.getenv("RAGFLOW_ENDPOINT"):
        #     self.ragflow.endpoint = os.getenv("RAGFLOW_ENDPOINT", self.ragflow.endpoint)
        # if os.getenv("RAGFLOW_DATASET_ID"):
        #     self.ragflow.dataset_id = os.getenv("RAGFLOW_DATASET_ID")

        #  v7.63: 读取博查配置
        if os.getenv("BOCHA_ENABLED"):
            self.bocha.enabled = os.getenv("BOCHA_ENABLED", "false").lower() in ("true", "1", "yes")
        if not self.bocha.api_key and os.getenv("BOCHA_API_KEY"):
            self.bocha.api_key = os.getenv("BOCHA_API_KEY", "")
        if os.getenv("BOCHA_BASE_URL"):
            self.bocha.base_url = os.getenv("BOCHA_BASE_URL", self.bocha.base_url)
        if os.getenv("BOCHA_DEFAULT_COUNT"):
            self.bocha.default_count = int(os.getenv("BOCHA_DEFAULT_COUNT", self.bocha.default_count))

        #  v7.162: 读取 TikHub 社交媒体搜索配置
        if os.getenv("BOCHA_TIKHUB_ENABLED"):
            self.bocha.tikhub_enabled = os.getenv("BOCHA_TIKHUB_ENABLED", "false").lower() in ("true", "1", "yes")
        if os.getenv("BOCHA_TIKHUB_API_KEY"):
            self.bocha.tikhub_api_key = os.getenv("BOCHA_TIKHUB_API_KEY", "")
        if os.getenv("BOCHA_TIKHUB_BASE_URL"):
            self.bocha.tikhub_base_url = os.getenv("BOCHA_TIKHUB_BASE_URL", self.bocha.tikhub_base_url)
        if os.getenv("BOCHA_TIKHUB_PLATFORMS"):
            self.bocha.tikhub_platforms = os.getenv("BOCHA_TIKHUB_PLATFORMS", self.bocha.tikhub_platforms)
        if os.getenv("BOCHA_TIKHUB_COUNT"):
            self.bocha.tikhub_count = int(os.getenv("BOCHA_TIKHUB_COUNT", self.bocha.tikhub_count))

        #  v7.237: 读取搜索质量优化配置
        if os.getenv("ENABLE_DESIGN_PROFESSIONAL_MODE"):
            self.search_quality.design_professional_mode = os.getenv(
                "ENABLE_DESIGN_PROFESSIONAL_MODE", "false"
            ).lower() in ("true", "1", "yes")
        if os.getenv("MIN_SEARCH_RELEVANCE"):
            self.search_quality.min_search_relevance = float(
                os.getenv("MIN_SEARCH_RELEVANCE", self.search_quality.min_search_relevance)
            )
        if os.getenv("PRIORITIZE_CASE_STUDIES"):
            self.search_quality.prioritize_case_studies = os.getenv("PRIORITIZE_CASE_STUDIES", "false").lower() in (
                "true",
                "1",
                "yes",
            )
        if os.getenv("ENHANCE_SCENARIO_KEYWORDS"):
            self.search_quality.enhance_scenario_keywords = os.getenv("ENHANCE_SCENARIO_KEYWORDS", "false").lower() in (
                "true",
                "1",
                "yes",
            )
        if os.getenv("FILTER_COMMERCIAL_CONTENT"):
            self.search_quality.filter_commercial_content = os.getenv("FILTER_COMMERCIAL_CONTENT", "false").lower() in (
                "true",
                "1",
                "yes",
            )

        return self

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == Environment.PROD

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment == Environment.DEV

    #  兼容旧版设置访问方式 (settings.LLM)
    @property
    def LLM(self) -> LLMConfig:  # pragma: no cover - 简单属性映射
        """兼容旧版大写属性访问方式"""
        return self.llm

    @LLM.setter
    def LLM(self, value: LLMConfig) -> None:  # pragma: no cover - 简单属性映射
        self.llm = value


# 全局配置实例 - 单例模式
settings = Settings()
