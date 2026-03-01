"""版本一致性检查脚本。

检查目标：
1) 根目录 VERSION 是否为 SemVer。
2) 后端/包版本是否都从 PRODUCT_VERSION 派生。
3) README 版本徽章与当前版本展示是否与 VERSION 一致。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        raise RuntimeError(f"读取文件失败: {path} ({exc})") from exc


def _assert(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []

    version_path = root / "VERSION"
    settings_path = root / "intelligent_project_analyzer" / "settings.py"
    package_init_path = root / "intelligent_project_analyzer" / "__init__.py"
    server_path = root / "intelligent_project_analyzer" / "api" / "server.py"
    readme_path = root / "README.md"

    version = _read(version_path).strip()
    _assert(bool(SEMVER_RE.match(version)), f"VERSION 不是合法 SemVer: {version!r}", errors)

    settings_text = _read(settings_path)
    _assert(
        "from intelligent_project_analyzer.versioning import PRODUCT_VERSION" in settings_text,
        "settings.py 未导入 PRODUCT_VERSION",
        errors,
    )
    _assert(
        "app_version: str = Field(default=PRODUCT_VERSION" in settings_text,
        "settings.py 的 app_version 未使用 PRODUCT_VERSION",
        errors,
    )

    package_init_text = _read(package_init_path)
    _assert(
        "__version__ = PRODUCT_VERSION" in package_init_text,
        "__init__.py 的 __version__ 未使用 PRODUCT_VERSION",
        errors,
    )

    server_text = _read(server_path)
    _assert(
        "APP_VERSION = settings.app_version" in server_text, "server.py 未定义 APP_VERSION = settings.app_version", errors
    )
    _assert("version=APP_VERSION" in server_text, "FastAPI app.version 未使用 APP_VERSION", errors)
    _assert('"version": APP_VERSION' in server_text, "根路由返回版本未使用 APP_VERSION", errors)

    readme_text = _read(readme_path)
    _assert(
        f"version-v{version}-blue.svg" in readme_text,
        f"README 版本徽章未同步 VERSION ({version})",
        errors,
    )
    _assert(
        f"**当前版本**: v{version}" in readme_text,
        f"README 当前版本展示未同步 VERSION ({version})",
        errors,
    )

    if errors:
        print("❌ 版本一致性检查失败:")
        for idx, err in enumerate(errors, 1):
            print(f"  {idx}. {err}")
        return 1

    print(f"✅ 版本一致性检查通过: v{version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
