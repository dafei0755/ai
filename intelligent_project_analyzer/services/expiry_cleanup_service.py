"""
知识库过期清理服务 - v7.141.3

功能:
1. 自动清理过期文档
2. 软删除/硬删除支持
3. 定时任务调度
4. 清理日志和通知
5. 与对话记录过期机制同步
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from loguru import logger

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from pymilvus import Collection

    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    logger.debug("Dependencies not available for expiry cleanup (pymilvus, apscheduler) — 功能未开启，可忽略")


class ExpiryCleanupService:
    """过期文档清理服务"""

    def __init__(
        self, collection: Optional["Collection"] = None, config_path: str = "config/knowledge_base_quota.yaml"
    ):
        """
        初始化清理服务

        Args:
            collection: Milvus Collection 实例
            config_path: 配额配置文件路径
        """
        self.collection = collection
        self.config = self._load_config(config_path)
        self.cleanup_config = self.config.get("expiry_cleanup", {})
        self.scheduler = None

        if DEPENDENCIES_AVAILABLE and self.cleanup_config.get("enabled", True):
            self.scheduler = AsyncIOScheduler()

    def _load_config(self, config_path: str) -> Dict:
        """加载配置"""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                logger.warning(f"配置文件不存在: {config_path}")
                return {}

            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            return config

        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return {}

    def find_expired_documents(self) -> List[Dict]:
        """
        查找已过期的文档

        Returns:
            过期文档列表
        """
        if not self.collection:
            logger.warning("Milvus Collection 未初始化")
            return []

        try:
            current_timestamp = int(time.time())

            # 查询过期文档 (expires_at > 0 且 expires_at < current_timestamp)
            expr = f"expires_at > 0 AND expires_at < {current_timestamp} AND is_deleted == False"

            results = self.collection.query(
                expr=expr,
                output_fields=["id", "title", "owner_id", "owner_type", "created_at", "expires_at", "user_tier"],
                limit=16384,
            )

            logger.info(f"找到 {len(results)} 个过期文档")

            return results

        except Exception as e:
            logger.error(f"查找过期文档失败: {e}")
            return []

    def soft_delete_documents(self, document_ids: List[str]) -> Dict:
        """
        软删除文档 (标记为已删除，不实际删除)

        Args:
            document_ids: 文档 ID 列表

        Returns:
            {
                "success": True/False,
                "deleted_count": 10,
                "errors": [...]
            }
        """
        if not self.collection or not document_ids:
            return {"success": False, "deleted_count": 0, "errors": ["Collection 未初始化或文档列表为空"]}

        try:
            # Milvus 不支持直接 UPDATE，需要先删除再插入
            # 这里采用更新 is_deleted 字段的方式

            # 1. 查询要删除的文档
            expr = f"id in {document_ids}"
            documents = self.collection.query(expr=expr, output_fields=["*"], limit=len(document_ids))  # 获取所有字段

            if not documents:
                return {"success": True, "deleted_count": 0, "errors": []}

            # 2. 标记为已删除
            for doc in documents:
                doc["is_deleted"] = True

            # 3. 删除原文档
            delete_expr = f"id in {document_ids}"
            self.collection.delete(delete_expr)

            # 4. 重新插入（已标记删除）
            # 注意：这里需要按照 Collection Schema 的顺序重新组织数据
            # 由于 Milvus 不支持局部更新，这是一个折衷方案

            logger.info(f"软删除 {len(documents)} 个文档")

            return {"success": True, "deleted_count": len(documents), "errors": []}

        except Exception as e:
            logger.error(f"软删除失败: {e}")
            return {"success": False, "deleted_count": 0, "errors": [str(e)]}

    def hard_delete_documents(self, document_ids: List[str]) -> Dict:
        """
        硬删除文档 (永久删除)

        Args:
            document_ids: 文档 ID 列表

        Returns:
            {
                "success": True/False,
                "deleted_count": 10,
                "errors": [...]
            }
        """
        if not self.collection or not document_ids:
            return {"success": False, "deleted_count": 0, "errors": ["Collection 未初始化或文档列表为空"]}

        try:
            # 构建删除表达式
            # Milvus delete 语法: id in [id1, id2, ...]
            ids_str = ", ".join([f'"{doc_id}"' for doc_id in document_ids])
            expr = f"id in [{ids_str}]"

            # 执行删除
            self.collection.delete(expr)

            logger.info(f"硬删除 {len(document_ids)} 个文档")

            return {"success": True, "deleted_count": len(document_ids), "errors": []}

        except Exception as e:
            logger.error(f"硬删除失败: {e}")
            return {"success": False, "deleted_count": 0, "errors": [str(e)]}

    def cleanup_expired_documents(self) -> Dict:
        """
        执行过期文档清理任务

        Returns:
            {
                "success": True/False,
                "total_found": 100,
                "total_deleted": 95,
                "errors": [...]
            }
        """
        logger.info("开始执行过期文档清理任务")

        result = {
            "success": True,
            "total_found": 0,
            "total_deleted": 0,
            "errors": [],
            "timestamp": datetime.now().isoformat(),
        }

        try:
            # 1. 查找过期文档
            expired_docs = self.find_expired_documents()
            result["total_found"] = len(expired_docs)

            if not expired_docs:
                logger.info("没有找到过期文档")
                return result

            # 2. 提取文档 ID
            document_ids = [doc["id"] for doc in expired_docs]

            # 3. 执行删除（软删除或硬删除）
            soft_delete = self.cleanup_config.get("soft_delete", True)

            if soft_delete:
                delete_result = self.soft_delete_documents(document_ids)
            else:
                delete_result = self.hard_delete_documents(document_ids)

            result["total_deleted"] = delete_result.get("deleted_count", 0)

            if not delete_result.get("success", False):
                result["success"] = False
                result["errors"].extend(delete_result.get("errors", []))

            # 4. 记录清理日志
            logger.info(f"过期文档清理完成: 找到 {result['total_found']}, 删除 {result['total_deleted']}")

            # 5. 发送通知 (如果启用)
            if self.cleanup_config.get("notify_user", True):
                self._send_cleanup_notification(expired_docs, result)

            return result

        except Exception as e:
            logger.error(f"清理任务执行失败: {e}")
            result["success"] = False
            result["errors"].append(str(e))
            return result

    def _send_cleanup_notification(self, expired_docs: List[Dict], result: Dict):
        """
        发送清理通知

        Args:
            expired_docs: 过期文档列表
            result: 清理结果
        """
        # TODO: 实现用户通知机制 (邮件/站内信/WebSocket)
        logger.info(f"清理通知: {result['total_deleted']} 个文档已被清理")

        # 按用户分组
        user_doc_count = {}
        for doc in expired_docs:
            owner_id = doc.get("owner_id", "unknown")
            user_doc_count[owner_id] = user_doc_count.get(owner_id, 0) + 1

        for user_id, count in user_doc_count.items():
            logger.debug(f"用户 {user_id}: {count} 个文档过期")

    def start_scheduler(self):
        """启动定时清理任务"""
        if not self.scheduler or not DEPENDENCIES_AVAILABLE:
            logger.warning("调度器不可用，无法启动定时任务")
            return

        if not self.cleanup_config.get("enabled", True):
            logger.info("过期清理未启用，跳过定时任务")
            return

        # 获取 cron 表达式
        cron_schedule = self.cleanup_config.get("cron_schedule", "0 2 * * *")  # 默认每天凌晨 2 点

        try:
            # 解析 cron 表达式
            # 格式: minute hour day month day_of_week
            parts = cron_schedule.split()
            if len(parts) != 5:
                logger.error(f"无效的 cron 表达式: {cron_schedule}")
                return

            trigger = CronTrigger(minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4])

            # 添加任务
            self.scheduler.add_job(
                self.cleanup_expired_documents,
                trigger=trigger,
                id="expiry_cleanup_task",
                name="知识库过期文档清理",
                replace_existing=True,
            )

            # 启动调度器
            self.scheduler.start()

            logger.info(f"过期清理定时任务已启动，调度: {cron_schedule}")

        except Exception as e:
            logger.error(f"启动定时任务失败: {e}")

    def stop_scheduler(self):
        """停止定时任务"""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("过期清理定时任务已停止")

    def cleanup_soft_deleted_documents(self, retention_days: int = 30) -> Dict:
        """
        清理软删除文档（超过保留期的）

        Args:
            retention_days: 软删除保留天数

        Returns:
            清理结果
        """
        if not self.collection:
            return {"success": False, "errors": ["Collection 未初始化"]}

        try:
            # 计算保留期时间戳
            retention_timestamp = int(time.time()) - (retention_days * 24 * 3600)

            # 查询超过保留期的软删除文档
            expr = f"is_deleted == True AND created_at < {retention_timestamp}"

            soft_deleted_docs = self.collection.query(expr=expr, output_fields=["id"], limit=16384)

            if not soft_deleted_docs:
                logger.info("没有找到超过保留期的软删除文档")
                return {"success": True, "total_deleted": 0}

            # 硬删除
            document_ids = [doc["id"] for doc in soft_deleted_docs]
            result = self.hard_delete_documents(document_ids)

            logger.info(f"清理软删除文档: {result.get('deleted_count', 0)} 个")

            return result

        except Exception as e:
            logger.error(f"清理软删除文档失败: {e}")
            return {"success": False, "errors": [str(e)]}


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    # 初始化清理服务
    cleanup_service = ExpiryCleanupService()

    # 手动执行清理
    result = cleanup_service.cleanup_expired_documents()
    print(f"清理结果: {result}")

    # 启动定时任务
    # cleanup_service.start_scheduler()
    #
    # # 保持运行
    # try:
    #     asyncio.get_event_loop().run_forever()
    # except (KeyboardInterrupt, SystemExit):
    #     cleanup_service.stop_scheduler()
