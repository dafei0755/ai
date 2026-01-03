"""
测试SearchStrategyGenerator.generate_deliverable_queries方法
"""

from intelligent_project_analyzer.agents.search_strategy import SearchStrategyGenerator

# 创建生成器实例
gen = SearchStrategyGenerator()

# 测试方法调用
queries = gen.generate_deliverable_queries(
    deliverable_name="空间布局方案",
    deliverable_description="15平米电竞空间设计",
    keywords=["电竞", "直播", "专业"],
    constraints={},
    project_task="职业电竞选手空间",
    num_queries=3,
)

print("测试结果:")
print(f"  方法调用: 成功")
print(f"  生成查询数量: {len(queries)}")
print(f"  查询内容:")
for i, q in enumerate(queries, 1):
    print(f"    {i}. {q}")

# 验证
assert len(queries) == 3, "应该生成3个查询"
assert all(isinstance(q, str) for q in queries), "所有查询应该是字符串"

print("\n所有测试通过!")
