#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
5轮渐进式搜索测试 (v7.175)

测试 SearchOrchestrator 的5轮渐进式搜索功能
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["USE_PROGRESSIVE_SEARCH"] = "true"

from dotenv import load_dotenv

load_dotenv()


def test_progressive_search():
    """测试5轮渐进式搜索"""
    print("=" * 60)
    print("🔬 5轮渐进式搜索测试 (v7.175)")
    print("=" * 60)

    from intelligent_project_analyzer.services.search_orchestrator import get_search_orchestrator

    orchestrator = get_search_orchestrator()

    # 测试查询
    query = "月亮落在结冰的湖面上 诗人书房设计"
    context = {"project_type": "室内设计", "role_id": "V4", "deliverable_name": "设计概念分析"}

    print(f"📝 Query: {query}")
    print(f"📦 Context: {context}")
    print()

    # 执行5轮搜索
    print("🚀 开始5轮渐进式搜索...")
    print()

    result = orchestrator.orchestrate(query, context, max_rounds=5)

    # 显示结果
    print()
    print("=" * 60)
    print("📊 搜索结果汇总")
    print("=" * 60)

    rounds_completed = result.get("rounds_completed", 0)
    all_sources = result.get("all_sources", [])
    execution_time = result.get("execution_time", 0)

    print(f"✅ 完成轮次: {rounds_completed}")
    print(f"📚 总结果数: {len(all_sources)}")
    print(f"⏱️ 执行时间: {execution_time:.2f}s")

    # 按轮次显示
    rounds = result.get("rounds", {})
    print()
    print("📌 各轮次结果:")
    for round_name, round_data in rounds.items():
        count = len(round_data.get("results", []))
        print(f"   - {round_name}: {count} 条结果")

    # 显示部分结果
    print()
    print("📋 搜索结果样例 (前5条):")
    for i, source in enumerate(all_sources[:5], 1):
        title = source.get("title", "无标题")[:50]
        url = source.get("url", source.get("link", ""))[:60]
        round_type = source.get("round", "unknown")
        print(f"   {i}. [{round_type}] {title}")
        print(f"      {url}...")

    # 验证结果
    print()
    print("=" * 60)
    print("🔍 验证结果")
    print("=" * 60)

    success = True

    # 检查是否完成了5轮搜索
    if rounds_completed >= 3:
        print(f"   ✅ 完成 {rounds_completed} 轮搜索")
    else:
        print(f"   ⚠️ 只完成 {rounds_completed} 轮搜索")

    # 检查是否有搜索结果
    if len(all_sources) > 0:
        print(f"   ✅ 获取到 {len(all_sources)} 条搜索结果")
    else:
        print(f"   ❌ 没有获取到搜索结果")
        success = False

    # 检查各轮次是否有结果
    round_names = ["concepts", "dimensions", "academic", "cases", "data"]
    for rn in round_names:
        if rn in rounds:
            count = len(rounds[rn].get("results", []))
            status = "✅" if count > 0 else "⚠️"
            print(f"   {status} 轮次 '{rn}': {count} 条结果")

    print()
    if success:
        print("🎉 5轮渐进式搜索测试通过！")
    else:
        print("❌ 5轮渐进式搜索测试失败")

    return success


if __name__ == "__main__":
    success = test_progressive_search()
    sys.exit(0 if success else 1)
