"""
v7.17 P1 测试脚本：两阶段需求分析
测试 Phase1（快速定性）→ Phase2（深度分析）的执行流程
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligent_project_analyzer.agents.requirements_analyst import RequirementsAnalystAgent
from intelligent_project_analyzer.services.llm_factory import get_llm

def test_two_phase_analysis():
    """测试两阶段分析模式"""
    print("=" * 60)
    print("v7.17 P1 测试：两阶段需求分析")
    print("=" * 60)
    
    # 创建 LLM 和 Agent
    llm = get_llm()
    agent = RequirementsAnalystAgent(llm_model=llm)
    
    # 测试用例：信息充足的需求
    test_input_sufficient = """
    我是一位32岁的前金融律师，刚刚辞职转型为生活美学博主。
    我有一套75平米的一居室公寓，位于上海，高层，南向，城市景观很好。
    预算60万，希望4个月内完成。
    
    我需要这个空间既能作为内容创作基地（拍摄、直播），又能是我的精神庇护所（冥想、阅读）。
    我很喜欢 Axel Vervoordt 的侘寂美学和 John Pawson 的极简主义。
    
    物业对噪音和施工时间有严格规定。
    """
    
    # 测试用例：信息不足的需求
    test_input_insufficient = """
    我想装修一下房子，预算不多，希望能好看点。
    """
    
    # 模拟 state
    state_sufficient = {
        "session_id": "test_v717_sufficient",
        "user_input": test_input_sufficient
    }
    
    state_insufficient = {
        "session_id": "test_v717_insufficient",
        "user_input": test_input_insufficient
    }
    
    # 测试信息充足的用例
    print("\n" + "-" * 60)
    print("测试1：信息充足的需求（预期执行 Phase1 + Phase2）")
    print("-" * 60)
    
    try:
        result = agent.execute(state_sufficient, config={}, use_two_phase=True)
        print(f"✅ 分析完成")
        print(f"   - analysis_mode: {result.structured_data.get('analysis_mode')}")
        print(f"   - info_status: {result.structured_data.get('info_status')}")
        print(f"   - phase1_elapsed: {result.structured_data.get('phase1_elapsed_s', 'N/A')}s")
        print(f"   - phase2_elapsed: {result.structured_data.get('phase2_elapsed_s', 'N/A')}s")
        print(f"   - confidence: {result.confidence}")
        print(f"   - deliverables: {len(result.structured_data.get('primary_deliverables', []))}个")
        
        # 检查关键字段
        assert result.structured_data.get('analysis_mode') == 'two_phase', "应该是 two_phase 模式"
        assert result.structured_data.get('project_task'), "应该有 project_task"
        print("   ✅ 所有断言通过")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    # 测试信息不足的用例
    print("\n" + "-" * 60)
    print("测试2：信息不足的需求（预期仅执行 Phase1）")
    print("-" * 60)
    
    try:
        result = agent.execute(state_insufficient, config={}, use_two_phase=True)
        print(f"✅ 分析完成")
        print(f"   - analysis_mode: {result.structured_data.get('analysis_mode')}")
        print(f"   - info_status: {result.structured_data.get('info_status')}")
        print(f"   - skip_reason: {result.structured_data.get('skip_phase2_reason', 'N/A')}")
        print(f"   - confidence: {result.confidence}")
        
        # 检查是否跳过了 Phase2
        mode = result.structured_data.get('analysis_mode')
        if mode == 'phase1_only':
            print("   ✅ 正确跳过 Phase2")
        else:
            print(f"   ⚠️ 意外模式: {mode}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_two_phase_analysis()
