"""
模式验证标准加载器（Mode Validation Criteria Loader）
v7.750 P1-Task3

目的：
加载MODE_VALIDATION_CRITERIA.yaml并提供验证功能，
让ability_validator.py能够基于模式特征验证专家输出。

核心功能：
1. 加载验证标准配置
2. 根据模式ID获取验证规则
3. 执行关键词匹配验证
4. 计算验证分数
"""

import yaml
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationResult:
    """验证结果"""

    mode_id: str
    mode_name: str
    passed: bool
    score: float  # 0.0 - 1.0
    feature_checks: List[Dict[str, Any]]  # 各特征检查详情
    missing_features: List[str]
    validation_summary: str


class ModeValidationCriteriaLoader:
    """模式验证标准加载器"""

    _config_cache = None
    _config_path = None

    @classmethod
    def _load_config(cls) -> Dict[str, Any]:
        """加载配置文件（带缓存）"""
        if cls._config_cache is not None:
            return cls._config_cache

        # 定位配置文件
        if cls._config_path is None:
            current_dir = Path(__file__).parent
            config_dir = current_dir.parent / "config"
            cls._config_path = config_dir / "MODE_VALIDATION_CRITERIA.yaml"

        if not cls._config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {cls._config_path}")

        # 加载YAML
        with open(cls._config_path, "r", encoding="utf-8") as f:
            cls._config_cache = yaml.safe_load(f)

        return cls._config_cache

    @classmethod
    def get_validation_criteria(cls, mode_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定模式的验证标准

        Args:
            mode_id: 模式ID，例如 "M1_concept_driven"

        Returns:
            验证标准字典，包含core_features, required_elements, quality_metrics
        """
        config = cls._load_config()
        return config.get(mode_id)

    @classmethod
    def get_global_config(cls) -> Dict[str, Any]:
        """获取全局配置"""
        config = cls._load_config()
        return config.get("global_config", {})

    @classmethod
    def get_strictness_level(cls, mode_id: str) -> float:
        """
        获取指定模式的验证严格程度

        Returns:
            严格程度分数 (0.3 - 0.7)
        """
        global_config = cls.get_global_config()

        # 检查是否有模式特定覆盖
        mode_specific = global_config.get("mode_specific_strictness", {})
        if mode_id in mode_specific:
            strictness_name = mode_specific[mode_id]
        else:
            strictness_name = global_config.get("default_strictness", "medium")

        # 转换为数值
        strictness_values = global_config.get("validation_strictness", {})
        return strictness_values.get(strictness_name, 0.5)

    @classmethod
    def validate_expert_output(
        cls, mode_id: str, expert_output: str, strictness_override: Optional[float] = None
    ) -> ValidationResult:
        """
        验证专家输出是否符合模式特征

        Args:
            mode_id: 模式ID
            expert_output: 专家输出文本
            strictness_override: 覆盖默认严格程度

        Returns:
            ValidationResult对象
        """
        criteria = cls.get_validation_criteria(mode_id)
        if not criteria:
            return ValidationResult(
                mode_id=mode_id,
                mode_name="Unknown Mode",
                passed=True,  # 无验证标准则默认通过
                score=1.0,
                feature_checks=[],
                missing_features=[],
                validation_summary="无验证标准，默认通过",
            )

        mode_name = criteria.get("mode_name", mode_id)
        core_features = criteria.get("core_features", [])

        # 获取严格程度
        strictness = strictness_override if strictness_override is not None else cls.get_strictness_level(mode_id)

        # 逐个检查核心特征
        feature_checks = []
        total_weight = 0.0
        weighted_score = 0.0
        missing_features = []

        for feature in core_features:
            feature_id = feature.get("feature_id", "")
            feature_name = feature.get("feature_name", "")
            keywords = feature.get("validation_keywords", [])
            rule = feature.get("validation_rule", "must_contain_at_least_1_keyword")
            weight = feature.get("weight", 0.1)

            # 检查关键词匹配
            match_result = cls._check_keywords_in_text(expert_output, keywords, rule)

            feature_checks.append(
                {
                    "feature_id": feature_id,
                    "feature_name": feature_name,
                    "passed": match_result["passed"],
                    "matched_keywords": match_result["matched_keywords"],
                    "match_ratio": match_result["match_ratio"],
                    "weight": weight,
                    "rule": rule,
                }
            )

            total_weight += weight
            if match_result["passed"]:
                weighted_score += weight
            else:
                # 如果规则不是recommended，则记录为缺失
                if rule != "recommended":
                    missing_features.append(feature_name)

        # 计算最终分数
        final_score = weighted_score / total_weight if total_weight > 0 else 0.0

        # 判断是否通过
        passed = final_score >= strictness

        # 生成验证总结
        validation_summary = cls._generate_validation_summary(
            mode_name, passed, final_score, strictness, missing_features
        )

        return ValidationResult(
            mode_id=mode_id,
            mode_name=mode_name,
            passed=passed,
            score=round(final_score, 2),
            feature_checks=feature_checks,
            missing_features=missing_features,
            validation_summary=validation_summary,
        )

    @classmethod
    def validate_multiple_modes(
        cls, detected_modes: List[Dict[str, Any]], expert_output: str, confidence_threshold: float = 0.3
    ) -> List[ValidationResult]:
        """
        验证多个模式

        Args:
            detected_modes: 检测到的模式列表 [{"mode": "M1_concept_driven", "confidence": 0.85}, ...]
            expert_output: 专家输出文本
            confidence_threshold: 模式置信度阈值

        Returns:
            验证结果列表
        """
        results = []

        for mode_info in detected_modes:
            mode_id = mode_info.get("mode", "")
            confidence = mode_info.get("confidence", 0)

            # 过滤低置信度模式
            if confidence < confidence_threshold:
                continue

            # 执行验证
            result = cls.validate_expert_output(mode_id, expert_output)
            results.append(result)

        return results

    @classmethod
    def _check_keywords_in_text(cls, text: str, keywords: List[str], rule: str) -> Dict[str, Any]:
        """
        检查文本中的关键词匹配情况

        Args:
            text: 待检查文本
            keywords: 关键词列表
            rule: 验证规则
                - "must_contain_at_least_1_keyword": 至少包含1个
                - "must_contain_at_least_2_keywords": 至少包含2个
                - "recommended": 推荐但非必需

        Returns:
            {
                "passed": bool,
                "matched_keywords": List[str],
                "match_ratio": float
            }
        """
        if not keywords:
            return {"passed": True, "matched_keywords": [], "match_ratio": 1.0}

        text_lower = text.lower()
        matched_keywords = []

        for keyword in keywords:
            # 中文关键词直接使用in检查
            keyword_lower = keyword.lower()
            if keyword_lower in text_lower:
                matched_keywords.append(keyword)

        match_ratio = len(matched_keywords) / len(keywords)

        # 根据规则判断是否通过
        if rule == "must_contain_at_least_1_keyword":
            passed = len(matched_keywords) >= 1
        elif rule == "must_contain_at_least_2_keywords":
            passed = len(matched_keywords) >= 2
        elif rule == "recommended":
            passed = True  # 推荐项总是通过
        else:
            passed = match_ratio >= 0.5  # 默认要求50%匹配

        return {"passed": passed, "matched_keywords": matched_keywords, "match_ratio": round(match_ratio, 2)}

    @classmethod
    def _generate_validation_summary(
        cls, mode_name: str, passed: bool, score: float, strictness: float, missing_features: List[str]
    ) -> str:
        """生成验证总结"""
        if passed:
            return f"✅ {mode_name}验证通过 (得分{score:.2f} >= 阈值{strictness:.2f})"
        else:
            missing_str = ", ".join(missing_features[:3])  # 只显示前3个
            if len(missing_features) > 3:
                missing_str += f" 等{len(missing_features)}项"

            return f"⚠️ {mode_name}验证未通过 (得分{score:.2f} < 阈值{strictness:.2f}) - " f"缺失特征: {missing_str}"


# 便捷函数：用于ability_validator.py中调用
def validate_mode_features(detected_modes: List[Dict[str, Any]], expert_output: str) -> List[ValidationResult]:
    """
    便捷调用函数

    使用方式（在ability_validator.py中）:

    ```python
    from ..services.mode_validation_loader import validate_mode_features

    # 假设state中有detected_modes
    detected_modes = state.get("detected_design_modes", [])
    expert_output = deliverable.get("content", "")

    # 执行模式验证
    validation_results = validate_mode_features(detected_modes, expert_output)

    for result in validation_results:
        if not result.passed:
            logger.warning(f"[ModeValidation] {result.validation_summary}")
    ```
    """
    return ModeValidationCriteriaLoader.validate_multiple_modes(
        detected_modes=detected_modes, expert_output=expert_output
    )
