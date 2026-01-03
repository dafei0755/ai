"""
GeoIP 地理位置服务

使用 MaxMind GeoLite2 离线数据库识别 IP 地址的地理位置
支持国家、省份、城市、经纬度识别
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Request
from loguru import logger

try:
    import geoip2.database
    from geoip2.errors import AddressNotFoundError

    GEOIP2_AVAILABLE = True
except ImportError:
    GEOIP2_AVAILABLE = False
    logger.warning("⚠️ geoip2 未安装，IP地理位置功能将不可用")


class GeoIPService:
    """GeoIP 地理位置服务"""

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化 GeoIP 服务

        Args:
            db_path: GeoLite2-City.mmdb 数据库路径，默认为 data/GeoLite2-City.mmdb
        """
        self.db_path = db_path or self._get_default_db_path()
        self.reader: Optional[geoip2.database.Reader] = None
        self.is_available = False

        if GEOIP2_AVAILABLE:
            self._initialize_reader()

    def _get_default_db_path(self) -> str:
        """获取默认数据库路径"""
        # 项目根目录的 data 文件夹
        project_root = Path(__file__).parent.parent.parent.parent
        return str(project_root / "data" / "GeoLite2-City.mmdb")

    def _initialize_reader(self):
        """初始化数据库读取器"""
        try:
            if not os.path.exists(self.db_path):
                logger.warning(f"⚠️ GeoLite2 数据库不存在: {self.db_path}\n" f"💡 请运行: python scripts/download_geoip_db.py")
                return

            self.reader = geoip2.database.Reader(self.db_path)
            self.is_available = True
            logger.info(f"✅ GeoIP 数据库加载成功: {self.db_path}")

        except Exception as e:
            logger.error(f"❌ GeoIP 数据库加载失败: {e}")
            self.is_available = False

    def get_client_ip(self, request: Request) -> str:
        """
        获取客户端真实 IP 地址

        优先级：
        1. X-Forwarded-For (代理/负载均衡)
        2. X-Real-IP (Nginx)
        3. request.client.host (直连)

        Args:
            request: FastAPI Request 对象

        Returns:
            客户端 IP 地址字符串
        """
        # 从代理头获取（多个IP时取第一个）
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
            logger.debug(f"🔍 IP from X-Forwarded-For: {ip}")
            return ip

        # 从 Nginx 代理头获取
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            logger.debug(f"🔍 IP from X-Real-IP: {real_ip}")
            return real_ip

        # 直连 IP
        client_ip = request.client.host if request.client else "127.0.0.1"
        logger.debug(f"🔍 IP from client.host: {client_ip}")
        return client_ip

    def get_location(self, ip: str) -> Dict[str, Any]:
        """
        从 IP 地址识别地理位置

        Args:
            ip: IP 地址字符串

        Returns:
            地理位置信息字典:
            {
                "ip": "1.2.3.4",
                "country": "中国",
                "province": "广东省",
                "city": "深圳市",
                "latitude": 22.5431,
                "longitude": 114.0579,
                "timezone": "Asia/Shanghai",
                "is_valid": True
            }
        """
        # 本地回环地址特殊处理
        if ip in ["127.0.0.1", "localhost", "::1"]:
            return self._get_localhost_location(ip)

        # 内网IP特殊处理
        if self._is_private_ip(ip):
            return self._get_private_ip_location(ip)

        # GeoIP2 不可用时返回未知
        if not self.is_available or not self.reader:
            return self._get_unknown_location(ip, reason="GeoIP服务不可用")

        try:
            response = self.reader.city(ip)

            # 提取中文地名（优先）
            country = response.country.names.get("zh-CN", response.country.name or "未知")
            city = response.city.names.get("zh-CN", response.city.name or "未知")
            province = ""

            # 获取省份信息
            if response.subdivisions:
                province = response.subdivisions.most_specific.names.get(
                    "zh-CN", response.subdivisions.most_specific.name or ""
                )

            location = {
                "ip": ip,
                "country": country,
                "province": province,
                "city": city,
                "latitude": response.location.latitude,
                "longitude": response.location.longitude,
                "timezone": response.location.time_zone or "未知",
                "is_valid": True,
            }

            logger.debug(f"✅ IP定位成功: {ip} -> {country}/{province}/{city}")
            return location

        except AddressNotFoundError:
            logger.warning(f"⚠️ IP地址未找到: {ip}")
            return self._get_unknown_location(ip, reason="IP不在数据库中")

        except Exception as e:
            logger.error(f"❌ IP定位失败: {ip}, 错误: {e}")
            return self._get_unknown_location(ip, reason=str(e))

    def _is_private_ip(self, ip: str) -> bool:
        """检查是否为内网IP"""
        try:
            parts = ip.split(".")
            if len(parts) != 4:
                return False

            first = int(parts[0])
            second = int(parts[1])

            # 10.0.0.0 - 10.255.255.255
            if first == 10:
                return True

            # 172.16.0.0 - 172.31.255.255
            if first == 172 and 16 <= second <= 31:
                return True

            # 192.168.0.0 - 192.168.255.255
            if first == 192 and second == 168:
                return True

            return False
        except:
            return False

    def _get_localhost_location(self, ip: str) -> Dict[str, Any]:
        """获取本地回环地址的位置信息"""
        return {
            "ip": ip,
            "country": "本地",
            "province": "",
            "city": "本地主机",
            "latitude": None,
            "longitude": None,
            "timezone": "本地",
            "is_valid": True,
            "note": "本地回环地址",
        }

    def _get_private_ip_location(self, ip: str) -> Dict[str, Any]:
        """获取内网IP的位置信息"""
        return {
            "ip": ip,
            "country": "内网",
            "province": "",
            "city": "局域网",
            "latitude": None,
            "longitude": None,
            "timezone": "内网",
            "is_valid": True,
            "note": "内网IP地址",
        }

    def _get_unknown_location(self, ip: str, reason: str = "未知") -> Dict[str, Any]:
        """获取未知位置的默认信息"""
        return {
            "ip": ip,
            "country": "未知",
            "province": "",
            "city": "未知",
            "latitude": None,
            "longitude": None,
            "timezone": "未知",
            "is_valid": False,
            "error": reason,
        }

    def __del__(self):
        """清理资源"""
        if self.reader:
            try:
                self.reader.close()
                logger.debug("👋 GeoIP 数据库连接已关闭")
            except:
                pass


# 全局单例
_geoip_service: Optional[GeoIPService] = None


def get_geoip_service() -> GeoIPService:
    """
    获取全局 GeoIP 服务单例

    Returns:
        GeoIPService 实例
    """
    global _geoip_service
    if _geoip_service is None:
        _geoip_service = GeoIPService()
    return _geoip_service
