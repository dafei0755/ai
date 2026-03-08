"""
域名质量统计服务

追踪搜索结果中每个域名的质量表现，支持自动评估和审核队列
"""

import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List
from urllib.parse import urlparse

from loguru import logger
from pydantic import BaseModel, Field


class DomainStats(BaseModel):
    """单个域名的质量统计"""

    domain: str = Field(..., description="域名")
    total_appearances: int = Field(default=0, description="总出现次数")
    avg_quality_score: float = Field(default=0.0, description="平均质量分 (0-100)")
    avg_relevance_score: float = Field(default=0.0, description="平均相关性分 (0-100)")
    low_score_count: int = Field(default=0, description="低分次数 (quality < 40)")
    very_low_score_count: int = Field(default=0, description="极低分次数 (quality < 25)")
    content_short_count: int = Field(default=0, description="内容过短次数 (<50字符)")
    dedup_filtered_count: int = Field(default=0, description="因重复被过滤次数")
    first_seen: str = Field(default_factory=lambda: datetime.now().isoformat(), description="首次出现时间")
    last_seen: str = Field(default_factory=lambda: datetime.now().isoformat(), description="最后出现时间")

    # 审核相关
    is_in_review_queue: bool = Field(default=False, description="是否在审核队列中")
    review_reason: str | None = Field(default=None, description="加入审核队列原因")
    review_added_time: str | None = Field(default=None, description="加入审核队列时间")

    # 处理状态
    is_approved: bool = Field(default=False, description="是否已批准（加入白名单）")
    is_blocked: bool = Field(default=False, description="是否已屏蔽（加入黑名单）")
    admin_action_time: str | None = Field(default=None, description="管理员操作时间")
    admin_notes: str | None = Field(default=None, description="管理员备注")

    # 历史分数记录（保留最近20次）
    score_history: List[float] = Field(default_factory=list, description="历史质量分记录")

    def update_score(
        self, quality_score: float, relevance_score: float, content_length: int = 0, is_duplicate: bool = False
    ):
        """更新域名统计"""
        self.total_appearances += 1
        self.last_seen = datetime.now().isoformat()

        # 计算新的平均分
        prev_total = self.total_appearances - 1
        if prev_total > 0:
            self.avg_quality_score = (self.avg_quality_score * prev_total + quality_score) / self.total_appearances
            self.avg_relevance_score = (
                self.avg_relevance_score * prev_total + relevance_score
            ) / self.total_appearances
        else:
            self.avg_quality_score = quality_score
            self.avg_relevance_score = relevance_score

        # 低分计数
        if quality_score < 40:
            self.low_score_count += 1
        if quality_score < 25:
            self.very_low_score_count += 1

        # 内容过短
        if content_length < 50:
            self.content_short_count += 1

        # 重复过滤
        if is_duplicate:
            self.dedup_filtered_count += 1

        # 保留最近20次分数
        self.score_history.append(quality_score)
        if len(self.score_history) > 20:
            self.score_history = self.score_history[-20:]


class DomainQualityStatsService:
    """
    域名质量统计服务

    功能：
    1. 追踪每个域名的质量表现
    2. 识别低质量域名并加入审核队列
    3. 支持管理员审核操作
    """

    # 审核触发阈值
    REVIEW_THRESHOLDS = {
        "low_score_consecutive": 5,  # 连续低分次数 >= 5
        "very_low_score_count": 3,  # 极低分次数 >= 3
        "avg_quality_below": 35,  # 平均质量分 < 35
        "content_short_rate": 0.7,  # 内容过短率 > 70%
        "min_appearances": 3,  # 最少出现次数（避免误判）
    }

    def __init__(self, data_path: Path | None = None):
        """
        初始化服务

        Args:
            data_path: 数据文件路径，默认为 data/domain_quality_stats.json
        """
        if data_path is None:
            project_root = Path(__file__).parent.parent.parent
            data_path = project_root / "data" / "domain_quality_stats.json"

        self.data_path = Path(data_path)
        self._stats: Dict[str, DomainStats] = {}
        self._lock = Lock()

        # 加载已有数据
        self._load()

        logger.info(f" 域名质量统计服务已初始化，已加载 {len(self._stats)} 个域名记录")

    def _load(self):
        """加载统计数据"""
        try:
            if self.data_path.exists():
                with open(self.data_path, encoding="utf-8") as f:
                    data = json.load(f)
                    for domain, stats_dict in data.items():
                        self._stats[domain] = DomainStats(**stats_dict)
        except Exception as e:
            logger.error(f" 加载域名统计数据失败: {e}")
            self._stats = {}

    def _save(self):
        """保存统计数据"""
        try:
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_path, "w", encoding="utf-8") as f:
                data = {domain: stats.model_dump() for domain, stats in self._stats.items()}
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f" 保存域名统计数据失败: {e}")

    @staticmethod
    def extract_domain(url: str) -> str | None:
        """从URL中提取域名"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # 移除 www. 前缀
            if domain.startswith("www."):
                domain = domain[4:]
            return domain if domain else None
        except Exception:
            return None

    def record_result(
        self,
        url: str,
        quality_score: float,
        relevance_score: float = 0.0,
        content_length: int = 0,
        is_duplicate: bool = False,
    ):
        """
        记录搜索结果质量

        Args:
            url: 结果URL
            quality_score: 综合质量分 (0-100)
            relevance_score: 相关性分 (0-100)
            content_length: 内容长度
            is_duplicate: 是否为重复内容
        """
        domain = self.extract_domain(url)
        if not domain:
            return

        with self._lock:
            if domain not in self._stats:
                self._stats[domain] = DomainStats(domain=domain)

            stats = self._stats[domain]
            stats.update_score(quality_score, relevance_score, content_length, is_duplicate)

            # 检查是否需要加入审核队列
            self._check_review_trigger(stats)

            # 定期保存（每10次记录保存一次）
            if stats.total_appearances % 10 == 0:
                self._save()

    def _check_review_trigger(self, stats: DomainStats):
        """检查是否触发审核队列"""
        if stats.is_in_review_queue or stats.is_blocked or stats.is_approved:
            return

        thresholds = self.REVIEW_THRESHOLDS
        reasons = []

        # 只有出现次数足够时才判断
        if stats.total_appearances < thresholds["min_appearances"]:
            return

        # 检查极低分次数
        if stats.very_low_score_count >= thresholds["very_low_score_count"]:
            reasons.append(f"极低分(quality<25)出现{stats.very_low_score_count}次")

        # 检查平均质量分
        if stats.avg_quality_score < thresholds["avg_quality_below"]:
            reasons.append(f"平均质量分过低({stats.avg_quality_score:.1f})")

        # 检查内容过短率
        if stats.total_appearances >= 5:
            short_rate = stats.content_short_count / stats.total_appearances
            if short_rate > thresholds["content_short_rate"]:
                reasons.append(f"内容过短率{short_rate:.0%}")

        # 检查连续低分（通过历史记录判断）
        if len(stats.score_history) >= thresholds["low_score_consecutive"]:
            recent_scores = stats.score_history[-thresholds["low_score_consecutive"] :]
            if all(s < 40 for s in recent_scores):
                reasons.append(f"连续{len(recent_scores)}次低分")

        # 如果有任何触发原因，加入审核队列
        if reasons:
            stats.is_in_review_queue = True
            stats.review_reason = "; ".join(reasons)
            stats.review_added_time = datetime.now().isoformat()
            logger.warning(f"️ 域名 {stats.domain} 已加入审核队列: {stats.review_reason}")

    def get_review_queue(self) -> List[Dict[str, Any]]:
        """
        获取待审核队列

        Returns:
            待审核域名列表，按严重程度排序
        """
        queue = []
        for domain, stats in self._stats.items():
            if stats.is_in_review_queue and not stats.is_blocked and not stats.is_approved:
                queue.append(
                    {
                        "domain": domain,
                        "total_appearances": stats.total_appearances,
                        "avg_quality_score": round(stats.avg_quality_score, 1),
                        "avg_relevance_score": round(stats.avg_relevance_score, 1),
                        "low_score_count": stats.low_score_count,
                        "very_low_score_count": stats.very_low_score_count,
                        "content_short_count": stats.content_short_count,
                        "review_reason": stats.review_reason,
                        "review_added_time": stats.review_added_time,
                        "first_seen": stats.first_seen,
                        "last_seen": stats.last_seen,
                        "score_history": stats.score_history[-10:],  # 最近10次分数
                    }
                )

        # 按平均质量分升序排序（分数越低越严重）
        queue.sort(key=lambda x: x["avg_quality_score"])
        return queue

    def approve_domain(self, domain: str, admin_notes: str | None = None) -> bool:
        """
        批准域名（移出审核队列，标记为已批准）

        Args:
            domain: 域名
            admin_notes: 管理员备注

        Returns:
            是否成功
        """
        with self._lock:
            if domain not in self._stats:
                logger.warning(f"️ 域名不存在: {domain}")
                return False

            stats = self._stats[domain]
            stats.is_in_review_queue = False
            stats.is_approved = True
            stats.admin_action_time = datetime.now().isoformat()
            stats.admin_notes = admin_notes

            self._save()
            logger.info(f" 域名 {domain} 已批准")
            return True

    def block_domain(self, domain: str, admin_notes: str | None = None) -> Dict[str, Any]:
        """
        屏蔽域名（移出审核队列，标记为已屏蔽，返回加入黑名单所需信息）

        Args:
            domain: 域名
            admin_notes: 管理员备注

        Returns:
            操作结果和黑名单添加信息
        """
        with self._lock:
            if domain not in self._stats:
                logger.warning(f"️ 域名不存在: {domain}")
                return {"success": False, "error": "域名不存在"}

            stats = self._stats[domain]
            stats.is_in_review_queue = False
            stats.is_blocked = True
            stats.admin_action_time = datetime.now().isoformat()
            stats.admin_notes = admin_notes

            self._save()
            logger.info(f" 域名 {domain} 已标记为屏蔽")

            return {
                "success": True,
                "domain": domain,
                "note": f"自动评估屏蔽 - {stats.review_reason}" + (f" | 管理员备注: {admin_notes}" if admin_notes else ""),
                "stats": {
                    "total_appearances": stats.total_appearances,
                    "avg_quality_score": round(stats.avg_quality_score, 1),
                    "review_reason": stats.review_reason,
                },
            }

    def dismiss_from_queue(self, domain: str, admin_notes: str | None = None) -> bool:
        """
        从审核队列移除（既不批准也不屏蔽，保持观察）

        Args:
            domain: 域名
            admin_notes: 管理员备注

        Returns:
            是否成功
        """
        with self._lock:
            if domain not in self._stats:
                return False

            stats = self._stats[domain]
            stats.is_in_review_queue = False
            stats.admin_notes = admin_notes
            # 重置计数器以便后续重新触发
            stats.low_score_count = 0
            stats.very_low_score_count = 0
            stats.content_short_count = 0

            self._save()
            logger.info(f" 域名 {domain} 已从审核队列移除")
            return True

    def get_domain_stats(self, domain: str) -> Dict[str, Any] | None:
        """获取单个域名的统计信息"""
        if domain in self._stats:
            return self._stats[domain].model_dump()
        return None

    def get_all_stats(self, limit: int = 100, sort_by: str = "total_appearances") -> List[Dict[str, Any]]:
        """
        获取所有域名统计

        Args:
            limit: 返回数量限制
            sort_by: 排序字段

        Returns:
            域名统计列表
        """
        stats_list = [stats.model_dump() for stats in self._stats.values()]

        # 排序
        if sort_by == "avg_quality_score":
            stats_list.sort(key=lambda x: x.get("avg_quality_score", 0))
        elif sort_by == "total_appearances":
            stats_list.sort(key=lambda x: x.get("total_appearances", 0), reverse=True)
        elif sort_by == "last_seen":
            stats_list.sort(key=lambda x: x.get("last_seen", ""), reverse=True)

        return stats_list[:limit]

    def get_statistics_summary(self) -> Dict[str, Any]:
        """获取统计概要"""
        total_domains = len(self._stats)
        in_review = sum(1 for s in self._stats.values() if s.is_in_review_queue)
        blocked = sum(1 for s in self._stats.values() if s.is_blocked)
        approved = sum(1 for s in self._stats.values() if s.is_approved)

        return {
            "total_domains": total_domains,
            "in_review_queue": in_review,
            "blocked": blocked,
            "approved": approved,
            "pending": total_domains - in_review - blocked - approved,
        }

    def save(self):
        """手动保存（用于外部调用）"""
        with self._lock:
            self._save()


# 全局单例
_stats_service: DomainQualityStatsService | None = None


def get_domain_stats_service() -> DomainQualityStatsService:
    """获取全局域名统计服务实例"""
    global _stats_service
    if _stats_service is None:
        _stats_service = DomainQualityStatsService()
    return _stats_service
