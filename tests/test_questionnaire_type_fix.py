"""
测试问卷类型修复功能

验证后端能够正确修复各种错误的问题类型别名，包括：
- multi_choice → multiple_choice
- checkbox → multiple_choice
- radio → single_choice
- text → open_ended
等其他常见错误格式

运行方式：
    pytest tests/test_questionnaire_type_fix.py -v
    或
    python tests/test_questionnaire_type_fix.py
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from intelligent_project_analyzer.interaction.questionnaire.llm_generator import LLMQuestionGenerator
from intelligent_project_analyzer.services.llm_gap_question_generator import LLMGapQuestionGenerator


def test_llm_generator_type_fix():
    """测试 LLMQuestionGenerator 的类型修复功能"""
    logger.info("=" * 60)
    logger.info("测试 LLMQuestionGenerator 类型修复")
    logger.info("=" * 60)

    # 模拟LLM返回的错误类型问题
    raw_questions = [
        {"id": "q1", "question": "这是单选题", "type": "single", "options": ["A", "B", "C"], "context": "测试"},  # 错误类型
        {"id": "q2", "question": "这是多选题", "type": "multi_choice", "options": ["A", "B", "C"], "context": "测试"},  # 错误类型
        {"id": "q3", "question": "这是另一个多选题", "type": "checkbox", "options": ["A", "B"], "context": "测试"},  # 错误类型
        {"id": "q4", "question": "这是单选题2", "type": "radio", "options": ["X", "Y"], "context": "测试"},  # 错误类型
        {"id": "q5", "question": "这是开放题", "type": "text", "placeholder": "请输入", "context": "测试"},  # 错误类型
        {"id": "q6", "question": "这是下拉选择", "type": "select", "options": ["选项1", "选项2"], "context": "测试"},  # 错误类型
        {"id": "q7", "question": "这是开放文本", "type": "textarea", "placeholder": "请详细描述", "context": "测试"},  # 错误类型
        {
            "id": "q8",
            "question": "这是多选带横线",
            "type": "multi-choice",  # 错误类型
            "options": ["A", "B", "C"],
            "context": "测试",
        },
    ]

    # 调用验证方法
    fixed_questions = LLMQuestionGenerator._validate_and_fix_questions(raw_questions)

    # 验证修复结果
    expected_types = {
        "q1": "single_choice",
        "q2": "multiple_choice",
        "q3": "multiple_choice",
        "q4": "single_choice",
        "q5": "open_ended",
        "q6": "single_choice",
        "q7": "open_ended",
        "q8": "multiple_choice",
    }

    logger.info(f"\n📊 修复结果统计:")
    all_passed = True
    for q in fixed_questions:
        qid = q["id"]
        expected = expected_types[qid]
        actual = q["type"]
        status = "✅" if actual == expected else "❌"
        logger.info(f"  {status} {qid}: {actual} (期望: {expected})")
        if actual != expected:
            all_passed = False

    if all_passed:
        logger.success("✅ LLMQuestionGenerator 类型修复测试通过")
    else:
        logger.error("❌ LLMQuestionGenerator 类型修复测试失败")

    return all_passed


def test_gap_generator_type_fix():
    """测试 LLMGapQuestionGenerator 的类型修复功能"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 LLMGapQuestionGenerator 类型修复")
    logger.info("=" * 60)

    # 模拟第三步LLM返回的错误类型问题
    raw_questions = [
        {
            "id": "budget",
            "question": "预算范围是？",
            "type": "multi_choice",  # 错误类型
            "options": ["10万以下", "10-30万"],
            "is_required": True,
        },
        {
            "id": "timeline",
            "question": "交付时间？",
            "type": "radio",  # 错误类型
            "options": ["1个月", "3个月"],
            "is_required": True,
        },
        {"id": "special", "question": "特殊需求？", "type": "text", "placeholder": "请描述", "is_required": False},  # 错误类型
    ]

    # 创建生成器实例并调用验证方法
    generator = LLMGapQuestionGenerator()
    fixed_questions = generator._validate_and_fix_questions(raw_questions)

    # 验证修复结果
    expected_types = {"budget": "multiple_choice", "timeline": "single_choice", "special": "open_ended"}

    logger.info(f"\n📊 修复结果统计:")
    all_passed = True
    for q in fixed_questions:
        qid = q["id"]
        expected = expected_types[qid]
        actual = q["type"]
        status = "✅" if actual == expected else "❌"
        logger.info(f"  {status} {qid}: {actual} (期望: {expected})")
        if actual != expected:
            all_passed = False

    if all_passed:
        logger.success("✅ LLMGapQuestionGenerator 类型修复测试通过")
    else:
        logger.error("❌ LLMGapQuestionGenerator 类型修复测试失败")

    return all_passed


def test_type_inference():
    """测试从问题文本推断类型"""
    logger.info("\n" + "=" * 60)
    logger.info("测试类型推断功能")
    logger.info("=" * 60)

    # 没有明确类型，但有标注或选项
    raw_questions = [
        {"id": "q1", "question": "您的预算范围是？(单选)", "type": "unknown_type", "options": ["A", "B"]},  # 未知类型，但文本有单选标注
        {"id": "q2", "question": "需要哪些功能？(多选)", "type": "xyz", "options": ["功能1", "功能2"]},  # 未知类型，但文本有多选标注
        {"id": "q3", "question": "请描述您的需求(开放题)", "type": "abc"},  # 未知类型，但文本有开放题标注
        {"id": "q4", "question": "选择一个选项", "type": "invalid", "options": ["选项1", "选项2"]},  # 未知类型，但有选项列表
    ]

    fixed_questions = LLMQuestionGenerator._validate_and_fix_questions(raw_questions)

    expected_types = {
        "q1": "single_choice",  # 从"(单选)"推断
        "q2": "multiple_choice",  # 从"(多选)"推断
        "q3": "open_ended",  # 从"(开放题)"推断
        "q4": "single_choice",  # 从有options推断
    }

    logger.info(f"\n📊 推断结果统计:")
    all_passed = True
    for q in fixed_questions:
        qid = q["id"]
        expected = expected_types[qid]
        actual = q["type"]
        status = "✅" if actual == expected else "❌"
        logger.info(f"  {status} {qid}: {actual} (期望: {expected})")
        if actual != expected:
            all_passed = False

    if all_passed:
        logger.success("✅ 类型推断测试通过")
    else:
        logger.error("❌ 类型推断测试失败")

    return all_passed


def run_all_tests():
    """运行所有测试"""
    logger.info("\n" + "🧪" * 30)
    logger.info("开始运行问卷类型修复测试套件")
    logger.info("🧪" * 30 + "\n")

    results = {
        "LLMQuestionGenerator类型修复": test_llm_generator_type_fix(),
        "LLMGapQuestionGenerator类型修复": test_gap_generator_type_fix(),
        "类型推断功能": test_type_inference(),
    }

    # 汇总结果
    logger.info("\n" + "=" * 60)
    logger.info("测试结果汇总")
    logger.info("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} - {test_name}")

    all_passed = all(results.values())

    if all_passed:
        logger.success("\n🎉 所有测试通过！")
    else:
        logger.error("\n⚠️ 部分测试失败，请检查日志")

    return all_passed


if __name__ == "__main__":
    import pytest

    # 检查是否通过pytest运行
    if "pytest" in sys.modules:
        # 通过pytest运行，定义测试函数
        def test_all():
            assert run_all_tests(), "部分测试失败"

    else:
        # 直接运行
        success = run_all_tests()
        sys.exit(0 if success else 1)
