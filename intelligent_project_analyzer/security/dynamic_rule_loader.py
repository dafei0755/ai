"""
动态安全规则加载器 - 支持热加载配置
"""

import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import yaml
from loguru import logger


class DynamicRuleLoader:
    """动态安全规则加载器（支持热加载）"""

    def __init__(
        self,
        config_path: str | None = None,
        auto_reload: bool = True,
        reload_interval: int = 60
    ):
        """
        初始化动态规则加载器

        Args:
            config_path: 配置文件路径（默认：security_rules.yaml）
            auto_reload: 是否自动重载（检测文件修改）
            reload_interval: 重载检查间隔（秒）
        """
        # 配置文件路径
        if config_path is None:
            # 默认路径：与本文件同目录的security_rules.yaml
            current_dir = Path(__file__).parent
            config_path = current_dir / "security_rules.yaml"
        self.config_path = Path(config_path)

        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        # 加载配置
        self._rules: Dict[str, Any] = {}
        self._last_modified: float = 0
        self._lock = threading.Lock()  # 线程安全

        # 自动重载配置
        self.auto_reload = auto_reload
        self.reload_interval = reload_interval

        # 首次加载
        self._reload_rules()

        logger.info(f" 动态规则加载器初始化成功 (配置文件: {self.config_path})")

    def get_rules(self) -> Dict[str, Any]:
        """
        获取当前规则配置（如果文件被修改，自动重载）

        Returns:
            规则配置字典
        """
        if self.auto_reload:
            self._check_and_reload()
        return self._rules.copy()

    def get_keywords(self) -> Dict[str, Any]:
        """获取关键词规则"""
        return self._rules.get("keywords", {})

    def get_privacy_patterns(self) -> Dict[str, Any]:
        """获取隐私信息检测规则"""
        return self._rules.get("privacy_patterns", {})

    def get_evasion_patterns(self) -> Dict[str, Any]:
        """获取变形规避检测规则"""
        return self._rules.get("evasion_patterns", {})

    def get_threat_intelligence(self) -> Dict[str, Any]:
        """获取威胁情报规则"""
        return self._rules.get("threat_intelligence", {})

    def get_detection_config(self) -> Dict[str, Any]:
        """获取检测配置"""
        return self._rules.get("detection_config", {})

    def get_whitelist(self) -> Dict[str, Any]:
        """获取白名单配置"""
        return self._rules.get("whitelist", {})

    def is_whitelisted(self, text: str, user_id: str | None = None) -> bool:
        """
        检查是否在白名单中

        Args:
            text: 待检测文本
            user_id: 用户ID（可选）

        Returns:
            是否在白名单中
        """
        whitelist = self.get_whitelist()
        if not whitelist.get("enabled", False):
            return False

        # 检查用户白名单
        if user_id and user_id in whitelist.get("users", []):
            return True

        # 检查域名白名单
        domains = whitelist.get("domains", [])
        for domain in domains:
            if domain in text:
                return True

        return False

    def _check_and_reload(self):
        """检查文件是否被修改，如果是则重载"""
        try:
            current_modified = os.path.getmtime(self.config_path)
            if current_modified > self._last_modified:
                self._reload_rules()
        except Exception as e:
            logger.error(f" 检查配置文件修改时间失败: {e}")

    def _reload_rules(self):
        """重新加载配置文件"""
        with self._lock:
            try:
                with open(self.config_path, encoding='utf-8') as f:
                    rules = yaml.safe_load(f)

                if not rules:
                    logger.error(" 配置文件为空")
                    return

                self._rules = rules
                self._last_modified = os.path.getmtime(self.config_path)

                logger.info(
                    f" 安全规则已重载 "
                    f"(版本: {rules.get('version', 'unknown')}, "
                    f"关键词类别: {len(rules.get('keywords', {}))}, "
                    f"隐私模式: {len(rules.get('privacy_patterns', {}))}, "
                    f"规避模式: {len(rules.get('evasion_patterns', {}))})"
                )

            except yaml.YAMLError as e:
                logger.error(f" YAML解析错误: {e}")
            except Exception as e:
                logger.error(f" 加载配置文件失败: {e}")

    def force_reload(self):
        """强制重新加载配置"""
        logger.info(" 强制重新加载安全规则...")
        self._reload_rules()

    def update_threat_intelligence(
        self,
        domains: list | None = None,
        ips: list | None = None,
        keywords: list | None = None
    ):
        """
        更新威胁情报（从外部情报源同步）

        Args:
            domains: 恶意域名列表
            ips: 恶意IP列表
            keywords: 威胁关键词列表
        """
        with self._lock:
            threat_intel = self._rules.get("threat_intelligence", {})

            if domains is not None:
                threat_intel.setdefault("malicious_domains", {})["domains"] = domains
                logger.info(f" 更新恶意域名: {len(domains)}个")

            if ips is not None:
                threat_intel.setdefault("malicious_ips", {})["ips"] = ips
                logger.info(f" 更新恶意IP: {len(ips)}个")

            if keywords is not None:
                threat_intel.setdefault("malicious_keywords", {})["keywords"] = keywords
                logger.info(f" 更新威胁关键词: {len(keywords)}个")

            # 更新时间戳
            threat_intel["last_updated"] = datetime.now().isoformat()

            self._rules["threat_intelligence"] = threat_intel

            # 保存到文件（可选）
            try:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(self._rules, f, allow_unicode=True, default_flow_style=False)
                logger.info(" 威胁情报已保存到配置文件")
            except Exception as e:
                logger.error(f" 保存威胁情报失败: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        获取规则统计信息

        Returns:
            统计信息字典
        """
        keywords = self.get_keywords()
        privacy = self.get_privacy_patterns()
        evasion = self.get_evasion_patterns()
        threat_intel = self.get_threat_intelligence()

        # 统计关键词数量
        total_keywords = sum(
            len(cat.get("words", []))
            for cat in keywords.values()
            if isinstance(cat, dict)
        )

        # 统计启用的规则
        enabled_keywords = sum(
            1 for cat in keywords.values()
            if isinstance(cat, dict) and cat.get("enabled", True)
        )

        enabled_privacy = sum(
            1 for pattern in privacy.values()
            if isinstance(pattern, dict) and pattern.get("enabled", True)
        )

        enabled_evasion = sum(
            1 for pattern in evasion.values()
            if isinstance(pattern, dict) and pattern.get("enabled", True)
        )

        return {
            "config_file": str(self.config_path),
            "version": self._rules.get("version", "unknown"),
            "last_modified": datetime.fromtimestamp(self._last_modified).isoformat(),
            "keywords": {
                "total_categories": len(keywords),
                "enabled_categories": enabled_keywords,
                "total_words": total_keywords
            },
            "privacy_patterns": {
                "total": len(privacy),
                "enabled": enabled_privacy
            },
            "evasion_patterns": {
                "total": len(evasion),
                "enabled": enabled_evasion
            },
            "threat_intelligence": {
                "enabled": threat_intel.get("enabled", False),
                "last_updated": threat_intel.get("last_updated", "never"),
                "malicious_domains": len(threat_intel.get("malicious_domains", {}).get("domains", [])),
                "malicious_ips": len(threat_intel.get("malicious_ips", {}).get("ips", [])),
                "malicious_keywords": len(threat_intel.get("malicious_keywords", {}).get("keywords", []))
            }
        }


# 全局单例（懒加载）
_loader_instance: DynamicRuleLoader | None = None
_loader_lock = threading.Lock()


def get_rule_loader() -> DynamicRuleLoader:
    """
    获取动态规则加载器单例

    Returns:
        DynamicRuleLoader实例
    """
    global _loader_instance

    if _loader_instance is None:
        with _loader_lock:
            if _loader_instance is None:
                _loader_instance = DynamicRuleLoader()

    return _loader_instance


def reload_rules():
    """强制重新加载规则（全局函数）"""
    loader = get_rule_loader()
    loader.force_reload()
