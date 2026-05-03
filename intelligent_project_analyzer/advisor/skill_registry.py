import os
from pathlib import Path
from typing import Optional
import yaml


class SkillManifest:
    def __init__(self, data: dict):
        self.skill_id: str = data["skill_id"]
        self.skill_name: str = data["skill_name"]
        self.skill_type: str = data["skill_type"]
        self.owner_domain: str = data["owner_domain"]
        self.input_contract: dict = data["input_contract"]
        self.output_contract: dict = data["output_contract"]
        self.execution_mode: str = data["execution_mode"]
        self.side_effect_level: str = data["side_effect_level"]
        self.timeout_ms: int = data["timeout_ms"]
        self.fallback_strategy: str = data["fallback_strategy"]
        self.version: str = data["version"]
        self.failure_modes: dict = data.get("failure_modes", {})


class SkillRegistry:
    """加载并提供 SkillManifest 查询。Skill 必须在此注册才能进入正式链路。"""

    def __init__(self, skills_dir: Optional[str] = None):
        if skills_dir is None:
            base = Path(__file__).parent.parent
            skills_dir = str(base / "config" / "skills")
        self._skills: dict[str, SkillManifest] = {}
        self._load_all(skills_dir)

    def _load_all(self, skills_dir: str) -> None:
        path = Path(skills_dir)
        if not path.exists():
            return
        for yaml_file in path.glob("*.yaml"):
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            manifest = SkillManifest(data)
            self._skills[manifest.skill_id] = manifest

    def get(self, skill_id: str) -> Optional[SkillManifest]:
        return self._skills.get(skill_id)

    def require(self, skill_id: str) -> SkillManifest:
        """获取 Skill，不存在则抛出异常（无 Manifest 不得进入正式链路）。"""
        manifest = self.get(skill_id)
        if manifest is None:
            raise ValueError(
                f"Skill '{skill_id}' not found in SkillRegistry. "
                "Register a SkillManifest YAML before entering the main pipeline."
            )
        return manifest

    def list_all(self) -> list[str]:
        return list(self._skills.keys())
