"""
统一学习任务调度器 (Learning Scheduler)

为所有自学习子系统提供定期执行基础设施：
- 动机模式分析 (weekly_pattern_analysis)
- 分类标签晋升 (taxonomy promotion check)
- 维度候选自动审批 (dimension auto-promotion)
- 验证报告聚合趋势分析

支持：
- 手动触发（管理员 API）
- 自动定时执行（asyncio 后台任务）
- 状态查询

版本: v1.0
创建日期: 2026-02-21
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, Optional

from loguru import logger


class LearningTask:
    """单个学习任务定义"""

    def __init__(
        self,
        name: str,
        func: Callable[..., Coroutine],
        interval_seconds: int,
        description: str = "",
    ):
        self.name = name
        self.func = func
        self.interval_seconds = interval_seconds
        self.description = description
        self.last_run: Optional[float] = None
        self.last_result: Optional[Dict[str, Any]] = None
        self.run_count: int = 0
        self.error_count: int = 0
        self.enabled: bool = True


class LearningScheduler:
    """
    统一学习任务调度器

    管理所有自学习子系统的定期任务，提供统一的启动/停止/状态查询接口。
    """

    def __init__(self):
        self.tasks: Dict[str, LearningTask] = {}
        self._running = False
        self._background_task: Optional[asyncio.Task] = None
        self._register_default_tasks()
        logger.info(" LearningScheduler 已初始化")

    def _register_default_tasks(self):
        """注册默认的学习任务"""

        # 1. 动机模式分析（每周一次 = 7天）
        self.register_task(
            name="motivation_pattern_analysis",
            func=self._run_motivation_analysis,
            interval_seconds=7 * 24 * 3600,
            description="分析低置信度动机案例，发现改进模式",
        )

        # 2. 分类标签晋升检查（每天一次）
        self.register_task(
            name="taxonomy_promotion_check",
            func=self._run_taxonomy_promotion,
            interval_seconds=24 * 3600,
            description="检查并晋升符合条件的分类标签",
        )

        # 3. 维度候选自动审批（每天一次）
        self.register_task(
            name="dimension_auto_promotion",
            func=self._run_dimension_auto_promotion,
            interval_seconds=24 * 3600,
            description="自动审批高置信度维度候选",
        )

        # 4. 项目类型扩展扫描（每 3 天一次）
        self.register_task(
            name="type_expansion_scan",
            func=self._run_type_expansion_scan,
            interval_seconds=3 * 24 * 3600,
            description="扫描爬虫知识库，发现未覆盖类型模式，生成候选待管理员审核",
        )

    def register_task(
        self,
        name: str,
        func: Callable[..., Coroutine],
        interval_seconds: int,
        description: str = "",
        run_immediately: bool = False,
    ):
        """注册一个学习任务

        Args:
            run_immediately: 若为 False（默认），首次执行推迟到首个完整间隔后，
                             避免启动时立即触发 LLM 调用。
        """
        task = LearningTask(
            name=name,
            func=func,
            interval_seconds=interval_seconds,
            description=description,
        )
        if not run_immediately:
            # 将 last_run 设为当前时间，使首次执行推迟一个完整间隔
            task.last_run = time.time()
        self.tasks[name] = task
        logger.debug(f" 注册学习任务: {name} (间隔: {interval_seconds}s, 立即执行: {run_immediately})")

    async def start(self):
        """启动调度器后台循环"""
        if self._running:
            logger.warning(" LearningScheduler 已在运行中")
            return

        self._running = True
        self._background_task = asyncio.create_task(self._scheduler_loop())
        logger.info(f" LearningScheduler 已启动，管理 {len(self.tasks)} 个任务")

    async def stop(self):
        """停止调度器"""
        self._running = False
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
        logger.info(" LearningScheduler 已停止")

    async def _scheduler_loop(self):
        """调度器主循环"""
        while self._running:
            now = time.time()
            for task in self.tasks.values():
                if not task.enabled:
                    continue
                # 检查是否到了执行时间
                if task.last_run is None or (now - task.last_run) >= task.interval_seconds:
                    await self._execute_task(task)

            # 每 60 秒检查一次
            await asyncio.sleep(60)

    async def _execute_task(self, task: LearningTask):
        """执行单个任务"""
        logger.info(f" [Scheduler] 执行任务: {task.name}")
        start = time.time()
        try:
            result = await task.func()
            task.last_result = result
            task.run_count += 1
            task.last_run = time.time()
            elapsed = time.time() - start
            logger.info(f" [Scheduler] {task.name} 完成 ({elapsed:.1f}s)")
        except Exception as e:
            task.error_count += 1
            task.last_run = time.time()
            task.last_result = {"error": str(e)}
            logger.error(f" [Scheduler] {task.name} 失败: {e}")

    async def run_task(self, task_name: str) -> Dict[str, Any]:
        """手动触发执行指定任务"""
        task = self.tasks.get(task_name)
        if not task:
            return {"error": f"任务不存在: {task_name}", "available": list(self.tasks.keys())}

        await self._execute_task(task)
        return {
            "task": task_name,
            "result": task.last_result,
            "run_count": task.run_count,
        }

    async def run_all(self) -> Dict[str, Any]:
        """手动触发执行所有任务"""
        results = {}
        for name, task in self.tasks.items():
            if task.enabled:
                await self._execute_task(task)
                results[name] = task.last_result
        return results

    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        tasks_status = {}
        for name, task in self.tasks.items():
            tasks_status[name] = {
                "description": task.description,
                "enabled": task.enabled,
                "interval_seconds": task.interval_seconds,
                "last_run": datetime.fromtimestamp(task.last_run).isoformat() if task.last_run else None,
                "run_count": task.run_count,
                "error_count": task.error_count,
                "last_result_status": "success"
                if task.last_result and "error" not in task.last_result
                else ("error" if task.last_result and "error" in task.last_result else "never_run"),
            }

        return {
            "running": self._running,
            "total_tasks": len(self.tasks),
            "enabled_tasks": sum(1 for t in self.tasks.values() if t.enabled),
            "tasks": tasks_status,
        }

    def set_task_enabled(self, task_name: str, enabled: bool) -> bool:
        """启用/禁用指定任务"""
        task = self.tasks.get(task_name)
        if not task:
            return False
        task.enabled = enabled
        logger.info(f" [Scheduler] {task_name} {'启用' if enabled else '禁用'}")
        return True

    # ========================================================================
    # 具体任务实现
    # ========================================================================

    @staticmethod
    async def _run_type_expansion_scan() -> Dict[str, Any]:
        """
        Step 3: 扫描爬虫知识库，发现未覆盖类型模式，自动入库候选待管理员审核。

        触发时机：每 3 天由调度器自动执行
        手动触发：管理员 API POST /admin/scheduling/run {"task":"type_expansion_scan"}
        """
        try:
            from .project_type_expansion import ProjectTypeCandidateCollector

            collector = ProjectTypeCandidateCollector()
            candidates = collector.scan_crawler_data(limit=200)

            saved = 0
            for cand in candidates:
                cid = collector.merge_or_save_candidate(cand)
                if cid:
                    saved += 1

            logger.info(f"✅ [Scheduler] 类型扩展扫描完成: 发现 {len(candidates)} 个模式，" f"入库 {saved} 条候选")
            return {
                "status": "success",
                "patterns_found": len(candidates),
                "candidates_saved": saved,
            }
        except Exception as e:
            logger.error(f"❌ [Scheduler] 类型扩展扫描失败: {e}")
            return {"status": "error", "error": str(e)}

    @staticmethod
    async def _run_motivation_analysis() -> Dict[str, Any]:
        """执行动机模式分析"""
        from .motivation_engine import MotivationTypeRegistry, MotivationLearningSystem

        registry = MotivationTypeRegistry()
        learning = MotivationLearningSystem(registry)
        return await learning.weekly_pattern_analysis()

    @staticmethod
    async def _run_taxonomy_promotion() -> Dict[str, Any]:
        """执行分类标签晋升检查"""
        from .taxonomy_promotion_service import TaxonomyPromotionService

        service = TaxonomyPromotionService()
        result = service.run_promotion_check(auto_promote=True)
        return result

    # LLM提取的category → ontology.yaml 有效 (project_type, category) 映射
    _CATEGORY_MAPPING = {
        # 空间/物质类 → meta_framework.ontological_foundations
        "spatial_experience": ("meta_framework", "ontological_foundations"),
        "material_system": ("meta_framework", "ontological_foundations"),
        "environmental_response": ("meta_framework", "ontological_foundations"),
        # 用户/社会类 → meta_framework.contemporary_imperatives
        "user_behavior": ("meta_framework", "contemporary_imperatives"),
        "social_dynamics": ("meta_framework", "contemporary_imperatives"),
        # 商业/运营类 → commercial_retail.business_positioning
        "business_logic": ("commercial_retail", "business_positioning"),
        "operational_strategy": ("commercial_retail", "operational_strategy"),
        # 临时/未分类 → meta_framework.universal_dimensions
        "extracted_from_expert": ("meta_framework", "universal_dimensions"),
    }
    _DEFAULT_CATEGORY = ("meta_framework", "universal_dimensions")


# 全局单例
_learning_scheduler: Optional[LearningScheduler] = None


def get_learning_scheduler() -> LearningScheduler:
    """获取全局学习调度器实例"""
    global _learning_scheduler
    if _learning_scheduler is None:
        _learning_scheduler = LearningScheduler()
    return _learning_scheduler
