"""
ST-3 (2026-03-01): node_guard 装饰器单元测试

验收标准（来自 sf/governance/ACTION_PLAN.md）：
- 模拟 LLM 调用抛出异常 → 工作流继续，errors 字段有记录
- GraphInterrupt 必须传播（不被吞掉）
- sync / async 节点均覆盖
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from intelligent_project_analyzer.workflow.node_guard import (
    _build_fallback,
    _log_node_error,
    _maybe_reraise,
    node_guard,
)


# ---------------------------------------------------------------------------
# Fake LangGraph GraphInterrupt（测试环境可能无 langgraph）
# ---------------------------------------------------------------------------

try:
    from langgraph.errors import GraphInterrupt
except ImportError:
    # 本地 stub，仅供测试
    class GraphInterrupt(Exception):  # type: ignore[no-redef]
        pass


# ---------------------------------------------------------------------------
# 辅助：简单的 fake state / self
# ---------------------------------------------------------------------------

FAKE_STATE: Dict[str, Any] = {"input": "test"}


class FakeWorkflow:
    """模拟持有节点方法的工作流对象。"""


# ---------------------------------------------------------------------------
# 1. sync 节点：正常执行
# ---------------------------------------------------------------------------


class TestSyncNodeSuccess:
    def test_success_returns_original_result(self):
        @node_guard(fallback={"errors": [], "status": "fallback"})
        def _my_node(self, state):
            return {"output": "ok"}

        result = _my_node(FakeWorkflow(), FAKE_STATE)
        assert result == {"output": "ok"}

    def test_decorator_preserves_function_name(self):
        @node_guard(fallback={"errors": []})
        def _named_node(self, state):
            return {}

        assert _named_node.__name__ == "_named_node"


# ---------------------------------------------------------------------------
# 2. sync 节点：LLM 抛出网络错误 → fallback 返回
# ---------------------------------------------------------------------------


class TestSyncNodeException:
    def test_exception_returns_fallback_with_errors(self):
        @node_guard(fallback={"errors": [], "status": "fallback"})
        def _failing_node(self, state):
            raise ConnectionError("LLM 调用超时")

        result = _failing_node(FakeWorkflow(), FAKE_STATE)

        assert result["status"] == "fallback"
        assert isinstance(result["errors"], list)
        assert len(result["errors"]) == 1
        assert "ConnectionError" in result["errors"][0]
        assert "LLM 调用超时" in result["errors"][0]

    def test_asyncio_timeout_returns_fallback(self):
        @node_guard(fallback={"errors": []})
        def _timeout_node(self, state):
            raise asyncio.TimeoutError()

        result = _timeout_node(FakeWorkflow(), FAKE_STATE)

        assert len(result["errors"]) == 1
        assert "TimeoutError" in result["errors"][0]

    def test_fallback_dict_is_copy_not_mutated(self):
        """多次失败不应累积同一个 list。"""
        fallback = {"errors": [], "status": "fallback"}

        @node_guard(fallback=fallback)
        def _fail_node(self, state):
            raise ValueError("boom")

        _ = _fail_node(FakeWorkflow(), FAKE_STATE)
        result2 = _fail_node(FakeWorkflow(), FAKE_STATE)

        # 第二次调用返回的 errors 应只有 1 条
        assert len(result2["errors"]) == 1
        # 原始 fallback 不应被修改
        assert fallback["errors"] == []

    def test_node_name_included_in_error(self):
        @node_guard(fallback={"errors": []})
        def _calibration_questionnaire_node(self, state):
            raise RuntimeError("some error")

        result = _calibration_questionnaire_node(FakeWorkflow(), FAKE_STATE)
        assert "_calibration_questionnaire_node" in result["errors"][0]


# ---------------------------------------------------------------------------
# 3. sync 节点：GraphInterrupt 必须透传
# ---------------------------------------------------------------------------


class TestSyncGraphInterruptPropagation:
    def test_graph_interrupt_is_reraised(self):
        @node_guard(fallback={"errors": []})
        def _questionnaire_node(self, state):
            raise GraphInterrupt("等待用户响应")

        with pytest.raises(GraphInterrupt):
            _questionnaire_node(FakeWorkflow(), FAKE_STATE)

    def test_graph_interrupt_not_in_errors(self):
        """确保 GraphInterrupt 不被记录到 errors 中。"""

        @node_guard(fallback={"errors": []})
        def _interrupt_node(self, state):
            raise GraphInterrupt("pause")

        with pytest.raises(GraphInterrupt):
            _interrupt_node(FakeWorkflow(), FAKE_STATE)
        # 如果到这里，证明 GraphInterrupt 确实传播了


# ---------------------------------------------------------------------------
# 4. async 节点：正常执行
# ---------------------------------------------------------------------------


class TestAsyncNodeSuccess:
    def test_async_success_returns_original_result(self):
        @node_guard(fallback={"errors": []})
        async def _async_node(self, state):
            return {"async_output": True}

        result = asyncio.get_event_loop().run_until_complete(_async_node(FakeWorkflow(), FAKE_STATE))
        assert result == {"async_output": True}

    def test_async_decorator_preserves_function_name(self):
        @node_guard(fallback={"errors": []})
        async def _async_named_node(self, state):
            return {}

        assert _async_named_node.__name__ == "_async_named_node"


# ---------------------------------------------------------------------------
# 5. async 节点：异常 → fallback
# ---------------------------------------------------------------------------


class TestAsyncNodeException:
    def test_async_exception_returns_fallback(self):
        @node_guard(fallback={"errors": [], "status": "async_fallback"})
        async def _async_failing_node(self, state):
            raise ConnectionError("async LLM 超时")

        result = asyncio.get_event_loop().run_until_complete(_async_failing_node(FakeWorkflow(), FAKE_STATE))
        assert result["status"] == "async_fallback"
        assert len(result["errors"]) == 1
        assert "ConnectionError" in result["errors"][0]

    def test_async_timeout_returns_fallback(self):
        @node_guard(fallback={"errors": []})
        async def _async_timeout_node(self, state):
            raise asyncio.TimeoutError()

        result = asyncio.get_event_loop().run_until_complete(_async_timeout_node(FakeWorkflow(), FAKE_STATE))
        assert len(result["errors"]) == 1

    def test_async_graph_interrupt_is_reraised(self):
        @node_guard(fallback={"errors": []})
        async def _async_interrupt_node(self, state):
            raise GraphInterrupt("async pause")

        with pytest.raises(GraphInterrupt):
            asyncio.get_event_loop().run_until_complete(_async_interrupt_node(FakeWorkflow(), FAKE_STATE))


# ---------------------------------------------------------------------------
# 6. 参数校验
# ---------------------------------------------------------------------------


class TestNodeGuardValidation:
    def test_missing_errors_key_raises_value_error(self):
        with pytest.raises(ValueError, match="errors"):

            @node_guard(fallback={"status": "fallback"})  # 缺少 'errors' key
            def _bad_node(self, state):
                return {}

    def test_empty_errors_list_is_valid(self):
        @node_guard(fallback={"errors": []})
        def _ok_node(self, state):
            return {"output": "ok"}

        result = _ok_node(FakeWorkflow(), FAKE_STATE)
        assert result == {"output": "ok"}


# ---------------------------------------------------------------------------
# 7. 内部辅助函数
# ---------------------------------------------------------------------------


class TestInternalHelpers:
    def test_build_fallback_appends_error(self):
        fallback = {"errors": [], "status": "base"}
        exc = ValueError("test error")
        result = _build_fallback(fallback, "my_node", exc)

        assert result["status"] == "base"
        assert len(result["errors"]) == 1
        assert "[my_node]" in result["errors"][0]
        assert "ValueError" in result["errors"][0]
        assert "test error" in result["errors"][0]

    def test_build_fallback_does_not_modify_original(self):
        original_fallback = {"errors": [], "status": "base"}
        _build_fallback(original_fallback, "node", ValueError("x"))
        assert original_fallback["errors"] == []

    def test_maybe_reraise_passes_regular_exception(self):
        exc = ValueError("normal error")
        try:
            _maybe_reraise(exc)  # 不应抛出
        except Exception:
            pytest.fail("_maybe_reraise should not raise for regular exceptions")

    def test_maybe_reraise_raises_graph_interrupt(self):
        exc = GraphInterrupt("pause")
        with pytest.raises(GraphInterrupt):
            _maybe_reraise(exc)

    def test_log_node_error_calls_logger(self):
        with patch("intelligent_project_analyzer.workflow.node_guard.logger") as mock_logger:
            _log_node_error("_test_node", ValueError("oops"))
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args[0]
            assert "_test_node" in str(call_args)


# ---------------------------------------------------------------------------
# 8. 集成场景：模拟 LLM 异常，工作流继续
# ---------------------------------------------------------------------------


class TestWorkflowContinuationOnLLMError:
    """
    验收标准: 模拟 LLM 调用抛出异常，工作流能继续而非崩溃，errors 字段有记录。
    """

    def test_llm_error_workflow_continues(self):
        """模拟 _progressive_step1_node 场景: LLM 网络异常。"""

        FALLBACK = {"errors": [], "questionnaire_completed": False}

        @node_guard(fallback=FALLBACK)
        def _progressive_step1_node(self, state):
            # 模拟 LLM 调用失败
            raise ConnectionError("OpenAI API 连接失败")

        workflow_state = {"input": "设计一个150平米住宅", "errors": []}
        result = _progressive_step1_node(FakeWorkflow(), workflow_state)

        # 工作流继续（没有抛出异常）
        assert isinstance(result, dict)
        # errors 字段有记录
        assert len(result["errors"]) > 0
        assert "ConnectionError" in result["errors"][0]
        assert "_progressive_step1_node" in result["errors"][0]
        # fallback 字段存在
        assert result["questionnaire_completed"] is False

    def test_multiple_nodes_independent_fallbacks(self):
        """多节点使用各自独立的 fallback，互不影响。"""

        @node_guard(fallback={"errors": [], "stage": "step1"})
        def _step1(self, state):
            raise RuntimeError("step1 失败")

        @node_guard(fallback={"errors": [], "stage": "step2"})
        def _step2(self, state):
            return {"stage": "step2_success"}

        fw = FakeWorkflow()
        r1 = _step1(fw, FAKE_STATE)
        r2 = _step2(fw, FAKE_STATE)

        assert r1["stage"] == "step1"
        assert len(r1["errors"]) == 1
        assert r2 == {"stage": "step2_success"}
        # step2 的 fallback errors 没有被污染
