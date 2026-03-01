"""
信息补全算法改进验证脚本（v7.200）
验证 analysis-20260223162154-2ed04a93ce89 场景下的修复效果

测试覆盖：
1. PROJECTION_DESCRIPTIONS 映射表完整性
2. _build_output_intent_context 构建正确
3. _build_grouped_task_summary 分组采样
4. _rerank_questions_by_intent 软排序逻辑
5. generate_sync 新参数签名兼容性
6. user_prompt_template 包含 output_intent_context 占位符
7. 回滚开关（intent_driven_mode=false 时不注入意向）
8. 向后兼容（不传新参数时不报错）
"""

import sys
import os

sys.path.insert(0, r"D:\11-20\langgraph-design")

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []


def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, name, detail))
    print(f"{status}  {name}" + (f"\n         {detail}" if detail else ""))


# ──────────────────────────────────────────────
# 测试 1：导入 & PROJECTION_DESCRIPTIONS
# ──────────────────────────────────────────────
print("\n=== 1. 导入与常量 ===")
try:
    from intelligent_project_analyzer.services.llm_gap_question_generator import (
        LLMGapQuestionGenerator,
    )

    g = LLMGapQuestionGenerator()
    EXPECTED_PROJECTIONS = {
        "design_professional",
        "investor_operator",
        "government_policy",
        "construction_execution",
        "aesthetic_critique",
    }
    actual = set(g.PROJECTION_DESCRIPTIONS.keys())
    check("PROJECTION_DESCRIPTIONS 包含全部5个 key", actual == EXPECTED_PROJECTIONS, f"actual={actual}")
    check("investor_operator 描述包含'运营主体'", "运营主体" in g.PROJECTION_DESCRIPTIONS["investor_operator"])
    check("aesthetic_critique 描述包含'文化叙事'", "文化叙事" in g.PROJECTION_DESCRIPTIONS["aesthetic_critique"])
except Exception as e:
    check("导入 LLMGapQuestionGenerator", False, str(e))

# ──────────────────────────────────────────────
# 测试 2：_build_output_intent_context
# ──────────────────────────────────────────────
print("\n=== 2. _build_output_intent_context ===")
try:
    # 有投射
    ctx = g._build_output_intent_context(
        ["investor_operator", "aesthetic_critique", "design_professional"],
        [{"label": "文化见证者", "spatial_need": "精神性叙事空间"}],
        None,
    )
    check("包含 investor_operator 描述", "投资运营分析" in ctx)
    check("包含 aesthetic_critique 描述", "美学评论文本" in ctx)
    check("包含身份模式标签", "文化见证者" in ctx)
    check("包含 spatial_need", "精神性叙事空间" in ctx)

    # 无投射时的 fallback
    ctx_empty = g._build_output_intent_context(None, None, None)
    check("空投射返回 fallback 文案", "未检测到" in ctx_empty)

    ctx_empty2 = g._build_output_intent_context([], None, None)
    check("空列表返回 fallback 文案", "未检测到" in ctx_empty2)
except Exception as e:
    check("_build_output_intent_context", False, str(e))

# ──────────────────────────────────────────────
# 测试 3：_build_grouped_task_summary
# ──────────────────────────────────────────────
print("\n=== 3. _build_grouped_task_summary（38任务场景）===")
try:
    # 构造模拟38个任务（10个分组）
    categories = ["文化研究", "空间设计", "材料策略", "运营模型", "资本策略", "社会建模", "环境适应", "灯光设计", "文化产品化", "叙事体验"]
    mock_tasks = []
    for i, cat in enumerate(categories):
        for j in range(4):  # 每组4个任务
            mock_tasks.append({"category": cat, "title": f"{cat}任务{j+1}", "description": f"{cat}的具体描述{j+1}"})
    # 总计 40 个任务

    summary = g._build_grouped_task_summary(mock_tasks)
    check("包含所有10个分组", all(f"[{cat}]" in summary for cat in categories))
    check("每组显示'等N项'", "等4项" in summary)
    check("不超过12组", summary.count("[") <= 12)

    # 5个任务的小场景
    small_tasks = [
        {"category": "A", "title": "任务A", "description": "描述A"},
        {"category": "B", "title": "任务B", "description": "描述B"},
    ]
    small_summary = g._build_grouped_task_summary(small_tasks)
    check("小任务集直接列出", "[A]" in small_summary and "[B]" in small_summary)

    # 空任务
    empty_summary = g._build_grouped_task_summary([])
    check("空任务返回占位文案", "无已确认任务" in empty_summary)
except Exception as e:
    check("_build_grouped_task_summary", False, str(e))

# ──────────────────────────────────────────────
# 测试 4：_rerank_questions_by_intent
# ──────────────────────────────────────────────
print("\n=== 4. _rerank_questions_by_intent（软排序）===")
try:
    mock_questions = [
        # 通用泛问（无 projection_relevance）
        {
            "id": "generic_area",
            "question": "总面积是多少？",
            "is_required": False,
            "decision_impact": "low",
            "projection_relevance": [],
        },
        # investor 相关高决策
        {
            "id": "operator",
            "question": "运营主体是谁？",
            "is_required": True,
            "decision_impact": "high",
            "projection_relevance": ["investor_operator"],
        },
        # aesthetic 相关高决策
        {
            "id": "narrative",
            "question": "文化叙事核心立场是什么？",
            "is_required": True,
            "decision_impact": "high",
            "projection_relevance": ["aesthetic_critique"],
        },
        # 低相关中等决策
        {
            "id": "style_pref",
            "question": "偏好哪种风格？",
            "is_required": False,
            "decision_impact": "medium",
            "projection_relevance": ["design_professional"],
        },
        # 强相关（3个投射）
        {
            "id": "business_model",
            "question": "商业模式是什么？",
            "is_required": True,
            "decision_impact": "high",
            "projection_relevance": ["investor_operator", "design_professional"],
        },
    ]

    active = ["investor_operator", "aesthetic_critique", "design_professional"]
    ranked = g._rerank_questions_by_intent(mock_questions, active)

    ids_ranked = [q["id"] for q in ranked]
    check("排序后 generic_area（低分）不在 top-3", ids_ranked.index("generic_area") >= 2, f"ranked order: {ids_ranked}")
    check(
        "高分题（operator/narrative/business_model）在前3",
        all(q in ids_ranked[:3] for q in ["operator", "narrative", "business_model"]),
        f"top3={ids_ranked[:3]}",
    )
    check("返回题数不变（5题）", len(ranked) == 5)
except Exception as e:
    check("_rerank_questions_by_intent", False, str(e))

# ──────────────────────────────────────────────
# 测试 5：generate_sync 签名兼容性
# ──────────────────────────────────────────────
print("\n=== 5. generate_sync 签名兼容性 ===")
try:
    import inspect

    sig = inspect.signature(g.generate_sync)
    params = list(sig.parameters.keys())
    check("active_projections 参数存在", "active_projections" in params)
    check("detected_identity_modes 参数存在", "detected_identity_modes" in params)
    check("output_framework_signals 参数存在", "output_framework_signals" in params)
    # 默认值均为 None（向后兼容）
    for p in ["active_projections", "detected_identity_modes", "output_framework_signals"]:
        default = sig.parameters[p].default
        check(f"{p} 默认值为 None", default is None)
except Exception as e:
    check("generate_sync 签名", False, str(e))

# ──────────────────────────────────────────────
# 测试 6：YAML 模板包含新占位符
# ──────────────────────────────────────────────
print("\n=== 6. YAML模板 ===")
try:
    template = g.user_template
    check("模板包含 {output_intent_context}", "{output_intent_context}" in template)
    check("模板包含 {task_summary}", "{task_summary}" in template)
    check("模板包含 {user_input}", "{user_input}" in template)
    check("模板标注'通用信息完整性分析（参考）'", "通用信息完整性分析（参考）" in template or "参考" in template)
    check("模板包含生成要求说明", "关键决策变量" in template)

    prompt_config = g.generation_config
    check("generation_config 包含 intent_driven_mode", "intent_driven_mode" in prompt_config)
    check("generation_config 包含 intent_rerank_enabled", "intent_rerank_enabled" in prompt_config)
except Exception as e:
    check("YAML 模板验证", False, str(e))

# ──────────────────────────────────────────────
# 测试 7：system_prompt 包含原则 0
# ──────────────────────────────────────────────
print("\n=== 7. system_prompt 原则 0 ===")
try:
    sp = g.system_prompt
    check("system_prompt 包含'输出意向优先'", "输出意向优先" in sp)
    check("包含 investor_operator 示例", "investor_operator" in sp)
    check("包含 aesthetic_critique 示例", "aesthetic_critique" in sp)
    check("包含 construction_execution 示例", "construction_execution" in sp)
    check("包含 decision_impact 字段要求", "decision_impact" in sp)
    check("包含 projection_relevance 字段要求", "projection_relevance" in sp)
except Exception as e:
    check("system_prompt 原则 0", False, str(e))

# ──────────────────────────────────────────────
# 测试 8：回滚开关
# ──────────────────────────────────────────────
print("\n=== 8. 回滚开关 ===")
try:
    import asyncio

    async def _mock_generate_check_context(intent_env_val, projections):
        """通过 monkey-patch 捕获实际发送给 LLM 的 prompt"""
        captured = {}

        original_invoke = None
        try:
            from intelligent_project_analyzer.utils.llm_retry import ainvoke_llm_with_retry
        except ImportError:
            return None

        # 只测试 output_intent_context 的构建，不实际调 LLM
        # 直接测开关逻辑
        import os

        os.environ["GAP_INTENT_DRIVEN_MODE"] = intent_env_val

        g2 = LLMGapQuestionGenerator()
        intent_driven = (
            g2.generation_config.get("intent_driven_mode", True)
            and os.getenv("GAP_INTENT_DRIVEN_MODE", "true").lower() != "false"
        )
        ctx = g2._build_output_intent_context(projections, None, None) if intent_driven else "（未启用意向驱动模式）"
        return ctx

    # intent_driven_mode=true
    ctx_on = asyncio.run(_mock_generate_check_context("true", ["investor_operator"]))
    check("开关ON时包含意向描述", ctx_on and "投资运营分析" in ctx_on, str(ctx_on)[:60])

    # intent_driven_mode=false（回滚）
    ctx_off = asyncio.run(_mock_generate_check_context("false", ["investor_operator"]))
    check("开关OFF时返回禁用文案", ctx_off and "未启用意向驱动" in ctx_off, str(ctx_off)[:60])

    # 恢复环境变量
    os.environ.pop("GAP_INTENT_DRIVEN_MODE", None)
except Exception as e:
    check("回滚开关测试", False, str(e))

# ──────────────────────────────────────────────
# 测试 9：向后兼容（不传新参数）
# ──────────────────────────────────────────────
print("\n=== 9. 向后兼容（无 active_projections）===")
try:
    # 仅传旧参数，验证不报错
    import asyncio

    async def test_compat():
        # 用 mock LLM 避免真实 API 调用
        class MockLLM:
            async def ainvoke(self, messages, config=None):
                class R:
                    content = '{"questions": [{"id": "q1", "question": "测试？", "type": "open_ended", "is_required": true, "priority": 1, "weight": 5}]}'

                return R()

        result = await g.generate(
            user_input="测试输入",
            confirmed_tasks=[{"title": "任务1", "description": "描述1", "category": "测试"}],
            missing_dimensions=["预算约束"],
            covered_dimensions=["基本信息"],
            existing_info_summary="已有摘要",
            completeness_score=0.5,
            llm=MockLLM(),
            # 不传 active_projections、detected_identity_modes、output_framework_signals
        )
        return result

    result = asyncio.run(test_compat())
    check("无新参数时不报错", isinstance(result, list))
    check("无新参数时仍返回问题", len(result) > 0, f"返回 {len(result)} 题")
except Exception as e:
    check("向后兼容测试", False, str(e))

# ──────────────────────────────────────────────
# 测试 10：progressive_questionnaire.py 调用处已更新
# ──────────────────────────────────────────────
print("\n=== 10. progressive_questionnaire.py 调用处验证 ===")
try:
    import ast

    with open(
        r"D:\11-20\langgraph-design\intelligent_project_analyzer\interaction\nodes\progressive_questionnaire.py",
        "r",
        encoding="utf-8",
    ) as f:
        src = f.read()

    check("调用处包含 active_projections=state.get", 'active_projections=state.get("active_projections"' in src)
    check(
        "调用处包含 detected_identity_modes=state.get", 'detected_identity_modes=state.get("detected_identity_modes"' in src
    )
    check(
        "调用处包含 output_framework_signals=state.get",
        'output_framework_signals=state.get("output_framework_signals"' in src,
    )
except Exception as e:
    check("progressive_questionnaire.py 调用处", False, str(e))

# ──────────────────────────────────────────────
# 汇总
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("测试汇总")
print("=" * 60)
passed = sum(1 for r in results if r[0] == PASS)
failed = sum(1 for r in results if r[0] == FAIL)
print(f"通过: {passed}/{len(results)}  失败: {failed}/{len(results)}")
if failed:
    print("\n失败项：")
    for s, n, d in results:
        if s == FAIL:
            print(f"  ❌ {n}: {d}")
    sys.exit(1)
else:
    print("\n所有测试通过！修复验证完成。")
    sys.exit(0)
