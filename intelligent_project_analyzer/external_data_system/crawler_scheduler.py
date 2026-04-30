"""
智能爬虫调度器

策略：
1. 同一网站串行，避免并发触发反爬
2. 分批爬取，每批间隔随机休眠
3. 分时段执行，模拟人类行为
4. 支持断点续爬
5. 实时监控&日志推送
"""

import time
import random
import threading
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
from pathlib import Path
import json


class CrawlerStatus(str, Enum):
    """爬虫状态"""
    IDLE = "idle"  # 空闲
    RUNNING = "running"  # 运行中
    PAUSED = "paused"  # 暂停
    STOPPED = "stopped"  # 停止
    ERROR = "error"  # 错误


@dataclass
class BatchConfig:
    """批次配置"""
    batch_size: int = 50  # 每批数量
    min_delay: float = 2.0  # 最小请求间隔（秒）
    max_delay: float = 5.0  # 最大请求间隔（秒）
    batch_rest: float = 60.0  # 批次间休息（秒）
    error_retry_delay: float = 30.0  # 错误重试延迟（秒）
    max_retries: int = 3  # 最大重试次数
    
    # 时段控制
    work_hours: List[int] = field(default_factory=lambda: list(range(0, 24)))  # 工作时段 24小时全天
    weekend_enabled: bool = True  # 是否在周末运行
    
    # 限速
    max_requests_per_hour: int = 500  # 每小时最大请求数
    max_requests_per_day: int = 5000  # 每天最大请求数


@dataclass
class CrawlerProgress:
    """爬虫进度"""
    task_id: str
    source: str
    status: CrawlerStatus
    
    # 统计
    total: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    
    # 时间
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    last_update: Optional[datetime] = None
    
    # 当前状态
    current_url: Optional[str] = None
    current_batch: int = 0
    total_batches: int = 0
    
    # 性能
    requests_count: int = 0
    success_rate: float = 0.0
    avg_response_time: float = 0.0
    
    # 错误
    last_error: Optional[str] = None
    error_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "source": self.source,
            "status": self.status.value,
            "total": self.total,
            "completed": self.completed,
            "failed": self.failed,
            "skipped": self.skipped,
            "progress_percent": (self.completed / self.total * 100) if self.total > 0 else 0,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "current_url": self.current_url,
            "current_batch": self.current_batch,
            "total_batches": self.total_batches,
            "requests_count": self.requests_count,
            "success_rate": self.success_rate,
            "avg_response_time": self.avg_response_time,
            "last_error": self.last_error,
            "error_count": self.error_count,
            "elapsed_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "estimated_remaining_seconds": self._estimate_remaining_time()
        }
    
    def _estimate_remaining_time(self) -> Optional[float]:
        """估算剩余时间"""
        if not self.start_time or self.completed == 0:
            return None
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        avg_time_per_item = elapsed / self.completed
        remaining_items = self.total - self.completed
        
        return avg_time_per_item * remaining_items


class IntelligentCrawlerScheduler:
    """智能爬虫调度器"""
    
    def __init__(self, config: Optional[BatchConfig] = None):
        """
        Args:
            config: 批次配置
        """
        self.config = config or BatchConfig()
        
        # 进度追踪
        self.active_tasks: Dict[str, CrawlerProgress] = {}
        
        # 监控回调
        self.progress_callbacks: List[Callable] = []
        self.log_callbacks: List[Callable] = []
        
        # 限速计数器
        self._rate_lock = threading.Lock()
        self.hourly_requests = 0
        self.daily_requests = 0
        self.last_hour_reset = datetime.now()
        self.last_day_reset = datetime.now().date()
        
        # 状态持久化
        self.state_dir = Path("data/crawler_state")
        self.state_dir.mkdir(parents=True, exist_ok=True)
    
    def register_progress_callback(self, callback: Callable):
        """注册进度回调（用于WebSocket推送）"""
        self.progress_callbacks.append(callback)
        logger.info(f"注册进度回调: {callback.__name__}")
    
    def register_log_callback(self, callback: Callable):
        """注册日志回调"""
        self.log_callbacks.append(callback)
        logger.info(f"注册日志回调: {callback.__name__}")
    
    def _emit_progress(self, task_id: str):
        """触发进度更新"""
        if task_id in self.active_tasks:
            progress = self.active_tasks[task_id]
            progress.last_update = datetime.now()
            
            # 调用所有回调
            for callback in self.progress_callbacks:
                try:
                    callback(progress.to_dict())
                except Exception as e:
                    logger.error(f"进度回调失败: {e}")
    
    def _emit_log(self, task_id: str, level: str, message: str):
        """触发日志推送"""
        log_data = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message
        }
        
        for callback in self.log_callbacks:
            try:
                callback(log_data)
            except Exception as e:
                logger.error(f"日志回调失败: {e}")
    
    def _check_rate_limit(self) -> bool:
        """检查是否触发限速"""
        with self._rate_lock:
            now = datetime.now()

            # 重置小时计数器
            if (now - self.last_hour_reset).total_seconds() >= 3600:
                self.hourly_requests = 0
                self.last_hour_reset = now

            # 重置日计数器
            if now.date() > self.last_day_reset:
                self.daily_requests = 0
                self.last_day_reset = now.date()

            # 检查限制
            if self.hourly_requests >= self.config.max_requests_per_hour:
                return False
            if self.daily_requests >= self.config.max_requests_per_day:
                return False

            return True
    
    def _should_work_now(self) -> bool:
        """判断当前时段是否应该工作"""
        now = datetime.now()
        
        # 检查周末
        if not self.config.weekend_enabled and now.weekday() >= 5:
            return False
        
        # 检查工作时段
        if now.hour not in self.config.work_hours:
            return False
        
        return True
    
    def _random_delay(self):
        """随机延迟（模拟人类行为）"""
        delay = random.uniform(self.config.min_delay, self.config.max_delay)
        time.sleep(delay)
    
    def _batch_rest(self, task_id: str):
        """批次间休息"""
        rest_time = self.config.batch_rest
        
        # 添加随机波动（±20%）
        rest_time *= random.uniform(0.8, 1.2)
        
        self._emit_log(task_id, "info", f"批次完成，休息 {rest_time:.1f} 秒...")
        time.sleep(rest_time)
    
    def crawl_batch(
        self,
        task_id: str,
        source: str,
        items: List[Any],
        crawl_func: Callable,
        resume_from: int = 0
    ) -> Dict[str, Any]:
        """
        批量爬取（智能调度）
        
        Args:
            task_id: 任务ID
            source: 数据源
            items: 待爬取项目列表
            crawl_func: 爬取函数 (item) -> bool (成功/失败)
            resume_from: 从第几项开始（断点续爬）
        
        Returns:
            结果统计
        """
        # 创建进度对象
        progress = CrawlerProgress(
            task_id=task_id,
            source=source,
            status=CrawlerStatus.RUNNING,
            total=len(items),
            start_time=datetime.now()
        )
        self.active_tasks[task_id] = progress
        
        # 计算批次
        total_items = len(items)
        progress.total_batches = (total_items + self.config.batch_size - 1) // self.config.batch_size
        
        self._emit_log(task_id, "info", f"开始爬取: {source}, 共 {total_items} 项, {progress.total_batches} 批")
        self._emit_progress(task_id)
        
        try:
            # 遍历所有项目
            for i in range(resume_from, total_items):
                # 检查是否应该暂停
                if progress.status == CrawlerStatus.PAUSED:
                    self._emit_log(task_id, "warning", "任务已暂停")
                    break
                
                if progress.status == CrawlerStatus.STOPPED:
                    self._emit_log(task_id, "warning", "任务已停止")
                    break
                
                # 检查工作时段
                if not self._should_work_now():
                    wait_until = self._next_work_time()
                    self._emit_log(task_id, "info", f"非工作时段，等待至 {wait_until.strftime('%H:%M')}")
                    
                    # 设置为暂停状态，等待工作时段
                    progress.status = CrawlerStatus.PAUSED
                    self._emit_progress(task_id)
                    
                    while not self._should_work_now():
                        time.sleep(60)  # 每分钟检查一次
                    
                    progress.status = CrawlerStatus.RUNNING
                    self._emit_log(task_id, "info", "恢复爬取")
                
                # 检查限速
                if not self._check_rate_limit():
                    self._emit_log(task_id, "warning", "触发限速，暂停1小时")
                    progress.status = CrawlerStatus.PAUSED
                    self._emit_progress(task_id)
                    time.sleep(3600)
                    progress.status = CrawlerStatus.RUNNING
                
                # 批次休息
                if i > 0 and i % self.config.batch_size == 0:
                    progress.current_batch = i // self.config.batch_size
                    self._emit_progress(task_id)
                    self._batch_rest(task_id)
                
                # 爬取单项
                item = items[i]
                progress.current_url = getattr(item, 'url', str(item))
                
                retry_count = 0
                success = False
                
                while retry_count < self.config.max_retries:
                    try:
                        start_time = time.time()
                        success = crawl_func(item)
                        response_time = time.time() - start_time
                        
                        # 更新平均响应时间
                        progress.avg_response_time = (
                            (progress.avg_response_time * progress.requests_count + response_time) 
                            / (progress.requests_count + 1)
                        )
                        
                        progress.requests_count += 1
                        with self._rate_lock:
                            self.hourly_requests += 1
                            self.daily_requests += 1
                        
                        if success:
                            progress.completed += 1
                            progress.success_rate = progress.completed / (progress.completed + progress.failed)
                            break
                        else:
                            retry_count += 1
                            if retry_count < self.config.max_retries:
                                self._emit_log(task_id, "warning", f"爬取失败，重试 {retry_count}/{self.config.max_retries}")
                                time.sleep(self.config.error_retry_delay)
                    
                    except Exception as e:
                        retry_count += 1
                        progress.error_count += 1
                        progress.last_error = str(e)
                        
                        self._emit_log(task_id, "error", f"爬取异常: {e}")
                        
                        if retry_count < self.config.max_retries:
                            time.sleep(self.config.error_retry_delay)
                
                if not success:
                    progress.failed += 1
                
                # 更新进度
                self._emit_progress(task_id)
                
                # 请求间随机延迟
                if i < total_items - 1:  # 最后一个不需要延迟
                    self._random_delay()
                
                # 保存断点
                if i % 10 == 0:
                    self._save_checkpoint(task_id, i)
        
        except Exception as e:
            progress.status = CrawlerStatus.ERROR
            progress.last_error = str(e)
            self._emit_log(task_id, "error", f"任务失败: {e}")
            logger.exception(f"爬取任务失败: {task_id}")
        
        finally:
            # 完成
            progress.end_time = datetime.now()
            progress.status = CrawlerStatus.IDLE
            self._emit_progress(task_id)
            
            elapsed = (progress.end_time - progress.start_time).total_seconds()
            self._emit_log(
                task_id, 
                "info", 
                f"任务完成: 成功 {progress.completed}, 失败 {progress.failed}, 耗时 {elapsed:.1f}秒"
            )
        
        return progress.to_dict()
    
    def _next_work_time(self) -> datetime:
        """计算下一个工作时段"""
        now = datetime.now()
        next_time = now
        
        # 找到下一个工作小时
        while next_time.hour not in self.config.work_hours:
            next_time += timedelta(hours=1)
            
            # 如果跨天了，检查周末
            if not self.config.weekend_enabled and next_time.weekday() >= 5:
                # 跳到下周一
                days_ahead = 7 - next_time.weekday()
                next_time += timedelta(days=days_ahead)
                next_time = next_time.replace(hour=self.config.work_hours[0], minute=0)
        
        return next_time
    
    def _save_checkpoint(self, task_id: str, position: int):
        """保存断点"""
        checkpoint_file = self.state_dir / f"{task_id}.checkpoint"
        
        checkpoint_data = {
            "task_id": task_id,
            "position": position,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
    
    def load_checkpoint(self, task_id: str) -> Optional[int]:
        """加载断点"""
        checkpoint_file = self.state_dir / f"{task_id}.checkpoint"
        
        if not checkpoint_file.exists():
            return None
        
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('position', 0)
        except Exception as e:
            logger.error(f"加载断点失败: {e}")
            return None
    
    def pause_task(self, task_id: str):
        """暂停任务"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].status = CrawlerStatus.PAUSED
            self._emit_log(task_id, "info", "任务已暂停")
            self._emit_progress(task_id)
    
    def resume_task(self, task_id: str):
        """恢复任务"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].status = CrawlerStatus.RUNNING
            self._emit_log(task_id, "info", "任务已恢复")
            self._emit_progress(task_id)
    
    def stop_task(self, task_id: str):
        """停止任务"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].status = CrawlerStatus.STOPPED
            self._emit_log(task_id, "info", "任务已停止")
            self._emit_progress(task_id)
    
    def get_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取进度"""
        if task_id in self.active_tasks:
            return self.active_tasks[task_id].to_dict()
        return None
    
    def get_all_progress(self) -> List[Dict[str, Any]]:
        """获取所有任务进度"""
        return [progress.to_dict() for progress in self.active_tasks.values()]
