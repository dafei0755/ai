"""
MT-6 原子重命名迁移脚本
=======================
将节点名与业务执行顺序对齐：

  旧                              新
  progressive_step3_gap_filling → progressive_step2_info_gather
  progressive_step2_radar       → progressive_step3_radar
  （以及对应的方法/函数名）

策略：两阶段交换，用临时占位符避免交叉污染。

Phase 1: step3_gap_filling → SWAPTEMP (avoid collision)
Phase 2: step2_radar       → step3_radar
Phase 3: SWAPTEMP          → step2_info_gather
"""

from pathlib import Path
import sys

ROOT = Path(__file__).parent

# ── 需要更新的文件列表 ──────────────────────────────────────────────────────
FILES = [
    # Python 源码
    ROOT / "intelligent_project_analyzer/workflow/main_workflow.py",
    ROOT / "intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py",
    ROOT / "intelligent_project_analyzer/api/admin_routes.py",
    ROOT / "intelligent_project_analyzer/api/workflow_runner.py",
    # 测试文件
    ROOT / "tests/e2e/test_v8_questionnaire_e2e.py",
    ROOT / "tests/integration/test_v8_radar_integration.py",
    ROOT / "tests/regression/test_v8_radar_regression.py",
    ROOT / "tests/regression/test_v93_regression.py",
    # 前端 TypeScript
    ROOT / "frontend-nextjs/app/analysis/[sessionId]/page.tsx",
    ROOT / "frontend-nextjs/app/admin/capability-boundary/page.tsx",
]

# 还需要查找 questionnaire_summary.py 等可能含引用的文件
EXTRA_PY_DIRS = [
    ROOT / "intelligent_project_analyzer/interaction/nodes",
    ROOT / "intelligent_project_analyzer/api",
]


def find_extra_files():
    """扫描额外目录，找到含旧节点名的文件（未在 FILES 中的）."""
    extra = []
    for d in EXTRA_PY_DIRS:
        if not d.exists():
            continue
        for f in d.glob("*.py"):
            if f in FILES:
                continue
            try:
                content = f.read_text(encoding="utf-8")
                if "progressive_step2_radar" in content or "progressive_step3_gap_filling" in content:
                    extra.append(f)
                    print(f"  [EXTRA] 发现额外文件: {f.relative_to(ROOT)}")
            except Exception:
                pass
    return extra


# ── 替换规则（两阶段，用 SWAPTEMP 避免交叉污染）───────────────────────────

PHASE1_REPLACEMENTS = [
    # 节点名字符串（最具体的先）
    ("progressive_step3_gap_filling_node", "progressive_SWAPTEMP_info_gather_node"),
    ("progressive_step3_gap_filling", "progressive_SWAPTEMP_info_gather"),
    # 方法名
    ("def step3_gap_filling", "def SWAPTEMP_info_gather"),
    # 注释/文档中的引用
    ("step3_gap_filling", "SWAPTEMP_info_gather"),
]

PHASE2_REPLACEMENTS = [
    # 节点名字符串（最具体的先）
    ("progressive_step2_radar_node", "progressive_step3_radar_node"),
    ("progressive_step2_radar", "progressive_step3_radar"),
    # 方法名
    ("def step2_radar", "def step3_radar"),
    # 注释/文档中的引用
    ("step2_radar", "step3_radar"),
]

PHASE3_REPLACEMENTS = [
    # 还原 SWAPTEMP → 正式名称
    ("progressive_SWAPTEMP_info_gather_node", "progressive_step2_info_gather_node"),
    ("progressive_SWAPTEMP_info_gather", "progressive_step2_info_gather"),
    ("def SWAPTEMP_info_gather", "def step2_info_gather"),
    ("SWAPTEMP_info_gather", "step2_info_gather"),
]


def apply_replacements(content: str, replacements: list[tuple[str, str]]) -> str:
    for old, new in replacements:
        content = content.replace(old, new)
    return content


def migrate_file(filepath: Path) -> tuple[int, str]:
    """迁移单个文件，返回 (替换次数, 新内容)."""
    if not filepath.exists():
        print(f"  [SKIP] 文件不存在: {filepath}")
        return 0, ""

    original = filepath.read_text(encoding="utf-8")

    c = original
    c = apply_replacements(c, PHASE1_REPLACEMENTS)
    c = apply_replacements(c, PHASE2_REPLACEMENTS)
    c = apply_replacements(c, PHASE3_REPLACEMENTS)

    # 统计实际变更次数
    changes = sum(
        original.count(old)
        for old, _ in PHASE1_REPLACEMENTS + PHASE2_REPLACEMENTS
        if old not in {r[0] for r in PHASE3_REPLACEMENTS}  # 排除 SWAPTEMP 行
    )

    return c != original, c


def main():
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    print(f"MT-6 重命名迁移 {'[DRY RUN]' if dry_run else '[APPLY]'}")
    print("=" * 60)

    # 扫描额外文件
    extra_files = find_extra_files()
    all_files = FILES + extra_files

    changed_count = 0
    skipped_count = 0
    details = []

    for filepath in all_files:
        changed, new_content = migrate_file(filepath)
        rel = filepath.relative_to(ROOT) if filepath.is_absolute() else filepath

        if changed:
            changed_count += 1
            details.append(str(rel))
            if not dry_run:
                filepath.write_text(new_content, encoding="utf-8")
                print(f"  [OK] {rel}")
            else:
                print(f"  [DRY] {rel}")
        else:
            skipped_count += 1

    print("\n" + "=" * 60)
    print(f"已{'更新' if not dry_run else '分析'}: {changed_count} 个文件")
    print(f"无变更跳过: {skipped_count} 个文件")
    if details:
        print("\n变更文件列表:")
        for d in details:
            print(f"  - {d}")

    # 验证：确认 SWAPTEMP 在文件中已消除
    if not dry_run:
        print("\n[验证] 检查 SWAPTEMP 残留...")
        has_residual = False
        for filepath in all_files:
            if filepath.exists():
                c = filepath.read_text(encoding="utf-8")
                if "SWAPTEMP" in c:
                    print(f"  [ERROR] SWAPTEMP 残留: {filepath}")
                    has_residual = True
        if not has_residual:
            print("  [OK] 无 SWAPTEMP 残留")


if __name__ == "__main__":
    main()
