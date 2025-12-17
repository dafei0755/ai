#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
v7.17 端到端真实 LLM 测试
测试 StateGraph Agent 在真实 LLM 调用下的表现
"""

import asyncio
import os
import sys
import time

# 设置环境变量
os.environ["USE_V717_REQUIREMENTS_ANALYST"] = "true"

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow
from intelligent_project_analyzer.services.llm_factory import LLMFactory
from intelligent_project_analyzer.settings import settings


def test_e2e_real_llm():
    """端到端真实 LLM 测试"""
    print("\n" + "=" * 60)
    print("🚀 v7.17 端到端真实 LLM 测试")
    print("=" * 60)
    
    # 初始化
    llm = LLMFactory.create_llm(settings.llm)
    workflow = MainWorkflow(llm_model=llm, config={})
    
    print(f"✅ 工作流初始化完成")
    print(f"   - v7.17 模式: {os.environ.get('USE_V717_REQUIREMENTS_ANALYST')}")
    
    # 构造测试状态
    state = {
        "session_id": "e2e-test-001",
        "user_input": """我是一位32岁的前金融律师，刚完成职业转型成为独立设计顾问。
我在上海有一套75平米的两室公寓，希望重新设计成既能满足远程办公需求，
又能体现我专业品质与生活温度融合的现代简约风格住宅。
预算约20万，希望三个月内完成。""",
        "calibration_processed": False,
        "calibration_skipped": False
    }
    
    print(f"\n📝 测试输入:")
    print(f"   {state['user_input'][:80]}...")
    
    # 执行需求分析
    print(f"\n🔄 正在执行需求分析（使用真实 LLM）...")
    start = time.time()
    result = workflow._requirements_analyst_node(state)
    elapsed = time.time() - start
    
    print(f"\n⏱️ 总耗时: {elapsed:.2f}秒")
    print(f"📊 返回字段: {list(result.keys())}")
    
    # 解析结构化需求
    sr = result.get("structured_requirements", {})
    analysis_mode = sr.get("analysis_mode", "unknown")
    project_type = sr.get("project_type", "unknown")
    project_task = sr.get("project_task", "")
    
    print(f"\n📋 分析结果:")
    print(f"   - 分析模式: {analysis_mode}")
    print(f"   - 项目类型: {project_type}")
    print(f"   - 项目任务: {project_task[:100]}...")
    
    # 检查交付物（从 deliverable_owner_map 或 deliverables 字段）
    deliverables = sr.get("deliverables", [])
    deliverable_owner_map = result.get("deliverable_owner_map", {})
    deliverable_count = len(deliverables) if deliverables else len(deliverable_owner_map)
    
    print(f"\n🎯 识别到 {deliverable_count} 个交付物:")
    if deliverables:
        for d in deliverables[:5]:
            d_id = d.get("id", "?")
            d_name = d.get("name", "?")
            d_priority = d.get("priority", "?")
            print(f"   - {d_id}: {d_name} ({d_priority})")
    elif deliverable_owner_map:
        for d_id, owner in list(deliverable_owner_map.items())[:5]:
            print(f"   - {d_id}: {owner}")
    
    # 检查专家接口
    expert_handoff = sr.get("expert_handoff", {})
    critical_questions = expert_handoff.get("critical_questions_for_experts", {})
    print(f"\n🤝 专家接口 ({len(critical_questions)} 个专家):")
    for expert, questions in list(critical_questions.items())[:3]:
        if questions:
            q = questions[0] if isinstance(questions, list) else str(questions)
            print(f"   - {expert}: {q[:60]}...")
    
    # 验证结果
    print("\n" + "=" * 60)
    print("📊 验证结果")
    print("=" * 60)
    
    checks = [
        ("分析模式", analysis_mode in ["two_phase", "fast_track", "info_insufficient"]),
        ("项目类型", project_type != "unknown" and project_type),
        ("项目任务", len(project_task) > 20),
        ("交付物识别", deliverable_count > 0),
        ("专家接口", len(critical_questions) > 0),
        ("耗时合理", elapsed < 60),  # 应在60秒内完成
    ]
    
    all_passed = True
    for name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"   {status} {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 端到端测试通过！v7.17 StateGraph Agent 工作正常")
    else:
        print("❌ 部分测试未通过，请检查日志")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = test_e2e_real_llm()
    sys.exit(0 if success else 1)
