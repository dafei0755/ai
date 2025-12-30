"""
角色选择策略管理器
Role Selection Strategy Manager

负责加载、验证和应用角色选择策略
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger


class StrategyManager:
    """策略管理器"""
    
    def __init__(self, strategy_file: Optional[str] = None):
        """
        初始化策略管理器
        
        Args:
            strategy_file: 策略配置文件路径,如果为None则使用默认路径
        """
        if strategy_file is None:
            # 使用默认策略文件
            config_dir = Path(__file__).parent.parent / "config"
            strategy_file = config_dir / "role_selection_strategy.yaml"
        
        self.strategy_file = Path(strategy_file)
        self.strategies = self._load_strategies()
        logger.info(f"Strategy manager initialized with {len(self.strategies.get('custom_strategies', {}))} custom strategies")
    
    def _load_strategies(self) -> Dict[str, Any]:
        """加载策略配置"""
        try:
            with open(self.strategy_file, 'r', encoding='utf-8') as f:
                strategies = yaml.safe_load(f)
            logger.info(f"Loaded strategies from {self.strategy_file}")
            return strategies
        except Exception as e:
            logger.error(f"Failed to load strategies: {e}")
            # 返回默认策略
            return self._get_default_strategies()
    
    def _get_default_strategies(self) -> Dict[str, Any]:
        """获取默认策略(当配置文件加载失败时使用)"""
        return {
            "version": "1.0",
            "default_strategy": {
                "name": "balanced",
                "description": "平衡策略",
                "min_roles": 3,
                "max_roles": 8,
                "selection_rules": {
                    "required_categories": ["V2_设计总监", "V6_专业总工程师"],
                    "priority_weights": {
                        "V2_设计总监": 1.0,
                        "V3_人物及叙事专家": 0.8,
                        "V4_设计研究员": 0.9,
                        "V5_场景与用户生态专家": 0.7,
                        "V6_专业总工程师": 1.0
                    }
                }
            }
        }
    
    def get_strategy(self, strategy_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取指定策略
        
        Args:
            strategy_name: 策略名称,如果为None则返回默认策略
        
        Returns:
            策略配置字典
        """
        if strategy_name is None or strategy_name == "default":
            return self.strategies.get("default_strategy", {})
        
        # 查找自定义策略
        custom_strategies = self.strategies.get("custom_strategies", {})
        if strategy_name in custom_strategies:
            return custom_strategies[strategy_name]
        
        logger.warning(f"Strategy '{strategy_name}' not found, using default strategy")
        return self.strategies.get("default_strategy", {})
    
    def list_available_strategies(self) -> List[Dict[str, str]]:
        """
        列出所有可用策略
        
        Returns:
            策略列表,每个策略包含name和description
        """
        strategies = []
        
        # 添加默认策略
        default = self.strategies.get("default_strategy", {})
        if default:
            strategies.append({
                "name": "default",
                "description": default.get("description", "默认策略")
            })
        
        # 添加自定义策略
        custom_strategies = self.strategies.get("custom_strategies", {})
        for name, config in custom_strategies.items():
            strategies.append({
                "name": name,
                "description": config.get("description", f"自定义策略: {name}")
            })
        
        return strategies
    
    def validate_role_selection(
        self, 
        selected_roles: List[str], 
        strategy_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        验证角色选择是否符合策略要求
        
        Args:
            selected_roles: 已选择的角色列表
            strategy_name: 使用的策略名称
        
        Returns:
            验证结果,包含is_valid和violations
        """
        strategy = self.get_strategy(strategy_name)
        violations = []
        
        # 检查角色数量
        min_roles = strategy.get("min_roles", 3)
        max_roles = strategy.get("max_roles", 8)
        
        if len(selected_roles) < min_roles:
            violations.append(f"角色数量不足: 需要至少{min_roles}个角色,当前只有{len(selected_roles)}个")
        
        if len(selected_roles) > max_roles:
            violations.append(f"角色数量过多: 最多允许{max_roles}个角色,当前有{len(selected_roles)}个")
        
        # 检查必选角色类别
        selection_rules = strategy.get("selection_rules", {})
        required_categories = selection_rules.get("required_categories", [])
        
        for required_cat in required_categories:
            # 检查是否有该类别的角色
            has_category = any(required_cat in role for role in selected_roles)
            if not has_category:
                violations.append(f"缺少必选角色类别: {required_cat}")
        
        return {
            "is_valid": len(violations) == 0,
            "violations": violations,
            "role_count": len(selected_roles),
            "min_roles": min_roles,
            "max_roles": max_roles
        }
    
    def get_task_template(self, role_category: str) -> List[str]:
        """
        获取角色的默认任务模板
        
        Args:
            role_category: 角色类别 (如 "V2_设计总监")
        
        Returns:
            任务列表
        """
        task_strategy = self.strategies.get("task_assignment_strategy", {})
        task_templates = task_strategy.get("task_templates", {})
        
        # 提取角色类别前缀 (如 "V2_设计总监_2-1" -> "V2_设计总监")
        category_prefix = "_".join(role_category.split("_")[:2])
        
        template = task_templates.get(category_prefix, {})
        return template.get("default_tasks", [
            f"分析{category_prefix}相关需求",
            f"制定{category_prefix}工作方案"
        ])
    
    def get_assignment_principles(self) -> List[str]:
        """获取任务分配原则"""
        task_strategy = self.strategies.get("task_assignment_strategy", {})
        return task_strategy.get("assignment_principles", [])
    
    def generate_decision_explanation(
        self,
        strategy_name: str,
        selected_roles: List[str],
        reasoning: str,
        alternatives: Optional[List[Dict]] = None,
        confidence: Optional[float] = None
    ) -> str:
        """
        生成决策说明
        
        Args:
            strategy_name: 使用的策略名称
            selected_roles: 选择的角色列表
            reasoning: 选择理由
            alternatives: 备选方案
            confidence: 置信度
        
        Returns:
            格式化的决策说明
        """
        strategy = self.get_strategy(strategy_name)
        transparency_config = self.strategies.get("decision_transparency", {})
        
        explanation = f"""
## 角色选择决策说明

### 选择策略
- **策略名称**: {strategy.get('name', strategy_name)}
- **策略描述**: {strategy.get('description', '无描述')}

### 选择的角色 ({len(selected_roles)}个)
"""
        for i, role in enumerate(selected_roles, 1):
            explanation += f"{i}. {role}\n"
        
        explanation += f"\n### 选择依据\n{reasoning}\n"
        
        # 添加备选方案
        if transparency_config.get("show_alternatives", True) and alternatives:
            explanation += "\n### 备选方案\n"
            for i, alt in enumerate(alternatives, 1):
                explanation += f"{i}. {alt.get('description', '无描述')} (评分: {alt.get('score', 'N/A')})\n"
        
        # 添加置信度
        if transparency_config.get("show_confidence", True) and confidence is not None:
            explanation += f"\n### 置信度评估\n整体置信度: {confidence:.1%}\n"
        
        return explanation
    
    def get_complementary_recommendations(
        self, 
        selected_roles: List[str],
        strategy_name: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        根据已选角色,获取互补性推荐
        
        Args:
            selected_roles: 已选择的角色列表
            strategy_name: 策略名称
        
        Returns:
            推荐列表,每项包含recommended_role和reason
        """
        strategy = self.get_strategy(strategy_name)
        selection_rules = strategy.get("selection_rules", {})
        complementary_rules = selection_rules.get("complementary_rules", [])
        
        recommendations = []
        
        for rule in complementary_rules:
            if_selected = rule.get("if_selected", "")
            then_recommend = rule.get("then_recommend", [])
            reason = rule.get("reason", "")
            
            # 检查是否有匹配的已选角色
            has_trigger = any(if_selected in role for role in selected_roles)
            
            if has_trigger:
                for recommended in then_recommend:
                    # 检查是否已经选择了推荐的角色
                    already_selected = any(recommended in role for role in selected_roles)
                    if not already_selected:
                        recommendations.append({
                            "recommended_role": recommended,
                            "reason": reason,
                            "triggered_by": if_selected
                        })
        
        return recommendations

