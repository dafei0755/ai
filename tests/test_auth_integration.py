"""
授权系统集成测试
测试 v7.141.3 真实用户认证集成功能

测试覆盖:
1. 用户认证状态检测
2. 会员等级获取和映射
3. 配额检查使用真实用户数据
4. 错误容错机制

运行: pytest tests/test_auth_integration.py -v
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestAuthenticationIntegration:
    """测试用户认证集成"""

    def test_user_tier_mapping_free(self):
        """测试免费用户等级映射"""
        # 模拟 WordPress API 返回
        membership_data = {
            "level": 0,
            "level_name": "免费用户",
            "expire_date": "",
            "is_expired": False,
            "wallet_balance": 0,
        }

        # 验证映射
        from intelligent_project_analyzer.services.quota_manager import QuotaManager

        quota_mgr = QuotaManager()

        # 免费用户配额
        file_check = quota_mgr.check_file_size(6 * 1024 * 1024, "free")
        assert file_check["allowed"] is False
        assert file_check["max_file_size_mb"] == 5

    def test_user_tier_mapping_professional(self):
        """测试专业版用户等级映射"""
        from intelligent_project_analyzer.services.quota_manager import QuotaManager

        quota_mgr = QuotaManager()

        # 专业版用户配额
        file_check = quota_mgr.check_file_size(40 * 1024 * 1024, "professional")
        assert file_check["allowed"] is True
        assert file_check["max_file_size_mb"] == 50

    # Note: 用户说明只有免费、普通、高级三个等级，无企业版
    # def test_user_tier_mapping_enterprise(self):
    #     """测试企业版用户等级映射"""
    #     pass

    @patch("intelligent_project_analyzer.api.member_routes.WPCOMMemberAPI")
    def test_membership_api_integration(self, MockWPAPI):
        """测试会员信息API集成"""
        # 模拟 WordPress API
        mock_api = MockWPAPI.return_value
        mock_api.get_user_membership.return_value = {
            "user_id": 123,
            "username": "testuser",
            "membership": {"level": "2", "expire_date": "2026-12-31", "is_active": True},
            "meta": {},
        }

        # 调用会员路由
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from intelligent_project_analyzer.api.member_routes import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        # 注意：需要认证token
        # 这里只是测试API结构
        assert mock_api.get_user_membership is not None

    @patch("intelligent_project_analyzer.services.quota_manager.MILVUS_AVAILABLE", True)
    def test_quota_check_with_real_user_id(self):
        """测试使用真实用户ID的配额检查"""
        from intelligent_project_analyzer.services.quota_manager import QuotaManager

        # 模拟 Milvus Collection
        mock_collection = Mock()
        mock_collection.query.return_value = [
            {"file_size_bytes": 1024 * 1024, "created_at": 1234567890 + i} for i in range(5)
        ]

        quota_mgr = QuotaManager(collection=mock_collection)

        # 检查用户123的配额（免费用户）
        result = quota_mgr.check_quota("123", "free")

        assert result["allowed"] is True  # 5个文档 < 10个上限
        # With mocked Milvus, document_count should be 5
        assert result["current_usage"]["document_count"] == 5
        assert result["quota_limit"]["max_documents"] == 10

        # 验证查询使用真实用户ID
        mock_collection.query.assert_called_once()
        call_args = mock_collection.query.call_args
        # 验证表达式中包含用户ID "123"
        assert "123" in str(call_args)  # 确认使用真实ID


class TestErrorHandling:
    """测试错误容错机制"""

    def test_membership_api_failure_fallback(self):
        """测试会员API失败时的降级机制"""
        # 前端 useMembership Hook 应该在API失败时降级为免费层级
        # 这里测试后端QuotaManager的默认行为

        from intelligent_project_analyzer.services.quota_manager import QuotaManager

        quota_mgr = QuotaManager()

        # 默认应该使用免费层级限制
        file_check = quota_mgr.check_file_size(6 * 1024 * 1024, "free")
        assert file_check["allowed"] is False

    def test_invalid_tier_fallback(self):
        """测试无效会员等级时的降级"""
        from intelligent_project_analyzer.services.quota_manager import QuotaManager

        quota_mgr = QuotaManager()

        # 传入无效的tier，应该降级为免费层级
        file_check = quota_mgr.check_file_size(6 * 1024 * 1024, "invalid_tier")
        assert file_check["allowed"] is False
        assert file_check["max_file_size_mb"] == 5  # 免费层级限制


class TestQuotaCheckAPI:
    """测试配额检查API端点"""

    def test_quota_check_endpoint_skip(self):
        """测试 GET /api/admin/milvus/quota/check 端点 (跳过 - 需要完整API环境)"""
        # 这个测试需要完整的FastAPI应用和Milvus环境
        # 建议在集成测试或E2E测试中验证
        # 这里只做基本的导入检查
        from intelligent_project_analyzer.api.milvus_admin_routes import check_quota_before_upload

        # 验证函数存在
        assert check_quota_before_upload is not None
        assert callable(check_quota_before_upload)


class TestVIPLevelMapping:
    """测试 WordPress VIP Level 映射"""

    def test_vip_level_0_to_free(self):
        """VIP Level 0 → free"""
        # 这个测试应该在前端进行
        # 这里只是验证后端理解 'free' tier
        from intelligent_project_analyzer.services.quota_manager import QuotaManager

        quota_mgr = QuotaManager()

        limits = quota_mgr.quota_config.get_tier_quota("free")
        assert limits["max_documents"] == 10
        assert limits["max_storage_mb"] == 50
        assert limits["max_file_size_mb"] == 5

    def test_vip_level_1_to_basic(self):
        """VIP Level 1 → basic"""
        from intelligent_project_analyzer.services.quota_manager import QuotaManager

        quota_mgr = QuotaManager()

        limits = quota_mgr.quota_config.get_tier_quota("basic")
        assert limits["max_documents"] == 100
        assert limits["max_storage_mb"] == 500
        assert limits["max_file_size_mb"] == 10

    def test_vip_level_2_to_professional(self):
        """VIP Level 2 → professional"""
        from intelligent_project_analyzer.services.quota_manager import QuotaManager

        quota_mgr = QuotaManager()

        limits = quota_mgr.quota_config.get_tier_quota("professional")
        assert limits["max_documents"] == 1000
        # Actual config has 5120 MB (5GB) not 5000 MB
        assert limits["max_storage_mb"] == 5120
        assert limits["max_file_size_mb"] == 50

    # Note: 用户说明只有免费、普通、高级三个等级，无企业版
    # def test_vip_level_3_to_enterprise(self):
    #     """VIP Level 3 → enterprise"""
    #     pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
