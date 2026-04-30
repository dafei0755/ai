"""
resume 流程回归测试

覆盖场景：
- 工作流在 pdf_generator 节点正常收尾
- graph state 未写入 final_report，且 total_batches/completed_batches 为默认空值
- 仍应判定为 completed（不能误判提前结束 failed）
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


class _FakeGraph:
    async def astream(self, _command, _config):
        # 模拟 resume 流程仅产出 pdf_generator 节点结果
        yield {
            "pdf_generator": {
                "detail": "生成最终交付文档",
                "pdf_path": "data/reports/resume-regression.pdf",
            }
        }

    async def aget_state(self, _config):
        # 模拟 state 中缺少 final_report 和批次信息（旧逻辑会误判 failed）
        return SimpleNamespace(values={})


class _FakeWorkflow:
    def __init__(self):
        self.graph = _FakeGraph()


@pytest.mark.asyncio
async def test_resume_pdf_generator_without_final_report_should_complete(client, mock_redis, monkeypatch):
    from intelligent_project_analyzer.api import server as server_module

    session_id = "analysis-regression-pdf-end"

    # 用本地 dict 维护会话状态，避免依赖 Redis 实现细节
    session_store = {
        session_id: {
            "session_id": session_id,
            "status": "waiting_for_input",
            "interrupt_data": {"interaction_type": "final_review"},
            "current_node": "report_guard",
            "detail": "等待确认",
            "progress": 0.95,
            "events": [],
            "history": [],
        }
    }

    async def _get_session(sid):
        data = session_store.get(sid)
        return dict(data) if data else None

    async def _update_session(sid, payload):
        if sid not in session_store:
            return False
        session_store[sid].update(payload)
        return True

    # 挂接 session manager 方法
    sm = server_module.session_manager
    sm.get = AsyncMock(side_effect=_get_session)
    sm.update = AsyncMock(side_effect=_update_session)
    sm.list_all_sessions = AsyncMock(return_value=[session_id])

    # 避免测试中产生无关副作用
    monkeypatch.setattr(server_module, "broadcast_to_websockets", AsyncMock(return_value=None))
    monkeypatch.setattr(server_module, "sync_checkpoint_to_redis", AsyncMock(return_value=False))

    # 注入 fake workflow（resume 入口依赖 workflows[session_id]）
    server_module.workflows[session_id] = _FakeWorkflow()

    try:
        response = await client.post(
            "/api/analysis/resume",
            json={
                "session_id": session_id,
                "resume_value": {"action": "approve"},
            },
        )

        assert response.status_code == 200

        # 等待 BackgroundTasks 完成
        for _ in range(50):
            if session_store[session_id].get("status") in {"completed", "failed"}:
                break
            await asyncio.sleep(0.01)

        assert session_store[session_id]["status"] == "completed"
        assert session_store[session_id]["progress"] == 1.0
    finally:
        server_module.workflows.pop(session_id, None)
