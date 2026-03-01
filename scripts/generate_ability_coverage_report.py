"""
生成能力覆盖报告 - P1 任务验证
================================

快速脚本：读取现有配置，生成覆盖报告
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from intelligent_project_analyzer.utils.ability_query import print_coverage_report

if __name__ == "__main__":
    print("\n🔍 正在扫描专家配置文件...")
    print("📊 生成能力覆盖报告...\n")

    try:
        print_coverage_report()
        print("\n✅ 报告生成完成！")
    except Exception as e:
        print(f"\n❌ 生成报告时出错: {e}")
        import traceback

        traceback.print_exc()
