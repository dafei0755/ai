"""
示例质量分析器 - Phase 1 Intelligence Evolution

基于 UsageTracker 收集的使用数据，对 Few-Shot 示例库进行
质量评分，生成日报告，并输出待优化/待淘汰示例清单。

Author: AI Architecture Team
Version: v1.0.0
Date: 2026-03-04
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .usage_tracker import UsageTracker


# ── 数据模型 ──────────────────────────────────────────────────────────────


@dataclass
class ExampleScore:
    """单条示例评分"""

    example_id: str
    role_id: str
    total_uses: int = 0
    positive_feedback: int = 0
    negative_feedback: int = 0
    avg_rating: Optional[float] = None
    quality_score: float = 0.0
    recommendation: str = "keep"  # keep / improve / retire


@dataclass
class QualityReport:
    """整体质量报告"""

    role_id: str
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    total_examples: int = 0
    analyzed_examples: int = 0
    scores: List[ExampleScore] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    recommendations: Dict[str, List[str]] = field(
        default_factory=lambda: {"keep": [], "improve": [], "retire": []}
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "generated_at": self.generated_at,
            "total_examples": self.total_examples,
            "analyzed_examples": self.analyzed_examples,
            "summary": self.summary,
            "recommendations": self.recommendations,
            "scores": [
                {
                    "example_id": s.example_id,
                    "total_uses": s.total_uses,
                    "positive_feedback": s.positive_feedback,
                    "negative_feedback": s.negative_feedback,
                    "avg_rating": s.avg_rating,
                    "quality_score": round(s.quality_score, 3),
                    "recommendation": s.recommendation,
                }
                for s in self.scores
            ],
        }


# ── 分析器 ────────────────────────────────────────────────────────────────


class ExampleQualityAnalyzer:
    """
    示例质量分析器

    评分公式（0~1）：
        quality_score = 0.5 * feedback_ratio
                      + 0.3 * normalized_uses
                      + 0.2 * rating_norm
    其中：
        feedback_ratio  = positive / (positive + negative + 1)
        normalized_uses = min(total_uses / 20, 1.0)
        rating_norm     = (avg_rating - 1) / 4  （1-5 分转 0-1）
    """

    def __init__(
        self,
        usage_tracker: UsageTracker,
        output_dir: Optional[Path] = None,
    ) -> None:
        self.tracker = usage_tracker

        if output_dir is None:
            output_dir = (
                Path(__file__).parent.parent.parent
                / "data"
                / "intelligence"
                / "quality_reports"
            )
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ── 分析入口 ─────────────────────────────────────────────────────

    def analyze(
        self,
        role_id: str,
        persist: bool = True,
    ) -> QualityReport:
        """
        对指定角色的示例库进行质量分析

        Args:
            role_id: 角色 ID
            persist: 是否将报告写入磁盘

        Returns:
            QualityReport
        """
        logger.info(f"[ExampleQualityAnalyzer] 开始分析角色: {role_id}")

        # 收集所有使用记录
        logs = self.tracker.get_logs(limit=50000, role_id=role_id)

        # 统计每个示例 ID 的使用情况
        example_stats: Dict[str, Dict[str, Any]] = {}
        for log in logs:
            examples = log.get("selected_examples") or []
            if not isinstance(examples, list):
                continue
            for ex_id in examples:
                if ex_id not in example_stats:
                    example_stats[ex_id] = {
                        "total_uses": 0,
                        "positive": 0,
                        "negative": 0,
                        "ratings": [],
                    }
                stats = example_stats[ex_id]
                stats["total_uses"] += 1

                fb = log.get("user_feedback") or {}
                if isinstance(fb, dict):
                    if fb.get("liked") is True:
                        stats["positive"] += 1
                    if fb.get("edited") is True or fb.get("liked") is False:
                        stats["negative"] += 1
                    if "rating" in fb:
                        try:
                            stats["ratings"].append(float(fb["rating"]))
                        except (TypeError, ValueError):
                            pass

        # 最大使用次数（用于归一化）
        max_uses = max((s["total_uses"] for s in example_stats.values()), default=1)

        # 评分
        scores: List[ExampleScore] = []
        for ex_id, stats in example_stats.items():
            pos = stats["positive"]
            neg = stats["negative"]
            uses = stats["total_uses"]
            ratings = stats["ratings"]

            feedback_ratio = pos / (pos + neg + 1)
            normalized_uses = min(uses / max(max_uses, 20), 1.0)
            rating_norm = (sum(ratings) / len(ratings) - 1) / 4 if ratings else 0.5

            quality = (
                0.5 * feedback_ratio
                + 0.3 * normalized_uses
                + 0.2 * rating_norm
            )

            if quality >= 0.6:
                recommendation = "keep"
            elif quality >= 0.35:
                recommendation = "improve"
            else:
                recommendation = "retire"

            avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

            scores.append(
                ExampleScore(
                    example_id=ex_id,
                    role_id=role_id,
                    total_uses=uses,
                    positive_feedback=pos,
                    negative_feedback=neg,
                    avg_rating=avg_rating,
                    quality_score=quality,
                    recommendation=recommendation,
                )
            )

        scores.sort(key=lambda s: s.quality_score, reverse=True)

        # 汇总
        report = QualityReport(
            role_id=role_id,
            total_examples=len(example_stats),
            analyzed_examples=len(scores),
            scores=scores,
            summary={
                "avg_quality_score": round(
                    sum(s.quality_score for s in scores) / len(scores), 3
                ) if scores else 0.0,
                "keep_count": sum(1 for s in scores if s.recommendation == "keep"),
                "improve_count": sum(1 for s in scores if s.recommendation == "improve"),
                "retire_count": sum(1 for s in scores if s.recommendation == "retire"),
                "total_usage_events": len(logs),
            },
            recommendations={
                "keep": [s.example_id for s in scores if s.recommendation == "keep"],
                "improve": [s.example_id for s in scores if s.recommendation == "improve"],
                "retire": [s.example_id for s in scores if s.recommendation == "retire"],
            },
        )

        if persist:
            self._save_report(report)

        logger.info(
            f"[ExampleQualityAnalyzer] 分析完成: {role_id} | "
            f"keep={report.summary.get('keep_count')} "
            f"improve={report.summary.get('improve_count')} "
            f"retire={report.summary.get('retire_count')}"
        )
        return report

    def analyze_all_roles(self, role_ids: List[str]) -> Dict[str, QualityReport]:
        """批量分析多个角色"""
        return {rid: self.analyze(rid) for rid in role_ids}

    # ── 持久化 ───────────────────────────────────────────────────────

    def _save_report(self, report: QualityReport) -> Path:
        """将报告保存为 JSON 文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report.role_id}_{timestamp}.json"
        out_path = self.output_dir / filename
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"[ExampleQualityAnalyzer] 报告已保存: {out_path}")
        return out_path

    def generate_weekly_report(self, role_ids: List[str]) -> Path:
        """
        生成周汇总报告（所有角色），保存为 Markdown

        Returns:
            报告文件路径
        """
        reports = self.analyze_all_roles(role_ids)

        lines = [
            f"# Few-Shot 示例周报告",
            f"",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"",
        ]
        for role_id, report in reports.items():
            s = report.summary
            lines += [
                f"## 角色 `{role_id}`",
                f"",
                f"- 分析示例数: {report.analyzed_examples}",
                f"- 总使用事件: {s.get('total_usage_events', 0)}",
                f"- 平均质量分: **{s.get('avg_quality_score', 0):.3f}**",
                f"- 保留: {s.get('keep_count', 0)}  待改进: {s.get('improve_count', 0)}  淘汰: {s.get('retire_count', 0)}",
                f"",
            ]
            if report.recommendations["retire"]:
                lines.append(f"### 建议淘汰")
                for ex_id in report.recommendations["retire"]:
                    lines.append(f"- `{ex_id}`")
                lines.append("")

        timestamp = datetime.now().strftime("%Y%m%d")
        out_path = self.output_dir / f"weekly_report_{timestamp}.md"
        out_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"[ExampleQualityAnalyzer] 周报告已保存: {out_path}")
        return out_path
