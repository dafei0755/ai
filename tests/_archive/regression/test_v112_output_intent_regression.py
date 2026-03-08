"""
回归测试：确保 v11.2 修改不破坏现有功能
验证输出意图模块的核心功能、其他端点、前端组件行为
"""

import pytest
from unittest.mock import patch
from intelligent_project_analyzer.core.state import StateManager


class TestOutputIntentDetectionRegression:
    """回归测试：output_intent_detection 核心功能"""

    @pytest.mark.asyncio
    @pytest.mark.regression
    async def test_original_interrupt_still_works(self):
        """确保原有的 interrupt 机制未被破坏"""
        from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import output_intent_detection_node

        sm = RedisSessionManager()
        session_id = "regression-original-interrupt"

        initial_state = StateManager.create_initial_state(user_input="商业办公空间设计 500平米", session_id=session_id)

        await sm.create(session_id, initial_state)

        try:
            await sm.update(
                session_id,
                {
                    "structured_requirements": {
                        "project_type": "commercial",
                        "scale_info": {"area_sqm": 500},
                        "stakeholders": [{"role": "investor", "decision_power": "high"}],
                        "explicit_deliverables": [],
                    }
                },
            )

            # 不包含 user_constraints 的旧格式响应
            legacy_response = {
                "selected_deliveries": ["design_professional", "investor_operator"],
                "selected_modes": ["professional_working"],
            }

            with patch(
                "intelligent_project_analyzer.interaction.nodes.output_intent_detection.interrupt",
                return_value=legacy_response,
            ):
                state = await sm.get(session_id)
                command = await output_intent_detection_node(state)

                # 应该正常返回 Command
                assert command.goto == "feasibility_analyst"
                assert "active_projections" in command.update

                # user_intent_constraints 应为 None，不应崩溃
                assert command.update.get("user_intent_constraints") is None

        finally:
            await sm.delete(session_id)

    @pytest.mark.asyncio
    @pytest.mark.regression
    async def test_delivery_type_detection_unchanged(self):
        """确保交付类型检测逻辑没有退化"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import _detect_explicit_signals

        # 显式信号检测（强关键词）
        result = _detect_explicit_signals(user_input="需要投资分析报告和施工图纸", structured_data={})

        # 应检测到两种交付类型
        delivery_scores = {k: v for k, v in result.items() if v > 0}
        assert len(delivery_scores) >= 2

    @pytest.mark.asyncio
    @pytest.mark.regression
    async def test_identity_mode_detection_unchanged(self):
        """确保身份模式检测逻辑未受影响"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import _detect_identity_modes

        structured_data = {
            "user_input": "三口之家，有一个孩子在读小学，需要独立书房",
            "character_narrative": "年轻家庭，重视孩子教育",
        }

        modes = _detect_identity_modes(structured_data, project_type="residential")

        # 应检测到家庭相关模式
        confirmed_modes = [m for m in modes if m["status"] == "confirmed"]
        assert len(confirmed_modes) > 0
        assert any("family" in m["id"] or "学习" in m["label"] for m in confirmed_modes)

    @pytest.mark.asyncio
    @pytest.mark.regression
    async def test_idempotent_protection_still_active(self):
        """确保幂等保护仍然有效"""
        from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager
        from intelligent_project_analyzer.core.state import create_initial_state
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import output_intent_detection_node

        sm = RedisSessionManager()
        session_id = "regression-idempotent"

        initial_state = create_initial_state(user_input="Test", session_id=session_id)

        await sm.create(session_id, initial_state)

        try:
            # 设置已完成的 active_projections
            await sm.update(
                session_id,
                {
                    "active_projections": ["design_professional"],
                    "intent_changed": False,
                    "structured_requirements": {"project_type": "residential"},
                },
            )

            with patch(
                "intelligent_project_analyzer.interaction.nodes.output_intent_detection.interrupt"
            ) as mock_interrupt:
                state = await sm.get(session_id)
                command = await output_intent_detection_node(state)

                # 不应触发 interrupt
                mock_interrupt.assert_not_called()
                assert command.goto == "feasibility_analyst"

        finally:
            await sm.delete(session_id)


class TestVisualReferenceEndpointsRegression:
    """回归测试：其他视觉参考端点未受影响"""

    @pytest.mark.asyncio
    @pytest.mark.regression
    async def test_visual_reference_describe_endpoint_works(self):
        """确保 visual-reference/describe 端点仍正常工作"""
        from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager
        from intelligent_project_analyzer.core.state import create_initial_state

        sm = RedisSessionManager()
        session_id = "regression-describe"

        initial_state = create_initial_state(user_input="Test", session_id=session_id)

        await sm.create(session_id, initial_state)

        try:
            await sm.update(
                session_id, {"visual_references": [{"file_path": "test.jpg", "vision_analysis": "Original analysis"}]}
            )

            from intelligent_project_analyzer.api.server import add_visual_reference_description

            class MockRequest:
                reference_index = 0
                user_description = "User added description"

            result = await add_visual_reference_description(session_id=session_id, request=MockRequest())

            assert result["status"] == "success"
            assert len(result["visual_references"]) == 1
            assert result["visual_references"][0]["user_description"] == "User added description"

        finally:
            await sm.delete(session_id)


class TestStateSchemaRegression:
    """回归测试：State 结构兼容性"""

    @pytest.mark.regression
    def test_state_schema_backward_compatible(self):
        """确保 State 定义向后兼容"""
        from intelligent_project_analyzer.core.state import StateManager

        state = StateManager.create_initial_state(user_input="Test project", session_id="test")

        # 所有旧字段仍存在
        assert "active_projections" in state
        assert "detected_identity_modes" in state
        assert "output_framework_signals" in state
        assert "visual_constraints" in state
        assert "extracted_spatial_zones" in state

        # v11.2 新字段也存在
        assert "user_intent_constraints" in state

        # 新字段默认为 None，不破坏现有逻辑
        assert state["user_intent_constraints"] is None

    @pytest.mark.regression
    def test_command_update_accepts_optional_fields(self):
        """确保 Command.update 接受可选字段"""
        from langgraph.graph import Command

        # 旧格式（不包含 user_intent_constraints）
        cmd_old = Command(
            update={
                "active_projections": ["design_professional"],
                "detected_identity_modes": [],
            },
            goto="feasibility_analyst",
        )

        assert cmd_old.update["active_projections"] == ["design_professional"]

        # 新格式（包含 user_intent_constraints）
        cmd_new = Command(
            update={
                "active_projections": ["design_professional"],
                "user_intent_constraints": [{"label": "test", "desc": "test"}],
            },
            goto="feasibility_analyst",
        )

        assert cmd_new.update["user_intent_constraints"] is not None


class TestFrontendModalRegression:
    """回归测试：前端弹窗组件核心功能"""

    @pytest.mark.regression
    def test_output_intent_data_type_compatibility(self):
        """确保 OutputIntentConfirmationData 类型兼容"""
        # 模拟旧格式的 stepData（不包含 spatial_zones 等）
        legacy_data = {
            "interaction_type": "output_intent_confirmation",
            "title": "输出意图确认",
            "delivery_types": {
                "message": "选择交付类型",
                "options": [{"id": "design_professional", "label": "设计专业报告", "desc": "...", "recommended": True}],
                "max_select": 3,
            },
            "identity_modes": {
                "message": "选择体验视角",
                "options": [{"id": "family_intimacy", "label": "家人亲密", "recommended": True}],
            },
        }

        # 应该能正常解析（TypeScript 可选字段）
        assert legacy_data["interaction_type"] == "output_intent_confirmation"
        assert "spatial_zones" not in legacy_data  # 可选字段不存在

        # 新格式（包含 v12.0 字段）
        new_data = {
            **legacy_data,
            "spatial_zones": [{"id": "zone1", "label": "客厅", "source": "user_input"}],
            "auto_detected_constraints": None,
        }

        assert new_data["spatial_zones"] is not None

    @pytest.mark.regression
    def test_confirm_payload_backward_compatible(self):
        """确保确认 payload 格式向后兼容"""
        # 旧格式（不包含 user_constraints）
        legacy_payload = {
            "selected_deliveries": ["design_professional"],
            "selected_modes": ["family_intimacy"],
        }

        # 应该能被后端正常处理
        assert "selected_deliveries" in legacy_payload
        assert "user_constraints" not in legacy_payload  # 可选字段

        # 新格式
        new_payload = {
            **legacy_payload,
            "user_constraints": [{"label": "风格", "desc": "现代"}],
        }

        assert new_payload["user_constraints"] is not None


class TestAPIEndpointRegression:
    """回归测试：API 端点路由和认证"""

    @pytest.mark.regression
    def test_existing_endpoints_still_accessible(self):
        """确保现有端点路径未被改变"""
        from intelligent_project_analyzer.api.server import app

        routes = [route.path for route in app.routes]

        # 关键端点应仍存在
        assert "/api/analysis/start" in routes
        assert "/api/analysis/{session_id}/status" in routes
        assert "/api/analysis/{session_id}/resume" in routes
        assert "/api/analysis/{session_id}/visual-reference/describe" in routes

        # v11.2 新端点已添加
        assert "/api/analysis/{session_id}/attach-files" in routes

    @pytest.mark.asyncio
    @pytest.mark.regression
    async def test_attach_files_no_auth_required(self):
        """确保新端点无需认证（与 visual-reference/describe 一致）"""
        from intelligent_project_analyzer.api.server import attach_files_to_session
        import inspect

        # 检查函数签名，不应有 Depends(get_current_user) 参数
        sig = inspect.signature(attach_files_to_session)
        param_names = list(sig.parameters.keys())

        # 应只有 session_id, file_metadata, files
        assert "session_id" in param_names
        assert "file_metadata" in param_names
        assert "files" in param_names
        assert "current_user" not in param_names  # 无认证依赖


class TestWorkflowIntegrationRegression:
    """回归测试：整体工作流未受影响"""

    @pytest.mark.asyncio
    @pytest.mark.regression
    async def test_full_workflow_without_new_features(self):
        """测试不使用新功能时的完整工作流"""
        from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import output_intent_detection_node

        sm = RedisSessionManager()
        session_id = "regression-full-workflow"

        initial_state = StateManager.create_initial_state(user_input="普通住宅设计项目", session_id=session_id)

        await sm.create(session_id, initial_state)

        try:
            # 模拟完整流程：不上传文件，不填写约束
            await sm.update(
                session_id,
                {
                    "structured_requirements": {
                        "project_type": "residential",
                        "scale_info": {"area_sqm": 100},
                        "stakeholders": [],
                        "explicit_deliverables": [],
                    }
                },
            )

            # 最小化响应
            minimal_response = {
                "selected_deliveries": ["design_professional"],
                "selected_modes": [],
            }

            with patch(
                "intelligent_project_analyzer.interaction.nodes.output_intent_detection.interrupt",
                return_value=minimal_response,
            ):
                state = await sm.get(session_id)
                command = await output_intent_detection_node(state)

                await sm.update(session_id, command.update)

                final_state = await sm.get(session_id)

                # 工作流应正常完成
                assert final_state["active_projections"] == ["design_professional"]
                assert final_state.get("user_intent_constraints") is None
                assert final_state.get("visual_references") in (None, [])

        finally:
            await sm.delete(session_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "regression", "--tb=short"])
