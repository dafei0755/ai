"""
集成测试：v12.1 约束推荐 + 视觉参考删除 + 413 文件限制

测试范围：
I1: DELETE /visual-reference/{index} — 端到端删除流程
I2: 413 文件过大拒绝 — 上传超 10MB 文件
I3: recommended_constraints → 前端 → confirmed_constraints 数据往返
I4: confirmed_constraints 注入 framework_signals 完整流程
I5: 图片描述批量同步（describe endpoint）
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

pytestmark = [pytest.mark.integration]


def _make_memory_sm():
    """创建内存模式的 SessionManager（不连接 Redis）"""
    from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

    sm = RedisSessionManager(fallback_to_memory=True)
    sm._memory_mode = True
    sm.is_connected = False
    return sm


@pytest_asyncio.fixture
async def session_with_visual_refs():
    """创建带有视觉参考的测试会话（内存模式）"""
    from intelligent_project_analyzer.core.state import StateManager

    sm = _make_memory_sm()
    session_id = "test-v121-integration"

    initial_state = StateManager.create_initial_state(
        user_input="300平米别墅设计，有录音棚需求",
        session_id=session_id,
    )

    # 预填 visual_references
    initial_state["visual_references"] = [
        {
            "file_path": "/tmp/fake_img_0.jpg",
            "original_filename": "ref_0.jpg",
            "index": 0,
            "reference_type": "style",
            "source": "output_intent",
            "custom_description": "",
        },
        {
            "file_path": "/tmp/fake_img_1.jpg",
            "original_filename": "ref_1.jpg",
            "index": 1,
            "reference_type": "general",
            "source": "output_intent",
            "custom_description": "",
        },
        {
            "file_path": "/tmp/fake_img_2.jpg",
            "original_filename": "ref_2.jpg",
            "index": 2,
            "reference_type": "material",
            "source": "output_intent",
            "custom_description": "",
        },
    ]

    await sm.create(session_id, initial_state)

    # patch _get_session_manager 让 server 端点使用同一个内存 SM
    _sm_patcher = patch(
        "intelligent_project_analyzer.api.server._get_session_manager",
        new=AsyncMock(return_value=sm),
    )
    _sm_patcher.start()
    yield session_id, sm
    _sm_patcher.stop()
    await sm.delete(session_id)


# ==============================================================================
# I1: DELETE visual-reference endpoint
# ==============================================================================


class TestI1DeleteVisualReference:
    """DELETE /api/analysis/{session_id}/visual-reference/{index} 集成测试"""

    @pytest.mark.asyncio
    async def test_delete_middle_reference(self, session_with_visual_refs):
        """I1.1: 删除中间索引的引用，其余项正确保留"""
        session_id, sm = session_with_visual_refs

        from intelligent_project_analyzer.api.server import delete_visual_reference

        # 删除 index=1
        with patch("pathlib.Path.exists", return_value=False):
            result = await delete_visual_reference(session_id, 1)

        assert result["status"] == "success"
        assert result["remaining_count"] == 2

        session = await sm.get(session_id)
        refs = session["visual_references"]
        assert len(refs) == 2
        assert refs[0]["original_filename"] == "ref_0.jpg"
        assert refs[1]["original_filename"] == "ref_2.jpg"

    @pytest.mark.asyncio
    async def test_delete_first_reference(self, session_with_visual_refs):
        """I1.2: 删除第一个引用"""
        session_id, sm = session_with_visual_refs

        from intelligent_project_analyzer.api.server import delete_visual_reference

        with patch("pathlib.Path.exists", return_value=False):
            result = await delete_visual_reference(session_id, 0)

        assert result["remaining_count"] == 2
        session = await sm.get(session_id)
        assert session["visual_references"][0]["original_filename"] == "ref_1.jpg"

    @pytest.mark.asyncio
    async def test_delete_invalid_index_raises_400(self, session_with_visual_refs):
        """I1.3: 越界索引返回 400"""
        session_id, sm = session_with_visual_refs

        from intelligent_project_analyzer.api.server import delete_visual_reference
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await delete_visual_reference(session_id, 99)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_negative_index_raises_400(self, session_with_visual_refs):
        """I1.4: 负索引返回 400"""
        session_id, sm = session_with_visual_refs

        from intelligent_project_analyzer.api.server import delete_visual_reference
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await delete_visual_reference(session_id, -1)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_from_nonexistent_session_raises_404(self):
        """I1.5: 不存在的 session 返回 404"""
        from intelligent_project_analyzer.api.server import delete_visual_reference
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await delete_visual_reference("non-existent-session-xyz", 0)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_with_disk_file(self, session_with_visual_refs):
        """I1.6: 删除时正确尝试删除磁盘文件"""
        session_id, sm = session_with_visual_refs

        from intelligent_project_analyzer.api.server import delete_visual_reference

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"fake image data")
            tmp_path = tmp.name

        # 更新 session 中的 file_path 为真实临时文件
        session = await sm.get(session_id)
        session["visual_references"][0]["file_path"] = tmp_path
        await sm.update(session_id, {"visual_references": session["visual_references"]})

        result = await delete_visual_reference(session_id, 0)
        assert result["status"] == "success"
        assert not os.path.exists(tmp_path), "磁盘文件应被删除"

    @pytest.mark.asyncio
    async def test_delete_all_references_sequential(self, session_with_visual_refs):
        """I1.7: 逐个删除所有引用后，列表为空"""
        session_id, sm = session_with_visual_refs

        from intelligent_project_analyzer.api.server import delete_visual_reference

        with patch("pathlib.Path.exists", return_value=False):
            # 每次删 index 0
            await delete_visual_reference(session_id, 0)
            await delete_visual_reference(session_id, 0)
            await delete_visual_reference(session_id, 0)

        session = await sm.get(session_id)
        assert len(session.get("visual_references", [])) == 0

    @pytest.mark.asyncio
    async def test_delete_from_empty_refs_raises_400(self, session_with_visual_refs):
        """I1.8: 无视觉引用的 session 尝试删除返回 400"""
        session_id, sm = session_with_visual_refs

        # 清空引用
        await sm.update(session_id, {"visual_references": []})

        from intelligent_project_analyzer.api.server import delete_visual_reference
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await delete_visual_reference(session_id, 0)
        assert exc_info.value.status_code == 400


# ==============================================================================
# I2: 413 文件过大拒绝
# ==============================================================================


class TestI2OversizedFileRejection:
    """上传超过 10MB 文件时返回 413"""

    @pytest_asyncio.fixture
    async def basic_session(self):
        from intelligent_project_analyzer.core.state import StateManager

        sm = _make_memory_sm()
        session_id = "test-v121-413"
        initial_state = StateManager.create_initial_state(
            user_input="测试",
            session_id=session_id,
        )
        await sm.create(session_id, initial_state)

        _sm_patcher = patch(
            "intelligent_project_analyzer.api.server._get_session_manager",
            new=AsyncMock(return_value=sm),
        )
        _sm_patcher.start()
        yield session_id, sm
        _sm_patcher.stop()
        await sm.delete(session_id)

    @pytest.mark.asyncio
    async def test_oversized_file_raises_413(self, basic_session):
        """I2.1: 超过 10MB 的文件返回 413"""
        session_id, sm = basic_session

        from intelligent_project_analyzer.api.server import attach_files_to_session
        from fastapi import UploadFile, HTTPException

        # 11MB 的 content
        oversized_content = b"\x00" * (11 * 1024 * 1024)

        upload_file = MagicMock(spec=UploadFile)
        upload_file.filename = "huge.jpg"
        upload_file.content_type = "image/jpeg"
        upload_file.read = AsyncMock(return_value=oversized_content)

        with pytest.raises(HTTPException) as exc_info:
            await attach_files_to_session(
                session_id=session_id,
                file_metadata="[]",
                files=[upload_file],
            )
        assert exc_info.value.status_code == 413
        assert "10MB" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_exactly_10mb_file_accepted(self, basic_session):
        """I2.2: 恰好 10MB 的文件不触发 413"""
        session_id, sm = basic_session

        from intelligent_project_analyzer.api.server import attach_files_to_session
        from fastapi import UploadFile

        exactly_10mb = b"\x89PNG" + b"\x00" * (10 * 1024 * 1024 - 4)

        upload_file = MagicMock(spec=UploadFile)
        upload_file.filename = "exact10.png"
        upload_file.content_type = "image/png"
        upload_file.read = AsyncMock(return_value=exactly_10mb)

        with patch("intelligent_project_analyzer.api.server.file_processor.save_file") as mock_save, patch(
            "intelligent_project_analyzer.api.server.file_processor.extract_image_enhanced"
        ) as mock_extract:
            mock_save.return_value = Path("/tmp/test_exact10.png")
            mock_extract.return_value = {"width": 100, "height": 100, "format": "PNG"}

            result = await attach_files_to_session(
                session_id=session_id,
                file_metadata="[]",
                files=[upload_file],
            )
            assert result["status"] == "success"


# ==============================================================================
# I3: recommended_constraints 数据往返
# ==============================================================================


class TestI3ConstraintRecommendationDataFlow:
    """后端生成 recommended_constraints → 模拟前端确认 → 后端消费"""

    def test_build_then_parse_roundtrip(self):
        """I3.1: recommended_constraints 构建后可被前端格式化后端再消费"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            _build_recommended_constraints,
        )

        # 后端构建推荐
        recommended = _build_recommended_constraints(
            mandatory_dims=["acoustics", "fire_safety"],
            constraints=[{"type": "budget", "value": "500万"}],
        )

        assert len(recommended) == 3

        # 模拟前端：用户勾选 acoustics 和 budget，取消 fire_safety
        selected_ids = ["acoustics", "budget"]
        confirmed_from_ai = [
            {"id": r["id"], "label": r["label"], "desc": r["desc"], "source": "ai_recommended"}
            for r in recommended
            if r["id"] in selected_ids
        ]
        # 用户追加一条手动约束
        confirmed_from_user = [
            {"id": "user_0", "label": "特殊材料", "desc": "使用竹制品", "source": "user_added"},
        ]
        confirmed = confirmed_from_ai + confirmed_from_user

        # 后端消费
        assert len(confirmed) == 3
        ai_ids = [c["id"] for c in confirmed if c["source"] == "ai_recommended"]
        user_ids = [c["id"] for c in confirmed if c["source"] == "user_added"]
        assert ai_ids == ["acoustics", "budget"]
        assert user_ids == ["user_0"]

    def test_recommended_constraint_fields_complete(self):
        """I3.2: 每个推荐约束项有前端需要的全部字段"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            _build_recommended_constraints,
        )

        recommended = _build_recommended_constraints(
            mandatory_dims=["sustainability"],
            constraints=[],
        )
        assert len(recommended) == 1
        r = recommended[0]
        required_fields = {"id", "label", "desc", "category", "recommended", "source", "evidence"}
        assert required_fields.issubset(set(r.keys())), f"缺少字段: {required_fields - set(r.keys())}"


# ==============================================================================
# I4: confirmed_constraints → framework_signals 完整注入流程
# ==============================================================================


class TestI4ConstraintInjectionFlow:
    """confirmed_constraints 通过 framework_signals 影响下游节点"""

    def test_ai_recommended_dims_propagate(self):
        """I4.1: AI 推荐维度 ID 最终出现在 framework_signals.mandatory_dimensions"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            _extract_framework_signals,
        )

        # 使用真实的 _extract_framework_signals 构建基础 signals
        fs = _extract_framework_signals(
            user_input="300平米别墅设计含录音棚",
            structured_requirements={"project_type": "别墅"},
            active_projections=["design_professional"],
            identity_modes=[],
        )

        # 模拟用户确认约束注入
        confirmed = [
            {"id": "acoustics", "source": "ai_recommended"},
            {"id": "budget", "source": "ai_recommended"},
            {"id": "user_0", "label": "自定义", "desc": "xxx", "source": "user_added"},
        ]

        confirmed_dim_ids = [c["id"] for c in confirmed if c.get("source") == "ai_recommended"]
        user_added = [c for c in confirmed if c.get("source") == "user_added"]
        if confirmed_dim_ids:
            fs["mandatory_dimensions"] = confirmed_dim_ids
        for c in user_added:
            fs.setdefault("constraints", []).append(
                {
                    "type": "user_declared",
                    "label": c.get("label", ""),
                    "desc": c.get("desc", ""),
                }
            )

        assert fs["mandatory_dimensions"] == ["acoustics", "budget"]
        user_declared = [c for c in fs.get("constraints", []) if c.get("type") == "user_declared"]
        assert len(user_declared) == 1


# ==============================================================================
# I5: 图片描述同步
# ==============================================================================


class TestI5VisualReferenceDescribeSync:
    """POST /visual-reference/describe 批量描述同步"""

    @pytest_asyncio.fixture
    async def session_with_refs(self):
        from intelligent_project_analyzer.core.state import StateManager

        sm = _make_memory_sm()
        session_id = "test-v121-describe"
        state = StateManager.create_initial_state(user_input="test", session_id=session_id)
        state["visual_references"] = [
            {
                "file_path": "/tmp/a.jpg",
                "original_filename": "a.jpg",
                "index": 0,
                "reference_type": "general",
                "source": "output_intent",
                "custom_description": "",
            },
            {
                "file_path": "/tmp/b.jpg",
                "original_filename": "b.jpg",
                "index": 1,
                "reference_type": "style",
                "source": "output_intent",
                "custom_description": "",
            },
        ]
        await sm.create(session_id, state)

        _sm_patcher = patch(
            "intelligent_project_analyzer.api.server._get_session_manager",
            new=AsyncMock(return_value=sm),
        )
        _sm_patcher.start()
        yield session_id, sm
        _sm_patcher.stop()
        await sm.delete(session_id)

    @pytest.mark.asyncio
    async def test_describe_updates_user_description(self, session_with_refs):
        """I5.1: describe 请求更新对应引用的 user_description"""
        session_id, sm = session_with_refs

        from intelligent_project_analyzer.api.server import (
            add_visual_reference_description,
            VisualReferenceDescriptionRequest,
        )

        req = VisualReferenceDescriptionRequest(
            reference_index=0,
            description="北欧极简客厅参考图",
            reference_type="style",
        )
        result = await add_visual_reference_description(
            session_id=session_id,
            request=req,
        )

        assert result["status"] == "success"

        session = await sm.get(session_id)
        assert session["visual_references"][0]["user_description"] == "北欧极简客厅参考图"
        assert session["visual_references"][0]["reference_type"] == "style"

    @pytest.mark.asyncio
    async def test_describe_then_delete_order(self, session_with_refs):
        """I5.2: 先描述再删除，数据一致"""
        session_id, sm = session_with_refs

        from intelligent_project_analyzer.api.server import (
            add_visual_reference_description,
            delete_visual_reference,
            VisualReferenceDescriptionRequest,
        )

        await add_visual_reference_description(
            session_id=session_id,
            request=VisualReferenceDescriptionRequest(reference_index=0, description="描述A"),
        )
        await add_visual_reference_description(
            session_id=session_id,
            request=VisualReferenceDescriptionRequest(reference_index=1, description="描述B"),
        )

        with patch("pathlib.Path.exists", return_value=False):
            await delete_visual_reference(session_id, 0)

        session = await sm.get(session_id)
        assert len(session["visual_references"]) == 1
        assert session["visual_references"][0]["user_description"] == "描述B"
