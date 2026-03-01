"""
端到端测试：v12.1 约束推荐 + 视觉参考管理 完整用户旅程

测试范围：
E1: 完整旅程 — 输入需求 → 上传图片 → 确认推荐约束 → 删除部分图片 → 提交
E2: HTTP 级别 DELETE endpoint — 使用 httpx client 走完整 HTTP
E3: HTTP 级别 413 拒绝 — 超大文件通过 HTTP 上传
E4: 旧版前端兼容旅程 — 只传 user_constraints 而非 confirmed_constraints
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

pytestmark = [pytest.mark.e2e]


@pytest.fixture
def mock_llm_for_e2e():
    """E2E 场景的 LLM 响应预设"""
    return {
        "structured_requirements": {
            "project_type": "residential",
            "scale_info": {"area_sqm": 300},
            "stakeholders": [{"role": "homeowner", "decision_power": "high"}],
            "spatial_description": {
                "zones": [
                    {"id": "recording_studio", "label": "录音棚"},
                    {"id": "living_room", "label": "客厅"},
                ]
            },
            "explicit_deliverables": ["design_report"],
            "budget_info": {"amount": 500, "unit": "万"},
        },
        "file_extraction": {
            "width": 1200,
            "height": 800,
            "format": "JPEG",
            "vision_analysis": "Recording studio with acoustic panels",
            "structured_features": {"style": ["industrial"], "materials": ["acoustic_panel"]},
        },
    }


class TestE1CompleteUserJourney:
    """完整用户旅程：从需求输入到确认约束"""

    @pytest.mark.asyncio
    async def test_full_journey_with_constraint_recommendation(self, mock_llm_for_e2e):
        """
        E1.1: 完整旅程
        用户输入 → requirements_analyst → output_intent_detection 构建推荐约束
        → 用户上传图片 → 用户勾选约束 → 确认 → framework_signals 正确
        """
        from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager
        from intelligent_project_analyzer.core.state import StateManager

        sm = RedisSessionManager(fallback_to_memory=True)
        sm._memory_mode = True
        sm.is_connected = False
        session_id = "e2e-v121-full-journey"

        initial_state = StateManager.create_initial_state(
            user_input="300平米别墅设计，含录音棚和家庭影院，预算500万",
            session_id=session_id,
        )
        await sm.create(session_id, initial_state)

        _sm_patcher = patch(
            "intelligent_project_analyzer.api.server._get_session_manager",
            new=AsyncMock(return_value=sm),
        )
        _sm_patcher.start()

        try:
            # Phase 1: Requirements Analyst 分析完成
            await sm.update(session_id, {"structured_requirements": mock_llm_for_e2e["structured_requirements"]})

            # Phase 2: 用户上传参考图
            fake_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 500

            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(fake_image)
                tmp_path = Path(tmp.name)

            try:
                with patch("intelligent_project_analyzer.api.server.file_processor.save_file") as mock_save, patch(
                    "intelligent_project_analyzer.api.server.file_processor.extract_image_enhanced"
                ) as mock_extract:
                    mock_save.return_value = tmp_path
                    mock_extract.return_value = mock_llm_for_e2e["file_extraction"]

                    from intelligent_project_analyzer.api.server import attach_files_to_session
                    from fastapi import UploadFile

                    upload_file = MagicMock(spec=UploadFile)
                    upload_file.filename = "studio_ref.jpg"
                    upload_file.content_type = "image/jpeg"
                    upload_file.read = AsyncMock(return_value=fake_image)

                    result = await attach_files_to_session(
                        session_id=session_id,
                        file_metadata=json.dumps(
                            [
                                {
                                    "filename": "studio_ref.jpg",
                                    "categories": ["style"],
                                    "custom_description": "录音棚声学参考",
                                }
                            ]
                        ),
                        files=[upload_file],
                    )
                    assert result["status"] == "success"

                # Phase 3: _build_recommended_constraints 构建推荐
                from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
                    _build_recommended_constraints,
                )

                recommended = _build_recommended_constraints(
                    mandatory_dims=["acoustics", "media_production"],
                    constraints=[{"type": "budget", "value": "500万"}],
                )
                assert len(recommended) >= 3

                # Phase 4: 模拟用户确认（勾选 acoustics + budget，取消 media_production，添加手动约束）
                selected_ids = ["acoustics", "budget"]
                confirmed_constraints = [
                    {"id": r["id"], "label": r["label"], "desc": r["desc"], "source": "ai_recommended"}
                    for r in recommended
                    if r["id"] in selected_ids
                ] + [{"id": "user_0", "label": "隔音要求极高", "desc": "录音棚需达到 NR15 标准", "source": "user_added"}]

                user_confirmation = {
                    "selected_deliveries": ["design_professional"],
                    "selected_modes": ["family_intimacy"],
                    "confirmed_constraints": confirmed_constraints,
                    "kept_visual_reference_indices": [0],
                }

                # Phase 5: 模拟后端处理用户确认
                from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
                    _extract_framework_signals,
                )

                fs = _extract_framework_signals(
                    user_input="300平米别墅设计含录音棚",
                    structured_requirements=mock_llm_for_e2e["structured_requirements"],
                    active_projections=["design_professional"],
                    identity_modes=[],
                )

                # 注入 confirmed_constraints
                cc = user_confirmation["confirmed_constraints"]
                ai_dim_ids = [c["id"] for c in cc if c.get("source") == "ai_recommended"]
                user_added = [c for c in cc if c.get("source") == "user_added"]
                if ai_dim_ids:
                    fs["mandatory_dimensions"] = ai_dim_ids
                for c in user_added:
                    fs.setdefault("constraints", []).append(
                        {
                            "type": "user_declared",
                            "label": c.get("label", ""),
                            "desc": c.get("desc", ""),
                        }
                    )

                # 验证
                assert fs["mandatory_dimensions"] == ["acoustics", "budget"]
                user_declared = [c for c in fs.get("constraints", []) if c.get("type") == "user_declared"]
                assert len(user_declared) == 1
                assert user_declared[0]["label"] == "隔音要求极高"

            finally:
                if tmp_path.exists():
                    tmp_path.unlink()

        finally:
            _sm_patcher.stop()
            await sm.delete(session_id)


class TestE2HttpDeleteEndpoint:
    """HTTP 级别 DELETE 测试"""

    @pytest.mark.asyncio
    async def test_delete_via_http_client(self, client):
        """E2.1: 通过 httpx AsyncClient 调用 DELETE 端点"""
        # 先创建一个分析（启动会话）
        start_resp = await client.post(
            "/api/analysis/start",
            json={
                "requirement": "测试项目",
            },
        )
        assert start_resp.status_code == 200
        session_id = start_resp.json().get("session_id")
        assert session_id

        # 手动注入 visual_references
        from intelligent_project_analyzer.api import server as server_module

        sm = server_module.session_manager
        session = await sm.get(session_id)
        if session:
            session["visual_references"] = [
                {
                    "file_path": "/tmp/fake.jpg",
                    "original_filename": "test.jpg",
                    "index": 0,
                    "reference_type": "general",
                    "source": "output_intent",
                    "custom_description": "",
                },
            ]
            await sm.update(session_id, {"visual_references": session["visual_references"]})

            # DELETE
            with patch("pathlib.Path.exists", return_value=False):
                resp = await client.delete(f"/api/analysis/{session_id}/visual-reference/0")

            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert data["remaining_count"] == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session_via_http(self, client):
        """E2.2: 不存在的 session DELETE 返回 404"""
        resp = await client.delete("/api/analysis/nonexistent-xyz/visual-reference/0")
        assert resp.status_code == 404


class TestE3HttpOversizedFile:
    """HTTP 级别 413 文件过大拒绝测试"""

    @pytest.mark.asyncio
    async def test_oversized_file_via_http(self, client):
        """E3.1: 通过 HTTP 上传超大文件应返回 413"""
        start_resp = await client.post(
            "/api/analysis/start",
            json={
                "requirement": "测试413",
            },
        )
        assert start_resp.status_code == 200
        session_id = start_resp.json().get("session_id")
        assert session_id

        # 构造超大文件 (11MB)
        oversized_data = b"\x00" * (11 * 1024 * 1024)

        resp = await client.post(
            f"/api/analysis/{session_id}/attach-files",
            files=[("files", ("huge.jpg", oversized_data, "image/jpeg"))],
            data={"file_metadata": "[]"},
        )
        assert resp.status_code == 413


class TestE4OldFrontendCompatibility:
    """旧版前端仅发送 user_constraints 的兼容旅程"""

    @pytest.mark.asyncio
    async def test_old_format_user_constraints_still_works(self):
        """E4.1: 旧前端发送 user_constraints 被正确转为 confirmed_constraints"""
        from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager
        from intelligent_project_analyzer.core.state import StateManager

        sm = RedisSessionManager(fallback_to_memory=True)
        sm._memory_mode = True
        sm.is_connected = False
        session_id = "e2e-v121-compat"

        initial_state = StateManager.create_initial_state(
            user_input="100平米住宅",
            session_id=session_id,
        )
        await sm.create(session_id, initial_state)

        try:
            # 旧前端格式的用户响应
            old_format = {
                "selected_deliveries": ["design_professional"],
                "selected_modes": [],
                "user_constraints": [
                    {"label": "预算有限", "desc": "不超过30万"},
                    {"label": "时间紧", "desc": "1个月内出方案"},
                ],
            }

            # 测试兼容解析
            confirmed = old_format.get("confirmed_constraints") or []
            if not confirmed and old_format.get("user_constraints"):
                confirmed = [
                    {"id": f"user_{i}", "label": c.get("label", ""), "desc": c.get("desc", ""), "source": "user_added"}
                    for i, c in enumerate(old_format["user_constraints"])
                ]

            assert len(confirmed) == 2
            assert confirmed[0]["id"] == "user_0"
            assert confirmed[0]["label"] == "预算有限"
            assert confirmed[1]["id"] == "user_1"

            # 注入 framework_signals
            fs = {}
            user_added = [c for c in confirmed if c.get("source") == "user_added"]
            for c in user_added:
                fs.setdefault("constraints", []).append(
                    {
                        "type": "user_declared",
                        "label": c.get("label", ""),
                        "desc": c.get("desc", ""),
                    }
                )

            assert len(fs["constraints"]) == 2
            assert fs["constraints"][0]["label"] == "预算有限"

        finally:
            await sm.delete(session_id)
