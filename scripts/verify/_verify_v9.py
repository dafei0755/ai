"""v9.0 修复验证脚本 (运行: python _verify_v9.py)"""
import sys

sys.path.insert(0, ".")

results = []


def check(name, fn):
    try:
        fn()
        results.append((name, True))
        print(f"  PASS  {name}")
    except Exception as e:
        results.append((name, False))
        print(f"  FAIL  {name}: {e}")


# ── P0: 断链修复 ──────────────────────────────────────────────
print("\n[P0] 动态贡献层——emotion/civilization 不再卡默认值")


def test_p0():
    from intelligent_project_analyzer.services import projection_dispatcher as pd

    pd._projections_config_cache = None
    state = {
        "selected_radar_dimensions": [
            {"id": "ritual", "category": "experience", "source": "decision"},
            {"id": "heritage", "category": "aesthetic", "source": "insight"},
            {"id": "openplan", "category": "functional", "source": "calibration"},
        ],
        "radar_dimension_values": {"ritual": 75, "heritage": 60, "openplan": 40},
    }
    s = pd.calculate_axis_scores(state)
    assert abs(s["emotion"] - 0.75) < 0.01, f"emotion={s['emotion']} should be ~0.75"
    assert abs(s["civilization"] - 0.60) < 0.01, f"civilization={s['civilization']} should be ~0.60"
    assert abs(s["operation"] - 0.40) < 0.01, f"operation={s['operation']} should be ~0.40"
    print(
        f"       emotion={s['emotion']:.3f}(exp 0.750)  civilization={s['civilization']:.3f}(exp 0.600)  operation={s['operation']:.3f}(exp 0.400)"
    )


check("emotion/civilization/operation 动态值正确", test_p0)

# ── P1: 编排器 ────────────────────────────────────────────────
print("\n[P1] RadarDimensionOrchestrator")


def test_p1_quality_pass():
    from intelligent_project_analyzer.services.radar_dimension_orchestrator import _compute_quality_score

    dims = [
        {
            "id": f"d{i}",
            "name": f"n{i}",
            "left_label": f"L{i}",
            "right_label": f"R{i}",
            "default_value": 20 + i * 10,
            "category": c,
            "source": s,
        }
        for i, (c, s) in enumerate(
            [
                ("aesthetic", "calibration"),
                ("experience", "decision"),
                ("functional", "insight"),
                ("technology", "calibration"),
                ("resource", "decision"),
                ("special", "insight"),
            ]
        )
    ]
    score, issues = _compute_quality_score(dims)
    assert score >= 0.55, f"quality={score} issues={issues}"
    print(f"       quality_score={score:.3f} (>= 0.55)")


check("质量得分函数——合格集得分 >= 0.55", test_p1_quality_pass)


def test_p1_quality_empty():
    from intelligent_project_analyzer.services.radar_dimension_orchestrator import _compute_quality_score

    score, _ = _compute_quality_score([])
    assert score == 0.0


check("质量得分函数——空列表得 0.0", test_p1_quality_empty)


def test_p1_fallback():
    from unittest.mock import patch
    from intelligent_project_analyzer.services.radar_dimension_orchestrator import RadarDimensionOrchestrator

    fake = [
        {
            "id": f"d{i}",
            "name": f"n{i}",
            "left_label": f"L{i}",
            "right_label": f"R{i}",
            "default_value": 30 + i * 8,
            "category": c,
            "source": "calibration",
        }
        for i, c in enumerate(["aesthetic", "experience", "functional", "technology", "resource", "special"])
    ]
    orch = RadarDimensionOrchestrator()
    with patch.object(
        orch, "_try_llm_generate", return_value={"success": False, "error": "timeout", "duration_ms": 0}
    ), patch.object(orch, "_semi_dynamic_fallback", return_value={"dimensions": []}), patch.object(
        orch, "_rule_engine_fallback", return_value=fake
    ), patch.object(
        orch, "_inject_scene_dimensions", side_effect=lambda s, d: d
    ):
        r = orch.orchestrate({"user_input": "test"})
    assert r["dimension_meta"]["degraded"] is True
    assert r["dimension_meta"]["generation_method"] == "rule_engine"
    assert r["dimension_meta"]["attempts"] == 3
    req = {"policy", "attempts", "degraded", "fallback_reason", "quality_score", "generation_method", "elapsed_ms"}
    missing = req - set(r["dimension_meta"].keys())
    assert not missing, f"meta missing: {missing}"
    print(f"       degraded=True  method=rule_engine  attempts=3  dims={len(r['dimensions'])}")


check("Orchestrator LLM全失败→规则引擎兜底，meta 字段完整", test_p1_fallback)


def test_p1_llm_success():
    from unittest.mock import patch
    from intelligent_project_analyzer.services.radar_dimension_orchestrator import RadarDimensionOrchestrator

    good = [
        {
            "id": f"d{i}",
            "name": f"n{i}",
            "left_label": f"L{i}",
            "right_label": f"R{i}",
            "default_value": 20 + i * 10,
            "category": c,
            "source": s,
        }
        for i, (c, s) in enumerate(
            [
                ("aesthetic", "calibration"),
                ("experience", "decision"),
                ("functional", "insight"),
                ("technology", "calibration"),
                ("resource", "decision"),
                ("special", "insight"),
            ]
        )
    ]
    orch = RadarDimensionOrchestrator()
    with patch.object(
        orch,
        "_try_llm_generate",
        return_value={"success": True, "dimensions": good, "generation_summary": "ok", "duration_ms": 800},
    ):
        r = orch.orchestrate({})
    assert r["dimension_meta"]["degraded"] is False
    assert r["dimension_meta"]["fallback_reason"] is None
    assert r["dimension_meta"]["attempts"] == 1
    print(f"       degraded=False  fallback_reason=None  quality={r['dimension_meta']['quality_score']:.3f}")


check("Orchestrator LLM成功→degraded=False fallback_reason=None", test_p1_llm_success)


def test_p1_timeout_override():
    from intelligent_project_analyzer.services.project_specific_dimension_generator import (
        ProjectSpecificDimensionGenerator,
    )

    g = ProjectSpecificDimensionGenerator(timeout_override=30)
    assert g is not None


check("ProjectSpecificDimensionGenerator(timeout_override=30) 正常构造", test_p1_timeout_override)

# ── P2: 接线 & 前端徽章 ───────────────────────────────────────
print("\n[P2] 可观测性接线")


def test_p2_backend():
    import pathlib, ast

    src = pathlib.Path("intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py").read_text(
        encoding="utf-8"
    )
    for kw in [
        "RadarDimensionOrchestrator",
        "orchestrate(",
        "dimension_meta",
        "radar_dimension_meta",
        "radar_generation_trace",
    ]:
        assert kw in src, f"missing keyword: {kw}"
    ast.parse(src)
    print("       语法 OK  接线字段 OK")


check("progressive_questionnaire 语法正确且接线字段完整", test_p2_backend)


def test_p2_frontend():
    import pathlib

    tsx = pathlib.Path("frontend-nextjs/components/UnifiedProgressiveQuestionnaireModal.tsx").read_text(
        encoding="utf-8"
    )
    assert "dimension_meta.degraded" in tsx, "frontend badge 未插入"
    assert "AI专属生成" in tsx, "AI专属生成 badge 未找到"
    assert "通用模板" in tsx, "通用模板 badge 未找到"
    assert "bg-green-100 text-green-700" in tsx, "green badge style 缺失"
    assert "bg-amber-100 text-amber-700" in tsx, "amber badge style 缺失"
    print("       dimension_meta.degraded ✓  AI专属生成 ✓  通用模板 ✓")


check("UnifiedProgressiveQuestionnaireModal.tsx 徽章代码已插入", test_p2_frontend)

# ── 汇总 ──────────────────────────────────────────────────────
print()
print("=" * 52)
passed = sum(1 for _, ok in results if ok)
total = len(results)
print(f"结果: {passed}/{total} 通过")
if passed == total:
    print("✅ 所有 v9.0 修复验证通过！")
    sys.exit(0)
else:
    failed = [n for n, ok in results if not ok]
    print(f"❌ 失败: {failed}")
    sys.exit(1)
