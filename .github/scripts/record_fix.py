#!/usr/bin/env python3
"""
修复记录器 - 自动记录代码修复过程

功能:
- 捕获修复上下文（文件、错误、代码变更）
- 验证修复结果
- 生成结构化文档
- 更新索引文件

用法:
    python record_fix.py --issue-id "dimension-selector-fix" --description "修复参数不匹配" --status success
    python record_fix.py --interactive  # 交互式模式
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class FixRecorder:
    """修复记录器"""

    FIXES_DIR = Path(".github/historical_fixes")
    FAILURES_DIR = Path(".github/failed_fixes")
    INDEX_FILE = FIXES_DIR / "index.json"

    def __init__(self):
        self.FIXES_DIR.mkdir(parents=True, exist_ok=True)
        self.FAILURES_DIR.mkdir(parents=True, exist_ok=True)
        self._ensure_index()

    def _ensure_index(self):
        """确保索引文件存在"""
        if not self.INDEX_FILE.exists():
            with open(self.INDEX_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "version": "1.0",
                        "last_updated": datetime.now().isoformat(),
                        "total_fixes": 0,
                        "total_failures": 0,
                        "fixes": [],
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

    def record_fix(
        self,
        issue_id: str,
        description: str,
        status: str = "success",
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        changed_files: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        duration: Optional[float] = None,
    ) -> Dict:
        """
        记录一次修复

        Args:
            issue_id: 问题唯一标识
            description: 修复描述
            status: 状态 (success/failed)
            error_type: 错误类型 (如 TypeError)
            error_message: 错误消息
            changed_files: 修改的文件列表
            tags: 标签列表
            author: 作者
            duration: 耗时（秒）

        Returns:
            记录的修复信息字典
        """
        # 自动获取 Git 信息
        if changed_files is None:
            changed_files = self._get_changed_files()

        if author is None:
            author = self._get_git_user()

        # 生成记录
        date_str = datetime.now().strftime("%Y-%m-%d")
        fix_id = f"{'fix' if status == 'success' else 'fail'}-{date_str}-{issue_id}"

        record = {
            "id": fix_id,
            "title": description,
            "date": date_str,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "author": author,
            "issue_id": issue_id,
            "error_type": error_type,
            "error_message": error_message,
            "files": changed_files or [],
            "tags": tags or self._auto_generate_tags(description, error_type, changed_files),
            "duration": duration,
        }

        # 保存文件
        self._save_record(record)

        # 更新索引
        self._update_index(record)

        # 输出结果
        emoji = "✅" if status == "success" else "❌"
        print(f"\n{emoji} 修复记录已保存:")
        print(f"   ID: {fix_id}")
        print(f"   描述: {description}")
        print(f"   状态: {status}")
        print(f"   文件: {len(changed_files or [])} 个")
        print(f"   路径: {record['path']}\n")

        return record

    def _save_record(self, record: Dict):
        """保存记录到文件"""
        target_dir = self.FIXES_DIR if record["status"] == "success" else self.FAILURES_DIR

        # 生成文件名
        filename = f"{record['date']}_{record['issue_id']}"

        # 保存 JSON
        json_path = target_dir / f"{filename}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)

        # 保存 Markdown
        md_path = target_dir / f"{filename}.md"
        md_content = self._generate_markdown(record)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        record["path"] = str(md_path.relative_to(Path.cwd()))

    def _update_index(self, record: Dict):
        """更新索引文件"""
        with open(self.INDEX_FILE, "r", encoding="utf-8") as f:
            index = json.load(f)

        # 添加新记录
        index["fixes"].append(
            {
                "id": record["id"],
                "title": record["title"],
                "date": record["date"],
                "status": record["status"],
                "tags": record["tags"],
                "files": record["files"],
                "error_type": record.get("error_type"),
                "error_message": record.get("error_message"),
                "path": record["path"],
            }
        )

        # 更新统计
        index["last_updated"] = datetime.now().isoformat()
        if record["status"] == "success":
            index["total_fixes"] = index.get("total_fixes", 0) + 1
        else:
            index["total_failures"] = index.get("total_failures", 0) + 1

        # 保存索引
        with open(self.INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

        print(f"✅ 索引已更新: {self.INDEX_FILE}")

    def _generate_markdown(self, record: Dict) -> str:
        """生成 Markdown 文档"""
        status_emoji = "✅" if record["status"] == "success" else "❌"

        return f"""# {status_emoji} {record['title']}

**Issue ID**: `{record['issue_id']}`
**Fix ID**: `{record['id']}`
**Status**: {status_emoji} {record['status'].upper()}
**Date**: {record['date']}
**Author**: {record['author'] or 'Unknown'}
{f"**Duration**: {record['duration']:.2f}s  " if record.get('duration') else ''}

---

## 📋 问题描述

{f"**错误类型**: `{record['error_type']}`" if record.get('error_type') else ''}

{f"**错误信息**:" if record.get('error_message') else ''}
{f"```" if record.get('error_message') else ''}
{record.get('error_message', '') if record.get('error_message') else '[待补充]'}
{f"```" if record.get('error_message') else ''}

---

## 📝 相关文件

{chr(10).join(f"- `{f}`" for f in record['files']) if record['files'] else '无'}

---

## 🔧 修复方案

[待补充：详细描述修复方案]

### 实施步骤

1. [步骤 1]
2. [步骤 2]
3. [步骤 3]

---

## {status_emoji} {'验证结果' if record['status'] == 'success' else '失败原因'}

[待补充：{'测试结果和验证过程' if record['status'] == 'success' else '失败原因分析和后续建议'}]

---

## 📚 经验教训

[待补充：从这次修复中学到了什么]

---

## 🏷️ 标签

{' '.join(f'`{tag}`' for tag in record['tags'])}

---

**生成时间**: {record['timestamp']}
**自动生成**: 此文档由 `record_fix.py` 自动生成，请手动补充详细内容
"""

    def _get_changed_files(self) -> List[str]:
        """获取 Git 中修改的文件"""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, check=True
            )
            files = [f for f in result.stdout.strip().split("\n") if f]

            if not files:
                # 尝试获取最近一次提交的文件
                result = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD~1", "HEAD"], capture_output=True, text=True, check=True
                )
                files = [f for f in result.stdout.strip().split("\n") if f]

            return files
        except subprocess.CalledProcessError:
            return []

    def _get_git_user(self) -> str:
        """获取 Git 用户名"""
        try:
            result = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "Unknown"

    def _auto_generate_tags(self, description: str, error_type: Optional[str], files: Optional[List[str]]) -> List[str]:
        """自动生成标签"""
        tags = []

        # 基于错误类型
        if error_type:
            tags.append(error_type.lower())

        # 基于描述关键词
        keywords_map = {
            "参数": "parameter",
            "接口": "interface",
            "类型": "type",
            "编码": "encoding",
            "配置": "configuration",
            "性能": "performance",
            "安全": "security",
            "维度": "dimension",
            "问卷": "questionnaire",
        }

        for keyword, tag in keywords_map.items():
            if keyword in description:
                tags.append(tag)

        # 基于文件路径
        if files:
            for file in files:
                if "services" in file:
                    tags.append("service")
                if "workflow" in file:
                    tags.append("workflow")
                if "agents" in file:
                    tags.append("agent")

        return list(set(tags))  # 去重

    def interactive_mode(self):
        """交互式记录模式"""
        print("📝 交互式修复记录\n")

        issue_id = input("Issue ID (如 dimension-selector-fix): ").strip()
        description = input("修复描述: ").strip()

        print("\n状态选择:")
        print("  1. ✅ success")
        print("  2. ❌ failed")
        status_choice = input("选择 (1/2) [默认 1]: ").strip() or "1"
        status = "success" if status_choice == "1" else "failed"

        error_type = input("错误类型 (如 TypeError，可选): ").strip() or None
        error_message = input("错误消息 (可选): ").strip() or None

        print(f"\n检测到修改的文件:")
        files = self._get_changed_files()
        if files:
            for i, f in enumerate(files, 1):
                print(f"  {i}. {f}")
            use_auto = input("使用这些文件? (Y/n) [默认 Y]: ").strip().lower()
            if use_auto == "n":
                files = None
        else:
            print("  (未检测到)")
            files = None

        tags_input = input("\n标签 (逗号分隔，可选): ").strip()
        tags = [t.strip() for t in tags_input.split(",")] if tags_input else None

        print("\n正在记录...")
        self.record_fix(
            issue_id=issue_id,
            description=description,
            status=status,
            error_type=error_type,
            error_message=error_message,
            changed_files=files,
            tags=tags,
        )


def main():
    parser = argparse.ArgumentParser(description="修复记录器")
    parser.add_argument("--issue-id", help="问题唯一标识")
    parser.add_argument("--description", help="修复描述")
    parser.add_argument("--status", choices=["success", "failed"], default="success")
    parser.add_argument("--error-type", help="错误类型 (如 TypeError)")
    parser.add_argument("--error-message", help="错误消息")
    parser.add_argument("--files", nargs="+", help="修改的文件列表")
    parser.add_argument("--tags", nargs="+", help="标签列表")
    parser.add_argument("--author", help="作者")
    parser.add_argument("--duration", type=float, help="耗时（秒）")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互式模式")

    args = parser.parse_args()

    recorder = FixRecorder()

    if args.interactive:
        recorder.interactive_mode()
    elif args.issue_id and args.description:
        recorder.record_fix(
            issue_id=args.issue_id,
            description=args.description,
            status=args.status,
            error_type=args.error_type,
            error_message=args.error_message,
            changed_files=args.files,
            tags=args.tags,
            author=args.author,
            duration=args.duration,
        )
    else:
        parser.print_help()
        print("\n提示: 使用 --interactive 进入交互式模式")
        sys.exit(1)


if __name__ == "__main__":
    main()
