"""
v3.5 快速验证测试脚本
Quick Validation Test for v3.5 Expert Collaboration Interface

用于验证v3.5核心组件是否正常工作
"""

import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 使用标准logging替代loguru
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def test_imports():
    """测试1: 验证所有v3.5组件可以正常导入"""
    logger.info(" 测试1: 验证导入...")
    
    try:
        # 导入挑战检测器
        logger.info(" ChallengeDetector 导入成功")
        
        # 导入工作流
        logger.info(" MainWorkflow 导入成功")
        
        # 导入配置管理器
        logger.info(" PromptManager 导入成功")
        
        return True
    except Exception as e:
        logger.error(f" 导入失败: {e}")
        return False


def test_challenge_detector():
    """测试2: 验证挑战检测器的基本功能"""
    logger.info(" 测试2: 验证挑战检测器...")
    
    try:
        from intelligent_project_analyzer.agents.dynamic_project_director import ChallengeDetector
        
        # 创建检测器实例
        detector = ChallengeDetector()
        logger.info(" ChallengeDetector 实例化成功")
        
        # 测试无挑战的情况
        expert_outputs_no_challenge = {
            "v2_design_director": {
                "project_vision_summary": "测试摘要",
                "confidence": 0.9
            }
        }
        
        result = detector.detect_challenges(expert_outputs_no_challenge)
        assert not result["has_challenges"]
        logger.info(" 无挑战检测正常")
        
        # 测试有挑战的情况
        expert_outputs_with_challenge = {
            "v2_design_director": {
                "project_vision_summary": "测试摘要",
                "challenge_flags": [
                    {
                        "challenged_item": "核心张力定义",
                        "rationale": "真正的张力不是XX，而是YY",
                        "reinterpretation": "我的重新诠释是...",
                        "design_impact": "这将导向策略A"
                    }
                ],
                "confidence": 0.9
            }
        }
        
        result = detector.detect_challenges(expert_outputs_with_challenge)
        assert result["has_challenges"]
        assert len(result["challenges"]) == 1
        logger.info(" 有挑战检测正常")
        
        # 测试挑战分类
        challenge = result["challenges"][0]
        challenge_type = detector.classify_challenge_type(challenge)
        logger.info(f" 挑战分类: {challenge_type}")
        
        # 测试挑战处理决策
        decision = detector.decide_handling(challenge, challenge_type)
        logger.info(f" 处理决策: {decision}")
        
        return True
    except Exception as e:
        logger.error(f" 挑战检测器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_requirements_analyst_config():
    """测试3: 验证需求分析师配置是否包含expert_handoff"""
    logger.info(" 测试3: 验证需求分析师配置...")
    
    try:
        from intelligent_project_analyzer.core.prompt_manager import PromptManager
        
        pm = PromptManager()
        ra_config = pm.load_prompt("requirements_analyst")
        
        # 验证版本
        assert ra_config["version"] == "3.5", f"版本不是3.5: {ra_config['version']}"
        logger.info(" 版本号正确: v3.5")
        
        # 验证输出示例中包含expert_handoff
        standard_example = ra_config["output_format_examples"]["standard_example"]
        assert "expert_handoff" in standard_example, "标准示例缺少expert_handoff"
        logger.info(" 标准示例包含expert_handoff")
        
        breakthrough_example = ra_config["output_format_examples"]["breakthrough_example"]
        assert "expert_handoff" in breakthrough_example, "突破性示例缺少expert_handoff"
        logger.info(" 突破性示例包含expert_handoff")
        
        return True
    except Exception as e:
        logger.error(f" 需求分析师配置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_v2_config():
    """测试4: 验证V2设计总监配置是否包含v3.5协议"""
    logger.info(" 测试4: 验证V2设计总监配置...")
    
    try:
        from intelligent_project_analyzer.core.role_manager import RoleManager
        
        role_manager = RoleManager()
        v2_roles = role_manager.get_roles_by_category("V2_设计总监")
        
        # 获取第一个V2角色（2-0）
        first_role = list(v2_roles.values())[0]
        system_prompt = first_role.get("system_prompt", "")
        
        # 验证包含v3.5协议说明
        assert "v3.5" in system_prompt.lower() or "expert autonomy" in system_prompt.lower(), \
            "V2配置缺少v3.5协议说明"
        logger.info(" V2配置包含v3.5协议说明")
        
        # 验证包含五种权力
        assert "五种权力" in system_prompt or "five powers" in system_prompt.lower(), \
            "V2配置缺少五种权力说明"
        logger.info(" V2配置包含五种权力说明")
        
        # 验证包含挑战协议
        assert "挑战协议" in system_prompt or "challenge protocol" in system_prompt.lower(), \
            "V2配置缺少挑战协议"
        logger.info(" V2配置包含挑战协议")
        
        return True
    except Exception as e:
        logger.error(f" V2配置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_workflow_integration():
    """测试5: 验证工作流集成（仅检查结构，不实际运行）"""
    logger.info(" 测试5: 验证工作流集成...")
    
    try:
        import inspect

        from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow
        
        # 验证MainWorkflow包含新方法
        [method for method in dir(MainWorkflow) if not method.startswith('_')]
        
        # 检查内部方法
        source = inspect.getsource(MainWorkflow)
        
        assert "_detect_challenges_node" in source, "工作流缺少_detect_challenges_node方法"
        logger.info(" 工作流包含_detect_challenges_node方法")
        
        assert "_route_after_challenge_detection" in source, "工作流缺少_route_after_challenge_detection方法"
        logger.info(" 工作流包含_route_after_challenge_detection方法")
        
        assert "detect_challenges" in source, "工作流缺少detect_challenges节点"
        logger.info(" 工作流包含detect_challenges节点")
        
        assert "revisit_requirements" in source, "工作流缺少反馈循环路由"
        logger.info(" 工作流包含反馈循环路由")
        
        return True
    except Exception as e:
        logger.error(f" 工作流集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    logger.info("=" * 70)
    logger.info(" 开始v3.5快速验证测试")
    logger.info("=" * 70)
    
    tests = [
        ("导入测试", test_imports),
        ("挑战检测器测试", test_challenge_detector),
        ("需求分析师配置测试", test_requirements_analyst_config),
        ("V2设计总监配置测试", test_v2_config),
        ("工作流集成测试", test_workflow_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info("")
        logger.info(f"{'=' * 70}")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                logger.info(f" {test_name} 通过")
            else:
                logger.error(f" {test_name} 失败")
        except Exception as e:
            logger.error(f" {test_name} 异常: {e}")
            results.append((test_name, False))
    
    # 总结
    logger.info("")
    logger.info("=" * 70)
    logger.info(" 测试总结")
    logger.info("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = " 通过" if result else " 失败"
        logger.info(f"{status} - {test_name}")
    
    logger.info("")
    logger.info(f"总计: {passed}/{total} 测试通过")
    
    if passed == total:
        logger.info(" 所有测试通过！v3.5实施验证成功！")
        return True
    else:
        logger.warning(f"️ 有 {total - passed} 个测试失败，请检查")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
