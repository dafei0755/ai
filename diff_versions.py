"""diff_versions.py - 对比当前版本与备份版本差异"""
import os
import sys
import hashlib
from pathlib import Path
from collections import defaultdict

# 修复 Windows 控制台编码
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

CURRENT = Path(r"d:\11-20\langgraph-design")
BACKUP = Path(r"F:\BaiduNetdiskDownload\2026.2.25\langgraph-design")

# 排除目录
EXCLUDE_DIRS = {
    "__pycache__",
    "node_modules",
    ".next",
    ".git",
    "htmlcov",
    ".pytest_cache",
    "-Force",
    "_archive",
    "backup",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".egg-info",
}
EXCLUDE_EXTS = {".pyc", ".pyo"}


def get_all_files(root: Path) -> set[str]:
    """获取相对路径集合，使用 os.walk 避免进入排除目录"""
    files = set()
    root_str = str(root)
    for dirpath, dirnames, filenames in os.walk(root_str):
        # 原地修改 dirnames 来跳过排除目录
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fname in filenames:
            # 跳过 Windows 特殊设备名
            if fname.lower() in ("nul", "con", "prn", "aux", "com1", "lpt1"):
                continue
            ext = os.path.splitext(fname)[1]
            if ext in EXCLUDE_EXTS:
                continue
            full = os.path.join(dirpath, fname)
            try:
                rel = os.path.relpath(full, root_str).replace("\\", "/")
            except ValueError:
                continue
            files.add(rel)
    return files


def file_hash(path: Path) -> str:
    h = hashlib.md5()
    try:
        h.update(path.read_bytes())
    except Exception:
        return ""
    return h.hexdigest()


def classify_module(rel_path: str) -> str:
    """根据路径分类模块"""
    parts = rel_path.split("/")
    if "external_data_system" in rel_path:
        return "🕷️ 爬虫(external_data_system)"
    if parts[0] == "frontend-nextjs":
        return "🖥️ 前端(frontend-nextjs)"
    if parts[0] == "frontend":
        return "🖥️ 旧前端(frontend)"
    if parts[0] == "tests":
        if "crawler" in rel_path.lower() or "spider" in rel_path.lower():
            return "🕷️🧪 爬虫测试(tests)"
        return "🧪 测试(tests)"
    if parts[0] == "scripts":
        if "crawl" in rel_path.lower() or "spider" in rel_path.lower():
            return "🕷️📜 爬虫脚本(scripts)"
        return "📜 脚本(scripts)"
    if parts[0] == "config":
        return "⚙️ 配置(config)"
    if parts[0] == "docs":
        return "📖 文档(docs)"
    if parts[0] == "docker":
        return "🐳 Docker(docker)"
    if parts[0] == "e2e-tests":
        return "🧪 E2E测试(e2e-tests)"
    if parts[0] == "intelligent_project_analyzer":
        if len(parts) > 1:
            sub = parts[1]
            if "crawl" in sub.lower() or "spider" in sub.lower():
                return "🕷️ 爬虫相关"
            return f"📦 核心({sub})"
        return "📦 核心"
    if parts[0] == "data":
        if "crawl" in rel_path.lower() or "cookie" in rel_path.lower():
            return "🕷️💾 爬虫数据(data)"
        return "💾 数据(data)"
    if parts[0] == "examples":
        return "📝 示例(examples)"
    if parts[0].startswith("_"):
        if (
            "crawl" in parts[0].lower()
            or "spider" in parts[0].lower()
            or "gooood" in parts[0].lower()
            or "scan" in parts[0].lower()
        ):
            return "🕷️🔧 爬虫临时脚本"
        return "🔧 临时脚本(根目录_*)"
    return f"📁 根目录文件"


# 检查备份目录是否存在
if not BACKUP.exists():
    print(f"❌ 备份目录不存在: {BACKUP}")
    print("请确认路径是否正确，或者U盘/网盘是否已挂载。")
    exit(1)

print("正在扫描当前版本...")
current_files = get_all_files(CURRENT)
print(f"  当前版本文件数: {len(current_files)}")

print("正在扫描备份版本...")
backup_files = get_all_files(BACKUP)
print(f"  备份版本文件数: {len(backup_files)}")

only_current = current_files - backup_files
only_backup = backup_files - current_files
common = current_files & backup_files

# 找出内容不同的文件
print(f"正在比对 {len(common)} 个共同文件...")
modified = set()
for i, f in enumerate(common):
    if file_hash(CURRENT / f) != file_hash(BACKUP / f):
        modified.add(f)
    if (i + 1) % 500 == 0:
        print(f"  已比对 {i+1}/{len(common)}...")

# 按模块分类
report = defaultdict(lambda: {"added": [], "deleted": [], "modified": []})

for f in sorted(only_current):
    report[classify_module(f)]["added"].append(f)
for f in sorted(only_backup):
    report[classify_module(f)]["deleted"].append(f)
for f in sorted(modified):
    report[classify_module(f)]["modified"].append(f)

# 输出报告
print()
print("=" * 80)
print("  版本差异报告：当前版本 vs 备份版本(2026.2.25)")
print("=" * 80)
print(
    f"\n  总计: +{len(only_current)} 新增 | -{len(only_backup)} 删除(备份有当前没有) | ~{len(modified)} 修改 | ={len(common)-len(modified)} 相同\n"
)

for module in sorted(report.keys()):
    info = report[module]
    total = len(info["added"]) + len(info["deleted"]) + len(info["modified"])
    if total == 0:
        continue
    print(f"\n{'─'*70}")
    print(f"  {module}  (+{len(info['added'])} -{len(info['deleted'])} ~{len(info['modified'])})")
    print(f"{'─'*70}")
    for f in info["added"][:25]:
        print(f"    + 新增: {f}")
    if len(info["added"]) > 25:
        print(f"    ... 还有 {len(info['added'])-25} 个新增文件")
    for f in info["deleted"][:25]:
        print(f"    - 删除(备份有): {f}")
    if len(info["deleted"]) > 25:
        print(f"    ... 还有 {len(info['deleted'])-25} 个删除文件")
    for f in info["modified"][:40]:
        print(f"    ~ 修改: {f}")
    if len(info["modified"]) > 40:
        print(f"    ... 还有 {len(info['modified'])-40} 个修改文件")

# 汇总统计
print(f"\n{'='*80}")
print("  模块汇总:")
print(f"{'='*80}")
crawler_changes = 0
non_crawler_changes = 0
for module in sorted(report.keys()):
    info = report[module]
    total = len(info["added"]) + len(info["deleted"]) + len(info["modified"])
    if total == 0:
        continue
    is_crawler = "爬虫" in module or "spider" in module.lower()
    if is_crawler:
        crawler_changes += total
    else:
        non_crawler_changes += total
    marker = " [爬虫-保留当前]" if is_crawler else " [可回退到备份]"
    print(f"  {module}: {total} 个变更{marker}")

print(f"\n  爬虫相关变更: {crawler_changes} 个文件")
print(f"  非爬虫变更:   {non_crawler_changes} 个文件")
print(f"\n{'='*80}")
print("报告结束")
