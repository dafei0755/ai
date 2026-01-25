"""
L2 Perspective Activator - v7.270

Programmatically determine which L2 extended perspectives should be activated
based on project type and user input keywords.

Base perspectives (always active):
- psychological, sociological, aesthetic, emotional, ritual

Extended perspectives (conditionally activated):
- business: Commercial projects, ROI focus
- technical: Technology-intensive projects
- ecological: Sustainability-focused projects
- cultural: Cultural/heritage projects
- political: Public/community projects with stakeholder dynamics

Author: AI Assistant
Date: 2026-01-25
"""

import os
import yaml
from typing import List, Dict, Any, Optional
from loguru import logger


class L2PerspectiveActivator:
    """Determine which L2 extended perspectives should be activated"""

    # Default activation rules (fallback if config not found)
    DEFAULT_ACTIVATION_RULES = {
        "business": {
            "activate_when": {
                "project_type": ["commercial_enterprise", "hybrid_residential_commercial", "hospitality_tourism"],
                "keywords": ["roi", "盈利", "商业模式", "市场", "竞争", "品牌", "坪效", "运营", "成本"]
            },
            "description": "商业视角：ROI、市场定位、竞争优势、商业模式"
        },
        "technical": {
            "activate_when": {
                "project_type": ["commercial_enterprise", "office_coworking"],
                "keywords": ["智能", "系统", "技术", "集成", "自动化", "设备", "ai", "数字", "科技"]
            },
            "description": "技术视角：可行性、技术栈、集成复杂度、维护成本"
        },
        "ecological": {
            "activate_when": {
                "project_type": ["cultural_educational", "healthcare_wellness"],
                "keywords": ["可持续", "环保", "绿色", "节能", "生态", "leed", "碳", "有机", "自然"]
            },
            "description": "生态视角：可持续性、环境影响、循环经济、碳足迹"
        },
        "cultural": {
            "activate_when": {
                "project_type": ["cultural_educational", "hospitality_tourism"],
                "keywords": ["文化", "传统", "历史", "遗产", "地域", "在地", "符号", "民族", "精神"]
            },
            "description": "文化视角：文化语境、象征意义、遗产保护、地域特色"
        },
        "political": {
            "activate_when": {
                "project_type": ["commercial_enterprise", "cultural_educational"],
                "keywords": ["社区", "利益相关者", "政策", "法规", "公共", "影响", "居民", "政府"]
            },
            "description": "政治视角：利益相关者权力动态、监管环境、社区影响"
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize L2 perspective activator

        Args:
            config_path: Path to requirements_analyst_phase2.yaml (optional)
        """
        self.activation_rules = self._load_activation_rules(config_path)

    def _load_activation_rules(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load activation rules from phase2 config

        Args:
            config_path: Path to config file

        Returns:
            Activation rules dictionary
        """
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    rules = config.get("l2_perspective_activation", ).get("conditional_perspectives", {})
                    if rules:
                        logger.info(f"✅ [L2 Activator] Loaded activation rules from {config_path}")
                        return rules
            except Exception as e:
                logger.warning(f"⚠️ [L2 Activator] Failed to load config: {e}")

        # Try default path
        default_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "config",
            "prompts",
            "requirements_analyst_phase2.yaml"
        )

        if os.path.exists(default_path):
            try:
                with open(default_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    rules = config.get("l2_perspective_activation", {}).get("conditional_perspectives", {})
                    if rules:
                        logger.info(f"✅ [L2 Activator] Loaded activation rules from default path")
                        return rules
            except Exception as e:
                logger.warning(f"⚠️ [L2 Activator] Failed to load default config: {e}")

        # Fallback to hardcoded rules
        logger.info("ℹ️ [L2 Activator] Using default activation rules")
        return self.DEFAULT_ACTIVATION_RULES

    def determine_active_perspectives(
        self,
        project_type: Optional[str],
        user_input: str,
        phase1_result: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Determine which extended perspectives to activate

        Args:
            project_type: Project type (e.g., "commercial_enterprise", "personal_residential")
            user_input: Original user input text
            phase1_result: Phase 1 analysis result (optional, for additional context)

        Returns:
            List of perspective names to activate, e.g. ["psychological", "sociological", "business"]
        """
        # Always include base perspectives
        base = ["psychological", "sociological", "aesthetic", "emotional", "ritual"]
        active = base.copy()

        # Check each extended perspective
        extended = ["business", "technical", "ecological", "cultural", "political"]

        user_input_lower = user_input.lower()

        for perspective in extended:
            if self._should_activate(perspective, project_type, user_input_lower, phase1_result):
                active.append(perspective)
                logger.info(f"✅ [L2 Activator] Activating perspective: {perspective}")

        logger.info(f"📋 [L2 Activator] Active perspectives: {active}")

        return active

    def _should_activate(
        self,
        perspective: str,
        project_type: Optional[str],
        user_input_lower: str,
        phase1_result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if perspective should be activated based on rules

        Args:
            perspective: Perspective name (e.g., "business")
            project_type: Project type
            user_input_lower: User input in lowercase
            phase1_result: Phase 1 result (optional)

        Returns:
            True if perspective should be activated
        """
        rules = self.activation_rules.get(perspective, {})
        activate_when = rules.get("activate_when", {})

        # Check project type match
        if project_type:
            allowed_types = activate_when.get("project_type", [])
            if project_type in allowed_types:
                logger.debug(f"  ✓ {perspective}: project_type match ({project_type})")
                return True

        # Check keyword match
        keywords = activate_when.get("keywords", [])
        matched_keywords = [kw for kw in keywords if kw.lower() in user_input_lower]

        if matched_keywords:
            logger.debug(f"  ✓ {perspective}: keyword match ({matched_keywords[:3]})")
            return True

        return False

    def get_perspective_description(self, perspective: str) -> str:
        """
        Get description for a perspective

        Args:
            perspective: Perspective name

        Returns:
            Description string
        """
        rules = self.activation_rules.get(perspective, {})
        return rules.get("description", f"{perspective} perspective")

    def format_activation_summary(
        self,
        active_perspectives: List[str]
    ) -> str:
        """
        Format activation summary for logging or prompt injection

        Args:
            active_perspectives: List of active perspective names

        Returns:
            Formatted summary string
        """
        base = ["psychological", "sociological", "aesthetic", "emotional", "ritual"]
        extended = [p for p in active_perspectives if p not in base]

        summary = f"**L2 Perspectives Activated**:\n"
        summary += f"- Base (always): {', '.join(base)}\n"

        if extended:
            summary += f"- Extended (conditional): {', '.join(extended)}\n"
            for p in extended:
                desc = self.get_perspective_description(p)
                summary += f"  - {p}: {desc}\n"
        else:
            summary += f"- Extended: None (base perspectives sufficient)\n"

        return summary

    def inject_into_prompt(
        self,
        base_prompt: str,
        active_perspectives: List[str]
    ) -> str:
        """
        Inject active perspectives into Phase 2 prompt

        Args:
            base_prompt: Base Phase 2 prompt
            active_perspectives: List of active perspectives

        Returns:
            Modified prompt with perspective activation instructions
        """
        # Build activation instruction
        base = ["psychological", "sociological", "aesthetic", "emotional", "ritual"]
        extended = [p for p in active_perspectives if p not in base]

        if not extended:
            # No extended perspectives, no need to modify prompt
            return base_prompt

        # Build injection text
        injection = "\n\n### 🎯 L2 Extended Perspectives Activation\n\n"
        injection += "Based on project analysis, the following extended perspectives are activated:\n\n"

        for p in extended:
            desc = self.get_perspective_description(p)
            injection += f"- **{p}**: {desc}\n"

        injection += "\nPlease ensure these perspectives are included in your L2_user_model analysis.\n"

        # Find insertion point (after L2 section header)
        l2_marker = "**L2: 建模**"
        if l2_marker in base_prompt:
            parts = base_prompt.split(l2_marker, 1)
            return parts[0] + l2_marker + injection + parts[1]

        # Fallback: append at end
        return base_prompt + injection


# Convenience function
def determine_active_perspectives(
    project_type: Optional[str],
    user_input: str,
    phase1_result: Optional[Dict[str, Any]] = None,
    config_path: Optional[str] = None
) -> List[str]:
    """
    Convenience function to determine active L2 perspectives

    Args:
        project_type: Project type
        user_input: User input text
        phase1_result: Phase 1 result (optional)
        config_path: Config file path (optional)

    Returns:
        List of active perspective names
    """
    activator = L2PerspectiveActivator(config_path=config_path)
    return activator.determine_active_perspectives(
        project_type=project_type,
        user_input=user_input,
        phase1_result=phase1_result
    )
