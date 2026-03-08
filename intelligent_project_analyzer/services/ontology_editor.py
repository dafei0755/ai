"""
本体论编辑器 (Ontology Editor)

安全地编辑 ontology.yaml 文件，保留注释和格式。

核心功能:
- 使用 ruamel.yaml 保留YAML注释和格式
- 使用 portalocker 避免并发写入冲突
- 自动备份机制（失败时回滚）
- 语法验证

版本: v1.0
创建日期: 2026-02-11
"""

import shutil
from pathlib import Path
from typing import Any, Dict

import yaml
from loguru import logger

try:
    from ruamel.yaml import YAML

    RUAMEL_AVAILABLE = True
except ImportError:
    RUAMEL_AVAILABLE = False
    logger.warning("️ ruamel.yaml 未安装，将使用标准 yaml 库（会丢失注释）")

try:
    import portalocker

    PORTALOCKER_AVAILABLE = True
except ImportError:
    PORTALOCKER_AVAILABLE = False
    logger.warning("️ portalocker 未安装，无法使用文件锁（并发写入可能冲突）")


class OntologyEditor:
    """
    本体论YAML文件编辑器

    提供安全的YAML编辑功能，包括：
    - 格式和注释保留
    - 文件锁（防止并发冲突）
    - 自动备份和回滚
    """

    def __init__(self):
        self.ontology_path = Path(__file__).parent.parent / "knowledge_base" / "ontology.yaml"
        self.backup_path = self.ontology_path.with_suffix(".yaml.bak")

        if RUAMEL_AVAILABLE:
            self.yaml = YAML()
            self.yaml.preserve_quotes = True
            self.yaml.width = 4096  # 防止长行折叠
            self.yaml.indent(mapping=2, sequence=2, offset=0)
        else:
            self.yaml = None

    def append_dimension(self, project_type: str, category: str, dimension_data: Dict[str, Any]) -> bool:
        """
        追加维度到 ontology.yaml

        Args:
            project_type: 项目类型（如 "personal_residential"）
            category: 类别（如 "spiritual_world"）
            dimension_data: 维度数据
                {
                    "name": "核心价值观 (Core Values)",
                    "description": "...",
                    "ask_yourself": "...",
                    "examples": "..."
                }

        Returns:
            是否成功
        """
        try:
            logger.info(f" 开始追加维度: {dimension_data.get('name')} 到 {project_type}.{category}")

            # 1. 备份原文件
            self._backup()

            # 2. 使用文件锁
            with self._file_lock():
                # 3. 读取并修改YAML
                if RUAMEL_AVAILABLE:
                    ontology = self._load_with_ruamel()
                else:
                    ontology = self._load_with_pyyaml()

                # 4. 定位到目标位置
                frameworks = ontology.get("ontology_frameworks", {})
                if project_type not in frameworks:
                    logger.error(f" 框架不存在: {project_type}")
                    return False

                framework = frameworks[project_type]
                if category not in framework:
                    logger.error(f" 类别不存在: {category}")
                    return False

                category_list = framework[category]
                if not isinstance(category_list, list):
                    logger.error(f" 类别 {category} 不是列表类型")
                    return False

                # 5. 追加新维度
                category_list.append(dimension_data)

                # 6. 写回文件
                if RUAMEL_AVAILABLE:
                    self._save_with_ruamel(ontology)
                else:
                    self._save_with_pyyaml(ontology)

                # 7. 验证语法
                if not self._validate_syntax():
                    logger.error(" 写入后语法验证失败，回滚")
                    self._rollback()
                    return False

            logger.info(f" 维度追加成功: {dimension_data.get('name')}")
            return True

        except Exception as e:
            logger.error(f" 追加维度失败: {e}")
            self._rollback()
            return False

    def _backup(self):
        """备份原文件"""
        try:
            shutil.copy(self.ontology_path, self.backup_path)
            logger.debug(f" 已备份: {self.backup_path}")
        except Exception as e:
            logger.warning(f"️ 备份失败: {e}")

    def _rollback(self):
        """回滚到备份文件"""
        try:
            if self.backup_path.exists():
                shutil.copy(self.backup_path, self.ontology_path)
                logger.info(" 已回滚到备份文件")
        except Exception as e:
            logger.error(f" 回滚失败: {e}")

    def _file_lock(self):
        """返回文件锁上下文管理器"""
        if PORTALOCKER_AVAILABLE:
            return portalocker.Lock(str(self.ontology_path.with_suffix(".lock")), timeout=10, mode="w")
        else:
            # 无锁实现（不安全，但至少能工作）
            from contextlib import nullcontext

            return nullcontext()

    def _load_with_ruamel(self) -> Dict[str, Any]:
        """使用 ruamel.yaml 加载（保留格式）"""
        with open(self.ontology_path, encoding="utf-8") as f:
            return self.yaml.load(f)

    def _load_with_pyyaml(self) -> Dict[str, Any]:
        """使用标准 yaml 加载（丢失注释）"""
        with open(self.ontology_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _save_with_ruamel(self, data: Dict[str, Any]):
        """使用 ruamel.yaml 保存（保留格式）"""
        with open(self.ontology_path, "w", encoding="utf-8") as f:
            self.yaml.dump(data, f)

    def _save_with_pyyaml(self, data: Dict[str, Any]):
        """使用标准 yaml 保存（丢失注释）"""
        with open(self.ontology_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def _validate_syntax(self) -> bool:
        """验证 YAML 语法"""
        try:
            with open(self.ontology_path, encoding="utf-8") as f:
                yaml.safe_load(f)
            return True
        except Exception as e:
            logger.error(f" YAML 语法错误: {e}")
            return False


# ============ 全局实例 ============

_ontology_editor: OntologyEditor | None = None


def get_ontology_editor() -> OntologyEditor:
    """获取全局本体论编辑器实例"""
    global _ontology_editor
    if _ontology_editor is None:
        _ontology_editor = OntologyEditor()
    return _ontology_editor
