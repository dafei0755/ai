from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

CURRENT_ROOT = Path(r"d:\11-20\langgraph-design")
V7_ROOT = Path(r"d:\11-20\langgraph-v7-0226-1000")
REPORT_DIR = CURRENT_ROOT / "docs" / "implementation-reports"

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    ".next",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    "dist",
    "build",
    "backup",
    "_restore_meta",
    "logs",
}
EXCLUDE_FILES = {"nul", "con", "prn", "aux", "com1", "lpt1"}


@dataclass(frozen=True)
class DimensionSpec:
    key: str
    title: str
    paths: tuple[str, ...]
    label: str
    rationale: str
    recommendation: str


DIMENSIONS = (
    DimensionSpec(
        key="frontend_deep_thinking",
        title="前端深度思考链路",
        paths=(
            "frontend-nextjs/app/analysis",
            "frontend-nextjs/components/OutputIntentConfirmationModal.tsx",
            "frontend-nextjs/components/QuestionnaireSummaryDisplay.tsx",
            "frontend-nextjs/components/UcpptSearchProgress.tsx",
            "frontend-nextjs/components/PlanReviewPanel.tsx",
            "frontend-nextjs/contexts/SessionContext.tsx",
            "frontend-nextjs/contexts/AuthContext.tsx",
        ),
        label="V7-better",
        rationale="用户已确认 V7 更接近主动调试结果；analysis 页面与当前版本存在实质差异。",
        recommendation="锁定 V7 为运行基线，仅把当前版本中的单点 UI 修复作为候选增量逐项验证。",
    ),
    DimensionSpec(
        key="backend_flow",
        title="后端流程编排",
        paths=(
            "intelligent_project_analyzer/api/server.py",
            "intelligent_project_analyzer/api/four_step_flow_routes.py",
            "intelligent_project_analyzer/api/search_routes.py",
            "intelligent_project_analyzer/interaction/nodes",
            "intelligent_project_analyzer/workflow/main_workflow.py",
        ),
        label="V7-better",
        rationale="核心 interaction 节点与 V7 一致，但 server.py 与入口层存在漂移，用户反馈当前行为已部分回旧。",
        recommendation="保留 V7 路由和主流程，后续只回收经过验证的非结构性入口增强。",
    ),
    DimensionSpec(
        key="algorithm_config",
        title="算法 / Prompt / 规则配置",
        paths=(
            "intelligent_project_analyzer/config",
            "config",
        ),
        label="V7-better",
        rationale="这部分直接决定行为正确性；按用户反馈 V7 更接近主动调试，当前版本存在后续整理造成的偏移风险。",
        recommendation="以 V7 配置为基线，后续仅对样例配置和文档化配置做回收。",
    ),
    DimensionSpec(
        key="admin_console",
        title="控制后台",
        paths=(
            "frontend-nextjs/app/admin",
            "intelligent_project_analyzer/api/routes",
            "intelligent_project_analyzer/api/external_data_routes.py",
            "intelligent_project_analyzer/api/search_quality_routes.py",
        ),
        label="V7-better",
        rationale="当前版本存在更多后台页和路由，但用户明确表示 V7 的控制后台更接近真实调试状态。",
        recommendation="优先保留 V7 的可用链路，再逐页核查当前新增后台入口是否真正闭环。",
    ),
    DimensionSpec(
        key="crawler_external_data",
        title="爬虫与外部数据系统",
        paths=(
            "intelligent_project_analyzer/external_data_system",
            "scripts/init_external_database.py",
            "scripts/init_external_db.py",
            "scripts/validate_external_data_system.py",
            "tests/integration/test_crawler_integration.py",
        ),
        label="V7-better",
        rationale="当前 external_data_system 文件数更多，但用户判断 V7 更完整；更可能是当前版本有未闭环扩张而非真正稳定增强。",
        recommendation="以 V7 的爬虫链路为运行基线，新增文件一律按模块闭环验证后再回收。",
    ),
    DimensionSpec(
        key="env_and_dependencies",
        title="环境配置与依赖",
        paths=(
            ".env.example",
            "requirements.txt",
            "package.json",
            "frontend-nextjs/tsconfig.json",
            "frontend-nextjs/next-env.d.ts",
            "config/SYSTEM_CONFIG.example.yaml",
            "config/SYSTEM_CONFIG.yaml",
            "mypy.ini",
            "ruff.toml",
        ),
        label="Current-better",
        rationale="当前版本保留了更多配置样例和治理文件，可作为非运行时增强候选池。",
        recommendation="优先回收文档化配置和样例文件；任何会改运行时行为的配置必须在 V7 上单独验证。",
    ),
    DimensionSpec(
        key="db_and_migrations",
        title="数据库与迁移",
        paths=(
            "scripts/migrate_add_bilingual_fields.py",
            "scripts/migrate_add_bilingual_fields_pg.py",
            "scripts/migrate_project_index_to_discovery.py",
            "scripts/migrate_taxonomy_learning_system.py",
            "scripts/migrate_taxonomy_v7.501_dual_track.py",
            "scripts/init_external_database.py",
            "scripts/init_external_db.py",
            "intelligent_project_analyzer/models",
        ),
        label="Current-better",
        rationale="当前版本包含更多治理导向的迁移与版本规则文件，但不能直接替换运行时模型层。",
        recommendation="迁移脚本可优先审查；模型与服务层禁止整包覆盖回 V7。",
    ),
    DimensionSpec(
        key="docs_and_governance",
        title="文档与治理",
        paths=(
            ".github",
            "docs/releases",
            "EMERGENCY_RECOVERY.md",
            "BACKUP_GUIDE.md",
            "README.md",
            "QUICKSTART.md",
            "CHANGELOG.md",
        ),
        label="Current-better",
        rationale="当前版本存在额外的版本治理、流程校验和发布文档，但不应反推运行时代码归属。",
        recommendation="回收治理文档时必须剥离与当前主干行为不一致的版本叙述。",
    ),
)

SAFE_CANDIDATES = (
    ".github/workflows/tag-guard.yml",
    "docs/releases/VERSIONING_POLICY.md",
    "scripts/check_version_consistency.py",
    "scripts/check_tag_naming.py",
    "scripts/rollback_to_tag.py",
    "scripts/generate_release_signoff.py",
)

MANUAL_REVIEW_CANDIDATES = (
    "VERSION",
    "intelligent_project_analyzer/versioning.py",
    "intelligent_project_analyzer/__init__.py",
    "intelligent_project_analyzer/settings.py",
    "intelligent_project_analyzer/api/server.py",
)

PROHIBITED_DIRECTORIES = (
    "frontend-nextjs",
    "intelligent_project_analyzer/api",
    "intelligent_project_analyzer/services",
    "intelligent_project_analyzer/interaction",
    "intelligent_project_analyzer/config/prompts",
    "intelligent_project_analyzer/external_data_system",
)


def iter_files(base: Path, relative: str) -> Iterable[tuple[str, Path]]:
    target = base / relative
    if not target.exists():
        return []
    if target.is_file():
        return [(relative.replace("\\", "/"), target)]

    collected: list[tuple[str, Path]] = []
    for root, dirnames, filenames in os.walk(target):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        root_path = Path(root)
        for name in filenames:
            if name.lower() in EXCLUDE_FILES:
                continue
            full = root_path / name
            rel = full.relative_to(base).as_posix()
            collected.append((rel, full))
    return collected


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compare_paths(paths: tuple[str, ...]) -> dict:
    current: dict[str, Path] = {}
    v7: dict[str, Path] = {}
    for rel in paths:
        for key, full in iter_files(CURRENT_ROOT, rel):
            current[key] = full
        for key, full in iter_files(V7_ROOT, rel):
            v7[key] = full

    current_keys = set(current)
    v7_keys = set(v7)
    common = sorted(current_keys & v7_keys)
    modified = [key for key in common if file_hash(current[key]) != file_hash(v7[key])]
    return {
        "current_count": len(current_keys),
        "v7_count": len(v7_keys),
        "current_only": sorted(current_keys - v7_keys),
        "v7_only": sorted(v7_keys - current_keys),
        "modified": sorted(modified),
    }


def render_matrix(rows: list[dict]) -> str:
    lines = [
        "# Runtime Baseline Matrix",
        "",
        "基线判定原则：行为正确性优先于文件数量、版本号和整理程度。",
        "",
        "| 维度 | 判定 | 当前文件数 | V7 文件数 | 仅当前 | 仅V7 | 内容差异 | 结论 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['title']} | `{row['label']}` | {row['current_count']} | {row['v7_count']} | "
            f"{len(row['current_only'])} | {len(row['v7_only'])} | {len(row['modified'])} | {row['recommendation']} |"
        )
    lines.extend(
        [
            "",
            "## 判定说明",
            "",
        ]
    )
    for row in rows:
        lines.extend(
            [
                f"### {row['title']}",
                f"- 判定: `{row['label']}`",
                f"- 依据: {row['rationale']}",
                f"- 执行建议: {row['recommendation']}",
                f"- 差异摘要: 当前 {row['current_count']} 个文件, V7 {row['v7_count']} 个文件, 仅当前 {len(row['current_only'])}, 仅V7 {len(row['v7_only'])}, 内容差异 {len(row['modified'])}",
                "",
            ]
        )
        if row["modified"]:
            lines.append("代表性差异文件:")
            for item in row["modified"][:8]:
                lines.append(f"- `{item}`")
            lines.append("")
        if row["current_only"]:
            lines.append("当前版本独有样本:")
            for item in row["current_only"][:5]:
                lines.append(f"- `{item}`")
            lines.append("")
        if row["v7_only"]:
            lines.append("V7 独有样本:")
            for item in row["v7_only"][:5]:
                lines.append(f"- `{item}`")
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_inventory(rows: list[dict]) -> str:
    lines = [
        "# Module Diff Inventory",
        "",
        "本清单用于指导 `V7` 修复时的取舍, 先锁主链, 再按候选增量池回收。",
        "",
        "## 已确认的核心差异",
        "",
        "- `frontend-nextjs/app/analysis/[sessionId]/page.tsx`: 当前与 V7 哈希不同, 属于前端主链入口, 禁止整包回收。",
        "- `intelligent_project_analyzer/api/server.py`: 当前与 V7 存在明显入口层差异, 包括路由注册、启动逻辑和版本注入。",
        "- `intelligent_project_analyzer/settings.py`: 当前引入 `PRODUCT_VERSION`, 属于治理性增强, 但会触及运行时配置入口。",
        "- `intelligent_project_analyzer/__init__.py`: 当前改为从 `versioning.py` 读取版本, 不是优先回收项。",
        "- `intelligent_project_analyzer/interaction/nodes/output_intent_detection.py`: 当前与 V7 一致。",
        "- `intelligent_project_analyzer/interaction/nodes/questionnaire_summary.py`: 当前与 V7 一致。",
        "",
        "## 允许作为候选增量池审查的文件",
        "",
    ]
    for rel in SAFE_CANDIDATES:
        current_exists = (CURRENT_ROOT / rel).exists()
        v7_exists = (V7_ROOT / rel).exists()
        status = "可审查" if current_exists else "缺失"
        lines.append(f"- `{rel}`: 当前存在={current_exists}, V7存在={v7_exists}, 状态={status}")
    lines.extend(
        [
            "",
            "## 需要人工复核后才能考虑回收的文件",
            "",
        ]
    )
    for rel in MANUAL_REVIEW_CANDIDATES:
        current_exists = (CURRENT_ROOT / rel).exists()
        v7_exists = (V7_ROOT / rel).exists()
        lines.append(f"- `{rel}`: 当前存在={current_exists}, V7存在={v7_exists}")
    lines.extend(
        [
            "",
            "## 禁止整包覆盖的目录",
            "",
        ]
    )
    for rel in PROHIBITED_DIRECTORIES:
        lines.append(f"- `{rel}`")

    lines.extend(
        [
            "",
            "## 分维度差异样本",
            "",
        ]
    )
    for row in rows:
        lines.append(f"### {row['title']}")
        lines.append(f"- 判定: `{row['label']}`")
        if row["modified"]:
            lines.append("- 内容差异样本:")
            for item in row["modified"][:10]:
                lines.append(f"  - `{item}`")
        if row["current_only"]:
            lines.append("- 仅当前样本:")
            for item in row["current_only"][:10]:
                lines.append(f"  - `{item}`")
        if row["v7_only"]:
            lines.append("- 仅V7样本:")
            for item in row["v7_only"][:10]:
                lines.append(f"  - `{item}`")
        lines.append(f"- 回收建议: {row['recommendation']}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> None:
    rows: list[dict] = []
    for spec in DIMENSIONS:
        summary = compare_paths(spec.paths)
        summary.update(
            {
                "title": spec.title,
                "label": spec.label,
                "rationale": spec.rationale,
                "recommendation": spec.recommendation,
            }
        )
        rows.append(summary)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "runtime_baseline_matrix.md").write_text(render_matrix(rows), encoding="utf-8")
    (REPORT_DIR / "module_diff_inventory.md").write_text(render_inventory(rows), encoding="utf-8")
    print("generated:", REPORT_DIR / "runtime_baseline_matrix.md")
    print("generated:", REPORT_DIR / "module_diff_inventory.md")


if __name__ == "__main__":
    main()
