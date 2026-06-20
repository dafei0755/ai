"""Insight-quality evaluator for demand reconstruction outputs."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


class DemandReconstructionInsightQualityEvaluator:
    """Detect whether first-screen demand reconstruction preserves deep signals."""

    _SIGNAL_TERMS = {
        "life_stage": ("50岁", "中年", "后半场", "人生阶段", "事业回望", "功成名就", "创业"),
        "professional_identity": ("室内设计师", "设计师", "建筑师", "职业身份", "专业经验"),
        "returning_home": ("背井离乡", "老家", "故乡", "返乡", "故土", "回归"),
        "dwelling_as_return": ("民居", "身心安放", "家族", "童年", "容器", "安放"),
    }
    _CAPTURE_TERMS = {
        "style_over_capture": ("风格标签", "网红", "侘寂风", "材料气质", "氛围感"),
        "hard_constraint_over_capture": ("施工条件", "硬性条件", "尺寸", "设备", "工艺上限", "预算表"),
    }

    def evaluate(
        self,
        *,
        source_message: str,
        semantic_package: Optional[Dict[str, Any]] = None,
        latent_model: Optional[Dict[str, Any]] = None,
        blueprint: Optional[Dict[str, Any]] = None,
        visible_reply: str = "",
    ) -> Dict[str, Any]:
        source_text = str(source_message or "")
        semantic_package = semantic_package or {}
        latent_model = latent_model or {}
        blueprint = blueprint or {}
        combined_visible = "\n".join(
            [
                visible_reply,
                str(blueprint.get("task_reframe") or ""),
                str(blueprint.get("primary_risk") or ""),
                str(blueprint.get("project_viability_judgment") or ""),
            ]
        )
        latent_text = self._flatten(latent_model)

        expected = self._expected_signals(source_text, semantic_package, latent_model)
        missing = [signal for signal in expected if not self._signal_preserved(signal, combined_visible, latent_text)]
        anti_capture_checks = self._anti_capture_checks(expected, combined_visible)
        affect = self._evaluate_evidence_bound_affect(latent_model, combined_visible)

        warning_issues = []
        for signal in missing:
            warning_issues.append({"code": "missing_high_value_signal", "signal": signal})
        for check_id, check in anti_capture_checks.items():
            if check.get("status") == "fail":
                warning_issues.append({"code": check_id, "signal": check.get("evidence")})

        if missing:
            level = "semantic_pass"
        elif affect.get("status") == "pass" and self._has_trust_language(combined_visible):
            level = "trust_pass"
        else:
            level = "insight_pass"

        score = 1.0 - (0.16 * len(missing)) - (0.12 * sum(1 for c in anti_capture_checks.values() if c.get("status") == "fail"))
        score = max(0.0, min(1.0, round(score, 3)))

        return {
            "schema_version": "demand_reconstruction_insight_quality.v1",
            "level": level,
            "score": score,
            "expected_high_value_signals": expected,
            "missing_high_value_signals": missing,
            "anti_capture_checks": anti_capture_checks,
            "evidence_bound_affect": affect,
            "warning_issues": warning_issues,
        }

    def _expected_signals(
        self,
        source_text: str,
        semantic_package: Dict[str, Any],
        latent_model: Dict[str, Any],
    ) -> List[str]:
        expected: List[str] = []
        for signal, terms in self._SIGNAL_TERMS.items():
            if self._contains_any(source_text, terms):
                expected.append(signal)
        latent_text = self._flatten(latent_model)
        for signal, terms in self._SIGNAL_TERMS.items():
            if signal not in expected and self._contains_any(latent_text, terms):
                expected.append(signal)
        semantic_text = self._flatten(semantic_package)
        for signal, terms in self._SIGNAL_TERMS.items():
            if signal not in expected and self._contains_any(semantic_text, terms):
                expected.append(signal)
        return expected

    def _signal_preserved(self, signal: str, visible_text: str, latent_text: str) -> bool:
        text = visible_text + "\n" + latent_text
        signal_terms = {
            "life_stage": ("50岁", "中年", "后半场", "人生阶段", "事业回望", "创业", "功成名就"),
            "professional_identity": ("室内设计师", "设计师", "专业经验", "职业身份"),
            "returning_home": ("背井离乡", "老家", "故乡", "返乡", "故土", "回归"),
            "dwelling_as_return": ("民居", "身心安放", "家族", "童年", "容器", "安放"),
        }
        return self._contains_any(text, signal_terms.get(signal, ()))

    def _anti_capture_checks(self, expected: List[str], visible_text: str) -> Dict[str, Dict[str, Any]]:
        checks: Dict[str, Dict[str, Any]] = {}
        style_risk = any(signal in expected for signal in ("life_stage", "returning_home", "dwelling_as_return"))
        hard_risk = any(signal in expected for signal in ("professional_identity", "returning_home"))
        checks["style_over_capture"] = self._capture_status(style_risk, visible_text, self._CAPTURE_TERMS["style_over_capture"])
        checks["hard_constraint_over_capture"] = self._capture_status(hard_risk, visible_text, self._CAPTURE_TERMS["hard_constraint_over_capture"])
        return checks

    @staticmethod
    def _capture_status(risk: bool, visible_text: str, terms: Iterable[str]) -> Dict[str, Any]:
        hits = [term for term in terms if term in visible_text]
        if risk and hits:
            return {"status": "fail", "evidence": hits}
        return {"status": "pass", "evidence": hits}

    def _evaluate_evidence_bound_affect(self, latent_model: Dict[str, Any], visible_text: str) -> Dict[str, Any]:
        items = latent_model.get("evidence_bound_affect") or []
        if not isinstance(items, list) or not items:
            return {"status": "not_applicable", "matched_terms": []}
        matched_terms: List[str] = []
        missing_refs = False
        for item in items:
            if not isinstance(item, dict):
                continue
            if not item.get("evidence_refs"):
                missing_refs = True
            for term in item.get("allowed_terms") or []:
                if str(term) and str(term) in visible_text:
                    matched_terms.append(str(term))
        if missing_refs:
            return {"status": "fail", "reason": "missing_evidence_refs", "matched_terms": matched_terms}
        if matched_terms:
            return {"status": "pass", "matched_terms": sorted(set(matched_terms))}
        return {"status": "warn", "reason": "no_visible_affect_term", "matched_terms": []}

    @staticmethod
    def _has_trust_language(text: str) -> bool:
        return any(term in text for term in ("不是", "而是", "真正", "核心", "先不急"))

    @staticmethod
    def _contains_any(text: str, terms: Iterable[str]) -> bool:
        return any(term in text for term in terms if term)

    def _flatten(self, value: Any) -> str:
        if isinstance(value, dict):
            return " ".join(f"{key} {self._flatten(item)}" for key, item in value.items())
        if isinstance(value, list):
            return " ".join(self._flatten(item) for item in value)
        return str(value or "")
