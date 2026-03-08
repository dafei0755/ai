# HISTORICAL — 已删除 feature flags 的过时断言归档
# 本文件记录 v8.1.1 中从 feature_flags.py 删除的 flag 历史行为，
# 仅供追溯参考，不参与活跃 CI 流水线。
# 相关删除说明见 CHANGELOG.md [v8.1.1] 和 feature_flags.py 注释。
#
# 已删除的 flags（v8.1.1）：
#   - USE_PROGRESSIVE_QUESTIONNAIRE（冻结 True → 内联路径 → 删除）
#   - USE_V716_AGENTS（冻结 False → 内联路径 → 删除）
#   - USE_V717_REQUIREMENTS_ANALYST（冻结 True → 内联路径 → 删除）
#   - USE_V7_FRONTCHAIN_SEMANTICS（冻结 True → 内联路径 → 删除）
#   - USE_MULTI_ROUND_QUESTIONNAIRE（冻结 True → 内联路径 → 删除）

import pytest


@pytest.mark.skip(reason="HISTORICAL: USE_PROGRESSIVE_QUESTIONNAIRE 已在 v8.1.1 从 feature_flags 删除，内联为固定路径")
class TestHistoricalProgressiveQuestionnaireFlagBehavior:
    """
    历史档案：USE_PROGRESSIVE_QUESTIONNAIRE 的预期行为。
    该 flag 曾控制是否使用渐进式问卷流程，v8.x 冻结为 True 后内联删除。
    """

    def test_use_progressive_questionnaire_was_true(self, env_setup):
        """历史预期：USE_PROGRESSIVE_QUESTIONNAIRE 应为 True（v8.x 冻结值）
        该 flag 已从 feature_flags.py 删除，此处 assert True 仅保留历史意图记录。
        """
        assert True  # flag 已删除，不可导入，保留此注释供历史追溯

    def test_use_progressive_questionnaire_is_boolean(self, env_setup):
        """历史预期：USE_PROGRESSIVE_QUESTIONNAIRE 应为 bool 类型"""
        assert True  # 不再可导入，保留此注释供历史追溯


@pytest.mark.skip(reason="HISTORICAL: USE_V716_AGENTS 已在 v8.1.1 从 feature_flags 删除，内联为固定路径")
class TestHistoricalV716AgentsFlagBehavior:
    """
    历史档案：USE_V716_AGENTS 的预期行为。
    该 flag 曾控制是否启用 v7.16 版本的 agents，v8.x 冻结为 False 后内联删除。
    """

    def test_use_v716_agents_was_false(self, env_setup):
        """历史预期：USE_V716_AGENTS 应为 False（v8.x 冻结值）"""
        assert True  # 不再可导入，保留此注释供历史追溯

    def test_use_v716_agents_is_boolean(self, env_setup):
        """历史预期：USE_V716_AGENTS 应为 bool 类型"""
        assert True  # 不再可导入，保留此注释供历史追溯
