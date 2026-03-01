"""
测试对话智能体功能

测试流程：
1. 创建模拟的分析上下文
2. 测试意图分类
3. 测试上下文检索
4. 测试问答生成
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_intent_classifier():
    """测试意图分类器"""
    print("=" * 60)
    print("测试 1: 意图分类器")
    print("=" * 60)

    from intelligent_project_analyzer.services.intent_classifier import IntentClassifier

    classifier = IntentClassifier()

    test_questions = [
        ("这个方案是什么意思？", "clarification"),
        ("能详细说明一下设计细节吗？", "deep_dive"),
        ("可以重新生成报告吗？", "regenerate"),
        ("我想开始一个新项目", "new_analysis"),
        ("成本大概多少？", "general"),
    ]

    for question, expected in test_questions:
        intent = classifier.classify(question)
        status = "✅" if intent == expected else "❌"
        print(f"{status} '{question}' → {intent} (期望: {expected})")

    print()


def test_context_retriever():
    """测试上下文检索器"""
    print("=" * 60)
    print("测试 2: 上下文检索器")
    print("=" * 60)

    from intelligent_project_analyzer.services.context_retriever import ContextRetriever
    from intelligent_project_analyzer.agents.conversation_agent import ConversationContext

    # 模拟报告数据
    mock_report = {
        "executive_summary": {
            "key_recommendations": ["建议1: 采用模块化设计", "建议2: 注重用户体验"],
            "key_findings": ["发现1: 市场需求强烈", "发现2: 竞争激烈"],
        },
        "sections": {
            "chapter_1": {"title": "需求分析", "content": "项目需求包括功能需求和非功能需求，核心用户群体为年轻白领..."},
            "chapter_2": {"title": "设计方案", "content": "推荐采用微服务架构，前后端分离，使用React和FastAPI技术栈..."},
            "chapter_3": {"title": "实施计划", "content": "项目周期预计6个月，分为3个阶段：需求调研、开发实施、测试上线..."},
        },
    }

    context = ConversationContext(final_report=mock_report, agent_results={}, requirements={}, user_input="设计一个电商平台")

    retriever = ContextRetriever()

    # 测试不同的查询
    test_queries = ["设计方案是什么？", "需要多长时间？", "核心建议有哪些？"]

    for query in test_queries:
        print(f"\n查询: '{query}'")
        result = retriever.retrieve(query, context, "general", top_k=2)

        print(f"  关键词: {result['metadata']['keywords']}")
        print(f"  检索到 {len(result['sections'])} 个相关章节:")
        for section in result["sections"]:
            print(f"    - {section['title']} (相关度: {section['relevance_score']:.2f})")

    print()


def test_conversation_agent():
    """测试对话智能体"""
    print("=" * 60)
    print("测试 3: 对话智能体")
    print("=" * 60)

    from intelligent_project_analyzer.agents.conversation_agent import ConversationAgent, ConversationContext

    # 模拟分析上下文
    mock_report = {
        "executive_summary": {
            "key_recommendations": ["采用模块化设计", "注重用户体验", "快速迭代"],
            "key_findings": ["市场需求强烈", "技术可行", "竞争激烈"],
        },
        "sections": {
            "chapter_1": {"title": "需求分析", "content": "项目目标是构建一个面向年轻白领的线上购物平台，核心功能包括商品浏览、购物车、支付结算等..."},
            "chapter_2": {
                "title": "设计方案",
                "content": "推荐采用微服务架构，前端使用React，后端使用FastAPI和PostgreSQL数据库。系统分为用户服务、商品服务、订单服务等模块...",
            },
        },
    }

    context = ConversationContext(final_report=mock_report, agent_results={}, requirements={}, user_input="设计一个电商平台")

    # 创建对话智能体
    try:
        agent = ConversationAgent()

        # 测试问答
        question = "核心设计建议是什么？"
        print(f"问题: {question}\n")

        result = agent.answer_question(question=question, context=context)

        print(f"意图: {result['intent']}")
        print(f"引用: {result['references']}")
        print(f"建议: {result['suggestions']}")
        print(f"\n回答:\n{result['answer']}")

    except Exception as e:
        print(f"❌ 对话智能体测试失败: {e}")
        import traceback

        traceback.print_exc()

    print()


def main():
    """主测试函数"""
    print("\n")
    print("🚀 对话智能体功能测试")
    print("=" * 60)
    print()

    try:
        # 测试1: 意图分类
        test_intent_classifier()

        # 测试2: 上下文检索
        test_context_retriever()

        # 测试3: 对话智能体
        test_conversation_agent()

        print("=" * 60)
        print("✅ 所有测试完成")
        print("=" * 60)

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
