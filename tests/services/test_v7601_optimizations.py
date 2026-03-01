"""
v7.601 需求分析师优化测试

覆盖范围:
1. 共享工具模块 (requirements_analyst_utils.py)
2. V2 StateGraph 新增 post_process 节点
3. Phase1 Structured Output
4. 增强型项目类型推断
5. 加权置信度公式
6. 增强 Fallback
7. 降级监控指标
8. 边界场景测试
9. LLM 集成测试标记

pytest markers:
- unit: 纯逻辑单元测试（不需要 LLM）
- integration: 依赖外部服务的集成测试
- llm: 需要真实 LLM API 的端到端测试
"""

import json
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# C-05: requirements_analyst_utils.py 已确认为死代码（V1/V2均未导入），已删除。
# 依赖该模块的测试类用 skip 标记，待迁移到对应的实际模块后恢复。
try:
    from intelligent_project_analyzer.agents.requirements_analyst_utils import (
        StructuredOutputMetrics,
        metrics,
        parse_json_response,
        infer_project_type,
        calculate_confidence,
        normalize_jtbd_fields,
        extract_keywords_from_input,
        build_enhanced_fallback,
        merge_phase_results,
        build_phase1_only_result,
    )

    _UTILS_AVAILABLE = True
except ImportError:
    _UTILS_AVAILABLE = False
    # 提供占位符避免NameError
    StructuredOutputMetrics = metrics = parse_json_response = infer_project_type = None
    calculate_confidence = normalize_jtbd_fields = extract_keywords_from_input = None
    build_enhanced_fallback = merge_phase_results = build_phase1_only_result = None

_skip_utils = pytest.mark.skipif(not _UTILS_AVAILABLE, reason="requirements_analyst_utils 已删除，相关测试待迁移")
from intelligent_project_analyzer.agents.requirements_analyst_agent import (
    RequirementsAnalystAgentV2,
    build_requirements_analyst_graph,
    precheck_node,
    should_execute_phase2,
    output_node,
)
from intelligent_project_analyzer.agents.requirements_analyst_schema import (
    Phase1Output,
    CoreTension,
    LensCategory,
    Phase1Deliverable,
    DeliverableTypeEnum,
    DeliverablePriorityEnum,
    DeliverableOwnerSuggestion,
    CapabilityCheck,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. 共享工具模块测试
# ═══════════════════════════════════════════════════════════════════════════════


@_skip_utils
class TestJsonParsing:
    """JSON 解析测试（4 层 fallback）"""

    @pytest.mark.unit
    def test_parse_code_fence(self):
        """测试 code fence 格式解析"""
        response = '这是分析结果:\n```json\n{"project_task": "设计住宅"}\n```\n完成。'
        result = parse_json_response(response)
        assert result["project_task"] == "设计住宅"

    @pytest.mark.unit
    def test_parse_bare_code_block(self):
        """测试无标记代码块解析"""
        response = '分析:\n```\n{"info_status": "sufficient"}\n```'
        result = parse_json_response(response)
        assert result["info_status"] == "sufficient"

    @pytest.mark.unit
    def test_parse_balanced_braces(self):
        """测试平衡括号栈匹配"""
        response = '输出: {"nested": {"key": "value"}, "list": [1, 2]}'
        result = parse_json_response(response)
        assert result["nested"]["key"] == "value"

    @pytest.mark.unit
    def test_parse_first_last_brace(self):
        """测试首尾大括号提取"""
        response = '开始 {"simple": true} 结束文本不影响'
        result = parse_json_response(response)
        assert result["simple"] is True

    @pytest.mark.unit
    def test_parse_no_json_raises(self):
        """测试无 JSON 时抛出 ValueError"""
        response = "这是一段没有任何JSON的纯文本"
        with pytest.raises(ValueError, match="无法从 LLM 响应中提取有效 JSON"):
            parse_json_response(response)

    @pytest.mark.unit
    def test_parse_empty_string_raises(self):
        """测试空字符串"""
        with pytest.raises(ValueError):
            parse_json_response("")

    @pytest.mark.unit
    def test_parse_malformed_json(self):
        """测试畸形 JSON（括号不平衡）"""
        response = '{"key": "value", "broken'
        with pytest.raises(ValueError):
            parse_json_response(response)

    @pytest.mark.unit
    def test_parse_deeply_nested(self):
        """测试深层嵌套 JSON"""
        deep = {"a": {"b": {"c": {"d": "deep_value"}}}}
        response = f"结果: {json.dumps(deep)}"
        result = parse_json_response(response)
        assert result["a"]["b"]["c"]["d"] == "deep_value"


@_skip_utils
class TestProjectTypeInference:
    """项目类型推断测试（增强版加权）"""

    @pytest.mark.unit
    def test_personal_residential(self):
        """测试住宅类型识别"""
        data = {"project_task": "75平米公寓装修，两室一厅，住宅"}
        assert infer_project_type(data) == "personal_residential"

    @pytest.mark.unit
    def test_commercial_enterprise(self):
        """测试商业类型识别"""
        data = {"project_task": "500平米办公空间，商业写字楼"}
        assert infer_project_type(data) == "commercial_enterprise"

    @pytest.mark.unit
    def test_hybrid_type(self):
        """测试混合类型（住宅+商业）"""
        data = {"project_task": "一楼商铺二楼住宅的复合公寓装修"}
        result = infer_project_type(data)
        assert result == "hybrid_residential_commercial"

    @pytest.mark.unit
    def test_cultural_educational(self):
        """测试文化教育类型"""
        data = {"project_task": "建设一座社区图书馆"}
        assert infer_project_type(data) == "cultural_educational"

    @pytest.mark.unit
    def test_healthcare_wellness(self):
        """测试医疗健康类型"""
        data = {"project_task": "高端养老院康复中心设计"}
        assert infer_project_type(data) == "healthcare_wellness"

    @pytest.mark.unit
    def test_hospitality(self):
        """测试民宿旅游类型（不再误判为住宅+商业混合）"""
        data = {"project_task": "山间民宿度假村设计"}
        result = infer_project_type(data)
        assert result == "hospitality_tourism"

    @pytest.mark.unit
    def test_no_match(self):
        """测试无法匹配时返回 None"""
        data = {"project_task": "这是一段完全无关的文字"}
        assert infer_project_type(data) is None

    @pytest.mark.unit
    def test_threshold(self):
        """测试阈值：单个弱关键词不触发"""
        data = {"project_task": "简单的书房设计"}  # "书房" weight=0.8, < threshold 2.0
        # 只有 "书房" 出现，weight=0.8 < 2.0
        result = infer_project_type(data)
        assert result is None


@_skip_utils
class TestConfidenceCalculation:
    """加权置信度计算测试"""

    @pytest.mark.unit
    def test_phase1_only_baseline(self):
        """Phase1 only 的基础置信度"""
        result = calculate_confidence({"info_status": "insufficient"})
        assert result == 0.30  # 基础分

    @pytest.mark.unit
    def test_phase1_sufficient(self):
        """Phase1 信息充足的置信度"""
        result = calculate_confidence(
            {"info_status": "sufficient", "primary_deliverables": [{"id": "D1"}, {"id": "D2"}]}
        )
        assert result == 0.55  # 0.30 + 0.15 + 0.10

    @pytest.mark.unit
    def test_two_phase_full(self):
        """两阶段完整分析的置信度"""
        phase1 = {"info_status": "sufficient", "primary_deliverables": [{"id": "D1"}, {"id": "D2"}]}
        phase2 = {
            "analysis_layers": {"L5_sharpness": {"score": 80}},
            "expert_handoff": {"critical_questions_for_experts": ["Q1"]},
        }
        result = calculate_confidence(phase1, phase2, entities_count=5, motivation_confidence=0.8)
        # 0.30 + 0.15 + 0.10 + 0.15 + 80/500=0.16 + 0.05 + 0.0125 + 0.04 = 0.9625
        assert 0.90 <= result <= 1.0

    @pytest.mark.unit
    def test_confidence_cap_at_1(self):
        """置信度不超过 1.0"""
        phase1 = {"info_status": "sufficient", "primary_deliverables": [{"id": "D1"}, {"id": "D2"}]}
        phase2 = {
            "analysis_layers": {"L5_sharpness": {"score": 100}},
            "expert_handoff": {"critical_questions_for_experts": ["Q1"]},
        }
        result = calculate_confidence(phase1, phase2, entities_count=50, motivation_confidence=1.0)
        assert result <= 1.0


@_skip_utils
class TestKeywordExtraction:
    """关键词提取测试"""

    @pytest.mark.unit
    def test_extract_area(self):
        """测试面积提取"""
        keywords = extract_keywords_from_input("150平米的住宅")
        assert any("面积:150" in kw for kw in keywords)

    @pytest.mark.unit
    def test_extract_style(self):
        """测试风格提取"""
        keywords = extract_keywords_from_input("现代简约风格的客厅")
        styles = [kw for kw in keywords if kw.startswith("风格:")]
        assert len(styles) >= 1

    @pytest.mark.unit
    def test_extract_budget(self):
        """测试预算提取"""
        keywords = extract_keywords_from_input("预算30万装修")
        assert any("预算:30" in kw for kw in keywords)

    @pytest.mark.unit
    def test_extract_multiple(self):
        """测试多要素提取"""
        text = "120平米现代简约别墅，预算50万，3口人居住"
        keywords = extract_keywords_from_input(text)
        assert len(keywords) >= 3

    @pytest.mark.unit
    def test_extract_empty(self):
        """测试空输入"""
        keywords = extract_keywords_from_input("这是一段普通文字")
        assert len(keywords) == 0


@_skip_utils
class TestEnhancedFallback:
    """增强 Fallback 输出测试"""

    @pytest.mark.unit
    def test_phase1_fallback_extracts_info(self):
        """Phase1 fallback 应从输入中提取信息"""
        result = build_enhanced_fallback("150平米现代简约住宅设计", phase=1)
        assert result["fallback"] is True
        assert result["phase"] == 1
        assert len(result.get("extracted_keywords", [])) >= 2
        assert "平米" in result.get("project_summary", "") or "150" in result.get("project_summary", "")

    @pytest.mark.unit
    def test_phase2_fallback_uses_keywords(self):
        """Phase2 fallback 应利用关键词改善输出"""
        result = build_enhanced_fallback("120平米日式客厅设计，预算20万", phase=2)
        assert result["fallback"] is True
        assert result["phase"] == 2
        layers = result["analysis_layers"]
        assert layers["L5_sharpness"]["score"] > 40  # 有关键词应加分

    @pytest.mark.unit
    def test_fallback_minimal_input(self):
        """极少信息的 fallback"""
        result = build_enhanced_fallback("设计", phase=1)
        assert result["fallback"] is True
        assert len(result["primary_deliverables"]) >= 1


@_skip_utils
class TestMergeResults:
    """结果合并测试"""

    @pytest.mark.unit
    def test_merge_basic(self):
        """基础合并"""
        phase1 = {"primary_deliverables": [{"id": "D1"}], "info_status": "sufficient"}
        phase2 = {"structured_output": {"project_task": "任务A", "character_narrative": "角色B"}}
        result = merge_phase_results(phase1, phase2, "输入")
        assert result["project_task"] == "任务A"
        assert result["info_status"] == "sufficient"
        assert len(result["primary_deliverables"]) == 1

    @pytest.mark.unit
    def test_phase1_only_result(self):
        """仅 Phase1 结果"""
        phase1 = {"project_summary": "某住宅项目", "info_status": "insufficient"}
        result = build_phase1_only_result(phase1, "用户输入")
        assert result["project_task"] == "某住宅项目"
        assert result["character_narrative"] == "待问卷补充后分析"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. 降级监控指标测试
# ═══════════════════════════════════════════════════════════════════════════════


@_skip_utils
class TestStructuredOutputMetrics:
    """降级监控指标测试"""

    @pytest.mark.unit
    def test_singleton(self):
        """测试单例模式"""
        m1 = StructuredOutputMetrics()
        m2 = StructuredOutputMetrics()
        assert m1 is m2

    @pytest.mark.unit
    def test_record_and_report(self):
        """测试记录和报告"""
        metrics.reset()
        metrics.record_phase1(True)
        metrics.record_phase1(True)
        metrics.record_phase1(False)
        metrics.record_phase2(True)

        report = metrics.get_report()
        assert report["phase1"]["success"] == 2
        assert report["phase1"]["degraded"] == 1
        assert report["phase1"]["total"] == 3
        assert abs(report["phase1"]["pass_rate"] - 2 / 3) < 0.01
        assert report["phase2"]["success"] == 1

    @pytest.mark.unit
    def test_json_parse_methods(self):
        """测试 JSON 解析方法记录"""
        metrics.reset()
        metrics.record_json_parse_method("code_fence")
        metrics.record_json_parse_method("code_fence")
        metrics.record_json_parse_method("balanced_braces")

        report = metrics.get_report()
        assert report["json_parse_methods"]["code_fence"] == 2
        assert report["json_parse_methods"]["balanced_braces"] == 1

    @pytest.mark.unit
    def test_fallback_count(self):
        """测试 fallback 计数"""
        metrics.reset()
        metrics.record_fallback()
        metrics.record_fallback()
        assert metrics.get_report()["fallback_count"] == 2


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Schema 验证测试
# ═══════════════════════════════════════════════════════════════════════════════


class TestPhase1Schema:
    """Phase1Output Schema 验证"""

    @pytest.mark.unit
    def test_valid_phase1_output(self):
        """测试合法的 Phase1 输出"""
        output = Phase1Output(
            info_status="sufficient",
            info_status_reason="用户已提供了完整的面积、风格偏好、预算等核心关键信息",
            project_type_preliminary="personal_residential",
            project_summary="75平米现代简约公寓装修，预算30万，两室一厅，年轻夫妻居住",
            primary_deliverables=[
                Phase1Deliverable(
                    deliverable_id="D1",
                    type=DeliverableTypeEnum.DESIGN_STRATEGY,
                    description="整体空间设计策略（含功能分区和风格定调）",
                    priority=DeliverablePriorityEnum.MUST_HAVE,
                    acceptance_criteria=["必须覆盖客厅、卧室、厨房三个核心空间"],
                    deliverable_owner_suggestion=DeliverableOwnerSuggestion(
                        primary_owner="V2_设计总监_2-2",
                        owner_rationale="整体空间策略需要设计总监统筹协调",
                    ),
                    capability_check=CapabilityCheck(within_capability=True),
                )
            ],
            recommended_next_step="phase2_analysis",
            next_step_reason="用户信息充足且完整，可以直接进入Phase2深度分析阶段",
        )
        assert output.info_status == "sufficient"
        assert len(output.primary_deliverables) == 1

    @pytest.mark.unit
    def test_insufficient_must_recommend_questionnaire(self):
        """信息不足时必须推荐问卷"""
        with pytest.raises(Exception):
            Phase1Output(
                info_status="insufficient",
                info_status_reason="缺少面积和预算等关键信息无法进行深度分析",
                project_type_preliminary="personal_residential",
                project_summary="用户想要设计一个舒适的住宅空间但信息不足",
                primary_deliverables=[
                    Phase1Deliverable(
                        deliverable_id="D1",
                        type=DeliverableTypeEnum.DESIGN_STRATEGY,
                        description="整体空间设计策略",
                        priority=DeliverablePriorityEnum.MUST_HAVE,
                        acceptance_criteria=["必须覆盖核心空间"],
                        deliverable_owner_suggestion=DeliverableOwnerSuggestion(
                            primary_owner="V2_设计总监",
                            owner_rationale="需要设计总监统筹",
                        ),
                        capability_check=CapabilityCheck(within_capability=True),
                    )
                ],
                recommended_next_step="phase2_analysis",  # ❌ 不足时不应推荐phase2
                next_step_reason="信息不足但仍然尝试分析",
            )

    @pytest.mark.unit
    def test_must_have_at_least_one_must_have(self):
        """至少需要一个 MUST_HAVE 交付物"""
        with pytest.raises(Exception):
            Phase1Output(
                info_status="sufficient",
                info_status_reason="信息充足足以进行深度分析",
                project_type_preliminary="personal_residential",
                project_summary="75平米简约公寓设计项目已提供足够信息",
                primary_deliverables=[
                    Phase1Deliverable(
                        deliverable_id="D1",
                        type=DeliverableTypeEnum.DESIGN_STRATEGY,
                        description="可选设计参考报告",
                        priority=DeliverablePriorityEnum.NICE_TO_HAVE,  # ❌ 没有 MUST_HAVE
                        acceptance_criteria=["必须包含至少3个方案"],
                        deliverable_owner_suggestion=DeliverableOwnerSuggestion(
                            primary_owner="V2_设计总监",
                            owner_rationale="需要设计总监统筹",
                        ),
                        capability_check=CapabilityCheck(within_capability=True),
                    )
                ],
                recommended_next_step="phase2_analysis",
                next_step_reason="可以进行深度分析",
            )


class TestCoreTensionSchema:
    """CoreTension Schema 验证"""

    @pytest.mark.unit
    def test_hallucinated_theory_rejected(self):
        """幻觉理论应被拒绝"""
        with pytest.raises(Exception):
            CoreTension(
                name="虚拟vs现实",
                theory_source="Postmodern_Deconstruction",  # ❌ 不在清单
                lens_category=LensCategory.CULTURAL_STUDIES,
                description="测试描述测试描述测试描述测试描述",
                design_implication="测试启示测试启示测试启示测试启示",
            )

    @pytest.mark.unit
    def test_theory_lens_mismatch_rejected(self):
        """理论与透镜类别不匹配应被拒绝"""
        with pytest.raises(Exception):
            CoreTension(
                name="安全需求vs自由需求",
                theory_source="Maslow_Hierarchy",  # Psychology
                lens_category=LensCategory.SOCIOLOGY,  # ❌ 错误类别
                description="马斯洛层次测试描述内容足够长度",
                design_implication="设计启示测试内容确保足够长度",
            )

    @pytest.mark.unit
    def test_valid_tension(self):
        """合法的核心张力"""
        tension = CoreTension(
            name="公共展示 vs 私密避难",
            theory_source="Goffman_Front_Back_Stage",
            lens_category=LensCategory.SOCIOLOGY,
            description="戈夫曼前后台理论在空间设计中的张力，玄关作为角色转换区",
            design_implication="设计独立玄关区域，实现工作-家庭身份过渡仪式",
        )
        assert tension.theory_source == "Goffman_Front_Back_Stage"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. V2 StateGraph 结构测试
# ═══════════════════════════════════════════════════════════════════════════════


class TestV2GraphStructure:
    """V2 StateGraph 结构验证"""

    @pytest.mark.unit
    def test_graph_node_count(self):
        """v7.601: 应有 4 个节点（precheck/phase1/phase2/output）"""
        graph = build_requirements_analyst_graph()
        nodes = list(graph.nodes.keys())
        expected = {"precheck", "phase1", "phase2", "output"}
        assert set(nodes) == expected, f"节点不匹配: 期望 {expected}, 实际 {set(nodes)}"

    @pytest.mark.unit
    def test_graph_compiles(self):
        """图应能成功编译"""
        graph = build_requirements_analyst_graph()
        compiled = graph.compile()
        assert compiled is not None


class TestPrecheckNode:
    """Precheck 节点测试"""

    @pytest.mark.unit
    def test_sufficient_input(self):
        """信息充足的输入"""
        state = {
            "user_input": "我是一位32岁的前金融律师，有一套75平米的公寓，预算60万，希望现代简约风格",
            "session_id": "test-001",
            "processing_log": [],
            "node_path": [],
        }
        result = precheck_node(state)
        assert "precheck_result" in result
        assert result["precheck_elapsed_ms"] > 0
        assert "precheck" in result["node_path"]

    @pytest.mark.unit
    def test_insufficient_input(self):
        """信息不足的输入"""
        state = {
            "user_input": "帮我设计一下房子",
            "session_id": "test-002",
            "processing_log": [],
            "node_path": [],
        }
        result = precheck_node(state)
        assert result["info_sufficient"] is False


class TestConditionalRouting:
    """条件路由测试"""

    @pytest.mark.unit
    def test_sufficient_goes_to_phase2(self):
        """信息充足应进入 Phase2"""
        state = {"phase1_info_status": "sufficient", "recommended_next_step": "phase2_analysis"}
        assert should_execute_phase2(state) == "phase2"

    @pytest.mark.unit
    def test_insufficient_still_executes_phase2(self):
        """v7.621: 信息不足也执行 Phase2"""
        state = {"phase1_info_status": "insufficient", "recommended_next_step": "questionnaire_first"}
        assert should_execute_phase2(state) == "phase2"

    @pytest.mark.unit
    def test_questionnaire_first_still_executes_phase2(self):
        """v7.621: 推荐问卷时也执行 Phase2"""
        state = {"phase1_info_status": "sufficient", "recommended_next_step": "questionnaire_first"}
        assert should_execute_phase2(state) == "phase2"


# post_process_node 已合并到 output_node 中，相关测试已移除


class TestOutputNode:
    """Output 节点测试"""

    @pytest.mark.unit
    def test_phase1_only_output(self):
        """Phase1 only 输出"""
        state = {
            "user_input": "设计住宅",
            "phase1_result": {"project_summary": "住宅设计", "info_status": "insufficient"},
            "phase2_result": {},
            "precheck_elapsed_ms": 5,
            "phase1_elapsed_ms": 100,
            "processing_log": [],
            "node_path": [],
        }
        result = output_node(state)
        assert result["analysis_mode"] == "phase1_only"
        assert result["confidence"] == 0.5  # v7.621: phase1_only 置信度为 0.5

    @pytest.mark.unit
    def test_two_phase_output_with_metrics(self):
        """两阶段输出应包含监控指标"""
        state = {
            "user_input": "150平米公寓设计",
            "phase1_result": {
                "info_status": "sufficient",
                "primary_deliverables": [{"id": "D1"}],
            },
            "phase2_result": {
                "structured_output": {"project_task": "公寓设计", "character_narrative": "用户"},
                "analysis_layers": {"L5_sharpness": {"score": 70}},
                "expert_handoff": {},
            },
            "post_process_entities": {},
            "post_process_motivation": {"confidence": 0.7},
            "post_process_validation": {"is_valid": True},
            "precheck_elapsed_ms": 5,
            "phase1_elapsed_ms": 100,
            "phase2_elapsed_ms": 200,
            "post_process_elapsed_ms": 50,
            "processing_log": [],
            "node_path": [],
        }
        result = output_node(state)
        assert result["analysis_mode"] == "two_phase"
        assert result["confidence"] > 0.5


# ═══════════════════════════════════════════════════════════════════════════════
# 5. 边界场景测试
# ═══════════════════════════════════════════════════════════════════════════════


class TestBoundaryScenarios:
    """边界场景测试"""

    @pytest.mark.unit
    def test_empty_input_precheck(self):
        """空输入不应崩溃"""
        state = {"user_input": "", "session_id": "test", "processing_log": [], "node_path": []}
        result = precheck_node(state)
        assert "precheck_result" in result

    @pytest.mark.unit
    def test_very_long_input_precheck(self):
        """超长输入不应崩溃"""
        state = {
            "user_input": "设计" * 5000,  # 10000 字符
            "session_id": "test",
            "processing_log": [],
            "node_path": [],
        }
        result = precheck_node(state)
        assert "precheck_result" in result

    @pytest.mark.unit
    @_skip_utils
    def test_unicode_input(self):
        """Unicode 特殊字符"""
        keywords = extract_keywords_from_input("150㎡的loft风格🏠设计")
        assert any("面积" in kw for kw in keywords)

    @pytest.mark.unit
    @_skip_utils
    def test_json_with_unicode_escape(self):
        """含 Unicode 转义的 JSON"""
        response = '{"task": "\\u8bbe\\u8ba1"}'
        result = parse_json_response(response)
        assert result["task"] == "设计"

    @pytest.mark.unit
    @_skip_utils
    def test_metrics_thread_safety_basic(self):
        """指标基本一致性"""
        metrics.reset()
        for _ in range(100):
            metrics.record_phase1(True)
        assert metrics.get_report()["phase1"]["success"] == 100


# ═══════════════════════════════════════════════════════════════════════════════
# 6. LLM 集成测试（需要真实 API Key）
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.llm
class TestLLMIntegration:
    """
    LLM 集成测试

    需要环境变量 OPENAI_API_KEY
    运行: python -m pytest tests/test_v7601_optimizations.py -m llm -v
    """

    @pytest.fixture(autouse=True)
    def check_api_key(self):
        """跳过没有 API Key 的环境"""
        if not os.environ.get("OPENAI_API_KEY"):
            pytest.skip("需要 OPENAI_API_KEY 环境变量")

    def test_v2_full_flow(self):
        """V2 完整流程端到端测试"""
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        agent = RequirementsAnalystAgentV2(llm_model=llm)

        result = agent.execute(
            user_input="我是一位32岁的科技公司产品经理，刚购入一套89平米的两室一厅公寓，" "预算35万，希望打造现代北欧极简风格，注重收纳和在家办公功能",
            session_id="llm-test-001",
        )

        assert result is not None
        assert result.structured_data is not None
        assert result.confidence > 0.3
        # 检查结构化数据完整性
        sd = result.structured_data
        assert sd.get("project_type") is not None
        assert sd.get("analysis_mode") in ("phase1_only", "two_phase")

    def test_v2_insufficient_flow(self):
        """V2 信息不足流程测试"""
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        agent = RequirementsAnalystAgentV2(llm_model=llm)

        result = agent.execute(
            user_input="帮我设计一下房子",
            session_id="llm-test-002",
        )

        assert result is not None
        sd = result.structured_data
        # 信息不足应该是 phase1_only
        assert sd.get("analysis_mode") == "phase1_only"


# ═══════════════════════════════════════════════════════════════════════════════
# 程序入口
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "unit", "--tb=short"])
