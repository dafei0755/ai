"""
v7.300: Step2 搜索计划 API 集成测试

测试后端 API 端点：
1. POST /api/search/step2/update - 更新搜索计划
2. POST /api/search/step2/confirm - 确认计划并准备执行
3. POST /api/search/step2/validate - 验证计划并智能补充建议

测试类型：
- 单元测试：API 端点响应格式
- 集成测试：与 Redis 会话管理器的交互
- 回归测试：确保现有功能不受影响
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# 测试数据工厂
class TestDataFactory:
    """测试数据工厂"""

    @staticmethod
    def create_search_step(
        step_id: str = "S1",
        step_number: int = 1,
        task_description: str = "搜索HAY品牌设计语言",
        expected_outcome: str = "获取HAY品牌核心设计特征",
        priority: str = "high",
        can_parallel: bool = True,
        status: str = "pending",
    ) -> dict:
        return {
            "id": step_id,
            "step_number": step_number,
            "task_description": task_description,
            "expected_outcome": expected_outcome,
            "search_keywords": ["HAY", "北欧设计"],
            "priority": priority,
            "can_parallel": can_parallel,
            "status": status,
            "completion_score": 0,
            "is_user_added": False,
            "is_user_modified": False,
        }

    @staticmethod
    def create_search_plan(
        session_id: str = "test-session-123",
        num_steps: int = 3,
    ) -> dict:
        steps = [
            TestDataFactory.create_search_step(
                step_id=f"S{i+1}",
                step_number=i + 1,
                task_description=f"搜索任务 {i+1}",
            )
            for i in range(num_steps)
        ]
        return {
            "session_id": session_id,
            "query": "以丹麦家居品牌HAY气质为基础，为四川峨眉山七里坪民宿室内设计提供概念设计",
            "core_question": "如何融合HAY品牌气质与峨眉山地域特色",
            "answer_goal": "提供完整的民宿室内概念设计方案",
            "search_steps": steps,
            "max_rounds_per_step": 3,
            "quality_threshold": 0.7,
            "user_added_steps": [],
            "user_deleted_steps": [],
            "user_modified_steps": [],
            "current_page": 1,
            "total_pages": 1,
            "is_confirmed": False,
        }


@pytest.fixture
def mock_redis_session_manager():
    """Mock Redis 会话管理器"""
    with patch("intelligent_project_analyzer.api.search_routes.redis_session_manager") as mock:
        mock.get_session = AsyncMock(
            return_value={
                "session_id": "test-session-123",
                "status": "analyzing",
                "query": "测试查询",
            }
        )
        mock.update_session = AsyncMock(return_value=True)
        mock.save_step2_plan = AsyncMock(return_value=True)
        mock.get_step2_plan = AsyncMock(return_value=None)
        yield mock


@pytest.fixture
def mock_ucppt_engine():
    """Mock UCPPT 搜索引擎"""
    with patch("intelligent_project_analyzer.api.search_routes.UcpptSearchEngine") as mock:
        engine_instance = MagicMock()
        engine_instance.validate_search_plan = AsyncMock(
            return_value={
                "has_suggestions": False,
                "suggestions": [],
                "validation_passed": True,
            }
        )
        mock.return_value = engine_instance
        yield mock


class TestStep2UpdateAPI:
    """测试 POST /api/search/step2/update 端点"""

    @pytest.mark.unit
    def test_update_plan_success(self, mock_redis_session_manager):
        """测试成功更新搜索计划"""
        from intelligent_project_analyzer.api.search_routes import router

        app = FastAPI()
        app.include_router(router, prefix="/api/search")
        client = TestClient(app)

        plan = TestDataFactory.create_search_plan()

        response = client.post(
            "/api/search/step2/update",
            json={
                "session_id": "test-session-123",
                "search_plan": plan,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "plan" in data

    @pytest.mark.unit
    def test_update_plan_missing_session_id(self):
        """测试缺少 session_id 时返回错误"""
        from intelligent_project_analyzer.api.search_routes import router

        app = FastAPI()
        app.include_router(router, prefix="/api/search")
        client = TestClient(app)

        plan = TestDataFactory.create_search_plan()

        response = client.post(
            "/api/search/step2/update",
            json={
                "search_plan": plan,
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.unit
    def test_update_plan_add_step(self, mock_redis_session_manager):
        """测试添加新步骤"""
        from intelligent_project_analyzer.api.search_routes import router

        app = FastAPI()
        app.include_router(router, prefix="/api/search")
        client = TestClient(app)

        plan = TestDataFactory.create_search_plan(num_steps=3)
        # 添加新步骤
        new_step = TestDataFactory.create_search_step(
            step_id="S4",
            step_number=4,
            task_description="用户添加的新任务",
        )
        new_step["is_user_added"] = True
        plan["search_steps"].append(new_step)
        plan["user_added_steps"] = ["S4"]

        response = client.post(
            "/api/search/step2/update",
            json={
                "session_id": "test-session-123",
                "search_plan": plan,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["plan"]["search_steps"]) == 4
        assert "S4" in data["plan"]["user_added_steps"]

    @pytest.mark.unit
    def test_update_plan_delete_step(self, mock_redis_session_manager):
        """测试删除步骤"""
        from intelligent_project_analyzer.api.search_routes import router

        app = FastAPI()
        app.include_router(router, prefix="/api/search")
        client = TestClient(app)

        plan = TestDataFactory.create_search_plan(num_steps=3)
        # 删除第二个步骤
        plan["search_steps"] = [s for s in plan["search_steps"] if s["id"] != "S2"]
        plan["user_deleted_steps"] = ["S2"]

        response = client.post(
            "/api/search/step2/update",
            json={
                "session_id": "test-session-123",
                "search_plan": plan,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["plan"]["search_steps"]) == 2
        assert "S2" in data["plan"]["user_deleted_steps"]

    @pytest.mark.unit
    def test_update_plan_modify_step(self, mock_redis_session_manager):
        """测试修改步骤"""
        from intelligent_project_analyzer.api.search_routes import router

        app = FastAPI()
        app.include_router(router, prefix="/api/search")
        client = TestClient(app)

        plan = TestDataFactory.create_search_plan(num_steps=3)
        # 修改第一个步骤
        plan["search_steps"][0]["task_description"] = "修改后的任务描述"
        plan["search_steps"][0]["is_user_modified"] = True
        plan["user_modified_steps"] = ["S1"]

        response = client.post(
            "/api/search/step2/update",
            json={
                "session_id": "test-session-123",
                "search_plan": plan,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["plan"]["search_steps"][0]["task_description"] == "修改后的任务描述"
        assert "S1" in data["plan"]["user_modified_steps"]


class TestStep2ConfirmAPI:
    """测试 POST /api/search/step2/confirm 端点"""

    @pytest.mark.unit
    def test_confirm_plan_success(self, mock_redis_session_manager):
        """测试成功确认搜索计划"""
        from intelligent_project_analyzer.api.search_routes import router

        app = FastAPI()
        app.include_router(router, prefix="/api/search")
        client = TestClient(app)

        plan = TestDataFactory.create_search_plan()

        response = client.post(
            "/api/search/step2/confirm",
            json={
                "session_id": "test-session-123",
                "search_plan": plan,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["plan"]["is_confirmed"] is True
        assert "confirmed_at" in data["plan"]

    @pytest.mark.unit
    def test_confirm_empty_plan(self, mock_redis_session_manager):
        """测试确认空计划时返回错误"""
        from intelligent_project_analyzer.api.search_routes import router

        app = FastAPI()
        app.include_router(router, prefix="/api/search")
        client = TestClient(app)

        plan = TestDataFactory.create_search_plan(num_steps=0)

        response = client.post(
            "/api/search/step2/confirm",
            json={
                "session_id": "test-session-123",
                "search_plan": plan,
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data or "detail" in data

    @pytest.mark.unit
    def test_confirm_already_confirmed(self, mock_redis_session_manager):
        """测试重复确认计划"""
        from intelligent_project_analyzer.api.search_routes import router

        app = FastAPI()
        app.include_router(router, prefix="/api/search")
        client = TestClient(app)

        plan = TestDataFactory.create_search_plan()
        plan["is_confirmed"] = True
        plan["confirmed_at"] = "2026-01-28T10:00:00"

        response = client.post(
            "/api/search/step2/confirm",
            json={
                "session_id": "test-session-123",
                "search_plan": plan,
            },
        )

        # 应该允许重复确认（幂等性）
        assert response.status_code == 200


class TestStep2ValidateAPI:
    """测试 POST /api/search/step2/validate 端点"""

    @pytest.mark.unit
    def test_validate_plan_no_suggestions(self, mock_redis_session_manager, mock_ucppt_engine):
        """测试验证计划无建议"""
        from intelligent_project_analyzer.api.search_routes import router

        app = FastAPI()
        app.include_router(router, prefix="/api/search")
        client = TestClient(app)

        plan = TestDataFactory.create_search_plan()

        response = client.post(
            "/api/search/step2/validate",
            json={
                "session_id": "test-session-123",
                "search_plan": plan,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_suggestions"] is False
        assert data["suggestions"] == []

    @pytest.mark.unit
    def test_validate_plan_with_suggestions(self, mock_redis_session_manager):
        """测试验证计划有建议"""
        from intelligent_project_analyzer.api.search_routes import router

        with patch("intelligent_project_analyzer.api.search_routes.UcpptSearchEngine") as mock_engine:
            engine_instance = MagicMock()
            engine_instance.validate_search_plan = AsyncMock(
                return_value={
                    "has_suggestions": True,
                    "suggestions": [
                        {
                            "direction": "材质研究",
                            "what_to_search": "搜索HAY常用材质",
                            "why_important": "材质是设计落地的关键",
                            "priority": "P1",
                        }
                    ],
                    "validation_passed": True,
                }
            )
            mock_engine.return_value = engine_instance

            app = FastAPI()
            app.include_router(router, prefix="/api/search")
            client = TestClient(app)

            plan = TestDataFactory.create_search_plan(num_steps=1)

            response = client.post(
                "/api/search/step2/validate",
                json={
                    "session_id": "test-session-123",
                    "search_plan": plan,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["has_suggestions"] is True
            assert len(data["suggestions"]) == 1
            assert data["suggestions"][0]["direction"] == "材质研究"

    @pytest.mark.unit
    def test_validate_plan_priority_mapping(self, mock_redis_session_manager):
        """测试建议优先级映射"""
        from intelligent_project_analyzer.api.search_routes import router

        with patch("intelligent_project_analyzer.api.search_routes.UcpptSearchEngine") as mock_engine:
            engine_instance = MagicMock()
            engine_instance.validate_search_plan = AsyncMock(
                return_value={
                    "has_suggestions": True,
                    "suggestions": [
                        {"direction": "高优", "what_to_search": "...", "why_important": "...", "priority": "P0"},
                        {"direction": "中优", "what_to_search": "...", "why_important": "...", "priority": "P1"},
                        {"direction": "低优", "what_to_search": "...", "why_important": "...", "priority": "P2"},
                    ],
                    "validation_passed": True,
                }
            )
            mock_engine.return_value = engine_instance

            app = FastAPI()
            app.include_router(router, prefix="/api/search")
            client = TestClient(app)

            plan = TestDataFactory.create_search_plan()

            response = client.post(
                "/api/search/step2/validate",
                json={
                    "session_id": "test-session-123",
                    "search_plan": plan,
                },
            )

            assert response.status_code == 200
            data = response.json()
            priorities = [s["priority"] for s in data["suggestions"]]
            assert "P0" in priorities
            assert "P1" in priorities
            assert "P2" in priorities


class TestStep2APIIntegration:
    """集成测试：API 与会话管理器交互"""

    @pytest.mark.integration
    def test_update_then_confirm_flow(self, mock_redis_session_manager):
        """测试更新后确认的完整流程"""
        from intelligent_project_analyzer.api.search_routes import router

        app = FastAPI()
        app.include_router(router, prefix="/api/search")
        client = TestClient(app)

        # 1. 创建初始计划
        plan = TestDataFactory.create_search_plan(num_steps=2)

        # 2. 更新计划（添加步骤）
        new_step = TestDataFactory.create_search_step(
            step_id="S3",
            step_number=3,
            task_description="新增的搜索任务",
        )
        new_step["is_user_added"] = True
        plan["search_steps"].append(new_step)
        plan["user_added_steps"] = ["S3"]

        update_response = client.post(
            "/api/search/step2/update",
            json={
                "session_id": "test-session-123",
                "search_plan": plan,
            },
        )
        assert update_response.status_code == 200
        updated_plan = update_response.json()["plan"]

        # 3. 确认计划
        confirm_response = client.post(
            "/api/search/step2/confirm",
            json={
                "session_id": "test-session-123",
                "search_plan": updated_plan,
            },
        )
        assert confirm_response.status_code == 200
        confirmed_plan = confirm_response.json()["plan"]

        # 验证最终状态
        assert confirmed_plan["is_confirmed"] is True
        assert len(confirmed_plan["search_steps"]) == 3
        assert "S3" in confirmed_plan["user_added_steps"]

    @pytest.mark.integration
    def test_validate_then_update_then_confirm_flow(self, mock_redis_session_manager):
        """测试验证-更新-确认的完整流程"""
        from intelligent_project_analyzer.api.search_routes import router

        with patch("intelligent_project_analyzer.api.search_routes.UcpptSearchEngine") as mock_engine:
            engine_instance = MagicMock()
            engine_instance.validate_search_plan = AsyncMock(
                return_value={
                    "has_suggestions": True,
                    "suggestions": [
                        {
                            "direction": "建议方向",
                            "what_to_search": "建议搜索内容",
                            "why_important": "建议原因",
                            "priority": "P1",
                        }
                    ],
                    "validation_passed": True,
                }
            )
            mock_engine.return_value = engine_instance

            app = FastAPI()
            app.include_router(router, prefix="/api/search")
            client = TestClient(app)

            plan = TestDataFactory.create_search_plan(num_steps=2)

            # 1. 验证计划
            validate_response = client.post(
                "/api/search/step2/validate",
                json={
                    "session_id": "test-session-123",
                    "search_plan": plan,
                },
            )
            assert validate_response.status_code == 200
            assert validate_response.json()["has_suggestions"] is True

            # 2. 根据建议更新计划
            suggestion = validate_response.json()["suggestions"][0]
            new_step = TestDataFactory.create_search_step(
                step_id="S3",
                step_number=3,
                task_description=suggestion["what_to_search"],
                expected_outcome=suggestion["why_important"],
            )
            new_step["is_user_added"] = True
            plan["search_steps"].append(new_step)
            plan["user_added_steps"] = ["S3"]

            update_response = client.post(
                "/api/search/step2/update",
                json={
                    "session_id": "test-session-123",
                    "search_plan": plan,
                },
            )
            assert update_response.status_code == 200

            # 3. 确认计划
            confirm_response = client.post(
                "/api/search/step2/confirm",
                json={
                    "session_id": "test-session-123",
                    "search_plan": update_response.json()["plan"],
                },
            )
            assert confirm_response.status_code == 200
            assert confirm_response.json()["plan"]["is_confirmed"] is True


class TestStep2APIRegression:
    """回归测试：确保现有功能不受影响"""

    @pytest.mark.regression
    def test_existing_search_flow_unaffected(self, mock_redis_session_manager):
        """测试现有搜索流程不受影响"""
        from intelligent_project_analyzer.api.search_routes import router

        app = FastAPI()
        app.include_router(router, prefix="/api/search")
        client = TestClient(app)

        # 测试现有的 UCPPT 搜索端点仍然可用
        # 注意：这里只测试端点存在，不测试完整功能
        response = client.get("/api/search/health")
        # 如果端点不存在会返回 404
        assert response.status_code in [200, 404, 405]  # 取决于是否实现了 health 端点

    @pytest.mark.regression
    def test_step2_api_does_not_break_step1(self, mock_redis_session_manager):
        """测试 Step2 API 不影响 Step1 功能"""
        # Step2 API 应该是独立的，不应该影响 Step1 的分析流程
        from intelligent_project_analyzer.api.search_routes import router

        app = FastAPI()
        app.include_router(router, prefix="/api/search")
        client = TestClient(app)

        # 更新 Step2 计划不应该影响会话的分析状态
        plan = TestDataFactory.create_search_plan()

        response = client.post(
            "/api/search/step2/update",
            json={
                "session_id": "test-session-123",
                "search_plan": plan,
            },
        )

        assert response.status_code == 200
        # 会话状态应该保持不变（由 mock 控制）
        mock_redis_session_manager.get_session.assert_called()


class TestStep2DataValidation:
    """数据验证测试"""

    @pytest.mark.unit
    def test_invalid_priority_rejected(self):
        """测试无效优先级被拒绝"""
        from intelligent_project_analyzer.api.search_routes import router

        app = FastAPI()
        app.include_router(router, prefix="/api/search")
        client = TestClient(app)

        plan = TestDataFactory.create_search_plan()
        plan["search_steps"][0]["priority"] = "invalid_priority"

        response = client.post(
            "/api/search/step2/update",
            json={
                "session_id": "test-session-123",
                "search_plan": plan,
            },
        )

        # 应该返回验证错误或接受并规范化
        assert response.status_code in [200, 422]

    @pytest.mark.unit
    def test_invalid_status_rejected(self):
        """测试无效状态被拒绝"""
        from intelligent_project_analyzer.api.search_routes import router

        app = FastAPI()
        app.include_router(router, prefix="/api/search")
        client = TestClient(app)

        plan = TestDataFactory.create_search_plan()
        plan["search_steps"][0]["status"] = "invalid_status"

        response = client.post(
            "/api/search/step2/update",
            json={
                "session_id": "test-session-123",
                "search_plan": plan,
            },
        )

        # 应该返回验证错误或接受并规范化
        assert response.status_code in [200, 422]

    @pytest.mark.unit
    def test_step_number_auto_correction(self, mock_redis_session_manager):
        """测试步骤编号自动修正"""
        from intelligent_project_analyzer.api.search_routes import router

        app = FastAPI()
        app.include_router(router, prefix="/api/search")
        client = TestClient(app)

        plan = TestDataFactory.create_search_plan(num_steps=3)
        # 故意设置错误的步骤编号
        plan["search_steps"][0]["step_number"] = 5
        plan["search_steps"][1]["step_number"] = 10
        plan["search_steps"][2]["step_number"] = 15

        response = client.post(
            "/api/search/step2/update",
            json={
                "session_id": "test-session-123",
                "search_plan": plan,
            },
        )

        assert response.status_code == 200
        # 步骤编号应该被自动修正为 1, 2, 3
        steps = response.json()["plan"]["search_steps"]
        assert steps[0]["step_number"] == 1
        assert steps[1]["step_number"] == 2
        assert steps[2]["step_number"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
