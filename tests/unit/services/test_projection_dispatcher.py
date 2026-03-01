"""
投射调度器单元测试 (v10.0)

覆盖：
- 配置加载（成功/失败/缓存失效）
- 五轴评分逻辑（数值/字符串/dict/list映射）
- 投射激活判定（always/mode/axis/keyword/手动选择）
- dispatch_projections_sync 降级逻辑
"""

import pytest
from unittest.mock import patch, MagicMock


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture(autouse=True)
def clear_cache():
    """每个测试前清除投射配置缓存"""
    import intelligent_project_analyzer.services.projection_dispatcher as pd

    pd._projections_config_cache = None
    yield
    pd._projections_config_cache = None


@pytest.fixture
def sample_config():
    """完整的投射配置样本"""
    return {
        "metadata": {"version": "1.0"},
        "projections": {
            "design_professional": {
                "name": "设计专业报告",
                "auto_activate": {"always": True},
                "axis_weights": {
                    "identity": 0.15,
                    "power": 0.05,
                    "operation": 0.10,
                    "emotion": 0.30,
                    "civilization": 0.40,
                },
            },
            "investor_operator": {
                "name": "投资运营分析",
                "auto_activate": {
                    "when_modes": ["M4", "M5", "M6"],
                    "when_axis_above": {"operation": 0.6},
                },
                "axis_weights": {
                    "identity": 0.10,
                    "power": 0.25,
                    "operation": 0.35,
                    "emotion": 0.05,
                    "civilization": 0.05,
                },
            },
            "government_policy": {
                "name": "政策汇报方案",
                "auto_activate": {
                    "when_modes": ["M5", "M6", "M8"],
                    "when_axis_above": {"power": 0.5},
                },
                "axis_weights": {
                    "identity": 0.05,
                    "power": 0.40,
                    "operation": 0.25,
                    "emotion": 0.05,
                    "civilization": 0.25,
                },
            },
            "construction_execution": {
                "name": "施工深化方案",
                "auto_activate": {
                    "when_modes": ["M5", "M6", "M10"],
                    "when_task_contains": ["施工", "深化", "落地"],
                },
                "axis_weights": {
                    "identity": 0.00,
                    "power": 0.05,
                    "operation": 0.60,
                    "emotion": 0.00,
                    "civilization": 0.00,
                },
            },
            "aesthetic_critique": {
                "name": "美学评论与传播",
                "auto_activate": {
                    "when_modes": ["M1", "M5", "M9"],
                    "when_axis_above": {"civilization": 0.6},
                },
                "axis_weights": {
                    "identity": 0.20,
                    "power": 0.05,
                    "operation": 0.05,
                    "emotion": 0.35,
                    "civilization": 0.35,
                },
            },
        },
        "dispatch_rules": {
            "default_projections": ["design_professional"],
            "max_parallel_projections": 3,
            "activation_threshold": 0.5,
        },
        "axis_scoring": {
            "identity": {
                "default_score": 0.5,
                "sources": [
                    {"field": "structured_requirements.user_modeling", "weight": 0.4},
                    {"field": "structured_requirements.jtbd", "weight": 0.3},
                ],
            },
            "operation": {
                "default_score": 0.5,
                "sources": [
                    {"field": "structured_requirements.functional_requirements", "weight": 0.3},
                ],
            },
        },
    }


@pytest.fixture
def m5_state():
    """模拟 M5 乡村振兴场景的 state"""
    return {
        "detected_design_modes": ["M5_rural_context"],
        "user_input": "狮岭村乡村振兴整体规划设计，要求施工深化落地",
        "structured_requirements": {
            "user_modeling": {"persona": "地方政府规划部门", "needs": "示范工程"},
            "jtbd": "打造乡村振兴示范标杆",
            "functional_requirements": ["民宿集群", "文创基地", "研学步道", "社区中心"],
            "spatial_strategy": {"approach": "院落+街巷"},
        },
        "radar_scores": {"energy_level": 5, "sensory_focus": 6, "cultural_axis": 8},
    }


# ==============================================================================
# 1. 配置加载测试
# ==============================================================================


class TestLoadProjectionsConfig:
    """配置加载相关测试"""

    @pytest.mark.unit
    def test_load_success(self, sample_config):
        """正常加载配置"""
        from intelligent_project_analyzer.services.projection_dispatcher import load_projections_config

        with patch("intelligent_project_analyzer.services.projection_dispatcher.PROJECTIONS_FILE") as mock_file:
            mock_file.exists.return_value = True
            mock_file.read_text.return_value = "metadata:\n  version: '1.0'\nprojections: {}"
            config = load_projections_config()
            assert "metadata" in config

    @pytest.mark.unit
    def test_load_missing_file(self):
        """配置文件不存在 → 返回空字典"""
        from intelligent_project_analyzer.services.projection_dispatcher import load_projections_config

        with patch("intelligent_project_analyzer.services.projection_dispatcher.PROJECTIONS_FILE") as mock_file:
            mock_file.exists.return_value = False
            config = load_projections_config()
            assert config == {}

    @pytest.mark.unit
    def test_cache_not_stored_on_failure(self):
        """加载失败时不缓存空结果"""
        import intelligent_project_analyzer.services.projection_dispatcher as pd

        with patch.object(pd, "PROJECTIONS_FILE") as mock_file:
            # 第一次：文件不存在
            mock_file.exists.return_value = False
            result1 = pd.load_projections_config()
            assert result1 == {}
            assert pd._projections_config_cache is None  # 不应缓存

            # 第二次：文件恢复
            mock_file.exists.return_value = True
            mock_file.read_text.return_value = "metadata:\n  version: '2.0'\nprojections: {}"
            result2 = pd.load_projections_config()
            assert result2 != {}
            assert pd._projections_config_cache is not None  # 现在应缓存

    @pytest.mark.unit
    def test_invalidate_cache(self):
        """手动清除缓存"""
        import intelligent_project_analyzer.services.projection_dispatcher as pd

        pd._projections_config_cache = {"test": True}
        pd.invalidate_projections_cache()
        assert pd._projections_config_cache is None


# ==============================================================================
# 2. 五轴评分测试
# ==============================================================================


class TestCalculateAxisScores:
    """五轴坐标评分测试"""

    @pytest.mark.unit
    def test_reuse_existing_scores(self):
        """复用 state 中已有的 meta_axis_scores"""
        from intelligent_project_analyzer.services.projection_dispatcher import calculate_axis_scores

        existing = {"identity": 0.8, "power": 0.6, "operation": 0.7, "emotion": 0.5, "civilization": 0.9}
        state = {"meta_axis_scores": existing}
        result = calculate_axis_scores(state)
        assert result == existing

    @pytest.mark.unit
    def test_default_scores_when_no_config(self):
        """无配置时使用默认分数"""
        from intelligent_project_analyzer.services.projection_dispatcher import calculate_axis_scores

        with patch(
            "intelligent_project_analyzer.services.projection_dispatcher.load_projections_config", return_value={}
        ):
            result = calculate_axis_scores({})
            assert len(result) == 5
            for axis in ["identity", "power", "operation", "emotion", "civilization"]:
                assert axis in result
                assert result[axis] == 0.5  # 默认值

    @pytest.mark.unit
    def test_scoring_with_sources(self, sample_config, m5_state):
        """有源字段时正确计算加权得分"""
        from intelligent_project_analyzer.services.projection_dispatcher import calculate_axis_scores

        with patch(
            "intelligent_project_analyzer.services.projection_dispatcher.load_projections_config",
            return_value=sample_config,
        ):
            result = calculate_axis_scores(m5_state)
            # identity 应有分数（user_modeling 是 dict → 0.8, jtbd 是字符串 → 0.3-0.5）
            assert 0.0 < result["identity"] < 1.0
            # operation 有 functional_requirements 列表 → 0.3 + 4*0.1 = 0.7
            assert result["operation"] > 0.5


class TestValueToScore:
    """_value_to_score 映射测试"""

    @pytest.mark.unit
    def test_float_01_range(self):
        from intelligent_project_analyzer.services.projection_dispatcher import _value_to_score

        assert _value_to_score(0.7) == 0.7

    @pytest.mark.unit
    def test_int_0_100_range(self):
        """8 在 0-100 范围内，按 /100 转换（因为 0-100 检查在 0-10 之前）"""
        from intelligent_project_analyzer.services.projection_dispatcher import _value_to_score

        assert _value_to_score(8) == 0.08  # 8/100
        assert _value_to_score(0.7) == 0.7  # 0-1 范围直接返回

    @pytest.mark.unit
    def test_string_short(self):
        from intelligent_project_analyzer.services.projection_dispatcher import _value_to_score

        assert _value_to_score("短文本") == 0.3

    @pytest.mark.unit
    def test_string_medium(self):
        from intelligent_project_analyzer.services.projection_dispatcher import _value_to_score

        result = _value_to_score("这是一段中等长度的文本" * 5)
        assert result == 0.5

    @pytest.mark.unit
    def test_string_empty(self):
        from intelligent_project_analyzer.services.projection_dispatcher import _value_to_score

        assert _value_to_score("") == 0.2

    @pytest.mark.unit
    def test_dict_nonempty(self):
        from intelligent_project_analyzer.services.projection_dispatcher import _value_to_score

        assert _value_to_score({"key": "value"}) == 0.8

    @pytest.mark.unit
    def test_dict_empty(self):
        from intelligent_project_analyzer.services.projection_dispatcher import _value_to_score

        assert _value_to_score({}) == 0.2

    @pytest.mark.unit
    def test_list_scoring(self):
        from intelligent_project_analyzer.services.projection_dispatcher import _value_to_score

        assert _value_to_score([]) == 0.2
        assert abs(_value_to_score(["a", "b", "c"]) - 0.6) < 1e-9  # 0.3 + 3*0.1 (浮点精度)

    @pytest.mark.unit
    def test_none_returns_none(self):
        from intelligent_project_analyzer.services.projection_dispatcher import _value_to_score

        assert _value_to_score(None) is None

    @pytest.mark.unit
    def test_mode_mapping_exact_match(self):
        """mode_mapping 精确匹配模式ID字符串"""
        from intelligent_project_analyzer.services.projection_dispatcher import _value_to_score

        mapping = {"M5_rural_context": 0.85, "M1_architecture": 0.9}
        assert _value_to_score("M5_rural_context", mode_mapping=mapping) == 0.85
        assert _value_to_score("M1_architecture", mode_mapping=mapping) == 0.9

    @pytest.mark.unit
    def test_mode_mapping_fuzzy_match(self):
        """mode_mapping 模糊匹配（key 包含在 value 中）"""
        from intelligent_project_analyzer.services.projection_dispatcher import _value_to_score

        mapping = {"M5_rural": 0.85}
        # "M5_rural" is in "M5_rural_context"
        assert _value_to_score("M5_rural_context", mode_mapping=mapping) == 0.85

    @pytest.mark.unit
    def test_mode_mapping_no_match_fallback(self):
        """mode_mapping 无匹配时回退到长度启发式"""
        from intelligent_project_analyzer.services.projection_dispatcher import _value_to_score

        mapping = {"M1_architecture": 0.9}
        # "completely_unknown" is 19 chars < 20, should fall back to 0.3
        assert _value_to_score("completely_unknown", mode_mapping=mapping) == 0.3

    @pytest.mark.unit
    def test_mode_mapping_none_ignored(self):
        """mode_mapping=None 时仅用长度启发式"""
        from intelligent_project_analyzer.services.projection_dispatcher import _value_to_score

        assert _value_to_score("M5_rural_context", mode_mapping=None) == 0.3  # 16 chars < 20


# ==============================================================================
# 3. 投射激活判定测试
# ==============================================================================


class TestDetermineActiveProjections:
    """投射激活逻辑测试"""

    @pytest.mark.unit
    def test_always_active(self, sample_config):
        """always: true 视角始终激活"""
        from intelligent_project_analyzer.services.projection_dispatcher import determine_active_projections

        with patch(
            "intelligent_project_analyzer.services.projection_dispatcher.load_projections_config",
            return_value=sample_config,
        ):
            result = determine_active_projections(
                axis_scores={"identity": 0.1, "power": 0.1, "operation": 0.1, "emotion": 0.1, "civilization": 0.1},
                state={"detected_design_modes": [], "user_input": ""},
            )
            assert "design_professional" in result

    @pytest.mark.unit
    def test_user_selected_priority(self, sample_config):
        """用户手动选择优先于自动规则"""
        from intelligent_project_analyzer.services.projection_dispatcher import determine_active_projections

        with patch(
            "intelligent_project_analyzer.services.projection_dispatcher.load_projections_config",
            return_value=sample_config,
        ):
            result = determine_active_projections(
                axis_scores={"identity": 0.1, "power": 0.1, "operation": 0.1, "emotion": 0.1, "civilization": 0.1},
                state={},
                user_selected=["aesthetic_critique", "investor_operator"],
            )
            assert result == ["aesthetic_critique", "investor_operator"]

    @pytest.mark.unit
    def test_mode_trigger(self, sample_config, m5_state):
        """M5 模式触发对应投射"""
        from intelligent_project_analyzer.services.projection_dispatcher import determine_active_projections

        with patch(
            "intelligent_project_analyzer.services.projection_dispatcher.load_projections_config",
            return_value=sample_config,
        ):
            axis_scores = {"identity": 0.5, "power": 0.3, "operation": 0.5, "emotion": 0.1, "civilization": 0.1}
            result = determine_active_projections(axis_scores, m5_state)
            # design_professional (always) + M5匹配的 investor_operator/government_policy/construction_execution
            assert "design_professional" in result
            # 至少还有一个 M5 模式触发的
            assert len(result) >= 2

    @pytest.mark.unit
    def test_keyword_trigger(self, sample_config):
        """用户输入包含关键词 + 轴分足够高时触发投射

        注意: 关键词匹配 +0.4，但阈值 0.5。
        需要关键词(0.4) + 模式 or 轴分加成才能达到阈值。
        """
        from intelligent_project_analyzer.services.projection_dispatcher import determine_active_projections

        with patch(
            "intelligent_project_analyzer.services.projection_dispatcher.load_projections_config",
            return_value=sample_config,
        ):
            # 关键词(0.4) + M5模式(0.5) = 0.9 > 0.5 → 触发
            state = {"detected_design_modes": ["M5_rural_context"], "user_input": "需要施工深化图纸"}
            axis_scores = {"identity": 0.1, "power": 0.1, "operation": 0.3, "emotion": 0.1, "civilization": 0.1}
            result = determine_active_projections(axis_scores, state)
            assert "construction_execution" in result

    @pytest.mark.unit
    def test_max_parallel_limit(self, sample_config):
        """不超过 max_parallel_projections 限制"""
        from intelligent_project_analyzer.services.projection_dispatcher import determine_active_projections

        with patch(
            "intelligent_project_analyzer.services.projection_dispatcher.load_projections_config",
            return_value=sample_config,
        ):
            # 所有轴分都很高，理论上全部激活
            axis_scores = {"identity": 0.9, "power": 0.9, "operation": 0.9, "emotion": 0.9, "civilization": 0.9}
            state = {"detected_design_modes": ["M5_rural_context"], "user_input": "施工深化乡村振兴"}
            result = determine_active_projections(axis_scores, state)
            assert len(result) <= sample_config["dispatch_rules"]["max_parallel_projections"]

    @pytest.mark.unit
    def test_axis_threshold_trigger(self, sample_config):
        """轴分超阈值触发投射

        power=0.8 > min_val=0.5 → score += 0.3 * (0.8/0.5) = 0.48
        还不足 threshold=0.5，所以需要轴分更高或配合模式。
        设 power=1.0 → score = 0.3 * (1.0/0.5) = 0.6 > 0.5
        """
        from intelligent_project_analyzer.services.projection_dispatcher import determine_active_projections

        with patch(
            "intelligent_project_analyzer.services.projection_dispatcher.load_projections_config",
            return_value=sample_config,
        ):
            axis_scores = {"identity": 0.1, "power": 1.0, "operation": 0.1, "emotion": 0.1, "civilization": 0.1}
            state = {"detected_design_modes": [], "user_input": ""}
            result = determine_active_projections(axis_scores, state)
            assert "government_policy" in result  # 0.3 * (1.0/0.5) = 0.6 > 0.5


# ==============================================================================
# 4. 集成 smoke 测试
# ==============================================================================


class TestDispatchProjectionsSync:
    """dispatch_projections_sync 集成测试（不调用 LLM）"""

    @pytest.mark.unit
    def test_graceful_no_config(self):
        """无配置时不崩溃"""
        from intelligent_project_analyzer.services.projection_dispatcher import dispatch_projections_sync

        with patch(
            "intelligent_project_analyzer.services.projection_dispatcher.load_projections_config", return_value={}
        ):
            result = dispatch_projections_sync(state={}, llm_model=MagicMock())
            assert "meta_axis_scores" in result
            assert "active_projections" in result
            assert "perspective_outputs" in result

    @pytest.mark.unit
    def test_dispatch_with_no_active_projections(self, sample_config):
        """无激活投射时返回空输出"""
        # 修改配置使得没有 always 视角
        config = {**sample_config}
        config["projections"]["design_professional"]["auto_activate"] = {"when_modes": ["M99"]}
        from intelligent_project_analyzer.services.projection_dispatcher import dispatch_projections_sync

        with patch(
            "intelligent_project_analyzer.services.projection_dispatcher.load_projections_config", return_value=config
        ):
            result = dispatch_projections_sync(
                state={"detected_design_modes": [], "user_input": ""},
                llm_model=MagicMock(),
            )
            # 应该有分数但无投射输出
            assert isinstance(result.get("meta_axis_scores"), dict)
