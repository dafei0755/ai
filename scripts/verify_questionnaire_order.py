"""
验证并修复问卷题型顺序
确保所有生成的问卷都遵循"单选→多选→文字输入"的顺序
"""
import json
from typing import List, Dict, Any

def verify_questionnaire_order(questions: List[Dict[str, Any]]) -> bool:
    """
    验证问卷题型顺序是否正确
    
    Args:
        questions: 问卷问题列表
        
    Returns:
        bool: True表示顺序正确，False表示需要修复
    """
    type_order = []
    for q in questions:
        q_type = q.get("type", "")
        if q_type not in type_order:
            type_order.append(q_type)
    
    # 期望的顺序
    expected_order = ["single_choice", "multiple_choice", "open_ended"]
    
    # 过滤出实际存在的题型
    actual_types = [t for t in expected_order if t in type_order]
    
    # 检查顺序是否匹配
    return type_order == actual_types


def fix_questionnaire_order(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    修复问卷题型顺序，按照"单选→多选→文字输入"重新排序
    
    Args:
        questions: 原始问卷问题列表
        
    Returns:
        List[Dict[str, Any]]: 修复后的问卷列表
    """
    single_choice = [q for q in questions if q.get("type") == "single_choice"]
    multiple_choice = [q for q in questions if q.get("type") == "multiple_choice"]
    open_ended = [q for q in questions if q.get("type") == "open_ended"]
    
    return single_choice + multiple_choice + open_ended


# 测试用例：用户提供的实际问卷数据
test_questionnaire = {
    "introduction": "为了让我们的设计更贴合您的真实需求...",
    "questions": [
        {"question": "请分享3-5个您喜欢的设计案例...", "type": "open_ended"},
        {"question": "请描述您在这个空间中的典型一天...", "type": "open_ended"},
        {"question": "如果在空间氛围上必须二选一...", "type": "single_choice", "options": []},
        {"question": "在护理服务与个人空间自由之间...", "type": "single_choice", "options": []},
        {"question": "在空间中，哪些元素对您的疗愈体验最有帮助？", "type": "multiple_choice", "options": []},
        {"question": "您产后最不能忍受的空间体验是什么？", "type": "open_ended"},
        {"question": "假设5年后再次回忆...", "type": "open_ended"},
        {"question": "在空间中，您更希望与其他产妇交流...", "type": "single_choice", "options": []}
    ]
}

if __name__ == "__main__":
    print("=" * 60)
    print("问卷题型顺序验证工具")
    print("=" * 60)
    
    questions = test_questionnaire["questions"]
    
    print("\n📋 原始问卷顺序:")
    for i, q in enumerate(questions, 1):
        q_type = q.get("type", "")
        print(f"  {i}. [{q_type}] {q['question'][:30]}...")
    
    print("\n🔍 验证结果:")
    is_valid = verify_questionnaire_order(questions)
    if is_valid:
        print("  ✅ 题型顺序正确")
    else:
        print("  ❌ 题型顺序错误，需要修复")
    
    if not is_valid:
        print("\n🔧 修复后的问卷顺序:")
        fixed_questions = fix_questionnaire_order(questions)
        for i, q in enumerate(fixed_questions, 1):
            q_type = q.get("type", "")
            print(f"  {i}. [{q_type}] {q['question'][:30]}...")
        
        print("\n📊 统计:")
        single_count = len([q for q in fixed_questions if q.get("type") == "single_choice"])
        multiple_count = len([q for q in fixed_questions if q.get("type") == "multiple_choice"])
        open_count = len([q for q in fixed_questions if q.get("type") == "open_ended"])
        print(f"  单选题: {single_count} 个")
        print(f"  多选题: {multiple_count} 个")
        print(f"  文字输入: {open_count} 个")
        print(f"  总计: {len(fixed_questions)} 个")
