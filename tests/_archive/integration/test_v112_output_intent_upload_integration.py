"""
集成测试：输出意图文件上传 + State 消费 (v11.2)
测试完整的数据流：前端 API → 后端处理 → output_intent_detection 消费
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import json


@pytest_asyncio.fixture
async def test_session():
    """创建测试会话"""
    from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager
    from intelligent_project_analyzer.core.state import StateManager

    sm = RedisSessionManager()
    session_id = "test-v112-integration"

    # 创建初始 state
    initial_state = StateManager.create_initial_state(user_input="150平米现代简约住宅设计", session_id=session_id)

    await sm.create(session_id, initial_state)

    yield session_id, sm

    # 清理
    await sm.delete(session_id)


class TestOutputIntentUploadIntegration:
    """测试输出意图上传的集成流程"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_upload_then_output_intent_consumes_constraints(self, test_session):
        """测试上传文件后，output_intent_detection 正确消费 user_constraints"""
        session_id, sm = test_session

        # Step 1: 模拟用户上传文件
        fake_image_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # Minimal PNG header

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(fake_image_data)
            tmp_path = Path(tmp.name)

        try:
            # Mock file_processor.save_file 和 extract_image_enhanced
            with patch("intelligent_project_analyzer.api.server.file_processor.save_file") as mock_save, patch(
                "intelligent_project_analyzer.api.server.file_processor.extract_image_enhanced"
            ) as mock_extract:
                mock_save.return_value = tmp_path
                mock_extract.return_value = {
                    "width": 1200,
                    "height": 800,
                    "format": "JPEG",
                    "vision_analysis": "Minimalist Nordic interior",
                    "structured_features": {"style": ["nordic", "minimalist"]},
                }

                from intelligent_project_analyzer.api.server import attach_files_to_session
                from fastapi import UploadFile

                # 创建 UploadFile mock
                upload_file = MagicMock(spec=UploadFile)
                upload_file.filename = "style_ref.jpg"
                upload_file.content_type = "image/jpeg"
                upload_file.read = AsyncMock(return_value=fake_image_data)

                result = await attach_files_to_session(
                    session_id=session_id,
                    file_metadata=json.dumps(
                        [
                            {
                                "filename": "style_ref.jpg",
                                "categories": ["style"],
                                "custom_description": "Nordic minimalist reference",
                            }
                        ]
                    ),
                    files=[upload_file],
                )

                assert result["status"] == "success"
                assert result["added_count"] == 1

            # Step 2: 验证 session 中的 visual_references 已更新
            session = await sm.get(session_id)
            assert "visual_references" in session
            assert len(session["visual_references"]) == 1
            assert session["visual_references"][0]["source"] == "output_intent"

            # Step 3: 模拟 output_intent_detection interrupt 用户确认
            from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
                output_intent_detection_node,
            )

            # 先添加必要的 structured_requirements（output_intent_detection 需要）
            await sm.update(
                session_id,
                {
                    "structured_requirements": {
                        "project_type": "residential",
                        "scale_info": {"area_sqm": 150},
                        "stakeholders": [],
                        "explicit_deliverables": [],
                    }
                },
            )

            # 模拟 interrupt 返回用户响应
            mock_user_response = {
                "selected_deliveries": ["design_professional", "investor_operator"],
                "selected_modes": ["family_intimacy", "professional_working"],
                "user_constraints": [
                    {"label": "风格偏好", "desc": "北欧极简风，避免繁复装饰"},
                    {"label": "预算约束", "desc": "硬装预算不超过30万"},
                ],
            }

            with patch(
                "intelligent_project_analyzer.interaction.nodes.output_intent_detection.interrupt",
                return_value=mock_user_response,
            ):
                # 执行节点
                state = await sm.get(session_id)
                command = await output_intent_detection_node(state)

                # 验证 Command 返回
                assert command.goto == "feasibility_analyst"
                assert "active_projections" in command.update
                assert "user_intent_constraints" in command.update

                # 验证 user_intent_constraints 被正确写入
                user_constraints = command.update["user_intent_constraints"]
                assert user_constraints is not None
                assert len(user_constraints) == 2
                assert user_constraints[0]["label"] == "风格偏好"
                assert user_constraints[1]["label"] == "预算约束"

                # 应用更新到 session
                await sm.update(session_id, command.update)

                # 验证持久化
                final_state = await sm.get(session_id)
                assert final_state["user_intent_constraints"] == user_constraints

        finally:
            # 清理临时文件
            if tmp_path.exists():
                tmp_path.unlink()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_upload_without_constraints_still_works(self, test_session):
        """测试不添加约束条件时系统正常运行"""
        session_id, sm = test_session

        await sm.update(
            session_id,
            {
                "structured_requirements": {
                    "project_type": "commercial",
                    "scale_info": {},
                    "stakeholders": [],
                    "explicit_deliverables": [],
                }
            },
        )

        # 模拟用户未填写约束条件
        mock_user_response = {
            "selected_deliveries": ["design_professional"],
            "selected_modes": [],
            # user_constraints 字段缺失
        }

        with patch(
            "intelligent_project_analyzer.interaction.nodes.output_intent_detection.interrupt",
            return_value=mock_user_response,
        ):
            from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
                output_intent_detection_node,
            )

            state = await sm.get(session_id)
            command = await output_intent_detection_node(state)

            # 应该有 None 值，而非抛出异常
            assert "user_intent_constraints" in command.update
            assert command.update["user_intent_constraints"] is None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_idempotent_no_second_interrupt(self, test_session):
        """测试幂等保护：已有 active_projections 时不再中断"""
        session_id, sm = test_session

        # 先设置已存在的 active_projections
        await sm.update(
            session_id,
            {
                "active_projections": ["design_professional"],
                "intent_changed": False,
                "structured_requirements": {"project_type": "residential"},
            },
        )

        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import output_intent_detection_node

        # 不应触发 interrupt
        with patch(
            "intelligent_project_analyzer.interaction.nodes.output_intent_detection.interrupt"
        ) as mock_interrupt:
            state = await sm.get(session_id)
            command = await output_intent_detection_node(state)

            # interrupt 不应被调用
            mock_interrupt.assert_not_called()

            # 应直接转到下一节点
            assert command.goto == "feasibility_analyst"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_visual_references_append_not_replace(self, test_session):
        """测试追加文件而非覆盖已有引用"""
        session_id, sm = test_session

        # 先添加一个初始引用
        await sm.update(session_id, {"visual_references": [{"file_path": "initial.jpg", "source": "initial_upload"}]})

        # 上传新文件
        with patch("intelligent_project_analyzer.api.server.file_processor.save_file") as mock_save, patch(
            "intelligent_project_analyzer.api.server.file_processor.extract_image_enhanced"
        ) as mock_extract:
            mock_save.return_value = Path("uploads/new.jpg")
            mock_extract.return_value = {
                "width": 800,
                "height": 600,
                "format": "JPEG",
                "vision_analysis": "",
                "structured_features": {},
            }

            from intelligent_project_analyzer.api.server import attach_files_to_session

            upload_file = MagicMock()
            upload_file.filename = "new.jpg"
            upload_file.content_type = "image/jpeg"
            upload_file.read = AsyncMock(return_value=b"data" * 100)

            result = await attach_files_to_session(session_id=session_id, file_metadata="[]", files=[upload_file])

            assert result["total_count"] == 2  # 1 existing + 1 new
            assert result["start_index"] == 1

            # 验证 session 中的引用列表
            session = await sm.get(session_id)
            refs = session["visual_references"]
            assert len(refs) == 2
            assert refs[0]["source"] == "initial_upload"
            assert refs[1]["source"] == "output_intent"


class TestStateFieldsPersistence:
    """测试 State 字段持久化"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_all_v112_fields_persist(self):
        """测试 v11.2 新增的所有字段都能正确持久化"""
        from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager
        from intelligent_project_analyzer.core.state import StateManager

        sm = RedisSessionManager()
        session_id = "test-v112-persistence"

        initial_state = StateManager.create_initial_state(user_input="Test project", session_id=session_id)

        await sm.create(session_id, initial_state)

        try:
            # 更新所有 v11.2 相关字段
            update_data = {
                "user_intent_constraints": [
                    {"label": "预算", "desc": "不超过50万"},
                    {"label": "风格", "desc": "现代简约"},
                ],
                "visual_constraints": {
                    "three_layer_constraints": {"L1": [], "L2": [], "L3": []},
                    "constraint_envelope": "Budget: max 500k",
                },
                "extracted_spatial_zones": [
                    {"id": "zone1", "label": "客厅", "source": "user_input"},
                    {"id": "zone2", "label": "卧室", "source": "structured"},
                ],
            }

            await sm.update(session_id, update_data)

            # 读取并验证
            state = await sm.get(session_id)
            assert state["user_intent_constraints"] == update_data["user_intent_constraints"]
            assert state["visual_constraints"] == update_data["visual_constraints"]
            assert state["extracted_spatial_zones"] == update_data["extracted_spatial_zones"]

        finally:
            await sm.delete(session_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration", "--tb=short"])
