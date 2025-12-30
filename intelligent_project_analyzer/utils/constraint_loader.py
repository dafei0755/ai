"""
交付物约束加载器
Deliverable Constraints Loader

提供统一的接口加载和验证交付物类型与角色约束规则
"""

from typing import Dict, List, Optional, Tuple
from pathlib import Path
import yaml
from loguru import logger


class ConstraintLoader:
    """交付物约束加载器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化约束加载器

        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        if config_path is None:
            # 默认路径：config/deliverable_role_constraints.yaml
            current_dir = Path(__file__).parent.parent
            config_path = current_dir / "config" / "deliverable_role_constraints.yaml"

        self.config_path = Path(config_path)
        self._constraints = None
        self._role_boundaries = None
        self._validation_rules = None

        # 加载配置
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            self._constraints = config.get('constraints', {})
            self._role_boundaries = config.get('role_boundaries', {})
            self._validation_rules = config.get('validation_rules', {})

            logger.info(f"✅ 成功加载交付物约束配置：{len(self._constraints)} 个类型")

        except FileNotFoundError:
            logger.warning(f"⚠️ 约束配置文件不存在：{self.config_path}")
            self._constraints = {}
            self._role_boundaries = {}
            self._validation_rules = {}

        except Exception as e:
            logger.error(f"❌ 加载约束配置失败：{e}")
            self._constraints = {}
            self._role_boundaries = {}
            self._validation_rules = {}

    def get_constraints(self, deliverable_type: str) -> Dict:
        """
        获取指定交付物类型的约束规则

        Args:
            deliverable_type: 交付物类型（如：naming_list, design_strategy）

        Returns:
            约束字典，包含 must_include, must_exclude, optional, reason 等字段
        """
        if deliverable_type in self._constraints:
            return self._constraints[deliverable_type]

        # 如果类型未定义，返回custom规则
        logger.warning(f"⚠️ 交付物类型 '{deliverable_type}' 未定义，使用custom规则")
        return self._constraints.get('custom', {
            'must_include': [],
            'must_exclude': [],
            'optional': [],
            'reason': '自定义类型需根据具体内容判断'
        })

    def validate_role_allocation(
        self,
        deliverables: List[Dict],
        selected_roles: List[str]
    ) -> Tuple[bool, str]:
        """
        验证角色分配是否符合约束规则

        Args:
            deliverables: 交付物列表，每个交付物应包含 type 字段
            selected_roles: 已选择的角色ID列表（如：['V3-3', 'V4-1']）

        Returns:
            (is_valid, error_message): 验证结果和错误信息
        """
        # 提取角色前缀（V2, V3, V4, V5, V6）
        role_prefixes = set()
        for role_id in selected_roles:
            if role_id.startswith('V'):
                # 提取V2, V3等前缀
                prefix = role_id.split('_')[0] if '_' in role_id else role_id.split('-')[0]
                role_prefixes.add(prefix)

        logger.info(f"[约束验证] 当前激活的角色前缀：{role_prefixes}")

        # 遍历每个交付物，检查约束
        for deliverable in deliverables:
            d_type = deliverable.get('type', 'custom')
            d_desc = deliverable.get('description', d_type)

            # 获取约束规则
            constraints = self.get_constraints(d_type)

            # 检查1：must_include（必须包含的角色）
            must_include = constraints.get('must_include', [])
            for required_role in must_include:
                if required_role not in role_prefixes:
                    error_msg = (
                        f"❌ 交付物 '{d_desc}' (类型：{d_type}) 必须包含角色 {required_role}，但当前未激活\n"
                        f"当前激活的角色：{list(role_prefixes)}\n"
                        f"原因：{constraints.get('reason', '未说明')}"
                    )
                    logger.error(f"[约束验证] {error_msg}")
                    return False, error_msg

            # 检查2：must_exclude（禁止包含的角色）
            must_exclude = constraints.get('must_exclude', [])
            violated_roles = role_prefixes.intersection(set(must_exclude))
            if violated_roles:
                error_msg = (
                    f"❌ 交付物 '{d_desc}' (类型：{d_type}) 禁止激活角色 {list(violated_roles)}，但当前已激活\n"
                    f"当前激活的角色：{list(role_prefixes)}\n"
                    f"原因：{constraints.get('reason', '未说明')}"
                )
                logger.error(f"[约束验证] {error_msg}")
                return False, error_msg

        # 检查3：角色数量是否合理
        validation_rules = self._validation_rules.get('check_role_count', {})
        if validation_rules.get('enabled', True):
            max_roles = validation_rules.get('max_roles', 8)
            min_roles = validation_rules.get('min_roles', 2)

            if len(selected_roles) > max_roles:
                warning_msg = f"⚠️ 当前激活了 {len(selected_roles)} 个角色，超过最大建议数量 {max_roles}，可能存在冗余"
                logger.warning(f"[约束验证] {warning_msg}")
                # 这里只警告，不阻止

            if len(selected_roles) < min_roles:
                warning_msg = f"⚠️ 当前激活了 {len(selected_roles)} 个角色，少于最小建议数量 {min_roles}，可能不足"
                logger.warning(f"[约束验证] {warning_msg}")

        logger.info(f"[约束验证] ✅ 所有约束验证通过")
        return True, ""

    def validate_anti_pattern(
        self,
        deliverables: List[Dict],
        selected_roles: List[str]
    ) -> Tuple[bool, str]:
        """
        验证anti_pattern约束（从需求分析师的建议中读取）

        Args:
            deliverables: 交付物列表，可能包含 deliverable_owner_suggestion.anti_pattern 字段
            selected_roles: 已选择的角色ID列表

        Returns:
            (is_valid, error_message): 验证结果和错误信息
        """
        # 提取角色前缀
        role_prefixes = set()
        for role_id in selected_roles:
            if role_id.startswith('V'):
                prefix = role_id.split('_')[0] if '_' in role_id else role_id.split('-')[0]
                role_prefixes.add(prefix)

        # 遍历每个交付物，检查anti_pattern
        for deliverable in deliverables:
            d_desc = deliverable.get('description', deliverable.get('type', ''))

            # 获取anti_pattern（如果存在）
            owner_suggestion = deliverable.get('deliverable_owner_suggestion', {})
            anti_patterns = owner_suggestion.get('anti_pattern', [])

            if not anti_patterns:
                continue  # 如果没有anti_pattern，跳过

            logger.info(f"[anti_pattern验证] 交付物 '{d_desc}' 的anti_pattern：{anti_patterns}")

            # 检查是否有违规角色被激活
            for anti_pattern_prefix in anti_patterns:
                # 提取角色前缀（如："V2_设计总监" → "V2"）
                if anti_pattern_prefix.startswith('V'):
                    prefix = anti_pattern_prefix.split('_')[0]
                else:
                    prefix = anti_pattern_prefix

                if prefix in role_prefixes:
                    error_msg = (
                        f"❌ 交付物 '{d_desc}' 的anti_pattern检测失败\n"
                        f"禁止激活的角色 '{anti_pattern_prefix}' 被错误分配\n"
                        f"当前激活的角色：{list(role_prefixes)}\n"
                        f"建议：{owner_suggestion.get('owner_rationale', '未说明')}"
                    )
                    logger.error(f"[anti_pattern验证] {error_msg}")
                    return False, error_msg

        logger.info(f"[anti_pattern验证] ✅ 所有anti_pattern验证通过")
        return True, ""

    def get_role_boundary(self, role_prefix: str) -> Dict:
        """
        获取指定角色的能力边界定义

        Args:
            role_prefix: 角色前缀（如：V2_设计总监）

        Returns:
            能力边界字典
        """
        return self._role_boundaries.get(role_prefix, {})

    def suggest_roles_for_deliverable(self, deliverable_type: str) -> List[str]:
        """
        根据交付物类型推荐合适的角色

        Args:
            deliverable_type: 交付物类型

        Returns:
            推荐的角色列表（按优先级：must_include + optional）
        """
        constraints = self.get_constraints(deliverable_type)

        must_include = constraints.get('must_include', [])
        optional = constraints.get('optional', [])

        # 合并推荐列表
        suggested_roles = must_include + optional

        logger.info(f"[角色推荐] 交付物类型 '{deliverable_type}' 推荐角色：{suggested_roles}")
        return suggested_roles


# 全局单例
_constraint_loader = None


def get_constraint_loader(config_path: Optional[str] = None) -> ConstraintLoader:
    """
    获取约束加载器单例

    Args:
        config_path: 配置文件路径（可选）

    Returns:
        ConstraintLoader实例
    """
    global _constraint_loader
    if _constraint_loader is None:
        _constraint_loader = ConstraintLoader(config_path)
    return _constraint_loader


# 便捷函数
def load_constraints(deliverable_type: str) -> Dict:
    """快速加载指定交付物类型的约束"""
    loader = get_constraint_loader()
    return loader.get_constraints(deliverable_type)


def validate_allocation(deliverables: List[Dict], selected_roles: List[str]) -> Tuple[bool, str]:
    """快速验证角色分配"""
    loader = get_constraint_loader()

    # 先验证配置文件中的约束
    is_valid, error_msg = loader.validate_role_allocation(deliverables, selected_roles)
    if not is_valid:
        return False, error_msg

    # 再验证anti_pattern约束
    is_valid, error_msg = loader.validate_anti_pattern(deliverables, selected_roles)
    return is_valid, error_msg
