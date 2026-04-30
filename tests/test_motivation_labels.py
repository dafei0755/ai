"""
测试动机类型标签优化
验证所有12种类型的label_zh已去掉"需求"两个字
"""

import os
import sys

# 设置UTF-8编码
if sys.platform == "win32":
    for _stream in (getattr(sys, "stdout", None), getattr(sys, "stderr", None)):
        if _stream is None:
            continue
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligent_project_analyzer.services.motivation_engine import get_motivation_engine


def test_motivation_labels():
    """测试动机类型标签"""
    engine = get_motivation_engine()

    print("=" * 80)
    print("动机类型标签优化验证")
    print("=" * 80)
    print()

    # 获取所有类型
    all_types = engine.registry.get_all_types()

    print(f"✅ 加载了 {len(all_types)} 个动机类型\n")

    # 预期的新标签（无"需求"）
    expected_labels = {
        "cultural": "文化认同",
        "commercial": "商业价值",
        "wellness": "健康疗愈",
        "technical": "技术创新",
        "sustainable": "可持续价值",
        "professional": "专业职能",
        "inclusive": "包容性",
        "functional": "功能性",
        "emotional": "情感性",
        "aesthetic": "审美",
        "social": "社交",
        "mixed": "综合",
    }

    # 验证每个类型
    success_count = 0
    fail_count = 0

    for mtype in all_types:
        expected = expected_labels.get(mtype.id, f"未知类型({mtype.id})")
        actual = mtype.label_zh

        if actual == expected:
            print(f"✅ {mtype.id:15} | '{actual}' (正确)")
            success_count += 1
        else:
            print(f"❌ {mtype.id:15} | '{actual}' (预期: '{expected}')")
            fail_count += 1

    print()
    print("=" * 80)
    print(f"测试结果: {success_count}✅ 通过 | {fail_count}❌ 失败")
    print("=" * 80)

    # 检查是否还有"需求"字样
    print("\n检查是否还有'需求'字样：")
    has_xuqiu = False
    for mtype in all_types:
        if "需求" in mtype.label_zh:
            print(f"  ⚠️ {mtype.id}: '{mtype.label_zh}' 仍包含'需求'")
            has_xuqiu = True

    if not has_xuqiu:
        print("  ✅ 所有标签都已去掉'需求'！")

    return fail_count == 0 and not has_xuqiu


if __name__ == "__main__":
    success = test_motivation_labels()
    sys.exit(0 if success else 1)
