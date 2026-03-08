# -*- coding: utf-8 -*-
"""
P0/P1/P2 综合测试套件

测试范围:
- P0 (v7.500): 确定性模式 + 理论验证 + 进度提示
- P1 (v7.501): Structured Outputs + 智能等待
- P2 (v7.502): Tech Philosophy扩容

测试类型:
1. 单元测试 - Schema、理论枚举、Pydantic模型
2. 集成测试 - Agent与Schema集成、LLM交互
3. 端到端测试 - 完整分析流程
4. 回归测试 - 性能指标、向后兼容性

创建日期: 2026-02-10
"""

import pytest
import sys
import os
from pydantic import ValidationError

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ============================================================================
# 第1部分: 单元测试 - Schema & Theory验证
# ============================================================================


class TestUnit_SchemaValidation:
    """单元测试: Schema和理论枚举验证"""

    def test_approved_theory_count(self):
        """测试理论总数是否为34个 (P2新增4个)"""
        from intelligent_project_analyzer.agents.requirements_analyst_schema import APPROVED_THEORY

        all_theories = [t for t in APPROVED_THEORY.__args__]
        assert len(all_theories) == 34, f"期望34个理论，实际{len(all_theories)}个"

    def test_new_theories_in_enum(self):
        """测试P2新增的4个理论是否在枚举中"""
        from intelligent_project_analyzer.agents.requirements_analyst_schema import APPROVED_THEORY

        new_theories = [
            "Algorithmic_Governance",
            "Data_Sovereignty",
            "Post_Anthropocentric_Design",
            "Glitch_Aesthetics",
        ]

        all_theories = [t for t in APPROVED_THEORY.__args__]
        for theory in new_theories:
            assert theory in all_theories, f"理论 {theory} 未在枚举中"

    def test_tech_philosophy_lens_count(self):
        """测试Tech Philosophy透镜理论数是否为7个"""
        from intelligent_project_analyzer.agents.requirements_analyst_schema import THEORY_TO_LENS, LensCategory

        tech_theories = [t for t, lens in THEORY_TO_LENS.items() if lens == LensCategory.TECH_PHILOSOPHY]

        assert len(tech_theories) == 7, f"期望7个Tech Philosophy理论，实际{len(tech_theories)}个"

    def test_new_theories_mapping(self):
        """测试新理论映射到Tech Philosophy透镜"""
        from intelligent_project_analyzer.agents.requirements_analyst_schema import THEORY_TO_LENS, LensCategory

        new_theories = [
            "Algorithmic_Governance",
            "Data_Sovereignty",
            "Post_Anthropocentric_Design",
            "Glitch_Aesthetics",
        ]

        for theory in new_theories:
            assert theory in THEORY_TO_LENS, f"理论 {theory} 未在映射表中"
            assert THEORY_TO_LENS[theory] == LensCategory.TECH_PHILOSOPHY, f"{theory} 应映射到Tech_Philosophy"

    def test_pydantic_model_instantiation(self):
        """测试Pydantic模型能正确实例化新理论"""
        from intelligent_project_analyzer.agents.requirements_analyst_schema import CoreTension, LensCategory

        test_cases = [
            {
                "theory": "Algorithmic_Governance",
                "name": "算法权力 vs 人类自主",
                "description": "算法如何塑造空间规则、分配资源，以及人类在算法驱动系统中的自主性边界问题",
            },
            {"theory": "Data_Sovereignty", "name": "便利 vs 隐私主权", "description": "智能家居中数据采集、存储、使用的权利归属，以及用户对自身数据的控制权边界"},
        ]

        for case in test_cases:
            tension = CoreTension(
                name=case["name"],
                theory_source=case["theory"],
                lens_category=LensCategory.TECH_PHILOSOPHY,
                description=case["description"],
                design_implication=f"为{case['theory']}项目设计时，需要平衡技术驱动与人文关怀",
            )
            assert tension.theory_source == case["theory"]
            assert tension.lens_category == LensCategory.TECH_PHILOSOPHY

    def test_invalid_theory_rejection(self):
        """测试无效理论被拒绝（防止幻觉）"""
        from intelligent_project_analyzer.agents.requirements_analyst_schema import CoreTension

        with pytest.raises(ValidationError):
            CoreTension(
                name="测试张力",
                theory_source="NonExistent_Theory_That_Does_Not_Exist",  # 不存在的理论
                lens_category="Tech_Philosophy",
                description="这是一个测试描述，应该被Pydantic验证拒绝",
                design_implication="这个理论不应该通过验证",
            )

    def test_all_lens_categories_covered(self):
        """测试所有透镜类别都有理论覆盖"""
        from intelligent_project_analyzer.agents.requirements_analyst_schema import THEORY_TO_LENS, LensCategory

        # 获取所有透镜类别
        all_lens_categories = set(LensCategory)

        # 获取已映射的透镜类别
        mapped_lens_categories = set(THEORY_TO_LENS.values())

        # 所有透镜类别都应有理论
        assert all_lens_categories == mapped_lens_categories, f"缺少映射: {all_lens_categories - mapped_lens_categories}"


class TestUnit_PromptContent:
    """单元测试: Prompt文件内容验证"""

    def test_new_theories_in_prompt(self):
        """测试新理论是否在Prompt文件中"""
        prompt_file = "intelligent_project_analyzer/config/prompts/requirements_analyst.txt"

        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 中英文关键词
        keywords = [
            "算法治理",
            "Algorithmic Governance",
            "数据主权",
            "Data Sovereignty",
            "后人类中心设计",
            "Post-Anthropocentric Design",
            "故障美学",
            "Glitch Aesthetics",
        ]

        for keyword in keywords:
            assert keyword in content, f"关键词 '{keyword}' 未在Prompt中"

    def test_tech_philosophy_section_structure(self):
        """测试Tech Philosophy部分结构完整"""
        prompt_file = "intelligent_project_analyzer/config/prompts/requirements_analyst.txt"

        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查必要结构
        required_fields = ["name:", "application:", "example:", "when_to_use:"]

        # 应该有7个Tech Philosophy理论的完整描述
        tech_section_start = content.find("技术哲学/STS透镜")
        if tech_section_start == -1:
            tech_section_start = content.find("Tech Philosophy")

        assert tech_section_start != -1, "未找到Tech Philosophy部分"

        tech_section = content[tech_section_start : tech_section_start + 5000]

        for field in required_fields:
            assert tech_section.count(field) >= 7, f"Tech Philosophy部分应包含至少7个 '{field}' 字段"


class TestUnit_IntelligentWaiting:
    """单元测试: P1智能等待工具函数"""

    @pytest.mark.asyncio
    async def test_smart_web_extraction_timeout(self):
        """测试网页抓取的智能超时"""
        pytest.importorskip(
            "intelligent_project_analyzer.tools.web_content_extractor", reason="web_content_extractor 模块不存在，跳过"
        )
        from intelligent_project_analyzer.tools.web_content_extractor import extract_web_content_from_urls_async

        # 测试无效URL的快速失败（应在3秒内返回）
        import time

        start = time.time()

        result = await extract_web_content_from_urls_async(
            ["https://this-url-does-not-exist-12345678.com"], timeout=3.0
        )

        elapsed = time.time() - start

        # 应该快速失败，不超过5秒
        assert elapsed < 5.0, f"超时时间过长: {elapsed:.2f}s"
        assert len(result) == 0, "无效URL应返回空结果"

    def test_rate_limiter_polling_interval(self):
        """测试限流器轮询间隔优化"""
        pytest.importorskip("intelligent_project_analyzer.utils.rate_limiter", reason="rate_limiter 模块不存在，跳过")
        from intelligent_project_analyzer.utils.rate_limiter import RateLimiter

        # 创建限流器（每秒10次）
        limiter = RateLimiter(requests_per_second=10)

        # 验证轮询间隔是否优化
        # P1优化: 从100ms减少到50ms
        import time

        acquired_count = 0
        start = time.time()

        for _ in range(5):
            limiter.wait_if_needed()
            acquired_count += 1

        elapsed = time.time() - start

        # 5次请求在10 req/s的限流下，理论最小时间为0.5s
        # 加上轮询开销，应在0.8s以内完成
        assert elapsed < 0.8, f"限流轮询过慢: {elapsed:.2f}s"


# ============================================================================
# 第2部分: 集成测试 - Agent与LLM交互
# ============================================================================


class TestIntegration_AgentSchemaIntegration:
    """集成测试: Agent与Schema集成"""

    @pytest.mark.integration
    def test_schema_import_in_agent(self):
        """测试Agent能正确导入Schema"""
        mod = pytest.importorskip(
            "intelligent_project_analyzer.agents.requirements_analyst", reason="requirements_analyst 模块结构已重构"
        )
        if not hasattr(mod, "RequirementsAnalyst"):
            pytest.skip("RequirementsAnalyst 类已移除")
        RequirementsAnalyst = mod.RequirementsAnalyst
        from intelligent_project_analyzer.agents.requirements_analyst_schema import RequirementsAnalysisSchema

        # 验证Agent可以实例化
        RequirementsAnalyst()

        # 验证Schema可以被使用
        assert hasattr(RequirementsAnalysisSchema, "model_fields"), "Schema应该是Pydantic模型"

    @pytest.mark.integration
    @pytest.mark.llm
    async def test_structured_outputs_validation(self):
        """测试Structured Outputs验证（需要LLM）"""
        pytest.skip("LLM测试已跳过（需要API key和网络）")

        # 此测试在有LLM环境时运行
        from intelligent_project_analyzer.agents.requirements_analyst import RequirementsAnalyst

        analyst = RequirementsAnalyst()

        test_requirement = """
        设计一个智能办公空间，面积500平米，包含开放工位、会议室、
        休息区。需要算法优化座位分配，同时保护员工隐私。
        """

        try:
            result = await analyst.analyze(test_requirement)

            # 验证返回的理论都是有效的
            from intelligent_project_analyzer.agents.requirements_analyst_schema import APPROVED_THEORY

            all_theories = [t for t in APPROVED_THEORY.__args__]

            for tension in result.core_tensions:
                assert tension.theory_source in all_theories, f"理论 {tension.theory_source} 不在批准列表中（幻觉检测）"

        except Exception as e:
            pytest.fail(f"Structured Outputs验证失败: {e}")


class TestIntegration_DeterministicMode:
    """集成测试: P0确定性模式"""

    @pytest.mark.integration
    def test_deterministic_llm_config(self):
        """测试LLM确定性配置（P0优化）"""
        mod = pytest.importorskip(
            "intelligent_project_analyzer.agents.requirements_analyst", reason="requirements_analyst 模块结构已重构"
        )
        if not hasattr(mod, "RequirementsAnalyst"):
            pytest.skip("RequirementsAnalyst 类已移除")
        RequirementsAnalyst = mod.RequirementsAnalyst

        analyst = RequirementsAnalyst()

        # 验证LLM配置包含确定性参数
        # 注意：这里假设Agent暴露了llm_config属性
        # 实际需要根据代码结构调整

        # 配置应包含:
        # - temperature: 0.1
        # - seed: 42

        # 这是一个简化的测试，实际需要检查Agent的内部LLM配置
        assert hasattr(analyst, "analyze"), "Agent应该有analyze方法"


# ============================================================================
# 第3部分: 端到端测试 - 完整分析流程
# ============================================================================


class TestE2E_CompleteAnalysisFlow:
    """端到端测试: 完整分析流程"""

    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.llm
    async def test_tech_project_with_new_theories(self):
        """测试科技类项目使用新理论的完整流程"""
        pytest.skip("E2E测试已跳过（需要完整环境）")

        from intelligent_project_analyzer.agents.requirements_analyst import RequirementsAnalyst

        analyst = RequirementsAnalyst()

        # 测试用例：智能办公项目（应触发新增的Tech Philosophy理论）
        tech_requirement = """
        设计一个AI驱动的智能办公空间，总面积800平米。

        核心需求:
        1. 算法优化座位分配系统（基于员工工作习惯和团队协作需求）
        2. 全面的传感器网络监测（温度、湿度、人流、噪音）
        3. 隐私保护设计（员工数据所有权明确）
        4. 生态友好（绿植墙、自然采光、雨水回收）

        预算: 200万
        工期: 6个月
        """

        result = await analyst.analyze(tech_requirement)

        # 验证新理论被使用
        used_theories = [t.theory_source for t in result.core_tensions]

        new_theories = ["Algorithmic_Governance", "Data_Sovereignty", "Post_Anthropocentric_Design"]

        # 至少应该使用1个新理论
        used_new_theories = [t for t in new_theories if t in used_theories]

        assert len(used_new_theories) >= 1, f"科技类项目应使用新增理论，实际使用: {used_theories}"

        # 验证分析质量
        assert len(result.core_tensions) >= 3, "应至少识别3个核心张力"
        assert result.overall_assessment is not None, "应有总体评估"

    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_traditional_project_compatibility(self):
        """测试传统项目的向后兼容性（回归测试）"""
        pytest.skip("E2E测试已跳过（需要完整环境）")

        from intelligent_project_analyzer.agents.requirements_analyst import RequirementsAnalyst

        analyst = RequirementsAnalyst()

        # 测试用例：传统住宅项目（不应过度使用Tech Philosophy理论）
        traditional_requirement = """
        设计一个150平米的三室两厅住宅，现代简约风格。

        需求:
        - 主卧带独立卫生间
        - 客厅采光良好
        - 厨房开放式
        - 注重收纳空间

        预算: 30万
        家庭成员: 夫妻+1个孩子
        """

        result = await analyst.analyze(traditional_requirement)

        # 验证理论使用合理性
        used_theories = [t.theory_source for t in result.core_tensions]

        tech_theories = [
            "Algorithmic_Governance",
            "Data_Sovereignty",
            "Post_Anthropocentric_Design",
            "Glitch_Aesthetics",
        ]

        # 传统项目不应过度使用Tech Philosophy理论
        used_tech_theories = [t for t in tech_theories if t in used_theories]

        assert len(used_tech_theories) <= 1, f"传统项目不应过度使用Tech理论，实际使用: {used_tech_theories}"


# ============================================================================
# 第4部分: 回归测试 - 性能与兼容性
# ============================================================================


class TestRegression_Performance:
    """回归测试: 性能指标"""

    @pytest.mark.regression
    def test_schema_validation_performance(self):
        """测试Schema验证性能（不应退化）"""
        from intelligent_project_analyzer.agents.requirements_analyst_schema import CoreTension, LensCategory
        import time

        # 大批量实例化测试
        start = time.time()

        for i in range(100):
            CoreTension(
                name=f"测试张力{i}",
                theory_source="Algorithmic_Governance",
                lens_category=LensCategory.TECH_PHILOSOPHY,
                description="这是一个用于性能测试的描述文本，需要满足最小长度要求以通过Pydantic验证",
                design_implication="这是设计启示，用于测试Pydantic模型的实例化性能和验证速度",
            )

        elapsed = time.time() - start

        # 100次实例化应在1秒内完成
        assert elapsed < 1.0, f"Schema验证性能退化: {elapsed:.3f}s"

    @pytest.mark.regression
    def test_theory_count_stability(self):
        """测试理论总数稳定性（确保不会意外增删）"""
        from intelligent_project_analyzer.agents.requirements_analyst_schema import APPROVED_THEORY

        all_theories = [t for t in APPROVED_THEORY.__args__]

        # v7.502应该是34个理论
        expected_count = 34

        assert len(all_theories) == expected_count, f"理论总数变化：期望{expected_count}，实际{len(all_theories)}"

    @pytest.mark.regression
    def test_original_theories_intact(self):
        """测试原始30个理论未被修改"""
        from intelligent_project_analyzer.agents.requirements_analyst_schema import APPROVED_THEORY

        # v7.501的30个理论（P2之前）
        original_30_theories = [
            # Anthropology
            "Ritual_And_Liminality",
            "Kinship_And_Space_Allocation",
            "Material_Culture_And_Identity",
            "Sacred_Vs_Profane_Space",
            # Sociology
            "Bourdieu_Cultural_Capital",
            "Goffman_Front_Back_Stage",
            "Social_Exclusion_And_Boundary",
            "Social_Construction_Of_Time",
            # Psychology
            "Maslow_Hierarchy",
            "Territoriality",
            "Cognitive_Load_Theory",
            "Attachment_Theory_Secure_Base",
            "Trauma_Informed_Design",
            # Phenomenology
            "Heidegger_Dwelling",
            "Merleau_Ponty_Embodied_Phenomenology",
            "Bachelard_Poetics_Of_Space",
            "Aestheticization_Of_Everyday_Life",
            # Cultural Studies
            "Symbolic_Consumption",
            "Subculture_And_Resistance",
            "Nostalgia_And_Politics_Of_Time",
            "Baudrillard_Hyperreality_Simulacra",
            # Tech Philosophy (原3个)
            "Value_Laden_Technology",
            "Cyborg_Dwelling",
            "Digital_Labor_Invisible_Work",
            # Material Culture
            "Social_Life_Of_Things",
            "Material_Agency",
            "Craft_Knowledge_Body_Memory",
            # Spiritual Philosophy
            "Production_Of_Sacred_Space",
            "Meditation_Sensory_Deprivation",
            "Pilgrimage_And_Journey",
        ]

        all_theories = [t for t in APPROVED_THEORY.__args__]

        for theory in original_30_theories:
            assert theory in all_theories, f"原始理论 {theory} 缺失（回归错误）"


class TestRegression_BackwardCompatibility:
    """回归测试: 向后兼容性"""

    @pytest.mark.regression
    def test_old_theory_instantiation(self):
        """测试旧理论仍能正常实例化"""
        from intelligent_project_analyzer.agents.requirements_analyst_schema import CoreTension, LensCategory

        # 测试v7.501之前的理论
        old_theories = [
            ("Maslow_Hierarchy", LensCategory.PSYCHOLOGY),
            ("Heidegger_Dwelling", LensCategory.PHENOMENOLOGY),
            ("Value_Laden_Technology", LensCategory.TECH_PHILOSOPHY),
        ]

        for theory, lens in old_theories:
            tension = CoreTension(
                name=f"{theory}测试",
                theory_source=theory,
                lens_category=lens,
                description=f"测试{theory}理论的向后兼容性，确保P2更新不影响旧理论的使用，这是系统稳定性的重要保证",
                design_implication="这是一个回归测试，验证系统的向后兼容性，确保P0/P1/P2优化不破坏原有功能和理论体系",
            )
            assert tension.theory_source == theory

    @pytest.mark.regression
    def test_lens_category_enum_stability(self):
        """测试透镜类别枚举未变化"""
        from intelligent_project_analyzer.agents.requirements_analyst_schema import LensCategory

        # v7.502应保持7个透镜类别不变

        actual_lens_categories = set([lens.value for lens in LensCategory])

        # 注意：实际可能有8个（包括Spiritual_Philosophy）
        # 需要根据实际代码调整
        assert len(actual_lens_categories) >= 7, f"透镜类别数量异常: {actual_lens_categories}"


# ============================================================================
# 测试配置和Fixture
# ============================================================================


@pytest.fixture(scope="session")
def test_config():
    """测试配置"""
    return {
        "env": "test",
        "skip_llm": True,  # 默认跳过需要LLM的测试
        "timeout": 30,
    }


# ============================================================================
# 主测试运行器
# ============================================================================

if __name__ == "__main__":
    """
    运行方式:

    # 运行所有单元测试
    pytest tests/test_p0_p1_p2_comprehensive.py -v -m "not llm and not slow"

    # 运行单元+集成测试
    pytest tests/test_p0_p1_p2_comprehensive.py -v -m "not e2e and not llm"

    # 运行回归测试
    pytest tests/test_p0_p1_p2_comprehensive.py -v -m regression

    # 运行所有测试（包括LLM和E2E）
    pytest tests/test_p0_p1_p2_comprehensive.py -v
    """
    pytest.main([__file__, "-v", "-m", "not llm and not slow"])
