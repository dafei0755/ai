"""
Requirements Validator - v7.270

✅ ACTIVE (v9.1 修正): 该组件仍被 requirements_analyst.py (L863) 和 async_post_processor.py 活跃调用。
此前误标为 DEPRECATED，现已更正。validate_phase2_output() 是 Phase2 输出的关键质量校验环节。

Validate requirements analysis output quality and completeness.

Validation checks:
1. L6 assumption audit presence and quality (at least 3 assumptions)
2. L7 systemic impact presence and completeness (short/medium/long term)
3. Human dimensions depth (no generic phrases)
4. L2 perspective activation (correct perspectives for project type)
5. Overall quality scoring

Author: AI Assistant
Date: 2026-01-25
"""

from typing import Dict, Any, List
from loguru import logger


class ValidationResult:
    """Validation result with issues and suggestions"""

    def __init__(self):
        self.is_valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.suggestions: List[str] = []
        self.quality_score = 1.0
        self.validation_details: Dict[str, Any] = {}

    def add_error(self, message: str):
        """Add an error (makes validation invalid)"""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str):
        """Add a warning (doesn't invalidate, but flags issue)"""
        self.warnings.append(message)

    def add_suggestion(self, message: str):
        """Add a suggestion for improvement"""
        self.suggestions.append(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/debugging"""
        return {
            "is_valid": self.is_valid,
            "quality_score": self.quality_score,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "validation_details": self.validation_details,
        }


class RequirementsValidator:
    """Validate requirements analysis output quality"""

    # Generic phrases to detect in human dimensions
    GENERIC_PHRASES = [
        "温馨",
        "舒适",
        "有归属感",
        "品质生活",
        "家庭氛围",
        "高端",
        "大气",
        "上档次",
        "有品位",
        "有格调",
        "现代感",
        "时尚感",
        "科技感",
        "未来感",
        "待进一步分析",
        "待明确",
        "待补齐",
        "待识别",
    ]

    def __init__(self):
        """Initialize validator"""
        pass

    def validate_phase2_output(self, phase2_result: Dict[str, Any]) -> ValidationResult:
        """
        Comprehensive validation of Phase 2 output

        Args:
            phase2_result: Phase 2 analysis result

        Returns:
            ValidationResult with errors, warnings, and quality score
        """
        result = ValidationResult()

        logger.info(" [Validation] Starting Phase 2 output validation")

        # Check L6 assumption audit
        self._validate_l6_assumption_audit(phase2_result, result)

        # Check L7 systemic impact
        self._validate_l7_systemic_impact(phase2_result, result)

        # Check human dimensions depth
        self._validate_human_dimensions(phase2_result, result)

        # Check L2 perspective activation
        self._validate_l2_perspectives(phase2_result, result)

        # Check expert handoff completeness
        self._validate_expert_handoff(phase2_result, result)

        # Calculate overall quality score
        result.quality_score = self._calculate_quality_score(result)

        # Log validation summary
        if result.is_valid:
            logger.info(f" [Validation] Phase 2 output valid (quality: {result.quality_score:.2f})")
        else:
            logger.warning(f"️ [Validation] Phase 2 output invalid: {len(result.errors)} errors")
            for error in result.errors:
                logger.warning(f"   - {error}")

        if result.warnings:
            logger.info(f"️ [Validation] {len(result.warnings)} warnings:")
            for warning in result.warnings:
                logger.info(f"   - {warning}")

        return result

    def _validate_l6_assumption_audit(self, data: Dict[str, Any], result: ValidationResult):
        """
        Ensure L6 has at least 3 assumptions with challenges

        L6 structure:
        {
            "identified_assumptions": [
                {
                    "assumption": "...",
                    "counter_assumption": "...",
                    "challenge_question": "...",
                    "impact_if_wrong": "...",
                    "alternative_approach": "..."
                }
            ],
            "unconventional_approaches": [...]
        }
        """
        l6 = data.get("analysis_layers", {}).get("L6_assumption_audit", {})
        assumptions = l6.get("identified_assumptions", [])

        # Check presence
        if not l6:
            result.add_error("L6_assumption_audit is missing entirely")
            result.validation_details["l6_present"] = False
            return

        result.validation_details["l6_present"] = True

        # Check minimum count
        if len(assumptions) < 3:
            result.add_error(f"L6 assumption audit incomplete: found {len(assumptions)} assumptions, need at least 3")
            result.validation_details["l6_count"] = len(assumptions)
            return

        result.validation_details["l6_count"] = len(assumptions)

        # Check each assumption has required fields
        required_fields = [
            "assumption",
            "counter_assumption",
            "challenge_question",
            "impact_if_wrong",
            "alternative_approach",
        ]

        incomplete_assumptions = []
        for i, assumption in enumerate(assumptions):
            missing = [f for f in required_fields if not assumption.get(f)]
            if missing:
                incomplete_assumptions.append((i + 1, missing))

        if incomplete_assumptions:
            for idx, missing in incomplete_assumptions:
                result.add_warning(f"L6 assumption {idx} missing fields: {', '.join(missing)}")

        # Check for depth (not just placeholder text)
        shallow_assumptions = []
        for i, assumption in enumerate(assumptions):
            assumption_text = assumption.get("assumption", "")
            if len(assumption_text) < 20 or "待" in assumption_text:
                shallow_assumptions.append(i + 1)

        if shallow_assumptions:
            result.add_warning(f"L6 assumptions {shallow_assumptions} appear shallow or incomplete")

        result.validation_details["l6_quality"] = (
            "good" if not incomplete_assumptions and not shallow_assumptions else "needs_improvement"
        )

    def _validate_l7_systemic_impact(self, data: Dict[str, Any], result: ValidationResult):
        """
        Ensure L7 covers short/medium/long term

        L7 structure:
        {
            "short_term": {"social": "...", "environmental": "...", ...},
            "medium_term": {...},
            "long_term": {...},
            "unintended_consequences": [...],
            "mitigation_strategies": [...]
        }
        """
        l7 = data.get("analysis_layers", {}).get("L7_systemic_impact", {})

        # Check presence
        if not l7:
            result.add_error("L7_systemic_impact is missing entirely")
            result.validation_details["l7_present"] = False
            return

        result.validation_details["l7_present"] = True

        # Check time dimensions
        required_terms = ["short_term", "medium_term", "long_term"]
        missing_terms = [t for t in required_terms if not l7.get(t)]

        if missing_terms:
            result.add_error(f"L7 systemic impact incomplete: missing time dimensions {missing_terms}")
            result.validation_details["l7_time_dimensions"] = [t for t in required_terms if t not in missing_terms]
            return

        result.validation_details["l7_time_dimensions"] = required_terms

        # Check each time dimension has impact categories
        impact_categories = ["social", "environmental", "economic", "cultural"]

        for term in required_terms:
            term_data = l7.get(term, {})
            if not isinstance(term_data, dict):
                result.add_warning(f"L7 {term} is not a dictionary structure")
                continue

            present_categories = [cat for cat in impact_categories if term_data.get(cat)]
            if len(present_categories) < 2:
                result.add_warning(
                    f"L7 {term} has only {len(present_categories)} impact categories, recommend at least 2"
                )

        # Check unintended consequences
        unintended = l7.get("unintended_consequences", [])
        if not unintended or len(unintended) < 2:
            result.add_warning(f"L7 should identify at least 2 unintended consequences (found {len(unintended)})")

        result.validation_details["l7_unintended_count"] = len(unintended)

        # Check mitigation strategies
        mitigation = l7.get("mitigation_strategies", [])
        if not mitigation:
            result.add_suggestion("L7 should include mitigation strategies for identified risks")

        result.validation_details["l7_quality"] = (
            "good" if not missing_terms and len(unintended) >= 2 else "needs_improvement"
        )

    def _validate_human_dimensions(self, data: Dict[str, Any], result: ValidationResult):
        """
        Check human dimensions are specific, not generic

        Human dimensions:
        - emotional_landscape
        - spiritual_aspirations
        - psychological_safety_needs
        - ritual_behaviors
        - memory_anchors
        """
        structured = data.get("structured_output", {})
        dimensions = [
            "emotional_landscape",
            "spiritual_aspirations",
            "psychological_safety_needs",
            "ritual_behaviors",
            "memory_anchors",
        ]

        result.validation_details["human_dimensions"] = {}

        for dim in dimensions:
            value = structured.get(dim, "")

            dim_result = {
                "present": bool(value),
                "length": len(value),
                "has_generic_phrases": False,
                "quality": "unknown",
            }

            # Check presence and length
            if not value or len(value) < 20:
                result.add_warning(f"{dim} too short or missing (length: {len(value)})")
                dim_result["quality"] = "too_short"
            else:
                # Check for generic phrases
                generic_found = [phrase for phrase in self.GENERIC_PHRASES if phrase in value]
                if generic_found:
                    result.add_warning(f"{dim} contains generic phrases: {', '.join(generic_found[:3])}")
                    dim_result["has_generic_phrases"] = True
                    dim_result["generic_phrases"] = generic_found
                    dim_result["quality"] = "generic"
                else:
                    dim_result["quality"] = "good"

            result.validation_details["human_dimensions"][dim] = dim_result

        # Overall human dimensions quality
        good_count = sum(1 for d in result.validation_details["human_dimensions"].values() if d["quality"] == "good")
        result.validation_details["human_dimensions_quality"] = f"{good_count}/{len(dimensions)} good"

        if good_count < len(dimensions) * 0.6:  # Less than 60% good
            result.add_suggestion(
                "Human dimensions need more specificity. Avoid generic phrases like '温馨', '舒适'. "
                "Describe specific emotional journeys, concrete rituals, and actionable insights."
            )

    def _validate_l2_perspectives(self, data: Dict[str, Any], result: ValidationResult):
        """
        Check L2 perspective activation

        Base perspectives (always required):
        - psychological, sociological, aesthetic, emotional, ritual

        Extended perspectives (conditional):
        - business, technical, ecological, cultural, political
        """
        l2_model = data.get("analysis_layers", {}).get("L2_user_model", {})

        if not l2_model:
            result.add_error("L2_user_model is missing")
            result.validation_details["l2_present"] = False
            return

        result.validation_details["l2_present"] = True

        # Check base perspectives
        base_perspectives = ["psychological", "sociological", "aesthetic", "emotional", "ritual"]
        missing_base = [p for p in base_perspectives if not l2_model.get(p)]

        if missing_base:
            result.add_error(f"L2 missing required base perspectives: {missing_base}")

        result.validation_details["l2_base_perspectives"] = [p for p in base_perspectives if p not in missing_base]

        # Check extended perspectives (just log, don't error)
        extended_perspectives = ["business", "technical", "ecological", "cultural", "political"]
        present_extended = [p for p in extended_perspectives if l2_model.get(p) and not l2_model[p].startswith("（如激活）")]

        result.validation_details["l2_extended_perspectives"] = present_extended

        if present_extended:
            logger.info(f" [Validation] L2 activated extended perspectives: {present_extended}")

    def _validate_expert_handoff(self, data: Dict[str, Any], result: ValidationResult):
        """
        Check expert handoff completeness

        Should have:
        - critical_questions_for_experts (at least 1 question per expert)
        - design_challenge_spectrum
        - permission_to_diverge
        """
        expert_handoff = data.get("expert_handoff", {})

        if not expert_handoff:
            result.add_warning("expert_handoff is missing")
            result.validation_details["expert_handoff_present"] = False
            return

        result.validation_details["expert_handoff_present"] = True

        # Check critical questions
        critical_questions = expert_handoff.get("critical_questions_for_experts", {})
        if not critical_questions:
            result.add_warning("expert_handoff missing critical_questions_for_experts")
        else:
            # Count questions per expert
            question_counts = {expert: len(questions) for expert, questions in critical_questions.items()}
            result.validation_details["expert_questions"] = question_counts

            # Check each expert has at least 1 question
            experts_without_questions = [expert for expert, count in question_counts.items() if count == 0]
            if experts_without_questions:
                result.add_warning(f"Experts without questions: {experts_without_questions}")

        # Check design challenge spectrum
        if not expert_handoff.get("design_challenge_spectrum"):
            result.add_warning("expert_handoff missing design_challenge_spectrum")

        # Check permission to diverge
        if not expert_handoff.get("permission_to_diverge"):
            result.add_warning("expert_handoff missing permission_to_diverge")

    def _calculate_quality_score(self, result: ValidationResult) -> float:
        """
        Calculate overall quality score based on validation results

        Score components:
        - Base: 0.5 (if valid)
        - L6 quality: +0.15
        - L7 quality: +0.15
        - Human dimensions: +0.10
        - L2 perspectives: +0.05
        - Expert handoff: +0.05

        Penalties:
        - Each error: -0.10
        - Each warning: -0.02
        """
        if not result.is_valid:
            # Start with lower base if invalid
            score = 0.3
        else:
            score = 0.5

        # L6 quality bonus
        l6_quality = result.validation_details.get("l6_quality", "unknown")
        if l6_quality == "good":
            score += 0.15
        elif l6_quality == "needs_improvement":
            score += 0.08

        # L7 quality bonus
        l7_quality = result.validation_details.get("l7_quality", "unknown")
        if l7_quality == "good":
            score += 0.15
        elif l7_quality == "needs_improvement":
            score += 0.08

        # Human dimensions bonus
        human_dims = result.validation_details.get("human_dimensions", {})
        good_dims = sum(1 for d in human_dims.values() if d.get("quality") == "good")
        total_dims = len(human_dims)
        if total_dims > 0:
            score += 0.10 * (good_dims / total_dims)

        # L2 perspectives bonus
        if result.validation_details.get("l2_present"):
            base_count = len(result.validation_details.get("l2_base_perspectives", []))
            if base_count >= 5:
                score += 0.05

        # Expert handoff bonus
        if result.validation_details.get("expert_handoff_present"):
            score += 0.05

        # Penalties
        score -= len(result.errors) * 0.10
        score -= len(result.warnings) * 0.02

        # Clamp to [0, 1]
        return max(0.0, min(1.0, score))


# Convenience function
def validate_requirements_output(phase2_result: Dict[str, Any]) -> ValidationResult:
    """
    Convenience function to validate requirements analysis output

    Args:
        phase2_result: Phase 2 analysis result

    Returns:
        ValidationResult
    """
    validator = RequirementsValidator()
    return validator.validate_phase2_output(phase2_result)
