"""
搜索模式配置管理器 - 统一管理搜索架构配置和参数
集中管理搜索任务规划、协调、分发、扩展的所有配置项
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SearchMode(Enum):
    """搜索模式"""

    PASSIVE = "passive"  # 被动搜索（专家触发）
    ACTIVE = "active"  # 主动搜索（结果导向）
    HYBRID = "hybrid"  # 混合模式


class QualityLevel(Enum):
    """质量等级"""

    BASIC = "basic"  # 基础质量
    STANDARD = "standard"  # 标准质量
    HIGH = "high"  # 高质量
    PREMIUM = "premium"  # 顶级质量


@dataclass
class SearchToolConfig:
    """搜索工具配置"""

    tool_name: str
    enabled: bool = True
    priority: int = 1  # 1-高优先级, 5-低优先级
    timeout: int = 30
    max_retries: int = 2
    cost_per_call: float = 0.01

    # 工具特定配置
    specific_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchTypeConfig:
    """搜索类型配置"""

    search_type: str
    enabled: bool = True
    default_tools: List[str] = field(default_factory=list)
    quality_threshold: float = 0.7
    min_results: int = 3
    max_results: int = 10
    estimated_duration: int = 30

    # 查询生成配置
    query_templates: List[str] = field(default_factory=list)
    query_expansion: bool = True
    query_variations: int = 2


@dataclass
class PlannerConfig:
    """搜索任务规划器配置"""

    enable_dependency_analysis: bool = True
    enable_resource_estimation: bool = True
    max_tasks_per_deliverable: int = 8
    default_quality_threshold: float = 0.7

    # 任务生成配置
    task_distribution_strategy: str = "balanced"  # balanced, quality_focused, coverage_focused
    enable_task_prioritization: bool = True
    dependency_resolution_timeout: int = 30


@dataclass
class CoordinatorConfig:
    """搜索协调器配置"""

    max_parallel_searches: int = 3
    deduplication_enabled: bool = True
    deduplication_threshold: float = 0.8
    result_sharing_enabled: bool = True

    # 执行控制
    task_timeout: int = 60
    retry_failed_tasks: bool = True
    max_task_retries: int = 2

    # 负载均衡
    load_balancing_enabled: bool = True
    tool_rotation_enabled: bool = True


@dataclass
class DistributorConfig:
    """结果分发器配置"""

    enable_smart_distribution: bool = True
    relevance_threshold: float = 0.6
    enable_cross_deliverable_sharing: bool = True

    # 分发策略
    distribution_strategy: str = "relevance_based"  # relevance_based, coverage_based, quality_based
    result_filtering_enabled: bool = True
    duplicate_removal_enabled: bool = True


@dataclass
class ExpanderConfig:
    """动态扩展器配置"""

    enabled: bool = True
    max_expansion_rounds: int = 2
    quality_gap_threshold: float = 0.2
    coverage_gap_threshold: float = 0.3

    # 扩展触发器
    enable_quality_gap_detection: bool = True
    enable_coverage_gap_detection: bool = True
    enable_discovery_signal_detection: bool = True

    # 扩展控制
    max_expansion_tasks: int = 5
    expansion_quality_boost: float = 0.1


@dataclass
class WorkflowConfig:
    """工作流程配置"""

    search_mode: SearchMode = SearchMode.ACTIVE
    quality_level: QualityLevel = QualityLevel.STANDARD

    # 阶段超时
    phase_timeouts: Dict[str, int] = field(
        default_factory=lambda: {"planning": 60, "coordination": 300, "distribution": 30, "expansion": 120}
    )

    # 成本控制
    cost_control: Dict[str, float] = field(
        default_factory=lambda: {"max_total_cost": 2.0, "max_api_calls": 100, "cost_per_call": 0.01}
    )

    # 性能优化
    performance_optimization: Dict[str, Any] = field(
        default_factory=lambda: {"enable_caching": True, "cache_ttl": 3600, "enable_batching": True, "batch_size": 5}
    )


@dataclass
class SearchModeConfig:
    """搜索模式完整配置"""

    # 核心配置
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)
    planner: PlannerConfig = field(default_factory=PlannerConfig)
    coordinator: CoordinatorConfig = field(default_factory=CoordinatorConfig)
    distributor: DistributorConfig = field(default_factory=DistributorConfig)
    expander: ExpanderConfig = field(default_factory=ExpanderConfig)

    # 工具配置
    search_tools: Dict[str, SearchToolConfig] = field(default_factory=dict)
    search_types: Dict[str, SearchTypeConfig] = field(default_factory=dict)

    # 元数据
    config_version: str = "1.0.0"
    last_updated: str = ""
    environment: str = "production"  # development, testing, production


class SearchModeConfigManager:
    """搜索模式配置管理器"""

    def __init__(self, config_dir: str | None = None):
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent / "config"
        self.config_dir.mkdir(exist_ok=True)

        # 当前配置
        self._current_config: SearchModeConfig | None = None

        # 默认配置文件路径
        self.config_file = self.config_dir / "search_mode_config.json"
        self.preset_configs_dir = self.config_dir / "presets"
        self.preset_configs_dir.mkdir(exist_ok=True)

        # 初始化配置
        self._initialize_default_configs()

    def _initialize_default_configs(self):
        """初始化默认配置"""
        # 创建默认配置
        default_config = self._create_default_config()

        # 如果配置文件不存在，创建默认配置文件
        if not self.config_file.exists():
            self.save_config(default_config, self.config_file)

        # 创建预设配置
        self._create_preset_configs()

    def _create_default_config(self) -> SearchModeConfig:
        """创建默认配置"""
        # 默认搜索工具配置
        default_tools = {
            "tavily_search": SearchToolConfig(
                tool_name="tavily_search",
                enabled=True,
                priority=1,
                timeout=30,
                max_retries=2,
                cost_per_call=0.005,
                specific_config={"search_depth": "advanced", "include_answer": True, "include_raw_content": False},
            ),
            "bocha_search": SearchToolConfig(
                tool_name="bocha_search",
                enabled=True,
                priority=2,
                timeout=25,
                max_retries=2,
                cost_per_call=0.003,
                specific_config={"search_type": "web", "result_format": "json"},
            ),
            "arxiv_search": SearchToolConfig(
                tool_name="arxiv_search",
                enabled=True,
                priority=1,
                timeout=20,
                max_retries=1,
                cost_per_call=0.001,
                specific_config={"max_results": 10, "sort_by": "relevance"},
            ),
            "milvus_kb": SearchToolConfig(
                tool_name="milvus_kb",
                enabled=True,
                priority=1,
                timeout=15,
                max_retries=1,
                cost_per_call=0.002,
                specific_config={"top_k": 10, "score_threshold": 0.7},
            ),
        }

        # 默认搜索类型配置
        default_search_types = {
            "concept_exploration": SearchTypeConfig(
                search_type="concept_exploration",
                enabled=True,
                default_tools=["tavily_search", "bocha_search"],
                quality_threshold=0.7,
                min_results=3,
                max_results=8,
                estimated_duration=30,
                query_templates=[
                    "{concept} comprehensive overview",
                    "{concept} best practices methodology",
                    "what is {concept} complete guide",
                ],
            ),
            "academic_research": SearchTypeConfig(
                search_type="academic_research",
                enabled=True,
                default_tools=["arxiv_search", "milvus_kb"],
                quality_threshold=0.8,
                min_results=2,
                max_results=6,
                estimated_duration=25,
                query_templates=[
                    "{topic} academic research papers",
                    "scholarly {topic} methodology study",
                    "{topic} peer reviewed research",
                ],
            ),
            "trend_analysis": SearchTypeConfig(
                search_type="trend_analysis",
                enabled=True,
                default_tools=["bocha_search", "tavily_search"],
                quality_threshold=0.7,
                min_results=3,
                max_results=8,
                estimated_duration=35,
                query_templates=[
                    "{domain} emerging trends 2024 2025",
                    "future {domain} innovations",
                    "{domain} industry evolution patterns",
                ],
            ),
            "case_studies": SearchTypeConfig(
                search_type="case_studies",
                enabled=True,
                default_tools=["tavily_search", "bocha_search"],
                quality_threshold=0.7,
                min_results=2,
                max_results=6,
                estimated_duration=40,
                query_templates=[
                    "successful {domain} implementation examples",
                    "{domain} proven case studies",
                    "award winning {domain} projects",
                ],
            ),
            "data_statistics": SearchTypeConfig(
                search_type="data_statistics",
                enabled=True,
                default_tools=["bocha_search", "tavily_search"],
                quality_threshold=0.6,
                min_results=2,
                max_results=6,
                estimated_duration=25,
                query_templates=[
                    "{domain} market statistics data",
                    "{domain} industry metrics 2024",
                    "{domain} quantitative analysis report",
                ],
            ),
            "expert_insights": SearchTypeConfig(
                search_type="expert_insights",
                enabled=True,
                default_tools=["bocha_search", "tavily_search"],
                quality_threshold=0.7,
                min_results=2,
                max_results=6,
                estimated_duration=30,
                query_templates=[
                    "{domain} expert opinions insights",
                    "thought leaders {domain} perspectives",
                    "{domain} industry expert recommendations",
                ],
            ),
            "technical_specs": SearchTypeConfig(
                search_type="technical_specs",
                enabled=True,
                default_tools=["arxiv_search", "tavily_search"],
                quality_threshold=0.8,
                min_results=2,
                max_results=5,
                estimated_duration=20,
                query_templates=[
                    "{technology} technical specifications",
                    "{technology} implementation guidelines",
                    "{technology} architecture documentation",
                ],
            ),
            "dimension_analysis": SearchTypeConfig(
                search_type="dimension_analysis",
                enabled=True,
                default_tools=["tavily_search", "bocha_search"],
                quality_threshold=0.7,
                min_results=3,
                max_results=8,
                estimated_duration=35,
                query_templates=[
                    "{topic} multi-dimensional analysis",
                    "{topic} comprehensive framework",
                    "{topic} systematic evaluation criteria",
                ],
            ),
        }

        return SearchModeConfig(search_tools=default_tools, search_types=default_search_types)

    def _create_preset_configs(self):
        """创建预设配置"""
        # 快速模式配置
        quick_config = self._create_default_config()
        quick_config.workflow.quality_level = QualityLevel.BASIC
        quick_config.coordinator.max_parallel_searches = 5
        quick_config.expander.enabled = False
        self.save_config(quick_config, self.preset_configs_dir / "quick_mode.json")

        # 高质量模式配置
        premium_config = self._create_default_config()
        premium_config.workflow.quality_level = QualityLevel.PREMIUM
        premium_config.planner.default_quality_threshold = 0.8
        premium_config.expander.max_expansion_rounds = 3
        premium_config.coordinator.max_parallel_searches = 2  # 更慢但质量更高
        self.save_config(premium_config, self.preset_configs_dir / "premium_mode.json")

        # 开发测试模式配置
        dev_config = self._create_default_config()
        dev_config.environment = "development"
        dev_config.workflow.cost_control["max_total_cost"] = 0.5
        dev_config.expander.enabled = False
        self.save_config(dev_config, self.preset_configs_dir / "development.json")

    def load_config(self, config_path: str | None = None) -> SearchModeConfig:
        """加载配置"""
        config_file = Path(config_path) if config_path else self.config_file

        try:
            if config_file.exists():
                with open(config_file, encoding="utf-8") as f:
                    config_dict = json.load(f)

                # 转换为配置对象
                config = self._dict_to_config(config_dict)
                self._current_config = config

                logger.info(f" 成功加载搜索模式配置: {config_file}")
                return config
            else:
                logger.warning(f"️ 配置文件不存在，使用默认配置: {config_file}")
                return self._create_default_config()

        except Exception as e:
            logger.error(f" 加载配置失败: {e}")
            return self._create_default_config()

    def save_config(self, config: SearchModeConfig, config_path: str | None = None):
        """保存配置"""
        config_file = Path(config_path) if config_path else self.config_file

        try:
            # 更新元数据
            config.last_updated = str(datetime.now())

            # 转换为字典并处理枚举类型
            config_dict = asdict(config)

            # 处理枚举类型
            if "workflow" in config_dict and config_dict["workflow"]:
                if "search_mode" in config_dict["workflow"]:
                    config_dict["workflow"]["search_mode"] = config_dict["workflow"]["search_mode"].value
                if "quality_level" in config_dict["workflow"]:
                    config_dict["workflow"]["quality_level"] = config_dict["workflow"]["quality_level"].value

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)

            logger.info(f" 成功保存搜索模式配置: {config_file}")

        except Exception as e:
            logger.error(f" 保存配置失败: {e}")
            # 如果保存失败，至少保存基本版本
            try:
                basic_config = {
                    "config_version": "1.0.0",
                    "environment": "production",
                    "search_tools": {},
                    "search_types": {},
                }
                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump(basic_config, f, indent=2)
            except Exception:
                pass

    def get_current_config(self) -> SearchModeConfig:
        """获取当前配置"""
        if self._current_config is None:
            self._current_config = self.load_config()
        return self._current_config

    def update_config(self, updates: Dict[str, Any]):
        """更新配置"""
        current_config = self.get_current_config()

        # 应用更新
        config_dict = asdict(current_config)
        self._deep_update(config_dict, updates)

        # 转换回配置对象并保存
        updated_config = self._dict_to_config(config_dict)
        self.save_config(updated_config)
        self._current_config = updated_config

    def load_preset_config(self, preset_name: str) -> SearchModeConfig:
        """加载预设配置"""
        preset_file = self.preset_configs_dir / f"{preset_name}.json"

        if not preset_file.exists():
            raise FileNotFoundError(f"预设配置不存在: {preset_name}")

        return self.load_config(str(preset_file))

    def list_available_presets(self) -> List[str]:
        """列出可用的预设配置"""
        preset_files = self.preset_configs_dir.glob("*.json")
        return [f.stem for f in preset_files]

    def get_tool_config(self, tool_name: str) -> SearchToolConfig | None:
        """获取工具配置"""
        config = self.get_current_config()
        return config.search_tools.get(tool_name)

    def get_search_type_config(self, search_type: str) -> SearchTypeConfig | None:
        """获取搜索类型配置"""
        config = self.get_current_config()
        return config.search_types.get(search_type)

    def get_workflow_config(self) -> WorkflowConfig:
        """获取工作流程配置"""
        return self.get_current_config().workflow

    # 辅助方法
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> SearchModeConfig:
        """将字典转换为配置对象"""
        # 转换工具配置
        tools_config = {}
        if "search_tools" in config_dict:
            for tool_name, tool_data in config_dict["search_tools"].items():
                tools_config[tool_name] = SearchToolConfig(**tool_data)

        # 转换搜索类型配置
        types_config = {}
        if "search_types" in config_dict:
            for type_name, type_data in config_dict["search_types"].items():
                types_config[type_name] = SearchTypeConfig(**type_data)

        # 转换核心配置，处理枚举类型
        workflow_data = config_dict.get("workflow", {})
        if "search_mode" in workflow_data and isinstance(workflow_data["search_mode"], str):
            workflow_data["search_mode"] = SearchMode(workflow_data["search_mode"])
        if "quality_level" in workflow_data and isinstance(workflow_data["quality_level"], str):
            workflow_data["quality_level"] = QualityLevel(workflow_data["quality_level"])

        workflow_config = WorkflowConfig(**workflow_data)
        planner_config = PlannerConfig(**config_dict.get("planner", {}))
        coordinator_config = CoordinatorConfig(**config_dict.get("coordinator", {}))
        distributor_config = DistributorConfig(**config_dict.get("distributor", {}))
        expander_config = ExpanderConfig(**config_dict.get("expander", {}))

        return SearchModeConfig(
            workflow=workflow_config,
            planner=planner_config,
            coordinator=coordinator_config,
            distributor=distributor_config,
            expander=expander_config,
            search_tools=tools_config,
            search_types=types_config,
            config_version=config_dict.get("config_version", "1.0.0"),
            last_updated=config_dict.get("last_updated", ""),
            environment=config_dict.get("environment", "production"),
        )

    def _deep_update(self, base_dict: Dict, update_dict: Dict):
        """深度更新字典"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value


# 全局配置管理器实例
_config_manager = None


def get_config_manager(config_dir: str | None = None) -> SearchModeConfigManager:
    """获取配置管理器实例（单例模式）"""
    global _config_manager
    if _config_manager is None:
        _config_manager = SearchModeConfigManager(config_dir)
    return _config_manager


def get_search_mode_config() -> SearchModeConfig:
    """获取当前搜索模式配置"""
    return get_config_manager().get_current_config()


def update_search_mode_config(updates: Dict[str, Any]):
    """更新搜索模式配置"""
    get_config_manager().update_config(updates)


# 便捷函数
def enable_quick_mode():
    """启用快速模式"""
    config_manager = get_config_manager()
    quick_config = config_manager.load_preset_config("quick_mode")
    config_manager._current_config = quick_config
    logger.info(" 已启用快速模式")


def enable_premium_mode():
    """启用高质量模式"""
    config_manager = get_config_manager()
    premium_config = config_manager.load_preset_config("premium_mode")
    config_manager._current_config = premium_config
    logger.info(" 已启用高质量模式")


def enable_development_mode():
    """启用开发模式"""
    config_manager = get_config_manager()
    dev_config = config_manager.load_preset_config("development")
    config_manager._current_config = dev_config
    logger.info(" 已启用开发模式")
