"""
ST-5: 孤岛代码检测（P1 清理验证）

目标：
  确保已标记为 HISTORICAL 的孤岛模块不被新代码导入，
  并验证已移除的冗余依赖未重新出现于 requirements.txt。

维护说明：
  - 如需删除 batch_parallel_executor.py，同时从 HISTORICAL_MODULES 移除
  - 如新增其他孤岛模块候选，按同样格式加入
"""
from __future__ import annotations

import pathlib
import re

import pytest

REPO_ROOT = pathlib.Path(__file__).parents[2]

# 已知孤岛/历史模块（文件路径相对 REPO_ROOT）
HISTORICAL_MODULES = [
    "intelligent_project_analyzer/workflow/batch_parallel_executor.py",
]

# requirements.txt 中不应再出现的已移除依赖
REMOVED_DEPS = [
    "aioredis",          # 由 redis>=5.0.0 内置 redis.asyncio 替代
]


@pytest.mark.unit
class TestOrphanCode:
    """孤岛代码与冗余依赖检测"""

    def test_historical_modules_have_historical_marker(self):
        """已标记为孤岛的模块文件头必须包含 HISTORICAL 关键字"""
        for rel_path in HISTORICAL_MODULES:
            fpath = REPO_ROOT / rel_path
            assert fpath.exists(), f"历史模块不存在，请从列表中移除：{rel_path}"
            content = fpath.read_text(encoding="utf-8")
            assert "HISTORICAL" in content[:500], (
                f"{rel_path} 未包含 HISTORICAL 标注（前 500 字符内），"
                "请在文件顶部添加历史说明。"
            )

    def test_batch_parallel_executor_not_imported(self):
        """
        batch_parallel_executor.py 是孤岛模块，不应被任何生产代码导入。
        静态扫描所有 .py 文件（排除自身）。
        """
        target = "batch_parallel_executor"
        violations: list[str] = []

        for py_file in (REPO_ROOT / "intelligent_project_analyzer").rglob("*.py"):
            if py_file.name == "batch_parallel_executor.py":
                continue
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            if target in content:
                violations.append(str(py_file.relative_to(REPO_ROOT)))

        assert not violations, (
            f"`batch_parallel_executor` 被以下文件引用，不应存在生产导入：\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_requirements_no_standalone_aioredis(self):
        """
        requirements.txt 不应再包含独立 aioredis 包（已由 redis>=5.0.0 内置替代）
        """
        req_file = REPO_ROOT / "requirements.txt"
        assert req_file.exists(), "requirements.txt 不存在"
        content = req_file.read_text(encoding="utf-8")

        for dep in REMOVED_DEPS:
            # 匹配形如 "aioredis" 或 "aioredis>=x.x.x"（非注释行，且是行首包名）
            lines_with_dep = [
                ln.strip() for ln in content.splitlines()
                if re.match(rf'^\s*{re.escape(dep)}', ln)
                and not ln.strip().startswith("#")
            ]
            assert not lines_with_dep, (
                f"requirements.txt 中发现已移除的依赖 `{dep}`：\n"
                + "\n".join(f"  {ln}" for ln in lines_with_dep)
                + "\n所有代码均使用 `redis.asyncio` 替代，无需独立安装 aioredis。"
            )

    def test_all_code_uses_redis_asyncio_not_standalone_aioredis(self):
        """
        生产代码中 aioredis 的使用形式应为 `redis.asyncio as aioredis`，
        不应出现 `import aioredis`（独立包导入）
        """
        violations: list[str] = []

        for py_file in (REPO_ROOT / "intelligent_project_analyzer").rglob("*.py"):
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            # 检查是否有独立 `import aioredis`（不是 redis.asyncio 形式）
            for line_no, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                # 排除注释行和 redis.asyncio 形式
                if (
                    re.match(r'^import aioredis', stripped)
                    and "redis.asyncio" not in line
                ):
                    violations.append(
                        f"{py_file.relative_to(REPO_ROOT)}:{line_no}: {stripped}"
                    )

        assert not violations, (
            "发现直接导入独立 aioredis 包（应使用 `redis.asyncio`）：\n"
            + "\n".join(violations)
        )
