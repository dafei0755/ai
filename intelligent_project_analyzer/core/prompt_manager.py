"""
提示词管理器 - Prompt Manager

负责加载、管理和提供提示词配置。
Responsible for loading, managing, and providing prompt configurations.
"""

from pathlib import Path
from typing import Dict, Optional

import yaml


class PromptManager:
    """
    提示词管理器 - 管理所有智能体的提示词配置 (单例模式)

    功能:
    1. 从YAML文件加载提示词配置
    2. 提供提示词查询接口
    3. 支持模板变量替换
    4. 创建默认配置模板
    5.  单例模式 + 类级别缓存,避免重复加载
    """

    # 类级别缓存
    _instances: Dict[str, "PromptManager"] = {}  # key: config_path, value: instance
    _default_instance: Optional["PromptManager"] = None

    def __new__(cls, config_path: Optional[str] = None):
        """
        单例模式实现 - 同一config_path只创建一个实例
        """
        # 确定配置路径
        if config_path is None:
            current_dir = Path(__file__).parent.parent
            config_path = str(current_dir / "config" / "prompts")
        else:
            config_path = str(Path(config_path).resolve())

        # 检查是否已存在实例
        if config_path not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[config_path] = instance
            # 标记为未初始化
            instance._initialized = False

        return cls._instances[config_path]

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化提示词管理器 (仅首次调用时执行)

        Args:
            config_path: 提示词配置目录路径，如果为None则使用默认路径
        """
        # 如果已初始化,直接返回
        if hasattr(self, "_initialized") and self._initialized:
            return

        if config_path is None:
            # 使用默认配置路径 - config/prompts/ 目录
            current_dir = Path(__file__).parent.parent
            config_path = current_dir / "config" / "prompts"

        self.config_path = Path(config_path)
        self.prompts: Dict[str, Dict] = {}

        # 加载提示词配置
        if self.config_path.exists():
            self._load_prompts()
            # 启动时检查配置完整性
            self._validate_config_integrity()
        else:
            print(f"[WARNING] Prompts directory does not exist: {self.config_path}")
            print("[INFO] Creating default prompts directory...")
            self.config_path.mkdir(parents=True, exist_ok=True)

        # 标记为已初始化
        self._initialized = True

    def _load_prompts(self) -> None:
        """从YAML文件目录加载提示词配置 (带缓存日志优化)"""
        try:
            if not self.config_path.is_dir():
                print(f"[WARNING] Config path is not a directory: {self.config_path}")
                self.prompts = {}
                return

            #  仅首次加载时输出详细日志
            is_first_load = len(PromptManager._instances) == 1
            if is_first_load:
                print(f"[INFO]  Loading prompts from directory: {self.config_path}")

            self.prompts = {}
            yaml_files = list(self.config_path.glob("*.yaml")) + list(self.config_path.glob("*.yml"))

            if not yaml_files:
                print("[WARNING] No YAML files found in prompts directory")
                return

            for yaml_file in yaml_files:
                if is_first_load:
                    print(f"[INFO] Loading {yaml_file.name}...")
                with open(yaml_file, "r", encoding="utf-8") as f:
                    file_content = yaml.safe_load(f) or {}
                    # 使用文件名（不含扩展名）作为 key
                    agent_name = yaml_file.stem
                    self.prompts[agent_name] = file_content

            if is_first_load:
                print(f"[OK]  Successfully loaded {len(self.prompts)} prompt configuration(s) (cached)")
            else:
                # 后续调用仅输出简洁信息
                print(f"[INFO] Using cached prompts ({len(self.prompts)} configs)")

        except Exception as e:
            print(f"[ERROR] Failed to load prompt configuration: {e}")
            self.prompts = {}

    def _validate_config_integrity(self) -> None:
        """
        验证配置完整性 - 检查所有核心提示词配置文件是否存在

        核心配置文件:
        - requirements_analyst_lite.yaml: 需求分析师 ( v4.2: 精简版)
        - review_agents.yaml: 审核系统（红队、蓝队、评委、甲方）
        - result_aggregator.yaml: 结果聚合器
        - dynamic_project_director_v2.yaml: 项目总监 (v2.1)

        如果缺失核心配置，将抛出异常
        """
        required_configs = [
            "requirements_analyst_lite",  #  v4.2: 使用精简版配置
            "review_agents",
            "result_aggregator",
            "dynamic_project_director_v2",  #  v2.1: 使用新版配置
        ]

        missing_configs = []
        for config_name in required_configs:
            # review_agents 使用特殊结构（reviewers字典），需要单独检查
            if config_name == "review_agents":
                if config_name not in self.prompts or not self.prompts[config_name].get("reviewers"):
                    missing_configs.append(f"{config_name}.yaml")
            else:
                if not self.has_prompt(config_name):
                    missing_configs.append(f"{config_name}.yaml")

        if missing_configs:
            error_msg = (
                " 配置完整性检查失败！缺少以下核心提示词配置文件:\n"
                + "\n".join(f"  - {name}" for name in missing_configs)
                + f"\n\n请确保这些文件存在于: {self.config_path}\n"
                + "系统无法使用硬编码提示词，必须提供完整的配置文件。"
            )
            raise FileNotFoundError(error_msg)

        print(f"[OK] Configuration integrity check passed - all {len(required_configs)} core configs present")

    def get_prompt(self, agent_name: str, return_full_config: bool = False, **kwargs) -> Optional[str | Dict]:
        """
        获取指定智能体的提示词

        Args:
            agent_name: 智能体名称 (如 "requirements_analyst", "dynamic_project_director")
            return_full_config: 是否返回完整配置字典（默认False，返回字符串）
            **kwargs: 模板变量 (如 role_name="红队审核专家", perspective="攻击方")

        Returns:
            提示词字符串或完整配置字典，如果不存在则返回None
        """
        if agent_name not in self.prompts:
            # 兼容旧名称/历史代码：部分 agent 的配置文件已升级或拆分。
            aliases = {
                # v4.x: 主需求分析师切换到精简版 YAML
                "requirements_analyst": "requirements_analyst_lite",
                # v2.x: 项目总监升级到 v2 配置
                "dynamic_project_director": "dynamic_project_director_v2",
            }
            alias = aliases.get(agent_name)
            if alias and alias in self.prompts:
                agent_name = alias
            else:
                print(f"[WARNING] Prompt not found for agent: {agent_name}")
                return None

        prompt_config = self.prompts[agent_name]

        # 如果请求完整配置，直接返回
        if return_full_config:
            return prompt_config

        # 兼容旧版本：尝试获取 'prompt' 或 'system_prompt' 字段
        prompt_template = prompt_config.get("prompt") or prompt_config.get("system_prompt", "")

        if not prompt_template:
            print(f"[WARNING] Empty prompt for agent: {agent_name}")
            return None

        # 如果提供了模板变量，进行替换
        if kwargs:
            try:
                return prompt_template.format(**kwargs)
            except KeyError as e:
                print(f"[ERROR] Missing template variable for {agent_name}: {e}")
                return prompt_template

        return prompt_template

    def get_reviewer_prompt(self, reviewer_role: str, role_name: str, perspective: str) -> Optional[str]:
        """
        获取审核者提示词（便捷方法）

        Args:
            reviewer_role: 审核者角色 ("red_team", "blue_team", "judge", "client")
            role_name: 角色名称 (如 "红队审核专家")
            perspective: 视角 (如 "攻击方")

        Returns:
            填充后的提示词字符串
        """
        # 审核系统使用统一的 review_agents 配置
        if "review_agents" not in self.prompts:
            print("[WARNING] review_agents prompt configuration not found")
            return None

        config = self.prompts["review_agents"]
        reviewers = config.get("reviewers", {})

        if reviewer_role not in reviewers:
            print(f"[WARNING] Reviewer role not found: {reviewer_role}")
            return None

        template = reviewers[reviewer_role].get("prompt_template", "")

        if not template:
            print(f"[WARNING] Empty prompt template for reviewer: {reviewer_role}")
            return None

        try:
            return template.format(role_name=role_name, perspective=perspective)
        except KeyError as e:
            print(f"[ERROR] Missing template variable for {reviewer_role}: {e}")
            return template

    def has_prompt(self, agent_name: str) -> bool:
        """
        检查是否存在指定智能体的提示词

        Args:
            agent_name: 智能体名称

        Returns:
            是否存在
        """
        if agent_name not in self.prompts:
            return False

        config = self.prompts[agent_name]
        # 兼容 v1.0 (prompt字段) 和 v2.0 (system_prompt字段)
        return bool(config.get("prompt") or config.get("system_prompt"))

    def get_all_agent_names(self) -> list:
        """
        获取所有已加载提示词的智能体名称列表

        Returns:
            智能体名称列表
        """
        return list(self.prompts.keys())

    def reload(self) -> None:
        """重新加载提示词配置"""
        print("[INFO] Reloading prompt configurations...")
        self._load_prompts()

    def get_metadata(self, agent_name: str) -> Optional[Dict]:
        """
        获取提示词元数据

        Args:
            agent_name: 智能体名称

        Returns:
            元数据字典（version, description等）
        """
        if agent_name not in self.prompts:
            return None

        config = self.prompts[agent_name]
        return {
            "version": config.get("version", "unknown"),
            "description": config.get("description", ""),
            "last_updated": config.get("last_updated", ""),
        }

    def get_task_description(self, agent_name: str, user_input: str, include_datetime: bool = True) -> Optional[str]:
        """
        获取任务描述，支持动态内容注入

        Args:
            agent_name: 智能体名称（如 "requirements_analyst"）
            user_input: 用户原始输入
            include_datetime: 是否包含日期时间信息（默认True）

        Returns:
            完整的任务描述字符串，如果配置不存在则返回None
        """
        if agent_name not in self.prompts:
            print(f"[WARNING] Prompt config not found for agent: {agent_name}")
            return None

        prompt_config = self.prompts[agent_name]
        template = prompt_config.get("task_description_template", "")

        if not template:
            print(f"[WARNING] No task_description_template found for agent: {agent_name}")
            return None

        # 处理日期时间
        datetime_info = ""
        business_config = prompt_config.get("business_config", {})
        if include_datetime and business_config.get("enable_dynamic_datetime", False):
            from datetime import datetime

            current_date_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
            datetime_info = f"当前日期是 {current_date_time}。"

        # 替换模板变量
        try:
            return template.format(datetime_info=datetime_info, user_input=user_input)
        except KeyError as e:
            print(f"[ERROR] Missing template variable in task_description_template: {e}")
            return template

    def get_output_example(self, agent_name: str) -> Optional[Dict]:
        """
        获取完整的JSON输出示例

        Args:
            agent_name: 智能体名称

        Returns:
            输出示例字典，如果不存在则返回None
        """
        if agent_name not in self.prompts:
            print(f"[WARNING] Prompt config not found for agent: {agent_name}")
            return None

        prompt_config = self.prompts[agent_name]
        output_example = prompt_config.get("output_example")

        if not output_example:
            print(f"[INFO] No output_example found for agent: {agent_name}")
            return None

        return output_example

    def get_ontology_framework(self, agent_name: str, project_type: Optional[str] = None) -> Optional[Dict]:
        """
        获取本体论框架配置

        Args:
            agent_name: 智能体名称
            project_type: 项目类型（如 "personal_residential"），None则返回所有启用的类型

        Returns:
            本体论框架字典，如果不存在则返回None
        """
        if agent_name not in self.prompts:
            print(f"[WARNING] Prompt config not found for agent: {agent_name}")
            return None

        prompt_config = self.prompts[agent_name]
        frameworks = prompt_config.get("ontology_frameworks", {})

        if not frameworks:
            print(f"[INFO] No ontology_frameworks found for agent: {agent_name}")
            return None

        # 如果指定了项目类型，返回该类型的框架
        if project_type:
            framework = frameworks.get(project_type)
            if not framework:
                print(f"[WARNING] Framework not found for project_type: {project_type}")
                return None
            return framework

        # 返回所有启用的项目类型
        business_config = prompt_config.get("business_config", {})
        enabled_types = business_config.get("project_types", [])

        if not enabled_types:
            print(f"[INFO] No enabled project_types in business_config for agent: {agent_name}")
            # 返回所有可用的框架
            return frameworks

        # 返回启用类型的框架
        enabled_frameworks = {}
        for pt in enabled_types:
            if pt in frameworks:
                enabled_frameworks[pt] = frameworks[pt]

        return enabled_frameworks if enabled_frameworks else None

    def get_business_config(self, agent_name: str) -> Optional[Dict]:
        """
        获取业务配置

        Args:
            agent_name: 智能体名称

        Returns:
            业务配置字典，如果不存在则返回None
        """
        if agent_name not in self.prompts:
            print(f"[WARNING] Prompt config not found for agent: {agent_name}")
            return None

        prompt_config = self.prompts[agent_name]
        business_config = prompt_config.get("business_config")

        if not business_config:
            print(f"[INFO] No business_config found for agent: {agent_name}")
            return None

        return business_config


# 使用示例
if __name__ == "__main__":
    # 创建提示词管理器
    manager = PromptManager()

    # 获取所有智能体名称
    print("\n所有已加载的智能体:")
    for name in manager.get_all_agent_names():
        metadata = manager.get_metadata(name)
        print(f"  - {name} (v{metadata['version']})")

    # 获取需求分析师提示词
    print("\n需求分析师提示词:")
    prompt = manager.get_prompt("requirements_analyst")
    if prompt:
        print(f"  长度: {len(prompt)} 字符")
        print(f"  前100字符: {prompt[:100]}...")

    # 获取审核者提示词（带模板变量）
    print("\n红队审核者提示词:")
    red_team_prompt = manager.get_reviewer_prompt(reviewer_role="red_team", role_name="红队审核专家", perspective="攻击方")
    if red_team_prompt:
        print(f"  长度: {len(red_team_prompt)} 字符")
