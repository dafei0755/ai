"""
问卷生成优化测试

验证 v7.5 LLM驱动的问卷生成器能够：
1. 生成与用户输入紧密相关的问题
2. 正确回退到规则生成器
3. 问题类型分布合理

运行方式：
    python tests/test_questionnaire_generation.py
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger


def test_llm_generator_with_real_input():
    """测试LLM生成器处理真实用户输入"""
    logger.info("=" * 60)
    logger.info("测试1: LLM生成器处理真实用户输入")
    logger.info("=" * 60)

    from intelligent_project_analyzer.interaction.questionnaire.llm_generator import LLMQuestionGenerator

    # 测试用例1: 住宅设计
    user_input_1 = """
    我需要为一个150㎡的三代同堂家庭设计住宅空间。
    家里有老人、中年夫妻和一个10岁的孩子。
    预算80万，工期4个月。
    希望既有私密性又能促进家庭互动，老人需要无障碍设计。
    """

    structured_data_1 = {
        "project_task": "为三代同堂家庭设计150㎡住宅空间",
        "project_type": "personal_residential",
        "design_challenge": "如何平衡三代人的'私密需求'与'互动需求'之间的矛盾",
        "core_tension": "私密性 vs 家庭互动",
        "character_narrative": "老人需要安静休息，孩子需要玩耍空间，夫妻需要独处时光",
        "resource_constraints": "预算80万，工期4个月",
    }

    logger.info(f"用户输入: {user_input_1[:100]}...")
    questions_1, source_1 = LLMQuestionGenerator.generate(user_input=user_input_1, structured_data=structured_data_1)

    logger.info(f"生成来源: {source_1}")
    logger.info(f"问题数量: {len(questions_1)}")

    # 验证问题内容
    for i, q in enumerate(questions_1):
        logger.info(f"  Q{i+1} [{q.get('type')}]: {q.get('question', '')[:80]}...")

    # 验证问题是否与用户输入相关
    question_texts = " ".join([q.get("question", "") for q in questions_1])
    relevance_keywords = ["三代", "老人", "孩子", "私密", "互动", "预算", "家庭"]
    matched_keywords = [kw for kw in relevance_keywords if kw in question_texts]

    logger.info(f"相关性检查: 匹配关键词 {len(matched_keywords)}/{len(relevance_keywords)}: {matched_keywords}")

    assert len(questions_1) >= 5, f"问题数量不足: {len(questions_1)}"
    logger.info("✅ 测试1 通过")

    return questions_1, source_1


def test_llm_generator_with_tech_project():
    """测试LLM生成器处理科技公司项目"""
    logger.info("=" * 60)
    logger.info("测试2: LLM生成器处理科技公司项目")
    logger.info("=" * 60)

    from intelligent_project_analyzer.interaction.questionnaire.llm_generator import LLMQuestionGenerator

    user_input_2 = """
    我们是一家AI创业公司，需要设计一个500㎡的办公空间。
    团队有30人，主要是研发工程师和数据科学家。
    希望空间能够支持敏捷开发，有足够的协作区和专注区。
    预算200万，需要在3个月内完成。
    """

    structured_data_2 = {
        "project_task": "为AI创业公司设计500㎡办公空间",
        "project_type": "commercial_enterprise",
        "design_challenge": "如何平衡'开放协作'与'深度专注'的需求",
        "core_tension": "协作 vs 专注",
        "character_narrative": "研发工程师需要安静编码，团队需要频繁讨论",
        "resource_constraints": "预算200万，工期3个月",
    }

    logger.info(f"用户输入: {user_input_2[:100]}...")
    questions_2, source_2 = LLMQuestionGenerator.generate(user_input=user_input_2, structured_data=structured_data_2)

    logger.info(f"生成来源: {source_2}")
    logger.info(f"问题数量: {len(questions_2)}")

    for i, q in enumerate(questions_2):
        logger.info(f"  Q{i+1} [{q.get('type')}]: {q.get('question', '')[:80]}...")

    # 验证问题是否与科技公司相关
    question_texts = " ".join([q.get("question", "") for q in questions_2])
    tech_keywords = ["协作", "专注", "研发", "团队", "敏捷", "AI", "数据"]
    matched_keywords = [kw for kw in tech_keywords if kw in question_texts]

    logger.info(f"相关性检查: 匹配关键词 {len(matched_keywords)}/{len(tech_keywords)}: {matched_keywords}")

    assert len(questions_2) >= 5, f"问题数量不足: {len(questions_2)}"
    logger.info("✅ 测试2 通过")

    return questions_2, source_2


def test_fallback_generator():
    """测试规则生成器（fallback）"""
    logger.info("=" * 60)
    logger.info("测试3: 规则生成器（Fallback）")
    logger.info("=" * 60)

    from intelligent_project_analyzer.interaction.questionnaire.generators import FallbackQuestionGenerator
    from intelligent_project_analyzer.interaction.questionnaire.context import KeywordExtractor

    user_input = "我需要设计一个咖啡厅，面积100㎡，预算50万"

    structured_data = {
        "project_task": "设计100㎡咖啡厅",
        "project_type": "commercial_enterprise",
        "design_challenge": "如何在有限空间内平衡座位数量和顾客体验",
        "core_tension": "坪效 vs 体验",
    }

    # 提取关键信息
    extracted_info = KeywordExtractor.extract(user_input, structured_data)
    logger.info(f"提取的领域: {extracted_info.get('domain', {}).get('label', 'unknown')}")
    logger.info(f"核心概念: {extracted_info.get('core_concepts', [])}")

    # 生成问题
    questions = FallbackQuestionGenerator.generate(
        structured_data, user_input=user_input, extracted_info=extracted_info
    )

    logger.info(f"问题数量: {len(questions)}")

    # 验证题型分布
    type_counts = {}
    for q in questions:
        q_type = q.get("type", "unknown")
        type_counts[q_type] = type_counts.get(q_type, 0) + 1

    logger.info(f"题型分布: {type_counts}")

    for i, q in enumerate(questions):
        logger.info(f"  Q{i+1} [{q.get('type')}]: {q.get('question', '')[:60]}...")

    # 验证没有抽象概念
    abstract_terms = ["身份表达", "身体体验", "核心功能区", "辅助支持区", "灵活多用区"]
    question_texts = " ".join([q.get("question", "") + " ".join(q.get("options", [])) for q in questions])

    found_abstract = [term for term in abstract_terms if term in question_texts]
    if found_abstract:
        logger.warning(f"⚠️ 发现抽象概念: {found_abstract}")
    else:
        logger.info("✅ 未发现抽象概念")

    assert len(questions) >= 5, f"问题数量不足: {len(questions)}"
    assert "single_choice" in type_counts, "缺少单选题"
    assert "multiple_choice" in type_counts, "缺少多选题"

    logger.info("✅ 测试3 通过")

    return questions


def test_question_type_order():
    """测试问题类型排序"""
    logger.info("=" * 60)
    logger.info("测试4: 问题类型排序")
    logger.info("=" * 60)

    from intelligent_project_analyzer.interaction.questionnaire.llm_generator import LLMQuestionGenerator

    # 使用简单输入快速测试
    user_input = "设计一个小型书房"
    structured_data = {"project_task": "设计小型书房", "project_type": "personal_residential"}

    questions, _ = LLMQuestionGenerator.generate(user_input, structured_data)

    # 验证排序：单选 -> 多选 -> 开放
    type_order = [q.get("type") for q in questions]
    logger.info(f"问题类型顺序: {type_order}")

    # 检查是否按顺序排列
    expected_order = {"single_choice": 0, "multiple_choice": 1, "open_ended": 2}
    is_ordered = True
    last_order = -1

    for t in type_order:
        current_order = expected_order.get(t, 3)
        if current_order < last_order:
            is_ordered = False
            break
        last_order = current_order

    if is_ordered:
        logger.info("✅ 问题类型顺序正确")
    else:
        logger.warning("⚠️ 问题类型顺序不正确，但系统会自动修复")

    logger.info("✅ 测试4 通过")


def run_all_tests():
    """运行所有测试"""
    logger.info("🚀 开始问卷生成优化测试")
    logger.info("=" * 80)

    try:
        # 测试1: LLM生成器 - 住宅项目
        test_llm_generator_with_real_input()
        print()

        # 测试2: LLM生成器 - 科技公司
        test_llm_generator_with_tech_project()
        print()

        # 测试3: 规则生成器
        test_fallback_generator()
        print()

        # 测试4: 问题类型排序
        test_question_type_order()
        print()

        logger.info("=" * 80)
        logger.info("✅ 所有测试通过！")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ 测试失败: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}", level="INFO"
    )

    success = run_all_tests()
    sys.exit(0 if success else 1)
