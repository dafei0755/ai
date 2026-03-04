"""
GeoIP 集成测试 - 测试与其他模块的集成

测试 GeoIP 服务与 FastAPI、Session 管理器的集成
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from intelligent_project_analyzer.services.geoip_service import get_geoip_service


class TestGeoIPServerIntegration:
    """测试与 server.py 的集成"""
    
    @pytest.fixture
    def mock_request(self):
        """创建模拟的 FastAPI Request"""
        request = Mock()
        request.headers = Mock()
        request.headers.get = Mock(side_effect=lambda key, default=None: {
            "X-Forwarded-For": "203.208.60.1",  # Google 香港 IP
            "User-Agent": "Mozilla/5.0"
        }.get(key, default))
        request.client = Mock(host="203.208.60.1")
        return request
    
    @pytest.fixture
    def mock_analysis_request(self):
        """创建模拟的分析请求"""
        request = Mock()
        request.user_input = "我需要设计一个现代简约风格的住宅"
        request.analysis_mode = "normal"
        return request
    
    def test_ip_collection_in_start_analysis(self, mock_request, mock_analysis_request):
        """测试在 start_analysis 中采集 IP"""
        geoip_service = get_geoip_service()
        
        # 获取客户端 IP
        client_ip = geoip_service.get_client_ip(mock_request)
        assert client_ip == "203.208.60.1"
        
        # 获取位置信息
        location_info = geoip_service.get_location(client_ip)
        
        # 验证数据结构
        assert "ip" in location_info
        assert "city" in location_info
        assert "country" in location_info
        assert "latitude" in location_info
        assert "longitude" in location_info
    
    def test_session_metadata_structure(self, mock_request):
        """测试 session metadata 数据结构"""
        geoip_service = get_geoip_service()
        
        client_ip = geoip_service.get_client_ip(mock_request)
        location_info = geoip_service.get_location(client_ip)
        
        # 构建 metadata（模拟 server.py 中的逻辑）
        metadata = {
            "client_ip": client_ip,
            "location": location_info.get("city", "未知"),
            "geo_info": location_info,
            "user_agent": mock_request.headers.get("User-Agent", ""),
        }
        
        # 验证结构
        assert metadata["client_ip"] == client_ip
        assert isinstance(metadata["location"], str)
        assert isinstance(metadata["geo_info"], dict)
        assert metadata["user_agent"] == "Mozilla/5.0"


class TestGeoIPAdminRoutesIntegration:
    """测试与 admin_routes.py 的集成"""
    
    @pytest.fixture
    def mock_sessions(self):
        """创建模拟的会话数据"""
        return [
            {
                "session_id": "user1-20260103-abc123",
                "user_id": "user1",
                "created_at": datetime.now().isoformat(),
                "metadata": {
                    "client_ip": "203.208.60.1",
                    "location": "香港",
                    "geo_info": {
                        "ip": "203.208.60.1",
                        "country": "中国",
                        "province": "香港",
                        "city": "香港",
                        "latitude": 22.2855,
                        "longitude": 114.1577,
                        "is_valid": True
                    }
                }
            },
            {
                "session_id": "user2-20260103-def456",
                "user_id": "user2",
                "created_at": datetime.now().isoformat(),
                "metadata": {
                    "client_ip": "1.2.3.4",
                    "location": "深圳市",
                    "geo_info": {
                        "ip": "1.2.3.4",
                        "country": "中国",
                        "province": "广东省",
                        "city": "深圳市",
                        "latitude": 22.5431,
                        "longitude": 114.0579,
                        "is_valid": True
                    }
                }
            },
            {
                "session_id": "guest-20260103-ghi789",
                "user_id": "guest",
                "created_at": datetime.now().isoformat(),
                "metadata": {
                    "client_ip": "127.0.0.1",
                    "location": "本地主机",
                    "geo_info": {
                        "ip": "127.0.0.1",
                        "country": "本地",
                        "city": "本地主机",
                        "is_valid": True
                    }
                }
            }
        ]
    
    def test_region_distribution_extraction(self, mock_sessions):
        """测试从 sessions 中提取地区分布"""
        region_distribution = {}
        region_coords = {}
        
        for session in mock_sessions:
            metadata = session.get("metadata", {})
            location = metadata.get("location", "未知")
            geo_info = metadata.get("geo_info", {})
            
            # 统计分布
            region_distribution[location] = region_distribution.get(location, 0) + 1
            
            # 收集坐标
            if geo_info.get("latitude") and geo_info.get("longitude"):
                if location not in region_coords:
                    region_coords[location] = {
                        "lat": geo_info["latitude"],
                        "lng": geo_info["longitude"],
                        "country": geo_info.get("country", ""),
                        "province": geo_info.get("province", "")
                    }
        
        # 验证统计结果
        assert region_distribution["香港"] == 1
        assert region_distribution["深圳市"] == 1
        assert region_distribution["本地主机"] == 1
        
        # 验证坐标数据
        assert "香港" in region_coords
        assert region_coords["香港"]["lat"] == 22.2855
        assert region_coords["深圳市"]["lng"] == 114.0579
    
    def test_region_list_with_coords(self, mock_sessions):
        """测试带坐标的地区列表生成"""
        region_distribution = {}
        region_coords = {}
        
        # 统计（复用上面的逻辑）
        for session in mock_sessions:
            metadata = session.get("metadata", {})
            location = metadata.get("location", "未知")
            geo_info = metadata.get("geo_info", {})
            
            region_distribution[location] = region_distribution.get(location, 0) + 1
            
            if geo_info.get("latitude") and geo_info.get("longitude"):
                if location not in region_coords:
                    region_coords[location] = {
                        "lat": geo_info["latitude"],
                        "lng": geo_info["longitude"],
                        "country": geo_info.get("country", ""),
                        "province": geo_info.get("province", "")
                    }
        
        # 生成列表（模拟 admin_routes.py 逻辑）
        region_list = []
        for region, count in sorted(region_distribution.items(), key=lambda x: x[1], reverse=True):
            item = {"region": region, "count": count}
            if region in region_coords:
                item.update(region_coords[region])
            region_list.append(item)
        
        # 验证
        assert len(region_list) == 3
        assert all("region" in item and "count" in item for item in region_list)
        
        # 检查有坐标的项
        coord_items = [item for item in region_list if "lat" in item and "lng" in item]
        assert len(coord_items) == 3  # 所有项都有坐标


class TestGeoIPFallbackMechanism:
    """测试回退机制"""
    
    def test_fallback_to_user_input(self):
        """测试回退到用户输入提取城市"""
        session = {
            "user_input": "我在深圳需要设计一个住宅",
            "metadata": {
                "location": "未知",  # IP 定位失败
                "geo_info": {"is_valid": False}
            }
        }
        
        # 模拟 admin_routes.py 的回退逻辑
        cities = ["北京", "上海", "广州", "深圳", "杭州"]
        user_input = session.get("user_input", "")
        metadata = session.get("metadata", {})
        
        location = metadata.get("location")
        
        if not location or location == "未知":
            detected_city = None
            for city in cities:
                if city in user_input:
                    detected_city = city
                    break
            location = detected_city or "未知地区"
        
        # 验证回退成功
        assert location == "深圳"
    
    def test_fallback_chain(self):
        """测试完整的回退链"""
        # 优先级：IP定位 > 用户输入 > 未知
        
        # 场景 1: IP 定位成功
        session1 = {
            "user_input": "我在北京",
            "metadata": {
                "location": "上海市",  # IP 定位的结果
                "geo_info": {"is_valid": True}
            }
        }
        location1 = session1["metadata"]["location"]
        assert location1 == "上海市"  # 使用 IP 定位结果
        
        # 场景 2: IP 定位失败，从用户输入提取
        session2 = {
            "user_input": "我在北京需要设计",
            "metadata": {
                "location": "未知",
                "geo_info": {"is_valid": False}
            }
        }
        cities = ["北京", "上海"]
        user_input = session2["user_input"]
        location2 = None
        for city in cities:
            if city in user_input:
                location2 = city
                break
        assert location2 == "北京"
        
        # 场景 3: 全部失败
        session3 = {
            "user_input": "我需要设计一个住宅",
            "metadata": {
                "location": "未知",
                "geo_info": {"is_valid": False}
            }
        }
        location3 = session3["metadata"]["location"]
        # 从用户输入也提取不到
        cities = ["北京", "上海"]
        user_input = session3["user_input"]
        detected = None
        for city in cities:
            if city in user_input:
                detected = city
                break
        location3 = detected or "未知地区"
        assert location3 == "未知地区"


class TestGeoIPPerformance:
    """性能测试"""
    
    @pytest.mark.slow
    def test_batch_ip_lookup(self):
        """测试批量 IP 查询性能"""
        import time
        
        service = get_geoip_service()
        test_ips = [
            "8.8.8.8",
            "1.1.1.1",
            "203.208.60.1",
            "127.0.0.1",
            "192.168.1.1"
        ]
        
        start_time = time.time()
        
        results = []
        for ip in test_ips:
            location = service.get_location(ip)
            results.append(location)
        
        elapsed_time = time.time() - start_time
        
        # 验证结果
        assert len(results) == len(test_ips)
        
        # 性能要求：5个IP查询应在1秒内完成
        assert elapsed_time < 1.0, f"批量查询耗时过长: {elapsed_time:.2f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
