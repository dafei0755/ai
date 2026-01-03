"""
自动化代码清理工具 - print语句转logger

功能：
1. 扫描Python文件中的print()语句
2. 分类print语句（debug/info/user-facing）
3. 生成logger替换建议
4. 可选：自动应用安全替换

使用方法：
    python scripts/cleanup_print_statements.py --scan intelligent_project_analyzer/
    python scripts/cleanup_print_statements.py --fix intelligent_project_analyzer/api/server.py --dry-run
    python scripts/cleanup_print_statements.py --fix intelligent_project_analyzer/api/server.py --apply

版本：v1.0
创建日期：2025-12-31
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class PrintStatementAnalyzer:
    """print语句分析器"""

    def __init__(self):
        # 排除目录
        self.exclude_dirs = {"tests", "examples", "frontend", "docs", "__pycache__", ".git", "node_modules"}

        # 排除文件
        self.exclude_files = {
            "debug_server_import.py",
            "run_frontend.py",
            "test_frontend.py",
            "cleanup_print_statements.py",
        }

        # 分类规则
        self.debug_patterns = [
            r'print\(["\']?DEBUG',
            r'print\(f?["\'].*调试',
            r'print\(f?["\'].*debug',
            r"print\(.*traceback",
            r'print\(f?["\']={3,}',  # 分隔线
        ]

        self.info_patterns = [
            r'print\(f?["\']✅',
            r'print\(f?["\']🚀',
            r'print\(f?["\'].*启动',
            r'print\(f?["\'].*完成',
            r'print\(f?["\'].*成功',
        ]

        self.warning_patterns = [
            r'print\(f?["\']⚠',
            r'print\(f?["\'].*警告',
            r'print\(f?["\'].*warning',
        ]

    def should_exclude(self, file_path: Path) -> bool:
        """检查文件是否应该被排除"""
        # 检查目录
        for part in file_path.parts:
            if part in self.exclude_dirs:
                return True

        # 检查文件名
        if file_path.name in self.exclude_files:
            return True

        return False

    def classify_print(self, line: str) -> str:
        """分类print语句"""
        # 检查debug模式
        for pattern in self.debug_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return "debug"

        # 检查warning模式
        for pattern in self.warning_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return "warning"

        # 检查info模式
        for pattern in self.info_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return "info"

        # 默认为debug
        return "debug"

    def suggest_replacement(self, line: str, indent: str) -> str:
        """建议替换方案"""
        category = self.classify_print(line)

        # 提取print内容
        # 简化处理：提取print()括号内的内容
        match = re.search(r"print\((.*)\)", line)
        if not match:
            return line

        content = match.group(1).strip()

        # 生成logger调用
        if category == "debug":
            replacement = f"{indent}logger.debug({content})"
        elif category == "info":
            replacement = f"{indent}logger.info({content})"
        elif category == "warning":
            replacement = f"{indent}logger.warning({content})"
        else:
            replacement = f"{indent}logger.info({content})"

        return replacement

    def scan_file(self, file_path: Path) -> List[Dict]:
        """扫描单个文件"""
        results = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                # 检查是否包含print(
                if "print(" in line and not line.strip().startswith("#"):
                    # 提取缩进
                    indent = line[: len(line) - len(line.lstrip())]

                    category = self.classify_print(line)
                    replacement = self.suggest_replacement(line, indent)

                    results.append(
                        {
                            "file": str(file_path),
                            "line_num": line_num,
                            "original": line.rstrip(),
                            "category": category,
                            "suggested": replacement,
                        }
                    )

        except Exception as e:
            print(f"⚠️  读取文件失败 {file_path}: {e}")

        return results

    def scan_directory(self, directory: Path) -> Dict[str, List[Dict]]:
        """扫描目录"""
        all_results = {}

        # 递归查找所有.py文件
        py_files = list(directory.rglob("*.py"))

        for py_file in py_files:
            if self.should_exclude(py_file):
                continue

            results = self.scan_file(py_file)
            if results:
                all_results[str(py_file)] = results

        return all_results

    def print_summary(self, all_results: Dict[str, List[Dict]]):
        """打印扫描摘要"""
        total_count = sum(len(results) for results in all_results.values())
        file_count = len(all_results)

        # 按类别统计
        category_counts = {"debug": 0, "info": 0, "warning": 0}
        for results in all_results.values():
            for result in results:
                category_counts[result["category"]] += 1

        print("=" * 80)
        print("📊 PRINT语句扫描摘要")
        print("=" * 80)
        print(f"文件总数: {file_count}")
        print(f"print语句总数: {total_count}")
        print()
        print("按类别分类:")
        print(f"  🔍 Debug:   {category_counts['debug']}")
        print(f"  ℹ️  Info:    {category_counts['info']}")
        print(f"  ⚠️  Warning: {category_counts['warning']}")
        print()

        # 按文件排序
        print("按文件分布 (前20个):")
        file_counts = [(file, len(results)) for file, results in all_results.items()]
        file_counts.sort(key=lambda x: x[1], reverse=True)

        for i, (file, count) in enumerate(file_counts[:20], 1):
            # 简化文件路径显示
            short_path = Path(file).relative_to(Path.cwd()) if Path.cwd() in Path(file).parents else Path(file)
            print(f"  {i:2d}. {short_path}: {count}")

    def apply_fixes(self, file_path: Path, dry_run: bool = True) -> bool:
        """应用修复到文件"""
        results = self.scan_file(file_path)

        if not results:
            print(f"✅ {file_path}: 未发现print语句")
            return True

        print(f"\n{'=' * 80}")
        print(f"📝 处理文件: {file_path}")
        print(f"{'=' * 80}")
        print(f"发现 {len(results)} 个print语句\n")

        # 读取文件
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 检查是否已有logger导入
        has_logger_import = False
        for line in lines:
            if "import logging" in line or "from logging import" in line:
                has_logger_import = True
                break

        if not has_logger_import:
            print("⚠️  文件中未发现logging导入")
            print("建议在文件顶部添加:")
            print("    import logging")
            print("    logger = logging.getLogger(__name__)")
            print()

        # 显示建议的替换
        for i, result in enumerate(results, 1):
            print(f"{i}. Line {result['line_num']}:")
            print(f"   原始: {result['original']}")
            print(f"   建议: {result['suggested']}")
            print(f"   类别: {result['category']}")
            print()

        if dry_run:
            print("🔍 这是dry-run模式，未实际修改文件")
            print("使用 --apply 标志来应用修改")
            return True

        # 应用修改
        print("⚠️  应用修改功能暂未实现")
        print("建议：手动复制上述建议进行替换")

        return True


def main():
    # Windows编码修复
    if sys.platform == "win32":
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

    parser = argparse.ArgumentParser(description="自动化print语句清理工具")
    parser.add_argument("--scan", type=str, help="扫描目录")
    parser.add_argument("--fix", type=str, help="修复指定文件")
    parser.add_argument("--dry-run", action="store_true", help="仅显示建议，不修改文件")
    parser.add_argument("--apply", action="store_true", help="应用修改到文件")

    args = parser.parse_args()

    analyzer = PrintStatementAnalyzer()

    if args.scan:
        # 扫描模式
        scan_path = Path(args.scan)
        if not scan_path.exists():
            print(f"❌ 路径不存在: {scan_path}")
            sys.exit(1)

        print(f"🔍 扫描目录: {scan_path}")
        print(f"排除目录: {', '.join(analyzer.exclude_dirs)}")
        print()

        results = analyzer.scan_directory(scan_path)
        analyzer.print_summary(results)

        # 保存详细结果
        output_file = Path("print_statement_analysis.txt")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("PRINT语句详细分析\n")
            f.write("=" * 80 + "\n\n")

            for file, file_results in results.items():
                f.write(f"\n文件: {file}\n")
                f.write("-" * 80 + "\n")

                for result in file_results:
                    f.write(f"Line {result['line_num']} ({result['category']}):\n")
                    f.write(f"  原始: {result['original']}\n")
                    f.write(f"  建议: {result['suggested']}\n\n")

        print()
        print(f"✅ 详细分析已保存到: {output_file}")

    elif args.fix:
        # 修复模式
        fix_path = Path(args.fix)
        if not fix_path.exists():
            print(f"❌ 文件不存在: {fix_path}")
            sys.exit(1)

        dry_run = not args.apply
        analyzer.apply_fixes(fix_path, dry_run=dry_run)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
