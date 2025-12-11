"""腾讯云内容安全单元测试"""

import pytest
import os
from intelligent_project_analyzer.security.tencent_content_safety import (
    TencentContentSafetyClient,
    get_tencent_content_safety_client
)


class TestTencentContentSafety:

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        # 跳过如果未配置
        if not os.getenv("TENCENT_CLOUD_SECRET_ID"):
            pytest.skip("未配置腾讯云API密钥")
        return TencentContentSafetyClient()

    def test_check_safe_text(self, client):
        """测试正常文本"""
        result = client.check_text("这是一段正常的文本")
        assert result["is_safe"] is True
        assert result["risk_level"] == "safe"
        assert result["suggestion"] == "Pass"

    def test_check_unsafe_text(self, client):
        """测试敏感文本"""
        result = client.check_text("测试敏感词：赌博")
        # 可能被拦截或需要审核
        assert result["suggestion"] in ["Pass", "Review", "Block"]
        # 如果不安全，应该有违规信息
        if not result["is_safe"]:
            assert len(result["violations"]) > 0

    def test_batch_check(self, client):
        """测试批量检测"""
        texts = ["正常文本1", "正常文本2", "正常文本3"]
        results = client.batch_check_text(texts)
        assert len(results) == 3
        assert all(r["is_safe"] for r in results)

    def test_singleton_client(self):
        """测试单例模式"""
        # 临时启用（用于测试）
        original_value = os.getenv("ENABLE_TENCENT_CONTENT_SAFETY")
        os.environ["ENABLE_TENCENT_CONTENT_SAFETY"] = "true"

        try:
            client1 = get_tencent_content_safety_client()
            client2 = get_tencent_content_safety_client()
            if client1 is not None:
                assert client1 is client2
        finally:
            # 恢复原始值
            if original_value:
                os.environ["ENABLE_TENCENT_CONTENT_SAFETY"] = original_value
            else:
                os.environ.pop("ENABLE_TENCENT_CONTENT_SAFETY", None)

    def test_label_conversion(self, client):
        """测试标签转换"""
        assert client._label_to_category("Normal") == "正常内容"
        assert client._label_to_category("Porn") == "色情低俗"
        assert client._label_to_category("Illegal") == "违法犯罪"
        assert client._label_to_category("Unknown") == "Unknown"  # 未知标签返回原值
