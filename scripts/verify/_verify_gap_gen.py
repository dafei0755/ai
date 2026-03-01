"""验证 LLMGapQuestionGenerator 的 space_type 关键词驱动改造"""
from intelligent_project_analyzer.services.llm_gap_question_generator import LLMGapQuestionGenerator

g = LLMGapQuestionGenerator()
print("space_type_keywords:", list(g._space_type_keywords.keys()))
print("dynamic_gap_dims:", list(g._dynamic_gap_dimensions.keys()))
print()

cases = [
    ("深圳湾高端别墅", "residential_premium"),
    ("广东狮岭乡村振兴改造", "rural"),
    ("上海某医院无障碍改造", "healthcare"),
    ("当代艺术博物馆", "cultural"),
    ("城市广场更新", "public"),
    ("联合办公空间", "office"),
    ("旗舰店商业空间", "commercial"),
    ("80平米公寓翻新", "residential_standard"),
    ("其他未知项目", "general"),
]
all_ok = True
for inp, expected in cases:
    result = g._detect_project_type(inp)
    ok = result == expected
    all_ok = all_ok and ok
    print(f'  {"OK" if ok else "FAIL"} {inp[:12]:12} -> {result} (expected {expected})')

print()
ctx_villa = g._build_output_intent_context(["investor_operator"], None, None, user_input="深圳湾别墅")
ctx_rural = g._build_output_intent_context(["investor_operator"], None, None, user_input="乡村振兴项目")
villa_ok = "村集体" not in ctx_villa
rural_ok = "村集体" in ctx_rural or "乡村" in ctx_rural or "运营" in ctx_rural
print(f'  {"OK" if villa_ok else "FAIL"} 别墅不含村集体: {repr(ctx_villa[:80])}')
print(f'  {"OK" if rural_ok else "FAIL"} 乡村含相关词:   {repr(ctx_rural[:80])}')
print()
print("ALL PASS" if (all_ok and villa_ok and rural_ok) else "SOME FAILURES - 见上方 FAIL 行")
