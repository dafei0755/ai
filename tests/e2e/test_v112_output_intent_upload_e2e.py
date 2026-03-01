"""
端到端测试：输出意图文件上传完整用户旅程 (v11.2)
模拟真实用户流程：输入需求 → 触发输出意图 → 上传文件 → 添加约束 → 确认 → 分析继续
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import json
from datetime import datetime
from intelligent_project_analyzer.core.state import StateManager


@pytest.fixture
def mock_llm_responses():
    """Mock LLM 响应，避免实际调用"""
    return {
        "requirements_analyst": {
            "project_type": "residential",
            "scale_info": {"area_sqm": 150},
            "stakeholders": [{"role": "homeowner", "decision_power": "high"}],
            "spatial_description": {
                "zones": [
                    {"id": "living_room", "label": "客厅"},
                    {"id": "bedroom", "label": "卧室"},
                ]
            },
            "explicit_deliverables": ["design_report"],
        },
        "file_extraction": {
            "width": 1920,
            "height": 1080,
            "format": "JPEG",
            "vision_analysis": "Nordic minimalist interior with natural light",
            "structured_features": {
                "style": ["nordic", "minimalist"],
                "materials": ["wood", "white_paint"],
                "color_palette": ["white", "beige", "wood_tone"],
            },
        },
    }


class TestOutputIntentUploadE2E:
    """端到端测试：完整用户旅程"""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_complete_user_journey_with_file_upload(self, mock_llm_responses):
        """
        完整用户旅程测试

        场景：用户输入需求 → requirements_analyst 分析 → output_intent_detection 中断
              → 用户上传参考图并添加约束 → 确认 → feasibility_analyst 继续
        """
        from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

        sm = RedisSessionManager()
        session_id = f"e2e-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # ============== Phase 1: 用户输入需求 ==============
        user_input = "150平米现代北欧风格住宅设计，预算50万，希望空间通透明亮"

        initial_state = StateManager.create_initial_state(user_input=user_input, session_id=session_id)

        await sm.create(session_id, initial_state)

        try:
            # ============== Phase 2: Requirements Analyst 分析（模拟） ==============
            await sm.update(session_id, {"structured_requirements": mock_llm_responses["requirements_analyst"]})

            # ============== Phase 3: 用户上传视觉参考文件 ==============
            fake_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 500

            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(fake_image)
                tmp_path = Path(tmp.name)

            try:
                with patch("intelligent_project_analyzer.api.server.file_processor.save_file") as mock_save, patch(
                    "intelligent_project_analyzer.api.server.file_processor.extract_image_enhanced"
                ) as mock_extract:
                    mock_save.return_value = tmp_path
                    mock_extract.return_value = mock_llm_responses["file_extraction"]

                    from intelligent_project_analyzer.api.server import attach_files_to_session

                    # 模拟前端上传请求
                    upload_file = MagicMock()
                    upload_file.filename = "nordic_style_ref.jpg"
                    upload_file.content_type = "image/jpeg"
                    upload_file.read = AsyncMock(return_value=fake_image)

                    upload_result = await attach_files_to_session(
                        session_id=session_id,
                        file_metadata=json.dumps(
                            [
                                {
                                    "filename": "nordic_style_ref.jpg",
                                    "categories": ["style"],
                                    "custom_description": "参考北欧风格的自然光运用和木质元素",
                                }
                            ]
                        ),
                        files=[upload_file],
                    )

                    assert upload_result["status"] == "success"
                    assert upload_result["added_count"] == 1

                # ============== Phase 4: Output Intent Detection 中断 ==============
                from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
                    output_intent_detection_node,
                )

                # 模拟用户在弹窗中的确认操作
                user_confirmation = {
                    "selected_deliveries": ["design_professional", "investor_operator"],
                    "selected_modes": ["family_intimacy", "professional_working"],
                    "user_constraints": [
                        {"label": "风格偏好", "desc": "北欧极简风，保留木质温暖感"},
                        {"label": "预算约束", "desc": "硬装预算不超过50万，优先保证采光和通风"},
                        {"label": "功能需求", "desc": "需要独立书房，客厅要足够开阔"},
                    ],
                }

                with patch(
                    "intelligent_project_analyzer.interaction.nodes.output_intent_detection.interrupt",
                    return_value=user_confirmation,
                ):
                    state = await sm.get(session_id)
                    command = await output_intent_detection_node(state)

                    # 验证返回的 Command
                    assert command.goto == "feasibility_analyst"
                    assert "active_projections" in command.update
                    assert "user_intent_constraints" in command.update
                    assert "visual_constraints" in command.update
                    assert "extracted_spatial_zones" in command.update

                    # 验证 active_projections
                    projections = command.update["active_projections"]
                    assert "design_professional" in projections
                    assert "investor_operator" in projections

                    # 验证 user_intent_constraints
                    constraints = command.update["user_intent_constraints"]
                    assert len(constraints) == 3
                    assert constraints[0]["label"] == "风格偏好"
                    assert "北欧" in constraints[0]["desc"]

                    # 验证 extracted_spatial_zones
                    zones = command.update["extracted_spatial_zones"]
                    assert zones is not None
                    assert any(z["label"] == "客厅" for z in zones)

                    # 应用更新
                    await sm.update(session_id, command.update)

                # ============== Phase 5: 验证最终状态 ==============
                final_state = await sm.get(session_id)

                # 验证所有关键字段都已正确写入
                assert final_state["active_projections"] == ["design_professional", "investor_operator"]
                assert final_state["user_intent_constraints"] == user_confirmation["user_constraints"]
                assert "visual_references" in final_state
                assert len(final_state["visual_references"]) == 1
                assert final_state["visual_references"][0]["source"] == "output_intent"
                assert final_state["visual_references"][0]["reference_type"] == "style"

                # 验证视觉分析已提取
                vision_ref = final_state["visual_references"][0]
                assert "vision_analysis" in vision_ref
                assert (
                    "nordic" in vision_ref["vision_analysis"].lower()
                    or "minimalist" in vision_ref["vision_analysis"].lower()
                )

                # 验证空间区域提取
                assert final_state["extracted_spatial_zones"] is not None

                # 验证 output_framework_signals 已生成
                assert "output_framework_signals" in final_state
                signals = final_state["output_framework_signals"]
                assert "scope" in signals
                assert "audience_needs" in signals
                assert len(signals["audience_needs"]) == 2  # design_professional + investor_operator

            finally:
                if tmp_path.exists():
                    tmp_path.unlink()

        finally:
            await sm.delete(session_id)

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_user_journey_without_file_upload(self):
        """测试不上传文件的正常流程"""
        from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

        sm = RedisSessionManager()
        session_id = f"e2e-no-upload-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        initial_state = StateManager.create_initial_state(user_input="简单办公空间设计", session_id=session_id)

        await sm.create(session_id, initial_state)

        try:
            await sm.update(
                session_id,
                {
                    "structured_requirements": {
                        "project_type": "commercial",
                        "scale_info": {"area_sqm": 80},
                        "stakeholders": [],
                        "explicit_deliverables": [],
                    }
                },
            )

            # 用户未上传文件，但填写了约束
            user_confirmation = {
                "selected_deliveries": ["design_professional"],
                "selected_modes": ["professional_working"],
                "user_constraints": [
                    {"label": "预算", "desc": "20万以内"},
                ],
            }

            with patch(
                "intelligent_project_analyzer.interaction.nodes.output_intent_detection.interrupt",
                return_value=user_confirmation,
            ):
                from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
                    output_intent_detection_node,
                )

                state = await sm.get(session_id)
                command = await output_intent_detection_node(state)

                await sm.update(session_id, command.update)

                final_state = await sm.get(session_id)

                # 应该正常处理，即使没有上传文件
                assert final_state["user_intent_constraints"] == user_confirmation["user_constraints"]
                assert final_state.get("visual_references") in (None, [])

        finally:
            await sm.delete(session_id)

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_multiple_files_batch_upload(self, mock_llm_responses):
        """测试批量上传多个文件的场景"""
        from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

        sm = RedisSessionManager()
        session_id = f"e2e-batch-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        initial_state = StateManager.create_initial_state(user_input="豪华别墅设计", session_id=session_id)

        await sm.create(session_id, initial_state)

        try:
            await sm.update(session_id, {"structured_requirements": mock_llm_responses["requirements_analyst"]})

            # 上传3个不同类型的文件
            files_metadata = [
                {"filename": "style_ref.jpg", "categories": ["style"], "custom_description": "风格参考"},
                {"filename": "layout_plan.jpg", "categories": ["layout"], "custom_description": "平面布局参考"},
                {"filename": "requirements.pdf", "categories": [], "custom_description": "需求文档"},
            ]

            with patch("intelligent_project_analyzer.api.server.file_processor.save_file") as mock_save, patch(
                "intelligent_project_analyzer.api.server.file_processor.extract_image_enhanced"
            ) as mock_extract_img, patch(
                "intelligent_project_analyzer.api.server.file_processor.extract_content"
            ) as mock_extract_pdf:
                mock_save.return_value = Path("uploads/test.jpg")
                mock_extract_img.return_value = mock_llm_responses["file_extraction"]
                mock_extract_pdf.return_value = {"summary": "PDF content summary"}

                from intelligent_project_analyzer.api.server import attach_files_to_session

                upload_files = []
                for meta in files_metadata:
                    uf = MagicMock()
                    uf.filename = meta["filename"]
                    uf.content_type = "image/jpeg" if meta["filename"].endswith(".jpg") else "application/pdf"
                    uf.read = AsyncMock(return_value=b"data" * 100)
                    upload_files.append(uf)

                result = await attach_files_to_session(
                    session_id=session_id, file_metadata=json.dumps(files_metadata), files=upload_files
                )

                assert result["added_count"] == 3

                state = await sm.get(session_id)
                refs = state["visual_references"]
                assert len(refs) == 3

                # 验证引用类型映射
                assert any(r["reference_type"] == "style" for r in refs if "reference_type" in r)
                assert any(r["reference_type"] == "layout" for r in refs if "reference_type" in r)

        finally:
            await sm.delete(session_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e", "--tb=short"])
