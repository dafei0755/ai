"""
知识库配额管理服务 - v7.141.3

功能:
1. 用户配额检查
2. 文档数量/存储空间统计
3. 配额超限告警
4. 会员等级管理
5. 与对话记录过期机制同步
"""

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from loguru import logger

try:
    from pymilvus import Collection, connections

    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False
    logger.warning("Milvus not available for quota manager")


class QuotaConfig:
    """配额配置类"""

    def __init__(self, config_path: str = "config/knowledge_base_quota.yaml"):
        """
        初始化配额配置

        Args:
            config_path: 配额配置文件路径
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.tiers = self.config.get("membership_tiers", {})
        self.default_tier = self.config.get("default_tier", "free")

    def _load_config(self) -> Dict:
        """加载配额配置"""
        try:
            if not self.config_path.exists():
                logger.error(f"配额配置文件不存在: {self.config_path}")
                return self._get_fallback_config()

            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            logger.info(f"配额配置已加载: {self.config_path}")
            return config

        except Exception as e:
            logger.error(f"加载配额配置失败: {e}")
            return self._get_fallback_config()

    def _get_fallback_config(self) -> Dict:
        """降级配置 (配置文件加载失败时使用)"""
        return {
            "membership_tiers": {
                "free": {
                    "name": "免费版",
                    "quota": {
                        "max_documents": 10,
                        "max_storage_mb": 50,
                        "max_file_size_mb": 5,
                        "document_expiry_days": 30,
                        "allow_sharing": False,
                        "allow_team_kb": False,
                    },
                }
            },
            "default_tier": "free",
            "quota_check": {"enabled": True},
            "exempt_users": ["admin", "system"],
        }

    def get_tier_quota(self, tier: str) -> Optional[Dict]:
        """
        获取指定会员等级的配额

        Args:
            tier: 会员等级 (free, basic, professional, enterprise)

        Returns:
            配额字典
        """
        if tier not in self.tiers:
            logger.warning(f"会员等级 '{tier}' 不存在，使用默认等级 '{self.default_tier}'")
            tier = self.default_tier

        return self.tiers.get(tier, {}).get("quota", {})

    def is_quota_enabled(self) -> bool:
        """配额检查是否启用"""
        return self.config.get("quota_check", {}).get("enabled", True)

    def is_user_exempt(self, user_id: str) -> bool:
        """检查用户是否豁免配额限制"""
        exempt_users = self.config.get("exempt_users", [])
        return user_id in exempt_users


class QuotaManager:
    """配额管理器"""

    def __init__(
        self, collection: Optional["Collection"] = None, config_path: str = "config/knowledge_base_quota.yaml"
    ):
        """
        初始化配额管理器

        Args:
            collection: Milvus Collection 实例
            config_path: 配额配置文件路径
        """
        self.collection = collection
        self.quota_config = QuotaConfig(config_path)

    def get_user_usage(self, user_id: str) -> Dict:
        """
        获取用户当前使用量

        Args:
            user_id: 用户ID

        Returns:
            {
                "document_count": 10,
                "storage_mb": 25.5,
                "oldest_document_timestamp": 1234567890,
                "newest_document_timestamp": 1234567890
            }
        """
        if not self.collection or not MILVUS_AVAILABLE:
            logger.warning("Milvus 不可用，返回模拟使用量")
            return {"document_count": 0, "storage_mb": 0.0}

        try:
            # 构建查询表达式 (仅查询未删除的文档)
            expr = f'owner_type == "user" AND owner_id == "{user_id}" AND is_deleted == False'

            # 查询文档
            results = self.collection.query(
                expr=expr, output_fields=["file_size_bytes", "created_at"], limit=16384  # Milvus 单次查询最大限制
            )

            # 统计
            document_count = len(results)
            total_bytes = sum(doc.get("file_size_bytes", 0) for doc in results)
            storage_mb = total_bytes / (1024 * 1024)

            # 获取最早和最新文档时间
            timestamps = [doc.get("created_at", 0) for doc in results if doc.get("created_at", 0) > 0]
            oldest = min(timestamps) if timestamps else 0
            newest = max(timestamps) if timestamps else 0

            logger.debug(f"用户 {user_id} 使用量: {document_count} 个文档, {storage_mb:.2f} MB")

            return {
                "document_count": document_count,
                "storage_mb": round(storage_mb, 2),
                "oldest_document_timestamp": oldest,
                "newest_document_timestamp": newest,
            }

        except Exception as e:
            logger.error(f"获取用户使用量失败: {e}")
            return {"document_count": 0, "storage_mb": 0.0}

    def check_quota(self, user_id: str, user_tier: str = "free") -> Dict:
        """
        检查用户配额状态

        Args:
            user_id: 用户ID
            user_tier: 用户会员等级

        Returns:
            {
                "allowed": True/False,
                "current_usage": {...},
                "quota_limit": {...},
                "warnings": [...],
                "errors": [...]
            }
        """
        result = {
            "allowed": True,
            "current_usage": {},
            "quota_limit": {},
            "warnings": [],
            "errors": [],
        }

        # 1. 检查是否启用配额检查
        if not self.quota_config.is_quota_enabled():
            result["warnings"].append("配额检查未启用")
            return result

        # 2. 检查用户是否豁免
        if self.quota_config.is_user_exempt(user_id):
            result["warnings"].append(f"用户 {user_id} 豁免配额限制")
            return result

        # 3. 获取配额限制
        quota = self.quota_config.get_tier_quota(user_tier)
        if not quota:
            result["errors"].append(f"无法获取会员等级 '{user_tier}' 的配额配置")
            result["allowed"] = False
            return result

        result["quota_limit"] = quota

        # 4. 获取当前使用量
        usage = self.get_user_usage(user_id)
        result["current_usage"] = usage

        # 5. 检查文档数量限制
        max_documents = quota.get("max_documents", 10)
        if max_documents != -1 and usage["document_count"] >= max_documents:
            result["allowed"] = False
            result["errors"].append(f"文档数量已达上限 ({usage['document_count']}/{max_documents})")

        # 6. 检查存储空间限制
        max_storage_mb = quota.get("max_storage_mb", 50)
        if max_storage_mb != -1 and usage["storage_mb"] >= max_storage_mb:
            result["allowed"] = False
            result["errors"].append(f"存储空间已达上限 ({usage['storage_mb']:.2f}/{max_storage_mb} MB)")

        # 7. 配额警告 (接近上限)
        warning_threshold = self.quota_config.config.get("quota_check", {}).get("warning_threshold", 80) / 100

        if max_documents != -1:
            doc_usage_ratio = usage["document_count"] / max_documents
            if doc_usage_ratio >= warning_threshold:
                result["warnings"].append(
                    f"文档数量接近上限 ({usage['document_count']}/{max_documents}, {doc_usage_ratio * 100:.1f}%)"
                )

        if max_storage_mb != -1:
            storage_usage_ratio = usage["storage_mb"] / max_storage_mb
            if storage_usage_ratio >= warning_threshold:
                result["warnings"].append(
                    f"存储空间接近上限 ({usage['storage_mb']:.2f}/{max_storage_mb} MB, {storage_usage_ratio * 100:.1f}%)"
                )

        logger.debug(f"用户 {user_id} 配额检查: {'通过' if result['allowed'] else '超限'}")

        return result

    def check_file_size(self, file_size_bytes: int, user_tier: str = "free") -> Dict:
        """
        检查文件大小是否符合配额限制

        Args:
            file_size_bytes: 文件大小（字节）
            user_tier: 用户会员等级

        Returns:
            {
                "allowed": True/False,
                "file_size_mb": 5.5,
                "max_file_size_mb": 10,
                "error": "..."
            }
        """
        quota = self.quota_config.get_tier_quota(user_tier)
        max_file_size_mb = quota.get("max_file_size_mb", 5)

        file_size_mb = file_size_bytes / (1024 * 1024)

        result = {
            "allowed": True,
            "file_size_mb": round(file_size_mb, 2),
            "max_file_size_mb": max_file_size_mb,
        }

        if max_file_size_mb != -1 and file_size_mb > max_file_size_mb:
            result["allowed"] = False
            result["error"] = f"文件大小超过限制 ({file_size_mb:.2f}/{max_file_size_mb} MB)"

        return result

    def calculate_expiry_timestamp(self, user_tier: str = "free") -> int:
        """
        计算文档过期时间戳

        Args:
            user_tier: 用户会员等级

        Returns:
            Unix 时间戳，0 表示永不过期
        """
        quota = self.quota_config.get_tier_quota(user_tier)
        expiry_days = quota.get("document_expiry_days", 30)

        if expiry_days == -1:
            return 0  # 永不过期

        expiry_datetime = datetime.now() + timedelta(days=expiry_days)
        return int(expiry_datetime.timestamp())

    def check_sharing_allowed(self, user_tier: str = "free") -> bool:
        """检查是否允许共享文档"""
        quota = self.quota_config.get_tier_quota(user_tier)
        return quota.get("allow_sharing", False)

    def check_team_kb_allowed(self, user_tier: str = "free") -> bool:
        """检查是否允许创建团队知识库"""
        quota = self.quota_config.get_tier_quota(user_tier)
        return quota.get("allow_team_kb", False)

    def get_allowed_document_types(self, user_tier: str = "free") -> List[str]:
        """获取允许的文档类型"""
        quota = self.quota_config.get_tier_quota(user_tier)
        return quota.get("allowed_document_types", ["文档"])


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    # 初始化配额管理器
    quota_manager = QuotaManager()

    # 检查用户配额
    result = quota_manager.check_quota(user_id="user_123", user_tier="free")
    print(f"配额检查结果: {result}")

    # 检查文件大小
    file_check = quota_manager.check_file_size(file_size_bytes=6 * 1024 * 1024, user_tier="free")
    print(f"文件大小检查: {file_check}")

    # 计算过期时间
    expiry = quota_manager.calculate_expiry_timestamp(user_tier="free")
    print(f"过期时间戳: {expiry} ({datetime.fromtimestamp(expiry) if expiry > 0 else '永不过期'})")
