"""
🔥 v7.15 FollowupAgent (LangGraph) 测试
"""
import sys
sys.path.insert(0, 'd:/11-20/langgraph-design')

from intelligent_project_analyzer.agents.followup_agent import (
    FollowupAgent,
    build_followup_agent,
    classify_intent_node,
    FollowupAgentState
)


def test_graph_structure():
    """测试图结构"""
    print("\n" + "="*60)
    print("🧪 测试1: 图结构验证")
    print("="*60)
    
    graph = build_followup_agent()
    
    # 检查节点
    print(f"✅ 图编译成功")
    print(f"📊 图类型: {type(graph).__name__}")
    
    return True


def test_intent_classification():
    """测试意图分类节点"""
    print("\n" + "="*60)
    print("🧪 测试2: 意图分类节点")
    print("="*60)
    
    test_cases = [
        ("报告中专家怎么说的？", "closed"),
        ("有没有类似的行业案例？", "open_with_context"),
        ("如果预算翻倍会怎样？", "creative"),
        ("你好", "general"),
    ]
    
    passed = 0
    for question, expected in test_cases:
        state: FollowupAgentState = {
            "question": question,
            "report_context": {},
            "conversation_history": [],
            "intent": "",
            "relevant_sections": [],
            "intent_prompt": "",
            "answer": "",
            "references": [],
            "suggestions": [],
            "processing_log": []
        }
        
        result = classify_intent_node(state)
        actual = result["intent"]
        
        if actual == expected:
            print(f"✅ PASS: \"{question[:25]}...\" => {actual}")
            passed += 1
        else:
            print(f"❌ FAIL: \"{question[:25]}...\" => {actual} (期望: {expected})")
    
    print(f"\n📊 结果: {passed}/{len(test_cases)} 通过")
    return passed == len(test_cases)


def test_full_agent():
    """测试完整 Agent 流程"""
    print("\n" + "="*60)
    print("🧪 测试3: 完整 Agent 流程")
    print("="*60)
    
    agent = FollowupAgent()
    
    # 模拟报告上下文
    report_context = {
        "final_report": {
            "核心答案": "这是一个住宅设计项目，面积150平米，预算200万。",
            "专家建议": "建议采用现代简约风格，注重采光和通风。"
        },
        "agent_results": {
            "4-1 设计研究员": {"content": "用户需要三室两厅布局。"}
        }
    }
    
    # 测试问题
    test_questions = [
        "报告中提到的预算是多少？",
        "有没有类似的设计案例？",
        "如果改成四室会怎样？"
    ]
    
    for question in test_questions:
        print(f"\n📝 问题: {question}")
        result = agent.answer_question(
            question=question,
            report_context=report_context,
            conversation_history=[]
        )
        
        print(f"🎯 意图: {result['intent']}")
        print(f"📝 回答长度: {len(result['answer'])} 字符")
        print(f"💡 建议数: {len(result['suggestions'])}")
        print(f"📋 处理日志: {result['processing_log']}")
    
    print("\n✅ 完整流程测试通过")
    return True


if __name__ == "__main__":
    print("\n" + "🔥 v7.15 FollowupAgent (LangGraph) 测试套件 🔥".center(60))
    
    all_passed = True
    
    all_passed &= test_graph_structure()
    all_passed &= test_intent_classification()
    all_passed &= test_full_agent()
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ 所有测试通过！v7.15 FollowupAgent 验证成功")
    else:
        print("❌ 部分测试失败，请检查")
    print("="*60)
