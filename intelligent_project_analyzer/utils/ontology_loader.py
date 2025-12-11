import yaml
from pathlib import Path
from typing import Dict, Any

class OntologyLoader:
    """
    按项目类型加载本体论片段（支持动态注入）
    """
    def __init__(self, ontology_path: str):
        self.ontology_path = Path(ontology_path)
        self.ontology_data = self._load_ontology()

    def _load_ontology(self) -> Dict[str, Any]:
        if not self.ontology_path.exists():
            raise FileNotFoundError(f"Ontology file not found: {self.ontology_path}")
        with open(self.ontology_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def get_ontology_by_type(self, project_type: str) -> Dict[str, Any]:
        """
        根据项目类型返回对应本体论片段
        """
        frameworks = self.ontology_data.get('ontology_frameworks', {})
        return frameworks.get(project_type, {})

    def get_meta_framework(self) -> Dict[str, Any]:
        """
        返回元框架（如需通用注入）
        """
        frameworks = self.ontology_data.get('ontology_frameworks', {})
        return frameworks.get('meta_framework', {})

