"""产品版本管理（SSOT）。

唯一版本源：仓库根目录 `VERSION` 文件。
"""

from pathlib import Path


_DEFAULT_VERSION = "0.0.0"


def load_product_version() -> str:
    """从仓库根目录读取产品版本。"""
    project_root = Path(__file__).resolve().parents[1]
    version_file = project_root / "VERSION"

    try:
        value = version_file.read_text(encoding="utf-8").strip()
        return value or _DEFAULT_VERSION
    except Exception:
        return _DEFAULT_VERSION


PRODUCT_VERSION = load_product_version()
