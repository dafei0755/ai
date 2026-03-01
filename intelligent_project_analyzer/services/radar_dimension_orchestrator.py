"""
雷达图维度生成编排器 (v9.0)
============================

架构：动态优先 + 三级重试 + 显式降级

主路径：
  ProjectSpecificDimensionGenerator (全量上下文, 60s)
     → 质量校验不过 → 压缩上下文重试 (30s)
     → 仍不过 → 最简上下文重试 (20s)
     → 仍不过 → 半动态兜底（关键词+YAML检索）
     → 仍不过 → 传统规则引擎（最终安全网）

每次结果均携带 dimension_meta（可观测）：
  policy / attempts / degraded / fallback_reason / quality_score / generation_method
"""

import os
import time
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


# ==============================================================================
# 质量门槛常量
# ==============================================================================

MIN_VALID_DIMENSIONS = 5  # 最少有效维度数
MIN_CATEGORY_TYPES = 3  # 至少覆盖的 category 种类
MAX_DEFAULT_CLUSTER_RATIO = 0.8  # default_value 45-55 集中比例上限
QUALITY_SCORE_THRESHOLD = 0.55  # 质量得分下限（0-1）


def _compute_quality_score(dimensions: List[Dict[str, Any]]) -> Tuple[float, List[str]]:
    """
    计算维度集合的质量得分（0-1）。

    返回 (quality_score, issues_list)
    """
    issues: List[str] = []
    if not dimensions:
        return 0.0, ["dimensions 为空"]

    count = len(dimensions)

    # Gate 1: 数量
    if count < MIN_VALID_DIMENSIONS:
        issues.append(f"维度数不足: {count} < {MIN_VALID_DIMENSIONS}")

    # Gate 2: category 种类覆盖
    categories = {d.get("category", "") for d in dimensions}
    if len(categories) < MIN_CATEGORY_TYPES:
        issues.append(f"category 种类不足: {len(categories)} < {MIN_CATEGORY_TYPES}")

    # Gate 3: default_value 不能过度集中在 45-55 区间
    clustered = sum(1 for d in dimensions if 45 <= d.get("default_value", 50) <= 55)
    cluster_ratio = clustered / count if count else 1.0
    if cluster_ratio > MAX_DEFAULT_CLUSTER_RATIO:
        issues.append(f"default_value 过度集中在中间: {cluster_ratio:.0%}")

    # Gate 4: source 不能全是 calibration
    sources = {d.get("source", "calibration") for d in dimensions}
    if sources == {"calibration"}:
        issues.append("所有维度都是 calibration，缺少决策/洞察层")

    # Gate 5: label 有效性（left ≠ right）
    invalid_labels = [
        d.get("name", d.get("id")) for d in dimensions if d.get("left_label", "") == d.get("right_label", "")
    ]
    if invalid_labels:
        issues.append(f"left_label == right_label: {invalid_labels[:3]}")

    # 评分：每个 gate 失败扣分
    deduction_per_issue = 0.2
    score = max(0.0, 1.0 - len(issues) * deduction_per_issue)
    return round(score, 3), issues


# ==============================================================================
# 编排器主体
# ==============================================================================


class RadarDimensionOrchestrator:
    """
    雷达图维度生成统一编排器

    职责：
    - 汇总上文上下文（任务、分析、不确定性、场景）
    - 调用 ProjectSpecificDimensionGenerator，最多 3 次重试
    - 质量校验，不通过则降级
    - 返回维度列表 + dimension_meta（完整可追溯）
    """

    def orchestrate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        主入口。

        Returns:
            {
                "dimensions": [...],
                "dimension_generation_method": "project_specific" | "rule_engine" | "fallback",
                "generation_summary_text": str,
                "generated_count": int,
                "existing_dimensions": [],   # 兼容旧变量
                "dimension_meta": {
                    "policy": "dynamic_first",
                    "attempts": int,
                    "degraded": bool,
                    "fallback_reason": str | None,
                    "quality_score": float,
                    "generation_method": str,
                },
                "generation_trace": [...],
            }
        """
        start_time = time.time()
        trace: List[Dict[str, Any]] = []
        policy = os.getenv("RADAR_DIM_POLICY", "dynamic_first")

        logger.info("=" * 60)
        logger.info(f"[Orchestrator v9.0] 开始维度生成 policy={policy}")

        # ------------------------------------------------------------------
        # 收集上下文
        # ------------------------------------------------------------------
        ctx = self._collect_context(state)
        logger.info(
            f"[Orchestrator] 上下文: input={len(ctx['user_input'])}字 "
            f"tasks={len(ctx['confirmed_tasks'])} "
            f"struct_keys={len(ctx['structured_data'])}"
        )

        # ------------------------------------------------------------------
        # 尝试 LLM 全量生成（最多 3 次，逐渐压缩输入）
        # ------------------------------------------------------------------
        dimensions: Optional[List[Dict[str, Any]]] = None
        generation_method = "rule_engine"
        generation_summary = ""
        quality_score = 0.0
        fallback_reason: Optional[str] = None
        attempts = 0

        attempt_configs = [
            {"label": "全量", "timeout": 60, "compress": False, "minimal": False},
            {"label": "压缩", "timeout": 30, "compress": True, "minimal": False},
            {"label": "最简", "timeout": 20, "compress": True, "minimal": True},
        ]

        for attempt_cfg in attempt_configs:
            attempts += 1
            label = attempt_cfg["label"]
            logger.info(f"[Orchestrator] 尝试 #{attempts} ({label}输入, timeout={attempt_cfg['timeout']}s)")

            attempt_result = self._try_llm_generate(ctx, attempt_cfg)
            trace.append(
                {
                    "attempt": attempts,
                    "label": label,
                    "success": attempt_result.get("success", False),
                    "dim_count": len(attempt_result.get("dimensions", [])),
                    "error": attempt_result.get("error"),
                    "duration_ms": attempt_result.get("duration_ms"),
                }
            )

            if not attempt_result.get("success"):
                logger.warning(f"[Orchestrator] 尝试 #{attempts} 失败: {attempt_result.get('error')}")
                continue

            candidate_dims = attempt_result.get("dimensions", [])
            q_score, q_issues = _compute_quality_score(candidate_dims)
            logger.info(f"[Orchestrator] 尝试 #{attempts} 质量得分: {q_score:.2f} issues={q_issues}")

            if q_score >= QUALITY_SCORE_THRESHOLD:
                dimensions = candidate_dims
                quality_score = q_score
                generation_method = "project_specific"
                generation_summary = attempt_result.get("generation_summary", "")
                logger.info(f"[Orchestrator] ✅ 尝试 #{attempts} 通过质量校验，{len(dimensions)} 个维度")
                break
            else:
                logger.warning(f"[Orchestrator] 尝试 #{attempts} 质量不足，继续重试")
                fallback_reason = f"质量不足(attempt={attempts}): {'; '.join(q_issues[:2])}"

        # ------------------------------------------------------------------
        # LLM 全部失败 → 半动态兜底（关键词 + YAML 检索）
        # ------------------------------------------------------------------
        if dimensions is None:
            logger.warning("[Orchestrator] LLM 3次尝试全部失败，进入半动态兜底")
            semi_result = self._semi_dynamic_fallback(ctx, state)
            candidate_dims = semi_result.get("dimensions", [])
            if len(candidate_dims) >= MIN_VALID_DIMENSIONS:
                dimensions = candidate_dims
                generation_method = "semi_dynamic"
                quality_score, _ = _compute_quality_score(dimensions)
                fallback_reason = fallback_reason or "LLM不可用"
                logger.info(f"[Orchestrator] 半动态兜底: {len(dimensions)} 个维度")
            else:
                fallback_reason = fallback_reason or "LLM不可用+半动态维度不足"

        # ------------------------------------------------------------------
        # 最终兜底 → 传统规则引擎
        # ------------------------------------------------------------------
        if dimensions is None:
            logger.warning("[Orchestrator] 半动态兜底也不足，使用规则引擎兜底")
            dimensions = self._rule_engine_fallback(state)
            generation_method = "rule_engine"
            quality_score, _ = _compute_quality_score(dimensions)
            fallback_reason = fallback_reason or "所有动态路径均失败"

        # ------------------------------------------------------------------
        # 场景注入（在最终维度基础上叠加专场维度）
        # 仅在非 project_specific 路径才执行（project_specific 已由 LLM 覆盖场景）
        # ------------------------------------------------------------------
        if generation_method != "project_specific":
            dimensions = self._inject_scene_dimensions(state, dimensions)

        # ------------------------------------------------------------------
        # 维度数上限保护
        # ------------------------------------------------------------------
        dimensions = dimensions[:14]

        elapsed = round((time.time() - start_time) * 1000)
        degraded = generation_method != "project_specific"
        logger.info(
            f"[Orchestrator] 完成: method={generation_method} "
            f"degraded={degraded} dims={len(dimensions)} "
            f"quality={quality_score:.2f} elapsed={elapsed}ms"
        )

        dimension_meta = {
            "policy": policy,
            "attempts": attempts,
            "degraded": degraded,
            "fallback_reason": fallback_reason,
            "quality_score": quality_score,
            "generation_method": generation_method,
            "elapsed_ms": elapsed,
        }

        return {
            "dimensions": dimensions,
            "dimension_generation_method": generation_method,
            "generation_summary_text": generation_summary,
            "generated_count": len(dimensions),
            "existing_dimensions": [],  # 兼容旧变量
            "dimension_meta": dimension_meta,
            "generation_trace": trace,
        }

    # -----------------------------------------------------------------------
    # 内部方法
    # -----------------------------------------------------------------------

    def _collect_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """汇总 LLM 上下文所需的所有字段"""
        agent_results = state.get("agent_results", {})
        req_result = agent_results.get("requirements_analyst", {})
        structured_data = req_result.get("structured_data", {})

        return {
            "user_input": state.get("user_input", ""),
            "project_type": state.get("project_type", ""),
            "confirmed_tasks": state.get("confirmed_core_tasks", []),
            "structured_data": structured_data,
            "special_scene": state.get("special_scene_metadata"),
        }

    def _try_llm_generate(
        self,
        ctx: Dict[str, Any],
        cfg: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        单次 LLM 生成尝试。

        cfg 字段：
          timeout (int)    — LLM 超时秒数
          compress (bool)  — 是否压缩 structured_data
          minimal (bool)   — 是否仅使用 user_input + confirmed_tasks（最简模式）
        """
        t0 = time.time()
        try:
            from .project_specific_dimension_generator import ProjectSpecificDimensionGenerator

            generator = ProjectSpecificDimensionGenerator(timeout_override=cfg["timeout"])

            if cfg.get("minimal"):
                # 最简模式：清空 structured_data，只保留核心字段
                structured_data = {
                    "core_tensions": ctx["structured_data"].get("core_tensions", []),
                }
            elif cfg.get("compress"):
                # 压缩模式：只保留最重要的高层字段，截断长文本
                sd = ctx["structured_data"]
                structured_data = {
                    "core_tensions": sd.get("core_tensions", []),
                    "uncertainty_map": sd.get("uncertainty_map", {}),
                    "human_dimensions": str(sd.get("human_dimensions", ""))[:300],
                    "five_whys_analysis": str(sd.get("five_whys_analysis", ""))[:300],
                }
            else:
                structured_data = ctx["structured_data"]

            result = generator.generate_dimensions(
                user_input=ctx["user_input"],
                structured_data=structured_data,
                confirmed_tasks=ctx["confirmed_tasks"],
                project_type=ctx["project_type"],
            )

            elapsed = round((time.time() - t0) * 1000)
            dims = result.get("dimensions", [])
            if dims:
                return {
                    "success": True,
                    "dimensions": dims,
                    "generation_summary": result.get("generation_summary", ""),
                    "duration_ms": elapsed,
                }
            else:
                return {"success": False, "error": "LLM返回空维度列表", "duration_ms": elapsed}

        except Exception as e:
            elapsed = round((time.time() - t0) * 1000)
            err = str(e)[:200]
            logger.error(f"[Orchestrator] LLM生成异常({cfg['label']}): {type(e).__name__}: {err}")
            return {"success": False, "error": err, "duration_ms": elapsed}

    def _semi_dynamic_fallback(
        self,
        ctx: Dict[str, Any],
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        半动态兜底：从用户输入提取关键词，在 radar_dimensions.yaml 中检索语义最近维度。
        比纯静态规则引擎更贴合上下文。
        """
        try:
            from .dimension_selector import DimensionSelector

            selector = DimensionSelector()
            result = selector.select_for_project(
                project_type=ctx["project_type"] or "personal_residential",
                user_input=ctx["user_input"],
                structured_data=ctx["structured_data"],
                min_dimensions=7,
                max_dimensions=12,
            )
            dims = result if isinstance(result, list) else result.get("dimensions", [])
            return {"dimensions": dims}
        except Exception as e:
            logger.error(f"[Orchestrator] 半动态兜底失败: {e}")
            return {"dimensions": []}

    def _rule_engine_fallback(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """传统规则引擎兜底（select_dimensions_for_state）"""
        try:
            from .dimension_selector import select_dimensions_for_state

            result = select_dimensions_for_state(state)
            dims = result if isinstance(result, list) else result.get("dimensions", [])
            return dims if isinstance(dims, list) else []
        except Exception as e:
            logger.error(f"[Orchestrator] 规则引擎兜底失败: {e}")
            return []

    def _inject_scene_dimensions(
        self,
        state: Dict[str, Any],
        dimensions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """特殊场景维度注入（仅在非 LLM 路径中执行）"""
        try:
            special_scene_metadata = state.get("special_scene_metadata")
            confirmed_tasks = state.get("confirmed_core_tasks", [])
            user_input = state.get("user_input", "")

            if not (special_scene_metadata or confirmed_tasks):
                return dimensions

            from .dimension_selector import DimensionSelector

            selector = DimensionSelector()
            result = selector.detect_and_inject_specialized_dimensions(
                user_input=user_input,
                confirmed_tasks=confirmed_tasks,
                current_dimensions=dimensions,
                special_scene_metadata=special_scene_metadata,
            )
            injected = result if isinstance(result, list) else result.get("dimensions", dimensions)
            if len(injected) > len(dimensions):
                logger.info(f"[Orchestrator] 场景注入: {len(dimensions)} → {len(injected)} 个维度")
            return injected
        except Exception as e:
            logger.warning(f"[Orchestrator] 场景注入失败: {e}")
            return dimensions
