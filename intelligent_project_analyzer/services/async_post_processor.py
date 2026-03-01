# -*- coding: utf-8 -*-
"""
异步后处理器 - v7.600
将Phase2后处理改造为并行执行，提升性能

性能优化:
- 串行执行: ~600ms (validation 200ms + entity_extraction 250ms + motivation 150ms)
- 并行执行: ~250ms (max(200, 250, 150) + 50ms overhead) → 62% 性能提升

创建日期: 2026-02-11
"""

import asyncio
from typing import Dict, Any
from loguru import logger
from datetime import datetime

from .entity_extractor import EntityExtractor
from .requirements_validator import RequirementsValidator
from .motivation_engine import MotivationInferenceEngine


class AsyncPostProcessor:
    """异步后处理器 - 并行执行验证、实体提取、动机推断"""

    def __init__(
        self,
        entity_extractor: EntityExtractor,
        requirements_validator: RequirementsValidator,
        motivation_engine: MotivationInferenceEngine,
    ):
        """
        初始化异步后处理器

        Args:
            entity_extractor: 实体提取器实例
            requirements_validator: 需求验证器实例
            motivation_engine: 动机推断引擎实例
        """
        self.entity_extractor = entity_extractor
        self.requirements_validator = requirements_validator
        self.motivation_engine = motivation_engine

    async def process_phase2_async(
        self, phase2_result: Dict[str, Any], user_input: str, structured_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        并行执行Phase2后处理

        Args:
            phase2_result: Phase2 LLM输出
            user_input: 用户原始输入
            structured_data: 合并后的结构化数据

        Returns:
            增强后的结构化数据（包含validation_result, entities, motivation_types）
        """
        start_time = datetime.now()
        logger.info(" [AsyncPostProcessor] Starting parallel post-processing...")

        # 创建三个并行任务
        validation_task = asyncio.create_task(self._validate_async(phase2_result, user_input))

        entity_extraction_task = asyncio.create_task(self._extract_entities_async(structured_data, user_input))

        motivation_task = asyncio.create_task(self._infer_motivation_async(structured_data, user_input))

        # 等待所有任务完成
        try:
            validation_result, entity_result, motivation_result = await asyncio.gather(
                validation_task, entity_extraction_task, motivation_task, return_exceptions=True  # 不因单个失败而中断
            )

            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f" [AsyncPostProcessor] Parallel processing completed in {elapsed_ms:.0f}ms")

            # 处理结果（检查是否有异常）
            enriched_data = structured_data.copy()

            # 1. Validation结果
            if isinstance(validation_result, Exception):
                logger.error(f" Validation failed: {validation_result}")
                enriched_data["validation_result"] = {"is_valid": False, "error": str(validation_result)}
            else:
                enriched_data["validation_result"] = validation_result.to_dict()
                logger.info(f"    Validation: {validation_result.is_valid}")

            # 2. Entity提取结果
            if isinstance(entity_result, Exception):
                logger.error(f" Entity extraction failed: {entity_result}")
                enriched_data["entities"] = {"error": str(entity_result)}
            else:
                enriched_data["entities"] = entity_result.to_dict()
                logger.info(f"    Entities: {entity_result.total_entities()} extracted")

            # 3. Motivation推断结果
            if isinstance(motivation_result, Exception):
                logger.error(f" Motivation inference failed: {motivation_result}")
                enriched_data["motivation_types"] = {"error": str(motivation_result)}
            else:
                enriched_data["motivation_types"] = {
                    "primary": motivation_result.primary,
                    "primary_label": motivation_result.primary_label,
                    "secondary": motivation_result.secondary or [],
                    "confidence": motivation_result.confidence,
                    "reasoning": motivation_result.reasoning,
                    "method": motivation_result.method,
                }
                logger.info(f"    Motivation: {motivation_result.primary_label} ({motivation_result.confidence:.1f}%)")

            # 性能统计
            enriched_data["_post_processing_metadata"] = {
                "execution_mode": "parallel_async",
                "elapsed_ms": elapsed_ms,
                "timestamp": start_time.isoformat(),
                "version": "v7.600",
            }

            return enriched_data

        except Exception as e:
            logger.error(f" [AsyncPostProcessor] Parallel processing error: {e}")
            raise

    async def _validate_async(self, phase2_result: Dict[str, Any], user_input: str):
        """异步验证Phase2输出"""
        logger.debug("    Validating Phase2 output...")
        # 将同步验证转为异步执行
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.requirements_validator.validate_phase2_output, phase2_result)
        return result

    async def _extract_entities_async(self, structured_data: Dict[str, Any], user_input: str):
        """异步提取实体"""
        logger.debug("    Extracting entities...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.entity_extractor.extract_entities, structured_data, user_input)
        return result

    async def _infer_motivation_async(self, structured_data: Dict[str, Any], user_input: str):
        """异步推断动机"""
        logger.debug("    Inferring motivation types...")

        # 构造任务字典
        task = {
            "project_overview": structured_data.get("project_overview", ""),
            "core_objectives": structured_data.get("core_objectives", []),
            "target_users": structured_data.get("target_users", ""),
        }

        # motivation_engine.infer已经是async方法，直接调用
        result = await self.motivation_engine.infer(task=task, user_input=user_input, structured_data=structured_data)
        return result


# ============================================================================
# 兼容性适配器 - 同步调用接口
# ============================================================================


def run_async_post_processing(
    entity_extractor: EntityExtractor,
    requirements_validator: RequirementsValidator,
    motivation_engine: MotivationInferenceEngine,
    phase2_result: Dict[str, Any],
    user_input: str,
    structured_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    同步调用接口（兼容现有代码）

    内部使用asyncio.run实现并行执行
    """
    processor = AsyncPostProcessor(
        entity_extractor=entity_extractor,
        requirements_validator=requirements_validator,
        motivation_engine=motivation_engine,
    )

    # 运行异步任务
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果已有事件循环，创建新的任务
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run, processor.process_phase2_async(phase2_result, user_input, structured_data)
                )
                return future.result()
        else:
            # 没有事件循环，直接运行
            return loop.run_until_complete(processor.process_phase2_async(phase2_result, user_input, structured_data))
    except RuntimeError:
        # 无事件循环，创建新的
        return asyncio.run(processor.process_phase2_async(phase2_result, user_input, structured_data))
