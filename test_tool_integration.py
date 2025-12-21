"""
测试工具系统集成到Agent工作流 (v7.63.1)

验证：
1. 工具工厂能正确创建所有工具
2. 专家配置包含正确的工具列表
3. 角色特定工具加载逻辑正确
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from intelligent_project_analyzer.services.tool_factory import ToolFactory
from intelligent_project_analyzer.interaction.services.strategy_generator import StrategyGenerator


def test_tool_factory():
    """测试1: 工具工厂能创建所有工具"""
    print("\n" + "="*60)
    print("测试1: 工具工厂创建所有工具")
    print("="*60)
    
    try:
        all_tools = ToolFactory.create_all_tools()
        
        expected_tools = ["bocha", "tavily", "ragflow", "arxiv"]
        
        print(f"✅ 工具工厂成功创建工具")
        print(f"📋 可用工具列表: {list(all_tools.keys())}")
        
        for tool_name in expected_tools:
            if tool_name in all_tools:
                tool = all_tools[tool_name]
                tool_display_name = getattr(tool, 'name', 'N/A')
                print(f"  ✓ {tool_name}: {tool_display_name}")
            else:
                print(f"  ✗ {tool_name}: 未找到")
                return False
        
        print("\n✅ 测试1通过: 所有预期工具已创建")
        return True
        
    except Exception as e:
        print(f"❌ 测试1失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_expert_tool_configs():
    """测试2: 专家工具配置正确性"""
    print("\n" + "="*60)
    print("测试2: 专家工具配置正确性")
    print("="*60)
    
    try:
        configs = StrategyGenerator.EXPERT_CONFIGS
        
        # 预期配置
        expected_configs = {
            "V4": {"tavily", "arxiv", "ragflow", "bocha"},  # 主要研究者，完整工具集
            "V3": {"tavily", "ragflow", "bocha"},           # 补充研究
            "V5": {"tavily", "ragflow", "bocha"},           # 补充研究
            "V2": {"ragflow"},                              # 综合决策者，仅内部知识库
            "V6": {"tavily", "arxiv", "ragflow", "bocha"},  # 技术规范查询
        }
        
        all_pass = True
        
        for expert_type, expected_tools in expected_configs.items():
            if expert_type not in configs:
                print(f"❌ {expert_type}: 配置缺失")
                all_pass = False
                continue
            
            config = configs[expert_type]
            actual_tools = set(config.tools)
            
            if actual_tools == expected_tools:
                print(f"✅ {expert_type} ({config.name})")
                print(f"   工具: {sorted(actual_tools)}")
            else:
                print(f"❌ {expert_type} ({config.name})")
                print(f"   预期: {sorted(expected_tools)}")
                print(f"   实际: {sorted(actual_tools)}")
                missing = expected_tools - actual_tools
                extra = actual_tools - expected_tools
                if missing:
                    print(f"   缺少: {sorted(missing)}")
                if extra:
                    print(f"   多余: {sorted(extra)}")
                all_pass = False
        
        if all_pass:
            print("\n✅ 测试2通过: 所有专家工具配置正确")
        else:
            print("\n❌ 测试2失败: 部分专家工具配置不正确")
        
        return all_pass
        
    except Exception as e:
        print(f"❌ 测试2失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_role_specific_loading():
    """测试3: 角色特定工具加载模拟"""
    print("\n" + "="*60)
    print("测试3: 角色特定工具加载模拟")
    print("="*60)
    
    try:
        all_tools = ToolFactory.create_all_tools()
        configs = StrategyGenerator.EXPERT_CONFIGS
        
        # 模拟不同角色的工具加载
        test_cases = [
            ("V4_设计研究员_4-1", "V4", 4),  # V4 应获得4个工具
            ("V2_设计总监_2-1", "V2", 1),    # V2 应获得1个工具（ragflow）
            ("V3_叙事专家_3-1", "V3", 3),    # V3 应获得3个工具
            ("V5_场景专家_5-1", "V5", 3),    # V5 应获得3个工具
            ("V6_总工程师_6-1", "V6", 4),    # V6 应获得4个工具
        ]
        
        all_pass = True
        
        for role_id, role_type, expected_count in test_cases:
            if role_type not in configs:
                print(f"❌ {role_id}: 配置缺失")
                all_pass = False
                continue
            
            config = configs[role_type]
            configured_tools = config.tools
            
            # 模拟工具加载
            expert_tools = []
            for tool_name in configured_tools:
                if tool_name in all_tools:
                    expert_tools.append(all_tools[tool_name])
            
            actual_count = len(expert_tools)
            
            if actual_count == expected_count:
                tool_names = [getattr(t, 'name', str(t)) for t in expert_tools]
                print(f"✅ {role_id}")
                print(f"   配置: {configured_tools}")
                print(f"   加载: {tool_names} ({actual_count}个)")
            else:
                print(f"❌ {role_id}")
                print(f"   预期工具数: {expected_count}")
                print(f"   实际工具数: {actual_count}")
                all_pass = False
        
        if all_pass:
            print("\n✅ 测试3通过: 角色特定工具加载正确")
        else:
            print("\n❌ 测试3失败: 部分角色工具加载不正确")
        
        return all_pass
        
    except Exception as e:
        print(f"❌ 测试3失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_v2_synthesizer_role():
    """测试4: V2综合者角色验证"""
    print("\n" + "="*60)
    print("测试4: V2综合者角色验证")
    print("="*60)
    
    try:
        configs = StrategyGenerator.EXPERT_CONFIGS
        v2_config = configs.get("V2")
        
        if not v2_config:
            print("❌ V2配置缺失")
            return False
        
        print(f"📋 V2配置检查:")
        print(f"   名称: {v2_config.name}")
        print(f"   工具: {v2_config.tools}")
        print(f"   角色描述: {v2_config.work_focus_description[:50]}...")
        
        # V2应该只有ragflow或无工具
        if v2_config.tools == ["ragflow"] or v2_config.tools == []:
            print("\n✅ V2角色正确配置为综合决策者（无外部搜索工具）")
            print("   理由: V2综合V3/V4/V5的研究结果，不应进行独立外部搜索")
            return True
        else:
            print(f"\n⚠️ V2工具配置可能不符合综合者角色: {v2_config.tools}")
            print("   建议: V2应仅使用 [] 或 ['ragflow']（内部知识库）")
            return False
        
    except Exception as e:
        print(f"❌ 测试4失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("🧪 工具系统集成测试套件 (v7.63.1)")
    print("="*80)
    
    results = []
    
    # 运行所有测试
    results.append(("工具工厂", test_tool_factory()))
    results.append(("专家工具配置", test_expert_tool_configs()))
    results.append(("角色特定加载", test_role_specific_loading()))
    results.append(("V2综合者角色", test_v2_synthesizer_role()))
    
    # 统计结果
    print("\n" + "="*80)
    print("📊 测试结果汇总")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {test_name}")
    
    print("\n" + "-"*80)
    print(f"总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！工具系统集成成功！")
        return 0
    else:
        print(f"\n⚠️ {total - passed} 个测试失败，请检查配置")
        return 1


if __name__ == "__main__":
    sys.exit(main())
