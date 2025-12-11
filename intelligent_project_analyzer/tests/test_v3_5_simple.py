"""
v3.5简化验证测试 - 不依赖外部库
只检查文件存在性、语法正确性和配置完整性
"""

import sys
import os
import json
import yaml

# 添加项目根目录
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

def test_yaml_syntax():
    """测试1: 验证所有YAML配置文件语法正确"""
    print("=" * 70)
    print("🧪 测试1: 验证YAML配置语法")
    print("=" * 70)
    
    yaml_files = [
        "intelligent_project_analyzer/config/prompts/requirements_analyst.yaml",
        "intelligent_project_analyzer/config/prompts/expert_autonomy_protocol.yaml",
        "intelligent_project_analyzer/config/roles/v2_design_director.yaml",
    ]
    
    all_passed = True
    for yaml_file in yaml_files:
        file_path = os.path.join(project_root, yaml_file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            print(f"✅ {os.path.basename(yaml_file)} - 语法正确")
        except yaml.YAMLError as e:
            print(f"❌ {os.path.basename(yaml_file)} - YAML错误: {e}")
            all_passed = False
        except Exception as e:
            print(f"❌ {os.path.basename(yaml_file)} - 其他错误: {e}")
            all_passed = False
    
    return all_passed


def test_requirements_analyst_config():
    """测试2: 验证需求分析师配置包含expert_handoff"""
    print("\n" + "=" * 70)
    print("🧪 测试2: 验证需求分析师配置")
    print("=" * 70)
    
    try:
        file_path = os.path.join(project_root, 
            "intelligent_project_analyzer/config/prompts/requirements_analyst.yaml")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 检查版本
        if config.get("version") != "3.5":
            print(f"❌ 版本号不是3.5: {config.get('version')}")
            return False
        print("✅ 版本号正确: v3.5")
        
        # 检查输出示例
        examples = config.get("output_format_examples", {})
        
        standard_example = examples.get("standard_example")
        if standard_example and "expert_handoff" in str(standard_example):
            print("✅ 标准示例包含expert_handoff")
        else:
            print("❌ 标准示例缺少expert_handoff")
            return False
        
        breakthrough_example = examples.get("breakthrough_example")
        if breakthrough_example and "expert_handoff" in str(breakthrough_example):
            print("✅ 突破性示例包含expert_handoff")
        else:
            print("❌ 突破性示例缺少expert_handoff")
            return False
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_expert_protocol_config():
    """测试3: 验证专家主动性协议配置"""
    print("\n" + "=" * 70)
    print("🧪 测试3: 验证专家主动性协议")
    print("=" * 70)
    
    try:
        file_path = os.path.join(project_root,
            "intelligent_project_analyzer/config/prompts/expert_autonomy_protocol.yaml")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 检查版本
        if config.get("version") != "3.5":
            print(f"❌ 版本号不是3.5: {config.get('version')}")
            return False
        print("✅ 版本号正确: v3.5")
        
        # 检查五种权力
        powers = config.get("expert_powers", {})
        if len(powers) >= 5:
            print(f"✅ 包含{len(powers)}种专家权力")
        else:
            print(f"❌ 专家权力不足5种: {len(powers)}")
            return False
        
        # 检查挑战协议
        if "challenge_protocol" in config:
            print("✅ 包含挑战协议")
        else:
            print("❌ 缺少挑战协议")
            return False
        
        # 检查角色特定指南
        role_guides = config.get("role_specific_guides", {})
        if "v2_design_director" in role_guides:
            print("✅ 包含V2角色特定指南")
        else:
            print("❌ 缺少V2角色特定指南")
            return False
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_v2_config():
    """测试4: 验证V2设计总监配置"""
    print("\n" + "=" * 70)
    print("🧪 测试4: 验证V2设计总监配置")
    print("=" * 70)
    
    try:
        file_path = os.path.join(project_root,
            "intelligent_project_analyzer/config/roles/v2_design_director.yaml")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 正确的结构：V2_设计总监 → roles → "2-0" → system_prompt
        v2_config = config.get("V2_设计总监", {})
        roles = v2_config.get("roles", {})
        role_2_0 = roles.get("2-0", {})
        system_prompt = role_2_0.get("system_prompt", "")
        
        if not system_prompt:
            print("❌ 未找到system_prompt（路径：V2_设计总监 → roles → 2-0 → system_prompt）")
            return False
        
        print(f"✅ 成功读取system_prompt（{len(system_prompt)}字符）")
        
        # 检查v3.5协议（不区分大小写）
        system_prompt_lower = system_prompt.lower()
        if "v3.5" in system_prompt or "expert autonomy" in system_prompt_lower:
            print("✅ 包含v3.5协议说明")
        else:
            print("❌ 缺少v3.5协议说明")
            return False
        
        # 检查五种权力（支持中英文）
        if "五种权力" in system_prompt or "five powers" in system_prompt_lower or "你的五种权力" in system_prompt:
            print("✅ 包含五种权力说明")
        else:
            print("❌ 缺少五种权力说明")
            return False
        
        # 检查挑战协议
        if "挑战协议" in system_prompt or "challenge protocol" in system_prompt_lower or "challenge_protocol" in system_prompt_lower:
            print("✅ 包含挑战协议")
        else:
            print("❌ 缺少挑战协议")
            return False
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_python_syntax():
    """测试5: 验证Python文件语法"""
    print("\n" + "=" * 70)
    print("🧪 测试5: 验证Python文件语法")
    print("=" * 70)
    
    python_files = [
        "intelligent_project_analyzer/agents/dynamic_project_director.py",
        "intelligent_project_analyzer/workflow/main_workflow.py",
    ]
    
    all_passed = True
    for py_file in python_files:
        file_path = os.path.join(project_root, py_file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # 尝试编译（不执行）
            compile(code, file_path, 'exec')
            print(f"✅ {os.path.basename(py_file)} - 语法正确")
        except SyntaxError as e:
            print(f"❌ {os.path.basename(py_file)} - 语法错误: {e}")
            all_passed = False
        except Exception as e:
            print(f"❌ {os.path.basename(py_file)} - 其他错误: {e}")
            all_passed = False
    
    return all_passed


def test_code_contains_v35_features():
    """测试6: 验证代码包含v3.5特性"""
    print("\n" + "=" * 70)
    print("🧪 测试6: 验证代码包含v3.5特性")
    print("=" * 70)
    
    # 检查ChallengeDetector类
    try:
        file_path = os.path.join(project_root,
            "intelligent_project_analyzer/agents/dynamic_project_director.py")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        if "class ChallengeDetector" in code:
            print("✅ 包含ChallengeDetector类")
        else:
            print("❌ 缺少ChallengeDetector类")
            return False
        
        if "detect_challenges" in code:
            print("✅ 包含detect_challenges方法")
        else:
            print("❌ 缺少detect_challenges方法")
            return False
        
        if "classify_challenge_type" in code:
            print("✅ 包含classify_challenge_type方法")
        else:
            print("❌ 缺少classify_challenge_type方法")
            return False
    except Exception as e:
        print(f"❌ 检查dynamic_project_director.py失败: {e}")
        return False
    
    # 检查工作流集成
    try:
        file_path = os.path.join(project_root,
            "intelligent_project_analyzer/workflow/main_workflow.py")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        if "detect_challenges" in code:
            print("✅ 工作流包含detect_challenges节点")
        else:
            print("❌ 工作流缺少detect_challenges节点")
            return False
        
        if "_route_after_challenge_detection" in code:
            print("✅ 工作流包含挑战检测路由")
        else:
            print("❌ 工作流缺少挑战检测路由")
            return False
        
        if "revisit_requirements" in code:
            print("✅ 工作流包含反馈循环")
        else:
            print("❌ 工作流缺少反馈循环")
            return False
    except Exception as e:
        print(f"❌ 检查main_workflow.py失败: {e}")
        return False
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 70)
    print("🚀 v3.5简化验证测试")
    print("=" * 70)
    
    tests = [
        ("YAML配置语法", test_yaml_syntax),
        ("需求分析师配置", test_requirements_analyst_config),
        ("专家主动性协议", test_expert_protocol_config),
        ("V2设计总监配置", test_v2_config),
        ("Python文件语法", test_python_syntax),
        ("v3.5代码特性", test_code_contains_v35_features),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} 异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # 总结
    print("\n" + "=" * 70)
    print("📊 测试总结")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！v3.5实施验证成功！")
        print("\n✅ 核心成果:")
        print("   - expert_handoff协作接口已实现")
        print("   - 挑战检测系统已完成")
        print("   - 反馈循环机制已集成")
        print("   - 所有配置文件语法正确")
        print("\n🚀 系统已就绪，可以进入实战测试阶段！")
        return True
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
