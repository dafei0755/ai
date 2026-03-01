"""
数据质量监控工具

监控和报告外部数据的质量状况
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from sqlalchemy import func


class DataQualityMonitor:
    """数据质量监控器"""

    def __init__(self, db):
        self.db = db

    def get_overall_stats(self) -> Dict[str, Any]:
        """获取总体统计"""
        from intelligent_project_analyzer.external_data_system.models import ExternalProject

        logger.info("📊 获取总体统计...")

        with self.db.get_session() as session:
            # 总项数
            total = session.query(ExternalProject).count()

            # 平均质量分数
            avg_quality = session.query(func.avg(ExternalProject.quality_score)).scalar() or 0.0

            # 各数据源统计
            source_stats = (
                session.query(
                    ExternalProject.source,
                    func.count(ExternalProject.id).label("count"),
                    func.avg(ExternalProject.quality_score).label("avg_quality"),
                )
                .group_by(ExternalProject.source)
                .all()
            )

            # 最近7天新增
            week_ago = datetime.now() - timedelta(days=7)
            recent = session.query(ExternalProject).filter(ExternalProject.crawled_at >= week_ago).count()

            return {
                "total_projects": total,
                "avg_quality_score": float(avg_quality),
                "recent_7days": recent,
                "sources": [
                    {
                        "source": s.source,
                        "count": s.count,
                        "avg_quality": float(s.avg_quality) if s.avg_quality else 0.0,
                    }
                    for s in source_stats
                ],
            }

    def get_quality_distribution(self) -> Dict[str, int]:
        """获取质量分布"""
        from intelligent_project_analyzer.external_data_system.models import ExternalProject

        logger.info("📊 分析质量分布...")

        with self.db.get_session() as session:
            # 按质量分级统计
            excellent = session.query(ExternalProject).filter(ExternalProject.quality_score >= 0.8).count()

            good = (
                session.query(ExternalProject)
                .filter(ExternalProject.quality_score >= 0.6, ExternalProject.quality_score < 0.8)
                .count()
            )

            fair = (
                session.query(ExternalProject)
                .filter(ExternalProject.quality_score >= 0.4, ExternalProject.quality_score < 0.6)
                .count()
            )

            poor = session.query(ExternalProject).filter(ExternalProject.quality_score < 0.4).count()

            return {
                "excellent": excellent,  # >= 0.8
                "good": good,  # 0.6-0.8
                "fair": fair,  # 0.4-0.6
                "poor": poor,  # < 0.4
            }

    def get_completeness_report(self) -> Dict[str, Any]:
        """获取数据完整度报告"""
        from intelligent_project_analyzer.external_data_system.models import ExternalProject

        logger.info("📊 分析数据完整度...")

        with self.db.get_session() as session:
            total = session.query(ExternalProject).count()

            # 各字段完整度
            fields = {
                "title": session.query(ExternalProject)
                .filter(ExternalProject.title.isnot(None), ExternalProject.title != "")
                .count(),
                "description": session.query(ExternalProject)
                .filter(ExternalProject.description.isnot(None), func.length(ExternalProject.description) > 100)
                .count(),
                "architects": session.query(ExternalProject).filter(ExternalProject.architects.isnot(None)).count(),
                "location": session.query(ExternalProject).filter(ExternalProject.location.isnot(None)).count(),
                "year": session.query(ExternalProject).filter(ExternalProject.year.isnot(None)).count(),
                "area_sqm": session.query(ExternalProject).filter(ExternalProject.area_sqm.isnot(None)).count(),
                "images": session.query(ExternalProject).filter(ExternalProject.images.any()).count(),
            }

            if total > 0:
                return {"字段": "完整数量", **{k: f"{v}/{total} ({v/total*100:.1f}%)" for k, v in fields.items()}}
            else:
                return {"error": "暂无数据"}

    def get_quality_issues_summary(self) -> Dict[str, Any]:
        """获取质量问题汇总"""
        from intelligent_project_analyzer.external_data_system.models import QualityIssue

        logger.info("📊 汇总质量问题...")

        with self.db.get_session() as session:
            # 按类型统计
            by_type = (
                session.query(QualityIssue.issue_type, func.count(QualityIssue.id).label("count"))
                .filter(QualityIssue.status == "unresolved")
                .group_by(QualityIssue.issue_type)
                .all()
            )

            # 按严重程度统计
            by_severity = (
                session.query(QualityIssue.severity, func.count(QualityIssue.id).label("count"))
                .filter(QualityIssue.status == "unresolved")
                .group_by(QualityIssue.severity)
                .all()
            )

            return {
                "by_type": {t.issue_type: t.count for t in by_type},
                "by_severity": {s.severity: s.count for s in by_severity},
                "total_unresolved": sum(t.count for t in by_type),
            }

    def generate_report(self) -> str:
        """生成完整的质量报告"""
        logger.info("=" * 60)
        logger.info("数据质量监控报告")
        logger.info(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)

        try:
            # 1. 总体统计
            stats = self.get_overall_stats()
            logger.info("\n📊 总体统计:")
            logger.info(f"  总项目数: {stats['total_projects']}")
            logger.info(f"  平均质量分数: {stats['avg_quality_score']:.2f}")
            logger.info(f"  近7天新增: {stats['recent_7days']}")

            logger.info("\n  各数据源:")
            for source in stats["sources"]:
                logger.info(f"    - {source['source']}: {source['count']} 个项目 (质量: {source['avg_quality']:.2f})")

            # 2. 质量分布
            dist = self.get_quality_distribution()
            logger.info("\n⭐ 质量分布:")
            total = sum(dist.values())
            if total > 0:
                logger.info(f"  优秀 (≥0.8): {dist['excellent']} ({dist['excellent']/total*100:.1f}%)")
                logger.info(f"  良好 (0.6-0.8): {dist['good']} ({dist['good']/total*100:.1f}%)")
                logger.info(f"  一般 (0.4-0.6): {dist['fair']} ({dist['fair']/total*100:.1f}%)")
                logger.info(f"  较差 (<0.4): {dist['poor']} ({dist['poor']/total*100:.1f}%)")

            # 3. 完整度报告
            completeness = self.get_completeness_report()
            logger.info("\n📝 数据完整度:")
            for field, value in completeness.items():
                logger.info(f"  {field}: {value}")

            # 4. 质量问题
            issues = self.get_quality_issues_summary()
            logger.info("\n⚠️ 质量问题:")
            logger.info(f"  未解决问题总数: {issues['total_unresolved']}")

            if issues["by_type"]:
                logger.info("\n  按类型:")
                for issue_type, count in issues["by_type"].items():
                    logger.info(f"    - {issue_type}: {count}")

            if issues["by_severity"]:
                logger.info("\n  按严重程度:")
                for severity, count in issues["by_severity"].items():
                    logger.info(f"    - {severity}: {count}")

            logger.info("\n" + "=" * 60)
            logger.success("✅ 报告生成完成")

            return "success"

        except Exception as e:
            logger.error(f"❌ 生成报告失败: {e}")
            import traceback

            traceback.print_exc()
            return "failed"


def main():
    """主函数"""
    logger.info("🚀 启动数据质量监控")

    try:
        from intelligent_project_analyzer.external_data_system import get_external_db

        db = get_external_db()
        monitor = DataQualityMonitor(db)

        result = monitor.generate_report()

        logger.info("\n💡 建议:")
        logger.info("  1. 定期运行此脚本监控数据质量")
        logger.info("  2. 优先处理高严重程度的质量问题")
        logger.info("  3. 对低质量数据源进行爬虫优化")
        logger.info("  4. 定期清理低质量项目")

        return 0 if result == "success" else 1

    except Exception as e:
        logger.error(f"❌ 监控失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
