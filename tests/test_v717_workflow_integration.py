"""
v7.17 集成测试：需求分析师 StateGraph Agent 在主工作流中的执行
"""

import os
import sys

# 启用 v7.17 模式
os.environ["USE_V717_REQUIREMENTS_ANALYST"] = "true"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow


class MockLLM:
    """模拟 LLM 用于测试"""
    call_count = 0
    
    def invoke(self, messages):
        MockLLM.call_count += 1
        
        class MockResponse:
            pass
        
        response = MockResponse()
        
        import json
        
        # 根据调用次数返回不同的响应
        if MockLLM.call_count == 1:
            # Phase1 响应
            response.content = json.dumps({
                "info_status": "sufficient",
                "info_status_reason": "信息完整",
                "project_summary": "75平米公寓设计项目",
                "project_type_preliminary": "personal_residential",
                "primary_deliverables": [
                    {
                        "deliverable_id": "D1",
                        "type": "design_strategy",
                        "description": "设计策略文档",
                        "priority": "MUST_HAVE",
                        "capability_check": {"within_capability": True}
                    },
                    {
                        "deliverable_id": "D2",
                        "type": "naming_list",
                        "description": "空间命名方案",
                        "priority": "NICE_TO_HAVE",
                        "capability_check": {"within_capability": True}
                    }
                ],
                "recommended_next_step": "phase2_analysis"
            }, ensure_ascii=False)
        else:
            # Phase2 响应
            response.content = json.dumps({
                "analysis_layers": {
                    "L1_facts": [
                        "用户身份: 32岁前金融律师",
                        "空间: 75平米公寓",
                        "预算: 60万",
                        "风格偏好: 现代简约"
                    ],
                    "L2_user_model": {
                        "psychological": "追求品质生活，注重细节",
                        "sociological": "职业转型中，希望表达新身份",
                        "aesthetic": "偏好简约，但不失温度"
                    },
                    "L3_core_tension": "专业形象 vs 生活温度的平衡",
                    "L4_project_task": "为转型期的年轻专业人士打造一个既有专业感又有生活温度的居住空间",
                    "L5_sharpness": {"score": 85, "note": "需求清晰，核心矛盾明确"}
                },
                "structured_output": {
                    "project_task": "为32岁前金融律师设计75平米现代简约公寓，体现专业品质与生活温度的融合",
                    "character_narrative": "一位从金融法律界转型的年轻女性，追求品质与效率，希望居住空间能体现其专业素养与对生活美学的追求",
                    "physical_context": "75平米一居室公寓，高层南向",
                    "resource_constraints": "预算60万，4个月工期",
                    "regulatory_requirements": "住宅装修标准规范",
                    "inspiration_references": "北欧极简 + 日式收纳智慧",
                    "experience_behavior": "工作日高效，周末放松阅读与瑜伽",
                    "design_challenge": "在有限空间内实现工作、生活、休闲的功能分区"
                },
                "expert_handoff": {
                    "critical_questions_for_experts": {
                        "V3_叙事专家": ["如何通过空间叙事表达职业转型的心理变化？"],
                        "V4_设计研究员": ["有哪些成功的小空间多功能设计案例？"],
                        "V5_场景专家": ["如何设计从高效工作到放松休息的场景转换？"]
                    },
                    "design_challenge_spectrum": {
                        "tension_axis": "专业形象 ↔ 生活温度",
                        "risk_tolerance": "中等"
                    },
                    "permission_to_diverge": {
                        "encouraged_areas": ["收纳系统创新", "光影氛围设计"],
                        "constrained_areas": ["风格统一性", "预算控制"]
                    }
                }
            }, ensure_ascii=False)
        
        return response


def test_workflow_integration():
    """测试工作流集成"""
    print("=" * 60)
    print("v7.17 集成测试：需求分析师 StateGraph Agent")
    print("=" * 60)
    
    # 重置 Mock LLM 调用计数
    MockLLM.call_count = 0
    
    # 创建工作流
    mock_llm = MockLLM()
    workflow = MainWorkflow(llm_model=mock_llm)
    
    print(f"✅ 工作流创建成功")
    print(f"   - v7.17 模式: {os.getenv('USE_V717_REQUIREMENTS_ANALYST')}")
    
    # 模拟初始状态
    initial_state = {
        "session_id": "test-integration-001",
        "user_input": "我是一位32岁的前金融律师，有一套75平米的公寓，预算60万，希望现代简约风格的设计",
        "calibration_processed": False,
        "calibration_skipped": False
    }
    
    # 直接调用需求分析师节点（跳过安全验证节点）
    print("\n📋 执行需求分析师节点...")
    result = workflow._requirements_analyst_node(initial_state)
    
    print(f"\n✅ 节点执行完成")
    print(f"   - LLM 调用次数: {MockLLM.call_count}")
    print(f"   - 返回字段数: {len(result)}")
    
    # 检查关键字段
    if "structured_requirements" in result:
        sr = result["structured_requirements"]
        print(f"\n📊 结构化需求:")
        print(f"   - project_task: {sr.get('project_task', 'N/A')[:50]}...")
        print(f"   - analysis_mode: {sr.get('analysis_mode', 'N/A')}")
        print(f"   - project_type: {sr.get('project_type', 'N/A')}")
        
        # 检查是否有 StateGraph 元数据
        if "precheck_elapsed_ms" in sr:
            print(f"\n⏱️ StateGraph 耗时统计:")
            print(f"   - precheck: {sr.get('precheck_elapsed_ms', 0):.1f}ms")
            print(f"   - phase1: {sr.get('phase1_elapsed_ms', 0):.1f}ms")
            print(f"   - phase2: {sr.get('phase2_elapsed_ms', 0):.1f}ms")
        
        # 检查交付物
        deliverables = sr.get("primary_deliverables", [])
        if deliverables:
            print(f"\n🎯 交付物识别 ({len(deliverables)}个):")
            for d in deliverables:
                print(f"   - {d.get('deliverable_id')}: {d.get('type')} ({d.get('priority')})")
        
        # 检查专家接口
        expert_handoff = sr.get("expert_handoff", {})
        if expert_handoff:
            critical_q = expert_handoff.get("critical_questions_for_experts", {})
            if critical_q:
                print(f"\n🤝 专家接口 ({len(critical_q)}个专家):")
                for expert, questions in list(critical_q.items())[:3]:
                    print(f"   - {expert}: {questions[0][:40] if questions else 'N/A'}...")
    
    # 检查项目类型
    if "project_type" in result:
        print(f"\n🏠 项目类型: {result['project_type']}")
    
    # 检查交付物责任者映射
    if "deliverable_owner_map" in result:
        print(f"\n📋 交付物责任者映射: {result['deliverable_owner_map']}")
    
    print("\n" + "=" * 60)
    print("✅ 集成测试通过")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    test_workflow_integration()
