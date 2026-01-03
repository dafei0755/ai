#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GeoIP 功能快速验证脚本

不需要真实的 GeoLite2 数据库，使用 Mock 验证功能
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from unittest.mock import Mock

print("=" * 70)
print(" 🧪 GeoIP 功能快速验证")
print("=" * 70)
print()

# 测试 1: 导入模块
print("📦 测试 1: 导入 GeoIP 服务模块...")
try:
    from intelligent_project_analyzer.services.geoip_service import GeoIPService, get_geoip_service
    print("   ✅ 导入成功")
except Exception as e:
    print(f"   ❌ 导入失败: {e}")
    sys.exit(1)

# 测试 2: 初始化服务
print("\n🔧 测试 2: 初始化 GeoIP 服务...")
try:
    service = GeoIPService()
    print(f"   ✅ 服务初始化成功")
    print(f"   数据库路径: {service.db_path}")
    print(f"   服务可用: {service.is_available}")
except Exception as e:
    print(f"   ❌ 初始化失败: {e}")
    sys.exit(1)

# 测试 3: IP 采集功能
print("\n🌐 测试 3: IP 采集功能...")
try:
    # 模拟 FastAPI Request
    mock_request = Mock()
    mock_request.headers = Mock()
    mock_request.headers.get = Mock(side_effect=lambda key, default=None: {
        "X-Forwarded-For": "8.8.8.8, 1.1.1.1",
        "User-Agent": "Mozilla/5.0 Test Browser"
    }.get(key, default))
    mock_request.client = Mock(host="192.168.1.1")
    
    ip = service.get_client_ip(mock_request)
    print(f"   ✅ IP 采集成功: {ip}")
    assert ip == "8.8.8.8", "IP 应该从 X-Forwarded-For 获取第一个"
except Exception as e:
    print(f"   ❌ IP 采集失败: {e}")
    sys.exit(1)

# 测试 4: 本地 IP 识别
print("\n🏠 测试 4: 本地 IP 识别...")
try:
    test_cases = [
        ("127.0.0.1", "本地主机"),
        ("localhost", "本地主机"),
        ("::1", "本地主机"),
    ]
    
    for ip, expected_city in test_cases:
        location = service.get_location(ip)
        assert location["city"] == expected_city, f"本地 IP {ip} 应识别为 {expected_city}"
        print(f"   ✅ {ip} -> {location['city']}")
except Exception as e:
    print(f"   ❌ 本地 IP 识别失败: {e}")
    sys.exit(1)

# 测试 5: 内网 IP 识别
print("\n🔒 测试 5: 内网 IP 识别...")
try:
    test_cases = [
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.1",
    ]
    
    for ip in test_cases:
        assert service._is_private_ip(ip), f"{ip} 应识别为内网 IP"
        location = service.get_location(ip)
        assert location["city"] == "局域网", f"内网 IP {ip} 应识别为局域网"
        print(f"   ✅ {ip} -> {location['city']}")
except Exception as e:
    print(f"   ❌ 内网 IP 识别失败: {e}")
    sys.exit(1)

# 测试 6: 公网 IP（优雅降级）
print("\n🌍 测试 6: 公网 IP 处理（优雅降级）...")
try:
    test_ips = ["8.8.8.8", "1.1.1.1", "1.2.3.4"]
    
    for ip in test_ips:
        location = service.get_location(ip)
        print(f"   ✅ {ip} -> {location['city']} ({location['country']})")
        
        # 验证数据结构
        required_fields = ["ip", "country", "province", "city", 
                          "latitude", "longitude", "timezone", "is_valid"]
        for field in required_fields:
            assert field in location, f"缺少字段: {field}"
except Exception as e:
    print(f"   ❌ 公网 IP 处理失败: {e}")
    sys.exit(1)

# 测试 7: 数据格式验证
print("\n📋 测试 7: 数据格式验证...")
try:
    location = service.get_location("127.0.0.1")
    
    # 类型检查
    assert isinstance(location["ip"], str), "IP 应为字符串"
    assert isinstance(location["country"], str), "国家应为字符串"
    assert isinstance(location["city"], str), "城市应为字符串"
    assert isinstance(location["is_valid"], bool), "is_valid 应为布尔值"
    
    print("   ✅ 数据格式正确")
    print(f"   示例数据: {location}")
except Exception as e:
    print(f"   ❌ 数据格式验证失败: {e}")
    sys.exit(1)

# 测试 8: 单例模式
print("\n🔗 测试 8: 全局单例...")
try:
    service1 = get_geoip_service()
    service2 = get_geoip_service()
    
    assert service1 is service2, "应返回相同的实例"
    print("   ✅ 单例模式工作正常")
except Exception as e:
    print(f"   ❌ 单例测试失败: {e}")
    sys.exit(1)

# 测试 9: 错误处理
print("\n⚠️ 测试 9: 错误处理...")
try:
    # 空 IP
    location = service.get_location("")
    assert location["is_valid"] == False, "空 IP 应标记为无效"
    print("   ✅ 空 IP 处理正常")
    
    # 无效格式
    location = service.get_location("invalid_ip")
    assert location["is_valid"] == False, "无效 IP 应标记为无效"
    print("   ✅ 无效 IP 处理正常")
except Exception as e:
    print(f"   ❌ 错误处理失败: {e}")
    sys.exit(1)

# 测试 10: 性能基准
print("\n⚡ 测试 10: 性能基准...")
try:
    import time
    
    test_ips = ["127.0.0.1", "192.168.1.1", "10.0.0.1"] * 10  # 30个IP
    
    start_time = time.time()
    for ip in test_ips:
        service.get_location(ip)
    elapsed = time.time() - start_time
    
    avg_time = (elapsed / len(test_ips)) * 1000  # 毫秒
    print(f"   ✅ 查询 {len(test_ips)} 个 IP 耗时: {elapsed:.3f}s")
    print(f"   平均每个 IP: {avg_time:.2f}ms")
    
    if avg_time > 10:
        print(f"   ⚠️ 性能警告: 平均耗时超过 10ms")
except Exception as e:
    print(f"   ❌ 性能测试失败: {e}")

# 总结
print("\n" + "=" * 70)
print(" ✅ 所有测试通过！GeoIP 功能正常")
print("=" * 70)
print()
print("💡 提示:")
print("   - 当前测试使用 Mock 数据，不需要真实数据库")
print("   - 下载 GeoLite2 数据库: python scripts/download_geoip_db.py")
print("   - 运行完整测试: python tests/run_geoip_tests.py")
print()
