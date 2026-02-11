"""
日志告警系统 - 错误日志超阈值自动告警

功能：
1. 监控错误日志频率
2. 错误超过阈值时触发告警
3. 支持多种告警方式（日志、邮件、Webhook）
4. 防止告警风暴（冷却期）
"""

import asyncio
import json
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List

import aiohttp
from loguru import logger


class AlertConfig:
    """告警配置"""

    # 错误阈值配置
    ERROR_THRESHOLD_1MIN = 10  # 1分钟内错误超过10次
    ERROR_THRESHOLD_5MIN = 30  # 5分钟内错误超过30次
    ERROR_THRESHOLD_15MIN = 50  # 15分钟内错误超过50次

    # 冷却期（防止告警风暴）
    COOLDOWN_PERIOD = 300  # 5分钟冷却期

    # Webhook 配置（可选）
    WEBHOOK_URL = ""  # 填入钉钉、企业微信、Slack webhook URL

    # 邮件配置（可选）
    EMAIL_ENABLED = False
    EMAIL_TO = []


class ErrorAlertMonitor:
    """错误告警监控器"""

    def __init__(self):
        self.error_timestamps = deque(maxlen=1000)  # 保留最近1000条错误时间戳
        self.last_alert_time = 0
        self.alert_count = 0
        self.lock = threading.Lock()

        # 告警日志文件
        self.alert_log_file = Path(__file__).parent.parent.parent / "logs" / "alerts.log"
        self.alert_log_file.parent.mkdir(exist_ok=True)

        # 启动后台监控线程
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._background_monitor, daemon=True)
        self.monitor_thread.start()

        logger.info(" 错误告警监控器已启动")

    def record_error(self, error_msg: str, level: str = "ERROR"):
        """记录错误"""
        with self.lock:
            self.error_timestamps.append(time.time())
            self._check_thresholds(error_msg, level)

    def _check_thresholds(self, error_msg: str, level: str):
        """检查是否超过阈值"""
        now = time.time()

        # 检查是否在冷却期内
        if now - self.last_alert_time < AlertConfig.COOLDOWN_PERIOD:
            return

        # 统计不同时间窗口的错误数
        errors_1min = sum(1 for t in self.error_timestamps if now - t < 60)
        errors_5min = sum(1 for t in self.error_timestamps if now - t < 300)
        errors_15min = sum(1 for t in self.error_timestamps if now - t < 900)

        # 触发告警条件
        alert_triggered = False
        alert_message = ""

        if errors_1min >= AlertConfig.ERROR_THRESHOLD_1MIN:
            alert_triggered = True
            alert_message = f"️ 高频错误告警：1分钟内出现 {errors_1min} 个错误！"
        elif errors_5min >= AlertConfig.ERROR_THRESHOLD_5MIN:
            alert_triggered = True
            alert_message = f"️ 错误激增告警：5分钟内出现 {errors_5min} 个错误！"
        elif errors_15min >= AlertConfig.ERROR_THRESHOLD_15MIN:
            alert_triggered = True
            alert_message = f"️ 持续错误告警：15分钟内出现 {errors_15min} 个错误！"

        if alert_triggered:
            self._trigger_alert(
                alert_message,
                error_msg,
                {"errors_1min": errors_1min, "errors_5min": errors_5min, "errors_15min": errors_15min},
            )
            self.last_alert_time = now
            self.alert_count += 1

    def _trigger_alert(self, alert_message: str, error_detail: str, stats: Dict):
        """触发告警"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. 写入告警日志
        alert_record = {
            "timestamp": timestamp,
            "message": alert_message,
            "error_detail": error_detail,
            "stats": stats,
            "alert_count": self.alert_count,
        }

        with open(self.alert_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(alert_record, ensure_ascii=False) + "\n")

        # 2. 控制台输出（直接写stderr，避免logger回调死锁）
        import sys

        alert_output = f"""
{'='*60}
 错误告警 #{self.alert_count}
{'='*60}
时间: {timestamp}
{alert_message}

错误详情: {error_detail[:200]}...

统计数据:
  - 最近1分钟: {stats['errors_1min']} 个错误
  - 最近5分钟: {stats['errors_5min']} 个错误
  - 最近15分钟: {stats['errors_15min']} 个错误

下次告警冷却期: {AlertConfig.COOLDOWN_PERIOD}秒
{'='*60}
        """
        sys.stderr.write(alert_output + "\n")
        sys.stderr.flush()

        # 3. 发送 Webhook 告警（异步）
        if AlertConfig.WEBHOOK_URL:
            asyncio.create_task(self._send_webhook_alert(alert_message, stats))

        # 4. 发送邮件告警（如果启用）
        if AlertConfig.EMAIL_ENABLED and AlertConfig.EMAIL_TO:
            self._send_email_alert(alert_message, error_detail, stats)

    async def _send_webhook_alert(self, message: str, stats: Dict):
        """发送 Webhook 告警（钉钉/企业微信/Slack）"""
        try:
            payload = {
                "msgtype": "text",
                "text": {
                    "content": f"【系统告警】\n{message}\n\n错误统计：\n"
                    f"1分钟: {stats['errors_1min']}\n"
                    f"5分钟: {stats['errors_5min']}\n"
                    f"15分钟: {stats['errors_15min']}"
                },
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(AlertConfig.WEBHOOK_URL, json=payload, timeout=5) as resp:
                    if resp.status == 200:
                        logger.info(" Webhook 告警发送成功")
                    else:
                        logger.warning(f"️ Webhook 告警发送失败: {resp.status}")
        except Exception as e:
            logger.error(f" Webhook 告警发送异常: {e}")

    def _send_email_alert(self, message: str, error_detail: str, stats: Dict):
        """发送邮件告警（可选实现）"""
        # TODO: 实现邮件发送逻辑
        logger.info(" 邮件告警功能待实现")

    def _background_monitor(self):
        """后台监控线程"""
        while self.monitoring:
            time.sleep(60)  # 每分钟检查一次

            # 清理过期错误记录（超过15分钟）
            with self.lock:
                cutoff_time = time.time() - 900
                while self.error_timestamps and self.error_timestamps[0] < cutoff_time:
                    self.error_timestamps.popleft()

    def stop(self):
        """停止监控"""
        self.monitoring = False
        logger.info(" 错误告警监控器已停止")

    def get_current_stats(self) -> Dict:
        """获取当前统计"""
        with self.lock:
            now = time.time()
            return {
                "errors_1min": sum(1 for t in self.error_timestamps if now - t < 60),
                "errors_5min": sum(1 for t in self.error_timestamps if now - t < 300),
                "errors_15min": sum(1 for t in self.error_timestamps if now - t < 900),
                "total_alerts": self.alert_count,
                "last_alert": datetime.fromtimestamp(self.last_alert_time).isoformat()
                if self.last_alert_time > 0
                else None,
            }


# 全局告警监控实例
alert_monitor = ErrorAlertMonitor()


# Loguru 自定义 sink，拦截错误日志
def alert_sink(message):
    """Loguru 自定义 sink，捕获错误并触发告警"""
    record = message.record
    if record["level"].name in ["ERROR", "CRITICAL"]:
        alert_monitor.record_error(error_msg=record["message"], level=record["level"].name)


# 添加到 logger（需要在 server.py 中启用）
# logger.add(alert_sink, level="ERROR")
