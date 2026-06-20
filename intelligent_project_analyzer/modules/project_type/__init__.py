"""Project type detection module boundary."""

from .contracts import (
    PROJECT_TYPE_CLASSIFICATION_OUTPUT_KEYS,
    PROJECT_TYPE_CONTEXT_ROLE,
    PROJECT_TYPE_FORBIDDEN_RESPONSIBILITIES,
    PROJECT_TYPE_MODULE_ID,
    PROJECT_TYPE_REGISTRY_PATHS,
    PROJECT_TYPE_VERSION,
    project_type_detection_contract,
)
from .registry_audit import (
    ProjectTypeRegistryAuditError,
    audit_project_type_registries,
)

__all__ = [
    "ProjectTypeRegistryAuditError",
    "PROJECT_TYPE_CLASSIFICATION_OUTPUT_KEYS",
    "PROJECT_TYPE_CONTEXT_ROLE",
    "PROJECT_TYPE_FORBIDDEN_RESPONSIBILITIES",
    "PROJECT_TYPE_MODULE_ID",
    "PROJECT_TYPE_REGISTRY_PATHS",
    "PROJECT_TYPE_VERSION",
    "audit_project_type_registries",
    "project_type_detection_contract",
]
