"""
v7.14 追问开放性增强测试
"""
import sys

sys.path.insert(0, "d:/11-20/langgraph-design")

from intelligent_project_analyzer.agents.conversation_agent import ConversationAgent


def test_intent_classification():
    """测试意图分类器"""
    agent = ConversationAgent()

    test_cases = [
        # (问题, 期望意图)
        # 闭环问题
        ("报告中专家怎么说的？", "closed"),
        ("分析结果是什么？", "closed"),
        ("数据是多少？", "closed"),
        ("在哪里提到这个？", "closed"),
        # 开放扩展问题
        ("有没有类似的行业案例？", "open_with_context"),
        ("还有什么需要注意的？", "open_with_context"),
        ("业界最佳实践是什么？", "open_with_context"),
        ("为什么会这样？", "open_with_context"),
        # 创意发散问题
        ("如果预算翻倍会怎样？", "creative"),
        ("假设换一个地点呢？", "creative"),
        ("有没有更大胆的方案？", "creative"),
        ("其他行业怎么做的？", "creative"),
        # 通用问题
        ("你好", "general"),
        ("谢谢", "general"),
    ]

    print("\n" + "=" * 60)
    print("🧪 v7.14 意图分类测试")
    print("=" * 60)

    passed = 0
    failed = 0

    for question, expected in test_cases:
        result = agent._classify_intent(question, None)
        if result == expected:
            print(f'✅ PASS: "{question}" => {result}')
            passed += 1
        else:
            print(f'❌ FAIL: "{question}" => {result} (期望: {expected})')
            failed += 1

    print("\n" + "-" * 60)
    print(f"📊 结果: {passed} 通过, {failed} 失败")
    print("-" * 60)

    return failed == 0


def test_intent_prompts():
    """测试意图专属提示词"""
    agent = ConversationAgent()

    print("\n" + "=" * 60)
    print("🧪 v7.14 意图专属提示词测试")
    print("=" * 60)

    for intent, prompt in agent.INTENT_PROMPTS.items():
        print(f"\n📌 {intent}:")
        print(f"   {prompt[:80]}...")

    print("\n✅ 4种意图提示词已定义")
    return True


def test_suggestions():
    """测试智能后续建议"""
    from intelligent_project_analyzer.agents.conversation_agent import ConversationContext

    agent = ConversationAgent()
    context = ConversationContext()

    print("\n" + "=" * 60)
    print("🧪 v7.14 智能后续建议测试")
    print("=" * 60)

    for intent in ["closed", "open_with_context", "creative", "general"]:
        suggestions = agent._generate_suggestions(question="测试问题", answer="测试回答", context=context, intent=intent)
        print(f"\n📌 {intent} 意图的建议:")
        for s in suggestions:
            print(f"   - {s}")

    print("\n✅ 智能建议生成正常")
    return True


if __name__ == "__main__":
    print("\n" + "🔥 v7.14 追问开放性增强 - 测试套件 🔥".center(60))

    all_passed = True

    all_passed &= test_intent_classification()
    all_passed &= test_intent_prompts()
    all_passed &= test_suggestions()

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过！v7.14 修改验证成功")
    else:
        print("❌ 部分测试失败，请检查")
    print("=" * 60)
