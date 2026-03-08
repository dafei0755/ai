"""
自动评估审核服务

整合域名质量统计和搜索过滤器，提供自动评估和审核管理功能
"""

from datetime import datetime
from typing import Any, Dict, List

from loguru import logger

from .domain_quality_stats import DomainQualityStatsService, get_domain_stats_service
from .search_filter_manager import SearchFilterManager, get_filter_manager


class AutoReviewService:
    """
    自动评估审核服务

    功能：
    1. 管理审核队列
    2. 执行批准/屏蔽操作（与搜索过滤器联动）
    3. 提供统计报告
    """

    def __init__(
        self,
        stats_service: DomainQualityStatsService | None = None,
        filter_manager: SearchFilterManager | None = None,
    ):
        """
        初始化服务

        Args:
            stats_service: 域名统计服务实例
            filter_manager: 搜索过滤器管理器实例
        """
        self._stats_service = stats_service or get_domain_stats_service()
        self._filter_manager = filter_manager or get_filter_manager()

        logger.info(" 自动评估审核服务已初始化")

    def get_review_queue(self) -> List[Dict[str, Any]]:
        """
        获取待审核队列

        Returns:
            待审核域名列表
        """
        return self._stats_service.get_review_queue()

    def get_review_queue_count(self) -> int:
        """获取待审核数量"""
        return len(self._stats_service.get_review_queue())

    def approve_domain(
        self, domain: str, add_to_whitelist: bool = False, admin_notes: str | None = None
    ) -> Dict[str, Any]:
        """
        批准域名

        Args:
            domain: 域名
            add_to_whitelist: 是否同时加入白名单
            admin_notes: 管理员备注

        Returns:
            操作结果
        """
        try:
            # 从审核队列移除并标记为已批准
            success = self._stats_service.approve_domain(domain, admin_notes)
            if not success:
                return {"success": False, "error": "域名不存在或操作失败"}

            result = {"success": True, "domain": domain, "action": "approved", "added_to_whitelist": False}

            # 可选：加入白名单
            if add_to_whitelist:
                note = f"审核批准 {datetime.now().strftime('%Y-%m-%d')}"
                if admin_notes:
                    note += f" - {admin_notes}"
                whitelist_success = self._filter_manager.add_to_whitelist(domain, note=note)
                result["added_to_whitelist"] = whitelist_success

            logger.info(f" 域名 {domain} 已批准" + (" 并加入白名单" if add_to_whitelist and result["added_to_whitelist"] else ""))
            return result

        except Exception as e:
            logger.error(f" 批准域名失败: {domain} - {e}")
            return {"success": False, "error": str(e)}

    def block_domain(self, domain: str, admin_notes: str | None = None) -> Dict[str, Any]:
        """
        屏蔽域名（加入黑名单）

        Args:
            domain: 域名
            admin_notes: 管理员备注

        Returns:
            操作结果
        """
        try:
            # 从审核队列移除并标记为已屏蔽
            block_result = self._stats_service.block_domain(domain, admin_notes)
            if not block_result.get("success"):
                return block_result

            # 加入搜索过滤器黑名单
            note = block_result.get("note", f"自动评估屏蔽 {datetime.now().strftime('%Y-%m-%d')}")
            blacklist_success = self._filter_manager.add_to_blacklist(domain, note=note)

            result = {
                "success": True,
                "domain": domain,
                "action": "blocked",
                "added_to_blacklist": blacklist_success,
                "stats": block_result.get("stats", {}),
            }

            logger.info(f" 域名 {domain} 已屏蔽并加入黑名单")
            return result

        except Exception as e:
            logger.error(f" 屏蔽域名失败: {domain} - {e}")
            return {"success": False, "error": str(e)}

    def dismiss_domain(self, domain: str, admin_notes: str | None = None) -> Dict[str, Any]:
        """
        移出审核队列（保持观察）

        Args:
            domain: 域名
            admin_notes: 管理员备注

        Returns:
            操作结果
        """
        try:
            success = self._stats_service.dismiss_from_queue(domain, admin_notes)
            if success:
                return {"success": True, "domain": domain, "action": "dismissed", "message": "已移出审核队列，将继续观察"}
            else:
                return {"success": False, "error": "域名不存在或操作失败"}
        except Exception as e:
            logger.error(f" 移出审核队列失败: {domain} - {e}")
            return {"success": False, "error": str(e)}

    def batch_action(self, domains: List[str], action: str, admin_notes: str | None = None) -> Dict[str, Any]:
        """
        批量操作

        Args:
            domains: 域名列表
            action: 操作类型 (approve/block/dismiss)
            admin_notes: 管理员备注

        Returns:
            操作结果汇总
        """
        results = {"total": len(domains), "success": 0, "failed": 0, "details": []}

        for domain in domains:
            if action == "approve":
                result = self.approve_domain(domain, admin_notes=admin_notes)
            elif action == "block":
                result = self.block_domain(domain, admin_notes=admin_notes)
            elif action == "dismiss":
                result = self.dismiss_domain(domain, admin_notes=admin_notes)
            else:
                result = {"success": False, "error": f"未知操作: {action}"}

            if result.get("success"):
                results["success"] += 1
            else:
                results["failed"] += 1

            results["details"].append({"domain": domain, **result})

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取综合统计

        Returns:
            统计信息
        """
        domain_stats = self._stats_service.get_statistics_summary()
        filter_stats = self._filter_manager.get_statistics()

        return {
            "domain_tracking": domain_stats,
            "search_filters": filter_stats,
            "review_queue_size": self.get_review_queue_count(),
        }

    def get_domain_detail(self, domain: str) -> Dict[str, Any] | None:
        """
        获取域名详细信息

        Args:
            domain: 域名

        Returns:
            域名详细信息（统计 + 黑白名单状态）
        """
        stats = self._stats_service.get_domain_stats(domain)
        if not stats:
            return None

        # 补充黑白名单状态
        test_url = f"https://{domain}/"
        stats["is_blacklisted"] = self._filter_manager.is_blacklisted(test_url)
        stats["is_whitelisted"] = self._filter_manager.is_whitelisted(test_url)

        return stats

    def get_low_quality_domains(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取低质量域名列表（按质量分排序）

        Args:
            limit: 返回数量限制

        Returns:
            低质量域名列表
        """
        return self._stats_service.get_all_stats(limit=limit, sort_by="avg_quality_score")


# 全局单例
_review_service: AutoReviewService | None = None


def get_auto_review_service() -> AutoReviewService:
    """获取全局自动审核服务实例"""
    global _review_service
    if _review_service is None:
        _review_service = AutoReviewService()
    return _review_service
