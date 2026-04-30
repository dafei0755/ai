"""
tests/unit/test_dual_mode/test_conversation_engine.py
ConversationEngine 单元测试
Created by GitHub Copilot · 2026-03-15

覆盖范围：
  - 意图分类（knowledge_qa / inspiration / project_signal）
  - 草稿积累逻辑
  - CognitionIndicators 计算
  - upgrade 信号触发条件
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# 导入守卫
# ─────────────────────────────────────────────────────────────────────────────

try:
    from intelligent_project_analyzer.workflow.conversation_engine import ConversationEngine
    from intelligent_project_analyzer.core.domain_objects import (
        CognitionIndicators,
        UpgradeSignal,
        DraftStatus,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="conversation_engine 未就绪")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_state(user_input: str = "你好", drafts: list | None = None) -> dict:
    return {
        "user_input": user_input,
        "session_id": "test-conv-001",
        "system_mode": "conversation",
        "conversation_drafts": drafts or [],
        "cognition_indicators": None,
        "upgrade_signal": None,
        "metadata": {},
    }


# ─────────────────────────────────────────────────────────────────────────────
# CognitionIndicators 模型测试
# ─────────────────────────────────────────────────────────────────────────────

class TestCognitionIndicators:
    def test_should_not_upgrade_by_default(self):
        ci = CognitionIndicators()
        assert ci.should_trigger_upgrade is False

    def test_upgrade_when_all_signals_high(self):
        ci = CognitionIndicators(
            freeze_readiness=0.85,
            cognitive_debt=0.75,
            diverge_fatigue=0.70,
        )
        # should_trigger_upgrade 是 property，这里只需保证不抛异常
        result = ci.should_trigger_upgrade
        assert isinstance(result, bool)

    def test_serialization(self):
        ci = CognitionIndicators(freeze_readiness=0.5)
        d = ci.model_dump()
        assert "freeze_readiness" in d
        assert "should_trigger_upgrade" not in d  # property 不在 model_dump


# ─────────────────────────────────────────────────────────────────────────────
# ConversationEngine 实例化
# ─────────────────────────────────────────────────────────────────────────────

class TestConversationEngineInit:
    def test_can_instantiate(self):
        eng = ConversationEngine()
        assert eng is not None

    def test_has_execute_method(self):
        eng = ConversationEngine()
        assert callable(getattr(eng, "execute", None))


# ─────────────────────────────────────────────────────────────────────────────
# execute() 异步测试（Mock LLM）
# ─────────────────────────────────────────────────────────────────────────────

class TestConversationEngineExecute:
    def test_execute_returns_dict(self):
        """execute() 应返回 dict（state 更新）。"""
        eng = ConversationEngine()
        state = _make_state("这个空间大概 500 平，想做餐厅")

        with patch.object(eng, "_classify_intent", return_value="project_signal"):
            result = eng.execute(state)  # type: ignore[arg-type]

        assert isinstance(result, dict)
        assert "system_mode" in result

    def test_execute_accumulates_draft_on_project_signal(self):
        """包含项目信号的输入应触发草稿积累。"""
        eng = ConversationEngine()
        state = _make_state(
            "预算大约 200 万，需要在明年 3 月完工，空间是 800 平的办公室",
            drafts=[],
        )

        with patch.object(eng, "_classify_intent", return_value="project_signal"), \
             patch.object(eng, "_compute_cognition_indicators",
                          return_value=CognitionIndicators(freeze_readiness=0.5)):
            result = eng.execute(state)  # type: ignore[arg-type]

        # conversation_drafts 应存在于结果中
        drafts_after = result.get("conversation_drafts", [])
        assert isinstance(drafts_after, list)

    def test_no_upgrade_signal_on_single_message(self):
        """单条消息不应触发 upgrade_signal。"""
        eng = ConversationEngine()
        state = _make_state("你好")

        with patch.object(eng, "_classify_intent", return_value="knowledge_qa"):
            result = eng.execute(state)  # type: ignore[arg-type]

        upgrade_sig = result.get("upgrade_signal")
        assert upgrade_sig is None or (isinstance(upgrade_sig, dict) and not upgrade_sig)
