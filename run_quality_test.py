#!/usr/bin/env python3
"""需求分析师质量测试 - 基于 sf/q.txt 场景"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# 设置UTF-8编码
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

sys.path.insert(0, r"d:\11-20\langgraph-design")

from intelligent_project_analyzer.agents.requirements_analyst_agent import (
    RequirementsAnalystAgentV2, 
    RequirementsAnalystState
)
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# 读取测试场景
def load_scenarios(file_path: str, limit: int = 10):
    """从 q.txt 加载测试场景"""
    scenarios = []
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 按行分割
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    for line in lines[:limit]:
        # 移除序号
        if '. ' in line:
            parts = line.split('. ', 1)
            if len(parts) == 2:
                num, text = parts
                scenarios.append({
                    'id': num,
                    'text': text
                })
    
    return scenarios

# 执行单个测试
def test_scenario(agent, scenario):
    """测试单个场景"""
    try:
        state = RequirementsAnalystState(
            user_input=scenario['text'],
            _llm_model=agent.llm_model,
            _prompt_manager=agent.prompt_manager
        )
        
        result = agent._graph.invoke(state)
        
        # 提取关键信息
        phase1_result = result.get('phase1_result', {})
        
        return {
            'scenario_id': scenario['id'],
            'success': True,
            'info_status': phase1_result.get('info_status', 'unknown'),
            'recommended_next': phase1_result.get('recommended_next_step', 'unknown'),
            'primary_deliverables': [
                d.get('type', 'unknown') for d in phase1_result.get('primary_deliverables', [])
            ],
            'is_fallback': phase1_result.get('fallback', False),
            'project_summary': phase1_result.get('project_summary', '')[:100] + '...'
        }
    except Exception as e:
        return {
            'scenario_id': scenario['id'],
            'success': False,
            'error': str(e)
        }

# 主测试流程
def main():
    print("="*60)
    print("需求分析师质量测试（完整版）")
    print("="*60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试文件: sf/q.txt")
    print(f"测试数量: 全部场景（25+）")
    print("="*60)
    
    # 加载场景
    scenarios = load_scenarios(r"d:\11-20\langgraph-design\sf\q.txt", limit=50)  # 读取所有场景
    print(f"\n✅ 加载了 {len(scenarios)} 个测试场景")
    
    # 初始化Agent
    print("\n初始化Agent...")
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        agent = RequirementsAnalystAgentV2(llm)
        print("✅ Agent初始化成功")
    except Exception as e:
        print(f"❌ Agent初始化失败: {e}")
        return
    
    # 执行测试
    print("\n" + "="*60)
    print("开始批量测试...")
    print("="*60)
    
    results = []
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n[{i}/{len(scenarios)}] 测试场景 #{scenario['id']}")
        print(f"输入: {scenario['text'][:80]}...")
        
        result = test_scenario(agent, scenario)
        results.append(result)
        
        if result['success']:
            print(f"✅ 成功")
            print(f"   信息状态: {result['info_status']}")
            print(f"   推荐步骤: {result['recommended_next']}")
            print(f"   交付物: {', '.join(result['primary_deliverables'])}")
            print(f"   Fallback: {result['is_fallback']}")
        else:
            print(f"❌ 失败: {result['error']}")
    
    # 生成报告
    print("\n" + "="*60)
    print("测试统计")
    print("="*60)
    
    success_count = sum(1 for r in results if r['success'])
    fallback_count = sum(1 for r in results if r.get('is_fallback', False))
    
    # 统计info_status
    info_sufficient = sum(1 for r in results if r.get('info_status') == 'sufficient')
    info_insufficient = sum(1 for r in results if r.get('info_status') == 'insufficient')
    
    # 统计recommended_next
    questionnaire_first = sum(1 for r in results if r.get('recommended_next') == 'questionnaire_first')
    direct_analysis = sum(1 for r in results if r.get('recommended_next') == 'direct_analysis')
    
    print(f"\n成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
    print(f"Fallback率: {fallback_count}/{success_count} ({fallback_count/success_count*100 if success_count > 0 else 0:.1f}%)")
    
    print(f"\n信息充足性:")
    print(f"  充足: {info_sufficient} ({info_sufficient/success_count*100 if success_count > 0 else 0:.1f}%)")
    print(f"  不足: {info_insufficient} ({info_insufficient/success_count*100 if success_count > 0 else 0:.1f}%)")
    
    print(f"\n推荐步骤:")
    print(f"  问卷优先: {questionnaire_first} ({questionnaire_first/success_count*100 if success_count > 0 else 0:.1f}%)")
    print(f"  直接分析: {direct_analysis} ({direct_analysis/success_count*100 if success_count > 0 else 0:.1f}%)")
    
    # 保存详细结果
    output_file = r"d:\11-20\langgraph-design\quality_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_scenarios': len(scenarios),
            'success_count': success_count,
            'fallback_count': fallback_count,
            'results': results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 详细结果已保存到: quality_test_results.json")
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)

if __name__ == "__main__":
    main()
