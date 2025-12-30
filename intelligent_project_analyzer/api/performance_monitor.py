"""
性能监控中间件 - 记录 API 响应时间和性能指标

功能：
1. 记录每个请求的响应时间
2. 记录慢请求（>1秒）
3. 统计 API 调用次数
4. 性能指标导出
"""

import time
import asyncio
from typing import Callable
from fastapi import Request, Response
from loguru import logger
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import threading


class PerformanceMonitor:
    """性能监控管理器"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.lock = threading.Lock()
        self.slow_request_threshold = 1.0  # 秒
        self.metrics_file = Path(__file__).parent.parent.parent / "logs" / "performance_metrics.jsonl"
        self.metrics_file.parent.mkdir(exist_ok=True)
        
    def record_request(self, path: str, method: str, duration: float, status_code: int):
        """记录请求性能"""
        with self.lock:
            self.metrics[path].append({
                "method": method,
                "duration": duration,
                "status_code": status_code,
                "timestamp": datetime.now().isoformat()
            })
            
            # 慢请求警告
            if duration > self.slow_request_threshold:
                logger.warning(f"🐌 慢请求检测: {method} {path} 耗时 {duration:.2f}秒")
            
            # 写入持久化日志
            self._write_metric(path, method, duration, status_code)
    
    def _write_metric(self, path: str, method: str, duration: float, status_code: int):
        """写入性能指标到文件"""
        # 🔥 v7.105: 添加文件锁定保护，避免Permission denied错误
        try:
            metric = {
                "timestamp": datetime.now().isoformat(),
                "path": path,
                "method": method,
                "duration": round(duration, 3),
                "status_code": status_code
            }
            
            # 尝试写入，如果失败则静默忽略（不影响主流程）
            try:
                with open(self.metrics_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(metric, ensure_ascii=False) + "\n")
            except (PermissionError, OSError) as file_error:
                # 文件锁定或权限问题，静默忽略（每10次记录一次警告）
                if not hasattr(self, '_write_error_count'):
                    self._write_error_count = 0
                self._write_error_count += 1
                if self._write_error_count % 10 == 1:
                    logger.debug(f"⚠️ 性能指标写入跳过 (文件被占用，已跳过{self._write_error_count}次)")
        except Exception as e:
            # 其他异常也不影响主流程
            pass
    
    def get_stats(self, path: str = None):
        """获取性能统计"""
        with self.lock:
            if path:
                metrics = self.metrics.get(path, [])
            else:
                metrics = [m for ms in self.metrics.values() for m in ms]
            
            if not metrics:
                return {}
            
            durations = [m["duration"] for m in metrics]
            return {
                "count": len(metrics),
                "avg_duration": sum(durations) / len(durations),
                "max_duration": max(durations),
                "min_duration": min(durations),
                "slow_requests": len([d for d in durations if d > self.slow_request_threshold])
            }


# 全局性能监控实例
performance_monitor = PerformanceMonitor()


async def performance_monitoring_middleware(request: Request, call_next: Callable):
    """
    性能监控中间件
    
    记录所有 API 请求的响应时间
    """
    # 跳过静态文件和 WebSocket
    if request.url.path.startswith("/static") or request.url.path.startswith("/ws"):
        return await call_next(request)
    
    start_time = time.time()
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # 记录性能指标
        performance_monitor.record_request(
            path=request.url.path,
            method=request.method,
            duration=duration,
            status_code=response.status_code
        )
        
        # 添加性能响应头
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        
        # 正常请求记录（INFO 级别）
        if duration < 0.5:
            logger.info(f"⚡ {request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
        elif duration < 1.0:
            logger.info(f"🔶 {request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
        else:
            logger.warning(f"🐌 {request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"❌ {request.method} {request.url.path} - ERROR - {duration:.3f}s - {str(e)}")
        
        # 记录失败请求
        performance_monitor.record_request(
            path=request.url.path,
            method=request.method,
            duration=duration,
            status_code=500
        )
        
        raise


class LLMPerformanceTracker:
    """LLM 调用性能追踪器"""
    
    def __init__(self):
        self.llm_metrics_file = Path(__file__).parent.parent.parent / "logs" / "llm_metrics.jsonl"
        self.llm_metrics_file.parent.mkdir(exist_ok=True)
    
    def record_llm_call(self, model: str, operation: str, duration: float, tokens: int = 0, success: bool = True):
        """记录 LLM 调用性能"""
        try:
            metric = {
                "timestamp": datetime.now().isoformat(),
                "model": model,
                "operation": operation,
                "duration": round(duration, 3),
                "tokens": tokens,
                "success": success
            }
            
            with open(self.llm_metrics_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(metric, ensure_ascii=False) + "\n")
            
            # 记录慢 LLM 调用
            if duration > 5.0:
                logger.warning(f"🐌 LLM 慢调用: {model} - {operation} - {duration:.2f}秒")
            else:
                logger.debug(f"🤖 LLM 调用: {model} - {operation} - {duration:.2f}秒 - {tokens} tokens")
                
        except Exception as e:
            logger.error(f"❌ 记录 LLM 性能失败: {e}")


# 全局 LLM 性能追踪器
llm_tracker = LLMPerformanceTracker()
