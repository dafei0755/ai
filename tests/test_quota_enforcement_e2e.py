"""
配额管理端到端测试 (E2E)

测试覆盖:
1. 文件大小检查（单文件上传）
2. 配额超限检查（文档数量）
3. 配额超限检查（存储空间）
4. 系统知识库豁免检查
5. 配额警告触发（80% 阈值）

运行: pytest tests/test_quota_enforcement_e2e.py -v
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


# 模拟配置（避免实际连接）
@pytest.fixture(autouse=True)
def mock_settings():
    """模拟 settings 配置"""
    with patch("intelligent_project_analyzer.api.milvus_admin_routes.settings") as mock_settings:
        mock_settings.milvus.host = "localhost"
        mock_settings.milvus.port = 19530
        mock_settings.milvus.collection_name = "test_collection"
        mock_settings.milvus.embedding_model = "test-model"
        mock_settings.milvus.reranker_model = "test-reranker"
        yield mock_settings


@pytest.fixture
def mock_quota_manager():
    """模拟 QuotaManager"""
    with patch("intelligent_project_analyzer.api.milvus_admin_routes.QuotaManager") as MockQuotaManager:
        manager = MockQuotaManager.return_value
        yield manager


@pytest.fixture
def mock_milvus_collection():
    """模拟 Milvus Collection"""
    with patch("intelligent_project_analyzer.api.milvus_admin_routes.Collection") as MockCollection, patch(
        "intelligent_project_analyzer.api.milvus_admin_routes.connections"
    ):
        collection = MockCollection.return_value
        collection.insert = Mock()
        collection.flush = Mock()
        collection.num_entities = 5  # 模拟已有 5 个文档
        yield collection


class TestFileUploadQuotaChecking:
    """测试文件上传配额检查"""

    @pytest.mark.asyncio
    async def test_free_user_upload_large_file_should_fail(self, mock_quota_manager, mock_milvus_collection):
        """
        测试用例 1: 免费用户上传 6MB 文件（应失败）

        预期: HTTP 413, 错误信息包含文件大小超限
        """
        from io import BytesIO

        from fastapi import HTTPException, UploadFile

        from intelligent_project_analyzer.api.milvus_admin_routes import import_file

        # 模拟 6MB 文件
        large_content = b"A" * (6 * 1024 * 1024)
        file = UploadFile(filename="large_file.txt", file=BytesIO(large_content))

        # 模拟配额检查返回值
        mock_quota_manager.check_file_size.return_value = {
            "allowed": False,
            "error": "文件大小超过限制 (6.0/5 MB)",
            "file_size_mb": 6.0,
            "max_file_size_mb": 5,
        }

        # 执行上传
        with pytest.raises(HTTPException) as exc_info:
            await import_file(
                file=file,
                document_type="文档",
                project_type="",
                owner_type="user",
                owner_id="user_123",
                visibility="public",
                team_id="",
                user_tier="free",
            )

        # 验证 HTTP 状态码
        assert exc_info.value.status_code == 413

        # 验证错误详情
        detail = exc_info.value.detail
        assert detail["error"] == "file_size_exceeded"
        assert detail["file_size_mb"] == 6.0
        assert detail["max_file_size_mb"] == 5
        assert detail["user_tier"] == "free"

        # 验证 QuotaManager.check_file_size 被调用
        mock_quota_manager.check_file_size.assert_called_once_with(6 * 1024 * 1024, "free")  # 文件大小（字节）

    @pytest.mark.asyncio
    async def test_professional_user_upload_large_file_should_succeed(self, mock_quota_manager, mock_milvus_collection):
        """
        测试用例 2: 专业版用户上传 40MB 文件（应成功）

        预期: HTTP 200, 成功导入
        """
        from io import BytesIO

        from fastapi import UploadFile

        from intelligent_project_analyzer.api.milvus_admin_routes import import_file

        # 模拟 40MB 文件
        large_content = b"B" * (40 * 1024 * 1024)
        file = UploadFile(filename="professional_file.txt", file=BytesIO(large_content))

        # 模拟配额检查通过
        mock_quota_manager.check_file_size.return_value = {
            "allowed": True,
            "file_size_mb": 40.0,
            "max_file_size_mb": 50,
        }
        mock_quota_manager.check_quota.return_value = {
            "allowed": True,
            "warnings": [],
            "current_usage": {"document_count": 5, "storage_mb": 100},
            "quota_limit": {"max_documents": 1000, "max_storage_mb": 5000},
        }
        mock_quota_manager.calculate_expiry_timestamp.return_value = int(time.time()) + 365 * 24 * 3600

        # 模拟 Embedding 模型
        with patch("intelligent_project_analyzer.api.milvus_admin_routes.SentenceTransformer") as MockEmbedding:
            mock_embedding = MockEmbedding.return_value
            mock_embedding.encode.return_value = [[0.1] * 768]  # 模拟向量

            # 执行上传
            result = await import_file(
                file=file,
                document_type="文档",
                project_type="",
                owner_type="user",
                owner_id="user_456",
                visibility="public",
                team_id="",
                user_tier="professional",
            )

        # 验证成功响应
        assert result["success"] is True
        assert result["total_documents"] == 1
        assert result["filename"] == "professional_file.txt"

        # 验证 Collection.insert 被调用
        mock_milvus_collection.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_free_user_exceed_document_quota_should_fail(self, mock_quota_manager, mock_milvus_collection):
        """
        测试用例 3: 免费用户文档数量超限（应失败）

        预期: HTTP 403, 错误信息包含配额超限详情
        """
        from io import BytesIO

        from fastapi import HTTPException, UploadFile

        from intelligent_project_analyzer.api.milvus_admin_routes import import_file

        # 模拟小文件
        small_content = b"C" * 1024  # 1KB
        file = UploadFile(filename="small_file.txt", file=BytesIO(small_content))

        # 模拟文件大小检查通过
        mock_quota_manager.check_file_size.return_value = {
            "allowed": True,
            "file_size_mb": 0.001,
            "max_file_size_mb": 5,
        }

        # 模拟配额超限
        mock_quota_manager.check_quota.return_value = {
            "allowed": False,
            "errors": ["文档数量已达上限 (10/10)"],
            "current_usage": {"document_count": 10, "storage_mb": 25},
            "quota_limit": {"max_documents": 10, "max_storage_mb": 50, "max_file_size_mb": 5},
        }

        # 执行上传
        with pytest.raises(HTTPException) as exc_info:
            await import_file(
                file=file,
                document_type="文档",
                project_type="",
                owner_type="user",
                owner_id="user_quota_test",
                visibility="public",
                team_id="",
                user_tier="free",
            )

        # 验证 HTTP 状态码
        assert exc_info.value.status_code == 403

        # 验证错误详情
        detail = exc_info.value.detail
        assert detail["error"] == "quota_exceeded"
        assert "文档数量已达上限" in detail["errors"][0]
        assert detail["current_usage"]["document_count"] == 10
        assert detail["quota_limit"]["max_documents"] == 10

        # 验证建议存在
        assert "suggestions" in detail
        assert len(detail["suggestions"]) > 0

    @pytest.mark.asyncio
    async def test_system_knowledge_base_exempt_quota(self, mock_quota_manager, mock_milvus_collection):
        """
        测试用例 4: 系统知识库不受配额限制

        预期: HTTP 200, 不调用配额检查
        """
        from io import BytesIO

        from fastapi import UploadFile

        from intelligent_project_analyzer.api.milvus_admin_routes import import_file

        # 模拟大文件
        large_content = b"D" * (100 * 1024 * 1024)  # 100MB
        file = UploadFile(filename="system_file.txt", file=BytesIO(large_content))

        # 模拟 Embedding 模型
        with patch("intelligent_project_analyzer.api.milvus_admin_routes.SentenceTransformer") as MockEmbedding:
            mock_embedding = MockEmbedding.return_value
            mock_embedding.encode.return_value = [[0.2] * 768]
            mock_quota_manager.calculate_expiry_timestamp.return_value = 0

            # 执行上传
            result = await import_file(
                file=file,
                document_type="文档",
                project_type="",
                owner_type="system",
                owner_id="public",
                visibility="public",
                team_id="",
                user_tier="free",  # 系统知识库不受此参数影响
            )

        # 验证成功
        assert result["success"] is True

        # 验证配额检查未被调用
        mock_quota_manager.check_file_size.assert_not_called()
        mock_quota_manager.check_quota.assert_not_called()

    @pytest.mark.asyncio
    async def test_quota_warning_logged_at_80_percent(self, mock_quota_manager, mock_milvus_collection, caplog):
        """
        测试用例 5: 配额警告触发（80% 阈值）

        预期: 上传成功，但日志包含警告信息
        """
        import logging
        from io import BytesIO

        from fastapi import UploadFile

        from intelligent_project_analyzer.api.milvus_admin_routes import import_file

        caplog.set_level(logging.WARNING)

        # 模拟小文件
        small_content = b"E" * 1024
        file = UploadFile(filename="warning_file.txt", file=BytesIO(small_content))

        # 模拟文件大小检查通过
        mock_quota_manager.check_file_size.return_value = {
            "allowed": True,
            "file_size_mb": 0.001,
            "max_file_size_mb": 5,
        }

        # 模拟配额警告（80% 使用率）
        mock_quota_manager.check_quota.return_value = {
            "allowed": True,
            "warnings": ["文档数量接近上限 (8/10, 80.0%)"],
            "current_usage": {"document_count": 8, "storage_mb": 40},
            "quota_limit": {"max_documents": 10, "max_storage_mb": 50},
        }
        mock_quota_manager.calculate_expiry_timestamp.return_value = int(time.time()) + 30 * 24 * 3600

        # 模拟 Embedding 模型
        with patch("intelligent_project_analyzer.api.milvus_admin_routes.SentenceTransformer") as MockEmbedding:
            mock_embedding = MockEmbedding.return_value
            mock_embedding.encode.return_value = [[0.3] * 768]

            # 执行上传
            result = await import_file(
                file=file,
                document_type="文档",
                project_type="",
                owner_type="user",
                owner_id="user_warning_test",
                visibility="public",
                team_id="",
                user_tier="free",
            )

        # 验证成功
        assert result["success"] is True

        # 验证警告日志
        assert any("配额警告" in record.message for record in caplog.records)


class TestQuotaManagerIntegration:
    """测试 QuotaManager 集成"""

    def test_quota_manager_check_file_size(self):
        """测试文件大小检查逻辑"""
        from intelligent_project_analyzer.services.quota_manager import QuotaManager

        manager = QuotaManager()

        # 免费用户上传 6MB 文件（超限）
        result = manager.check_file_size(6 * 1024 * 1024, "free")
        assert result["allowed"] is False
        assert result["file_size_mb"] == 6.0
        assert result["max_file_size_mb"] == 5

        # 专业版用户上传 40MB 文件（通过）
        result = manager.check_file_size(40 * 1024 * 1024, "professional")
        assert result["allowed"] is True
        assert result["file_size_mb"] == 40.0
        assert result["max_file_size_mb"] == 50

    @patch("intelligent_project_analyzer.services.quota_manager.Collection")
    def test_quota_manager_check_quota_exceeded(self, MockCollection):
        """测试配额超限检查逻辑"""
        from intelligent_project_analyzer.services.quota_manager import QuotaManager

        # 模拟 Collection 查询
        mock_collection = MockCollection.return_value
        mock_collection.query.return_value = [{"file_size_bytes": 10 * 1024 * 1024} for _ in range(10)]

        manager = QuotaManager(collection=mock_collection)

        # 检查免费用户配额（10 个文档已满）
        result = manager.check_quota("user_123", "free")

        assert result["allowed"] is False
        assert "文档数量已达上限" in result["errors"][0]
        assert result["current_usage"]["document_count"] == 10
        assert result["quota_limit"]["max_documents"] == 10

    @patch("intelligent_project_analyzer.services.quota_manager.Collection")
    def test_quota_manager_warning_at_80_percent(self, MockCollection):
        """测试 80% 配额警告触发"""
        from intelligent_project_analyzer.services.quota_manager import QuotaManager

        # 模拟 Collection 查询（8 个文档，80% 使用率）
        mock_collection = MockCollection.return_value
        mock_collection.query.return_value = [{"file_size_bytes": 5 * 1024 * 1024} for _ in range(8)]

        manager = QuotaManager(collection=mock_collection)

        # 检查免费用户配额
        result = manager.check_quota("user_456", "free")

        assert result["allowed"] is True  # 仍可上传
        assert len(result["warnings"]) > 0  # 但有警告
        assert "接近上限" in result["warnings"][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
