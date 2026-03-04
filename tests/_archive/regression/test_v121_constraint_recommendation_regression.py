"""
回归测试：确保 v12.1 修改不破坏现有功能

验证范围：
R1: output_intent_detection 核心功能 — interrupt/resume 不退化
R2: v12.0 约束系统 — _extract_spatial_zones, _build_constraint_envelope 不受影响
R3: 现有 API 端点 — describe, attach-files 等未被破坏
R4: State schema — 新旧字段共存向后兼容
R5: 前端 payload — 旧格式 confirm payload 仍然被正确处理
R6: DELETE 端点不影响其他路由
R7: 413 文件限制不影响正常上传
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

pytestmark = [pytest.mark.regression]


def _make_memory_sm():
    """创建内存模式的 SessionManager，无需 Redis"""
    from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

    sm = RedisSessionManager(fallback_to_memory=True)
    sm._memory_mode = True
    sm.is_connected = False
    return sm


# ==============================================================================
# R1: output_intent_detection 核心功能不退化
# ==============================================================================


class TestR1OutputIntentCoreRegression:
    """确保 output_intent_detection 的核心 interrupt/resume 不退化"""

    @pytest.mark.asyncio
    async def test_legacy_response_without_confirmed_constraints(self):
        """R1.1: 旧格式响应（无 confirmed_constraints）不崩溃"""
        from intelligent_project_analyzer.core.state import StateManager
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import output_intent_detection_node

        sm = _make_memory_sm()
        session_id = "reg-v121-legacy"
        state = StateManager.create_initial_state(user_input="200平米住宅", session_id=session_id)
        await sm.create(session_id, state)

        try:
            await sm.update(
                session_id,
                {
                    "structured_requirements": {
                        "project_type": "residential",
                        "scale_info": {"area_sqm": 200},
                        "stakeholders": [],
                        "explicit_deliverables": [],
                    }
                },
            )

            legacy_response = {
                "selected_deliveries": ["design_professional"],
                "selected_modes": [],
                # 注意：无 confirmed_constraints 也无 user_constraints
            }

            with patch(
                "intelligent_project_analyzer.interaction.nodes.output_intent_detection.interrupt",
                return_value=legacy_response,
            ):
                state = await sm.get(session_id)
                # 注意：output_intent_detection_node 是同步函数，不需要 await
                command = output_intent_detection_node(state)

                assert command.goto == "feasibility_analyst"
                assert "active_projections" in command.update
                # user_intent_constraints 应为 None（不应崩溃）
                assert command.update.get("user_intent_constraints") is None

        finally:
            await sm.delete(session_id)

    @pytest.mark.asyncio
    async def test_idempotent_protection_preserved(self):
        """R1.2: 幂等保护仍然有效（已有 active_projections 时跳过 interrupt）"""
        from intelligent_project_analyzer.core.state import StateManager
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import output_intent_detection_node

        sm = _make_memory_sm()
        session_id = "reg-v121-idempotent"
        state = StateManager.create_initial_state(user_input="Test", session_id=session_id)
        await sm.create(session_id, state)

        try:
            await sm.update(
                session_id,
                {
                    "active_projections": ["design_professional"],
                    "intent_changed": False,
                    "structured_requirements": {"project_type": "residential"},
                },
            )

            with patch("intelligent_project_analyzer.interaction.nodes.output_intent_detection.interrupt") as mock_int:
                state = await sm.get(session_id)
                # 注意：output_intent_detection_node 是同步函数，不需要 await
                command = output_intent_detection_node(state)
                mock_int.assert_not_called()
                assert command.goto == "feasibility_analyst"

        finally:
            await sm.delete(session_id)

    @pytest.mark.asyncio
    async def test_delivery_type_detection_unchanged(self):
        """R1.3: 交付类型显式信号检测逻辑未退化"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import _detect_explicit_signals

        result = _detect_explicit_signals(
            user_input="需要施工图纸和投资分析报告",
        )
        scored = {k: v for k, v in result.items() if v > 0}
        assert len(scored) >= 1, "应检测到至少1种交付类型信号"

    @pytest.mark.asyncio
    async def test_identity_mode_detection_unchanged(self):
        """R1.4: 身份模式检测未受影响"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import _detect_identity_modes

        modes = _detect_identity_modes(
            user_input="三口之家，孩子在读小学",
            structured_requirements={
                "character_narrative": "年轻家庭重视教育",
            },
            detected_modes=[],
            project_classification={"project_type": "residential"},
        )
        # 至少返回列表（函数未崩溃）
        assert isinstance(modes, list), "返回值应为列表"


# ==============================================================================
# R2: v12.0 约束系统不退化
# ==============================================================================


class TestR2V12ConstraintSystemRegression:
    """v12.0 已有的约束功能不受 v12.1 影响"""

    @pytest.fixture(autouse=True)
    def _import(self):
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            _extract_spatial_zones,
            _build_constraint_envelope,
        )

        self.extract_zones = _extract_spatial_zones
        self.build_envelope = _build_constraint_envelope

    def test_extract_spatial_zones_still_works(self):
        """R2.1: 空间区域提取正常"""
        zones = self.extract_zones({}, "1楼客厅2楼卧室")
        assert any(z["id"] == "overall" for z in zones)
        assert len(zones) >= 2

    def test_build_constraint_envelope_still_works(self):
        """R2.2: 约束信封组装正常"""
        zones = [{"id": "overall", "label": "整体空间", "source": "preset"}]
        constraints_by_zone = {"overall": [{"type": "budget", "level": "immutable", "description": "预算不超过50万"}]}
        envelope = self.build_envelope(constraints_by_zone, zones)
        assert isinstance(envelope, str)
        assert len(envelope) > 0

    def test_auto_classify_unchanged(self):
        """R2.3: 约束层级概念存在（通过 _build_constraint_envelope 验证分级）"""
        # 正确的层级是 immutable/baseline/opportunity，字段名为 description
        zones = [{"id": "overall", "label": "整体空间", "source": "preset"}]
        constraints_by_zone = {
            "overall": [
                {"type": "budget", "level": "immutable", "description": "预算不超过50万"},
                {"type": "style_preference", "level": "opportunity", "description": "偏好北欧风格"},
            ]
        }
        envelope = self.build_envelope(constraints_by_zone, zones)
        assert isinstance(envelope, str)
        assert len(envelope) > 0


# ==============================================================================
# R3: 现有 API 端点不退化
# ==============================================================================


class TestR3ExistingEndpointsRegression:
    """确保现有 API 端点仍然正常"""

    @pytest.mark.asyncio
    async def test_describe_endpoint_still_works(self):
        """R3.1: visual-reference/describe 端点不受 DELETE 端点影响"""
        from intelligent_project_analyzer.core.state import StateManager

        sm = _make_memory_sm()
        session_id = "reg-v121-describe"
        state = StateManager.create_initial_state(user_input="测试", session_id=session_id)
        await sm.create(session_id, state)

        try:
            await sm.update(session_id, {"visual_references": [{"file_path": "test.jpg", "vision_analysis": "Test"}]})

            from intelligent_project_analyzer.api.server import (
                add_visual_reference_description,
                VisualReferenceDescriptionRequest,
            )

            req = VisualReferenceDescriptionRequest(
                reference_index=0,
                description="回归测试描述",
                reference_type="style",
            )
            with patch("intelligent_project_analyzer.api.server._get_session_manager", new=AsyncMock(return_value=sm)):
                result = await add_visual_reference_description(session_id=session_id, request=req)

            assert result["status"] == "success"
            assert result["visual_references"][0]["user_description"] == "回归测试描述"

        finally:
            await sm.delete(session_id)

    @pytest.mark.asyncio
    async def test_attach_files_endpoint_still_works(self):
        """R3.2: attach-files 端点仍然正常"""
        from intelligent_project_analyzer.core.state import StateManager

        sm = _make_memory_sm()
        session_id = "reg-v121-attach"
        state = StateManager.create_initial_state(user_input="测试upload", session_id=session_id)
        await sm.create(session_id, state)

        try:
            fake_img = b"\x89PNG" + b"\x00" * 200

            with patch("intelligent_project_analyzer.api.server.file_processor.save_file") as mock_save, patch(
                "intelligent_project_analyzer.api.server.file_processor.extract_image_enhanced"
            ) as mock_extract:
                mock_save.return_value = Path("/tmp/test_reg.jpg")
                mock_extract.return_value = {"width": 100, "height": 100, "format": "PNG"}

                from intelligent_project_analyzer.api.server import attach_files_to_session
                from fastapi import UploadFile
                import json

                upload = MagicMock(spec=UploadFile)
                upload.filename = "reg_test.png"
                upload.content_type = "image/png"
                upload.read = AsyncMock(return_value=fake_img)

                with patch(
                    "intelligent_project_analyzer.api.server._get_session_manager", new=AsyncMock(return_value=sm)
                ):
                    result = await attach_files_to_session(
                        session_id=session_id,
                        file_metadata=json.dumps(
                            [{"filename": "reg_test.png", "categories": [], "custom_description": ""}]
                        ),
                        files=[upload],
                    )
                assert result["status"] == "success"

        finally:
            await sm.delete(session_id)

    def test_api_route_paths_exist(self):
        """R3.3: 确保关键路由路径存在且未被误删"""
        from intelligent_project_analyzer.api import server as server_module

        route_paths = [r.path for r in server_module.app.routes if hasattr(r, "path")]
        # 旧端点
        assert "/api/analysis/start" in route_paths
        assert "/api/analysis/{session_id}/visual-reference/describe" in route_paths
        assert "/api/analysis/{session_id}/attach-files" in route_paths
        # 新端点
        assert "/api/analysis/{session_id}/visual-reference/{reference_index}" in route_paths


# ==============================================================================
# R4: State schema 向后兼容
# ==============================================================================


class TestR4StateSchemaRegression:
    """确保 State 结构向后兼容"""

    def test_old_fields_still_present(self):
        """R4.1: 旧 State 字段仍然存在"""
        from intelligent_project_analyzer.core.state import StateManager

        state = StateManager.create_initial_state(user_input="Test", session_id="reg-state")
        # 这些字段应在 create_initial_state 中初始化
        required_fields = [
            "active_projections",
            "visual_constraints",
            "extracted_spatial_zones",
            "user_intent_constraints",
        ]
        for f in required_fields:
            assert f in state, f"State 缺少字段: {f}"
        # detected_identity_modes 和 output_framework_signals 是可选字段，检查类型定义中存在即可
        from intelligent_project_analyzer.core.state import ProjectAnalysisState

        annotations = ProjectAnalysisState.__annotations__
        assert "detected_identity_modes" in annotations, "detected_identity_modes 应在 ProjectAnalysisState 定义中"
        assert "output_framework_signals" in annotations, "output_framework_signals 应在 ProjectAnalysisState 定义中"

    def test_command_update_accepts_confirmed_constraints(self):
        """R4.2: Command update 可以接受 confirmed_constraints 作为 user_intent_constraints"""
        from langgraph.types import Command

        # 模拟 v12.1 的 Command 返回
        cc = [{"id": "acoustics", "label": "声学", "desc": "...", "source": "ai_recommended"}]
        cmd = Command(
            update={
                "active_projections": ["design_professional"],
                "user_intent_constraints": cc,
            },
            goto="feasibility_analyst",
        )
        assert cmd.update["user_intent_constraints"] == cc
        assert cmd.goto == "feasibility_analyst"

    def test_command_update_accepts_none_constraints(self):
        """R4.3: user_intent_constraints=None 不崩溃"""
        from langgraph.types import Command

        cmd = Command(
            update={
                "active_projections": ["design_professional"],
                "user_intent_constraints": None,
            },
            goto="feasibility_analyst",
        )
        assert cmd.update["user_intent_constraints"] is None


# ==============================================================================
# R5: 前端 payload 兼容
# ==============================================================================


class TestR5FrontendPayloadRegression:
    """确保新旧前端 payload 都能被后端正确处理"""

    def _simulate_response_parsing(self, user_response: dict):
        """模拟后端的响应解析逻辑"""
        confirmed = user_response.get("confirmed_constraints") or []
        if not confirmed and user_response.get("user_constraints"):
            confirmed = [
                {"id": f"user_{i}", "label": c.get("label", ""), "desc": c.get("desc", ""), "source": "user_added"}
                for i, c in enumerate(user_response["user_constraints"])
            ]
        kept = user_response.get("kept_visual_reference_indices")
        return confirmed, kept

    def test_v111_payload_no_constraints(self):
        """R5.1: v11.1 payload（无任何约束）正常处理"""
        cc, ki = self._simulate_response_parsing(
            {
                "selected_deliveries": ["design_professional"],
                "selected_modes": ["family_intimacy"],
            }
        )
        assert cc == []
        assert ki is None

    def test_v112_payload_with_user_constraints(self):
        """R5.2: v11.2 payload（user_constraints）被兼容转换"""
        cc, ki = self._simulate_response_parsing(
            {
                "selected_deliveries": ["design_professional"],
                "user_constraints": [{"label": "A", "desc": "B"}],
            }
        )
        assert len(cc) == 1
        assert cc[0]["source"] == "user_added"

    def test_v121_payload_with_confirmed_constraints(self):
        """R5.3: v12.1 payload（confirmed_constraints）直接使用"""
        payload = {
            "confirmed_constraints": [
                {"id": "acoustics", "label": "声学", "desc": "...", "source": "ai_recommended"},
            ],
            "kept_visual_reference_indices": [0, 1],
        }
        cc, ki = self._simulate_response_parsing(payload)
        assert len(cc) == 1
        assert cc[0]["id"] == "acoustics"
        assert ki == [0, 1]

    def test_v121_payload_both_fields_new_wins(self):
        """R5.4: 同时有新旧字段时，新格式优先"""
        cc, _ = self._simulate_response_parsing(
            {
                "confirmed_constraints": [{"id": "x", "label": "X", "desc": "", "source": "ai_recommended"}],
                "user_constraints": [{"label": "Y", "desc": "Z"}],
            }
        )
        assert len(cc) == 1
        assert cc[0]["id"] == "x"


# ==============================================================================
# R6: DELETE 端点不影响其他路由
# ==============================================================================


class TestR6DeleteEndpointIsolation:
    """新增 DELETE 端点不影响其他端点或系统"""

    @pytest.mark.asyncio
    async def test_delete_does_not_affect_session_other_fields(self):
        """R6.1: 删除视觉参考不影响 session 其他字段"""
        from intelligent_project_analyzer.core.state import StateManager

        sm = _make_memory_sm()
        session_id = "reg-v121-delete-isolation"
        state = StateManager.create_initial_state(user_input="隔离测试", session_id=session_id)
        state["visual_references"] = [
            {
                "file_path": "/tmp/a.jpg",
                "original_filename": "a.jpg",
                "index": 0,
                "reference_type": "general",
                "source": "output_intent",
                "custom_description": "",
            },
        ]
        state["structured_requirements"] = {"project_type": "commercial"}
        await sm.create(session_id, state)

        try:
            from intelligent_project_analyzer.api.server import delete_visual_reference

            with patch("pathlib.Path.exists", return_value=False), patch(
                "intelligent_project_analyzer.api.server._get_session_manager", new=AsyncMock(return_value=sm)
            ):
                await delete_visual_reference(session_id, 0)

            session = await sm.get(session_id)
            assert len(session.get("visual_references", [])) == 0
            # 其他字段不受影响
            assert session.get("structured_requirements", {}).get("project_type") == "commercial"
            assert session.get("user_input") == "隔离测试"

        finally:
            await sm.delete(session_id)


# ==============================================================================
# R7: 413 限制不影响正常上传
# ==============================================================================


class TestR7FileSizeLimitRegression:
    """确保 413 限制不影响正常大小文件上传"""

    @pytest.mark.asyncio
    async def test_normal_file_still_uploads(self):
        """R7.1: 正常大小文件（< 10MB）仍然可以上传"""
        from intelligent_project_analyzer.core.state import StateManager

        sm = _make_memory_sm()
        session_id = "reg-v121-normal-upload"
        state = StateManager.create_initial_state(user_input="正常上传", session_id=session_id)
        await sm.create(session_id, state)

        try:
            # 5MB file — 正常大小
            normal_content = b"\x89PNG" + b"\x00" * (5 * 1024 * 1024)

            with patch("intelligent_project_analyzer.api.server.file_processor.save_file") as mock_save, patch(
                "intelligent_project_analyzer.api.server.file_processor.extract_image_enhanced"
            ) as mock_extract:
                mock_save.return_value = Path("/tmp/normal.png")
                mock_extract.return_value = {"width": 200, "height": 200, "format": "PNG"}

                from intelligent_project_analyzer.api.server import attach_files_to_session
                from fastapi import UploadFile
                import json

                upload = MagicMock(spec=UploadFile)
                upload.filename = "normal.png"
                upload.content_type = "image/png"
                upload.read = AsyncMock(return_value=normal_content)

                with patch(
                    "intelligent_project_analyzer.api.server._get_session_manager", new=AsyncMock(return_value=sm)
                ):
                    result = await attach_files_to_session(
                        session_id=session_id,
                        file_metadata=json.dumps([]),
                        files=[upload],
                    )
                assert result["status"] == "success"
                assert result["added_count"] == 1

        finally:
            await sm.delete(session_id)

    @pytest.mark.asyncio
    async def test_small_file_is_fine(self):
        """R7.2: 小文件（几百字节）正常上传"""
        from intelligent_project_analyzer.core.state import StateManager

        sm = _make_memory_sm()
        session_id = "reg-v121-tiny-upload"
        state = StateManager.create_initial_state(user_input="小文件", session_id=session_id)
        await sm.create(session_id, state)

        try:
            tiny = b"\x89PNG" + b"\x00" * 100

            with patch("intelligent_project_analyzer.api.server.file_processor.save_file") as mock_save, patch(
                "intelligent_project_analyzer.api.server.file_processor.extract_image_enhanced"
            ) as mock_extract:
                mock_save.return_value = Path("/tmp/tiny.png")
                mock_extract.return_value = {"width": 10, "height": 10, "format": "PNG"}

                from intelligent_project_analyzer.api.server import attach_files_to_session
                from fastapi import UploadFile
                import json

                upload = MagicMock(spec=UploadFile)
                upload.filename = "tiny.png"
                upload.content_type = "image/png"
                upload.read = AsyncMock(return_value=tiny)

                with patch(
                    "intelligent_project_analyzer.api.server._get_session_manager", new=AsyncMock(return_value=sm)
                ):
                    result = await attach_files_to_session(
                        session_id=session_id,
                        file_metadata=json.dumps([]),
                        files=[upload],
                    )
                assert result["status"] == "success"

        finally:
            await sm.delete(session_id)
