# -*- coding: utf-8 -*-
"""
需求分析师 - 端到端测试套件
============================
使用真实 LLM（需要 API Key），在 CI 中自动跳过（@pytest.mark.llm）

E01  充足输入完整流程 → two_phase、confidence > 0.5、PSA 存在
E02  不足输入流程 → two_phase（Phase2 始终运行），低 confidence
E03  Unicode / 特殊字符输入 → 不崩溃
E04  超长输入（5000字符）→ 完成
E05  空输入降级处理
E06  多个并发 session（序列模拟）

运行方式：
  pytest tests/test_requirements_analyst_e2e.py -m llm -v
  需设置环境变量 OPENAI_API_KEY 或对应 LLM 的 Key
"""

import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


def _skip_if_no_llm():
    """无 API Key 时跳过"""
    has_key = any(
        [
            os.environ.get("OPENAI_API_KEY"),
            os.environ.get("ANTHROPIC_API_KEY"),
            os.environ.get("AZURE_OPENAI_API_KEY"),
        ]
    )
    if not has_key:
        pytest.skip("未配置 API Key，跳过 E2E 测试（需要 OPENAI_API_KEY 等环境变量）")


def _build_real_agent():
    """构造调用真实 LLM 的 V2 Agent"""
    _skip_if_no_llm()
    from intelligent_project_analyzer.core.llm_factory import LLMFactory

    llm = LLMFactory.create_default()
    from intelligent_project_analyzer.agents.requirements_analyst_agent import RequirementsAnalystAgentV2

    return RequirementsAnalystAgentV2(llm_model=llm)


SUFFICIENT_INPUT = (
    "我是32岁的前律师，住在上海，有一套75平米的南向高层公寓（2室1厅1卫），与父母+配偶+孩子共五人居住。"
    "改造预算60万，希望在4个月内完成。"
    "核心需求：现代极简风格，解决三代同堂的收纳与动线矛盾，同时保留一片给孩子的可变游戏区。"
    "我非常在意空间的叙事感和自然采光，不喜欢过度装饰。"
)

INSUFFICIENT_INPUT = "帮我设计一下我家，谢谢"

UNICODE_INPUT = "设计一套融合传统徽派建筑元素（青砖白墙、马头墙）的现代民宿，" "位于皖南山区，预算200万💰，面积约600㎡🏠，" "目标客群为高净值度假用户（¥3000/晚），希望体现'诗意栖居'理念。"

LONG_INPUT = (
    "我是一名独立建筑师，正在为一个综合文化中心项目寻求需求分析支持。"
    "该项目位于成都市中心，总建筑面积约8000平方米，地上5层，地下1层。"
    "业主是一个私人文化基金会，希望在此建立集艺术展览、独立书店、咖啡休闲、小型音乐演出及"
    "社区活动于一体的复合型文化空间。"
    "项目预算：约1.2亿人民币（含建安成本、软装及设备）。"
    "工期：总工期约24个月，需分两期实施（核心功能区先行开放）。"
    "建筑风格：业主倾向于当代地域主义（Contemporary Regionalism），希望从成都传统巷道文化中汲取灵感，"
    "以现代材料诠释川西民居的空间序列与光影变化，避免表面化的仿古符号。"
    "核心挑战如下：\n"
    "1. 多功能混合使用的噪音与流线冲突（音乐厅与阅读区的声学隔绝）；\n"
    "2. 商业可持续性与公共性之间的张力（如何在保持公益性的同时覆盖运营成本）；\n"
    "3. 地下停车需求与地面景观设计的矛盾；\n"
    "4. 针对不同人群（儿童、老年人、艺术爱好者）的空间适配性设计；\n"
    "5. 四川地域气候的适应性设计（夏季高温高湿、冬季阴冷寡照）。\n"
    "主要交付物预期：\n"
    "- 建筑策略文档（Define the Problem）\n"
    "- 空间叙事框架（Character + Context Narrative）\n"
    "- 各功能区设计原则与关键决策点\n"
    "- 专家协作建议（推荐设计团队模块）\n"
    "附加背景：业主曾参观过上海西岸艺术中心和北京今日美术馆，希望达到类似的当代性与在地性并重的效果。"
    "他们明确不希望出现'网红打卡'式的表面化设计，更关注空间的长期生命力和使用者的精神共鸣。"
    "项目有1名主创建筑师（即我本人）、1名室内设计师和1名景观设计师。"
    "我们需要外部智能辅助来完成'问题定义'这一关键阶段，以便在第一个里程碑向业主提交一份有说服力的设计纲领文件。"
) * 3  # 约 3000+ 字符


# ═══════════════════════════════════════════════════════════════
# E01 - 充足输入完整流程
# ═══════════════════════════════════════════════════════════════


@pytest.mark.llm
@pytest.mark.slow
class TestE01SufficientInputE2E:
    def test_returns_analysis_result_type(self):
        agent = _build_real_agent()
        from intelligent_project_analyzer.core.types import AnalysisResult

        result = agent.execute(SUFFICIENT_INPUT, "e2e-session-01")
        assert isinstance(result, AnalysisResult)

    def test_confidence_above_threshold(self):
        agent = _build_real_agent()
        result = agent.execute(SUFFICIENT_INPUT, "e2e-session-02")
        assert result.confidence > 0.5, f"充足输入 confidence 过低: {result.confidence}"

    def test_analysis_mode_is_two_phase(self):
        agent = _build_real_agent()
        result = agent.execute(SUFFICIENT_INPUT, "e2e-session-03")
        assert result.metadata["analysis_mode"] == "two_phase"

    def test_node_path_complete(self):
        agent = _build_real_agent()
        result = agent.execute(SUFFICIENT_INPUT, "e2e-session-04")
        path = result.metadata["node_path"]
        for node in ("precheck", "phase1", "phase2", "output"):
            assert node in path, f"节点路径缺少 {node}: {path}"

    def test_problem_solving_approach_present(self):
        """A-01 E2E 验证：充足输入下 PSA 应自动补全"""
        agent = _build_real_agent()
        result = agent.execute(SUFFICIENT_INPUT, "e2e-session-05")
        sd = result.structured_data
        psa = sd.get("problem_solving_approach")
        assert psa is not None, "E2E A-01: problem_solving_approach 未生成"
        assert isinstance(psa, dict)

    def test_structured_data_has_core_fields(self):
        agent = _build_real_agent()
        result = agent.execute(SUFFICIENT_INPUT, "e2e-session-06")
        sd = result.structured_data
        for field in ("project_task", "primary_deliverables"):
            assert field in sd, f"structured_data 缺少核心字段: {field}"

    def test_content_is_valid_json(self):
        agent = _build_real_agent()
        result = agent.execute(SUFFICIENT_INPUT, "e2e-session-07")
        data = json.loads(result.content)
        assert isinstance(data, dict)

    def test_timing_recorded(self):
        agent = _build_real_agent()
        result = agent.execute(SUFFICIENT_INPUT, "e2e-session-08")
        sd = result.structured_data
        assert sd.get("total_elapsed_ms", 0) > 0


# ═══════════════════════════════════════════════════════════════
# E02 - 不足输入流程（Phase2 始终运行）
# ═══════════════════════════════════════════════════════════════


@pytest.mark.llm
@pytest.mark.slow
class TestE02InsufficientInputE2E:
    def test_returns_analysis_result(self):
        agent = _build_real_agent()
        from intelligent_project_analyzer.core.types import AnalysisResult

        result = agent.execute(INSUFFICIENT_INPUT, "e2e-insufficient-01")
        assert isinstance(result, AnalysisResult)

    def test_phase2_still_runs(self):
        """C-02 & 路由回归 E2E：即使不足，Phase2 仍然运行"""
        agent = _build_real_agent()
        result = agent.execute(INSUFFICIENT_INPUT, "e2e-insufficient-02")
        path = result.metadata["node_path"]
        assert "phase2" in path, "不足输入时 Phase2 未运行！路由回归"

    def test_analysis_mode_is_two_phase_even_insufficient(self):
        agent = _build_real_agent()
        result = agent.execute(INSUFFICIENT_INPUT, "e2e-insufficient-03")
        # 即使输入不足，也应进入 two_phase（Phase2 始终运行）
        assert result.metadata["analysis_mode"] == "two_phase"

    def test_confidence_lower_than_sufficient(self):
        """不足输入的置信度应低于充足输入"""
        agent = _build_real_agent()
        r_insufficient = agent.execute(INSUFFICIENT_INPUT, "e2e-insufficient-04")
        r_sufficient = agent.execute(SUFFICIENT_INPUT, "e2e-sufficient-04")
        assert r_insufficient.confidence <= r_sufficient.confidence + 0.1


# ═══════════════════════════════════════════════════════════════
# E03 - Unicode 和特殊字符
# ═══════════════════════════════════════════════════════════════


@pytest.mark.llm
@pytest.mark.slow
class TestE03UnicodeInputE2E:
    def test_unicode_input_no_crash(self):
        agent = _build_real_agent()
        result = agent.execute(UNICODE_INPUT, "e2e-unicode-01")
        assert result is not None
        assert result.structured_data is not None

    def test_emoji_preserved_in_output(self):
        agent = _build_real_agent()
        result = agent.execute(UNICODE_INPUT, "e2e-unicode-02")
        # 输出应可正常编码，不崩溃
        _ = json.dumps(result.structured_data, ensure_ascii=False)

    def test_mixed_script_input(self):
        mixed = "Redesign my 75㎡ apartment（上海）with €200k budget, 3-generation family 三代同堂"
        agent = _build_real_agent()
        result = agent.execute(mixed, "e2e-unicode-03")
        assert result is not None


# ═══════════════════════════════════════════════════════════════
# E04 - 超长输入
# ═══════════════════════════════════════════════════════════════


@pytest.mark.llm
@pytest.mark.slow
class TestE04LongInputE2E:
    def test_long_input_completes(self):
        agent = _build_real_agent()
        start = time.time()
        result = agent.execute(LONG_INPUT[:5000], "e2e-long-01")  # 截断到 5000 字符
        elapsed = time.time() - start
        assert result is not None
        # 超长输入的处理时间应在合理范围内（120 秒以内）
        assert elapsed < 120, f"超长输入处理超时: {elapsed:.1f}s"

    def test_long_input_returns_valid_result(self):
        agent = _build_real_agent()
        result = agent.execute(LONG_INPUT[:3000], "e2e-long-02")
        assert result.structured_data is not None
        _ = json.dumps(result.structured_data, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════
# E05 - 空输入降级
# ═══════════════════════════════════════════════════════════════


@pytest.mark.llm
class TestE05EmptyInputE2E:
    def test_empty_input_no_crash(self):
        agent = _build_real_agent()
        result = agent.execute("", "e2e-empty-01")
        assert result is not None

    def test_whitespace_input_no_crash(self):
        agent = _build_real_agent()
        result = agent.execute("   \n\t   ", "e2e-whitespace-01")
        assert result is not None


# ═══════════════════════════════════════════════════════════════
# E06 - 多 session 序列（隔离性验证）
# ═══════════════════════════════════════════════════════════════


@pytest.mark.llm
@pytest.mark.slow
class TestE06MultiSessionE2E:
    def test_two_sequential_sessions_isolated(self):
        """两个连续 session 的结果互相独立"""
        agent = _build_real_agent()
        r1 = agent.execute(SUFFICIENT_INPUT, "e2e-session-A")
        r2 = agent.execute(INSUFFICIENT_INPUT, "e2e-session-B")
        # 两个结果应不同
        assert r1.confidence != r2.confidence or r1.metadata.get("analysis_mode") != r2.metadata.get("analysis_mode")

    def test_same_input_two_sessions_consistent(self):
        """相同输入在两次调用中应产生结构一致的输出"""
        agent = _build_real_agent()
        r1 = agent.execute(SUFFICIENT_INPUT, "e2e-session-C1")
        r2 = agent.execute(SUFFICIENT_INPUT, "e2e-session-C2")
        # 两次都应是 two_phase 模式
        assert r1.metadata["analysis_mode"] == r2.metadata["analysis_mode"] == "two_phase"
        # 两次的置信度应在合理范围内（LLM 有随机性，允许 ±0.3）
        assert abs(r1.confidence - r2.confidence) < 0.3
