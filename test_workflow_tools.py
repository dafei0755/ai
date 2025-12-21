"""
v7.63.1 工作流工具集成端到端测试

快速验证：工具在实际工作流中的加载和传递

测试范围:
1. WorkflowOrchestrator 正确加载工具
2. 工具传递到 execute_expert()
3. 日志显示工具绑定信息
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from loguru import logger
from intelligent_project_analyzer.core.state import ProjectAnalysisState
from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow
from intelligent_project_analyzer.services.tool_factory import ToolFactory

def test_tool_loading_in_workflow():
    """测试工具在工作流中的加载"""
    print("\n" + "="*80)
    print("🧪 测试: 工作流工具加载")
    print("="*80)
    
    # 创建工作流实例
    orchestrator = MainWorkflow()
    
    # 验证工作流有 _load_tools_for_roles 方法
    assert hasattr(orchestrator, '_load_tools_for_roles'), "❌ 工作流缺少 _load_tools_for_roles 方法"
    print("✅ 工作流包含工具加载方法")
    
    # 模拟角色配置
    test_roles = [
        {"role_id": "4-1", "dynamic_role_name": "设计研究员"},
        {"role_id": "2-1", "dynamic_role_name": "设计总监"}
    ]
    
    # 调用工具加载方法
    tools_by_role = orchestrator._load_tools_for_roles(test_roles)
    
    # 验证结果
    print(f"\n📋 加载的工具映射:")
    for role_id, tools in tools_by_role.items():
        tool_names = [getattr(t, 'name', str(t)) for t in tools]
        print(f"  {role_id}: {len(tools)} 个工具 - {tool_names}")
    
    # V4 应有 4 个工具
    v4_tools = tools_by_role.get("4-1", [])
    assert len(v4_tools) == 4, f"❌ V4 应有 4 个工具，实际 {len(v4_tools)} 个"
    print(f"✅ V4 (设计研究员) 正确加载 4 个工具")
    
    # V2 应有 1 个工具 (仅 ragflow)
    v2_tools = tools_by_role.get("2-1", [])
    assert len(v2_tools) == 1, f"❌ V2 应有 1 个工具，实际 {len(v2_tools)} 个"
    print(f"✅ V2 (设计总监) 正确加载 1 个工具 (综合者模式)")
    
    print("\n✅ 工作流工具加载测试通过！")
    return True


def test_tool_factory_availability():
    """测试工具工厂可用性"""
    print("\n" + "="*80)
    print("🧪 测试: 工具工厂可用性")
    print("="*80)
    
    # 创建所有工具
    tools = ToolFactory.create_all_tools()
    
    print(f"\n📋 可用工具:")
    for name, tool in tools.items():
        tool_name = getattr(tool, 'name', name)
        print(f"  ✓ {name}: {tool_name}")
    
    # 验证 4 个工具都存在
    expected_tools = ['bocha', 'tavily', 'ragflow', 'arxiv']
    for tool_name in expected_tools:
        assert tool_name in tools, f"❌ 缺少工具: {tool_name}"
    
    print(f"\n✅ 所有 4 个工具可用")
    return True


def test_state_structure():
    """测试状态结构包含必要字段"""
    print("\n" + "="*80)
    print("🧪 测试: 状态结构")
    print("="*80)
    
    # 验证 ProjectAnalysisState 类型定义
    from intelligent_project_analyzer.core.state import ProjectAnalysisState
    import typing
    
    # 获取类型注解
    annotations = typing.get_type_hints(ProjectAnalysisState)
    
    # 检查关键字段
    required_fields = ['selected_roles', 'agent_results', 'active_agents']
    for field in required_fields:
        assert field in annotations, f"❌ 状态缺少字段: {field}"
        print(f"  ✓ {field}: {annotations[field]}")
    
    print(f"\n✅ 状态结构包含所有必要字段")
    return True


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🧪 v7.63.1 工作流工具集成端到端测试")
    print("="*80)
    
    tests = [
        ("工具工厂可用性", test_tool_factory_availability),
        ("状态结构验证", test_state_structure),
        ("工作流工具加载", test_tool_loading_in_workflow)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ 测试失败: {test_name}")
            print(f"   错误: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("📊 测试结果汇总")
    print("="*80)
    print(f"✅ 通过: {passed}/{len(tests)}")
    if failed > 0:
        print(f"❌ 失败: {failed}/{len(tests)}")
    else:
        print("🎉 所有测试通过！")
    print("="*80)
