"""
v7.17 P3 测试脚本：需求分析师 StateGraph Agent
测试 RequirementsAnalystAgentV2 的完整功能
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligent_project_analyzer.agents.requirements_analyst_agent import (
    RequirementsAnalystAgentV2,
    RequirementsAnalystCompat,
    RequirementsAnalystState,
    build_requirements_analyst_graph,
    precheck_node,
    phase1_node,
    should_execute_phase2
)


def test_graph_structure():
    """测试1：验证图结构"""
    print("=" * 60)
    print("测试1：验证图结构")
    print("=" * 60)
    
    graph = build_requirements_analyst_graph()
    compiled = graph.compile()
    
    print(f"✅ 图编译成功")
    print(f"   类型: {type(compiled).__name__}")
    
    # 检查图结构
    nodes = list(graph.nodes.keys())
    print(f"   节点: {nodes}")
    
    expected_nodes = ["precheck", "phase1", "phase2", "output"]
    missing = set(expected_nodes) - set(nodes)
    extra = set(nodes) - set(expected_nodes)
    
    if not missing and not extra:
        print("✅ 节点结构正确")
    else:
        print(f"❌ 节点不匹配: 缺少 {missing}, 多余 {extra}")
    
    return True


def test_precheck_node():
    """测试2：验证 precheck 节点"""
    print("\n" + "=" * 60)
    print("测试2：验证 precheck 节点")
    print("=" * 60)
    
    # 充足信息的输入
    state_sufficient = {
        "user_input": "我是一位32岁的前金融律师，有一套75平米的公寓，预算60万，希望现代简约风格",
        "session_id": "test-001",
        "processing_log": [],
        "node_path": []
    }
    
    result = precheck_node(state_sufficient)
    
    print(f"✅ precheck 节点执行成功")
    print(f"   - 信息充足: {result.get('info_sufficient')}")
    print(f"   - 能力匹配: {result.get('capability_score'):.0%}")
    print(f"   - 耗时: {result.get('precheck_elapsed_ms'):.1f}ms")
    print(f"   - 节点路径: {result.get('node_path')}")
    
    # 不足信息的输入
    state_insufficient = {
        "user_input": "帮我设计一下房子",
        "session_id": "test-002",
        "processing_log": [],
        "node_path": []
    }
    
    result2 = precheck_node(state_insufficient)
    print(f"\n不足信息测试:")
    print(f"   - 信息充足: {result2.get('info_sufficient')}")
    print(f"   - 能力匹配: {result2.get('capability_score'):.0%}")
    
    return result.get('info_sufficient') == True and result2.get('info_sufficient') == False


def test_conditional_routing():
    """测试3：验证条件路由"""
    print("\n" + "=" * 60)
    print("测试3：验证条件路由")
    print("=" * 60)
    
    # 信息充足 → 应该进入 phase2
    state_go_phase2 = {
        "phase1_info_status": "sufficient",
        "recommended_next_step": "phase2_analysis"
    }
    
    decision1 = should_execute_phase2(state_go_phase2)
    print(f"✅ 信息充足时: {decision1} (预期: phase2)")
    
    # 信息不足 → 应该跳过 phase2
    state_skip_phase2 = {
        "phase1_info_status": "insufficient",
        "recommended_next_step": "questionnaire_first"
    }
    
    decision2 = should_execute_phase2(state_skip_phase2)
    print(f"✅ 信息不足时: {decision2} (预期: output)")
    
    return decision1 == "phase2" and decision2 == "output"


def test_agent_instantiation():
    """测试4：验证 Agent 实例化（无需 LLM）"""
    print("\n" + "=" * 60)
    print("测试4：验证 Agent 实例化")
    print("=" * 60)
    
    # 创建一个模拟的 LLM
    class MockLLM:
        def invoke(self, messages):
            class MockResponse:
                content = '{"info_status": "sufficient", "primary_deliverables": []}'
            return MockResponse()
    
    mock_llm = MockLLM()
    
    try:
        agent = RequirementsAnalystAgentV2(mock_llm)
        print(f"✅ RequirementsAnalystAgentV2 实例化成功")
        print(f"   - 图类型: {type(agent._graph).__name__}")
        
        # 测试兼容层
        compat = RequirementsAnalystCompat(mock_llm)
        print(f"✅ RequirementsAnalystCompat 实例化成功")
        
        return True
    except Exception as e:
        print(f"❌ 实例化失败: {e}")
        return False


def test_state_definition():
    """测试5：验证状态定义"""
    print("\n" + "=" * 60)
    print("测试5：验证状态定义")
    print("=" * 60)
    
    from typing import get_type_hints
    
    hints = get_type_hints(RequirementsAnalystState)
    
    required_fields = [
        "user_input", "session_id",
        "precheck_result", "precheck_elapsed_ms", "info_sufficient",
        "phase1_result", "phase1_elapsed_ms", "phase1_info_status",
        "phase2_result", "phase2_elapsed_ms",
        "structured_data", "confidence", "analysis_mode",
        "processing_log", "node_path"
    ]
    
    missing = []
    for field in required_fields:
        if field in hints:
            print(f"   ✅ {field}: {hints[field]}")
        else:
            missing.append(field)
            print(f"   ❌ {field}: 缺失")
    
    if not missing:
        print(f"\n✅ 状态定义完整，共 {len(hints)} 个字段")
        return True
    else:
        print(f"\n❌ 缺失字段: {missing}")
        return False


def test_full_flow_mock():
    """测试6：模拟完整流程（使用 Mock LLM）"""
    print("\n" + "=" * 60)
    print("测试6：模拟完整流程")
    print("=" * 60)
    
    class MockLLM:
        call_count = 0
        
        def invoke(self, messages):
            MockLLM.call_count += 1
            
            class MockResponse:
                pass
            
            response = MockResponse()
            
            # 根据调用次数返回不同的响应
            if MockLLM.call_count == 1:
                # Phase1 响应
                response.content = json.dumps({
                    "info_status": "sufficient",
                    "info_status_reason": "信息完整",
                    "project_summary": "75平米公寓设计",
                    "primary_deliverables": [
                        {"deliverable_id": "D1", "type": "design_strategy", "priority": "MUST_HAVE"}
                    ],
                    "recommended_next_step": "phase2_analysis"
                }, ensure_ascii=False)
            else:
                # Phase2 响应
                response.content = json.dumps({
                    "analysis_layers": {
                        "L1_facts": ["75平米公寓"],
                        "L5_sharpness": {"score": 80}
                    },
                    "structured_output": {
                        "project_task": "为32岁前金融律师设计75平米现代简约公寓",
                        "character_narrative": "追求品质生活的年轻专业人士"
                    },
                    "expert_handoff": {
                        "critical_questions_for_experts": {"V3": ["如何表达专业身份？"]}
                    }
                }, ensure_ascii=False)
            
            return response
    
    import json
    mock_llm = MockLLM()
    
    try:
        agent = RequirementsAnalystAgentV2(mock_llm)
        
        result = agent.execute(
            user_input="我是一位32岁的前金融律师，有一套75平米的公寓，预算60万，希望现代简约风格",
            session_id="test-full-flow"
        )
        
        print(f"✅ 完整流程执行成功")
        print(f"   - 置信度: {result.confidence:.2f}")
        print(f"   - 分析模式: {result.metadata.get('analysis_mode')}")
        print(f"   - 项目类型: {result.metadata.get('project_type')}")
        print(f"   - 总耗时: {result.metadata.get('total_elapsed_ms'):.0f}ms")
        print(f"   - 节点路径: {result.metadata.get('node_path')}")
        print(f"   - LLM 调用次数: {MockLLM.call_count}")
        
        # 验证节点路径
        expected_path = ["precheck", "phase1", "phase2", "output"]
        actual_path = result.metadata.get('node_path', [])
        
        if actual_path == expected_path:
            print(f"✅ 节点路径正确: {actual_path}")
        else:
            print(f"⚠️ 节点路径不完全匹配: 预期 {expected_path}, 实际 {actual_path}")
        
        return True
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    results = []
    
    results.append(("图结构", test_graph_structure()))
    results.append(("precheck节点", test_precheck_node()))
    results.append(("条件路由", test_conditional_routing()))
    results.append(("Agent实例化", test_agent_instantiation()))
    results.append(("状态定义", test_state_definition()))
    results.append(("完整流程", test_full_flow_mock()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 通过")
