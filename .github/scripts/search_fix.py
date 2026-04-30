#!/usr/bin/env python3
"""
修复历史搜索工具 - 快速查找相似问题的解决方案

用法:
    python search_fix.py --error TypeError
    python search_fix.py --file dimension_selector.py
    python search_fix.py --tag parameter-mismatch
    python search_fix.py --keyword "special_scenes"
    python search_fix.py --recent 10  # 最近10条
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class FixSearcher:
    """修复记录搜索器"""

    INDEX_FILE = Path(".github/historical_fixes/index.json")

    def __init__(self):
        self.index = self._load_index()

    def _load_index(self) -> Dict:
        """加载索引文件"""
        if not self.INDEX_FILE.exists():
            print(f"⚠️ 索引文件不存在: {self.INDEX_FILE}")
            return {"fixes": []}

        with open(self.INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def search(
        self,
        error_type: Optional[str] = None,
        file_pattern: Optional[str] = None,
        tag: Optional[str] = None,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        recent: Optional[int] = None,
    ) -> List[Dict]:
        """
        搜索修复记录

        Args:
            error_type: 错误类型 (如 TypeError)
            file_pattern: 文件路径模式
            tag: 标签
            keyword: 关键词
            status: 状态 (success/failed)
            recent: 返回最近N条记录

        Returns:
            匹配的修复记录列表
        """
        results = []
        fixes = self.index.get("fixes", [])

        # 按日期排序（最新的在前）
        fixes = sorted(fixes, key=lambda x: x.get("date", ""), reverse=True)

        for fix in fixes:
            match = True

            # 错误类型匹配
            if error_type:
                fix_error = fix.get("error_type", "").lower()
                if error_type.lower() not in fix_error:
                    match = False

            # 文件路径匹配
            if file_pattern:
                files = fix.get("files", [])
                if not any(file_pattern.lower() in f.lower() for f in files):
                    match = False

            # 标签匹配
            if tag:
                tags = fix.get("tags", [])
                if tag.lower() not in [t.lower() for t in tags]:
                    match = False

            # 关键词匹配（全文搜索）
            if keyword:
                searchable_text = json.dumps(fix, ensure_ascii=False).lower()
                if keyword.lower() not in searchable_text:
                    match = False

            # 状态匹配
            if status:
                if fix.get("status") != status:
                    match = False

            if match:
                results.append(fix)

        # 限制返回数量
        if recent:
            results = results[:recent]

        return results

    def display_results(self, results: List[Dict], verbose: bool = False):
        """显示搜索结果"""
        if not results:
            print("❌ 未找到匹配的修复记录")
            print("\n提示:")
            print("  - 尝试更宽泛的搜索条件")
            print("  - 检查拼写是否正确")
            print("  - 使用 --keyword 进行全文搜索")
            return

        print(f"✅ 找到 {len(results)} 条匹配记录:\n")
        print("=" * 80)

        for i, fix in enumerate(results, 1):
            status_emoji = "✅" if fix["status"] == "success" else "❌"

            print(f"\n{i}. {status_emoji} {fix['title']}")
            print(f"   ID: {fix['id']}")
            print(f"   日期: {fix['date']}")
            print(f"   状态: {fix['status']}")

            if fix.get("error_type"):
                print(f"   错误类型: {fix['error_type']}")

            if verbose and fix.get("error_message"):
                print(f"   错误信息: {fix['error_message'][:100]}...")

            if fix.get("files"):
                file_count = len(fix["files"])
                files_display = fix["files"][:3]
                print(f"   文件 ({file_count}): {', '.join(files_display)}")
                if file_count > 3:
                    print(f"           ... 还有 {file_count - 3} 个")

            if fix.get("tags"):
                print(f"   标签: {', '.join(fix['tags'])}")

            print(f"   文档: {fix['path']}")
            print("-" * 80)

        print(f"\n💡 提示: 使用 --verbose 查看更多详情")
        print(f"💡 提示: 使用 cat 或编辑器打开文档查看完整内容")

    def get_stats(self) -> Dict:
        """获取统计信息"""
        fixes = self.index.get("fixes", [])

        total = len(fixes)
        success = sum(1 for f in fixes if f.get("status") == "success")
        failed = total - success

        # 统计错误类型
        error_types = {}
        for fix in fixes:
            error_type = fix.get("error_type", "Unknown")
            error_types[error_type] = error_types.get(error_type, 0) + 1

        # 统计最常修改的文件
        file_counts = {}
        for fix in fixes:
            for file in fix.get("files", []):
                file_counts[file] = file_counts.get(file, 0) + 1

        # 统计标签
        tag_counts = {}
        for fix in fixes:
            for tag in fix.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": (success / total * 100) if total > 0 else 0,
            "error_types": sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5],
            "frequent_files": sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "popular_tags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10],
        }

    def display_stats(self):
        """显示统计信息"""
        stats = self.get_stats()

        print("📊 修复记录统计")
        print("=" * 80)
        print(f"\n总体统计:")
        print(f"  总记录数: {stats['total']}")
        print(f"  成功: {stats['success']} ({stats['success_rate']:.1f}%)")
        print(f"  失败: {stats['failed']} ({100 - stats['success_rate']:.1f}%)")

        if stats["error_types"]:
            print(f"\nTop 5 错误类型:")
            for error_type, count in stats["error_types"]:
                print(f"  - {error_type}: {count} 次")

        if stats["frequent_files"]:
            print(f"\nTop 5 频繁修改文件:")
            for file, count in stats["frequent_files"]:
                print(f"  - {file}: {count} 次")

        if stats["popular_tags"]:
            print(f"\n热门标签:")
            tags_str = ", ".join(f"{tag}({count})" for tag, count in stats["popular_tags"])
            print(f"  {tags_str}")

        print("\n" + "=" * 80)
        print(f"最后更新: {self.index.get('last_updated', 'Unknown')}")


def main():
    parser = argparse.ArgumentParser(
        description="搜索历史修复记录", epilog="示例: python search_fix.py --error TypeError --file dimension_selector"
    )

    # 搜索条件
    parser.add_argument("--error", "-e", help="错误类型 (如 TypeError)")
    parser.add_argument("--file", "-f", help="文件路径模式")
    parser.add_argument("--tag", "-t", help="标签")
    parser.add_argument("--keyword", "-k", help="关键词（全文搜索）")
    parser.add_argument("--status", "-s", choices=["success", "failed"], help="状态")
    parser.add_argument("--recent", "-r", type=int, help="显示最近N条记录")

    # 显示选项
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")

    args = parser.parse_args()

    searcher = FixSearcher()

    # 显示统计信息
    if args.stats:
        searcher.display_stats()
        return

    # 执行搜索
    results = searcher.search(
        error_type=args.error,
        file_pattern=args.file,
        tag=args.tag,
        keyword=args.keyword,
        status=args.status,
        recent=args.recent,
    )

    searcher.display_results(results, verbose=args.verbose)

    # 如果找到结果，提示相关操作
    if results:
        print("\n📚 后续操作:")
        print("  - 查看详细文档: cat [文档路径]")
        print("  - 编辑补充内容: code [文档路径]")
        print("  - 查看代码变更: git show [commit-hash]")


if __name__ == "__main__":
    main()
