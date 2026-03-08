"""
免费 IP 轮换工具（Windows 专用）

策略说明
─────────────────────────────────────────────────────────────────────
大部分家庭/办公宽带使用 **动态 IP**（PPPoE 拨号 or DHCP）。
断开并重连网络适配器后，运营商会分配新的公网 IP，等同于免费换 IP。

本模块提供:
  1. ``renew_ip()`` — 自动 release/renew DHCP 或重启适配器
  2. ``get_public_ip()`` — 查询当前公网 IP（用于验证是否更换成功）
  3. ``maybe_rotate_ip()`` — 高级入口：仅在连续失败 N 次后触发

注意事项
─────────────────────────────────────────────────────────────────────
- 需要以 **管理员权限** 运行 Python 进程（netsh 需提权）
- 光猫桥接 + 路由器 PPPoE 的场景下，release/renew 可能无效，
  此时需要使用路由器管理页面 API 重新拨号（需自行对接路由器型号）
- 行为温和：仅在确认需要时才执行，不会主动断网
"""

from __future__ import annotations

import subprocess
import time
import urllib.request

from loguru import logger


def get_public_ip(timeout: float = 10) -> str | None:
    """
    查询当前公网 IP（使用多个免费 API 做 fallback）。

    Returns:
        IP 字符串，失败返回 None
    """
    apis = [
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://icanhazip.com",
        "https://checkip.amazonaws.com",
    ]
    for api in apis:
        try:
            req = urllib.request.Request(api, headers={"User-Agent": "curl/7.68"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                ip = resp.read().decode().strip()
                if ip and "." in ip:
                    return ip
        except Exception:
            continue
    return None


def renew_ip(adapter_name: str | None = None, wait: float = 8.0) -> bool:
    """
    通过 DHCP release/renew 获取新 IP（Windows）。

    Args:
        adapter_name: 网络适配器名称（None = 所有适配器）
        wait: release 后等待秒数再 renew（给运营商时间释放旧 IP）

    Returns:
        True=成功执行（不保证 IP 一定变化），False=执行失败
    """
    old_ip = get_public_ip()
    logger.info(f"IP 轮换开始 | 当前 IP: {old_ip}")

    try:
        # 释放 DHCP 租约
        if adapter_name:
            subprocess.run(
                ["ipconfig", "/release", adapter_name],
                capture_output=True,
                timeout=15,
                check=False,
            )
        else:
            subprocess.run(
                ["ipconfig", "/release"],
                capture_output=True,
                timeout=15,
                check=False,
            )

        time.sleep(wait)

        # 重新获取 DHCP 租约
        if adapter_name:
            subprocess.run(
                ["ipconfig", "/renew", adapter_name],
                capture_output=True,
                timeout=30,
                check=False,
            )
        else:
            subprocess.run(
                ["ipconfig", "/renew"],
                capture_output=True,
                timeout=30,
                check=False,
            )

        time.sleep(3)  # 等待网络恢复
        new_ip = get_public_ip()
        changed = old_ip != new_ip
        logger.info(f"IP 轮换完成 | 新 IP: {new_ip} | 已变化: {changed}")
        return True

    except Exception as e:
        logger.error(f"IP 轮换失败: {e}")
        return False


def restart_adapter(adapter_name: str, wait: float = 5.0) -> bool:
    """
    重启指定网络适配器（需管理员权限）。

    比 DHCP renew 更彻底，适用于 PPPoE 拨号场景。

    Args:
        adapter_name: 适配器名称（如 "以太网", "WLAN", "Ethernet"）
        wait: 禁用后等待秒数

    Returns:
        True=成功，False=失败
    """
    try:
        logger.info(f"重启适配器: {adapter_name}")
        subprocess.run(
            ["netsh", "interface", "set", "interface", adapter_name, "disable"],
            capture_output=True,
            timeout=15,
            check=True,
        )
        time.sleep(wait)
        subprocess.run(
            ["netsh", "interface", "set", "interface", adapter_name, "enable"],
            capture_output=True,
            timeout=15,
            check=True,
        )
        time.sleep(5)  # 等待重新连接
        new_ip = get_public_ip()
        logger.info(f"适配器重启完成 | 新 IP: {new_ip}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"适配器重启失败（需管理员权限？）: {e}")
        return False
    except Exception as e:
        logger.error(f"适配器重启失败: {e}")
        return False


class IPRotator:
    """
    智能 IP 轮换器（仅在连续失败达到阈值时触发）。

    用法::

        rotator = IPRotator(failure_threshold=5)

        # 在爬虫每次失败时调用
        rotator.on_failure()

        # 成功时重置计数
        rotator.on_success()

    参数:
        failure_threshold: 连续失败多少次后触发 IP 轮换
        adapter_name: 网络适配器名称（None=自动 DHCP renew）
        enabled: 是否启用（默认 False，需手动开启）
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        adapter_name: str | None = None,
        enabled: bool = False,
    ):
        self.failure_threshold = failure_threshold
        self.adapter_name = adapter_name
        self.enabled = enabled
        self._consecutive_failures = 0
        self._total_rotations = 0

    def on_success(self):
        """爬取成功，重置失败计数"""
        self._consecutive_failures = 0

    def on_failure(self) -> bool:
        """
        爬取失败，累加计数并在达到阈值时自动轮换 IP。

        Returns:
            True=触发了 IP 轮换，False=未触发
        """
        if not self.enabled:
            return False

        self._consecutive_failures += 1
        if self._consecutive_failures < self.failure_threshold:
            return False

        logger.warning(f"连续失败 {self._consecutive_failures} 次 " f"(阈值={self.failure_threshold})，触发 IP 轮换")
        self._consecutive_failures = 0
        self._total_rotations += 1

        if self.adapter_name:
            return restart_adapter(self.adapter_name)
        return renew_ip()


__all__ = [
    "get_public_ip",
    "renew_ip",
    "restart_adapter",
    "IPRotator",
]
