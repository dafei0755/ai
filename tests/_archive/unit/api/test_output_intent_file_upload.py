"""
单元测试：输出意图文件上传端点 (v11.2)
测试 POST /api/analysis/{session_id}/attach-files 端点
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path


@pytest.fixture
def mock_session_manager():
    """Mock SessionManager"""
    sm = AsyncMock()
    sm.get = AsyncMock(
        return_value={
            "session_id": "test-session-123",
            "visual_references": [{"file_path": "existing.jpg", "source": "initial"}],
        }
    )
    sm.update = AsyncMock()
    return sm


@pytest.fixture
def mock_file_processor():
    """Mock FileProcessor"""
    fp = MagicMock()
    fp.save_file = AsyncMock(return_value=Path("uploads/test-session-123/test.jpg"))
    fp.extract_image_enhanced = AsyncMock(
        return_value={
            "width": 1920,
            "height": 1080,
            "format": "JPEG",
            "vision_analysis": "Modern minimalist interior",
            "structured_features": {"style": ["minimalist", "modern"]},
        }
    )
    fp.extract_content = AsyncMock(
        return_value={
            "summary": "PDF document summary",
        }
    )
    return fp


@pytest.fixture
def mock_upload_file():
    """Mock UploadFile"""
    file = MagicMock()
    file.filename = "test_image.jpg"
    file.content_type = "image/jpeg"
    file.read = AsyncMock(return_value=b"fake image data" * 1000)
    return file


class TestAttachFilesEndpoint:
    """测试 attach-files 端点核心逻辑"""

    @pytest.mark.asyncio
    async def test_attach_image_success(self, mock_session_manager, mock_file_processor, mock_upload_file):
        """测试成功上传图片文件"""

        with patch(
            "intelligent_project_analyzer.api.server._get_session_manager", return_value=mock_session_manager
        ), patch("intelligent_project_analyzer.api.server.file_processor", mock_file_processor):
            # 模拟端点调用
            from intelligent_project_analyzer.api.server import attach_files_to_session

            result = await attach_files_to_session(
                session_id="test-session-123",
                file_metadata='[{"filename": "test_image.jpg", "categories": ["style"], "custom_description": "Nordic style reference"}]',
                files=[mock_upload_file],
            )

            # 验证返回结果
            assert result["status"] == "success"
            assert result["added_count"] == 1
            assert result["total_count"] == 2  # 1 existing + 1 new
            assert result["start_index"] == 1
            assert result["end_index"] == 1

            # 验证 session 更新被调用
            mock_session_manager.update.assert_called_once()
            call_args = mock_session_manager.update.call_args
            assert call_args[0][0] == "test-session-123"
            updated_refs = call_args[0][1]["visual_references"]
            assert len(updated_refs) == 2

            # 验证新增的引用结构
            new_ref = updated_refs[1]
            assert new_ref["reference_type"] == "style"
            assert new_ref["user_description"] == "Nordic style reference"
            assert new_ref["source"] == "output_intent"
            assert "categories" in new_ref
            assert "style" in new_ref["categories"]

    @pytest.mark.asyncio
    async def test_attach_pdf_success(self, mock_session_manager, mock_file_processor):
        """测试上传 PDF 文件"""
        pdf_file = MagicMock()
        pdf_file.filename = "requirements.pdf"
        pdf_file.content_type = "application/pdf"
        pdf_file.read = AsyncMock(return_value=b"fake pdf data" * 500)

        with patch(
            "intelligent_project_analyzer.api.server._get_session_manager", return_value=mock_session_manager
        ), patch("intelligent_project_analyzer.api.server.file_processor", mock_file_processor):
            from intelligent_project_analyzer.api.server import attach_files_to_session

            result = await attach_files_to_session(
                session_id="test-session-123",
                file_metadata='[{"filename": "requirements.pdf", "categories": [], "custom_description": ""}]',
                files=[pdf_file],
            )

            assert result["status"] == "success"
            assert result["added_count"] == 1

            # 验证调用了非图片处理逻辑
            mock_file_processor.extract_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_attach_multiple_files(self, mock_session_manager, mock_file_processor):
        """测试批量上传多个文件"""
        files = []
        for i in range(3):
            file = MagicMock()
            file.filename = f"image_{i}.jpg"
            file.content_type = "image/jpeg"
            file.read = AsyncMock(return_value=b"data" * 100)
            files.append(file)

        with patch(
            "intelligent_project_analyzer.api.server._get_session_manager", return_value=mock_session_manager
        ), patch("intelligent_project_analyzer.api.server.file_processor", mock_file_processor):
            from intelligent_project_analyzer.api.server import attach_files_to_session

            result = await attach_files_to_session(session_id="test-session-123", file_metadata="[]", files=files)

            assert result["added_count"] == 3
            assert result["total_count"] == 4  # 1 existing + 3 new

    @pytest.mark.asyncio
    async def test_file_too_large_skipped(self, mock_session_manager, mock_file_processor):
        """测试超大文件返回 413"""
        large_file = MagicMock()
        large_file.filename = "huge.jpg"
        large_file.content_type = "image/jpeg"
        large_file.read = AsyncMock(return_value=b"x" * (11 * 1024 * 1024))  # 11MB > 10MB limit

        with patch(
            "intelligent_project_analyzer.api.server._get_session_manager", return_value=mock_session_manager
        ), patch("intelligent_project_analyzer.api.server.file_processor", mock_file_processor):
            from intelligent_project_analyzer.api.server import attach_files_to_session

            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await attach_files_to_session(session_id="test-session-123", file_metadata="[]", files=[large_file])
            assert exc_info.value.status_code == 413

    @pytest.mark.asyncio
    async def test_session_not_found(self, mock_session_manager, mock_file_processor, mock_upload_file):
        """测试会话不存在时返回 404"""
        mock_session_manager.get = AsyncMock(return_value=None)

        with patch(
            "intelligent_project_analyzer.api.server._get_session_manager", return_value=mock_session_manager
        ), patch("intelligent_project_analyzer.api.server.file_processor", mock_file_processor):
            from intelligent_project_analyzer.api.server import attach_files_to_session
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await attach_files_to_session(session_id="non-existent", file_metadata="[]", files=[mock_upload_file])

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_category_to_reference_type_mapping(
        self, mock_session_manager, mock_file_processor, mock_upload_file
    ):
        """测试 category → reference_type 映射逻辑"""
        test_cases = [
            (["style"], "style"),
            (["layout"], "layout"),
            (["color"], "color"),
            (["other"], "general"),
            ([], "general"),
        ]

        for categories, expected_type in test_cases:
            # 重置 mock
            mock_session_manager.reset_mock()
            mock_session_manager.get = AsyncMock(return_value={"session_id": "test", "visual_references": []})
            mock_session_manager.update = AsyncMock()

            with patch(
                "intelligent_project_analyzer.api.server._get_session_manager", return_value=mock_session_manager
            ), patch("intelligent_project_analyzer.api.server.file_processor", mock_file_processor):
                from intelligent_project_analyzer.api.server import attach_files_to_session

                # 注意：categories 需要用 JSON 格式字符串
                categories_str = json.dumps(categories)
                metadata = (
                    f'[{{"filename": "test_image.jpg", "categories": {categories_str}, "custom_description": ""}}]'
                )
                await attach_files_to_session(session_id="test", file_metadata=metadata, files=[mock_upload_file])

                call_args = mock_session_manager.update.call_args
                updated_refs = call_args[0][1]["visual_references"]
                assert updated_refs[0]["reference_type"] == expected_type

    @pytest.mark.asyncio
    async def test_malformed_metadata_handled(self, mock_session_manager, mock_file_processor, mock_upload_file):
        """测试畸形 JSON metadata 被安全处理"""
        with patch(
            "intelligent_project_analyzer.api.server._get_session_manager", return_value=mock_session_manager
        ), patch("intelligent_project_analyzer.api.server.file_processor", mock_file_processor):
            from intelligent_project_analyzer.api.server import attach_files_to_session

            # 畸形 JSON 应回退到空数组，不应崩溃
            result = await attach_files_to_session(
                session_id="test-session-123", file_metadata="{invalid json", files=[mock_upload_file]
            )

            assert result["status"] == "success"
            assert result["added_count"] == 1

    @pytest.mark.asyncio
    async def test_partial_failure_resilience(self, mock_session_manager, mock_file_processor):
        """测试部分文件失败时的容错处理"""
        good_file = MagicMock()
        good_file.filename = "good.jpg"
        good_file.content_type = "image/jpeg"
        good_file.read = AsyncMock(return_value=b"data" * 100)

        bad_file = MagicMock()
        bad_file.filename = "bad.jpg"
        bad_file.content_type = "image/jpeg"
        bad_file.read = AsyncMock(side_effect=Exception("Read error"))

        with patch(
            "intelligent_project_analyzer.api.server._get_session_manager", return_value=mock_session_manager
        ), patch("intelligent_project_analyzer.api.server.file_processor", mock_file_processor):
            from intelligent_project_analyzer.api.server import attach_files_to_session

            result = await attach_files_to_session(
                session_id="test-session-123", file_metadata="[]", files=[good_file, bad_file]
            )

            # 应只添加成功的文件
            assert result["added_count"] == 1
            assert result["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
