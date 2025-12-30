"""
测试 quality_preflight 节点的 JSON 解析修复
验证：
1. 含注释的 JSON 能正确解析
2. 缺少引号的键名能自动修复
3. 完全无效的 JSON 会降级到默认值
"""
import re
import json

def test_json_repair():
    """测试 JSON 修复逻辑"""
    
    # 测试用例1：含单行注释
    test_case_1 = """{
        "risk_assessment": {
            "requirement_clarity": 75,  // 需求清晰度
            "task_complexity": 60,
            "overall_risk_score": 62
        },
        "risk_points": ["风险1"]
    }"""
    
    # 测试用例2：缺少引号的键名（Qwen 常见问题）
    test_case_2 = """{
        risk_assessment: {
            requirement_clarity: 75,
            task_complexity: 60
        },
        risk_points: ["风险1"]
    }"""
    
    # 测试用例3：混合问题
    test_case_3 = """{
        risk_assessment: {  // 评估结果
            requirement_clarity: 75,  /* 清晰度 */
            task_complexity: 60
        },
        risk_points: ["风险1", "风险2"]
    }"""
    
    # 测试用例4：完全无效
    test_case_4 = "这不是JSON"
    
    test_cases = [
        ("含单行注释", test_case_1),
        ("缺少引号的键名", test_case_2),
        ("混合问题", test_case_3),
        ("完全无效", test_case_4)
    ]
    
    for name, json_str in test_cases:
        print(f"\n{'='*60}")
        print(f"测试用例: {name}")
        print(f"原始输入:\n{json_str[:100]}...")
        
        # 应用修复逻辑
        json_match = re.search(r'\{[\s\S]*\}', json_str)
        if json_match:
            fixed_json = json_match.group()
            
            # 1. 移除单行注释
            fixed_json = re.sub(r'//.*?(?=\n|$)', '', fixed_json)
            # 2. 移除多行注释
            fixed_json = re.sub(r'/\*.*?\*/', '', fixed_json, flags=re.DOTALL)
            # 3. 修复缺少引号的键名
            fixed_json = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', fixed_json)
            
            print(f"修复后:\n{fixed_json[:100]}...")
            
            try:
                result = json.loads(fixed_json)
                print(f"✅ 解析成功: {list(result.keys())}")
            except json.JSONDecodeError as e:
                print(f"❌ 解析失败: {e}")
                print("   → 将使用默认值")
        else:
            print("❌ 未找到 JSON 结构")
            print("   → 将使用默认值")

if __name__ == "__main__":
    print("JSON 修复逻辑测试")
    print("="*60)
    test_json_repair()
    print("\n" + "="*60)
    print("测试完成！")
