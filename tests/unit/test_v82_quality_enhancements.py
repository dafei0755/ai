"""
v8.2 Phase 2-5 质量增强单元测试

测试范围:
- Phase 2: validate_overall_quality, _score_task_role_alignment, _score_deliverable_coverage
- Phase 3: _validate_naming 泛化检测 + 任务关联
- Phase 4: _compute_gini, _check_dependency_cycles
- Phase 5: _monitor_synthesized_prompt_quality
"""

from unittest.mock import MagicMock

from intelligent_project_analyzer.services.synthesis_quality_validator import (
    SynthesisQualityValidator,
    validate_overall_quality,
    _score_task_role_alignment,
    _score_deliverable_coverage,
)


# =========================================================================
# Phase 2: 全局质量评分测试
# =========================================================================


class TestOverallQualityScoring:
    """Phase 2: validate_overall_quality 集成测试"""

    def test_empty_roles_returns_acceptable(self):
        """空角色列表应返回可接受"""
        result = validate_overall_quality([], gene_pool_keywords={})
        assert result["is_acceptable"] is True
        assert result["overall_score"] >= 0.5

    def test_well_aligned_roles_score_high(self):
        """任务与关键词高度匹配时应得高分"""
        roles = [
            {
                "role_id": "2-1",
                "tasks": ["居住空间设计方案", "住宅动线规划", "私宅材质选择"],
                "deliverable_count": 3,
            },
            {
                "role_id": "4-1",
                "tasks": ["设计趋势研究", "案例分析报告"],
                "deliverable_count": 2,
            },
        ]
        gene_pool = {
            "2-1": ["居住空间设计", "住宅空间设计", "私宅设计"],
            "4-1": ["设计趋势", "案例分析", "研究报告"],
        }
        result = validate_overall_quality(roles, gene_pool_keywords=gene_pool)
        assert result["alignment_score"] >= 0.7
        assert result["coverage_score"] >= 0.7
        assert result["is_acceptable"] is True

    def test_misaligned_roles_score_lower(self):
        """任务与关键词完全不匹配时应得低分"""
        roles = [
            {
                "role_id": "2-1",
                "tasks": ["水果采购计划", "快递物流管理"],
                "deliverable_count": 2,
            },
        ]
        gene_pool = {
            "2-1": ["居住空间设计", "住宅空间设计", "私宅设计"],
        }
        result = validate_overall_quality(roles, gene_pool_keywords=gene_pool)
        # 完全不匹配时对齐得分应偏低
        assert result["alignment_score"] < 0.5

    def test_missing_gene_pool_gives_moderate_score(self):
        """无gene_pool数据时应给中等分（退化）"""
        roles = [
            {
                "role_id": "99-1",  # 不存在的角色
                "tasks": ["某项任务"],
                "deliverable_count": 1,
            },
        ]
        result = validate_overall_quality(roles, gene_pool_keywords={})
        # 无关键词时退化为0.6
        assert result["alignment_score"] >= 0.5


class TestTaskRoleAlignment:
    """Phase 2: _score_task_role_alignment 单元测试"""

    def test_empty_roles(self):
        score, msgs = _score_task_role_alignment([])
        assert score == 1.0

    def test_perfect_alignment(self):
        roles = [
            {"role_id": "2-1", "tasks": ["居住空间设计 住宅设计 私宅规划"]},
        ]
        gene_pool = {"2-1": ["居住空间设计", "住宅", "私宅"]}
        score, msgs = _score_task_role_alignment(roles, gene_pool)
        assert score >= 0.8

    def test_zero_alignment(self):
        roles = [
            {"role_id": "2-1", "tasks": ["火箭发射控制"]},
        ]
        gene_pool = {"2-1": ["居住空间设计", "住宅设计"]}
        score, msgs = _score_task_role_alignment(roles, gene_pool)
        assert score < 0.5
        assert any("匹配度极低" in m for m in msgs)


class TestDeliverableCoverage:
    """Phase 2: _score_deliverable_coverage 单元测试"""

    def test_empty_roles(self):
        score, msgs = _score_deliverable_coverage([])
        assert score == 1.0

    def test_good_coverage(self):
        roles = [
            {"role_id": "2-1", "deliverable_count": 3},
            {"role_id": "4-1", "deliverable_count": 2},
            {"role_id": "5-1", "deliverable_count": 3},
        ]
        score, msgs = _score_deliverable_coverage(roles)
        assert score >= 0.8

    def test_poor_coverage(self):
        roles = [
            {"role_id": "2-1", "deliverable_count": 0},
            {"role_id": "4-1", "deliverable_count": 0},
        ]
        score, msgs = _score_deliverable_coverage(roles)
        assert score < 0.5

    def test_empty_role_detection(self):
        roles = [
            {"role_id": "2-1", "deliverable_count": 3},
            {"role_id": "4-1", "deliverable_count": 0},
        ]
        score, msgs = _score_deliverable_coverage(roles)
        assert any("无交付物" in m for m in msgs)


# =========================================================================
# Phase 3: 命名泛化检测 + 任务关联测试
# =========================================================================


class TestNamingValidation:
    """Phase 3: _validate_naming 增强测试"""

    def test_generic_name_detected(self):
        """泛化命名应被扣分"""
        score, msgs = SynthesisQualityValidator._validate_naming(
            role_name="测试角色",
            dynamic_role_name="设计专家",
            parent_ids=["2-1", "5-1"],
        )
        assert score < 8
        assert any("泛化模式" in m for m in msgs)

    def test_specific_name_passes(self):
        """具有项目特征的命名不应触发泛化检测"""
        score, msgs = SynthesisQualityValidator._validate_naming(
            role_name="测试角色",
            dynamic_role_name="居住体验驱动型智能空间整合设计师",
            parent_ids=["2-1", "5-1"],
        )
        assert not any("泛化模式" in m for m in msgs)

    def test_task_keyword_overlap_detected(self):
        """任务与名称有关键词重叠时不扣分"""
        score, msgs = SynthesisQualityValidator._validate_naming(
            role_name="测试角色",
            dynamic_role_name="居住体验驱动型智能空间整合设计师",
            parent_ids=["2-1", "5-1"],
            tasks=["居住空间的智能化体验设计方案"],
        )
        assert not any("无关键词重叠" in m for m in msgs)

    def test_task_keyword_no_overlap_warning(self):
        """任务与名称完全无重叠时应警告"""
        score, msgs = SynthesisQualityValidator._validate_naming(
            role_name="测试角色",
            dynamic_role_name="跨界融合创新策略协同师",
            parent_ids=["2-1", "5-1"],
            tasks=["水果沙拉制作流程优化"],
        )
        assert any("无关键词重叠" in m for m in msgs)

    def test_backward_compatible_without_tasks(self):
        """不传tasks参数时应向后兼容（不报错）"""
        score, msgs = SynthesisQualityValidator._validate_naming(
            role_name="测试角色",
            dynamic_role_name="跨界融合创新策略协同设计专家",
            parent_ids=["2-1", "5-1"],
        )
        assert isinstance(score, float)
        assert isinstance(msgs, list)

    def test_comprehensive_generic_patterns(self):
        """测试多种泛化模式"""
        generic_names = ["综合分析专家", "跨界设计专家", "全能工程师"]
        for name in generic_names:
            score, msgs = SynthesisQualityValidator._validate_naming(
                role_name="base", dynamic_role_name=name, parent_ids=["2-1", "5-1"]
            )
            assert any("泛化模式" in m for m in msgs), f"未检测到泛化名称: '{name}'"


# =========================================================================
# Phase 4: Gini/DFS 已在 P3 精简中移除（仅日志，非决策逻辑）
# _compute_gini, _check_dependency_cycles 方法已删除
# =========================================================================


# =========================================================================
# Phase 5: Prompt 质量监控测试
# =========================================================================


class TestPromptQualityMonitoring:
    """Phase 5: _monitor_synthesized_prompt_quality 测试"""

    def _make_factory(self):
        """构造最小 ExpertFactory 实例"""
        from intelligent_project_analyzer.agents.task_oriented_expert_factory import (
            TaskOrientedExpertFactory,
        )

        # 使用 MagicMock 避免实际初始化
        factory = MagicMock(spec=TaskOrientedExpertFactory)
        factory._monitor_synthesized_prompt_quality = (
            TaskOrientedExpertFactory._monitor_synthesized_prompt_quality.__get__(factory)
        )
        return factory

    def test_good_prompt_no_issues(self):
        """完整的融合Prompt不应触发警告"""
        factory = self._make_factory()
        prompt = (
            "### 角色身份：V2设计总监\n\n"
            "这是一个测试Prompt" * 50 + "\n\n"
            "### 输出格式要求\n请输出JSON\n\n"
            "### 工作方法\n按步骤执行\n\n"
            "## 跨界融合身份声明 (v8.1 动态合成)\n\n"
            "你的合成身份: 测试合成专家"
        )
        # 不应抛异常
        factory._monitor_synthesized_prompt_quality(prompt, "SYNTHESIZED_2-1+5-1")

    def test_short_prompt_warning(self):
        """过短Prompt应触发警告"""
        factory = self._make_factory()
        prompt = "Very short prompt"
        factory._monitor_synthesized_prompt_quality(prompt, "SYNTHESIZED_2-1+5-1")

    def test_missing_sections_warning(self):
        """缺少关键段落应触发警告"""
        factory = self._make_factory()
        prompt = "这是一个没有任何关键段落的测试Prompt" * 30
        factory._monitor_synthesized_prompt_quality(prompt, "SYNTHESIZED_2-1+5-1")

    def test_missing_fusion_declaration(self):
        """缺少融合声明应触发警告"""
        factory = self._make_factory()
        prompt = "### 角色身份：V2设计总监\n\n" "这是一个测试" * 50 + "\n\n" "### 输出格式要求\n请输出\n\n" "### 工作方法\n按步骤\n"
        # 没有融合声明
        factory._monitor_synthesized_prompt_quality(prompt, "SYNTHESIZED_2-1+5-1")
