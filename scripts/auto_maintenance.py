#!/usr/bin/env python
"""
自动维护调度器 - 数据库定期清理和优化

功能：
1. 清理 base64 图片数据
2. VACUUM 压缩数据库
3. 归档旧会话（可选）
4. 统计报告

作者: Claude (GitHub Copilot)
创建: 2026-02-06
版本: v7.402
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
import subprocess

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_script(script_path: str, description: str) -> dict:
    """
    执行脚本并返回结果

    Args:
        script_path: 脚本路径
        description: 脚本描述

    Returns:
        执行结果字典
    """
    print(f"\n{'=' * 80}")
    print(f"⏳ {description}")
    print(f"{'=' * 80}")

    start_time = time.time()

    try:
        result = subprocess.run(
            ["python", script_path], capture_output=True, text=True, encoding="utf-8", timeout=600  # 10分钟超时
        )

        elapsed = time.time() - start_time

        if result.returncode == 0:
            print(result.stdout)
            print(f"✅ 完成，耗时: {elapsed:.2f}秒")
            return {"success": True, "elapsed": elapsed, "output": result.stdout}
        else:
            print(result.stdout)
            print(result.stderr)
            print(f"❌ 失败，耗时: {elapsed:.2f}秒")
            return {"success": False, "elapsed": elapsed, "error": result.stderr}

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        print(f"❌ 超时（{elapsed:.0f}秒）")
        return {"success": False, "elapsed": elapsed, "error": "Timeout"}

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ 异常: {e}")
        return {"success": False, "elapsed": elapsed, "error": str(e)}


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据库自动维护调度器")
    parser.add_argument("--once", action="store_true", help="执行一次维护后退出（用于任务计划）")
    parser.add_argument("--archive", action="store_true", help="同时执行会话归档（30天前）")
    parser.add_argument("--skip-vacuum", action="store_true", help="跳过 VACUUM 压缩（节省时间）")

    args = parser.parse_args()

    print("=" * 80)
    print("🔧 数据库自动维护调度器 v7.402")
    print("=" * 80)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 工作目录: {project_root}")

    # 执行维护任务
    tasks = []

    # 任务1: 清理 base64 数据
    result1 = run_script(str(project_root / "clean_base64_from_db.py"), "第1步：清理 base64 图片数据")
    tasks.append(("清理 base64", result1))

    # 任务2: VACUUM 压缩
    if not args.skip_vacuum:
        result2 = run_script(str(project_root / "vacuum_db_now.py"), "第2步：VACUUM 压缩数据库")
        tasks.append(("VACUUM 压缩", result2))
    else:
        print("\n⏭️  跳过 VACUUM 压缩")

    # 可选任务3: 归档旧会话
    if args.archive:
        result3 = run_script(str(project_root / "scripts" / "database_maintenance.py"), "第3步：归档30天前的会话（可选）")
        tasks.append(("归档旧会话", result3))

    # 生成报告
    print("\n" + "=" * 80)
    print("📊 维护报告")
    print("=" * 80)

    total_time = sum(t[1]["elapsed"] for t in tasks)
    success_count = sum(1 for t in tasks if t[1]["success"])

    for name, result in tasks:
        status = "✅ 成功" if result["success"] else "❌ 失败"
        print(f"  {name:<20} {status} ({result['elapsed']:.1f}秒)")

    print(f"\n总计: {success_count}/{len(tasks)} 个任务成功，耗时 {total_time:.1f}秒")

    # 建议
    print("\n💡 建议:")
    if success_count == len(tasks):
        print("  ✅ 所有维护任务已成功完成！")
        print("  📅 下次维护建议: 1周后")
    else:
        print("  ⚠️  部分任务失败，请检查日志")
        print("  🔍 建议手动运行失败的脚本排查问题")

    print("\n⏰ 结束时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)

    # 返回状态码
    sys.exit(0 if success_count == len(tasks) else 1)


if __name__ == "__main__":
    main()
