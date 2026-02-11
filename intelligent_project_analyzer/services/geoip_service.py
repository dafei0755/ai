"""
GeoIP 地理位置服务

使用 ip-api.com 免费 API 识别 IP 地址的地理位置
支持国家、省份、城市、经纬度识别
无需注册，免费使用（限制：45次/分钟）
"""

import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from fastapi import Request
from loguru import logger

try:
    import geoip2.database  # type: ignore
    from geoip2.errors import AddressNotFoundError  # type: ignore
except Exception:  # pragma: no cover - geoip2 为可选依赖
    geoip2 = None

    class AddressNotFoundError(Exception):
        """占位异常，兼容未安装 geoip2 时的类型引用"""

        pass


class GeoIPService:
    """GeoIP 地理位置服务（支持本地数据库 + ip-api.com 双模式）"""

    # ip-api.com 免费版限制：45次/分钟
    API_URL = "http://ip-api.com/json/{ip}"
    API_PARAMS = {
        "fields": "status,message,country,countryCode,region,regionName,city,lat,lon,timezone,query",
        "lang": "zh-CN",  # 返回中文地名
    }

    DEFAULT_DB_PATH = Path("data/GeoLite2-City.mmdb")

    # 速率限制：45次/分钟，保守设为40次
    RATE_LIMIT = 40
    RATE_WINDOW = 60  # 秒

    def __init__(self, db_path: Optional[str] = None):
        """初始化 GeoIP 服务"""

        self.db_path = db_path or str(self.DEFAULT_DB_PATH)
        self._request_times: list[float] = []
        self.reader = None
        self.is_available = False
        self.use_local_db = db_path is not None

        if self.use_local_db:
            if geoip2 is None:
                logger.warning("️ 未安装 geoip2 库，无法启用本地 GeoIP 数据库模式")
                return

            db_file = Path(self.db_path)
            if not db_file.exists():
                logger.warning("️ GeoLite2 数据库文件不存在: %s", db_file)
                return

            try:
                self.reader = geoip2.database.Reader(str(db_file))
                self.is_available = True
                logger.info(" GeoIP 服务初始化成功（使用 MaxMind 数据库）: %s", db_file)
            except Exception as exc:
                logger.warning(f"️ 无法加载 GeoLite2 数据库: {exc}")
        else:
            self.is_available = True
            logger.info(" GeoIP 服务初始化成功（使用 ip-api.com 免费API）")

    def _check_rate_limit(self) -> bool:
        """检查是否超过速率限制"""
        now = time.time()
        # 清理超过时间窗口的请求记录
        self._request_times = [t for t in self._request_times if now - t < self.RATE_WINDOW]

        if len(self._request_times) >= self.RATE_LIMIT:
            logger.warning(f"️ 达到速率限制：{self.RATE_LIMIT}次/{self.RATE_WINDOW}秒")
            return False

        self._request_times.append(now)
        return True

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
            logger.debug(f" IP from X-Forwarded-For: {ip}")
            return ip

        # 从 Nginx 代理头获取
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            logger.debug(f" IP from X-Real-IP: {real_ip}")
            return real_ip

        # 直连 IP
        client_ip = request.client.host if request.client else "127.0.0.1"
        logger.debug(f" IP from client.host: {client_ip}")
        return client_ip

    def get_location(self, ip: str) -> Dict[str, Any]:
        """
        从 IP 地址识别地理位置（使用 ip-api.com API）

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
        # 空IP或无效格式检查
        if not ip or not isinstance(ip, str) or len(ip.strip()) == 0:
            return self._get_unknown_location(ip or "空IP", reason="IP地址为空")

        ip = ip.strip()

        # 本地回环地址特殊处理
        if ip in ["127.0.0.1", "localhost", "::1"]:
            return self._get_localhost_location(ip)

        # 内网IP特殊处理
        if self._is_private_ip(ip):
            return self._get_private_ip_location(ip)

        if self.use_local_db:
            if not self.is_available or self.reader is None:
                return self._get_unknown_location(ip, reason="GeoIP数据库不可用")
            return self._lookup_local_database(ip)

        return self._lookup_remote_service(ip)

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

    def _lookup_local_database(self, ip: str) -> Dict[str, Any]:
        """使用本地 GeoLite 数据库查询"""

        try:
            result = self.reader.city(ip)
        except AddressNotFoundError:
            return self._get_unknown_location(ip, reason="地址未收录")
        except Exception as exc:
            logger.error(f" 本地 GeoIP 查询失败: {ip}, 错误: {exc}")
            return self._get_unknown_location(ip, reason=str(exc))

        country_data = getattr(result, "country", None)
        subdivision = getattr(getattr(result, "subdivisions", None), "most_specific", None)
        city_data = getattr(result, "city", None)

        country = (getattr(country_data, "names", {}) or {}).get("zh-CN") or getattr(country_data, "name", "未知")
        province = (getattr(subdivision, "names", {}) or {}).get("zh-CN") or getattr(subdivision, "name", "")
        city = (getattr(city_data, "names", {}) or {}).get("zh-CN") or getattr(city_data, "name", "未知")

        location_data = getattr(result, "location", None)

        location = {
            "ip": ip,
            "country": country or "未知",
            "province": province or "",
            "city": city or "未知",
            "latitude": getattr(location_data, "latitude", None),
            "longitude": getattr(location_data, "longitude", None),
            "timezone": getattr(location_data, "time_zone", "未知"),
            "is_valid": True,
        }

        logger.debug(f" 本地数据库定位成功: {ip} -> {location['country']}/{location['province']}/{location['city']}")
        return location

    def _lookup_remote_service(self, ip: str) -> Dict[str, Any]:
        """使用 ip-api.com 查询"""

        # 检查速率限制
        if not self._check_rate_limit():
            logger.warning(f"️ 速率限制，跳过IP查询: {ip}")
            return self._get_unknown_location(ip, reason="速率限制")

        try:
            url = self.API_URL.format(ip=ip)
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url, params=self.API_PARAMS)
                response.raise_for_status()
                data = response.json()

            if data.get("status") != "success":
                error_msg = data.get("message", "未知错误")
                logger.warning(f"️ IP查询失败: {ip}, 原因: {error_msg}")
                return self._get_unknown_location(ip, reason=error_msg)

            location = {
                "ip": data.get("query", ip),
                "country": data.get("country", "未知"),
                "province": data.get("regionName", ""),
                "city": data.get("city", "未知"),
                "latitude": data.get("lat"),
                "longitude": data.get("lon"),
                "timezone": data.get("timezone", "未知"),
                "is_valid": True,
            }

            logger.debug(f" IP定位成功: {ip} -> {location['country']}/{location['province']}/{location['city']}")
            return location

        except httpx.TimeoutException:
            logger.warning(f"️ IP查询超时: {ip}")
            return self._get_unknown_location(ip, reason="请求超时")
        except httpx.HTTPError as exc:
            logger.error(f" IP查询HTTP错误: {ip}, 错误: {exc}")
            return self._get_unknown_location(ip, reason=f"HTTP错误: {exc}")
        except Exception as exc:
            logger.error(f" IP定位失败: {ip}, 错误: {exc}")
            return self._get_unknown_location(ip, reason=str(exc))

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

    def batch_get_locations(self, ips: list[str]) -> list[Dict[str, Any]]:
        """
        批量查询IP地理位置（注意速率限制）

        Args:
            ips: IP地址列表

        Returns:
            地理位置信息列表
        """
        results = []
        for ip in ips:
            results.append(self.get_location(ip))
            # 避免触发速率限制，每次查询间隔
            if len(ips) > 10:
                time.sleep(0.1)
        return results


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
