"""
GeoIP 服务单元测试

测试 IP 地址采集和地理位置识别功能
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# 测试前先设置环境，避免真实导入 geoip2
import sys
sys.modules['geoip2'] = MagicMock()
sys.modules['geoip2.database'] = MagicMock()
sys.modules['geoip2.errors'] = MagicMock()

from intelligent_project_analyzer.services.geoip_service import GeoIPService, get_geoip_service


class TestGeoIPService:
    """GeoIP 服务测试类"""
    
    @pytest.fixture
    def mock_db_path(self, tmp_path):
        """创建临时数据库路径"""
        db_file = tmp_path / "GeoLite2-City.mmdb"
        db_file.write_text("mock database")
        return str(db_file)
    
    @pytest.fixture
    def geoip_service(self, mock_db_path):
        """创建 GeoIP 服务实例"""
        return GeoIPService(db_path=mock_db_path)
    
    def test_init_with_custom_path(self, mock_db_path):
        """测试自定义数据库路径初始化"""
        service = GeoIPService(db_path=mock_db_path)
        assert service.db_path == mock_db_path
    
    def test_init_with_default_path(self):
        """测试默认数据库路径"""
        service = GeoIPService()
        assert "GeoLite2-City.mmdb" in service.db_path
        assert "data" in service.db_path
    
    def test_get_client_ip_from_x_forwarded_for(self, geoip_service):
        """测试从 X-Forwarded-For 头获取 IP"""
        mock_request = Mock()
        mock_request.headers.get = Mock(side_effect=lambda key: {
            "X-Forwarded-For": "1.2.3.4, 5.6.7.8"
        }.get(key))
        
        ip = geoip_service.get_client_ip(mock_request)
        assert ip == "1.2.3.4"  # 应返回第一个IP
    
    def test_get_client_ip_from_x_real_ip(self, geoip_service):
        """测试从 X-Real-IP 头获取 IP"""
        mock_request = Mock()
        mock_request.headers.get = Mock(side_effect=lambda key: {
            "X-Real-IP": "9.10.11.12"
        }.get(key))
        
        ip = geoip_service.get_client_ip(mock_request)
        assert ip == "9.10.11.12"
    
    def test_get_client_ip_from_client_host(self, geoip_service):
        """测试从直连 client.host 获取 IP"""
        mock_request = Mock()
        mock_request.headers.get = Mock(return_value=None)
        mock_request.client = Mock(host="13.14.15.16")
        
        ip = geoip_service.get_client_ip(mock_request)
        assert ip == "13.14.15.16"
    
    def test_get_client_ip_priority(self, geoip_service):
        """测试 IP 获取优先级"""
        mock_request = Mock()
        mock_request.headers.get = Mock(side_effect=lambda key: {
            "X-Forwarded-For": "1.1.1.1",
            "X-Real-IP": "2.2.2.2"
        }.get(key))
        mock_request.client = Mock(host="3.3.3.3")
        
        ip = geoip_service.get_client_ip(mock_request)
        # X-Forwarded-For 优先级最高
        assert ip == "1.1.1.1"
    
    def test_is_private_ip(self, geoip_service):
        """测试内网 IP 识别"""
        assert geoip_service._is_private_ip("10.0.0.1") == True
        assert geoip_service._is_private_ip("172.16.0.1") == True
        assert geoip_service._is_private_ip("172.31.255.255") == True
        assert geoip_service._is_private_ip("192.168.1.1") == True
        assert geoip_service._is_private_ip("8.8.8.8") == False
        assert geoip_service._is_private_ip("1.2.3.4") == False
    
    def test_get_localhost_location(self, geoip_service):
        """测试本地回环地址"""
        # 127.0.0.1
        location = geoip_service.get_location("127.0.0.1")
        assert location["ip"] == "127.0.0.1"
        assert location["city"] == "本地主机"
        assert location["country"] == "本地"
        assert location["is_valid"] == True
        
        # localhost
        location = geoip_service.get_location("localhost")
        assert location["city"] == "本地主机"
        
        # IPv6 回环
        location = geoip_service.get_location("::1")
        assert location["city"] == "本地主机"
    
    def test_get_private_ip_location(self, geoip_service):
        """测试内网 IP 定位"""
        location = geoip_service.get_location("192.168.1.100")
        assert location["ip"] == "192.168.1.100"
        assert location["city"] == "局域网"
        assert location["country"] == "内网"
        assert location["is_valid"] == True
        assert "note" in location
    
    def test_get_unknown_location(self, geoip_service):
        """测试未知 IP"""
        # 模拟 GeoIP 服务不可用
        geoip_service.is_available = False
        
        location = geoip_service.get_location("1.2.3.4")
        assert location["ip"] == "1.2.3.4"
        assert location["city"] == "未知"
        assert location["is_valid"] == False
        assert "error" in location
    
    @patch('geoip2.database.Reader')
    def test_get_location_success(self, mock_reader_class, geoip_service):
        """测试成功获取地理位置"""
        # 模拟 geoip2 响应
        mock_response = Mock()
        mock_response.country.names = {'zh-CN': '中国'}
        mock_response.country.name = 'China'
        mock_response.city.names = {'zh-CN': '深圳市'}
        mock_response.city.name = 'Shenzhen'
        mock_response.subdivisions.most_specific.names = {'zh-CN': '广东省'}
        mock_response.subdivisions.most_specific.name = 'Guangdong'
        mock_response.location.latitude = 22.5431
        mock_response.location.longitude = 114.0579
        mock_response.location.time_zone = 'Asia/Shanghai'
        
        mock_reader = Mock()
        mock_reader.city = Mock(return_value=mock_response)
        
        geoip_service.reader = mock_reader
        geoip_service.is_available = True
        
        location = geoip_service.get_location("1.2.3.4")
        
        assert location["ip"] == "1.2.3.4"
        assert location["country"] == "中国"
        assert location["province"] == "广东省"
        assert location["city"] == "深圳市"
        assert location["latitude"] == 22.5431
        assert location["longitude"] == 114.0579
        assert location["timezone"] == "Asia/Shanghai"
        assert location["is_valid"] == True
    
    @patch('geoip2.database.Reader')
    def test_get_location_address_not_found(self, mock_reader_class, geoip_service):
        """测试 IP 不在数据库中"""
        from geoip2.errors import AddressNotFoundError
        
        mock_reader = Mock()
        mock_reader.city = Mock(side_effect=AddressNotFoundError("Not found"))
        
        geoip_service.reader = mock_reader
        geoip_service.is_available = True
        
        location = geoip_service.get_location("1.2.3.4")
        
        assert location["ip"] == "1.2.3.4"
        assert location["city"] == "未知"
        assert location["is_valid"] == False
    
    def test_singleton_get_geoip_service(self):
        """测试全局单例"""
        service1 = get_geoip_service()
        service2 = get_geoip_service()
        
        # 应该返回相同的实例
        assert service1 is service2


class TestGeoIPServiceIntegration:
    """GeoIP 服务集成测试"""
    
    @pytest.fixture
    def mock_fastapi_request(self):
        """创建模拟的 FastAPI Request"""
        request = Mock()
        request.headers = {
            "User-Agent": "Mozilla/5.0 Test Browser",
            "X-Forwarded-For": "8.8.8.8",
        }
        request.headers.get = Mock(side_effect=lambda key, default=None: 
            request.headers.get(key, default))
        request.client = None
        return request
    
    def test_full_workflow_with_request(self, mock_fastapi_request):
        """测试完整的请求处理流程"""
        service = GeoIPService()
        
        # 获取 IP
        ip = service.get_client_ip(mock_fastapi_request)
        assert ip == "8.8.8.8"
        
        # 获取位置（如果数据库不存在会返回未知）
        location = service.get_location(ip)
        assert location["ip"] == "8.8.8.8"
        assert "city" in location
        assert "country" in location
    
    def test_edge_cases(self):
        """测试边界情况"""
        service = GeoIPService()
        
        # 空 IP
        location = service.get_location("")
        assert location["is_valid"] == False
        
        # 无效 IP 格式
        location = service.get_location("invalid_ip")
        assert location["is_valid"] == False
        
        # 特殊 IP
        location = service.get_location("0.0.0.0")
        assert "ip" in location


class TestGeoIPDataFormat:
    """测试地理位置数据格式"""
    
    def test_location_data_structure(self):
        """测试返回数据结构完整性"""
        service = GeoIPService()
        location = service.get_location("127.0.0.1")
        
        # 必需字段
        required_fields = ["ip", "country", "province", "city", 
                          "latitude", "longitude", "timezone", "is_valid"]
        
        for field in required_fields:
            assert field in location, f"缺少字段: {field}"
    
    def test_location_data_types(self):
        """测试数据类型正确性"""
        service = GeoIPService()
        location = service.get_location("127.0.0.1")
        
        assert isinstance(location["ip"], str)
        assert isinstance(location["country"], str)
        assert isinstance(location["city"], str)
        assert isinstance(location["is_valid"], bool)
        # latitude 和 longitude 可能是 None 或 float


class TestGeoIPErrorHandling:
    """测试错误处理"""
    
    def test_missing_database_file(self):
        """测试数据库文件不存在"""
        service = GeoIPService(db_path="/nonexistent/path/GeoLite2-City.mmdb")
        
        # 应该优雅降级，不抛出异常
        assert service.is_available == False
        
        # 仍能返回默认位置
        location = service.get_location("1.2.3.4")
        assert location["city"] == "未知"
    
    def test_corrupted_database(self):
        """测试损坏的数据库文件"""
        # 实际测试需要真实的损坏文件，这里只测试异常捕获
        service = GeoIPService()
        
        # 模拟读取器异常
        if service.reader:
            service.reader.city = Mock(side_effect=Exception("Database corrupted"))
            service.is_available = True
            
            location = service.get_location("1.2.3.4")
            assert location["is_valid"] == False


# Pytest 配置
def pytest_configure(config):
    """Pytest 配置钩子"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
