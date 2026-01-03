"""
内容安全守卫 - 检测违规内容（支持动态规则加载）
"""

import re
from typing import Any, Dict, List, Optional

from loguru import logger


class ContentSafetyGuard:
    """内容安全守卫（支持动态规则）"""

    def __init__(
        self,
        llm_model=None,
        use_external_api: bool = False,
        use_dynamic_rules: bool = True,
        enable_evasion_check: Optional[bool] = None,
        enable_privacy_check: Optional[bool] = None,
    ):
        """
        初始化内容安全守卫

        Args:
            llm_model: LLM模型实例（用于深度语义检测）
            use_external_api: 是否使用外部API（腾讯云内容安全）
            use_dynamic_rules: 是否使用动态规则加载（默认True）
            enable_evasion_check: 是否启用变形规避检测。为 None 时，将根据 use_external_api 自动启用/禁用。
            enable_privacy_check: 是否启用隐私信息检测。为 None 时，将根据 use_external_api 自动启用/禁用。
        """
        self.llm_model = llm_model
        self.use_external_api = use_external_api
        self.use_dynamic_rules = use_dynamic_rules

        # 设计项目默认不做隐私/规避正则检测（避免误报），但在“全功能/生产级”模式下应启用。
        self.enable_privacy_check = enable_privacy_check if enable_privacy_check is not None else bool(use_external_api)
        self.enable_evasion_check = enable_evasion_check if enable_evasion_check is not None else bool(use_external_api)

        # 动态规则加载器（懒加载）
        self._rule_loader = None

        # 回退规则（如果动态规则加载失败）
        self.FALLBACK_KEYWORDS = {
            "政治敏感": [],
            "色情低俗": ["色情", "黄色", "裸体", "性爱"],
            "暴力血腥": ["杀人", "自杀", "血腥", "暴力", "屠杀", "谋杀"],
            "违法犯罪": ["毒品", "诈骗", "洗钱", "赌博", "走私", "贩卖"],
            "歧视仇恨": ["歧视", "仇恨", "种族", "歧视性"],
        }

    @property
    def rule_loader(self):
        """懒加载规则加载器"""
        if self._rule_loader is None and self.use_dynamic_rules:
            try:
                from .dynamic_rule_loader import get_rule_loader

                self._rule_loader = get_rule_loader()
                logger.info("✅ 动态规则加载器已启用")
            except Exception as e:
                logger.warning(f"⚠️ 动态规则加载器初始化失败，使用回退规则: {e}")
                self.use_dynamic_rules = False
        return self._rule_loader

    def check(self, text: str, context: str = "input") -> Dict[str, Any]:
        """
        检查内容安全

        Args:
            text: 待检测文本
            context: 上下文（input/output/report）

        Returns:
            {
                "is_safe": bool,
                "risk_level": "safe" | "low" | "medium" | "high",
                "violations": List[Dict],
                "sanitized_text": str  # 如果可修复
            }
        """
        violations = []

        # 1. 关键词检测（快速过滤）
        keyword_violations = self._check_keywords(text)
        violations.extend(keyword_violations)

        # 2. 正则模式检测
        pattern_violations = self._check_patterns(text)
        violations.extend(pattern_violations)

        # 3. 外部API检测（推荐生产环境）
        if self.use_external_api:
            try:
                api_violations = self._check_with_external_api(text)
                violations.extend(api_violations)
            except Exception as e:
                logger.warning(f"⚠️ 外部API检测失败: {e}")

        # 4. LLM深度检测（可选，用于语义理解）
        if len(violations) == 0 and self.llm_model:
            try:
                llm_result = self._llm_safety_check(text)
                if not llm_result["is_safe"]:
                    violations.append(llm_result["violation"])
            except Exception as e:
                logger.warning(f"⚠️ LLM安全检测失败: {e}")

        # 5. 综合判断（改进：更宽容、更智能）
        if len(violations) == 0:
            return {"is_safe": True, "risk_level": "safe", "violations": []}

        # 5.1 仅正则命中（隐私/规避）时：在 full features 模式下应判定为不安全
        regex_violations = [
            v for v in violations if v.get("method") == "regex_match" and v.get("category") in ("隐私信息", "变形规避")
        ]
        keyword_violations_present = any(v.get("method") == "keyword_match" for v in violations)

        if regex_violations and not keyword_violations_present:
            severity_order = {"low": 1, "medium": 2, "high": 3}
            max_sev = max((v.get("severity") or "low") for v in regex_violations)
            # 防御性：未知 severity 统一按 low
            if max_sev not in severity_order:
                max_sev = "low"

            return {
                "is_safe": False,
                "risk_level": max_sev,
                "violations": violations,
                "action": "sanitize",
            }

        # 统计违规情况
        high_severity = sum(1 for v in violations if v.get("severity") == "high")
        medium_severity = sum(1 for v in violations if v.get("severity") == "medium")
        low_severity = sum(1 for v in violations if v.get("severity") == "low")

        # 计算文本长度（用于比例判断）
        text_length = len(text)
        violation_density = len(violations) / max(text_length / 100, 1)  # 每100字的违规数

        # 判断严重性（更宽容的策略）
        # 1. 高危内容：有 high 级别的违规
        if high_severity > 0:
            # 但如果只有1个 high 且文本较长（超过200字），可能是学术讨论
            if high_severity == 1 and text_length > 200:
                logger.warning(f"⚠️ 检测到1个高危词汇，但文本较长({text_length}字)，可能是学术/专业讨论，降级处理")
                return {
                    "is_safe": True,  # 改为True，允许通过
                    "risk_level": "safe",
                    "violations": [],  # 不返回违规
                    "action": "allow",
                    "message": "检测到少量敏感词汇，但考虑到文本长度和上下文，判定为学术/专业讨论",
                }

            # 多个 high 或非常短的文本中的 high，拒绝
            return {"is_safe": False, "risk_level": "high", "violations": violations, "action": "reject"}

        # 2. 中危内容：有 medium 级别的违规
        if medium_severity > 0:
            # 如果只有1-2个 medium，且文本不短（超过500字），放行
            if medium_severity <= 2 and text_length > 500:
                logger.info(f"✅ 检测到{medium_severity}个中危词汇，文本较长({text_length}字)，判定为正常使用，放行")
                return {
                    "is_safe": True,
                    "risk_level": "safe",
                    "violations": [],  # 不返回违规，避免日志污染
                    "action": "allow",
                    "message": "检测到少量敏感词汇，但判断为学术/专业讨论，已放行",
                }

            # 多个 medium 或短文本，拒绝
            if medium_severity > 3 or (medium_severity > 1 and text_length < 200):
                return {"is_safe": False, "risk_level": "medium", "violations": violations, "action": "reject"}

            # 其他情况，警告但放行
            return {
                "is_safe": True,
                "risk_level": "safe",
                "violations": [],
                "action": "allow",
                "message": "检测到少量中危词汇，但未达到拦截阈值",
            }

        # 3. 低危内容：只有 low 级别的违规
        if low_severity > 0:
            # low 级别一般不拦截，除非密度过高
            if violation_density > 0.1:  # 每100字超过10个违规
                logger.warning(f"⚠️ 低危违规密度过高({violation_density:.2f}/100字)，拒绝")
                return {"is_safe": False, "risk_level": "medium", "violations": violations, "action": "reject"}

            # 正常情况，放行
            logger.info(f"✅ 仅有{low_severity}个低危违规，判定为正常，放行")
            return {"is_safe": True, "risk_level": "safe", "violations": [], "action": "allow"}

        # 默认情况（不应该到达这里）
        return {"is_safe": False, "risk_level": "medium", "violations": violations, "action": "sanitize"}

    def _check_keywords(self, text: str) -> List[Dict]:
        """关键词检测（使用动态规则）"""
        violations = []
        text_lower = text.lower()

        # 获取关键词规则
        if self.use_dynamic_rules and self.rule_loader:
            try:
                keywords_config = self.rule_loader.get_keywords()
            except Exception as e:
                logger.warning(f"⚠️ 获取动态关键词失败，使用回退规则: {e}")
                keywords_config = self.FALLBACK_KEYWORDS
        else:
            keywords_config = self.FALLBACK_KEYWORDS

        # 检测关键词
        for category, config in keywords_config.items():
            # 支持新格式（字典）和旧格式（列表）
            if isinstance(config, dict):
                if not config.get("enabled", True):
                    continue  # 跳过禁用的类别
                keywords = config.get("words", [])
                severity = config.get("severity", "high")
            else:
                keywords = config
                severity = "high"

            matched = [kw for kw in keywords if kw in text_lower]
            if matched:
                violations.append(
                    {"category": category, "matched_keywords": matched, "severity": severity, "method": "keyword_match"}
                )

        return violations

    def _check_patterns(self, text: str) -> List[Dict]:
        """正则模式检测（隐私信息和变形规避）"""
        # 两类正则都关闭时直接跳过
        if not self.enable_privacy_check and not self.enable_evasion_check:
            logger.debug("⏭️ 正则检测已禁用（隐私/规避均关闭），跳过")
            return []

        try:
            from .enhanced_regex_detector import EnhancedRegexDetector

            # 创建增强检测器实例
            detector = EnhancedRegexDetector(
                enable_privacy_check=self.enable_privacy_check,
                enable_evasion_check=self.enable_evasion_check,
            )

            # 执行检测
            violations = detector.check(text)

            return violations

        except Exception as e:
            logger.warning(f"⚠️ 增强正则检测失败，回退到基础检测: {e}")
            # 回退到基础检测（仅覆盖手机号/身份证）
            return self._check_patterns_basic(text) if self.enable_privacy_check else []

    def _check_patterns_basic(self, text: str) -> List[Dict]:
        """基础正则模式检测（保留作为回退方案）"""
        violations = []

        # 检测手机号
        phone_pattern = r"1[3-9]\d{9}"
        if re.search(phone_pattern, text):
            violations.append(
                {"category": "隐私信息", "matched_pattern": "手机号", "severity": "low", "method": "regex_match"}
            )

        # 检测身份证号
        id_pattern = r"\d{17}[\dXx]"
        if re.search(id_pattern, text):
            violations.append(
                {"category": "隐私信息", "matched_pattern": "身份证号", "severity": "medium", "method": "regex_match"}
            )

        return violations

    def _check_with_external_api(self, text: str) -> List[Dict]:
        """
        调用外部内容安全API

        推荐：
        1. 腾讯云内容安全（已集成）
        2. 阿里云内容安全：https://help.aliyun.com/document_detail/53427.html
        3. 百度内容审核：https://ai.baidu.com/tech/textcensoring
        """
        try:
            # 导入腾讯云客户端
            from .tencent_content_safety import get_tencent_content_safety_client

            # 获取客户端实例
            client = get_tencent_content_safety_client()
            if client is None:
                logger.debug("腾讯云内容安全未启用，跳过外部API检测")
                return []

            # 调用检测
            result = client.check_text(text)

            # 如果安全，返回空列表
            if result.get("is_safe", True):
                return []

            # 返回违规信息
            return result.get("violations", [])

        except Exception as e:
            logger.warning(f"⚠️ 外部API检测失败: {e}")
            return []

    def _llm_safety_check(self, text: str) -> Dict:
        """使用LLM进行深度语义安全检测"""
        if not self.llm_model:
            return {"is_safe": True}

        try:
            from .llm_safety_detector import LLMSafetyDetector

            # 创建检测器实例
            detector = LLMSafetyDetector(llm_model=self.llm_model, confidence_threshold=0.7)  # 置信度阈值

            # 执行检测
            result = detector.check(text, mode="normal")

            # 如果安全或置信度低，返回安全
            if result["is_safe"] or result.get("confidence", 0) < 0.7:
                return {"is_safe": True}

            # 构建违规信息
            violation = result.get("violation", {})
            violation["method"] = "llm_semantic_analysis"

            return {"is_safe": False, "violation": violation}

        except Exception as e:
            logger.error(f"❌ LLM安全检测异常: {e}")
            return {"is_safe": True}  # 出错时假定安全，避免误拦截
